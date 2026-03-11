from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from contextlib import asynccontextmanager
import os

from routes.analyze import router as analyze_router

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    yield
    # shutdown


app = FastAPI(
    title="Sales Insight Automator API",
    description=(
        "Upload CSV/XLSX sales data and receive an AI-generated executive "
        "summary as a downloadable PDF. Powered by Groq (Llama 3.3 70B)."
    ),
    version="1.0.0",
    contact={
        "name": "Rabbitt AI Engineering",
        "url": "https://github.com/hardik3739",
    },
    license_info={"name": "MIT"},
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

allowed_origins_raw = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,https://sales-insight-frontend.vercel.app",
)
allowed_origins = [o.strip() for o in allowed_origins_raw.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(analyze_router, prefix="/api/v1", tags=["Analysis"])


@app.get("/health", tags=["Health"])
async def health_check():
    """Liveness probe used by Render and monitoring tools."""
    return {"status": "ok", "version": "1.0.0"}
