"""Testes de enviar_lembretes (janela, agrupamento, PAGO, self, sem e-mail)."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Casal, MembroCasal
from apps.accounts.services import ItemRegra, criar_regra_divisao
from apps.expenses.models import Rateio
from apps.expenses.services import registrar_compra
from apps.notifications.services import enviar_lembretes

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture
def casal_70_30():
    casal = Casal.objects.create(nome="Casal Teste")
    eberte = MembroCasal.objects.create(
        casal=casal,
        usuario=User.objects.create_user(username="eberte", email="eberte@test.dev"),
    )
    namorada = MembroCasal.objects.create(
        casal=casal,
        usuario=User.objects.create_user(username="namorada", email="namorada@test.dev"),
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


def _compra(casal, pago_por, valor, vencimento):
    return registrar_compra(
        casal=casal,
        descricao="Geladeira",
        categoria=None,
        valor_total=valor,
        quantidade_parcelas=1,
        data_compra=date(2026, 6, 19),
        pago_por=pago_por,
        primeira_data_vencimento=vencimento,
    )


def test_envia_lembrete_ao_devedor(casal_70_30, mailoutbox):
    casal, eberte, namorada = casal_70_30
    _compra(casal, pago_por=eberte, valor=Decimal("302.89"), vencimento=date(2026, 7, 2))

    enviados = enviar_lembretes(dias=3, hoje=date(2026, 7, 1))

    assert enviados == ["namorada@test.dev"]
    assert len(mailoutbox) == 1
    msg = mailoutbox[0]
    assert msg.to == ["namorada@test.dev"]
    assert "90.87" in msg.body  # valor devido
    assert "Geladeira" in msg.body
    assert "você deve" in msg.body.lower()


def test_pagador_nao_recebe_pelo_proprio_gasto(casal_70_30, mailoutbox):
    """Eberte paga tudo: o self-rateio dele não vira lembrete; só a namorada recebe."""
    casal, eberte, namorada = casal_70_30
    _compra(casal, pago_por=eberte, valor=Decimal("302.89"), vencimento=date(2026, 7, 2))

    enviar_lembretes(dias=3, hoje=date(2026, 7, 1))

    destinatarios = [addr for m in mailoutbox for addr in m.to]
    assert "eberte@test.dev" not in destinatarios


def test_ignora_vencimento_fora_da_janela(casal_70_30, mailoutbox):
    casal, eberte, _ = casal_70_30
    _compra(casal, pago_por=eberte, valor=Decimal("302.89"), vencimento=date(2026, 7, 30))

    enviados = enviar_lembretes(dias=3, hoje=date(2026, 7, 1))

    assert enviados == []
    assert len(mailoutbox) == 0


def test_ignora_rateio_pago(casal_70_30, mailoutbox):
    casal, eberte, namorada = casal_70_30
    compra = _compra(casal, pago_por=eberte, valor=Decimal("302.89"), vencimento=date(2026, 7, 2))
    rateio = compra.parcelas.get().rateios.get(membro=namorada)
    rateio.status_pagamento = Rateio.StatusPagamento.PAGO
    rateio.save(update_fields=["status_pagamento"])

    enviados = enviar_lembretes(dias=3, hoje=date(2026, 7, 1))

    assert enviados == []
    assert len(mailoutbox) == 0


def test_pula_pessoa_sem_email(casal_70_30, mailoutbox):
    casal, eberte, namorada = casal_70_30
    namorada.usuario.email = ""
    namorada.usuario.save(update_fields=["email"])
    _compra(casal, pago_por=eberte, valor=Decimal("302.89"), vencimento=date(2026, 7, 2))

    enviados = enviar_lembretes(dias=3, hoje=date(2026, 7, 1))

    assert enviados == []
    assert len(mailoutbox) == 0
