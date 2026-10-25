"""Tests for server auth and CV history endpoints."""
import json
import threading
import urllib.request
import urllib.error
import pytest

from src.app.server import BoundedHTTPServer, Handler, WORKER
from src.app.security import SecuritySettings
from src.app.db import Database


@pytest.fixture
def test_server(tmp_path, monkeypatch):
    db_file = tmp_path / "test_auth.db"
    monkeypatch.setenv("ATS_DB_PATH", str(db_file))
    # Reset global db instance
    import src.app.db as db_mod
    db_mod._DB_INSTANCE = Database(db_path=db_file)

    settings = SecuritySettings(mode="local", allowed_hosts=("127.0.0.1", "localhost"))
    server = BoundedHTTPServer(("127.0.0.1", 0), Handler, settings)
    port = server.server_port

    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    base_url = f"http://127.0.0.1:{port}"
    yield base_url

    server.shutdown()
    server.server_close()


def make_request(url, method="GET", data=None, headers=None):
    hdrs = headers or {}
    encoded = json.dumps(data).encode("utf-8") if data is not None else None
    if encoded is not None and "Content-Type" not in hdrs:
        hdrs["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=encoded, headers=hdrs, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            cookie = res.headers.get("Set-Cookie")
            body = json.loads(res.read().decode("utf-8"))
            return res.status, body, cookie
    except urllib.error.HTTPError as exc:
        body = json.loads(exc.read().decode("utf-8")) if exc.headers.get("Content-Type", "").startswith("application/json") else {}
        return exc.code, body, None


def test_auth_and_history_flow(test_server):
    # 1. Initially unauthenticated
    status, body, _ = make_request(f"{test_server}/api/auth/me")
    assert status == 200
    assert body["authenticated"] is False

    # 2. History requires auth
    status, body, _ = make_request(f"{test_server}/api/history")
    assert status == 401

    # 3. Signup
    status, body, cookie = make_request(
        f"{test_server}/api/auth/signup",
        method="POST",
        data={"username": "test_pilot", "email": "pilot@example.com", "password": "SecurePassword123!"}
    )
    assert status == 201
    assert body["ok"] is True
    assert body["user"]["username"] == "test_pilot"
    assert "ats_session=" in cookie
    token = body["token"]

    # 4. Auth me with cookie
    status, body, _ = make_request(
        f"{test_server}/api/auth/me",
        headers={"Cookie": f"ats_session={token}"}
    )
    assert status == 200
    assert body["authenticated"] is True
    assert body["user"]["username"] == "test_pilot"
    assert body["user"]["cv_count"] == 0

    # 5. History initially empty
    status, body, _ = make_request(
        f"{test_server}/api/history",
        headers={"Cookie": f"ats_session={token}"}
    )
    assert status == 200
    assert body["submissions"] == []

    # 6. Logout
    status, body, clear_cookie = make_request(
        f"{test_server}/api/auth/logout",
        method="POST",
        headers={"Cookie": f"ats_session={token}"}
    )
    assert status == 200
    assert "Max-Age=0" in clear_cookie

    # 7. Check after logout
    status, body, _ = make_request(
        f"{test_server}/api/auth/me",
        headers={"Cookie": f"ats_session={token}"}
    )
    assert status == 200
    assert body["authenticated"] is False

    # 8. Login with username
    status, body, login_cookie = make_request(
        f"{test_server}/api/auth/login",
        method="POST",
        data={"username_or_email": "test_pilot", "password": "SecurePassword123!"}
    )
    assert status == 200
    assert body["ok"] is True
    new_token = body["token"]

    # 9. Login with email
    status, body, _ = make_request(
        f"{test_server}/api/auth/login",
        method="POST",
        data={"username_or_email": "pilot@example.com", "password": "SecurePassword123!"}
    )
    assert status == 200
    assert body["ok"] is True


def test_submission_history_saved_when_logged_in(test_server, monkeypatch):
    # Mock WORKER.run to avoid loading ML weights during unit test
    monkeypatch.setattr(
        WORKER,
        "run",
        lambda payload: {
            "schema_version": "2.0",
            "decision": "review_recommended",
            "combined_score": 0.88,
            "score_kind": "model_score",
            "findings": [{"id": 1, "category": "keyword_stuffing"}],
            "status": "complete",
            "input_mode": "text",
            "analysis_id": "test-123",
            "created_at": "2026-10-23T00:00:00Z",
            "policy_version": "2.1",
        }
    )

    # 1. Signup a user
    status, body, _ = make_request(
        f"{test_server}/api/auth/signup",
        method="POST",
        data={"username": "cv_uploader", "email": "uploader@example.com", "password": "Password123!"}
    )
    assert status == 201
    token = body["token"]

    # 2. Run analysis while authenticated
    status, body, _ = make_request(
        f"{test_server}/analyze",
        method="POST",
        data={"text": "Software Engineer with 5 years experience in Python and SQL."},
        headers={"Cookie": f"ats_session={token}"}
    )
    assert status == 200
    assert body["decision"] == "review_recommended"
    assert "saved_submission_id" in body
    submission_id = body["saved_submission_id"]

    # 3. Check history contains this submission
    status, body, _ = make_request(
        f"{test_server}/api/history",
        headers={"Cookie": f"ats_session={token}"}
    )
    assert status == 200
    assert len(body["submissions"]) == 1
    sub = body["submissions"][0]
    assert sub["id"] == submission_id
    assert sub["decision"] == "review_recommended"
    assert sub["findings_count"] == 1
    assert "Software Engineer" in sub["document_name"]

    # 4. Fetch detail of submission
    status, body, _ = make_request(
        f"{test_server}/api/history/{submission_id}",
        headers={"Cookie": f"ats_session={token}"}
    )
    assert status == 200
    detail = body["submission"]
    assert detail["id"] == submission_id
    assert detail["result"]["decision"] == "review_recommended"
    assert detail["result"]["combined_score"] == 0.88

    # 5. Delete submission
    status, body, _ = make_request(
        f"{test_server}/api/history/{submission_id}",
        method="DELETE",
        headers={"Cookie": f"ats_session={token}"}
    )
    assert status == 200
    assert body["ok"] is True

    # 6. Check history is now empty
    status, body, _ = make_request(
        f"{test_server}/api/history",
        headers={"Cookie": f"ats_session={token}"}
    )
    assert status == 200
    assert len(body["submissions"]) == 0
