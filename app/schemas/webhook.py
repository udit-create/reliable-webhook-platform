
from pydantic import BaseModel, HttpUrl


class WebhookCreate(BaseModel):
    name: str
    target_url: HttpUrl
