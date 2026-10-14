"""
Warstwa logiki domenowej (reguła A2 z architecture.md).

Nie zna HTTP — przyjmuje i zwraca obiekty domenowe, o problemach
sygnalizuje wyjątkami z inventory.exceptions.

Import submodułów tutaj pozwala pisać `from . import services`
i dalej `services.item_service.create_item(...)` — używane w admin.py
(reguła A5), gdzie wygodnie jest mieć wszystkie serwisy pod jedną nazwą.
"""

from . import item_service, location_service, naming_service, path_service

__all__ = ["item_service", "location_service", "naming_service", "path_service"]
