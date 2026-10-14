
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.api.webhooks import get_db


def test_create_webhook():
    mock_db = MagicMock()

    def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    def assign_id(webhook):
        webhook.id = 1
        webhook.created_at = None

    mock_db.refresh.side_effect = assign_id

    client = TestClient(app)

    try:
        response = client.post(
            "/webhooks",
            json={
                "name": "Test Payment Webhook",
                "target_url": "https://example.com/webhook",
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert data["message"] == "Webhook registered successfully"
        assert data["webhook"]["id"] == 1
        assert data["webhook"]["name"] == "Test Payment Webhook"
        assert data["webhook"]["target_url"] == "https://example.com/webhook"

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    finally:
        app.dependency_overrides.pop(get_db, None)


def test_create_webhook_with_invalid_url():
    client = TestClient(app)

    response = client.post(
        "/webhooks",
        json={
            "name": "Invalid Webhook",
            "target_url": "not-a-valid-url",
        },
    )

    assert response.status_code == 422

def test_list_webhooks():
    mock_db = MagicMock()

    def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    mock_webhook = MagicMock()
    mock_webhook.id = 1
    mock_webhook.name = "Payment Webhook"
    mock_webhook.target_url = "https://example.com/webhook"
    mock_webhook.created_at = None

    mock_db.query.return_value.order_by.return_value.all.return_value = [
        mock_webhook
    ]

    client = TestClient(app)

    try:
        response = client.get("/webhooks")

        assert response.status_code == 200

        data = response.json()

        assert data["count"] == 1
        assert len(data["webhooks"]) == 1
        assert data["webhooks"][0]["id"] == 1
        assert data["webhooks"][0]["name"] == "Payment Webhook"
        assert (
            data["webhooks"][0]["target_url"]
            == "https://example.com/webhook"
        )

    finally:
        app.dependency_overrides.pop(get_db, None)

def test_get_webhook_by_id():
    mock_db = MagicMock()

    def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    mock_webhook = MagicMock()
    mock_webhook.id = 1
    mock_webhook.name = "Payment Webhook"
    mock_webhook.target_url = "https://example.com/webhook"
    mock_webhook.created_at = None

    mock_db.query.return_value.filter.return_value.first.return_value = (
        mock_webhook
    )

    client = TestClient(app)

    try:
        response = client.get("/webhooks/1")

        assert response.status_code == 200

        data = response.json()

        assert data["id"] == 1
        assert data["name"] == "Payment Webhook"
        assert data["target_url"] == "https://example.com/webhook"

    finally:
        app.dependency_overrides.pop(get_db, None)

def test_get_webhook_not_found():
    mock_db = MagicMock()

    def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    # Simulate a database query that finds no webhook.
    mock_db.query.return_value.filter.return_value.first.return_value = None

    client = TestClient(app)

    try:
        response = client.get("/webhooks/99999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Webhook not found"

    finally:
        app.dependency_overrides.pop(get_db, None)
