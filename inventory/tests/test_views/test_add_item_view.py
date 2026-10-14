"""
Testy widoku szybkiego dodawania rzeczy — scenariusz 5.2 z vision.md.
"""

from io import BytesIO

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from PIL import Image

from inventory.models import Item
from inventory.services import path_service

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


def _plik_obrazu(nazwa: str = "zdjecie.jpg") -> SimpleUploadedFile:
    img = Image.new("RGB", (2000, 1500), color=(0, 255, 0))
    bufor = BytesIO()
    img.save(bufor, format="JPEG")
    bufor.seek(0)
    return SimpleUploadedFile(nazwa, bufor.read(), content_type="image/jpeg")


class TestWymaganeLogowanie:
    def test_niezalogowany_jest_przekierowany(self, client, dom):
        resp = client.get(reverse("inventory:add_item"))
        assert resp.status_code == 302


class TestDodawanieMinimalne:
    """P2: jedyne wymagane pole to nazwa, reszta opcjonalna."""

    def test_formularz_sie_wyswietla(self, client_zalogowany, dom):
        resp = client_zalogowany.get(reverse("inventory:add_item"))
        assert resp.status_code == 200
        assert "Nazwa" in resp.content.decode()

    def test_dodanie_z_samym_wymaganym_minimum(self, client_zalogowany, dom, szafa):
        resp = client_zalogowany.post(
            reverse("inventory:add_item"),
            {
                "name": "Śrubokręt",
                "location": szafa.pk,
                "quantity": 1,
                "description": "",
                "tags": "",
            },
        )
        assert resp.status_code == 302

        rzecz = Item.objects.get(name="Śrubokręt")
        assert rzecz.location_id == szafa.pk
        assert rzecz.home_id == dom.pk
        assert rzecz.quantity == 1

    def test_przekierowanie_do_szczegolow(self, client_zalogowany, dom, szafa):
        resp = client_zalogowany.post(
            reverse("inventory:add_item"),
            {
                "name": "Klucz",
                "location": szafa.pk,
                "quantity": 1,
                "description": "",
                "tags": "",
            },
        )
        rzecz = Item.objects.get(name="Klucz")
        assert resp.url == reverse("inventory:item_detail", args=[rzecz.pk])


class TestP11RzeczBezposrednioWDomu:
    def test_mozna_wybrac_dom_jako_lokalizacje(self, client_zalogowany, dom):
        resp = client_zalogowany.post(
            reverse("inventory:add_item"),
            {
                "name": "Choinka",
                "location": dom.pk,
                "quantity": 1,
                "description": "",
                "tags": "",
            },
        )
        assert resp.status_code == 302
        rzecz = Item.objects.get(name="Choinka")
        assert rzecz.location_id == dom.pk


class TestN2PropozycjaSufiksu:
    def test_duplikat_pokazuje_propozycje_bez_zapisu(
        self, client_zalogowany, dom, szafa, mlotek
    ):
        resp = client_zalogowany.post(
            reverse("inventory:add_item"),
            {
                "name": "Młotek",
                "location": szafa.pk,
                "quantity": 1,
                "description": "",
                "tags": "",
            },
        )
        assert resp.status_code == 200  # formularz wraca, nie przekierowuje
        assert "Młotek_2" in resp.content.decode()
        assert Item.objects.filter(name_norm="mlotek").count() == 1  # bez zmian

    def test_akceptacja_sufiksu_zapisuje_z_nowa_nazwa(
        self, client_zalogowany, dom, szafa, mlotek
    ):
        resp = client_zalogowany.post(
            reverse("inventory:add_item"),
            {
                "name": "Młotek",
                "location": szafa.pk,
                "quantity": 1,
                "description": "",
                "tags": "",
                "accept_suggested_name": "1",
            },
        )
        assert resp.status_code == 302
        assert Item.objects.filter(name="Młotek_2").exists()

    def test_nazwa_nigdy_nie_zmienia_sie_cicho(
        self, client_zalogowany, dom, szafa, mlotek
    ):
        """Bez accept_suggested_name nazwa 'Młotek' pozostaje niezajęta ponownie."""
        client_zalogowany.post(
            reverse("inventory:add_item"),
            {
                "name": "Młotek",
                "location": szafa.pk,
                "quantity": 1,
                "description": "",
                "tags": "",
            },
        )
        # Druga próba z tą samą nazwą - wciąż tylko propozycja, nie zapis
        resp = client_zalogowany.post(
            reverse("inventory:add_item"),
            {
                "name": "Młotek",
                "location": szafa.pk,
                "quantity": 1,
                "description": "",
                "tags": "",
            },
        )
        assert "Młotek_2" in resp.content.decode()
        assert Item.objects.filter(name_norm="mlotek").count() == 1


class TestTagi:
    def test_tagi_oddzielone_przecinkami(self, client_zalogowany, dom, szafa):
        client_zalogowany.post(
            reverse("inventory:add_item"),
            {
                "name": "Latarka",
                "location": szafa.pk,
                "quantity": 1,
                "description": "",
                "tags": "turystyka, awaryjne",
            },
        )
        rzecz = Item.objects.get(name="Latarka")
        nazwy_tagow = set(rzecz.tags.values_list("name", flat=True))
        assert nazwy_tagow == {"turystyka", "awaryjne"}

    def test_nowy_tag_jest_tworzony(self, client_zalogowany, dom, szafa):
        """T2: tagi tworzą się automatycznie przy wpisywaniu."""
        from inventory.models import Tag

        assert not Tag.objects.filter(name_norm="unikalny_tag_xyz").exists()
        client_zalogowany.post(
            reverse("inventory:add_item"),
            {
                "name": "Rzecz",
                "location": szafa.pk,
                "quantity": 1,
                "description": "",
                "tags": "unikalny_tag_xyz",
            },
        )
        assert Tag.objects.filter(name_norm="unikalny_tag_xyz").exists()


class TestUploadZdjecia:
    def test_zdjecie_jest_przetwarzane_i_zapisywane(
        self, client_zalogowany, dom, szafa
    ):
        resp = client_zalogowany.post(
            reverse("inventory:add_item"),
            {
                "name": "ZeZdjęciem",
                "location": str(szafa.pk),
                "quantity": "1",
                "description": "",
                "tags": "",
                "photo": _plik_obrazu(),
            },
        )
        assert resp.status_code == 302

        rzecz = Item.objects.get(name="ZeZdjęciem")
        assert rzecz.photo.name.endswith(".webp")
        assert rzecz.photo_thumbnail.name.endswith("_thumb.webp")

    def test_bez_zdjecia_pola_pozostaja_puste(self, client_zalogowany, dom, szafa):
        client_zalogowany.post(
            reverse("inventory:add_item"),
            {
                "name": "BezZdjecia",
                "location": szafa.pk,
                "quantity": 1,
                "description": "",
                "tags": "",
            },
        )
        rzecz = Item.objects.get(name="BezZdjecia")
        assert not rzecz.photo
        assert not rzecz.photo_thumbnail

    def test_niewlasciwy_plik_jest_odrzucany_z_komunikatem(
        self, client_zalogowany, dom, szafa
    ):
        zly_plik = SimpleUploadedFile(
            "dokument.pdf", b"nie jest to obraz", content_type="application/pdf"
        )
        resp = client_zalogowany.post(
            reverse("inventory:add_item"),
            {
                "name": "ZZepsutymZdjeciem",
                "location": szafa.pk,
                "quantity": 1,
                "description": "",
                "tags": "",
                "photo": zly_plik,
            },
        )
        assert resp.status_code == 200
        assert not Item.objects.filter(name="ZZepsutymZdjeciem").exists()


class TestWstepneWypelnienieLokalizacji:
    """Przycisk „+ Dodaj rzecz tutaj” w location_detail.html przekazuje ?location="""

    def test_parametr_location_wypelnia_pole(self, client_zalogowany, dom, szafa):
        resp = client_zalogowany.get(
            reverse("inventory:add_item"), {"location": szafa.pk}
        )
        tresc = resp.content.decode()
        assert f'value="{szafa.pk}" selected' in tresc
