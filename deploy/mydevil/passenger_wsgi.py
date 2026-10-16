"""
Punkt wejścia dla Phusion Passenger na mydevil.net.

TEN PLIK NIE JEST CZĘŚCIĄ APLIKACJI DJANGO — żyje poza repozytorium,
w katalogu public_python/ wskazanym przy konfigurowaniu domeny
w panelu mydevil (devil www add). Trzymany tutaj w repo wyłącznie
po to, żeby był wersjonowany; instalacja to ręczne skopiowanie
(patrz docs/wdrozenie-mydevil.md).

Oczekiwana struktura katalogów na serwerze:

    ~/domains/gdziestanik.lubian.net/
    ├── Source/GdzieStanik/       <- repozytorium git (ten projekt)
    ├── venv/gdzie_stanik_venv/   <- interpreter wskazany w panelu mydevil
    ├── data/                     <- baza, media, .env (POZA repo)
    └── public_python/
        ├── passenger_wsgi.py     <- TEN PLIK (kopia stąd)
        ├── tmp/restart.txt       <- dotknięcie = restart aplikacji
        └── public/static/        <- cel collectstatic

Passenger importuje ten moduł i szuka w nim zmiennej `application`
(standard WSGI) — nie wywołuje żadnej funkcji, tylko czyta atrybut
modułu na poziomie importu.
"""

import os
import sys
from pathlib import Path

# Katalog z kodem Django — jeden poziom wyżej niż public_python/,
# potem Source/GdzieStanik/. Jeśli struktura na koncie jest inna,
# to jedyna linijka do poprawienia w całym pliku.
PROJECT_DIR = Path(__file__).resolve().parent.parent / "Source" / "GdzieStanik"

sys.path.insert(0, str(PROJECT_DIR))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.mydevil")

from django.core.wsgi import get_wsgi_application  # noqa: E402

application = get_wsgi_application()
