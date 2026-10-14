"""
Operacje na lokalizacjach — reguły L1–L6.

Warstwa nie zna HTTP (reguła A2): przyjmuje i zwraca obiekty domenowe,
o problemach sygnalizuje wyjątkami z inventory.exceptions.
"""

from __future__ import annotations

from django.db import transaction

from ..exceptions import NotEmptyError
from ..models import Item, Location
from . import path_service


@transaction.atomic
def create_location(
    *,
    name: str,
    parent: Location | None = None,
    kind: str = "",
    description: str = "",
    updated_by=None,
) -> Location:
    """
    Tworzy lokalizację.

    Unikalność nazwy wśród rodzeństwa (L2) i nazw domów (L6) wymusza
    baza — nie duplikujemy tu tej walidacji.
    """
    lokalizacja = Location(
        name=name,
        parent=parent,
        kind=kind,
        description=description,
        updated_by=updated_by,
    )
    lokalizacja.full_clean(exclude=["name_norm", "home"])
    lokalizacja.save()

    path_service.invalidate_tree()
    return lokalizacja


@transaction.atomic
def move_location(
    location: Location,
    new_parent: Location | None,
    *,
    updated_by=None,
) -> Location:
    """
    Przenosi lokalizację wraz z całą zawartością.

    Kluczowa właściwość modelu: przenosi się pojemnik, nie każdą rzecz
    osobno. Wszystkie rzeczy w środku automatycznie zmieniają ścieżkę.

    Rzuca CycleError, gdy nowy rodzic jest potomkiem przenoszonej
    lokalizacji (L1).
    """
    path_service.check_location_cycle(location, new_parent)

    stary_dom = path_service.home_for_location(location)

    location.parent = new_parent
    location.updated_by = updated_by
    location.save()

    path_service.invalidate_tree()

    # Przeniesienie między domami wymaga aktualizacji home
    # wszystkich rzeczy w poddrzewie (reguła P7)
    nowy_dom = path_service.home_for_location(location)
    if nowy_dom != stary_dom and nowy_dom is not None:
        _update_home_for_subtree(location, nowy_dom)

    return location


def _update_home_for_subtree(root: Location, home_id: int) -> int:
    """
    Aktualizuje Item.home dla całego poddrzewa lokalizacji (P7).

    Zwraca liczbę zmienionych rzeczy. Obejmuje też przedmioty
    zagnieżdżone w pojemnikach.
    """
    ids_lokalizacji = [node.id for node in _descendants(root)]

    zmienione = Item.objects.filter(location_id__in=ids_lokalizacji).update(
        home_id=home_id
    )

    # Rzeczy w pojemnikach: schodzimy poziomami w głąb
    rodzice = list(
        Item.objects.filter(location_id__in=ids_lokalizacji).values_list(
            "id", flat=True
        )
    )
    while rodzice:
        zmienione += Item.objects.filter(parent_item_id__in=rodzice).update(
            home_id=home_id
        )
        rodzice = list(
            Item.objects.filter(parent_item_id__in=rodzice).values_list("id", flat=True)
        )

    return zmienione


def _descendants(root: Location) -> list:
    """Lokalizacja wraz ze wszystkimi potomkami, z cache drzewa."""
    drzewo = path_service.get_tree()

    dzieci: dict[int | None, list] = {}
    for wezel in drzewo.values():
        dzieci.setdefault(wezel.parent_id, []).append(wezel)

    wynik = []
    stos = [drzewo[root.pk]] if root.pk in drzewo else []
    while stos:
        wezel = stos.pop()
        wynik.append(wezel)
        stos.extend(dzieci.get(wezel.id, []))

    return wynik


def check_can_delete(location: Location) -> None:
    """
    Sprawdza, czy lokalizację można usunąć bez utraty danych (L3).

    Rzuca NotEmptyError z liczbą podlokalizacji i rzeczy — widok
    pokaże je użytkownikowi przed potwierdzeniem.
    """
    podlokalizacje = location.children.count()
    rzeczy = location.items.count()

    if podlokalizacje or rzeczy:
        raise NotEmptyError(location.name, podlokalizacje, rzeczy)


@transaction.atomic
def delete_location(
    location: Location,
    *,
    move_contents_to_parent: bool = False,
    force: bool = False,
) -> None:
    """
    Usuwa lokalizację (L3).

    Domyślnie odmawia, gdy coś zawiera. Wywołujący musi świadomie
    wybrać jedną z opcji:

      move_contents_to_parent — przenieś zawartość o poziom wyżej
      force                   — usuń kaskadowo wszystko w środku
    """
    if move_contents_to_parent:
        location.children.update(parent=location.parent)
        if location.parent_id is not None:
            location.items.update(location_id=location.parent_id)
        else:
            # Usuwamy dom — rzeczy nie mają dokąd pójść
            raise NotEmptyError(
                location.name,
                location.children.count(),
                location.items.count(),
            )
    elif not force:
        check_can_delete(location)

    if force:
        # Kasujemy od liści, żeby PROTECT nie zablokował operacji
        for wezel in reversed(_descendants(location)):
            Item.objects.filter(location_id=wezel.id).delete()
            Location.objects.filter(pk=wezel.id).delete()
    else:
        location.delete()

    path_service.invalidate_tree()


def get_homes() -> list[Location]:
    """Wszystkie nieruchomości, czyli korzenie drzewa (L6)."""
    return list(Location.objects.filter(parent__isnull=True).order_by("name"))
