"""Services de escrita do app accounts (regra de negócio fica aqui, não na view)."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.accounts.models import (
    Casal,
    MembroCasal,
    RegraDivisao,
    RegraDivisaoItem,
)

SOMA_ESPERADA = Decimal("100.00")


@dataclass(frozen=True)
class ItemRegra:
    """Entrada do service: um membro e seu percentual na regra."""

    membro: MembroCasal
    percentual: Decimal


@transaction.atomic
def criar_regra_divisao(
    *,
    casal: Casal,
    vigente_desde: date,
    itens: list[ItemRegra],
) -> RegraDivisao:
    """
    Cria uma nova RegraDivisao versionada validando que a soma dos percentuais
    dos itens seja exatamente 100.00.

    Split é versionado: nunca editamos uma regra existente — criamos uma nova
    com `vigente_desde`. Levanta ValidationError se a soma != 100.00 ou se a
    lista de itens estiver vazia. Tudo dentro de transaction.atomic.
    """
    if not itens:
        raise ValidationError("A regra de divisão precisa de ao menos um item.")

    soma = sum((Decimal(item.percentual) for item in itens), Decimal("0"))
    if soma != SOMA_ESPERADA:
        raise ValidationError(
            f"A soma dos percentuais deve ser {SOMA_ESPERADA}, mas é {soma}."
        )

    regra = RegraDivisao.objects.create(casal=casal, vigente_desde=vigente_desde)
    RegraDivisaoItem.objects.bulk_create(
        [
            RegraDivisaoItem(
                regra=regra,
                membro=item.membro,
                percentual=Decimal(item.percentual),
            )
            for item in itens
        ]
    )
    return regra
