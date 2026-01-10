from typing import Any, Dict, Optional

from helpers.aux_functions import (
    build_dialogflow_response,
    find_customer_by_dni_last4,
    format_eur,
    make_context,
)

""" 

INTENTS

    1. Billing.SendInvoice.Last 
        Enviamos la última factura disponible al cliente.
    
    2. Billing.SendInvoice.Period
        Enviamos la factura de un periodo concreto al cliente, la que él indique.

"""


def _normalize_cups_last6(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    value = str(value).strip().upper()
    if value.startswith("ES") and len(value) == 8:
        return value[2:]
    if len(value) == 6:
        return value
    return None


def _get_supply_for_user(data: Dict[str, Any], user_id: Any, cups_last6: Optional[str]) -> Optional[Dict[str, Any]]:
    supplies = [s for s in data.get("supplies", []) if s.get("user_id") == user_id]
    if not supplies:
        return None
    if len(supplies) == 1:
        return supplies[0]
    if not cups_last6:
        return None
    for s in supplies:
        cups = str(s.get("cups", "")).upper()
        if cups.endswith(cups_last6):
            return s
    return None


def handle_send_invoice(session: str, params: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    dni = params.get("DNI") or params.get("dni_last4") or params.get("dni_last4_letter")
    if not dni:
        ctx = [make_context(session, "awaiting_identity", 5)]
        return build_dialogflow_response(
            "Para continuar necesito los ultimos 4 digitos y letra del DNI.",
            output_contexts=ctx,
        )

    customer = find_customer_by_dni_last4(str(dni), data)
    if not customer:
        return build_dialogflow_response("No he encontrado ningun cliente con ese DNI. Puedes revisarlo?")

    user_id = customer.get("user_id")
    cups_last6 = _normalize_cups_last6(params.get("cups_last6") or params.get("CUPS"))
    supply = _get_supply_for_user(data, user_id, cups_last6)
    if not supply:
        ctx = [make_context(session, "awaiting_supply", 5, {"dni_last4": dni})]
        return build_dialogflow_response(
            "Tienes varios suministros. Indica el CUPS (ES + 6 caracteres) o los ultimos 6 caracteres.",
            output_contexts=ctx,
        )

    cups = supply.get("cups")
    invoices = [i for i in data.get("invoices", []) if i.get("user_id") == user_id and i.get("cups") == cups]
    invoices.sort(key=lambda x: (x.get("issue_date", ""), x.get("due_date", "")), reverse=True)

    period = params.get("period") or params.get("month")
    if period:
        invoice = next((i for i in invoices if i.get("period") == period), None)
        if not invoice:
            return build_dialogflow_response(f"No se ha encontrado factura para el periodo {period}.")
        mensaje = f"Perfecto. Te reenviaremos la factura del periodo {period}. Por favor, revise su buzon en unos minutos."
    else:
        invoice = invoices[0] if invoices else None
        if not invoice:
            return build_dialogflow_response("No tengo facturas disponibles para tu contrato.")
        period = invoice.get("period")
        mensaje = (
            "Perfecto. A continuacion te reenviaremos la ultima factura disponible. "
            "Por favor, revise su buzon en unos minutos."
        )

    link = f"https://pagos.demo.local/factura/{invoice['invoice_id']}"
    total = format_eur(float(invoice["amount"]))
    mensaje = f"{mensaje}\nImporte: {total}. Link: {link}"

    ctx = [
        make_context(
            session,
            "identity_verified",
            10,
            {"dni_last4": dni, "period": period, "id_cups": supply.get("id_cups")},
        )
    ]
    return build_dialogflow_response(mensaje, output_contexts=ctx)
