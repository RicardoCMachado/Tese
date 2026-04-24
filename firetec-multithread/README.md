# FireTec Multithread Server

Servidor de alerta de incêndio para rádio FM, evoluindo a versão monolítica antiga para arquitetura modular/multithread **sem quebrar compatibilidade com os FireTec Switches do laboratório**.

## Compatibilidade de laboratório (prioridade máxima)

- Switches físicos: `192.168.0.22`, `192.168.0.21`
- Porta TCP: `8080`
- **Protocolo obrigatório enviado ao switch (legacy Rodolfo):**
  - `wav_data + b"PS=...;" + b"PI=...;" + b"AF=...;"`
- CAP XML é gerado apenas para dissertação/interoperabilidade, **não** é payload do switch.

## Requisitos

- **Python 3.10 ou 3.11 recomendado**
- ffmpeg disponível no sistema (necessário para `pydub`)

## Arquitetura

```text
main.py
src/
  core/
    alert_processor.py
    worker_pool.py
  services/
    antenna_service.py
    location_service.py
    road_service.py
    audio_service.py
    transmission_service.py
    cap_service.py
    kml_service.py
  models/
    alert.py
    config.py
  utils/
    logger.py
    retry.py
    validation.py
```

## Configuração (.env)

```env
FIRETEC_SWITCH_IPS=192.168.0.22,192.168.0.21
FIRETEC_SWITCH_PORT=8080
FIRETEC_MAX_WORKERS=5
FIRETEC_ENABLE_OVERPASS=true
FIRETEC_ENABLE_CAP=true
FIRETEC_SIMULATION=false
```

## Execução

### Windows (PowerShell)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

Se o PowerShell bloquear scripts:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

### Windows (CMD)

```bat
python -m venv .venv
.venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

### Linux/macOS (bash/zsh)

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
python main.py
```

## Pipeline técnico

1. Procura antenas reais (CSV)
2. Geolocalização (Nominatim; fallback CSV local)
3. Estradas via Overpass (retry + endpoints alternativos + fallback)
4. Mensagem textual
5. Áudio: **gTTS → MP3 temporário → WAV final (32kHz, sample_width=1)**
6. Payload legacy `WAV + PS/PI/AF` enviado em paralelo para os dois switches
7. CAP XML opcional salvo em disco (não enviado ao switch)

## Modo laboratório vs simulação

- `FIRETEC_SIMULATION=false`: modo real, conecta aos switches físicos.
- `FIRETEC_SIMULATION=true`: não abre socket; útil para testes locais e carga.

## Overpass resiliente

- Timeout real por query
- Retries limitados
- Rotação de endpoints:
  - `https://overpass-api.de/api/interpreter`
  - `https://lz4.overpass-api.de/api/interpreter`
  - `https://overpass.kumi.systems/api/interpreter`
- Aceita `ref` ou `name`
- Se falhar: alerta continua normalmente com mensagem de precaução

## Testes rápidos

```bash
pytest
python -m compileall main.py src
```
