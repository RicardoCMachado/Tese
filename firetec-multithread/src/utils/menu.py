"""
Menu interativo para teste do sistema
"""
import random
import time
from ..models.alert import Coordinates, AlertPriority


class MainMenu:
    """Menu principal interativo"""
    
    def __init__(self, processor):
        self.processor = processor
        self.running = True
    
    def run(self):
        """Loop principal do menu"""
        while self.running:
            self._show_menu()
            choice = input("\nEscolha uma opção: ").strip()
            
            if choice == '1':
                self._manual_alert()
            elif choice == '2':
                self._random_alert()
            elif choice == '3':
                self._cacia_alert()
            elif choice == '4':
                self._multiple_alerts()
            elif choice == '5':
                self._show_status()
            elif choice == '6':
                self._show_statistics()
            elif choice == '0':
                self.running = False
            else:
                print("❌ Opção inválida!")
            
            if self.running and choice != '0':
                input("\nPressione ENTER para continuar...")
    
    def _show_menu(self):
        """Exibe menu"""
        print("\n" + "="*60)
        print("  MENU PRINCIPAL  ".center(60))
        print("="*60)
        print()
        print("📍 CRIAR ALERTA:")
        print("  1 - Inserir coordenadas manualmente")
        print("  2 - Gerar coordenadas aleatórias (Portugal)")
        print("  3 - Alerta em Cacia (pré-definido)")
        print("  4 - Criar múltiplos alertas simultâneos (TESTE)")
        print()
        print("📊 MONITORIZAÇÃO:")
        print("  5 - Ver status dos alertas")
        print("  6 - Ver estatísticas do sistema")
        print()
        print("  0 - Sair")
        print("="*60)
    
    def _manual_alert(self):
        """Criar alerta com coordenadas manuais"""
        print("\n📍 INSERIR COORDENADAS MANUALMENTE")
        print("-" * 60)
        print("Portugal Continental:")
        print("  Latitude:  37.16 a 41.90 (Sul-Norte)")
        print("  Longitude: -9.59 a -7.06 (Oeste-Este)")
        print()
        
        try:
            lat = float(input("Latitude: "))
            lon = float(input("Longitude: "))
            
            # Validação básica
            if not (37.0 <= lat <= 42.0):
                print("⚠️  Latitude fora do intervalo esperado")
            if not (-10.0 <= lon <= -6.0):
                print("⚠️  Longitude fora do intervalo esperado")
            
            priority_choice = input(
                "Prioridade? (1=Normal, 2=Alta, 3=Crítica) [1]: "
            ).strip() or "1"
            
            priority = AlertPriority.NORMAL
            if priority_choice == "2":
                priority = AlertPriority.HIGH
            elif priority_choice == "3":
                priority = AlertPriority.CRITICAL
            
            coords = Coordinates(latitude=lat, longitude=lon)
            alert_id = self.processor.submit_alert(coords, priority)
            
            print(f"\n✅ Alerta submetido: {alert_id}")
            print(f"   Coordenadas: {coords}")
            print(f"   Prioridade: {priority.name}")
        
        except ValueError as e:
            print(f"❌ Erro: Coordenadas inválidas - {e}")
        except Exception as e:
            print(f"❌ Erro: {e}")
    
    def _random_alert(self):
        """Criar alerta com coordenadas aleatórias"""
        print("\n🎲 GERAR COORDENADAS ALEATÓRIAS")
        print("-" * 60)
        
        # Limites de Portugal Continental
        lat = round(random.uniform(37.275684, 41.765498), 6)
        lon = round(random.uniform(-8.586549, -7.356487), 6)
        
        coords = Coordinates(latitude=lat, longitude=lon)
        alert_id = self.processor.submit_alert(coords)
        
        print(f"Coordenadas geradas: {coords}")
        print(f"✅ Alerta submetido: {alert_id}")
    
    def _cacia_alert(self):
        """Criar alerta em Cacia (pré-definido)"""
        print("\n📍 ALERTA EM CACIA")
        print("-" * 60)
        
        coords = Coordinates(latitude=40.682352, longitude=-8.63209)
        alert_id = self.processor.submit_alert(coords)
        
        print(f"Localização: Cacia, Aveiro")
        print(f"Coordenadas: {coords}")
        print(f"✅ Alerta submetido: {alert_id}")
    
    def _multiple_alerts(self):
        """Criar múltiplos alertas simultâneos (teste de concorrência)"""
        print("\n🔥 CRIAR MÚLTIPLOS ALERTAS SIMULTÂNEOS")
        print("-" * 60)
        
        try:
            num = int(input("Quantos alertas criar? [3]: ").strip() or "3")
            
            if num > 20:
                print("⚠️  Limite: 20 alertas")
                num = 20
            
            print(f"\nCriando {num} alertas...")
            
            alert_ids = []
            for i in range(num):
                lat = round(random.uniform(37.3, 41.7), 6)
                lon = round(random.uniform(-8.5, -7.4), 6)
                
                coords = Coordinates(latitude=lat, longitude=lon)
                
                # Variar prioridades
                if i == 0:
                    priority = AlertPriority.CRITICAL
                elif i < num // 2:
                    priority = AlertPriority.HIGH
                else:
                    priority = AlertPriority.NORMAL
                
                alert_id = self.processor.submit_alert(coords, priority)
                alert_ids.append(alert_id)
                
                print(f"  {i+1}. {alert_id} - {priority.name}")
                time.sleep(0.1)  # Pequeno delay
            
            print(f"\n✅ {num} alertas submetidos!")
            print("Os alertas estão a ser processados em paralelo...")
        
        except ValueError:
            print("❌ Número inválido")
        except Exception as e:
            print(f"❌ Erro: {e}")
    
    def _show_status(self):
        """Mostrar status dos alertas ativos"""
        print("\n📊 STATUS DOS ALERTAS")
        print("=" * 60)
        
        stats = self.processor.get_statistics()
        
        print(f"Alertas na fila: {stats['queue_size']}")
        print(f"Alertas ativos: {stats['active_alerts']}")
        print(f"Workers disponíveis: {stats['workers']}/{stats['max_workers']}")
        print()
        
        # Mostrar alertas ativos
        with self.processor.alerts_lock:
            if not self.processor.active_alerts:
                print("Nenhum alerta ativo no momento.")
            else:
                print("ALERTAS ATIVOS:")
                print("-" * 60)
                for alert_id, alert in self.processor.active_alerts.items():
                    status_icon = {
                        'pending': '⏳',
                        'processing': '⚙️',
                        'processed': '✅',
                        'sent': '📡',
                        'failed': '❌'
                    }.get(alert.status.value, '❓')
                    
                    print(f"{status_icon} {alert_id}")
                    print(f"   Status: {alert.status.value.upper()}")
                    print(f"   Coordenadas: {alert.coordinates}")
                    print(f"   Hora: {alert.timestamp.strftime('%H:%M:%S')}")
                    if alert.location:
                        print(f"   Localidade: {alert.location}")
                    if alert.processing_time:
                        print(f"   Tempo: {alert.processing_time:.2f}s")
                    print()
    
    def _show_statistics(self):
        """Mostrar estatísticas gerais"""
        print("\n📈 ESTATÍSTICAS DO SISTEMA")
        print("=" * 60)
        
        stats = self.processor.get_statistics()
        
        total = stats['processed_total'] + stats['failed_total']
        success_rate = (stats['processed_total'] / total * 100) if total > 0 else 0
        
        print(f"Total processado: {stats['processed_total']}")
        print(f"Total falhado: {stats['failed_total']}")
        print(f"Taxa de sucesso: {success_rate:.1f}%")
        print()
        print(f"Fila atual: {stats['queue_size']} alertas")
        print(f"Alertas ativos: {stats['active_alerts']}")
        print(f"Workers: {stats['workers']} (máx: {stats['max_workers']})")
        print()
        
        # Estatísticas dos serviços
        print("SERVIÇOS:")
        print(f"  Antenas carregadas: {len(self.processor.antenna_service.stations)}")
        print(f"  Localidades: {len(self.processor.location_service.localities_data)}")
