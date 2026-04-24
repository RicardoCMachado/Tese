"""Configuração central do servidor FireTec."""
from dataclasses import dataclass, field
from typing import List


@dataclass
class ServerConfig:
    antenna_csv: str = "123.csv"
    localities_csv: str = "Localidades_Portugal.csv"

    initial_search_radius: float = 7.0
    radius_increment: float = 2.0
    min_antennas: int = 5

    initial_road_radius: int = 2000
    road_radius_increment: int = 500
    min_roads: int = 1
    enable_overpass: bool = True

    switch_ips: List[str] = field(default_factory=lambda: ["192.168.0.22", "192.168.0.21"])
    switch_port: int = 8080

    max_workers: int = 5
    queue_size: int = 100

    enable_cap: bool = True
    simulation_mode: bool = False

    log_level: str = "INFO"
    log_file: str = "logs/firetec.log"

    # endpoints de fallback Overpass
    overpass_endpoints: List[str] = field(
        default_factory=lambda: [
            "https://overpass-api.de/api/interpreter",
            "https://lz4.overpass-api.de/api/interpreter",
            "https://overpass.kumi.systems/api/interpreter",
        ]
    )
