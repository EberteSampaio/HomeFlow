"""Job mensal: gera as compras das despesas recorrentes da competência (idempotente)."""

from datetime import date, datetime

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.accounts.models import Casal
from apps.expenses.services import gerar_recorrentes


class Command(BaseCommand):
    help = (
        "Gera as compras das despesas recorrentes ativas para a competência "
        "(default: mês atual). Idempotente — não duplica se rodar de novo."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--competencia",
            help="Mês de referência no formato YYYY-MM (default: mês atual).",
        )

    def handle(self, *args, **options):
        competencia = self._parse_competencia(options.get("competencia"))

        total = 0
        for casal in Casal.objects.all():
            criadas = gerar_recorrentes(casal=casal, competencia=competencia)
            total += len(criadas)
            if criadas:
                self.stdout.write(
                    f"{casal}: {len(criadas)} compra(s) recorrente(s) gerada(s)."
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"Competência {competencia:%Y-%m}: {total} compra(s) gerada(s)."
            )
        )

    def _parse_competencia(self, valor: str | None) -> date:
        if not valor:
            return timezone.localdate().replace(day=1)
        try:
            return datetime.strptime(valor, "%Y-%m").date().replace(day=1)
        except ValueError as exc:
            raise CommandError(
                "--competencia deve estar no formato YYYY-MM (ex.: 2026-06)."
            ) from exc
