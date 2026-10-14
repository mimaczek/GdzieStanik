"""
Testy operacji na lokalizacjach — reguły L1, L3, L6, P7.
"""

import pytest

from inventory.exceptions import CycleError, NotEmptyError
from inventory.models import Item, Location
from inventory.services import location_service, path_service

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def czysty_cache():
    path_service.invalidate_tree()
    yield
    path_service.invalidate_tree()


class TestTworzenie:
    def test_dom_jako_korzen(self):
        dom = location_service.create_location(name="Mieszkanie")
        assert dom.parent_id is None
        assert dom.is_home is True

    def test_pokoj_w_domu(self, dom):
        pokoj = location_service.create_location(name="Kuchnia", parent=dom)
        assert pokoj.parent_id == dom.pk
        assert pokoj.is_home is False

    def test_cache_jest_uniewazniany(self, dom):
        path_service.get_tree()
        location_service.create_location(name="Piwnica", parent=dom)

        drzewo = path_service.get_tree()
        assert "Piwnica" in {w.name for w in drzewo.values()}


class TestL1Przenoszenie:
    def test_przeniesienie_do_innego_pokoju(self, dom, sypialnia, szafa):
        kuchnia = location_service.create_location(name="Kuchnia", parent=dom)
        location_service.move_location(szafa, kuchnia)

        szafa.refresh_from_db()
        assert szafa.parent_id == kuchnia.pk

    def test_cykl_jest_blokowany(self, sypialnia, szafa):
        with pytest.raises(CycleError):
            location_service.move_location(sypialnia, szafa)

    def test_przeniesienie_zmienia_sciezke_zawartosci(
        self, dom, sypialnia, szafa, mlotek
    ):
        """Przenosi się pojemnik, nie każda rzecz osobno."""
        piwnica = location_service.create_location(name="Piwnica", parent=dom)
        location_service.move_location(szafa, piwnica)

        assert path_service.path_for_item(mlotek) == ["Dom", "Piwnica", "Szafa"]


class TestP7PrzenoszenieMiedzyDomami:
    def test_home_rzeczy_jest_aktualizowane(self, dom, domek, szafa, mlotek):
        """
        Przeniesienie szafy do innej nieruchomości musi zaktualizować
        home wszystkich rzeczy w środku.
        """
        location_service.move_location(szafa, domek)

        mlotek.refresh_from_db()
        assert mlotek.home_id == domek.pk

    def test_home_aktualizowane_w_glab_drzewa(self, dom, domek, sypialnia):
        polka = location_service.create_location(name="Półka", parent=sypialnia)
        rzecz = Item.objects.create(name="Książka", location=polka, home=dom)

        location_service.move_location(sypialnia, domek)

        rzecz.refresh_from_db()
        assert rzecz.home_id == domek.pk

    def test_home_aktualizowane_dla_rzeczy_w_pojemnikach(self, dom, domek, szafa):
        walizka = Item.objects.create(name="Walizka", location=szafa, home=dom)
        pasta = Item.objects.create(name="Pasta", parent_item=walizka, home=dom)

        location_service.move_location(szafa, domek)

        pasta.refresh_from_db()
        assert pasta.home_id == domek.pk


class TestL3Usuwanie:
    def test_pusta_lokalizacja_usuwa_sie(self, dom):
        pusta = location_service.create_location(name="Spiżarnia", parent=dom)
        location_service.delete_location(pusta)
        assert not Location.objects.filter(name="Spiżarnia").exists()

    def test_niepusta_odmawia_usuniecia(self, sypialnia, szafa):
        with pytest.raises(NotEmptyError) as exc:
            location_service.delete_location(sypialnia)
        assert exc.value.children == 1

    def test_wyjatek_niesie_liczby(self, dom, szafa, mlotek):
        with pytest.raises(NotEmptyError) as exc:
            location_service.delete_location(szafa)
        assert exc.value.items == 1
        assert exc.value.children == 0

    def test_przeniesienie_zawartosci_do_rodzica(self, dom, sypialnia, szafa, mlotek):
        location_service.delete_location(szafa, move_contents_to_parent=True)

        mlotek.refresh_from_db()
        assert mlotek.location_id == sypialnia.pk
        assert not Location.objects.filter(name="Szafa").exists()

    def test_force_usuwa_kaskadowo(self, dom, sypialnia, szafa, mlotek):
        location_service.delete_location(sypialnia, force=True)

        assert not Location.objects.filter(name="Sypialnia").exists()
        assert not Location.objects.filter(name="Szafa").exists()
        assert not Item.objects.filter(name="Młotek").exists()

    def test_dom_zostaje_po_usunieciu_pokoju(self, dom, sypialnia, szafa):
        location_service.delete_location(sypialnia, force=True)
        assert Location.objects.filter(pk=dom.pk).exists()


class TestL6Domy:
    def test_lista_nieruchomosci(self, dom, domek, sypialnia):
        domy = location_service.get_homes()
        nazwy = [d.name for d in domy]

        assert "Dom" in nazwy
        assert "Domek letniskowy" in nazwy
        assert "Sypialnia" not in nazwy

    def test_pokoj_nie_jest_domem(self, sypialnia):
        assert sypialnia.is_home is False
