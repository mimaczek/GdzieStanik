# GdzieStanik — architektura

> Status: **szkic do dyskusji** · Wersja dokumentu: 0.1 · Data: 2026-10-14
>
> Dokument opisuje **jak** realizujemy model opisany w `domain-model.md`.
> Uzasadnienia poszczególnych wyborów są w `adr/`.

---

## 1. Stos technologiczny

| Warstwa | Wybór | Uzasadnienie |
|---|---|---|
| Język | Python 3.12+ | ADR-0004 |
| Framework HTTP | FastAPI | ADR-0004 |
| Szablony | Jinja2 | renderowanie po stronie serwera |
| Interaktywność | HTMX | bez builda, bez Node (ADR-0004) |
| CSS | Pico.css lub własny | brak bundlera, jeden plik |
| ORM | SQLAlchemy 2.x | styl deklaratywny, typowanie |
| Migracje | Alembic | standard dla SQLAlchemy |
| Baza | SQLite w trybie WAL | ADR-0003 |
| Walidacja | Pydantic v2 | formularze i konfiguracja |
| Hasła | Argon2 (`argon2-cffi`) | ADR-0005 |
| Sesje | ciasteczko `HttpOnly` + tabela sesji | ADR-0005 |
| Obrazy | Pillow | skalowanie przy uploadzie (ADR-0006) |
| Serwer | Uvicorn | za reverse proxy |
| Proxy | Caddy | automatyczny HTTPS, prosty config |
| Testy | pytest + httpx | testy warstwy serwisów i tras |
| Jakość | ruff + mypy | lint, format i typowanie |
| Uruchomienie | Docker Compose | Raspberry Pi, ARM64 |

**Zasada:** żadnej zależności od Node.js. HTMX i CSS to pliki statyczne
dołączone do repozytorium, nie pakiety npm.

## 2. Warstwy

```
┌──────────────────────────────────────────────┐
│  Przeglądarka: HTML + HTMX                   │
└────────────────────┬─────────────────────────┘
                     │ HTTP, fragmenty HTML
┌────────────────────▼─────────────────────────┐
│  web/      trasy FastAPI, szablony Jinja     │  ← HTTP, formularze, sesja
├──────────────────────────────────────────────┤
│  services/ logika domenowa                   │  ← reguły L*, P*, N*, T*, U*
├──────────────────────────────────────────────┤
│  repositories/  dostęp do danych             │  ← zapytania SQLAlchemy
├──────────────────────────────────────────────┤
│  models/   encje SQLAlchemy                  │  ← schemat bazy
└──────────────────────────────────────────────┘
```

**Reguły przepływu:**

- **A1.** Warstwa `web/` nie zawiera logiki domenowej — tylko odbiór żądania,
  wywołanie serwisu i wybór szablonu.
- **A2.** Warstwa `services/` nie wie nic o HTTP: żadnych `Request`,
  `Response` ani kodów statusu. Przyjmuje i zwraca obiekty domenowe,
  rzuca wyjątki domenowe.
- **A3.** Zapytania do bazy wyłącznie w `repositories/`. Serwis nie buduje
  SQL-a ani nie używa `session.query` bezpośrednio.
- **A4.** Walidacja reguł biznesowych zawsze w serwisie, nawet jeśli baza
  ma odpowiadające ograniczenie. Ograniczenia w bazie to siatka
  bezpieczeństwa, nie główny mechanizm.

Uzasadnienie A2: to warunek taniego dołożenia JSON API w przyszłości —
nowa warstwa `api/` wywoła te same serwisy.

## 3. Struktura katalogów

```
gdziestanik/
├── docs/                        dokumentacja projektu
├── src/gdziestanik/
│   ├── main.py                  tworzenie aplikacji, montowanie tras
│   ├── config.py                ustawienia z env (Pydantic Settings)
│   ├── database.py              silnik, sesja, PRAGMA dla SQLite
│   │
│   ├── models/                  encje SQLAlchemy
│   │   ├── base.py              klasa bazowa + miksin znaczników czasu
│   │   ├── location.py          Lokalizacja
│   │   ├── item.py              Przedmiot
│   │   ├── tag.py               Tag + tabele łączące
│   │   └── user.py              Użytkownik, Sesja
│   │
│   ├── repositories/            dostęp do danych
│   │   ├── location_repo.py
│   │   ├── item_repo.py
│   │   └── search_repo.py       zapytania wyszukiwania
│   │
│   ├── services/                logika domenowa
│   │   ├── location_service.py  reguły L1–L6
│   │   ├── item_service.py      reguły P1–P11
│   │   ├── naming_service.py    reguły N1–N5 (sufiksy)
│   │   ├── path_service.py      budowanie ścieżek, cache drzewa
│   │   ├── search_service.py    reguły W1–W7
│   │   ├── photo_service.py     skalowanie i zapis zdjęć
│   │   └── auth_service.py      logowanie, sesje, hasła
│   │
│   ├── web/                     warstwa HTTP
│   │   ├── deps.py              zależności: sesja DB, bieżący użytkownik
│   │   ├── forms.py             modele Pydantic dla formularzy
│   │   ├── csrf.py              generowanie i walidacja tokenu
│   │   ├── errors.py            mapowanie wyjątków domenowych na HTTP
│   │   └── routes/
│   │       ├── auth.py          logowanie, wylogowanie
│   │       ├── search.py        wyszukiwanie (trasa krytyczna)
│   │       ├── locations.py     drzewo i lokalizacje
│   │       ├── items.py         przedmioty
│   │       └── photos.py        serwowanie zdjęć
│   │
│   ├── templates/
│   │   ├── base.html            layout, nagłówek, pole wyszukiwania
│   │   ├── partials/            fragmenty zwracane przez HTMX
│   │   │   ├── search_results.html
│   │   │   ├── tree_node.html
│   │   │   └── item_form.html
│   │   ├── search.html
│   │   ├── location.html
│   │   └── item.html
│   │
│   └── static/
│       ├── htmx.min.js          dołączony do repo, nie z CDN
│       ├── style.css
│       └── icons/
│
├── migrations/                  Alembic
├── tests/
│   ├── conftest.py
│   ├── test_services/           testy logiki domenowej (większość)
│   ├── test_web/                testy tras
│   └── test_rules/              po jednym teście na regułę L*, P*, N*
│
├── scripts/
│   ├── create_user.py           zakładanie konta (reguła U1)
│   └── backup.sh                kopia bazy i zdjęć
│
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── .env.example
```

## 4. Schemat bazy danych

### 4.1 `locations`

```sql
CREATE TABLE locations (
    id            INTEGER PRIMARY KEY,
    name          TEXT    NOT NULL,
    name_norm     TEXT    NOT NULL,          -- bez diakrytyków, małe litery
    parent_id     INTEGER REFERENCES locations(id) ON DELETE RESTRICT,
    kind          TEXT,                       -- dom|pokój|mebel|półka|...
    description   TEXT,
    photo_path    TEXT,
    sort_order    INTEGER NOT NULL DEFAULT 0,
    created_at    TEXT    NOT NULL,
    updated_at    TEXT    NOT NULL,
    updated_by_id INTEGER REFERENCES users(id) ON DELETE SET NULL
);

-- L2: unikalność nazwy wśród rodzeństwa
CREATE UNIQUE INDEX ux_loc_sibling
    ON locations(COALESCE(parent_id, -1), name_norm);

CREATE INDEX ix_loc_parent ON locations(parent_id);
```

Reguła L6 (unikalność nazw domów) wynika z `ux_loc_sibling`: wszystkie
korzenie mają `parent_id IS NULL`, więc są rodzeństwem. Stąd `COALESCE`,
bo SQLite traktuje `NULL` jako wartości różne w indeksie unikalnym.

### 4.2 `items`

```sql
CREATE TABLE items (
    id             INTEGER PRIMARY KEY,
    name           TEXT    NOT NULL,
    name_norm      TEXT    NOT NULL,
    description    TEXT,
    quantity       INTEGER NOT NULL DEFAULT 1,
    location_id    INTEGER REFERENCES locations(id) ON DELETE RESTRICT,
    parent_item_id INTEGER REFERENCES items(id)     ON DELETE CASCADE,
    home_id        INTEGER NOT NULL REFERENCES locations(id),
    owner_id       INTEGER REFERENCES users(id)     ON DELETE SET NULL,
    photo_path     TEXT,
    created_at     TEXT    NOT NULL,
    updated_at     TEXT    NOT NULL,
    updated_by_id  INTEGER REFERENCES users(id)     ON DELETE SET NULL,

    -- P1: dokładnie jeden rodzic
    CONSTRAINT ck_single_parent CHECK (
        (location_id IS NOT NULL AND parent_item_id IS NULL) OR
        (location_id IS NULL     AND parent_item_id IS NOT NULL)
    ),
    -- P3: ilość dodatnia
    CONSTRAINT ck_quantity_positive CHECK (quantity > 0)
);

-- N1: unikalność nazwy w obrębie domu
CREATE UNIQUE INDEX ux_item_home_name ON items(home_id, name_norm);

CREATE INDEX ix_item_location ON items(location_id);
CREATE INDEX ix_item_parent   ON items(parent_item_id);
CREATE INDEX ix_item_name     ON items(name_norm);
```

Uwaga do `ON DELETE CASCADE` przy `parent_item_id`: realizuje regułę P5,
ale kaskada w bazie działa po cichu. Serwis **musi** wcześniej policzyć
zawartość i pokazać potwierdzenie — baza jest tu zabezpieczeniem przed
osieroconymi wierszami, nie mechanizmem interfejsu.

### 4.3 `tags` i tabele łączące

```sql
CREATE TABLE tags (
    id        INTEGER PRIMARY KEY,
    name      TEXT NOT NULL,
    name_norm TEXT NOT NULL UNIQUE
);

CREATE TABLE item_tags (
    item_id INTEGER NOT NULL REFERENCES items(id) ON DELETE CASCADE,
    tag_id  INTEGER NOT NULL REFERENCES tags(id)  ON DELETE CASCADE,
    PRIMARY KEY (item_id, tag_id)
);

CREATE TABLE location_tags (
    location_id INTEGER NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    tag_id      INTEGER NOT NULL REFERENCES tags(id)      ON DELETE CASCADE,
    PRIMARY KEY (location_id, tag_id)
);
```

Reguła T4 (wspólna pula tagów) jest tu realizowana przez dwie tabele
łączące wskazujące jedną tabelę `tags`.

### 4.4 `users` i `sessions`

```sql
CREATE TABLE users (
    id            INTEGER PRIMARY KEY,
    login         TEXT    NOT NULL UNIQUE,
    display_name  TEXT    NOT NULL,
    password_hash TEXT    NOT NULL,
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT    NOT NULL
);

CREATE TABLE sessions (
    token      TEXT PRIMARY KEY,         -- losowy, 32 bajty, base64url
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    user_agent TEXT
);

CREATE INDEX ix_sessions_expires ON sessions(expires_at);
```

Sesje w tabeli, nie w podpisanym ciasteczku — pozwala unieważnić sesję
natychmiast po wylogowaniu lub zmianie hasła (ADR-0005).

### 4.5 Konfiguracja SQLite

Przy każdym połączeniu:

```sql
PRAGMA journal_mode = WAL;      -- równoległy odczyt podczas zapisu
PRAGMA foreign_keys = ON;       -- w SQLite domyślnie wyłączone
PRAGMA busy_timeout = 5000;     -- czekaj na blokadę zapisu
PRAGMA synchronous = NORMAL;    -- wystarczające przy WAL
```

`foreign_keys = ON` jest krytyczne — bez tego wszystkie `REFERENCES`
i `ON DELETE` powyżej są martwym zapisem.

## 5. Mechanizmy kluczowe

### 5.1 Normalizacja tekstu

Jedna funkcja obsługuje wyszukiwanie (W4) i unikalność nazw (N1, G5):

```python
def normalize(text: str) -> str:
    """'Młotek Gumowy ' -> 'mlotek gumowy'"""
    nfkd = unicodedata.normalize("NFKD", text.strip().casefold())
    without_marks = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", without_marks.replace("ł", "l"))
```

Polskie `ł` wymaga osobnej obsługi — nie jest literą z diakrytykiem
w rozumieniu Unicode, więc dekompozycja NFKD go nie rozkłada.

Kolumny `name_norm` wypełniane są w zdarzeniach SQLAlchemy przy zapisie,
nie w kodzie wywołującym — inaczej któreś miejsce na pewno o tym zapomni.

### 5.2 Budowanie ścieżki

Dwie pętle w górę (najpierw przedmioty, potem lokalizacje) z cache'owanym
drzewem lokalizacji w pamięci:

```
PathService
├── _tree: dict[int, LocationNode]   całe drzewo, ładowane raz
├── invalidate()                     po każdej zmianie lokalizacji
├── path_for_location(id) -> list[str]
└── path_for_item(item)   -> list[str]
        wchodzi po parent_item_id (zwykle 0–3 kroki),
        potem korzysta z cache dla części lokalizacyjnej
```

Przy 50–200 lokalizacjach na dom cache zajmuje kilkadziesiąt kilobajtów.
Unieważnienie całości przy każdej zmianie jest wystarczające — zmiany
struktury są rzadkie w porównaniu z odczytami.

### 5.3 Wykrywanie cykli (L1, P6)

Przed zmianą rodzica: wejście w górę od nowego rodzica z licznikiem kroków.
Jeśli po drodze napotkamy przenoszony węzeł — błąd walidacji. Licznik chroni
przed zapętleniem na danych już uszkodzonych.

### 5.4 Nadawanie sufiksów (N2, N3)

```
NamingService.suggest_name(home_id, "młotek") -> "młotek_4"
```

Znajduje największy użyty sufiks dla danego rdzenia w obrębie domu
i zwraca kolejny. Nie szuka luk (N3 — licznik nie cofa się).

Serwis **tylko proponuje**. Zapis następuje dopiero po zatwierdzeniu przez
użytkownika — nazwa nigdy nie zmienia się cicho.

### 5.5 Wyszukiwanie

Jedno zapytanie `UNION ALL` po przedmiotach, tagach i lokalizacjach,
z kolumną rangi realizującą regułę W5:

| Dopasowanie | Ranga |
|---|---|
| nazwa przedmiotu od początku | 1 |
| fragment nazwy przedmiotu | 2 |
| nazwa tagu | 3 |
| nazwa lokalizacji | 4 |
| opis przedmiotu | 5 |

Przy wymaganiu W6 (poniżej 300 ms dla 5000 przedmiotów na Raspberry Pi)
indeks na `name_norm` plus `LIKE 'fraza%'` powinien wystarczyć. Jeśli nie —
FTS5 jako następny krok, ale dopiero po pomiarze.

### 5.6 Obsługa zdjęć

```
upload → walidacja typu (JPEG/PNG/WebP, max 20 MB)
       → Pillow: EXIF-transpose, resize do 1600 px, konwersja na WebP
       → miniatura 300 px
       → zapis pod UUID w /data/photos/{rok}/{miesiąc}/
       → w bazie tylko ścieżka względna
```

Oryginał nie jest zachowywany (G4). Katalog `/data` to wolumen Dockera
montowany z **dysku USB/SSD, nie z karty SD** (ADR-0006).

## 6. Bezpieczeństwo

| Zagadnienie | Realizacja |
|---|---|
| Hasła | Argon2id, domyślne parametry `argon2-cffi` |
| Sesja | token 32 bajty z `secrets.token_urlsafe`, ciasteczko `HttpOnly`, `SameSite=Lax`, `Secure` przy HTTPS |
| Czas życia sesji | 30 dni, przedłużana przy aktywności |
| CSRF | token w sesji, ukryte pole w każdym formularzu, walidacja dla POST/PUT/DELETE |
| Ochrona przed zgadywaniem haseł | opóźnienie i limit prób logowania na konto |
| Upload plików | biała lista typów, limit rozmiaru, nazwa z UUID, ponowne kodowanie przez Pillow |
| SQL injection | wyłącznie zapytania parametryzowane przez SQLAlchemy |
| XSS | autoescape Jinja2 włączony, `|safe` zabronione w szablonach |

HTMX wymaga przekazywania tokenu CSRF w żądaniach — rozwiązane przez
atrybut `hx-headers` na elemencie `<body>` w `base.html`.

## 7. Wdrożenie

```yaml
# docker-compose.yml (szkic)
services:
  app:
    build: .
    environment:
      - DATABASE_PATH=/data/gdziestanik.db
      - PHOTOS_PATH=/data/photos
      - SECRET_KEY=${SECRET_KEY}
    volumes:
      - /mnt/ssd/gdziestanik:/data      # dysk USB, nie karta SD
    restart: unless-stopped

  caddy:
    image: caddy:alpine
    ports: ["80:80", "443:443"]
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
    restart: unless-stopped
```

**Wymagania dla Raspberry Pi:**

- obraz bazowy `python:3.12-slim` dla ARM64,
- Pillow ma gotowe pakiety dla ARM64 — brak kompilacji przy instalacji,
- cały katalog `/data` na dysku zewnętrznym (baza i zdjęcia),
- backup: `sqlite3 .backup` plus `rsync` katalogu zdjęć, codziennie przez cron.

## 8. Strategia testów

| Poziom | Zakres | Priorytet |
|---|---|---|
| Reguły domenowe | po jednym teście na L1–L6, P1–P11, N1–N5, T1–T4, U1–U5 | najwyższy |
| Serwisy | ścieżki, cykle, sufiksy, wyszukiwanie | wysoki |
| Trasy HTTP | formularze, przekierowania, CSRF, autoryzacja | średni |
| Wydajność | W6: 5000 przedmiotów, pomiar czasu wyszukiwania | przed wydaniem |

Każda reguła z `domain-model.md` ma odpowiadający test o nazwie zawierającej
jej identyfikator (`test_p1_dokladnie_jeden_rodzic`). Dzięki temu widać
wprost, czy reguła jest sprawdzana.

## 9. Kolejność implementacji

1. **Szkielet** — projekt, konfiguracja, połączenie z bazą, PRAGMA
2. **Modele i migracje** — wszystkie tabele, ograniczenia, indeksy
3. **Normalizacja** — funkcja i zdarzenia SQLAlchemy, testy
4. **Uwierzytelnianie** — użytkownicy, sesje, CSRF, logowanie
5. **Lokalizacje** — CRUD, drzewo, cykle, cache ścieżek
6. **Przedmioty** — CRUD, dwaj rodzice, sufiksy nazw
7. **Wyszukiwanie** — trasa krytyczna, pełne ścieżki w wynikach
8. **Zdjęcia** — upload, skalowanie, serwowanie
9. **Dopracowanie UI** — HTMX, wygoda na telefonie
10. **Docker i wdrożenie** — obraz ARM64, Caddy, backup

Punkty 1–7 dają działającą aplikację odpowiadającą na pytanie „gdzie jest X?”.

## 10. Pytania otwarte

| # | Pytanie | Kontekst |
|---|---|---|
| **A1** | Czy `kind` lokalizacji to enum w bazie, czy wolny tekst? | Enum jest czystszy, ale każde nowe pojęcie wymaga migracji |
| **A2** | Cache ścieżek przy wielu procesach Uvicorn? | Przy jednym procesie problemu nie ma; przy kilku trzeba unieważniać międzyprocesowo |
| **A3** | Czy serwować zdjęcia przez Caddy zamiast aplikacji? | Szybsze, ale omija kontrolę dostępu |

---

## Powiązane dokumenty

- [`vision.md`](vision.md) — problem i zakres
- [`domain-model.md`](domain-model.md) — encje i reguły realizowane przez ten schemat
- [`adr/`](adr/) — uzasadnienia wyborów technicznych
