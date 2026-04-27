"""
Processador de alertas multithread - NÚCLEO DO SISTEMA
"""
import threading
import queue
import time
import uuid
from datetime import datetime
from typing import Optional, Callable, Dict
import logging

from ..models.alert import (
    FireAlert, AlertStatus, AlertPriority,
    Coordinates, ProcessingMetrics, ServerConfig
)
from ..services.antenna_service import AntennaService
from ..services.location_service import LocationService
from ..services.road_service import RoadService
from ..services.audio_service import AudioService
from ..services.transmission_service import TransmissionService

logger = logging.getLogger(__name__)


class AlertProcessor:
    """
    Processador multithread de alertas de incêndio

    Funcionalidades:
    - Fila de prioridades para alertas
    - Processamento paralelo de múltiplos alertas
    - Gestão de workers threads
    - Callbacks para notificações
    """

    def __init__(
        self,
        config: ServerConfig,
        on_alert_complete: Optional[Callable[[FireAlert], None]] = None,
        on_alert_failed: Optional[Callable[[FireAlert], None]] = None
    ):
        """
        Args:
            config: Configuração do servidor
            on_alert_complete: Callback quando alerta é processado com sucesso
            on_alert_failed: Callback quando alerta falha
        """
        self.config = config
        self.on_alert_complete = on_alert_complete
        self.on_alert_failed = on_alert_failed

        # Fila de alertas (priority queue)
        self.alert_queue: queue.PriorityQueue = queue.PriorityQueue(
            maxsize=config.queue_size
        )

        # Workers threads
        self.workers: list = []
        self.max_workers = config.max_workers
        self.shutdown_flag = threading.Event()
        self.busy_workers = 0
        self.busy_workers_lock = threading.Lock()

        # Serviços
        self.antenna_service = AntennaService(config)
        self.location_service = LocationService(config)
        self.road_service = RoadService(config)
        self.audio_service = AudioService(config)
        self.transmission_service = TransmissionService(config)

        # Rastreamento de alertas ativos
        self.active_alerts: Dict[str, FireAlert] = {}
        self.alerts_lock = threading.Lock()

        # Métricas
        self.processed_count = 0
        self.failed_count = 0

        logger.info(
            f"AlertProcessor inicializado com {self.max_workers} workers"
        )

    def start(self):
        """Inicia workers threads"""
        logger.info("Iniciando workers...")

        for i in range(self.max_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"Worker-{i+1}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)

        logger.info(f"{len(self.workers)} workers iniciados")

    def stop(self):
        """Para todos os workers"""
        logger.info("Parando workers...")
        self.shutdown_flag.set()

        # Aguardar todos os workers terminarem
        for worker in self.workers:
            worker.join(timeout=5)

        logger.info("Todos os workers parados")

    def submit_alert(
        self,
        coordinates: Coordinates,
        priority: AlertPriority = AlertPriority.NORMAL
    ) -> str:
        """
        Submete novo alerta para processamento

        Args:
            coordinates: Coordenadas do incêndio
            priority: Prioridade do alerta

        Returns:
            ID do alerta criado

        Raises:
            queue.Full: Se a fila estiver cheia
        """
        # Gerar ID único
        alert_id = f"ALERT-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"

        # Criar alerta
        alert = FireAlert(
            alert_id=alert_id,
            coordinates=coordinates,
            priority=priority,
            status=AlertStatus.PENDING
        )

        # Adicionar à fila (priority queue usa tupla: (prioridade, contador, item))
        # Prioridade invertida: menor valor = maior prioridade
        priority_value = -priority.value  # Inverter para high ter prioridade

        try:
            self.alert_queue.put_nowait((priority_value, time.time(), alert))

            with self.alerts_lock:
                self.active_alerts[alert_id] = alert

            logger.info(
                f"Alerta {alert_id} submetido (prioridade: {priority.name})"
            )

            return alert_id

        except queue.Full:
            logger.error(f"Fila cheia! Não foi possível adicionar alerta")
            raise

    def get_alert_status(self, alert_id: str) -> Optional[FireAlert]:
        """Obtém status de um alerta específico"""
        with self.alerts_lock:
            return self.active_alerts.get(alert_id)

    def get_queue_size(self) -> int:
        """Retorna tamanho atual da fila"""
        return self.alert_queue.qsize()

    def get_active_count(self) -> int:
        """Retorna número de alertas ativos"""
        with self.alerts_lock:
            return len(self.active_alerts)

    def _worker_loop(self):
        """Loop principal de cada worker thread"""
        worker_name = threading.current_thread().name
        logger.info(f"{worker_name} iniciado")

        while not self.shutdown_flag.is_set():
            try:
                # Aguardar alerta da fila (timeout 1s)
                _, _, alert = self.alert_queue.get(timeout=1)

                logger.info(f"{worker_name} processando {alert.alert_id}")

                # Processar alerta
                self._set_worker_busy(True)
                self._process_alert(alert, worker_name)
                self._set_worker_busy(False)

                # Marcar tarefa como completa
                self.alert_queue.task_done()

            except queue.Empty:
                # Timeout - continuar loop
                continue

            except Exception as e:
                self._set_worker_busy(False)
                logger.error(
                    f"{worker_name} erro inesperado: {e}",
                    exc_info=True
                )

        logger.info(f"{worker_name} terminado")

    def _process_alert(self, alert: FireAlert, worker_name: str):
        """
        Processa um alerta completo

        Args:
            alert: Alerta a processar
            worker_name: Nome da thread worker
        """
        metrics = ProcessingMetrics(
            alert_id=alert.alert_id,
            start_time=datetime.now()
        )

        try:
            alert.queue_wait_time = max(
                0.0,
                (datetime.now() - alert.timestamp).total_seconds()
            )
            alert.status = AlertStatus.PROCESSING
            logger.info(f"[{alert.alert_id}] Iniciando processamento")
            logger.info(
                f"[{alert.alert_id}] Tempo de espera na fila: "
                f"{alert.queue_wait_time:.2f}s"
            )

            # 1. Procurar antenas próximas
            start = time.time()
            alert.nearby_stations = self.antenna_service.find_nearby_stations(
                alert.coordinates
            )
            metrics.antenna_search_time = time.time() - start
            logger.info(
                f"[{alert.alert_id}] Antenas encontradas: "
                f"{len(alert.nearby_stations)}"
            )

            # 2. Determinar localidade
            start = time.time()
            alert.location = self.location_service.find_location(
                alert.coordinates
            )
            metrics.location_search_time = time.time() - start
            logger.info(f"[{alert.alert_id}] Localidade: {alert.location}")

            # 3. Procurar estradas
            start = time.time()
            alert.nearby_roads = self.road_service.find_nearby_roads(
                alert.coordinates
            )
            metrics.road_search_time = time.time() - start
            logger.info(
                f"[{alert.alert_id}] Estradas encontradas: "
                f"{len(alert.nearby_roads)}"
            )

            # 4. Gerar mensagem
            alert.message_text = self.location_service.generate_alert_message(
                alert.location,
                alert.nearby_roads
            )
            logger.info(f"[{alert.alert_id}] Mensagem: {alert.message_text}")

            # 5. Gerar áudio
            start = time.time()
            audio_file = self.audio_service.generate_audio(
                alert.message_text,
                alert.alert_id
            )
            metrics.audio_generation_time = time.time() - start

            if not audio_file:
                raise RuntimeError("Falha ao gerar áudio WAV")

            alert.audio_file = audio_file
            logger.info(f"[{alert.alert_id}] Áudio gerado: {audio_file}")

            # 6. Transmitir para switches FireTec (protocolo legado do Rodolfo)
            audio_bytes = self.audio_service.read_audio_bytes(audio_file)
            if audio_bytes:
                if self.config.hardware_enabled:
                    start = time.time()
                    transmission_results = self.transmission_service.transmit_to_switches(
                        alert,
                        audio_bytes
                    )
                    alert.transmission_results = transmission_results
                    metrics.transmission_time = time.time() - start

                    # Verificar se transmissão foi bem sucedida
                    success_count = sum(
                        1 for r in transmission_results.values() if r['success']
                    )

                    if success_count > 0:
                        alert.status = AlertStatus.SENT
                        logger.info(
                            f"[{alert.alert_id}] Transmitido para "
                            f"{success_count} switch(es)"
                        )
                    else:
                        logger.warning(
                            f"[{alert.alert_id}] Falha na transmissão para "
                            f"todos os switches"
                        )
                else:
                    logger.info(
                        f"[{alert.alert_id}] Modo hardware OFF: "
                        "transmissão para switches ignorada"
                    )
            else:
                raise RuntimeError("Falha ao ler áudio WAV")

            # Se não foi transmitido, marcar como processado
            if alert.status != AlertStatus.SENT:
                alert.status = AlertStatus.PROCESSED
            metrics.mark_complete()
            alert.processing_time = metrics.duration

            self.processed_count += 1

            logger.info(
                f"[{alert.alert_id}] Processado com sucesso "
                f"em {metrics.duration:.2f}s"
            )

            # Callback sucesso
            if self.on_alert_complete:
                self.on_alert_complete(alert)

        except Exception as e:
            alert.status = AlertStatus.FAILED
            alert.error_message = str(e)
            self.failed_count += 1

            logger.error(
                f"[{alert.alert_id}] Falha no processamento: {e}",
                exc_info=True
            )

            # Callback falha
            if self.on_alert_failed:
                self.on_alert_failed(alert)

        finally:
            # Remover de alertas ativos após um tempo
            # (manter histórico por alguns minutos)
            threading.Timer(
                300,  # 5 minutos
                self._remove_from_active,
                args=[alert.alert_id]
            ).start()

    def _remove_from_active(self, alert_id: str):
        """Remove alerta da lista de ativos"""
        with self.alerts_lock:
            if alert_id in self.active_alerts:
                del self.active_alerts[alert_id]
                logger.debug(f"Alerta {alert_id} removido do histórico ativo")

    def get_statistics(self) -> dict:
        """Retorna estatísticas do processador"""
        return {
            'active_alerts': self.get_active_count(),
            'queue_size': self.get_queue_size(),
            'processed_total': self.processed_count,
            'failed_total': self.failed_count,
            'busy_workers': self.busy_workers,
            'available_workers': max(0, self.max_workers - self.busy_workers),
            'workers': len(self.workers),
            'max_workers': self.max_workers
        }

    def _set_worker_busy(self, busy: bool):
        """Atualiza contador de workers ocupados de forma thread-safe."""
        with self.busy_workers_lock:
            if busy:
                self.busy_workers += 1
            else:
                self.busy_workers = max(0, self.busy_workers - 1)
