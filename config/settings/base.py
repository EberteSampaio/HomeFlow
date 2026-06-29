"""
Settings base do HomeFlow.

Configuração compartilhada por todos os ambientes. Não usar diretamente:
selecione `config.settings.dev` ou `config.settings.prod` via DJANGO_SETTINGS_MODULE.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Carrega variáveis do .env na raiz do projeto.
load_dotenv()

# config/settings/base.py -> config/settings -> config -> raiz
BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-change-me")

# DEBUG/ALLOWED_HOSTS têm default seguro aqui e são reforçados em dev/prod.
DEBUG = False
ALLOWED_HOSTS: list[str] = []


# Application definition

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS: list[str] = []

LOCAL_APPS = [
    "apps.core",
    "apps.accounts",
    "apps.expenses",
    "apps.settlements",
    "apps.notifications",
    "apps.payments",
    "apps.web",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# Database — default SQLite; sobreposto em prod.
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# Modelo de usuário custom (AbstractUser) — definido antes da primeira migração.
AUTH_USER_MODEL = "accounts.User"

# Autenticação: todas as telas exigem login (dados financeiros são privados).
LOGIN_URL = "web:login"
LOGIN_REDIRECT_URL = "web:dashboard"
LOGOUT_REDIRECT_URL = "web:login"


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# Internationalization
LANGUAGE_CODE = os.getenv("LANGUAGE_CODE", "pt-br")
TIME_ZONE = os.getenv("TIME_ZONE", "America/Sao_Paulo")
USE_I18N = True
USE_TZ = True


# Static files — servidos pelo WhiteNoise (gunicorn não serve estáticos sozinho).
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}


# E-mail (backend definido por ambiente: console em dev, SMTP em prod).
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "no-reply@homeflow.app")
# Janela padrão (dias) de antecedência para lembretes de vencimento.
LEMBRETE_DIAS_ANTECEDENCIA = int(os.getenv("LEMBRETE_DIAS_ANTECEDENCIA", "3"))

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
