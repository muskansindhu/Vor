from datetime import datetime
from typing import Optional
from sqlalchemy import func

from shared.config import Config

from shared.models import Stay, SuspiciousVisit



class RiskScorer:
    def __init__(self, db) -> None:
        self.db = db

    def score(
        self,
        professional_id: str,
        customer_id: str,
        booking_id: str,
        category: str,
        stay_start: datetime,
        lat: float,
        lon: float,
        duration_min: float,
        cluster: str,
        home_cluster: Optional[str],
        gps_gap: bool,
        spoofing: bool,
    ) -> SuspiciousVisit:
        risk = 0
        reasons: list[str] = []

        risk += Config.RISK_WEIGHTS["repeat_window"]
        reasons.append("Visit occurred within expected repeat window")

        risk += Config.RISK_WEIGHTS["unmatched_near_past"]
        reasons.append("Unmatched visit near prior service location")

        if duration_min >= 30:
            risk += Config.RISK_WEIGHTS["long_duration"]
            reasons.append("Long duration stay")

        if gps_gap:
            risk += Config.RISK_WEIGHTS["gps_gap"]
            reasons.append("GPS gaps during working hours")

        if spoofing:
            risk += Config.RISK_WEIGHTS["spoofing"]
            reasons.append("Possible GPS spoofing detected")

        existing = (
            self.db.query(SuspiciousVisit)
            .filter(
                SuspiciousVisit.professional_id == professional_id,
                SuspiciousVisit.reference_booking_id == booking_id,
            )
            .count()
        )
        if existing >= 1:
            risk += Config.RISK_WEIGHTS["repeated_unmatched"]
            reasons.append("Repeated unmatched visit near prior service location")

        top_clusters = (
            self.db.query(Stay.cluster_key, func.count(Stay.id).label("cnt"))
            .filter(Stay.professional_id == professional_id)
            .group_by(Stay.cluster_key)
            .order_by(func.count(Stay.id).desc())
            .limit(3)
            .all()
        )
        if any(cluster == row[0] for row in top_clusters):
            risk += Config.RISK_WEIGHTS["normal_area"]
            reasons.append("Visit within normal operating area")

        distinct_customers = (
            self.db.query(func.count(func.distinct(SuspiciousVisit.customer_id)))
            .filter(SuspiciousVisit.professional_id == professional_id)
            .scalar()
            or 0
        )
        if distinct_customers >= 2:
            risk += Config.RISK_WEIGHTS["multiple_customers"]
            reasons.append("Multiple customers with suspicious visits")

        return SuspiciousVisit(
            professional_id=professional_id,
            customer_id=customer_id,
            reference_booking_id=booking_id,
            category=category,
            suspicious_visit_time=stay_start,
            visit_latitude=lat,
            visit_longitude=lon,
            visit_duration_minutes=duration_min,
            risk_score=max(0, int(risk)),
            flagged=risk >= 7,
            reason="; ".join(reasons),
            cluster_key=cluster,
        )
