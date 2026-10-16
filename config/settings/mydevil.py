"""
Ustawienia produkcyjne — hosting mydevil.net (FreeBSD, Phusion Passenger).

Różnice względem prod.py (który zakłada Docker na Raspberry Pi):

  - brak SECURE_PROXY_SSL_HEADER swoisty dla Caddy — mydevil kończy
    HTTPS na własnym reverse proxy przed Passengerem, z innym sposobem
    przekazywania informacji o protokole (sprawdzone empirycznie,
    patrz uwaga przy SESSION_COOKIE_SECURE niżej)
  - dane (baza, media, .env) leżą w ~/domains/<domena>/data/, POZA
    katalogiem repozytorium (Source/) — żeby `git clean` czy reset
    gałęzi nigdy ich nie dotknęły
  - statyki trafiają wprost do public_python/public/static/, bo
    mydevil ma własny serwer frontowy obsługujący ten katalog;
    CompressedManifestStaticFilesStorage (z prod.py) nie jest tu
    potrzebny — hosting współdzielony nie korzysta z WhiteNoise

Zobacz docs/architecture.md §9 (opisuje wariant Docker/Raspberry Pi;
ten plik to alternatywna ścieżka wdrożenia, patrz ADR-0008).
"""

import os
from pathlib import Path

from .base import *  # noqa: F403

DEBUG = False

SECRET_KEY = os.environ["SECRET_KEY"]  # celowo bez wartości domyślnej

ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "gdziestanik.lubian.net").split(",")

CSRF_TRUSTED_ORIGINS = os.environ.get(
    "CSRF_TRUSTED_ORIGINS", "https://gdziestanik.lubian.net"
).split(",")


# ─────────────────────────────────────────────────────────────────
# Dane poza katalogiem repozytorium
# ─────────────────────────────────────────────────────────────────
#
# DATA_DIR domyślnie zakłada strukturę:
#   ~/domains/gdziestanik.lubian.net/Source/GdzieStanik/   <- BASE_DIR
#   ~/domains/gdziestanik.lubian.net/data/                 <- DATA_DIR
#
# czyli DATA_DIR to "dwa poziomy w górę od repo, potem data/".
# Nadpisywalne zmienną środowiskową, gdyby struktura katalogów
# na koncie była inna.

DATA_DIR = Path(
    os.environ.get("DATA_DIR", BASE_DIR.parent.parent / "data")  # noqa: F405
)

DATABASES["default"]["NAME"] = DATA_DIR / "gdziestanik.db"  # noqa: F405

# Jak w prod.py: photo_upload_path dokleja "photos/" samo,
# więc MEDIA_ROOT wskazuje na katalog nadrzędny wobec photos/.
MEDIA_ROOT = DATA_DIR


# ─────────────────────────────────────────────────────────────────
# Pliki statyczne — wprost do katalogu serwowanego przez mydevil
# ─────────────────────────────────────────────────────────────────
#
# Brak WhiteNoise w tym wariancie: mydevil ma własny serwer frontowy
# (nie Passenger/Python) obsługujący public_python/public/ — prostszy
# i bardziej typowy dla tej platformy wzorzec niż serwowanie plików
# statycznych z poziomu aplikacji Django.
#
# STATIC_ROOT musi wskazywać na katalog pod public_python/public/,
# żeby serwer frontowy mydevil w ogóle widział te pliki. Domyślna
# wartość zakłada strukturę:
#   ~/domains/gdziestanik.lubian.net/public_python/public/static/

STATIC_ROOT = Path(
    os.environ.get(
        "STATIC_ROOT",
        BASE_DIR.parent.parent / "public_python" / "public" / "static",  # noqa: F405
    )
)


# ─────────────────────────────────────────────────────────────────
# Bezpieczeństwo
# ─────────────────────────────────────────────────────────────────
#
# mydevil deklaruje HTTPS + Let's Encrypt na warstwie przed Passengerem.
# SECURE_PROXY_SSL_HEADER zależy od tego, JAK ten proxy przekazuje
# informację o oryginalnym protokole — Passenger na FreeBSD zwykle
# ustawia to poprawnie bez dodatkowej konfiguracji, ale WYMAGA
# WERYFIKACJI PO PIERWSZYM WDROŻENIU (patrz docs/wdrozenie-mydevil.md).
#
# Dopóki nie jest potwierdzone, że request.is_secure() zwraca True
# przy realnym żądaniu HTTPS, SESSION_COOKIE_SECURE=True mogłoby
# uniemożliwić zalogowanie się (ciasteczko nie zostałoby wysłane).

SESSION_COOKIE_SECURE = os.environ.get("HTTPS_CONFIRMED") == "1"
CSRF_COOKIE_SECURE = os.environ.get("HTTPS_CONFIRMED") == "1"

SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# HSTS wyłączony do czasu potwierdzenia powyższego — błędne wymuszenie
# HTTPS przy niedziałającym jeszcze certyfikacie zablokowałoby dostęp
# bez możliwości łatwego cofnięcia (przeglądarki pamiętają HSTS).
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
