"""
Operacje na przedmiotach — reguły P1–P11 oraz N1–N5.

Najważniejsze zadania tej warstwy:
  - wyliczanie pola home (P7), którego użytkownik nigdy nie podaje
  - pilnowanie, by rzecz miała dokładnie jednego rodzica (P1)
  - obsługa kolizji nazw z propozycją sufiksu (N2, N5)
  - kaskadowe przenoszenie i usuwanie pojemników (P5, P8)
"""

from __future__ import annotations

from django.db import transaction

from ..exceptions import InvalidParentError, NameCollisionError
from ..models import Item, Location
from . import naming_service, path_service


def _resolve_home(location: Location | None, parent_item: Item | None) -> Location:
    """
    Ustala dom dla rzeczy (P7).

    Użytkownik nigdy nie podaje tego pola — wynika z miejsca, w którym
    rzecz leży.
    """
    if location is not None and parent_item is not None:
        raise InvalidParentError(
            "Rzecz może leżeć w lokalizacji albo w innym przedmiocie, nie w obu naraz."
        )

    if location is not None:
        home_id = path_service.home_for_location(location)
        if home_id is None:
            raise InvalidParentError(
                f"Nie udało się ustalić domu dla lokalizacji „{location.name}”."
            )
        return Location.objects.get(pk=home_id)

    if parent_item is not None:
        return parent_item.home

    raise InvalidParentError(
        "Rzecz musi leżeć w lokalizacji albo w innym przedmiocie (P1)."
    )


@transaction.atomic
def create_item(
    *,
    name: str,
    location: Location | None = None,
    parent_item: Item | None = None,
    quantity: int = 1,
    description: str = "",
    owner=None,
    tags: list | None = None,
    accept_suggested_name: bool = False,
    updated_by=None,
) -> Item:
    """
    Tworzy przedmiot.

    Gdy nazwa jest zajęta w tym domu (N1), rzuca NameCollisionError
    z propozycją sufiksu. Widok pokaże ją użytkownikowi, który może
    zatwierdzić albo wpisać własną nazwę (N2).

    accept_suggested_name=True przyjmuje propozycję bez pytania —
    używane po zatwierdzeniu przez użytkownika.
    """
    home = _resolve_home(location, parent_item)

    wolna, propozycja = naming_service.resolve_name(home, name)
    if not wolna:
        if not accept_suggested_name:
            raise NameCollisionError(name, propozycja)
        name = propozycja

    rzecz = Item(
        name=name,
        description=description,
        quantity=quantity,
        location=location,
        parent_item=parent_item,
        home=home,
        owner=owner,
        updated_by=updated_by,
    )
    rzecz.full_clean(exclude=["name_norm", "home"])
    rzecz.save()

    if tags:
        rzecz.tags.set(tags)

    return rzecz


@transaction.atomic
def move_item(
    item: Item,
    *,
    location: Location | None = None,
    parent_item: Item | None = None,
    accept_suggested_name: bool = False,
    updated_by=None,
) -> Item:
    """
    Przenosi rzecz wraz z zawartością (P8).

    Przeniesienie do innego domu, gdzie nazwa jest zajęta, wywołuje
    propozycję sufiksu (N5) — przenosiny nie są blokowane, ale nazwa
    nie zmienia się cicho.
    """
    path_service.check_item_cycle(item, parent_item)

    nowy_dom = _resolve_home(location, parent_item)

    # Zapamiętujemy PRZED zmianą — po przypisaniu item.home porównanie
    # zawsze dawałoby fałsz i zawartość zostałaby w starym domu.
    zmiana_domu = nowy_dom.pk != item.home_id

    if zmiana_domu:
        wolna, propozycja = naming_service.resolve_name(
            nowy_dom, item.name, exclude_pk=item.pk
        )
        if not wolna:
            if not accept_suggested_name:
                raise NameCollisionError(item.name, propozycja)
            item.name = propozycja

    item.location = location
    item.parent_item = parent_item
    item.home = nowy_dom
    item.updated_by = updated_by
    item.save()

    # P8: zawartość idzie razem z pojemnikiem
    if zmiana_domu:
        _update_home_for_contents(item, nowy_dom.pk)

    return item


def _update_home_for_contents(item: Item, home_id: int) -> int:
    """Aktualizuje home dla wszystkiego wewnątrz pojemnika (P7, P8)."""
    zmienione = 0
    poziom = [item.pk]

    while poziom:
        zmienione += Item.objects.filter(parent_item_id__in=poziom).update(
            home_id=home_id
        )
        poziom = list(
            Item.objects.filter(parent_item_id__in=poziom).values_list("id", flat=True)
        )

    return zmienione


@transaction.atomic
def rename_item(
    item: Item,
    new_name: str,
    *,
    accept_suggested_name: bool = False,
    updated_by=None,
) -> Item:
    """
    Zmienia nazwę rzeczy (N4).

    Podlega tej samej walidacji co tworzenie — przy kolizji
    użytkownik dostaje propozycję sufiksu.
    """
    wolna, propozycja = naming_service.resolve_name(
        item.home, new_name, exclude_pk=item.pk
    )
    if not wolna:
        if not accept_suggested_name:
            raise NameCollisionError(new_name, propozycja)
        new_name = propozycja

    item.name = new_name
    item.updated_by = updated_by
    item.save()
    return item


def count_contents(item: Item) -> int:
    """
    Liczba rzeczy wewnątrz pojemnika, ze wszystkimi poziomami (P5).

    Widok pokazuje tę liczbę przed usunięciem — kaskada w bazie
    działa po cichu, więc użytkownik musi wiedzieć, co kasuje.
    """
    razem = 0
    poziom = [item.pk]

    while poziom:
        dzieci = list(
            Item.objects.filter(parent_item_id__in=poziom).values_list("id", flat=True)
        )
        razem += len(dzieci)
        poziom = dzieci

    return razem


@transaction.atomic
def delete_item(item: Item) -> int:
    """
    Usuwa rzecz wraz z zawartością (P5).

    Zwraca liczbę usuniętych obiektów. Wywołujący powinien wcześniej
    pokazać count_contents() użytkownikowi.
    """
    liczba = count_contents(item) + 1
    item.delete()
    return liczba
