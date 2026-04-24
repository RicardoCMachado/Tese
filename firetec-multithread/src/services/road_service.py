"""Serviço resiliente de consulta de estradas via Overpass."""
import logging
import threading
import time
from typing import Dict, List

import overpy

from ..models.alert import Coordinates, Road
from ..models.config import ServerConfig
from ..utils.validation import unique_preserve_order

logger = logging.getLogger(__name__)


class RoadService:
    def __init__(self, config: ServerConfig):
        self.config = config
        self._cache: Dict[str, List[Road]] = {}
        self._cache_lock = threading.Lock()

    def find_nearby_roads(self, coordinates: Coordinates, min_roads: int | None = None) -> List[Road]:
        if not self.config.enable_overpass:
            return []

        min_roads = min_roads or self.config.min_roads
        cache_key = f"{round(coordinates.latitude, 3)}:{round(coordinates.longitude, 3)}"

        with self._cache_lock:
            if cache_key in self._cache:
                return self._cache[cache_key]

        search_radius = self.config.initial_road_radius
        roads: List[Road] = []
        max_attempts = 6

        for attempt in range(1, max_attempts + 1):
            endpoint = self.config.overpass_endpoints[(attempt - 1) % len(self.config.overpass_endpoints)]
            try:
                roads = self._query_overpass(endpoint, coordinates, search_radius)
                if len(roads) >= min_roads:
                    break
                search_radius += self.config.road_radius_increment
            except Exception as exc:
                logger.warning(
                    "Overpass falhou tentativa %s/%s (%s): %s",
                    attempt,
                    max_attempts,
                    endpoint,
                    exc,
                )
                search_radius += self.config.road_radius_increment
                time.sleep(min(1.0 * attempt, 5.0))

        with self._cache_lock:
            self._cache[cache_key] = roads

        return roads

    @staticmethod
    def _query_overpass(endpoint: str, coordinates: Coordinates, radius: int) -> List[Road]:
        api = overpy.Overpass(url=endpoint)
        query = f"""[out:json][timeout:20];
        (
            way(around:{radius},{coordinates.latitude},{coordinates.longitude})
            [highway~\"^(motorway|trunk|primary|secondary|tertiary)$\"];
        );
        out body;"""
        result = api.query(query)

        refs = []
        roads: List[Road] = []
        for way in result.ways:
            ref = way.tags.get("ref") or way.tags.get("name")
            if not ref:
                continue
            refs.append(str(ref))

        for ref in unique_preserve_order(refs):
            roads.append(Road(ref=ref, highway_type="unknown"))

        return roads
