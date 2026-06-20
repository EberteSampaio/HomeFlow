"""Job diário: envia lembretes de vencimento por e-mail (agrupados por pessoa)."""

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.notifications.services import enviar_lembretes


class Command(BaseCommand):
    help = (
        "Envia lembretes por e-mail dos rateios PENDENTES que vencem até "
        "hoje + N dias, agrupados por pessoa (com o saldo atual)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dias",
            type=int,
            default=settings.LEMBRETE_DIAS_ANTECEDENCIA,
            help="Antecedência em dias para considerar o vencimento próximo.",
        )

    def handle(self, *args, **options):
        enviados = enviar_lembretes(dias=options["dias"])
        self.stdout.write(
            self.style.SUCCESS(
                f"{len(enviados)} lembrete(s) enviado(s)."
                + (f" Para: {', '.join(enviados)}" if enviados else "")
            )
        )
