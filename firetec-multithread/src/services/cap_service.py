"""Geração opcional de CAP XML para interoperabilidade académica."""
import binascii
import logging
from pathlib import Path
from typing import Optional

from ..models.alert import FireAlert

try:
    import capparser

    CAP_AVAILABLE = True
except ImportError:  # pragma: no cover
    CAP_AVAILABLE = False

logger = logging.getLogger(__name__)


class CAPService:
    def __init__(self, output_dir: str = "cap"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_cap(self, alert: FireAlert, audio_bytes: Optional[bytes] = None) -> Optional[str]:
        if not CAP_AVAILABLE:
            return None

        cap_alert = capparser.element.Alert(
            sender="FireTec",
            status=capparser.enums.Status.Actual,
            msgType=capparser.enums.MsgType.Alert,
            scope=capparser.enums.Scope.Private,
        )
        cap_alert.setSource("FireTec")
        cap_alert.addAddress("FireTec")

        info = capparser.element.Info(
            category=[capparser.enums.Category.Fire],
            event="Incendio Florestal",
            urgency=capparser.enums.Urgency.Immediate,
            severity=capparser.enums.Severity.Severe,
            certainty=capparser.enums.Certainty.Observed,
        )

        info.setSenderName("FireTec")
        info.setInstruction(alert.message_text or "Alerta FireTec")

        station = alert.get_primary_station()
        ps = station.ps if station else "FIRETEC1"
        pi = station.pi if station else "8400"
        af_values = alert.get_frequencies() or [100.0, 102.0]

        info.addParameter(capparser.element.Parameter(parameterName="PS", parameterValue=ps))
        info.addParameter(capparser.element.Parameter(parameterName="PI", parameterValue=pi))
        info.addParameter(
            capparser.element.Parameter(
                parameterName="AF",
                parameterValue=",".join(str(v) for v in af_values),
            )
        )

        if audio_bytes:
            resource = capparser.Resource()
            resource.setResourceDesc("Audio Message")
            resource.setMimeType("audio/wav")
            resource.setDerefUri(binascii.hexlify(audio_bytes).decode("utf8"))
            info.addResource(resource)

        cap_alert.addInfo(info)
        output_file = self.output_dir / f"{alert.alert_id}.xml"
        capparser.writeAlertToFile(cap_alert, str(output_file))
        return str(output_file)
