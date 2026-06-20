"""DTOs do app payments."""

from dataclasses import dataclass
from decimal import Decimal

from apps.accounts.models import MembroCasal


@dataclass(frozen=True)
class CobrancaPix:
    """Cobrança Pix gerada para um saldo: copia-e-cola + imagem QR."""

    brcode: str  # string copia-e-cola (EMV BR Code)
    qr_png: bytes  # imagem PNG do QR Code
    valor: Decimal
    credor: MembroCasal  # quem recebe
    devedor: MembroCasal  # quem paga
