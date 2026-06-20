"""Testes das views web (auth obrigatória, thin views, isolamento por casal, HTMX)."""

from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from apps.accounts.models import Casal, MembroCasal
from apps.accounts.services import ItemRegra, criar_regra_divisao
from apps.expenses.models import Categoria, Compra, DespesaRecorrente, Rateio
from apps.expenses.services import registrar_compra
from apps.settlements.selectors import calcular_saldo
from apps.web.forms import LancamentoForm

User = get_user_model()

pytestmark = pytest.mark.django_db


def _monta_casal(nome, prefixo, chave_pix=""):
    casal = Casal.objects.create(nome=nome)
    eberte = MembroCasal.objects.create(
        casal=casal,
        usuario=User.objects.create_user(
            username=f"{prefixo}_a",
            email=f"{prefixo}_a@test.dev",
            first_name="Eberte",
            chave_pix=chave_pix,
        ),
    )
    namorada = MembroCasal.objects.create(
        casal=casal,
        usuario=User.objects.create_user(
            username=f"{prefixo}_b", email=f"{prefixo}_b@test.dev", first_name="Namorada"
        ),
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


@pytest.fixture
def casal_70_30():
    return _monta_casal("Eberte & Namorada", "casal1", chave_pix="ia@engaisolutions.com.br")


@pytest.fixture
def auth_client(client, casal_70_30):
    _, eberte, _ = casal_70_30
    client.force_login(eberte.usuario)
    return client


# --- Autenticação --------------------------------------------------------

def test_dashboard_anonimo_redireciona_para_login(client, casal_70_30):
    resp = client.get(reverse("web:dashboard"))
    assert resp.status_code == 302
    assert reverse("web:login") in resp.url


@pytest.mark.parametrize(
    "url_name", ["web:dashboard", "web:lancamento_novo", "web:installments", "web:settlements"]
)
def test_views_exigem_login(client, casal_70_30, url_name):
    resp = client.get(reverse(url_name))
    assert resp.status_code == 302
    assert reverse("web:login") in resp.url


def test_login_page_200(client):
    resp = client.get(reverse("web:login"))
    assert resp.status_code == 200
    assert "Casal Finanças".encode() in resp.content


# --- Isolamento por casal ------------------------------------------------

def test_usuario_ve_apenas_o_proprio_casal(client, casal_70_30):
    casal1, eberte1, _ = casal_70_30
    registrar_compra(
        casal=casal1, descricao="CompraDoCasal1", categoria=None,
        valor_total=Decimal("100.00"), quantidade_parcelas=1,
        data_compra=date(2026, 6, 19), pago_por=eberte1,
        primeira_data_vencimento=date(2026, 7, 10),
    )
    casal2, eberte2, _ = _monta_casal("Outro Casal", "casal2")
    registrar_compra(
        casal=casal2, descricao="CompraDoCasal2", categoria=None,
        valor_total=Decimal("100.00"), quantidade_parcelas=1,
        data_compra=date(2026, 6, 19), pago_por=eberte2,
        primeira_data_vencimento=date(2026, 7, 10),
    )

    client.force_login(eberte1.usuario)
    resp = client.get(reverse("web:dashboard"))
    assert b"CompraDoCasal1" in resp.content
    assert b"CompraDoCasal2" not in resp.content  # não vaza o outro casal


# --- Telas (autenticado) -------------------------------------------------

def test_dashboard_200(auth_client):
    resp = auth_client.get(reverse("web:dashboard"))
    assert resp.status_code == 200
    assert "Núcleo Financeiro".encode() in resp.content


def test_lancamento_get_200_mostra_divisao(auth_client):
    resp = auth_client.get(reverse("web:lancamento_novo"))
    assert resp.status_code == 200
    assert "Divisão Automática".encode() in resp.content


def test_lancamento_post_cria_compra(auth_client, casal_70_30):
    casal, eberte, _ = casal_70_30
    resp = auth_client.post(
        reverse("web:lancamento_novo"),
        data={
            "descricao": "Geladeira",
            "valor_total": "302.89",
            "data_compra": "2026-06-19",
            "pago_por": str(eberte.pk),
            "quantidade_parcelas": "1",
            "primeira_data_vencimento": "2026-07-10",
        },
    )
    assert resp.status_code == 302
    assert resp.url == reverse("web:dashboard")
    assert Compra.objects.filter(casal=casal, descricao="Geladeira").count() == 1


def test_divisao_preview_htmx(auth_client):
    resp = auth_client.get(
        reverse("web:divisao_preview"),
        data={"valor_total": "100.00", "data_compra": "2026-06-19"},
    )
    assert resp.status_code == 200
    # 70% do Eberte = 70,00; 30% da Namorada = 30,00 (formatação pt-br).
    assert b"70%" in resp.content
    assert "R$ 70,00".encode() in resp.content
    assert "R$ 30,00".encode() in resp.content


def _compra_simples(casal, descricao, pago_por, categoria=None, valor="100.00", parcelas=1):
    # Vencimento no passado para não aparecer no widget global "Próximas Parcelas",
    # isolando o efeito dos filtros na tabela de Despesas Recentes.
    return registrar_compra(
        casal=casal, descricao=descricao, categoria=categoria,
        valor_total=Decimal(valor), quantidade_parcelas=parcelas,
        data_compra=date(2026, 1, 2), pago_por=pago_por,
        primeira_data_vencimento=date(2026, 1, 5),
    )


# --- Filtros do painel ---------------------------------------------------

def test_dashboard_filtra_por_categoria(auth_client, casal_70_30):
    casal, eberte, namorada = casal_70_30
    moradia = Categoria.objects.create(casal=casal, nome="Moradia")
    lazer = Categoria.objects.create(casal=casal, nome="Lazer")
    _compra_simples(casal, "Aluguel", eberte, categoria=moradia)
    _compra_simples(casal, "Cinema", namorada, categoria=lazer)

    resp = auth_client.get(reverse("web:dashboard"), {"categoria": moradia.id})
    assert resp.status_code == 200
    assert b"Aluguel" in resp.content
    assert b"Cinema" not in resp.content


def test_dashboard_saldo_respeita_o_filtro(auth_client, casal_70_30):
    casal, eberte, namorada = casal_70_30
    moradia = Categoria.objects.create(casal=casal, nome="Moradia")
    lazer = Categoria.objects.create(casal=casal, nome="Lazer")
    _compra_simples(casal, "Aluguel", eberte, categoria=moradia, valor="100.00")  # devido 30,00
    _compra_simples(casal, "Cinema", eberte, categoria=lazer, valor="200.00")  # devido 60,00

    # Sem filtro: saldo total devido pela namorada = 90,00.
    resp = auth_client.get(reverse("web:dashboard"))
    assert "R$ 90,00".encode() in resp.content

    # Filtrando por Moradia: saldo cai para 30,00 (e o 90,00 some).
    resp = auth_client.get(reverse("web:dashboard"), {"categoria": moradia.id})
    assert "R$ 30,00".encode() in resp.content
    assert "R$ 90,00".encode() not in resp.content


def test_dashboard_filtra_por_quem_pagou(auth_client, casal_70_30):
    casal, eberte, namorada = casal_70_30
    _compra_simples(casal, "Aluguel", eberte)
    _compra_simples(casal, "Cinema", namorada)

    resp = auth_client.get(reverse("web:dashboard"), {"pago_por": namorada.id})
    assert resp.status_code == 200
    assert b"Cinema" in resp.content
    assert b"Aluguel" not in resp.content


# --- Pix por parcela + marcar pago --------------------------------------

def test_settlements_gera_um_pix_por_parcela(auth_client, casal_70_30):
    casal, eberte, _ = casal_70_30
    _compra_simples(casal, "Sofá", eberte, valor="300.00", parcelas=3)

    resp = auth_client.get(reverse("web:settlements"))
    assert resp.status_code == 200
    # 3 parcelas -> 3 dívidas da namorada -> 3 QRs e 3 botões de pagamento.
    assert resp.content.count(b"data:image/png;base64,") == 3
    assert resp.content.count(b"Marcar como pago") == 3


def test_marcar_rateio_pago_zera_saldo(auth_client, casal_70_30):
    casal, eberte, namorada = casal_70_30
    compra = _compra_simples(casal, "Geladeira", eberte, valor="302.89")
    rateio = compra.parcelas.get().rateios.get(membro=namorada)

    resp = auth_client.post(reverse("web:rateio_pagar", args=[rateio.id]))
    assert resp.status_code == 302
    assert resp.url == reverse("web:settlements")

    rateio.refresh_from_db()
    assert rateio.status_pagamento == Rateio.StatusPagamento.PAGO
    assert rateio.data_pagamento is not None
    assert calcular_saldo(casal) == []  # dívida saiu do saldo


def test_rateio_pagar_de_outro_casal_404(client, casal_70_30):
    casal1, eberte1, _ = casal_70_30
    casal2, eberte2, namorada2 = _monta_casal("Outro Casal", "casalx")
    compra2 = _compra_simples(casal2, "Coisa", eberte2, valor="302.89")
    rateio2 = compra2.parcelas.get().rateios.get(membro=namorada2)

    client.force_login(eberte1.usuario)  # usuário do casal 1
    resp = client.post(reverse("web:rateio_pagar", args=[rateio2.id]))
    assert resp.status_code == 404  # não pode quitar dívida de outro casal

    rateio2.refresh_from_db()
    assert rateio2.status_pagamento == Rateio.StatusPagamento.PENDENTE


def test_lancamento_form_nao_tem_checkbox_parcelada(casal_70_30):
    casal, *_ = casal_70_30
    form = LancamentoForm(casal=casal)
    assert "parcelada" not in form.fields
    assert "quantidade_parcelas" in form.fields


def test_lancamento_post_com_parcelas_cria_n_parcelas(auth_client, casal_70_30):
    casal, eberte, _ = casal_70_30
    resp = auth_client.post(
        reverse("web:lancamento_novo"),
        data={
            "descricao": "Sofá",
            "valor_total": "300.00",
            "data_compra": "2026-06-19",
            "pago_por": str(eberte.pk),
            "quantidade_parcelas": "3",
            "primeira_data_vencimento": "2026-07-10",
        },
    )
    assert resp.status_code == 302
    compra = Compra.objects.get(casal=casal, descricao="Sofá")
    assert compra.parcelas.count() == 3


# --- Parcelas agrupadas por compra + QR Pix embutido --------------------

def test_installments_agrupa_compra_e_mostra_qr(auth_client, casal_70_30):
    casal, eberte, _ = casal_70_30
    _compra_simples(casal, "Geladeira", eberte, valor="302.89")

    resp = auth_client.get(reverse("web:installments"))
    assert resp.status_code == 200
    assert b"Geladeira" in resp.content
    # Dívida pendente da namorada -> QR Pix embutido e botão de pagar na própria tela.
    assert b"data:image/png;base64," in resp.content
    assert b"Marcar como pago" in resp.content


def test_installments_filtra_por_categoria(auth_client, casal_70_30):
    casal, eberte, namorada = casal_70_30
    moradia = Categoria.objects.create(casal=casal, nome="Moradia")
    lazer = Categoria.objects.create(casal=casal, nome="Lazer")
    _compra_simples(casal, "Aluguel", eberte, categoria=moradia)
    _compra_simples(casal, "Cinema", namorada, categoria=lazer)

    resp = auth_client.get(reverse("web:installments"), {"categoria": moradia.id})
    assert resp.status_code == 200
    assert b"Aluguel" in resp.content
    assert b"Cinema" not in resp.content


def test_rateio_pagar_volta_para_origem(auth_client, casal_70_30):
    casal, eberte, namorada = casal_70_30
    compra = _compra_simples(casal, "Geladeira", eberte, valor="302.89")
    rateio = compra.parcelas.get().rateios.get(membro=namorada)

    resp = auth_client.post(
        reverse("web:rateio_pagar", args=[rateio.id]),
        data={"next": reverse("web:installments")},
    )
    assert resp.status_code == 302
    assert resp.url == reverse("web:installments")


# --- Contas do Mês (fixas e variáveis) ----------------------------------

def test_despesas_mes_lista_fixas_e_variaveis(auth_client, casal_70_30):
    casal, eberte, _ = casal_70_30
    DespesaRecorrente.objects.create(
        casal=casal, descricao="Aluguel", valor=Decimal("2000.00"),
        dia_vencimento=10, pago_por=eberte, ativo=True,
    )
    # Variável avulsa vencendo em 06/2026.
    registrar_compra(
        casal=casal, descricao="Mercado", categoria=None,
        valor_total=Decimal("250.00"), quantidade_parcelas=1,
        data_compra=date(2026, 6, 1), pago_por=eberte,
        primeira_data_vencimento=date(2026, 6, 15),
    )

    resp = auth_client.get(reverse("web:despesas_mes"), {"mes": "2026-06"})
    assert resp.status_code == 200
    assert b"Aluguel" in resp.content       # fixa
    assert b"Mercado" in resp.content       # variável
    assert "Despesas Fixas".encode() in resp.content
    assert "Despesas Variáveis".encode() in resp.content


def test_despesas_mes_filtra_pelo_mes(auth_client, casal_70_30):
    casal, eberte, _ = casal_70_30
    registrar_compra(
        casal=casal, descricao="MercadoJulho", categoria=None,
        valor_total=Decimal("100.00"), quantidade_parcelas=1,
        data_compra=date(2026, 7, 1), pago_por=eberte,
        primeira_data_vencimento=date(2026, 7, 15),
    )
    # Mês de junho não deve listar a parcela que vence em julho.
    resp = auth_client.get(reverse("web:despesas_mes"), {"mes": "2026-06"})
    assert b"MercadoJulho" not in resp.content
    # Mês de julho lista.
    resp = auth_client.get(reverse("web:despesas_mes"), {"mes": "2026-07"})
    assert b"MercadoJulho" in resp.content


def test_settlements_mostra_saldo_e_pix(auth_client, casal_70_30):
    casal, eberte, _ = casal_70_30
    registrar_compra(
        casal=casal,
        descricao="Geladeira",
        categoria=None,
        valor_total=Decimal("302.89"),
        quantidade_parcelas=1,
        data_compra=date(2026, 6, 19),
        pago_por=eberte,
        primeira_data_vencimento=date(2026, 7, 10),
    )
    resp = auth_client.get(reverse("web:settlements"))
    assert resp.status_code == 200
    assert b"90.87" in resp.content  # valor no payload Pix
    assert b"Pix copia-e-cola" in resp.content
    assert b"data:image/png;base64," in resp.content  # QR embutido
