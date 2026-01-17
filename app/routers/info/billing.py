from typing import Any, Dict, List
from datetime import datetime

from helpers.aux_functions import periodo_a_texto


""" 

INTENTS

    1. Info.NextInvoiceDate --> handle_next_invoice_date
        Comprobamos la próxima fecha de emisión de factura.

"""

def handle_next_invoice_date(params: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    
    today = datetime.now()
    next_month = today.month + 1 if today.month < 12 else 1
    year = today.year + (1 if next_month == 1 else 0)
    month_name = datetime(year, next_month, 1)
    text = f"La próxima fecha de emisión de factura es en {periodo_a_texto(month_name.strftime('%Y-%m'))}."
    return text, params

# def handle_