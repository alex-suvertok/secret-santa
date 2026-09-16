"""
Production/container settings for secret_santa (Docker + PostgreSQL).
"""

from .base import *  # noqa F401,F403
from .base import env

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = env.bool("DJANGO_DEBUG", default=False)
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
# Required from env (see .env.example). No hardcoded fallback.
SECRET_KEY = env("DJANGO_SECRET_KEY")

# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

# DATABASES
# ------------------------------------------------------------------------------
# Postgres connection string, e.g. postgres://user:pass@db:5432/secret_santa
DATABASES = {"default": env.db("DATABASE_URL")}

# SECURITY
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#secure-proxy-ssl-header
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# https://docs.djangoproject.com/en/dev/ref/settings/#session-cookie-secure
SESSION_COOKIE_SECURE = not DEBUG
# https://docs.djangoproject.com/en/dev/ref/settings/#csrf-cookie-secure
CSRF_COOKIE_SECURE = not DEBUG

# STATIC
# ------------------------------------------------------------------------------
# https://whitenoise.readthedocs.io/en/latest/django.html
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"