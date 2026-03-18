import os


class Config:
    STAY_RADIUS_M = 75.0
    STAY_MIN_MINUTES = 15
    STAY_MAX_GAP_MINUTES = 30
    MATCH_DISTANCE_M = 100.0
    CLUSTER_RADIUS_M = 30.0
    BOOKING_TIME_WINDOW_HOURS = 2
    SPOOFING_SPEED_KMPH = 200.0
    GPS_GAP_HOURS = 2

    REPEAT_SERVICE_CATEGORIES = [
        "home_cleaning",
        "salon_at_home",
        "massage_therapy",
        "ac_servicing",
        "plumbing",
        "electrical",
    ]

    REPEAT_CATEGORY_WINDOWS = {
        "home_cleaning": {"min_days": 5, "max_days": 30},
        "salon_at_home": {"min_days": 10, "max_days": 45},
        "massage_therapy": {"min_days": 7, "max_days": 30},
        "ac_servicing": {"min_days": 60, "max_days": 180},
        "plumbing": {"min_days": 30, "max_days": 180},
        "electrical": {"min_days": 30, "max_days": 180},
    }

    RISK_WEIGHTS = {
        "repeat_window": 3,
        "unmatched_near_past": 3,
        "repeated_unmatched": 5,
        "long_duration": 2,
        "multiple_customers": 4,
        "gps_gap": 2,
        "spoofing": 4,
        "normal_area": -2,
    }

    ONE_TIME_CATEGORIES = ["pest_control", "sofa_cleaning", "appliance_install"]

    KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
    KAFKA_PINGS_TOPIC = os.getenv("KAFKA_PINGS_TOPIC", "gps-pings")
    KAFKA_CONSUMER_GROUP = os.getenv("KAFKA_CONSUMER_GROUP", "vor-processing")
    KAFKA_ALERTS_TOPIC = os.getenv("KAFKA_ALERTS_TOPIC", "suspicious-visits")
