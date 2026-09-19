# Document Intelligence & Question Extraction - API Reference

Base URL: `http://localhost:8000`  
Interactive Swagger UI: `http://localhost:8000/docs`  
ReDoc Documentation: `http://localhost:8000/redoc`

---

## 1. Authentication Endpoints

### Register User
* **Endpoint**: `POST /api/v1/auth/register`
* **Status**: `201 Created`
* **Request**:
```json
{
  "email": "examiner@example.com",
  "password": "SecurePassword123!",
  "full_name": "Chief Examiner"
}
```
* **Response**:
```json
{
  "id": "e4b2d35e-63f2-45e3-b541-2c9e831671af",
  "email": "examiner@example.com",
  "full_name": "Chief Examiner",
  "is_active": true
}
```

### Login (Obtain JWT Token)
* **Endpoint**: `POST /api/v1/auth/login`
* **Status**: `200 OK`
* **Request**:
```json
{
  "email": "examiner@example.com",
  "password": "SecurePassword123!"
}
```
* **Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "user_id": "e4b2d35e-63f2-45e3-b541-2c9e831671af",
  "email": "examiner@example.com"
}
```

### Current User Profile
* **Endpoint**: `GET /api/v1/auth/me`
* **Headers**: `Authorization: Bearer <token>`
* **Status**: `200 OK`

---

## 2. Document Groups

### Create Document Group
* **Endpoint**: `POST /api/v1/groups`
* **Headers**: `Authorization: Bearer <token>`
* **Status**: `201 Created`
* **Request**:
```json
{
  "name": "Senior Secondary Science Examination 2026",
  "description": "Question Paper and Answer Key group"
}
```

### Get Document Group Details
* **Endpoint**: `GET /api/v1/groups/{group_id}`
* **Headers**: `Authorization: Bearer <token>`
* **Status**: `200 OK`
* **Response**:
```json
{
  "id": "7b79a528-63bb-4034-8c88-e9f3b50c0529",
  "user_id": "e4b2d35e-63f2-45e3-b541-2c9e831671af",
  "name": "Senior Secondary Science Examination 2026",
  "description": "Question Paper and Answer Key group",
  "created_at": "2026-09-19T22:30:00Z",
  "updated_at": "2026-09-19T22:30:00Z",
  "documents": [
    {
      "id": "19134d71-dbf9-4d3d-abab-c68761d8cf44",
      "filename": "05_question_paper.pdf",
      "file_type": "PDF",
      "status": "COMPLETED",
      "created_at": "2026-09-19T22:31:00Z"
    }
  ]
}
```

---

## 3. Documents & Upload

### Upload Document
* **Endpoint**: `POST /api/v1/documents/upload`
* **Headers**: `Authorization: Bearer <token>`
* **Content-Type**: `multipart/form-data`
* **Parameters**:
  - `file`: Binary file (PDF, PNG, JPG, JPEG, max 50MB)
  - `group_id` *(optional)*: UUID of document group
* **Status**: `202 Accepted`
* **Response**:
```json
{
  "document_id": "19134d71-dbf9-4d3d-abab-c68761d8cf44",
  "status": "PENDING",
  "message": "Document accepted for asynchronous processing"
}
```

### Document Status & Progress
* **Endpoint**: `GET /api/v1/documents/{document_id}/status`
* **Headers**: `Authorization: Bearer <token>`
* **Status**: `200 OK`
* **Response**:
```json
{
  "document_id": "19134d71-dbf9-4d3d-abab-c68761d8cf44",
  "status": "COMPLETED",
  "progress": 100,
  "total_pages": 2,
  "processed_pages": 2,
  "questions_extracted": 5,
  "warnings": 1,
  "error_message": null
}
```

---

## 4. Questions & Answers

### List Document Questions
* **Endpoint**: `GET /api/v1/documents/{document_id}/questions`
* **Headers**: `Authorization: Bearer <token>`
* **Query Parameters**:
  - `question_type`: Filter by type (`MULTIPLE_CHOICE`, `TRUE_FALSE`, `SHORT_ANSWER`, `DESCRIPTIVE`, `UNKNOWN`)
  - `review_status`: Filter by status (`ACCEPTED`, `PENDING_REVIEW`, `REJECTED`)
  - `page`: Page number (default `1`)
  - `page_size`: Items per page (default `20`)
* **Status**: `200 OK`
* **Response**:
```json
{
  "items": [
    {
      "id": "a5d09f7a-b51c-43f9-a2e1-456cb310a012",
      "document_id": "19134d71-dbf9-4d3d-abab-c68761d8cf44",
      "question_number": "1",
      "question_text": "What is the primary function of mitochondria in eukaryotic cells?",
      "question_type": "MULTIPLE_CHOICE",
      "options": [
        { "id": "uuid-1", "option_key": "A", "option_text": "Photosynthesis", "is_correct": false },
        { "id": "uuid-2", "option_key": "B", "option_text": "ATP energy production", "is_correct": true },
        { "id": "uuid-3", "option_key": "C", "option_text": "Protein packaging", "is_correct": false },
        { "id": "uuid-4", "option_key": "D", "option_text": "Lipid synthesis", "is_correct": false }
      ],
      "answer": {
        "id": "uuid-ans",
        "source_document_id": "19134d71-dbf9-4d3d-abab-c68761d8cf44",
        "answer_text": "B",
        "answer_key_reference": "Answer: B",
        "match_type": "matched",
        "confidence_score": 0.95,
        "explanation": "Detected inline answer in question text: Answer: B"
      },
      "source_pages": [1],
      "confidence_score": 0.95,
      "review_status": "ACCEPTED",
      "has_visual_content": false,
      "visual_metadata": { "has_visual": false },
      "raw_metadata": {},
      "warnings": [],
      "created_at": "2026-09-19T22:35:00Z",
      "updated_at": "2026-09-19T22:35:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "page_size": 20
}
```

### Get Single Question
* **Endpoint**: `GET /api/v1/questions/{question_id}`
* **Headers**: `Authorization: Bearer <token>`
* **Status**: `200 OK`

### Document Answer Key Summary
* **Endpoint**: `GET /api/v1/documents/{document_id}/answer-key`
* **Headers**: `Authorization: Bearer <token>`
* **Status**: `200 OK`
* **Response**:
```json
{
  "document_id": "19134d71-dbf9-4d3d-abab-c68761d8cf44",
  "total_questions": 3,
  "matched_count": 3,
  "unmatched_count": 0,
  "uncertain_count": 0,
  "not_available_count": 0,
  "answers": [
    {
      "question_id": "a5d09f7a-b51c-43f9-a2e1-456cb310a012",
      "question_number": "1",
      "matched_answer": "B",
      "reference": "Answer: B",
      "match_type": "matched",
      "confidence_score": 0.95,
      "source_document_id": "19134d71-dbf9-4d3d-abab-c68761d8cf44",
      "explanation": "Detected inline answer in question text: Answer: B"
    }
  ]
}
```

---

## 5. Review Queue & Resolution

### Get Flagged Review Items
* **Endpoint**: `GET /api/v1/reviews/flagged`
* **Headers**: `Authorization: Bearer <token>`
* **Query Parameters**:
  - `status`: `PENDING`, `RESOLVED`, `DISMISSED`
  - `confidence_max`: Float threshold (e.g. `0.75`)
  - `page`: Page number
  - `page_size`: Items per page
* **Status**: `200 OK`

### Resolve Review Item
* **Endpoint**: `POST /api/v1/reviews/{review_id}/resolve`
* **Headers**: `Authorization: Bearer <token>`
* **Request**:
```json
{
  "status": "RESOLVED",
  "notes": "Verified by examiner committee."
}
```
* **Status**: `200 OK`

---

## 6. System Health & Readiness

### Health Check
* **Endpoint**: `GET /health`
* **Status**: `200 OK`
* **Response**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "api": "online",
    "storage_backend": "local",
    "ai_provider": "mock"
  }
}
```

### Readiness Check
* **Endpoint**: `GET /ready`
* **Status**: `200 OK`
* **Response**:
```json
{
  "status": "ready",
  "database": true,
  "redis": true,
  "storage": true
}
```
