"""Settings de desenvolvimento."""

import os

from .base import *  # noqa: F401,F403

DEBUG = True

ALLOWED_HOSTS = [os.getenv("DJANGO_ALLOWED_HOST"),"localhost", "127.0.0.1", "0.0.0.0"]

# PostgreSQL (banco da branch developer). Se POSTGRES_HOST não estiver
# definido, mantém o SQLite herdado do base.py.
if os.getenv("POSTGRES_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "homeflow"),
            "USER": os.getenv("POSTGRES_USER", "postgres"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", ""),
            "HOST": os.getenv("POSTGRES_HOST", "localhost"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
        }
    }

# E-mail no console em dev (sem SMTP).
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
# CSRF_TRUSTED_ORIGINS = [f"https://{h}" for h in ALLOWED_HOSTS if "." in h and h not in ("127.0.0.1",)]