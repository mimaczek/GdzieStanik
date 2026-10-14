# ADR-0001: Przedmiot może zawierać inne przedmioty

- **Status:** zaakceptowany
- **Data:** 2026-10-14
- **Dotyczy:** model domeny, schemat bazy, obliczanie ścieżek

## Kontekst

Pierwotny model zakładał dwie rozłączne encje: Lokalizacja tworzy drzewo
i zawiera rzeczy, Przedmiot jest liściem i niczego nie zawiera.

Rzeczywistość domowa tego nie potwierdza. Spakowana walizka, kosmetyczka,
plecak turystyczny, organizer na biurku, etui z narzędziami — to rzeczy,
które równocześnie są przedmiotami (mają właściciela, są przenośne, same
bywają szukane) i pojemnikami.

W modelu rozłącznym trzeba było wybrać jedno:

- **Walizka jako Lokalizacja** — traci właściciela i ilość, przestaje być
  wyszukiwalna jako rzecz, a po rozpakowaniu zostaje pusty węzeł drzewa.
- **Walizka jako Przedmiot** — nie da się zapisać, co jest w środku, więc
  rzeczy w niej znikają z katalogu.

Oba warianty wymuszają ręczną konwersję typu wpisu przy każdym spakowaniu
i rozpakowaniu — operacji zdarzającej się regularnie.

## Rozważane warianty

### A. Granica ostra: co zawiera rzeczy, jest Lokalizacją

Najprostszy model, jedno drzewo, ścieżka liczona jedną pętlą.

Odrzucony: wymusza konwersję encji przy pakowaniu, odbiera walizce właściciela
i obecność w wynikach wyszukiwania rzeczy. Konwersja Przedmiot↔Lokalizacja to
operacja gubiąca dane i trudna do wytłumaczenia użytkownikowi.

### B. Scalenie w jedną encję „Element”

Jeden typ z `parent_id` i flagą określającą rolę. Maksymalna elastyczność.

Odrzucony: pokój i długopis trafiają do jednej tabeli. Znikają sensowne
walidacje (pokój nie powinien mieć właściciela ani ilości), a model przestaje
odzwierciedlać język, którym mówi użytkownik.

### C. Flaga `jest_pojemnikiem` na przedmiocie

Zawartość mogą mieć tylko przedmioty z ustawioną flagą.

Odrzucony: użytkownik musiałby z góry deklarować, co kiedyś będzie pojemnikiem.
Flaga nie wnosi nic poza dodatkowym krokiem — i tak trzeba obsłużyć zagnieżdżenie.

### D. Przedmiot z `parent_item_id` — **wybrany**

Przedmiot ma dokładnie jednego rodzica: lokalizację albo inny przedmiot.
Każdy przedmiot może przyjąć zawartość, bez deklaracji z góry.

## Decyzja

Przedmiot otrzymuje pole `parent_item_id`. Obowiązuje niezmiennik:

```
(lokalizacja_id IS NOT NULL AND parent_item_id IS NULL)
OR
(lokalizacja_id IS NULL AND parent_item_id IS NOT NULL)
```

Wymuszane ograniczeniem `CHECK` w bazie, nie tylko walidacją aplikacyjną.

Dodatkowo przedmiot dostaje zdenormalizowane `dom_id`, wyliczane przy zapisie —
potrzebne do walidacji unikalności nazw (ADR-0002) bez wchodzenia po drzewie
przy każdej operacji.

## Konsekwencje

### Pozytywne

- Model odpowiada rzeczywistości: spakowana walizka zostaje przedmiotem
  z właścicielem, a jej zawartość jest widoczna w katalogu.
- Pakowanie i rozpakowywanie nie zmienia typu encji — to zwykła zmiana rodzica.
- Przeniesienie pojemnika przenosi zawartość automatycznie (reguła P8).
- Użytkownik nie musi z góry decydować, co jest pojemnikiem.

### Negatywne — przyjęte świadomie

- **Ścieżka wymaga dwóch pętli.** Najpierw w górę po `parent_item_id`, potem
  po `rodzic_id`. Algorytm jest istotnie bardziej złożony niż przy jednym drzewie.
- **Dwa rodzaje cykli do pilnowania.** Reguła L1 dla lokalizacji i bliźniacza
  P6 dla przedmiotów, każda z osobnym testem.
- **Kaskadowe usuwanie staje się realnym ryzykiem.** Skasowanie walizki może
  usunąć kilkanaście rzeczy. Wymagane potwierdzenie z liczbą obiektów (P5).
- **`dom_id` trzeba utrzymywać.** Przeniesienie pojemnika między domami musi
  zaktualizować całe poddrzewo. Denormalizacja wymaga dyscypliny.
- **Granica encji jest mniej ostra.** Skoro przedmiot ma rodzica i zawartość,
  różni go od lokalizacji już tylko to, że jest przenośny i ma właściciela.
  Zaciera się pojęciowa czystość modelu.

### Kiedy wrócić do tej decyzji

Jeśli po kilku miesiącach okaże się, że przedmioty-pojemniki są używane
sporadycznie, a koszt utrzymania drugiego drzewa (ścieżki, cykle, kaskady)
jest wyraźny — warto rozważyć powrót do wariantu A z wygodną konwersją w UI.

## Powiązane

- `docs/domain-model.md` §3.2 — reguły P1, P5–P11
- ADR-0002 — unikalność nazw, korzysta ze zdenormalizowanego `dom_id`
