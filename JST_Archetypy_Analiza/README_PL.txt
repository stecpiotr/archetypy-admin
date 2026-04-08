POZNAŃ – ANALIZA ARCHETYPÓW (CAWI) – NARZĘDZIE AUTOMATYCZNE
==========================================================

Co dostajesz?
-------------
1) automatyczną analizę bloków A+B+C+D (bez metryczki)
2) wynik „popyt archetypowy” P (12 archetypów)
3) wynik „doświadczenie miasta” E (12 archetypów)
4) wynik „luka/potrzeba” G (12 archetypów)
5) kontrolę jakości danych (spójność, klikanie, skrajności)
6) segmentację mieszkańców (automatyczny wybór liczby segmentów)
7) gotowy raport HTML + pliki CSV z wynikami

Wymagania (najprościej)
-----------------------
• Windows 10/11
• Zainstalowany Python 3.11+ (oficjalny instalator z python.org)
  Podczas instalacji ZAZNACZ: "Add python to PATH".

Krok po kroku (1:1)
-------------------
1) Utwórz folder:
   C:\Poznan_Archetypy_Analiza\

2) Skopiuj do niego ZAWARTOŚĆ tej paczki (wszystkie pliki).

3) Wgraj do tego folderu plik z eksportu CAWI jako:
   C:\Poznan_Archetypy_Analiza\data.csv

4) Uruchom analizę:
   • dwuklik na plik: 01_ANALIZA_START.bat

5) Wyniki znajdziesz w folderze:
   C:\Poznan_Archetypy_Analiza\WYNIKI\

Jak ma wyglądać data.csv (najważniejsze)
----------------------------------------
Najlepiej, żeby w CAWI kody pytań były dokładnie takie, jak poniżej.
Wtedy skrypt sam wszystko rozpozna bez ustawień.

Wymagane kolumny:
A1..A18  (liczby 1-5)
C1..C6   (A/B lub 1/2; A=opcja A, B=opcja B)
D1..D12  (A/B lub 1/2; A=PLUS, B=MINUS)

Blok B – są 2 możliwości (skrypt rozpoznaje automatycznie):
B1 wariant 1 (zalecany):
• kolumny B1_1, B1_2, ..., B1_12 (0/1)  -> zaznaczenie w B1
• kolumna B2 (liczba 1-12)               -> wybór 1 najważniejszej z B1

B1 wariant 2:
• kolumna B1 (tekst z listą wybranych opcji; np. "1;4;10")
• kolumna B2 (liczba 1-12)

D13 (wybór 1 z wygranych) – dwie możliwości:
• kolumna D13 zawiera identyfikator typu: "D7_A" albo "D7_B"
  (czyli: z której pary i którą odpowiedź wybrał)
ALBO
• brak D13 – wtedy skrypt policzy wyniki bez dodatkowego wzmocnienia (k=0)

Uwaga o kodowaniu odpowiedzi A/B
--------------------------------
• W blokach C i D: A oznacza pierwszą odpowiedź (A), B oznacza drugą (B).
• W D: A = wersja PLUS, B = wersja MINUS.

Co generuje narzędzie?
----------------------
WYNIKI\
• wyniki_indywidualne.csv   – P, E, G dla każdej osoby (12 archetypów)
• wyniki_grupowe.csv        – średnie, odchylenia, topy i rankingi
• przedzialy_ufnosci.csv    – bootstrap 95% CI dla P, E, G (domyślnie 2000 replik)
• segmenty.csv              – segmentacja (K wybierane automatycznie)
• raport.html               – raport do otwarcia w przeglądarce
• log.txt                   – informacje o danych, brakach, filtrach jakości

Jeżeli chcesz – można łatwo podmienić nazwę miasta w raporcie.
W pliku settings.json ustaw "city": "Poznań".


==============================
NOWOŚCI w wersji 2.0
==============================

1) Dodatkowe pliki CSV (poza wyniki_grupowe.csv):
- A_pary.csv – dla każdej pary A1..A18: % lewa / neutral / prawa + zwycięzca
- A_sila_archetypow.csv – „siła” archetypów z A (Bradley–Terry) + wins/losses
- B_ranking_trojki.csv – ranking „najczęściej w trójce” (B1)
- B_ranking_najwazniejsze.csv – ranking „najważniejsze” (B2)
- C_pary.csv – zwycięzcy scenariuszy C1..C6 (odsetki A/B)
- D_sentiment.csv – odsetek PLUS vs MINUS dla D1..D12
- D13_rozkład.csv – rozkład wyboru D13 + sentyment dla wybranego archetypu
- segmenty_profil.csv – NAZWY segmentów + opis + sugestie komunikacyjne + ryzyka

2) Wykres G_mean.png ma kolory:
- czerwony = luka (E < 50)
- niebieski = potrzeba bardziej preferencyjna (E ≥ 50)

3) Do testów dodano plik:
- PRZYKLAD_data_500_segmenty.csv (syntetyczne dane z wyraźnymi segmentami)
