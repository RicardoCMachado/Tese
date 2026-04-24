"""Modelos de domínio dos alertas FireTec."""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Tuple


class AlertStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    SENT = "sent"
    FAILED = "failed"


class AlertPriority(Enum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Coordinates:
    latitude: float
    longitude: float

    def __str__(self) -> str:
        return f"({self.latitude:.6f}, {self.longitude:.6f})"

    def to_tuple(self) -> Tuple[float, float]:
        return self.latitude, self.longitude


@dataclass
class RadioStation:
    ps: str
    pi: str
    frequency: float
    latitude: float
    longitude: float
    coverage_radius: float
    concelho: str = ""
    distrito: str = ""


@dataclass
class Location:
    freguesia: str
    concelho: str
    distrito: str
    coordinates: Coordinates

    def __str__(self) -> str:
        return f"{self.freguesia}, {self.concelho}, {self.distrito}"


@dataclass
class Road:
    ref: str
    highway_type: str


@dataclass
class ProcessingMetrics:
    alert_id: str
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    duration: Optional[float] = None

    antenna_search_time: float = 0.0
    location_search_time: float = 0.0
    road_search_time: float = 0.0
    audio_generation_time: float = 0.0
    transmission_time: float = 0.0
    switch_success_rate: float = 0.0

    def mark_complete(self) -> None:
        self.end_time = datetime.now()
        self.duration = (self.end_time - self.start_time).total_seconds()


@dataclass
class FireAlert:
    alert_id: str
    coordinates: Coordinates
    timestamp: datetime = field(default_factory=datetime.now)
    priority: AlertPriority = AlertPriority.NORMAL
    status: AlertStatus = AlertStatus.PENDING

    location: Optional[Location] = None
    nearby_stations: List[RadioStation] = field(default_factory=list)
    nearby_roads: List[Road] = field(default_factory=list)
    message_text: Optional[str] = None
    audio_file: Optional[str] = None
    cap_file: Optional[str] = None

    processing_time: Optional[float] = None
    error_message: Optional[str] = None
    metrics: Optional[ProcessingMetrics] = None
    transmission_results: Dict[str, Dict] = field(default_factory=dict)

    def get_frequencies(self) -> List[float]:
        return sorted({station.frequency for station in self.nearby_stations})

    def get_primary_station(self) -> Optional[RadioStation]:
        return self.nearby_stations[0] if self.nearby_stations else None
