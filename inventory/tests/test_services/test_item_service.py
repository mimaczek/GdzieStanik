"""
Testy operacji na przedmiotach — reguły P1, P5, P7, P8, P11, N2, N4, N5.
"""

import pytest

from inventory.exceptions import (
    CycleError,
    InvalidParentError,
    NameCollisionError,
)
from inventory.models import Item, Location
from inventory.services import item_service, path_service

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def czysty_cache():
    path_service.invalidate_tree()
    yield
    path_service.invalidate_tree()


class TestTworzenie:
    def test_rzecz_w_lokalizacji(self, dom, szafa):
        rzecz = item_service.create_item(name="Czapka", location=szafa)
        assert rzecz.home_id == dom.pk
        assert rzecz.location_id == szafa.pk
        assert rzecz.parent_item_id is None

    def test_rzecz_w_pojemniku(self, dom, szafa):
        walizka = item_service.create_item(name="Walizka", location=szafa)
        w_srodku = item_service.create_item(name="Pasta", parent_item=walizka)
        assert w_srodku.home_id == dom.pk
        assert w_srodku.location_id is None
        assert w_srodku.parent_item_id == walizka.pk

    def test_P7_home_wyliczane_automatycznie(self, dom, szafa):
        """Użytkownik nigdy nie podaje pola home."""
        rzecz = item_service.create_item(name="Czapka", location=szafa)
        assert rzecz.home_id == dom.pk

    def test_P1_brak_rodzica_odrzucony(self, dom):
        with pytest.raises(InvalidParentError):
            item_service.create_item(name="Sierota")

    def test_P1_dwaj_rodzice_odrzuceni(self, dom, szafa):
        walizka = item_service.create_item(name="Walizka", location=szafa)
        with pytest.raises(InvalidParentError):
            item_service.create_item(
                name="Zdezorientowana", location=szafa, parent_item=walizka
            )

    def test_P11_rzecz_bezposrednio_w_domu(self, dom):
        """P11: dom jest zwykłą lokalizacją."""
        rzecz = item_service.create_item(name="Choinka", location=dom)
        assert rzecz.location_id == dom.pk
        assert rzecz.home_id == dom.pk

    def test_P2_wystarczy_nazwa_i_miejsce(self, szafa):
        """Niskie tarcie — reszta pól opcjonalna."""
        rzecz = item_service.create_item(name="Coś", location=szafa)
        assert rzecz.quantity == 1
        assert rzecz.description == ""
        assert rzecz.owner is None


class TestN2KolizjaNazwPrzyTworzeniu:
    def test_kolizja_rzuca_wyjatek_z_propozycja(self, dom, szafa, mlotek):
        with pytest.raises(NameCollisionError) as exc:
            item_service.create_item(name="Młotek", location=szafa)
        assert exc.value.suggestion == "Młotek_2"

    def test_zatwierdzenie_propozycji(self, dom, szafa, mlotek):
        rzecz = item_service.create_item(
            name="Młotek", location=szafa, accept_suggested_name=True
        )
        assert rzecz.name == "Młotek_2"

    def test_nazwa_nie_zmienia_sie_cicho(self, dom, szafa, mlotek):
        """
        Bez accept_suggested_name operacja musi się nie powieść —
        system nigdy nie podmienia nazwy bez wiedzy użytkownika.
        """
        with pytest.raises(NameCollisionError):
            item_service.create_item(name="Młotek", location=szafa)
        assert Item.objects.filter(name_norm="mlotek").count() == 1

    def test_ta_sama_nazwa_w_innym_domu_przechodzi(self, domek, mlotek):
        garaz = Location.objects.create(name="Garaż", parent=domek)
        path_service.invalidate_tree()
        rzecz = item_service.create_item(name="Młotek", location=garaz)
        assert rzecz.name == "Młotek"
        assert rzecz.home_id == domek.pk


class TestPrzenoszenie:
    def test_przeniesienie_do_innej_lokalizacji(self, dom, szafa, mlotek):
        kuchnia = Location.objects.create(name="Kuchnia", parent=dom)
        path_service.invalidate_tree()

        item_service.move_item(mlotek, location=kuchnia)
        mlotek.refresh_from_db()
        assert mlotek.location_id == kuchnia.pk

    def test_wlozenie_do_pojemnika(self, dom, szafa, mlotek):
        skrzynka = item_service.create_item(name="Skrzynka", location=szafa)
        item_service.move_item(mlotek, parent_item=skrzynka)

        mlotek.refresh_from_db()
        assert mlotek.parent_item_id == skrzynka.pk
        assert mlotek.location_id is None

    def test_P6_cykl_jest_blokowany(self, dom, szafa):
        walizka = item_service.create_item(name="Walizka", location=szafa)
        kosmetyczka = item_service.create_item(name="Kosmetyczka", parent_item=walizka)
        with pytest.raises(CycleError):
            item_service.move_item(walizka, parent_item=kosmetyczka)

    def test_P8_zawartosc_idzie_z_pojemnikiem(self, dom, domek, szafa):
        """Przeniesienie walizki do innego domu zabiera zawartość."""
        walizka = item_service.create_item(name="Walizka", location=szafa)
        item_service.create_item(name="Szczoteczka", parent_item=walizka)

        garaz = Location.objects.create(name="Garaż", parent=domek)
        path_service.invalidate_tree()

        item_service.move_item(walizka, location=garaz)

        szczoteczka = Item.objects.get(name="Szczoteczka")
        assert szczoteczka.home_id == domek.pk
        assert szczoteczka.parent_item_id == walizka.pk

    def test_N5_kolizja_przy_przenosinach_miedzy_domami(
        self, dom, domek, szafa, mlotek
    ):
        """
        N5: przeniesienie do domu z zajętą nazwą proponuje sufiks,
        ale nie blokuje operacji.
        """
        garaz = Location.objects.create(name="Garaż", parent=domek)
        path_service.invalidate_tree()
        Item.objects.create(name="Młotek", location=garaz, home=domek)

        with pytest.raises(NameCollisionError) as exc:
            item_service.move_item(mlotek, location=garaz)
        assert exc.value.suggestion == "Młotek_2"

        item_service.move_item(mlotek, location=garaz, accept_suggested_name=True)
        mlotek.refresh_from_db()
        assert mlotek.name == "Młotek_2"
        assert mlotek.home_id == domek.pk


class TestN4ZmianaNazwy:
    def test_zmiana_na_wolna_nazwe(self, dom, mlotek):
        item_service.rename_item(mlotek, "Łopata")
        mlotek.refresh_from_db()
        assert mlotek.name == "Łopata"
        assert mlotek.name_norm == "lopata"

    def test_zmiana_na_zajeta_rzuca_wyjatek(self, dom, szafa, mlotek):
        Item.objects.create(name="Łopata", location=szafa, home=dom)
        with pytest.raises(NameCollisionError):
            item_service.rename_item(mlotek, "Łopata")

    def test_zapis_bez_zmiany_nazwy_nie_koliduje(self, dom, mlotek):
        """exclude_pk zapobiega kolizji rzeczy ze sobą samą."""
        item_service.rename_item(mlotek, "Młotek")
        mlotek.refresh_from_db()
        assert mlotek.name == "Młotek"


class TestP5UsuwaniePojemnika:
    def test_liczenie_zawartosci(self, dom, szafa):
        walizka = item_service.create_item(name="Walizka", location=szafa)
        kosmetyczka = item_service.create_item(name="Kosmetyczka", parent_item=walizka)
        item_service.create_item(name="Pasta", parent_item=kosmetyczka)
        item_service.create_item(name="Adapter", parent_item=walizka)

        assert item_service.count_contents(walizka) == 3

    def test_pusty_przedmiot_ma_zero_zawartosci(self, mlotek):
        assert item_service.count_contents(mlotek) == 0

    def test_usuniecie_kasuje_zawartosc(self, dom, szafa):
        walizka = item_service.create_item(name="Walizka", location=szafa)
        item_service.create_item(name="Pasta", parent_item=walizka)

        liczba = item_service.delete_item(walizka)

        assert liczba == 2
        assert Item.objects.count() == 0
