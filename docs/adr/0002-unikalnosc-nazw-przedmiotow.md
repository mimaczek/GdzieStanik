# ADR-0002: Nazwy przedmiotów unikalne w obrębie domu

- **Status:** zaakceptowany
- **Data:** 2026-10-14
- **Dotyczy:** model domeny, walidacja, interfejs dodawania rzeczy

## Kontekst

Dom zawiera wiele egzemplarzy tej samej rzeczy w różnych miejscach: młotek
w garażu i drugi w piwnicy, ładowarka USB-C w kilku pokojach, zapasowe żarówki
w trzech szafkach.

Przy swobodnych nazwach lista wyników wyszukiwania „młotek” pokazuje kilka
identycznie nazwanych pozycji. Rozróżnia je wyłącznie ścieżka wyświetlana obok.

Pytanie brzmiało, czy to akceptowalne, czy nazwy mają być wymuszenie unikalne.

## Rozważane warianty

### A. Nazwy mogą się powtarzać, rozróżnia je ścieżka

Model pozostaje czysty: dwa młotki to dwa wpisy o nazwie „młotek”, każdy
w swojej lokalizacji. Interfejs zawsze pokazuje nazwę razem ze ścieżką.

Argumenty za: dane nie są modyfikowane przez system, wyszukiwanie zwraca
dokładnie to, co użytkownik wpisał, brak efektów ubocznych przy usuwaniu.

Odrzucony decyzją właściciela projektu — preferencja za jednoznaczną
identyfikacją rzeczy po samej nazwie.

### B. Ostrzeżenie bez wymuszania

Przy dodawaniu komunikat „podobna rzecz jest już w: Garaż › Regał”, ale nazwa
może się powtórzyć.

Odrzucony: nie daje gwarancji jednoznaczności, a dokłada krok do procesu.

### C. Unikalność globalna w całej bazie

Jedna nazwa „młotek” w całym systemie, niezależnie od nieruchomości.

Odrzucony: przy kilku domach prowadziłby do absurdu — młotek w domku
letniskowym dostawałby sufiks tylko dlatego, że w mieszkaniu też jest młotek.

### D. Unikalność w obrębie domu z proponowanym sufiksem — **wybrany**

Nazwa unikalna w granicach jednej nieruchomości. Przy kolizji system proponuje
sufiks, użytkownik zatwierdza lub wpisuje własną nazwę.

## Decyzja

Nazwa przedmiotu jest unikalna w obrębie domu (korzenia drzewa lokalizacji),
według reguł N1–N5 w `domain-model.md`:

1. Porównanie po postaci **znormalizowanej** — małe litery, bez diakrytyków,
   przycięte spacje. „Młotek”, „mlotek” i „MŁOTEK " to kolizja.
2. Przy kolizji system **proponuje** `nazwa_2`, `nazwa_3` i czeka na decyzję.
   Nazwa nigdy nie zmienia się bez wiedzy użytkownika.
3. Użytkownik może zamiast sufiksu wpisać nazwę opisową („młotek gumowy”) —
   i to jest zachowanie preferowane, promowane treścią komunikatu.
4. Licznik sufiksów nigdy się nie cofa. Po usunięciu `młotek_2` kolejny nowy
   dostaje `młotek_4`.
5. Ręczna zmiana nazwy i przeniesienie do innego domu podlegają tej samej
   walidacji.

Kolumna znormalizowana obsługuje równocześnie tę walidację i wyszukiwanie
bez diakrytyków (wymaganie W4) — jeden mechanizm, dwa zastosowania.

## Konsekwencje

### Pozytywne

- Nazwa jednoznacznie identyfikuje rzecz w obrębie domu.
- Normalizacja wyłapuje kolizje mimo różnic w ogonkach i wielkości liter.
- Propozycja zamiast cichej zmiany daje szansę na nazwę opisową, lepszą
  niż numer.
- Kolumna znormalizowana przydaje się ponownie przy wyszukiwaniu.

### Negatywne — przyjęte świadomie

- **Sufiks opisuje system, nie rzecz.** `młotek_2` nie mówi nic o młotku.
  Dwie rzeczy różniące się realnie (ślusarski i gumowy) dostają nazwy
  różniące się cyfrą.
- **Luki w numeracji.** Po usunięciach powstaje ciąg `młotek`, `młotek_3`,
  `młotek_7`. Wygląda na błąd, choć jest celowe (N3).
- **Dodatkowy krok przy dodawaniu.** Zderza się z zasadą „niskiego tarcia”
  z `vision.md` §9.3 — dodanie drugiej takiej samej rzeczy wymaga decyzji.
- **Walidacja wymaga znajomości domu.** Stąd zdenormalizowane `dom_id`
  (ADR-0001), które trzeba utrzymywać przy przenosinach.
- **Przenosiny między domami mogą wymusić zmianę nazwy** — operacja
  pozornie niezwiązana z nazewnictwem nagle o nie pyta (N5).
- **Ryzyko zaśmiecenia wyników.** Użytkownik szukający „młotek” zobaczy
  `młotek_4` i może nie wiedzieć, czy to inny model, czy artefakt systemu.

### Kiedy wrócić do tej decyzji

Sygnały, że wariant A był lepszy:

- baza zapełnia się wpisami `_2`, `_3` zamiast nazw opisowych,
- użytkownicy wahają się przy dodawaniu rzeczy, bo nie wiedzą, jaką nazwę nadać,
- sufiksy pojawiają się w wynikach wyszukiwania i wprowadzają w błąd.

Odwrót jest tani: wystarczy zdjąć ograniczenie unikalności. Istniejące sufiksy
pozostaną w danych jako ślad po tej decyzji.

## Powiązane

- `docs/domain-model.md` §3.2 — reguły N1–N5
- ADR-0001 — wprowadza `dom_id`, na którym opiera się walidacja
- `docs/vision.md` §9.3 — zasada „niskie tarcie ponad kompletność”
