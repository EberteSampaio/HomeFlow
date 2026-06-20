"""
Utils de dinheiro e fechamento de centavos.

Regra do projeto: todo valor monetário é `Decimal` com 2 casas, arredondado
com `ROUND_HALF_UP`. Ao dividir um total (em parcelas ou por percentuais), a
sobra de arredondamento é jogada no **último** item, garantindo que a soma das
partes seja exatamente igual ao total.
"""

from decimal import ROUND_HALF_UP, Decimal

CENTAVOS = Decimal("0.01")


def quantize_money(valor: Decimal) -> Decimal:
    """Arredonda para 2 casas com ROUND_HALF_UP."""
    return Decimal(valor).quantize(CENTAVOS, rounding=ROUND_HALF_UP)


def dividir_em_partes(total: Decimal, n: int) -> list[Decimal]:
    """
    Divide `total` em `n` partes iguais fechando centavos na última parte.

    Ex.: 100,00 / 3 -> [33.33, 33.33, 33.34]. A soma das partes == total.
    """
    if n < 1:
        raise ValueError("n deve ser >= 1")

    total = quantize_money(total)
    parte = quantize_money(total / Decimal(n))
    partes = [parte] * (n - 1)
    partes.append(quantize_money(total - parte * (n - 1)))
    return partes


def ratear_por_percentuais(
    total: Decimal, percentuais: list[Decimal]
) -> list[Decimal]:
    """
    Rateia `total` segundo `percentuais` (que somam 100) fechando centavos no último.

    A soma dos valores devolvidos == total, sem perder/criar centavo no
    arredondamento de cada fatia.
    """
    if not percentuais:
        raise ValueError("percentuais não pode ser vazio")

    total = quantize_money(total)
    cem = Decimal("100")
    valores = [
        quantize_money(total * Decimal(p) / cem) for p in percentuais[:-1]
    ]
    valores.append(quantize_money(total - sum(valores)))
    return valores
