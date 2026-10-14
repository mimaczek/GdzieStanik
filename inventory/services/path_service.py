"""
Budowanie ścieżek i wykrywanie cykli.

Ścieżka to rdzeń aplikacji — wymaganie W1 mówi, że każdy wynik
wyszukiwania musi ją zawierać w pełnej postaci:

    Dom › Sypialnia › Szafa › Szuflada 2

Po wprowadzeniu przedmiotów-pojemników (ADR-0001) ścieżka przechodzi
przez dwa drzewa: najpierw w górę po parent_item, potem po parent
lokalizacji.

Zobacz docs/architecture.md §5.2 i §5.3.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache

from ..exceptions import CycleError
from ..models import Item, Location

SEPARATOR = " › "

# Zabezpieczenie przed zapętleniem na danych już uszkodzonych.
# Normalne drzewo ma 3–6 poziomów (reguła L4).
MAX_DEPTH = 100

_CACHE_KEY = "inventory:location_tree:v1"


@dataclass(frozen=True, slots=True)
class LocationNode:
    """Lekka reprezentacja lokalizacji — tylko to, co potrzebne do ścieżki."""

    id: int
    name: str
    parent_id: int | None


def _load_tree() -> dict[int, LocationNode]:
    """
    Wczytuje całe drzewo lokalizacji do pamięci.

    Dom ma realistycznie 50–200 lokalizacji, czyli kilkadziesiąt
    kilobajtów. Alternatywą byłyby rekurencyjne CTE, ale przy tej
    skali trzymanie drzewa w pamięci jest prostsze i szybsze.

    Zapytanie values_list zamiast pełnych obiektów — nie potrzebujemy
    reszty pól, a różnica jest zauważalna na Raspberry Pi.
    """
    return {
        pk: LocationNode(id=pk, name=name, parent_id=parent_id)
        for pk, name, parent_id in Location.objects.values_list(
            "id", "name", "parent_id"
        )
    }


def get_tree() -> dict[int, LocationNode]:
    """Drzewo lokalizacji z cache. Wczytuje przy pierwszym użyciu."""
    tree = cache.get(_CACHE_KEY)
    if tree is None:
        tree = _load_tree()
        # Bez limitu czasu — unieważniamy jawnie przy każdej zmianie.
        cache.set(_CACHE_KEY, tree, timeout=None)
    return tree


def invalidate_tree() -> None:
    """
    Unieważnia cache drzewa.

    Wołane po każdej zmianie struktury lokalizacji. Unieważniamy
    całość, bo zmiany są rzadkie w porównaniu z odczytami.

    UWAGA: przy wielu procesach Gunicorna domyślny cache lokalny
    nie wystarczy — każdy proces ma własny. Zobacz pytanie otwarte A2
    w architecture.md §12.
    """
    cache.delete(_CACHE_KEY)


# ─────────────────────────────────────────────────────────────────
# Ścieżki
# ─────────────────────────────────────────────────────────────────


def location_ancestors(location_id: int) -> list[LocationNode]:
    """
    Zwraca przodków lokalizacji od domu w dół, włącznie z nią samą.

    Pusta lista, gdy lokalizacja nie istnieje — może się zdarzyć
    przy nieświeżym cache.
    """
    tree = get_tree()
    lancuch: list[LocationNode] = []

    biezacy_id: int | None = location_id
    for _ in range(MAX_DEPTH):
        if biezacy_id is None:
            break
        wezel = tree.get(biezacy_id)
        if wezel is None:
            break
        lancuch.append(wezel)
        biezacy_id = wezel.parent_id

    lancuch.reverse()
    return lancuch


def path_for_location(location: Location | int) -> list[str]:
    """
    Nazwy od domu do wskazanej lokalizacji włącznie.

    >>> path_for_location(szuflada)
    ['Dom', 'Sypialnia', 'Szafa', 'Szuflada 2']
    """
    location_id = location if isinstance(location, int) else location.pk
    return [wezel.name for wezel in location_ancestors(location_id)]


def path_for_item(item: Item) -> list[str]:
    """
    Pełna ścieżka do rzeczy — przez przedmioty-pojemniki i lokalizacje.

    >>> path_for_item(szczoteczka)
    ['Dom', 'Sypialnia', 'Szafa', 'walizka', 'kosmetyczka']

    Zwracana ścieżka NIE zawiera nazwy samej rzeczy — opisuje miejsce,
    w którym leży. Interfejs pokazuje nazwę osobno.

    Część przedmiotowa wymaga zapytań do bazy (brak cache), ale
    zagnieżdżenie rzadko przekracza 3 poziomy (reguła P10).
    """
    pojemniki: list[str] = []

    biezacy = item
    for _ in range(MAX_DEPTH):
        if biezacy.parent_item_id is None:
            break
        rodzic = (
            Item.objects.filter(pk=biezacy.parent_item_id)
            .only("id", "name", "parent_item_id", "location_id")
            .first()
        )
        if rodzic is None:
            break
        pojemniki.append(rodzic.name)
        biezacy = rodzic

    pojemniki.reverse()

    # Najwyższy przedmiot w łańcuchu leży już w lokalizacji (reguła P1)
    czesc_lokalizacji: list[str] = []
    if biezacy.location_id is not None:
        czesc_lokalizacji = path_for_location(biezacy.location_id)

    return czesc_lokalizacji + pojemniki


def format_path(parts: list[str]) -> str:
    """
    Składa ścieżkę w tekst gotowy do wyświetlenia.

    >>> format_path(['Dom', 'Sypialnia', 'Szafa'])
    'Dom › Sypialnia › Szafa'
    """
    return SEPARATOR.join(parts)


# ─────────────────────────────────────────────────────────────────
# Dom i głębokość
# ─────────────────────────────────────────────────────────────────


def home_for_location(location: Location | int) -> int | None:
    """
    Korzeń drzewa, w którym leży lokalizacja (reguła L6).

    Potrzebne do wyliczenia pola Item.home (reguła P7).
    """
    location_id = location if isinstance(location, int) else location.pk
    przodkowie = location_ancestors(location_id)
    return przodkowie[0].id if przodkowie else None


def home_for_item(item: Item) -> int | None:
    """
    Dom, w którym leży rzecz — także gdy jest zagnieżdżona w pojemniku.

    Realizuje regułę P7: home wyliczane automatycznie, nie podawane
    przez użytkownika.
    """
    if item.location_id is not None:
        return home_for_location(item.location_id)

    if item.parent_item_id is not None:
        rodzic = (
            Item.objects.filter(pk=item.parent_item_id).only("id", "home_id").first()
        )
        if rodzic is not None:
            return rodzic.home_id

    return None


def location_depth(location: Location | int) -> int:
    """Głębokość w drzewie: dom = 1, pokój = 2, mebel = 3 (reguła L4)."""
    location_id = location if isinstance(location, int) else location.pk
    return len(location_ancestors(location_id))


def item_nesting_depth(item: Item) -> int:
    """
    Zagnieżdżenie rzeczy w pojemnikach (reguła P10).

    Rzecz leżąca wprost w lokalizacji ma głębokość 0.
    """
    glebokosc = 0
    biezacy = item

    for _ in range(MAX_DEPTH):
        if biezacy.parent_item_id is None:
            break
        rodzic = (
            Item.objects.filter(pk=biezacy.parent_item_id)
            .only("id", "parent_item_id")
            .first()
        )
        if rodzic is None:
            break
        glebokosc += 1
        biezacy = rodzic

    return glebokosc


def exceeds_location_depth_warning(location: Location | int) -> bool:
    """Czy przekroczono próg ostrzeżenia dla lokalizacji (L4)."""
    return location_depth(location) > settings.LOCATION_DEPTH_WARNING


def exceeds_item_nesting_warning(item: Item) -> bool:
    """Czy przekroczono próg ostrzeżenia dla zagnieżdżenia rzeczy (P10)."""
    return item_nesting_depth(item) > settings.ITEM_NESTING_WARNING


# ─────────────────────────────────────────────────────────────────
# Wykrywanie cykli
# ─────────────────────────────────────────────────────────────────


def check_location_cycle(location: Location, new_parent: Location | None) -> None:
    """
    Sprawdza, czy przeniesienie lokalizacji nie utworzy cyklu (L1).

    Wchodzi w górę od nowego rodzica. Napotkanie przenoszonego węzła
    oznacza, że próbujemy umieścić szafę wewnątrz jej własnej szuflady.

    Rzuca CycleError — nie zwraca wartości, bo wywołujący nie ma
    sensownej alternatywy poza przerwaniem operacji.
    """
    if new_parent is None:
        return  # przeniesienie do korzenia zawsze bezpieczne

    if new_parent.pk == location.pk:
        raise CycleError(
            f"Lokalizacja „{location.name}” nie może znajdować się w samej sobie."
        )

    # Świeże dane, nie z cache — walidacja musi widzieć stan faktyczny
    rodzice: dict[int, int | None] = dict(
        Location.objects.values_list("id", "parent_id")
    )

    biezacy_id: int | None = new_parent.pk
    for _ in range(MAX_DEPTH):
        if biezacy_id is None:
            return
        if biezacy_id == location.pk:
            raise CycleError(
                f"Nie można przenieść „{location.name}” do "
                f"„{new_parent.name}” — to jej własna podlokalizacja."
            )
        biezacy_id = rodzice.get(biezacy_id)

    raise CycleError(
        "Przekroczono maksymalną głębokość drzewa — dane mogą być uszkodzone."
    )


def check_item_cycle(item: Item, new_parent_item: Item | None) -> None:
    """
    Sprawdza, czy przeniesienie rzeczy nie utworzy cyklu (P6).

    Bliźniacza reguła do L1, ale dla drzewa przedmiotów. Potrzebna,
    odkąd przedmiot może zawierać inne przedmioty (ADR-0001).
    """
    if new_parent_item is None:
        return

    if new_parent_item.pk == item.pk:
        raise CycleError(f"Przedmiot „{item.name}” nie może leżeć w samym sobie.")

    biezacy_id: int | None = new_parent_item.pk
    for _ in range(MAX_DEPTH):
        if biezacy_id is None:
            return
        if biezacy_id == item.pk:
            raise CycleError(
                f"Nie można włożyć „{item.name}” do "
                f"„{new_parent_item.name}” — ta rzecz jest w środku."
            )
        rodzic = (
            Item.objects.filter(pk=biezacy_id)
            .values_list("parent_item_id", flat=True)
            .first()
        )
        biezacy_id = rodzic

    raise CycleError(
        "Przekroczono maksymalną głębokość zagnieżdżenia — dane mogą być uszkodzone."
    )
