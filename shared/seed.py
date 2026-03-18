from datetime import datetime, timedelta
import random

from shared.config import Config
from shared.models import Booking, Customer, Professional
from shared.db import SessionLocal

def _rand_coord(base_lat: float, base_lon: float, jitter: float = 0.002) -> tuple[float, float]:
    return (
        base_lat + random.uniform(-jitter, jitter),
        base_lon + random.uniform(-jitter, jitter),
    )

def seed_db(
    professionals: int = 5,
    customers: int = 12,
    bookings: int = 20,
    days_back: int = 120,
) -> None:

    db = SessionLocal()
    try:
        existing = db.query(Booking).count()
        if existing > 0:
            return

        random.seed(42)

        prof_ids = [f"P{idx+1}" for idx in range(professionals)]
        cust_ids = [f"C{idx+1}" for idx in range(customers)]

        for pid in prof_ids:
            db.add(Professional(professional_id=pid, name=f"Pro {pid}"))

        for cid in cust_ids:
            db.add(Customer(customer_id=cid, name=f"Customer {cid}"))

        base_lat, base_lon = 28.6139, 77.2090
        now = datetime.utcnow()

        category_pool = Config.REPEAT_SERVICE_CATEGORIES + Config.ONE_TIME_CATEGORIES
        for idx in range(bookings):
            booking_id = f"B{idx+1}"
            professional_id = random.choice(prof_ids)
            customer_id = random.choice(cust_ids)
            category = random.choice(category_pool)

            scheduled = now - timedelta(days=random.randint(5, days_back))
            completed = scheduled + timedelta(hours=1)
            lat, lon = _rand_coord(base_lat, base_lon, jitter=0.01)

            db.add(
                Booking(
                    booking_id=booking_id,
                    professional_id=professional_id,
                    customer_id=customer_id,
                    category=category,
                    service_latitude=lat,
                    service_longitude=lon,
                    scheduled_time=scheduled,
                    completed_time=completed,
                    status="completed",
                )
            )

        db.commit()
    finally:
        db.close()


def ensure_simulation_reference_booking(days_ago: int = 10) -> None:
    """
    Ensure a deterministic repeatable booking exists so simulator traffic can
    reliably trigger suspicious-visit flows.
    """
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        completed = now - timedelta(days=days_ago)
        scheduled = completed - timedelta(hours=1)

        professional_id = "SIM_PRO"
        customer_id = "SIM_CUST"
        booking_id = "B_SIM_REFERENCE"

        prof = db.get(Professional, professional_id)
        if prof is None:
            db.add(Professional(professional_id=professional_id, name="Simulator Professional"))

        customer = db.get(Customer, customer_id)
        if customer is None:
            db.add(Customer(customer_id=customer_id, name="Simulator Customer"))

        booking = db.get(Booking, booking_id)
        if booking is None:
            db.add(
                Booking(
                    booking_id=booking_id,
                    professional_id=professional_id,
                    customer_id=customer_id,
                    category="home_cleaning",
                    service_latitude=28.6139,
                    service_longitude=77.2090,
                    scheduled_time=scheduled,
                    completed_time=completed,
                    status="completed",
                )
            )
        else:
            booking.professional_id = professional_id
            booking.customer_id = customer_id
            booking.category = "home_cleaning"
            booking.service_latitude = 28.6139
            booking.service_longitude = 77.2090
            booking.scheduled_time = scheduled
            booking.completed_time = completed
            booking.status = "completed"

        db.commit()
    finally:
        db.close()
