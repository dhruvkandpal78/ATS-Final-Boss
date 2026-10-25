"""Tests for database storage, user authentication, and submission history."""
import json
import pytest

from src.app.db import Database


@pytest.fixture
def db():
    return Database(db_path=":memory:")


def test_user_registration_and_auth(db):
    user = db.register_user("alice_dev", "alice@example.com", "SecretPass123!")
    assert user["id"] is not None
    assert user["username"] == "alice_dev"
    assert user["email"] == "alice@example.com"

    # Authenticate by username
    auth = db.authenticate_user("alice_dev", "SecretPass123!")
    assert auth["id"] == user["id"]

    # Authenticate by email
    auth_email = db.authenticate_user("alice@example.com", "SecretPass123!")
    assert auth_email["id"] == user["id"]

    # Reject wrong password
    with pytest.raises(ValueError, match="Invalid"):
        db.authenticate_user("alice_dev", "WrongPassword")

    # Reject duplicate username
    with pytest.raises(ValueError, match="already taken"):
        db.register_user("alice_dev", "another@example.com", "Pass1234")

    # Reject duplicate email
    with pytest.raises(ValueError, match="already exists"):
        db.register_user("bob_dev", "alice@example.com", "Pass1234")


def test_invalid_registration_inputs(db):
    with pytest.raises(ValueError, match="Username"):
        db.register_user("ab", "valid@example.com", "ValidPass123")

    with pytest.raises(ValueError, match="email"):
        db.register_user("valid_user", "invalid-email", "ValidPass123")

    with pytest.raises(ValueError, match="Password"):
        db.register_user("valid_user", "valid@example.com", "short")


def test_session_lifecycle(db):
    user = db.register_user("carol", "carol@example.com", "PassCarol999")
    token = db.create_session(user["id"])
    assert token is not None

    session_user = db.get_user_by_session(token)
    assert session_user is not None
    assert session_user["username"] == "carol"

    # Invalid token returns None
    assert db.get_user_by_session("non-existent-token") is None
    assert db.get_user_by_session(None) is None

    # Delete session
    assert db.delete_session(token) is True
    assert db.get_user_by_session(token) is None


def test_submission_history_storage(db):
    user = db.register_user("dave", "dave@example.com", "PasswordDave1")
    fake_result = {
        "decision": "review_recommended",
        "combined_score": 0.82,
        "findings": [{"id": 1, "category": "injection"}]
    }

    sub1 = db.save_submission(
        user_id=user["id"],
        document_name="Dave_CV.pdf",
        mode="pdf",
        snippet="Dave's engineering experience...",
        decision="review_recommended",
        score=0.82,
        score_kind="model_score",
        findings_count=1,
        result_json=json.dumps(fake_result)
    )

    assert sub1["id"] is not None
    assert sub1["document_name"] == "Dave_CV.pdf"

    # Save second submission
    sub2 = db.save_submission(
        user_id=user["id"],
        document_name="Plain_Text_Resume",
        mode="text",
        snippet="Built web applications...",
        decision="no_signals_detected",
        score=0.15,
        score_kind="model_score",
        findings_count=0,
        result_json=json.dumps({"decision": "no_signals_detected"})
    )

    history = db.get_user_submissions(user["id"])
    assert len(history) == 2
    # Check descending order
    assert history[0]["id"] == sub2["id"]
    assert history[1]["id"] == sub1["id"]
    assert db.get_user_submission_count(user["id"]) == 2

    # Fetch detail
    detail = db.get_submission_detail(sub1["id"], user["id"])
    assert detail is not None
    assert json.loads(detail["result_json"])["decision"] == "review_recommended"

    # Another user cannot access dave's submission
    user2 = db.register_user("eve", "eve@example.com", "PasswordEve2")
    assert db.get_submission_detail(sub1["id"], user2["id"]) is None
    assert len(db.get_user_submissions(user2["id"])) == 0

    # Delete submission
    assert db.delete_submission(sub1["id"], user["id"]) is True
    assert db.get_submission_detail(sub1["id"], user["id"]) is None
    assert db.get_user_submission_count(user["id"]) == 1
