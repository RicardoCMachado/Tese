"""Entrypoint do servidor FireTec multithread."""
import logging
import os
import signal
import sys
from pathlib import Path

from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.core.alert_processor import AlertProcessor
from src.models import ServerConfig
from src.utils.logger import setup_logging
from src.utils.menu import MainMenu
from src.utils.validation import parse_switch_ips


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _configure_console_encoding() -> None:
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream and hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass


_configure_console_encoding()
load_dotenv(Path(__file__).parent / ".env")

setup_logging()
logger = logging.getLogger(__name__)
shutdown_requested = False


def on_alert_complete(alert):
    success = sum(1 for result in alert.transmission_results.values() if result.get("success"))
    print("\n" + "=" * 60)
    print(f"✓ ALERTA {alert.alert_id} PROCESSADO")
    print(f"Localidade: {alert.location}")
    print(f"Mensagem: {alert.message_text}")
    print(f"Switches OK: {success}/{len(alert.transmission_results) or len(alert.nearby_stations)}")
    print(f"Tempo de processamento: {alert.processing_time:.2f}s")
    print("=" * 60 + "\n")


def on_alert_failed(alert):
    print(f"\n✗ ERRO: Alerta {alert.alert_id} falhou!")
    print(f"Erro: {alert.error_message}\n")


def signal_handler(sig, frame):  # noqa: ARG001
    global shutdown_requested
    if not shutdown_requested:
        shutdown_requested = True
        print("\n\n⚠️  Shutdown solicitado (Ctrl+C)...")
        print("🔄 Aguardando conclusão de alertas ativos...")
    else:
        print("\n❌ Encerrando imediatamente...")
        sys.exit(1)


def build_config() -> ServerConfig:
    data_dir = Path(__file__).parent / "data"
    return ServerConfig(
        antenna_csv=str(data_dir / "123.csv"),
        localities_csv=str(data_dir / "Localidades_Portugal.csv"),
        switch_ips=parse_switch_ips(
            os.getenv("FIRETEC_SWITCH_IPS", "192.168.0.22,192.168.0.21"),
            ["192.168.0.22", "192.168.0.21"],
        ),
        switch_port=_env_int("FIRETEC_SWITCH_PORT", 8080),
        max_workers=_env_int("FIRETEC_MAX_WORKERS", 5),
        enable_overpass=_env_bool("FIRETEC_ENABLE_OVERPASS", True),
        enable_cap=_env_bool("FIRETEC_ENABLE_CAP", True),
        simulation_mode=_env_bool("FIRETEC_SIMULATION", False),
    )


def main() -> None:
    signal.signal(signal.SIGINT, signal_handler)

    config = build_config()
    logger.info(
        "Configuração | switches=%s:%s | workers=%s | overpass=%s | cap=%s | simulation=%s",
        ",".join(config.switch_ips),
        config.switch_port,
        config.max_workers,
        config.enable_overpass,
        config.enable_cap,
        config.simulation_mode,
    )

    processor = AlertProcessor(config, on_alert_complete, on_alert_failed)
    processor.start()

    try:
        MainMenu(processor).run()
    finally:
        processor.stop()


if __name__ == "__main__":
    main()
