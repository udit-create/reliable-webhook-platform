
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.api.deliveries import get_db


def test_list_deliveries():
    mock_db = MagicMock()

    def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    delivery1 = MagicMock()
    delivery1.id = 2
    delivery1.status = "pending"

    delivery2 = MagicMock()
    delivery2.id = 1
    delivery2.status = "success"

    mock_query = mock_db.query.return_value
    mock_query.count.return_value = 2
    mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [
        delivery1,
        delivery2,
    ]

    client = TestClient(app)

    try:
        response = client.get("/deliveries/")

        assert response.status_code == 200

        data = response.json()
        assert data["count"] == 2
        assert data["total"] == 2
        assert data["limit"] == 10
        assert data["offset"] == 0
        assert len(data["deliveries"]) == 2

    finally:
        app.dependency_overrides.pop(get_db, None)


def test_list_deliveries_with_status_filter():
    mock_db = MagicMock()

    def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    mock_query = mock_db.query.return_value
    mock_query.filter.return_value = mock_query
    mock_query.count.return_value = 1
    mock_query.order_by.return_value.offset.return_value.limit.return_value.all.return_value = []

    client = TestClient(app)

    try:
        response = client.get("/deliveries/?status=pending")

        assert response.status_code == 200
        assert response.json()["total"] == 1
        mock_query.filter.assert_called_once()

    finally:
        app.dependency_overrides.pop(get_db, None)


def test_retry_dead_letter_delivery():
    mock_db = MagicMock()

    def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    delivery = MagicMock()
    delivery.id = 10
    delivery.status = "dead_letter"
    delivery.attempts = 3
    delivery.total_attempts = 5
    delivery.next_retry_at = "some-date"
    delivery.error_message = "Previous failure"
    delivery.last_response_code = 405

    mock_db.query.return_value.filter.return_value.first.return_value = delivery

    client = TestClient(app)

    try:
        response = client.post("/deliveries/10/retry")

        assert response.status_code == 200

        data = response.json()
        assert data["message"] == "Delivery queued for manual retry"
        assert data["delivery_id"] == 10
        assert data["status"] == "pending"
        assert data["attempts"] == 0

        # Lifetime attempts must be preserved.
        assert data["total_attempts"] == 5
        assert delivery.total_attempts == 5

        assert delivery.next_retry_at is None
        assert delivery.error_message is None
        assert delivery.last_response_code is None

        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once_with(delivery)

    finally:
        app.dependency_overrides.pop(get_db, None)


def test_retry_delivery_not_found():
    mock_db = MagicMock()

    def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    mock_db.query.return_value.filter.return_value.first.return_value = None

    client = TestClient(app)

    try:
        response = client.post("/deliveries/999/retry")

        assert response.status_code == 404
        assert response.json()["detail"] == "Delivery not found"

    finally:
        app.dependency_overrides.pop(get_db, None)


def test_retry_delivery_with_invalid_status():
    mock_db = MagicMock()

    def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    delivery = MagicMock()
    delivery.id = 11
    delivery.status = "pending"

    mock_db.query.return_value.filter.return_value.first.return_value = delivery

    client = TestClient(app)

    try:
        response = client.post("/deliveries/11/retry")

        assert response.status_code == 400
        assert response.json()["detail"] == (
            "Only dead-letter deliveries can be retried"
        )

        mock_db.commit.assert_not_called()

    finally:
        app.dependency_overrides.pop(get_db, None)
