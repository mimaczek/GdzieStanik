"""
Wyjątki domenowe.

Warstwa services/ nie zna HTTP (reguła A2), więc sygnalizuje problemy
wyjątkami. Mapowanie na odpowiedzi HTTP odbywa się w widokach.
"""


class DomainError(Exception):
    """Wspólna klasa bazowa — pozwala łapać wszystkie naraz."""


class CycleError(DomainError):
    """
    Próba umieszczenia węzła wewnątrz samego siebie.

    Reguły L1 (lokalizacje) i P6 (przedmioty).
    """


class NameCollisionError(DomainError):
    """
    Nazwa jest już zajęta w tym domu (N1).

    Niesie propozycję nazwy z sufiksem, żeby widok mógł ją pokazać
    użytkownikowi do zatwierdzenia (N2) — nazwa nigdy nie zmienia się
    cicho.
    """

    def __init__(self, name: str, suggestion: str) -> None:
        self.name = name
        self.suggestion = suggestion
        super().__init__(
            f"Nazwa „{name}” jest już zajęta w tym domu. Proponowana: „{suggestion}”."
        )


class NotEmptyError(DomainError):
    """
    Próba usunięcia lokalizacji, która coś zawiera (L3).

    Niesie liczbę obiektów, żeby widok mógł pokazać skalę operacji
    przed potwierdzeniem.
    """

    def __init__(self, location_name: str, children: int, items: int) -> None:
        self.location_name = location_name
        self.children = children
        self.items = items
        super().__init__(
            f"Lokalizacja „{location_name}” zawiera {children} "
            f"podlokalizacji i {items} rzeczy."
        )


class InvalidParentError(DomainError):
    """Naruszenie reguły P1 — zły zestaw pól rodzica."""
