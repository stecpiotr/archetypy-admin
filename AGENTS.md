# AGENTS.md

## Cel
Ten plik utrzymuje stale zasady pracy w repo, tak aby po kompaktowaniu kontekstu, wznowieniu sesji lub przejsciu do nowego czatu kontynuowac prace bez restartu analizy.

## Zasady startowe
1. Na starcie kazdej sesji przeczytaj:
   - `AGENTS.md`
   - `PLANS.md`
   - `STATUS.md`
   - `DECISIONS.md`
2. Traktuj te pliki jako glowne zrodlo stanu projektu.
3. Nie rozpoczynaj pelnej analizy repo od zera, jezeli stan pracy jest juz zapisany w tych plikach.
4. Najpierw wskaz pierwszy niedomkniety krok z `PLANS.md`, a dopiero potem przejdz do pracy.

## Zasady operacyjne
1. Kontynuuj od pierwszego niedomknietego kroku z `PLANS.md`.
2. Po kazdym zakonczonym kroku zaktualizuj:
   - `PLANS.md`
   - `STATUS.md`
3. Jesli zapadla decyzja architektoniczna, domenowa, UX lub techniczna, dopisz ja do `DECISIONS.md`.
4. Nie powtarzaj analizy, ktora jest juz zapisana w `STATUS.md` lub `DECISIONS.md`.
5. W razie niepewnosci wpisz `BLOKER` lub `RYZYKO` do `STATUS.md` oraz zaproponuj minimalny kolejny krok.
6. Nie wykonuj szerokiego skanu calego repo, jesli zadanie dotyczy konkretnego pliku, modulu albo jednej funkcji.
7. Nie zmieniaj rzeczy niezwiązanych z biezacym krokiem.
8. Nie cofaj dzialajacych fragmentow bez wyraznej potrzeby.

## Definicja kroku
Krok jest zakonczony dopiero gdy:
1. kod i logika dla kroku sa wdrozone,
2. sa wykonane sensowne testy lokalne lub smoke-check,
3. pliki sterujace sa zaktualizowane,
4. wynik zostal krotko opisany w odpowiedzi.

## Raportowanie po kazdym kroku
Na koncu kazdej odpowiedzi pokaz tylko:
- `ZROBIONE:`
- `TERAZ ROBIE:`
- `NASTEPNY KROK:`

## Zakres repo
- `app.py` - glowne widoki panelu admina
- `send_link_jst.py` - wysylka i ponowna wysylka SMS/e-mail dla JST
- `jst_analysis.py` + `JST_Archetypy_Analiza/*` - generowanie raportow i warstwa wizualna raportu
- `db_jst_utils.py` - logika danych JST
- powiazany frontend ankiety znajduje sie w `../archetypy-ankieta` i wolno go zmieniac tylko wtedy, gdy wymaga tego aktualny krok
