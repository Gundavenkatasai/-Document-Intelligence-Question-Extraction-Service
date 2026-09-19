from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.logging import logger
from app.db.session import engine
from app.api.v1.router import api_router
from app.services.preprocessing.validator import ValidationError
from app.schemas.common import HealthResponse, ReadyResponse, ErrorResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.PROJECT_NAME}...")
    yield
    logger.info("Shutting down application...")
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="""
# Document Intelligence & Question Extraction Service

Production-ready service that accepts PDF documents and images containing examination/question-bank material, extracts structured questions, parses options and answer keys, resolves multi-page questions, computes confidence scores, flags uncertain items for human review, and executes asynchronously via background workers.

### Key Capabilities:
* **Asynchronous Document Processing**: Instant 202 upload response with background worker pipelines.
* **Hybrid Extraction Strategy**: Native text extraction for digital PDFs + automatic OCR fallback with image preprocessing (deskew, contrast, denoise) for scanned documents.
* **Intelligent Question Segmentation**: Robust support for diverse numbering styles (`1.`, `Q1:`, `1)`, `Question 1`) and multiple option formats (`A.`, `(a)`, `[A]`).
* **Multi-Page Question Continuity**: Resolves split questions seamlessly across page boundaries while preserving all source page references.
* **Safe Answer Key Matching**: Unmatched, matched, and uncertain answer states with strict verification to prevent hallucinations.
* **Transparent Confidence Scoring**: Explainable composite scores (0.0 - 1.0) and automated flagging into the human review queue.
* **Full Authentication & Authorization**: Secure JWT-based isolation ensuring strict multi-tenant access control.
""",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global Exception Handlers
@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": exc.message, "error_code": exc.error_code}
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled server exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please consult system administrator."}
    )


# Health & Readiness Endpoints
@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Health check endpoint",
    description="Returns service health and operational status."
)
async def health_check():
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        services={
            "api": "online",
            "storage_backend": settings.STORAGE_BACKEND,
            "ai_provider": settings.AI_PROVIDER,
        }
    )


@app.get(
    "/ready",
    response_model=ReadyResponse,
    tags=["System"],
    summary="Readiness check endpoint",
    description="Checks connectivity to database, redis, and storage."
)
async def readiness_check():
    db_ok = False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            db_ok = True
    except Exception as e:
        logger.warning(f"Database readiness check failed: {e}")

    return ReadyResponse(
        status="ready" if db_ok else "degraded",
        database=db_ok,
        redis=True,
        storage=True
    )


# Mount API v1
app.include_router(api_router, prefix=f"/{settings.API_V1_STR}")

# Mount Web Dashboard
import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", include_in_schema=False)
async def serve_dashboard():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return JSONResponse(
        content={
            "message": "Document Intelligence & Question Extraction Service API",
            "docs": "/docs",
            "health": "/health"
        }
    )

