# FireTec Multithread Server
## Sistema de Alerta de Incêndios por Rádio FM

**Dissertação de Mestrado**  
**Aluno:** Ricardo  
**Orientador:** Prof. António Navarro  
**Data:** Dezembro 2025 - Junho 2026

---

## 📋 Descrição do Projeto

Sistema multithread para suporte a alertas simultâneos de incêndios através de rádios FM locais. Evolução do sistema original (Rodolfo Oliveira) para suportar múltiplos incêndios em paralelo.

## 🎯 Objetivos da Tese

- ✅ Analisar código existente
- ✅ Modularizar sistema
- 🔄 Implementar arquitetura multithread
- 🔄 Gestão de múltiplos alertas simultâneos
- 🔄 Interface de monitorização
- 🔄 Testes e validação
- 🔄 Documentação técnica

## 🏗️ Arquitetura do Sistema

```
firetec-multithread/
├── src/
│   ├── core/           # Lógica principal
│   ├── services/       # Serviços (antenas, localidades, estradas)
│   ├── models/         # Modelos de dados
│   ├── utils/          # Utilitários
│   └── config/         # Configurações
├── data/               # Ficheiros CSV, KML
├── logs/               # Logs do sistema
└── docs/               # Documentação
```

## 📅 Timeline

| Período | Tarefa |
|---------|--------|
| Dez-Jan | Estrutura + Código modular + Multithread básico |
| Fev-Mar | Sistema completo + Testes |
| Abril | Refinamentos + Interface |
| Maio | Testes finais + Documentação |
| Junho | Escrita da tese |

## 🚀 Como Executar

```bash
# Instalar dependências
pip install -r requirements.txt

# Executar servidor
python main.py
```

## 📊 Funcionalidades

### Versão Original
- ✅ Receção de alerta (coordenadas)
- ✅ Identificação de antenas FM próximas
- ✅ Determinação de localidade
- ✅ Busca de estradas próximas
- ✅ Geração de mensagem de áudio
- ✅ Envio via CAP para switches

### Nova Versão (Multithread) ⭐
- 🆕 **Suporte a múltiplos alertas simultâneos**
- 🆕 **Fila de prioridades** (CRITICAL > HIGH > NORMAL)
- 🆕 **Gestão de recursos** (antenas) thread-safe
- 🆕 **API REST** para integração externa
- 🆕 **Logging avançado** com métricas
- 🆕 **Processamento paralelo** configurável (5-100+ workers)
- 🆕 **Geração automática** de áudio (gTTS)
- 🆕 **CAP XML** completo com recursos
- 🆕 **Transmissão automática** para switches FireTec

---

**Instituto de Telecomunicações - Universidade de Aveiro**
