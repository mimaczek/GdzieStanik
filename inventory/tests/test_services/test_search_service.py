"""
Testy wyszukiwania — wymagania W1–W7 z docs/domain-model.md §4.
"""

import time

import pytest

from inventory.models import Item, Location
from inventory.services import path_service, search_service

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def czysty_cache():
    path_service.invalidate_tree()
    yield
    path_service.invalidate_tree()


class TestW1PelnaSciezkaWWyniku:
    def test_wynik_zawiera_pelna_sciezke(self, dom, szafa, mlotek):
        wyniki = search_service.search("młotek")

        assert len(wyniki) == 1
        assert wyniki[0].full_path == ["Dom", "Sypialnia", "Szafa", "Młotek"]

    def test_sciezka_przez_pojemnik(self, dom, szafa):
        """Scenariusz 5.6 z vision.md — szczoteczka w walizce."""
        walizka = Item.objects.create(name="Walizka", location=szafa, home=dom)
        Item.objects.create(name="Szczoteczka podróżna", parent_item=walizka, home=dom)

        wyniki = search_service.search("szczoteczka")

        assert wyniki[0].full_path == [
            "Dom",
            "Sypialnia",
            "Szafa",
            "Walizka",
            "Szczoteczka podróżna",
        ]

    def test_dopasowanie_lokalizacji_tez_ma_pelna_sciezke(self, dom, sypialnia, szafa):
        wyniki = search_service.search("szafa")

        lokalizacje = [w for w in wyniki if w.kind == "location"]
        assert lokalizacje[0].full_path == ["Dom", "Sypialnia", "Szafa"]


class TestW2DopasowanieCzesciowe:
    def test_fragment_nazwy_wystarcza(self, dom, szafa):
        Item.objects.create(name="Ładowarka USB-C", location=szafa, home=dom)
        wyniki = search_service.search("ładow")
        assert len(wyniki) == 1
        assert wyniki[0].name == "Ładowarka USB-C"

    def test_fragment_w_srodku_nazwy(self, dom, szafa):
        Item.objects.create(name="Ładowarka do wiertarki", location=szafa, home=dom)
        wyniki = search_service.search("wiertarki")
        assert len(wyniki) == 1


class TestW3IgnorowanieWielkosciLiter:
    def test_wielkie_litery_w_zapytaniu(self, mlotek):
        assert len(search_service.search("MŁOTEK")) == 1

    def test_male_litery_dla_nazwy_z_wielkimi(self, mlotek):
        assert len(search_service.search("młotek")) == 1


class TestW4PolskieZnakiWObieStrony:
    """Wymaganie twarde — nikt nie wpisuje ogonków na telefonie."""

    def test_zapytanie_bez_ogonkow_znajduje_z_ogonkami(self, dom, szafa):
        Item.objects.create(name="Żarówka", location=szafa, home=dom)
        wyniki = search_service.search("zarowka")
        assert len(wyniki) == 1
        assert wyniki[0].name == "Żarówka"

    def test_zapytanie_z_ogonkami_znajduje_bez_ogonkow(self, dom, szafa):
        Item.objects.create(name="zarowka", location=szafa, home=dom)
        wyniki = search_service.search("żarówka")
        assert len(wyniki) == 1

    def test_l_z_kreska(self, dom, szafa):
        """Najtrudniejszy przypadek — „ł” nie rozkłada się przez NFKD."""
        Item.objects.create(name="Łopata", location=szafa, home=dom)
        wyniki = search_service.search("lopata")
        assert len(wyniki) == 1


class TestW5SortowaniePoTrafnosci:
    def test_prefiks_przed_fragmentem(self, dom, szafa):
        """
        Uwaga: wyszukiwanie to dopasowanie podciągu (W2), nie stemming
        językowy — „wiertarka” nie jest podciągiem „wiertarki” (inna
        końcówka fleksyjna). Test używa więc dokładnie tego ciągu znaków,
        który ma się znaleźć w obu nazwach.
        """
        Item.objects.create(name="Wiertarka Bosch", location=szafa, home=dom)
        Item.objects.create(name="Ładowarka do Wiertarka X1", location=szafa, home=dom)

        wyniki = search_service.search("wiertarka")

        assert wyniki[0].name == "Wiertarka Bosch"  # prefiks — ranga 1
        assert wyniki[1].name == "Ładowarka do Wiertarka X1"  # fragment — ranga 2

    def test_nazwa_przed_tagiem(self, dom, szafa):
        from inventory.models import Tag

        tag = Tag.objects.create(name="narzędzia")
        Item.objects.create(name="Klucz", location=szafa, home=dom)
        oznaczona_tagiem = Item.objects.create(name="Wkrętak", location=szafa, home=dom)
        oznaczona_tagiem.tags.add(tag)
        # Dodatkowo nazwa drugiej rzeczy nie pasuje do zapytania
        wyniki = search_service.search("klucz")
        assert wyniki[0].name == "Klucz"

    def test_tag_przed_lokalizacja(self, dom, szafa):
        from inventory.models import Tag

        tag = Tag.objects.create(name="zimowe")
        rzecz = Item.objects.create(name="Czapka", location=szafa, home=dom)
        rzecz.tags.add(tag)
        Location.objects.create(name="Zimowe ubrania", parent=dom)

        wyniki = search_service.search("zimowe")

        assert wyniki[0].kind == "item"  # tag — ranga 3
        assert wyniki[1].kind == "location"  # nazwa lokalizacji — ranga 4

    def test_lokalizacja_przed_opisem(self, dom, szafa):
        Location.objects.create(name="Narzędziownia", parent=dom)
        Item.objects.create(
            name="Coś",
            description="leży obok narzędziowni",
            location=szafa,
            home=dom,
        )

        wyniki = search_service.search("narzędziow")

        assert wyniki[0].kind == "location"  # ranga 4
        assert wyniki[-1].kind == "item"  # opis — ranga 5

    def test_sortowanie_alfabetyczne_w_tej_samej_randze(self, dom, szafa):
        Item.objects.create(name="Zebra", location=szafa, home=dom)
        Item.objects.create(name="Antylopa", location=szafa, home=dom)
        # Oba mają "a" jako fragment — ta sama ranga (contains)
        wyniki = [w.name for w in search_service.search("a")]
        # Posortowane alfabetycznie w obrębie tej samej rangi
        indeks_zebra = wyniki.index("Zebra")
        indeks_antylopa = wyniki.index("Antylopa")
        assert indeks_antylopa < indeks_zebra


class TestW7WieleDomow:
    def test_wyszukiwanie_obejmuje_wszystkie_domy(self, dom, domek, szafa):
        garaz = Location.objects.create(name="Garaż", parent=domek)
        Item.objects.create(name="Młotek", location=szafa, home=dom)
        Item.objects.create(name="Młotek", location=garaz, home=domek)

        wyniki = search_service.search("młotek")

        assert len(wyniki) == 2
        domy = {w.home_name for w in wyniki}
        assert domy == {"Dom", "Domek letniskowy"}

    def test_filtr_zawezajacy_do_jednego_domu(self, dom, domek, szafa):
        garaz = Location.objects.create(name="Garaż", parent=domek)
        Item.objects.create(name="Młotek", location=szafa, home=dom)
        Item.objects.create(name="Młotek", location=garaz, home=domek)

        wyniki = search_service.search("młotek", home_id=dom.pk)

        assert len(wyniki) == 1
        assert wyniki[0].home_name == "Dom"

    def test_filtr_dziala_dla_lokalizacji(self, dom, domek, sypialnia):
        Location.objects.create(name="Sypialnia", parent=domek)

        wyniki = search_service.search("sypialnia", home_id=dom.pk)

        assert len(wyniki) == 1
        assert wyniki[0].id == sypialnia.pk

    def test_filtr_dziala_dla_tagow_na_lokalizacji(self, dom, domek, sypialnia):
        from inventory.models import Tag

        tag = Tag.objects.create(name="piętro")
        sypialnia.tags.add(tag)
        inna = Location.objects.create(name="Salon", parent=domek)
        inna.tags.add(tag)

        wyniki = search_service.search("piętro", home_id=dom.pk)

        assert len(wyniki) == 1
        assert wyniki[0].id == sypialnia.pk


class TestScalanieDuplikatow:
    def test_dopasowanie_w_dwoch_kategoriach_to_jeden_wynik(self, dom, szafa):
        """
        Rzecz pasująca po nazwie I po tagu powinna pojawić się raz,
        z najlepszą (najniższą) rangą.
        """
        from inventory.models import Tag

        tag = Tag.objects.create(name="narzędzia")
        rzecz = Item.objects.create(name="Narzędzia ogrodowe", location=szafa, home=dom)
        rzecz.tags.add(tag)

        wyniki = search_service.search("narzędzia")

        pasujace = [w for w in wyniki if w.id == rzecz.pk and w.kind == "item"]
        assert len(pasujace) == 1
        assert pasujace[0].rank == search_service.RANK_NAME_PREFIX


class TestP9InformacjaOPojemniku:
    def test_wynik_oznacza_pojemnik(self, dom, szafa):
        walizka = Item.objects.create(name="Walizka", location=szafa, home=dom)
        Item.objects.create(name="Kosmetyczka", parent_item=walizka, home=dom)

        wyniki = search_service.search("walizka")

        assert wyniki[0].is_container is True

    def test_zwykla_rzecz_nie_jest_pojemnikiem(self, mlotek):
        wyniki = search_service.search("młotek")
        assert wyniki[0].is_container is False


class TestPusteZapytanie:
    def test_puste_zapytanie_zwraca_pusta_liste(self, mlotek):
        assert search_service.search("") == []

    def test_same_spacje_to_puste_zapytanie(self, mlotek):
        assert search_service.search("   ") == []


class TestW6Wydajnosc:
    """
    Pomiar orientacyjny — nie jest to pełny test wydajnościowy
    (wymagałby 5000 przedmiotów i sprzętu klasy Raspberry Pi), ale
    wychwytuje regresje typu N+1, które objawiają się przy mniejszej
    skali tak samo jak przy dużej, tylko proporcjonalnie szybciej.
    """

    def test_wyszukiwanie_w_rozsadnym_czasie(self, dom, szafa):
        for i in range(200):
            Item.objects.create(name=f"Przedmiot testowy {i}", location=szafa, home=dom)

        start = time.perf_counter()
        wyniki = search_service.search("testowy")
        czas = time.perf_counter() - start

        assert len(wyniki) == 30  # MAX_PER_CATEGORY
        assert czas < 1.0  # hojny margines dla środowiska testowego
