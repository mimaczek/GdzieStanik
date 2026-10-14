"""
Panel administracyjny — zarządzanie strukturą domu i kontami (ADR-0007).

REGUŁA A5 (architecture.md §2): zapisy i usunięcia muszą przechodzić
przez warstwę services/, nigdy bezpośrednio przez ORM. Admin Django
domyślnie robi to drugie — bez poniższych nadpisań ominąłby:

  - wykrywanie cykli (L1, P6)
  - wyliczanie i propagację pola home (P7, P8)
  - unikalność nazw z propozycją sufiksu (N1, N2)
  - sprawdzenie zawartości przed usunięciem (L3, P5)

Walidacja domenowa jest w ModelForm.clean(), NIE w save_model().
Django wywołuje clean() przed save_model() — błąd zgłoszony w clean()
wraca jako zwykły błąd formularza (status 200, czytelny komunikat
pod polem). Błąd rzucony dopiero w save_model() jest już po stronie
zapisu i Django nie potrafi go ładnie obsłużyć — kończy się
nieobsłużonym wyjątkiem zamiast formularza do poprawy.

save_model() i delete_model() zakładają, że dane przeszły już clean()
i wykonują operację przez serwisy — pełnią rolę wykonawcy, nie bramki
walidacyjnej.

Testy tej reguły są w inventory/tests/test_admin/test_rule_a5.py.
"""

from __future__ import annotations

from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.db import models as db_models
from django.forms import ModelForm, Textarea
from django.http import HttpRequest

from . import services
from .exceptions import CycleError, DomainError, NotEmptyError
from .models import Item, Location, Tag
from .services import path_service

# ─────────────────────────────────────────────────────────────────
# Tag
# ─────────────────────────────────────────────────────────────────


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ["name", "item_count", "location_count"]
    search_fields = ["name_norm"]
    readonly_fields = ["name_norm"]

    @admin.display(description="przedmioty")
    def item_count(self, obj: Tag) -> int:
        return obj.items.count()

    @admin.display(description="lokalizacje")
    def location_count(self, obj: Tag) -> int:
        return obj.locations.count()


# ─────────────────────────────────────────────────────────────────
# Location
# ─────────────────────────────────────────────────────────────────


class LocationForm(ModelForm):
    class Meta:
        model = Location
        fields = [
            "name",
            "parent",
            "kind",
            "description",
            "photo",
            "sort_order",
            "tags",
        ]
        widgets = {"description": Textarea(attrs={"rows": 3})}

    def clean(self):
        """
        Walidacja domenowa PRZED zapisem (zob. nota o regule A5 u góry
        pliku). Cykl (L1) musi być wykryty tutaj, nie w save_model —
        inaczej operator dostałby błąd 500 zamiast formularza z opisem
        problemu pod polem „parent”.
        """
        dane = super().clean()
        parent = dane.get("parent")

        if self.instance.pk and parent is not None:
            try:
                path_service.check_location_cycle(self.instance, parent)
            except CycleError as exc:
                self.add_error("parent", str(exc))

        return dane


class LocationChildrenInline(admin.TabularInline):
    """Podgląd bezpośredniej zawartości — bez edycji, tylko orientacja."""

    model = Location
    fk_name = "parent"
    extra = 0
    fields = ["name", "kind"]
    readonly_fields = ["name", "kind"]
    can_delete = False
    verbose_name_plural = "zawarte lokalizacje"

    def has_add_permission(self, request: HttpRequest, obj=None) -> bool:
        return False


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    form = LocationForm
    list_display = ["full_path_display", "kind", "item_count", "updated_at"]
    list_filter = ["kind"]
    search_fields = ["name_norm"]
    # raw_id_fields zamiast listy rozwijanej — przy tysiącach lokalizacji
    # standardowy <select> byłby bardzo wolny (architecture.md §6)
    raw_id_fields = ["parent"]
    # full_path_display jako readonly_fields trafia na koniec formularza
    # automatycznie (Django dokłada readonly_fields do domyślnych
    # fieldsets, gdy nie są one zdefiniowane jawnie) — nie trzeba
    # nadpisywać get_fieldsets.
    readonly_fields = [
        "full_path_display",
        "name_norm",
        "created_at",
        "updated_at",
        "updated_by",
    ]
    list_select_related = ["parent"]
    inlines = [LocationChildrenInline]

    @admin.display(description="pełna ścieżka")
    def full_path_display(self, obj: Location) -> str:
        """
        Pełna ścieżka od domu włącznie z samą lokalizacją.

        Przy dodawaniu nowej lokalizacji (obj.pk is None) nie ma jeszcze
        czego pokazać — path_service operuje na obiektach już zapisanych
        w drzewie.
        """
        if obj.pk is None:
            return "—"
        return path_service.format_path(path_service.path_for_location(obj))

    @admin.display(description="rzeczy")
    def item_count(self, obj: Location) -> int:
        return obj.items.count()

    # ── Reguła A5 ──────────────────────────────────────────────

    def save_model(
        self, request: HttpRequest, obj: Location, form: LocationForm, change: bool
    ) -> None:
        """
        Wykonuje zapis przez services.location_service.

        Walidacja cyklu (L1) już się odbyła w LocationForm.clean() —
        tutaj zakładamy, że obj.parent jest bezpieczny do zapisania.
        Przy edycji z nowym rodzicem wołamy move_location, które
        propaguje home do całej zawartości (P7) — pominięcie tego
        kroku zostawiłoby dane w niespójnym stanie.
        """
        if not change:
            nowa = services.location_service.create_location(
                name=obj.name,
                parent=obj.parent,
                kind=obj.kind,
                description=obj.description,
                updated_by=request.user,
            )
            obj.pk = nowa.pk
            return

        stara = Location.objects.get(pk=obj.pk)
        if stara.parent_id != obj.parent_id:
            services.location_service.move_location(
                stara, obj.parent, updated_by=request.user
            )

        # Pola bez wpływu na drzewo — zwykły zapis wystarczy,
        # ale przez metodę modelu, nie przez cichy UPDATE
        stara.refresh_from_db()
        stara.kind = obj.kind
        stara.description = obj.description
        stara.sort_order = obj.sort_order
        # request.user jest zawsze zalogowanym User w adminie (is_staff
        # wymagane), nigdy AnonymousUser — django-stubs tego nie widzi.
        stara.updated_by = request.user  # type: ignore[assignment]
        if obj.photo:
            stara.photo = obj.photo
        stara.full_clean(exclude=["name_norm", "home"])
        stara.save()

    def delete_model(self, request: HttpRequest, obj: Location) -> None:
        """
        Odmawia usunięcia niepustej lokalizacji (L3) zamiast kasować
        po cichu razem z całą zawartością.
        """
        try:
            services.location_service.delete_location(obj)
        except NotEmptyError as exc:
            messages.error(
                request,
                f"{exc} Użyj widoku przenoszenia, żeby najpierw opróżnić "
                f"lokalizację, albo usuń zawartość ręcznie.",
            )
            raise ValidationError(str(exc)) from exc

    def delete_queryset(self, request: HttpRequest, queryset) -> None:
        """Usuwanie masowe idzie przez tę samą ścieżkę co pojedyncze."""
        for obj in queryset:
            self.delete_model(request, obj)


# ─────────────────────────────────────────────────────────────────
# Item
# ─────────────────────────────────────────────────────────────────


class ItemForm(ModelForm):
    class Meta:
        model = Item
        fields = [
            "name",
            "description",
            "quantity",
            "location",
            "parent_item",
            "owner",
            "photo",
            "tags",
        ]
        widgets = {"description": Textarea(attrs={"rows": 3})}

    def clean(self):
        """
        Walidacja domenowa PRZED zapisem (zob. nota o regule A5 u góry
        pliku) — P1, P6 i N1 muszą być sprawdzone tutaj, żeby operator
        dostał czytelny błąd pod właściwym polem zamiast błędu 500
        albo surowego IntegrityError z bazy.
        """
        dane = super().clean()
        if self.errors:
            return dane  # pola podstawowe już błędne — nie komplikujemy

        location = dane.get("location")
        parent_item = dane.get("parent_item")
        name = dane.get("name")

        if location and parent_item:
            self.add_error(
                "parent_item",
                "Rzecz może leżeć w lokalizacji albo w innym przedmiocie, "
                "nie w obu naraz (P1).",
            )
            return dane

        if not location and not parent_item:
            self.add_error(
                "location",
                "Rzecz musi leżeć w lokalizacji albo w innym przedmiocie (P1).",
            )
            return dane

        if self.instance.pk and parent_item is not None:
            try:
                path_service.check_item_cycle(self.instance, parent_item)
            except CycleError as exc:
                self.add_error("parent_item", str(exc))
                return dane

        try:
            home = services.item_service.resolve_home(location, parent_item)
        except DomainError as exc:
            self.add_error(None, str(exc))
            return dane

        if name:
            wolna, propozycja = services.naming_service.resolve_name(
                home, name, exclude_pk=self.instance.pk
            )
            if not wolna:
                self.add_error(
                    "name",
                    f"Nazwa „{name}” jest już zajęta w tym domu. "
                    f"Spróbuj: „{propozycja}”.",
                )

        return dane


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    form = ItemForm
    list_display = [
        "name",
        "full_path_display",
        "quantity",
        "owner",
        "is_container_display",
    ]
    list_filter = ["home", "owner"]
    search_fields = ["name_norm"]
    raw_id_fields = ["location", "parent_item", "owner"]
    readonly_fields = [
        "full_path_display",
        "name_norm",
        "home",
        "created_at",
        "updated_at",
        "updated_by",
    ]
    list_select_related = ["home", "owner"]
    formfield_overrides = {
        db_models.TextField: {"widget": Textarea(attrs={"rows": 3})},
    }

    @admin.display(description="pełna ścieżka")
    def full_path_display(self, obj: Item) -> str:
        """
        Ścieżka do miejsca, w którym rzecz leży, bez nazwy samej rzeczy
        — ta sama konwencja co w wynikach wyszukiwania
        (search_service.SearchResult.path vs full_path).

        Przechodzi przez przedmioty-pojemniki (ADR-0001), np.:
        „Dom › Sypialnia › Szafa › Walizka”.
        """
        if obj.pk is None:
            return "—"
        return path_service.format_path(path_service.path_for_item(obj))

    @admin.display(description="pojemnik", boolean=True)
    def is_container_display(self, obj: Item) -> bool:
        return obj.is_container

    # ── Reguła A5 ──────────────────────────────────────────────

    def save_model(
        self, request: HttpRequest, obj: Item, form: ItemForm, change: bool
    ) -> None:
        """
        Wykonuje zapis przez services.item_service.

        Walidacja P1, P6 i N1 już się odbyła w ItemForm.clean() —
        dotarcie tutaj oznacza, że dane są poprawne. Wyjątek mógłby
        się pojawić tylko przy rzadkim wyścigu (ktoś dodał kolidującą
        nazwę między walidacją a zapisem) — wtedy pokazujemy komunikat
        i przerywamy, zamiast zapisywać niespójne dane.
        """
        tagi = list(form.cleaned_data.get("tags", []))
        try:
            if not change:
                nowy = services.item_service.create_item(
                    name=obj.name,
                    location=obj.location,
                    parent_item=obj.parent_item,
                    quantity=obj.quantity,
                    description=obj.description,
                    owner=obj.owner,
                    tags=tagi,
                    updated_by=request.user,
                )
                obj.pk = nowy.pk
                obj.home = nowy.home
                return

            stary = Item.objects.get(pk=obj.pk)
            zmiana_miejsca = (
                stary.location_id != obj.location_id
                or stary.parent_item_id != obj.parent_item_id
            )
            zmiana_nazwy = stary.name != obj.name

            if zmiana_miejsca:
                services.item_service.move_item(
                    stary,
                    location=obj.location,
                    parent_item=obj.parent_item,
                    updated_by=request.user,
                )
            if zmiana_nazwy:
                services.item_service.rename_item(
                    stary, obj.name, updated_by=request.user
                )

            stary.refresh_from_db()
            stary.description = obj.description
            stary.quantity = obj.quantity
            stary.owner = obj.owner
            # request.user jest zawsze zalogowanym User (patrz komentarz
            # w LocationAdmin.save_model wyżej w pliku)
            stary.updated_by = request.user  # type: ignore[assignment]
            if obj.photo:
                stary.photo = obj.photo
            stary.full_clean(exclude=["name_norm", "home"])
            stary.save()
            stary.tags.set(tagi)
        except DomainError as exc:
            # Rzadki wyścig — clean() przeszedł, ale stan zmienił się
            # tuż przed zapisem. Transakcja na poziomie widoku admina
            # i tak nie zacommituje częściowych zmian.
            messages.error(
                request,
                f"Zapis nie powiódł się: {exc}. Odśwież stronę i spróbuj ponownie.",
            )
            raise ValidationError(str(exc)) from exc

    def delete_model(self, request: HttpRequest, obj: Item) -> None:
        """
        Usuwa przez services.item_service, żeby operator zobaczył
        ostrzeżenie o liczbie rzeczy wewnątrz pojemnika (P5) zamiast
        cichej kaskady.
        """
        liczba_wewnatrz = services.item_service.count_contents(obj)
        if liczba_wewnatrz:
            messages.warning(
                request,
                f"Usunięto „{obj.name}” wraz z {liczba_wewnatrz} rzeczami w środku.",
            )
        services.item_service.delete_item(obj)

    def delete_queryset(self, request: HttpRequest, queryset) -> None:
        for obj in queryset:
            self.delete_model(request, obj)
