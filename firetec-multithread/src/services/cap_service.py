"""
Serviço para geração de mensagens CAP (Common Alerting Protocol)
"""
import binascii
from typing import List, Optional
from pathlib import Path
import logging

try:
    import capparser
    CAP_AVAILABLE = True
except ImportError:
    CAP_AVAILABLE = False
    logging.warning("capparser não disponível. Instalar: pip install capparser")

from ..models.alert import FireAlert

logger = logging.getLogger(__name__)


class CAPService:
    """Serviço para gerar mensagens CAP XML"""
    
    def __init__(self, output_dir: str = "cap"):
        """
        Args:
            output_dir: Diretório para salvar ficheiros CAP
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        if not CAP_AVAILABLE:
            logger.warning("CAPService inicializado sem capparser!")
    
    def generate_cap(
        self, 
        alert: FireAlert,
        audio_bytes: Optional[bytes] = None
    ) -> Optional[str]:
        """
        Gera mensagem CAP XML para um alerta
        
        Args:
            alert: Alerta de incêndio
            audio_bytes: Bytes do ficheiro de áudio (opcional)
        
        Returns:
            Caminho do ficheiro CAP XML gerado, ou None se falhar
        """
        if not CAP_AVAILABLE:
            logger.error("capparser não disponível!")
            return None
        
        logger.info(f"[{alert.alert_id}] Gerando CAP XML")
        
        try:
            # Criar alerta CAP
            cap_alert = capparser.element.Alert(
                sender="FireTec",
                status=capparser.enums.Status.Actual,
                msgType=capparser.enums.MsgType.Alert,
                scope=capparser.enums.Scope.Private
            )
            
            cap_alert.setSource("FireTec")
            cap_alert.addAddress("FireTec")
            
            # Criar informação do alerta
            info = capparser.element.Info(
                category=[capparser.enums.Category.Fire],
                event="Incendio Florestal",
                urgency=capparser.enums.Urgency.Immediate,
                severity=capparser.enums.Severity.Severe,
                certainty=capparser.enums.Certainty.Observed
            )
            
            info.setSenderName("FireTec")
            info.setInstruction(
                "Foi detetado um possível incêndio florestal na sua área. "
                "Precaução é aconselhada."
            )
            
            # Adicionar parâmetros RDS (PS, PI, AF)
            self._add_rds_parameters(info, alert)
            
            # Adicionar informação ao alerta
            cap_alert.addInfo(info)
            
            # Adicionar recurso de áudio se disponível
            if audio_bytes:
                self._add_audio_resource(info, audio_bytes)
                cap_alert.addInfo(info)
            
            # Salvar ficheiro CAP XML
            output_file = self.output_dir / f"{alert.alert_id}.xml"
            capparser.writeAlertToFile(cap_alert, str(output_file))
            
            logger.info(
                f"[{alert.alert_id}] CAP XML gerado: {output_file.name} "
                f"({output_file.stat().st_size} bytes)"
            )
            
            return str(output_file)
        
        except Exception as e:
            logger.error(
                f"[{alert.alert_id}] Erro ao gerar CAP: {e}",
                exc_info=True
            )
            return None
    
    def _add_rds_parameters(self, info, alert: FireAlert):
        """
        Adiciona parâmetros RDS (Radio Data System) ao CAP
        COMPATIBILIDADE: Usa estações reais do alerta (como código original Rodolfo)
        
        Args:
            info: Objeto capparser.element.Info
            alert: Alerta de incêndio
        """
        # CRITICAL FIX: Usar PS/PI das estações reais encontradas (compatibilidade com Rodolfo)
        if alert.nearby_stations and len(alert.nearby_stations) > 0:
            # Usar primeira estação encontrada
            station = alert.nearby_stations[0]
            ps_value = station.ps
            pi_value = station.pi
        else:
            # Fallback: usar valores de teste
            ps_value = "FIRETEC1"
            pi_value = "8400"
            logger.warning(f"[{alert.alert_id}] Nenhuma estação encontrada, usando PS/PI de teste")
        
        param_ps = capparser.element.Parameter(
            parameterName="PS",
            parameterValue=ps_value
        )
        info.addParameter(param_ps)
        
        param_pi = capparser.element.Parameter(
            parameterName="PI",
            parameterValue=pi_value
        )
        info.addParameter(param_pi)
        
        # AF (Alternative Frequencies)
        frequencies = alert.get_frequencies()
        
        # CRITICAL FIX: Apenas adicionar frequências de lab se não houver reais
        if not frequencies or len(frequencies) == 0:
            frequencies = [100.0, 102.0]  # Laboratório
            logger.warning(f"[{alert.alert_id}] Usando frequências de laboratório")
        
        if frequencies:
            # Usar primeira frequência real encontrada
            af_value = str(frequencies[0])
            
            param_af = capparser.element.Parameter(
                parameterName="AF",
                parameterValue=af_value
            )
            info.addParameter(param_af)
            
            logger.debug(
                f"[{alert.alert_id}] Parâmetros RDS: "
                f"PS={ps_value}, PI={pi_value}, AF={af_value}"
            )
    
    def _add_audio_resource(self, info, audio_bytes: bytes):
        """
        Adiciona recurso de áudio ao CAP
        
        Args:
            info: Objeto capparser.element.Info
            audio_bytes: Bytes do ficheiro de áudio
        """
        try:
            resource = capparser.Resource()
            resource.setResourceDesc("Audio Message")
            # CRITICAL FIX: Usar MIME type correto para MP3
            resource.setMimeType("audio/mpeg")
            
            # Converter bytes para string hexadecimal
            hex_data = binascii.hexlify(audio_bytes).decode('utf8')
            resource.setDerefUri(hex_data)
            
            info.addResource(resource)
            
            logger.debug(f"Recurso de áudio adicionado ({len(audio_bytes)} bytes)")
        
        except Exception as e:
            logger.warning(f"Erro ao adicionar recurso de áudio: {e}")
    
    def read_cap_data(self, cap_file: str) -> Optional[bytes]:
        """
        Lê ficheiro CAP como bytes (para transmissão)
        
        Args:
            cap_file: Caminho do ficheiro CAP
        
        Returns:
            Conteúdo do ficheiro em bytes
        """
        try:
            with open(cap_file, "rb") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Erro ao ler ficheiro CAP: {e}")
            return None
