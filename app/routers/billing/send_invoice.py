from typing import Any, Dict, Optional

from helpers.aux_functions import (
    build_dialogflow_response,
    periodo_a_texto,
)

""" 

INTENTS

    1. Billing.SendInvoice.Last 
        Enviamos la última factura disponible al cliente.
    
    2. Billing.SendInvoice.Period
        Enviamos la factura de un periodo concreto al cliente, la que él indique.

"""


def handle_send_invoice(params: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        
    if not params.get("user_id"):
        return build_dialogflow_response("No hemos podido identificar el suministro. Por favor, vuelva a intentarlo más tarde.")
    
    if not params.get("cups_id"):
        return build_dialogflow_response("No hemos podido identificarlo. Por favor, vuelva a intentarlo más tarde.")

    # Identificamos al cliente y su suministro
    cups_id = params.get("cups_id")
    user_id = params.get("user_id")
    invoices = [i for i in data.get("invoices", []) if i.get("user_id") == user_id and i.get("cups_id") == cups_id]
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

        periodo_escrito = periodo_a_texto(period)
        mensaje = (
            f"Perfecto. A continuación te adjuntamos la última factura disponible. Es la factura correspondiente al periodo de {periodo_escrito}"
        )

    link = f"https://pagos.demo.local/factura/{invoice['invoice_id']}"
    mensaje = f"{mensaje}\n Puede descargarla a través del siguiente link: {link}"

    return mensaje, params
