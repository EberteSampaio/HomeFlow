"""Seed do casal inicial: Eberte + namorada, com regra 70/30 vigente desde hoje."""

import os
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import Casal, MembroCasal, RegraDivisao
from apps.accounts.services import ItemRegra, criar_regra_divisao

User = get_user_model()


class Command(BaseCommand):
    help = "Cria o casal Eberte + namorada com a regra de divisão 70/30 vigente desde hoje (idempotente)."

    @transaction.atomic
    def handle(self, *args, **options):
        eberte, criou_eberte = User.objects.get_or_create(
            username="eberte",
            defaults={
                "email": "ia@engaisolutions.com.br",
                "first_name": "Eberte",
                "chave_pix": "ia@engaisolutions.com.br",
            },
        )
        namorada, criou_namorada = User.objects.get_or_create(
            username="namorada",
            defaults={
                "email": "namorada@homeflow.app",
                "first_name": "Namorada",
            },
        )

        # Define senha de login. Para usuários recém-criados sem senha utilizável,
        # aplica SEED_PASSWORD (se definida) ou orienta a definir manualmente.
        senha = os.getenv("SEED_PASSWORD")
        for user, criou in ((eberte, criou_eberte), (namorada, criou_namorada)):
            if criou and not user.has_usable_password():
                if senha:
                    user.set_password(senha)
                    user.save(update_fields=["password"])
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Usuário '{user.username}' criado SEM senha. "
                            f"Defina com: python manage.py changepassword {user.username} "
                            "(ou rode o seed com SEED_PASSWORD=...)."
                        )
                    )

        casal, _ = Casal.objects.get_or_create(nome="Eberte & Namorada")

        membro_eberte, _ = MembroCasal.objects.get_or_create(
            casal=casal, usuario=eberte
        )
        membro_namorada, _ = MembroCasal.objects.get_or_create(
            casal=casal, usuario=namorada
        )

        if RegraDivisao.objects.filter(casal=casal).exists():
            self.stdout.write(
                self.style.WARNING(
                    "Regra de divisão já existe para o casal — nada a criar."
                )
            )
            return

        criar_regra_divisao(
            casal=casal,
            vigente_desde=timezone.localdate(),
            itens=[
                ItemRegra(membro=membro_eberte, percentual=Decimal("70.00")),
                ItemRegra(membro=membro_namorada, percentual=Decimal("30.00")),
            ],
        )

        self.stdout.write(
            self.style.SUCCESS(
                "Seed concluído: casal 'Eberte & Namorada' com regra 70/30 "
                f"vigente desde {timezone.localdate()}."
            )
        )
