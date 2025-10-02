# Plano de Trabalho - Dissertação de Mestrado  
**Título:** Servidor para Suporte a um Sistema de Alerta por Rádio FM  
**Prazo de Entrega:** 6 de junho de 2026  
**Local:** Instituto de Telecomunicações (IT)  

---

## Estrutura Temporal

### Outubro 2025
- Estudo da dissertação de Rodolfo Oliveira.  
- Revisão do código atual do servidor em Python.  
- Pesquisa sobre técnicas de multithreading em Python.  
- Definição do plano técnico para adaptação.  

### Novembro 2025
- Identificação dos módulos a adaptar:
  - Sockets DTS  
  - Detecção de estações  
  - Geração de mensagens (texto + áudio)  
  - Envio para Firetec Switch  
- Desenho da arquitetura multithread (thread pool / asyncio).  
- Protótipo inicial para comunicação paralela com DTS.  

### Dezembro 2025
- Implementação multithread no módulo **DTS → servidor**.  
- Testes unitários com dados simulados.  

### Janeiro 2026
- Implementação multithread na **detecção de estações de rádio**.  
- Garantia de consistência na base de dados de estações.  
- Testes comparativos (single-thread vs multithread).  

### Fevereiro 2026
- Implementação multithread na **geração de mensagens (texto + áudio)**.  
- Gestão de ficheiros temporários (nomes únicos / memória).  
- Testes com alertas múltiplos em paralelo.  

### Março 2026
- Implementação multithread na **comunicação com Firetec Switch (PCF e CAP)**.  
- Integração completa (DTS → servidor → rádios).  
- Testes de carga com vários fogos em simultâneo.  

### Abril 2026
- Refinamento do código e otimizações finais.  
- Testes finais no IT em ambiente de demonstração.  
- Recolha de métricas de desempenho (tempo médio, escalabilidade, fiabilidade).  
- Escrita preliminar de notas para o capítulo de resultados.  

---

## Escrita da Dissertação

### Maio 2026
- Redação integral da dissertação:
  - Introdução e motivação  
  - Estado da arte  
  - Implementação detalhada  
  - Resultados experimentais  
  - Conclusões e trabalhos futuros  
- Preparação de figuras, fluxogramas e gráficos. 

### Junho 2026
- Revisão integral, formatação e bibliografia.  
- Entrega final a **6 de junho de 2026**.  

---

## Notas
- **Implementação termina em abril de 2026.**  
- **Maio é dedicado à escrita.**  
- O código deverá estar testado e validado antes da fase de redação
