"""
API REST para receber alertas externos
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading
import logging

from ..models.alert import Coordinates, AlertPriority
from ..core.alert_processor import AlertProcessor

logger = logging.getLogger(__name__)


class FireTecAPI:
    """API REST para sistema FireTec"""
    
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
        
        # Criar app Flask
        self.app = Flask(__name__)
        CORS(self.app)  # Permitir CORS
        
        # Configurar logging do Flask
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.WARNING)
        
        # Registrar rotas
        self._register_routes()
        
        self.server_thread = None
    
    def _register_routes(self):
        """Registra rotas da API"""
        
        @self.app.route('/health', methods=['GET'])
        def health():
            """Endpoint de health check"""
            return jsonify({
                'status': 'ok',
                'service': 'FireTec API',
                'version': '1.0.0'
            })
        
        @self.app.route('/api/alert', methods=['POST'])
        def create_alert():
            """
            Criar novo alerta
            
            Body JSON:
            {
                "latitude": 40.6,
                "longitude": -8.6,
                "priority": "NORMAL"  // opcional: NORMAL, HIGH, CRITICAL
            }
            """
            try:
                data = request.get_json()
                
                # Validar dados
                if not data:
                    return jsonify({'error': 'JSON inválido'}), 400
                
                if 'latitude' not in data or 'longitude' not in data:
                    return jsonify({
                        'error': 'Campos obrigatórios: latitude, longitude'
                    }), 400
                
                # Extrair dados
                latitude = float(data['latitude'])
                longitude = float(data['longitude'])
                
                # Validar coordenadas (Portugal Continental)
                if not (36.0 <= latitude <= 43.0):
                    return jsonify({'error': 'Latitude fora do intervalo'}), 400
                if not (-10.0 <= longitude <= -6.0):
                    return jsonify({'error': 'Longitude fora do intervalo'}), 400
                
                # Prioridade (opcional)
                priority_str = data.get('priority', 'NORMAL').upper()
                try:
                    priority = AlertPriority[priority_str]
                except KeyError:
                    priority = AlertPriority.NORMAL
                
                # Criar coordenadas
                coords = Coordinates(latitude=latitude, longitude=longitude)
                
                # Submeter alerta
                alert_id = self.processor.submit_alert(coords, priority)
                
                logger.info(
                    f"Alerta recebido via API: {alert_id} "
                    f"({latitude}, {longitude})"
                )
                
                return jsonify({
                    'success': True,
                    'alert_id': alert_id,
                    'coordinates': {
                        'latitude': latitude,
                        'longitude': longitude
                    },
                    'priority': priority.name
                }), 201
            
            except ValueError as e:
                return jsonify({'error': f'Dados inválidos: {e}'}), 400
            except Exception as e:
                logger.error(f"Erro ao criar alerta via API: {e}", exc_info=True)
                return jsonify({'error': 'Erro interno do servidor'}), 500
        
        @self.app.route('/api/alert/<alert_id>', methods=['GET'])
        def get_alert(alert_id):
            """Obter status de um alerta específico"""
            alert = self.processor.get_alert_status(alert_id)
            
            if not alert:
                return jsonify({'error': 'Alerta não encontrado'}), 404
            
            return jsonify({
                'alert_id': alert.alert_id,
                'status': alert.status.value,
                'coordinates': {
                    'latitude': alert.coordinates.latitude,
                    'longitude': alert.coordinates.longitude
                },
                'priority': alert.priority.name,
                'timestamp': alert.timestamp.isoformat(),
                'location': str(alert.location) if alert.location else None,
                'message': alert.message_text,
                'processing_time': alert.processing_time,
                'nearby_stations': len(alert.nearby_stations),
                'nearby_roads': len(alert.nearby_roads)
            })
        
        @self.app.route('/api/alerts', methods=['GET'])
        def list_alerts():
            """Listar alertas ativos"""
            with self.processor.alerts_lock:
                alerts = []
                for alert in self.processor.active_alerts.values():
                    alerts.append({
                        'alert_id': alert.alert_id,
                        'status': alert.status.value,
                        'coordinates': {
                            'latitude': alert.coordinates.latitude,
                            'longitude': alert.coordinates.longitude
                        },
                        'priority': alert.priority.name,
                        'timestamp': alert.timestamp.isoformat()
                    })
            
            return jsonify({
                'count': len(alerts),
                'alerts': alerts
            })
        
        @self.app.route('/api/statistics', methods=['GET'])
        def statistics():
            """Obter estatísticas do sistema"""
            stats = self.processor.get_statistics()
            
            return jsonify({
                'active_alerts': stats['active_alerts'],
                'queue_size': stats['queue_size'],
                'processed_total': stats['processed_total'],
                'failed_total': stats['failed_total'],
                'workers': stats['workers'],
                'max_workers': stats['max_workers'],
                'success_rate': (
                    stats['processed_total'] / 
                    (stats['processed_total'] + stats['failed_total']) * 100
                ) if (stats['processed_total'] + stats['failed_total']) > 0 else 0
            })
    
    def start(self):
        """Inicia servidor API em thread separada"""
        logger.info(f"Iniciando API REST em {self.host}:{self.port}")
        
        self.server_thread = threading.Thread(
            target=self._run_server,
            daemon=True,
            name="API-Server"
        )
        self.server_thread.start()
        
        logger.info(f"API disponível em http://{self.host}:{self.port}")
    
    def _run_server(self):
        """Executa servidor Flask"""
        self.app.run(
            host=self.host,
            port=self.port,
            debug=False,
            use_reloader=False
        )
