"""
Basic integration tests that run without a real Groq key.
The AI and PDF services are mocked.
"""
import io
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


# ── Health check ───────────────────────────────────────────────────────────────
def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


# ── Swagger docs reachable ─────────────────────────────────────────────────────
def test_swagger_ui():
    r = client.get("/docs")
    assert r.status_code == 200


# ── /analyze rejects non-file requests ────────────────────────────────────────
def test_analyze_no_file():
    r = client.post("/api/v1/analyze")
    assert r.status_code == 422  # Unprocessable Entity — missing file field


# ── /analyze rejects bad extension ────────────────────────────────────────────
def test_analyze_bad_extension():
    r = client.post(
        "/api/v1/analyze",
        files={"file": ("malware.exe", b"\x00evil", "application/octet-stream")},
    )
    assert r.status_code == 400
    assert "not allowed" in r.json()["detail"].lower()


# ── /analyze happy path (mocked AI + PDF) ─────────────────────────────────────
SAMPLE_CSV = b"""Date,Product_Category,Region,Units_Sold,Unit_Price,Revenue,Status
2026-01-05,Electronics,North,150,1200,180000,Shipped
2026-01-12,Home Appliances,South,45,450,20250,Shipped
2026-02-15,Electronics,North,210,1250,262500,Delivered
"""


@patch("routes.analyze.generate_summary", return_value="Strong Q1 performance.")
def test_analyze_success(mock_summary):
    r = client.post(
        "/api/v1/analyze",
        files={"file": ("sales_q1.csv", SAMPLE_CSV, "text/csv")},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "success"
    assert "summary" in body
    assert "metrics" in body
    assert "job_id" in body or body.get("pdf_available") is True


# ── /analyze/pdf 404 for unknown job ──────────────────────────────────────────
def test_pdf_unknown_job():
    r = client.get("/api/v1/analyze/pdf/nonexistent-job-id")
    assert r.status_code == 404
