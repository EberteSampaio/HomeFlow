"""Testes do service registrar_compra (parcelas, rateios, snapshot, invariantes)."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.accounts.models import Casal, MembroCasal
from apps.accounts.services import ItemRegra, criar_regra_divisao
from apps.expenses.models import Compra, Parcela, Rateio
from apps.expenses.services import registrar_compra, registrar_pagamento_rateio

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


def test_compra_avista_geladeira(casal_70_30):
    """Exemplo da planilha: 302,89 pago por Eberte -> namorada deve 90,87."""
    casal, eberte, namorada = casal_70_30

    compra = registrar_compra(
        casal=casal,
        descricao="Geladeira",
        categoria=None,
        valor_total=Decimal("302.89"),
        quantidade_parcelas=1,
        data_compra=date(2026, 6, 19),
        pago_por=eberte,
        primeira_data_vencimento=date(2026, 7, 10),
    )

    assert compra.parcelas.count() == 1
    parcela = compra.parcelas.get()
    assert parcela.valor == Decimal("302.89")

    rateio_namorada = parcela.rateios.get(membro=namorada)
    rateio_eberte = parcela.rateios.get(membro=eberte)
    assert rateio_namorada.valor_devido == Decimal("90.87")
    assert rateio_eberte.valor_devido == Decimal("212.02")
    # Snapshot do percentual vigente.
    assert rateio_namorada.percentual_aplicado == Decimal("30.00")
    assert rateio_eberte.percentual_aplicado == Decimal("70.00")


def test_parcelamento_fecha_centavos(casal_70_30):
    casal, eberte, namorada = casal_70_30

    compra = registrar_compra(
        casal=casal,
        descricao="Sofá parcelado",
        categoria=None,
        valor_total=Decimal("100.00"),
        quantidade_parcelas=3,
        data_compra=date(2026, 6, 19),
        pago_por=eberte,
        primeira_data_vencimento=date(2026, 7, 10),
    )

    parcelas = list(compra.parcelas.order_by("numero"))
    assert [p.valor for p in parcelas] == [
        Decimal("33.33"),
        Decimal("33.33"),
        Decimal("33.34"),
    ]
    # Invariante: soma das parcelas == valor_total.
    assert sum(p.valor for p in parcelas) == Decimal("100.00")

    # Vencimentos mês a mês a partir da primeira data.
    assert [p.data_vencimento for p in parcelas] == [
        date(2026, 7, 10),
        date(2026, 8, 10),
        date(2026, 9, 10),
    ]


def test_soma_dos_rateios_igual_valor_da_parcela(casal_70_30):
    casal, eberte, namorada = casal_70_30

    compra = registrar_compra(
        casal=casal,
        descricao="Compra parcelada",
        categoria=None,
        valor_total=Decimal("100.00"),
        quantidade_parcelas=3,
        data_compra=date(2026, 6, 19),
        pago_por=eberte,
        primeira_data_vencimento=date(2026, 7, 10),
    )

    for parcela in compra.parcelas.all():
        soma_rateios = sum(r.valor_devido for r in parcela.rateios.all())
        assert soma_rateios == parcela.valor


def test_erro_sem_regra_vigente(casal_70_30):
    """Compra anterior à vigência da regra (2026-01-01) não tem split."""
    casal, eberte, _ = casal_70_30

    with pytest.raises(ValidationError):
        registrar_compra(
            casal=casal,
            descricao="Compra antiga",
            categoria=None,
            valor_total=Decimal("50.00"),
            quantidade_parcelas=1,
            data_compra=date(2025, 12, 31),
            pago_por=eberte,
            primeira_data_vencimento=date(2026, 1, 10),
        )

    # Nada persistido (transaction.atomic + validação antes de criar).
    assert Compra.objects.count() == 0
    assert Parcela.objects.count() == 0
    assert Rateio.objects.count() == 0


def test_registrar_pagamento_rateio_marca_pago_e_eh_idempotente(casal_70_30):
    casal, eberte, namorada = casal_70_30
    compra = registrar_compra(
        casal=casal, descricao="Geladeira", categoria=None,
        valor_total=Decimal("302.89"), quantidade_parcelas=1,
        data_compra=date(2026, 6, 19), pago_por=eberte,
        primeira_data_vencimento=date(2026, 7, 10),
    )
    rateio = compra.parcelas.get().rateios.get(membro=namorada)
    assert rateio.status_pagamento == Rateio.StatusPagamento.PENDENTE

    registrar_pagamento_rateio(rateio=rateio, data_pagamento=date(2026, 7, 5))
    rateio.refresh_from_db()
    assert rateio.status_pagamento == Rateio.StatusPagamento.PAGO
    assert rateio.data_pagamento == date(2026, 7, 5)

    # Idempotente: rodar de novo não altera a data já registrada.
    registrar_pagamento_rateio(rateio=rateio, data_pagamento=date(2026, 8, 1))
    rateio.refresh_from_db()
    assert rateio.data_pagamento == date(2026, 7, 5)
