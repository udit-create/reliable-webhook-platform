
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.main import app
from app.api.events import get_db
from app.models.event import Event
from app.models.delivery import Delivery


def test_create_event():
    mock_db = MagicMock()

    def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db

    # Capture the event and delivery objects passed to db.add().
    added_objects = []

    def capture_added_object(obj):
        added_objects.append(obj)

    mock_db.add.side_effect = capture_added_object

    # Simulate the database assigning an ID during flush().
    def assign_event_id():
        event = next(
            obj for obj in added_objects if isinstance(obj, Event)
        )
        event.id = 101
        event.status = "pending"
        event.created_at = None

    mock_db.flush.side_effect = assign_event_id

    # Simulate two registered webhook destinations.
    webhook1 = MagicMock()
    webhook1.id = 1

    webhook2 = MagicMock()
    webhook2.id = 2

    mock_db.query.return_value.order_by.return_value.all.return_value = [
        webhook1,
        webhook2,
    ]

    client = TestClient(app)

    try:
        response = client.post(
            "/events",
            json={
                "event_type": "payment.success",
                "payload": {
                    "payment_id": "pay_123",
                    "amount": 500,
                },
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert data["message"] == "Event created successfully"
        assert data["event"]["id"] == 101
        assert data["event"]["event_type"] == "payment.success"
        assert data["event"]["payload"]["payment_id"] == "pay_123"
        assert data["event"]["payload"]["amount"] == 500
        assert data["event"]["status"] == "pending"

        # One event plus two delivery records.
        assert data["deliveries_created"] == 2
        assert mock_db.add.call_count == 3

        # Confirm two Delivery objects were created.
        delivery_objects = [
            obj for obj in added_objects
            if isinstance(obj, Delivery)
        ]
        assert len(delivery_objects) == 2

        assert all(
            delivery.event_id == 101
            for delivery in delivery_objects
        )
        assert {d.webhook_id for d in delivery_objects} == {1, 2}
        assert all(
            delivery.status == "pending"
            and delivery.attempts == 0
            for delivery in delivery_objects
        )

        mock_db.flush.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    finally:
        app.dependency_overrides.pop(get_db, None)
