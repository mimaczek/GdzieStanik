from django.apps import AppConfig
from django.db.backends.signals import connection_created
from django.dispatch import receiver


@receiver(connection_created)
def configure_sqlite(sender, connection, **kwargs) -> None:
    """
    Ustawia PRAGMA przy każdym nowym połączeniu (ADR-0003).

    Django nie włącza trybu WAL samo. Bez tego równoległy odczyt
    podczas zapisu nie działa, a przy kilku domownikach korzystających
    naraz pojawiłyby się blokady.

    Zobacz docs/architecture.md §4.5.
    """
    if connection.vendor != "sqlite":
        return

    with connection.cursor() as cursor:
        # Odczyt równolegle z zapisem
        cursor.execute("PRAGMA journal_mode = WAL")
        # Wystarczające przy WAL, wyraźnie szybsze niż FULL
        cursor.execute("PRAGMA synchronous = NORMAL")
        # Czekaj na zwolnienie blokady zamiast zgłaszać błąd
        cursor.execute("PRAGMA busy_timeout = 5000")
        # Klucze obce — Django włącza je samo, ale lepiej mieć pewność
        cursor.execute("PRAGMA foreign_keys = ON")


class InventoryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "inventory"
    verbose_name = "Inwentarz"

    def ready(self) -> None:
        # Rejestracja sygnałów wypełniających name_norm (reguła G5)
        from . import signals  # noqa: F401
