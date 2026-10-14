"""
Testy reguły A5: panel administracyjny musi wołać serwisy.

Weryfikujemy to na poziomie efektów — jeśli admin ominąłby serwisy,
poniższe operacje dałyby niespójny stan (błędny cykl, zły home,
cicha kolizja nazw) albo zakończyłyby się nieobsłużonym wyjątkiem
zamiast czytelnego komunikatu.

Testy przez Client + panel admina, nie przez wywołanie ModelAdmin
bezpośrednio — tak właśnie korzysta z niego operator.
"""

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from inventory.models import Item, Location

pytestmark = pytest.mark.django_db

User = get_user_model()


@pytest.fixture
def admin_client(db) -> Client:
    User.objects.create_superuser(username="admin", password="haslo12345")
    client = Client()
    client.login(username="admin", password="haslo12345")
    return client


def _formset_management(prefix: str, total: int = 0) -> dict:
    """
    Pola management-form wymagane przez Django dla inline'ów (tu:
    LocationChildrenInline). W przeglądarce renderują się jako ukryte
    inputy i są wysyłane automatycznie — w testach trzeba je dodać
    ręcznie do danych POST.
    """
    return {
        f"{prefix}-TOTAL_FORMS": str(total),
        f"{prefix}-INITIAL_FORMS": "0",
        f"{prefix}-MIN_NUM_FORMS": "0",
        f"{prefix}-MAX_NUM_FORMS": "1000",
    }


class TestA5LokalizacjaWyciagaCykl:
    """
    Bez wywołania move_location (które woła check_location_cycle)
    admin zapisałby cykl przez zwykły UPDATE — baza tego nie wyłapie,
    bo ograniczenie L1 istnieje tylko w warstwie serwisów.
    """

    def test_proba_cyklu_nie_jest_zapisywana(self, admin_client, sypialnia, szafa):
        url = reverse("admin:inventory_location_change", args=[sypialnia.pk])
        resp = admin_client.post(
            url,
            {
                "name": sypialnia.name,
                "parent": szafa.pk,  # szafa jest WEWNĄTRZ sypialni — cykl
                "kind": sypialnia.kind,
                "description": "",
                "sort_order": 0,
                "tags": [],
                **_formset_management("children"),
            },
        )

        # Formularz nie przechodzi — strona wraca z błędem, nie 302
        assert resp.status_code == 200

        sypialnia.refresh_from_db()
        assert sypialnia.parent_id != szafa.pk


class TestA5PropagacjaHome:
    """
    Bez wywołania move_location, pole Item.home rzeczy wewnątrz
    przenoszonej lokalizacji zostałoby nieaktualne (P7) — zwykły
    UPDATE lokalizacji nic nie wie o zagnieżdżonych przedmiotach.
    """

    def test_przeniesienie_przez_admin_aktualizuje_home(
        self, admin_client, dom, domek, szafa, mlotek
    ):
        url = reverse("admin:inventory_location_change", args=[szafa.pk])
        resp = admin_client.post(
            url,
            {
                "name": szafa.name,
                "parent": domek.pk,
                "kind": szafa.kind,
                "description": "",
                "sort_order": 0,
                "tags": [],
                **_formset_management("children"),
            },
        )
        assert resp.status_code == 302

        mlotek.refresh_from_db()
        assert mlotek.home_id == domek.pk


class TestA5UnikalnoscNazwPrzedmiotow:
    """
    Bez wywołania create_item/rename_item admin zapisałby duplikat
    nazwy w tym samym domu po cichu — ograniczenie N1 istnieje w bazie
    jako CheckConstraint, ale bez przejścia przez serwis operator
    dostałby surowy IntegrityError zamiast propozycji sufiksu.
    """

    def test_duplikat_nazwy_jest_odrzucany_z_komunikatem(
        self, admin_client, dom, szafa, mlotek
    ):
        url = reverse("admin:inventory_item_add")
        resp = admin_client.post(
            url,
            {
                "name": "Młotek",
                "location": szafa.pk,
                "parent_item": "",
                "quantity": 1,
                "description": "",
                "owner": "",
                "tags": [],
            },
        )

        # Nie 302 (sukces) — operacja nie powinna się powieść po cichu
        assert resp.status_code != 302
        assert Item.objects.filter(name_norm="mlotek").count() == 1

    def test_komunikat_zawiera_propozycje_sufiksu(
        self, admin_client, dom, szafa, mlotek
    ):
        url = reverse("admin:inventory_item_add")
        resp = admin_client.post(
            url,
            {
                "name": "Młotek",
                "location": szafa.pk,
                "parent_item": "",
                "quantity": 1,
                "description": "",
                "owner": "",
                "tags": [],
            },
            follow=True,
        )
        tresc = resp.content.decode("utf-8")
        assert "Młotek_2" in tresc


class TestA5OdmowaUsunieciaNiepustejLokalizacji:
    """
    Bez delete_model wywołującego check_can_delete admin usunąłby
    lokalizację kaskadowo razem z zawartością bez ostrzeżenia (L3) —
    PROTECT na kluczu obcym i tak by to zablokował, ale z nieczytelnym
    ProtectedError zamiast komunikatu w interfejsie.
    """

    def test_usuniecie_niepustej_lokalizacji_nie_powoduje_utraty_danych(
        self, admin_client, sypialnia, szafa, mlotek
    ):
        url = reverse("admin:inventory_location_delete", args=[sypialnia.pk])
        admin_client.post(url, {"post": "yes"})

        # Niezależnie od kodu odpowiedzi — dane muszą przetrwać
        assert Location.objects.filter(pk=sypialnia.pk).exists()
        assert Location.objects.filter(pk=szafa.pk).exists()
        assert Item.objects.filter(pk=mlotek.pk).exists()


class TestA5KaskadoweUsuwaniePojemnika:
    """
    delete_model dla Item musi pokazać ostrzeżenie o zawartości (P5)
    zamiast cichej kaskady — tu weryfikujemy samą kaskadę, bo to ona
    jest źródłem ryzyka, gdyby ktoś pominął serwis.
    """

    def test_usuniecie_pojemnika_usuwa_zawartosc(self, admin_client, dom, szafa):
        walizka = Item.objects.create(name="Walizka", location=szafa, home=dom)
        Item.objects.create(name="Kosmetyczka", parent_item=walizka, home=dom)

        url = reverse("admin:inventory_item_delete", args=[walizka.pk])
        admin_client.post(url, {"post": "yes"})

        assert not Item.objects.filter(name="Walizka").exists()
        assert not Item.objects.filter(name="Kosmetyczka").exists()
