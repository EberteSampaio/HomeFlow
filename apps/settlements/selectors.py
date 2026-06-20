"""
Selectors de leitura do app settlements: motor "quem deve para quem".

Regra (seção 3.3 da spec):
- Quem deve um `valor_devido` deve para quem PAGOU a parcela (`compra.pago_por`).
- Se a pessoa do rateio é a mesma que pagou, a dívida dela ali é zero.
- Soma-se sobre os rateios PENDENTES e apresenta-se o saldo LÍQUIDO por par,
  com a direção correta (quem deve para quem).
"""

from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.db.models import F, QuerySet

from apps.accounts.models import Casal, MembroCasal
from apps.expenses.models import Rateio


@dataclass(frozen=True)
class SaldoPar:
    """Saldo líquido de um par: `devedor` deve `valor` a `credor` (valor > 0)."""

    devedor: MembroCasal
    credor: MembroCasal
    valor: Decimal


def _filtrar_rateios_por_compra(qs, filtros: dict | None):
    """Restringe os rateios pelos atributos da compra (categoria/pagador/status/mês)."""
    if not filtros:
        return qs
    if filtros.get("categoria"):
        qs = qs.filter(parcela__compra__categoria=filtros["categoria"])
    if filtros.get("pago_por"):
        qs = qs.filter(parcela__compra__pago_por=filtros["pago_por"])
    if filtros.get("status"):
        qs = qs.filter(parcela__compra__status=filtros["status"])
    mes = filtros.get("mes")
    if mes:
        qs = qs.filter(
            parcela__compra__data_compra__year=mes.year,
            parcela__compra__data_compra__month=mes.month,
        )
    return qs


def _saldo_de_rateios(rateios) -> list[SaldoPar]:
    """Netta uma coleção de rateios em saldos líquidos por par (devedor->credor)."""
    divida: dict[tuple[int, int], Decimal] = defaultdict(lambda: Decimal("0.00"))
    membros_por_id: dict[int, MembroCasal] = {}

    for r in rateios:
        credor = r.parcela.compra.pago_por
        membros_por_id[r.membro_id] = r.membro
        membros_por_id[credor.id] = credor
        if r.membro_id != credor.id:
            divida[(r.membro_id, credor.id)] += r.valor_devido

    resultado: list[SaldoPar] = []
    pares_vistos: set[frozenset[int]] = set()

    for (dev_id, cred_id), valor in divida.items():
        par = frozenset({dev_id, cred_id})
        if par in pares_vistos:
            continue
        pares_vistos.add(par)

        inverso = divida.get((cred_id, dev_id), Decimal("0.00"))
        liquido = valor - inverso

        if liquido > 0:
            resultado.append(
                SaldoPar(
                    devedor=membros_por_id[dev_id],
                    credor=membros_por_id[cred_id],
                    valor=liquido,
                )
            )
        elif liquido < 0:
            resultado.append(
                SaldoPar(
                    devedor=membros_por_id[cred_id],
                    credor=membros_por_id[dev_id],
                    valor=-liquido,
                )
            )
        # liquido == 0 -> quitado entre os dois, não entra no resultado.

    return resultado


def _rateios_pendentes(casal: Casal, filtros: dict | None):
    rateios = (
        Rateio.objects.filter(
            parcela__compra__casal=casal,
            status_pagamento=Rateio.StatusPagamento.PENDENTE,
        )
        .select_related(
            "membro__usuario",
            "parcela",
            "parcela__compra__pago_por__usuario",
        )
    )
    return _filtrar_rateios_por_compra(rateios, filtros)


def calcular_saldo(casal: Casal, *, filtros: dict | None = None) -> list[SaldoPar]:
    """
    Saldo líquido total entre os membros (quem deve pra quem), a partir dos
    rateios PENDENTES. `filtros` (opcional) restringe a um recorte das compras
    (categoria, quem pagou, status, mês) — usado pelo Painel.
    """
    return _saldo_de_rateios(_rateios_pendentes(casal, filtros))


def saldo_por_mes(casal: Casal, *, filtros: dict | None = None) -> list[dict]:
    """
    Saldo líquido agrupado pelo **mês de vencimento** das parcelas.

    Devolve, em ordem cronológica, uma lista de
    `{"mes": date(ano, mes, 1), "saldos": [SaldoPar, ...]}` — somando os valores
    das parcelas que vencem em cada mês e nettando por par dentro do mês. Meses
    sem dívida líquida ficam de fora.
    """
    grupos: dict[date, list] = defaultdict(list)
    for r in _rateios_pendentes(casal, filtros):
        venc = r.parcela.data_vencimento
        grupos[date(venc.year, venc.month, 1)].append(r)

    resultado: list[dict] = []
    for mes in sorted(grupos):
        saldos = _saldo_de_rateios(grupos[mes])
        if saldos:
            resultado.append({"mes": mes, "saldos": saldos})
    return resultado


def rateios_a_quitar(casal: Casal) -> QuerySet[Rateio]:
    """
    Rateios PENDENTES que representam dívida real (devedor != pagador).

    Usado para cobrar/pagar o Pix **por parcela** (cada rateio é uma dívida
    individual com seu valor e vencimento), em vez de um Pix pelo total.
    Ordenado por vencimento.
    """
    return (
        Rateio.objects.filter(
            parcela__compra__casal=casal,
            status_pagamento=Rateio.StatusPagamento.PENDENTE,
        )
        .exclude(membro=F("parcela__compra__pago_por"))
        .select_related(
            "membro__usuario",
            "parcela__compra",
            "parcela__compra__pago_por__usuario",
        )
        .order_by("parcela__data_vencimento")
    )
