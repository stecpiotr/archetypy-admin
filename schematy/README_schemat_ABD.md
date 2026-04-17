# Schemat odpowiedzi i kodowania pytań A, B i D

Wygenerowano: 2026-04-17 02:14:56
Źródło mapowań: db_jst_utils.py (ARCHETYPES, normalizatory), app.py (JST_A_PAIRS, JST_D_ITEMS).

## Pliki
- schemat_odpowiedzi_i_kodowania_ABD.xlsx (pełny schemat, 6 zakładek)
- schemat_A_pary_i_kodowanie.csv
- schemat_B_kodowanie.csv
- schemat_D_kodowanie.csv
- slownik_archetypow_1_12.csv
- szablon_importu_jst_z_metryczka_przyklad.csv

## Uwaga
Dla B2/D13 najbezpieczniejsze wejście to pełna nazwa archetypu lub numer 1..12.

## Spójność metryczki (JST + personal)
- Jeśli pytanie metryczkowe ma opcję otwartą (`is_open = true`, np. „inna (jaka?)”), w imporcie/eksporcie występuje kolumna pomocnicza `M_*_OTHER`.
- Dla wyboru opcji otwartej pole `M_*_OTHER` jest wymagane (nie może być puste).
