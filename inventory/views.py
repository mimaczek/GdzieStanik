"""
Widoki aplikacji inventory.

Widoki pozostają cienkie: odbierają żądanie, wołają serwis, wybierają
szablon (reguła A1). Logika wyszukiwania w całości w search_service.
"""

from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, render

from .models import Item, Location
from .services import location_service, path_service, search_service


def search(request: HttpRequest) -> HttpResponse:
    """
    Wyszukiwarka — trasa krytyczna aplikacji (wymagania W1–W7).

    GET ?q=<zapytanie>&home=<id>

    Żądanie HTMX (nagłówek HX-Request) dostaje sam fragment z wynikami
    — używany przy wyszukiwaniu na żywo, bez przeładowania strony.
    Zwykłe żądanie dostaje pełną stronę z tym samym fragmentem
    w środku, żeby działało również bez JavaScriptu.
    """
    query = request.GET.get("q", "").strip()
    home_param = request.GET.get("home", "")
    home_id = int(home_param) if home_param.isdigit() else None

    wyniki = search_service.search(query, home_id=home_id) if query else []

    context = {
        "query": query,
        "results": wyniki,
        "homes": location_service.get_homes(),
        "selected_home_id": home_id,
    }

    template = (
        "inventory/partials/search_results.html"
        if request.headers.get("HX-Request")
        else "inventory/search.html"
    )
    return render(request, template, context)


def item_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Szczegóły przedmiotu — pełna ścieżka, zdjęcie, zawartość jeśli
    pojemnik (P9). Formularz edycji powstanie w kroku 8.
    """
    item = get_object_or_404(
        Item.objects.select_related("home", "owner").prefetch_related("tags"),
        pk=pk,
    )
    return render(
        request,
        "inventory/item_detail.html",
        {
            "item": item,
            "path": path_service.path_for_item(item),
            "contents": item.contents.all(),
        },
    )


def location_detail(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Przeglądanie lokalizacji — podlokalizacje i rzeczy w środku.
    Rozwijanie drzewa przez HTMX powstanie w kroku 8.
    """
    location = get_object_or_404(Location, pk=pk)
    return render(
        request,
        "inventory/location_detail.html",
        {
            "location": location,
            "path": path_service.path_for_location(location),
            "children": location.children.all(),
            "items": location.items.all(),
        },
    )
