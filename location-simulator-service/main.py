import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

import httpx


logging.basicConfig(
    level=os.getenv("SIM_LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s simulator: %(message)s",
)
logger = logging.getLogger("simulator")


class PingSimulator:
    def __init__(self) -> None:
        self.ingest_url = os.getenv("INGEST_URL", "http://gps-ingest-service:8000/locations")
        self.ping_interval_s = float(os.getenv("PING_INTERVAL_SECONDS", "1"))
        timeout_s = float(os.getenv("REQUEST_TIMEOUT_SECONDS", "5"))
        self._client = httpx.AsyncClient(timeout=timeout_s)
        self._day_cursor = 0

    def _ts(self, day: datetime, hour: int, minute: int) -> int:
        return int(day.replace(hour=hour, minute=minute, second=0, microsecond=0).timestamp())

    async def _post(self, label: str, payload: dict) -> None:
        try:
            response = await self._client.post(self.ingest_url, json=payload)
            logger.info("%s status=%s payload=%s", label, response.status_code, payload)
        except Exception as err:
            logger.exception("%s request failed: %s", label, err)
        await asyncio.sleep(self.ping_interval_s)

    async def _send_invalid_payload(self, day: datetime) -> None:
        del day
        payload = {
            "professional_id": "SIM_BAD",
            "timestamp": "invalid-timestamp",
            "latitude": 28.6139,
            "longitude": 77.2090,
        }
        await self._post("invalid_payload", payload)

    async def _send_normal_stay(self, day: datetime) -> None:
        p = "SIM_NORM"
        base_lat, base_lon = 28.6139, 77.2090
        await self._post(
            "normal_1",
            {"professional_id": p, "timestamp": self._ts(day, 10, 0), "latitude": base_lat, "longitude": base_lon},
        )
        await self._post(
            "normal_2",
            {"professional_id": p, "timestamp": self._ts(day, 10, 8), "latitude": base_lat + 0.00001, "longitude": base_lon + 0.00001},
        )
        await self._post(
            "normal_3",
            {"professional_id": p, "timestamp": self._ts(day, 10, 20), "latitude": base_lat + 0.00002, "longitude": base_lon + 0.00002},
        )
        await self._post(
            "normal_close",
            {"professional_id": p, "timestamp": self._ts(day, 10, 50), "latitude": 28.7041, "longitude": 77.1025},
        )

    async def _send_spoofing_stay(self, day: datetime) -> None:
        p = "SIM_SPOOF"
        await self._post(
            "spoof_1",
            {"professional_id": p, "timestamp": self._ts(day, 11, 0), "latitude": 28.6139, "longitude": 77.2090},
        )
        await self._post(
            "spoof_2",
            {"professional_id": p, "timestamp": self._ts(day, 11, 10), "latitude": 19.0760, "longitude": 72.8777},
        )
        await self._post(
            "spoof_3",
            {"professional_id": p, "timestamp": self._ts(day, 11, 30), "latitude": 19.0761, "longitude": 72.8778},
        )
        await self._post(
            "spoof_close",
            {"professional_id": p, "timestamp": self._ts(day, 11, 55), "latitude": 28.7041, "longitude": 77.1025},
        )

    async def _send_gps_gap_stay(self, day: datetime) -> None:
        p = "SIM_GAP"
        base_lat, base_lon = 28.6139, 77.2090
        await self._post(
            "gap_1",
            {"professional_id": p, "timestamp": self._ts(day, 9, 0), "latitude": base_lat, "longitude": base_lon},
        )
        await self._post(
            "gap_2",
            {"professional_id": p, "timestamp": self._ts(day, 12, 0), "latitude": base_lat + 0.00001, "longitude": base_lon + 0.00001},
        )
        await self._post(
            "gap_3",
            {"professional_id": p, "timestamp": self._ts(day, 12, 20), "latitude": base_lat + 0.00002, "longitude": base_lon + 0.00002},
        )
        await self._post(
            "gap_close",
            {"professional_id": p, "timestamp": self._ts(day, 12, 50), "latitude": 28.7041, "longitude": 77.1025},
        )

    async def _send_suspicious_candidate(self, day: datetime) -> None:
        # SIM_PRO has a deterministic reference booking seeded by processing-service.
        p = "SIM_PRO"
        ref_lat, ref_lon = 28.6139, 77.2090
        await self._post(
            "suspicious_1",
            {"professional_id": p, "timestamp": self._ts(day, 14, 0), "latitude": ref_lat, "longitude": ref_lon},
        )
        await self._post(
            "suspicious_2",
            {"professional_id": p, "timestamp": self._ts(day, 14, 10), "latitude": ref_lat + 0.00001, "longitude": ref_lon + 0.00001},
        )
        await self._post(
            "suspicious_3",
            {"professional_id": p, "timestamp": self._ts(day, 14, 25), "latitude": ref_lat + 0.00002, "longitude": ref_lon + 0.00002},
        )
        await self._post(
            "suspicious_close",
            {"professional_id": p, "timestamp": self._ts(day, 15, 0), "latitude": 28.7041, "longitude": 77.1025},
        )

    async def run_forever(self) -> None:
        while True:
            day = datetime.now(timezone.utc) + timedelta(days=self._day_cursor)
            self._day_cursor += 1
            logger.info("Starting simulator cycle for utc_date=%s", day.date().isoformat())
            try:
                await self._send_invalid_payload(day)
                await self._send_normal_stay(day)
                await self._send_spoofing_stay(day)
                await self._send_gps_gap_stay(day)
                await self._send_suspicious_candidate(day)
            except Exception as err:
                logger.exception("Simulator cycle failed: %s", err)
            logger.info("Completed simulator cycle for utc_date=%s; continuing immediately", day.date().isoformat())

    async def close(self) -> None:
        await self._client.aclose()


async def _main() -> None:
    simulator = PingSimulator()
    try:
        await simulator.run_forever()
    finally:
        await simulator.close()


if __name__ == "__main__":
    asyncio.run(_main())
