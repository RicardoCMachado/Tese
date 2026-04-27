"""
Menu interativo do sistema FireTec.
"""
from collections import deque
import msvcrt
import os
import random
import re
import sys
import threading
import time
from ..models.alert import Coordinates, AlertPriority


class MainMenu:
    """Menu principal interativo."""
    _active_instance = None

    def __init__(self, processor):
        self.processor = processor
        self.running = True
        self._io_lock = threading.Lock()
        self._event_log = deque(maxlen=200)
        self._screen_dirty = True
        self._input_active = False
        self._prompt_text = ""
        self._prompt_buffer = ""
        MainMenu._active_instance = self

    @classmethod
    def get_active(cls):
        return cls._active_instance

    def emit_message(self, message: str):
        """Guarda mensagem no histórico e redesenha o ecrã quando seguro."""
        with self._io_lock:
            self._append_event(message)
            self._screen_dirty = True
            self._render_screen()

    def run(self):
        """Loop principal do menu."""
        self._render_screen()

        while self.running:
            choice = self._prompt("Escolha uma opção: ").strip()

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
            elif choice == "6":
                self._test_switches()
            elif choice == "0":
                self.running = False
            else:
                self.emit_message("Opção inválida.")

    def _show_menu(self):
        """Exibe o menu principal."""
        for line in self._build_menu_lines():
            print(line)

    def _build_menu_lines(self):
        """Constroi linhas do menu principal."""
        stats = self.processor.get_statistics()
        hardware = "ON" if self.processor.config.hardware_enabled else "OFF"

        return [
            "=" * 64,
            "FIRETEC MULTITHREAD SERVER".center(64),
            "=" * 64,
            f"Hardware: {hardware} | "
            f"Fila: {stats['queue_size']} | "
            f"Ativos: {stats['active_alerts']} | "
            f"Workers ocupados: {stats['busy_workers']}/{stats['max_workers']}",
            "-" * 64,
            "Criar alerta",
            "  1  Inserir coordenadas manualmente",
            "  2  Gerar coordenadas aleatórias em Portugal",
            "  3  Criar múltiplos alertas simultâneos",
            "",
            "Monitorização",
            "  4  Ver estado dos alertas",
            "  5  Ver estatísticas do sistema",
            "",
            "  6  Testar ligacao aos switches",
            "  0  Sair",
            "=" * 64,
        ]

    def _manual_alert(self):
        """Criar alerta com coordenadas manuais."""
        self.emit_message(
            "\nINSERIR COORDENADAS\n"
            + "-" * 64 + "\n"
            "Portugal Continental:\n"
            "  Latitude:   37.16 a 41.90\n"
            "  Longitude: -9.59 a -7.06\n"
            "  Exemplo: 40.629504, -8.650095\n"
        )

        try:
            raw = self._prompt("Coordenadas (lat,lon): ").strip()
            lat, lon = self._parse_manual_coordinates(raw)

            if not (37.0 <= lat <= 42.0):
                self.emit_message("Aviso: latitude fora do intervalo esperado.")
            if not (-10.0 <= lon <= -6.0):
                self.emit_message("Aviso: longitude fora do intervalo esperado.")

            priority = self._ask_priority()
            coords = Coordinates(latitude=lat, longitude=lon)
            alert_id = self.processor.submit_alert(coords, priority)

            self.emit_message(
                "\nAlerta submetido.\n"
                f"  ID: {alert_id}\n"
                f"  Coordenadas: {coords}\n"
                f"  Prioridade: {priority.name}"
            )

        except ValueError as e:
            self.emit_message(f"Erro: coordenadas inválidas ({e}).")
        except Exception as e:
            self.emit_message(f"Erro: {e}")

    def _parse_manual_coordinates(self, raw_value: str) -> tuple[float, float]:
        """Aceita coordenadas no formato 'lat, lon' e variações simples."""
        if not raw_value:
            raise ValueError("entrada vazia")

        values = re.findall(r"[-+]?\d+(?:\.\d+)?", raw_value)
        if len(values) != 2:
            raise ValueError(
                "use o formato 40.629504, -8.650095"
            )

        return float(values[0]), float(values[1])

    def _random_alert(self):
        """Criar alerta com coordenadas aleatórias."""
        self.emit_message("\nCOORDENADAS ALEATÓRIAS\n" + "-" * 64)

        lat = round(random.uniform(37.275684, 41.765498), 6)
        lon = round(random.uniform(-8.586549, -7.356487), 6)

        coords = Coordinates(latitude=lat, longitude=lon)
        alert_id = self.processor.submit_alert(coords)

        self.emit_message(
            "Alerta submetido.\n"
            f"  ID: {alert_id}\n"
            f"  Coordenadas: {coords}"
        )

    def _multiple_alerts(self):
        """Criar múltiplos alertas simultâneos."""
        self.emit_message("\nMÚLTIPLOS ALERTAS\n" + "-" * 64)

        try:
            num = int(self._prompt("Quantos alertas criar?: ").strip() or "3")

            if num < 1:
                self.emit_message("Nada para criar.")
                return
            if num > 20:
                self.emit_message("Limite aplicado: 20 alertas.")
                num = 20

            self.emit_message(f"\nA criar {num} alertas...")

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
                self.emit_message(
                    f"  {i + 1:02d}. {alert_id} | {priority.name} | {coords}"
                )
                time.sleep(0.1)

            self.emit_message("\nAlertas submetidos. O processamento continua em paralelo.")

        except ValueError:
            self.emit_message("Erro: número inválido.")
        except Exception as e:
            self.emit_message(f"Erro: {e}")

    def _show_status(self):
        """Mostrar estado dos alertas ativos."""
        stats = self.processor.get_statistics()
        lines = [
            "\nESTADO DOS ALERTAS",
            "=" * 64,
            f"Fila: {stats['queue_size']}",
            f"Ativos: {stats['active_alerts']}",
            (
                f"Workers ocupados: {stats['busy_workers']}/{stats['max_workers']} | "
                f"Disponíveis: {stats['available_workers']}"
            ),
            "-" * 64,
        ]

        with self.processor.alerts_lock:
            if not self.processor.active_alerts:
                lines.append("Nenhum alerta ativo.")
                self.emit_message("\n".join(lines))
                return

            for alert_id, alert in self.processor.active_alerts.items():
                lines.append(f"{alert_id}")
                lines.append(f"  Estado: {alert.status.value.upper()}")
                lines.append(f"  Coordenadas: {alert.coordinates}")
                lines.append(f"  Hora: {alert.timestamp.strftime('%H:%M:%S')}")
                if alert.location:
                    lines.append(f"  Localidade: {alert.location}")
                if alert.processing_time:
                    lines.append(f"  Tempo: {alert.processing_time:.2f}s")
                if alert.queue_wait_time is not None:
                    lines.append(f"  Espera em fila: {alert.queue_wait_time:.2f}s")
                lines.append("")

        self.emit_message("\n".join(lines))

    def _show_statistics(self):
        """Mostrar estatísticas gerais."""
        stats = self.processor.get_statistics()
        total = stats["processed_total"] + stats["failed_total"]
        success_rate = (stats["processed_total"] / total * 100) if total > 0 else 0

        self.emit_message(
            "\nESTATÍSTICAS\n"
            + "=" * 64 + "\n"
            f"Processados: {stats['processed_total']}\n"
            f"Falhados: {stats['failed_total']}\n"
            f"Taxa de sucesso: {success_rate:.1f}%\n"
            f"Fila atual: {stats['queue_size']}\n"
            f"Alertas ativos: {stats['active_alerts']}\n"
            f"Workers ocupados: {stats['busy_workers']}/{stats['max_workers']}\n"
            f"Workers disponíveis: {stats['available_workers']}\n"
            + "-" * 64 + "\n"
            f"Antenas carregadas: {len(self.processor.antenna_service.stations)}\n"
            f"Localidades: {len(self.processor.location_service.localities_data)}\n"
            f"Pontos de estrada: {len(self.processor.road_service.road_points)}"
        )

    def _test_switches(self):
        """Testa ligacao TCP aos switches configurados."""
        if not self.processor.config.hardware_enabled:
            self.emit_message(
                "\nTESTE DE SWITCHES\n"
                + "=" * 64 + "\n"
                "Hardware OFF. Define FIRETEC_HARDWARE_ENABLED=true para testar."
            )
            return

        self.emit_message(
            "\nTESTE DE SWITCHES\n"
            + "=" * 64 + "\n"
            "A testar ligacao TCP aos switches configurados..."
        )

        results = self.processor.transmission_service.test_all_switches()
        available = sum(1 for status in results.values() if status)

        lines = [
            "",
            "RESULTADO DO TESTE DE SWITCHES",
            "=" * 64,
            f"Switches acessiveis: {available}/{len(results)}",
        ]

        for switch_ip, is_available in results.items():
            state = "OK" if is_available else "FALHOU"
            lines.append(f"  {switch_ip}: {state}")

        if available == 0:
            lines.append("Nenhum switch respondeu ao teste de ligacao.")
        elif available < len(results):
            lines.append("Ligacao parcial: pelo menos um switch nao respondeu.")
        else:
            lines.append("Todos os switches responderam ao teste de ligacao.")

        self.emit_message("\n".join(lines))

    def _ask_priority(self) -> AlertPriority:
        choice = self._prompt("Prioridade (1=Normal, 2=Alta, 3=Crítica) [1]: ").strip() or "1"
        if choice == "2":
            return AlertPriority.HIGH
        if choice == "3":
            return AlertPriority.CRITICAL
        return AlertPriority.NORMAL

    def _prompt(self, prompt: str) -> str:
        """Prompt manual para permitir refresh do ecrã durante espera."""
        with self._io_lock:
            self._input_active = True
            self._prompt_text = prompt
            self._prompt_buffer = ""
            self._render_screen()

        last_render = time.time()

        while True:
            if msvcrt.kbhit():
                key = msvcrt.getwch()

                if key in ("\r", "\n"):
                    value = self._prompt_buffer
                    with self._io_lock:
                        self._append_event(f"{self._prompt_text}{self._prompt_buffer}")
                        self._prompt_buffer = ""
                        self._prompt_text = ""
                        self._input_active = False
                        self._screen_dirty = True
                        self._render_screen()
                    return value

                if key == "\003":
                    raise KeyboardInterrupt

                if key == "\b":
                    with self._io_lock:
                        self._prompt_buffer = self._prompt_buffer[:-1]
                        self._screen_dirty = True
                    continue

                if key in ("\x00", "\xe0"):
                    if msvcrt.kbhit():
                        msvcrt.getwch()
                    continue

                if key.isprintable():
                    with self._io_lock:
                        self._prompt_buffer += key
                        self._screen_dirty = True
                    continue

            now = time.time()
            if now - last_render >= 0.2:
                with self._io_lock:
                    self._screen_dirty = True
                    self._render_screen()
                last_render = now

            time.sleep(0.02)

    def _append_event(self, message: str):
        text = message.replace("\r\n", "\n").replace("\r", "\n")
        for line in text.split("\n"):
            self._event_log.append(line)

    def _render_screen(self):
        """Desenha menu e histórico de forma robusta após resize."""
        menu_lines = self._build_menu_lines()
        terminal_height = 30
        if sys.stdout.isatty():
            try:
                terminal_height = os.get_terminal_size().lines
            except OSError:
                terminal_height = 30
        available_log_lines = max(3, terminal_height - len(menu_lines) - 2)
        visible_log = list(self._event_log)[-available_log_lines:]

        self._clear_screen()
        for line in menu_lines:
            print(line)
        print()
        for line in visible_log:
            print(line)
        if self._input_active:
            print(f"{self._prompt_text}{self._prompt_buffer}", end="", flush=True)
        self._screen_dirty = False
        sys.stdout.flush()

    def _clear_screen(self):
        if os.name == "nt":
            os.system("cls")
        else:
            os.system("clear")

    def _write(self, value: str):
        sys.stdout.write(value)
