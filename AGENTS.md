# AGENTS.md

## Cel
Plik utrzymuje stale zasady pracy, tak aby po kompaktowaniu kontekstu lub wznowieniu sesji kontynuować bez restartu analizy.

## Zasady operacyjne
1. Na starcie kazdej sesji przeczytaj: `AGENTS.md`, `PLANS.md`, `STATUS.md`, `DECISIONS.md`.
2. Kontynuuj od pierwszego niedomknietego kroku z `PLANS.md`.
3. Po kazdym zakonczonym kroku zaktualizuj: `PLANS.md` i `STATUS.md`.
4. Jesli zapadla decyzja architektoniczna, domenowa lub UX, dopisz ja do `DECISIONS.md`.
5. Nie powtarzaj analizy, ktora jest juz zapisana w `STATUS.md` lub `DECISIONS.md`.
6. W razie niepewnosci wpisz `BLOKER` lub `RYZYKO` do `STATUS.md` oraz zaproponuj minimalny kolejny krok.

## Definicja kroku
Krok jest zakonczony dopiero gdy:
1. kod i logika dla kroku sa wdrozone,
2. sa wykonane sensowne testy lokalne lub smoke-check,
3. pliki sterujace sa zaktualizowane.

## Zakres repo
- `app.py` - glowne widoki panelu admina.
- `send_link_jst.py` - wysylka i ponowna wysylka SMS/e-mail dla JST.
- `jst_analysis.py` + `JST_Archetypy_Analiza/*` - generowanie raportow i warstwa wizualna raportu.
- `db_jst_utils.py` - logika danych JST.
- Powiazany frontend ankiety znajduje sie w `../archetypy-ankieta` (do zmian, gdy krok tego wymaga).

