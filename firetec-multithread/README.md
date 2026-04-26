# FireTec - Sistema de Alerta de Incêndios por Rádio FM

**Dissertação de Mestrado - Ricardo Machado**  
**Orientador:** Prof. António Navarro  
**Ano Letivo:** 2025/2026

---

## 📅 Planeamento

| Fase | Período | Estado |
|------|---------|--------|
| **Desenvolvimento Técnico Final** | 26 Fev - 6 Abr 2026 | ✅ Concluído |
| **Torneios (pausa técnica)** | 7 Abr - 21 Abr 2026 | ✅ Concluído |
| **Escrita da Dissertação** | 22 Abr - 5 Jun 2026 | 🔄 Em curso (10%) |
| **Entrega Final** | **6 Junho 2026** | 🎯 Deadline |

> **Estado a 26 Abril 2026:** sistema funcional para testes locais e com preparação para hardware; foco principal atual na redação da dissertação até à entrega de 6 Junho 2026.

---

## 🎯 Objetivos

### Objetivo Principal
Desenvolver um sistema multithread de alerta de incêndios que utilize a rede de rádio FM existente em Portugal para difusão automática de alertas georeferenciados.

### Objetivos Específicos
- ✅ Processamento paralelo de alertas (5 workers)
- ✅ Geolocalização automática via Nominatim
- ✅ Identificação de estações FM próximas (714 estações)
- ✅ Deteção de estradas afetadas via OpenStreetMap
- ✅ Geração de áudio em português (gTTS)
- ✅ Protocolo CAP (Common Alerting Protocol)
- ⏳ Testes com hardware FireTec real

---

## 📊 Estado Atual

### ✅ Implementado (Atualizado 26 Abr 2026)

**Core do Sistema:**
- Arquitetura multithread com 5 workers **✅ THREAD-SAFE**
- Sistema de prioridades (LOW, NORMAL, HIGH, CRITICAL)
- Fila de processamento com PriorityQueue
- Logging completo
- Shutdown suave (Ctrl+C)

**Serviços:**
- `AntennaService` - 714 estações FM **✅ Com validação de dados**
- `LocationService` - 171,977 localidades **✅ Thread-safe (Nominatim por request)**
- `RoadService` - Estradas próximas via CSV local gerado do GeoPackage da Geofabrik
- `AudioService` - Mensagens de voz em português
- `CAPService` - Geração de XML CAP **✅ PS/PI de estações reais**
- `TransmissionService` - Envio para switches FireTec **✅ Socket sempre fechado**

**Interface:**
- Menu interativo via terminal
- Opções: criar alerta manual, aleatório, múltiplos alertas
- Visualização de estatísticas em tempo real

### ⏳ Pendente

**Sistema:**
- Testes com switches FireTec reais **(prioridade máxima)**
- Atualização periódica do CSV local de estradas
- Caching de resultados de geocoding
- Testes de carga e stress

**Dissertação:**
- Escrita global em curso **(10%)**
- Revisão bibliográfica completa
- Diagramas de arquitetura
- Análise de resultados
- Discussão e conclusões
- Trabalho futuro

---

## 🔧 Correções Críticas (26 Fev 2026)

### Problemas Corrigidos:
1. ✅ **Thread Safety**: Nominatim criado por request; estradas consultadas localmente sem API externa
2. ✅ **Switch Compatibility**: PS/PI de estações reais em vez de hardcoded
3. ✅ **Socket Management**: Sempre fechado corretamente
4. ✅ **Data Validation**: CSV com validação de campos obrigatórios
5. ✅ **MIME Types**: audio/mpeg correto para MP3

**📄 Detalhes**: Ver documentação completa em SECURITY_AND_IMPROVEMENTS.md

---

## 🚀 Execução

### Windows CMD

O fluxo principal deste projeto passa por correr localmente em Windows, no `cmd`, com Python `3.11`.

1. Entrar na pasta do projeto:

```bat
cd C:\Users\PcVIP\Desktop\Tese\firetec-multithread
```

2. Criar o ambiente virtual em Python 3.11 e ativá-lo:

```bat
python -m venv .venv
.venv\Scripts\activate
python -V
```

O `python -V` deve mostrar `Python 3.11.x`.

3. Instalar dependências:

```bat
python -m pip install --upgrade pip
pip install -r requirements.txt
```

4. Garantir que os ficheiros de dados existem em `data\`:
- `123.csv`
- `Localidades_Portugal.csv`
- `roads_portugal.csv`

Se ainda não existir `roads_portugal.csv`, gera-o a partir do GeoPackage da Geofabrik:

```bat
python scripts\build_roads_csv.py --input data\portugal.gpkg --output data\roads_portugal.csv
```

5. Correr o sistema:

```bat
python main.py
```

### Windows CMD Sem Hardware

Para desenvolvimento normal, testes do menu e processamento sem switch físico:

```bat
set FIRETEC_HARDWARE_ENABLED=false
set FIRETEC_MAX_WORKERS=5
set FIRETEC_QUEUE_SIZE=50

python main.py
```

### Windows CMD Com Hardware

Para testar com a montagem real no portátil, em Windows `cmd`, com o switch ligado por cabo ao PC:

1. Ligar o switch FireTec ao portátil por cabo de rede.
2. No adaptador Ethernet do Windows, configurar IPv4 manual para:
   `192.168.0.10`
3. Manter a ligação à internet por Wi-Fi ou dados móveis, se precisares dela para o resto do sistema.
4. Configurar o FireTec para usar os IPs reais dos switches.

Exemplo em `cmd`:

```bat
set FIRETEC_HARDWARE_ENABLED=true
set FIRETEC_SWITCH_IPS=192.168.0.22,192.168.0.21
set FIRETEC_SWITCH_PORT=8080
set FIRETEC_MAX_WORKERS=5
set FIRETEC_QUEUE_SIZE=50

python main.py
```

Notas para a montagem física:
- O portátil fica com a interface Ethernet em `192.168.0.10`.
- O switch fica ligado a essa interface por cabo.
- O Wi-Fi pode continuar ligado para manter internet, desde que a rede local do switch continue a sair pela placa Ethernet.
- Se fores testar apenas um switch, podes pôr só um IP em `FIRETEC_SWITCH_IPS`.

Variáveis suportadas:
- `FIRETEC_HARDWARE_ENABLED` (`true` para transmitir para hardware, `false` para simulação)
- `FIRETEC_SWITCH_IPS` (lista separada por vírgulas)
- `FIRETEC_SWITCH_PORT` (porta TCP)
- `FIRETEC_MAX_WORKERS`
- `FIRETEC_QUEUE_SIZE`

Comando de execução do projeto (em qualquer ambiente):
- `python main.py`

**Menu Interativo**:
- Opção 1: Inserir coordenadas manualmente
- Opção 2: Gerar coordenadas aleatórias
- Opção 3: Criar múltiplos alertas simultâneos
- Opção 4: Ver estado dos alertas
- Opção 5: Ver estatísticas do sistema

---

## 📈 Métricas

- **Tempo médio de processamento:** 35-45s por alerta
- **Estações FM:** 714 (Portugal Continental)
- **Localidades:** 171,977
- **Workers:** 5 threads paralelos
- **Taxa de sucesso:** >95% (exceto timeout de switches)

---

## 📝 Tarefas Prioritárias

### Até 30 Abril 2026
- [ ] Testes com hardware FireTec real
- [ ] Validar montagem física em portátil Windows
- [ ] Recolher screenshots e registos de execução
- [ ] Fechar notas técnicas para o capítulo de implementação

### 1 Maio - 15 Maio 2026
- [ ] Introdução e contexto
- [ ] Estado da arte
- [ ] Arquitetura e implementação
- [ ] Descrição da pipeline de processamento

### 16 Maio - 31 Maio 2026
- [ ] Testes e validação
- [ ] Análise de resultados
- [ ] Conclusões e trabalho futuro
- [ ] Revisão bibliográfica final
- [ ] Consolidar figuras, tabelas e anexos

### 1 Junho - 5 Junho 2026
- [ ] Revisão completa
- [ ] Formatação final
- [ ] Versão final para submissão

### 6 Junho 2026
- [ ] **🎯 Entrega da dissertação**

---Geopy** - Geolocalização
- **gTTS** - Text-to-Speech
- **GeoPackage/CSV local** - OpenStreetMap via Geofabrik
- **CAP Parser** - Common Alerting Protocol
- **Threading** - Processamento paralelo
- **Pandas** - Processamento de dados
- **Geopy** - Geolocalização
- **gTTS** - Text-to-Speech
- **GeoPackage/CSV local** - OpenStreetMap via Geofabrik
- **CAP Parser** - Common Alerting Protocol
- **Threading** - Processamento paralelo

---

## 📧 Contacto

**Ricardo Machado**  
Email: [ricardo.machado@ua.pt]  
GitHub: [RicardoCMachado/Tese](https://github.com/RicardoCMachado/Tese)
