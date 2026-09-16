from .base import *  # noqa

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
# Required from .env — see .env.example. No hardcoded fallback.
SECRET_KEY = env("DJANGO_SECRET_KEY")

# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["0.0.0.0", "127.0.0.1"]) + ['localhost']

# CACHES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "",
    }
}

# EMAIL
# ------------------------------------------------------------------------------
# SMTP config lives in the DynamicEmailConfiguration singleton (admin panel).
# The DES backend reads it from the DB — no need to restart the server on change.
# For local dev, point the DynamicEmailConfiguration at Mailcatcher (127.0.0.1:1025).
EMAIL_BACKEND = "des.backends.ConfiguredEmailBackend"

# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#internal-ips
INTERNAL_IPS = ["127.0.0.1", "10.0.2.2"]

# django-extensions
# ------------------------------------------------------------------------------
# https://django-extensions.readthedocs.io/en/latest/installation_instructions.html#configuration
INSTALLED_APPS += ["django_extensions"]  # noqa F405

# Your stuff...
# ------------------------------------------------------------------------------
try:
    from .local_settings import *  # pylint: disable=wildcard-import, unused-wildcard-import
except ImportError:
    pass

