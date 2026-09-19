# Architectural Decision Records (ADR)

## ADR 001: Asynchronous Non-Blocking Processing via Celery & Redis

### Context
Documents can range from single-page images to 50+ page PDFs with high-resolution scans. Synchronous processing within FastAPI HTTP request handlers would tie up worker threads, cause client timeouts, and degrade throughput.

### Decision
Implement an asynchronous worker queue using Celery backed by Redis. When a document is uploaded, the API performs structural validation, saves the raw file, creates a database record in `PENDING` state, enqueues a background task, and returns `HTTP 202 Accepted` immediately.

### Consequences
- **Pros**: Sub-second client response times, independent scalability of API and processing workers, fault tolerance, retry backoff on external failures.
- **Cons**: Requires running Redis and Celery worker processes alongside the API (mitigated by Docker Compose and an in-process eager fallback for local development).

---

## ADR 002: Layered Extraction Strategy (Native Text First, OCR Fallback)

### Context
Documents submitted to the service include both digitally generated PDFs (with embedded text streams) and scanned documents/raster images. Blindly running OCR on all documents is computationally expensive, slow, and prone to OCR recognition errors on clean digital text.

### Decision
Implement a layered extraction strategy:
1. Inspect page character density via PyMuPDF (`fitz`).
2. If text count $\ge 40$ characters, extract native text directly (`extraction_method = 'native_text'`).
3. If text count $< 40$ characters, trigger OpenCV preprocessing (deskew, contrast enhancement, noise reduction) and OCR fallback via Tesseract (`extraction_method = 'ocr'`).
4. Record extraction provenance at the individual page level.

### Consequences
- **Pros**: Up to 10x faster processing for digital PDFs, 100% character accuracy on native text, fallback resiliency on scanned and camera-captured documents.
- **Cons**: Requires maintaining two extraction pathways in the pipeline.

---

## ADR 003: Multi-Page Question Continuity Resolution

### Context
Exam questions frequently break across page boundaries (e.g. Question stem and options A/B on Page 4, options C/D and answer on Page 5). Naive page-by-page extraction would produce truncated questions or orphan option fragments.

### Decision
Implement `MultipageResolver` which analyzes adjacent page boundaries. When a question at the end of Page $N$ has incomplete options or incomplete sentence structure and the subsequent Page $N+1$ begins with orphan options or continuation text, the resolver merges them into a single question entity and records all involved pages in `source_pages: [N, N+1]`.

### Consequences
- **Pros**: Accurately handles real-world multi-page exams, preserves complete question structure and option sets.
- **Cons**: Requires sequence-aware processing across page boundaries.

---

## ADR 004: Non-Hallucinatory Answer Matching Safety Model

### Context
In automated examination analysis, returning an incorrect hallucinated answer can compromise grading integrity. Answer keys can be found inside the document, at the end, or in a separate document within a document group.

### Decision
Enforce a four-state answer classification:
1. `matched`: Verified match against question text or answer key table, verified against available MCQ options.
2. `uncertain`: Answer indicated in key, but does not match question options (e.g. key says 'E', options are A-D). Marked with `needs_review: true`.
3. `unmatched`: Question number is not present in answer key.
4. `not_available`: No answer key provided.

### Consequences
- **Pros**: Prevents hallucinated answers; clearly informs reviewers when human intervention is needed.

---

## ADR 005: Transparent, Explainable Confidence Scoring & Review Queue

### Context
Users and human examiners require an explainable metric to gauge extraction reliability, rather than an arbitrary opaque percentage.

### Decision
Compute a transparent composite score starting from a baseline (1.0 for native text, OCR average word confidence for scans) and applying quantifiable deductions for missing numbers ($-0.20$), short text ($-0.25$), incomplete options ($-0.30$), multi-page ambiguity ($-0.15$), and answer mismatches ($-0.15$). Scores below $0.75$ or with critical warnings automatically populate the `ReviewItem` table for human verification.

### Consequences
- **Pros**: Auditability, transparent explanation for every flagged item, easy threshold tuning via environment variables.
