"""Serviço de estações/antenas FM."""
import logging
import math
from typing import List, Optional

import pandas as pd

from ..models.alert import Coordinates, RadioStation
from ..models.config import ServerConfig

logger = logging.getLogger(__name__)


class AntennaService:
    def __init__(self, config: ServerConfig):
        self.config = config
        self.stations: List[RadioStation] = []
        self._load_stations()

    def _load_stations(self) -> None:
        data = pd.read_csv(self.config.antenna_csv)
        stations: List[RadioStation] = []

        for _, row in data.iterrows():
            if not all(
                pd.notna(row.get(col))
                for col in [
                    "PS",
                    "PI",
                    "Frequência [MHz]",
                    "Latitude Corrigida",
                    "Longitude Corrigida",
                    "Raio [Km]",
                ]
            ):
                continue

            stations.append(
                RadioStation(
                    ps=str(row["PS"]),
                    pi=str(row["PI"]),
                    frequency=float(row["Frequência [MHz]"]),
                    latitude=float(row["Latitude Corrigida"]),
                    longitude=float(row["Longitude Corrigida"]),
                    coverage_radius=float(row["Raio [Km]"]),
                    concelho=str(row.get("Concelho", "")),
                    distrito=str(row.get("Distrito", "")),
                )
            )

        if not stations:
            raise ValueError("Sem estações válidas no CSV")

        self.stations = stations
        logger.info("Carregadas %s estações de rádio", len(self.stations))

    def find_nearby_stations(self, coordinates: Coordinates, min_stations: Optional[int] = None) -> List[RadioStation]:
        min_stations = min_stations or self.config.min_antennas
        search_radius = self.config.initial_search_radius
        found: List[RadioStation] = []

        while len(found) < min_stations and search_radius <= 100:
            radius_deg = search_radius / 111.11
            lat_min = coordinates.latitude - radius_deg
            lat_max = coordinates.latitude + radius_deg
            lon_min = coordinates.longitude - radius_deg
            lon_max = coordinates.longitude + radius_deg

            candidates = [
                station
                for station in self.stations
                if lat_min <= station.latitude <= lat_max and lon_min <= station.longitude <= lon_max
            ]
            found = self._dedupe_by_location(candidates)
            if len(found) < min_stations:
                search_radius += self.config.radius_increment

        return found[:min_stations]

    @staticmethod
    def _dedupe_by_location(stations: List[RadioStation]) -> List[RadioStation]:
        seen = set()
        unique = []
        for station in stations:
            key = (round(station.latitude, 6), round(station.longitude, 6))
            if key in seen:
                continue
            seen.add(key)
            unique.append(station)
        return unique

    @staticmethod
    def calculate_distance(coord1: Coordinates, coord2: Coordinates) -> float:
        r_km = 6371
        lat1 = math.radians(coord1.latitude)
        lat2 = math.radians(coord2.latitude)
        delta_lat = math.radians(coord2.latitude - coord1.latitude)
        delta_lon = math.radians(coord2.longitude - coord1.longitude)
        a = (
            math.sin(delta_lat / 2) ** 2
            + math.cos(lat1) * math.cos(lat2) * math.sin(delta_lon / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return r_km * c
