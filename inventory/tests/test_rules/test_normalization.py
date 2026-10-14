"""
Testy normalizacji tekstu — wymaganie W4 i reguły N1, G5.

Zobacz docs/domain-model.md §4 oraz docs/architecture.md §5.1.
"""

import pytest

from inventory.normalization import normalize, split_suffix


class TestW4PolskieZnaki:
    """W4: wyszukiwanie odporne na brak polskich znaków, w obie strony."""

    @pytest.mark.parametrize(
        ("wejscie", "oczekiwane"),
        [
            ("żarówka", "zarowka"),
            ("ŻARÓWKA", "zarowka"),
            ("Żarówka", "zarowka"),
            ("śruba", "sruba"),
            ("gwóźdź", "gwozdz"),
            ("ćwiek", "cwiek"),
            ("nóż", "noz"),
            ("łańcuch", "lancuch"),
            ("piła", "pila"),
            ("zęby", "zeby"),
        ],
    )
    def test_usuwa_diakrytyki(self, wejscie, oczekiwane):
        assert normalize(wejscie) == oczekiwane

    def test_l_z_kreska_jest_obslugiwane(self):
        """
        Najważniejszy przypadek: „ł” nie jest literą z diakrytykiem
        w rozumieniu Unicode, więc NFKD go nie rozkłada.

        Bez jawnej obsługi „mlotek” nie znalazłby „młotka”.
        """
        assert normalize("młotek") == "mlotek"
        assert normalize("Łopata") == "lopata"
        assert "ł" not in normalize("łóżko")

    def test_wyszukiwanie_dziala_w_obie_strony(self):
        """Użytkownik może wpisać z ogonkami albo bez — wynik ten sam."""
        assert normalize("żarówka") == normalize("zarowka")
        assert normalize("młotek") == normalize("mlotek")


class TestNormalizacjaPodstawowa:
    @pytest.mark.parametrize(
        ("wejscie", "oczekiwane"),
        [
            ("Młotek", "mlotek"),
            ("  młotek  ", "mlotek"),
            ("młotek   gumowy", "młotek gumowy".replace("ł", "l")),
            ("", ""),
            ("   ", ""),
        ],
    )
    def test_przypadki(self, wejscie, oczekiwane):
        assert normalize(wejscie) == oczekiwane

    def test_scala_wielokrotne_spacje(self):
        assert normalize("wiertarka    Bosch") == "wiertarka bosch"

    def test_przycina_biale_znaki(self):
        assert normalize("\t młotek \n") == "mlotek"


class TestN1WykrywanieKolizji:
    """N1: porównanie po postaci znormalizowanej."""

    def test_rozna_wielkosc_liter_to_kolizja(self):
        assert normalize("Młotek") == normalize("MŁOTEK") == normalize("młotek")

    def test_roznica_w_ogonkach_to_kolizja(self):
        assert normalize("Młotek") == normalize("mlotek")

    def test_nadmiarowe_spacje_to_kolizja(self):
        assert normalize("młotek ") == normalize(" młotek")

    def test_rozne_nazwy_to_nie_kolizja(self):
        assert normalize("młotek") != normalize("młotek gumowy")


class TestN3Sufiksy:
    """N2, N3: rozpoznawanie sufiksów liczbowych."""

    @pytest.mark.parametrize(
        ("wejscie", "rdzen", "numer"),
        [
            ("młotek", "młotek", None),
            ("młotek_2", "młotek", 2),
            ("młotek_17", "młotek", 17),
            ("młotek_gumowy", "młotek_gumowy", None),
            ("młotek_gumowy_3", "młotek_gumowy", 3),
        ],
    )
    def test_rozdziela_sufiks(self, wejscie, rdzen, numer):
        assert split_suffix(wejscie) == (rdzen, numer)

    def test_nazwa_opisowa_nie_jest_sufiksem(self):
        """
        „młotek_gumowy” to nazwa nadana przez użytkownika (N2),
        nie wynik automatycznej numeracji.
        """
        rdzen, numer = split_suffix("młotek_gumowy")
        assert numer is None
