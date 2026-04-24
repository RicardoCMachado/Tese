"""Serviço de geolocalização com fallback local."""
import logging
import math
from typing import List, Optional

import pandas as pd
from geopy.geocoders import Nominatim

from ..models.alert import Coordinates, Location, Road
from ..models.config import ServerConfig

logger = logging.getLogger(__name__)


class LocationService:
    def __init__(self, config: ServerConfig):
        self.config = config
        self.user_agent = "FireTec_Server"
        self.localities_data: List[dict] = []
        self._load_localities()

    def _load_localities(self) -> None:
        data = pd.read_csv(self.config.localities_csv)
        self.localities_data = [
            {
                "longitude": float(row["Longitude"]),
                "latitude": float(row["Latitude"]),
                "freguesia": str(row["Freguesia"]),
                "concelho": str(row["Concelho"]),
                "distrito": str(row["Distrito"]),
            }
            for _, row in data.iterrows()
        ]
        logger.info("Carregadas %s localidades", len(self.localities_data))

    def find_location(self, coordinates: Coordinates) -> Location:
        by_reverse = self._try_reverse_geocoding(coordinates)
        if by_reverse:
            return by_reverse
        return self._nearest_locality(coordinates)

    def _try_reverse_geocoding(self, coordinates: Coordinates) -> Optional[Location]:
        try:
            geocoder = Nominatim(user_agent=self.user_agent)
            result = geocoder.reverse((coordinates.latitude, coordinates.longitude), timeout=5)
            if not result:
                return None

            parts = [item.strip() for item in result.address.split(",")]
            if len(parts) < 4:
                return None

            # lógica semelhante à versão do Rodolfo, mas protegida
            has_postal = len(parts) >= 2 and any(ch.isdigit() for ch in parts[-2])
            if has_postal and len(parts) >= 5:
                freguesia, concelho, distrito = parts[-5], parts[-4], parts[-3]
            elif not has_postal and len(parts) >= 4:
                freguesia, concelho, distrito = parts[-4], parts[-3], parts[-2]
            else:
                return None

            return Location(
                freguesia=freguesia,
                concelho=concelho,
                distrito=distrito,
                coordinates=coordinates,
            )
        except Exception as exc:
            logger.warning("Reverse geocoding falhou: %s", exc)
            return None

    def _nearest_locality(self, coordinates: Coordinates) -> Location:
        lat_rad = math.radians(coordinates.latitude)
        lon_rad = math.radians(coordinates.longitude)

        nearest = None
        min_distance = float("inf")
        for locality in self.localities_data:
            lat_loc = math.radians(locality["latitude"])
            lon_loc = math.radians(locality["longitude"])
            cosine_arg = (
                math.sin(lat_rad) * math.sin(lat_loc)
                + math.cos(lat_rad) * math.cos(lat_loc) * math.cos(lon_rad - lon_loc)
            )
            cosine_arg = max(min(cosine_arg, 1.0), -1.0)
            distance = 6372795.477 * math.acos(cosine_arg)

            if distance < min_distance:
                min_distance = distance
                nearest = locality

        if nearest is None:
            return Location(
                freguesia="Desconhecida",
                concelho="Desconhecido",
                distrito="Desconhecido",
                coordinates=coordinates,
            )

        return Location(
            freguesia=nearest["freguesia"],
            concelho=nearest["concelho"],
            distrito=nearest["distrito"],
            coordinates=coordinates,
        )

    @staticmethod
    def generate_alert_message(location: Location, roads: Optional[List[Road]] = None) -> str:
        base = (
            f"Alerta de Incêndio na Freguesia de {location.freguesia}, "
            f"no Concelho de {location.concelho}, "
            f"no Distrito de {location.distrito}"
        )

        if roads:
            roads_text = ", ".join(road.ref for road in roads)
            return f"{base}, cuidado ao circular na estrada {roads_text}"

        return f"{base}. Evite circular na zona afetada."
