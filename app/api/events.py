
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.event import Event
from app.models.webhook import Webhook
from app.models.delivery import Delivery
from app.schemas.event import EventCreate

router = APIRouter()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/events")
def create_event(
    event: EventCreate,
    db: Session = Depends(get_db),
):
    # Save the event
    new_event = Event(
        event_type=event.event_type,
        payload=event.payload,
    )

    db.add(new_event)
    db.flush()

    # Find all registered webhook destinations
    webhooks = db.query(Webhook).order_by(Webhook.id).all()

    # Create a pending delivery for each destination
    deliveries = []

    for webhook in webhooks:
        delivery = Delivery(
            event_id=new_event.id,
            webhook_id=webhook.id,
            status="pending",
            attempts=0,
        )

        db.add(delivery)
        deliveries.append(delivery)

    # Save the event and its delivery records together
    db.commit()
    db.refresh(new_event)

    return {
        "message": "Event created successfully",
        "event": {
            "id": new_event.id,
            "event_type": new_event.event_type,
            "payload": new_event.payload,
            "status": new_event.status,
            "created_at": new_event.created_at,
        },
        "deliveries_created": len(deliveries),
    }


@router.get("/events")
def get_events(
    db: Session = Depends(get_db),
):
    events = (
        db.query(Event)
        .order_by(Event.id.desc())
        .all()
    )

    return {
        "count": len(events),
        "events": [
            {
                "id": event.id,
                "event_type": event.event_type,
                "payload": event.payload,
                "status": event.status,
                "created_at": event.created_at,
            }
            for event in events
        ],
    }
