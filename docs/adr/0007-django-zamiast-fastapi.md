# ADR-0007: Django zamiast FastAPI

- **Status:** zaakceptowany
- **Data:** 2026-10-14
- **Zastępuje:** ADR-0004 (FastAPI z Jinja2 i HTMX), ADR-0005 (sesje i CSRF)
- **Dotyczy:** framework, uwierzytelnianie, struktura projektu

## Kontekst

ADR-0004 wybrał FastAPI z Jinja2 i HTMX. Decyzja była podjęta po rezygnacji
z frontendu SPA, ale **zachowywała framework wybrany pod SPA**. Sam ADR-0004
przyznawał to wprost:

> FastAPI nie jest frameworkiem do HTML-a. Nie ma obsługi formularzy,
> ochrony CSRF ani uwierzytelniania — wszystko trzeba napisać. Rezygnujemy
> z głównego powodu, dla którego wybiera się FastAPI.

Django zostało wtedy odrzucone z adnotacją „decyzja częściowo preferencyjna,
wariant uczciwie konkurencyjny”.

Przy pisaniu `architecture.md` koszt tego wyboru stał się policzalny.
Do napisania własnoręcznie:

| Element | Szacunek |
|---|---|
| Sesje w tabeli, cykl życia, czyszczenie wygasłych | ~150 linii |
| Ochrona CSRF z obsługą HTMX | ~100 linii |
| Hashowanie haseł, logowanie, limit prób | ~120 linii |
| Walidacja i renderowanie formularzy | ~200 linii |
| Konfiguracja migracji (Alembic) | ~80 linii |
| Interfejs do zarządzania strukturą domu | ~400 linii |

Razem ponad tysiąc linii kodu infrastrukturalnego, który w Django jest
konfiguracją. Co istotniejsze — **własna implementacja CSRF i sesji to kod,
w którym błąd oznacza realną podatność**, pisany bez przeglądu kodu przez
drugą osobę.

Równolegle ujawniła się druga korzyść: panel administracyjny Django pokrywa
zarządzanie drzewem lokalizacji i kontami, czyli operacje wykonywane rzadko,
przy komputerze. Własne widoki zostają potrzebne tylko tam, gdzie wygoda
naprawdę ma znaczenie — wyszukiwanie i dodawanie rzeczy z telefonu.

## Rozważane warianty

### A. Pozostanie przy FastAPI

Nic nie trzeba przepisywać — kodu jeszcze nie ma, więc argument jest słaby.

Odrzucony: ponad tysiąc linii infrastruktury do napisania i utrzymania,
w tym fragmenty krytyczne dla bezpieczeństwa.

### B. Flask z rozszerzeniami

`Flask-WTF`, `Flask-Login`, `Flask-SQLAlchemy` pokrywają większość braków.

Odrzucony: składanie frameworka z wtyczek daje ten sam efekt co Django,
ale bez spójności i z większą liczbą zależności do pilnowania.

### C. Django — **wybrany**

## Decyzja

Django 5.x jako framework aplikacji.

### Co odpada z wcześniejszych planów

- Własne sesje — `django.contrib.sessions`
- Własny CSRF — `CsrfViewMiddleware`
- Własne hashowanie haseł — Argon2 przez `PASSWORD_HASHERS`
- Alembic — migracje Django
- SQLAlchemy — Django ORM
- Pydantic do formularzy — `django.forms`
- Własny skrypt zakładania kont — `createsuperuser`
- Interfejs zarządzania strukturą — panel administracyjny

### Co zostaje bez zmian

- SQLite w trybie WAL (ADR-0003) — Django obsługuje natywnie
- HTMX — działa z szablonami Django tak samo jak z Jinja2
- Brak Node.js i procesu budowania
- Skalowanie zdjęć (ADR-0006) — przez `ImageField` i Pillow
- Decyzje domenowe (ADR-0001, ADR-0002) — niezależne od frameworka

### Ustalenia szczegółowe

1. **Własny model użytkownika** dziedziczący po `AbstractUser`, ustawiony
   przed pierwszą migracją. Późniejsza zmiana `AUTH_USER_MODEL` jest
   w Django bardzo kosztowna.
2. **Dwie aplikacje:** `inventory` (lokalizacje, przedmioty, tagi) oraz
   `accounts` (użytkownicy). Rozdzielanie lokalizacji i przedmiotów
   tworzyłoby sztuczne granice i cykliczne importy.
3. **Warstwa `services/` zostaje**, mimo że nie jest idiomatyczna dla Django.
   Reguły domenowe P1–P11, N1–N5, L1–L6 są zbyt rozbudowane, by rozsypać je
   po metodach modeli. Dostęp do danych przez Managery i QuerySety —
   bez osobnej warstwy repozytoriów.
4. **Panel administracyjny obsługuje strukturę domu i konta.** Własne widoki
   powstają wyłącznie dla wyszukiwania i szybkiego dodawania rzeczy.

## Konsekwencje

### Pozytywne

- Ponad tysiąc linii infrastruktury zastąpione konfiguracją.
- Mechanizmy bezpieczeństwa (sesje, CSRF, hasła) sprawdzone w praktyce
  przez lata, zamiast pisanych samodzielnie.
- Panel administracyjny pokrywa zarządzanie strukturą — znika z zakresu v1
  cała grupa ekranów.
- `createsuperuser` zamiast własnego skryptu (reguła U1).
- Formularze z walidacją, komunikatami błędów i tokenem CSRF z pudełka.
- Dojrzałe migracje z wykrywaniem zmian w modelach.
- ADR-0005 przestaje być potrzebny w całości.

### Negatywne — przyjęte świadomie

- **Framework narzuca strukturę.** Warstwa `services/` idzie pod prąd
  konwencji Django. Trzeba pilnować, by logika nie wyciekała do widoków
  i modeli — sam framework w tym nie pomoże.
- **Cięższy niż FastAPI.** Około 50–80 MB RAM więcej na Raspberry Pi.
  Przy 2 GB bez znaczenia, ale to realna różnica.
- **Brak async w ORM.** Nieistotne przy SQLite, gdzie zapisy i tak są
  serializowane.
- **Django ORM jest słabiej typowany niż SQLAlchemy 2.x.** Mniej pomocy
  ze strony mypy; `django-stubs` tylko częściowo to nadrabia.
- **Panel admina kusi do nadużywania.** Jest fatalny na telefonie, więc
  pokusa „zrobimy to w adminie” musi być kontrolowana — główny scenariusz
  użycia to telefon.
- **Dołożenie JSON API wymaga DRF albo django-ninja**, czyli kolejnej
  zależności. W FastAPI byłoby to natywne. Reguła A2 (serwisy niezależne
  od HTTP) nadal to zabezpiecza.

### Kiedy wrócić do tej decyzji

- Panel administracyjny okazuje się niewystarczający i i tak trzeba napisać
  własne ekrany zarządzania — wtedy przewaga Django topnieje.
- Pojawia się potrzeba wydajnego API dla aplikacji mobilnej z dużym ruchem.
- Narzut pamięciowy staje się problemem na docelowym sprzęcie.

Powrót byłby kosztowny: migracje, ORM i uwierzytelnianie są ściśle związane
z frameworkiem. Warstwa `services/` pozostaje jedynym elementem przenośnym —
i to jest główny powód, dla którego ją zachowujemy.

## Powiązane

- ADR-0004 — zastąpiony przez ten dokument
- ADR-0005 — zastąpiony, Django dostarcza sesje i CSRF
- ADR-0003 — SQLite, decyzja nadal obowiązuje
- `docs/architecture.md` — przepisany pod Django
