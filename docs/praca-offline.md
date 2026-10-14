# Praca bez dostępu do internetu

> Dotyczy sytuacji, w której maszyna deweloperska pracuje na VPN-ie
> bez dostępu do PyPI i repozytoriów Ubuntu.

Zasada: **pobierasz raz, mając internet; potem pracujesz offline.**

---

## Procedura

### Krok 1 — rozłącz VPN

```bash
cd ~/PROJECTS/GdzieStanik
./scripts/pobierz-zaleznosci.sh
```

Skrypt pobiera:

| Co | Dokąd | Po co |
|---|---|---|
| pakiety Pythona (wheels) | `vendor/wheels/` | Django, Pillow, argon2, pytest |
| pakiety systemowe (.deb) | `vendor/deb/` | `python3-pip`, `python3-venv` — brak ich w systemie |
| `get-pip.py` | `vendor/` | awaryjna instalacja pipa |
| HTMX i Pico.css | `static/` | frontend bez Node.js |

Skrypt **niczego nie instaluje w systemie i nie wymaga sudo.** Pliki `.deb`
są wyłącznie pobierane — instalacja to osobny, świadomy krok.

### Krok 2 — pakiety systemowe (raz)

Jeśli skrypt pobrał pliki `.deb`, trzeba je zainstalować. To jedyny moment
wymagający hasła:

```bash
sudo dpkg -i vendor/deb/*.deb
sudo apt-get install -f        # tylko gdyby zgłosił brakujące zależności
```

Krok można pominąć, gdy `python3 -m pip --version` już działa.

### Krok 3 — wróć na VPN i zainstaluj

```bash
./scripts/instaluj-offline.sh
```

Tworzy `.venv/` i instaluje wszystko z `vendor/wheels/` z flagą
`--no-index`, która całkowicie odcina dostęp do sieci. Na końcu sprawdza,
czy Django, Pillow, argon2 i pytest faktycznie się importują.

### Krok 4 — praca

```bash
source .venv/bin/activate
python manage.py runserver
```

---

## Dlaczego to takie zawiłe

Ubuntu 26.04 nie dostarcza `pip` ani `venv` w domyślnej instalacji.
Standardowe `python3 -m venv .venv` kończy się błędem, bo brakuje modułu
`ensurepip`. Stąd potrzeba pobrania pakietów `.deb` — zwykłe pobranie
wheels z PyPI nie wystarczy, bo nie ma czym ich zainstalować.

Skrypt `instaluj-offline.sh` radzi sobie także z sytuacją pośrednią:
gdy `venv` istnieje, ale bez `ensurepip`, tworzy środowisko przez
`--without-pip` i doinstalowuje pipa z pobranego wheela.

## Wersje

| Element | Wersja | Uwagi |
|---|---|---|
| Python | 3.14 | jedyny dostępny w Ubuntu 26.04 |
| Django | 6.0 | jedyna linia wspierająca Pythona 3.14 |
| SQLite | 3.37+ | wymagane przez `CheckConstraint` |

**Uwaga o wersjach:** `requirements.txt` ma wszystkie wersje przypięte
(`==`). To celowe — pobieranie odbywa się raz, a przy braku sieci nie ma
jak sprawdzić, co zmieniło się w nowszym wydaniu.

Django 6.0 nie jest wydaniem LTS. LTS-em jest 5.2, ale obsługuje Pythona
najwyżej do 3.13. Wybór wynika z wersji Pythona w systemie, nie z preferencji.

## Co nie trafia do repozytorium

```
vendor/                 setki MB binariów
static/htmx.min.js      pobierane skryptem
static/pico.min.css     pobierane skryptem
.venv/                  środowisko lokalne
```

Repozytorium zawiera tylko `requirements.txt`, `requirements-dev.txt`
i skrypty. Odtworzenie środowiska na nowej maszynie to powtórzenie
procedury powyżej.

## Rozwiązywanie problemów

### „Brak dostępu do https://pypi.org"

Jesteś na VPN-ie. Rozłącz się i spróbuj ponownie.

### „Katalog vendor/wheels/ jest pusty"

Nie uruchomiono jeszcze `pobierz-zaleznosci.sh`, albo pobieranie się nie
powiodło. Sprawdź `vendor/pobieranie.log`.

### „Brak modułu venv"

Nie wykonano kroku 2. Uruchom `sudo dpkg -i vendor/deb/*.deb`.

### Instalacja offline zgłasza brakujący pakiet

Któregoś wheela zabrakło — najczęściej z powodu zależności niewidocznej
przy pobieraniu. Trzeba powtórzyć krok 1 mając internet.

### Pakiet jest tylko w formie źródłowej

Skrypt ostrzega o tym na końcu. Kompilacja wymaga `build-essential`
i `python3-dev` — oba są na liście pobieranych `.deb`.

## Dokładanie nowej zależności

1. Dopisz pakiet z przypiętą wersją do `requirements.txt`.
2. Rozłącz VPN, uruchom `./scripts/pobierz-zaleznosci.sh`.
3. Wróć na VPN, uruchom `./scripts/instaluj-offline.sh`.

Skrypt pobiera przyrostowo — już obecne pliki pomija.

---

## Powiązane

- [`architecture.md`](architecture.md) — stos technologiczny
- [`adr/0007-django-zamiast-fastapi.md`](adr/0007-django-zamiast-fastapi.md)
