"""
Integration and validation tests for FastAPI endpoints.
"""
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_health_check_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data


def test_repository_status_endpoint():
    response = client.get("/api/repository/status")
    assert response.status_code == 200
    data = response.json()
    assert "is_indexed" in data
    assert "status" in data


def test_analyze_invalid_url():
    # Empty URL
    response = client.post("/api/repository/analyze", json={"github_url": ""})
    assert response.status_code == 400

    # Non-GitHub URL
    response = client.post("/api/repository/analyze", json={"github_url": "https://notgithub.com/a/b"})
    assert response.status_code == 400


def test_chat_without_indexed_repository():
    response = client.post("/api/chat", json={"question": "Where is authentication?"})
    assert response.status_code == 400
    assert "No repository is currently indexed" in response.json()["detail"]


def test_suggested_questions():
    response = client.get("/api/chat/suggested-questions")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) > 0
