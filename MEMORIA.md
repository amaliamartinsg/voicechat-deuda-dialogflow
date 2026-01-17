# Memoria del proyecto: Chatbot Deuda (Dialogflow + Telegram + RAG)

## 1. Resumen ejecutivo

Este proyecto implementa un prototipo de asistente conversacional para consultas de facturacion electrica. El sistema se apoya en Dialogflow ES para interpretar intenciones y un webhook en FastAPI para responder con datos deterministas (estado de cuenta, facturas y pagos). En paralelo, se ha preparado un flujo RAG (Retrieval Augmented Generation) con Qdrant que permite responder preguntas informativas basadas en documentos.

El objetivo final es un servicio conectado a Telegram: el usuario escribe o envia audio, Dialogflow interpreta la intencion y decide si necesita fulfillment. Si no lo necesita, responde directamente; si lo necesita, el webhook realiza la logica de negocio determinista o deriva a RAG cuando proceda.

## 2. Alcance y objetivos

### Objetivos funcionales

- Consultas de estado de pago.
- Listado de facturas pendientes y total adeudado.
- Fecha estimada de proxima factura.
- Envio de factura (simulado) por canal.
- Envio de enlace de pago (simulado).
- Respuestas informativas sobre pagos, condiciones y atencion (via RAG).

### Fuera de alcance (prototipo)

- Desglose detallado de facturas.
- Cambios contractuales (tarifa, potencia, titularidad).
- Reclamaciones o incidencias.
- Refinanciaciones o historicos completos.

## 3. Arquitectura de alto nivel

Flujo deseado del prototipo:

1. Usuario -> Telegram (texto o voz).
2. Bot Telegram -> Dialogflow (detect intent).
3. Dialogflow:
   - Sin fulfillment: responde directo al usuario.
   - Con fulfillment: llama a `POST /dialogflow/webhook`.
4. Webhook:
   - Si es determinista: resuelve con datos.
   - Si requiere conocimiento documental: consulta RAG y responde.

Componentes principales:

- Bot Telegram: `app/app.py`.
- Webhook Dialogflow (FastAPI): `app/main.py`.
- Motor RAG (LangChain + Qdrant): `app/src/agent/*`.
- Indexador de PDFs: `app/scripts/rag_indexer.py`.
- Almacen de datos demo: `app/data/sample_data.json`.

## 4. Estado actual del codigo

Implementado:

- Webhook de Dialogflow con intents deterministas y manejo de identidad.
- Bot de Telegram (texto y voz, con STT opcional).
- Pipeline RAG completo (ingesta + embeddings + Qdrant + cadena).

Pendiente o parcial:

- Exponer el endpoint RAG como servicio FastAPI.
- Conectar el RAG a intents informativas dentro del webhook de Dialogflow.
- Dockerfile de la API (el compose actual lo referencia pero no esta en el repo).

## 5. Detalle de componentes

### 5.1. Webhook Dialogflow

Archivo: `app/main.py`

- Endpoint `POST /dialogflow/webhook`.
- Identificacion del usuario por DNI parcial y CUPS.
- Contextos de Dialogflow para pedir identidad y reintentar acciones.
- Intents actuales:
  - `Billing.Info.AccountStatus`
  - `Billing.Info.UnpaidInvoices`
  - `Billing.Info.OutstandingAmount`
  - `Billing.SendInvoice.*`
  - `Info.NextInvoiceDate`
  - `Payments.SendLink`

### 5.2. Bot Telegram

Archivo: `app/app.py`

- Procesa texto y voz.
- Envia mensajes a Dialogflow con `detect_intent`.
- Responde al usuario con `fulfillment_text`.
- Incluye STT con Whisper y TTS opcional.

### 5.3. RAG

Archivos:

- `app/src/agent/chain.py`: cadena RAG con `qdrant_langchain`.
- `app/src/agent/prompts.py`: prompts de sistema.
- `app/src/services/embeddings.py`: embeddings (HuggingFace).
- `app/src/services/llms.py`: LLM via `ChatOpenAI`.
- `app/src/services/vector_store.py`: conexion con Qdrant.

Indexado:

- `app/scripts/rag_indexer.py`: procesa PDFs (OCR si es necesario), genera chunks y hace upsert en Qdrant.

## 6. Datos y modelos

- Datos demo de clientes y facturas: `app/data/sample_data.json`.
- Base vectorial: Qdrant.
- Embeddings: `sentence-transformers/all-MiniLM-L6-v2` por defecto.
- LLM: `gpt-4o-mini` por defecto.

## 7. Configuracion y despliegue

### 7.1. Variables de entorno

Recomendadas:

- `TELEGRAM_BOT_TOKEN`
- `DIALOGFLOW_PROJECT_ID`
- `GOOGLE_APPLICATION_CREDENTIALS`
- `OPENAI_API_KEY`
- `QDRANT_URL`
- `QDRANT_COLLECTION`
- `EMBEDDING_MODEL`
- `LLM_MODEL`
- `LLM_TEMPERATURE`
- `K_DOCS`, `THRESHOLD`
- `PYTHONPATH=app`

### 7.2. Ejecucion con uv

```bash
uv sync
cd app
docker-compose up -d
uv run python app/scripts/rag_indexer.py
uv run uvicorn app.main:app --host 0.0.0.0 --port 8008 --reload
uv run python app/app.py
```

### 7.3. Docker

Existe `app/docker-compose.yaml` para Qdrant y una API, pero falta el Dockerfile de la API. Se debe agregar o ajustar el compose para un despliegue completo en contenedores.

## 8. Seguridad y privacidad

- Las claves (`TELEGRAM_BOT_TOKEN`, `OPENAI_API_KEY`, etc.) no deben versionarse.
- El prototipo usa datos ficticios en `sample_data.json`.
- El endpoint de webhook no incluye autenticacion (entorno demo).

## 9. Pruebas y validacion

Recomendaciones:

- Probar intents deterministas con Dialogflow simulator.
- Validar flujo de identidad (DNI/CUPS).
- Verificar conexion a Qdrant e ingesta de PDFs.
- Probar bot en Telegram con texto y audio.

## 10. Roadmap sugerido

1. Integrar el RAG dentro del webhook segun intencion detectada.
2. Exponer endpoint RAG en FastAPI.
3. Completar Dockerfile y pipeline de despliegue.
4. Instrumentar logs y metricas.
5. Añadir tests basicos de intents y RAG.

