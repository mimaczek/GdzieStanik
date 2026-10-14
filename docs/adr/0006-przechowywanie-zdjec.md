# ADR-0006: Zdjęcia skalowane przy uploadzie, dane poza kartą SD

- **Status:** zaakceptowany
- **Data:** 2026-10-14
- **Dotyczy:** obsługa plików, wydajność, trwałość sprzętu

## Kontekst

Przedmioty i lokalizacje mogą mieć zdjęcie (Q1, Q2). Główny sposób dodawania
to telefon w trakcie porządków — czyli pliki prosto z aparatu, zwykle
3–8 MB, o rozdzielczości rzędu 4000 × 3000.

Aplikacja działa na Raspberry Pi, domyślnie z systemem na karcie microSD.
Karty SD mają ograniczoną liczbę cykli zapisu i są najczęstszą przyczyną
awarii tych urządzeń.

Szacunek: 500 zdjęć w oryginale to około 2,5 GB. Wyświetlenie listy wyników
z dziesięcioma takimi zdjęciami oznacza przesłanie kilkudziesięciu megabajtów
do telefonu.

Cel zdjęcia w tej aplikacji to **rozpoznanie rzeczy lub pudełka**, nie
dokumentacja fotograficzna.

## Rozważane warianty

### A. Zapis oryginałów bez zmian

Najprostszy w implementacji, zachowuje pełną jakość.

Odrzucony: zajeżdża kartę SD, zapycha dysk, spowalnia interfejs na telefonie.
Jakość ponad potrzeby zastosowania.

### B. Zapis plików w bazie jako BLOB

Backup obejmuje wszystko w jednym pliku, spójność transakcyjna.

Odrzucony: plik SQLite urósłby do gigabajtów, co spowalnia kopie zapasowe
i zwiększa ryzyko przy uszkodzeniu. Serwowanie plików z bazy jest wolniejsze
niż z systemu plików.

### C. Oryginał plus wersje pochodne

Zachowanie oryginału na wypadek przyszłych potrzeb.

Odrzucony: potraja zużycie miejsca dla korzyści, która może nigdy nie
wystąpić. Łatwiej zrobić zdjęcie ponownie niż utrzymywać archiwum.

### D. Skalowanie przy uploadzie, oryginał odrzucany — **wybrany**

## Decyzja

### Przetwarzanie

```
upload → walidacja typu (JPEG/PNG/WebP) i rozmiaru (max 20 MB)
       → EXIF-transpose (korekta orientacji z telefonu)
       → skalowanie do maks. 1600 px dłuższego boku
       → konwersja na WebP, jakość 82
       → miniatura 300 px, również WebP
       → zapis pod nazwą UUID w /data/photos/{rok}/{miesiąc}/
       → w bazie wyłącznie ścieżka względna
```

Oryginał nie jest zachowywany. Metadane EXIF są usuwane poza orientacją —
zdjęcia z telefonu zawierają współrzędne GPS.

Ponowne zakodowanie przez Pillow pełni też funkcję bezpieczeństwa: plik
wyjściowy jest tworzony od zera, więc nie przenosi złośliwej zawartości
ukrytej w pliku wejściowym.

Rozmiar po przetworzeniu: zwykle 150–400 kB zamiast 3–8 MB.

### Rozmieszczenie danych

Cały katalog `/data` — baza SQLite **i** zdjęcia — znajduje się na dysku
USB lub SSD podpiętym do Raspberry Pi, nigdy na karcie SD z systemem.

```yaml
volumes:
  - /mnt/ssd/gdziestanik:/data
```

Układ katalogów z podziałem na rok i miesiąc zapobiega powstaniu jednego
katalogu z tysiącami plików.

## Konsekwencje

### Pozytywne

- Zużycie miejsca mniejsze o rząd wielkości; 500 zdjęć to około 150 MB.
- Szybkie ładowanie na telefonie, szczególnie miniatur w wynikach.
- Karta SD nie jest obciążana zapisami — dłuższa żywotność sprzętu.
- Backup to kopia pliku bazy plus `rsync` katalogu zdjęć.
- Usunięte metadane GPS — brak przypadkowego wycieku lokalizacji domu.

### Negatywne — przyjęte świadomie

- **Utrata jakości jest nieodwracalna.** Po wgraniu nie ma powrotu do
  oryginału. Dla etykiety na pudełku bez znaczenia, dla zdjęcia tabliczki
  znamionowej z drobnym drukiem może być problemem.
- **1600 px to arbitralny próg.** Może okazać się za mały przy fotografowaniu
  numerów seryjnych. Zmiana wartości nie podniesie jakości już wgranych zdjęć.
- **Przetwarzanie obciąża procesor Pi.** Skalowanie zdjęcia 8 MP zajmuje
  na Pi 4 około sekundy — upload nie jest natychmiastowy.
- **Wymagany dysk zewnętrzny.** Dodatkowy sprzęt i punkt awarii; przy jego
  odłączeniu aplikacja przestaje działać.
- **Pliki i baza mogą się rozjechać.** Usunięcie wiersza bez usunięcia pliku
  zostawia śmieci. Potrzebny okresowy skrypt porządkujący.

### Kiedy wrócić do tej decyzji

- Okaże się, że 1600 px nie wystarcza do odczytania napisów na zdjęciach.
- Pojawi się potrzeba galerii zdjęć na przedmiot (obecnie poza zakresem, Q1).
- Zdjęcia zaczną zajmować tyle, że backup przestanie być wygodny.

## Powiązane

- `docs/architecture.md` §5.6 — przepływ przetwarzania
- `docs/domain-model.md` §6 — reguła G4
- ADR-0003 — SQLite, którego plik również trafia na dysk zewnętrzny
