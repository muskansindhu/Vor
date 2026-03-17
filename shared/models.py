from datetime import datetime
from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

from .db import Base


class Professional(Base):
    __tablename__ = "professionals"

    professional_id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=True)
    home_cluster_key = Column(String(32), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Customer(Base):
    __tablename__ = "customers"

    customer_id = Column(String(64), primary_key=True, index=True)
    name = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Booking(Base):
    __tablename__ = "bookings"

    booking_id = Column(String(64), primary_key=True, index=True)
    professional_id = Column(String(64), index=True)
    customer_id = Column(String(64), index=True)
    category = Column(String(64), index=True)
    service_latitude = Column(Float, nullable=False)
    service_longitude = Column(Float, nullable=False)
    scheduled_time = Column(DateTime, nullable=False)
    completed_time = Column(DateTime, nullable=False)
    status = Column(String(32), nullable=False)


class Stay(Base):
    __tablename__ = "stays"

    id = Column(Integer, primary_key=True, autoincrement=True)
    professional_id = Column(String(64), index=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    duration_minutes = Column(Float, nullable=False)
    cluster_key = Column(String(32), index=True)
    gps_gap_detected = Column(Boolean, default=False)
    spoofing_detected = Column(Boolean, default=False)
    home_cluster_key = Column(String(32), nullable=True)


class SuspiciousVisit(Base):
    __tablename__ = "suspicious_visits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    professional_id = Column(String(64), index=True)
    customer_id = Column(String(64), index=True)
    reference_booking_id = Column(String(64), index=True)
    category = Column(String(64), index=True)
    suspicious_visit_time = Column(DateTime, nullable=False)
    visit_latitude = Column(Float, nullable=False)
    visit_longitude = Column(Float, nullable=False)
    visit_duration_minutes = Column(Float, nullable=False)
    risk_score = Column(Integer, nullable=False)
    flagged = Column(Boolean, default=False)
    reason = Column(Text, nullable=False)
    cluster_key = Column(String(32), index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
