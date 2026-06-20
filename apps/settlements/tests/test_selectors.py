"""Testes do motor de saldo calcular_saldo (direção, netting, PAGO, self, vazio)."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Casal, MembroCasal
from apps.accounts.services import ItemRegra, criar_regra_divisao
from apps.expenses.models import Rateio
from apps.expenses.services import registrar_compra
from apps.settlements.selectors import calcular_saldo, saldo_por_mes

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture
def casal_70_30():
    casal = Casal.objects.create(nome="Casal Teste")
    eberte = MembroCasal.objects.create(
        casal=casal,
        usuario=User.objects.create_user(username="eberte", email="e@test.dev"),
    )
    namorada = MembroCasal.objects.create(
        casal=casal,
        usuario=User.objects.create_user(username="namorada", email="n@test.dev"),
    )
    criar_regra_divisao(
        casal=casal,
        vigente_desde=date(2026, 1, 1),
        itens=[
            ItemRegra(membro=eberte, percentual=Decimal("70.00")),
            ItemRegra(membro=namorada, percentual=Decimal("30.00")),
        ],
    )
    return casal, eberte, namorada


def _compra(casal, pago_por, valor):
    return registrar_compra(
        casal=casal,
        descricao="Compra",
        categoria=None,
        valor_total=valor,
        quantidade_parcelas=1,
        data_compra=date(2026, 6, 19),
        pago_por=pago_por,
        primeira_data_vencimento=date(2026, 7, 10),
    )


def test_saldo_vazio(casal_70_30):
    casal, _, _ = casal_70_30
    assert calcular_saldo(casal) == []


def test_saldo_por_mes_agrupa_pelo_vencimento(casal_70_30):
    """Compra parcelada 300/3x paga por Eberte -> namorada deve 30,00 por mês."""
    casal, eberte, namorada = casal_70_30
    registrar_compra(
        casal=casal, descricao="Sofá", categoria=None,
        valor_total=Decimal("300.00"), quantidade_parcelas=3,
        data_compra=date(2026, 6, 19), pago_por=eberte,
        primeira_data_vencimento=date(2026, 7, 10),
    )

    grupos = saldo_por_mes(casal)

    # Três meses de vencimento (jul, ago, set/2026), em ordem cronológica.
    assert [g["mes"] for g in grupos] == [
        date(2026, 7, 1),
        date(2026, 8, 1),
        date(2026, 9, 1),
    ]
    for g in grupos:
        assert len(g["saldos"]) == 1
        par = g["saldos"][0]
        assert par.devedor == namorada
        assert par.credor == eberte
        assert par.valor == Decimal("30.00")


def test_saldo_por_mes_vazio_quando_sem_divida(casal_70_30):
    casal, _, _ = casal_70_30
    assert saldo_por_mes(casal) == []


def test_direcao_quando_eberte_paga(casal_70_30):
    """Eberte paga 302,89 -> namorada deve 90,87 (30%) a ele."""
    casal, eberte, namorada = casal_70_30
    _compra(casal, pago_por=eberte, valor=Decimal("302.89"))

    saldo = calcular_saldo(casal)
    assert len(saldo) == 1
    par = saldo[0]
    assert par.devedor == namorada
    assert par.credor == eberte
    assert par.valor == Decimal("90.87")


def test_self_rateio_nao_vira_divida(casal_70_30):
    """A parte do próprio pagador (70% do Eberte) não gera dívida — só os 90,87."""
    casal, eberte, namorada = casal_70_30
    compra = _compra(casal, pago_por=eberte, valor=Decimal("302.89"))

    # O rateio do Eberte (pagador) existe, mas não conta como dívida.
    assert compra.parcelas.get().rateios.count() == 2
    saldo = calcular_saldo(casal)
    assert sum(p.valor for p in saldo) == Decimal("90.87")


def test_netting_bidirecional(casal_70_30):
    """
    Eberte paga 100 (namorada deve 30) e namorada paga 100 (eberte deve 70).
    Líquido: eberte deve 70 - 30 = 40 à namorada.
    """
    casal, eberte, namorada = casal_70_30
    _compra(casal, pago_por=eberte, valor=Decimal("100.00"))
    _compra(casal, pago_por=namorada, valor=Decimal("100.00"))

    saldo = calcular_saldo(casal)
    assert len(saldo) == 1
    par = saldo[0]
    assert par.devedor == eberte
    assert par.credor == namorada
    assert par.valor == Decimal("40.00")


def test_ignora_rateio_pago(casal_70_30):
    """Rateio marcado como PAGO não entra no saldo."""
    casal, eberte, namorada = casal_70_30
    compra = _compra(casal, pago_por=eberte, valor=Decimal("302.89"))

    rateio = compra.parcelas.get().rateios.get(membro=namorada)
    rateio.status_pagamento = Rateio.StatusPagamento.PAGO
    rateio.save(update_fields=["status_pagamento"])

    assert calcular_saldo(casal) == []


def test_quitacao_exata_some_do_saldo(casal_70_30):
    """Dívidas iguais nos dois sentidos se anulam (líquido zero)."""
    casal, eberte, namorada = casal_70_30
    # Eberte paga 100 (namorada deve 30); namorada paga ~42,86 (eberte deve 30).
    _compra(casal, pago_por=eberte, valor=Decimal("100.00"))
    _compra(casal, pago_por=namorada, valor=Decimal("42.86"))  # 70% -> 30.00

    saldo = calcular_saldo(casal)
    assert saldo == []
