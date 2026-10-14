#!/usr/bin/env bash
#
# GdzieStanik — pobieranie zależności do pracy offline
#
# URUCHOM TEN SKRYPT GDY MASZ DOSTĘP DO INTERNETU (poza VPN-em).
# Wszystko ląduje w katalogu vendor/ i działa potem bez sieci.
#
#   ./scripts/pobierz-zaleznosci.sh
#
# Po zakończeniu: ./scripts/instaluj-offline.sh (już bez internetu)
#
# Skrypt NIE instaluje niczego w systemie i NIE wymaga sudo.
# Pliki .deb tylko pobiera — instalacja jest osobnym, świadomym krokiem.

set -euo pipefail

# ─────────────────────────────────────────────────────────────────
# Ustawienia
# ─────────────────────────────────────────────────────────────────

PROJEKT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENDOR_DIR="${PROJEKT_DIR}/vendor"
WHEELS_DIR="${VENDOR_DIR}/wheels"
DEB_DIR="${VENDOR_DIR}/deb"
LOG="${VENDOR_DIR}/pobieranie.log"

# Pakiety systemowe potrzebne, bo Ubuntu 26.04 nie ma pip ani venv
PAKIETY_APT=(python3-pip python3-venv python3-dev build-essential)

# ─────────────────────────────────────────────────────────────────
# Pomocnicze
# ─────────────────────────────────────────────────────────────────

CZERWONY=$'\033[0;31m'; ZIELONY=$'\033[0;32m'
ZOLTY=$'\033[0;33m';    NIEBIESKI=$'\033[0;34m'; RESET=$'\033[0m'

info()  { echo "${NIEBIESKI}==>${RESET} $*"; }
ok()    { echo "${ZIELONY}  OK${RESET} $*"; }
uwaga() { echo "${ZOLTY}  UWAGA${RESET} $*"; }
blad()  { echo "${CZERWONY}  BŁĄD${RESET} $*" >&2; }

umieram() { blad "$*"; echo; echo "Przerwano. Zobacz: ${LOG}"; exit 1; }

# ─────────────────────────────────────────────────────────────────
# 1. Sprawdzenie środowiska
# ─────────────────────────────────────────────────────────────────

echo
echo "╔════════════════════════════════════════════════════════╗"
echo "║  GdzieStanik — pobieranie zależności                   ║"
echo "╚════════════════════════════════════════════════════════╝"
echo

info "Sprawdzam dostęp do internetu..."
if ! timeout 10 curl -sI https://pypi.org >/dev/null 2>&1; then
    blad "Brak dostępu do https://pypi.org"
    echo
    echo "  Ten skrypt wymaga internetu. Jeśli jesteś na VPN-ie,"
    echo "  rozłącz się i uruchom go ponownie."
    exit 1
fi
ok "Internet działa"

info "Sprawdzam wersję Pythona..."
PY_WERSJA="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
ok "Python ${PY_WERSJA}"

if [[ "${PY_WERSJA}" != "3.14" ]]; then
    uwaga "Projekt zakłada Pythona 3.14 (zob. docs/architecture.md)"
    uwaga "Masz ${PY_WERSJA} — pobrane pakiety mogą nie pasować"
    read -rp "  Kontynuować mimo to? [t/N] " odp
    [[ "${odp}" =~ ^[tT]$ ]] || exit 1
fi

mkdir -p "${WHEELS_DIR}" "${DEB_DIR}"
: > "${LOG}"

# ─────────────────────────────────────────────────────────────────
# 2. pip — potrzebny do pobrania reszty
# ─────────────────────────────────────────────────────────────────

info "Sprawdzam pip..."

PIP_CMD=""
if python3 -m pip --version >/dev/null 2>&1; then
    PIP_CMD="python3 -m pip"
    ok "pip jest dostępny w systemie"
else
    uwaga "Brak pip — pobieram get-pip.py"

    if ! curl -fsSL https://bootstrap.pypa.io/get-pip.py \
         -o "${VENDOR_DIR}/get-pip.py" 2>>"${LOG}"; then
        umieram "Nie udało się pobrać get-pip.py"
    fi
    ok "Zapisano vendor/get-pip.py"

    # Instalacja pip tylko dla bieżącego użytkownika, bez sudo.
    info "Instaluję pip lokalnie (--user, bez sudo)..."
    if python3 "${VENDOR_DIR}/get-pip.py" --user >>"${LOG}" 2>&1; then
        export PATH="${HOME}/.local/bin:${PATH}"
        PIP_CMD="python3 -m pip"
        ok "pip zainstalowany w ~/.local"
    else
        umieram "Instalacja pip nie powiodła się — zobacz ${LOG}"
    fi
fi

# ─────────────────────────────────────────────────────────────────
# 3. Pakiety systemowe (.deb)
# ─────────────────────────────────────────────────────────────────

info "Pobieram pakiety systemowe (.deb)..."
echo "     ${PAKIETY_APT[*]}"

# apt-get download nie wymaga sudo. Pobieramy też zależności,
# bo bez sieci nie będzie skąd ich wziąć.
cd "${DEB_DIR}"

BRAKUJACE=()
for pakiet in "${PAKIETY_APT[@]}"; do
    if dpkg -s "${pakiet}" >/dev/null 2>&1; then
        echo "     ${pakiet} — już zainstalowany, pomijam"
    else
        BRAKUJACE+=("${pakiet}")
    fi
done

if [[ ${#BRAKUJACE[@]} -eq 0 ]]; then
    ok "Wszystkie pakiety systemowe są już zainstalowane"
else
    # Lista zależności, które trzeba pobrać razem z pakietami.
    ZALEZNOSCI="$(apt-get install --no-install-recommends \
                   --print-uris --yes "${BRAKUJACE[@]}" 2>>"${LOG}" \
                  | grep -oP "(?<=')[^']*\.deb(?=')" || true)"

    if [[ -z "${ZALEZNOSCI}" ]]; then
        uwaga "Nie udało się ustalić listy .deb — pobieram pojedynczo"
        for pakiet in "${BRAKUJACE[@]}"; do
            apt-get download "${pakiet}" >>"${LOG}" 2>&1 \
                && echo "     pobrano ${pakiet}" \
                || uwaga "nie udało się pobrać ${pakiet}"
        done
    else
        LICZBA="$(echo "${ZALEZNOSCI}" | wc -l)"
        echo "     do pobrania: ${LICZBA} plików"
        echo "${ZALEZNOSCI}" | while read -r url; do
            nazwa="$(basename "${url}")"
            [[ -f "${nazwa}" ]] && continue
            curl -fsSL -O "${url}" 2>>"${LOG}" \
                || uwaga "pominięto ${nazwa}"
        done
    fi
    ok "Pakiety .deb w vendor/deb/ ($(ls -1 ./*.deb 2>/dev/null | wc -l) plików)"
fi

cd "${PROJEKT_DIR}"

# ─────────────────────────────────────────────────────────────────
# 4. Pakiety Pythona (wheels)
# ─────────────────────────────────────────────────────────────────

info "Pobieram pakiety Pythona do vendor/wheels/..."

for plik in requirements.txt requirements-dev.txt; do
    [[ -f "${plik}" ]] || umieram "Brak pliku ${plik}"
done

# --only-binary=:all: wymusza gotowe wheels zamiast źródeł.
# Bez tego instalacja offline mogłaby wymagać kompilacji.
if ${PIP_CMD} download \
        --dest "${WHEELS_DIR}" \
        --requirement requirements-dev.txt \
        --only-binary=:all: \
        >>"${LOG}" 2>&1; then
    ok "Pobrano wheels ($(ls -1 "${WHEELS_DIR}" | wc -l) plików)"
else
    uwaga "Pobieranie z --only-binary nie powiodło się"
    uwaga "Ponawiam, dopuszczając pakiety źródłowe..."

    if ${PIP_CMD} download \
            --dest "${WHEELS_DIR}" \
            --requirement requirements-dev.txt \
            >>"${LOG}" 2>&1; then
        ok "Pobrano ($(ls -1 "${WHEELS_DIR}" | wc -l) plików)"
        uwaga "Część pakietów jest w formie źródłowej."
        uwaga "Instalacja offline może wymagać build-essential i python3-dev."
    else
        umieram "Pobieranie pakietów Pythona nie powiodło się — zobacz ${LOG}"
    fi
fi

# pip, setuptools i wheel — potrzebne do stworzenia środowiska offline
info "Pobieram narzędzia do budowy środowiska..."
${PIP_CMD} download --dest "${WHEELS_DIR}" \
    pip setuptools wheel >>"${LOG}" 2>&1 \
    && ok "pip, setuptools, wheel" \
    || uwaga "Nie udało się pobrać narzędzi — venv może nie zadziałać offline"

# ─────────────────────────────────────────────────────────────────
# 5. Zasoby statyczne (bez Node.js — ADR-0007)
# ─────────────────────────────────────────────────────────────────

info "Pobieram zasoby frontendu..."

STATIC_DIR="${PROJEKT_DIR}/static"
mkdir -p "${STATIC_DIR}"

pobierz_statyk() {
    local url="$1" cel="$2" opis="$3"
    if [[ -f "${cel}" ]]; then
        echo "     ${opis} — już jest, pomijam"
        return 0
    fi
    if curl -fsSL "${url}" -o "${cel}" 2>>"${LOG}"; then
        echo "     pobrano ${opis}"
    else
        uwaga "nie udało się pobrać ${opis}"
    fi
}

pobierz_statyk \
    "https://unpkg.com/htmx.org@2.0.4/dist/htmx.min.js" \
    "${STATIC_DIR}/htmx.min.js" \
    "HTMX 2.0.4"

pobierz_statyk \
    "https://unpkg.com/@picocss/pico@2.0.6/css/pico.min.css" \
    "${STATIC_DIR}/pico.min.css" \
    "Pico.css 2.0.6"

ok "Zasoby statyczne w static/"

# ─────────────────────────────────────────────────────────────────
# 6. Podsumowanie
# ─────────────────────────────────────────────────────────────────

LICZBA_WHEELS="$(ls -1 "${WHEELS_DIR}" 2>/dev/null | wc -l)"
LICZBA_DEB="$(ls -1 "${DEB_DIR}"/*.deb 2>/dev/null | wc -l || echo 0)"
ROZMIAR="$(du -sh "${VENDOR_DIR}" 2>/dev/null | cut -f1)"

echo
echo "╔════════════════════════════════════════════════════════╗"
echo "║  Gotowe                                                ║"
echo "╚════════════════════════════════════════════════════════╝"
echo
echo "  vendor/wheels/   ${LICZBA_WHEELS} pakietów Pythona"
echo "  vendor/deb/      ${LICZBA_DEB} pakietów systemowych"
echo "  static/          HTMX + Pico.css"
echo "  Razem:           ${ROZMIAR}"
echo
echo "  Możesz wrócić na VPN. Dalej:"
echo
if [[ ${LICZBA_DEB} -gt 0 ]]; then
    echo "    1. sudo dpkg -i vendor/deb/*.deb     # wymaga hasła"
    echo "    2. ./scripts/instaluj-offline.sh"
else
    echo "    ./scripts/instaluj-offline.sh"
fi
echo
echo "  Log: ${LOG}"
echo
