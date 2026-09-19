import uuid
import pytest
from httpx import AsyncClient
from app.db.models.user import User


@pytest.mark.asyncio
async def test_user_registration_and_login(client: AsyncClient):
    # 1. Register new user
    reg_payload = {
        "email": "new_student@example.com",
        "password": "Password123!",
        "full_name": "New Student"
    }
    res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == "new_student@example.com"
    assert "id" in data

    # 2. Duplicate registration rejected
    res_dup = await client.post("/api/v1/auth/register", json=reg_payload)
    assert res_dup.status_code == 400

    # 3. Login with JSON
    login_res = await client.post("/api/v1/auth/login", json={
        "email": "new_student@example.com",
        "password": "Password123!"
    })
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

    # 4. Access /me endpoint
    me_res = await client.get("/api/v1/auth/me", headers={
        "Authorization": f"Bearer {token_data['access_token']}"
    })
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "new_student@example.com"


@pytest.mark.asyncio
async def test_unauthorized_access(client: AsyncClient):
    # Upload without token should be 401
    res = await client.post("/api/v1/documents/upload")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_upload_valid_pdf_and_status(client: AsyncClient, auth_headers: dict):
    with open("sample_documents/01_digital_exam.pdf", "rb") as f:
        pdf_bytes = f.read()

    res = await client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={"file": ("01_digital_exam.pdf", pdf_bytes, "application/pdf")}
    )
    assert res.status_code == 202
    data = res.json()
    assert "document_id" in data
    assert data["status"] == "PENDING"
    assert "asynchronous" in data["message"]

    doc_id = data["document_id"]

    # Check status endpoint
    status_res = await client.get(f"/api/v1/documents/{doc_id}/status", headers=auth_headers)
    assert status_res.status_code == 200
    s_data = status_res.json()
    assert s_data["document_id"] == doc_id
    assert "progress" in s_data


@pytest.mark.asyncio
async def test_upload_valid_image(client: AsyncClient, auth_headers: dict):
    with open("sample_documents/02_scanned_exam.png", "rb") as f:
        img_bytes = f.read()

    res = await client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={"file": ("02_scanned_exam.png", img_bytes, "image/png")}
    )
    assert res.status_code == 202
    data = res.json()
    assert "document_id" in data


@pytest.mark.asyncio
async def test_reject_unsupported_file(client: AsyncClient, auth_headers: dict):
    res = await client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={"file": ("malicious.exe", b"MZ_EXE_BINARY_CODE", "application/x-msdownload")}
    )
    assert res.status_code == 400
    assert "Unsupported file extension" in res.json()["detail"]


@pytest.mark.asyncio
async def test_reject_corrupted_file(client: AsyncClient, auth_headers: dict):
    with open("sample_documents/07_corrupted.pdf", "rb") as f:
        bad_bytes = f.read()

    res = await client.post(
        "/api/v1/documents/upload",
        headers=auth_headers,
        files={"file": ("07_corrupted.pdf", bad_bytes, "application/pdf")}
    )
    assert res.status_code == 400
    assert "magic signatures" in res.json()["detail"] or "Malformed" in res.json()["detail"]


@pytest.mark.asyncio
async def test_group_creation_and_isolation(client: AsyncClient, auth_headers: dict):
    # Create group
    group_res = await client.post(
        "/api/v1/groups",
        headers=auth_headers,
        json={"name": "Mathematics Exam 2026", "description": "Paper and key group"}
    )
    assert group_res.status_code == 201
    group_data = group_res.json()
    group_id = group_data["id"]

    # Get group details
    get_res = await client.get(f"/api/v1/groups/{group_id}", headers=auth_headers)
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Mathematics Exam 2026"
