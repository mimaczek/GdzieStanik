# GdzieStanik — model domeny

> Status: **uzgodniony szkic** · Wersja dokumentu: 0.2 · Data: 2026-10-14
>
> Dokument opisuje **co** przechowujemy i **jakie reguły** obowiązują.
> Szczegóły techniczne (warstwy, biblioteki, wdrożenie) są w `architecture.md`.
>
> Zmiany w 0.2: rozstrzygnięto pytania Q1–Q6. Przedmiot może zawierać inne
> przedmioty (ADR-0001), nazwy przedmiotów są unikalne w obrębie domu
> (ADR-0002), obsługa wielu domów wchodzi do v1.

---

## 1. Słownik pojęć

| Pojęcie | Znaczenie |
|---|---|
| **Lokalizacja** | Dowolne miejsce, w którym może leżeć rzecz: pokój, mebel, półka, szuflada, pudełko. Może zawierać inne lokalizacje |
| **Przedmiot** | Rzecz przechowywana w domu. Leży w lokalizacji albo wewnątrz innego przedmiotu. Sam też może zawierać przedmioty |
| **Dom** | Lokalizacja będąca korzeniem drzewa (`rodzic_id = NULL`). Osobna nieruchomość: mieszkanie, domek letniskowy, garaż wolnostojący |
| **Ścieżka** | Pełna droga od domu do rzeczy, np. `Piwnica › Regał › Pudełko 7` |
| **Tag** | Swobodna etykieta grupująca przedmioty lub lokalizacje niezależnie od miejsca w drzewie |
| **Użytkownik** | Domownik posiadający konto; może być właścicielem przedmiotów. Widzi wszystkie domy |
| **Kontener** | Dowolny byt mogący coś zawierać — lokalizacja albo przedmiot |

## 2. Diagram encji

```
┌─────────────┐
│ Użytkownik  │
└──────┬──────┘
       │ jest właścicielem (0..n)
       ▼
┌─────────────┐  n..n   ┌──────┐
│  Przedmiot  │◄───────►│ Tag  │
└──┬───────┬──┘         └───┬──┘
   │       │                │ n..n
   │       └── zawiera (0..n)│  (relacja do samej siebie,
   │           ▲─────────────┘   przez parent_item_id)
   │ leży w (0..1)
   ▼
┌─────────────┐
│ Lokalizacja │──┐ zawiera (0..n)
└─────────────┘◄─┘  (relacja do samej siebie, przez rodzic_id)
```

Przedmiot ma **dokładnie jednego rodzica**: albo lokalizację, albo inny
przedmiot. Nigdy obu naraz i nigdy żadnego.

## 3. Encje

### 3.1 Lokalizacja

**Jeden typ dla wszystkich poziomów** — dom, pokój, szafa, półka i pudełko to
ta sama encja, różniąca się tylko miejscem w drzewie i opcjonalnym rodzajem.

| Pole | Typ | Wymagane | Opis |
|---|---|---|---|
| `id` | int | tak | Klucz główny |
| `nazwa` | str(100) | tak | Np. „Szuflada 2”, „Szafa w sypialni” |
| `rodzic_id` | int / NULL | nie | `NULL` oznacza dom (korzeń drzewa) |
| `rodzaj` | enum / NULL | nie | Podpowiedź wizualna: `dom`, `pokój`, `mebel`, `półka`, `szuflada`, `pojemnik`, `inne` |
| `opis` | text | nie | Np. „ta wysoka przy oknie” |
| `zdjecie_sciezka` | str / NULL | nie | Zdjęcie pojemnika — ułatwia rozpoznanie (Q2) |
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
- **L6.** Lokalizacja bez rodzica jest **domem**. Nazwy domów muszą być
  unikalne globalnie.

### 3.2 Przedmiot

| Pole | Typ | Wymagane | Opis |
|---|---|---|---|
| `id` | int | tak | Klucz główny |
| `nazwa` | str(200) | tak | Unikalna w obrębie domu (ADR-0002) |
| `opis` | text | nie | Szczegóły, model, stan |
| `ilosc` | int | tak | Domyślnie `1`. Sztuki w tym jednym miejscu |
| `lokalizacja_id` | int / NULL | warunkowo | Gdzie leży — gdy rodzicem jest lokalizacja |
| `parent_item_id` | int / NULL | warunkowo | W którym przedmiocie leży (ADR-0001) |
| `dom_id` | int | tak | Denormalizacja: korzeń drzewa. Potrzebny do walidacji unikalności |
| `wlasciciel_id` | int / NULL | nie | `NULL` = rzecz wspólna |
| `zdjecie_sciezka` | str / NULL | nie | Jedno zdjęcie w v1 (Q1) |
| `created_at` | datetime | tak | Automatyczne |
| `updated_at` | datetime | tak | Automatyczne |
| `updated_by_id` | int | nie | Kto ostatnio zmienił |

**Reguły:**

- **P1.** Przedmiot ma **dokładnie jednego rodzica**: albo `lokalizacja_id`,
  albo `parent_item_id`. Dokładnie jedno z tych pól jest wypełnione —
  wymuszane ograniczeniem `CHECK` na poziomie bazy.
- **P2.** Jedyne pole wymagane od użytkownika to `nazwa`; rodzic wynika
  z kontekstu. Wszystko inne jest opcjonalne — zasada „niskiego tarcia”.
- **P3.** `ilosc` musi być większa od zera. Zużycie rzeczy to jej usunięcie,
  a nie ustawienie zera.
- **P4.** Usunięcie użytkownika nie usuwa jego przedmiotów — `wlasciciel_id`
  staje się `NULL`.
- **P5.** Usunięcie przedmiotu usuwa plik zdjęcia oraz **kaskadowo wszystkie
  przedmioty w jego wnętrzu** (z potwierdzeniem pokazującym ich liczbę).
- **P6.** Przedmiot nie może być swoim przodkiem — cykle po `parent_item_id`
  są zabronione, analogicznie do L1 (Q6).
- **P7.** `dom_id` jest wyliczany automatycznie przy zapisie i aktualizowany
  kaskadowo dla całego poddrzewa przy przenosinach.
- **P8.** Przeniesienie przedmiotu zawierającego inne przedmioty przenosi
  całą zawartość.

#### Unikalność nazw (ADR-0002)

- **N1.** Nazwa przedmiotu jest unikalna **w obrębie jednego domu**.
  Porównanie po postaci znormalizowanej: małe litery, bez diakrytyków,
  przycięte spacje. „Młotek” i „mlotek” to kolizja.
- **N2.** Przy kolizji system **proponuje** nazwę z sufiksem `_2`, `_3`
  i czeka na zatwierdzenie. Użytkownik może wpisać własną, np.
  „młotek gumowy”. Nazwa nigdy nie zmienia się cicho.
- **N3.** Licznik sufiksów **nigdy nie cofa się**. Po usunięciu `młotek_2`
  kolejny nowy dostaje `młotek_4`, nie `młotek_2`. Luki w numeracji są
  akceptowane — chodzi o to, by nazwa nie wskazywała kiedyś innej rzeczy.
- **N4.** Ręczna zmiana nazwy podlega tej samej walidacji; przy kolizji
  użytkownik znów dostaje propozycję sufiksu.
- **N5.** Przeniesienie przedmiotu do domu, gdzie nazwa jest zajęta,
  wywołuje tę samą propozycję — przenosiny nie są blokowane.

### 3.3 Tag

| Pole | Typ | Wymagane | Opis |
|---|---|---|---|
| `id` | int | tak | Klucz główny |
| `nazwa` | str(50) | tak | Unikalna globalnie, zapisywana małymi literami |

**Reguły:**

- **T1.** Nazwa jest normalizowana: przycięte spacje, małe litery.
  `Zimowe` i `zimowe ` to ten sam tag.
- **T2.** Tagi tworzą się automatycznie przy wpisywaniu — brak osobnego
  ekranu zarządzania w v1.
- **T3.** Tag bez żadnego powiązania jest usuwany automatycznie.
- **T4.** Tagi mogą być przypisane **zarówno do przedmiotów, jak i do
  lokalizacji** (Q5). Pula tagów jest wspólna.

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
- **U5.** Każdy użytkownik widzi **wszystkie domy** — brak uprawnień
  per nieruchomość.

## 4. Wyszukiwanie — rdzeń aplikacji

To najważniejsza funkcja, więc jej zachowanie opisujemy precyzyjnie.

**Wejście:** jeden ciąg tekstowy wpisany przez użytkownika.

**Przeszukiwane pola:**

1. `Przedmiot.nazwa` — waga najwyższa
2. `Przedmiot.opis`
3. `Tag.nazwa`
4. `Lokalizacja.nazwa` — pozwala znaleźć „co jest w pudełku 7”

**Wymagania:**

- **W1.** Każdy wynik zawiera **pełną ścieżkę** od domu, nie samego
  bezpośredniego rodzica.
- **W2.** Dopasowanie częściowe: „ładow” znajduje „ładowarka”.
- **W3.** Ignorowanie wielkości liter.
- **W4.** Ignorowanie polskich znaków diakrytycznych w obie strony:
  „zarowka” znajduje „żarówka” i odwrotnie. **Wymaganie twarde** —
  nikt nie wpisuje ogonków na telefonie w pośpiechu.
- **W5.** Wyniki posortowane według trafności: najpierw dopasowanie nazwy
  od początku, potem fragment nazwy, potem tagi, na końcu opis.
- **W6.** Czas odpowiedzi poniżej 300 ms na Raspberry Pi przy 5000 przedmiotów.
- **W7.** Wyszukiwanie obejmuje **wszystkie domy**; wynik pokazuje, z którego
  domu pochodzi. Opcjonalny filtr zawęża do jednego.

**Uwaga techniczna:** wymaganie W4 wyklucza naiwne `LIKE` na SQLite. Potrzebna
jest kolumna z nazwą znormalizowaną (bez diakrytyków, małe litery) wypełniana
przy zapisie — ta sama, która służy do walidacji unikalności (N1).

## 5. Obliczanie ścieżki

Ścieżka powstaje przez wejście w górę po dwóch relacjach: najpierw
`parent_item_id` (dopóki rodzicem jest przedmiot), potem `rodzic_id`
aż do domu.

Przykład: `Dom › Sypialnia › Szafa › Walizka › Kosmetyczka › szczoteczka`,
gdzie `Walizka` i `Kosmetyczka` to przedmioty, nie lokalizacje.

Problem: przy liście 50 wyników to 50 × głębokość zapytań (N+1).

**Rozwiązanie dla v1:** całe drzewo lokalizacji wczytywane do pamięci przy
starcie i trzymane w cache z unieważnianiem przy zmianie. Realistycznie
50–200 lokalizacji na dom, czyli kilkadziesiąt kilobajtów. Przedmioty-
pojemniki doliczane zapytaniem rekurencyjnym tylko dla faktycznych wyników.

## 6. Reguły globalne

- **G1.** Każda modyfikacja ustawia `updated_at` i `updated_by_id`.
- **G2.** Usunięcia są trwałe — brak kosza w v1.
- **G3.** Wszystkie znaczniki czasu w UTC, konwersja do czasu lokalnego
  dopiero przy wyświetlaniu.
- **G4.** Zdjęcia skalowane przy uploadzie do maks. 1600 px dłuższego boku
  plus miniatura 300 px. Oryginał nie jest zachowywany (ADR-0005).
- **G5.** Nazwy przedmiotów, lokalizacji i tagów mają kolumnę
  znormalizowaną — służy równocześnie wyszukiwaniu (W4) i unikalności (N1).

## 7. Rozstrzygnięte pytania

| # | Pytanie | Decyzja |
|---|---|---|
| **Q1** | Kilka zdjęć na przedmiot? | **Jedno w v1.** Wystarcza do rozpoznania; galeria to osobna funkcja |
| **Q2** | Czy lokalizacja może mieć zdjęcie? | **Tak, w v1.** Mechanizm uploadu i tak powstaje; zdjęcie pudełka bardzo pomaga przy szukaniu |
| **Q3** | Przedmiot jako pojemnik? | **Tak** — pole `parent_item_id`. Walizka z rzeczami pozostaje przedmiotem (ADR-0001) |
| **Q4** | Powtarzające się nazwy przedmiotów? | **Nazwy unikalne w obrębie domu**, przy kolizji proponowany sufiks `_2` do zatwierdzenia (ADR-0002) |
| **Q5** | Tagi na lokalizacjach? | **Tak**, wspólna pula tagów dla przedmiotów i lokalizacji |
| **Q6** | Cykle przy przenoszeniu? | **Błąd walidacji** dla obu drzew — reguły L1 i P6 |

## 8. Pytania nadal otwarte

| # | Pytanie | Kontekst |
|---|---|---|
| **Q7** | Czy pusty przedmiot-pojemnik różni się czymś od zwykłego przedmiotu? | Propozycja: nie. Dowolny przedmiot przyjmuje zawartość, bez flagi |
| **Q8** | Limit zagnieżdżenia przedmiotów? | Dla lokalizacji ostrzegamy przy 6 poziomach (L4). Dla przedmiotów chyba 3 wystarczą |
| **Q9** | Czy przenieść przedmiot „do korzenia domu” bez wskazania pokoju? | Technicznie możliwe (dom to lokalizacja), ale może prowadzić do bałaganu |

## 9. Przykładowe dane

```
Dom (korzeń)
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
│       └── Szafa                       [tag: strefa-zimowa]
│           └── Półka górna
│               └── Pudełko „Zima”      [zdjęcie: pudelko-zima.jpg]
│                   • czapki (3, tagi: zimowe, ubrania)
│                   • walizka kabinowa (1)        ← przedmiot-pojemnik
│                     • kosmetyczka (1)           ← pojemnik w pojemniku
│                       • szczoteczka podróżna (1)
│                     • adapter gniazdek (1, tagi: elektronika)
└── Piwnica
    └── Regał metalowy
        └── Pudełko „Elektronarzędzia”
            • wiertarka Bosch (1, właściciel: Michał, tagi: narzędzia)
            • ładowarka do wiertarki (1, tagi: narzędzia, elektronika)

Domek letniskowy (osobny korzeń)
└── Garaż
    └── Skrzynka narzędziowa
        • młotek (1, tagi: narzędzia)   ← nazwa wolna: inny dom
```

Wyszukanie `ladowarka` (bez ogonków, małe litery) zwraca:

```
ładowarka USB-C           → Dom › Parter › Salon › Komoda › Szuflada górna
ładowarka do wiertarki    → Dom › Piwnica › Regał metalowy › Pudełko „Elektronarzędzia”
```

Wyszukanie `szczoteczka` pokazuje ścieżkę przez przedmioty-pojemniki:

```
szczoteczka podróżna → Dom › Piętro › Sypialnia › Szafa › Półka górna ›
                       Pudełko „Zima” › walizka kabinowa › kosmetyczka
```

---

## Powiązane dokumenty

- [`vision.md`](vision.md) — problem, użytkownicy, zakres
- [`adr/0001-przedmiot-jako-pojemnik.md`](adr/0001-przedmiot-jako-pojemnik.md)
- [`adr/0002-unikalnosc-nazw-przedmiotow.md`](adr/0002-unikalnosc-nazw-przedmiotow.md)
- [`architecture.md`](architecture.md) — realizacja techniczna *(do napisania)*
