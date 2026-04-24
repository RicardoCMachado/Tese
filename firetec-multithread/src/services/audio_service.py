"""Geração de áudio no formato legado do laboratório."""
import logging
from pathlib import Path
from typing import Optional

from gtts import gTTS
from pydub import AudioSegment

logger = logging.getLogger(__name__)


class AudioService:
    def __init__(self, output_dir: str = "audio"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_audio(self, text: str, alert_id: str) -> Optional[str]:
        """Fluxo obrigatório: gTTS -> MP3 temporário -> WAV (32kHz, 8-bit)."""
        mp3_file = self.output_dir / f"{alert_id}.mp3"
        wav_file = self.output_dir / f"{alert_id}.wav"

        try:
            tts = gTTS(text=text, lang="pt")
            tts.save(str(mp3_file))

            audio = AudioSegment.from_file(mp3_file, format="mp3")
            audio = audio.set_frame_rate(32000)
            audio = audio.set_sample_width(1)
            audio.export(wav_file, format="wav")

            return str(wav_file)
        except Exception as exc:
            logger.error("[%s] Erro a gerar áudio: %s", alert_id, exc, exc_info=True)
            return None

    @staticmethod
    def read_audio_bytes(audio_file: str) -> Optional[bytes]:
        try:
            with open(audio_file, "rb") as handler:
                return handler.read()
        except Exception:
            return None
