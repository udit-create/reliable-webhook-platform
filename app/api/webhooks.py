
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.webhook import Webhook
from app.schemas.webhook import WebhookCreate

router = APIRouter()


# Database session dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Register a new webhook
@router.post("/webhooks")
def create_webhook(
    webhook: WebhookCreate,
    db: Session = Depends(get_db),
):
    new_webhook = Webhook(
        name=webhook.name,
        target_url=str(webhook.target_url),
    )

    db.add(new_webhook)
    db.commit()
    db.refresh(new_webhook)

    return {
        "message": "Webhook registered successfully",
        "webhook": {
            "id": new_webhook.id,
            "name": new_webhook.name,
            "target_url": new_webhook.target_url,
            "created_at": new_webhook.created_at,
        },
    }


# Retrieve all registered webhooks
@router.get("/webhooks")
def list_webhooks(
    db: Session = Depends(get_db),
):
    webhooks = (
        db.query(Webhook)
        .order_by(Webhook.id)
        .all()
    )

    return {
        "count": len(webhooks),
        "webhooks": [
            {
                "id": webhook.id,
                "name": webhook.name,
                "target_url": webhook.target_url,
                "created_at": webhook.created_at,
            }
            for webhook in webhooks
        ],
    }


# Retrieve a specific webhook by ID
@router.get("/webhooks/{webhook_id}")
def get_webhook(
    webhook_id: int,
    db: Session = Depends(get_db),
):
    webhook = (
        db.query(Webhook)
        .filter(Webhook.id == webhook_id)
        .first()
    )

    if webhook is None:
        raise HTTPException(
            status_code=404,
            detail="Webhook not found",
        )

    return {
        "id": webhook.id,
        "name": webhook.name,
        "target_url": webhook.target_url,
        "created_at": webhook.created_at,
    }
