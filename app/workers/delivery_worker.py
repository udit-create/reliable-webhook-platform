
from datetime import datetime, timedelta
import time

import httpx
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.delivery import Delivery
from app.models.event import Event
from app.models.webhook import Webhook


MAX_ATTEMPTS = 3
POLL_INTERVAL = 5

PERMANENT_HTTP_ERRORS = [400, 401, 403, 404, 405, 410, 422]


def get_retry_delay(attempts: int) -> int:
    return 5 * (3 ** (attempts - 1))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def fetch_pending_deliveries(db: Session):
    now = datetime.now()

    deliveries = (
        db.query(Delivery)
        .filter(
            Delivery.attempts < MAX_ATTEMPTS,
            Delivery.status.in_(["pending", "failed"]),
            (Delivery.next_retry_at.is_(None))
            | (Delivery.next_retry_at <= now),
        )
        .order_by(Delivery.id)
        .all()
    )

    return deliveries


def log_delivery(delivery: Delivery, message: str = ""):
    """Print delivery status and both attempt counters."""
    prefix = f"{message} " if message else ""

    print(
        f"{prefix}Delivery {delivery.id}: "
        f"Status: {delivery.status} | "
        f"Attempts: {delivery.attempts} | "
        f"Total Attempts: {delivery.total_attempts} | "
        f"HTTP Code: {delivery.last_response_code} | "
        f"Error: {delivery.error_message} | "
        f"Next retry: {delivery.next_retry_at}"
    )


def send_webhook(delivery: Delivery, db: Session):
    # Find the webhook destination
    webhook = (
        db.query(Webhook)
        .filter(Webhook.id == delivery.webhook_id)
        .first()
    )

    # Find the event to deliver
    event = (
        db.query(Event)
        .filter(Event.id == delivery.event_id)
        .first()
    )

    # Handle missing database records
    if webhook is None or event is None:
        delivery.attempts += 1
        delivery.total_attempts += 1
        delivery.error_message = "Missing webhook or event record"

        if delivery.attempts >= MAX_ATTEMPTS:
            delivery.status = "dead_letter"
            delivery.next_retry_at = None
        else:
            delivery.status = "failed"
            delay = get_retry_delay(delivery.attempts)
            delivery.next_retry_at = (
                datetime.now() + timedelta(seconds=delay)
            )

        db.commit()
        log_delivery(delivery, "Failed:")
        return

    # Prepare the HTTP request body
    payload = {
        "event_id": event.id,
        "event_type": event.event_type,
        "payload": event.payload,
    }

    # Count this delivery attempt
    delivery.attempts += 1
    delivery.total_attempts += 1

    try:
        # Send the HTTP POST request
        response = httpx.post(
            webhook.target_url,
            json=payload,
            timeout=10.0,
        )

        # Save the HTTP response code
        delivery.last_response_code = response.status_code

        # Handle successful responses
        if 200 <= response.status_code < 300:
            delivery.status = "success"
            delivery.next_retry_at = None
            delivery.error_message = None

        # Handle permanent HTTP errors
        elif response.status_code in PERMANENT_HTTP_ERRORS:
            delivery.status = "dead_letter"
            delivery.next_retry_at = None
            delivery.error_message = (
                f"HTTP {response.status_code}: "
                f"{response.reason_phrase}"
            )

        # Handle exhausted attempts
        elif delivery.attempts >= MAX_ATTEMPTS:
            delivery.status = "dead_letter"
            delivery.next_retry_at = None
            delivery.error_message = (
                f"HTTP {response.status_code}: "
                f"{response.reason_phrase}"
            )

        # Handle retryable HTTP errors
        else:
            delivery.status = "failed"
            delay = get_retry_delay(delivery.attempts)
            delivery.next_retry_at = (
                datetime.now() + timedelta(seconds=delay)
            )
            delivery.error_message = (
                f"HTTP {response.status_code}: "
                f"{response.reason_phrase}"
            )

        # Save changes to MySQL
        db.commit()
        log_delivery(delivery)

    except httpx.RequestError as error:
        # Record connection errors and timeouts
        delivery.error_message = (
            f"Connection error: {str(error)[:450]}"
        )
        delivery.last_response_code = None

        if delivery.attempts >= MAX_ATTEMPTS:
            delivery.status = "dead_letter"
            delivery.next_retry_at = None
        else:
            delivery.status = "failed"
            delay = get_retry_delay(delivery.attempts)
            delivery.next_retry_at = (
                datetime.now() + timedelta(seconds=delay)
            )

        db.commit()
        log_delivery(delivery, "Request failed:")

def process_single_delivery(delivery_id: int):
    """Process one delivery requested by the dashboard."""
    db = SessionLocal()

    try:
        delivery = (
            db.query(Delivery)
            .filter(Delivery.id == delivery_id)
            .with_for_update()
            .first()
        )

        if delivery is None:
            print(f"Delivery {delivery_id} not found.")
            return

        if delivery.status != "pending":
            print(
                f"Delivery {delivery_id} was not processed: "
                f"status is {delivery.status}."
            )
            return

        print(f"Processing manually retried delivery: {delivery_id}")
        send_webhook(delivery, db)

    except Exception as error:
        db.rollback()
        print(f"Manual retry error for delivery {delivery_id}: {error}")

    finally:
        db.close()


if __name__ == "__main__":
    print("Webhook delivery worker started...")

    try:
        while True:
            db = SessionLocal()

            try:
                deliveries = fetch_pending_deliveries(db)

                if deliveries:
                    print(
                        f"Eligible deliveries found: "
                        f"{len(deliveries)}"
                    )

                    for delivery in deliveries:
                        print(
                            f"Processing delivery ID: {delivery.id}"
                        )
                        send_webhook(delivery, db)

            except Exception as error:
                db.rollback()
                print(f"Worker error: {error}")

            finally:
                db.close()

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        print("Webhook delivery worker stopped.")
