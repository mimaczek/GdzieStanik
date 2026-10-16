# Wdrożenie na mydevil.net

> Status: **pierwsze wdrożenie w toku** · Data: 2026-10-14
>
> Alternatywa dla wariantu Docker/Raspberry Pi z `architecture.md` §9.
> Uzasadnienie wyboru platformy: [ADR-0008](adr/0008-hosting-mydevil.md).

---

## Założenia

| | |
|---|---|
| Platforma | FreeBSD, hosting współdzielony, Phusion Passenger |
| Python | 3.12 (systemowy na mydevil) |
| Django | 6.0 (bez zmian względem środowiska deweloperskiego) |
| Serwer aplikacji | Passenger — **nie** gunicorn, **nie** `runserver` |
| HTTPS | Let's Encrypt zarządzany przez panel mydevil |
| Baza i media | poza repozytorium, w `~/domains/<domena>/data/` |

## Struktura katalogów na serwerze

```
~/domains/gdziestanik.lubian.net/
├── Source/GdzieStanik/          repozytorium git — ten projekt
├── venv/gdzie_stanik_venv/      środowisko Python, skonfigurowane w panelu
├── data/                        POZA repo — baza, zdjęcia, .env
│   ├── .env
│   ├── gdziestanik.db
│   └── photos/
├── public_python/
│   ├── passenger_wsgi.py        kopia z deploy/mydevil/
│   ├── tmp/
│   │   └── restart.txt          dotknięcie = restart aplikacji
│   └── public/
│       └── static/              cel collectstatic
└── logs/
```

**Dlaczego dane są poza `Source/`:** `git clean -fdx`, reset gałęzi albo
nieostrożne `git checkout` nie mogą dotknąć bazy ani zdjęć, jeśli te
w ogóle nie leżą w repozytorium.

## Dlaczego nie `manage.py runserver`

Passenger **sam** jest serwerem aplikacji — importuje `passenger_wsgi.py`
i czyta z niego obiekt `application` (standard WSGI), analogicznie do tego,
jak w Dockerze robiłby to `gunicorn`. `runserver` to narzędzie
deweloperskie z własnym mechanizmem przeładowywania kodu
(`StatReloader`), który na hostingu współdzielonym z ograniczeniami
jail/sandboxu FreeBSD może nie mieć uprawnień do operacji, jakich
próbuje — stąd błąd `Operation not permitted` przy próbie uruchomienia.
To nie jest awaria aplikacji, tylko użycie złego narzędzia na tej
platformie.

## Procedura wdrożenia (pierwsze uruchomienie)

### 1. Katalog na dane

```bash
mkdir -p ~/domains/gdziestanik.lubian.net/data/photos
```

### 2. Plik `.env`

```bash
cp ~/domains/gdziestanik.lubian.net/Source/GdzieStanik/deploy/mydevil/.env.example \
   ~/domains/gdziestanik.lubian.net/data/.env
chmod 600 ~/domains/gdziestanik.lubian.net/data/.env
```

Wygeneruj `SECRET_KEY` i wklej do pliku:

```bash
python3.12 -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
```

Zostaw `HTTPS_CONFIRMED=0` na razie — patrz sekcja o weryfikacji HTTPS niżej.

### 3. `passenger_wsgi.py`

```bash
cp ~/domains/gdziestanik.lubian.net/Source/GdzieStanik/deploy/mydevil/passenger_wsgi.py \
   ~/domains/gdziestanik.lubian.net/public_python/passenger_wsgi.py
```

Jeśli struktura katalogów na Twoim koncie różni się od założonej
(`Source/GdzieStanik` obok `public_python/`), jedyna linia do poprawienia
to `PROJECT_DIR` w tym pliku.

### 4. Migracje i statyki

```bash
source ~/domains/gdziestanik.lubian.net/venv/gdzie_stanik_venv/bin/activate
cd ~/domains/gdziestanik.lubian.net/Source/GdzieStanik
export DJANGO_SETTINGS_MODULE=config.settings.mydevil

python manage.py migrate
python manage.py collectstatic --no-input
python manage.py createsuperuser
```

`DJANGO_SETTINGS_MODULE` ustawiony ręcznie w powłoce jest potrzebny
tylko do ręcznych komend — `passenger_wsgi.py` ustawia go sam przy
każdym żądaniu HTTP.

### 5. Uruchomienie (restart)

```bash
mkdir -p ~/domains/gdziestanik.lubian.net/public_python/tmp
touch ~/domains/gdziestanik.lubian.net/public_python/tmp/restart.txt
```

Passenger przeładowuje aplikację przy każdej zmianie czasu modyfikacji
tego pliku — ten sam `touch` służy do restartu po każdym kolejnym
wdrożeniu nowej wersji kodu.

### 6. Pierwsza weryfikacja

Wejdź na `https://gdziestanik.lubian.net/accounts/login/` i zaloguj się
kontem utworzonym w kroku 4.

## Weryfikacja HTTPS — krok krytyczny

`SESSION_COOKIE_SECURE` i `CSRF_COOKIE_SECURE` w `config/settings/mydevil.py`
są uzależnione od zmiennej `HTTPS_CONFIRMED`, bo nie wiadomo z góry,
jak dokładnie reverse proxy mydevil przekazuje Passengerowi informację
o oryginalnym protokole (nagłówek `X-Forwarded-Proto` albo coś innego).

**Zanim ustawisz `HTTPS_CONFIRMED=1`:**

1. Zaloguj się przez `https://gdziestanik.lubian.net/accounts/login/`
   z `HTTPS_CONFIRMED=0`.
2. Jeśli logowanie działa i strona po zalogowaniu pamięta sesję —
   w powłoce z aktywnym venv sprawdź wprost:

   ```bash
   python manage.py shell -c "
   from django.test import RequestFactory
   r = RequestFactory().get('/', secure=True)
   print(r.is_secure())
   "
   ```

   To tylko test syntetyczny — właściwa weryfikacja to realne żądanie.
   Dodaj tymczasowo do `inventory/views.py` w widoku `search`:

   ```python
   print("is_secure:", request.is_secure(), file=sys.stderr)
   ```

   i sprawdź w `logs/` po odświeżeniu strony przez HTTPS.
3. Jeśli `is_secure()` zwraca `True` — ustaw `HTTPS_CONFIRMED=1` w `.env`,
   `touch tmp/restart.txt`, usuń tymczasowy print.
4. Jeśli `False` — prawdopodobnie trzeba dodać do `mydevil.py`:

   ```python
   SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
   ```

   (to samo ustawienie co w `prod.py` dla wariantu Docker/Caddy) i
   powtórzyć test. Bez tego kroku `SESSION_COOKIE_SECURE=True`
   zablokowałoby logowanie — przeglądarka nie wysłałaby ciasteczka
   sesji, bo z punktu widzenia Django żądanie wyglądałoby jak HTTP.

## Kolejne wdrożenia (aktualizacja kodu)

```bash
cd ~/domains/gdziestanik.lubian.net/Source/GdzieStanik
git pull
source ~/domains/gdziestanik.lubian.net/venv/gdzie_stanik_venv/bin/activate
pip install -r requirements.txt   # gdy requirements.txt się zmienił
python manage.py migrate          # gdy są nowe migracje
python manage.py collectstatic --no-input   # gdy zmieniły się statyki
touch ~/domains/gdziestanik.lubian.net/public_python/tmp/restart.txt
```

## Backup

Baza i zdjęcia leżą w `~/domains/gdziestanik.lubian.net/data/` — backup
to kopia tego jednego katalogu. Harmonogram i automatyzacja (cron)
**celowo pominięte na razie** — do uzupełnienia przed przejściem
z danych testowych na realne użycie domowe.

## Rozwiązywanie problemów

### `Error: [Errno 1] Operation not permitted`

Użyto `manage.py runserver` zamiast wdrożenia przez Passenger. Na
mydevil ten komunikat jest nieszkodliwy i oczekiwany — po prostu nie
używaj `runserver` do weryfikacji, zamiast tego `touch restart.txt`
i sprawdzaj przez przeglądarkę.

### Strona pokazuje błąd 500 bez szczegółów

`DEBUG = False` w `config/settings/mydevil.py` celowo ukrywa szczegóły
błędu przed użytkownikiem. Sprawdź `~/domains/gdziestanik.lubian.net/logs/`.

### Statyki (CSS, HTMX) nie ładują się

`STATIC_ROOT` musi wskazywać dokładnie na katalog, który serwer
frontowy mydevil faktycznie serwuje (`public_python/public/static/`).
Po zmianie struktury katalogów uruchom `collectstatic` ponownie.

### Zalogowanie przekierowuje z powrotem na stronę logowania

Najczęstsza przyczyna: `SESSION_COOKIE_SECURE=True` (czyli
`HTTPS_CONFIRMED=1`) ustawione przed potwierdzeniem, że
`request.is_secure()` faktycznie zwraca `True`. Cofnij na `0`,
`touch restart.txt`, przejdź przez sekcję „Weryfikacja HTTPS” wyżej.

---

## Powiązane

- [`architecture.md`](architecture.md) §9 — wariant Docker/Raspberry Pi
- [`adr/0008-hosting-mydevil.md`](adr/0008-hosting-mydevil.md)
- [`deploy/mydevil/`](../deploy/mydevil/) — pliki do skopiowania na serwer
