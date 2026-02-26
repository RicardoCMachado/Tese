"""
Serviço para busca de estradas próximas
"""
import pandas as pd
import overpy
import time
from typing import List
from ..models.alert import Coordinates, Road, ServerConfig
import logging

logger = logging.getLogger(__name__)


class RoadService:
    """Serviço para encontrar estradas próximas do alerta"""
    
    def __init__(self, config: ServerConfig):
        self.config = config
        # THREAD SAFETY: Não criar API aqui - será criado por thread
        self.overpass_url = "https://overpass-api.de/api/interpreter"
    
    def find_nearby_roads(
        self,
        coordinates: Coordinates,
        min_roads: int = None
    ) -> List[Road]:
        """
        Encontra estradas principais próximas do alerta
        
        Args:
            coordinates: Coordenadas do alerta
            min_roads: Número mínimo de estradas (default: config.min_roads)
        
        Returns:
            Lista de estradas encontradas
        """
        if min_roads is None:
            min_roads = self.config.min_roads
        
        search_radius = self.config.initial_road_radius
        roads = []
        
        logger.info(f"Procurando estradas próximas a {coordinates}")
        
        # Limite de tentativas
        max_attempts = 10
        attempt = 0
        
        while len(roads) < min_roads and attempt < max_attempts:
            attempt += 1
            
            try:
                # Delay entre requisições para evitar "Too many requests"
                if attempt > 1:
                    time.sleep(5)  # Aguardar 5 segundos entre tentativas (aumentado)
                
                roads = self._query_overpass(coordinates, search_radius)
                
                logger.debug(
                    f"Raio {search_radius}m: {len(roads)} estradas encontradas"
                )
                
                if len(roads) < min_roads:
                    search_radius += self.config.road_radius_increment
            
            except Exception as e:
                error_msg = str(e).lower()
                if "server load too high" in error_msg or "rate limit" in error_msg or "too many requests" in error_msg:
                    logger.warning(
                        f"Overpass API sobrecarregada (tentativa {attempt}/{max_attempts}). "
                        f"Aguardando 10 segundos antes de retry..."
                    )
                    time.sleep(10)  # Aguardar 10 segundos em caso de rate limit
                    search_radius += self.config.road_radius_increment
                else:
                    logger.error(f"Erro ao consultar Overpass API: {e}")
                    search_radius += self.config.road_radius_increment
        
        if len(roads) == 0:
            logger.warning("Nenhuma estrada encontrada")
        else:
            logger.info(
                f"Encontradas {len(roads)} estradas "
                f"(raio final: {search_radius}m)"
            )
        
        return roads
    
    def _query_overpass(
        self,
        coordinates: Coordinates,
        radius: int
    ) -> List[Road]:
        """
        Consulta Overpass API para obter estradas
        
        Args:
            coordinates: Coordenadas do centro
            radius: Raio de busca em metros
        
        Returns:
            Lista de estradas
        """
        # THREAD SAFETY: Criar nova instância Overpass por requisição
        api = overpy.Overpass(url=self.overpass_url)
        
        # Query Overpass para estradas principais
        query = f"""(
            way
            (around:{radius},{coordinates.latitude},{coordinates.longitude})
            [highway~"^(motorway|trunk|primary|secondary|tertiary)$"];
        >;);out;"""
        
        result = api.query(query)
        
        # Extrair informação das estradas
        roads_data = []
        for way in result.ways:
            way.tags['id'] = way.id
            roads_data.append(way.tags)
        
        # Salvar temporariamente (para debug)
        if roads_data:
            df = pd.DataFrame(roads_data)
            # df.to_csv('temp_roads.csv')
        
        # Processar e remover duplicados
        return self._process_roads(roads_data)
    
    def _process_roads(self, roads_data: List[dict]) -> List[Road]:
        """
        Processa dados das estradas e remove duplicados
        
        Args:
            roads_data: Lista de dicionários com dados das estradas
        
        Returns:
            Lista de objetos Road únicos
        """
        unique_roads = {}
        
        for road_dict in roads_data:
            # Verificar se tem referência (nome da estrada)
            ref = road_dict.get('ref', None)
            
            if ref and pd.notna(ref):
                highway_type = road_dict.get('highway', 'unknown')
                
                # Usar ref como chave para evitar duplicados
                if ref not in unique_roads:
                    unique_roads[ref] = Road(
                        ref=str(ref),
                        highway_type=highway_type
                    )
        
        return list(unique_roads.values())
    
    def format_roads_list(self, roads: List[Road]) -> str:
        """
        Formata lista de estradas para mensagem
        
        Args:
            roads: Lista de estradas
        
        Returns:
            String formatada com nomes das estradas
        """
        if not roads:
            return ""
        
        return ", ".join([road.ref for road in roads])
