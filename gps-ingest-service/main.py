from fastapi import FastAPI, HTTPException
from datetime import datetime, timezone

from shared.schemas import GPSData


app = FastAPI(title="GPS Ingest Service")

@app.post("/locations")
async def ingest_gps_data(payload: GPSData) -> dict:
    try:
        ts = datetime.fromtimestamp(payload.timestamp, tz=timezone.utc)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid timestamp format"
        )

    return {"message": "Location ingested successfully"}

@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
