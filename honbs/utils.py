from datetime import datetime

def format_date(date):
    """Formata datetime para string legível."""
    if isinstance(date, datetime):
        return date.strftime("%d/%m/%Y %H:%M")
    return "Data Inválida"