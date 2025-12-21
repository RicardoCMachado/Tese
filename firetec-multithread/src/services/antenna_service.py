"""
Serviço para gestão de antenas/estações de rádio FM
"""
import pandas as pd
import math
from typing import List, Tuple, Optional
from ..models.alert import Coordinates, RadioStation, ServerConfig
import logging

logger = logging.getLogger(__name__)


class AntennaService:
    """Serviço para procurar e gerir antenas de rádio FM"""
    
    def __init__(self, config: ServerConfig):
        self.config = config
        self.stations: List[RadioStation] = []
        self._load_stations()
    
    def _load_stations(self):
        """Carrega estações de rádio do ficheiro CSV"""
        try:
            data = pd.read_csv(self.config.antenna_csv)
            
            for _, row in data.iterrows():
                station = RadioStation(
                    ps=str(row["PS"]),
                    pi=str(row["PI"]),
                    frequency=float(row["Frequência [MHz]"]),
                    latitude=float(row["Latitude Corrigida"]),
                    longitude=float(row["Longitude Corrigida"]),
                    coverage_radius=float(row["Raio [Km]"]),
                    concelho=str(row["Concelho"]),
                    distrito=str(row["Distrito"])
                )
                self.stations.append(station)
            
            logger.info(f"Carregadas {len(self.stations)} estações de rádio")
        
        except Exception as e:
            logger.error(f"Erro ao carregar estações: {e}")
            raise
    
    def find_nearby_stations(
        self, 
        coordinates: Coordinates, 
        min_stations: Optional[int] = None
    ) -> List[RadioStation]:
        """
        Encontra estações próximas do ponto de alerta
        
        Args:
            coordinates: Coordenadas do alerta
            min_stations: Número mínimo de estações (default: config.min_antennas)
        
        Returns:
            Lista de estações próximas (sem duplicados de localização)
        """
        if min_stations is None:
            min_stations = self.config.min_antennas
        
        search_radius = self.config.initial_search_radius
        found_stations = []
        
        logger.info(f"Procurando antenas próximas a {coordinates}")
        
        while len(found_stations) < min_stations:
            # Converter km para graus (aproximado)
            radius_deg = search_radius / 111.11
            
            # Limites da área de busca
            lat_min = coordinates.latitude - radius_deg
            lat_max = coordinates.latitude + radius_deg
            lon_min = coordinates.longitude - radius_deg
            lon_max = coordinates.longitude + radius_deg
            
            # Buscar estações na área
            candidates = []
            for station in self.stations:
                if (lat_min <= station.latitude <= lat_max and
                    lon_min <= station.longitude <= lon_max):
                    candidates.append(station)
            
            # Remover duplicados de localização
            found_stations = self._remove_duplicates(candidates)
            
            logger.debug(
                f"Raio {search_radius:.1f}km: {len(found_stations)} estações únicas"
            )
            
            # Aumentar raio se necessário
            if len(found_stations) < min_stations:
                search_radius += self.config.radius_increment
                
                # Limite de segurança
                if search_radius > 100:
                    logger.warning(
                        f"Limite de raio atingido. Encontradas apenas "
                        f"{len(found_stations)} estações"
                    )
                    break
        
        logger.info(
            f"Encontradas {len(found_stations)} estações "
            f"(raio final: {search_radius:.1f}km)"
        )
        
        return found_stations[:min_stations]
    
    def _remove_duplicates(self, stations: List[RadioStation]) -> List[RadioStation]:
        """
        Remove estações duplicadas (mesma localização)
        Mantém apenas uma estação por localização física
        """
        unique = []
        seen_locations = set()
        
        for station in stations:
            location_key = (
                round(station.latitude, 6),
                round(station.longitude, 6)
            )
            
            if location_key not in seen_locations:
                unique.append(station)
                seen_locations.add(location_key)
        
        return unique
    
    def get_station_by_frequency(self, frequency: float) -> Optional[RadioStation]:
        """Retorna estação por frequência"""
        for station in self.stations:
            if abs(station.frequency - frequency) < 0.01:
                return station
        return None
    
    def calculate_distance(
        self, 
        coord1: Coordinates, 
        coord2: Coordinates
    ) -> float:
        """
        Calcula distância entre duas coordenadas (Haversine)
        
        Returns:
            Distância em km
        """
        R = 6371  # Raio da Terra em km
        
        lat1_rad = math.radians(coord1.latitude)
        lat2_rad = math.radians(coord2.latitude)
        delta_lat = math.radians(coord2.latitude - coord1.latitude)
        delta_lon = math.radians(coord2.longitude - coord1.longitude)
        
        a = (math.sin(delta_lat / 2) ** 2 +
             math.cos(lat1_rad) * math.cos(lat2_rad) *
             math.sin(delta_lon / 2) ** 2)
        
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
