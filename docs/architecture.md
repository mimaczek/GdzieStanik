# GdzieStanik — architektura

> Status: **szkic do dyskusji** · Wersja dokumentu: 0.2 · Data: 2026-10-14
>
> Dokument opisuje **jak** realizujemy model opisany w `domain-model.md`.
> Uzasadnienia poszczególnych wyborów są w `adr/`.
>
> Zmiany w 0.2: framework zmieniony z FastAPI na Django (ADR-0007).
> Sesje, CSRF, formularze, migracje i zarządzanie strukturą domu przechodzą
> na mechanizmy wbudowane.

---

## 1. Stos technologiczny

| Warstwa | Wybór | Uzasadnienie |
|---|---|---|
| Język | Python 3.14 | jedyny w Ubuntu 26.04 |
| Framework | Django 6.0 | ADR-0007, jedyna linia dla Py 3.14 |
| Szablony | Django Templates | wbudowane |
| Interaktywność | HTMX | bez builda, bez Node |
| CSS | Pico.css lub własny | jeden plik, bez bundlera |
| ORM i migracje | Django ORM | wbudowane |
| Baza | SQLite w trybie WAL | ADR-0003 |
| Formularze | `django.forms` | walidacja, CSRF, komunikaty |
| Uwierzytelnianie | `django.contrib.auth` | sesje, hasła, logowanie |
| Hasła | Argon2 (`argon2-cffi`) | przez `PASSWORD_HASHERS` |
| Zarządzanie strukturą | `django.contrib.admin` | ADR-0007 |
| Obrazy | Pillow + `ImageField` | ADR-0006 |
| Serwer | Gunicorn | za reverse proxy |
| Proxy | Caddy | automatyczny HTTPS |
| Testy | pytest + `pytest-django` | |
| Jakość | ruff + mypy + `django-stubs` | |
| Uruchomienie | Docker Compose | Raspberry Pi, ARM64 |

**Zasada:** żadnej zależności od Node.js. HTMX i CSS to pliki statyczne
w repozytorium, nie pakiety npm. W projekcie nie ma `package.json`.

## 2. Warstwy

```
┌──────────────────────────────────────────────┐
│  Przeglądarka: HTML + HTMX                   │
└────────────────────┬─────────────────────────┘
                     │ HTTP, fragmenty HTML
┌────────────────────▼─────────────────────────┐
│  views.py + forms.py                         │  ← HTTP, formularze
├──────────────────────────────────────────────┤
│  admin.py            zarządzanie strukturą   │  ← rzadkie operacje
├──────────────────────────────────────────────┤
│  services/           logika domenowa         │  ← reguły L*, P*, N*, W*
├──────────────────────────────────────────────┤
│  models.py + managers.py                     │  ← schemat, QuerySety
└──────────────────────────────────────────────┘
```

**Reguły przepływu:**

- **A1.** Widoki nie zawierają logiki domenowej — odbierają żądanie,
  wołają serwis, wybierają szablon.
- **A2.** Warstwa `services/` nie wie nic o HTTP: żadnych `HttpRequest`,
  `HttpResponse` ani kodów statusu. Przyjmuje i zwraca obiekty domenowe,
  rzuca wyjątki domenowe.
- **A3.** Reguły biznesowe wymagające więcej niż jednego modelu zawsze
  w serwisie. Metody modeli tylko dla operacji lokalnych dla encji.
- **A4.** Walidacja w serwisie, nawet jeśli baza ma odpowiadające
  ograniczenie. Ograniczenia bazy to siatka bezpieczeństwa.
- **A5.** Panel administracyjny też wywołuje serwisy — przez nadpisane
  `save_model()` i `delete_model()`. Inaczej ominąłby reguły domenowe.

**Uwaga:** warstwa `services/` nie jest idiomatyczna dla Django, które
preferuje grube modele. Zachowujemy ją, bo reguł jest około trzydziestu
i rozsypanie ich po modelach utrudniłoby weryfikację. Wymaga to dyscypliny —
framework w tym nie pomoże (ADR-0007).

Reguła A5 jest nieoczywista i łatwa do przeoczenia: domyślnie admin zapisuje
obiekty bezpośrednio przez ORM, z pominięciem serwisów.

## 3. Struktura katalogów

```
gdziestanik/
├── docs/
├── config/                      projekt Django
│   ├── settings/
│   │   ├── base.py              wspólne
│   │   ├── dev.py
│   │   └── prod.py
│   ├── urls.py
│   └── wsgi.py
│
├── accounts/                    aplikacja: użytkownicy
│   ├── models.py                User na AbstractUser
│   ├── admin.py
│   └── migrations/
│
├── inventory/                   aplikacja: rdzeń domeny
│   ├── models.py                Location, Item, Tag
│   ├── managers.py              QuerySety: drzewo, wyszukiwanie
│   ├── admin.py                 zarządzanie strukturą domu
│   ├── forms.py                 formularze dodawania i edycji
│   ├── views.py                 wyszukiwanie, przeglądanie, dodawanie
│   ├── urls.py
│   ├── signals.py               wypełnianie name_norm przy zapisie
│   ├── exceptions.py            wyjątki domenowe
│   │
│   ├── services/
│   │   ├── location_service.py  reguły L1–L6
│   │   ├── item_service.py      reguły P1–P11
│   │   ├── naming_service.py    reguły N1–N5 (sufiksy)
│   │   ├── path_service.py      budowanie ścieżek, cache drzewa
│   │   ├── search_service.py    reguły W1–W7
│   │   └── photo_service.py     skalowanie zdjęć
│   │
│   ├── templatetags/
│   │   └── inventory_extras.py  filtr formatujący ścieżkę
│   │
│   ├── templates/inventory/
│   │   ├── base.html            layout, pole wyszukiwania
│   │   ├── partials/            fragmenty dla HTMX
│   │   │   ├── search_results.html
│   │   │   ├── tree_node.html
│   │   │   └── item_form.html
│   │   ├── search.html
│   │   ├── location_detail.html
│   │   └── item_detail.html
│   │
│   ├── migrations/
│   └── tests/
│       ├── test_rules/          po jednym teście na regułę
│       ├── test_services/
│       └── test_views/
│
├── static/
│   ├── htmx.min.js              w repozytorium, nie z CDN
│   └── style.css
│
├── manage.py
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
└── .env.example
```

## 4. Modele

### 4.1 `accounts.User`

```python
class User(AbstractUser):
    display_name = models.CharField(max_length=100)
```

Ustawiony jako `AUTH_USER_MODEL` **przed pierwszą migracją** — późniejsza
zmiana jest w Django bardzo kosztowna. Reguły U1–U5 realizuje w całości
`django.contrib.auth`: `is_active` zamiast usuwania, `createsuperuser`
zamiast własnego skryptu, Argon2 przez `PASSWORD_HASHERS`.

### 4.2 `inventory.Location`

```python
class Location(models.Model):
    name       = models.CharField(max_length=100)
    name_norm  = models.CharField(max_length=100, editable=False)
    parent     = models.ForeignKey("self", null=True, blank=True,
                                   on_delete=models.PROTECT,
                                   related_name="children")
    kind       = models.CharField(max_length=20, choices=Kind, blank=True)
    description = models.TextField(blank=True)
    photo      = models.ImageField(upload_to=photo_path, blank=True)
    sort_order = models.IntegerField(default=0)
    # created_at, updated_at, updated_by — z miksina

    class Meta:
        constraints = [
            # L2: unikalność nazwy wśród rodzeństwa
            models.UniqueConstraint(
                fields=["parent", "name_norm"],
                name="uq_location_sibling",
            ),
            # L6: unikalność nazw domów (parent IS NULL)
            models.UniqueConstraint(
                fields=["name_norm"],
                condition=Q(parent__isnull=True),
                name="uq_home_name",
            ),
        ]
```

Dwa osobne ograniczenia, bo SQLite traktuje każdy `NULL` jako wartość
różną — pierwsze nie zadziałałoby dla korzeni. Django rozwiązuje to
ograniczeniem warunkowym, czystszym niż `COALESCE` w surowym SQL-u.

### 4.3 `inventory.Item`

```python
class Item(models.Model):
    name        = models.CharField(max_length=200)
    name_norm   = models.CharField(max_length=200, editable=False)
    description = models.TextField(blank=True)
    quantity    = models.PositiveIntegerField(default=1)
    location    = models.ForeignKey(Location, null=True, blank=True,
                                    on_delete=models.PROTECT,
                                    related_name="items")
    parent_item = models.ForeignKey("self", null=True, blank=True,
                                    on_delete=models.CASCADE,
                                    related_name="contents")
    home        = models.ForeignKey(Location, on_delete=models.CASCADE,
                                    related_name="+", editable=False)
    owner       = models.ForeignKey(User, null=True, blank=True,
                                    on_delete=models.SET_NULL)
    photo       = models.ImageField(upload_to=photo_path, blank=True)
    tags        = models.ManyToManyField(Tag, related_name="items")

    class Meta:
        constraints = [
            # P1: dokładnie jeden rodzic
            models.CheckConstraint(
                condition=(
                    Q(location__isnull=False, parent_item__isnull=True) |
                    Q(location__isnull=True,  parent_item__isnull=False)
                ),
                name="ck_item_single_parent",
            ),
            # P3: ilość dodatnia
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="ck_item_quantity_positive",
            ),
            # N1: unikalność nazwy w obrębie domu
            models.UniqueConstraint(
                fields=["home", "name_norm"],
                name="uq_item_home_name",
            ),
        ]
        indexes = [models.Index(fields=["name_norm"])]
```

`on_delete=CASCADE` przy `parent_item` realizuje regułę P5, ale działa
po cichu. Serwis **musi** wcześniej policzyć zawartość i pokazać
potwierdzenie — ORM jest tu zabezpieczeniem przed osieroconymi wierszami,
nie mechanizmem interfejsu.

`home` jest zdenormalizowane (reguła P7), wypełniane w serwisie przy
zapisie i aktualizowane kaskadowo przy przenosinach.

### 4.4 `inventory.Tag`

```python
class Tag(models.Model):
    name      = models.CharField(max_length=50)
    name_norm = models.CharField(max_length=50, unique=True, editable=False)
```

Relacje `ManyToMany` z `Item` i `Location` realizują regułę T4 —
wspólna pula tagów dla obu typów.

### 4.5 Konfiguracja SQLite

Django nie ustawia trybu WAL samo. Potrzebny sygnał przy nawiązaniu
połączenia:

```python
@receiver(connection_created)
def configure_sqlite(sender, connection, **kwargs):
    if connection.vendor == "sqlite":
        cursor = connection.cursor()
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA synchronous = NORMAL")
        cursor.execute("PRAGMA busy_timeout = 5000")
```

Klucze obce Django włącza samo (inaczej niż przy surowym SQLite),
ale `CheckConstraint` wymaga SQLite 3.37+ dla pełnej obsługi.

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

Wypełnianie `name_norm` w `pre_save` (`signals.py`), nie w kodzie
wywołującym — inaczej któreś miejsce na pewno o tym zapomni. Dotyczy to
również zapisów z panelu administracyjnego.

### 5.2 Budowanie ścieżki

Dwie pętle w górę (najpierw przedmioty po `parent_item`, potem lokalizacje
po `parent`) z cache'owanym drzewem lokalizacji:

```
PathService
├── _tree: dict[int, LocationNode]   całe drzewo, ładowane raz
├── invalidate()                     po każdej zmianie lokalizacji
├── path_for_location(id) -> list[str]
└── path_for_item(item)   -> list[str]
```

Przy 50–200 lokalizacjach na dom cache zajmuje kilkadziesiąt kilobajtów.
Unieważnianie całości przy każdej zmianie wystarcza — zmiany struktury są
rzadkie w porównaniu z odczytami.

### 5.3 Wykrywanie cykli (L1, P6)

Przed zmianą rodzica: wejście w górę od nowego rodzica z licznikiem kroków.
Napotkanie przenoszonego węzła to błąd walidacji. Licznik chroni przed
zapętleniem na danych już uszkodzonych.

### 5.4 Nadawanie sufiksów (N2, N3)

```
NamingService.suggest_name(home, "młotek") -> "młotek_4"
```

Znajduje największy użyty sufiks dla rdzenia w obrębie domu i zwraca
kolejny. Nie szuka luk (N3 — licznik się nie cofa).

Serwis **tylko proponuje**. Zapis następuje po zatwierdzeniu przez
użytkownika — nazwa nigdy nie zmienia się cicho.

### 5.5 Wyszukiwanie

QuerySet łączący przedmioty, tagi i lokalizacje, z adnotacją rangi
realizującą regułę W5:

| Dopasowanie | Ranga |
|---|---|
| nazwa przedmiotu od początku | 1 |
| fragment nazwy przedmiotu | 2 |
| nazwa tagu | 3 |
| nazwa lokalizacji | 4 |
| opis przedmiotu | 5 |

Przy wymaganiu W6 (poniżej 300 ms dla 5000 przedmiotów na Raspberry Pi)
indeks na `name_norm` z `startswith` i `contains` powinien wystarczyć.
Jeśli nie — FTS5 przez surowe zapytanie, ale dopiero po pomiarze.

Kluczowe: `select_related` i `prefetch_related` przy pobieraniu wyników,
inaczej budowanie ścieżek wygeneruje lawinę zapytań.

### 5.6 Obsługa zdjęć

```
upload → walidacja typu i rozmiaru (max 20 MB)
       → Pillow: EXIF-transpose, resize do 1600 px, WebP
       → miniatura 300 px
       → zapis pod UUID w MEDIA_ROOT/photos/{rok}/{miesiąc}/
       → w bazie ścieżka przez ImageField
```

Przetwarzanie w `PhotoService`, wywoływane przed zapisem modelu.
Oryginał nie jest zachowywany (G4), metadane EXIF usuwane poza orientacją.

`MEDIA_ROOT` wskazuje na `/data/photos`, czyli wolumen z dysku USB/SSD,
nie z karty SD (ADR-0006).

## 6. Panel administracyjny

Pokrywa operacje wykonywane rzadko i przy komputerze:

| Obszar | Zakres |
|---|---|
| Lokalizacje | tworzenie struktury domu, edycja drzewa, zdjęcia pojemników |
| Użytkownicy | zakładanie kont, dezaktywacja, zmiana haseł |
| Tagi | porządkowanie, scalanie |
| Przedmioty | edycja masowa, przeglądanie tabelaryczne |

Konfiguracja: `list_filter` po domu i lokalizacji, `search_fields`
po `name_norm`, `raw_id_fields` dla relacji (inaczej listy rozwijane
z tysiącami pozycji), `list_select_related` przeciw zapytaniom N+1.

**Reguła A5 jest tu krytyczna** — `save_model()` i `delete_model()` muszą
wywoływać serwisy, inaczej admin ominie walidację cykli, nadawanie
sufiksów i aktualizację `home`.

Panel jest nieużyteczny na telefonie — dlatego wyszukiwanie i szybkie
dodawanie rzeczy mają własne widoki.

## 7. Własne widoki

Tylko tam, gdzie wygoda ma znaczenie:

| Widok | Ścieżka | Rola |
|---|---|---|
| Wyszukiwanie | `/` | **trasa krytyczna** — pole, wyniki na żywo przez HTMX, pełne ścieżki |
| Szczegóły przedmiotu | `/item/<id>/` | zdjęcie, ścieżka, zawartość jeśli pojemnik |
| Szybkie dodanie | `/add/` | minimum pól, aparat, wybór lokalizacji |
| Przeglądanie drzewa | `/location/<id>/` | rozwijane węzły przez HTMX |
| Przeniesienie | `/item/<id>/move/` | zmiana rodzica z obsługą kolizji nazw (N5) |

Wszystkie wymagają zalogowania (`LoginRequiredMiddleware`).

## 8. Bezpieczeństwo

| Zagadnienie | Realizacja |
|---|---|
| Hasła | Argon2id — pierwszy w `PASSWORD_HASHERS` |
| Sesje | `django.contrib.sessions`, `HttpOnly`, `SameSite=Lax` |
| CSRF | `CsrfViewMiddleware`, token w `{% csrf_token %}` |
| CSRF w HTMX | `hx-headers` na `<body>` z `X-CSRFToken` |
| Dostęp | `LoginRequiredMiddleware` globalnie |
| Upload | walidacja typu, limit rozmiaru, ponowne kodowanie przez Pillow |
| SQL injection | ORM, zero surowych zapytań z interpolacją |
| XSS | autoescape w szablonach, `\|safe` zabronione |
| HTTPS | Caddy; `SECURE_*` i `SESSION_COOKIE_SECURE` w `prod.py` |

Wszystko poza obsługą uploadu to konfiguracja, nie kod — na tym polegała
zmiana frameworka (ADR-0007).

Dopóki HTTPS nie działa, ciasteczko sesyjne leci otwartym tekstem —
świadomie przyjęte ryzyko ograniczone do sieci lokalnej.

## 9. Wdrożenie

> **Rzeczywiste pierwsze wdrożenie poszło inną drogą** — hosting
> współdzielony mydevil.net (FreeBSD, Phusion Passenger) zamiast
> Raspberry Pi. Uzasadnienie w [ADR-0008](adr/0008-hosting-mydevil.md),
> pełna procedura w [`docs/wdrozenie-mydevil.md`](wdrozenie-mydevil.md).
> Poniższy plan Docker/Raspberry Pi pozostaje udokumentowaną opcją
> alternatywną, `config/settings/prod.py` nie został usunięty.

```yaml
services:
  app:
    build: .
    command: gunicorn config.wsgi --bind 0.0.0.0:8000 --workers 2
    environment:
      - DJANGO_SETTINGS_MODULE=config.settings.prod
      - SECRET_KEY=${SECRET_KEY}
      - DATABASE_PATH=/data/gdziestanik.db
      - MEDIA_ROOT=/data/photos
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

**Uwagi dla Raspberry Pi:**

- obraz `python:3.14-slim` dla ARM64,
- Pillow i `argon2-cffi` mają gotowe pakiety ARM64 — brak kompilacji,
- **dwa procesy Gunicorna** ze względu na cache ścieżek (§5.2) —
  przy większej liczbie trzeba unieważniać go międzyprocesowo (pytanie A2),
- `collectstatic` przy budowaniu obrazu, pliki statyczne przez WhiteNoise,
- backup: `sqlite3 .backup` plus `rsync` zdjęć, codziennie przez cron.

## 10. Strategia testów

| Poziom | Zakres | Priorytet |
|---|---|---|
| Reguły domenowe | po jednym teście na L1–L6, P1–P11, N1–N5, T1–T4 | najwyższy |
| Serwisy | ścieżki, cykle, sufiksy, wyszukiwanie | wysoki |
| Widoki | formularze, przekierowania, dostęp bez logowania | średni |
| Admin | czy `save_model` wywołuje serwisy (reguła A5) | wysoki |
| Wydajność | W6: 5000 przedmiotów, pomiar czasu | przed wydaniem |

Nazwa testu zawiera identyfikator reguły (`test_p1_dokladnie_jeden_rodzic`),
dzięki czemu widać wprost, które reguły są sprawdzane.

Test dla A5 jest nieoczywisty, a bez niego łatwo o sytuację, w której
aplikacja pilnuje reguł, a admin je omija.

## 11. Kolejność implementacji

1. **Szkielet** — projekt, ustawienia, PRAGMA dla SQLite
2. **`accounts`** — własny model User **przed pierwszą migracją**
3. **Modele `inventory`** — ograniczenia, indeksy, migracje
4. **Normalizacja** — funkcja, sygnały, testy
5. **Serwisy** — ścieżki, cykle, sufiksy
6. **Admin** — zarządzanie strukturą, reguła A5
7. **Wyszukiwanie** — trasa krytyczna, pełne ścieżki
8. **Dodawanie i przenoszenie** — formularze, HTMX
9. **Zdjęcia** — upload, skalowanie
10. **Docker i wdrożenie** — ARM64, Caddy, backup

Po kroku 7 aplikacja odpowiada na pytanie „gdzie jest X?”, a strukturę domu
można wprowadzać przez panel administracyjny.

Krok 2 jest nieodwracalny — zmiana `AUTH_USER_MODEL` po pierwszej migracji
wymaga ręcznego przepisywania danych.

## 12. Pytania otwarte

| # | Pytanie | Kontekst |
|---|---|---|
| **A1** | `kind` jako `choices` czy wolny tekst? | `choices` nie wymaga migracji przy zmianie — wartości są w kodzie |
| **A2** | Cache ścieżek przy wielu procesach Gunicorna | Przy dwóch procesach cache może się rozjechać. Opcje: jeden proces, cache w Django cache framework, albo unieważnianie przez sygnał |
| **A3** | Serwować zdjęcia przez Caddy zamiast Django? | Szybsze, ale omija kontrolę dostępu |

---

## Powiązane dokumenty

- [`vision.md`](vision.md) — problem i zakres
- [`domain-model.md`](domain-model.md) — encje i reguły realizowane przez ten schemat
- [`adr/0007-django-zamiast-fastapi.md`](adr/0007-django-zamiast-fastapi.md) — wybór frameworka
- [`adr/`](adr/) — pozostałe decyzje
