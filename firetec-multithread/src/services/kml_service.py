"""Serviço opcional para geração de KML de diagnóstico."""
from pathlib import Path
from typing import List

import simplekml

from ..models.alert import Coordinates, RadioStation


class KMLService:
    def __init__(self, output_dir: str = "kml"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_alert_map(self, alert_id: str, alert_coords: Coordinates, stations: List[RadioStation]) -> str:
        kml = simplekml.Kml()
        kml.newpoint(name="FIRE!", coords=[(alert_coords.longitude, alert_coords.latitude)])
        for station in stations:
            kml.newpoint(name=station.ps, coords=[(station.longitude, station.latitude)])
        path = self.output_dir / f"{alert_id}.kml"
        kml.save(str(path))
        return str(path)
