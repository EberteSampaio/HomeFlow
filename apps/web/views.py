"""Views finas: orquestram services/selectors; sem regra de negócio aqui."""

import base64
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.expenses.models import Compra, Parcela, Rateio
from apps.expenses.services import registrar_compra, registrar_pagamento_rateio
from apps.payments.services import gerar_cobranca_de_rateio
from apps.settlements.selectors import rateios_a_quitar
from apps.web.forms import CompraFiltroForm, LancamentoForm
from apps.web.selectors import (
    _aplicar_filtros,
    dashboard_data,
    despesas_do_mes,
    parcelas_por_mes,
    preview_divisao,
    saldo_do_casal,
)
from apps.web.utils import get_casal_atual

CIDADE_PADRAO = "SAO PAULO"


def _cobrancas_por_rateio(casal) -> dict[int, dict]:
    """
    Mapa {rateio_id: cobrança Pix} para as dívidas PENDENTES do casal.

    Cada dívida (rateio de quem não pagou a compra) vira um BR Code + QR PNG a
    favor da chave Pix do credor. Usado tanto em Acertos quanto em Parcelas.
    """
    cobrancas: dict[int, dict] = {}
    for rateio in rateios_a_quitar(casal):
        try:
            cobranca = gerar_cobranca_de_rateio(rateio=rateio, cidade=CIDADE_PADRAO)
        except ValueError:
            cobrancas[rateio.id] = {"erro": "Credor sem chave Pix cadastrada."}
        else:
            qr_b64 = base64.b64encode(cobranca.qr_png).decode("ascii")
            cobrancas[rateio.id] = {
                "brcode": cobranca.brcode,
                "qr_data_uri": f"data:image/png;base64,{qr_b64}",
            }
    return cobrancas


@login_required
def dashboard(request):
    casal = get_casal_atual(request)
    if casal is None:
        return render(request, "web/sem_casal.html", status=200)

    filtro_form = CompraFiltroForm(request.GET or None, casal=casal)
    filtros = filtro_form.cleaned_data if filtro_form.is_valid() else {}

    dados = dashboard_data(casal, filtros=filtros)

    chart_categorias = {
        "labels": [g["nome"] for g in dados["gastos_por_categoria"]],
        "data": [float(g["total"] or 0) for g in dados["gastos_por_categoria"]],
    }
    chart_meses = {
        "labels": [g["mes"].strftime("%m/%y") for g in dados["gastos_por_mes"]],
        "data": [float(g["total"] or 0) for g in dados["gastos_por_mes"]],
    }

    ctx = {
        "casal": casal,
        "ativo": "dashboard",
        "filtro_form": filtro_form,
        "chart_categorias": chart_categorias,
        "chart_meses": chart_meses,
        **dados,
    }
    return render(request, "web/dashboard.html", ctx)


@login_required
def lancamento_novo(request):
    casal = get_casal_atual(request)
    if casal is None:
        return render(request, "web/sem_casal.html", status=200)

    if request.method == "POST":
        form = LancamentoForm(request.POST, casal=casal)
        if form.is_valid():
            cd = form.cleaned_data
            try:
                compra = registrar_compra(
                    casal=casal,
                    descricao=cd["descricao"],
                    categoria=cd["categoria"],
                    valor_total=cd["valor_total"],
                    quantidade_parcelas=cd["quantidade_parcelas"],
                    data_compra=cd["data_compra"],
                    pago_por=cd["pago_por"],
                    primeira_data_vencimento=cd["primeira_data_vencimento"],
                )
            except ValidationError as exc:
                form.add_error(None, exc)
            else:
                messages.success(
                    request, f"Lançamento '{compra.descricao}' confirmado."
                )
                return redirect(reverse("web:dashboard"))
    else:
        form = LancamentoForm(casal=casal)

    ctx = {
        "casal": casal,
        "ativo": "lancamento",
        "form": form,
        "divisao": preview_divisao(
            casal=casal, valor=Decimal("0.00"), data=timezone.localdate()
        ),
    }
    return render(request, "web/lancamento.html", ctx)


@login_required
def divisao_preview(request):
    """Endpoint HTMX: recalcula a Divisão Automática conforme valor/data."""
    casal = get_casal_atual(request)
    valor = _parse_decimal(request.GET.get("valor_total"))
    data = _parse_date(request.GET.get("data_compra")) or timezone.localdate()

    divisao = preview_divisao(casal=casal, valor=valor, data=data) if casal else None
    return render(
        request,
        "web/partials/divisao.html",
        {"divisao": divisao, "valor": valor},
    )


@login_required
def installments(request):
    casal = get_casal_atual(request)
    if casal is None:
        return render(request, "web/sem_casal.html", status=200)

    filtro_form = CompraFiltroForm(request.GET or None, casal=casal)
    filtros = filtro_form.cleaned_data if filtro_form.is_valid() else {}

    cobrancas = _cobrancas_por_rateio(casal)
    compras = _aplicar_filtros(
        Compra.objects.filter(casal=casal), filtros
    ).select_related("categoria", "pago_por__usuario").prefetch_related(
        "parcelas__rateios__membro__usuario"
    ).order_by("-data_compra", "-criado_em")

    grupos = []
    for compra in compras:
        parcelas = []
        pendentes = 0
        for parcela in compra.parcelas.all():
            pagador_id = compra.pago_por_id
            rateios = []
            paga = True
            for r in parcela.rateios.all():
                is_divida = r.membro_id != pagador_id
                pendente = r.status_pagamento == Rateio.StatusPagamento.PENDENTE
                if is_divida and pendente:
                    paga = False
                rateios.append(
                    {
                        "rateio": r,
                        "is_divida": is_divida,
                        "pago": not pendente,
                        "cobranca": cobrancas.get(r.id),
                    }
                )
            if not paga:
                pendentes += 1
            parcelas.append({"parcela": parcela, "paga": paga, "rateios": rateios})
        grupos.append(
            {"compra": compra, "parcelas": parcelas, "pendentes": pendentes}
        )

    serie = parcelas_por_mes(casal, filtros)
    chart_parcelas = {
        "labels": [s["mes"].strftime("%m/%y") for s in serie],
        "data": [float(s["total"] or 0) for s in serie],
    }

    return render(
        request,
        "web/installments.html",
        {
            "casal": casal,
            "ativo": "installments",
            "grupos": grupos,
            "filtro_form": filtro_form,
            "filtros_ativos": bool(filtros),
            "chart_parcelas": chart_parcelas,
        },
    )


@login_required
def settlements(request):
    casal = get_casal_atual(request)
    if casal is None:
        return render(request, "web/sem_casal.html", status=200)

    # Resumo líquido (quem deve pra quem) + cobranças Pix POR PARCELA.
    saldo = saldo_do_casal(casal)
    cobrancas_map = _cobrancas_por_rateio(casal)
    cobrancas = [
        {"rateio": rateio, **cobrancas_map.get(rateio.id, {})}
        for rateio in rateios_a_quitar(casal)
    ]

    return render(
        request,
        "web/settlements.html",
        {"casal": casal, "ativo": "settlements", "saldo": saldo, "cobrancas": cobrancas},
    )


@login_required
def despesas_mes(request):
    """Contas do mês: despesas fixas (recorrentes) e variáveis a pagar no mês."""
    casal = get_casal_atual(request)
    if casal is None:
        return render(request, "web/sem_casal.html", status=200)

    mes = _parse_mes(request.GET.get("mes")) or timezone.localdate().replace(day=1)
    ctx = {
        "casal": casal,
        "ativo": "despesas_mes",
        "mes_valor": mes.strftime("%Y-%m"),
        **despesas_do_mes(casal, mes),
    }
    return render(request, "web/despesas_mes.html", ctx)


@login_required
@require_POST
def rateio_pagar(request, rateio_id):
    """Marca uma parcela (rateio) como paga. Escopo limitado ao casal do usuário."""
    casal = get_casal_atual(request)
    if casal is None:
        return redirect(reverse("web:dashboard"))

    rateio = get_object_or_404(
        Rateio, pk=rateio_id, parcela__compra__casal=casal
    )
    registrar_pagamento_rateio(rateio=rateio)
    messages.success(
        request,
        f"Parcela '{rateio.parcela.compra.descricao}' marcada como paga.",
    )
    return redirect(_safe_next(request, fallback=reverse("web:settlements")))


def _parse_decimal(valor: str | None) -> Decimal:
    if not valor:
        return Decimal("0.00")
    try:
        return Decimal(valor.replace(",", "."))
    except (InvalidOperation, AttributeError):
        return Decimal("0.00")


def _parse_date(valor: str | None) -> date | None:
    if not valor:
        return None
    try:
        return date.fromisoformat(valor)
    except ValueError:
        return None


def _parse_mes(valor: str | None) -> date | None:
    """Converte 'YYYY-MM' (input type=month) no 1º dia do mês."""
    if not valor:
        return None
    try:
        return datetime.strptime(valor, "%Y-%m").date().replace(day=1)
    except ValueError:
        return None


def _safe_next(request, *, fallback: str) -> str:
    """Redireciona para o `next` do POST se for uma URL local segura."""
    destino = request.POST.get("next")
    if destino and url_has_allowed_host_and_scheme(
        destino, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        return destino
    return fallback
