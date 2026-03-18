import asyncio
import json
import logging
import os
from collections import deque
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timezone
from typing import Any

from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaError
from fastapi import FastAPI, Query

from shared.config import Config

logger = logging.getLogger("uvicorn.error")
alerts_buffer = deque(maxlen=int(os.getenv("ALERT_BUFFER_SIZE", "1000")))


async def _consume_alerts(stop_event: asyncio.Event) -> None:
    while not stop_event.is_set():
        consumer = AIOKafkaConsumer(
            Config.KAFKA_ALERTS_TOPIC,
            bootstrap_servers=Config.KAFKA_BOOTSTRAP_SERVERS,
            group_id=os.getenv("KAFKA_ALERTS_CONSUMER_GROUP", "vor-alert-service"),
            value_deserializer=lambda value: json.loads(value.decode("utf-8")),
            auto_offset_reset="earliest",
            enable_auto_commit=True,
        )
        try:
            await consumer.start()
            logger.info(
                "Alert consumer started (topic=%s, bootstrap=%s)",
                Config.KAFKA_ALERTS_TOPIC,
                Config.KAFKA_BOOTSTRAP_SERVERS,
            )
            while not stop_event.is_set():
                batches = await consumer.getmany(timeout_ms=1000, max_records=100)
                for messages in batches.values():
                    for message in messages:
                        payload: dict[str, Any] = message.value
                        alerts_buffer.append(
                            {
                                "topic": message.topic,
                                "partition": message.partition,
                                "offset": message.offset,
                                "consumed_at": datetime.now(timezone.utc).isoformat(),
                                "event": payload,
                            }
                        )
                        logger.info(
                            "Alert consumed topic=%s partition=%s offset=%s id=%s professional_id=%s risk_score=%s",
                            message.topic,
                            message.partition,
                            message.offset,
                            payload.get("id"),
                            payload.get("professional_id"),
                            payload.get("risk_score"),
                        )
        except asyncio.CancelledError:
            raise
        except KafkaError as err:
            logger.exception("Kafka alert consumer error: %s", err)
            await asyncio.sleep(2)
        finally:
            await consumer.stop()


@asynccontextmanager
async def lifespan(app: FastAPI):
    stop_event = asyncio.Event()
    consumer_task = asyncio.create_task(_consume_alerts(stop_event))
    app.state.kafka_stop_event = stop_event
    app.state.kafka_consumer_task = consumer_task
    try:
        yield
    finally:
        stop_event.set()
        consumer_task.cancel()
        with suppress(asyncio.CancelledError):
            await consumer_task


app = FastAPI(title="Alert Service", lifespan=lifespan)


@app.get("/alerts")
async def list_alerts(limit: int = Query(default=50, ge=1, le=500)) -> dict[str, list[dict[str, Any]]]:
    items = list(alerts_buffer)
    return {"alerts": list(reversed(items[-limit:]))}


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "alerts_buffered": len(alerts_buffer)}
