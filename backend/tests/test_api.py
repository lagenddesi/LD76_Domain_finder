import os

os.environ["APP_ENV"] = "test"
os.environ["APP_DEBUG"] = "false"
os.environ["API_SECRET_KEY"] = "test-secret-key"
os.environ["ANDROID_API_KEY"] = "test-android-key"
os.environ["DATABASE_URL"] = "sqlite:///./test_ld76_domain_finder.db"
os.environ["CORS_ORIGINS"] = "http://localhost:3000"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from backend.app.database import Base, SessionLocal, engine
from backend.app.main import app
from backend.app.models import DomainResult, ScanHistory
from backend.app.services.persistence import upsert_domain_result


HEADERS = {
    "X-Android-API-Key": "test-android-key",
}


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)

    yield

    db = SessionLocal()

    try:
        db.execute(delete(DomainResult))
        db.execute(delete(ScanHistory))
        db.commit()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def clean_database():
    db = SessionLocal()

    try:
        db.execute(delete(DomainResult))
        db.execute(delete(ScanHistory))
        db.commit()
    finally:
        db.close()

    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "healthy"
    assert data["service"] == "ld76-domain-finder-api"


def test_root(client):
    response = client.get("/")

    assert response.status_code == 200

    data = response.json()

    assert data["name"] == "LD76 Domain Finder API"
    assert data["status"] == "online"
    assert data["environment"] == "test"


def test_results_requires_authentication(client):
    response = client.get("/api/results")

    assert response.status_code == 401


def test_stats_requires_authentication(client):
    response = client.get("/api/stats")

    assert response.status_code == 401


def test_history_requires_authentication(client):
    response = client.get("/api/history")

    assert response.status_code == 401


def test_scan_requires_authentication(client):
    response = client.post("/api/scan/start")

    assert response.status_code == 401


def test_rescan_requires_authentication(client):
    response = client.post(
        "/api/rescan/example.top"
    )

    assert response.status_code == 401


def test_results_endpoint_empty(client):
    response = client.get(
        "/api/results",
        headers=HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == []


def test_history_endpoint_empty(client):
    response = client.get(
        "/api/history",
        headers=HEADERS,
    )

    assert response.status_code == 200
    assert response.json() == []


def test_stats_endpoint_empty(client):
    response = client.get(
        "/api/stats",
        headers=HEADERS,
    )

    assert response.status_code == 200

    data = response.json()

    assert "domains" in data
    assert "scans" in data

    assert data["domains"]["total"] == 0
    assert data["domains"]["active"] == 0
    assert data["domains"]["python_candidates"] == 0
    assert data["domains"]["strong_candidates"] == 0
    assert data["domains"]["gemini_analyzed"] == 0

    assert data["scans"]["completed"] == 0
    assert data["scans"]["failed"] == 0
    assert data["scans"]["running"] == 0
    assert data["scans"]["total"] == 0


def test_invalid_result_domain(client):
    response = client.get(
        "/api/results/",
        headers=HEADERS,
        follow_redirects=False,
    )

    assert response.status_code in {404, 307}


def test_result_serialization(client):
    db = SessionLocal()

    try:
        upsert_domain_result(
            db,
            {
                "domain": "example.top",
                "status": "active",
                "python_score": 85,
                "gemini_score": 92,
                "gemini_analyzed": True,
                "content_hash": "abc123",
                "title": "Example Investment",
                "url": "https://example.top",
                "classification": "investment",
                "reason": "Investment-related signals detected.",
                "evidence": [
                    {
                        "type": "keyword",
                        "text": "daily profit",
                    }
                ],
                "signals": [
                    "investment",
                    "profit",
                ],
            }
        )

        db.commit()
    finally:
        db.close()

    response = client.get(
        "/api/results",
        headers=HEADERS,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1

    result = data[0]

    assert result["domain"] == "example.top"
    assert result["status"] == "active"
    assert result["python_score"] == 85
    assert result["gemini_score"] == 92
    assert result["gemini_analyzed"] is True
    assert result["title"] == "Example Investment"
    assert result["classification"] == "investment"

    assert isinstance(result["evidence"], list)
    assert isinstance(result["signals"], list)

    assert result["evidence"][0]["type"] == "keyword"
    assert result["signals"] == [
        "investment",
        "profit",
    ]


def test_get_single_result(client):
    db = SessionLocal()

    try:
        upsert_domain_result(
            db,
            {
                "domain": "example.top",
                "status": "active",
                "python_score": 75,
                "title": "Example",
            }
        )

        db.commit()
    finally:
        db.close()

    response = client.get(
        "/api/results/example.top",
        headers=HEADERS,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["domain"] == "example.top"
    assert data["python_score"] == 75
    assert data["title"] == "Example"


def test_get_single_result_case_insensitive(client):
    db = SessionLocal()

    try:
        upsert_domain_result(
            db,
            {
                "domain": "example.top",
                "status": "active",
                "python_score": 70,
            }
        )

        db.commit()
    finally:
        db.close()

    response = client.get(
        "/api/results/EXAMPLE.TOP",
        headers=HEADERS,
    )

    assert response.status_code == 200
    assert response.json()["domain"] == "example.top"


def test_get_missing_result(client):
    response = client.get(
        "/api/results/not-found.top",
        headers=HEADERS,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Domain result not found."
    )


def test_results_score_filter(client):
    db = SessionLocal()

    try:
        upsert_domain_result(
            db,
            {
                "domain": "low.top",
                "status": "active",
                "python_score": 40,
            }
        )

        upsert_domain_result(
            db,
            {
                "domain": "high.top",
                "status": "active",
                "python_score": 90,
            }
        )

        db.commit()
    finally:
        db.close()

    response = client.get(
        "/api/results?min_score=80",
        headers=HEADERS,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["domain"] == "high.top"


def test_results_classification_filter(client):
    db = SessionLocal()

    try:
        upsert_domain_result(
            db,
            {
                "domain": "investment.top",
                "classification": "investment",
                "python_score": 80,
            }
        )

        upsert_domain_result(
            db,
            {
                "domain": "normal.top",
                "classification": "normal",
                "python_score": 80,
            }
        )

        db.commit()
    finally:
        db.close()

    response = client.get(
        "/api/results?classification=investment",
        headers=HEADERS,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["domain"] == "investment.top"


def test_results_search_filter(client):
    db = SessionLocal()

    try:
        upsert_domain_result(
            db,
            {
                "domain": "profit.top",
                "title": "Daily Profit Investment",
                "python_score": 85,
            }
        )

        upsert_domain_result(
            db,
            {
                "domain": "normal.top",
                "title": "Normal Website",
                "python_score": 50,
            }
        )

        db.commit()
    finally:
        db.close()

    response = client.get(
        "/api/results?search=profit",
        headers=HEADERS,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["domain"] == "profit.top"


def test_results_limit_validation(client):
    response = client.get(
        "/api/results?limit=0",
        headers=HEADERS,
    )

    assert response.status_code == 422


def test_results_limit_max_validation(client):
    response = client.get(
        "/api/results?limit=501",
        headers=HEADERS,
    )

    assert response.status_code == 422


def test_history_serialization(client):
    db = SessionLocal()

    try:
        history = ScanHistory(
            status="completed",
            domains_discovered=100,
            domains_scanned=80,
            candidates_found=12,
        )

        db.add(history)
        db.commit()
    finally:
        db.close()

    response = client.get(
        "/api/history",
        headers=HEADERS,
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1

    item = data[0]

    assert item["status"] == "completed"
    assert item["domains_discovered"] == 100
    assert item["domains_scanned"] == 80
    assert item["candidates_found"] == 12


def test_stats_with_data(client):
    db = SessionLocal()

    try:
        upsert_domain_result(
            db,
            {
                "domain": "active.top",
                "status": "active",
                "python_score": 85,
            }
        )

        upsert_domain_result(
            db,
            {
                "domain": "candidate.top",
                "status": "active",
                "python_score": 65,
            }
        )

        upsert_domain_result(
            db,
            {
                "domain": "analyzed.top",
                "status": "active",
                "python_score": 90,
                "gemini_score": 95,
                "gemini_analyzed": True,
            }
        )

        db.add(
            ScanHistory(
                status="completed",
                domains_discovered=3,
                domains_scanned=3,
                candidates_found=3,
            )
        )

        db.add(
            ScanHistory(
                status="failed",
                domains_discovered=2,
                domains_scanned=1,
                candidates_found=1,
                error_message="Test failure",
            )
        )

        db.commit()
    finally:
        db.close()

    response = client.get(
        "/api/stats",
        headers=HEADERS,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["domains"]["total"] == 3
    assert data["domains"]["active"] == 3
    assert data["domains"]["python_candidates"] == 3
    assert data["domains"]["strong_candidates"] == 2
    assert data["domains"]["gemini_analyzed"] == 1

    assert data["scans"]["completed"] == 1
    assert data["scans"]["failed"] == 1
    assert data["scans"]["running"] == 0
    assert data["scans"]["total"] == 2


def test_scan_status_without_previous_scan(client):
    response = client.get(
        "/api/scan/status",
        headers=HEADERS,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["scan_id"] == 0
    assert data["status"] == "idle"
    assert data["domains_discovered"] == 0
    assert data["domains_scanned"] == 0
    assert data["candidates_found"] == 0


def test_scan_status_missing_scan(client):
    response = client.get(
        "/api/scan/status/999999",
        headers=HEADERS,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Scan not found."


def test_scan_start(client, monkeypatch):
    monkeypatch.setattr(
        "backend.app.routers.scans.scan_manager.start_scan",
        lambda: 123,
    )

    response = client.post(
        "/api/scan/start",
        headers=HEADERS,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["scan_id"] == 123
    assert data["status"] == "started"


def test_scan_start_conflict(client, monkeypatch):
    def raise_conflict():
        raise RuntimeError(
            "Scan 123 is already running."
        )

    monkeypatch.setattr(
        "backend.app.routers.scans.scan_manager.start_scan",
        raise_conflict,
    )

    response = client.post(
        "/api/scan/start",
        headers=HEADERS,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Scan 123 is already running."
    )


def test_rescan_empty_domain(client):
    response = client.post(
        "/api/rescan/%20",
        headers=HEADERS,
    )

    assert response.status_code in {400, 404}


def test_rescan_conflict(client, monkeypatch):
    monkeypatch.setattr(
        "backend.app.routers.rescan.scan_manager.is_running",
        lambda: True,
    )

    response = client.post(
        "/api/rescan/example.top",
        headers=HEADERS,
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Another scan is already running."
    )


def test_rescan_start(client, monkeypatch):
    monkeypatch.setattr(
        "backend.app.routers.rescan.scan_manager.is_running",
        lambda: False,
    )

    monkeypatch.setattr(
        "backend.app.routers.rescan.scan_manager.start_rescan",
        lambda domain: 456,
    )

    response = client.post(
        "/api/rescan/example.top",
        headers=HEADERS,
    )

    assert response.status_code == 200

    data = response.json()

    assert data["scan_id"] == 456
    assert data["status"] == "running"
    assert data["domain"] == "example.top"


def test_invalid_api_key(client):
    response = client.get(
        "/api/results",
        headers={
            "X-Android-API-Key": "wrong-key",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Invalid API key."
    )


def test_missing_api_key(client):
    response = client.get(
        "/api/results",
    )

    assert response.status_code == 401
    assert response.json()["detail"] == (
        "Missing API key."
        )
