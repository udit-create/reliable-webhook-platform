
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import httpx

from app.workers import delivery_worker as worker


def make_delivery(attempts=0, total_attempts=0):
    return SimpleNamespace(
        id=1,
        webhook_id=10,
        event_id=20,
        status="pending",
        attempts=attempts,
        total_attempts=total_attempts,
        last_response_code=None,
        next_retry_at=None,
        error_message=None,
    )


def setup_database(delivery):
    db = MagicMock()

    webhook = SimpleNamespace(
        id=10,
        target_url="https://receiver.example/webhook",
    )

    event = SimpleNamespace(
        id=20,
        event_type="payment.success",
        payload={"payment_id": "pay_123"},
    )

    webhook_query = MagicMock()
    webhook_query.filter.return_value.first.return_value = webhook

    event_query = MagicMock()
    event_query.filter.return_value.first.return_value = event

    db.query.side_effect = [webhook_query, event_query]

    return db


def test_retry_delay():
    assert worker.get_retry_delay(1) == 5
    assert worker.get_retry_delay(2) == 15
    assert worker.get_retry_delay(3) == 45


def test_successful_delivery(monkeypatch):
    delivery = make_delivery()
    db = setup_database(delivery)

    response = SimpleNamespace(
        status_code=200,
        reason_phrase="OK",
    )

    monkeypatch.setattr(
        worker.httpx,
        "post",
        lambda *args, **kwargs: response,
    )

    worker.send_webhook(delivery, db)

    assert delivery.status == "success"
    assert delivery.attempts == 1
    assert delivery.total_attempts == 1
    assert delivery.last_response_code == 200
    assert delivery.next_retry_at is None
    assert delivery.error_message is None
    db.commit.assert_called_once()


def test_temporary_http_error_schedules_retry(monkeypatch):
    delivery = make_delivery()
    db = setup_database(delivery)

    response = SimpleNamespace(
        status_code=500,
        reason_phrase="Internal Server Error",
    )

    monkeypatch.setattr(
        worker.httpx,
        "post",
        lambda *args, **kwargs: response,
    )

    before = datetime.now()
    worker.send_webhook(delivery, db)
    after = datetime.now()

    assert delivery.status == "failed"
    assert delivery.attempts == 1
    assert delivery.total_attempts == 1
    assert delivery.last_response_code == 500

    assert before + timedelta(seconds=5) <= delivery.next_retry_at
    assert delivery.next_retry_at <= after + timedelta(seconds=5)

    db.commit.assert_called_once()


def test_permanent_http_error_goes_to_dead_letter(monkeypatch):
    delivery = make_delivery()
    db = setup_database(delivery)

    response = SimpleNamespace(
        status_code=405,
        reason_phrase="Method Not Allowed",
    )

    monkeypatch.setattr(
        worker.httpx,
        "post",
        lambda *args, **kwargs: response,
    )

    worker.send_webhook(delivery, db)

    assert delivery.status == "dead_letter"
    assert delivery.attempts == 1
    assert delivery.total_attempts == 1
    assert delivery.last_response_code == 405
    assert delivery.next_retry_at is None
    assert "HTTP 405" in delivery.error_message

    db.commit.assert_called_once()


def test_connection_error_respects_max_attempts(monkeypatch):
    delivery = make_delivery(
        attempts=2,
        total_attempts=7,
    )
    db = setup_database(delivery)

    def raise_connection_error(*args, **kwargs):
        raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr(
        worker.httpx,
        "post",
        raise_connection_error,
    )

    worker.send_webhook(delivery, db)

    assert delivery.status == "dead_letter"
    assert delivery.attempts == 3
    assert delivery.total_attempts == 8
    assert delivery.last_response_code is None
    assert delivery.next_retry_at is None
    assert "Connection error" in delivery.error_message

    db.commit.assert_called_once()
