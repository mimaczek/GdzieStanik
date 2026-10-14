"""
Przetwarzanie zdjęć — ADR-0006.

Przepływ (architecture.md §5.6):

    upload → walidacja typu i rozmiaru (max 20 MB)
           → Pillow: EXIF-transpose, resize do 1600 px, WebP
           → miniatura 300 px
           → zapis pod UUID w MEDIA_ROOT/photos/{rok}/{miesiąc}/
           → w bazie ścieżka przez ImageField

Oryginał NIE jest zachowywany (reguła G4) — celowo, żeby nie zajeżdżać
karty SD / dysku na Raspberry Pi zdjęciami 5–8 MB z telefonu, skoro
cel zdjęcia w tej aplikacji to rozpoznanie rzeczy, nie dokumentacja
fotograficzna. Metadane EXIF są usuwane poza orientacją — zdjęcia
z telefonu zawierają współrzędne GPS, które nie powinny trafiać na
serwer razem ze zdjęciem pudełka w piwnicy.

Ponowne zakodowanie przez Pillow (zamiast zapisania bajtów 1:1) ma
dodatkowo znaczenie bezpieczeństwa: plik wyjściowy jest tworzony od
zera z zdekodowanych pikseli, więc nie może przenieść złośliwej
zawartości ukrytej w nagłówkach czy metadanych pliku wejściowego.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile, UploadedFile
from PIL import Image, ImageOps, UnidentifiedImageError

from ..exceptions import InvalidPhotoError


@dataclass(frozen=True, slots=True)
class ProcessedPhoto:
    """Wynik przetworzenia — dwa gotowe pliki do przypisania do pól modelu."""

    main: SimpleUploadedFile
    thumbnail: SimpleUploadedFile


def validate_upload(upload: UploadedFile) -> None:
    """
    Wstępna walidacja PRZED otwarciem przez Pillow (szybki odrzut
    oczywiście złych plików bez kosztu dekodowania).

    Rzuca InvalidPhotoError z komunikatem gotowym do pokazania
    użytkownikowi pod polem formularza.
    """
    if upload.size is not None and upload.size > settings.PHOTO_MAX_UPLOAD_BYTES:
        limit_mb = settings.PHOTO_MAX_UPLOAD_BYTES // (1024 * 1024)
        raise InvalidPhotoError(f"Plik jest za duży — limit to {limit_mb} MB.")

    content_type = getattr(upload, "content_type", None)
    if content_type and content_type not in settings.PHOTO_ALLOWED_TYPES:
        raise InvalidPhotoError(
            "Nieobsługiwany format pliku. Dozwolone: JPEG, PNG, WebP."
        )


def process_photo(upload: UploadedFile) -> ProcessedPhoto:
    """
    Przetwarza wgrany plik: prostowanie orientacji, skalowanie,
    konwersja do WebP, wygenerowanie miniatury.

    Rzuca InvalidPhotoError, gdy Pillow nie potrafi otworzyć pliku
    jako obrazu (uszkodzony plik albo coś, co tylko udaje zdjęcie).
    """
    validate_upload(upload)

    try:
        wczytany = Image.open(upload)
        # Wymusza pełne zdekodowanie teraz, zamiast leniwie przy
        # pierwszym dostępie do pikseli — inaczej błąd uszkodzonego
        # pliku wypłynąłby dopiero przy .resize() niżej, z gorszym
        # komunikatem.
        wczytany.load()
    except UnidentifiedImageError as exc:
        raise InvalidPhotoError("Nie udało się odczytać pliku jako obrazu.") from exc

    # Zmienna typu Image.Image (nie ImageFile) od tego miejsca —
    # exif_transpose i Image.new zwracają typ bazowy, a obraz jest
    # dalej modyfikowany (przypisywany ponownie) w kolejnych krokach.
    obraz: Image.Image = wczytany

    # Usuwa metadane EXIF (w tym GPS) poza orientacją, którą
    # exif_transpose już wykorzystał do obrócenia pikseli — po tym
    # wywołaniu orientacja jest zapisana w samych pikselach, więc
    # oryginalny tag EXIF staje się zbędny.
    obraz = ImageOps.exif_transpose(obraz) or obraz

    # RGBA/P (paleta) nie zapisują się bezpiecznie do WebP bez
    # jawnej konwersji — białe tło zamiast przezroczystości, bo
    # miniatury rzeczy w szafie i tak nie potrzebują kanału alfa.
    if obraz.mode not in ("RGB", "L"):
        tlo = Image.new("RGB", obraz.size, (255, 255, 255))
        if obraz.mode in ("RGBA", "LA") or (
            obraz.mode == "P" and "transparency" in obraz.info
        ):
            tlo.paste(obraz, mask=obraz.convert("RGBA").split()[-1])
        else:
            tlo.paste(obraz)
        obraz = tlo

    glowne = _resize_and_encode(obraz, settings.PHOTO_MAX_DIMENSION)
    miniatura = _resize_and_encode(obraz, settings.PHOTO_THUMBNAIL_DIMENSION)

    return ProcessedPhoto(
        main=SimpleUploadedFile("photo.webp", glowne, content_type="image/webp"),
        thumbnail=SimpleUploadedFile(
            "thumbnail.webp", miniatura, content_type="image/webp"
        ),
    )


def _resize_and_encode(obraz: Image.Image, max_dimension: int) -> bytes:
    """
    Skaluje obraz tak, by dłuższy bok nie przekraczał max_dimension,
    i koduje do WebP.

    Obrazy mniejsze niż limit NIE są powiększane — thumbnail() z Pillow
    skaluje tylko w dół, co jest właściwym zachowaniem (nie ma sensu
    sztucznie powiększać małego zdjęcia).
    """
    kopia = obraz.copy()
    kopia.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)

    bufor = BytesIO()
    kopia.save(
        bufor,
        format="WEBP",
        quality=settings.PHOTO_WEBP_QUALITY,
        method=6,  # najwolniejsza, najlepsza kompresja — czas uploadu
        # ma mniejsze znaczenie niż rozmiar pliku przy każdym
        # późniejszym wyświetleniu w wynikach wyszukiwania
    )
    return bufor.getvalue()
