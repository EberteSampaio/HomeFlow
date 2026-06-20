"""Settings de desenvolvimento."""

from .base import *  # noqa: F401,F403

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0"]

# E-mail no console em dev (sem SMTP).
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
