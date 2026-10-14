"""
Widoki aplikacji inventory.

Pełna implementacja w krokach 7–8 (architecture.md §11).
Widoki pozostają cienkie: odbierają żądanie, wołają serwis,
wybierają szablon (reguła A1).
"""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import render


def search(request: HttpRequest) -> HttpResponse:
    """
    Wyszukiwarka — trasa krytyczna aplikacji (wymagania W1–W7).

    Na razie zaślepka potwierdzająca, że szkielet działa.
    """
    return render(request, "inventory/search.html", {"query": ""})
