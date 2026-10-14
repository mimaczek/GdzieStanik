"""
Testy przetwarzania zdjęć — ADR-0006.
"""

from io import BytesIO

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from PIL import Image

from inventory.exceptions import InvalidPhotoError
from inventory.services import photo_service


def _obraz(
    width: int = 2000,
    height: int = 1500,
    fmt: str = "JPEG",
    mode: str = "RGB",
) -> SimpleUploadedFile:
    """Tworzy w pamięci prawdziwy plik obrazu do testów uploadu."""
    # Kolor zależny od trybu — "L" (skala szarości) i "RGBA" przyjmują
    # inny kształt wartości niż "RGB".
    kolor: int | tuple[int, ...]
    if mode == "L":
        kolor = 128
    elif mode == "RGBA":
        kolor = (200, 50, 50, 255)
    else:
        kolor = (200, 50, 50)
    img = Image.new(mode, (width, height), color=kolor)
    bufor = BytesIO()
    img.save(bufor, format=fmt)
    bufor.seek(0)
    content_type = "image/jpeg" if fmt == "JPEG" else f"image/{fmt.lower()}"
    return SimpleUploadedFile(
        f"zdjecie.{fmt.lower()}", bufor.read(), content_type=content_type
    )


class TestWalidacjaRozmiaru:
    def test_za_duzy_plik_jest_odrzucany(self):
        plik = _obraz()
        plik.size = 25 * 1024 * 1024  # symulacja 25 MB, powyżej limitu 20 MB
        with pytest.raises(InvalidPhotoError, match="za duży"):
            photo_service.validate_upload(plik)

    def test_plik_w_limicie_przechodzi(self):
        plik = _obraz()
        photo_service.validate_upload(plik)  # bez wyjątku


class TestWalidacjaTypu:
    def test_niedozwolony_typ_jest_odrzucany(self):
        plik = SimpleUploadedFile(
            "dokument.pdf", b"%PDF-1.4 fake", content_type="application/pdf"
        )
        with pytest.raises(InvalidPhotoError, match="format"):
            photo_service.validate_upload(plik)

    def test_jpeg_jest_dozwolony(self):
        photo_service.validate_upload(_obraz(fmt="JPEG"))

    def test_png_jest_dozwolony(self):
        photo_service.validate_upload(_obraz(fmt="PNG"))


class TestPrzetwarzanieObrazu:
    def test_uszkodzony_plik_jest_odrzucany(self):
        plik = SimpleUploadedFile(
            "zepsute.jpg", b"to nie jest obraz", content_type="image/jpeg"
        )
        with pytest.raises(InvalidPhotoError, match="odczytać"):
            photo_service.process_photo(plik)

    @override_settings(PHOTO_MAX_DIMENSION=1600, PHOTO_THUMBNAIL_DIMENSION=300)
    def test_duzy_obraz_jest_skalowany(self):
        """Wejście 3000×2000 → dłuższy bok maks. 1600 px (ADR-0006)."""
        wynik = photo_service.process_photo(_obraz(width=3000, height=2000))

        glowny = Image.open(wynik.main)
        assert max(glowny.size) <= 1600

        miniatura = Image.open(wynik.thumbnail)
        assert max(miniatura.size) <= 300

    @override_settings(PHOTO_MAX_DIMENSION=1600)
    def test_maly_obraz_nie_jest_powiekszany(self):
        """Zdjęcie 400×300 zostaje w oryginalnym rozmiarze, nie 1600."""
        wynik = photo_service.process_photo(_obraz(width=400, height=300))
        glowny = Image.open(wynik.main)
        assert glowny.size == (400, 300)

    def test_wynik_jest_webp(self):
        wynik = photo_service.process_photo(_obraz())
        assert Image.open(wynik.main).format == "WEBP"
        assert Image.open(wynik.thumbnail).format == "WEBP"

    def test_proporcje_sa_zachowane(self):
        """Obraz 3000×1500 (2:1) po skalowaniu zostaje 2:1."""
        wynik = photo_service.process_photo(_obraz(width=3000, height=1500))
        glowny = Image.open(wynik.main)
        proporcja = glowny.size[0] / glowny.size[1]
        assert abs(proporcja - 2.0) < 0.01

    def test_png_z_przezroczystoscia_konwertuje_sie_bez_bledu(self):
        """RGBA nie zapisuje się bezpiecznie do WebP bez konwersji na RGB."""
        wynik = photo_service.process_photo(_obraz(fmt="PNG", mode="RGBA"))
        assert Image.open(wynik.main).mode in ("RGB", "RGBA")

    def test_skala_szarosci_dziala(self):
        wynik = photo_service.process_photo(_obraz(mode="L"))
        Image.open(wynik.main).load()  # nie rzuca wyjątku


class TestOrientacjaExif:
    """
    Telefony zapisują zdjęcia w oryginalnej orientacji sensora i dodają
    tag EXIF mówiący, jak je obrócić do wyświetlenia. Bez exif_transpose
    zdjęcie pionowe z telefonu wyświetlałoby się na boku.
    """

    def test_orientacja_z_exif_obraca_piksele(self):
        """
        Obraz 100×50 z tagiem orientacji 6 (obrót 90°) powinien
        po przetworzeniu mieć zamienione wymiary — bo exif_transpose
        fizycznie obraca piksele, a nie tylko odczytuje tag.
        """
        img = Image.new("RGB", (100, 50), color=(255, 0, 0))
        exif = img.getexif()
        exif[0x0112] = 6  # tag Orientation ze specyfikacji EXIF
        bufor = BytesIO()
        img.save(bufor, format="JPEG", exif=exif)
        bufor.seek(0)
        plik = SimpleUploadedFile(
            "pionowe.jpg", bufor.read(), content_type="image/jpeg"
        )

        wynik = photo_service.process_photo(plik)
        glowny = Image.open(wynik.main)

        # Przed obróceniem: szerokość > wysokość. Po: odwrotnie.
        assert glowny.size[0] < glowny.size[1]


class TestRozmiarPliku:
    def test_webp_jest_mniejszy_niz_oryginalny_jpeg(self):
        """Weryfikacja realnego zysku z konwersji — sens całej funkcji."""
        oryginal = _obraz(width=2000, height=1500)
        rozmiar_oryginalu = oryginal.size

        wynik = photo_service.process_photo(oryginal)
        rozmiar_webp = wynik.main.size

        assert rozmiar_webp < rozmiar_oryginalu
