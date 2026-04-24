"""Transmissão TCP para FireTec switches (protocolo legado obrigatório)."""
import logging
import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict

from ..models.alert import FireAlert
from ..models.config import ServerConfig

logger = logging.getLogger(__name__)


class TransmissionService:
    def __init__(self, config: ServerConfig):
        self.config = config
        self.switch_ips = config.switch_ips
        self.switch_port = config.switch_port
        self.connection_timeout = 5
        self.retry_attempts = 3

    def build_legacy_payload(self, alert: FireAlert, wav_data: bytes) -> bytes:
        station = alert.get_primary_station()
        ps = station.ps if station else "FIRETEC1"
        pi = station.pi if station else "8400"

        frequencies = alert.get_frequencies()
        if not frequencies:
            frequencies = [100.0, 102.0]

        af = ",".join(str(freq) for freq in frequencies)
        return wav_data + f"PS={ps};PI={pi};AF={af};".encode("utf-8")

    def transmit_legacy_to_switches(self, alert: FireAlert, payload: bytes) -> Dict[str, Dict]:
        """Envio paralelo para os switches; falhas parciais não quebram aplicação."""
        if self.config.simulation_mode:
            return {ip: {"success": True, "attempts": 0, "duration": 0.0, "error": None} for ip in self.switch_ips}

        results: Dict[str, Dict] = {}
        with ThreadPoolExecutor(max_workers=len(self.switch_ips)) as executor:
            future_by_ip = {
                executor.submit(self._transmit_to_single_switch, alert.alert_id, ip, payload): ip
                for ip in self.switch_ips
            }
            for future in as_completed(future_by_ip):
                ip = future_by_ip[future]
                try:
                    results[ip] = future.result()
                except Exception as exc:  # pragma: no cover - segurança extra
                    results[ip] = {
                        "success": False,
                        "attempts": self.retry_attempts,
                        "duration": 0.0,
                        "error": str(exc),
                    }
        return results

    def _transmit_to_single_switch(self, alert_id: str, switch_ip: str, payload: bytes) -> Dict:
        result = {"success": False, "attempts": 0, "error": None, "duration": 0.0}
        start = time.time()

        for attempt in range(1, self.retry_attempts + 1):
            result["attempts"] = attempt
            sock = None
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.connection_timeout)
                sock.connect((switch_ip, self.switch_port))
                sock.sendall(payload)
                result["success"] = True
                logger.info("[%s] Switch %s OK na tentativa %s", alert_id, switch_ip, attempt)
                break
            except Exception as exc:
                result["error"] = str(exc)
                logger.warning("[%s] Switch %s falhou tentativa %s: %s", alert_id, switch_ip, attempt, exc)
                time.sleep(0.5)
            finally:
                if sock is not None:
                    try:
                        sock.close()
                    except Exception:
                        pass

        result["duration"] = time.time() - start
        return result
