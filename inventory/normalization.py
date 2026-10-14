"""
Normalizacja tekstu — fundament wyszukiwania i unikalności nazw.

Jedna funkcja obsługuje dwa wymagania:
  W4 — wyszukiwanie odporne na brak polskich znaków
  N1 — porównywanie nazw przy sprawdzaniu unikalności

Zobacz docs/architecture.md §5.1.
"""

import re
import unicodedata

# Znaki, których dekompozycja NFKD nie rozkłada, bo nie są literami
# z diakrytykiem w rozumieniu Unicode — to osobne znaki.
# Polskie „ł” jest tu najważniejsze: bez tego „mlotek” nie znalazłby
# „młotka”, czyli wymaganie W4 byłoby spełnione tylko częściowo.
NIEROZKLADALNE = str.maketrans(
    {
        "ł": "l",
        "Ł": "l",
        "ø": "o",
        "Ø": "o",
        "đ": "d",
        "Đ": "d",
        "ß": "ss",
        "æ": "ae",
        "Æ": "ae",
        "œ": "oe",
        "Œ": "oe",
    }
)

_WIELOKROTNE_SPACJE = re.compile(r"\s+")


def normalize(text: str) -> str:
    """
    Sprowadza tekst do postaci porównywalnej.

    >>> normalize("Młotek Gumowy ")
    'mlotek gumowy'
    >>> normalize("ŻARÓWKA")
    'zarowka'
    >>> normalize("  wiertarka   Bosch  ")
    'wiertarka bosch'

    Kolejność operacji ma znaczenie: casefold() przed translate(),
    bo „Ł” i „ł” mają trafić na ten sam wynik.
    """
    if not text:
        return ""

    # casefold() jest agresywniejszy niż lower() — poprawnie obsługuje
    # przypadki takie jak niemieckie „ß”
    tekst = text.strip().casefold()

    # Znaki nierozkładalne przez NFKD
    tekst = tekst.translate(NIEROZKLADALNE)

    # Rozkład na literę bazową i znak diakrytyczny, potem usunięcie znaków
    rozlozony = unicodedata.normalize("NFKD", tekst)
    bez_znakow = "".join(znak for znak in rozlozony if not unicodedata.combining(znak))

    # Wielokrotne spacje na pojedyncze
    return _WIELOKROTNE_SPACJE.sub(" ", bez_znakow).strip()


def split_suffix(name: str) -> tuple[str, int | None]:
    """
    Rozdziela nazwę na rdzeń i numer sufiksu (reguły N2, N3).

    >>> split_suffix("młotek")
    ('młotek', None)
    >>> split_suffix("młotek_2")
    ('młotek', 2)
    >>> split_suffix("młotek_gumowy")
    ('młotek_gumowy', None)

    Rozpoznaje wyłącznie sufiks liczbowy. „młotek_gumowy” to nazwa
    nadana przez użytkownika, nie wynik automatycznej numeracji.
    """
    dopasowanie = re.fullmatch(r"(.+)_(\d+)", name)
    if dopasowanie:
        return dopasowanie.group(1), int(dopasowanie.group(2))
    return name, None
