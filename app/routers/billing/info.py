from typing import Any, Dict, List


from helpers.aux_functions import (
    build_dialogflow_response,
    format_eur
)

""" 

INTENTS

    1. Billing.Info.AccountStatus --> handle_check_account_status
        Comprobamos el estado de la cuenta del cliente, si tiene facturas pendientes o está al corriente.
    
    2. Billing.Info.UnpaidInvoices --> handle_list_unpaid_invoices
        Listamos las facturas pendientes de pago del cliente.
        
    3. Billing.Info.OutstandingAmount --> handle_check_outstanding_amount
        Comprobamos el importe total pendiente de pago del cliente.

"""

def invoice_is_unpaid(inv: Dict[str, Any]) -> bool:
    return inv.get("status") in ("DUE", "OVERDUE")

def list_unpaid_invoices(invoices: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    unpaid = [i for i in invoices if invoice_is_unpaid(i)]
    # Keep most recent first
    unpaid.sort(key=lambda x: (x.get("due_date", ""), x.get("issue_date", "")), reverse=True)
    return unpaid


def handle_check_account_status(params: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Función para manejar el intent Billing.Info.AccountStatus.
    
    Comprobamos el estado de la cuenta del cliente, si tiene facturas pendientes o está al corriente.
    """

    if not params.get("user_id"):
        return build_dialogflow_response("No hemos podido identificar el suministro. Por favor, vuelva a intentarlo más tarde.")
    
    if not params.get("cups_id"):
        return build_dialogflow_response("No hemos podido identificarlo. Por favor, vuelva a intentarlo más tarde.")
    
    # Identificamos al cliente y su suministro
    cups_id = params.get("cups_id")
    user_id = params.get("user_id")

    # Traemos sus facturas pendientes
    invoices = [i for i in data.get("invoices", []) if i.get("user_id") == user_id and i.get("cups_id") == cups_id]
    unpaid = list_unpaid_invoices(invoices)
    total_due = sum(float(i["amount"]) for i in unpaid) if unpaid else 0.0

    if not unpaid:
        text = "Estás al corriente de pago. No tienes facturas pendientes."
    else:
        if len(unpaid) == 1:
            text = f"Tienes 1 factura pendiente por un total de {format_eur(total_due)}."
        else: 
            text = f"Tienes {len(unpaid)} facturas pendientes por un total de {format_eur(total_due)}."

    return text, params


def handle_list_unpaid_invoices(params: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Función para manejar el intent Billing.Info.UnpaidInvoices.
    
    Listamos las facturas pendientes de pago del cliente.
    """
    
    if not params.get("user_id"):
        return build_dialogflow_response("No hemos podido identificar el suministro. Por favor, vuelva a intentarlo más tarde.")
    
    if not params.get("cups_id"):
        return build_dialogflow_response("No hemos podido identificarlo. Por favor, vuelva a intentarlo más tarde.")
    
    # Identificamos al cliente y su suministro
    cups_id = params.get("cups_id")
    user_id = params.get("user_id")

    # Traemos sus facturas pendientes
    invoices = [i for i in data.get("invoices", []) if i.get("user_id") == user_id and i.get("cups") == cups_id]
    unpaid = list_unpaid_invoices(invoices)

    if not unpaid:
        text = "No tienes facturas pendientes."
    else:
        # List max 3 for brevity
        lines = []
        for inv in unpaid[:3]:
            lines.append(f"- {inv['period']} | {format_eur(float(inv['amount']))} | vence {inv['due_date']} | {inv['status']}")
        text = "Estas son tus facturas pendientes (máx. 3):\n" + "\n".join(lines)

    return text, params


def handle_check_outstanding_amount(params: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Función para manejar el intent Billing.Info.OutstandingAmount.
    
    Comprobamos el importe total pendiente de pago del cliente.
    """
    
    # Identificamos al cliente y su suministro
    cups_id = params.get("cups_id")
    user_id = params.get("user_id")

    # Traemos sus facturas pendientes
    invoices = [i for i in data.get("invoices", []) if i.get("user_id") == user_id and i.get("cups") == cups_id]
    unpaid = list_unpaid_invoices(invoices)
    total_due = sum(float(i["amount"]) for i in unpaid) if unpaid else 0.0

    if not unpaid:
        text = "No tienes importe pendiente."
    else:
        text = f"Tu importe pendiente total es {format_eur(total_due)} ({len(unpaid)} factura(s))."

    return text, params