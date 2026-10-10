from fastapi import FastAPI

app = FastAPI(title="CampusCue Core API")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/ready")
async def ready():
    return {"status": "ready"}
