"""Services de escrita do app expenses (regra de negócio: compra -> parcelas -> rateios)."""

from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Casal, MembroCasal, RegraDivisao
from apps.core.dates import add_months
from apps.core.money import dividir_em_partes, ratear_por_percentuais
from apps.expenses.models import (
    Categoria,
    Compra,
    DespesaRecorrente,
    Parcela,
    Rateio,
)


@transaction.atomic
def registrar_compra(
    *,
    casal: Casal,
    descricao: str,
    categoria: Categoria | None,
    valor_total: Decimal,
    quantidade_parcelas: int,
    data_compra: date,
    pago_por: MembroCasal,
    primeira_data_vencimento: date,
    origem: str = Compra.Origem.AVULSA,
    recorrente: DespesaRecorrente | None = None,
    competencia: date | None = None,
) -> Compra:
    """
    Registra uma compra gerando suas parcelas e rateios, tudo atômico.

    1. Cria a Compra.
    2. Divide `valor_total` em N parcelas iguais, fechando os centavos da sobra
       na última parcela (soma das parcelas == valor_total). Vencimentos mês a mês.
    3. Para cada parcela, busca a RegraDivisao vigente na `data_compra` e cria
       1 Rateio por membro com `percentual_aplicado` (snapshot) e `valor_devido`,
       fechando centavos no último membro (soma dos rateios == valor da parcela).

    Levanta ValidationError se não houver regra de divisão vigente na data ou se
    `quantidade_parcelas < 1`.
    """
    if quantidade_parcelas < 1:
        raise ValidationError("quantidade_parcelas deve ser >= 1.")

    regra = RegraDivisao.vigente_em(casal, data_compra)
    if regra is None:
        raise ValidationError(
            f"Não há RegraDivisao vigente em {data_compra} para o casal."
        )

    itens = list(regra.itens.select_related("membro"))
    percentuais = [item.percentual for item in itens]

    compra = Compra.objects.create(
        casal=casal,
        descricao=descricao,
        categoria=categoria,
        valor_total=Decimal(valor_total),
        quantidade_parcelas=quantidade_parcelas,
        data_compra=data_compra,
        pago_por=pago_por,
        origem=origem,
        recorrente=recorrente,
        competencia=competencia,
    )

    valores_parcelas = dividir_em_partes(compra.valor_total, quantidade_parcelas)

    for numero, valor_parcela in enumerate(valores_parcelas, start=1):
        parcela = Parcela.objects.create(
            compra=compra,
            numero=numero,
            valor=valor_parcela,
            data_vencimento=add_months(primeira_data_vencimento, numero - 1),
        )

        # Snapshot do percentual vigente; fechamento de centavos no último membro.
        valores_devidos = ratear_por_percentuais(valor_parcela, percentuais)
        Rateio.objects.bulk_create(
            [
                Rateio(
                    parcela=parcela,
                    membro=item.membro,
                    percentual_aplicado=item.percentual,
                    valor_devido=valor_devido,
                )
                for item, valor_devido in zip(itens, valores_devidos)
            ]
        )

    return compra


@transaction.atomic
def gerar_recorrentes(*, casal: Casal, competencia: date) -> list[Compra]:
    """
    Gera as compras das despesas recorrentes ativas do casal para a competência.

    `competencia` deve ser o 1º dia do mês (date(ano, mes, 1)). Para cada
    DespesaRecorrente ativa cria uma Compra(origem=RECORRENTE, parcelas=1)
    reusando registrar_compra. É **idempotente**: se já existe compra daquela
    recorrente na competência, pula (não duplica). Vencimento = dia_vencimento
    do mês da competência.
    """
    competencia = competencia.replace(day=1)
    criadas: list[Compra] = []

    recorrentes = DespesaRecorrente.objects.filter(casal=casal, ativo=True)
    for rec in recorrentes:
        ja_existe = Compra.objects.filter(
            recorrente=rec, competencia=competencia
        ).exists()
        if ja_existe:
            continue

        vencimento = competencia.replace(day=rec.dia_vencimento)
        compra = registrar_compra(
            casal=casal,
            descricao=rec.descricao,
            categoria=rec.categoria,
            valor_total=rec.valor,
            quantidade_parcelas=1,
            data_compra=competencia,
            pago_por=rec.pago_por,
            primeira_data_vencimento=vencimento,
            origem=Compra.Origem.RECORRENTE,
            recorrente=rec,
            competencia=competencia,
        )
        criadas.append(compra)

    return criadas


@transaction.atomic
def registrar_pagamento_rateio(
    *, rateio: Rateio, data_pagamento: date | None = None
) -> Rateio:
    """
    Marca um rateio (a parte de uma pessoa numa parcela) como PAGO.

    Registra a data do pagamento (default: hoje). Idempotente: se já estiver
    pago, não altera a data. Sai do saldo de 'quem deve pra quem' por deixar de
    ser PENDENTE.
    """
    if rateio.status_pagamento == Rateio.StatusPagamento.PAGO:
        return rateio

    rateio.status_pagamento = Rateio.StatusPagamento.PAGO
    rateio.data_pagamento = data_pagamento or timezone.localdate()
    rateio.save(
        update_fields=["status_pagamento", "data_pagamento", "atualizado_em"]
    )
    return rateio
