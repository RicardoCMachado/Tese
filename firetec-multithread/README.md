# FireTec - Sistema de Alerta de Incêndios por Rádio FM

**Dissertação de Mestrado - Ricardo Machado**  
**Orientador:** Prof. António Navarro  
**Ano Letivo:** 2025/2026

---

## 📅 Planeamento

| Fase | Período | Estado |
|------|---------|--------|
| **Desenvolvimento Técnico Final** | 26 Fev - 6 Abr 2026 | 🔄 Em curso (39 dias) |
| **Torneios (pausa técnica)** | 7 Abr - 21 Abr 2026 | ⏸️ Só escrita (15 dias) |
| **Escrita da Dissertação** | 22 Abr - 5 Jun 2026 | ⏳ Pendente (45 dias) |
| **Entrega Final** | **6 Junho 2026** | 🎯 Deadline |

> **Nota:** Durante os torneios (7-21 Abr), apenas trabalho de escrita será realizado.

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

### ✅ Implementado (92% - Atualizado 26 Fev 2026)

**Core do Sistema:**
- Arquitetura multithread com 5 workers **✅ THREAD-SAFE**
- Sistema de prioridades (LOW, NORMAL, HIGH, CRITICAL)
- Fila de processamento com PriorityQueue
- Logging completo
- Shutdown suave (Ctrl+C)

**Serviços:**
- `AntennaService` - 714 estações FM **✅ Com validação de dados**
- `LocationService` - 171,977 localidades **✅ Thread-safe (Nominatim por request)**
- `RoadService` - Estradas próximas via Overpass API **✅ Thread-safe**
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
- Otimização de rate limiting da Overpass API
- Caching de resultados de geocoding
- Testes de carga e stress

**Dissertação:**
- Revisão bibliográfica completa
- Diagramas de arquitetura
- Análise de resultados
- Discussão e conclusões
- Trabalho futuro

---

## 🔧 Correções Críticas (26 Fev 2026)

### Problemas Corrigidos:
1. ✅ **Thread Safety**: Nominatim e Overpass API agora thread-safe (criados por request)
2. ✅ **Switch Compatibility**: PS/PI de estações reais em vez de hardcoded
3. ✅ **Socket Management**: Sempre fechado corretamente
4. ✅ **Data Validation**: CSV com validação de campos obrigatórios
5. ✅ **MIME Types**: audio/mpeg correto para MP3

**📄 Detalhes**: Ver documentação completa em SECURITY_AND_IMPROVEMENTS.md

---

## 🚀 Execução

```powershell
# Instalar dependências
pip install -r requirements.txt

# Executar sistema
python main.py
```

### Execução em Máquina Virtual (VM)

Para correr exatamente o mesmo código no PC do laboratório e numa VM, configura apenas variáveis de ambiente antes de executar:

**Windows (PowerShell):**

```powershell
# Switches da rede do laboratório
$env:FIRETEC_SWITCH_IPS="192.168.0.22,192.168.0.21"
$env:FIRETEC_SWITCH_PORT="8080"

# Ajuste opcional de performance
$env:FIRETEC_MAX_WORKERS="5"
$env:FIRETEC_QUEUE_SIZE="50"

python main.py
```

**Linux (Bash):**

```bash
# Switches da rede do laboratório
export FIRETEC_SWITCH_IPS="192.168.0.22,192.168.0.21"
export FIRETEC_SWITCH_PORT="8080"

# Ajuste opcional de performance
export FIRETEC_MAX_WORKERS="5"
export FIRETEC_QUEUE_SIZE="50"

python main.py
```

Variáveis suportadas:
- `FIRETEC_SWITCH_IPS` (lista separada por vírgulas)
- `FIRETEC_SWITCH_PORT` (porta TCP)
- `FIRETEC_MAX_WORKERS`
- `FIRETEC_QUEUE_SIZE`

Nota de rede para VM:
- Usa adaptador em `Bridged` (não `NAT`) para a VM conseguir alcançar os switches físicos na LAN.

### Preparar imagem VM no teu PC (sem hardware)

Objetivo: criar uma imagem que no laboratório seja só importar e correr.

1. Criar VM local (Ubuntu 24.04 LTS) e clonar este repositório.
2. Instalar dependências base do Ubuntu (uma vez):

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
```

3. Na raiz do projeto, criar ambiente virtual e instalar dependências:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

4. Criar `.env` a partir de `.env.example`:

```bash
cp .env.example .env
```

5. Testar arranque local (sempre pelo mesmo comando):

```bash
source .venv/bin/activate
python main.py
```

6. Depois de validado, desligar a VM e exportar para `OVA/OVF`.
7. No laboratório: importar imagem, abrir terminal na pasta do projeto e correr:

```bash
source .venv/bin/activate
python main.py
```

Se fores testar com hardware no laboratório:
- confirmar `FIRETEC_SWITCH_IPS` e `FIRETEC_SWITCH_PORT`
- usar rede `Bridged`

Comando de execução do projeto (em qualquer ambiente):
- `python main.py`

**Menu Interativo**:
- Opção 1: Inserir coordenadas manualmente
- Opção 2: Gerar coordenadas aleatórias
- Opção 3: Local de alerta em Cacia
- Opção 4: Múltiplos alertas (teste de carga)
- Opção 5: Mostrar status
- Opção 6: Estatísticas

---

## 📈 Métricas

- **Tempo médio de processamento:** 35-45s por alerta
- **Estações FM:** 714 (Portugal Continental)
- **Localidades:** 171,977
- **Workers:** 5 threads paralelos
- **Taxa de sucesso:** >95% (exceto timeout de switches)

---

## 📝 Tarefas Prioritárias

### Até 6 Abril 2026 (Desenvolvimento Técnico)
- [ ] Testes com hardware FireTec real
- [ ] Otimização de rate limiting (Overpass API)
- [ ] Métricas de performance finais
- [ ] Screenshots e vídeos de demonstração
- [ ] Documentação técnica completa

### 7-21 Abril 2026 (Torneios - Apenas Escrita)
- [ ] Rascunho de introdução e contexto
- [ ] Rascunho de estado da arte
- [ ] Esboço de arquitetura do sistema
- [ ] Documentação de testes realizados

### 22 Abril - 5 Junho 2026 (Escrita Intensiva)
- [ ] Introdução e contexto (finalizar)
- [ ] Estado da arte (finalizar)
- [ ] Arquitetura e implementação
- [ ] Testes e validação
- [ ] Análise de resultados
- [ ] Conclusões e trabalho futuro
- [ ] Revisão completa
- [ ] Formatação final

### 6 Junho 2026
- [ ] **🎯 Entrega da dissertação**

---Geopy** - Geolocalização
- **gTTS** - Text-to-Speech
- **Overpass API** - OpenStreetMap
- **CAP Parser** - Common Alerting Protocol
- **Threading** - Processamento paralelo
- **Pandas** - Processamento de dados
- **Geopy** - Geolocalização
- **gTTS** - Text-to-Speech
- **Overpass API** - OpenStreetMap
- **CAP Parser** - Common Alerting Protocol
- **Threading** - Processamento paralelo

---

## 📧 Contacto

**Ricardo Machado**  
Email: [ricardo.machado@ua.pt]  
GitHub: [RicardoCMachado/Tese](https://github.com/RicardoCMachado/Tese)
