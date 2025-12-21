# FireTec Multithread - Documentação da API REST

## Base URL

```
http://localhost:5000
```

## Endpoints

### 1. Criar Alerta

**POST** `/api/alert`

Cria um novo alerta de incêndio para processamento.

**Request Body:**
```json
{
  "latitude": 39.5,
  "longitude": -8.0,
  "priority": "NORMAL"
}
```

**Campos:**
- `latitude` (float, obrigatório): Latitude do incêndio
- `longitude` (float, obrigatório): Longitude do incêndio
- `priority` (string, opcional): "LOW", "NORMAL", "HIGH", "CRITICAL" (padrão: "NORMAL")

**Response (201 Created):**
```json
{
  "alert_id": "ALERT-20251221-123456-abc123",
  "status": "pending",
  "message": "Alerta criado com sucesso"
}
```

**Exemplo (PowerShell):**
```powershell
$body = @{
    latitude = 39.5
    longitude = -8.0
    priority = "NORMAL"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:5000/api/alert" -Method Post -Body $body -ContentType "application/json"
```

---

### 2. Consultar Status de Alerta

**GET** `/api/alert/<alert_id>`

Obtém o status e detalhes de um alerta específico.

**Parâmetros:**
- `alert_id` (string): ID do alerta

**Response (200 OK):**
```json
{
  "alert_id": "ALERT-20251221-123456-abc123",
  "status": "processed",
  "coordinates": {
    "latitude": 39.5,
    "longitude": -8.0
  },
  "priority": "NORMAL",
  "timestamp": "2025-12-21T12:34:56",
  "location": {
    "name": "Castelo Branco",
    "district": "Castelo Branco",
    "county": "Castelo Branco"
  },
  "nearby_stations": [
    {
      "name": "RTP Antena 1",
      "frequency": 95.7,
      "distance_km": 5.2
    }
  ],
  "nearby_roads": [
    {
      "name": "A23",
      "type": "motorway"
    }
  ],
  "processing_time": 4.52
}
```

**Status possíveis:**
- `pending` - Na fila de processamento
- `processing` - A ser processado
- `processed` - Processado com sucesso
- `sent` - Transmitido para switches
- `failed` - Falhou no processamento

**Exemplo (PowerShell):**
```powershell
Invoke-RestMethod -Uri "http://localhost:5000/api/alert/ALERT-20251221-123456-abc123" -Method Get
```

---

### 3. Listar Todos os Alertas

**GET** `/api/alerts`

Lista todos os alertas no sistema.

**Parâmetros de Query (opcionais):**
- `status` (string): Filtrar por status
- `limit` (int): Número máximo de resultados (padrão: 100)

**Response (200 OK):**
```json
{
  "total": 42,
  "alerts": [
    {
      "alert_id": "ALERT-20251221-123456-abc123",
      "status": "sent",
      "priority": "HIGH",
      "timestamp": "2025-12-21T12:34:56",
      "processing_time": 4.52
    },
    {
      "alert_id": "ALERT-20251221-123457-def456",
      "status": "processing",
      "priority": "NORMAL",
      "timestamp": "2025-12-21T12:34:57"
    }
  ]
}
```

**Exemplo (PowerShell):**
```powershell
# Todos os alertas
Invoke-RestMethod -Uri "http://localhost:5000/api/alerts" -Method Get

# Filtrar por status
Invoke-RestMethod -Uri "http://localhost:5000/api/alerts?status=sent" -Method Get
```

---

### 4. Estatísticas do Sistema

**GET** `/api/statistics`

Obtém estatísticas de processamento do sistema.

**Response (200 OK):**
```json
{
  "total_alerts": 42,
  "processed_alerts": 38,
  "failed_alerts": 1,
  "pending_alerts": 3,
  "average_processing_time": 4.8,
  "active_workers": 5,
  "queue_size": 3,
  "uptime_seconds": 3600
}
```

**Campos:**
- `total_alerts`: Total de alertas submetidos
- `processed_alerts`: Alertas processados com sucesso
- `failed_alerts`: Alertas que falharam
- `pending_alerts`: Alertas na fila
- `average_processing_time`: Tempo médio de processamento (segundos)
- `active_workers`: Número de threads ativas
- `queue_size`: Tamanho atual da fila
- `uptime_seconds`: Tempo de execução do sistema

**Exemplo (PowerShell):**
```powershell
Invoke-RestMethod -Uri "http://localhost:5000/api/statistics" -Method Get
```

---

### 5. Health Check

**GET** `/health`

Verifica se a API está online.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-21T12:34:56"
}
```

**Exemplo (PowerShell):**
```powershell
Invoke-RestMethod -Uri "http://localhost:5000/health" -Method Get
```

---

## Códigos de Erro

### 400 Bad Request
```json
{
  "error": "Coordenadas inválidas"
}
```

### 404 Not Found
```json
{
  "error": "Alerta não encontrado"
}
```

### 500 Internal Server Error
```json
{
  "error": "Erro interno do servidor"
}
```

---

## Exemplo Completo de Uso

```powershell
# 1. Criar alerta
$alert = @{
    latitude = 39.868306
    longitude = -7.526667
    priority = "HIGH"
} | ConvertTo-Json

$response = Invoke-RestMethod -Uri "http://localhost:5000/api/alert" -Method Post -Body $alert -ContentType "application/json"
$alertId = $response.alert_id

Write-Host "Alerta criado: $alertId"

# 2. Aguardar processamento
Start-Sleep -Seconds 5

# 3. Verificar status
$status = Invoke-RestMethod -Uri "http://localhost:5000/api/alert/$alertId" -Method Get

Write-Host "Status: $($status.status)"
Write-Host "Localidade: $($status.location.name)"
Write-Host "Antenas: $($status.nearby_stations.Count)"
Write-Host "Tempo: $($status.processing_time)s"

# 4. Ver estatísticas
$stats = Invoke-RestMethod -Uri "http://localhost:5000/api/statistics" -Method Get

Write-Host "Total processados: $($stats.processed_alerts)"
Write-Host "Tempo médio: $($stats.average_processing_time)s"
```

---

## CORS

A API tem CORS habilitado para todos os origins (`*`), permitindo chamadas de qualquer domínio.

---

## Autenticação

Atualmente a API não requer autenticação. Para produção, implementar autenticação via API keys ou OAuth.
