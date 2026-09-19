import httpx
import time

def main():
    client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=30)
    auth_res = client.post("/api/v1/auth/login", json={"email": "demo@docintel.com", "password": "DemoPassword123!"})
    token = auth_res.json()["access_token"]

    with open("sample_documents/02_scanned_exam.png", "rb") as f:
        img_bytes = f.read()

    upload_res = client.post(
        "/api/v1/documents/upload",
        headers={"Authorization": f"Bearer {token}"},
        files={"file": ("02_scanned_exam.png", img_bytes, "image/png")}
    )
    doc_id = upload_res.json()["document_id"]
    print("Uploaded document ID:", doc_id)

    for i in range(25):
        time.sleep(1)
        st = client.get(f"/api/v1/documents/{doc_id}/status", headers={"Authorization": f"Bearer {token}"}).json()
        print(f"Status [{i}s]: {st.get('status')} - progress: {st.get('progress')}%")
        if st.get("status") == "COMPLETED":
            break

    q_res = client.get(f"/api/v1/documents/{doc_id}/questions", headers={"Authorization": f"Bearer {token}"}).json()
    items = q_res.get("items", [])
    print(f"\n--- SUCCESS: {len(items)} REAL QUESTIONS EXTRACTED ---")
    for q in items:
        print(f"Question {q.get('question_number')}: {q.get('question_text')}")
        for o in q.get("options", []):
            print(f"   [{o.get('option_key')}] {o.get('option_text')}")
        ans = q.get("answer")
        if ans:
            print(f"   => Answer: {ans.get('answer_text')} (Match: {ans.get('match_type')})")

if __name__ == "__main__":
    main()
