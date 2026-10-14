"""
Testy budowania ścieżek i wykrywania cykli.

Reguły L1, L4, P6, P7, P10 oraz wymaganie W1.
"""

import pytest

from inventory.exceptions import CycleError
from inventory.models import Item, Location
from inventory.services import path_service

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def czysty_cache():
    """Cache drzewa musi być pusty przed każdym testem."""
    path_service.invalidate_tree()
    yield
    path_service.invalidate_tree()


class TestW1PelnaSciezka:
    """W1: każdy wynik zawiera pełną ścieżkę od domu."""

    def test_sciezka_lokalizacji(self, dom, sypialnia, szafa):
        assert path_service.path_for_location(szafa) == [
            "Dom",
            "Sypialnia",
            "Szafa",
        ]

    def test_sciezka_domu_to_sam_dom(self, dom):
        assert path_service.path_for_location(dom) == ["Dom"]

    def test_formatowanie_ze_strzalkami(self, szafa):
        sciezka = path_service.path_for_location(szafa)
        assert path_service.format_path(sciezka) == "Dom › Sypialnia › Szafa"

    def test_sciezka_rzeczy_w_lokalizacji(self, mlotek):
        assert path_service.path_for_item(mlotek) == [
            "Dom",
            "Sypialnia",
            "Szafa",
        ]


class TestSciezkaPrzezPojemniki:
    """ADR-0001: ścieżka przechodzi przez przedmioty-pojemniki."""

    def test_rzecz_w_walizce(self, dom, szafa):
        walizka = Item.objects.create(name="Walizka", location=szafa, home=dom)
        szczotka = Item.objects.create(
            name="Szczoteczka", parent_item=walizka, home=dom
        )
        assert path_service.path_for_item(szczotka) == [
            "Dom",
            "Sypialnia",
            "Szafa",
            "Walizka",
        ]

    def test_pojemnik_w_pojemniku(self, dom, szafa):
        """Scenariusz 5.6 z vision.md — spakowana walizka."""
        walizka = Item.objects.create(name="Walizka", location=szafa, home=dom)
        kosmetyczka = Item.objects.create(
            name="Kosmetyczka", parent_item=walizka, home=dom
        )
        szczotka = Item.objects.create(
            name="Szczoteczka", parent_item=kosmetyczka, home=dom
        )
        assert path_service.path_for_item(szczotka) == [
            "Dom",
            "Sypialnia",
            "Szafa",
            "Walizka",
            "Kosmetyczka",
        ]

    def test_sciezka_nie_zawiera_nazwy_samej_rzeczy(self, mlotek):
        """Ścieżka opisuje miejsce, nie rzecz."""
        assert "Młotek" not in path_service.path_for_item(mlotek)


class TestP7WyliczanieDomu:
    def test_dom_dla_lokalizacji(self, dom, szafa):
        assert path_service.home_for_location(szafa) == dom.pk

    def test_dom_dla_rzeczy(self, dom, mlotek):
        assert path_service.home_for_item(mlotek) == dom.pk

    def test_dom_dla_rzeczy_w_pojemniku(self, dom, szafa):
        walizka = Item.objects.create(name="Walizka", location=szafa, home=dom)
        w_srodku = Item.objects.create(name="Pasta", parent_item=walizka, home=dom)
        assert path_service.home_for_item(w_srodku) == dom.pk

    def test_rozne_domy_sa_rozdzielone(self, dom, domek):
        garaz = Location.objects.create(name="Garaż", parent=domek)
        assert path_service.home_for_location(garaz) == domek.pk
        assert path_service.home_for_location(garaz) != dom.pk


class TestL1CykleLokalizacji:
    def test_lokalizacja_w_samej_sobie(self, szafa):
        with pytest.raises(CycleError):
            path_service.check_location_cycle(szafa, szafa)

    def test_rodzic_w_swoim_dziecku(self, sypialnia, szafa):
        """Próba umieszczenia sypialni w szafie, która w niej stoi."""
        with pytest.raises(CycleError):
            path_service.check_location_cycle(sypialnia, szafa)

    def test_glebokie_zagniezdzenie_tez_wykryte(self, dom, sypialnia, szafa):
        polka = Location.objects.create(name="Półka", parent=szafa)
        with pytest.raises(CycleError):
            path_service.check_location_cycle(dom, polka)

    def test_przeniesienie_do_rodzenstwa_jest_ok(self, dom, sypialnia, szafa):
        kuchnia = Location.objects.create(name="Kuchnia", parent=dom)
        path_service.check_location_cycle(szafa, kuchnia)  # bez wyjątku

    def test_przeniesienie_do_korzenia_jest_ok(self, szafa):
        path_service.check_location_cycle(szafa, None)


class TestP6CyklePrzedmiotow:
    def test_przedmiot_w_samym_sobie(self, dom, mlotek):
        with pytest.raises(CycleError):
            path_service.check_item_cycle(mlotek, mlotek)

    def test_pojemnik_we_wlasnej_zawartosci(self, dom, szafa):
        walizka = Item.objects.create(name="Walizka", location=szafa, home=dom)
        kosmetyczka = Item.objects.create(
            name="Kosmetyczka", parent_item=walizka, home=dom
        )
        with pytest.raises(CycleError):
            path_service.check_item_cycle(walizka, kosmetyczka)

    def test_glebokie_zagniezdzenie_tez_wykryte(self, dom, szafa):
        a = Item.objects.create(name="A", location=szafa, home=dom)
        b = Item.objects.create(name="B", parent_item=a, home=dom)
        c = Item.objects.create(name="C", parent_item=b, home=dom)
        with pytest.raises(CycleError):
            path_service.check_item_cycle(a, c)

    def test_wlozenie_do_niepowiazanego_jest_ok(self, dom, szafa, mlotek):
        pudelko = Item.objects.create(name="Pudełko", location=szafa, home=dom)
        path_service.check_item_cycle(mlotek, pudelko)


class TestL4P10Glebokosc:
    def test_glebokosc_lokalizacji(self, dom, sypialnia, szafa):
        assert path_service.location_depth(dom) == 1
        assert path_service.location_depth(sypialnia) == 2
        assert path_service.location_depth(szafa) == 3

    def test_ostrzezenie_przy_przekroczeniu_progu(self, dom):
        """L4: ostrzeżenie powyżej 6 poziomów."""
        biezaca = dom
        for i in range(7):
            biezaca = Location.objects.create(name=f"Poziom {i}", parent=biezaca)
        path_service.invalidate_tree()
        assert path_service.exceeds_location_depth_warning(biezaca) is True

    def test_zagniezdzenie_rzeczy(self, dom, szafa, mlotek):
        assert path_service.item_nesting_depth(mlotek) == 0

        walizka = Item.objects.create(name="Walizka", location=szafa, home=dom)
        w_srodku = Item.objects.create(name="Pasta", parent_item=walizka, home=dom)
        assert path_service.item_nesting_depth(w_srodku) == 1

    def test_ostrzezenie_dla_rzeczy_powyzej_3_poziomow(self, dom, szafa):
        """P10: ostrzeżenie powyżej 3 poziomów zagnieżdżenia."""
        biezacy = Item.objects.create(name="P0", location=szafa, home=dom)
        for i in range(1, 5):
            biezacy = Item.objects.create(name=f"P{i}", parent_item=biezacy, home=dom)
        assert path_service.exceeds_item_nesting_warning(biezacy) is True


class TestCacheDrzewa:
    def test_cache_jest_uzywany(self, dom, sypialnia):
        drzewo_a = path_service.get_tree()
        drzewo_b = path_service.get_tree()
        assert drzewo_a.keys() == drzewo_b.keys()

    def test_uniewaznienie_odswieza_dane(self, dom):
        path_service.get_tree()
        Location.objects.create(name="Nowy pokój", parent=dom)

        path_service.invalidate_tree()
        drzewo = path_service.get_tree()

        nazwy = {w.name for w in drzewo.values()}
        assert "Nowy pokój" in nazwy
