"""
Widoki aplikacji inventory.

Widoki pozostają cienkie: odbierają żądanie, wołają serwis, wybierają
szablon (reguła A1). Logika wyszukiwania w całości w search_service.
"""

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .exceptions import DomainError, NameCollisionError
from .forms import AddItemForm, MoveItemForm
from .models import Item, Location
from .services import item_service, location_service, path_service, search_service


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


def location_children(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Fragment HTMX z bezpośrednimi podlokalizacjami i rzeczami —
    używany do rozwijania węzła drzewa bez przeładowania strony
    (architecture.md §7, wiersz „Przeglądanie drzewa”).
    """
    location = get_object_or_404(Location, pk=pk)
    return render(
        request,
        "inventory/partials/tree_node_children.html",
        {
            "children": location.children.all(),
            "items": location.items.all(),
        },
    )


def add_item(request: HttpRequest) -> HttpResponse:
    """
    Szybkie dodanie rzeczy (scenariusz 5.2 z vision.md) — minimum pól,
    ma działać jedną ręką w trakcie porządków.

    Kolizja nazwy (N1) wraca jako błąd formularza z propozycją sufiksu
    (AddItemForm.clean) — użytkownik dostaje przycisk „użyj tej nazwy”
    zamiast musieć wpisywać ją ręcznie (N2).
    """
    initial = {}
    location_param = request.GET.get("location", "")
    if location_param.isdigit():
        initial["location"] = int(location_param)

    if request.method == "POST":
        # Zaakceptowanie zaproponowanego sufiksu — przycisk w szablonie
        # wysyła to samo co poprzednio plus ten jeden parametr. Flaga
        # idzie do konstruktora formularza, żeby AddItemForm.clean()
        # nie zgłosił błędu kolizji, tylko podmienił nazwę (N2).
        accept_suggested = request.POST.get("accept_suggested_name") == "1"
        form = AddItemForm(
            request.POST, request.FILES, accept_suggested_name=accept_suggested
        )

        if form.is_valid():
            try:
                rzecz = item_service.create_item(
                    name=form.cleaned_data["name"],
                    location=form.cleaned_data["location"],
                    quantity=form.cleaned_data["quantity"],
                    description=form.cleaned_data["description"],
                    photo=form.cleaned_data.get("photo"),
                    tags=_resolve_tags(form.cleaned_data["tags"]),
                    accept_suggested_name=accept_suggested,
                    updated_by=request.user,
                )
            except NameCollisionError as exc:
                # Rzadki wyścig — clean() przeszedł, ale ktoś dodał
                # kolidującą nazwę między walidacją a zapisem.
                form.add_error(
                    "name",
                    f"Nazwa „{exc.name}” właśnie została zajęta. "
                    f"Spróbuj: „{exc.suggestion}”.",
                )
            except DomainError as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(request, f"Dodano „{rzecz.name}”.")
                return redirect(reverse("inventory:item_detail", args=[rzecz.pk]))
    else:
        form = AddItemForm(initial=initial)

    return render(request, "inventory/add_item.html", {"form": form})


def move_item(request: HttpRequest, pk: int) -> HttpResponse:
    """
    Przeniesienie rzeczy (architecture.md §7) — zmiana lokalizacji albo
    włożenie do innego przedmiotu, z obsługą kolizji nazw przy zmianie
    domu (N5).
    """
    item = get_object_or_404(Item, pk=pk)

    if request.method == "POST":
        form = MoveItemForm(request.POST, item=item)
        if form.is_valid():
            try:
                item_service.move_item(
                    item,
                    location=form.cleaned_data.get("location"),
                    parent_item=form.cleaned_data.get("parent_item"),
                    updated_by=request.user,
                )
            except DomainError as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(request, f"Przeniesiono „{item.name}”.")
                return redirect(reverse("inventory:item_detail", args=[item.pk]))
    else:
        form = MoveItemForm(item=item)

    return render(
        request,
        "inventory/move_item.html",
        {
            "form": form,
            "item": item,
            "current_path": path_service.path_for_item(item),
        },
    )


def _resolve_tags(names: list[str]):
    """Zamienia nazwy tagów z formularza na obiekty Tag, tworząc nowe (T2)."""
    from .models import Tag

    return [Tag.objects.get_or_create(name=nazwa)[0] for nazwa in names]
