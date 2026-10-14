
from pydantic import BaseModel
from typing import Any


class EventCreate(BaseModel):
    event_type: str
    payload: dict[str, Any]
