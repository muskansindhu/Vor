from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import and_

from shared.config import Config

from shared.geo import haversine_m
from shared.models import Booking



class VisitAnalyzer:
    def __init__(self, db) -> None:
        self.db = db

    def find_matching_booking(self, professional_id: str, stay_start: datetime, lat: float, lon: float) -> Optional[Booking]:
        window = timedelta(hours=Config.BOOKING_TIME_WINDOW_HOURS)
        start = stay_start - window
        end = stay_start + window
        candidates = (
            self.db.query(Booking)
            .filter(
                and_(
                    Booking.professional_id == professional_id,
                    Booking.completed_time >= start,
                    Booking.completed_time <= end,
                )
            )
            .all()
        )
        for booking in candidates:
            dist = haversine_m(booking.service_latitude, booking.service_longitude, lat, lon)
            if dist <= Config.MATCH_DISTANCE_M:
                return booking
        return None

    def find_reference_booking(self, professional_id: str, stay_start: datetime, lat: float, lon: float) -> Optional[Booking]:
        candidates = (
            self.db.query(Booking)
            .filter(
                and_(
                    Booking.professional_id == professional_id,
                    Booking.category.in_(Config.REPEAT_SERVICE_CATEGORIES),
                    Booking.completed_time < stay_start,
                )
            )
            .order_by(Booking.completed_time.desc())
            .limit(25)
            .all()
        )
        closest = None
        closest_dist = None
        for booking in candidates:
            dist = haversine_m(booking.service_latitude, booking.service_longitude, lat, lon)
            if dist <= Config.CLUSTER_RADIUS_M:
                if closest is None or dist < closest_dist:
                    closest = booking
                    closest_dist = dist
        return closest

    def within_repeat_window(self, booking: Booking, stay_start: datetime) -> bool:
        window = Config.REPEAT_CATEGORY_WINDOWS.get(booking.category)
        if not window:
            return False
        days_since = (stay_start - booking.completed_time).days
        return window["min_days"] <= days_since <= window["max_days"]