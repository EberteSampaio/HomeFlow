"""Leitura para lembretes de vencimento."""

from datetime import date, timedelta

from django.db.models import F, QuerySet

from apps.expenses.models import Rateio


def rateios_proximos_do_vencimento(*, hoje: date, dias: int) -> QuerySet[Rateio]:
    """
    Rateios PENDENTES cujo vencimento cai até `hoje + dias`.

    Exclui rateios em que o devedor é o próprio pagador (não há dívida), pelo
    mesmo critério do motor de saldo. Ordenado por vencimento.
    """
    limite = hoje + timedelta(days=dias)
    return (
        Rateio.objects.filter(
            status_pagamento=Rateio.StatusPagamento.PENDENTE,
            parcela__data_vencimento__lte=limite,
        )
        .exclude(membro=F("parcela__compra__pago_por"))
        .select_related(
            "membro__usuario",
            "membro__casal",
            "parcela__compra",
            "parcela__compra__casal",
            "parcela__compra__pago_por__usuario",
        )
        .order_by("parcela__data_vencimento")
    )
