"""
FireTec Multithread Server - Sistema Principal
Dissertação de Mestrado - Ricardo Machado
"""
import sys
import signal
import logging
import random
import os
from pathlib import Path
from typing import List

try:
    from dotenv import load_dotenv
except ImportError: 
    load_dotenv = None

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.models.alert import ServerConfig, Coordinates, AlertPriority
from src.core.alert_processor import AlertProcessor
from src.utils.logger import setup_logging
from src.utils.menu import MainMenu

if load_dotenv is not None:
    # Permite configurar VM via ficheiro .env sem editar código
    load_dotenv(Path(__file__).parent / ".env")


def _configure_console_encoding():
    """Evita erros de encoding em terminais Windows/Linux."""
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                # Mantém comportamento padrão se o terminal não suportar reconfigure
                pass


_configure_console_encoding()

# Configurar logging
setup_logging()
logger = logging.getLogger(__name__)

# Flag global para shutdown suave
shutdown_requested = False


def _env_int(name: str, default: int) -> int:
    """Lê inteiro de variável de ambiente com fallback seguro."""
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        logger.warning(f"Variável {name} inválida ('{value}'). Usando {default}.")
        return default


def _env_list(name: str, default: List[str]) -> List[str]:
    """Lê lista CSV de variável de ambiente."""
    value = os.getenv(name)
    if value is None:
        return default
    parsed = [item.strip() for item in value.split(",") if item.strip()]
    return parsed or default


def _env_bool(name: str, default: bool) -> bool:
    """Lê booleano de variável de ambiente com fallback seguro."""
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "sim", "on")


def on_alert_complete(alert):
    """Callback quando alerta é processado com sucesso"""
    queue_wait = alert.queue_wait_time or 0.0
    processing_time = alert.processing_time or 0.0
    total_time = queue_wait + processing_time

    logger.info(f"✓ ALERTA COMPLETO: {alert.alert_id}")
    logger.info(f"  Localização: {alert.location}")
    logger.info(f"  Antenas: {len(alert.nearby_stations)}")
    logger.info(f"  Estradas: {len(alert.nearby_roads)}")
    logger.info(f"  Espera em fila: {queue_wait:.2f}s")
    logger.info(f"  Processamento: {processing_time:.2f}s")
    logger.info(f"  Tempo total: {total_time:.2f}s")
    logger.info(f"  Mensagem: {alert.message_text}")
    menu = MainMenu.get_active()
    message = (
        "\n" + "=" * 60 + "\n"
        f"✓ ALERTA {alert.alert_id} PROCESSADO\n"
        f"Localidade: {alert.location}\n"
        f"Mensagem: {alert.message_text}\n"
        f"Tempo em fila: {queue_wait:.2f}s\n"
        f"Tempo de processamento: {processing_time:.2f}s\n"
        f"Tempo total (fila + processamento): {total_time:.2f}s\n"
        + "=" * 60 + "\n"
    )
    if menu is not None:
        menu.emit_message(message)
    else:
        print(message)


def on_alert_failed(alert):
    """Callback quando alerta falha"""
    logger.error(f"✗ ALERTA FALHOU: {alert.alert_id}")
    logger.error(f"  Erro: {alert.error_message}")
    menu = MainMenu.get_active()
    message = (
        f"\n✗ ERRO: Alerta {alert.alert_id} falhou!\n"
        f"Erro: {alert.error_message}\n"
    )
    if menu is not None:
        menu.emit_message(message)
    else:
        print(message)


def signal_handler(sig, frame):
    """Handler para Ctrl+C - shutdown suave"""
    global shutdown_requested
    if not shutdown_requested:
        shutdown_requested = True
        print("\n\n⚠️  Shutdown solicitado (Ctrl+C)...")
        print("🔄 Aguardando conclusão de alertas ativos...")
        print("💡 Pressione Ctrl+C novamente para forçar encerramento\n")
    else:
        print("\n❌ Encerrando imediatamente...")
        sys.exit(1)


def main():
    """Função principal"""
    # Registrar handler para Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)

    # Verificar ficheiros de dados
    data_dir = Path(__file__).parent / "data"
    if not (data_dir / "123.csv").exists():
        print("⚠️  AVISO: Ficheiro '123.csv' não encontrado em /data/")
        print("   Copie os ficheiros CSV para a pasta 'data/'")
        print()

    if not (data_dir / "Localidades_Portugal.csv").exists():
        print("⚠️  AVISO: Ficheiro 'Localidades_Portugal.csv' não encontrado")
        print()

    if not (data_dir / "roads_portugal.csv").exists():
        print("⚠️  AVISO: Ficheiro 'roads_portugal.csv' não encontrado")
        print("   Gere-o com: python scripts/build_roads_csv.py --input data/portugal.gpkg")
        print()

    # Configuração (VM-friendly via variáveis de ambiente)
    default_switch_ips = ["192.168.0.22", "192.168.0.21"]
    switch_ips = _env_list("FIRETEC_SWITCH_IPS", default_switch_ips)

    config = ServerConfig(
        antenna_csv=str(data_dir / "123.csv"),
        localities_csv=str(data_dir / "Localidades_Portugal.csv"),
        roads_csv=os.getenv(
            "FIRETEC_ROADS_CSV",
            str(data_dir / "roads_portugal.csv")
        ),
        road_overrides_csv=os.getenv(
            "FIRETEC_ROAD_OVERRIDES_CSV",
            str(data_dir / "road_overrides.csv")
        ),
        max_workers=_env_int("FIRETEC_MAX_WORKERS", 5),
        queue_size=_env_int("FIRETEC_QUEUE_SIZE", 50),
        hardware_enabled=_env_bool("FIRETEC_HARDWARE_ENABLED", False),
        switch_ips=switch_ips,
        switch_port=_env_int("FIRETEC_SWITCH_PORT", 8080)
    )

    logger.info(
        "Configuração ativa | workers=%s | hardware=%s | switches=%s:%s",
        config.max_workers,
        "ON" if config.hardware_enabled else "OFF",
        ",".join(config.switch_ips),
        config.switch_port
    )
    if not config.hardware_enabled:
        logger.info("Modo hardware OFF: transmissão para switches desativada")

    # Criar processador
    logger.info("Inicializando servidor...")
    processor = AlertProcessor(
        config=config,
        on_alert_complete=on_alert_complete,
        on_alert_failed=on_alert_failed
    )

    # Iniciar workers
    processor.start()

    try:
        # Menu interativo
        menu = MainMenu(processor)
        menu.run()

    except KeyboardInterrupt:
        # Já tratado pelo signal_handler, mas mantém para compatibilidade
        pass

    except Exception as e:
        logger.error(f"Erro fatal: {e}", exc_info=True)
        print(f"\n❌ ERRO FATAL: {e}")

    finally:
        # Parar processador
        if not shutdown_requested:
            print("\n🛑 Encerrando servidor...")

        logger.info("Parando processador de alertas...")
        processor.stop()

        # Estatísticas finais
        stats = processor.get_statistics()
        print("\n" + "="*60)
        print("ESTATÍSTICAS FINAIS")
        print("="*60)
        print(f"Alertas processados: {stats['processed_total']}")
        print(f"Alertas falhados: {stats['failed_total']}")
        print(f"Taxa de sucesso: {stats['processed_total']/(stats['processed_total']+stats['failed_total'])*100:.1f}%"
              if (stats['processed_total']+stats['failed_total']) > 0 else "N/A")
        print("="*60)

        logger.info("Servidor encerrado")
        print("\n👋 Até breve!")


if __name__ == "__main__":
    main()
