from datetime import datetime
from typing import Dict, Optional

from shared.config import Config

from shared.schemas import ClusterState
from shared.geo import haversine_m



class StayDetector:
    def __init__(self) -> None:
        self._clusters: Dict[str, ClusterState] = {}

    def update(self, professional_id: str, ts: datetime, lat: float, lon: float) -> Optional[ClusterState]:
        state = self._clusters.get(professional_id)
        if state is None:
            self._clusters[professional_id] = ClusterState(start_time=ts, last_time=ts, lat=lat, lon=lon, count=1)
            return None

        gap_min = (ts - state.last_time).total_seconds() / 60.0
        dist = haversine_m(state.lat, state.lon, lat, lon)

        if dist <= Config.STAY_RADIUS_M and gap_min <= Config.STAY_MAX_GAP_MINUTES:
            state.count += 1

            # Update the stay cluster center using a running average to smooth GPS noise.
            state.lat = (state.lat * (state.count - 1) + lat) / state.count
            state.lon = (state.lon * (state.count - 1) + lon) / state.count

            state.last_time = ts
            return None

        completed = state
        self._clusters[professional_id] = ClusterState(start_time=ts, last_time=ts, lat=lat, lon=lon, count=1)
        return completed