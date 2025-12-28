"""
Serviço para geração de mensagens de áudio
"""
import os
from pathlib import Path
from typing import Optional
from gtts import gTTS
import logging

logger = logging.getLogger(__name__)


class AudioService:
    """Serviço para gerar mensagens de áudio de alerta"""
    
    def __init__(self, output_dir: str = "audio"):
        """
        Args:
            output_dir: Diretório para salvar ficheiros de áudio
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        self.language = "pt"
    
    def generate_audio(
        self, 
        text: str, 
        alert_id: str,
        format: str = "mp3"
    ) -> Optional[str]:
        """
        Gera ficheiro de áudio a partir de texto
        
        Args:
            text: Texto da mensagem
            alert_id: ID do alerta (para nome do ficheiro)
            format: Formato de saída (sempre "mp3" - compatibilidade Python 3.14)
        
        Returns:
            Caminho do ficheiro gerado, ou None se falhar
        """
        logger.info(f"[{alert_id}] Gerando áudio: '{text[:50]}...'")
        
        try:
            # Gerar ficheiro MP3 com gTTS
            output_file = self.output_dir / f"{alert_id}.mp3"
            
            tts = gTTS(text=text, lang=self.language)
            tts.save(str(output_file))
            
            logger.info(
                f"[{alert_id}] Áudio MP3 gerado: {output_file.name} "
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
        import time
        
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
