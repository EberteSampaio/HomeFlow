from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.models import TimeStampedModel


class User(AbstractUser):
    """Usuário do sistema. Estende AbstractUser (hash/login/perms prontos)."""

    email = models.EmailField(unique=True)
    # Chave Pix para gerar QR a favor deste usuário quando ele for credor.
    chave_pix = models.CharField(max_length=140, blank=True)

    def __str__(self) -> str:
        return self.get_full_name() or self.username


class Casal(TimeStampedModel):
    nome = models.CharField(max_length=120)

    def __str__(self) -> str:
        return self.nome


class MembroCasal(TimeStampedModel):
    casal = models.ForeignKey(
        Casal, related_name="membros", on_delete=models.CASCADE
    )
    usuario = models.OneToOneField(
        "accounts.User", related_name="membro", on_delete=models.CASCADE
    )

    def __str__(self) -> str:
        return f"{self.usuario} ({self.casal})"


class RegraDivisao(TimeStampedModel):
    """Versiona o split do casal por data de vigência (nunca editar; criar nova)."""

    casal = models.ForeignKey(
        Casal, related_name="regras", on_delete=models.CASCADE
    )
    vigente_desde = models.DateField()

    class Meta:
        ordering = ["-vigente_desde"]

    def __str__(self) -> str:
        return f"Regra {self.casal} desde {self.vigente_desde}"

    @classmethod
    def vigente_em(cls, casal: Casal, data):
        """Retorna a regra de maior `vigente_desde <= data` (a vigente na data)."""
        return cls.objects.filter(casal=casal, vigente_desde__lte=data).first()


class RegraDivisaoItem(TimeStampedModel):
    """1 linha por membro (escala para república); soma=100 validada no service."""

    regra = models.ForeignKey(
        RegraDivisao, related_name="itens", on_delete=models.CASCADE
    )
    membro = models.ForeignKey(MembroCasal, on_delete=models.PROTECT)
    percentual = models.DecimalField(max_digits=5, decimal_places=2)  # 70.00 / 30.00

    class Meta:
        unique_together = [("regra", "membro")]

    def __str__(self) -> str:
        return f"{self.membro} = {self.percentual}%"
