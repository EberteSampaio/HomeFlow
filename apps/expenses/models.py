from django.db import models
from django.db.models import Q

from apps.accounts.models import Casal, MembroCasal
from apps.core.models import TimeStampedModel


class Categoria(TimeStampedModel):
    casal = models.ForeignKey(
        Casal, related_name="categorias", on_delete=models.CASCADE
    )
    nome = models.CharField(max_length=60)  # Moradia, Outros...

    def __str__(self) -> str:
        return self.nome


class Compra(TimeStampedModel):
    class Status(models.TextChoices):
        ABERTA = "ABERTA", "Aberta"
        QUITADA = "QUITADA", "Quitada"
        CANCELADA = "CANCELADA", "Cancelada"

    class Origem(models.TextChoices):
        AVULSA = "AVULSA", "Avulsa"
        RECORRENTE = "RECORRENTE", "Recorrente"

    casal = models.ForeignKey(
        Casal, related_name="compras", on_delete=models.CASCADE
    )
    descricao = models.CharField(max_length=160)
    categoria = models.ForeignKey(
        Categoria, null=True, blank=True, on_delete=models.SET_NULL
    )
    valor_total = models.DecimalField(max_digits=12, decimal_places=2)
    quantidade_parcelas = models.PositiveSmallIntegerField(default=1)
    data_compra = models.DateField()
    pago_por = models.ForeignKey(
        MembroCasal, related_name="compras_pagas", on_delete=models.PROTECT
    )
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.ABERTA
    )
    origem = models.CharField(
        max_length=12, choices=Origem.choices, default=Origem.AVULSA
    )
    # Vínculo de origem para compras geradas por job mensal (idempotência).
    recorrente = models.ForeignKey(
        "expenses.DespesaRecorrente",
        null=True,
        blank=True,
        related_name="compras",
        on_delete=models.SET_NULL,
    )
    competencia = models.DateField(
        null=True, blank=True
    )  # 1º dia do mês de referência (só p/ RECORRENTE)

    class Meta:
        constraints = [
            # Uma despesa recorrente gera no máximo 1 compra por competência.
            models.UniqueConstraint(
                fields=["recorrente", "competencia"],
                condition=Q(recorrente__isnull=False),
                name="uniq_recorrente_por_competencia",
            )
        ]

    def __str__(self) -> str:
        return f"{self.descricao} ({self.valor_total})"


class Parcela(TimeStampedModel):
    compra = models.ForeignKey(
        Compra, related_name="parcelas", on_delete=models.CASCADE
    )
    numero = models.PositiveSmallIntegerField()
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    data_vencimento = models.DateField()

    class Meta:
        unique_together = [("compra", "numero")]
        ordering = ["data_vencimento"]

    def __str__(self) -> str:
        return f"{self.compra.descricao} {self.numero}/{self.compra.quantidade_parcelas}"


class Rateio(TimeStampedModel):
    """Quanto CADA pessoa deve naquela parcela (snapshot do percentual)."""

    class StatusPagamento(models.TextChoices):
        PENDENTE = "PENDENTE", "Pendente"
        PAGO = "PAGO", "Pago"

    parcela = models.ForeignKey(
        Parcela, related_name="rateios", on_delete=models.CASCADE
    )
    membro = models.ForeignKey(
        MembroCasal, related_name="rateios", on_delete=models.PROTECT
    )
    percentual_aplicado = models.DecimalField(
        max_digits=5, decimal_places=2
    )  # snapshot
    valor_devido = models.DecimalField(max_digits=12, decimal_places=2)
    status_pagamento = models.CharField(
        max_length=10,
        choices=StatusPagamento.choices,
        default=StatusPagamento.PENDENTE,
    )
    data_pagamento = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = [("parcela", "membro")]

    def __str__(self) -> str:
        return f"{self.membro} deve {self.valor_devido}"


class DespesaRecorrente(TimeStampedModel):
    """Aluguel, Internet, Energia... gerada todo mês por job (Fase 4)."""

    casal = models.ForeignKey(
        Casal, related_name="recorrentes", on_delete=models.CASCADE
    )
    descricao = models.CharField(max_length=160)
    categoria = models.ForeignKey(
        Categoria, null=True, blank=True, on_delete=models.SET_NULL
    )
    valor = models.DecimalField(max_digits=12, decimal_places=2)
    dia_vencimento = models.PositiveSmallIntegerField()  # 1..28
    pago_por = models.ForeignKey(MembroCasal, on_delete=models.PROTECT)
    ativo = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.descricao} (dia {self.dia_vencimento})"
