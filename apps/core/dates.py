"""Utils de data: avanço de competência/vencimentos mensais."""

import calendar
from datetime import date


def add_months(d: date, n: int) -> date:
    """
    Avança `d` em `n` meses, fixando o dia ao último dia válido do mês destino.

    Ex.: 31/01 + 1 mês -> 28/02 (ou 29/02 em ano bissexto). Usado para gerar
    vencimentos de parcelas mês a mês sem estourar dia inexistente.
    """
    total = d.month - 1 + n
    ano = d.year + total // 12
    mes = total % 12 + 1
    ultimo_dia = calendar.monthrange(ano, mes)[1]
    return date(ano, mes, min(d.day, ultimo_dia))
