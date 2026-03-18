from datetime import datetime, timezone
from typing import Dict, Optional

from shared.config import Config
from shared.db import SessionLocal
from shared.geo import cluster_key, haversine_m
from shared.models import Professional, Stay

from .risk_scorer import RiskScorer
from .stay_detector import StayDetector
from .visit_analyzer import VisitAnalyzer


class ProcessingPipeline:
    def __init__(self) -> None:
        self._detector = StayDetector()
        self._last_ping: Dict[str, dict] = {}
        self._spoofing_flag: Dict[str, bool] = {}
        self._gps_gap_flag: Dict[str, bool] = {}
        self._home_counts: Dict[str, Dict[str, int]] = {}

    async def _handle_ping(self, ping_data: dict) -> Optional[dict]:
        professional_id = ping_data["professional_id"]
        ts_raw = ping_data["timestamp"]
        if isinstance(ts_raw, (int, float)):
            ts = datetime.fromtimestamp(ts_raw, tz=timezone.utc)
        elif isinstance(ts_raw, str):
            ts_str = ts_raw.strip()
            if ts_str.isdigit():
                ts = datetime.fromtimestamp(int(ts_str), tz=timezone.utc)
            else:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        else:
            raise ValueError("timestamp must be ISO 8601 string or Unix seconds")

        # Normalize to naive UTC to keep comparisons consistent with seeded data.
        if ts.tzinfo is not None:
            ts = ts.astimezone(timezone.utc).replace(tzinfo=None)
        lat = ping_data["latitude"]
        lon = ping_data["longitude"]

        self._update_flags(professional_id, ts, lat, lon)
        self._update_home_cluster(professional_id, ts, lat, lon)

        completed = self._detector.update(professional_id, ts, lat, lon)
        if completed is None:
            return None

        duration_min = (completed.last_time - completed.start_time).total_seconds() / 60.0
        if duration_min < Config.STAY_MIN_MINUTES:
            return None

        home_cluster_key = self._get_home_cluster(professional_id)
        stay_cluster = cluster_key(completed.lat, completed.lon)

        db = SessionLocal()
        try:
            db.add(
                Stay(
                    professional_id=professional_id,
                    start_time=completed.start_time,
                    end_time=completed.last_time,
                    latitude=completed.lat,
                    longitude=completed.lon,
                    duration_minutes=duration_min,
                    cluster_key=stay_cluster,
                    gps_gap_detected=self._gps_gap_flag.get(professional_id, False),
                    spoofing_detected=self._spoofing_flag.get(professional_id, False),
                    home_cluster_key=home_cluster_key,
                )
            )

            prof = db.get(Professional, professional_id)
            if prof is None:
                prof = Professional(professional_id=professional_id)
                db.add(prof)
            if home_cluster_key:
                prof.home_cluster_key = home_cluster_key

            analyzer = VisitAnalyzer(db)
            matched = analyzer.find_matching_booking(
                professional_id,
                completed.start_time,
                completed.lat,
                completed.lon,
            )
            if matched:
                db.commit()
                return None

            reference = analyzer.find_reference_booking(
                professional_id,
                completed.start_time,
                completed.lat,
                completed.lon,
            )
            if reference is None:
                db.commit()
                return None

            if not analyzer.within_repeat_window(reference, completed.start_time):
                db.commit()
                return None

            if home_cluster_key and home_cluster_key == stay_cluster:
                db.commit()
                return None

            scorer = RiskScorer(db)
            alert = scorer.score(
                professional_id=professional_id,
                customer_id=reference.customer_id,
                booking_id=reference.booking_id,
                category=reference.category,
                stay_start=completed.start_time,
                lat=completed.lat,
                lon=completed.lon,
                duration_min=duration_min,
                cluster=stay_cluster,
                home_cluster=home_cluster_key,
                gps_gap=self._gps_gap_flag.get(professional_id, False),
                spoofing=self._spoofing_flag.get(professional_id, False),
            )
            db.add(alert)
            db.commit()
            db.refresh(alert)
            return {
                "id": alert.id,
                "professional_id": alert.professional_id,
                "customer_id": alert.customer_id,
                "reference_booking_id": alert.reference_booking_id,
                "category": alert.category,
                "suspicious_visit_time": alert.suspicious_visit_time.isoformat(),
                "visit_latitude": alert.visit_latitude,
                "visit_longitude": alert.visit_longitude,
                "visit_duration_minutes": alert.visit_duration_minutes,
                "risk_score": alert.risk_score,
                "flagged": alert.flagged,
                "reason": alert.reason,
                "cluster_key": alert.cluster_key,
                "created_at": alert.created_at.isoformat() if alert.created_at else None,
            }

        finally:
            db.close()
        return None

    def _update_flags(self, professional_id: str, ts: datetime, lat: float, lon: float) -> None:
        prev = self._last_ping.get(professional_id)
        if prev is not None:
            dt_hours = (ts - prev["timestamp"]).total_seconds() / 3600.0
            if dt_hours > 0:
                dist_km = haversine_m(prev["latitude"], prev["longitude"], lat, lon) / 1000.0
                speed = dist_km / dt_hours
                if speed > Config.SPOOFING_SPEED_KMPH:
                    self._spoofing_flag[professional_id] = True

                if dt_hours >= Config.GPS_GAP_HOURS and 8 <= prev["timestamp"].hour <= 20:
                    self._gps_gap_flag[professional_id] = True

        self._last_ping[professional_id] = {"timestamp": ts, "latitude": lat, "longitude": lon}

    def _update_home_cluster(self, professional_id: str, ts: datetime, lat: float, lon: float) -> None:
        if ts.hour >= 22 or ts.hour < 6:
            key = cluster_key(lat, lon)
            self._home_counts.setdefault(professional_id, {})
            self._home_counts[professional_id][key] = self._home_counts[professional_id].get(key, 0) + 1

    def _get_home_cluster(self, professional_id: str) -> Optional[str]:
        counts = self._home_counts.get(professional_id, {})
        if not counts:
            return None
        return max(counts.items(), key=lambda kv: kv[1])[0]
