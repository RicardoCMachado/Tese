"""
FireTec Multithread Server - Sistema Principal
Dissertação de Mestrado - Ricardo Machado
"""
import sys
import signal
import logging
import random
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.models.alert import ServerConfig, Coordinates, AlertPriority
from src.core.alert_processor import AlertProcessor
from src.utils.logger import setup_logging
from src.utils.menu import MainMenu

# Configurar logging
setup_logging()
logger = logging.getLogger(__name__)

# Flag global para shutdown suave
shutdown_requested = False


def on_alert_complete(alert):
    """Callback quando alerta é processado com sucesso"""
    logger.info(f"✓ ALERTA COMPLETO: {alert.alert_id}")
    logger.info(f"  Localização: {alert.location}")
    logger.info(f"  Antenas: {len(alert.nearby_stations)}")
    logger.info(f"  Estradas: {len(alert.nearby_roads)}")
    logger.info(f"  Tempo: {alert.processing_time:.2f}s")
    logger.info(f"  Mensagem: {alert.message_text}")
    print("\n" + "="*60)
    print(f"✓ ALERTA {alert.alert_id} PROCESSADO")
    print(f"Localidade: {alert.location}")
    print(f"Mensagem: {alert.message_text}")
    print(f"Tempo de processamento: {alert.processing_time:.2f}s")
    print("="*60 + "\n")


def on_alert_failed(alert):
    """Callback quando alerta falha"""
    logger.error(f"✗ ALERTA FALHOU: {alert.alert_id}")
    logger.error(f"  Erro: {alert.error_message}")
    print(f"\n✗ ERRO: Alerta {alert.alert_id} falhou!")
    print(f"Erro: {alert.error_message}\n")


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
    print()
    print("="*70)
    print("  FIRETEC MULTITHREAD SERVER  ".center(70))
    print("  Sistema de Alerta de Incêndios por Rádio FM  ".center(70))
    print("="*70)
    print()
    print("Dissertação de Mestrado - 2025/2026")
    print("Aluno: Ricardo Machado")
    print("Orientador: Prof. António Navarro")
    print()
    print("="*70)
    print()
    print()
    
    # Verificar ficheiros de dados
    data_dir = Path(__file__).parent / "data"
    if not (data_dir / "123.csv").exists():
        print("⚠️  AVISO: Ficheiro '123.csv' não encontrado em /data/")
        print("   Copie os ficheiros CSV para a pasta 'data/'")
        print()
    
    if not (data_dir / "Localidades_Portugal.csv").exists():
        print("⚠️  AVISO: Ficheiro 'Localidades_Portugal.csv' não encontrado")
        print()
    
    # Configuração
    config = ServerConfig(
        antenna_csv=str(data_dir / "123.csv"),
        localities_csv=str(data_dir / "Localidades_Portugal.csv"),
        max_workers=5,  
        queue_size=50,
        test_mode=False  # Se True: desativa chamadas externas (Overpass + Switches)
    )
    
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
