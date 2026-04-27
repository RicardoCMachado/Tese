"""
Modelos de dados para o sistema FireTec
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from datetime import datetime
from enum import Enum


class AlertStatus(Enum):
    """Estados possíveis de um alerta"""
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    SENT = "sent"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AlertPriority(Enum):
    """Prioridade do alerta"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Coordinates:
    """Coordenadas geográficas"""
    latitude: float
    longitude: float

    def __str__(self) -> str:
        return f"({self.latitude}, {self.longitude})"

    def to_tuple(self) -> Tuple[float, float]:
        return (self.latitude, self.longitude)


@dataclass
class RadioStation:
    """Estação de rádio FM"""
    ps: str  # Program Service
    pi: str  # Program Identification
    frequency: float  # MHz
    latitude: float
    longitude: float
    coverage_radius: float  # km
    concelho: str
    distrito: str

    def __hash__(self):
        return hash((self.ps, self.pi, self.frequency))

    def __eq__(self, other):
        if not isinstance(other, RadioStation):
            return False
        return (self.ps == other.ps and
                self.pi == other.pi and
                self.frequency == other.frequency)


@dataclass
class Location:
    """Informação de localidade"""
    freguesia: str
    concelho: str
    distrito: str
    coordinates: Coordinates

    def __str__(self) -> str:
        return f"{self.freguesia}, {self.concelho}, {self.distrito}"


@dataclass
class Road:
    """Estrada próxima do alerta"""
    ref: str  # Referência da estrada (ex: "A1", "N1")
    highway_type: str  # motorway, trunk, primary, etc.

    def __str__(self) -> str:
        return self.ref


@dataclass
class FireAlert:
    """Alerta de incêndio"""
    alert_id: str
    coordinates: Coordinates
    timestamp: datetime = field(default_factory=datetime.now)
    priority: AlertPriority = AlertPriority.NORMAL
    status: AlertStatus = AlertStatus.PENDING

    # Dados processados
    location: Optional[Location] = None
    nearby_stations: List[RadioStation] = field(default_factory=list)
    nearby_roads: List[Road] = field(default_factory=list)
    message_text: Optional[str] = None
    audio_file: Optional[str] = None
    kml_file: Optional[str] = None
    transmission_results: Dict[str, dict] = field(default_factory=dict)

    # Metadados
    queue_wait_time: Optional[float] = None  # segundos na fila antes de processar
    processing_time: Optional[float] = None  # segundos
    error_message: Optional[str] = None

    def __str__(self) -> str:
        return (f"Alert {self.alert_id}: {self.coordinates} "
                f"[{self.status.value}] - {self.timestamp.strftime('%H:%M:%S')}")

    def get_frequencies(self) -> List[float]:
        """Retorna lista de frequências das estações próximas"""
        return list(set([station.frequency for station in self.nearby_stations]))

    def get_ps_list(self) -> List[str]:
        """Retorna lista de PS das estações próximas"""
        return list(set([station.ps for station in self.nearby_stations]))


@dataclass
class ServerConfig:
    """Configuração do servidor"""
    # Dados
    antenna_csv: str = "123.csv"
    localities_csv: str = "Localidades_Portugal.csv"

    # Antenas
    initial_search_radius: float = 7.0  # km
    radius_increment: float = 2.0  # km
    min_antennas: int = 5

    # Estradas
    initial_road_radius: int = 2000  # metros
    road_radius_increment: int = 500  # metros
    max_road_radius: int = 6000  # metros
    min_roads: int = 1
    max_roads_returned: int = 5
    roads_csv: str = "data/roads_portugal.csv"
    road_overrides_csv: str = "data/road_overrides.csv"
    road_grid_cell_degrees: float = 0.05

    # Áudio
    audio_language: str = "pt"
    audio_sample_rate: int = 32000
    audio_bit_depth: int = 1

    # Protocolo FireTec legado (igual ao script do Rodolfo)
    rds_ps: str = "FIRETEC1"
    rds_pi: str = "8400"
    lab_frequencies: List[float] = field(default_factory=lambda: [100.0, 102.0])

    # FireTec Switches
    hardware_enabled: bool = False
    switch_ips: List[str] = field(default_factory=lambda: ["192.168.0.22", "192.168.0.21"])
    switch_port: int = 8080

    # Threading
    max_workers: int = 10
    queue_size: int = 100

    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/firetec.log"


@dataclass
class ProcessingMetrics:
    """Métricas de processamento"""
    alert_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None

    # Tempos parciais
    antenna_search_time: Optional[float] = None
    location_search_time: Optional[float] = None
    road_search_time: Optional[float] = None
    audio_generation_time: Optional[float] = None
    transmission_time: Optional[float] = None

    def mark_complete(self):
        """Marca processamento como completo e calcula duração"""
        self.end_time = datetime.now()
        self.duration = (self.end_time - self.start_time).total_seconds()
