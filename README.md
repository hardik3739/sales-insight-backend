# Sales Insight Automator — Backend

> FastAPI · Groq Llama 3.3 · ReportLab PDF · Deployed on Render

---

## Live URLs

| Resource | URL |
|---|---|
| **API Base** | `https://sales-insight-backend.onrender.com` |
| **Swagger UI** | `https://sales-insight-backend.onrender.com/docs` |
| **ReDoc** | `https://sales-insight-backend.onrender.com/redoc` |
| **Health** | `https://sales-insight-backend.onrender.com/health` |

---

## Running Locally via Docker Compose

```bash
# 1. Clone the repo
git clone https://github.com/hardik3739/sales-insight-backend
cd sales-insight-backend

# 2. Create your .env file from the example
cp .env.example .env
# Edit .env and add your GROQ_API_KEY

# 3. Spin up
docker-compose up --build

# 4. Open Swagger
open http://localhost:8000/docs
```

---

## Request Flow

```
User uploads CSV/XLSX
        │
        ▼
POST /api/v1/analyze
        │
   ┌────┴───────────────┐
   │ Security layer:    │
   │ • Extension check  │
   │ • libmagic MIME    │
   │ • 5 MB size cap    │
   │ • 15 req/min/IP    │
   └────┬───────────────┘
        │
        ▼
file_processor.py → pandas aggregates metrics
        │
        ▼
ai_service.py → Groq Llama 3.3 70B → narrative summary
        │
        ▼
JSON response + job_id cached in memory
        │
        ▼
GET /api/v1/analyze/pdf/{job_id}
        │
        ▼
pdf_service.py → ReportLab → PDF download
```

---

## How Endpoints Are Secured

| Threat | Defence |
|---|---|
| Malicious file upload | Extension allowlist + libmagic checks **actual bytes**, not just filename |
| File bombs / huge files | Hard 5 MB cap enforced before pandas touches the data |
| API abuse / DDoS | `slowapi` rate limiter — 15 requests/minute per IP |
| Prompt injection via CSV | Only **computed metrics** (aggregates) are sent to the LLM — raw row data never reaches the prompt |
| Exposed API keys | Environment variables only, never committed; `.env` in `.gitignore` |
| Cross-origin abuse | CORS restricted to explicit allowed origins via `ALLOWED_ORIGINS` env var |
| Oversized AI output | `max_tokens=350` cap on Groq response |

---

## Environment Variables

See `.env.example`:

```
GROQ_API_KEY=           # Required — get free key at console.groq.com
ALLOWED_ORIGINS=        # Comma-separated allowed CORS origins
MAX_FILE_SIZE_MB=5      # Optional, default 5
RATE_LIMIT_PER_MINUTE=15  # Optional, default 15
```

---

## Reference Data

`sales_q1_2026.csv` — included in the repo root for testing:

```
Date,Product_Category,Region,Units_Sold,Unit_Price,Revenue,Status
2026-01-05,Electronics,North,150,1200,180000,Shipped
...
```

---

## Tech Stack

- **FastAPI** — async Python web framework with auto-generated OpenAPI
- **Groq** — Llama 3.3 70B Versatile, free tier, < 2s response
- **pandas + openpyxl** — CSV/XLSX parsing
- **ReportLab** — in-memory PDF generation
- **python-magic** — libmagic MIME detection
- **slowapi** — rate limiting
- **Docker** — multi-stage build, non-root user, ~120 MB image
- **Render** — zero-config Python deployment
