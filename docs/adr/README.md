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
| [0004](0004-fastapi-jinja-htmx.md) | FastAPI z Jinja2 i HTMX zamiast SPA | zaakceptowany |
| [0005](0005-sesje-i-csrf.md) | Uwierzytelnianie sesją w ciasteczku, nie JWT | zaakceptowany |
| [0006](0006-przechowywanie-zdjec.md) | Zdjęcia skalowane przy uploadzie, dane poza kartą SD | zaakceptowany |

## Zależności między decyzjami

```
0004 (Jinja zamiast SPA)
  └─> 0005 (sesje zamiast JWT, własny CSRF)

0001 (parent_item_id, dom_id)
  └─> 0002 (unikalność nazw opiera się na dom_id)

0003 (SQLite, plik bazy)
  └─> 0006 (plik bazy i zdjęcia na dysku zewnętrznym)
```

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
