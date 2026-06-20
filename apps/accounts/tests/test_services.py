"""Testes do service criar_regra_divisao (invariante soma=100 e caso de erro)."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.accounts.models import Casal, MembroCasal, RegraDivisao, RegraDivisaoItem
from apps.accounts.services import ItemRegra, criar_regra_divisao

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture
def casal_com_membros():
    casal = Casal.objects.create(nome="Casal Teste")
    eberte = MembroCasal.objects.create(
        casal=casal,
        usuario=User.objects.create_user(username="eberte", email="e@test.dev"),
    )
    namorada = MembroCasal.objects.create(
        casal=casal,
        usuario=User.objects.create_user(username="namorada", email="n@test.dev"),
    )
    return casal, eberte, namorada


def test_cria_regra_quando_soma_eh_100(casal_com_membros):
    casal, eberte, namorada = casal_com_membros

    regra = criar_regra_divisao(
        casal=casal,
        vigente_desde=date(2026, 6, 19),
        itens=[
            ItemRegra(membro=eberte, percentual=Decimal("70.00")),
            ItemRegra(membro=namorada, percentual=Decimal("30.00")),
        ],
    )

    assert isinstance(regra, RegraDivisao)
    assert regra.casal == casal
    assert regra.itens.count() == 2

    soma = sum((item.percentual for item in regra.itens.all()), Decimal("0"))
    assert soma == Decimal("100.00")

    # A regra criada é a vigente na data.
    assert RegraDivisao.vigente_em(casal, date(2026, 6, 19)) == regra


def test_erro_quando_soma_diferente_de_100(casal_com_membros):
    casal, eberte, namorada = casal_com_membros

    with pytest.raises(ValidationError):
        criar_regra_divisao(
            casal=casal,
            vigente_desde=date(2026, 6, 19),
            itens=[
                ItemRegra(membro=eberte, percentual=Decimal("70.00")),
                ItemRegra(membro=namorada, percentual=Decimal("40.00")),  # soma 110
            ],
        )

    # Rollback: nada deve ter sido persistido (transaction.atomic).
    assert RegraDivisao.objects.count() == 0
    assert RegraDivisaoItem.objects.count() == 0
