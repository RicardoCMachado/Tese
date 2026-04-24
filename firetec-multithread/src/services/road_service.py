"""
Local road lookup service.

Runtime is fully offline: roads are read from CSV files generated from an
OpenStreetMap extract.
"""
import csv
import math
import re
import threading
from pathlib import Path
from typing import Dict, List, Tuple

from ..models.alert import Coordinates, Road, ServerConfig
import logging

logger = logging.getLogger(__name__)


class RoadService:
    """Find nearby roads using local CSV data only."""

    _cache = {}
    _cache_lock = threading.Lock()

    def __init__(self, config: ServerConfig):
        self.config = config
        self.cell_size = config.road_grid_cell_degrees
        self.road_points: List[dict] = []
        self.grid_index: Dict[Tuple[int, int], List[int]] = {}
        self.override_points = self._load_road_overrides()
        self._load_road_points()

    def find_nearby_roads(
        self,
        coordinates: Coordinates,
        min_roads: int = None
    ) -> List[Road]:
        """
        Find nearby roads from local CSV data.

        The search starts with config.initial_road_radius and expands until
        min_roads is reached or config.max_road_radius is exceeded.
        """
        if min_roads is None:
            min_roads = self.config.min_roads

        cache_key = self._cache_key(coordinates, min_roads)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        search_radius = self.config.initial_road_radius
        roads: List[Road] = []

        while search_radius <= self.config.max_road_radius:
            roads = self._merge_unique_roads(
                self._find_csv_roads(coordinates, search_radius),
                self._find_override_roads(coordinates)
            )

            if len(roads) >= min_roads:
                break

            search_radius += self.config.road_radius_increment

        if not roads:
            logger.warning(
                "Nenhuma estrada encontrada no CSV local para %s", coordinates
            )
        else:
            logger.info(
                "Estradas encontradas no CSV local para %s: %s",
                coordinates,
                ", ".join(road.ref for road in roads)
            )

        roads = roads[:self.config.max_roads_returned]
        self._set_cached(cache_key, roads)
        return roads

    def _load_road_points(self):
        path = Path(self.config.roads_csv)
        if not path.exists():
            logger.warning(
                "Ficheiro de estradas '%s' nao encontrado. "
                "O sistema vai usar apenas road_overrides.csv.",
                path
            )
            return

        try:
            with path.open("r", encoding="utf-8", newline="") as csv_file:
                reader = csv.DictReader(csv_file)
                for row in reader:
                    point = self._parse_road_point(row)
                    if point is None:
                        continue

                    index = len(self.road_points)
                    self.road_points.append(point)
                    cell = self._cell_for(point["latitude"], point["longitude"])
                    self.grid_index.setdefault(cell, []).append(index)

            logger.info(
                "Carregados %s pontos de estradas de %s",
                len(self.road_points),
                path
            )
        except Exception as e:
            logger.error("Erro ao carregar CSV de estradas: %s", e, exc_info=True)

    def _parse_road_point(self, row: dict):
        ref = (row.get("ref") or "").strip()
        name = (row.get("name") or "").strip()
        highway = row.get("highway") or "unknown"
        if not ref and not name:
            return None

        try:
            latitude = float(row.get("latitude") or row.get("lat"))
            longitude = float(row.get("longitude") or row.get("lon"))
        except (TypeError, ValueError):
            return None

        return {
            "road_id": row.get("road_id") or row.get("id") or ref or name,
            "raw_ref": ref,
            "raw_name": name,
            "highway": highway,
            "latitude": latitude,
            "longitude": longitude
        }

    def _format_road_label(self, ref: str, name: str, highway: str) -> str:
        refs = self._split_refs(ref)
        motorway_ref = self._first_matching_ref(refs, r"^A[\s.-]*\d+")
        national_ref = self._first_matching_ref(refs, r"^(EN|E\.N\.)[\s.-]*\d+")
        main_itinerary_ref = self._first_matching_ref(refs, r"^IP[\s.-]*\d+")
        complementary_itinerary_ref = self._first_matching_ref(refs, r"^IC[\s.-]*\d+")

        if motorway_ref:
            return self._compact_ref(motorway_ref)

        if national_ref:
            return self._compact_ref(national_ref).replace("E.N.", "EN")

        if main_itinerary_ref:
            return self._compact_ref(main_itinerary_ref)

        if complementary_itinerary_ref:
            return self._compact_ref(complementary_itinerary_ref)

        if name:
            return name

        return self._compact_ref(ref) if ref else ""

    def _ref_lookup_key(self, ref: str) -> str:
        return re.sub(r"\s+", "", ref.strip()).upper()

    def _split_refs(self, ref: str) -> List[str]:
        return [
            item.strip()
            for item in re.split(r"[;,/]", ref or "")
            if item.strip()
        ]

    def _first_matching_ref(self, refs: List[str], pattern: str) -> str:
        for ref in refs:
            if re.match(pattern, ref, flags=re.IGNORECASE):
                return ref
        return ""

    def _compact_ref(self, ref: str) -> str:
        return re.sub(r"\s+", "", ref.strip()).upper()

    def _load_road_overrides(self) -> List[dict]:
        path = Path(self.config.road_overrides_csv)
        if not path.exists():
            return []

        overrides = []
        try:
            with path.open("r", encoding="utf-8", newline="") as csv_file:
                reader = csv.DictReader(csv_file)
                for row in reader:
                    road_names = [
                        road.strip()
                        for road in row.get("roads", "").split(";")
                        if road.strip()
                    ]
                    if not road_names:
                        continue

                    overrides.append({
                        "latitude": float(row["latitude"]),
                        "longitude": float(row["longitude"]),
                        "radius_m": float(row.get("radius_m") or 1500),
                        "roads": road_names
                    })

            logger.info(
                "Carregados %s pontos manuais de estradas", len(overrides)
            )
        except Exception as e:
            logger.warning("Erro ao carregar road_overrides.csv: %s", e)

        return overrides

    def _find_override_roads(self, coordinates: Coordinates) -> List[Road]:
        roads = []
        for override in self.override_points:
            distance = self._distance_meters(
                coordinates.latitude,
                coordinates.longitude,
                override["latitude"],
                override["longitude"]
            )

            if distance > override["radius_m"]:
                continue

            for road_name in override["roads"]:
                roads.append(Road(ref=road_name, highway_type="local_override"))

        return roads

    def _find_csv_roads(self, coordinates: Coordinates, radius_m: int) -> List[Road]:
        if not self.road_points:
            return []

        candidates = self._candidate_points(coordinates, radius_m)
        nearest_by_road = {}

        for point in candidates:
            distance = self._distance_meters(
                coordinates.latitude,
                coordinates.longitude,
                point["latitude"],
                point["longitude"]
            )
            if distance > radius_m:
                continue

            key = self._road_group_key(point)
            current = nearest_by_road.setdefault(key, {
                "distance": float("inf"),
                "name_distance": float("inf"),
                "ref": point["raw_ref"],
                "name": point["raw_name"],
                "nearest_name": "",
                "highway": point["highway"],
            })

            if distance < current["distance"]:
                current["distance"] = distance
                current["ref"] = point["raw_ref"]
                current["name"] = point["raw_name"]
                current["highway"] = point["highway"]

            if point["raw_name"] and distance < current["name_distance"]:
                current["name_distance"] = distance
                current["nearest_name"] = point["raw_name"]

        ordered = sorted(nearest_by_road.values(), key=lambda item: item["distance"])
        roads = []
        for item in ordered:
            label = self._format_road_label(
                item["ref"],
                item["nearest_name"] or item["name"],
                item["highway"]
            )
            if label:
                roads.append(Road(ref=label, highway_type=item["highway"]))
        return roads

    def _road_group_key(self, point: dict) -> str:
        if point["raw_ref"]:
            return f"ref:{self._ref_lookup_key(point['raw_ref'])}"
        return f"name:{point['raw_name'].strip().lower()}"

    def _candidate_points(self, coordinates: Coordinates, radius_m: int) -> List[dict]:
        lat_radius = radius_m / 111_320
        cos_lat = max(abs(math.cos(math.radians(coordinates.latitude))), 0.01)
        lon_radius = radius_m / (111_320 * cos_lat)

        min_cell = self._cell_for(
            coordinates.latitude - lat_radius,
            coordinates.longitude - lon_radius
        )
        max_cell = self._cell_for(
            coordinates.latitude + lat_radius,
            coordinates.longitude + lon_radius
        )

        points = []
        for lat_cell in range(min_cell[0], max_cell[0] + 1):
            for lon_cell in range(min_cell[1], max_cell[1] + 1):
                for index in self.grid_index.get((lat_cell, lon_cell), []):
                    points.append(self.road_points[index])

        return points

    def _merge_unique_roads(self, *road_lists: List[Road]) -> List[Road]:
        roads = []
        seen = set()
        for road_list in road_lists:
            for road in road_list:
                if road.ref in seen:
                    continue
                roads.append(road)
                seen.add(road.ref)
        return roads

    def _cell_for(self, latitude: float, longitude: float) -> Tuple[int, int]:
        return (
            math.floor(latitude / self.cell_size),
            math.floor(longitude / self.cell_size)
        )

    def _distance_meters(
        self,
        lat1: float,
        lon1: float,
        lat2: float,
        lon2: float
    ) -> float:
        radius_m = 6_371_000
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_phi / 2) ** 2 +
            math.cos(phi1) * math.cos(phi2) *
            math.sin(delta_lambda / 2) ** 2
        )
        return radius_m * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def _cache_key(self, coordinates: Coordinates, min_roads: int):
        return (
            round(coordinates.latitude, 4),
            round(coordinates.longitude, 4),
            min_roads
        )

    def _get_cached(self, cache_key):
        with self._cache_lock:
            cached = self._cache.get(cache_key)
            if cached is None:
                return None
            return list(cached)

    def _set_cached(self, cache_key, roads: List[Road]):
        with self._cache_lock:
            self._cache[cache_key] = list(roads)

    def format_roads_list(self, roads: List[Road]) -> str:
        if not roads:
            return ""
        return ", ".join([road.ref for road in roads])
