# FireTec Multithread - Guia Rápido

## Instalação

```powershell
# Instalar dependências
py -m pip install -r requirements.txt
```

## Execução

```powershell
# Executar sistema
py main.py
```

## Menu Principal

```
1. Processar alerta único
2. Processar múltiplos alertas
3. Ver estatísticas
4. Iniciar API REST
5. Sair
```

## Configuração

Editar `main.py` para ajustar:

```python
config = ServerConfig(
    num_workers=5,              # Número de threads
    stations_file="data/123.csv",
    localities_file="data/Localidades_Portugal.csv",
    log_level="INFO"            # DEBUG, INFO, WARNING, ERROR
)
```

## Testar Alerta

1. Executar `py main.py`
2. Escolher opção `1`
3. Introduzir coordenadas (ex: 39.5, -8.0)
4. Sistema processa automaticamente

## API REST

1. Executar `py main.py`
2. Escolher opção `4`
3. API disponível em `http://localhost:5000`

### Endpoints

```
POST   /api/alert          - Criar alerta
GET    /api/alert/<id>     - Ver status
GET    /api/alerts         - Listar todos
GET    /api/statistics     - Estatísticas
```

## Dados Necessários

- `data/123.csv` - 714 estações de rádio
- `data/Localidades_Portugal.csv` - 171,977 localidades

## Outputs

- `audio/` - Mensagens de áudio MP3
- `cap/` - Ficheiros CAP XML
- `logs/` - Logs do sistema
