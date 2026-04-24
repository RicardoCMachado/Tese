"""
Configuração de logging do sistema
"""
import logging
import sys
from pathlib import Path
from datetime import datetime
import colorlog


def setup_logging(log_level: str = "INFO", log_file: str = None):
    """
    Configura sistema de logging
    
    Args:
        log_level: Nível de log (DEBUG, INFO, WARNING, ERROR)
        log_file: Caminho para ficheiro de log (opcional)
    """
    # Criar diretório de logs se necessário
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        log_dir = Path(__file__).parent.parent.parent / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"firetec_{datetime.now().strftime('%Y%m%d')}.log"
    
    # Formato com cores para console
    console_formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s [%(levelname)-8s]%(reset)s "
        "%(cyan)s%(name)s%(reset)s - %(message)s",
        datefmt="%H:%M:%S",
        log_colors={
            'DEBUG': 'white',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'red,bg_white',
        }
    )
    
    # Formato para ficheiro
    file_formatter = logging.Formatter(
        "%(asctime)s [%(levelname)-8s] %(name)-20s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Handler para console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_formatter)
    
    # Handler para ficheiro
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    
    # Configurar root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Silenciar logs verbosos de bibliotecas externas
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('geopy').setLevel(logging.WARNING)
    
    root_logger.info(f"Logging configurado (nível: {log_level}, ficheiro: {log_file})")
