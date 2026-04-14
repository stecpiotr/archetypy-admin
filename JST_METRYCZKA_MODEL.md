# Model: Metryczka Konfigurowalna JST (v1)

## Cel
Umożliwić konfigurację metryczki dla badań JST:
- 5 pytań bazowych (obecny standard) jako rdzeń,
- możliwość dodawania pytań dodatkowych z własnym kodowaniem,
- stabilne mapowanie do importu i raportów bez psucia spójności historycznych danych.

## Założenia projektowe
1. Rdzeń metryczki jest obowiązkowy i ma stałe identyfikatory:
   - `M_PLEC`, `M_WIEK`, `M_WYKSZT`, `M_ZAWOD`, `M_MATERIAL`.
2. Treść pytań i etykiety odpowiedzi rdzenia mogą być edytowalne, ale:
   - `id` i `db_column` pytań rdzenia są niezmienne.
3. Pytania dodatkowe:
   - mają `scope = "custom"`,
   - muszą mieć unikalny `db_column`,
   - każdy wariant odpowiedzi ma własny `code`.
4. Każde badanie JST przechowuje własną definicję metryczki (`metryczka_config`).

## Struktura danych
Definicja metryczki dla badania:

```json
{
  "version": 1,
  "questions": [
    {
      "id": "M_PLEC",
      "scope": "core",
      "db_column": "M_PLEC",
      "prompt": "Proszę o podanie płci.",
      "required": true,
      "multiple": false,
      "aliases": ["M_PLEC", "Płeć", "Plec"],
      "options": [
        {"label": "kobieta", "code": "1"},
        {"label": "mężczyzna", "code": "2"}
      ]
    }
  ]
}
```

## Zmiany w bazie
Tabela `jst_studies`:
- `metryczka_config JSONB NULL`
- `metryczka_config_version INTEGER NOT NULL DEFAULT 1`

Nowe badania dostają domyślną konfigurację 5 pytań.

## Mapowanie do importu
Reguły:
1. Dla rdzenia (`scope = core`) parser importu szuka:
   - najpierw po `db_column`,
   - potem po aliasach (`aliases`).
2. Dla pytań dodatkowych parser szuka po `db_column` i aliasach.
3. Wartości importowe mapowane są do `code` odpowiedzi:
   - po `code`,
   - po etykiecie (`label`) z normalizacją tekstu.
4. Nieznane kolumny/metadane z importu nie nadpisują rdzenia.

## Mapowanie do raportów
v1 (bez regresji):
1. Obecne raporty i ważenie działają nadal na rdzeniu 5 zmiennych.
2. Pytania dodatkowe są przechowywane i gotowe do użycia w kolejnych iteracjach raportowych.
3. Dla raportów demograficznych:
   - rdzeń pozostaje źródłem tabel i wag poststratyfikacyjnych,
   - pytania dodatkowe mogą wejść jako nowe przekroje po wdrożeniu panelu filtrów.

## Spójność i bezpieczeństwo danych
1. `id`/`db_column` rdzenia niezmienne => brak rozpadu parsera raportowego.
2. Konfiguracja ma wersję (`version`) i normalizator.
3. Dla historycznych badań bez konfiguracji:
   - runtime dostarcza konfigurację domyślną (fallback).
4. Kolizje `db_column` między pytaniami dodatkowymi są odrzucane.

## Kolejność wdrożenia
1. Fundament (zrobione):
   - model danych + walidator + kolumny DB.
2. UI administracyjne (kolejny etap):
   - zakładka `Metryczka` w ustawieniach JST,
   - edycja rdzenia + dodawanie pytań dodatkowych.
3. Front ankiety JST:
   - render metryczki na podstawie `metryczka_config`.
4. Import/raport:
   - rozszerzenie parsera o pytania dodatkowe i konfigurację.
