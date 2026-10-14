"""
Formularze własnych widoków (nie panelu administracyjnego — tam są
osobne formularze w admin.py).

Walidacja domenowa (P1, P6, N1) jest tu w clean(), analogicznie do
admin.py — Django wywołuje clean() przed zapisem, więc błąd wraca
jako czytelny komunikat pod polem zamiast wyjątku w widoku.
"""

from __future__ import annotations

from typing import cast

from django import forms

from .exceptions import CycleError, DomainError
from .models import Item, Location
from .services import naming_service, path_service
from .services.item_service import resolve_home


class LocationChoiceField(forms.ModelChoiceField):
    """
    Lista lokalizacji z pełną ścieżką zamiast samej nazwy — bez tego
    dwie lokalizacje o nazwie „Szuflada” w różnych meblach byłyby
    nie do odróżnienia na liście rozwijanej.
    """

    def label_from_instance(self, obj: Location) -> str:
        return path_service.format_path(path_service.path_for_location(obj))


class AddItemForm(forms.Form):
    """
    Szybkie dodanie rzeczy (scenariusz 5.2 z vision.md) — minimum pól,
    żeby działało jedną ręką w trakcie porządków (reguła P2: jedyne
    wymagane pole to nazwa, reszta opcjonalna).
    """

    name = forms.CharField(label="Nazwa", max_length=200)
    location = LocationChoiceField(
        label="Gdzie",
        queryset=Location.objects.all(),
        required=True,
        help_text="Dom jest też lokalizacją — można wybrać wprost jego (P11).",
    )
    quantity = forms.IntegerField(label="Ilość", min_value=1, initial=1)
    description = forms.CharField(
        label="Opis", required=False, widget=forms.Textarea(attrs={"rows": 2})
    )
    photo = forms.ImageField(label="Zdjęcie", required=False)
    tags = forms.CharField(
        label="Tagi",
        required=False,
        help_text="Oddzielone przecinkami, np. „zimowe, ubrania”.",
    )

    def __init__(self, *args, accept_suggested_name: bool = False, **kwargs):
        """
        accept_suggested_name=True pomija błąd kolizji i podmienia
        nazwę w cleaned_data na propozycję z sufiksem (N2) — ustawiane
        przez widok, gdy użytkownik kliknął przycisk „użyj tej nazwy”.
        """
        self.accept_suggested_name = accept_suggested_name
        self.suggested_name: str | None = None
        super().__init__(*args, **kwargs)
        # Sortowanie po ścieżce, nie po nazwie — żeby lista była
        # pogrupowana wizualnie wg drzewa, nie alfabetycznie wymieszana.
        # self.fields ma typ dict[str, Field] (unia wszystkich pól
        # formularza) — rzutowanie, bo wiemy, że to konkretnie
        # ModelChoiceField zdefiniowane wyżej.
        location_field = cast(forms.ModelChoiceField, self.fields["location"])
        location_field.queryset = Location.objects.select_related("parent").order_by(
            "name_norm"
        )

    def clean(self):
        """
        Walidacja N1 PRZED zapisem — ten sam wzorzec co w admin.py
        (ItemForm.clean): błąd tutaj wraca jako komunikat pod polem
        „name” ze statusem 200, nie jako wyjątek w widoku.
        """
        dane = super().clean()
        if self.errors:
            return dane

        location = dane.get("location")
        name = dane.get("name")
        if not location or not name:
            return dane

        try:
            home = resolve_home(location, None)
        except DomainError as exc:
            self.add_error(None, str(exc))
            return dane

        wolna, propozycja = naming_service.resolve_name(home, name)
        if not wolna:
            if self.accept_suggested_name:
                # Użytkownik już zaakceptował sufiks — podmieniamy
                # nazwę w cleaned_data, żeby widok zapisał „Młotek_2”,
                # nie oryginalne „Młotek” (które i tak by się nie zapisało).
                dane["name"] = propozycja
            else:
                self.add_error(
                    "name",
                    f"Nazwa „{name}” jest już zajęta w tym domu ({home.name}). "
                    f"Spróbuj: „{propozycja}”.",
                )
                # Propozycja zapamiętana, żeby widok mógł zaoferować
                # przycisk „użyj tej nazwy” bez ponownego liczenia (N2).
                self.suggested_name = propozycja

        return dane

    def clean_tags(self) -> list[str]:
        surowe = self.cleaned_data.get("tags", "")
        return [t.strip() for t in surowe.split(",") if t.strip()]


class MoveItemForm(forms.Form):
    """
    Przeniesienie rzeczy — nowa lokalizacja ALBO nowy przedmiot-rodzic
    (P1), nigdy oba naraz. Obsługuje kolizję nazwy przy przenosinach
    między domami (N5).
    """

    location = LocationChoiceField(
        label="Nowa lokalizacja", queryset=Location.objects.all(), required=False
    )
    parent_item = forms.ModelChoiceField(
        label="Włóż do przedmiotu",
        queryset=Item.objects.all(),
        required=False,
        help_text="Np. do walizki — rzecz nadal można znaleźć w wyszukiwaniu.",
    )

    def __init__(self, *args, item: Item, **kwargs):
        self.item = item
        super().__init__(*args, **kwargs)

        location_field = cast(forms.ModelChoiceField, self.fields["location"])
        location_field.queryset = Location.objects.select_related("parent").order_by(
            "name_norm"
        )

        # Przedmiot nie może stać się własnym rodzicem — wykluczenie
        # tutaj jest tylko wygodą UI, twarda walidacja cyklu (P6)
        # i tak jest w clean() niżej i w path_service.
        parent_item_field = cast(forms.ModelChoiceField, self.fields["parent_item"])
        parent_item_field.queryset = Item.objects.exclude(pk=item.pk).select_related(
            "home"
        )

    def clean(self):
        dane = super().clean()
        if self.errors:
            return dane

        location = dane.get("location")
        parent_item = dane.get("parent_item")

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
                "Wybierz nową lokalizację albo przedmiot, do którego włożyć rzecz.",
            )
            return dane

        if parent_item is not None:
            try:
                path_service.check_item_cycle(self.item, parent_item)
            except CycleError as exc:
                self.add_error("parent_item", str(exc))
                return dane

        try:
            nowy_dom = resolve_home(location, parent_item)
        except DomainError as exc:
            self.add_error(None, str(exc))
            return dane

        if nowy_dom.pk != self.item.home_id:
            wolna, propozycja = naming_service.resolve_name(
                nowy_dom, self.item.name, exclude_pk=self.item.pk
            )
            if not wolna:
                self.add_error(
                    None,
                    f"W „{nowy_dom.name}” już jest rzecz o nazwie "
                    f"„{self.item.name}”. Zmień najpierw nazwę na "
                    f"np. „{propozycja}”, żeby przenieść.",
                )

        return dane
