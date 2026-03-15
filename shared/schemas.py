from pydantic import BaseModel, Field


class GPSData(BaseModel):
    professor_id: str = Field(..., min_length=1)
    timestamp: int = Field(..., description="Unix timestamp in seconds")
    latitude: float 
    longitude: float
