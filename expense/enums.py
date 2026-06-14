from django.db import models
from django.utils.translation import gettext_lazy as _

class PaymentStatus(models.TextChoices):
    PENDING = "PE", _("Pending")
    PAID = "PA", _("Paid")
    LATE ="LA", _("Late")