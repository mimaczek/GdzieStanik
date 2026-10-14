"""
Testy ograniczeń bazy danych.

Weryfikują, że reguły domenowe są egzekwowane na poziomie schematu —
czyli że siatka bezpieczeństwa z reguły A4 faktycznie istnieje.

Walidacja aplikacyjna (warstwa services/) jest testowana osobno.
"""

import pytest
from django.db import IntegrityError, transaction

from inventory.models import Item, Location

pytestmark = pytest.mark.django_db


class TestP1DokladnieJedenRodzic:
    """P1: przedmiot leży w lokalizacji ALBO w przedmiocie."""

    def test_lokalizacja_jest_poprawna(self, dom, szafa):
        rzecz = Item.objects.create(name="Czapka", location=szafa, home=dom)
        assert rzecz.pk is not None

    def test_przedmiot_nadrzedny_jest_poprawny(self, dom, szafa):
        walizka = Item.objects.create(name="Walizka", location=szafa, home=dom)
        kosmetyczka = Item.objects.create(
            name="Kosmetyczka", parent_item=walizka, home=dom
        )
        assert kosmetyczka.location_id is None
        assert kosmetyczka.parent_item_id == walizka.pk

    def test_brak_rodzica_jest_odrzucany(self, dom):
        """Rzecz musi gdzieś leżeć — nie może wisieć w próżni."""
        with pytest.raises(IntegrityError), transaction.atomic():
            Item.objects.create(name="Sierota", home=dom)

    def test_dwaj_rodzice_sa_odrzucani(self, dom, szafa):
        """Nie można leżeć równocześnie w szafie i w walizce."""
        walizka = Item.objects.create(name="Walizka", location=szafa, home=dom)
        with pytest.raises(IntegrityError), transaction.atomic():
            Item.objects.create(
                name="Zdezorientowana",
                location=szafa,
                parent_item=walizka,
                home=dom,
            )


class TestP3IloscDodatnia:
    """P3: zużycie rzeczy to jej usunięcie, nie ustawienie zera."""

    def test_zero_jest_odrzucane(self, dom, szafa):
        with pytest.raises(IntegrityError), transaction.atomic():
            Item.objects.create(name="Nic", location=szafa, home=dom, quantity=0)

    def test_dodatnia_przechodzi(self, dom, szafa):
        rzecz = Item.objects.create(
            name="Skarpety", location=szafa, home=dom, quantity=5
        )
        assert rzecz.quantity == 5


class TestN1UnikalnoscWObrebieDomu:
    """N1: nazwa unikalna w granicach jednej nieruchomości."""

    def test_duplikat_w_tym_samym_domu_jest_odrzucany(self, dom, szafa, mlotek):
        with pytest.raises(IntegrityError), transaction.atomic():
            Item.objects.create(name="Młotek", location=szafa, home=dom)

    def test_rozna_wielkosc_liter_to_wciaz_duplikat(self, dom, szafa, mlotek):
        """Porównanie po name_norm, nie po surowej nazwie."""
        with pytest.raises(IntegrityError), transaction.atomic():
            Item.objects.create(name="MŁOTEK", location=szafa, home=dom)

    def test_brak_ogonkow_to_wciaz_duplikat(self, dom, szafa, mlotek):
        """„mlotek” i „młotek” to ta sama nazwa po normalizacji."""
        with pytest.raises(IntegrityError), transaction.atomic():
            Item.objects.create(name="mlotek", location=szafa, home=dom)

    def test_ta_sama_nazwa_w_innym_domu_jest_dozwolona(self, dom, szafa, domek, mlotek):
        """
        Kluczowy przypadek: unikalność dotyczy domu, nie całej bazy.
        Młotek w domku letniskowym to osobna, legalna rzecz.
        """
        garaz = Location.objects.create(name="Garaż", parent=domek)
        drugi = Item.objects.create(name="Młotek", location=garaz, home=domek)
        assert drugi.pk != mlotek.pk
        assert Item.objects.filter(name_norm="mlotek").count() == 2

    def test_sufiks_omija_kolizje(self, dom, szafa, mlotek):
        """N2: „młotek_2” to inna nazwa, więc przechodzi."""
        drugi = Item.objects.create(name="Młotek_2", location=szafa, home=dom)
        assert drugi.pk is not None


class TestL2UnikalnoscWsrodRodzenstwa:
    """L2: nazwa lokalizacji unikalna wśród rodzeństwa."""

    def test_duplikat_u_tego_samego_rodzica_jest_odrzucany(self, sypialnia):
        Location.objects.create(name="Szuflada", parent=sypialnia)
        with pytest.raises(IntegrityError), transaction.atomic():
            Location.objects.create(name="Szuflada", parent=sypialnia)

    def test_ta_sama_nazwa_u_innego_rodzica_jest_dozwolona(self, dom, sypialnia):
        """„Szuflada 2” może być w każdym meblu — rozróżnia je ścieżka."""
        kuchnia = Location.objects.create(name="Kuchnia", parent=dom)
        a = Location.objects.create(name="Szuflada", parent=sypialnia)
        b = Location.objects.create(name="Szuflada", parent=kuchnia)
        assert a.pk != b.pk


class TestL6UnikalnoscNazwDomow:
    """L6: nazwy korzeni unikalne globalnie."""

    def test_duplikat_domu_jest_odrzucany(self, dom):
        with pytest.raises(IntegrityError), transaction.atomic():
            Location.objects.create(name="Dom")

    def test_rozne_domy_przechodza(self, dom, domek):
        assert Location.objects.filter(parent__isnull=True).count() == 2

    def test_nazwa_domu_moze_sie_powtorzyc_nizej_w_drzewie(self, dom):
        """
        Ograniczenie dotyczy wyłącznie korzeni. Pokój nazwany „Dom”
        wewnątrz domu jest dziwny, ale dozwolony.
        """
        wnetrze = Location.objects.create(name="Dom", parent=dom)
        assert wnetrze.pk is not None


class TestG5NormalizacjaPrzyZapisie:
    """G5: name_norm wypełniane automatycznie przez sygnał."""

    def test_lokalizacja_dostaje_name_norm(self, dom):
        assert dom.name_norm == "dom"

    def test_przedmiot_dostaje_name_norm(self, mlotek):
        assert mlotek.name_norm == "mlotek"

    def test_zmiana_nazwy_aktualizuje_name_norm(self, mlotek):
        mlotek.name = "Łopata"
        mlotek.save()
        mlotek.refresh_from_db()
        assert mlotek.name_norm == "lopata"

    def test_przedmiot_dostaje_description_norm(self, dom, szafa):
        """
        W4 dotyczy też opisu, nie tylko nazwy (domain-model.md §4,
        pole nr 2). Bez description_norm wyszukiwanie po opisie bez
        polskich znaków prawie nigdy by nie trafiało.
        """
        rzecz = Item.objects.create(
            name="Coś", description="leży obok narzędziowni", location=szafa, home=dom
        )
        assert rzecz.description_norm == "lezy obok narzedziowni"

    def test_pusty_opis_daje_pusty_description_norm(self, mlotek):
        assert mlotek.description_norm == ""


class TestP9KazdyPrzedmiotMozeBycPojemnikiem:
    """P9: brak flagi „jest pojemnikiem”."""

    def test_pusty_przedmiot_nie_jest_pojemnikiem(self, mlotek):
        assert mlotek.is_container is False

    def test_przedmiot_z_zawartoscia_jest_pojemnikiem(self, dom, szafa):
        walizka = Item.objects.create(name="Walizka", location=szafa, home=dom)
        Item.objects.create(name="Szczoteczka", parent_item=walizka, home=dom)
        assert walizka.is_container is True

    def test_dowolna_rzecz_przyjmuje_zawartosc(self, dom, szafa, mlotek):
        """Nawet młotek — nie trzeba niczego deklarować z góry."""
        Item.objects.create(name="Naklejka", parent_item=mlotek, home=dom)
        assert mlotek.is_container is True


class TestP4UsuniecieWlascicielaZachowujeRzeczy:
    def test_rzecz_zostaje_po_usunieciu_wlasciciela(
        self, dom, szafa, django_user_model
    ):
        anna = django_user_model.objects.create_user(username="anna", password="x")
        rower = Item.objects.create(name="Rower", location=szafa, home=dom, owner=anna)
        anna.delete()
        rower.refresh_from_db()
        assert rower.owner is None
        assert rower.name == "Rower"


class TestP5KaskadoweUsuwaniePojemnika:
    def test_usuniecie_pojemnika_usuwa_zawartosc(self, dom, szafa):
        walizka = Item.objects.create(name="Walizka", location=szafa, home=dom)
        Item.objects.create(name="Kosmetyczka", parent_item=walizka, home=dom)
        walizka.delete()
        assert not Item.objects.filter(name="Kosmetyczka").exists()

    def test_kaskada_siega_glebiej(self, dom, szafa):
        """Usunięcie walizki usuwa też rzeczy w kosmetyczce w środku."""
        walizka = Item.objects.create(name="Walizka", location=szafa, home=dom)
        kosmetyczka = Item.objects.create(
            name="Kosmetyczka", parent_item=walizka, home=dom
        )
        Item.objects.create(name="Szczoteczka", parent_item=kosmetyczka, home=dom)
        walizka.delete()
        assert Item.objects.count() == 0


class TestL3UsuniecieNiepustejLokalizacji:
    """
    L3: usunięcie lokalizacji z zawartością wymaga świadomej decyzji.

    PROTECT wymusza przejście przez serwis, który zapyta o los
    zawartości — zamiast cicho usunąć.
    """

    def test_lokalizacja_z_podlokalizacja_jest_chroniona(self, sypialnia, szafa):
        from django.db.models import ProtectedError

        with pytest.raises(ProtectedError), transaction.atomic():
            sypialnia.delete()

    def test_lokalizacja_z_rzeczami_jest_chroniona(self, szafa, mlotek):
        from django.db.models import ProtectedError

        with pytest.raises(ProtectedError), transaction.atomic():
            szafa.delete()

    def test_pusta_lokalizacja_usuwa_sie_normalnie(self, dom):
        pusta = Location.objects.create(name="Pusty pokój", parent=dom)
        pusta.delete()
        assert not Location.objects.filter(name="Pusty pokój").exists()
