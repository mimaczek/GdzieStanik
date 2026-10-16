"""Ustawienia dla pracy lokalnej."""

from .base import *  # noqa: F403

DEBUG = True

# Klucz tylko dla środowiska deweloperskiego — nigdy w produkcji
SECRET_KEY = "dev-key-nie-uzywac-w-produkcji-0000000000000000000000"

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "[::1]", "*"]

# Bez HTTPS lokalnie
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

INTERNAL_IPS = ["127.0.0.1"]
