# Chatbot Deuda (Dialogflow + Telegram + RAG)

Proyecto de demo para un asistente conversacional de facturacion electrica. El flujo actual usa Dialogflow ES para interpretar la intencion del usuario y un webhook en FastAPI para responder con datos deterministas (facturas y estado de cuenta). En paralelo, existe un pipeline RAG con Qdrant para responder preguntas informativas a partir de documentos.

Este repositorio tambien incluye un bot de Telegram (texto y voz) que envia los mensajes a Dialogflow.

## Arquitectura (objetivo del prototipo)

Flujo deseado:

1. Usuario escribe en Telegram.
2. Bot de Telegram envía texto/voz a Dialogflow.
3. Dialogflow detecta la intencion:
   - Si NO requiere fulfillment: responde directo a Telegram.
   - Si requiere fulfillment: llama a `POST /dialogflow/webhook`.
4. El webhook resuelve:
   - Respuesta determinista basada en datos (facturas, estado, etc.).
   - O bien usa RAG para contestar con base en documentos en la base vectorial.

Estado actual:
- El webhook determinista esta implementado en `app/main.py`.
- El RAG esta implementado en `app/src/agent/*` y `app/scripts/rag_indexer.py`, pero no esta expuesto como endpoint en FastAPI (hay un `rag_invoke` de prueba en `app/src/api/router.py`).
- El bot de Telegram esta en `app/app.py`.

## Componentes principales

- Webhook Dialogflow (FastAPI): `app/main.py`
- Bot Telegram: `app/app.py`
- RAG (LangChain + Qdrant): `app/src/agent/*`, `app/src/services/*`
- Indexador de PDFs (OCR + embeddings): `app/scripts/rag_indexer.py`
- Datos demo: `app/data/sample_data.json`
- Configuracion Qdrant: `app/config/config.yaml`

## Requisitos

- Python 3.11+
- uv (recomendado)
- Docker (para Qdrant)
- Credenciales de Google Dialogflow (JSON)
- Tesseract + Poppler (solo si haces OCR de PDFs en el indexador)

## Variables de entorno

Crea un archivo `app/.env` (no subir a git) con los valores necesarios:

- `TELEGRAM_BOT_TOKEN`
- `DIALOGFLOW_PROJECT_ID`
- `GOOGLE_APPLICATION_CREDENTIALS` (ruta al JSON de credenciales)
- `OPENAI_API_KEY`
- `QDRANT_URL` (por defecto `http://localhost:6333`)
- `QDRANT_COLLECTION` (opcional)
- `EMBEDDING_MODEL` (opcional, por defecto `sentence-transformers/all-MiniLM-L6-v2`)
- `LLM_MODEL` (opcional, por defecto `gpt-4o-mini`)
- `LLM_TEMPERATURE` (opcional)
- `K_DOCS` / `THRESHOLD` (opcional)
- `PYTHONPATH` (recomendado `app` para resolver imports)

## Ejecucion local con uv

1. Instalar dependencias:
```bash
uv sync
```

2. Levantar Qdrant con Docker:
```bash
cd app
docker-compose up -d
```

3. Ingesta de documentos para RAG (opcional):
```bash
uv run python app/scripts/rag_indexer.py
```

4. Levantar el webhook de Dialogflow:
```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8008 --reload
```

5. Levantar el bot de Telegram:
```bash
uv run python app/app.py
```

## Ejecucion con Docker (pendiente de completar)

Hay un `app/docker-compose.yaml` que levanta Qdrant y una API, pero el `Dockerfile` de la API no esta en el repo. Para usar Docker end-to-end, necesitas agregar el `Dockerfile` esperado en `app/src/Dockerfile` o ajustar el compose. Mientras tanto, se recomienda levantar el API con `uvicorn` como se indica arriba.

## Endpoints

- `POST /dialogflow/webhook` en `app/main.py`
- `GET /health` para chequeo basico

## Datos y flujo determinista

La logica determinista usa `app/data/sample_data.json` y requiere identificar al usuario por DNI parcial y CUPS. Se mantienen contextos de Dialogflow para pedir identidad y reintentar acciones pendientes.

## RAG

El indexador `app/scripts/rag_indexer.py`:
- extrae texto de PDFs (si no hay texto embebido, usa OCR),
- genera embeddings,
- guarda chunks en Qdrant.

La cadena RAG esta en `app/src/agent/chain.py` y los prompts en `app/src/agent/prompts.py`.

## Notas y mejoras pendientes

- Conectar el flujo RAG al webhook de Dialogflow para intenciones informativas.
- Exponer un endpoint RAG real en FastAPI.
- Completar Dockerfile para la API.

