from django.contrib.auth.models import User

from django.db import models
from expense.enums import PaymentStatus
from django.core.validators import MinValueValidator
from django.utils.translation import gettext_lazy as _

# Create your models here.

class Purchase(models.Model):
    item=models.TextField(
        verbose_name=_("Purchased Item"),
    )
    total_amount=models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Total Amount"),

    )
    installment_count=models.PositiveIntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name=_("Installment Count"),
    )
    purchase_date=models.DateField(
        verbose_name=_("Purchase Date"),
    )
    status=models.CharField(
        max_length=5,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        verbose_name=_("Status"),
    )
    created_at=models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created at"),
    )
    updated_at=models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated at"),
    )

    class Meta:
        verbose_name = _("Purchase")
        verbose_name_plural = _("Purchases")
        ordering = ["-purchase_date","-created_at"]
        db_table = "purchases"

    def __str__(self):
        return f"Purchase #{self.pk} - {self.get_status_display()}"

class Installment(models.Model):
    purchase=models.ForeignKey(
        Purchase,
        on_delete=models.CASCADE,
        related_name="installments",
        verbose_name=_("Purchase"),
    )
    installment_number=models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name=_("Installment Number"),
    )
    amount=models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    status = models.CharField(
        max_length=5,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        verbose_name=_("Status"),
    )
    due_date=models.DateField(
        verbose_name=_("Due Date"),
    )
    created_at=models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created at"),
    )
    updated_at=models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated at"),
    )

    class Meta:
        verbose_name = _("Installment")
        verbose_name_plural = _("Installments")
        ordering = ["-created_at","-updated_at"]
        db_table = "installments"

    def __str__(self):
        return f"Installment #{self.pk} - {self.get_status_display()}"


class InstallmentSplit(models.Model):
    installment=models.ForeignKey(
        Installment,
        on_delete=models.CASCADE,
        related_name="installment",
        verbose_name=_("Installment Split"),
    )
    debtor=models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="debtor",
    )
    percentage_applied=models.DecimalField(
        max_digits=10,
        decimal_places=2,
    )
    amount_owed=models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Amount Owed"),
    )

    status=models.CharField(
        max_length=5,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING,
        verbose_name=_("Status"),
    )
    created_at=models.DateTimeField(
        auto_now_add=True,
        verbose_name=_("Created at"),
    )
    updated_at=models.DateTimeField(
        auto_now=True,
        verbose_name=_("Updated at"),
    )
    payment_date=models.DateField(
        verbose_name=_("Payment Date"),
        null=True,
        blank=True,
    )
    class Meta:
        verbose_name = _("Installment Split")
        verbose_name_plural = _("Installment Splits")
        ordering = ["-status","-created_at"]
        db_table = "installment_splits"

    def __str__(self):
        return f"Installment Split #{self.pk} - {self.get_status_display()}"
