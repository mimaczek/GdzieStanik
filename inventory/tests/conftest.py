"""Wspólne fixtures dla testów inventory."""

import pytest

from inventory.models import Item, Location


@pytest.fixture
def dom(db) -> Location:
    """Korzeń drzewa — lokalizacja bez rodzica (L6)."""
    return Location.objects.create(name="Dom", kind=Location.Kind.HOME)


@pytest.fixture
def domek(db) -> Location:
    """Druga nieruchomość — do testów unikalności nazw w obrębie domu."""
    return Location.objects.create(name="Domek letniskowy", kind=Location.Kind.HOME)


@pytest.fixture
def sypialnia(dom) -> Location:
    return Location.objects.create(
        name="Sypialnia", parent=dom, kind=Location.Kind.ROOM
    )


@pytest.fixture
def szafa(sypialnia) -> Location:
    return Location.objects.create(
        name="Szafa", parent=sypialnia, kind=Location.Kind.FURNITURE
    )


@pytest.fixture
def mlotek(dom, szafa) -> Item:
    return Item.objects.create(name="Młotek", location=szafa, home=dom)
