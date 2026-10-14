
from fastapi import FastAPI, Request

app = FastAPI(title="Webhook Test Receiver")


@app.post("/receive")
async def receive_webhook(request: Request):
    payload = await request.json()

    print("Webhook received:", payload)

    return {
        "message": "Webhook received successfully",
        "received": True,
    }

@app.post("/receive-404")
async def receive_404():
    from fastapi import HTTPException

    raise HTTPException(
        status_code=404,
        detail="Test webhook endpoint not found"
    )

