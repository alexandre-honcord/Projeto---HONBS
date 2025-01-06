from datetime import date, datetime

def format_datetime(date_obj, include_time=False):
    """Formata datetime para string legível."""
    if date_obj is None:
        return "N/A"  # Retorna um valor padrão para datas inválidas ou ausentes
    if isinstance(date_obj, datetime):
        return date_obj.strftime("%d/%m/%Y %H:%M:%S") if include_time else date_obj.strftime("%d/%m/%Y")
    elif isinstance(date_obj, date):
        return date_obj.strftime("%d/%m/%Y")
    return "Data Inválida"

def separar_iniciais_por_ponto(iniciais):
    """Recebe as iniciais e separa cada letra por ponto."""
    if not iniciais:
        return "N/A"
    return ".".join(list(iniciais.upper())) + "."