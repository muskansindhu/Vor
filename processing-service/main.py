import asyncio
import json
import logging
from contextlib import asynccontextmanager, suppress

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import KafkaError
from fastapi import FastAPI, Request

from .processing_pipeline import ProcessingPipeline

from shared.config import Config
from shared.db import init_db
from shared.seed import ensure_simulation_reference_booking, seed_db

logger = logging.getLogger("uvicorn.error")
pipeline = ProcessingPipeline()
producer: AIOKafkaProducer | None = None


async def _publish_alert(alert_event: dict) -> None:
    if producer is None:
        logger.warning("Kafka alert producer unavailable; dropping alert event id=%s", alert_event.get("id"))
        return
    metadata = await producer.send_and_wait(Config.KAFKA_ALERTS_TOPIC, alert_event)
    logger.info(
        "Published alert topic=%s partition=%s offset=%s id=%s professional_id=%s risk_score=%s",
        metadata.topic,
        metadata.partition,
        metadata.offset,
        alert_event.get("id"),
        alert_event.get("professional_id"),
        alert_event.get("risk_score"),
    )


async def _process_ping(ping_data: dict) -> None:
    alert_event = await pipeline._handle_ping(ping_data)
    if alert_event is None:
        return
    try:
        await _publish_alert(alert_event)
    except KafkaError as err:
        logger.exception("Failed to publish alert event: %s", err)


async def _consume_pings(stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        consumer = AIOKafkaConsumer(
            Config.KAFKA_PINGS_TOPIC,
            bootstrap_servers=Config.KAFKA_BOOTSTRAP_SERVERS,
            group_id=Config.KAFKA_CONSUMER_GROUP,
            value_deserializer=lambda value: json.loads(value.decode("utf-8")),
            auto_offset_reset="earliest",
            enable_auto_commit=True,
        )
        try:
            await consumer.start()
            logger.info(
                "Kafka consumer started (topic=%s, group=%s, bootstrap=%s)",
                Config.KAFKA_PINGS_TOPIC,
                Config.KAFKA_CONSUMER_GROUP,
                Config.KAFKA_BOOTSTRAP_SERVERS,
            )

            while not stop_event.is_set():
                batches = await consumer.getmany(timeout_ms=1000, max_records=100)
                for messages in batches.values():
                    for message in messages:
                        try:
                            await _process_ping(message.value)
                            professional_id = message.value.get("professional_id")
                            logger.info(
                                "Consumed ping topic=%s partition=%s offset=%s professional_id=%s",
                                message.topic,
                                message.partition,
                                message.offset,
                                professional_id,
                            )
                        except Exception:
                            logger.exception("Failed to process Kafka ping: %s", message.value)
        except asyncio.CancelledError:
            raise
        except KafkaError as err:
            logger.exception("Kafka consumer error: %s", err)
            await asyncio.sleep(2)
        finally:
            await consumer.stop()


@asynccontextmanager
async def lifespan(app: FastAPI):
    global producer
    init_db()
    seed_db()
    ensure_simulation_reference_booking()

    producer = AIOKafkaProducer(
        bootstrap_servers=Config.KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda value: json.dumps(value).encode("utf-8"),
    )
    try:
        await producer.start()
    except KafkaError as err:
        logger.exception("Failed to start Kafka alert producer: %s", err)
        producer = None

    stop_event = asyncio.Event()
    consumer_task = asyncio.create_task(_consume_pings(stop_event))
    app.state.kafka_stop_event = stop_event
    app.state.kafka_consumer_task = consumer_task
    try:
        yield
    finally:
        stop_event.set()
        consumer_task.cancel()
        with suppress(asyncio.CancelledError):
            await consumer_task
        if producer is not None:
            await producer.stop()
            producer = None


app = FastAPI(title="Processing Service", lifespan=lifespan)

@app.post("/pings")
async def ingest_ping(request: Request):
    ping_data = await request.json()
    await _process_ping(ping_data)
    return {"result": "Processed"}

@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
