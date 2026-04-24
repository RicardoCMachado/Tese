"""
Serviço para determinação de localidades
"""
import pandas as pd
import math
from typing import Optional
from geopy.geocoders import Nominatim
from ..models.alert import Coordinates, Location, ServerConfig
import logging

logger = logging.getLogger(__name__)


class LocationService:
    """Serviço para determinar localidade de um alerta"""
    
    def __init__(self, config: ServerConfig):
        self.config = config
        self.localities_data = []
        self._load_localities()
        # THREAD SAFETY: Não criar geocoder aqui - será criado por thread
        self.user_agent = 'FireTec_Server'
    
    def _load_localities(self):
        """Carrega base de dados de localidades"""
        try:
            data = pd.read_csv(self.config.localities_csv)
            
            self.localities_data = []
            for _, row in data.iterrows():
                self.localities_data.append({
                    'longitude': float(row['Longitude']),
                    'latitude': float(row['Latitude']),
                    'freguesia': str(row['Freguesia']),
                    'concelho': str(row['Concelho']),
                    'distrito': str(row['Distrito'])
                })
            
            logger.info(f"Carregadas {len(self.localities_data)} localidades")
        
        except Exception as e:
            logger.error(f"Erro ao carregar localidades: {e}")
            raise
    
    def find_location(self, coordinates: Coordinates) -> Location:
        """
        Determina localidade do alerta
        
        Tenta primeiro usar geocoding reverso (Nominatim),
        se falhar usa a base de dados local por proximidade
        
        Args:
            coordinates: Coordenadas do alerta
        
        Returns:
            Informação da localidade
        """
        logger.info(f"Determinando localidade para {coordinates}")
        
        # Tentar geocoding reverso
        try:
            location = self._try_reverse_geocoding(coordinates)
            if location:
                logger.info(f"Localidade encontrada (geocoding): {location}")
                return location
        except Exception as e:
            logger.warning(f"Geocoding falhou: {e}")
        
        # Fallback: usar base de dados local
        location = self._find_nearest_locality(coordinates)
        logger.info(f"Localidade encontrada (proximidade): {location}")
        return location
    
    def _try_reverse_geocoding(self, coordinates: Coordinates) -> Optional[Location]:
        """
        Tenta obter localidade via geocoding reverso (Nominatim)
        THREAD SAFETY: Criar novo geocoder por requisição (Nominatim não é thread-safe)
        """
        try:
            # CRITICAL FIX: Criar geocoder por thread para evitar race conditions
            geocoder = Nominatim(user_agent=self.user_agent)
            result = geocoder.reverse(
                (coordinates.latitude, coordinates.longitude),
                timeout=5  # Reduzido de 10s para 5s
            )
            
            if not result:
                return None
            
            # Parsear endereço
            address_parts = result.address.split(',')
            
            # Verificar se tem código postal
            has_postal = any(char.isdigit() for char in address_parts[-2])
            
            if has_postal:
                if len(address_parts) >= 5:
                    freguesia = address_parts[-5].strip()
                    concelho = address_parts[-4].strip()
                    distrito = address_parts[-3].strip()
                else:
                    return None
            else:
                if len(address_parts) >= 4:
                    freguesia = address_parts[-4].strip()
                    concelho = address_parts[-3].strip()
                    distrito = address_parts[-2].strip()
                else:
                    return None
            
            return Location(
                freguesia=freguesia,
                concelho=concelho,
                distrito=distrito,
                coordinates=coordinates
            )
        
        except Exception as e:
            logger.debug(f"Erro no geocoding: {e}")
            return None
    
    def _find_nearest_locality(self, coordinates: Coordinates) -> Location:
        """
        Encontra localidade mais próxima na base de dados local
        """
        min_distance = float('inf')
        nearest = None
        
        lat_rad = math.radians(coordinates.latitude)
        lon_rad = math.radians(coordinates.longitude)
        
        for locality in self.localities_data:
            lat_loc_rad = math.radians(locality['latitude'])
            lon_loc_rad = math.radians(locality['longitude'])
            
            # Fórmula de Haversine
            distance = 6372795.477 * math.acos(
                math.sin(lat_rad) * math.sin(lat_loc_rad) +
                math.cos(lat_rad) * math.cos(lat_loc_rad) *
                math.cos(lon_rad - lon_loc_rad)
            )
            
            if distance < min_distance:
                min_distance = distance
                nearest = locality
        
        if nearest is None:
            raise ValueError("Nenhuma localidade encontrada")
        
        logger.debug(f"Localidade mais próxima a {min_distance:.0f}m")
        
        return Location(
            freguesia=nearest['freguesia'],
            concelho=nearest['concelho'],
            distrito=nearest['distrito'],
            coordinates=Coordinates(
                latitude=nearest['latitude'],
                longitude=nearest['longitude']
            )
        )
    
    def generate_alert_message(
        self,
        location: Location,
        roads: list = None
    ) -> str:
        """
        Gera mensagem de alerta textual
        
        Args:
            location: Localidade do alerta
            roads: Lista de estradas próximas (opcional)
        
        Returns:
            Mensagem de alerta formatada
        """
        message = (
            f"Alerta de Incêndio na Freguesia de {location.freguesia}, "
            f"no Concelho de {location.concelho}, "
            f"no Distrito de {location.distrito}"
        )
        
        if roads and len(roads) > 0:
            road_names = [road.ref for road in roads]
            message += self._format_roads_warning(road_names)
        
        return message

    def _format_roads_warning(self, road_names: list) -> str:
        roads_text = ", ".join(road_names)
        return f", cuidado ao circular na estrada {roads_text}"
