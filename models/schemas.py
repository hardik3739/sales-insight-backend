from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class AnalyzeResponse(BaseModel):
    status: str = Field(..., examples=["success"])
    summary: str = Field(..., description="AI-generated executive narrative")
    metrics: dict = Field(..., description="Key computed metrics from the file")
    filename: str = Field(..., description="Original uploaded filename")
    pdf_available: bool = Field(
        True, description="Whether a PDF download is available"
    )
    job_id: str = Field(..., description="UUID to use with GET /analyze/pdf/{job_id}")


class ErrorResponse(BaseModel):
    detail: str
    code: Optional[str] = None
