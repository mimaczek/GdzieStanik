"""
Ustawienia produkcyjne — Raspberry Pi w sieci domowej.

Zobacz docs/architecture.md §9.
"""

import os
from pathlib import Path

from .base import *  # noqa: F403

DEBUG = False

SECRET_KEY = os.environ["SECRET_KEY"]  # celowo bez wartości domyślnej

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "gdziestanik.local,localhost").split(
    ","
)

CSRF_TRUSTED_ORIGINS = os.environ.get(
    "CSRF_TRUSTED_ORIGINS", "https://gdziestanik.local"
).split(",")


# ─────────────────────────────────────────────────────────────────
# Dane na dysku zewnętrznym, nie na karcie SD (ADR-0006)
# ─────────────────────────────────────────────────────────────────

DATABASES["default"]["NAME"] = Path(  # noqa: F405
    os.environ.get("DATABASE_PATH", "/data/gdziestanik.db")
)

# UWAGA: photo_upload_path (inventory/models.py) sam dokleja prefiks
# "photos/" do każdej ścieżki — MEDIA_ROOT musi więc wskazywać na
# katalog NADRZĘDNY, inaczej pliki trafią do .../photos/photos/...
MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", "/data"))


# ─────────────────────────────────────────────────────────────────
# Pliki statyczne — hashowane nazwy, wymaga collectstatic (§9)
# ─────────────────────────────────────────────────────────────────

STORAGES["staticfiles"] = {  # noqa: F405
    "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
}


# ─────────────────────────────────────────────────────────────────
# Bezpieczeństwo
# ─────────────────────────────────────────────────────────────────
#
# UWAGA: poniższe zakłada działające HTTPS przez Caddy.
# Przy dostępie po HTTP ciasteczko sesyjne nie zostanie wysłane.

SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# Nagłówek od reverse proxy
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# HSTS wyłączony — w sieci lokalnej z certyfikatem wewnętrznym
# mógłby zablokować dostęp po jego wygaśnięciu
SECURE_HSTS_SECONDS = 0


LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}
