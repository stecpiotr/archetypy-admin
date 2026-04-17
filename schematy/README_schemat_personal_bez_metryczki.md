# Schemat odpowiedzi i kodowania – ankieta personalna

Aktualizacja: 2026-04-17  
Źródło mapowania pytań: `admin_dashboard.py` (zmienna `archetypes`) oraz aktualny import/eksport z `db_utils.py`.

## 1) Kodowanie odpowiedzi
- Każde pytanie archetypowe (`Q1..Q48`) ma skalę **0..5**.
- Dozwolone wartości: `0, 1, 2, 3, 4, 5` (czyli **4 jest poprawna i liczona**).
- Poza zakresem lub brak wartości = rekord nie przechodzi walidacji kompletności 48 pytań.

## 2) Aktualny układ importu (zalecany)
- Początek rekordu: `respondent_id`, `created_at`, `response_id`.
- Następnie metryczka `M_*` (jeśli występuje w konfiguracji konkretnego badania).
- Jeśli w metryczce istnieje odpowiedź otwarta (`is_open = true`, np. „inna (jaka?)”), pojawia się kolumna `M_*_OTHER`.
- Dla wyboru odpowiedzi otwartej pole `M_*_OTHER` jest wymagane (nie może być puste).
- Na końcu odpowiedzi: `Q1..Q48` (każde pytanie w oddzielnej kolumnie).
- `respondent_id` może być pusty (system nada automatycznie, np. `R0001`).
- `created_at` i `response_id` są techniczne/opsjonalne przy imporcie.

## 3) Eksport odpowiedzi (aktualny)
- Kolejność kolumn w eksporcie:
  1. `respondent_id`
  2. `created_at`
  3. `response_id`
  4. kolumny metryczki `M_*` (jeżeli są)
  5. `Q1..Q48`
  6. `raw_total`

## 4) Liczenie archetypów
- 12 archetypów, każdy liczony z 4 pytań.
- Suma archetypu: zakres `0..20`.
- Procent archetypu: `(suma / 20) * 100`.
- Średnia dla badania: średnia procentów po wszystkich kompletnych rekordach.

## 5) Pliki
- `schemat_odpowiedzi_i_kodowania_personal_bez_metryczki.xlsx`
- `schemat_personal_pytania_1_48.csv`
- `schemat_personal_kodowanie_0_5.csv`
- `schemat_personal_mapa_archetypow.csv`
- `szablon_importu_personal_bez_metryczki.csv` (wariant minimalny: bez metryczki)
- `szablon_importu_personal_z_metryczka_przyklad.csv` (wariant przykładowy z metryczką)

## 6) Kompatybilność wsteczna
- System nadal akceptuje starszy format z kolumną `answers` (JSON), ale format rekomendowany i dokumentowany to tabela z `Q1..Q48`.
