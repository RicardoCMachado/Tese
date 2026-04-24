"""Núcleo de processamento de alertas multithread."""
import logging
import queue
import threading
import time
import uuid
from datetime import datetime
from typing import Callable, Dict, Optional

from ..models import AlertPriority, AlertStatus, Coordinates, FireAlert, ProcessingMetrics, ServerConfig
from ..services import (
    AntennaService,
    AudioService,
    CAPService,
    KMLService,
    LocationService,
    RoadService,
    TransmissionService,
)
from .worker_pool import WorkerPool

logger = logging.getLogger(__name__)


class AlertProcessor:
    def __init__(
        self,
        config: ServerConfig,
        on_alert_complete: Optional[Callable[[FireAlert], None]] = None,
        on_alert_failed: Optional[Callable[[FireAlert], None]] = None,
    ):
        self.config = config
        self.on_alert_complete = on_alert_complete
        self.on_alert_failed = on_alert_failed

        self.pool = WorkerPool(
            max_workers=config.max_workers,
            queue_size=config.queue_size,
            worker_fn=self._process_alert,
        )

        self.antenna_service = AntennaService(config)
        self.location_service = LocationService(config)
        self.road_service = RoadService(config)
        self.audio_service = AudioService()
        self.transmission_service = TransmissionService(config)
        self.cap_service = CAPService()
        self.kml_service = KMLService()

        self.active_alerts: Dict[str, FireAlert] = {}
        self.alerts_lock = threading.Lock()
        self.processed_count = 0
        self.failed_count = 0

    def start(self) -> None:
        self.pool.start()

    def stop(self) -> None:
        self.pool.stop()

    def submit_alert(self, coordinates: Coordinates, priority: AlertPriority = AlertPriority.NORMAL) -> str:
        alert_id = f"ALERT-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:6]}"
        alert = FireAlert(alert_id=alert_id, coordinates=coordinates, priority=priority)

        with self.alerts_lock:
            self.active_alerts[alert_id] = alert

        try:
            # menor valor = maior prioridade
            self.pool.submit(priority=-priority.value, payload=alert)
        except queue.Full:
            with self.alerts_lock:
                self.active_alerts.pop(alert_id, None)
            raise
        return alert_id

    def _process_alert(self, alert: FireAlert) -> None:
        metrics = ProcessingMetrics(alert_id=alert.alert_id)
        alert.metrics = metrics

        try:
            alert.status = AlertStatus.PROCESSING

            start = time.time()
            alert.nearby_stations = self.antenna_service.find_nearby_stations(alert.coordinates)
            metrics.antenna_search_time = time.time() - start

            start = time.time()
            alert.location = self.location_service.find_location(alert.coordinates)
            metrics.location_search_time = time.time() - start

            start = time.time()
            alert.nearby_roads = self.road_service.find_nearby_roads(alert.coordinates)
            metrics.road_search_time = time.time() - start

            alert.message_text = self.location_service.generate_alert_message(
                alert.location,
                alert.nearby_roads,
            )

            start = time.time()
            audio_file = self.audio_service.generate_audio(alert.message_text, alert.alert_id)
            metrics.audio_generation_time = time.time() - start
            if not audio_file:
                raise RuntimeError("Falha a gerar WAV de alerta")

            alert.audio_file = audio_file
            wav_data = self.audio_service.read_audio_bytes(audio_file)
            if not wav_data:
                raise RuntimeError("Falha a ler WAV gerado")

            start = time.time()
            payload = self.transmission_service.build_legacy_payload(alert, wav_data)
            transmission = self.transmission_service.transmit_legacy_to_switches(alert, payload)
            metrics.transmission_time = time.time() - start
            alert.transmission_results = transmission

            success_count = sum(1 for item in transmission.values() if item.get("success"))
            metrics.switch_success_rate = success_count / max(len(self.config.switch_ips), 1)

            if self.config.enable_cap:
                alert.cap_file = self.cap_service.generate_cap(alert, wav_data)

            metrics.mark_complete()
            alert.processing_time = metrics.duration
            alert.status = AlertStatus.SENT if success_count > 0 else AlertStatus.PROCESSED
            self.processed_count += 1

            if self.on_alert_complete:
                self.on_alert_complete(alert)

        except Exception as exc:
            alert.status = AlertStatus.FAILED
            alert.error_message = str(exc)
            self.failed_count += 1
            logger.error("[%s] Falha no processamento: %s", alert.alert_id, exc, exc_info=True)
            if self.on_alert_failed:
                self.on_alert_failed(alert)

        finally:
            threading.Timer(300, self._remove_from_active, args=[alert.alert_id]).start()

    def _remove_from_active(self, alert_id: str) -> None:
        with self.alerts_lock:
            self.active_alerts.pop(alert_id, None)

    def get_queue_size(self) -> int:
        return self.pool.size()

    def get_active_count(self) -> int:
        with self.alerts_lock:
            return len(self.active_alerts)

    def get_alert_status(self, alert_id: str) -> Optional[FireAlert]:
        with self.alerts_lock:
            return self.active_alerts.get(alert_id)

    def get_statistics(self) -> dict:
        return {
            "active_alerts": self.get_active_count(),
            "queue_size": self.get_queue_size(),
            "processed_total": self.processed_count,
            "failed_total": self.failed_count,
            "workers": len(self.pool.workers),
            "max_workers": self.pool.max_workers,
        }
