from fastapi import FastAPI
from app.api.routes import events

app = FastAPI(title="CampusCue Core API")

app.include_router(events.router)

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/ready")
async def ready():
    return {"status": "ready"}
