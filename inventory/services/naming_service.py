"""
Unikalność nazw przedmiotów i proponowanie sufiksów.

Reguły N1–N5 z docs/domain-model.md §3.2, uzasadnienie w ADR-0002.

Kluczowa zasada: serwis **proponuje** nazwę, nigdy jej nie narzuca.
Zapis następuje dopiero po zatwierdzeniu przez użytkownika — nazwa
nie zmienia się cicho (N2).
"""

from __future__ import annotations

from ..models import Item, Location
from ..normalization import normalize, split_suffix

# Zabezpieczenie przed pętlą, gdyby coś poszło nie tak z numeracją
MAX_SUFFIX_ATTEMPTS = 1000


def is_name_taken(
    home: Location | int,
    name: str,
    *,
    exclude_pk: int | None = None,
) -> bool:
    """
    Czy nazwa jest zajęta w tym domu (N1).

    Porównanie po postaci znormalizowanej: „Młotek”, „mlotek”
    i „MŁOTEK " to ta sama nazwa.

    exclude_pk pozwala pominąć edytowaną rzecz — inaczej każda edycja
    bez zmiany nazwy zgłaszałaby kolizję ze sobą samą.
    """
    home_id = home if isinstance(home, int) else home.pk

    zapytanie = Item.objects.filter(home_id=home_id, name_norm=normalize(name))
    if exclude_pk is not None:
        zapytanie = zapytanie.exclude(pk=exclude_pk)

    return zapytanie.exists()


def suggest_name(home: Location | int, name: str) -> str:
    """
    Proponuje wolną nazwę, dodając sufiks liczbowy (N2, N3).

    >>> suggest_name(dom, "młotek")        # gdy wolna
    'młotek'
    >>> suggest_name(dom, "młotek")        # gdy zajęta
    'młotek_2'

    N3: licznik nigdy się nie cofa. Po usunięciu „młotek_2” kolejny
    nowy dostanie „młotek_4”, nie „młotek_2” — luki w numeracji są
    akceptowane, żeby nazwa nie wskazywała kiedyś innej rzeczy.

    Jeśli użytkownik poda już „młotek_2”, a ta jest zajęta, numerujemy
    dalej od rdzenia „młotek”, nie tworzymy „młotek_2_2”.
    """
    home_id = home if isinstance(home, int) else home.pk

    if not is_name_taken(home_id, name):
        return name

    rdzen, _ = split_suffix(name)
    rdzen_norm = normalize(rdzen)

    # Najwyższy użyty numer dla tego rdzenia — stąd brak cofania (N3)
    uzyte = Item.objects.filter(
        home_id=home_id, name_norm__startswith=rdzen_norm
    ).values_list("name", flat=True)

    najwyzszy = 1
    for istniejaca in uzyte:
        istn_rdzen, istn_numer = split_suffix(istniejaca)
        if normalize(istn_rdzen) != rdzen_norm:
            continue  # „młotek gumowy” to nie wariant „młotka”
        if istn_numer is not None:
            najwyzszy = max(najwyzszy, istn_numer)

    for numer in range(najwyzszy + 1, najwyzszy + MAX_SUFFIX_ATTEMPTS):
        kandydat = f"{rdzen}_{numer}"
        if not is_name_taken(home_id, kandydat):
            return kandydat

    raise RuntimeError(
        f"Nie znaleziono wolnej nazwy dla „{name}” po {MAX_SUFFIX_ATTEMPTS} próbach."
    )


def resolve_name(
    home: Location | int,
    name: str,
    *,
    exclude_pk: int | None = None,
) -> tuple[bool, str]:
    """
    Sprawdza nazwę i zwraca (czy_wolna, propozycja).

    Pozwala widokowi zapytać użytkownika przed zapisem (N2, N4):

        wolna, propozycja = resolve_name(dom, "młotek")
        if not wolna:
            # pokaż: „Nazwa zajęta. Proponuję: młotek_2”
            # użytkownik może wpisać własną, np. „młotek gumowy”

    Dla nazwy wolnej zwraca ją bez zmian.
    """
    if not is_name_taken(home, name, exclude_pk=exclude_pk):
        return True, name
    return False, suggest_name(home, name)
