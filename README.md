# Analiza POG

**Wtyczka QGIS do analizy ustaleń planu ogólnego gminy (POG) na potrzeby prac nad miejscowymi planami zagospodarowania przestrzennego (MPZP) i decyzjami o warunkach zabudowy (DWZ).**

## English summary

QGIS plugin for analysing Polish General Municipal Plans (POG) in relation to local spatial development plans (MPZP) and planning decisions (DWZ).

The plugin extracts relevant POG information for a selected planning area and generates a structured Excel report. It is designed specifically for the Polish spatial planning system.

---

## Po co powstała wtyczka?

Plan ogólny gminy zawiera dużą ilość danych przestrzennych i opisowych. Przy pracy nad konkretnym miejscowym planem zagospodarowania przestrzennego albo decyzją o warunkach zabudowy nie zawsze potrzebujemy jednak analizować całego POG.

Najczęściej potrzebujemy odpowiedzi na znacznie prostsze pytanie:

> **Jakie ustalenia planu ogólnego dotyczą konkretnego terenu, nad którym właśnie pracuję?**

**Analiza POG** automatyzuje zestawienie granicy analizowanego terenu z danymi POG i przygotowuje uporządkowany raport w formacie Excel.

Wtyczka została zaprojektowana jako narzędzie wspomagające codzienną pracę urbanisty z danymi POG.

Nie służy do tworzenia ani walidacji POG. Wykorzystuje gotowe, prawidłowe dane POG jako źródło informacji do dalszych analiz planistycznych.

---

# Tryby pracy

Wtyczka posiada dwa tryby analizy:

- **MPZP**
- **DWZ**

Po uruchomieniu wtyczki użytkownik wybiera tryb, w którym chce pracować.

---

# Tryb MPZP

Tryb MPZP służy do analizy granic miejscowego planu zagospodarowania przestrzennego w odniesieniu do ustaleń POG.

Możliwe jest analizowanie:

- jednego MPZP,
- kilku MPZP znajdujących się w jednej warstwie,
- planów posiadających części nieprzylegające do siebie,
- obiektów identyfikowanych na podstawie wybranego pola atrybutowego.

Wtyczka może wykorzystać:

- GML POG wskazany z dysku,
- albo odpowiednie warstwy POG znajdujące się już w projekcie QGIS.

### Analiza MPZP obejmuje m.in.:

- identyfikację stref planistycznych występujących w granicach MPZP,
- powierzchnię części stref znajdujących się w granicach analizowanego terenu,
- udział stref w powierzchni analizowanego terenu,
- profile funkcjonalne podstawowe,
- profile funkcjonalne dodatkowe,
- podstawowe parametry stref,
- informacje dotyczące OUZ,
- kontrolę pokrycia analizowanego obszaru przez dane POG.

Jeżeli warstwa zawiera wiele obiektów MPZP, wtyczka umożliwia wskazanie pola, według którego obiekty mają zostać pogrupowane.

---

# Tryb DWZ

Tryb DWZ służy do analizy terenów inwestycji w odniesieniu do ustaleń POG.

Warstwa terenów inwestycji może zawierać wiele poligonów.

Każdy poligon jest traktowany jako **odrębny teren inwestycji**, nawet jeżeli kilka obiektów posiada tę samą wartość w wybranym polu opisowym.

Dzięki temu możliwe jest np. przeprowadzenie jednego procesu dla kilku terenów inwestycji i otrzymanie jednego raportu zawierającego wyniki dla każdego z nich.

### Identyfikacja terenów

Użytkownik wskazuje pole z warstwy terenów inwestycji, którego wartość ma być używana do opisania analizowanego terenu.

Może to być np.:

- numer działki,
- obręb,
- oznaczenie sprawy,
- własny identyfikator terenu.

Wartość tego pola jest przenoszona do raportu.

**Ważne:** identyczna wartość pola nie powoduje połączenia obiektów. Jeżeli w warstwie znajdują się cztery poligony opisane jako `170/1`, każdy z nich pozostaje osobnym terenem analizy.

### Analiza wszystkich lub tylko zaznaczonych terenów

W trybie DWZ dostępna jest opcja:

> **Analizuj tylko zaznaczone obiekty**

Jeżeli opcja jest wyłączona, analizowane są wszystkie obiekty warstwy.

Jeżeli opcja jest włączona, analizowane są wyłącznie obiekty zaznaczone w QGIS.

Pozwala to np. przygotować jeden raport dla kilku wybranych terenów bez konieczności tworzenia osobnych warstw.

### OUZ

W trybie DWZ obecność obszaru uzupełnienia zabudowy (OUZ) w POG jest traktowana jako warunek konieczny dla wygenerowania raportu.

Jeżeli w wybranym POG nie wyznaczono OUZ, wtyczka nie generuje raportu i informuje o tym użytkownika.

---

# Dane wejściowe

## GML POG

Wtyczka może korzystać z pliku GML POG wskazanego z dysku.

Możliwe jest również korzystanie z danych POG znajdujących się już w projekcie QGIS.

W przypadku wskazania pliku z dysku wtyczka sprawdza, czy zawiera on wymagane dane POG.

Jeżeli wskazany zostanie plik w innym formacie, użytkownik otrzyma komunikat:

> **Wskaż prawidłowy plik .gml**

Jeżeli wskazany zostanie plik `.gml`, który nie zawiera wymaganych danych POG:

> **Wybrany plik GML nie zawiera wymaganych danych POG. Wskaż prawidłowy plik GML POG.**

## Warstwa analizowanego terenu

W zależności od trybu użytkownik wskazuje:

- **MPZP** — warstwę zawierającą granice MPZP,
- **DWZ** — warstwę zawierającą tereny inwestycji.

W DWZ użytkownik może dodatkowo wskazać pole opisujące analizowany teren.

---

# Raport wynikowy

Wyniki analizy są zapisywane w pliku **Excel (`.xlsx`)**.

Użytkownik sam wskazuje miejsce zapisu raportu.

Raport zawiera uporządkowane dane pozwalające na dalszą pracę w Excelu.

## STREFY

Arkusz zawiera informacje o strefach POG występujących w analizowanym terenie.

W zależności od trybu obejmuje m.in.:

- identyfikację analizowanego terenu,
- oznaczenie strefy,
- symbol,
- powierzchnię,
- udział powierzchni,
- profile podstawowe,
- profile dodatkowe,
- maksymalną intensywność zabudowy,
- maksymalny udział powierzchni zabudowy,
- maksymalną wysokość zabudowy,
- minimalny udział powierzchni biologicznie czynnej.

Profile podstawowe i dodatkowe są przedstawiane oddzielnie.

Profile dodatkowe są wyróżnione **szarym wypełnieniem**, dzięki czemu można je łatwo odróżnić od profili podstawowych.

## PROFILE

Arkusz zawiera szczegółowe zestawienie profili funkcjonalnych przypisanych do stref POG.

Profile podstawowe i dodatkowe są rozdzielone i zachowują kolejność wynikającą z danych POG.

## OUZ

Arkusz zawiera informacje dotyczące obszarów uzupełnienia zabudowy występujących w analizowanym terenie.

W szczególności raportuje:

- oznaczenie OUZ,
- powierzchnię OUZ,
- powierzchnię OUZ znajdującą się w analizowanym terenie,
- udział OUZ w analizowanym terenie.

## KONTROLA

Arkusz zawiera informacje kontrolne dotyczące przebiegu analizy.

Służy m.in. do wskazania sytuacji wymagających sprawdzenia przez użytkownika.

Uwagi kontrolne są wyróżnione **czerwoną czcionką**.

---

# Czy wtyczka waliduje POG?

**Nie.**

Analiza POG nie zastępuje narzędzi służących do tworzenia i technicznej walidacji danych planu ogólnego.

Wtyczka zakłada, że użytkownik dysponuje prawidłowymi danymi POG i wykorzystuje je do analizy konkretnego terenu.

Jej zadaniem jest przede wszystkim:

> **wydobycie z danych POG informacji potrzebnych do dalszej pracy planistycznej.**

---

# Instalacja

1. Pobierz plik ZIP z wybraną wersją wtyczki.
2. W QGIS wybierz:
   **Wtyczki → Zarządzaj i instaluj wtyczki → Instaluj z ZIP**
3. Wskaż pobrany plik `.zip`.
4. Zainstaluj wtyczkę.
5. Uruchom **Analiza POG** z menu wtyczek QGIS.

Nie należy rozpakowywać pliku ZIP przed instalacją.

---

# Wymagania

Wtyczka jest rozwijana i testowana w środowisku:

- **QGIS 3.34.15**
- Python dostarczany z QGIS.

Aktualna wersja testowa została przygotowana z myślą o pracy z danymi POG zgodnymi z obowiązującym modelem danych.

---

# Ważne informacje

Wynik analizy należy traktować jako **narzędzie wspomagające pracę urbanisty**, a nie jako automatyczną interpretację przepisów.

Wtyczka zestawia dane przestrzenne i atrybutowe POG z określonym przez użytkownika terenem. Ostateczna ocena znaczenia ustaleń POG dla konkretnej sprawy pozostaje po stronie osoby wykonującej analizę.

W szczególności raport nie zastępuje:

- analizy przepisów prawa,
- analizy dokumentacji planistycznej,
- oceny stanu faktycznego,
- weryfikacji danych źródłowych,
- indywidualnej oceny urbanistycznej.

---

# Testowanie i zgłaszanie uwag

Wtyczka jest rozwijana z myślą o praktycznym wykorzystaniu przez urbanistów.

Jeżeli podczas pracy znajdziesz:

- błąd,
- nieprawidłowy wynik,
- nieczytelny fragment raportu,
- nietypowy przypadek, którego wtyczka nie obsługuje,
- pomysł na przydatną funkcję,

zgłoś go wraz z możliwie dokładnym opisem.

Szczególnie pomocne są:

- zrzut ekranu,
- opis wykonanych czynności,
- informacja, czego oczekiwano,
- informacja, jaki wynik został faktycznie otrzymany.

**Nie poprawiaj ręcznie danych przed zgłoszeniem problemu**, jeżeli celem jest sprawdzenie działania wtyczki — nietypowe przypadki są szczególnie wartościowe podczas jej rozwoju.

---

# Rozwój wtyczki

Aktualna wersja koncentruje się na wykorzystaniu danych POG w pracach nad:

- MPZP,
- DWZ.

W przyszłości możliwe jest rozszerzenie wtyczki o kolejne funkcje, w tym analizę odwrotną, pozwalającą na sprawdzanie relacji pomiędzy projektowanym MPZP a ustaleniami POG.

---

# Licencja

Kod wtyczki jest udostępniany na warunkach **MIT License**.

Dokumentacja projektu jest udostępniana na warunkach **CC BY 4.0**.
