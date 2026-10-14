"""
Testy widoku przenoszenia rzeczy (architecture.md §7, wiersz
„Przeniesienie”).
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from inventory.models import Item, Location
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
    def test_niezalogowany_jest_przekierowany(self, client, mlotek):
        resp = client.get(reverse("inventory:move_item", args=[mlotek.pk]))
        assert resp.status_code == 302


class TestFormularzPrzenoszenia:
    def test_formularz_pokazuje_obecna_sciezke(
        self, client_zalogowany, dom, szafa, mlotek
    ):
        resp = client_zalogowany.get(reverse("inventory:move_item", args=[mlotek.pk]))
        tresc = resp.content.decode()
        assert resp.status_code == 200
        assert "Dom" in tresc and "Sypialnia" in tresc and "Szafa" in tresc


class TestPrzeniesienieDoLokalizacji:
    def test_zmiana_lokalizacji(self, client_zalogowany, dom, szafa, mlotek):
        kuchnia = Location.objects.create(name="Kuchnia", parent=dom)
        resp = client_zalogowany.post(
            reverse("inventory:move_item", args=[mlotek.pk]),
            {"location": kuchnia.pk, "parent_item": ""},
        )
        assert resp.status_code == 302

        mlotek.refresh_from_db()
        assert mlotek.location_id == kuchnia.pk

    def test_przekierowanie_do_szczegolow(self, client_zalogowany, dom, szafa, mlotek):
        kuchnia = Location.objects.create(name="Kuchnia", parent=dom)
        resp = client_zalogowany.post(
            reverse("inventory:move_item", args=[mlotek.pk]),
            {"location": kuchnia.pk, "parent_item": ""},
        )
        assert resp.url == reverse("inventory:item_detail", args=[mlotek.pk])


class TestWlozenieDoPojemnika:
    def test_przeniesienie_do_przedmiotu(self, client_zalogowany, dom, szafa, mlotek):
        walizka = item_service.create_item(name="Walizka", location=szafa)

        resp = client_zalogowany.post(
            reverse("inventory:move_item", args=[mlotek.pk]),
            {"location": "", "parent_item": walizka.pk},
        )
        assert resp.status_code == 302

        mlotek.refresh_from_db()
        assert mlotek.parent_item_id == walizka.pk
        assert mlotek.location_id is None


class TestP1WalidacjaFormularza:
    def test_brak_obu_pol_jest_odrzucany(self, client_zalogowany, mlotek):
        resp = client_zalogowany.post(
            reverse("inventory:move_item", args=[mlotek.pk]),
            {"location": "", "parent_item": ""},
        )
        assert resp.status_code == 200  # formularz wraca z błędem
        assert "Wybierz" in resp.content.decode()

    def test_oba_pola_naraz_sa_odrzucane(self, client_zalogowany, dom, szafa, mlotek):
        walizka = item_service.create_item(name="Walizka2", location=szafa)
        resp = client_zalogowany.post(
            reverse("inventory:move_item", args=[mlotek.pk]),
            {"location": szafa.pk, "parent_item": walizka.pk},
        )
        assert resp.status_code == 200
        assert "nie w obu naraz" in resp.content.decode()


class TestP6CyklJestBlokowany:
    def test_wlozenie_pojemnika_do_wlasnej_zawartosci(
        self, client_zalogowany, dom, szafa
    ):
        walizka = item_service.create_item(name="Walizka", location=szafa)
        kosmetyczka = item_service.create_item(name="Kosmetyczka", parent_item=walizka)

        resp = client_zalogowany.post(
            reverse("inventory:move_item", args=[walizka.pk]),
            {"location": "", "parent_item": kosmetyczka.pk},
        )
        assert resp.status_code == 200

        walizka.refresh_from_db()
        assert walizka.location_id == szafa.pk  # bez zmian

    def test_lista_parent_item_wyklucza_sam_siebie(
        self, client_zalogowany, dom, szafa, mlotek
    ):
        """
        Wygoda UI (nie twarda walidacja) — formularz nie oferuje
        wyboru samego siebie jako nowego rodzica.

        Uwaga: pk lokalizacji i przedmiotów to osobne numeracje (różne
        tabele), więc nie można po prostu szukać 'value="<pk>"' w całym
        HTML — trzeba sprawdzić formularz na poziomie querysetu pola.
        """
        resp = client_zalogowany.get(reverse("inventory:move_item", args=[mlotek.pk]))
        form = resp.context["form"]
        dostepne_id = set(
            form.fields["parent_item"].queryset.values_list("pk", flat=True)
        )
        assert mlotek.pk not in dostepne_id


class TestN5KolizjaPrzyPrzenosinachMiedzyDomami:
    def test_kolizja_blokuje_przeniesienie_z_komunikatem(
        self, client_zalogowany, dom, domek, szafa, mlotek
    ):
        garaz = Location.objects.create(name="Garaż", parent=domek)
        Item.objects.create(name="Młotek", location=garaz, home=domek)

        resp = client_zalogowany.post(
            reverse("inventory:move_item", args=[mlotek.pk]),
            {"location": garaz.pk, "parent_item": ""},
        )
        assert resp.status_code == 200
        tresc = resp.content.decode()
        assert "Młotek_2" in tresc

        mlotek.refresh_from_db()
        assert mlotek.home_id == dom.pk  # nie przeniesiono

    def test_przeniesienie_do_domu_bez_kolizji_dziala(
        self, client_zalogowany, dom, domek, szafa, mlotek
    ):
        garaz = Location.objects.create(name="Garaż", parent=domek)

        resp = client_zalogowany.post(
            reverse("inventory:move_item", args=[mlotek.pk]),
            {"location": garaz.pk, "parent_item": ""},
        )
        assert resp.status_code == 302

        mlotek.refresh_from_db()
        assert mlotek.home_id == domek.pk
