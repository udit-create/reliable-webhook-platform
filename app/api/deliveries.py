
from typing import Literal

from fastapi import APIRouter, Depends,HTTPException,  Query
from sqlalchemy.orm import Session
from fastapi import BackgroundTasks
from app.workers.delivery_worker import process_single_delivery

from app.core.database import SessionLocal
from app.models.delivery import Delivery


router = APIRouter(
    prefix="/deliveries",
    tags=["Deliveries"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()




@router.get("/")
def get_deliveries(
    status: Literal[
        "pending",
        "failed",
        "success",
        "dead_letter",
        "paused"
    ] | None = Query(default=None),
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db)
):
    query = db.query(Delivery)

    if status is not None:
        query = query.filter(Delivery.status == status)

    total = query.count()

    deliveries = (
        query
        .order_by(Delivery.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "count": len(deliveries),
        "total": total,
        "limit": limit,
        "offset": offset,
        "deliveries": deliveries
    }


@router.post("/{delivery_id}/retry")
def retry_delivery(
    delivery_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    delivery = (
        db.query(Delivery)
        .filter(Delivery.id == delivery_id)
        .first()
    )

    if delivery is None:
        raise HTTPException(
            status_code=404,
            detail="Delivery not found"
        )

    if delivery.status != "dead_letter":
        raise HTTPException(
            status_code=400,
            detail="Only dead-letter deliveries can be retried"
        )

    delivery.status = "pending"
    delivery.attempts = 0
    delivery.next_retry_at = None
    delivery.error_message = None
    delivery.last_response_code = None

    delivery_id_to_process = delivery.id

    db.commit()
    db.refresh(delivery)

    # Trigger delivery processing after the response is prepared.
    background_tasks.add_task(
        process_single_delivery,
        delivery_id_to_process
    )

    return {
        "message": "Delivery queued for automatic retry",
        "delivery_id": delivery.id,
        "status": delivery.status,
        "attempts": delivery.attempts,
        "total_attempts": delivery.total_attempts
    }
