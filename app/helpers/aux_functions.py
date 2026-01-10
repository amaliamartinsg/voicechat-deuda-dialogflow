from __future__ import annotations

from datetime import datetime
import re
from typing import Any, Dict, List, Optional


def find_customer_by_dni_last4(dni_last4: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    dni_last4 = str(dni_last4).strip().upper()
    for c in data.get("customers", []):
        # Prefer explicit field if present
        if str(c.get("dni_last4", "")).strip().upper() == dni_last4:
            return c
        account_dni = str(c.get("account_dni", "")).strip().upper()
        if account_dni.endswith(dni_last4):
            return c
    return None

def parse_iso_date(s: str) -> Optional[datetime]:
    """
    Dialogflow sys.date can return:
      - '2025-02-01'
      - '2025-02-15'
      - sometimes '2025-02' (less common)
    We'll handle YYYY-MM and YYYY-MM-DD.
    """
    if not s:
        return None
    s = str(s)
    try:
        if len(s) == 7:  # YYYY-MM
            return datetime.strptime(s, "%Y-%m")
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        return None

def normalize_period(date_param: Optional[str], month_param: Optional[str]) -> Optional[str]:
    """
    Output:
      - 'YYYY-MM' if year present
      - 'XXXX-MM' if only month
      - None if neither provided
    """
    # Prefer sys.date if provided and parseable
    if date_param:
        dt = parse_iso_date(date_param)
        if dt:
            return dt.strftime("%Y-%m")

        # If date_param is directly "YYYY-MM"
        if isinstance(date_param, str) and len(date_param) == 7 and date_param[4] == "-":
            return date_param

    # Otherwise month (already '01'..'12')
    if month_param:
        mm = str(month_param).zfill(2)
        if mm.isdigit() and 1 <= int(mm) <= 12:
            return f"XXXX-{mm}"

    return None

def format_eur(amount: float) -> str:
    # Simple formatting Spanish style (comma decimal)
    return f"{amount:,.2f}€".replace(",", "X").replace(".", ",").replace("X", ".")

def get_invoices_for_customer(customer: Dict[str, Any], data: Dict[str, Any]) -> List[Dict[str, Any]]:
    user_id = customer.get("user_id")
    invoices = [i for i in data.get("invoices", []) if i.get("user_id") == user_id]
    # Sort descending by issue_date then due_date
    invoices.sort(key=lambda x: (x.get("issue_date", ""), x.get("due_date", "")), reverse=True)
    return invoices

def invoice_is_unpaid(inv: Dict[str, Any]) -> bool:
    return inv.get("status") in ("DUE", "OVERDUE")

def list_unpaid_invoices(invoices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    unpaid = [i for i in invoices if invoice_is_unpaid(i)]
    # Keep most recent first
    unpaid.sort(key=lambda x: (x.get("due_date", ""), x.get("issue_date", "")), reverse=True)
    return unpaid

def build_dialogflow_response(
    text: str,
    output_contexts: Optional[List[Dict[str, Any]]] = None,
    payload: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    resp: Dict[str, Any] = {"fulfillmentText": text}
    if output_contexts:
        resp["outputContexts"] = output_contexts
    if payload:
        resp["payload"] = payload
    return resp

def make_context(session: str, name: str, lifespan: int, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    # In Dialogflow ES v2, context name is: {session}/contexts/{contextName}
    ctx = {
        "name": f"{session}/contexts/{name}",
        "lifespanCount": lifespan,
    }
    if parameters:
        ctx["parameters"] = parameters
    return ctx


# --- Dialogflow context helpers ---
def get_context_params(payload: Dict[str, Any], context_name: str) -> Dict[str, Any]:
    output_contexts = payload.get("queryResult", {}).get("outputContexts", [])
    for ctx in output_contexts:
        name = ctx.get("name", "")
        if name.endswith("/contexts/" + context_name):
            return ctx.get("parameters", {}) or {}
    return {}

def upsert_context(payload: Dict[str, Any], context_name: str, params: Dict[str, Any], lifespan: int = 5) -> Dict[str, Any]:
    session = payload.get("session", "")
    return {
        "name": f"{session}/contexts/{context_name}",
        "lifespanCount": lifespan,
        "parameters": params,
    }

# --- Identity helpers ---
DNI_PARTIAL_RE = re.compile(r"^\d{4}[A-Za-z]$")
CUPS_PARTIAL_RE = re.compile(r"^(ES)?[A-Za-z0-9]{6}$")

def normalize_dni_partial(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = str(value).strip().upper()
    if DNI_PARTIAL_RE.match(value):
        return value
    return None

def normalize_cups_last6(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = str(value).strip().upper()
    if CUPS_PARTIAL_RE.match(value):
        if value.startswith("ES"):
            return value[2:]
        return value
    return None

def identify_user(payload: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
    """
    status:
      - OK: id_user + id_cups resueltos
      - NEED_DNI: falta dni parcial
      - NEED_CUPS: usuario con multiples suministros y falta cups_last6
    """
    data = payload.get("_data", {})
    params = payload.get("queryResult", {}).get("parameters", {}) or {}
    state = get_context_params(payload, "session_state")

    id_user = state.get("id_user")
    id_cups = state.get("id_cups")
    if id_user and id_cups:
        return "OK", {"id_user": id_user, "id_cups": id_cups}

    dni = normalize_dni_partial(params.get("dni_last4_letter") or params.get("dni_last4") or params.get("DNI") or state.get("dni_last4_letter") or state.get("dni_last4"))
    cups_last6 = normalize_cups_last6(params.get("cups_last6") or state.get("cups_last6"))

    if not dni:
        return "NEED_DNI", {
            "message": "Para continuar necesito los ultimos 4 digitos y letra del DNI (ej: 5678Z)."
        }

    customer = find_customer_by_dni_last4(dni, data)
    if not customer:
        return "NEED_DNI", {
            "message": "No encuentro ese DNI parcial. Puedes revisarlo y repetirlo?"
        }

    id_user = customer.get("user_id")
    supplies = [s for s in data.get("supplies", []) if s.get("user_id") == id_user]

    if len(supplies) == 1:
        return "OK", {"id_user": id_user, "id_cups": supplies[0].get("id_cups"), "dni_last4_letter": dni}

    if not cups_last6:
        return "NEED_CUPS", {
            "id_user": id_user,
            "message": "Tienes varios suministros. Indica el CUPS (ES + 6 caracteres) o los ultimos 6 caracteres."
        }

    supply = None
    for s in supplies:
        cups = str(s.get("cups", "")).upper()
        if cups[-6:] == cups_last6:
            supply = s
            break

    if not supply:
        return "NEED_CUPS", {
            "id_user": id_user,
            "message": "Ese CUPS no coincide con tus suministros. Dime los ultimos 6 caracteres correctos."
        }

    return "OK", {
        "id_user": id_user,
        "id_cups": supply.get("id_cups"),
        "dni_last4_letter": dni,
    }
