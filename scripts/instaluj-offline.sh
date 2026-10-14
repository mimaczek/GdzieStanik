#!/usr/bin/env bash
#
# GdzieStanik — instalacja środowiska bez dostępu do internetu
#
# Wymaga wcześniejszego uruchomienia ./scripts/pobierz-zaleznosci.sh
# (poza VPN-em). Ten skrypt działa już całkowicie offline.
#
#   ./scripts/instaluj-offline.sh
#
# Tworzy .venv/ i instaluje do niego wszystko z vendor/wheels/.

set -euo pipefail

PROJEKT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENDOR_DIR="${PROJEKT_DIR}/vendor"
WHEELS_DIR="${VENDOR_DIR}/wheels"
VENV_DIR="${PROJEKT_DIR}/.venv"

CZERWONY=$'\033[0;31m'; ZIELONY=$'\033[0;32m'
ZOLTY=$'\033[0;33m';    NIEBIESKI=$'\033[0;34m'; RESET=$'\033[0m'

info()  { echo "${NIEBIESKI}==>${RESET} $*"; }
ok()    { echo "${ZIELONY}  OK${RESET} $*"; }
uwaga() { echo "${ZOLTY}  UWAGA${RESET} $*"; }
blad()  { echo "${CZERWONY}  BŁĄD${RESET} $*" >&2; }

echo
echo "╔════════════════════════════════════════════════════════╗"
echo "║  GdzieStanik — instalacja offline                      ║"
echo "╚════════════════════════════════════════════════════════╝"
echo

cd "${PROJEKT_DIR}"

# ─────────────────────────────────────────────────────────────────
# 1. Czy jest co instalować
# ─────────────────────────────────────────────────────────────────

if [[ ! -d "${WHEELS_DIR}" ]] || [[ -z "$(ls -A "${WHEELS_DIR}" 2>/dev/null)" ]]; then
    blad "Katalog vendor/wheels/ jest pusty lub nie istnieje"
    echo
    echo "  Najpierw uruchom — MAJĄC DOSTĘP DO INTERNETU:"
    echo
    echo "      ./scripts/pobierz-zaleznosci.sh"
    echo
    exit 1
fi

ok "Znaleziono $(ls -1 "${WHEELS_DIR}" | wc -l) pakietów w vendor/wheels/"

# ─────────────────────────────────────────────────────────────────
# 2. Czy venv w ogóle zadziała
# ─────────────────────────────────────────────────────────────────

info "Sprawdzam moduł venv..."

if ! python3 -c "import venv" 2>/dev/null; then
    blad "Brak modułu venv"
    echo
    echo "  Zainstaluj pakiety systemowe (wymaga hasła):"
    echo
    echo "      sudo dpkg -i vendor/deb/*.deb"
    echo "      sudo apt-get install -f          # gdyby brakowało zależności"
    echo
    exit 1
fi

# W Ubuntu venv bywa bez ensurepip — wtedy tworzymy środowisko
# bez pipa i doinstalowujemy go ręcznie z vendor/wheels/.
MA_ENSUREPIP=1
python3 -c "import ensurepip" 2>/dev/null || MA_ENSUREPIP=0

if [[ ${MA_ENSUREPIP} -eq 0 ]]; then
    uwaga "Brak ensurepip — venv powstanie bez pipa, doinstaluję go osobno"
fi
ok "Moduł venv dostępny"

# ─────────────────────────────────────────────────────────────────
# 3. Środowisko wirtualne
# ─────────────────────────────────────────────────────────────────

if [[ -d "${VENV_DIR}" ]]; then
    uwaga "Katalog .venv już istnieje"
    read -rp "  Usunąć i utworzyć od nowa? [t/N] " odp
    if [[ "${odp}" =~ ^[tT]$ ]]; then
        rm -rf "${VENV_DIR}"
        info "Usunięto stare .venv"
    else
        echo "  Zostawiam istniejące środowisko."
    fi
fi

if [[ ! -d "${VENV_DIR}" ]]; then
    info "Tworzę środowisko wirtualne..."
    if [[ ${MA_ENSUREPIP} -eq 1 ]]; then
        python3 -m venv "${VENV_DIR}"
    else
        python3 -m venv --without-pip "${VENV_DIR}"
    fi
    ok "Utworzono .venv"
fi

PY="${VENV_DIR}/bin/python"

# ─────────────────────────────────────────────────────────────────
# 4. pip wewnątrz środowiska
# ─────────────────────────────────────────────────────────────────

if ! "${PY}" -m pip --version >/dev/null 2>&1; then
    info "Instaluję pip w środowisku..."

    PIP_WHEEL="$(find "${WHEELS_DIR}" -name 'pip-*.whl' | head -1)"

    if [[ -n "${PIP_WHEEL}" ]]; then
        # Wheel pipa jest wykonywalny — można go uruchomić wprost
        "${PY}" "${PIP_WHEEL}/pip" install \
            --no-index --find-links "${WHEELS_DIR}" pip \
            >/dev/null 2>&1 && ok "pip zainstalowany z wheela"
    elif [[ -f "${VENDOR_DIR}/get-pip.py" ]]; then
        "${PY}" "${VENDOR_DIR}/get-pip.py" \
            --no-index --find-links "${WHEELS_DIR}" \
            >/dev/null 2>&1 && ok "pip zainstalowany z get-pip.py"
    else
        blad "Brak pipa i brak sposobu na jego instalację"
        echo "  Uruchom ponownie pobierz-zaleznosci.sh mając internet."
        exit 1
    fi
fi

# ─────────────────────────────────────────────────────────────────
# 5. Zależności projektu
# ─────────────────────────────────────────────────────────────────

info "Instaluję zależności z vendor/wheels/ (bez sieci)..."

# --no-index odcina PyPI całkowicie — gwarancja, że nic nie leci do sieci
if "${PY}" -m pip install \
        --no-index \
        --find-links "${WHEELS_DIR}" \
        --requirement requirements-dev.txt; then
    ok "Zależności zainstalowane"
else
    blad "Instalacja nie powiodła się"
    echo
    echo "  Najczęstsza przyczyna: brakujący pakiet w vendor/wheels/."
    echo "  Uruchom ponownie pobierz-zaleznosci.sh mając dostęp do sieci."
    exit 1
fi

# ─────────────────────────────────────────────────────────────────
# 6. Weryfikacja
# ─────────────────────────────────────────────────────────────────

info "Sprawdzam instalację..."

sprawdz() {
    local modul="$1" opis="$2"
    if "${PY}" -c "import ${modul}" 2>/dev/null; then
        echo "     ${opis}"
    else
        uwaga "${opis} — NIEDOSTĘPNY"
        return 1
    fi
}

BLEDY=0
sprawdz django        "Django $("${PY}" -c 'import django; print(django.get_version())' 2>/dev/null)" || BLEDY=1
sprawdz PIL           "Pillow" || BLEDY=1
sprawdz argon2        "argon2-cffi" || BLEDY=1
sprawdz pytest        "pytest" || BLEDY=1

# SQLite musi mieć 3.37+ ze względu na CheckConstraint (architecture.md §4.5)
SQLITE_WER="$("${PY}" -c 'import sqlite3; print(sqlite3.sqlite_version)' 2>/dev/null)"
echo "     SQLite ${SQLITE_WER}"

if [[ "$(printf '%s\n3.37.0\n' "${SQLITE_WER}" | sort -V | head -1)" != "3.37.0" ]]; then
    uwaga "SQLite starszy niż 3.37 — CheckConstraint może nie działać"
fi

# ─────────────────────────────────────────────────────────────────
# 7. Zasoby statyczne
# ─────────────────────────────────────────────────────────────────

for plik in htmx.min.js pico.min.css; do
    if [[ -f "${PROJEKT_DIR}/static/${plik}" ]]; then
        echo "     static/${plik}"
    else
        uwaga "Brak static/${plik} — interfejs nie będzie działał poprawnie"
    fi
done

echo
if [[ ${BLEDY} -eq 0 ]]; then
    echo "╔════════════════════════════════════════════════════════╗"
    echo "║  Środowisko gotowe                                     ║"
    echo "╚════════════════════════════════════════════════════════╝"
else
    echo "╔════════════════════════════════════════════════════════╗"
    echo "║  Zainstalowano, ale z brakami — zobacz UWAGA powyżej   ║"
    echo "╚════════════════════════════════════════════════════════╝"
fi
echo
echo "  Aktywacja:"
echo "      source .venv/bin/activate"
echo
echo "  Potem:"
echo "      python manage.py migrate"
echo "      python manage.py createsuperuser"
echo "      python manage.py runserver"
echo
