from fastapi.testclient import TestClient

from app.main import app
from config.settings import settings


def test_health_endpoint_is_public():
    settings.admin_username = "test-admin"
    settings.admin_password = "test-password"
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_dashboard_requires_admin_login():
    settings.admin_username = "test-admin"
    settings.admin_password = "test-password"
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 401
    assert "WWW-Authenticate" in response.headers


def test_dashboard_accepts_admin_login():
    settings.admin_username = "test-admin"
    settings.admin_password = "test-password"
    with TestClient(app) as client:
        response = client.get("/", auth=("test-admin", "test-password"))
    assert response.status_code == 200
    assert "Sports Lover Agent" in response.text
