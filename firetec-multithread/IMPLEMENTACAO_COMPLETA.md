# FireTec Multithread - Guia de Implementação Completa

## Arquitetura do Sistema

### Visão Geral

O sistema FireTec Multithread processa alertas de incêndio em paralelo usando uma arquitetura de **produtor-consumidor** com:

- **Fila de Prioridades**: Ordenação de alertas por urgência
- **Pool de Workers**: N threads processando simultaneamente
- **Thread-Safe Operations**: Locks para sincronização
- **Pipeline de Processamento**: 7 etapas sequenciais por alerta

### Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────────┐
│                         AlertProcessor                          │
│  ┌──────────────────┐      ┌──────────────────┐                │
│  │ PriorityQueue    │      │ Worker Pool      │                │
│  │ (Thread-Safe)    │─────▶│ (N Threads)      │                │
│  └──────────────────┘      └──────────────────┘                │
│           │                          │                          │
│           ▼                          ▼                          │
│  ┌────────────────────────────────────────────────────┐        │
│  │              Processing Pipeline               │        │
│  │  1. AntennaService                                 │        │
│  │  2. LocationService                                │        │
│  │  3. RoadService                                    │        │
│  │  4. AudioService                                   │        │
│  │  5. CAPService                                     │        │
│  │  6. TransmissionService                            │        │
│  └────────────────────────────────────────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Estrutura de Código

### 1. Models (`src/models/alert.py`)

Define todas as estruturas de dados:

```python
@dataclass
class FireAlert:
    alert_id: str
    coordinates: Coordinates
    timestamp: datetime
    priority: AlertPriority
    status: AlertStatus
    location: Optional[Location]
    nearby_stations: List[RadioStation]
    nearby_roads: List[Road]
    message_text: Optional[str]
    audio_file: Optional[str]
    cap_file: Optional[str]
    processing_time: Optional[float]
```

**Enums:**
- `AlertStatus`: PENDING, PROCESSING, PROCESSED, SENT, FAILED
- `AlertPriority`: LOW, NORMAL, HIGH, CRITICAL

---

### 2. AlertProcessor (`src/core/alert_processor.py`)

Núcleo do sistema multithread.

#### Inicialização

```python
processor = AlertProcessor(
    config=ServerConfig(num_workers=5),
    on_alert_complete=callback_sucesso,
    on_alert_failed=callback_erro
)
processor.start()
```

#### Submissão de Alertas

```python
alert_id = processor.submit_alert(
    coordinates=Coordinates(latitude=39.5, longitude=-8.0),
    priority=AlertPriority.HIGH
)
```

#### Arquitetura Interna

**PriorityQueue:**
```python
self.alert_queue = queue.PriorityQueue(maxsize=config.queue_size)
# Items: (priority_value, timestamp, alert)
# priority_value = -priority.value (negado para ordem decrescente)
```

**Worker Loop:**
```python
def _worker_loop(self, worker_name: str):
    while self.running:
        try:
            priority, timestamp, alert = self.alert_queue.get(timeout=1)
            self._process_alert(alert, worker_name)
        except queue.Empty:
            continue
```

**Thread Safety:**
```python
self.lock = threading.Lock()  # Protege active_alerts dict
with self.lock:
    self.active_alerts[alert_id] = alert
```

---

### 3. Services

#### AntennaService (`src/services/antenna_service.py`)

Encontra estações de rádio FM próximas.

**Algoritmo:**
1. Carrega base de dados (714 estações)
2. Calcula distância com fórmula de Haversine
3. Busca com raio dinâmico (7km → 9km → 11km → ...)
4. Remove duplicados por localização
5. Retorna mínimo 5 estações

**Código Principal:**
```python
def find_nearby_stations(self, coords: Coordinates) -> List[RadioStation]:
    radius = self.initial_radius
    while True:
        stations = self._search_in_radius(coords, radius)
        stations = self._remove_duplicates(stations)
        
        if len(stations) >= self.min_stations:
            return stations[:self.min_stations]
        
        radius += self.radius_increment
```

---

#### LocationService (`src/services/location_service.py`)

Determina localidade do incêndio.

**Algoritmo:**
1. Tenta geocodificação reversa (Nominatim API)
2. Se falhar, busca na base local (171,977 localidades)
3. Encontra localidade mais próxima
4. Gera mensagem de alerta em português

**Código Principal:**
```python
def find_location(self, coords: Coordinates) -> Optional[Location]:
    # Tentar API
    location = self._geocode_nominatim(coords)
    if location:
        return location
    
    # Fallback: base local
    return self._find_nearest_locality(coords)
```

---

#### RoadService (`src/services/road_service.py`)

Encontra estradas próximas via OpenStreetMap.

**Algoritmo:**
1. Query Overpass API com raio dinâmico
2. Filtra por tipo (motorway, trunk, primary, ...)
3. Retry automático se rate limit
4. Retorna mínimo 1 estrada

**Código Principal:**
```python
def find_nearby_roads(self, coords: Coordinates) -> List[Road]:
    radius = self.initial_radius
    while True:
        roads = self._query_overpass(coords, radius)
        
        if len(roads) >= self.min_roads:
            return roads
        
        radius += self.radius_increment
```

**Query Overpass:**
```python
query = f"""
[out:json][timeout:25];
(
  way["highway"~"motorway|trunk|primary|secondary|tertiary"]
  (around:{radius},{lat},{lon});
);
out body;
"""
```

---

#### AudioService (`src/services/audio_service.py`)

Gera mensagens de áudio.

**Algoritmo:**
1. Usa Google TTS (gTTS) para português
2. Gera MP3 diretamente
3. Salva em `audio/ALERT-ID.mp3`

**Código Principal:**
```python
def generate_audio(self, text: str, alert_id: str) -> Optional[str]:
    output_file = self.output_dir / f"{alert_id}.mp3"
    
    tts = gTTS(text=text, lang="pt")
    tts.save(str(output_file))
    
    return str(output_file)
```

---

#### CAPService (`src/services/cap_service.py`)

Gera mensagens CAP XML (Common Alerting Protocol).

**Algoritmo:**
1. Cria estrutura CAP com metadados
2. Adiciona parâmetros RDS (PS, PI, AF)
3. Embebe áudio como hex
4. Salva em `cap/ALERT-ID.xml`

**Estrutura CAP:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<alert xmlns="urn:oasis:names:tc:emergency:cap:1.2">
  <identifier>ALERT-ID</identifier>
  <sender>firetec@protecaocivil.pt</sender>
  <sent>2025-12-21T12:34:56Z</sent>
  <status>Actual</status>
  <msgType>Alert</msgType>
  <scope>Public</scope>
  <info>
    <category>Fire</category>
    <event>Incêndio Florestal</event>
    <urgency>Immediate</urgency>
    <severity>Severe</severity>
    <certainty>Observed</certainty>
    <area>
      <areaDesc>Localidade</areaDesc>
      <circle>39.5,-8.0 5.0</circle>
    </area>
    <parameter>
      <valueName>RDS_PS</valueName>
      <value>FIRETEC</value>
    </parameter>
    <resource>
      <resourceDesc>Audio Alert</resourceDesc>
      <mimeType>audio/mpeg</mimeType>
      <derefUri>data:audio/mpeg;base64,...</derefUri>
    </resource>
  </info>
</alert>
```

---

#### TransmissionService (`src/services/transmission_service.py`)

Transmite para switches FireTec.

**Algoritmo:**
1. Envia CAP XML para cada switch via TCP
2. 3 tentativas por switch
3. Timeout de 5 segundos
4. Retorna dicionário de resultados

**Código Principal:**
```python
def transmit_to_switches(self, alert: FireAlert, cap_data: bytes) -> Dict:
    results = {}
    
    for switch_ip in self.switches:
        success = self._transmit_to_single_switch(switch_ip, cap_data)
        results[switch_ip] = {'success': success}
    
    return results
```

---

### 4. API REST (`src/api/rest_api.py`)

Flask API rodando em thread daemon separada.

**Inicialização:**
```python
api = FireTecAPI(processor)
api.start()  # Daemon thread
```

**Endpoints:**
```python
@app.route('/api/alert', methods=['POST'])
def create_alert():
    data = request.json
    coords = Coordinates(data['latitude'], data['longitude'])
    priority = AlertPriority[data.get('priority', 'NORMAL')]
    
    alert_id = processor.submit_alert(coords, priority)
    return jsonify({'alert_id': alert_id, 'status': 'pending'}), 201
```

---

### 5. Utilities

#### Logger (`src/utils/logger.py`)

Logging colorido com colorlog.

```python
def setup_logging(log_level: str = "INFO"):
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        '%(log_color)s%(asctime)s [%(levelname)-8s] %(name)s - %(message)s'
    ))
    
    logger = logging.getLogger()
    logger.setLevel(log_level)
    logger.addHandler(handler)
```

#### Menu (`src/utils/menu.py`)

Sistema de menu interativo.

```python
class MainMenu:
    def run(self):
        while True:
            print("\n=== FireTec Multithread ===")
            print("1. Processar alerta único")
            print("2. Processar múltiplos alertas")
            print("3. Ver estatísticas")
            print("4. Iniciar API REST")
            print("5. Sair")
            
            choice = input("\nEscolha: ")
            self._handle_choice(choice)
```

---

## Pipeline de Processamento

Cada alerta passa por 7 etapas:

```python
def _process_alert(self, alert: FireAlert, worker_name: str):
    # 1. Procurar antenas
    alert.nearby_stations = antenna_service.find_nearby_stations(
        alert.coordinates
    )
    
    # 2. Determinar localidade
    alert.location = location_service.find_location(
        alert.coordinates
    )
    
    # 3. Procurar estradas (skip em test_mode)
    if not config.test_mode:
        alert.nearby_roads = road_service.find_nearby_roads(
            alert.coordinates
        )
    
    # 4. Gerar mensagem
    alert.message_text = location_service.generate_alert_message(
        alert.location,
        alert.nearby_roads
    )
    
    # 5. Gerar áudio
    alert.audio_file = audio_service.generate_audio(
        alert.message_text,
        alert.alert_id
    )
    
    # 6. Gerar CAP XML
    audio_bytes = audio_service.read_audio_bytes(alert.audio_file)
    alert.cap_file = cap_service.generate_cap(alert, audio_bytes)
    
    # 7. Transmitir (skip em test_mode)
    if not config.test_mode:
        cap_data = cap_service.read_cap_data(alert.cap_file)
        transmission_service.transmit_to_switches(alert, cap_data)
    
    alert.status = AlertStatus.SENT
```

---

## Configuração

### ServerConfig

```python
@dataclass
class ServerConfig:
    # Dados
    antenna_csv: str = "123.csv"
    localities_csv: str = "Localidades_Portugal.csv"
    
    # Antenas
    initial_search_radius: float = 7.0  # km
    radius_increment: float = 2.0
    min_antennas: int = 5
    
    # Estradas
    initial_road_radius: int = 2000  # metros
    road_radius_increment: int = 500
    min_roads: int = 1
    
    # FireTec Switches
    switch_ips: List[str] = ["192.168.0.22", "192.168.0.21"]
    switch_port: int = 8080
    
    # Threading
    max_workers: int = 10
    queue_size: int = 100
    
    # Logging
    log_level: str = "INFO"
    
    # Test mode (skip network I/O)
    test_mode: bool = False
```

---

## Dependências

```
pandas>=2.0.0
numpy>=1.24.0
geopy>=2.3.0
shapely>=2.0.0
polycircles>=0.3.0
simplekml>=1.3.0
overpy>=0.6.0
colorlog>=6.10.0
gTTS>=2.3.0
Flask>=3.1.0
flask-cors>=6.0.0
```

---

## Melhorias Futuras

### Performance
- Cache de geocodificação (Redis)
- Pool de conexões HTTP
- Compressão de áudio

### Escalabilidade
- Message queue (RabbitMQ/Kafka)
- Distributed workers
- Load balancing

### Robustez
- Dead letter queue para falhas
- Circuit breaker para APIs externas
- Retry exponencial

### Monitorização
- Prometheus metrics
- Grafana dashboards
- Alert monitoring

---

## Testing

### Test Mode

Para testes rápidos sem network I/O:

```python
config = ServerConfig(
    num_workers=5,
    test_mode=True  # Skip Overpass API e switches
)
```

### Unit Tests

Estrutura sugerida:

```python
# tests/test_antenna_service.py
def test_find_nearby_stations():
    service = AntennaService("data/123.csv")
    coords = Coordinates(39.5, -8.0)
    stations = service.find_nearby_stations(coords)
    
    assert len(stations) >= 5
    assert all(s.distance_km > 0 for s in stations)
```

---

## Deployment

### Produção

```powershell
# 1. Instalar dependências
py -m pip install -r requirements.txt

# 2. Configurar logs
# Editar ServerConfig em main.py:
log_level="WARNING"

# 3. Executar como serviço
py main.py
```

### Docker (opcional)

```dockerfile
FROM python:3.14
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

---

## Troubleshooting

### Erro: "No module named audioop"

Python 3.14 removeu `audioop`. Sistema já usa apenas MP3 (sem pydub).

### Erro: "Overpass API: Server load too high"

Rate limiting da API. Sistema tem retry automático. Em produção, considerar cache.

### Erro: "Timeout ao conectar a switches"

Switches FireTec não estão acessíveis. Normal em ambiente de desenvolvimento. Usar `test_mode=True`.

### Performance lenta

- Aumentar `num_workers`
- Ativar `test_mode` para testes
- Verificar latência de rede (Nominatim, Overpass)
