from typing import Any, Dict, Optional

from helpers.aux_functions import (
    build_dialogflow_response,
    find_customer_by_dni_last4,
    format_eur,
    make_context
)

""" 

INTENTS

    1. Billing.Info.AccountStatus --> handle_check_account_status
        Comprobamos el estado de la cuenta del cliente, si tiene facturas pendientes o está al corriente.
    
    2. Billing.Info.UnpaidInvoices --> handle_list_unpaid_invoices
        Listamos las facturas pendientes de pago del cliente.

"""



def handle_check_account_status(session: str, params: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    dni, prompt = require_dni_or_prompt(params)
    if prompt:
        # Ask for dni, keep context awaiting_identity
        ctx = [make_context(session, "awaiting_identity", 5)]
        return build_dialogflow_response(prompt, output_contexts=ctx)

    customer = find_customer_by_dni_last4(dni, data)
    if not customer:
        return build_dialogflow_response("No he encontrado ningún cliente con esos datos. ¿Puedes revisar los últimos 4 dígitos del DNI?")

    invoices = get_invoices_for_customer(customer, data)
    unpaid = list_unpaid_invoices(invoices)
    total_due = sum(float(i["amount"]) for i in unpaid) if unpaid else 0.0

    if not unpaid:
        text = "Estás al corriente de pago ✅ No tienes facturas pendientes."
    else:
        text = f"Tienes {len(unpaid)} factura(s) pendiente(s) por un total de {format_eur(total_due)}."
    ctx = [make_context(session, "identity_verified", 10, {"dni_last4": dni})]
    return build_dialogflow_response(text, output_contexts=ctx)

def handle_list_unpaid_invoices(session: str, params: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    dni, prompt = require_dni_or_prompt(params)
    if prompt:
        ctx = [make_context(session, "awaiting_identity", 5)]
        return build_dialogflow_response(prompt, output_contexts=ctx)

    customer = find_customer_by_dni_last4(dni, data)
    if not customer:
        return build_dialogflow_response("No he podido validar el titular con esos datos. ¿Me dices de nuevo los últimos 4 dígitos del DNI?")

    invoices = get_invoices_for_customer(customer, data)
    unpaid = list_unpaid_invoices(invoices)

    if not unpaid:
        text = "No tienes facturas pendientes ✅"
    else:
        # List max 3 for brevity
        lines = []
        for inv in unpaid[:3]:
            lines.append(f"- {inv['period']} | {format_eur(float(inv['amount']))} | vence {inv['due_date']} | {inv['status']}")
        text = "Estas son tus facturas pendientes (máx. 3):\n" + "\n".join(lines)

    ctx = [make_context(session, "identity_verified", 10, {"dni_last4": dni})]
    return build_dialogflow_response(text, output_contexts=ctx)

