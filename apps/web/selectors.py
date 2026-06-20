"""Leitura/composição para as telas (mantém as views finas)."""

import calendar
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db.models import Sum
from django.db.models.functions import TruncMonth
from django.utils import timezone

from apps.accounts.models import Casal, RegraDivisao
from apps.core.money import ratear_por_percentuais
from apps.expenses.models import Compra, DespesaRecorrente, Parcela, Rateio
from apps.settlements.selectors import SaldoPar, calcular_saldo, saldo_por_mes


@dataclass(frozen=True)
class LinhaDivisao:
    nome: str
    percentual: Decimal
    valor: Decimal


def _aplicar_filtros(qs, filtros: dict | None):
    """Aplica os filtros opcionais do Painel a um queryset de Compra."""
    if not filtros:
        return qs
    if filtros.get("categoria"):
        qs = qs.filter(categoria=filtros["categoria"])
    if filtros.get("pago_por"):
        qs = qs.filter(pago_por=filtros["pago_por"])
    if filtros.get("status"):
        qs = qs.filter(status=filtros["status"])
    mes = filtros.get("mes")
    if mes:
        qs = qs.filter(data_compra__year=mes.year, data_compra__month=mes.month)
    return qs


def dashboard_data(casal: Casal, *, filtros: dict | None = None) -> dict:
    """
    Agrega os dados do Painel. Os `filtros` (categoria, quem pagou, mês, status)
    são aplicados às Despesas Recentes e ao gráfico de Gastos por Categoria.
    O saldo e as próximas parcelas permanecem globais (estado real do casal).
    """
    hoje = timezone.localdate()

    compras = _aplicar_filtros(Compra.objects.filter(casal=casal), filtros)

    compras_recentes = compras.select_related(
        "categoria", "pago_por__usuario"
    ).order_by("-data_compra", "-criado_em")[:50]

    proximas_parcelas = (
        Parcela.objects.filter(compra__casal=casal, data_vencimento__gte=hoje)
        .select_related("compra", "compra__pago_por__usuario")
        .order_by("data_vencimento")[:50]
    )

    gastos_por_categoria = list(
        compras.values("categoria__nome")
        .annotate(total=Sum("valor_total"))
        .order_by("-total")
    )
    total_geral = sum((g["total"] or Decimal("0.00")) for g in gastos_por_categoria)
    for g in gastos_por_categoria:
        g["nome"] = g["categoria__nome"] or "Sem categoria"
        g["pct"] = (
            int((g["total"] or Decimal("0")) / total_geral * 100)
            if total_geral
            else 0
        )

    gastos_por_mes = _gastos_por_mes(casal, filtros)
    qtd_despesas = compras.count()
    saldo_total = sum(
        (par.valor for par in calcular_saldo(casal, filtros=filtros)),
        Decimal("0.00"),
    )

    return {
        "saldo_por_mes": saldo_por_mes(casal, filtros=filtros),
        "compras_recentes": compras_recentes,
        "proximas_parcelas": proximas_parcelas,
        "gastos_por_categoria": gastos_por_categoria,
        "gastos_por_mes": gastos_por_mes,
        "total_geral": total_geral,
        "qtd_despesas": qtd_despesas,
        "saldo_total": saldo_total,
        "filtros_ativos": bool(filtros),
    }


def _gastos_por_mes(casal: Casal, filtros: dict | None) -> list[dict]:
    """
    Série de gasto total por mês (mês da compra), para o gráfico de tendência.

    Respeita os filtros de categoria/quem pagou/status, mas **ignora** o filtro
    de mês — assim o gráfico mostra a evolução e o mês escolhido fica em destaque.
    """
    f = dict(filtros or {})
    f.pop("mes", None)
    qs = _aplicar_filtros(Compra.objects.filter(casal=casal), f)
    rows = (
        qs.annotate(mes_ref=TruncMonth("data_compra"))
        .values("mes_ref")
        .annotate(total=Sum("valor_total"))
        .order_by("mes_ref")
    )
    return [
        {"mes": r["mes_ref"], "total": r["total"] or Decimal("0.00")}
        for r in rows
        if r["mes_ref"] is not None
    ]


def _aplicar_filtros_parcela(qs, filtros: dict | None):
    """Aplica os filtros do Painel a um queryset de Parcela (via atributos da compra)."""
    if not filtros:
        return qs
    if filtros.get("categoria"):
        qs = qs.filter(compra__categoria=filtros["categoria"])
    if filtros.get("pago_por"):
        qs = qs.filter(compra__pago_por=filtros["pago_por"])
    if filtros.get("status"):
        qs = qs.filter(compra__status=filtros["status"])
    mes = filtros.get("mes")
    if mes:
        qs = qs.filter(
            data_vencimento__year=mes.year, data_vencimento__month=mes.month
        )
    return qs


def parcelas_por_mes(casal: Casal, filtros: dict | None = None) -> list[dict]:
    """
    Série do valor de **parcelas** por mês de **vencimento**, para o gráfico
    da aba Parcelas. Respeita categoria/quem pagou/status, mas ignora o filtro
    de mês (a série mostra a evolução completa).
    """
    f = dict(filtros or {})
    f.pop("mes", None)
    qs = _aplicar_filtros_parcela(Parcela.objects.filter(compra__casal=casal), f)
    rows = (
        qs.annotate(mes_ref=TruncMonth("data_vencimento"))
        .values("mes_ref")
        .annotate(total=Sum("valor"))
        .order_by("mes_ref")
    )
    return [
        {"mes": r["mes_ref"], "total": r["total"] or Decimal("0.00")}
        for r in rows
        if r["mes_ref"] is not None
    ]


def _parcela_quitada(parcela: Parcela) -> bool:
    """True se não há dívida PENDENTE de terceiros nessa parcela (usa rateios prefetchados)."""
    pagador_id = parcela.compra.pago_por_id
    for r in parcela.rateios.all():
        if (
            r.membro_id != pagador_id
            and r.status_pagamento == Rateio.StatusPagamento.PENDENTE
        ):
            return False
    return True


def despesas_do_mes(casal: Casal, mes: date) -> dict:
    """
    Contas a pagar no mês, separadas em **fixas** (despesas recorrentes) e
    **variáveis** (parcelas de compras avulsas que vencem no mês).

    `mes` é normalizado para o 1º dia. As fixas usam a definição da
    DespesaRecorrente ativa (vencimento = dia_vencimento ajustado ao mês);
    as variáveis vêm das parcelas avulsas com vencimento no mês.
    """
    mes = mes.replace(day=1)
    ultimo_dia = calendar.monthrange(mes.year, mes.month)[1]

    fixas: list[dict] = []
    total_fixas = Decimal("0.00")
    recorrentes = DespesaRecorrente.objects.filter(
        casal=casal, ativo=True
    ).select_related("categoria", "pago_por__usuario")
    for rec in recorrentes:
        vencimento = mes.replace(day=min(rec.dia_vencimento, ultimo_dia))
        gerada = Compra.objects.filter(recorrente=rec, competencia=mes).first()
        fixas.append(
            {
                "descricao": rec.descricao,
                "categoria": rec.categoria,
                "valor": rec.valor,
                "vencimento": vencimento,
                "pago_por": rec.pago_por,
                "gerada": gerada is not None,
            }
        )
        total_fixas += rec.valor
    fixas.sort(key=lambda f: f["vencimento"])

    parcelas = (
        Parcela.objects.filter(
            compra__casal=casal,
            compra__origem=Compra.Origem.AVULSA,
            data_vencimento__year=mes.year,
            data_vencimento__month=mes.month,
        )
        .select_related("compra__categoria", "compra__pago_por__usuario")
        .prefetch_related("rateios")
        .order_by("data_vencimento")
    )
    variaveis: list[dict] = []
    total_variaveis = Decimal("0.00")
    for p in parcelas:
        variaveis.append({"parcela": p, "pago": _parcela_quitada(p)})
        total_variaveis += p.valor

    return {
        "mes": mes,
        "fixas": fixas,
        "variaveis": variaveis,
        "total_fixas": total_fixas,
        "total_variaveis": total_variaveis,
        "total": total_fixas + total_variaveis,
    }


def preview_divisao(
    *, casal: Casal, valor: Decimal, data: date
) -> list[LinhaDivisao] | None:
    """
    Prévia da 'Divisão Automática': aplica a regra vigente na data ao valor.

    Retorna None se não houver regra vigente na data (a UI mostra um aviso).
    """
    regra = RegraDivisao.vigente_em(casal, data)
    if regra is None:
        return None

    itens = list(regra.itens.select_related("membro__usuario"))
    percentuais = [item.percentual for item in itens]

    if valor and valor > 0:
        valores = ratear_por_percentuais(valor, percentuais)
    else:
        valores = [Decimal("0.00")] * len(itens)

    return [
        LinhaDivisao(
            nome=item.membro.usuario.first_name
            or item.membro.usuario.username,
            percentual=item.percentual,
            valor=v,
        )
        for item, v in zip(itens, valores)
    ]


def saldo_do_casal(casal: Casal) -> list[SaldoPar]:
    return calcular_saldo(casal)
