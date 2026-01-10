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

# Billing.SendInvoice
from routers.billing.send_invoice import handle_send_invoice

#Billing.Info
from routers.billing.info import handle_check_account_status, handle_list_unpaid_invoices, handle_check_outstanding_amount

# Info
from routers.info.billing import handle_next_invoice_date

from helpers.aux_functions import (
    identify_user,
    build_dialogflow_response,
    get_context_params,
    make_context,
    upsert_context
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


AUTH_INTENTS = {"Billing.Info.AccountStatus", "Billing.Info.CheckOutstandingAmount", "Billing.Info.NextInvoiceDate", "Billing.Info.ListUnpaidInvoices",
                "Billing.SendInvoice.ByMonth", "Billing.SendInvoice.Last",
                "Payments.SendLink"}
RETRY_INTENTS = {
    "Default.FeedBack.Negative",
}

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

def execute_intent_handler(payload: Dict[str, Any], data: Dict[str, Any], intent_name: str, handler_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Ejecuta un handler por nombre de intent.
    Devuelve SIEMPRE un dict en formato Dialogflow response.
    """
    handler = INTENT_HANDLERS.get(intent_name)
    if not handler:
        return build_dialogflow_response(f"El intent '{intent_name}' aún no está conectado al webhook. (Demo)")

    try:
        result = handler(params=handler_params, data=data)

        # Tus handlers a veces devuelven dict, y handle_send_invoice devuelve (mensaje, params).
        if isinstance(result, tuple) and len(result) == 2:
            msg, returned_params = result
            # Devolvemos el mensaje como response DF, y dejamos params para contextos
            # (el caller montará contextos)
            return {"_message": str(msg), "_params": returned_params}

        if isinstance(result, dict):
            # Si ya viene como build_dialogflow_response
            return {"_df": result, "_params": handler_params}

        # Fallback por si algún handler devuelve string
        return {"_message": str(result), "_params": handler_params}

    except Exception:
        return build_dialogflow_response("Ha ocurrido un error procesando tu solicitud. ¿Puedes intentarlo de nuevo?")


def _normalize_identity_params(params: Dict[str, Any], state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normaliza DNI/CUPS de Dialogflow params a tus claves internas:
      - DNI (solo últimos 4 dígitos + letra)
      - CUPS (solo 6 dígitos)
    """
    dni = (params.get("DNI") or state.get("dni_last4") or "").strip().upper()
    cups = (params.get("CUPS") or state.get("cups_last6") or "").strip().upper()

    # cups_last6: si viene ES000005 guardamos "000005"
    cups_last6 = ""
    if cups:
        if cups.startswith("ES") and len(cups) >= 8:
            cups_last6 = cups[-6:]
        elif re.fullmatch(r"\d{6}", cups):
            cups_last6 = cups
        else:
            # Si no cuadra, lo dejamos tal cual (tu identify_user decidirá si es válido)
            cups_last6 = cups

    merged = dict(state)
    if dni:
        merged["DNI"] = dni
    if cups_last6:
        merged["CUPS"] = cups_last6

    return merged


def handle_business_intents(payload: Dict[str, Any], data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Maneja intents que requieren autenticación en webhook.
    - Guarda pending_action/pending_params cuando falta identidad.
    - En Auth.ProvideIdentity, al completar identidad, ejecuta pending_action.
    """
    query_result = payload.get("queryResult", {}) or {}
    intent = (query_result.get("intent") or {}).get("displayName", "")
    params = query_result.get("parameters", {}) or {}

    session = payload.get("session", "")

    state = get_context_params(payload, "session_state") or {}
    state = _normalize_identity_params(params, state)

    pending_action = state.get("pending_action")
    pending_params = state.get("pending_params") or {}

    print("\n\n\n[general] Intent detectado:", intent)
    print("[general] Parámetros recibidos:", params)
    print("[general] Estado de sesión:", state)
    print("[general] Acción pendiente:", pending_action)
    print("[general] Parámetros pendientes:", pending_params)

    # RETRY: reintentar manteniendo estado
    if intent in RETRY_INTENTS:
        # decide qué reintentar (pending primero, si no last_action)
        action_to_run = state.get("pending_action") or state.get("last_action")
        action_params = state.get("pending_params") or state.get("last_params") or {}

        print("[general][RETRY] action_to_run:", action_to_run)
        print("[general][RETRY] action_params:", action_params)

        if not action_to_run:
            ctx = [upsert_context(payload, "session_state", state, lifespan=10)]
            return build_dialogflow_response(
                "Entendido. ¿Qué estabas intentando hacer exactamente?",
                output_contexts=ctx
            )

    # if intent not in AUTH_INTENTS and intent != "Auth.ProvideIdentity":
    #     return None

    status, ident = identify_user(data, {**state, **params})
    print("[general] Resultado de identify_user:", status, ident)

    if status == "NEED_DNI":
        if intent != "Auth.ProvideIdentity" and intent in AUTH_INTENTS:
            state["pending_action"] = intent
            state["pending_params"] = dict(params)

        ctx = [
            upsert_context(payload, "session_state", state, lifespan=7),
            make_context(session, "ctx_awaiting_identity", 3, {"expected": "DNI"}),
        ]
        print("[general] Falta DNI. Contextos devueltos:", ctx)
        return build_dialogflow_response(
            "Por favor, dime los últimos 4 dígitos y la letra del DNI del titular.",
            output_contexts=ctx
        )

    if status == "NEED_CUPS":
        if intent != "Auth.ProvideIdentity" and intent in AUTH_INTENTS:
            state["pending_action"] = intent
            state["pending_params"] = dict(params)

        ctx = [
            upsert_context(payload, "session_state", state, lifespan=7),
            make_context(session, "ctx_awaiting_identity", 3, {"expected": "CUPS"}),
        ]
        print("[general] Falta CUPS. Contextos devueltos:", ctx)
        return build_dialogflow_response(
            "Para poder identificar el suministro, necesitaré ES + los 6 últimos dígitos del CUPS (por ejemplo: ES123456).",
            output_contexts=ctx
        )

    enriched_params = dict(params)
    if isinstance(ident, dict):
        for k, v in ident.items():
            if v is not None:
                enriched_params[k] = v
    print("[general] Parámetros enriquecidos:", enriched_params)

    action_to_run = None
    action_params = None

    if intent == "Auth.ProvideIdentity" and pending_action:
        action_to_run = pending_action
        action_params = dict(pending_params or {})
        action_params.update({k: enriched_params.get(k) for k in ("user_id", "cups_id") if enriched_params.get(k) is not None})
        print(f"[general] Ejecutando acción pendiente: {action_to_run} con params: {action_params}")
    else:
        action_to_run = intent
        action_params = enriched_params
        print(f"[general] Ejecutando intent actual: {action_to_run} con params: {action_params}")

    result = execute_intent_handler(payload, data, action_to_run, action_params)

    if isinstance(result, dict) and "_df" in result:
        state.pop("pending_action", None)
        state.pop("pending_params", None)

        ctx = [
            upsert_context(payload, "session_state", state, lifespan=10),
            make_context(session, "ctx_awaiting_identity", 0, {}),
            make_context(session, "ctx_identity_verified", 20, {
                "user_id": enriched_params.get("user_id"),
                "cups_id": enriched_params.get("cups_id"),
            }),
        ]
        print("[general] Respuesta directa del handler (error o especial):", result["_df"])
        print("[general] Contextos devueltos:", ctx)
        df_resp = result["_df"]
        df_resp["outputContexts"] = ctx
        return df_resp

    output_msg = result.get("_message", "")
    returned_params = result.get("_params", {}) or {}

    state["last_action"] = action_to_run
    state["last_params"] = action_params

    if intent == "Auth.ProvideIdentity" and pending_action:
        state.pop("pending_action", None)
        state.pop("pending_params", None)

    verified_payload = {}
    if enriched_params.get("user_id") is not None and enriched_params.get("cups_id") is not None:
        verified_payload = {"user_id": enriched_params.get("user_id"), "cups_id": enriched_params.get("cups_id")}

    ctx = [
        upsert_context(payload, "session_state", {**state, **returned_params}, lifespan=10),
        make_context(session, "ctx_awaiting_identity", 0, {}),
    ]
    if verified_payload:
        ctx.append(make_context(session, "ctx_identity_verified", 20, verified_payload))

    print("[general] Mensaje de salida:", output_msg)
    print("[general] Contextos devueltos:", ctx)

    return build_dialogflow_response(output_msg, output_contexts=ctx)


def handle_send_payment_link(params: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    
    if not params.get("user_id"):
        return build_dialogflow_response("No hemos podido identificar el suministro. Por favor, vuelva a intentarlo más tarde.")
    
    if not params.get("cups_id"):
        return build_dialogflow_response("No hemos podido identificarlo. Por favor, vuelva a intentarlo más tarde.")
    
    # Identificamos al cliente y su suministro
    cups_id = params.get("cups_id")
    user_id = params.get("user_id")

    # Simulated link generation
    link = f"https://pagos.demo.local/pago?c={user_id}&t={int(datetime.utcnow().timestamp())}"
    phone = "desconocido"
    text = f"Listo. He enviado un enlace de pago al móvil {phone}. (Simulado)\nEnlace: {link}"

    return text, params


# -----------------------------
# Intent routing
# -----------------------------
INTENT_HANDLERS = {
    "Info.NextInvoiceDate": handle_next_invoice_date,
    
    "Billing.Info.UnpaidInvoices": handle_list_unpaid_invoices,
    "Billing.Info.OutstandingAmount": handle_check_outstanding_amount,
    "Billing.Info.AccountStatus": handle_check_account_status,
    
    "Billing.SendInvoice.ByMonth": handle_send_invoice,
    "Billing.SendInvoice.Last": handle_send_invoice,
    
    "Payments.SendLink": handle_send_payment_link,
}

@app.post("/dialogflow/webhook")
async def dialogflow_fulfillment(request: Request) -> JSONResponse:
    body = await request.json()
    
    print("\n\n\n body = ", body)  # Esto lo verás en la consola

    session = body.get("session", "")
    query_result = body.get("queryResult", {}) or {}
    intent = (query_result.get("intent") or {}).get("displayName", "")
    params = query_result.get("parameters", {}) or {}

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