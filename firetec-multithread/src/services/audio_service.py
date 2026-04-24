"""
Serviço para geração de mensagens de áudio
"""
import os
import time
from pathlib import Path
from typing import Optional
from gtts import gTTS
from pydub import AudioSegment
import logging

from ..models.alert import ServerConfig

try:
    import imageio_ffmpeg
except ImportError:  # pragma: no cover - fallback para ffmpeg do sistema
    imageio_ffmpeg = None

logger = logging.getLogger(__name__)


class AudioService:
    """Serviço para gerar mensagens de áudio de alerta"""

    def __init__(self, config: Optional[ServerConfig] = None, output_dir: str = "audio"):
        """
        Args:
            config: Configuração do servidor
            output_dir: Diretório para salvar ficheiros de áudio
        """
        self.config = config or ServerConfig()
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)

        self.language = self.config.audio_language
        if imageio_ffmpeg is not None:
            AudioSegment.converter = imageio_ffmpeg.get_ffmpeg_exe()

    def generate_audio(
        self,
        text: str,
        alert_id: str,
        format: str = "wav"
    ) -> Optional[str]:
        """
        Gera ficheiro de áudio a partir de texto

        Args:
            text: Texto da mensagem
            alert_id: ID do alerta (para nome do ficheiro)
            format: Mantido por compatibilidade; o hardware usa WAV como no Rodolfo

        Returns:
            Caminho do ficheiro gerado, ou None se falhar
        """
        logger.info(f"[{alert_id}] Gerando áudio: '{text[:50]}...'")

        try:
            # Igual ao script do Rodolfo: gTTS gera MP3, depois converte para WAV.
            mp3_file = self.output_dir / f"{alert_id}.mp3"
            output_file = self.output_dir / f"{alert_id}.wav"

            tts = gTTS(text=text, lang=self.language)
            tts.save(str(mp3_file))

            audio = AudioSegment.from_file(str(mp3_file), format="mp3")
            audio = audio.set_frame_rate(self.config.audio_sample_rate)
            audio = audio.set_sample_width(self.config.audio_bit_depth)
            audio.export(str(output_file), format="wav")

            logger.info(
                f"[{alert_id}] Áudio WAV gerado: {output_file.name} "
                f"({output_file.stat().st_size} bytes)"
            )

            return str(output_file)

        except Exception as e:
            logger.error(f"[{alert_id}] Erro ao gerar áudio: {e}", exc_info=True)
            return None

    def read_audio_bytes(self, audio_file: str) -> Optional[bytes]:
        """
        Lê ficheiro de áudio como bytes

        Args:
            audio_file: Caminho do ficheiro

        Returns:
            Conteúdo do ficheiro em bytes, ou None se falhar
        """
        try:
            with open(audio_file, "rb") as f:
                return f.read()
        except Exception as e:
            logger.error(f"Erro ao ler ficheiro de áudio: {e}")
            return None

    def cleanup_old_files(self, max_age_hours: int = 24):
        """
        Remove ficheiros de áudio antigos

        Args:
            max_age_hours: Idade máxima dos ficheiros em horas
        """
        now = time.time()
        max_age_seconds = max_age_hours * 3600

        removed_count = 0

        for audio_file in self.output_dir.glob("*"):
            if audio_file.is_file():
                age = now - audio_file.stat().st_mtime

                if age > max_age_seconds:
                    audio_file.unlink()
                    removed_count += 1

        if removed_count > 0:
            logger.info(f"Removidos {removed_count} ficheiros de áudio antigos")
