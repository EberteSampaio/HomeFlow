"""
Geração de Pix estático: BR Code copia-e-cola + QR Code PNG.

Sem integração com PSP/banco na v1: apenas monta o payload EMV (via pix-utils,
que já calcula o CRC16) e renderiza o QR como PNG (via qrcode). A cobrança é
gerada pelo valor líquido do saldo, a favor da chave Pix de quem é credor.
"""

import io
import unicodedata
from decimal import Decimal

import qrcode
from pix_utils import Code

from apps.expenses.models import Rateio
from apps.payments.dtos import CobrancaPix
from apps.settlements.selectors import SaldoPar

MAX_NOME = 25  # limite EMV do nome do recebedor
MAX_CIDADE = 15  # limite EMV da cidade


def _normalizar(texto: str, *, limite: int) -> str:
    """Remove acentos, coloca em caixa-alta e trunca para o limite do EMV."""
    sem_acento = (
        unicodedata.normalize("NFKD", texto)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    return sem_acento.upper().strip()[:limite]


def gerar_brcode(
    *,
    chave: str,
    valor: Decimal,
    nome: str,
    cidade: str,
    txid: str | None = None,
) -> str:
    """Monta o BR Code Pix estático (copia-e-cola) com CRC16 ao final."""
    return Code(
        key=chave,
        name=_normalizar(nome, limite=MAX_NOME),
        city=_normalizar(cidade, limite=MAX_CIDADE),
        value=Decimal(valor),
        identifier=txid,
    )


def gerar_qrcode_png(payload: str) -> bytes:
    """Renderiza o BR Code como imagem PNG (bytes)."""
    img = qrcode.make(payload)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def gerar_cobranca_do_saldo(*, saldo: SaldoPar, cidade: str, txid: str | None = None) -> CobrancaPix:
    """
    Gera a cobrança Pix de um saldo: BR Code + PNG a favor da chave do credor.

    O credor é quem recebe (`saldo.credor`); o valor é o líquido devido. Exige
    que o credor tenha `chave_pix` cadastrada.
    """
    credor = saldo.credor.usuario
    if not credor.chave_pix:
        raise ValueError(
            f"O credor {credor} não possui chave_pix cadastrada para gerar o Pix."
        )

    brcode = gerar_brcode(
        chave=credor.chave_pix,
        valor=saldo.valor,
        nome=credor.get_full_name() or credor.username,
        cidade=cidade,
        txid=txid,
    )
    return CobrancaPix(
        brcode=brcode,
        qr_png=gerar_qrcode_png(brcode),
        valor=saldo.valor,
        credor=saldo.credor,
        devedor=saldo.devedor,
    )


def gerar_cobranca_de_rateio(
    *, rateio: Rateio, cidade: str, txid: str | None = None
) -> CobrancaPix:
    """
    Gera a cobrança Pix de UMA parcela (rateio): BR Code + PNG pelo `valor_devido`
    daquela parcela, a favor da chave Pix de quem pagou a compra.

    Exige que o credor (pagador da parcela) tenha `chave_pix` cadastrada.
    """
    credor_membro = rateio.parcela.compra.pago_por
    credor = credor_membro.usuario
    if not credor.chave_pix:
        raise ValueError(
            f"O credor {credor} não possui chave_pix cadastrada para gerar o Pix."
        )

    brcode = gerar_brcode(
        chave=credor.chave_pix,
        valor=rateio.valor_devido,
        nome=credor.get_full_name() or credor.username,
        cidade=cidade,
        txid=txid or f"P{rateio.pk}",
    )
    return CobrancaPix(
        brcode=brcode,
        qr_png=gerar_qrcode_png(brcode),
        valor=rateio.valor_devido,
        credor=credor_membro,
        devedor=rateio.membro,
    )
