# ADR-0008: Hosting mydevil.net zamiast Raspberry Pi

- **Status:** zaakceptowany
- **Data:** 2026-10-14
- **Dotyczy:** platforma wdrożenia, serwer aplikacji, struktura katalogów

## Kontekst

`architecture.md` §9 zakładał Docker Compose na Raspberry Pi w sieci
domowej — obraz ARM64, Gunicorn jako serwer WSGI, Caddy jako reverse
proxy z automatycznym HTTPS. Decyzja powstała przy założeniu, że
aplikacja działa wyłącznie w LAN, bez dostępu spoza domu (`vision.md` §6,
pozycja „Dostęp spoza domu” w tabeli poza zakresem).

Zamiast tego do wdrożenia wybrano istniejące konto na hostingu
współdzielonym mydevil.net (FreeBSD, Phusion Passenger), na którym
właściciel ma już inne działające aplikacje Python. To zmienia prawie
każdy element warstwy wdrożeniowej:

| | Raspberry Pi (plan pierwotny) | mydevil.net (wybrane) |
|---|---|---|
| System | Linux (Debian/Raspberry Pi OS) | FreeBSD |
| Izolacja | Docker | brak — bezpośrednio w venv |
| Serwer WSGI | Gunicorn | Phusion Passenger |
| Reverse proxy / HTTPS | Caddy, certyfikat własny | wbudowany w mydevil, Let's Encrypt |
| Architektura CPU | ARM64 | x86_64 (serwer hostingowy) |
| Restart aplikacji | `docker compose restart` | `touch tmp/restart.txt` |
| Dostępność | tylko LAN | internet publiczny |

Ostatni wiersz jest najistotniejszy: hosting publiczny oznacza, że
założenie „dostęp tylko z sieci domowej” z `vision.md` przestaje
obowiązywać, co zmienia też wagę pytań bezpieczeństwa (HTTPS nie jest
już opcjonalny do rozważenia później, tylko wymagany od pierwszego dnia).

## Rozważane warianty

### A. Zostać przy planie Raspberry Pi

Zgodne z `architecture.md`, zero nowej pracy koncepcyjnej.

Odrzucony: użytkownik ma już działające konto na mydevil z innymi
projektami i wybrał je jako miejsce wdrożenia — decyzja biznesowa,
nie techniczna, i nadrzędna wobec wcześniejszego planu.

### B. mydevil.net z Dockerem

Próba zachowania wariantu kontenerowego na nowej platformie.

Odrzucony: mydevil to hosting współdzielony bez dostępu do demona
Dockera — architektura kontenerowa jest tu niewykonalna, niezależnie
od preferencji.

### C. mydevil.net z Phusion Passenger — **wybrany**

Natywny dla tej platformy sposób uruchamiania aplikacji Python.

## Decyzja

Aplikacja uruchamiana przez Phusion Passenger, zgodnie z konwencją
mydevil: plik `passenger_wsgi.py` eksportujący obiekt `application`,
środowisko Python w venv skonfigurowanym przez panel hostingu.

### Struktura katalogów

```
~/domains/gdziestanik.lubian.net/
├── Source/GdzieStanik/       repozytorium git
├── venv/gdzie_stanik_venv/   interpreter, zarządzany przez panel mydevil
├── data/                     baza, zdjęcia, .env — POZA repozytorium
└── public_python/
    ├── passenger_wsgi.py
    ├── tmp/restart.txt       mechanizm restartu Passengera
    └── public/static/        cel collectstatic
```

Dane poza `Source/` to świadoma zmiana względem wariantu Docker (gdzie
wolumen montowany z zewnątrz dawał tę separację za darmo) — tutaj trzeba
ją wymusić strukturą katalogów, inaczej `git clean` mógłby usunąć bazę.

### Wersje: Python 3.12, Django 6.0 (bez zmian)

Mydevil ma Python 3.12 — zgodny zarówno z Django 6.0 (obecnie używane
po ADR-0007), jak i z Django 5.2 LTS (pierwotny wybór sprzed problemu
z Ubuntu 26.04 opisanego w ADR-0007). Świadomie **pozostano przy
Django 6.0**: kod był już napisany i przetestowany pod tę wersję,
a zmiana na 5.2 LTS nie rozwiązywałaby żadnego konkretnego problemu —
jedynie wydłużała okres wsparcia, co dla pojedynczego wdrożenia
domowego ma małe znaczenie wobec kosztu ponownego testowania.

### Ustawienia: nowy moduł, nie modyfikacja `prod.py`

`config/settings/prod.py` (wariant Docker/Raspberry Pi) pozostaje
nienaruszony — to wciąż poprawna opcja na przyszłość, gdyby plany się
zmieniły. Konfiguracja mydevil żyje w osobnym
`config/settings/mydevil.py`, różniącym się głównie:

- brakiem `SECURE_PROXY_SSL_HEADER` swoistym dla Caddy,
- ścieżkami do `data/` zamiast `/data` z Dockera,
- brakiem WhiteNoise — serwer frontowy mydevil serwuje
  `public_python/public/` bezpośrednio, co jest prostszym i bardziej
  typowym wzorcem na tej platformie niż serwowanie statyków z poziomu
  aplikacji Python.

### HTTPS weryfikowany przed wymuszeniem

`SESSION_COOKIE_SECURE` i `CSRF_COOKIE_SECURE` sterowane są zmienną
`HTTPS_CONFIRMED`, domyślnie wyłączoną. Powód: nie wiadomo z góry, jak
dokładnie reverse proxy mydevil przekazuje Passengerowi informację
o oryginalnym protokole — przedwczesne wymuszenie `Secure` na
ciasteczkach przy źle wykrywanym HTTPS uniemożliwiłoby zalogowanie się
bez oczywistego komunikatu błędu. Procedura weryfikacji w
`docs/wdrozenie-mydevil.md`.

## Konsekwencje

### Pozytywne

- Wykorzystanie istniejącej infrastruktury (konto, znajomość panelu
  mydevil z innych projektów) zamiast kupowania i konfigurowania
  nowego sprzętu.
- Let's Encrypt zarządzany przez panel hostingu — brak ręcznego
  odnawiania certyfikatów, inaczej niż przy self-signed w wariancie
  domowym.
- Dostęp spoza sieci domowej bez dodatkowej konfiguracji VPN.

### Negatywne — przyjęte świadomie

- **Dwa równoległe warianty wdrożenia do utrzymania** (`prod.py` i
  `mydevil.py`) — zmiana w jednym łatwo przeoczyć w drugim. Żadne testy
  automatyczne nie sprawdzają zgodności między nimi.
- **Dane domowe na serwerze zewnętrznym**, nie na sprzęcie we własnym
  mieszkaniu — zmiana modelu zaufania względem pierwotnego założenia
  z `vision.md` o pełnej kontroli nad danymi.
- **Dostępność z internetu zwiększa powierzchnię ataku** względem
  planu „tylko LAN” z `vision.md` §6. Logowanie, CSRF i walidacja
  uploadu (już zaimplementowane) nabierają większego znaczenia niż
  przy założeniu izolacji sieciowej.
- **Backup pominięty na razie** (świadoma decyzja przy tym wdrożeniu) —
  dane leżą na pojedynczym koncie hostingowym bez automatycznej kopii.
  Akceptowalne na czas testów, nie na czas realnego użycia domowego.
- **Brak kontroli nad systemem operacyjnym.** Aktualizacje Pythona,
  dostępność pakietów systemowych i limity zasobów zależą od
  dostawcy hostingu, nie od właściciela aplikacji.
- **Koszt zgadywania konfiguracji HTTPS** — bez dostępu do dokumentacji
  mydevil w trakcie podejmowania tej decyzji, część ustawień
  (`SECURE_PROXY_SSL_HEADER`) wymaga weryfikacji empirycznej po
  pierwszym wdrożeniu zamiast jednoznacznego ustalenia z góry.

### Kiedy wrócić do tej decyzji

- Limity hostingu współdzielonego (CPU, pamięć, miejsce na dysk)
  okażą się niewystarczające przy realnym użyciu.
- Zabraknie kontroli nad wersją Pythona albo pakietami systemowymi
  potrzebnymi do nowej funkcji.
- Zdecydowanie o powrocie do modelu „tylko LAN” z pełną kontrolą nad
  danymi — wtedy `config/settings/prod.py` i plan Docker/Raspberry Pi
  czekają gotowe, nienaruszone przez tę decyzję.
- Backup przestanie być pomijalny — wtedy to pierwszy element do
  domknięcia niezależnie od wyboru platformy.

## Powiązane

- `docs/architecture.md` §9 — wariant Docker/Raspberry Pi, wciąż aktualny
  jako opcja alternatywna
- `docs/wdrozenie-mydevil.md` — pełna procedura krok po kroku
- `deploy/mydevil/` — pliki do skopiowania na serwer
  (`passenger_wsgi.py`, `.env.example`)
- ADR-0007 — wybór Django 6.0, którego dotyczy decyzja o niezmienianiu
  wersji mimo dostępności Pythona 3.12 kompatybilnego też z 5.2 LTS
- `vision.md` §6 — zapis „dostęp tylko z sieci domowej”, nieaktualny
  po wyborze hostingu publicznego
