"""Testes de gerar_recorrentes (geração, idempotência, inativas)."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Casal, MembroCasal
from apps.accounts.services import ItemRegra, criar_regra_divisao
from apps.expenses.models import Compra, DespesaRecorrente
from apps.expenses.services import gerar_recorrentes

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


def test_gera_compra_recorrente_com_rateio(casal_70_30):
    casal, eberte, namorada = casal_70_30
    aluguel = DespesaRecorrente.objects.create(
        casal=casal,
        descricao="Aluguel",
        categoria=None,
        valor=Decimal("2000.00"),
        dia_vencimento=10,
        pago_por=eberte,
    )

    criadas = gerar_recorrentes(casal=casal, competencia=date(2026, 6, 1))

    assert len(criadas) == 1
    compra = criadas[0]
    assert compra.origem == Compra.Origem.RECORRENTE
    assert compra.recorrente == aluguel
    assert compra.competencia == date(2026, 6, 1)
    assert compra.quantidade_parcelas == 1

    parcela = compra.parcelas.get()
    assert parcela.valor == Decimal("2000.00")
    assert parcela.data_vencimento == date(2026, 6, 10)
    # Rateio com a regra vigente (30% da namorada = 600,00).
    assert parcela.rateios.get(membro=namorada).valor_devido == Decimal("600.00")


def test_idempotente_nao_duplica(casal_70_30):
    casal, eberte, _ = casal_70_30
    DespesaRecorrente.objects.create(
        casal=casal,
        descricao="Internet",
        categoria=None,
        valor=Decimal("120.00"),
        dia_vencimento=5,
        pago_por=eberte,
    )

    primeira = gerar_recorrentes(casal=casal, competencia=date(2026, 6, 1))
    segunda = gerar_recorrentes(casal=casal, competencia=date(2026, 6, 1))

    assert len(primeira) == 1
    assert len(segunda) == 0  # não duplica na 2ª rodada
    assert Compra.objects.filter(origem=Compra.Origem.RECORRENTE).count() == 1


def test_competencias_diferentes_geram_compras_distintas(casal_70_30):
    casal, eberte, _ = casal_70_30
    DespesaRecorrente.objects.create(
        casal=casal,
        descricao="Energia",
        categoria=None,
        valor=Decimal("180.00"),
        dia_vencimento=15,
        pago_por=eberte,
    )

    gerar_recorrentes(casal=casal, competencia=date(2026, 6, 1))
    gerar_recorrentes(casal=casal, competencia=date(2026, 7, 1))

    assert Compra.objects.filter(origem=Compra.Origem.RECORRENTE).count() == 2


def test_ignora_recorrente_inativa(casal_70_30):
    casal, eberte, _ = casal_70_30
    DespesaRecorrente.objects.create(
        casal=casal,
        descricao="Lavanderia (cancelada)",
        categoria=None,
        valor=Decimal("90.00"),
        dia_vencimento=20,
        pago_por=eberte,
        ativo=False,
    )

    criadas = gerar_recorrentes(casal=casal, competencia=date(2026, 6, 1))
    assert criadas == []


def test_normaliza_competencia_para_dia_1(casal_70_30):
    """Passar uma data no meio do mês deve normalizar a competência para o dia 1."""
    casal, eberte, _ = casal_70_30
    DespesaRecorrente.objects.create(
        casal=casal,
        descricao="Aluguel",
        categoria=None,
        valor=Decimal("2000.00"),
        dia_vencimento=10,
        pago_por=eberte,
    )

    criadas = gerar_recorrentes(casal=casal, competencia=date(2026, 6, 19))
    assert criadas[0].competencia == date(2026, 6, 1)
