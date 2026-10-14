#!/usr/bin/env python
"""Narzędzie wiersza poleceń Django."""

import os
import sys


def main() -> None:
    # Domyślnie środowisko deweloperskie; produkcja ustawia zmienną sama
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Nie można zaimportować Django. Czy środowisko jest aktywne?\n"
            "    source .venv/bin/activate"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
