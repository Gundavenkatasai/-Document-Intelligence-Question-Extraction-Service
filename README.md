# Document Intelligence & Question Extraction Service

Production-oriented, asynchronous service for ingesting examination documents and question banks (digital PDFs, scanned PDFs, PNG, JPG, JPEG), extracting structured questions, identifying question types, parsing diverse option formats, resolving questions across page boundaries, associating answer keys, computing transparent confidence metrics, and flagging uncertain items for human review.

---

## 1. System Architecture

```text
               CLIENT (Postman / Browser / App)
                            │
                            ▼
               ┌─────────────────────────┐
               │    FastAPI REST API     │
               │ (JWT Auth, Pydantic v2) │
               └────────────┬────────────┘
                            │
                 ┌──────────┴──────────┐
                 ▼                     ▼
          PostgreSQL 16          Storage Service
         (Asyncpg/SQLAlchemy)    (Local Disk / S3)
                 │
                 ▼
          Redis Task Queue
                 │
                 ▼
       Celery Background Worker
                 │
                 ▼
 ┌──────────────────────────────────────────────┐
 │         Document Processing Pipeline         │
 │                                              │
 │ 1. File & Magic Signature Validation         │
 │ 2. Page Rendering (PyMuPDF / Poppler)        │
 │ 3. Native Text Extraction                    │
 │ 4. OCR Fallback & Preprocessing (OpenCV)     │
 │ 5. Question & Option Parsing (Multimodal AI) │
 │ 6. Multi-Page Continuation Resolution        │
 │ 7. Cross-Document Answer Key Matching        │
 │ 8. Transparent Confidence Scoring            │
 │ 9. Automated Human Review Flagging           │
 └──────────────────────┬───────────────────────┘
                        │
                        ▼
                   PostgreSQL
```

---

## 2. Prerequisites

* **Python**: 3.11 or higher
* **Docker & Docker Compose** (for containerized deployment)
* **PostgreSQL 16+** & **Redis 7+** (if running natively without Docker)
* **Tesseract OCR** (optional for scanned image processing, automatically bundled in Docker)

---

## 3. Quick Start with Docker Compose (Recommended)

The simplest and most reliable way to spin up the entire cluster (API, Celery worker, PostgreSQL, Redis, and persistent volumes):

```bash
# 1. Clone the repository and navigate to root
cd task

# 2. Copy the environment configuration
cp .env.example .env

# 3. Build and launch all services
docker compose up -d --build

# 4. Verify running containers
docker compose ps
```

The services will be available at:
* **API & Swagger Documentation**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **ReDoc Interactive Reference**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
* **Health Check Endpoint**: [http://localhost:8000/health](http://localhost:8000/health)
* **Readiness Check Endpoint**: [http://localhost:8000/ready](http://localhost:8000/ready)

---

## 4. Local Development Setup (Native Python)

### Step 1: Create and Activate Virtual Environment
```bash
# Using python venv or uv:
uv venv --python 3.11 .venv

# On Windows:
.venv\Scripts\activate

# On Linux / macOS:
source .venv/bin/activate
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

### Step 3: Run Database Migrations
```bash
alembic upgrade head
```

### Step 4: Start the API Server
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 5. Interactive Web Application Dashboard

The service includes an interactive Web Dashboard accessible directly in your browser:

* **URL**: [http://localhost:8000/](http://localhost:8000/)
* **Interactive Features**:
  * **One-Click Benchmark Runners**: Instantly test digital PDFs, scanned papers, rotated/deskewed documents, multi-page split questions, cross-document answer keys, and ambiguous review queue test cases.
  * **Drag & Drop Upload**: Upload any custom PDF or image with real-time pipeline progress tracking.
  * **Extracted Questions Explorer**: Visual cards with Question Number, Type, Options, Matched Answer Keys, and Source Pages.
  * **Answer Keys & Matching Table**: Displays matched, unmatched, and uncertain states with confidence scores.
  * **Flagged Human Review Queue**: Filter by warning code, inspect reasons, and resolve flagged questions.
  * **Structured JSON Viewer**: Live copyable JSON payload matching the REST API schema.
* **Interactive OpenAPI Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **ReDoc Documentation**: [http://localhost:8000/redoc](http://localhost:8000/redoc)
* **Health Endpoint**: [http://localhost:8000/health](http://localhost:8000/health)

---

## 6. Running Automated Tests

The repository includes a comprehensive `pytest` test suite with 80%+ code coverage across API routes, asynchronous pipeline stages, multi-page question continuity, answer matching, and review queues.

```bash
# Run all tests with verbose output
pytest -v

# Run with test coverage report
pytest --cov=app --cov-report=term-missing
```

---

## 6. End-to-End Demonstration Workflow

### Step 1: Register User and Obtain JWT Token
```bash
# Register
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "examiner@example.com", "password": "SecurePassword123!", "full_name": "Dr. Smith"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "examiner@example.com", "password": "SecurePassword123!"}'
# Save the returned "access_token" to $TOKEN
```

### Step 2: Create a Document Group
```bash
curl -X POST http://localhost:8000/api/v1/groups \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Senior Physics Exam 2026", "description": "Exam Paper and Answer Key Set"}'
# Save the returned "id" to $GROUP_ID
```

### Step 3: Upload an Examination Document (Asynchronous)
```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@sample_documents/01_digital_exam.pdf" \
  -F "group_id=$GROUP_ID"
# Expected response: 202 Accepted
# {"document_id": "...", "status": "PENDING", "message": "Document accepted for asynchronous processing"}
```

### Step 4: Monitor Document Processing Status
```bash
curl -X GET http://localhost:8000/api/v1/documents/$DOCUMENT_ID/status \
  -H "Authorization: Bearer $TOKEN"
# {"document_id": "...", "status": "COMPLETED", "progress": 100, "total_pages": 1, "questions_extracted": 3}
```

### Step 5: Retrieve Structured Question Data
```bash
curl -X GET "http://localhost:8000/api/v1/documents/$DOCUMENT_ID/questions?page=1&page_size=20" \
  -H "Authorization: Bearer $TOKEN"
```

### Step 6: Query Matched Answer Keys
```bash
curl -X GET http://localhost:8000/api/v1/documents/$DOCUMENT_ID/answer-key \
  -H "Authorization: Bearer $TOKEN"
```

### Step 7: Inspect Flagged Human Review Items
```bash
curl -X GET "http://localhost:8000/api/v1/reviews/flagged?page=1&page_size=20" \
  -H "Authorization: Bearer $TOKEN"
```

### Step 8: Resolve a Review Item
```bash
curl -X POST http://localhost:8000/api/v1/reviews/$REVIEW_ID/resolve \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "RESOLVED", "notes": "Verified by examination committee."}'
```

---

## 7. Sample Test Documents

The repository contains pre-generated sample documents in `sample_documents/` covering all mandated test scenarios:

| File | Scenario Tested |
| :--- | :--- |
| `01_digital_exam.pdf` | Clean digital exam with multiple choice, True/False, and embedded answers. |
| `02_scanned_exam.png` | Scanned raster image processed through OCR and image enhancement. |
| `03_rotated_exam.png` | Skewed image testing OpenCV rotation and deskewing algorithms. |
| `04_multipage_exam.pdf` | Question 17 begins on Page 1 and continues on Page 2 (`source_pages: [1, 2]`). |
| `05_question_paper.pdf` | Question paper matched against separate answer key in a document group. |
| `05_answer_key.pdf` | Separate official answer key table matched with sibling document. |
| `06_ambiguous_exam.pdf` | Low-confidence question with missing numbers and options flagged for review. |
| `07_corrupted.pdf` | Malformed file verifying HTTP 400 rejection and security validation. |

You can regenerate these samples at any time using:
```bash
python sample_documents/generate_samples.py
```

---

## 8. Postman Collection

Ready-to-import Postman files are located in `postman/`:
* `postman/Document_Intelligence_Collection.postman_collection.json`: Complete workflow collection with auto-token test scripts.
* `postman/Document_Intelligence_Environment.postman_environment.json`: Pre-configured environment containing `base_url`, `token`, `document_id`, `question_id`, and `group_id`.

---

## 9. Environment Variables Reference

| Variable | Default | Description |
| :--- | :--- | :--- |
| `DATABASE_URL` | `postgresql+asyncpg://...` | Asynchronous database connection string. |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis broker and backend URL for Celery. |
| `STORAGE_BACKEND` | `local` | Object storage mode (`local` or `s3`). |
| `STORAGE_PATH` | `./data/storage` | Directory path for local document storage. |
| `MAX_UPLOAD_SIZE_MB` | `50` | Maximum file upload size limit in Megabytes. |
| `CONFIDENCE_REVIEW_THRESHOLD` | `0.75` | Questions with confidence below this threshold are flagged for review. |
| `AI_PROVIDER` | `mock` | Document understanding AI (`mock`, `gemini`, or `openai`). |
| `AI_API_KEY` | None | API key for Gemini or OpenAI (optional). |
| `SECRET_KEY` | Required | Cryptographic secret for signing JWT access tokens. |
| `CELERY_TASK_ALWAYS_EAGER` | `false` | When true, executes Celery tasks inline synchronously (useful for local test runner). |

---

## 10. Troubleshooting

* **File Upload 400 Bad Request**: Verify that the file format is PDF, PNG, JPG, or JPEG and does not exceed 50MB. Malformed or 0-byte files are rejected automatically.
* **Database Connection Errors**: Verify PostgreSQL is running and migrations have been applied via `alembic upgrade head`.
* **Worker Job Not Processing**: Check that Redis is running on port 6379 and the Celery worker process is active.
* **OCR Quality on Imperfect Scans**: Ensure `Tesseract OCR` is installed and the language data packs (`tesseract-ocr-eng`) are present on your system or run via Docker Compose.
