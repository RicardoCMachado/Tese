"""
Serviço para transmissão de alertas aos switches FireTec
"""
import socket
import time
from typing import List, Optional
from ..models.alert import FireAlert, ServerConfig
import logging

logger = logging.getLogger(__name__)


class TransmissionService:
    """Serviço para transmitir alertas aos switches FireTec"""
    
    def __init__(self, config: ServerConfig):
        """
        Args:
            config: Configuração do servidor
        """
        self.config = config
        self.switch_ips = config.switch_ips
        self.switch_port = config.switch_port
        self.connection_timeout = 5  # segundos
        self.retry_attempts = 3
        self.retry_delay = 0.5  # segundos
    
    def transmit_to_switches(
        self, 
        alert: FireAlert,
        cap_data: bytes
    ) -> dict:
        """
        Transmite alerta para todos os switches configurados
        
        Args:
            alert: Alerta de incêndio
            cap_data: Dados CAP XML em bytes
        
        Returns:
            Dicionário com resultados da transmissão para cada switch
        """
        logger.info(
            f"[{alert.alert_id}] Transmitindo para {len(self.switch_ips)} switches"
        )
        
        results = {}
        
        for switch_ip in self.switch_ips:
            result = self._transmit_to_single_switch(
                alert.alert_id,
                switch_ip,
                cap_data
            )
            results[switch_ip] = result
        
        # Resumo
        success_count = sum(1 for r in results.values() if r['success'])
        logger.info(
            f"[{alert.alert_id}] Transmissão: {success_count}/{len(self.switch_ips)} "
            f"switches OK"
        )
        
        return results
    
    def _transmit_to_single_switch(
        self,
        alert_id: str,
        switch_ip: str,
        data: bytes
    ) -> dict:
        """
        Transmite para um único switch com retry
        
        Args:
            alert_id: ID do alerta
            switch_ip: IP do switch
            data: Dados a transmitir
        
        Returns:
            Dicionário com resultado da transmissão
        """
        result = {
            'success': False,
            'attempts': 0,
            'error': None,
            'duration': 0
        }
        
        start_time = time.time()
        
        for attempt in range(1, self.retry_attempts + 1):
            result['attempts'] = attempt
            
            try:
                logger.debug(
                    f"[{alert_id}] Tentativa {attempt}/{self.retry_attempts} "
                    f"para {switch_ip}"
                )
                
                # Criar socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.connection_timeout)
                
                # Conectar
                sock.connect((switch_ip, self.switch_port))
                logger.debug(f"[{alert_id}] Conectado a {switch_ip}:{self.switch_port}")
                
                # Enviar dados
                sock.sendall(data)
                logger.debug(
                    f"[{alert_id}] {len(data)} bytes enviados para {switch_ip}"
                )
                
                # Fechar conexão
                sock.close()
                
                # Sucesso!
                result['success'] = True
                result['duration'] = time.time() - start_time
                
                logger.info(
                    f"[{alert_id}] ✓ Switch {switch_ip} OK "
                    f"({result['duration']:.2f}s)"
                )
                
                break  # Sair do loop de retry
            
            except socket.timeout:
                error_msg = f"Timeout ao conectar a {switch_ip}"
                logger.warning(f"[{alert_id}] {error_msg}")
                result['error'] = error_msg
            
            except socket.error as e:
                error_msg = f"Erro de socket: {e}"
                logger.warning(f"[{alert_id}] {error_msg}")
                result['error'] = error_msg
            
            except Exception as e:
                error_msg = f"Erro inesperado: {e}"
                logger.error(
                    f"[{alert_id}] {error_msg}",
                    exc_info=True
                )
                result['error'] = error_msg
            
            finally:
                try:
                    sock.close()
                except:
                    pass
            
            # Aguardar antes de retry (exceto na última tentativa)
            if attempt < self.retry_attempts:
                time.sleep(self.retry_delay)
        
        # Se falhou após todas as tentativas
        if not result['success']:
            logger.error(
                f"[{alert_id}] ✗ Switch {switch_ip} FALHOU "
                f"após {result['attempts']} tentativas"
            )
        
        result['duration'] = time.time() - start_time
        return result
    
    def test_switch_connection(self, switch_ip: str) -> bool:
        """
        Testa conexão com um switch
        
        Args:
            switch_ip: IP do switch
        
        Returns:
            True se conseguiu conectar, False caso contrário
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect((switch_ip, self.switch_port))
            sock.close()
            
            logger.info(f"✓ Switch {switch_ip} acessível")
            return True
        
        except Exception as e:
            logger.warning(f"✗ Switch {switch_ip} não acessível: {e}")
            return False
    
    def test_all_switches(self) -> dict:
        """
        Testa conexão com todos os switches
        
        Returns:
            Dicionário com status de cada switch
        """
        logger.info("Testando conexão com switches...")
        
        results = {}
        for switch_ip in self.switch_ips:
            results[switch_ip] = self.test_switch_connection(switch_ip)
        
        available = sum(1 for status in results.values() if status)
        logger.info(
            f"Switches disponíveis: {available}/{len(self.switch_ips)}"
        )
        
        return results
