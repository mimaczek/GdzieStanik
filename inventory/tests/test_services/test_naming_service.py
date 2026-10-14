"""
Testy unikalności nazw i sufiksów — reguły N1–N5, ADR-0002.
"""

import pytest

from inventory.models import Item, Location
from inventory.services import naming_service

pytestmark = pytest.mark.django_db


class TestN1WykrywanieZajetejNazwy:
    def test_wolna_nazwa(self, dom):
        assert naming_service.is_name_taken(dom, "Młotek") is False

    def test_zajeta_nazwa(self, dom, mlotek):
        assert naming_service.is_name_taken(dom, "Młotek") is True

    def test_porownanie_ignoruje_wielkosc_liter(self, dom, mlotek):
        assert naming_service.is_name_taken(dom, "MŁOTEK") is True

    def test_porownanie_ignoruje_ogonki(self, dom, mlotek):
        assert naming_service.is_name_taken(dom, "mlotek") is True

    def test_porownanie_ignoruje_spacje(self, dom, mlotek):
        assert naming_service.is_name_taken(dom, "  Młotek  ") is True

    def test_inny_dom_to_inna_przestrzen_nazw(self, domek, mlotek):
        """Unikalność dotyczy domu, nie całej bazy."""
        assert naming_service.is_name_taken(domek, "Młotek") is False

    def test_exclude_pk_pomija_edytowana_rzecz(self, dom, mlotek):
        """Bez tego każda edycja zgłaszałaby kolizję ze sobą samą."""
        assert (
            naming_service.is_name_taken(dom, "Młotek", exclude_pk=mlotek.pk) is False
        )


class TestN2PropozycjaSufiksu:
    def test_wolna_nazwa_zwracana_bez_zmian(self, dom):
        assert naming_service.suggest_name(dom, "Młotek") == "Młotek"

    def test_zajeta_dostaje_sufiks_2(self, dom, mlotek):
        assert naming_service.suggest_name(dom, "Młotek") == "Młotek_2"

    def test_kolejne_numery(self, dom, szafa, mlotek):
        Item.objects.create(name="Młotek_2", location=szafa, home=dom)
        assert naming_service.suggest_name(dom, "Młotek") == "Młotek_3"

    def test_sufiks_liczony_od_rdzenia(self, dom, szafa, mlotek):
        """Podanie „Młotek_2” numeruje dalej, nie tworzy „Młotek_2_2”."""
        Item.objects.create(name="Młotek_2", location=szafa, home=dom)
        assert naming_service.suggest_name(dom, "Młotek_2") == "Młotek_3"

    def test_nazwa_opisowa_nie_jest_wariantem(self, dom, szafa, mlotek):
        """„Młotek gumowy” to osobna rzecz, nie wariant „Młotka”."""
        Item.objects.create(name="Młotek gumowy", location=szafa, home=dom)
        assert naming_service.suggest_name(dom, "Młotek") == "Młotek_2"


class TestN3LicznikNieCofaSie:
    def test_luka_po_usunieciu_nie_jest_wypelniana(self, dom, szafa, mlotek):
        """
        Kluczowa reguła: po usunięciu „Młotek_2” kolejny dostaje
        „Młotek_4”, żeby numer nie wskazywał kiedyś innej rzeczy.
        """
        drugi = Item.objects.create(name="Młotek_2", location=szafa, home=dom)
        Item.objects.create(name="Młotek_3", location=szafa, home=dom)

        drugi.delete()

        assert naming_service.suggest_name(dom, "Młotek") == "Młotek_4"

    def test_po_usunieciu_wszystkich_wariantow(self, dom, szafa, mlotek):
        trzeci = Item.objects.create(name="Młotek_3", location=szafa, home=dom)
        trzeci.delete()
        # Zostaje „Młotek”, więc kolejny to _2
        assert naming_service.suggest_name(dom, "Młotek") == "Młotek_2"


class TestResolveName:
    def test_wolna_nazwa(self, dom):
        wolna, propozycja = naming_service.resolve_name(dom, "Wiertarka")
        assert wolna is True
        assert propozycja == "Wiertarka"

    def test_zajeta_nazwa_z_propozycja(self, dom, mlotek):
        wolna, propozycja = naming_service.resolve_name(dom, "Młotek")
        assert wolna is False
        assert propozycja == "Młotek_2"

    def test_ta_sama_nazwa_w_dwoch_domach(self, dom, domek, mlotek):
        """Scenariusz 5.7 — młotek może być w obu nieruchomościach."""
        garaz = Location.objects.create(name="Garaż", parent=domek)
        Item.objects.create(name="Młotek", location=garaz, home=domek)

        assert Item.objects.filter(name_norm="mlotek").count() == 2
