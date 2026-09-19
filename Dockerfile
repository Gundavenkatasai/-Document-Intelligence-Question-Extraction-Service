# Multi-stage Dockerfile for Document Intelligence Service
FROM python:3.11-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


FROM python:3.11-slim AS final

WORKDIR /app

# Install runtime system dependencies: Tesseract OCR, OpenCV runtime libs, Poppler utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    tesseract-ocr-eng \
    libgl1 \
    libglib2.0-0 \
    poppler-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy installed Python packages from builder
COPY --from=builder /install /usr/local

# Copy application source code
COPY app/ ./app/
COPY alembic/ ./alembic/
COPY alembic.ini .
COPY sample_documents/ ./sample_documents/

# Create non-root user and persistent storage directory
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/data/storage && \
    chown -R appuser:appuser /app

USER appuser

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    STORAGE_PATH=/app/data/storage

EXPOSE 8000

# Default command starts FastAPI application via Uvicorn
# PORT is injected by Railway/Render at runtime; fallback to 8000 locally
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}
