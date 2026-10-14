"""
Sygnały wypełniające kolumny znormalizowane (reguła G5).

Dlaczego sygnał, a nie metoda save():
  - działa też przy zapisach z panelu administracyjnego,
  - działa przy bulk_create z ustawionym pre_save,
  - nie da się pominąć przez zapomnienie w nowym miejscu w kodzie.

Zobacz docs/architecture.md §5.1.
"""

from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import Item, Location, Tag
from .normalization import normalize


@receiver(pre_save, sender=Location)
@receiver(pre_save, sender=Item)
@receiver(pre_save, sender=Tag)
def fill_name_norm(sender, instance, **kwargs) -> None:
    """
    Wypełnia name_norm przed każdym zapisem.

    Obsługuje wszystkie trzy modele — pole nazywa się tak samo,
    a logika jest identyczna.
    """
    instance.name_norm = normalize(instance.name)


@receiver(pre_save, sender=Item)
def fill_description_norm(sender, instance: Item, **kwargs) -> None:
    """
    Wypełnia description_norm — potrzebne do wyszukiwania po opisie
    odpornego na brak polskich znaków (W4). Bez tego porównanie
    znormalizowanego zapytania z surowym opisem prawie nigdy nie trafia.
    """
    instance.description_norm = normalize(instance.description)
