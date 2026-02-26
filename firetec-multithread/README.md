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

### ✅ Implementado (98% - Atualizado 26 Fev 2026)

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
- Interface web React (opcional)
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
