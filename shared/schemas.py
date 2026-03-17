from pydantic import BaseModel, Field
from datetime import datetime


class GPSData(BaseModel):
    professional_id: str = Field(..., min_length=1)
    timestamp: int = Field(..., description="Unix timestamp in seconds")
    latitude: float 
    longitude: float

class ClusterState(BaseModel):
    start_time: datetime
    last_time: datetime
    lat: float
    lon: float
    count: int
