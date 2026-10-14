# ADR-0004: FastAPI z Jinja2 i HTMX zamiast SPA

- **Status:** ⚠️ **zastąpiony przez [ADR-0007](0007-django-zamiast-fastapi.md)**
- **Data:** 2026-10-14
- **Dotyczy:** warstwa prezentacji, proces budowania, wdrożenie

> **Dokument nieaktualny.** Wybór FastAPI został wycofany na rzecz Django
> jeszcze przed rozpoczęciem implementacji. Powód: koszt własnej
> implementacji sesji, CSRF, formularzy i panelu zarządzania — oszacowany
> na ponad tysiąc linii kodu, w tym fragmenty krytyczne dla bezpieczeństwa.
> Zachowane w repozytorium, bo rozpoznanie wariantów i odrzucenie SPA
> pozostają aktualne i doprowadziły do obecnego kształtu projektu.

## Kontekst

Pierwotnie zakładaliśmy REST API w FastAPI plus osobny frontend SPA
(React albo Vue). W trakcie planowania zmieniliśmy podejście na renderowanie
po stronie serwera.

Powody zmiany:

- **Build SPA na Raspberry Pi jest problematyczny.** `npm run build` przy
  1–2 GB RAM potrafi zakończyć się błędem braku pamięci. Wymagałoby to
  budowania w CI albo na laptopie i wgrywania gotowych plików.
- **Brak odbiorcy dla API.** Jedynym klientem byłby własny frontend.
  Automatyczna dokumentacja OpenAPI, główny argument za FastAPI, nie
  miałaby komu służyć.
- **Nieproporcjonalna złożoność.** Dwa repozytoria lub dwa katalogi, dwa
  języki, CORS, routing po obu stronach, synchronizacja typów — dla
  aplikacji o kilkunastu ekranach.

Aplikacja ma niewiele widoków i jeden element wymagający interaktywności:
wyszukiwarkę z wynikami pojawiającymi się w trakcie pisania.

## Rozważane warianty

### A. FastAPI + REST API + SPA

Pełne rozdzielenie, maksymalna elastyczność frontendu.

Odrzucony: powody wymienione w kontekście.

### B. Django

Formularze, CSRF, uwierzytelnianie, panel administracyjny i migracje
dostępne od razu. Dla aplikacji renderowanej serwerowo to naturalny wybór
i znacząco mniej własnego kodu.

Odrzucony mimo realnych zalet: cięższy, narzuca strukturę projektu,
a panel administracyjny i system uprawnień pozostałyby w dużej części
niewykorzystane. Decyzja częściowo preferencyjna — wariant uczciwie
konkurencyjny.

### C. Flask + Jinja2

Jinja to natywny silnik Flaska, `Flask-WTF` daje formularze i ochronę CSRF
praktycznie za darmo.

Odrzucony: brak natywnego async i słabsza integracja z Pydantic.
Różnica wobec wybranego wariantu jest niewielka.

### D. FastAPI + Jinja2 + HTMX — **wybrany**

Renderowanie serwerowe z punktową interaktywnością przez HTMX.

## Decyzja

FastAPI serwuje HTML przez `Jinja2Templates`. Interaktywność realizuje HTMX
dołączony jako plik statyczny w repozytorium.

**Zasada twarda: żadnej zależności od Node.js.** HTMX i CSS to pliki
w `static/`, nie pakiety npm. W projekcie nie ma `package.json`.

Trasy HTMX zwracają fragmenty HTML z katalogu `templates/partials/`,
nie JSON.

## Konsekwencje

### Pozytywne

- Brak procesu budowania — wdrożenie to skopiowanie kodu i uruchomienie.
- Jeden język w całym projekcie.
- Brak CORS, brak podwójnego routingu, brak synchronizacji typów.
- Wyszukiwanie na żywo i rozwijanie drzewa działają bez pisania JavaScriptu.
- Aplikacja działa także przy wyłączonym JS, w trybie pełnych przeładowań.

### Negatywne — przyjęte świadomie

- **FastAPI nie jest frameworkiem do HTML-a.** Nie ma obsługi formularzy,
  ochrony CSRF ani uwierzytelniania — wszystko trzeba napisać (ADR-0005).
  Rezygnujemy z głównego powodu, dla którego wybiera się FastAPI.
- **Brak panelu administracyjnego.** Django dałoby go za darmo. Zakładanie
  kont realizuje skrypt CLI (reguła U1).
- **HTMX to mniej znany wzorzec.** Przy złożonych interakcjach trudniej
  szukać gotowych rozwiązań niż dla Reacta.
- **Ograniczona interaktywność.** Przeciąganie przedmiotów między
  lokalizacjami metodą „przeciągnij i upuść” byłoby trudne. Nie ma go
  w zakresie v1, ale to realne ograniczenie.
- **Każda interakcja to żądanie HTTP.** W sieci domowej bez znaczenia,
  przy dostępie spoza domu byłoby odczuwalne.

### Kiedy wrócić do tej decyzji

- Interfejs zaczyna wymagać złożonego stanu po stronie klienta
  (edycja wielu rzeczy naraz, przeciąganie w drzewie).
- Powstaje potrzeba aplikacji mobilnej — wtedy dochodzi warstwa `api/`
  wywołująca te same serwisy, zgodnie z regułą A2 z `architecture.md`.
- Liczba własnego kodu na formularze, CSRF i sesje przekracza to, co
  Django dałoby gotowe.

## Powiązane

- `docs/architecture.md` §2 — warstwy, reguła A2 umożliwiająca dołożenie API
- ADR-0005 — sesje i CSRF, czyli koszt tej decyzji
