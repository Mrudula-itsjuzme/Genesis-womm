from fastapi import FastAPI

app = FastAPI(title="CampusCue RAG API")

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.get("/ready")
def ready_check():
    return {"status": "ready"}
