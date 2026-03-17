from fastapi import FastAPI, Request
from .processing_pipeline import ProcessingPipeline

from shared.db import init_db
from shared.seed import seed_db

app = FastAPI(title="Processing Service")
pipeline = ProcessingPipeline()

init_db()
seed_db()

@app.post("/pings")
async def ingest_ping(request: Request):
    ping_data = await request.json()
    await pipeline._handle_ping(ping_data)
    return {"result": "Processed"}

@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
