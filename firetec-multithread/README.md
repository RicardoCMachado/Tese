# FireTec - Sistema de Alerta de Incêndios por Rádio FM

**Dissertação de Mestrado - Ricardo Machado**  
**Orientador:** Prof. António Navarro  
**Ano Letivo:** 2025/2026

---

## 📅 Planeamento

| Fase | Período | Estado |
|------|---------|--------|
| **Desenvolvimento do Sistema** | Set 2025 - Abr 2026 | 🔄 Em curso |
| **Testes e Validação** | Mai 2026 | 🔄 Em curso |
| **Escrita da Dissertação** | Mai 2026 - 5 Jun 2026 | ⏳ Pendente |
| **Entrega Final** | **6 Junho 2026** | ⏳ Pendente |

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
- ✅ API REST para integração externa
- ⏳ Interface web de monitorização
- ⏳ Testes com hardware FireTec real

---

## 📊 Estado Atual

### ✅ Implementado (95%)

**Core do Sistema:**
- Arquitetura multithread com 5 workers
- Sistema de prioridades (LOW, NORMAL, HIGH, CRITICAL)
- Fila de processamento com PriorityQueue
- Logging completo
- Shutdown suave (Ctrl+C)

**Serviços:**
- `AntennaService` - 714 estações FM
- `LocationService` - 171,977 localidades de Portugal
- `RoadService` - Estradas próximas via Overpass API
- `AudioService` - Mensagens de voz em português
- `CAPService` - Geração de XML CAP
- `TransmissionService` - Envio para switches FireTec

**API REST:**
- FastAPI com Swagger UI
- Endpoints: criar alerta, consultar status, estatísticas
- Documentação automática em `/`

### ⏳ Pendente

**Sistema:**
- Testes com switches FireTec reais
- Interface web React
- Testes de carga e stress

**Dissertação:**
- Revisão bibliográfica completa
- Diagramas de arquitetura
- Análise de resultados
- Discussão e conclusões
- Trabalho futuro

---

## 🚀 Execução

```powershell
# Instalar dependências
pip install -r requirements.txt

# Executar sistema
python main.py
```

**API REST:** http://localhost:5000  
**Documentação:** http://localhost:5000/ (Swagger UI)

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
- [ ] Testes com hardware real
- [ ] Interface web completa
- [ ] Métricas de performance finais
- [ ] Screenshots e vídeos de demonstração

### Maio 2026 (Escrita)
- [ ] Introdução e contexto
- [ ] Estado da arte
- [ ] Arquitetura e implementação
- [ ] Testes e validação
- [ ] Conclusões
- [ ] Revisão final

### 5 Junho 2026
- [ ] **Entrega da dissertação**

---

## 🛠️ Tecnologias

- **Python 3.14**
- **FastAPI** - API REST
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
