
from fastapi import FastAPI

from app.api.webhooks import router as webhooks_router
from app.api.events import router as events_router
from app.api.deliveries import router as deliveries_router
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Reliable Webhook Platform",
    description="A platform for reliable event delivery and processing",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(webhooks_router)
app.include_router(events_router)
app.include_router(deliveries_router)


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "webhook-platform",
    }
