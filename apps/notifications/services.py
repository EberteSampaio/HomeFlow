"""Service de envio de lembretes de vencimento por e-mail."""

from collections import defaultdict
from datetime import date

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone

from apps.accounts.models import MembroCasal
from apps.expenses.models import Rateio
from apps.notifications.selectors import rateios_proximos_do_vencimento
from apps.settlements.selectors import SaldoPar, calcular_saldo

ASSUNTO = "HomeFlow — vencimentos próximos"


def enviar_lembretes(*, dias: int = 3, hoje: date | None = None) -> list[str]:
    """
    Envia 1 e-mail por devedor com seus rateios PENDENTES que vencem até
    `hoje + dias`, mais o saldo líquido atual. Reusa o motor de saldo.

    Agrupa os rateios próximos por pessoa, monta uma mensagem com os itens e o
    saldo, e envia via django.core.mail (console em dev, SMTP em prod). Pessoas
    sem e-mail são puladas. Retorna a lista de e-mails para os quais enviou.
    """
    hoje = hoje or timezone.localdate()
    rateios = rateios_proximos_do_vencimento(hoje=hoje, dias=dias)

    por_membro: dict[MembroCasal, list[Rateio]] = defaultdict(list)
    for r in rateios:
        por_membro[r.membro].append(r)

    if not por_membro:
        return []

    saldos_por_casal: dict[int, list[SaldoPar]] = {}
    enviados: list[str] = []

    for membro, itens in por_membro.items():
        email = membro.usuario.email
        if not email:
            continue

        casal = membro.casal
        if casal.id not in saldos_por_casal:
            saldos_por_casal[casal.id] = calcular_saldo(casal)

        corpo = _montar_corpo(membro, itens, saldos_por_casal[casal.id])
        send_mail(
            subject=ASSUNTO,
            message=corpo,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        enviados.append(email)

    return enviados


def _nome(membro: MembroCasal) -> str:
    return membro.usuario.get_full_name() or membro.usuario.username


def _montar_corpo(
    membro: MembroCasal, itens: list[Rateio], saldo: list[SaldoPar]
) -> str:
    linhas = [
        f"Olá, {_nome(membro)}!",
        "",
        "Você tem vencimentos próximos:",
    ]
    for r in itens:
        compra = r.parcela.compra
        credor = _nome(compra.pago_por)
        linhas.append(
            f"  - {compra.descricao} (parcela {r.parcela.numero}): "
            f"R$ {r.valor_devido} para {credor}, "
            f"vence em {r.parcela.data_vencimento:%d/%m/%Y}"
        )

    linhas.append("")
    minha_divida = next((s for s in saldo if s.devedor == membro), None)
    if minha_divida is not None:
        linhas.append(
            f"Saldo atual: você deve R$ {minha_divida.valor} "
            f"a {_nome(minha_divida.credor)}."
        )
    else:
        linhas.append("Saldo atual: você está em dia.")

    return "\n".join(linhas)
