"""
/api/v1/analyze — main endpoint.
Accepts multipart form with a CSV/XLSX file.
Returns:
  - POST /analyze        → JSON with summary + metrics
  - GET  /analyze/pdf    → PDF download (uses session cache key)

Session cache is a simple in-process dict keyed by a UUID.
Fine for a stateless single-instance deployment on Render.
"""
import uuid
import json
from fastapi import APIRouter, UploadFile, File, Request, HTTPException
from fastapi.responses import Response, JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

from utils.security import validate_file
from services.file_processor import process_file
from services.ai_service import generate_summary
from services.pdf_service import generate_pdf
from models.schemas import AnalyzeResponse, ErrorResponse

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

# In-process cache: { job_id: {"summary": str, "metrics": dict, "filename": str} }
_job_cache: dict[str, dict] = {}
_MAX_CACHE = 200  # prevent unbounded memory growth


@router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid file type"},
        413: {"model": ErrorResponse, "description": "File too large (> 5 MB)"},
        415: {"model": ErrorResponse, "description": "Disallowed MIME type"},
        422: {"model": ErrorResponse, "description": "Unparseable file"},
        429: {"model": ErrorResponse, "description": "Rate limit exceeded"},
        502: {"model": ErrorResponse, "description": "Upstream AI error"},
        503: {"model": ErrorResponse, "description": "API key not configured"},
    },
    summary="Upload sales data and generate AI executive summary",
    description=(
        "Upload a `.csv` or `.xlsx` file (max 5 MB). "
        "The backend computes aggregated metrics, sends them to Groq (Llama 3.3 70B), "
        "and returns a professional narrative summary plus a `job_id` you can use "
        "to download the PDF via `GET /api/v1/analyze/pdf/{job_id}`."
    ),
)
@limiter.limit("15/minute")
async def analyze(
    request: Request,
    file: UploadFile = File(..., description="CSV or XLSX sales data file"),
):
    # 1. Security: validate extension, MIME, size
    raw = await validate_file(file)

    # 2. Parse & compute metrics
    metrics = process_file(raw, file.filename or "upload")

    # 3. Generate AI summary (only structured metrics reach the LLM)
    summary = generate_summary(metrics)

    # 4. Cache for PDF download
    job_id = str(uuid.uuid4())
    if len(_job_cache) >= _MAX_CACHE:
        # Evict oldest entry
        oldest = next(iter(_job_cache))
        del _job_cache[oldest]
    _job_cache[job_id] = {
        "summary": summary,
        "metrics": metrics,
        "filename": file.filename or "report",
    }

    return AnalyzeResponse(
        status="success",
        summary=summary,
        metrics=metrics,
        filename=file.filename or "upload",
        pdf_available=True,
        job_id=job_id,
    )


@router.get(
    "/analyze/pdf/{job_id}",
    responses={
        200: {"content": {"application/pdf": {}}, "description": "PDF report"},
        404: {"model": ErrorResponse, "description": "Job not found or expired"},
    },
    summary="Download the PDF report for a completed analysis",
    description=(
        "Returns a PDF file generated from a prior `/analyze` call. "
        "Job IDs are cached in-memory for the lifetime of the server process."
    ),
)
async def download_pdf(job_id: str):
    job = _job_cache.get(job_id)
    if not job:
        raise HTTPException(
            status_code=404,
            detail="Job not found. The server may have restarted — please re-upload.",
        )

    pdf_bytes = generate_pdf(
        summary=job["summary"],
        metrics=job["metrics"],
        filename=job["filename"],
    )

    safe_name = job["filename"].rsplit(".", 1)[0].replace(" ", "_")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_name}_report.pdf"'
        },
    )
