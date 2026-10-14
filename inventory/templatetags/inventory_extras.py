"""
Filtry szablonowe aplikacji inventory.

Zobacz docs/architecture.md §3 — templatetags/.
"""

from django import template

from ..services import path_service

register = template.Library()


@register.filter(name="join_path")
def join_path(parts: list[str]) -> str:
    """
    Składa listę nazw ścieżki w tekst ze strzałkami (W1).

    {{ wynik.path|join_path }} -> "Dom › Sypialnia › Szafa"
    """
    return path_service.format_path(list(parts))
