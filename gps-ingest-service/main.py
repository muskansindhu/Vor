import json
import logging
from datetime import datetime, timezone
from contextlib import asynccontextmanager

from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaError
from fastapi import FastAPI, HTTPException

from shared.config import Config
from shared.schemas import GPSData

logger = logging.getLogger("uvicorn.error")
producer: AIOKafkaProducer | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    del app
    global producer
    producer = AIOKafkaProducer(
        bootstrap_servers=Config.KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    )
    try:
        await producer.start()
    except KafkaError as err:
        logger.exception("Failed to connect producer to Kafka: %s", err)
        producer = None

    try:
        yield
    finally:
        if producer is not None:
            await producer.stop()
            producer = None


app = FastAPI(title="GPS Ingest Service", lifespan=lifespan)

@app.post("/locations")
async def ingest_gps_data(payload: GPSData) -> dict:
    try:
        ts = datetime.fromtimestamp(payload.timestamp, tz=timezone.utc)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid timestamp format"
        )

    if producer is None:
        raise HTTPException(
            status_code=503,
            detail="Kafka producer unavailable",
        )

    message = payload.model_dump()
    message["timestamp"] = int(ts.timestamp())
    try:
        metadata = await producer.send_and_wait(Config.KAFKA_PINGS_TOPIC, message)
        logger.info(
            "Published ping to Kafka topic=%s partition=%s offset=%s professional_id=%s",
            metadata.topic,
            metadata.partition,
            metadata.offset,
            message["professional_id"],
        )
    except KafkaError as err:
        logger.exception("Kafka publish failed: %s", err)
        raise HTTPException(status_code=503, detail="Failed to publish ping to Kafka")

    return {"message": "Location queued successfully"}

@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
