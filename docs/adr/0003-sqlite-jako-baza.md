# ADR-0003: SQLite jako baza danych

- **Status:** zaakceptowany
- **Data:** 2026-10-14
- **Dotyczy:** przechowywanie danych, wdrożenie, backup

## Kontekst

Aplikacja działa na Raspberry Pi w sieci domowej. Korzysta z niej kilka osób,
sporadycznie — kilkadziesiąt odczytów i kilka zapisów dziennie. Docelowy
rozmiar danych to rzędu kilku tysięcy przedmiotów i kilkuset lokalizacji.

Wymagania wobec bazy:

- działa na ARM64 przy 1–2 GB RAM, bez zauważalnego narzutu,
- backup możliwie prosty, bez narzędzi specyficznych dla silnika,
- relacje i więzy integralności (model ma drzewa i klucze obce),
- obsługa kilku równoczesnych użytkowników.

## Rozważane warianty

### A. PostgreSQL

Pełnoprawny serwer, świetna współbieżność, bogate typy i wyszukiwanie
pełnotekstowe z obsługą języka polskiego.

Odrzucony: osobny kontener zjadający kilkaset MB RAM na Pi, backup wymaga
`pg_dump`, a cała przewaga we współbieżności jest bezużyteczna przy kilku
zapisach dziennie. Rozwiązanie nieproporcjonalne do problemu.

### B. Pliki JSON lub YAML

Czytelne dla człowieka, edytowalne ręcznie, backup przez skopiowanie pliku.

Odrzucony: brak więzów integralności i transakcji. Przy drzewach lokalizacji
i przedmiotów utrzymanie spójności spada na kod aplikacji. Wyszukiwanie
wymaga wczytania całości do pamięci, a równoczesne zapisy grożą utratą danych.

### C. SQLite w trybie WAL — **wybrany**

Plik bazy, zero procesów w tle, biblioteka w standardzie Pythona.

## Decyzja

SQLite z następującymi ustawieniami przy każdym połączeniu:

```sql
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;
PRAGMA synchronous = NORMAL;
```

Tryb WAL pozwala czytać podczas trwającego zapisu, co przy profilu
„dużo odczytów, mało zapisów” usuwa praktycznie całą kontencję.

`foreign_keys = ON` jest obowiązkowe — SQLite domyślnie **ignoruje** klucze
obce, więc bez tego wszystkie `REFERENCES` i `ON DELETE` w schemacie byłyby
jedynie dokumentacją.

## Konsekwencje

### Pozytywne

- Zero dodatkowych procesów i kontenerów na Pi.
- Backup to skopiowanie jednego pliku (`sqlite3 .backup`) plus katalogu zdjęć.
- Transakcje i więzy integralności dostępne od razu.
- Baza w standardowej bibliotece Pythona — brak sterowników do instalacji.
- Możliwość otwarcia pliku dowolnym narzędziem przy diagnostyce.

### Negatywne — przyjęte świadomie

- **Zapisy są serializowane.** Jednoczesny zapis dwóch osób oznacza, że jedna
  czeka. Przy domowej skali niezauważalne, ale to twarde ograniczenie.
- **Brak wyszukiwania pełnotekstowego z obsługą polskiego.** Stąd własna
  normalizacja tekstu (wymaganie W4) zamiast gotowego mechanizmu.
- **Słabe typowanie.** SQLite nie waliduje typów tak ostro jak Postgres —
  odpowiedzialność spada na SQLAlchemy i warstwę serwisów.
- **Ryzyko uszkodzenia przy nagłym zaniku zasilania.** Realne na Raspberry Pi.
  `synchronous = NORMAL` przy WAL jest kompromisem; backup pozostaje konieczny.
- **Jeden plik to pojedynczy punkt awarii.** Karta SD z bazą może paść —
  dlatego `/data` ląduje na dysku USB/SSD (ADR-0006).

### Kiedy wrócić do tej decyzji

- Liczba przedmiotów przekracza 50 000 i wyszukiwanie przestaje mieścić się
  w 300 ms (wymaganie W6) mimo indeksów i FTS5.
- Pojawia się potrzeba dostępu spoza domu dla wielu równoczesnych osób.
- Zapisy zaczynają się blokować w praktyce, nie tylko teoretycznie.

Migracja do PostgreSQL przy użyciu SQLAlchemy jest wykonalna — głównym
kosztem będą różnice w składni zapytań wyszukiwania.

## Powiązane

- `docs/architecture.md` §4.5 — konfiguracja PRAGMA
- ADR-0006 — rozmieszczenie danych na dysku zewnętrznym
