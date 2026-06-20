"""Testes de payments (BR Code EMV/CRC, QR PNG, normalização, cobrança do saldo)."""

from binascii import crc_hqx
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Casal, MembroCasal
from apps.accounts.services import ItemRegra, criar_regra_divisao
from apps.expenses.services import registrar_compra
from apps.payments.services import (
    _normalizar,
    gerar_brcode,
    gerar_cobranca_de_rateio,
    gerar_cobranca_do_saldo,
    gerar_qrcode_png,
)
from apps.settlements.selectors import SaldoPar

User = get_user_model()

PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def test_brcode_estrutura_e_valor():
    payload = gerar_brcode(
        chave="ia@engaisolutions.com.br",
        valor=Decimal("90.87"),
        nome="Eberte",
        cidade="Sao Paulo",
        txid="SALDO0001",
    )
    assert payload.startswith("000201")  # Payload Format Indicator
    assert "BR.GOV.BCB.PIX" in payload
    assert "ia@engaisolutions.com.br" in payload
    assert "540590.87" in payload  # tag 54 (valor) len 05 = "90.87"


def test_brcode_crc16_valido():
    payload = gerar_brcode(
        chave="ia@engaisolutions.com.br",
        valor=Decimal("90.87"),
        nome="Eberte",
        cidade="Sao Paulo",
    )
    corpo, marcador, crc = payload[:-8], payload[-8:-4], payload[-4:]
    assert marcador == "6304"
    esperado = format(crc_hqx(bytes(corpo + "6304", "ascii"), 0xFFFF), "X")
    assert crc == esperado


def test_normaliza_nome_e_cidade():
    # Remove acento, caixa-alta e trunca para o limite EMV (nome=25).
    assert _normalizar("São Paulo", limite=15) == "SAO PAULO"
    assert _normalizar("Eberte de Andrade Sampaio Junior", limite=25) == (
        "EBERTE DE ANDRADE SAMPAIO"
    )


def test_brcode_aceita_nome_longo_com_acento():
    # Não deve estourar o limite de 25 chars do EMV (lib levantaria ValueError).
    payload = gerar_brcode(
        chave="chave@x.com",
        valor=Decimal("10.00"),
        nome="José Antônio da Silva Pereira dos Santos",
        cidade="São José dos Campos",
    )
    assert payload.startswith("000201")


def test_qrcode_png_bytes_validos():
    payload = gerar_brcode(
        chave="chave@x.com", valor=Decimal("10.00"), nome="Eberte", cidade="SP"
    )
    png = gerar_qrcode_png(payload)
    assert isinstance(png, bytes)
    assert png.startswith(PNG_MAGIC)
    assert len(png) > 100


@pytest.mark.django_db
def test_cobranca_do_saldo_a_favor_do_credor():
    casal = Casal.objects.create(nome="Casal")
    credor = MembroCasal.objects.create(
        casal=casal,
        usuario=User.objects.create_user(
            username="eberte",
            email="e@test.dev",
            first_name="Eberte",
            chave_pix="ia@engaisolutions.com.br",
        ),
    )
    devedor = MembroCasal.objects.create(
        casal=casal,
        usuario=User.objects.create_user(username="namorada", email="n@test.dev"),
    )
    saldo = SaldoPar(devedor=devedor, credor=credor, valor=Decimal("90.87"))

    cobranca = gerar_cobranca_do_saldo(saldo=saldo, cidade="Sao Paulo")

    assert cobranca.valor == Decimal("90.87")
    assert cobranca.credor == credor
    assert cobranca.devedor == devedor
    assert "ia@engaisolutions.com.br" in cobranca.brcode  # chave do credor
    assert "540590.87" in cobranca.brcode
    assert cobranca.qr_png.startswith(PNG_MAGIC)


@pytest.mark.django_db
def test_cobranca_sem_chave_pix_levanta_erro():
    casal = Casal.objects.create(nome="Casal")
    credor = MembroCasal.objects.create(
        casal=casal,
        usuario=User.objects.create_user(username="eberte", email="e@test.dev"),
    )
    devedor = MembroCasal.objects.create(
        casal=casal,
        usuario=User.objects.create_user(username="namorada", email="n@test.dev"),
    )
    saldo = SaldoPar(devedor=devedor, credor=credor, valor=Decimal("50.00"))

    with pytest.raises(ValueError):
        gerar_cobranca_do_saldo(saldo=saldo, cidade="Sao Paulo")


@pytest.mark.django_db
def test_cobranca_de_rateio_usa_o_valor_da_parcela():
    casal = Casal.objects.create(nome="Casal")
    eberte = MembroCasal.objects.create(
        casal=casal,
        usuario=User.objects.create_user(
            username="eberte", email="e@test.dev", first_name="Eberte",
            chave_pix="ia@engaisolutions.com.br",
        ),
    )
    namorada = MembroCasal.objects.create(
        casal=casal,
        usuario=User.objects.create_user(username="namorada", email="n@test.dev"),
    )
    criar_regra_divisao(
        casal=casal, vigente_desde=date(2026, 1, 1),
        itens=[
            ItemRegra(membro=eberte, percentual=Decimal("70.00")),
            ItemRegra(membro=namorada, percentual=Decimal("30.00")),
        ],
    )
    compra = registrar_compra(
        casal=casal, descricao="Sofá", categoria=None,
        valor_total=Decimal("300.00"), quantidade_parcelas=3,
        data_compra=date(2026, 6, 19), pago_por=eberte,
        primeira_data_vencimento=date(2026, 7, 10),
    )
    parcela = compra.parcelas.order_by("numero").first()  # R$ 100,00
    rateio = parcela.rateios.get(membro=namorada)  # 30% = R$ 30,00

    cobranca = gerar_cobranca_de_rateio(rateio=rateio, cidade="Sao Paulo")

    assert cobranca.valor == Decimal("30.00")  # valor DA PARCELA, não do total
    assert cobranca.credor == eberte
    assert cobranca.devedor == namorada
    assert "540530.00" in cobranca.brcode  # tag 54 (valor) = 30.00
    assert cobranca.qr_png.startswith(PNG_MAGIC)
