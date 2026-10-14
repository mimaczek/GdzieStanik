"""
Testy przeglądania drzewa lokalizacji i rozwijania węzłów przez HTMX
(architecture.md §7, wiersz „Przeglądanie drzewa”).
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from inventory.models import Location
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


class TestWidokLokalizacji:
    def test_pokazuje_podlokalizacje(self, client_zalogowany, dom, sypialnia):
        resp = client_zalogowany.get(
            reverse("inventory:location_detail", args=[dom.pk])
        )
        assert "Sypialnia" in resp.content.decode()

    def test_pokazuje_rzeczy(self, client_zalogowany, dom, szafa, mlotek):
        resp = client_zalogowany.get(
            reverse("inventory:location_detail", args=[szafa.pk])
        )
        assert "Młotek" in resp.content.decode()

    def test_przycisk_dodaj_rzecz_wskazuje_biezaca_lokalizacje(
        self, client_zalogowany, dom, szafa
    ):
        resp = client_zalogowany.get(
            reverse("inventory:location_detail", args=[szafa.pk])
        )
        oczekiwany = f"{reverse('inventory:add_item')}?location={szafa.pk}"
        assert oczekiwany in resp.content.decode()

    def test_wezel_ma_atrybut_hx_get_do_rozwijania(
        self, client_zalogowany, dom, sypialnia
    ):
        resp = client_zalogowany.get(
            reverse("inventory:location_detail", args=[dom.pk])
        )
        oczekiwany = reverse("inventory:location_children", args=[sypialnia.pk])
        assert oczekiwany in resp.content.decode()


class TestRozwijanieWezla:
    def test_fragment_zwraca_dzieci(self, client_zalogowany, dom, sypialnia, szafa):
        resp = client_zalogowany.get(
            reverse("inventory:location_children", args=[sypialnia.pk])
        )
        assert resp.status_code == 200
        assert "Szafa" in resp.content.decode()

    def test_fragment_nie_zawiera_pelnej_strony(
        self, client_zalogowany, dom, sypialnia, szafa
    ):
        resp = client_zalogowany.get(
            reverse("inventory:location_children", args=[sypialnia.pk])
        )
        assert b"<html" not in resp.content.lower()

    def test_pusty_wezel_pokazuje_informacje(self, client_zalogowany, dom):
        pusta = Location.objects.create(name="Pusta szuflada", parent=dom)
        resp = client_zalogowany.get(
            reverse("inventory:location_children", args=[pusta.pk])
        )
        assert "Pusto" in resp.content.decode()

    def test_nieistniejaca_lokalizacja_daje_404(self, client_zalogowany):
        resp = client_zalogowany.get(
            reverse("inventory:location_children", args=[99999])
        )
        assert resp.status_code == 404
