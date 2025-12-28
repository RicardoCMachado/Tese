"""
API REST para receber alertas externos - FastAPI
"""
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional
import threading
import uvicorn
import logging

from ..models.alert import Coordinates, AlertPriority
from ..core.alert_processor import AlertProcessor

logger = logging.getLogger(__name__)


# Modelos Pydantic para validação
class AlertCreate(BaseModel):
    latitude: float = Field(..., ge=36.0, le=43.0, description="Latitude (Portugal Continental)")
    longitude: float = Field(..., ge=-10.0, le=-6.0, description="Longitude (Portugal Continental)")
    priority: Optional[str] = Field("NORMAL", description="Prioridade: NORMAL, HIGH, CRITICAL")
    
    class Config:
        json_schema_extra = {
            "example": {
                "latitude": 40.6,
                "longitude": -8.6,
                "priority": "NORMAL"
            }
        }


class AlertResponse(BaseModel):
    success: bool
    alert_id: str
    coordinates: dict
    priority: str


class FireTecAPI:
    """API REST para sistema FireTec usando FastAPI"""
    
    def __init__(self, processor: AlertProcessor, host: str = "0.0.0.0", port: int = 5000):
        """
        Args:
            processor: Processador de alertas
            host: Host da API
            port: Porta da API
        """
        self.processor = processor
        self.host = host
        self.port = port
        
        # Criar app FastAPI
        self.app = FastAPI(
            title="FireTec Multithread API",
            description="Sistema de Alerta de Incêndios por Rádio FM",
            version="1.0.0",
            docs_url="/",
            redoc_url="/redoc"
        )
        
        # Registrar rotas
        self._register_routes()
        
        self.server_thread = None
    
    def _register_routes(self):
        """Registra rotas da API"""
        
        @self.app.get("/health", tags=["Sistema"])
        def health():
            """Health check do serviço"""
            return {
                "status": "ok",
                "service": "FireTec API",
                "version": "1.0.0"
            }
        
        @self.app.post("/api/alert", response_model=AlertResponse, tags=["Alertas"])
        def create_alert(alert_data: AlertCreate):
            """
            Criar novo alerta de incêndio
            
            - **latitude**: Coordenada de latitude (36.0 a 43.0)
            - **longitude**: Coordenada de longitude (-10.0 a -6.0)
            - **priority**: Prioridade do alerta (NORMAL, HIGH, CRITICAL)
            """
            try:
                # Validar prioridade
                priority_str = alert_data.priority.upper()
                try:
                    priority = AlertPriority[priority_str]
                except KeyError:
                    priority = AlertPriority.NORMAL
                
                # Criar coordenadas
                coords = Coordinates(
                    latitude=alert_data.latitude,
                    longitude=alert_data.longitude
                )
                
                # Submeter alerta
                alert_id = self.processor.submit_alert(coords, priority)
                
                logger.info(
                    f"Alerta recebido via API: {alert_id} "
                    f"({alert_data.latitude}, {alert_data.longitude})"
                )
                
                return {
                    "success": True,
                    "alert_id": alert_id,
                    "coordinates": {
                        "latitude": alert_data.latitude,
                        "longitude": alert_data.longitude
                    },
                    "priority": priority.name
                }
            
            except Exception as e:
                logger.error(f"Erro ao criar alerta via API: {e}", exc_info=True)
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Erro interno do servidor: {str(e)}"
                )
        
        @self.app.get("/api/alert/{alert_id}", tags=["Alertas"])
        def get_alert(alert_id: str):
            """Obter status de um alerta específico"""
            alert = self.processor.get_alert_status(alert_id)
            
            if not alert:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Alerta {alert_id} não encontrado"
                )
            
            return {
                "alert_id": alert.alert_id,
                "status": alert.status.value,
                "coordinates": {
                    "latitude": alert.coordinates.latitude,
                    "longitude": alert.coordinates.longitude
                },
                "priority": alert.priority.name,
                "timestamp": alert.timestamp.isoformat(),
                "location": str(alert.location) if alert.location else None,
                "message": alert.message_text,
                "processing_time": alert.processing_time,
                "nearby_stations": len(alert.nearby_stations),
                "nearby_roads": len(alert.nearby_roads)
            }
        
        @self.app.get("/api/alerts", tags=["Alertas"])
        def list_alerts():
            """Listar todos os alertas ativos"""
            with self.processor.alerts_lock:
                alerts = []
                for alert_id, alert in self.processor.active_alerts.items():
                    alerts.append({
                        "alert_id": alert.alert_id,
                        "status": alert.status.value,
                        "latitude": alert.coordinates.latitude,
                        "longitude": alert.coordinates.longitude,
                        "priority": alert.priority.name,
                        "timestamp": alert.timestamp.isoformat()
                    })
            
            return {
                "count": len(alerts),
                "alerts": alerts
            }
        
        @self.app.get("/api/statistics", tags=["Sistema"])
        def statistics():
            """Obter estatísticas do sistema"""
            stats = self.processor.get_statistics()
            
            success_rate = 0
            total = stats['processed_total'] + stats['failed_total']
            if total > 0:
                success_rate = (stats['processed_total'] / total) * 100
            
            return {
                "active_alerts": stats['active_alerts'],
                "queue_size": stats['queue_size'],
                "processed_total": stats['processed_total'],
                "failed_total": stats['failed_total'],
                "workers": stats['workers'],
                "max_workers": stats['max_workers'],
                "success_rate": round(success_rate, 2)
            }
    
    def start(self):
        """Inicia servidor API em thread separada"""
        logger.info(f"Iniciando API REST em {self.host}:{self.port}")
        
        self.server_thread = threading.Thread(
            target=self._run_server,
            daemon=True,
            name="API-Server"
        )
        self.server_thread.start()
        
        logger.info(f"✅ API disponível em http://{self.host}:{self.port}")
        logger.info(f"📖 Documentação interativa em http://{self.host}:{self.port}/")
    
    def _run_server(self):
        """Executa servidor Uvicorn"""
        uvicorn.run(
            self.app,
            host=self.host,
            port=self.port,
            log_level="warning"
        )
