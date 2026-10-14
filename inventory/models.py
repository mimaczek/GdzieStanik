"""
Modele domeny GdzieStanik.

Odpowiadają encjom z docs/domain-model.md. Identyfikatory reguł
(L1–L6, P1–P11, N1–N5, T1–T4) w komentarzach odsyłają do tego dokumentu.

Ograniczenia bazy to siatka bezpieczeństwa — główna walidacja odbywa się
w warstwie services/ (reguła A4 z architecture.md).
"""

from __future__ import annotations

import uuid
from pathlib import Path

from django.conf import settings
from django.db import models
from django.db.models import Q


def photo_upload_path(instance: models.Model, filename: str) -> str:
    """
    Ścieżka zapisu zdjęcia: photos/{rok}/{miesiąc}/{uuid}.webp

    Podział na rok i miesiąc zapobiega powstaniu jednego katalogu
    z tysiącami plików. Nazwa z UUID — oryginalna nazwa pliku z telefonu
    nie niesie informacji, a mogłaby zawierać niebezpieczne znaki.
    """
    from django.utils import timezone

    teraz = timezone.now()
    rozszerzenie = Path(filename).suffix.lower() or ".webp"
    return f"photos/{teraz:%Y}/{teraz:%m}/{uuid.uuid4().hex}{rozszerzenie}"


class TimestampedModel(models.Model):
    """
    Pola audytowe wspólne dla encji (reguła G1).

    Namiastka pełnego dziennika zmian, który jest poza zakresem v1.
    Pozwala odpowiedzieć na pytanie „kto to ostatnio ruszał?”.
    """

    created_at = models.DateTimeField("utworzono", auto_now_add=True)
    updated_at = models.DateTimeField("zmieniono", auto_now=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="zmienił",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
        editable=False,
    )

    class Meta:
        abstract = True


class Tag(models.Model):
    """
    Etykieta grupująca rzeczy niezależnie od miejsca (§3.3).

    T4: wspólna pula dla przedmiotów i lokalizacji.
    """

    name = models.CharField("nazwa", max_length=50)
    # T1: unikalność po postaci znormalizowanej
    name_norm = models.CharField(max_length=50, unique=True, editable=False)

    class Meta:
        verbose_name = "tag"
        verbose_name_plural = "tagi"
        ordering = ["name_norm"]

    def __str__(self) -> str:
        return self.name


class Location(TimestampedModel):
    """
    Miejsce: dom, pokój, mebel, półka, pojemnik (§3.1).

    Jeden typ dla wszystkich poziomów — różni je tylko miejsce
    w drzewie i opcjonalny rodzaj.

    Lokalizacja bez rodzica jest domem (L6).
    """

    class Kind(models.TextChoices):
        HOME = "dom", "dom"
        ROOM = "pokoj", "pokój"
        FURNITURE = "mebel", "mebel"
        SHELF = "polka", "półka"
        DRAWER = "szuflada", "szuflada"
        CONTAINER = "pojemnik", "pojemnik"
        OTHER = "inne", "inne"

    name = models.CharField("nazwa", max_length=100)
    name_norm = models.CharField(max_length=100, editable=False, db_index=True)

    parent = models.ForeignKey(
        "self",
        verbose_name="znajduje się w",
        null=True,
        blank=True,
        # PROTECT, bo usunięcie musi przejść przez serwis,
        # który zapyta o los zawartości (L3)
        on_delete=models.PROTECT,
        related_name="children",
        help_text="Puste oznacza osobny dom lub nieruchomość.",
    )

    kind = models.CharField(
        "rodzaj",
        max_length=20,
        choices=Kind,
        blank=True,
        help_text="Tylko podpowiedź wizualna — nie ogranicza zagnieżdżania (L5).",
    )

    description = models.TextField(
        "opis", blank=True, help_text="Np. „ta wysoka przy oknie”."
    )

    photo = models.ImageField("zdjęcie", upload_to=photo_upload_path, blank=True)

    sort_order = models.IntegerField("kolejność", default=0)

    tags = models.ManyToManyField(
        Tag, verbose_name="tagi", blank=True, related_name="locations"
    )

    class Meta:
        verbose_name = "lokalizacja"
        verbose_name_plural = "lokalizacje"
        ordering = ["sort_order", "name_norm"]
        constraints = [
            # L2: nazwa unikalna wśród rodzeństwa.
            # Nie obejmuje korzeni, bo SQLite traktuje każdy NULL
            # jako wartość różną — stąd osobne ograniczenie poniżej.
            models.UniqueConstraint(
                fields=["parent", "name_norm"],
                condition=Q(parent__isnull=False),
                name="uq_location_sibling",
            ),
            # L6: nazwy domów unikalne globalnie
            models.UniqueConstraint(
                fields=["name_norm"],
                condition=Q(parent__isnull=True),
                name="uq_home_name",
            ),
        ]
        indexes = [
            models.Index(fields=["parent"], name="ix_location_parent"),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def is_home(self) -> bool:
        """Lokalizacja bez rodzica jest domem (L6)."""
        return self.parent_id is None


class Item(TimestampedModel):
    """
    Rzecz przechowywana w domu (§3.2).

    P1: leży w lokalizacji ALBO w innym przedmiocie — dokładnie jedno
    z dwóch. Spakowana walizka pozostaje przedmiotem, a mimo to
    zawiera inne rzeczy (ADR-0001).
    """

    name = models.CharField("nazwa", max_length=200)
    name_norm = models.CharField(max_length=200, editable=False, db_index=True)

    description = models.TextField("opis", blank=True)
    # W4 dotyczy też opisu (jest pozycją nr 2 wśród przeszukiwanych pól,
    # domain-model.md §4) — bez tej kolumny filtr porównywałby
    # znormalizowane zapytanie z surowym, ogonkowym tekstem i prawie
    # nigdy by nie trafił.
    description_norm = models.TextField(editable=False, blank=True)

    quantity = models.PositiveIntegerField(
        "ilość",
        default=1,
        help_text="Liczba sztuk w tym jednym miejscu. Ta sama rzecz "
        "w innym miejscu to osobny wpis (P1).",
    )

    # ── Rodzic: dokładnie jeden z dwóch (P1) ──────────────────────

    location = models.ForeignKey(
        Location,
        verbose_name="leży w",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="items",
    )

    parent_item = models.ForeignKey(
        "self",
        verbose_name="w środku",
        null=True,
        blank=True,
        # P5: usunięcie pojemnika usuwa zawartość.
        # Serwis MUSI wcześniej pokazać potwierdzenie z liczbą rzeczy —
        # kaskada w bazie działa po cichu.
        on_delete=models.CASCADE,
        related_name="contents",
        help_text="Wypełnione, gdy rzecz leży w innym przedmiocie, np. w walizce.",
    )

    # P7: denormalizacja — dom wyliczany przy zapisie.
    # Potrzebny do walidacji unikalności nazw (N1) bez wchodzenia
    # po drzewie przy każdej operacji.
    home = models.ForeignKey(
        Location,
        verbose_name="dom",
        on_delete=models.CASCADE,
        related_name="+",
        editable=False,
    )

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="właściciel",
        null=True,
        blank=True,
        # P4: usunięcie użytkownika nie usuwa jego rzeczy
        on_delete=models.SET_NULL,
        related_name="owned_items",
        help_text="Puste oznacza rzecz wspólną.",
    )

    photo = models.ImageField("zdjęcie", upload_to=photo_upload_path, blank=True)

    tags = models.ManyToManyField(
        Tag, verbose_name="tagi", blank=True, related_name="items"
    )

    class Meta:
        verbose_name = "przedmiot"
        verbose_name_plural = "przedmioty"
        ordering = ["name_norm"]
        constraints = [
            # P1: dokładnie jeden rodzic
            models.CheckConstraint(
                condition=(
                    Q(location__isnull=False, parent_item__isnull=True)
                    | Q(location__isnull=True, parent_item__isnull=False)
                ),
                name="ck_item_single_parent",
                violation_error_message=(
                    "Przedmiot musi leżeć w lokalizacji albo w innym "
                    "przedmiocie — dokładnie jedno z dwóch."
                ),
            ),
            # P3: ilość większa od zera
            models.CheckConstraint(
                condition=Q(quantity__gt=0),
                name="ck_item_quantity_positive",
                violation_error_message="Ilość musi być większa od zera.",
            ),
            # N1: nazwa unikalna w obrębie domu
            models.UniqueConstraint(
                fields=["home", "name_norm"],
                name="uq_item_home_name",
                violation_error_message=("Rzecz o tej nazwie już istnieje w tym domu."),
            ),
        ]
        indexes = [
            models.Index(fields=["location"], name="ix_item_location"),
            models.Index(fields=["parent_item"], name="ix_item_parent"),
            models.Index(fields=["home", "name_norm"], name="ix_item_home_name"),
        ]

    def __str__(self) -> str:
        if self.quantity > 1:
            return f"{self.name} ({self.quantity} szt.)"
        return self.name

    @property
    def is_container(self) -> bool:
        """
        Czy coś zawiera.

        P9: nie ma flagi „jest pojemnikiem” — każdy przedmiot może
        przyjąć zawartość. To pytanie o stan faktyczny, nie o typ.
        """
        return self.contents.exists()
