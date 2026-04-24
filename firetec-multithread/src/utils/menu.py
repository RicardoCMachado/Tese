"""
Menu interativo do sistema FireTec.
"""
import random
import time
from ..models.alert import Coordinates, AlertPriority


class MainMenu:
    """Menu principal interativo."""

    def __init__(self, processor):
        self.processor = processor
        self.running = True

    def run(self):
        """Loop principal do menu."""
        while self.running:
            self._show_menu()
            choice = input("\nEscolha uma opção: ").strip()

            if choice == "1":
                self._manual_alert()
            elif choice == "2":
                self._random_alert()
            elif choice == "3":
                self._multiple_alerts()
            elif choice == "4":
                self._show_status()
            elif choice == "5":
                self._show_statistics()
            elif choice == "0":
                self.running = False
            else:
                print("Opção inválida.")

            if self.running and choice != "0":
                input("\nPressione ENTER para continuar...")

    def _show_menu(self):
        """Exibe o menu principal."""
        stats = self.processor.get_statistics()
        hardware = "ON" if self.processor.config.hardware_enabled else "OFF"

        print("\n" + "=" * 64)
        print("FIRETEC MULTITHREAD SERVER".center(64))
        print("=" * 64)
        print(
            f"Hardware: {hardware} | "
            f"Fila: {stats['queue_size']} | "
            f"Ativos: {stats['active_alerts']} | "
            f"Workers: {stats['workers']}/{stats['max_workers']}"
        )
        print("-" * 64)
        print("Criar alerta")
        print("  1  Inserir coordenadas manualmente")
        print("  2  Gerar coordenadas aleatórias em Portugal")
        print("  3  Criar múltiplos alertas simultâneos")
        print()
        print("Monitorização")
        print("  4  Ver estado dos alertas")
        print("  5  Ver estatísticas do sistema")
        print()
        print("  0  Sair")
        print("=" * 64)

    def _manual_alert(self):
        """Criar alerta com coordenadas manuais."""
        print("\nINSERIR COORDENADAS")
        print("-" * 64)
        print("Portugal Continental:")
        print("  Latitude:   37.16 a 41.90")
        print("  Longitude: -9.59 a -7.06")
        print()

        try:
            lat = float(input("Latitude: ").strip())
            lon = float(input("Longitude: ").strip())

            if not (37.0 <= lat <= 42.0):
                print("Aviso: latitude fora do intervalo esperado.")
            if not (-10.0 <= lon <= -6.0):
                print("Aviso: longitude fora do intervalo esperado.")

            priority = self._ask_priority()
            coords = Coordinates(latitude=lat, longitude=lon)
            alert_id = self.processor.submit_alert(coords, priority)

            print("\nAlerta submetido.")
            print(f"  ID: {alert_id}")
            print(f"  Coordenadas: {coords}")
            print(f"  Prioridade: {priority.name}")

        except ValueError as e:
            print(f"Erro: coordenadas inválidas ({e}).")
        except Exception as e:
            print(f"Erro: {e}")

    def _random_alert(self):
        """Criar alerta com coordenadas aleatórias."""
        print("\nCOORDENADAS ALEATÓRIAS")
        print("-" * 64)

        lat = round(random.uniform(37.275684, 41.765498), 6)
        lon = round(random.uniform(-8.586549, -7.356487), 6)

        coords = Coordinates(latitude=lat, longitude=lon)
        alert_id = self.processor.submit_alert(coords)

        print("Alerta submetido.")
        print(f"  ID: {alert_id}")
        print(f"  Coordenadas: {coords}")

    def _multiple_alerts(self):
        """Criar múltiplos alertas simultâneos."""
        print("\nMÚLTIPLOS ALERTAS")
        print("-" * 64)

        try:
            num = int(input("Quantos alertas criar?: ").strip() or "3")

            if num < 1:
                print("Nada para criar.")
                return
            if num > 20:
                print("Limite aplicado: 20 alertas.")
                num = 20

            print(f"\nA criar {num} alertas...")

            for i in range(num):
                lat = round(random.uniform(37.3, 41.7), 6)
                lon = round(random.uniform(-8.5, -7.4), 6)
                coords = Coordinates(latitude=lat, longitude=lon)

                if i == 0:
                    priority = AlertPriority.CRITICAL
                elif i < num // 2:
                    priority = AlertPriority.HIGH
                else:
                    priority = AlertPriority.NORMAL

                alert_id = self.processor.submit_alert(coords, priority)
                print(f"  {i + 1:02d}. {alert_id} | {priority.name} | {coords}")
                time.sleep(0.1)

            print("\nAlertas submetidos. O processamento continua em paralelo.")

        except ValueError:
            print("Erro: número inválido.")
        except Exception as e:
            print(f"Erro: {e}")

    def _show_status(self):
        """Mostrar estado dos alertas ativos."""
        print("\nESTADO DOS ALERTAS")
        print("=" * 64)

        stats = self.processor.get_statistics()
        print(f"Fila: {stats['queue_size']}")
        print(f"Ativos: {stats['active_alerts']}")
        print(f"Workers: {stats['workers']}/{stats['max_workers']}")
        print("-" * 64)

        with self.processor.alerts_lock:
            if not self.processor.active_alerts:
                print("Nenhum alerta ativo.")
                return

            for alert_id, alert in self.processor.active_alerts.items():
                print(f"{alert_id}")
                print(f"  Estado: {alert.status.value.upper()}")
                print(f"  Coordenadas: {alert.coordinates}")
                print(f"  Hora: {alert.timestamp.strftime('%H:%M:%S')}")
                if alert.location:
                    print(f"  Localidade: {alert.location}")
                if alert.processing_time:
                    print(f"  Tempo: {alert.processing_time:.2f}s")
                print()

    def _show_statistics(self):
        """Mostrar estatísticas gerais."""
        print("\nESTATÍSTICAS")
        print("=" * 64)

        stats = self.processor.get_statistics()
        total = stats["processed_total"] + stats["failed_total"]
        success_rate = (stats["processed_total"] / total * 100) if total > 0 else 0

        print(f"Processados: {stats['processed_total']}")
        print(f"Falhados: {stats['failed_total']}")
        print(f"Taxa de sucesso: {success_rate:.1f}%")
        print(f"Fila atual: {stats['queue_size']}")
        print(f"Alertas ativos: {stats['active_alerts']}")
        print(f"Workers: {stats['workers']}/{stats['max_workers']}")
        print("-" * 64)
        print(f"Antenas carregadas: {len(self.processor.antenna_service.stations)}")
        print(f"Localidades: {len(self.processor.location_service.localities_data)}")
        print(f"Pontos de estrada: {len(self.processor.road_service.road_points)}")

    def _ask_priority(self) -> AlertPriority:
        choice = input("Prioridade (1=Normal, 2=Alta, 3=Crítica) [1]: ").strip() or "1"
        if choice == "2":
            return AlertPriority.HIGH
        if choice == "3":
            return AlertPriority.CRITICAL
        return AlertPriority.NORMAL
