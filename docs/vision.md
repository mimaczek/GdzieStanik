# GdzieStanik — wizja produktu

> Status: **uzgodniony szkic** · Wersja dokumentu: 0.2 · Data: 2026-10-14
>
> Zmiany w 0.2: zakres v1 obejmuje wiele nieruchomości, zdjęcia lokalizacji
> oraz przedmioty-pojemniki (walizka z rzeczami w środku).

---

## 1. Problem

W domu rzeczy używane rzadko trafiają „gdzieś”: do pudełka na strychu, do szuflady
w piwnicy, na półkę w szafie w pokoju gościnnym. Po kilku miesiącach nikt nie
pamięta gdzie. Szukanie kończy się przeglądaniem kolejnych pojemników, a często
zakupem drugiego egzemplarza rzeczy, którą już się ma.

Problem nasila się, gdy:

- domowników jest kilku i każdy chowa rzeczy po swojemu,
- rzeczy są sezonowe (ozdoby świąteczne, opony, ubrania zimowe),
- pojemniki są nieprzezroczyste i nieopisane,
- miejsce przechowywania zmienia się po każdych porządkach.

## 2. Rozwiązanie

Aplikacja webowa dostępna w domowej sieci, która odpowiada na jedno pytanie:

> **„Gdzie jest X?”** → `Sypialnia › Szafa › Szuflada 2`

Użytkownik wpisuje nazwę rzeczy i natychmiast dostaje pełną ścieżkę do miejsca,
w którym ona leży. Wszystko inne w tej aplikacji istnieje po to, żeby ta jedna
odpowiedź była możliwa i aktualna.

## 3. Wizja w jednym zdaniu

**GdzieStanik to domowy katalog rzeczy, który w sekundę pokazuje, w którym
pokoju, meblu i pojemniku leży szukany przedmiot.**

## 4. Użytkownicy

| Rola | Kto to | Czego potrzebuje |
|---|---|---|
| **Domownik** | Każda osoba mieszkająca w domu | Szybko znaleźć rzecz. Rzadziej: dodać nową lub odnotować przeniesienie |
| **Opiekun katalogu** | Osoba, która założyła strukturę domu | Dodaje pokoje i meble, porządkuje, zakłada konta domownikom |

Uwaga: w v1 **nie ma podziału uprawnień** — każde zalogowane konto może
wszystko. Rozróżnienie ról jest tu opisem zachowań, nie mechanizmem w kodzie.

## 5. Scenariusze użycia

### 5.1 Szukanie rzeczy — scenariusz główny

> Anna szuka ładowarki do wiertarki. Wchodzi na `gdziestanik.local` z telefonu,
> wpisuje „ładowarka”. Dostaje dwa wyniki:
> `Piwnica › Regał metalowy › Pudełko „Elektronarzędzia”` oraz
> `Salon › Komoda › Szuflada górna`. Przy pierwszym jest zdjęcie pudełka.
> Schodzi do piwnicy i bierze ładowarkę.

Wynik wyszukiwania **musi** zawierać pełną ścieżkę — sama nazwa pojemnika
(„Pudełko 3”) jest bezużyteczna.

### 5.2 Dodawanie rzeczy przy chowaniu

> Michał pakuje ozdoby świąteczne do pudełka i odnosi je na strych. Przed
> zamknięciem dodaje w aplikacji przedmiot „lampki choinkowe, 3 komplety”,
> wybiera lokalizację `Strych › Regał › Pudełko 7`, robi zdjęcie zawartości.

Dodawanie musi działać wygodnie **na telefonie, jedną ręką, w trakcie
porządków** — to główny moment kontaktu z aplikacją.

### 5.3 Przeglądanie zawartości pojemnika

> Anna stoi przed szafą i chce wiedzieć, co jest w której szufladzie, zanim
> zacznie je otwierać. Wchodzi w `Sypialnia › Szafa` i rozwija drzewo.

### 5.4 Przenoszenie rzeczy

> Po porządkach pudełko „Elektronarzędzia” wędruje z piwnicy do garażu. Michał
> zmienia rodzica tego pojemnika — wszystkie rzeczy w środku automatycznie
> zmieniają ścieżkę.

To kluczowa właściwość modelu: **przenosi się pojemnik, nie każdą rzecz
osobno**.

### 5.5 Czyje to jest

> „Czyj jest ten rower w garażu?” — przedmiot ma przypisanego właściciela
> spośród domowników.

### 5.6 Spakowana walizka

> Anna wraca z wyjazdu i odstawia walizkę do szafy, nie rozpakowując
> kosmetyczki. Dwa tygodnie później szuka szczoteczki podróżnej. Aplikacja
> pokazuje: `Dom › Sypialnia › Szafa › Półka górna › walizka › kosmetyczka`.

Walizka i kosmetyczka pozostają **przedmiotami** — mają właściciela, da się
je znaleźć jako rzeczy — a mimo to zawierają inne przedmioty. Przeniesienie
walizki przenosi całą zawartość (ADR-0001).

### 5.7 Dwie nieruchomości

> Michał w domku letniskowym szuka wkrętarki. Pamięta, że gdzieś jest, ale
> nie wie, czy przywiózł ją z miasta. Wyszukuje „wkretarka” i widzi, że rzecz
> jest w mieszkaniu, w piwnicy — nie ma po co szukać na miejscu.

Wyszukiwanie obejmuje **wszystkie nieruchomości**, a wynik pokazuje, w której
z nich rzecz się znajduje. Negatywna odpowiedź („to jest gdzie indziej”) bywa
równie cenna jak pozytywna.

## 6. Zakres wersji 1.0

### W zakresie

- [ ] Konta domowników: logowanie, wylogowanie, zmiana hasła
- [ ] **Wiele nieruchomości** — mieszkanie, domek letniskowy, garaż; każda
      jako osobne drzewo, wspólne konta domowników
- [ ] Drzewo lokalizacji o dowolnej głębokości (pokój → mebel → półka → pojemnik)
- [ ] Dodawanie, edycja i usuwanie lokalizacji, ze zdjęciem pojemnika
- [ ] Przedmioty: nazwa, opis, ilość, tagi, zdjęcie, właściciel, lokalizacja
- [ ] **Przedmioty-pojemniki** — walizka czy kosmetyczka pozostaje rzeczą,
      a mimo to można zapisać, co jest w środku
- [ ] Tagi na przedmiotach i lokalizacjach
- [ ] **Wyszukiwanie po nazwie, opisie i tagach z pełną ścieżką w wyniku**,
      odporne na brak polskich znaków
- [ ] Przeglądanie drzewa i zawartości lokalizacji
- [ ] Przenoszenie przedmiotów i całych lokalizacji wraz z zawartością
- [ ] Interfejs działający na telefonie (responsywny)
- [ ] Uruchomienie przez `docker compose` na Raspberry Pi

### Poza zakresem v1 (świadomie)

| Funkcja | Dlaczego nie teraz |
|---|---|
| JSON API dla aplikacji zewnętrznych | Brak odbiorcy. Warstwa serwisów przygotowana, doklejenie będzie tanie |
| Pełny dziennik zmian (audit log) | Narzut implementacyjny. Zostają pola `updated_at` / `updated_by` jako namiastka |
| Historia przenosin rzeczy | Wymaga pełnego audit logu |
| Kody kreskowe i QR | Wymaga obsługi kamery i generowania etykiet — osobny duży temat |
| Daty ważności i przypomnienia | Inny problem (spiżarnia, apteczka) niż „gdzie to jest” |
| Dostęp spoza domu | Wymaga hardeningu, publicznego HTTPS, backupów |
| Aplikacja mobilna natywna | Strona responsywna wystarczy |
| Import/eksport CSV | Przy ręcznym wprowadzaniu danych mało przydatne |
| Wypożyczania i zwroty rzeczy | Inny model użycia |
| Galeria zdjęć przedmiotu | Jedno zdjęcie wystarcza do rozpoznania rzeczy (Q1) |
| Uprawnienia per nieruchomość | Każde konto widzi wszystkie domy — ta sama rodzina |

## 7. Kryteria sukcesu

Projekt uznajemy za udany, jeśli po trzech miesiącach używania:

1. **Znalezienie rzeczy zajmuje poniżej 10 sekund** od otwarcia aplikacji.
2. **Domownicy faktycznie z niej korzystają**, zamiast krzyczeć „gdzie jest…?”.
3. **Dane są aktualne** — rzeczy wpisane do bazy leżą tam, gdzie aplikacja mówi.
4. **Dodanie rzeczy zajmuje poniżej 30 sekund** na telefonie, ze zdjęciem.

Punkt 3 jest najtrudniejszy i decyduje o wszystkim. Katalog, któremu nie można
ufać, jest gorszy niż jego brak — dlatego priorytetem jest **maksymalnie
niskie tarcie przy dodawaniu i przenoszeniu**, nie bogactwo funkcji.

## 8. Główne ryzyka

| Ryzyko | Skutek | Przeciwdziałanie |
|---|---|---|
| **Baza się zdezaktualizuje** | Aplikacja traci sens | Minimalna liczba pól wymaganych, dodanie rzeczy w kilku kliknięciach |
| **Wprowadzenie danych początkowych zniechęci** | Projekt umiera po tygodniu | Nie katalogujemy całego domu naraz; zaczynamy od rzeczy trudnych do znalezienia |
| **Zdjęcia zajadą kartę SD w Pi** | Awaria sprzętu | Skalowanie przy uploadzie, pliki na dysku USB/SSD poza kartą |
| **Brak backupu** | Utrata całej pracy | Kopia pliku SQLite + katalogu zdjęć, zadanie cron |
| **Rozrost zakresu** | v1 nigdy nie powstaje | Lista „poza zakresem” powyżej jest wiążąca |
| **Wymuszona unikalność nazw spowalnia dodawanie** | Tarcie wbrew zasadzie 9.3 | Komunikat zachęca do nazwy opisowej zamiast sufiksu `_2`; obserwować, czy baza nie zapełnia się numerami (ADR-0002) |
| **Kaskadowe usunięcie pojemnika** | Utrata kilkunastu wpisów naraz | Potwierdzenie z liczbą rzeczy w środku przed usunięciem |

## 9. Zasady projektowe

1. **Jedno pytanie, jedna odpowiedź.** Każda funkcja musi służyć szybkiemu
   znajdowaniu rzeczy. Jeśli nie służy — nie wchodzi do v1.
2. **Telefon przede wszystkim.** Główny kontakt z aplikacją następuje na
   stojąco, przy szafie, z telefonem w ręce.
3. **Niskie tarcie ponad kompletność.** Lepiej mieć w bazie 200 rzeczy z samą
   nazwą niż 20 opisanych perfekcyjnie.
4. **Dane są twoje.** Jeden plik SQLite i katalog ze zdjęciami. Backup przez
   skopiowanie dwóch rzeczy, bez eksportów i migracji z chmury.
5. **Prostota wdrożenia.** `docker compose up` na Raspberry Pi i działa.

## 10. Pochodzenie nazwy

„GdzieStanik” — żartobliwe nawiązanie do klasycznego domowego pytania
„gdzie jest…?”. Nazwa jest robocza i może się zmienić przed wydaniem.

---

## Powiązane dokumenty

- [`domain-model.md`](domain-model.md) — encje, relacje i reguły biznesowe
- [`adr/0001-przedmiot-jako-pojemnik.md`](adr/0001-przedmiot-jako-pojemnik.md)
- [`adr/0002-unikalnosc-nazw-przedmiotow.md`](adr/0002-unikalnosc-nazw-przedmiotow.md)
- [`architecture.md`](architecture.md) — warstwy i struktura kodu *(do napisania)*
