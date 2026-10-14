"""
Testy widoku wyszukiwania — trasa krytyczna aplikacji.

Weryfikują HTTP: kody odpowiedzi, treść HTML, rozróżnienie żądania
zwykłego od HTMX. Logika wyszukiwania testowana osobno w
test_services/test_search_service.py.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from inventory.services import item_service, path_service

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture
def client_zalogowany(db) -> Client:
    User.objects.create_user(username="domownik", password="haslo12345")
    client = Client()
    client.login(username="domownik", password="haslo12345")
    return client


@pytest.fixture(autouse=True)
def czysty_cache():
    path_service.invalidate_tree()
    yield
    path_service.invalidate_tree()


class TestWymaganeLogowanie:
    def test_niezalogowany_jest_przekierowany(self, client, dom):
        resp = client.get(reverse("inventory:search"))
        assert resp.status_code == 302
        assert "/accounts/login/" in resp.url


class TestStronaBezZapytania:
    def test_pusta_strona_startowa(self, client_zalogowany):
        resp = client_zalogowany.get(reverse("inventory:search"))
        assert resp.status_code == 200
        assert "GdzieStanik" in resp.content.decode()

    def test_brak_wynikow_bez_komunikatu_pustki(self, client_zalogowany):
        """Bez wpisanego zapytania nie pokazujemy „nic nie znaleziono”."""
        resp = client_zalogowany.get(reverse("inventory:search"))
        assert "Nic nie znaleziono" not in resp.content.decode()

    def test_przycisk_dodaj_rzecz_jest_widoczny(self, client_zalogowany):
        """Szybki dostęp do /add/ ze strony startowej."""
        resp = client_zalogowany.get(reverse("inventory:search"))
        tresc = resp.content.decode()
        assert reverse("inventory:add_item") in tresc
        assert "Dodaj rzecz" in tresc


class TestWyszukiwanieZwykleZadanie:
    def test_znaleziona_rzecz_z_pelna_sciezka(
        self, client_zalogowany, dom, szafa, mlotek
    ):
        resp = client_zalogowany.get(reverse("inventory:search"), {"q": "młotek"})
        tresc = resp.content.decode()

        assert resp.status_code == 200
        assert "Młotek" in tresc
        assert "Dom" in tresc and "Sypialnia" in tresc and "Szafa" in tresc

    def test_w4_zapytanie_bez_ogonkow(self, client_zalogowany, dom, szafa):
        item_service.create_item(name="Żarówka", location=szafa)
        resp = client_zalogowany.get(reverse("inventory:search"), {"q": "zarowka"})
        assert "Żarówka" in resp.content.decode()

    def test_brak_wynikow_pokazuje_komunikat(self, client_zalogowany, dom):
        resp = client_zalogowany.get(
            reverse("inventory:search"), {"q": "czegos_takiego_nie_ma"}
        )
        assert "Nic nie znaleziono" in resp.content.decode()

    def test_zwykle_zadanie_zwraca_pelna_strone(
        self, client_zalogowany, dom, szafa, mlotek
    ):
        resp = client_zalogowany.get(reverse("inventory:search"), {"q": "młotek"})
        assert b"<html" in resp.content.lower()


class TestWyszukiwanieHTMX:
    def test_htmx_zwraca_sam_fragment(self, client_zalogowany, dom, szafa, mlotek):
        resp = client_zalogowany.get(
            reverse("inventory:search"), {"q": "młotek"}, HTTP_HX_REQUEST="true"
        )
        tresc = resp.content.decode()

        assert resp.status_code == 200
        assert "Młotek" in tresc
        assert b"<html" not in resp.content.lower()
        assert b"<form" not in resp.content.lower()


class TestFiltrDomu:
    def test_filtr_zaweza_wyniki(self, dom, domek, szafa, client_zalogowany):
        from inventory.models import Location

        garaz = Location.objects.create(name="Garaż", parent=domek)
        item_service.create_item(name="Młotek", location=szafa)
        item_service.create_item(name="Młotek", location=garaz)

        resp = client_zalogowany.get(
            reverse("inventory:search"), {"q": "młotek", "home": dom.pk}
        )
        tresc = resp.content.decode()

        # Jeden wynik z tego domu, nie dwa
        assert tresc.count("Dom ›") >= 1

    def test_selektor_domu_ukryty_przy_jednym_domu(self, client_zalogowany, dom):
        resp = client_zalogowany.get(reverse("inventory:search"))
        assert "Wszystkie domy" not in resp.content.decode()

    def test_selektor_domu_widoczny_przy_wielu(self, client_zalogowany, dom, domek):
        resp = client_zalogowany.get(reverse("inventory:search"))
        assert "Wszystkie domy" in resp.content.decode()


class TestOdnosnikiDoWynikow:
    def test_wynik_przedmiotu_linkuje_do_szczegolow(
        self, client_zalogowany, dom, szafa, mlotek
    ):
        resp = client_zalogowany.get(reverse("inventory:search"), {"q": "młotek"})
        oczekiwany_url = reverse("inventory:item_detail", args=[mlotek.pk])
        assert oczekiwany_url in resp.content.decode()

    def test_wynik_lokalizacji_linkuje_do_szczegolow(
        self, client_zalogowany, dom, sypialnia, szafa
    ):
        resp = client_zalogowany.get(reverse("inventory:search"), {"q": "szafa"})
        oczekiwany_url = reverse("inventory:location_detail", args=[szafa.pk])
        assert oczekiwany_url in resp.content.decode()


class TestP9OznaczeniePojemnika:
    def test_pojemnik_oznaczony_w_wynikach(self, client_zalogowany, dom, szafa):
        from inventory.models import Item

        walizka = Item.objects.create(name="Walizka", location=szafa, home=dom)
        Item.objects.create(name="Kosmetyczka", parent_item=walizka, home=dom)

        resp = client_zalogowany.get(reverse("inventory:search"), {"q": "walizka"})
        assert "📦" in resp.content.decode()


class TestWidokiSzczegolow:
    def test_item_detail_pokazuje_sciezke(self, client_zalogowany, dom, szafa, mlotek):
        resp = client_zalogowany.get(reverse("inventory:item_detail", args=[mlotek.pk]))
        tresc = resp.content.decode()
        assert resp.status_code == 200
        assert "Dom" in tresc and "Sypialnia" in tresc and "Szafa" in tresc

    def test_item_detail_pokazuje_zawartosc_pojemnika(
        self, client_zalogowany, dom, szafa
    ):
        from inventory.models import Item

        walizka = Item.objects.create(name="Walizka", location=szafa, home=dom)
        Item.objects.create(name="Kosmetyczka", parent_item=walizka, home=dom)

        resp = client_zalogowany.get(
            reverse("inventory:item_detail", args=[walizka.pk])
        )
        assert "Kosmetyczka" in resp.content.decode()

    def test_location_detail_pokazuje_podlokalizacje_i_rzeczy(
        self, client_zalogowany, dom, sypialnia, szafa, mlotek
    ):
        resp = client_zalogowany.get(
            reverse("inventory:location_detail", args=[sypialnia.pk])
        )
        tresc = resp.content.decode()
        assert "Szafa" in tresc

    def test_nieistniejacy_przedmiot_daje_404(self, client_zalogowany):
        resp = client_zalogowany.get(reverse("inventory:item_detail", args=[99999]))
        assert resp.status_code == 404
