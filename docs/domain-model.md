# GdzieStanik — model domeny

> Status: **szkic do dyskusji** · Wersja dokumentu: 0.1 · Data: 2026-10-14
>
> Dokument opisuje **co** przechowujemy i **jakie reguły** obowiązują.
> Szczegóły techniczne (warstwy, biblioteki, wdrożenie) są w `architecture.md`.

---

## 1. Słownik pojęć

| Pojęcie | Znaczenie |
|---|---|
| **Lokalizacja** | Dowolne miejsce, w którym może leżeć rzecz: pokój, mebel, półka, szuflada, pudełko. Może zawierać inne lokalizacje |
| **Przedmiot** | Rzecz przechowywana w domu, przypisana do dokładnie jednej lokalizacji |
| **Ścieżka** | Pełna droga od korzenia do lokalizacji, np. `Piwnica › Regał › Pudełko 7` |
| **Tag** | Swobodna etykieta grupująca przedmioty niezależnie od miejsca, np. `zimowe`, `narzędzia` |
| **Użytkownik** | Domownik posiadający konto; może być właścicielem przedmiotów |
| **Korzeń** | Lokalizacja bez rodzica — najwyższy poziom (zwykle pokój lub budynek) |

## 2. Diagram encji

```
┌─────────────┐
│ Użytkownik  │
└──────┬──────┘
       │ jest właścicielem (0..n)
       │
       ▼
┌─────────────┐  n..n   ┌──────┐
│  Przedmiot  │◄───────►│ Tag  │
└──────┬──────┘         └──────┘
       │ leży w (1)
       ▼
┌─────────────┐
│ Lokalizacja │──┐ zawiera (0..n)
└─────────────┘◄─┘  (relacja do samej siebie)
```

## 3. Encje

### 3.1 Lokalizacja

Encja centralna. **Jeden typ dla wszystkich poziomów** — pokój, szafa, półka
i pudełko to ta sama encja różniąca się tylko miejscem w drzewie i opcjonalnym
rodzajem. Uzasadnienie w ADR-0002.

| Pole | Typ | Wymagane | Opis |
|---|---|---|---|
| `id` | int | tak | Klucz główny |
| `nazwa` | str(100) | tak | Np. „Szuflada 2”, „Szafa w sypialni” |
| `rodzic_id` | int / NULL | nie | `NULL` oznacza korzeń |
| `rodzaj` | enum / NULL | nie | Podpowiedź wizualna: `budynek`, `pokój`, `mebel`, `półka`, `szuflada`, `pojemnik`, `inne` |
| `opis` | text | nie | Np. „ta wysoka przy oknie” |
| `kolejnosc` | int | nie | Ręczne sortowanie wśród rodzeństwa |
| `created_at` | datetime | tak | Automatyczne |
| `updated_at` | datetime | tak | Automatyczne |
| `updated_by_id` | int | nie | Kto ostatnio zmienił |

**Reguły:**

- **L1.** Lokalizacja nie może być swoim przodkiem — cykle są zabronione
  (sprawdzane przy zmianie rodzica).
- **L2.** Nazwa musi być unikalna **wśród rodzeństwa**. W różnych szafach
  może być „Szuflada 2”.
- **L3.** Usunięcie lokalizacji zawierającej cokolwiek wymaga wyboru:
  przenieś zawartość do rodzica albo usuń kaskadowo (z potwierdzeniem).
- **L4.** Głębokość drzewa nie jest ograniczona technicznie, ale interfejs
  ostrzega powyżej 6 poziomów — to zwykle sygnał błędu w strukturze.
- **L5.** `rodzaj` jest wyłącznie informacyjny — nie ogranicza zagnieżdżania.
  Pudełko może stać w pudełku.

### 3.2 Przedmiot

| Pole | Typ | Wymagane | Opis |
|---|---|---|---|
| `id` | int | tak | Klucz główny |
| `nazwa` | str(200) | tak | Jedyne pole wymagane od użytkownika |
| `opis` | text | nie | Szczegóły, model, stan |
| `ilosc` | int | tak | Domyślnie `1` |
| `lokalizacja_id` | int | tak | Gdzie leży |
| `wlasciciel_id` | int | nie | `NULL` = rzecz wspólna |
| `zdjecie_sciezka` | str / NULL | nie | Ścieżka względna do pliku |
| `created_at` | datetime | tak | Automatyczne |
| `updated_at` | datetime | tak | Automatyczne |
| `updated_by_id` | int | nie | Kto ostatnio zmienił |

**Reguły:**

- **P1.** Przedmiot leży **w dokładnie jednej** lokalizacji. Nigdy w zerowej,
  nigdy w dwóch.
- **P2.** Jedyne pole wymagane przy dodawaniu to `nazwa` (plus lokalizacja
  z kontekstu). Wszystko inne jest opcjonalne — patrz zasada „niskiego tarcia”.
- **P3.** `ilosc` musi być większa od zera. Zużycie rzeczy to jej usunięcie,
  a nie ustawienie zera.
- **P4.** Usunięcie użytkownika nie usuwa jego przedmiotów — `wlasciciel_id`
  staje się `NULL`.
- **P5.** Usunięcie przedmiotu usuwa też plik zdjęcia.

**Pytanie otwarte:** czy jeden przedmiot może mieć kilka zdjęć? Na razie
zakładam jedno (patrz §7).

### 3.3 Tag

| Pole | Typ | Wymagane | Opis |
|---|---|---|---|
| `id` | int | tak | Klucz główny |
| `nazwa` | str(50) | tak | Unikalna globalnie, zapisywana małymi literami |

**Reguły:**

- **T1.** Nazwa tagu jest normalizowana: przycięte spacje, małe litery.
  `Zimowe` i `zimowe ` to ten sam tag.
- **T2.** Tagi tworzą się automatycznie przy wpisywaniu — brak osobnego
  ekranu zarządzania w v1.
- **T3.** Tag bez żadnego przedmiotu jest usuwany automatycznie.
- **T4.** Tagi należą do przedmiotów, nie do lokalizacji.

### 3.4 Użytkownik

| Pole | Typ | Wymagane | Opis |
|---|---|---|---|
| `id` | int | tak | Klucz główny |
| `login` | str(50) | tak | Unikalny |
| `nazwa_wyswietlana` | str(100) | tak | Np. „Michał” |
| `hash_hasla` | str | tak | Argon2 lub bcrypt — nigdy jawne hasło |
| `aktywny` | bool | tak | Dezaktywacja zamiast usuwania |
| `created_at` | datetime | tak | Automatyczne |

**Reguły:**

- **U1.** Brak publicznej rejestracji. Konta zakłada istniejący użytkownik
  albo polecenie CLI.
- **U2.** W v1 wszyscy zalogowani mają identyczne uprawnienia — brak ról.
- **U3.** Musi istnieć co najmniej jedno aktywne konto; ostatniego nie można
  dezaktywować.
- **U4.** Hasło nigdy nie jest przechowywane ani logowane w postaci jawnej.

## 4. Wyszukiwanie — rdzeń aplikacji

To najważniejsza funkcja, więc jej zachowanie opisujemy precyzyjnie.

**Wejście:** jeden ciąg tekstowy wpisany przez użytkownika.

**Przeszukiwane pola:**

1. `Przedmiot.nazwa` — waga najwyższa
2. `Przedmiot.opis`
3. `Tag.nazwa`
4. `Lokalizacja.nazwa` — pozwala znaleźć „co jest w pudełku 7”

**Wymagania:**

- **W1.** Każdy wynik zawiera **pełną ścieżkę** od korzenia, nie samą
  lokalizację bezpośrednią.
- **W2.** Dopasowanie częściowe: „ładow” znajduje „ładowarka”.
- **W3.** Ignorowanie wielkości liter.
- **W4.** Ignorowanie polskich znaków diakrytycznych w obie strony:
  „zarowka” znajduje „żarówka” i odwrotnie. **To wymaganie twarde** —
  nikt nie wpisuje ogonków na telefonie w pośpiechu.
- **W5.** Wyniki posortowane według trafności: najpierw dopasowanie nazwy
  od początku, potem fragment nazwy, potem tagi, na końcu opis.
- **W6.** Czas odpowiedzi poniżej 300 ms na Raspberry Pi przy 5000 przedmiotów.

**Uwaga techniczna:** wymaganie W4 wyklucza naiwne `LIKE` na SQLite. Potrzebna
jest kolumna z nazwą znormalizowaną (bez diakrytyków, małe litery) wypełniana
przy zapisie, albo FTS5 z własnym tokenizerem. Decyzja w osobnym ADR.

## 5. Obliczanie ścieżki

Ścieżka `Piwnica › Regał › Pudełko 7` powstaje przez wejście po `rodzic_id`
aż do korzenia.

Problem: przy liście 50 wyników to 50 × głębokość zapytań do bazy
(N+1). Rozważane podejścia:

| Podejście | Zalety | Wady |
|---|---|---|
| Rekurencyjne CTE | Jedno zapytanie, zawsze aktualne | Składnia SQL mniej czytelna |
| Cache ścieżki w kolumnie | Odczyt natychmiastowy | Trzeba przeliczyć całe poddrzewo przy przenosinach |
| Wczytanie całego drzewa do pamięci | Bardzo proste, drzewo jest małe (~100 węzłów) | Nie skaluje się, ale przy domu skalować się nie musi |

**Propozycja dla v1:** wczytanie całego drzewa lokalizacji do pamięci przy
starcie i trzymanie go w cache z unieważnianiem przy zmianie. Dom ma
realistycznie 50–200 lokalizacji — to kilkadziesiąt kilobajtów.

## 6. Reguły globalne

- **G1.** Każda modyfikacja ustawia `updated_at` i `updated_by_id`.
- **G2.** Usunięcia są trwałe — brak kosza w v1.
- **G3.** Wszystkie znaczniki czasu w UTC, konwersja do czasu lokalnego
  dopiero przy wyświetlaniu.
- **G4.** Zdjęcia skalowane przy uploadzie do maks. 1600 px dłuższego boku
  plus miniatura 300 px. Oryginał nie jest zachowywany (ADR-0005).

## 7. Pytania otwarte

| # | Pytanie | Wstępna propozycja |
|---|---|---|
| **Q1** | Kilka zdjęć na przedmiot? | Jedno w v1 — prościej, wystarczy do identyfikacji |
| **Q2** | Czy lokalizacja może mieć zdjęcie? | Tak byłoby przydatne („to pudełko”), ale odkładamy na v1.1 |
| **Q3** | Przedmiot jako pojemnik — „plecak z rzeczami w środku”? | Nie. Jeśli coś zawiera rzeczy, jest lokalizacją, nie przedmiotem |
| **Q4** | Ilość a osobne egzemplarze — 3 młotki w różnych miejscach? | Trzy osobne przedmioty. `ilosc` dotyczy rzeczy w jednym miejscu |
| **Q5** | Czy potrzebny jest tag na lokalizacji? | Nie w v1 |
| **Q6** | Co przy przeniesieniu lokalizacji pod jej własne dziecko? | Błąd walidacji (reguła L1) |

## 8. Przykładowe dane

```
Dom
├── Parter
│   ├── Salon
│   │   └── Komoda
│   │       ├── Szuflada górna
│   │       │   • dokumenty samochodowe (1, tagi: dokumenty)
│   │       │   • ładowarka USB-C (2, tagi: elektronika)
│   │       └── Szuflada dolna
│   │           • obrusy (4, właściciel: Anna)
│   └── Kuchnia
│       └── Szafka pod zlewem
│           • worki na śmieci 60l (1 rolka, tagi: chemia)
├── Piętro
│   └── Sypialnia
│       └── Szafa
│           └── Półka górna
│               └── Pudełko „Zima”
│                   • czapki (3, tagi: zimowe, ubrania)
│                   • rękawiczki (2 pary, tagi: zimowe, ubrania)
└── Piwnica
    └── Regał metalowy
        └── Pudełko „Elektronarzędzia”
            • wiertarka Bosch (1, właściciel: Michał, tagi: narzędzia)
            • ładowarka do wiertarki (1, tagi: narzędzia, elektronika)
```

Wyszukanie `ladowarka` (bez ogonków, małe litery) zwraca:

```
ładowarka USB-C              → Dom › Parter › Salon › Komoda › Szuflada górna
ładowarka do wiertarki       → Dom › Piwnica › Regał metalowy › Pudełko „Elektronarzędzia”
```

---

## Powiązane dokumenty

- [`vision.md`](vision.md) — problem, użytkownicy, zakres
- [`architecture.md`](architecture.md) — realizacja techniczna *(do napisania)*
