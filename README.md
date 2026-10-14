# GdzieStanik

Domowy katalog rzeczy, który odpowiada na jedno pytanie:

> **Gdzie jest X?** → `Sypialnia › Szafa › Szuflada 2`

Wpisujesz nazwę rzeczy, dostajesz pełną ścieżkę do miejsca, w którym leży.
Wszystko inne w tej aplikacji istnieje po to, żeby ta odpowiedź była możliwa
i aktualna.

> **Status: planowanie.** Dokumentacja jest gotowa, kodu jeszcze nie ma.

## Co potrafi (zakres wersji 1.0)

- **Wyszukiwanie z pełną ścieżką** — działa też bez polskich znaków:
  `zarowka` znajdzie `żarówkę`
- **Dowolnie głęboka struktura** — dom → piętro → pokój → szafa → półka →
  pudełko, bez sztywnych poziomów
- **Przedmioty-pojemniki** — spakowana walizka pozostaje rzeczą, a mimo to
  widać, co jest w środku
- **Wiele nieruchomości** — mieszkanie, domek letniskowy, garaż
- **Zdjęcia** — przedmiotów i pojemników, skalowane przy wgrywaniu
- **Tagi** — `zimowe`, `narzędzia`, `dokumenty`
- **Właściciel rzeczy** — „czyj jest ten rower?”
- **Konta domowników** — wspólna baza dla całej rodziny

Aplikacja jest projektowana **pod telefon** — główny moment użycia to
porządki, na stojąco, przy szafie.

## Czego nie ma i nie będzie w v1

JSON API, dziennika zmian, historii przenosin, kodów kreskowych, dat
ważności, dostępu spoza domu. Uzasadnienia w `docs/vision.md` §6.

## Stos

| | |
|---|---|
| Backend | Python 3.12, Django 5.x |
| Frontend | szablony Django + HTMX — **bez Node.js i bez procesu budowania** |
| Baza | SQLite w trybie WAL |
| Wdrożenie | Docker Compose na Raspberry Pi, w sieci domowej |

Strukturą domu i kontami zarządza panel administracyjny Django. Własne
widoki obsługują to, co musi być wygodne na telefonie: wyszukiwanie
i szybkie dodawanie rzeczy.

Wybory uzasadnione w `docs/adr/`.

## Dokumentacja

| Dokument | Zawartość |
|---|---|
| [`docs/vision.md`](docs/vision.md) | Problem, scenariusze użycia, zakres, ryzyka |
| [`docs/domain-model.md`](docs/domain-model.md) | Encje i reguły biznesowe |
| [`docs/architecture.md`](docs/architecture.md) | Warstwy, struktura kodu, schemat bazy |
| [`docs/adr/`](docs/adr/) | Decyzje architektoniczne z uzasadnieniami |

Czytając po raz pierwszy: `vision.md` → `domain-model.md` → `architecture.md`.

## Uruchomienie

> Dostępne po implementacji.

```bash
cp .env.example .env                              # ustaw SECRET_KEY
docker compose up -d
docker compose exec app python manage.py migrate
docker compose exec app python manage.py createsuperuser
```

Aplikacja nasłuchuje na porcie 8000, zwykle za reverse proxy Caddy.
Panel administracyjny pod `/admin/`.

## Dane i backup

Wszystkie dane w jednym katalogu, na dysku USB/SSD (nie na karcie SD):

```
/mnt/ssd/gdziestanik/
├── gdziestanik.db      baza SQLite
└── photos/             zdjęcia
```

Backup to skopiowanie tych dwóch rzeczy. Bez eksportów, bez chmury,
bez uzależnienia od zewnętrznych usług.

## Nazwa

Żartobliwe nawiązanie do klasycznego domowego pytania „gdzie jest…?”.
Robocza, może się zmienić przed wydaniem.

## Licencja

Projekt prywatny, do użytku własnego.
