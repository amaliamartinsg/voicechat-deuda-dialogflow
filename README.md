
# Chatbot Deuda (Dialogflow + Telegram + RAG)


Proyecto de demo para un asistente conversacional de facturación eléctrica. El flujo actual usa Dialogflow ES para interpretar la intención del usuario y un webhook en FastAPI para responder con datos deterministas (facturas y estado de cuenta). En paralelo, existe un pipeline RAG con Qdrant para responder preguntas informativas a partir de documentos.


Este repositorio también incluye un bot de Telegram (texto y voz) que envía los mensajes a Dialogflow.


## Arquitectura (objetivo del prototipo)


Flujo deseado:


1. Usuario escribe o envía audio en Telegram.
2. Bot de Telegram envía texto/voz a Dialogflow.
3. Dialogflow detecta la intención:
   - Si NO requiere fulfillment: responde directo a Telegram.
   - Si requiere fulfillment: llama a `POST /dialogflow/webhook`.
4. El webhook resuelve:
   - Respuesta determinista basada en datos (facturas, estado, etc.).
   - O bien usa RAG para contestar con base en documentos en la base vectorial.


Estado actual:
- El webhook determinista y el flujo RAG están implementados en `app/main.py`.
- El RAG está implementado en `app/src/agent/*`, `app/src/services/*` y el indexador en `app/scripts/rag_indexer.py`. El endpoint RAG está expuesto en `/rag/query` en FastAPI.
- El bot de Telegram está en `app/app.py`.


## Componentes principales


- Webhook Dialogflow (FastAPI): `app/main.py`
- Bot Telegram: `app/app.py`
- RAG (LangChain + Qdrant): `app/src/agent/*`, `app/src/services/*`
- Indexador de PDFs (OCR + embeddings): `app/scripts/rag_indexer.py`
- Datos demo: `app/data/sample_data.json`
- Configuración Qdrant: `app/config/config.yaml`


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


## Ejecución local con uv


1. Instalar dependencias:
```bash
uv pip install -r app/requirements.txt
```


2. Levantar Qdrant con Docker:
```bash
cd app
docker-compose up -d qdrant
```
Esto levantará tanto el servicio de Qdrant como el de la API (dialogflow_api) definidos en el archivo docker-compose.yaml.


3. Ingesta de documentos para RAG (opcional):
```bash
uv run -m scripts.rag_indexer
```


4. Levantar el webhook de Dialogflow y el endpoint RAG:
```bash
uv run uvicorn main:app --host 0.0.0.0 --port 8008 --reload
```


5. Levantar el bot de Telegram:
```bash
uv run python app.py
```


## Ejecución con Docker


Hay un `docker-compose.yaml` que levanta Qdrant y la API. El `Dockerfile` de la API está en `app/Dockerfile`. Para usar Docker end-to-end, asegúrate de tener ambos archivos y ejecuta:
```bash
cd app
docker-compose up --build -d
```



## Endpoints


- `POST /dialogflow/webhook` en `app/main.py` (webhook principal)
- `POST /rag/query` en `app/main.py` (consulta RAG)
- `GET /health` para chequeo básico


## Datos y flujo determinista


La lógica determinista usa `app/data/sample_data.json` y requiere identificar al usuario por DNI parcial y CUPS. Se mantienen contextos de Dialogflow para pedir identidad y reintentar acciones pendientes.


## RAG


El indexador `app/scripts/rag_indexer.py`:
- extrae texto de PDFs (si no hay texto embebido, usa OCR),
- genera embeddings,
- guarda chunks en Qdrant.


La cadena RAG está en `app/src/agent/chain.py` y los prompts en `app/src/agent/prompts.py`.


## Intents actuales

**Manejados por el webhook:**
  **- Respuesta determinista**
   - `Auth.ProvideIdentity`
   - `Billing.Info.AccountStatus`
   - `Billing.Info.OutstandingAmount`
   - `Billing.Info.UnpaidInvoices`
   - `Billing.SendInvoice.ByMonth`
   - `Billing.SendInvoice.Channel`
   - `Billing.SendInvoice.Last`
   - `Info.NextInvoiceDate`
   - `Payments.SendLink`
   
   **- Respuesta modelo de lenguaje**
   - `Info.General`

**Respuesta directa en Dialogflow:**
   - `Default.WelcomeIntent`
   - `Default.Fallback`
   - `Default.FeedBack.Possitive`
   - `Default.FeedBack.Negative`
   - `Payments.Options`
   - `Support.HumanHandoff`


## Notas y mejoras pendientes

- Añadir despliegue de la app de Telegram en Docker
- Añadir tests básicos de intents y RAG.
- Instrumentar logs y métricas.

