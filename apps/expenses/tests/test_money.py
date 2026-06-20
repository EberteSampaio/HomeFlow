"""Testes unitários dos utils de dinheiro (fechamento de centavos)."""

from decimal import Decimal

import pytest

from apps.core.money import dividir_em_partes, ratear_por_percentuais


def test_divide_fechando_centavos_na_ultima():
    partes = dividir_em_partes(Decimal("100.00"), 3)
    assert partes == [Decimal("33.33"), Decimal("33.33"), Decimal("33.34")]
    assert sum(partes) == Decimal("100.00")


def test_divide_uma_parcela():
    assert dividir_em_partes(Decimal("302.89"), 1) == [Decimal("302.89")]


def test_divide_exige_n_positivo():
    with pytest.raises(ValueError):
        dividir_em_partes(Decimal("10.00"), 0)


def test_rateio_70_30_fecha_centavos():
    valores = ratear_por_percentuais(Decimal("302.89"), [Decimal("70"), Decimal("30")])
    # 70% = 212.023 -> 212.02 ; sobra fecha na última pessoa.
    assert valores == [Decimal("212.02"), Decimal("90.87")]
    assert sum(valores) == Decimal("302.89")


def test_rateio_soma_sempre_igual_ao_total():
    valores = ratear_por_percentuais(Decimal("33.34"), [Decimal("70"), Decimal("30")])
    assert sum(valores) == Decimal("33.34")
