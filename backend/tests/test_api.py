import os

os.environ.setdefault(
    "APP_ENV",
    "test",
)

os.environ.setdefault(
    "API_SECRET_KEY",
    "test-secret-key",
)

os.environ.setdefault(
    "ANDROID_API_KEY",
    "test-android-key",
)

os.environ.setdefault(
    "DATABASE_URL",
    "sqlite:///./test_ld76_domain_finder.db",
)

from fastapi.testclient import TestClient

from backend.app.main import app


client = TestClient(app)

HEADERS = {
    "X-Android-API-Key": "test-android-key",
}


def test_health():
    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "healthy"


def test_root():
    response = client.get("/")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "online"


def test_results_requires_authentication():
    response = client.get("/api/results")

    assert response.status_code == 401


def test_results_endpoint():
    response = client.get(
        "/api/results",
        headers=HEADERS,
    )

    assert response.status_code == 200

    assert isinstance(
        response.json(),
        list,
    )


def test_history_endpoint():
    response = client.get(
        "/api/history",
        headers=HEADERS,
    )

    assert response.status_code == 200

    assert isinstance(
        response.json(),
        list,
    )


def test_stats_endpoint():
    response = client.get(
        "/api/stats",
        headers=HEADERS,
    )

    assert response.status_code == 200

    data = response.json()

    assert "domains" in data
    assert "scans" in data

    assert "total" in data["domains"]
    assert "active" in data["domains"]
    assert "python_candidates" in data["domains"]

    assert "completed" in data["scans"]
    assert "failed" in data["scans"]
    assert "running" in data["scans"]


def test_invalid_result_domain():
    response = client.get(
        "/api/results/",
        headers=HEADERS,
    )

    # FastAPI routing should not expose an empty-domain lookup.
    assert response.status_code in {404, 307}


def test_stats_requires_authentication():
    response = client.get("/api/stats")

    assert response.status_code == 401
