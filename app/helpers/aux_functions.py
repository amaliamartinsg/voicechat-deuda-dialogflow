from __future__ import annotations

import re
import locale
from datetime import datetime
from typing import Any, Dict, List, Optional


# Convertir el periodo (YYYY-MM) a "mes de año" en español
locale.setlocale(locale.LC_TIME, "es_ES.UTF-8")
def periodo_a_texto(periodo):
    
    if not periodo or not isinstance(periodo, str) or not periodo[:7].replace("-", "").isdigit():
        return periodo
        
    meses = [
    "", "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
    ]
    
    try:
        anio, mes = periodo.split("-")
        mes_nombre = meses[int(mes)]
        return f"{mes_nombre} de {anio}"
    except Exception:
        return periodo

def texto_a_periodo(texto: str) -> Optional[str]:
    texto = texto.lower().strip()
    meses = {
        "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
        "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
        "septiembre": "09", "octubre": "10", "noviembre": "11", "diciembre": "12"
    }
    mes_num = meses.get(texto)
    
    # Si el texto es solo un mes, y estamos en ese mes pero aún no ha terminado, se refiere al año pasado
    if mes_num:
        ahora = datetime.now()
        mes_actual = ahora.month
        anio_actual = ahora.year
        if mes_actual < int(mes_num) and ahora.day < 28:
            # Consideramos que el mes no ha terminado si es antes del día 28
            return f"{anio_actual - 1}-{mes_num}"
        return f"{anio_actual}-{mes_num}"
    if mes_num:
        return mes_num
    
    return None



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

def format_eur(amount: float) -> str:
    # Simple formatting Spanish style (comma decimal)
    return f"{amount:,.2f}€".replace(",", "X").replace(".", ",").replace("X", ".")


def build_dialogflow_response(text: str, output_contexts: Optional[List[Dict[str, Any]]] = None, payload: Optional[Dict[str, Any]] = None ) -> Dict[str, Any]:
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
    if value == '-':
        return None
    value = str(value).strip().upper()
    if DNI_PARTIAL_RE.match(value):
        return value
    return None

def normalize_cups_last6(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    if value == '-':
        return None
    value = str(value).strip().upper()
    if CUPS_PARTIAL_RE.match(value):
        if value.startswith("ES"):
            return value[2:]
        return value
    return None


def identify_user(data: Dict[str, Any], params: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
    """
    status:
      - OK: user_id + cups_id resueltos
      - NEED_DNI: falta dni parcial
      - NEED_CUPS: usuario con multiples suministros y falta cups_last6
    """
    user_id = params.get("user_id")
    cups_id = params.get("cups_id")
    if user_id and cups_id:
        return "OK", {"user_id": user_id, "cups_id": cups_id}

    dni_original = params.get("DNI") or params.get("dni_last4")
    cups_original = params.get("CUPS") or params.get("cups_last6")

    dni_last4 = normalize_dni_partial(dni_original)
    cups_last6 = normalize_cups_last6(cups_original)
    
    if not dni_last4:
        return "NEED_DNI", {
            "message": "Para continuar necesito los ultimos 4 digitos y letra del DNI (ej: 5678Z)."
        }

    customer = find_customer_by_dni_last4(dni_last4, data)
    if not customer:
        return "NEED_DNI", {
            "message": "No encuentro ese DNI parcial. Puedes revisarlo y repetirlo?"
        }

    user_id = customer.get("user_id")
    supplies = [s for s in data.get("supplies", []) if s.get("user_id") == user_id]

    if len(supplies) == 1:
        return "OK", {"user_id": user_id, "cups_id": supplies[0].get("cups_id")}

    if not cups_last6:
        return "NEED_CUPS", {
            "user_id": user_id,
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
            "user_id": user_id,
            "message": "Ese CUPS no coincide con tus suministros. Dime los ultimos 6 caracteres correctos."
        }

    return "OK", {
        "user_id": user_id,
        "cups_id": supply.get("cups_id"),
    }
