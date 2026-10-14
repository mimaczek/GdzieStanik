# ADR-0005: Uwierzytelnianie sesją w ciasteczku, nie JWT

- **Status:** zaakceptowany
- **Data:** 2026-10-14
- **Dotyczy:** uwierzytelnianie, bezpieczeństwo formularzy

## Kontekst

Pierwotnie planowaliśmy JWT, co było spójne z założeniem o frontendzie SPA:
aplikacja przechowuje token i dołącza go w nagłówku `Authorization`.

Po zmianie na renderowanie serwerowe (ADR-0004) to założenie upadło.
Przeglądarka wysyłająca zwykły formularz przekazuje ciasteczka i nic więcej.
JWT trzeba by umieścić w ciasteczku — czyli zbudować sesję, tylko gorszą:
bez możliwości natychmiastowego unieważnienia i z większym ładunkiem
w każdym żądaniu.

Naturalne pary to: SPA → JWT, renderowanie serwerowe → sesja w ciasteczku.

Druga konsekwencja: uwierzytelnianie ciasteczkami wymaga ochrony przed CSRF,
której przy nagłówku `Authorization` nie trzeba.

## Rozważane warianty

### A. JWT w nagłówku `Authorization`

Odrzucony: niemożliwy do użycia przy zwykłych formularzach HTML.

### B. JWT w ciasteczku

Odrzucony: zachowuje wady JWT (brak unieważniania, rozmiar) bez żadnej
zalety w tym kontekście.

### C. Podpisane ciasteczko bezstanowe (jak `SECRET_KEY` w Flasku)

Prostsze, nie wymaga tabeli w bazie.

Odrzucony: nie da się unieważnić pojedynczej sesji. Po zmianie hasła
albo utracie telefonu trzeba by zmieniać klucz aplikacji i wylogowywać
wszystkich.

### D. Token sesji w bazie — **wybrany**

Losowy token w ciasteczku, stan sesji w tabeli.

## Decyzja

### Sesje

- Token: `secrets.token_urlsafe(32)`, przechowywany w tabeli `sessions`.
- Ciasteczko: `HttpOnly`, `SameSite=Lax`, `Secure` gdy HTTPS jest dostępne.
- Czas życia 30 dni, przedłużany przy aktywności.
- Wylogowanie i zmiana hasła usuwają wpisy z tabeli — unieważnienie
  jest natychmiastowe.

### Hasła

Argon2id przez `argon2-cffi`, parametry domyślne biblioteki.
Logowanie objęte limitem prób i opóźnieniem po nieudanych próbach.

### Ochrona CSRF

FastAPI nie ma wbudowanego mechanizmu, więc implementujemy go sami:

- token generowany przy tworzeniu sesji, powiązany z nią,
- ukryte pole `csrf_token` w każdym formularzu,
- walidacja dla wszystkich metod zmieniających stan (POST, PUT, DELETE),
- HTMX przekazuje token nagłówkiem przez `hx-headers` na elemencie `<body>`.

### HTTPS

Caddy jako reverse proxy. W sieci domowej certyfikat wewnętrzny lub
samopodpisany. Dopóki HTTPS nie działa, flaga `Secure` pozostaje wyłączona,
a ciasteczko sesyjne jest przesyłane otwartym tekstem — **świadomie przyjęte
ryzyko ograniczone do sieci lokalnej**.

## Konsekwencje

### Pozytywne

- Natychmiastowe unieważnianie sesji.
- Możliwość pokazania listy aktywnych sesji i ich zakończenia.
- Ciasteczko `HttpOnly` jest niedostępne dla JavaScriptu — kradzież tokenu
  przez XSS jest trudniejsza niż przy JWT w `localStorage`.
- Tokeny są krótkie, bez ładunku danych.

### Negatywne — przyjęte świadomie

- **Stan po stronie serwera.** Każde żądanie odpytuje tabelę sesji.
  Przy SQLite i domowym ruchu bez znaczenia.
- **Trzeba posprzątać wygasłe sesje.** Zadanie okresowe albo czyszczenie
  przy logowaniu.
- **CSRF w całości własnym kodem.** Około stu linii plus testy. Pomyłka
  oznacza realną podatność — to najpoważniejszy koszt wyboru FastAPI
  zamiast Django (ADR-0004).
- **Łatwo zapomnieć o tokenie.** Każdy nowy formularz i każde żądanie HTMX
  musi go zawierać. Rozwiązanie: wspólny szablon formularza i test
  sprawdzający, że trasy modyfikujące odrzucają żądania bez tokenu.
- **Bez HTTPS ochrona jest pozorna.** Ciasteczko można podsłuchać w sieci
  lokalnej.

### Kiedy wrócić do tej decyzji

- Pojawia się aplikacja mobilna lub API — wtedy JWT obok sesji ma sens.
- Własna implementacja CSRF okazuje się źródłem błędów; wtedy rozważyć
  gotową bibliotekę albo zmianę frameworka.

## Powiązane

- `docs/architecture.md` §6 — tabela zabezpieczeń
- `docs/domain-model.md` §3.4 — reguły U1–U5
- ADR-0004 — wybór FastAPI, z którego wynika konieczność własnego CSRF
