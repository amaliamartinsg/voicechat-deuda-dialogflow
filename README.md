# 📄 Chatbot Conversacional de Facturación Eléctrica

> **Importante:** Todos los datos utilizados en el proyecto son ficticios.
---

## 📌 Descripción general

Este proyecto implementa un chatbot conversacional de facturación eléctrica, diseñado para permitir a un cliente consultar de forma sencilla el estado de sus facturas, conocer si tiene importes pendientes de pago, recibir información sobre la próxima factura y obtener opciones para realizar el pago.

El chatbot está desarrollado con Dialogflow ES como motor conversacional y utiliza un backend simulado (webhook) para representar los datos de clientes y facturas. Además, incorpora un flujo de RAG (Retrieval Augmented Generation) para responder a preguntas informativas relacionadas con métodos de pago, plazos y atención al cliente, a partir de documentación procesada mediante OCR.

El objetivo del proyecto es demostrar un asistente conversacional end-to-end, no replicar un sistema real de facturación.

🎯 Objetivo del chatbot

El chatbot permite al usuario:

Saber si está al corriente de pago

Conocer si tiene facturas pendientes

Consultar el importe total adeudado

Ver la fecha estimada de la próxima factura

Recibir información sobre cómo pagar una deuda

Solicitar el envío de un enlace de pago (simulado)

Todo ello mediante una conversación natural y guiada, con soporte multi-turn.

🧩 Casos de uso incluidos
1️⃣ Consulta de estado de pago

El usuario puede preguntar si está al corriente de pago.

Ejemplo

“¿Estoy al día con mis facturas?”

Respuesta esperada

Sí, el cliente está al corriente

No, el cliente tiene facturas pendientes (con resumen)

2️⃣ Consulta de facturas pendientes

El usuario puede conocer si tiene facturas sin pagar y obtener un resumen.

Información proporcionada

Número de facturas pendientes

Importe total adeudado

Periodo e importe de cada factura (máx. 3)

3️⃣ Consulta de próxima factura

El chatbot informa de la fecha estimada de emisión de la próxima factura.

Ejemplo

“¿Cuándo me llega la próxima factura?”


# 📄 Chatbot Conversacional de Facturación Eléctrica

## 📌 Descripción General

Este proyecto implementa un chatbot conversacional de facturación eléctrica, diseñado para que el cliente pueda:
- Consultar el estado de sus facturas
- Saber si tiene importes pendientes de pago
- Recibir información sobre la próxima factura
- Obtener opciones para realizar el pago

El chatbot está desarrollado con **Dialogflow ES** como motor conversacional y utiliza un **webhook simulado** para representar los datos de clientes y facturas. Además, incorpora un flujo de **RAG** (Retrieval Augmented Generation) para responder a preguntas informativas sobre métodos de pago, plazos y atención al cliente, a partir de documentación procesada mediante OCR.

> **Nota:** El objetivo es demostrar un asistente conversacional end-to-end, no replicar un sistema real de facturación.

---


## 🎯 Objetivos del Chatbot

El chatbot permite al usuario:

- Saber si está al corriente de pago
- Conocer si tiene facturas pendientes
- Consultar el importe total adeudado
- Ver la fecha estimada de la próxima factura
- Recibir información sobre cómo pagar una deuda
- Solicitar el envío de un enlace de pago (simulado)

Todo ello mediante una conversación natural y guiada, con soporte multi-turn.

---

## 🧩 Casos de Uso Incluidos

### 1️⃣ Consulta de estado de pago
- El usuario puede preguntar si está al corriente de pago.
	- **Ejemplo:**
		- “¿Estoy al día con mis facturas?”
	- **Respuesta esperada:**
		- Sí, el cliente está al corriente
		- No, el cliente tiene facturas pendientes (con resumen)

### 2️⃣ Consulta de facturas pendientes
- El usuario puede conocer si tiene facturas sin pagar y obtener un resumen.
	- **Información proporcionada:**
		- Número de facturas pendientes
		- Importe total adeudado
		- Periodo e importe de cada factura (máx. 3)

### 3️⃣ Consulta de próxima factura
- El chatbot informa de la fecha estimada de emisión de la próxima factura.
	- **Ejemplo:**
		- “¿Cuándo me llega la próxima factura?”

### 4️⃣ Información sobre métodos de pago (RAG)
- El usuario puede preguntar cómo pagar una deuda.
	- **Ejemplos:**
		- “¿Cómo puedo pagar lo que debo?”
		- “¿Puedo pagar por teléfono?”
		- “¿Hay pago presencial?”
	- Las respuestas se generan mediante RAG, a partir de documentación simulada (guías y FAQs).

### 5️⃣ Envío de enlace de pago (simulado)
- El usuario puede solicitar que se le envíe un enlace de pago.
	- **Ejemplo:**
		- “Envíame el enlace de pago por SMS”
	- El sistema simula el envío y confirma la acción.

### 6️⃣ Preguntas informativas adicionales (RAG)
- El chatbot responde preguntas frecuentes como:
		- Qué ocurre si se paga fuera de plazo
		- Cuánto tarda en reflejarse un pago
		- Canales de atención al cliente
	- Estas respuestas no dependen de datos del cliente, sino de documentación indexada.

---

## 🔐 Verificación de Identidad (Simulada)

Para acceder a información sensible, el chatbot solicita:
- Últimos 3 dígitos del DNI
- Últimos 6 caracteres del CUPS

Esta verificación es simulada y solo tiene fines demostrativos.

---

## 🚫 Casos de Uso Excluidos (Fuera de Alcance)

Para mantener el proyecto acotado, el chatbot **no gestiona**:

- Desglose detallado de facturas
- Cambios de tarifa, titularidad o potencia
- Reclamaciones o incidencias
- Fraccionamientos o refinanciaciones
- Históricos completos de facturación
- Múltiples contratos por cliente

Si el usuario solicita algo fuera de alcance, el bot ofrece una respuesta informativa o deriva a atención al cliente.

---

## 🛠️ Arquitectura y Componentes

- **Dialogflow** → entiende al usuario
- **Webhook** → simula clientes y facturas
- **DB simulada** → guarda datos ficticios
- **OCR + embeddings** → indexa documentos
- **Vector DB** → busca texto relevante
- **LLM** → redacta respuestas
- **Canal externo** → muestra la demo