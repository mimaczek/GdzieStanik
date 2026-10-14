"""
Ustawienia wspólne dla wszystkich środowisk.

Wartości zależne od środowiska są w dev.py i prod.py.
Zobacz docs/architecture.md §1 i §9.
"""

from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent

load_dotenv(BASE_DIR / ".env")


# ─────────────────────────────────────────────────────────────────
# Aplikacje
# ─────────────────────────────────────────────────────────────────

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # własne
    "accounts",
    "inventory",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Wszystkie widoki wymagają zalogowania (architecture.md §7).
    # Wyjątki oznacza się dekoratorem @login_not_required.
    "django.contrib.auth.middleware.LoginRequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

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


# ─────────────────────────────────────────────────────────────────
# Baza danych — SQLite w trybie WAL (ADR-0003)
# ─────────────────────────────────────────────────────────────────
#
# Tryb WAL i pozostałe PRAGMA ustawia sygnał connection_created
# w inventory/apps.py — Django nie robi tego samo.

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "gdziestanik.db",
        "OPTIONS": {
            # Wymagane dla CheckConstraint w transakcjach
            "transaction_mode": "IMMEDIATE",
            "timeout": 5,
        },
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ─────────────────────────────────────────────────────────────────
# Uwierzytelnianie (ADR-0007)
# ─────────────────────────────────────────────────────────────────
#
# Własny model użytkownika ustawiony PRZED pierwszą migracją.
# Późniejsza zmiana jest w Django bardzo kosztowna.

AUTH_USER_MODEL = "accounts.User"

# Argon2id jako pierwszy — reszta dla zgodności ze starymi hasłami
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

_VALIDATORS = "django.contrib.auth.password_validation"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": f"{_VALIDATORS}.UserAttributeSimilarityValidator"},
    {"NAME": f"{_VALIDATORS}.MinimumLengthValidator"},
    {"NAME": f"{_VALIDATORS}.CommonPasswordValidator"},
    {"NAME": f"{_VALIDATORS}.NumericPasswordValidator"},
]

LOGIN_URL = "/accounts/login/"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/accounts/login/"

# Sesja ważna 30 dni, przedłużana przy aktywności
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30
SESSION_SAVE_EVERY_REQUEST = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"


# ─────────────────────────────────────────────────────────────────
# Lokalizacja
# ─────────────────────────────────────────────────────────────────

LANGUAGE_CODE = "pl"
TIME_ZONE = "Europe/Warsaw"
USE_I18N = True
# Znaczniki czasu w UTC, konwersja przy wyświetlaniu (reguła G3)
USE_TZ = True


# ─────────────────────────────────────────────────────────────────
# Pliki statyczne i media
# ─────────────────────────────────────────────────────────────────

STATIC_URL = "/static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}


# ─────────────────────────────────────────────────────────────────
# Zdjęcia (ADR-0006)
# ─────────────────────────────────────────────────────────────────

PHOTO_MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB
PHOTO_MAX_DIMENSION = 1600  # dłuższy bok po skalowaniu
PHOTO_THUMBNAIL_DIMENSION = 300
PHOTO_WEBP_QUALITY = 82
PHOTO_ALLOWED_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})


# ─────────────────────────────────────────────────────────────────
# Reguły domenowe — progi ostrzeżeń
# ─────────────────────────────────────────────────────────────────

LOCATION_DEPTH_WARNING = 6  # reguła L4
ITEM_NESTING_WARNING = 3  # reguła P10
