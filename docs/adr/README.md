# Decyzje architektoniczne (ADR)

Każdy plik opisuje jedną decyzję: kontekst, rozważane warianty, wybór
i konsekwencje — również te niekorzystne.

**Zasada:** zaakceptowanego ADR-a się nie zmienia. Jeśli decyzja przestaje
obowiązywać, powstaje nowy dokument, a stary dostaje status „zastąpiony
przez ADR-XXXX”. Dzięki temu widać nie tylko bieżący stan, ale i drogę,
która do niego doprowadziła.

Każdy ADR zawiera sekcję **„Kiedy wrócić do tej decyzji”** z konkretnymi
sygnałami ostrzegawczymi.

## Spis

| # | Decyzja | Status |
|---|---|---|
| [0001](0001-przedmiot-jako-pojemnik.md) | Przedmiot może zawierać inne przedmioty | zaakceptowany |
| [0002](0002-unikalnosc-nazw-przedmiotow.md) | Nazwy przedmiotów unikalne w obrębie domu | zaakceptowany |
| [0003](0003-sqlite-jako-baza.md) | SQLite jako baza danych | zaakceptowany |
| [0004](0004-fastapi-jinja-htmx.md) | ~~FastAPI z Jinja2 i HTMX zamiast SPA~~ | zastąpiony przez 0007 |
| [0005](0005-sesje-i-csrf.md) | ~~Uwierzytelnianie sesją w ciasteczku, nie JWT~~ | zastąpiony przez 0007 |
| [0006](0006-przechowywanie-zdjec.md) | Zdjęcia skalowane przy uploadzie, dane poza kartą SD | zaakceptowany |
| [0007](0007-django-zamiast-fastapi.md) | Django zamiast FastAPI | zaakceptowany |
| [0008](0008-hosting-mydevil.md) | Hosting mydevil.net zamiast Raspberry Pi | zaakceptowany |

## Zależności między decyzjami

```
0004 (odrzucenie SPA)              [zastąpiony]
  └─> 0005 (sesje zamiast JWT)     [zastąpiony]
        └─> 0007 (Django dostarcza sesje i CSRF gotowe)

0001 (parent_item_id, home)
  └─> 0002 (unikalność nazw opiera się na home)

0003 (SQLite, plik bazy)
  └─> 0006 (plik bazy i zdjęcia na dysku zewnętrznym)
        └─> 0008 (ta sama zasada, inna ścieżka: ~/domains/.../data/)

0007 (Django 6.0 na Pythonie 3.14, wymuszone przez Ubuntu 26.04)
  └─> 0008 (mydevil ma Python 3.12 — świadomie pozostano przy 6.0)
```

Decyzja o rezygnacji z SPA na rzecz renderowania serwerowego pozostaje
w mocy — zmienił się wyłącznie framework, który to realizuje.

## Format

Wzorowany na szablonie Michaela Nygarda. Nowy dokument:

```markdown
# ADR-XXXX: Tytuł w trybie oznajmującym

- **Status:** proponowany | zaakceptowany | zastąpiony przez ADR-YYYY
- **Data:** RRRR-MM-DD
- **Dotyczy:** obszary objęte decyzją

## Kontekst
Co wymusza podjęcie decyzji.

## Rozważane warianty
Każdy z uzasadnieniem przyjęcia lub odrzucenia.

## Decyzja
Co konkretnie zostało postanowione.

## Konsekwencje
### Pozytywne
### Negatywne — przyjęte świadomie
### Kiedy wrócić do tej decyzji

## Powiązane
```
