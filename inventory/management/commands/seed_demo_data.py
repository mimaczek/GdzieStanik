"""
Wgrywa przykładowe dane z docs/domain-model.md §8 — do szybkiego
sprawdzenia aplikacji na żywo, bez ręcznego klikania w panelu admina.

Użycie:

    python manage.py seed_demo_data

Domyślnie odmawia działania, gdy w bazie są już jakiekolwiek
lokalizacje — żeby przypadkiem nie zaśmiecić prawdziwych danych
domu. Wymuszenie (i skasowanie wszystkiego, co już jest):

    python manage.py seed_demo_data --reset

Dane tworzone są WYŁĄCZNIE przez warstwę services/, nie przez surowe
Model.objects.create() — tak samo jak zrobiłby to prawdziwy użytkownik
przez formularz albo panel administracyjny. Dzięki temu wygenerowane
dane automatycznie przechodzą te same reguły (unikalność nazw, zakaz
cykli, dokładnie jeden rodzic), które pilnuje aplikacja — więc nie da
się tą komendą wytworzyć stanu, którego nie dałoby się osiągnąć
normalnym użyciem.
"""

from __future__ import annotations

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from inventory.models import Location, Tag
from inventory.services import item_service, location_service

# get_user_model() zwraca typ dynamiczny, nieużywalny wprost jako
# adnotacja (django-stubs). AbstractUser jest wspólną klasą bazową
# wszystkich modeli użytkownika, w tym accounts.User (ADR-0007).
User = get_user_model()


class Command(BaseCommand):
    help = "Wgrywa przykładowe dane z domain-model.md §8 do szybkich testów."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Usuwa WSZYSTKIE istniejące lokalizacje i przedmioty przed wgraniem.",
        )

    def handle(self, *args, **options) -> None:
        if Location.objects.exists() and not options["reset"]:
            raise CommandError(
                "W bazie są już lokalizacje. Użyj --reset, żeby je "
                "skasować i wgrać dane demo od nowa (NIEODWRACALNE)."
            )

        if options["reset"]:
            self._wyczysc_wszystko()

        with transaction.atomic():
            domownicy = self._utworz_domownikow()
            self._utworz_dom_glowny(domownicy)
            self._utworz_domek_letniskowy()

        self.stdout.write(
            self.style.SUCCESS(
                "Gotowe. Wejdź na / i wyszukaj np. „ladowarka” (bez ogonków)."
            )
        )

    # ── Domownicy ────────────────────────────────────────────────

    def _utworz_domownikow(self) -> dict[str, AbstractUser]:
        """
        Dwoje przykładowych właścicieli z domain-model.md §8 — Anna
        i Michał. get_or_create, żeby --reset nie plątał się z kontami,
        które mogą być używane do prawdziwego logowania.

        UWAGA: konta tworzone są BEZ ustawionego hasła (set_unusable_
        password domyślnie przy tworzeniu bez create_user) — służą
        wyłącznie jako właściciele przedmiotów w danych demo, nie da
        się nimi zalogować. Do logowania użyj manage.py createsuperuser.
        """
        domownicy: dict[str, AbstractUser] = {}
        for login, display_name in [("anna", "Anna"), ("michal", "Michał")]:
            user, _ = User.objects.get_or_create(
                username=login, defaults={"display_name": display_name}
            )
            domownicy[login] = user
        return domownicy

    # ── Dom główny ───────────────────────────────────────────────

    def _utworz_dom_glowny(self, domownicy: dict[str, AbstractUser]) -> None:
        dom = location_service.create_location(name="Dom")

        parter = location_service.create_location(name="Parter", parent=dom)
        salon = location_service.create_location(name="Salon", parent=parter)
        komoda = location_service.create_location(name="Komoda", parent=salon)
        szuflada_gorna = location_service.create_location(
            name="Szuflada górna", parent=komoda
        )
        szuflada_dolna = location_service.create_location(
            name="Szuflada dolna", parent=komoda
        )

        item_service.create_item(
            name="dokumenty samochodowe",
            location=szuflada_gorna,
            tags=self._tagi("dokumenty"),
        )
        item_service.create_item(
            name="ładowarka USB-C",
            location=szuflada_gorna,
            quantity=2,
            tags=self._tagi("elektronika"),
        )
        item_service.create_item(
            name="obrusy",
            location=szuflada_dolna,
            quantity=4,
            owner=domownicy["anna"],
        )

        kuchnia = location_service.create_location(name="Kuchnia", parent=parter)
        szafka = location_service.create_location(
            name="Szafka pod zlewem", parent=kuchnia
        )
        item_service.create_item(
            name="worki na śmieci 60l",
            location=szafka,
            quantity=1,
            tags=self._tagi("chemia"),
        )

        pietro = location_service.create_location(name="Piętro", parent=dom)
        sypialnia = location_service.create_location(name="Sypialnia", parent=pietro)
        szafa = location_service.create_location(name="Szafa", parent=sypialnia)
        szafa.tags.add(*self._tagi("strefa-zimowa"))

        polka = location_service.create_location(name="Półka górna", parent=szafa)
        pudelko_zima = location_service.create_location(
            name="Pudełko „Zima”", parent=polka
        )

        item_service.create_item(
            name="czapki",
            location=pudelko_zima,
            quantity=3,
            tags=self._tagi("zimowe", "ubrania"),
        )

        # Przedmiot-pojemnik zagnieżdżony dwa poziomy (ADR-0001,
        # scenariusz 5.6 z vision.md) — spakowana walizka.
        walizka = item_service.create_item(
            name="walizka kabinowa", location=pudelko_zima
        )
        kosmetyczka = item_service.create_item(name="kosmetyczka", parent_item=walizka)
        item_service.create_item(name="szczoteczka podróżna", parent_item=kosmetyczka)
        item_service.create_item(
            name="adapter gniazdek",
            parent_item=walizka,
            tags=self._tagi("elektronika"),
        )

        piwnica = location_service.create_location(name="Piwnica", parent=dom)
        regal = location_service.create_location(name="Regał metalowy", parent=piwnica)
        pudelko_narzedzia = location_service.create_location(
            name="Pudełko „Elektronarzędzia”", parent=regal
        )

        item_service.create_item(
            name="wiertarka Bosch",
            location=pudelko_narzedzia,
            owner=domownicy["michal"],
            tags=self._tagi("narzędzia"),
        )
        item_service.create_item(
            name="ładowarka do wiertarki",
            location=pudelko_narzedzia,
            tags=self._tagi("narzędzia", "elektronika"),
        )

    # ── Domek letniskowy (druga nieruchomość) ───────────────────

    def _utworz_domek_letniskowy(self) -> None:
        """
        Osobny korzeń drzewa (W7) — dowodzi, że nazwa „młotek” wolna
        tu jest, mimo że w domu głównym jest zajęta przez inny
        przedmiot (gdyby był), bo unikalność dotyczy domu (N1),
        nie całej bazy.
        """
        domek = location_service.create_location(name="Domek letniskowy")
        garaz = location_service.create_location(name="Garaż", parent=domek)
        skrzynka = location_service.create_location(
            name="Skrzynka narzędziowa", parent=garaz
        )
        item_service.create_item(
            name="młotek", location=skrzynka, tags=self._tagi("narzędzia")
        )

    # ── Pomocnicze ───────────────────────────────────────────────

    def _wyczysc_wszystko(self) -> None:
        """
        Usuwa wszystkie lokalizacje i przedmioty przed wgraniem demo.

        Location.parent ma on_delete=PROTECT (reguła L3 — usunięcie
        niepustej lokalizacji wymaga świadomej decyzji), więc zwykłe
        Location.objects.all().delete() rzuca ProtectedError: Django
        próbuje skasować cały queryset naraz, a rodzic z dziećmi wciąż
        istniejącymi w tym samym poleceniu nie przechodzi.

        Rozwiązanie: usuwamy każdy dom osobno przez
        location_service.delete_location(force=True), które samo
        kasuje poddrzewo od liści w górę (zob. _descendants
        w location_service.py). Bezpieczne dla wielu domów (W7) —
        iterujemy po wszystkich korzeniach.
        """
        from inventory.services import location_service

        self.stdout.write("Usuwam istniejące dane...")
        for dom in list(Location.objects.filter(parent__isnull=True)):
            location_service.delete_location(dom, force=True)

    def _tagi(self, *names: str) -> list[Tag]:
        """get_or_create dla każdej nazwy — T2: tagi tworzą się automatycznie."""
        return [Tag.objects.get_or_create(name=nazwa)[0] for nazwa in names]
