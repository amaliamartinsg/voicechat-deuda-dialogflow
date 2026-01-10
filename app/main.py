from __future__ import annotations

import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="Dialogflow ES Webhook - Billing Demo", version="1.0.0")

DATA_PATH = os.getenv("BILLING_DATA_PATH", os.path.join(os.path.dirname(__file__), "data", "sample_data.json"))

from routers.billing.send_invoice import handle_send_invoice

from helpers.aux_functions import (
    build_dialogflow_response,
    format_eur,
    get_invoices_for_customer,
    make_context,
    list_unpaid_invoices,
    find_customer_by_dni_last4,
    get_context_params,
    upsert_context,
    identify_user,
)



# -----------------------------
# Helpers: load data
# -----------------------------


def load_data() -> Dict[str, Any]:
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)



# -----------------------------
# Business intents with pending action + identity
# -----------------------------


AUTH_INTENTS = {"Billing.CheckAccountStatus", "Billing.CheckOutstandingAmount", "Billing.NextInvoiceDate", "Billing.ListUnpaidInvoices",
                "Billing.SendInvoice.ByMonth", "Billing.SendInvoice.Last",
                "Payments.SendLink"}
BUSINESS_INTENTS = {"Billing.SendInvoice.ByMonth"}

MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


def normalize_month(value: Any) -> Any:
    if value is None:
        return None
    value = str(value).strip()
    if MONTH_RE.match(value):
        return value
    return None


def get_supply_by_id(data: Dict[str, Any], cups_id: Any) -> Optional[Dict[str, Any]]:
    for s in data.get("supplies", []):
        if s.get("cups_id") == cups_id:
            return s
    return None


def find_invoice_for_period(data: Dict[str, Any], user_id: Any, cups: Optional[str], period: str) -> Optional[Dict[str, Any]]:
    for inv in data.get("invoices", []):
        if inv.get("user_id") == user_id and inv.get("cups") == cups and inv.get("period") == period:
            return inv
    return None


def calc_debt_for_supply(data: Dict[str, Any], user_id: Any, cups: Optional[str]) -> float:
    total = 0.0
    for inv in data.get("invoices", []):
        if inv.get("user_id") == user_id and inv.get("cups") == cups and inv.get("status") in ("DUE", "OVERDUE"):
            total += float(inv.get("amount", 0) or 0)
    return total


def handle_business_intents(payload: Dict[str, Any], data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    payload["_data"] = data

    query_result = payload.get("queryResult", {}) or {}
    intent = (query_result.get("intent") or {}).get("displayName", "")
    params = query_result.get("parameters", {}) or {}

    state = get_context_params(payload, "session_state")
    pending_action = state.get("pending_action")
    pending_params = state.get("pending_params") or {}

    status, ident = identify_user(payload)

    def build_state_response(text: str, updates: Dict[str, Any], lifespan: int = 5) -> Dict[str, Any]:
        merged = dict(state)
        merged.update({k: v for k, v in updates.items() if v is not None})
        ctx = [upsert_context(payload, "session_state", merged, lifespan=lifespan)]
        return build_dialogflow_response(text, output_contexts=ctx)


    def execute_intent_handler(intent_name: str, handler_params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        handler = INTENT_HANDLERS.get(intent_name)
        if not handler:
            return build_dialogflow_response(f"El intent '{intent_name}' aún no está conectado al webhook. (Demo)")
        # El handler espera (session, params, data)
        session = payload.get("session", "")
        try:
            return handler(session=session, params=handler_params, data=data)
        except Exception:
            return build_dialogflow_response("Ha ocurrido un error procesando tu solicitud. ¿Puedes intentarlo de nuevo?")

    if pending_action and status == "OK":
        # Enriquecer los parámetros con los identificados
        enriched_params = dict(pending_params)
        if isinstance(ident, dict):
            enriched_params.update({k: v for k, v in ident.items() if v is not None})
        return execute_intent_handler(pending_action, enriched_params)


    if intent in AUTH_INTENTS:
        if status != "OK":
            updates = {
                "pending_action": intent,
                "pending_params": params,
                "auth_level": "basic",
                "dni_last4": params.get("DNI") or params.get("dni_last4"),
                "cups_last6": params.get("CUPS") or state.get("cups_last6"),
            }
            return build_state_response(ident.get("message", "Necesito mas datos para continuar."), updates)

        # Enriquecer los parámetros originales con los identificados
        enriched_params = dict(params)
        if isinstance(ident, dict):
            enriched_params.update({k: v for k, v in ident.items() if v is not None})
        return execute_intent_handler(intent, enriched_params)

    return None



def require_dni_or_prompt(params: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    dni = params.get("dni_last4")
    if dni is None or str(dni).strip() == "":
        return None, "Para continuar necesito verificar al titular. Dime los últimos 4 dígitos del DNI."
    return str(dni).strip(), None

def handle_check_outstanding_amount(session: str, params: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    dni, prompt = require_dni_or_prompt(params)
    if prompt:
        ctx = [make_context(session, "awaiting_identity", 5)]
        return build_dialogflow_response(prompt, output_contexts=ctx)

    customer = find_customer_by_dni_last4(dni, data)
    if not customer:
        return build_dialogflow_response("No he encontrado el titular con ese DNI. ¿Puedes repetir los últimos 4 dígitos?")

    invoices = get_invoices_for_customer(customer, data)
    unpaid = list_unpaid_invoices(invoices)
    total_due = sum(float(i["amount"]) for i in unpaid) if unpaid else 0.0

    if not unpaid:
        text = "No tienes importe pendiente ✅"
    else:
        text = f"Tu importe pendiente total es {format_eur(total_due)} ({len(unpaid)} factura(s))."

    ctx = [make_context(session, "identity_verified", 10, {"dni_last4": dni})]
    return build_dialogflow_response(text, output_contexts=ctx)

def handle_next_invoice_date(session: str, params: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    
    #! esto simplemente quiero que devuelva el mes siguiente de facturación -- no necesito identificación
    today = datetime.now()
    next_month = today.month + 1 if today.month < 12 else 1
    year = today.year + (1 if next_month == 1 else 0)
    month_name = datetime(year, next_month, 1)
    text = f"La próxima fecha de emisión de factura es en {month_name.strftime('%Y-%m-%d')}."
    return build_dialogflow_response(text)


def handle_send_payment_link(session: str, params: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    dni, prompt = require_dni_or_prompt(params)
    if prompt:
        ctx = [make_context(session, "awaiting_identity", 5)]
        return build_dialogflow_response(prompt, output_contexts=ctx)

    customer = find_customer_by_dni_last4(dni, data)
    if not customer:
        return build_dialogflow_response("No he podido validar el titular. ¿Me dices otra vez los últimos 3 del DNI?")

    # Simulated link generation
    link = f"https://pagos.demo.local/pago?c={customer['user_id']}&t={int(datetime.utcnow().timestamp())}"
    phone = customer.get("phone", "desconocido")
    text = f"Listo. He enviado un enlace de pago al móvil {phone}. (Simulado)\nEnlace: {link}"

    ctx = [make_context(session, "identity_verified", 10, {"dni_last4": dni})]
    return build_dialogflow_response(text, output_contexts=ctx)


# -----------------------------
# Intent routing
# -----------------------------
INTENT_HANDLERS = {
    # "Billing.ListUnpaidInvoices": handle_list_unpaid_invoices,
    "Billing.NextInvoiceDate": handle_next_invoice_date,
    "Payments.SendLink": handle_send_payment_link,
    
    "Billing.Info.OutstandingAmount": handle_check_outstanding_amount,
    # "Billing.Info.AccountStatus": handle_check_account_status,
    "Billing.SendInvoice.ByMonth": handle_send_invoice,
    "Billing.SendInvoice.Last": handle_send_invoice,
}

@app.post("/dialogflow/webhook")
@app.post("/webhook")
async def dialogflow_fulfillment(request: Request) -> JSONResponse:
    body = await request.json()
    
    print("\n\n\nBody recibido desde Dialogflow:", body)  # Esto lo verás en la consola

    session = body.get("session", "")
    query_result = body.get("queryResult", {}) or {}
    intent = (query_result.get("intent") or {}).get("displayName", "")
    params = query_result.get("parameters", {}) or {}

    print("\n\nIntent detectado:", intent)
    print("\nParámetros:", params)

    data = load_data()

    # New business intents with identity + pending action
    business_resp = handle_business_intents(body, data)
    if business_resp is not None:
        return JSONResponse(content=business_resp)

    handler = INTENT_HANDLERS.get(intent)
    if not handler:
        # Safe default: let user know it's not wired yet
        return JSONResponse(
            content=build_dialogflow_response(
                f"El intent '{intent}' aún no está conectado al webhook. (Demo)",
            )
        )

    try:
        resp = handler(session=session, params=params, data=data)
        return JSONResponse(content=resp)
    except Exception as e:
        # Avoid leaking stack traces to user
        return JSONResponse(
            content=build_dialogflow_response(
                "Ha ocurrido un error procesando tu solicitud. ¿Puedes intentarlo de nuevo?"
            ),
            status_code=200,
        )

@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8008, log_level="info", reload=True)