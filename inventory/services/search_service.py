"""
Wyszukiwanie — rdzeń aplikacji (wymagania W1–W7 z domain-model.md §4).

Decyzje projektowe nieprecyzowane wprost w specyfikacji, podjęte tutaj:

  - Wynik wyszukiwania to zawsze pojedynczy obiekt do znalezienia:
    przedmiot albo LOKALIZACJA. Gdy dopasowanie trafia w nazwę
    lokalizacji (np. „Szuflada”), wynikiem jest ta lokalizacja, a nie
    każdy przedmiot w jej wnętrzu osobno — to zaśmieciłoby wyniki przy
    pojemnikach z wieloma rzeczami.

  - Tagi obejmują obie kategorie (reguła T4) — dopasowanie po tagu
    może zwrócić zarówno przedmiot, jak i lokalizację oznaczoną tym
    tagiem.

  - Ten sam obiekt pasujący w kilku kategoriach (np. nazwa i tag)
    pojawia się w wynikach raz, z najlepszą (najniższą) rangą.

  - SearchResult.path to ścieżka do MIEJSCA, w którym obiekt się
    znajduje — nie zawiera nazwy samego obiektu. Pełna ścieżka do
    wyniku to zawsze path + [name], spójnie dla obu kategorii.

Ranga (reguła W5, architecture.md §5.5):
    1 — nazwa przedmiotu od początku
    2 — fragment nazwy przedmiotu
    3 — nazwa tagu (przedmiot albo lokalizacja)
    4 — nazwa lokalizacji
    5 — opis przedmiotu
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from django.db.models import Q

from ..models import Item, Location
from ..normalization import normalize
from . import path_service

# Limit na kategorię, zanim zbudujemy ścieżki (kosztowne dla Item —
# brak cache dla drzewa przedmiotów, w przeciwieństwie do lokalizacji).
# Interfejs i tak nie pokaże więcej wyników na jednym ekranie telefonu.
MAX_PER_CATEGORY = 30

RANK_NAME_PREFIX = 1
RANK_NAME_CONTAINS = 2
RANK_TAG = 3
RANK_LOCATION_NAME = 4
RANK_DESCRIPTION = 5


@dataclass(frozen=True, slots=True)
class SearchResult:
    """Jeden wynik wyszukiwania — przedmiot albo lokalizacja."""

    kind: Literal["item", "location"]
    id: int
    name: str
    path: list[str]  # ścieżka DO miejsca, bez nazwy samego wyniku
    rank: int
    quantity: int | None = None  # tylko dla przedmiotów
    is_container: bool = False  # tylko dla przedmiotów (P9)

    @property
    def full_path(self) -> list[str]:
        """Pełna ścieżka włącznie z nazwą wyniku — do wyświetlenia."""
        return [*self.path, self.name]

    @property
    def home_name(self) -> str:
        """Dom, z którego pochodzi wynik (W7) — pierwszy element ścieżki."""
        return self.path[0] if self.path else self.name


def search(query: str, *, home_id: int | None = None) -> list[SearchResult]:
    """
    Wyszukuje przedmioty i lokalizacje pasujące do zapytania.

    home_id zawęża wyniki do jednej nieruchomości — opcjonalny filtr
    z wymagania W7. Bez niego przeszukiwane są wszystkie domy.

    Zwraca listę posortowaną według trafności (W5): ranga rosnąco,
    w obrębie rangi alfabetycznie po nazwie.
    """
    query_norm = normalize(query)
    if not query_norm:
        return []

    # {(kind, id): SearchResult} — pozwala scalić duplikaty,
    # zachowując najlepszą (najniższą) rangę dla każdego obiektu
    znalezione: dict[tuple[str, int], SearchResult] = {}

    def _dodaj(wynik: SearchResult) -> None:
        klucz = (wynik.kind, wynik.id)
        istniejacy = znalezione.get(klucz)
        if istniejacy is None or wynik.rank < istniejacy.rank:
            znalezione[klucz] = wynik

    for wynik in _search_items_by_name(query_norm, home_id):
        _dodaj(wynik)
    for wynik in _search_by_tag(query_norm, home_id):
        _dodaj(wynik)
    for wynik in _search_locations_by_name(query_norm, home_id):
        _dodaj(wynik)
    for wynik in _search_items_by_description(query_norm, home_id):
        _dodaj(wynik)

    wyniki = list(znalezione.values())
    wyniki.sort(key=lambda w: (w.rank, w.name.casefold()))
    return wyniki


def _item_to_result(item: Item, rank: int) -> SearchResult:
    return SearchResult(
        kind="item",
        id=item.pk,
        name=item.name,
        path=path_service.path_for_item(item),
        rank=rank,
        quantity=item.quantity,
        is_container=item.is_container,
    )


def _location_to_result(location: Location, rank: int) -> SearchResult:
    # path_for_location zwraca ścieżkę WŁĄCZNIE z lokalizacją (W1) —
    # tutaj potrzebujemy tylko drogi DO niej, nazwę trzymamy osobno
    # (spójność z Itemem, zob. SearchResult.full_path)
    pelna = path_service.path_for_location(location)
    return SearchResult(
        kind="location",
        id=location.pk,
        name=location.name,
        path=pelna[:-1],
        rank=rank,
    )


def _location_ids_in_home(home_id: int) -> set[int]:
    """
    Identyfikatory wszystkich lokalizacji należących do danego domu.

    Jedno pobranie drzewa z cache (unika powtarzania deserializacji,
    do której doszłoby przy wołaniu home_for_location() per lokalizacja)
    i przejście w dół od korzenia (BFS) po relacji parent_id.
    """
    drzewo = path_service.get_tree()
    if home_id not in drzewo:
        return set()

    dzieci: dict[int, list[int]] = {}
    for node in drzewo.values():
        if node.parent_id is not None:
            dzieci.setdefault(node.parent_id, []).append(node.id)

    wynik: set[int] = set()
    kolejka = [home_id]
    while kolejka:
        biezacy = kolejka.pop()
        wynik.add(biezacy)
        kolejka.extend(dzieci.get(biezacy, []))

    return wynik


def _filter_locations_by_home(queryset, home_id: int | None):
    """
    Zawęża lokalizacje do jednej nieruchomości (W7).

    Location nie ma kolumny home — przynależność do domu wynika
    z pozycji w drzewie, nie z klucza obcego. Stąd filtrowanie przez
    cache drzewa (path_service), a nie przez ORM.
    """
    if home_id is None:
        return queryset
    return queryset.filter(pk__in=_location_ids_in_home(home_id))


def _search_items_by_name(query_norm: str, home_id: int | None) -> list[SearchResult]:
    """Ranga 1 (prefiks) i 2 (fragment) — reguła W2, W3, W4."""
    pasujace = Item.objects.filter(name_norm__contains=query_norm)
    if home_id is not None:
        pasujace = pasujace.filter(home_id=home_id)

    pasujace = pasujace.only(
        "id", "name", "quantity", "location_id", "parent_item_id", "home_id"
    )[: MAX_PER_CATEGORY * 2]  # z zapasem, bo dzielimy na dwie rangi

    wyniki = []
    for item in pasujace:
        ranga = (
            RANK_NAME_PREFIX
            if item.name_norm.startswith(query_norm)
            else RANK_NAME_CONTAINS
        )
        wyniki.append(_item_to_result(item, ranga))
    return wyniki[:MAX_PER_CATEGORY]


def _search_by_tag(query_norm: str, home_id: int | None) -> list[SearchResult]:
    """
    Ranga 3 — dopasowanie po nazwie tagu.

    T4: tagi są wspólne dla przedmiotów i lokalizacji, więc obie
    kategorie są przeszukiwane.
    """
    wyniki: list[SearchResult] = []

    items = Item.objects.filter(tags__name_norm__contains=query_norm)
    if home_id is not None:
        items = items.filter(home_id=home_id)
    wyniki.extend(
        _item_to_result(item, RANK_TAG) for item in items.distinct()[:MAX_PER_CATEGORY]
    )

    locations = Location.objects.filter(tags__name_norm__contains=query_norm)
    locations = _filter_locations_by_home(locations, home_id)
    wyniki.extend(
        _location_to_result(loc, RANK_TAG)
        for loc in locations.distinct()[:MAX_PER_CATEGORY]
    )

    return wyniki


def _search_locations_by_name(
    query_norm: str, home_id: int | None
) -> list[SearchResult]:
    """Ranga 4 — pozwala znaleźć „co jest w pudełku 7”."""
    lokalizacje = Location.objects.filter(name_norm__contains=query_norm)
    lokalizacje = _filter_locations_by_home(lokalizacje, home_id)
    return [
        _location_to_result(loc, RANK_LOCATION_NAME)
        for loc in lokalizacje[:MAX_PER_CATEGORY]
    ]


def _search_items_by_description(
    query_norm: str, home_id: int | None
) -> list[SearchResult]:
    """
    Ranga 5 — najniższy priorytet.

    Filtrujemy po description_norm (kolumna wypełniana sygnałem
    fill_description_norm), nie po surowym description — porównanie
    znormalizowanego zapytania z tekstem zawierającym ogonki prawie
    nigdy by nie trafiło (W4 dotyczy też opisu, nie tylko nazw).
    """
    pasujace = Item.objects.filter(Q(description_norm__contains=query_norm)).exclude(
        name_norm__contains=query_norm
    )  # nie duplikuj rangi 1–2
    if home_id is not None:
        pasujace = pasujace.filter(home_id=home_id)

    pasujace = pasujace.only(
        "id", "name", "quantity", "location_id", "parent_item_id", "home_id"
    )[:MAX_PER_CATEGORY]
    return [_item_to_result(item, RANK_DESCRIPTION) for item in pasujace]
