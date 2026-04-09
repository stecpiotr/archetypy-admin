# STATUS.md

## Stan biezacy (2026-04-09)

### Punkt startowy
- Odczytano stan repo i brak istniejacych plikow sterujacych (`AGENTS.md`, `PLANS.md`, `STATUS.md`, `DECISIONS.md`).
- Utworzono pliki sterujace i zapisano plan 8 krokow.
- Ustalono wykonanie teraz tylko `Kroku 1` z `PLANS.md`.

### Zrobione w tej sesji
- Krok 1 zrealizowany:
  1. `send_link_jst.py`:
     - resend SMS pobiera kontekst JST po `row.study_id` i nie ufa tylko aktualnemu wyborowi z UI,
     - dodano walidacje zgodnosci `row.study_id` z aktywnym badaniem,
     - wymuszane jest poprawne wstrzykniecie linku `?t=<token>` do tresci SMS,
     - dla domyslnego szablonu SMS wymuszana jest poprawna nazwa JST.
  2. `db_jst_utils.py`:
     - dodano RPC `public.get_jst_token_meta(p_token text)` zwracajace:
       `channel`, `contact`, `study_slug`, `completed`, `rejected`.
  3. `archetypy-ankieta`:
     - `src/lib/tokens.ts`: dodano klienta RPC `getJstTokenMeta`,
     - `src/App.tsx`: blokada wejscia po `completed_at` + przekierowanie do poprawnego `slug` jesli token wskazuje inne badanie,
       z fallbackiem do `isJstTokenCompleted` gdy nowe RPC nie jest jeszcze dostepne,
     - `src/AlreadyCompleted.tsx`: komunikat dynamiczny:
       `Ankieta dla tego numeru telefonu ...` albo `Ankieta dla tego adresu e-mail ...`.
  4. Testy techniczne:
     - `python -m py_compile send_link_jst.py db_jst_utils.py` (OK),
     - `npm run build` w `archetypy-ankieta` (OK).

### W toku
- Oczekuje realizacji `Krok 8` (stabilnosc eksportu HTML/ZIP, osadzanie zasobow, fonty i UX pobierania).
- Pierwszy krok wykonawczy: audyt trybu standalone HTML vs ZIP i decyzja, czy wymuszamy ZIP albo poprawiamy self-contained HTML.

### Start Hotfix H-004 (2026-04-09, wieczor)
- Zgloszone regresje:
  1. `🧭 Matching`: blad renderu porownania profili (`ImageMixin.image() got an unexpected keyword argument 'use_container_width'`) i brak kompletnego zestawienia profili.
  2. Raport Poznania: nadal rozjazd licznikow `TOP3/TOP1` (widoczne stare wartosci `2745` i `1048`).
- Pierwszy krok wykonawczy:
  - przejrzec `app.py` (render wykresow Matching) oraz pipeline raportu (`jst_analysis.py` + `analyze_poznan_archetypes.py`) i potwierdzic, gdzie wynik traci poprawki.

### Zrobione po uwagach (Krok 1A)
- `archetypy-ankieta/src/JstSurvey.tsx`:
  - dla `M_ZAWOD = "inna (jaka?)"` dodano warunkowe pole tekstowe,
  - wpis staje sie obligatoryjny (walidacja przed przejsciem dalej),
  - wartosc jest zapisywana do payloadu jako `M_ZAWOD_OTHER`.
- `archetypy-ankieta/src/JstSurvey.css`:
  - dodano style nowego pola (normal + missing + dark mode).
- `archetypy-ankieta/src/App.tsx`:
  - blokada tokenu JST dziala teraz dla obu stanow:
    - `completed`,
    - `rejected` (`Nie spelnia`).
- `archetypy-admin/db_jst_utils.py`:
  - `is_jst_token_completed` zwraca `true` rowniez dla `rejected_at IS NOT NULL`,
    wiec fallback frontendu tez blokuje ponowne wejscie po `Nie spelnia`.
- Testy techniczne:
  - `npm run build` w `archetypy-ankieta` (OK),
  - `python -m py_compile db_jst_utils.py` (OK).

### Zrobione po kolejnych uwagach (Krok 1B)
- `send_link_jst.py`:
  - resend e-mail ma teraz walidacje `row.study_id == selected_study.id`,
  - resend e-mail buduje kontekst JST po rekordzie (`study_id`) i wymusza poprawny link tokenu,
  - dla domyslnej tresci/tematu e-mail wymuszana jest tresc i temat zgodna z aktualna JST,
  - analogiczne uszczelnienie dodane przy zwyklej wysylce e-mail (nie tylko resend).
- `app.py`:
  - stopka build pobiera hash i date ostatniego commita z git (z fallbackiem do env/local).
- `archetypy-ankieta/src/JstSurvey.tsx`:
  - usunieto ukrywanie "wypelnionych" sekcji po bledzie walidacji (koniec z pustym ekranem),
  - `inna (jaka?)` wymaga min. 3 znakow i ma precyzyjny komunikat bledu.
- Testy techniczne:
  - `python -m py_compile app.py send_link_jst.py db_jst_utils.py` (OK),
  - `npm run build` w `archetypy-ankieta` (OK).

### Zrobione w Kroku 2 (Matching / Demografia)
- `app.py` (`matching_view`, zakladka `Demografia`):
  - przeniesiono styl kart i tabel do wariantu wizualnie zgodnego z `Demografia priorytetu (B2)`:
    - karty: grid `minmax(175px, 1fr)`, identyczna typografia i kolorystyka B2,
    - tabela: grube obramowania (`3px`), styl naglowkow, separator grup zmiennej, bary i kolory roznic jak w B2,
    - dodano ikony zmiennych (`Płeć`, `Wiek`, `Wykształcenie`, `Status zawodowy`, `Sytuacja materialna`) i kategorii.
  - poszerzono kontener tabeli (`max-width: 100%`), aby uniknac utraty danych przy szerszych widokach.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Kroku 2 - iteracja dopieszczajaca
- `app.py` (`matching_view`, `tab_demo`):
  - dodano obramowane sekcje `Statystyczny profil demograficzny` i `Profil demograficzny` (styl box jak B2),
  - wyrownano typografie tabeli (stale rozmiary fontow naglowkow i komorek),
  - dopracowano obramowania tabeli (gruba prawa krawedz, naglowki, obramowania sekcji),
  - wrapper tabeli ustawiony jak w B2 (`max-width:940px`, `min-width:720px`) dla zgodnosci wizualnej.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Kroku 2 - iteracja wagowania i etykiet tabeli
- `app.py` (`matching_view`, `tab_demo`):
  - naglowki sekcji `📌 ...` i `👥 ...` zwiekszone (wieksza czcionka),
  - kolumna referencyjna tabeli ma teraz dynamiczny naglowek:
    `{nazwa JST} / (po wagowaniu)`,
  - procenty w tabeli demografii liczone z uwzglednieniem wag poststratyfikacyjnych (plec × wiek), jesli sa zdefiniowane w badaniu JST,
  - roznica nazwana `Róznica (w pp.)`,
  - wartosci w kolumnie roznicy maja normalna czcionke (bez pogrubienia).
  - dodano notke techniczna pod tabela:
    - gdy wagi sa dostepne: informacja o liczeniu po wagowaniu,
    - gdy brak wag: informacja o rozkladzie surowym.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Kroku 2 - finalne dopieszczenie typografii
- `app.py` (`matching_view`, `tab_demo`):
  - zwiekszono rozmiar naglowkow sekcji `📌 STATYSTYCZNY PROFIL DEMOGRAFICZNY` i `👥 PROFIL DEMOGRAFICZNY`,
  - naglowki kart (np. `💰 SYTUACJA MATERIALNA`) ustawione na `12px`,
  - wartosci procentowe kart (`xx.x% • yy.y pp`) ustawione na `12.5px`,
  - czcionka tabeli `Profil demograficzny` ustawiona na `13.5px`.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Kroku 3 (bez pustych koncowych wierszy tabel)
- `app.py`:
  - `🧭 Matching / Podsumowanie`: wysokosc `st.dataframe` ustawiona ciasno do liczby rekordow (`cmp_height`),
  - `Badania mieszkancow - panel`: wysokosc tabeli statystyk JST ustawiona ciasno do liczby rekordow (`jst_height`).
- Efekt:
  - po ostatnim rekordzie nie sa renderowane puste koncowe rzedy.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Kroku 4 (spojnosc metryk i formatow liczbowych)
- `app.py`:
  - `_calc_jst_target_profile` rozszerzone o audyt komponentow A/B1/B2/D13:
    - pokrycie poprawnych odpowiedzi A/B2/D13,
    - srednia liczba wskazan B1,
    - srednie skladowe na archetyp (`A`, `B1`, `B2`, `D13`, `TOTAL`),
  - `matching_view` zapisuje i renderuje audyt w sekcji
    `Jak liczony jest poziom dopasowania?`,
  - dodano jednoznaczny opis przeliczenia komponentu A:
    `p_prawy = (wartosc_A - 1) / 6`, `p_lewy = 1 - p_prawy`,
    oraz pelna formule:
    `score = 100 * (0.40*A_norm + 0.20*B1_hit + 0.25*B2_hit + 0.15*D13_hit)`,
  - tabela `🧭 Matching / Podsumowanie` renderuje stale `x.y` (takze dla liczb calkowitych):
    - `Profil polityka (%)`,
    - `Oczekiwania mieszkancow (%)`,
    - `Różnica |Δ|`.
- `JST_Archetypy_Analiza/analyze_poznan_archetypes.py`:
  - tytul raportu ma teraz postac:
    `Raport: Archetypy/Wartosci - {JST} (N={liczba respondentow})`.
- `jst_analysis.py`:
  - synchronizacja silnika raportu dla istniejacych katalogow `_runs/*`,
    aby poprawki generatora (w tym `(N=...)`) dzialaly bez recznego czyszczenia runa.
- Test techniczny:
  - `python -m py_compile app.py jst_analysis.py JST_Archetypy_Analiza\\analyze_poznan_archetypes.py` (OK).

### Zrobione w Kroku 5 (nowa metryka dopasowania + UX sekcji dopasowan)
- `app.py` (`matching_view`):
  - zamieniono wzor `100 - MAE` na metryke mieszana:
    `match = clamp(0,100, 0.40*(100-MAE) + 0.25*(100-RMSE) + 0.35*(100-TOP3_MAE))`,
  - dodano skladowe metryki do wyniku:
    - `MAE`,
    - `RMSE`,
    - `TOP3_MAE` (srednia 3 najwiekszych luk),
    - opis pasma oceny dopasowania,
  - w podsumowaniu matching dodano panel metryk (MAE/RMSE/TOP3) i opis pasma,
  - przebudowano sekcje informacji o dopasowaniach:
    - `Najlepsze dopasowania` i `Największe luki` jako czytelne boksy z chipami,
    - kazdy archetyp pokazuje konkretne `|Δ|` w pp.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Kroku 6 (audyt i korekta agregacji pytan)
- `JST_Archetypy_Analiza/analyze_poznan_archetypes.py`:
  - poprawiono `B_rankings`:
    - kolumna `liczba` dla `B1_top3`, `B2_top1` i `B1_trojki` jest liczona surowo (bez wag),
    - kolumna `%` pozostaje liczona na wagach (metodycznie dla udzialow).
  - uszczelniono parser B1 (`_clean_binary_mark`): obsluga m.in. `1`, `1.0`, wariantow bool i dodatnich wartosci liczbowych,
  - rozszerzono parser archetypu (`_parse_archetype_index`) o formaty numeryczne:
    `1..12`, `0..11`, prefiksy typu `nr 1`,
  - tabela `mentions_by_question.csv` jest liczona surowo (raw), bez mieszania wag i zaokraglen,
  - dodano audyt spojnosc agregacji:
    - `question_aggregation_audit.csv` (A1..A18, B1, B2, D13),
    - kolumny: `expected_raw`, `reported_raw`, `delta`,
    - ostrzezenie w logu, jesli `delta != 0`.
- Weryfikacja na danych Poznania (`_runs/.../9a69...`):
  - `B1_top3.csv`: suma `liczba` = `2741` (zgodna z baza),
  - `B2_top1.csv`: suma `liczba` = `1050` (zgodna z baza),
  - `question_aggregation_audit.csv`: `delta = 0` dla wszystkich pytan.
- Testy techniczne:
  - `python -m py_compile JST_Archetypy_Analiza\\analyze_poznan_archetypes.py jst_analysis.py app.py` (OK),
  - pelny run generatora raportu dla Poznania: `python analyze_poznan_archetypes.py` (OK).

### Zrobione w Kroku 7 (porownanie profili polityk vs mieszkancy)
- `admin_dashboard.py`:
  - dodano selektor `Porownaj z badaniem mieszkancow (JST)` w widoku
    `📊 Sprawdz wyniki badania archetypu`,
  - selektor ma domyslny wybor JST dopasowany po nazwie miasta polityka (jesli znaleziony),
  - dodano obliczanie profilu JST (A/B1/B2/D13 -> 0..100) bezposrednio w module raportu personalnego.
- Radar 0-20:
  - wspolny wykres dla polityka i mieszkancow JST (nakladanie dwoch profili),
  - osobne kolory TOP3 dla polityka i dla mieszkancow,
  - czytelna legenda rozdzielajaca oba zestawy TOP3 oraz linie porownawcze.
- Profil 0-100:
  - sekcja profilu archetypowego pokazuje dwa kola obok siebie:
    `Profil archetypowy {osoba}` vs `Profil archetypowy mieszkancow {JST} (N=...)`,
  - na mobile profile sa renderowane jeden pod drugim.
- Test techniczny:
  - `python -m py_compile admin_dashboard.py app.py` (OK).

### Zrobione w Hotfix H-001 (stopka build)
- `app.py`:
  - usunieto twarda sciezke `git` dla Linuksa (`/usr/bin/git`),
  - dodano wykrywanie binarki przez `shutil.which("git")` (fallback: `git`),
  - dzieki temu stopka `build: ... | commit: ...` pobiera date i hash takze na Windows.
- Test techniczny:
  - `python -m py_compile app.py` (OK),
  - `git -C ... rev-parse --short=8 HEAD` (OK),
  - `git -C ... show -s --format=%cI HEAD` (OK).

### Zrobione w Hotfix H-002 (korekta lokalizacji porownan z Kroku 7)
- `admin_dashboard.py`:
  - cofnięto dodatki porownania JST z widoku `📊 Sprawdz wyniki badania archetypu`,
  - przywrocono poprzedni render radaru i pojedynczego profilu 0-100.
- `app.py` (`matching_view`, `Podsumowanie`):
  - dodano sekcje `Porownanie profili archetypowych`,
  - radar 0-20 nakladany: polityk vs mieszkancy JST,
  - osobne kolory TOP3 dla polityka i mieszkancow + legenda,
  - profile 0-100 obok siebie: polityk oraz mieszkancy JST.
- Test techniczny:
  - `python -m py_compile app.py admin_dashboard.py` (OK).

### Zrobione w Hotfix H-003 (stopka build na deployu)
- `app.py`:
  - rozbudowano `_app_build_signature()` o fallbacki dla srodowiska deploy bez `.git`,
  - dodano pobieranie metadanych z GitHub API (`repo/branch`) z cache,
  - dodano obsluge env/secrets dla SHA i czasu commita,
  - commit time konwertowany jest do strefy `Europe/Warsaw`,
  - przy znanym SHA stopka pokazuje `commit: <sha8>` zamiast `local`.
- Test techniczny:
  - `python -m py_compile app.py` (OK),
  - test zapytania API GitHub (`stecpiotr/archetypy-admin/main`) zwraca poprawny SHA i timestamp.

### Zrobione w Hotfix H-004 (Matching + wymuszenie przeliczenia po zmianie silnika)
- `app.py` (`matching_view`, zakladka `Podsumowanie`):
  - naprawiono regresje renderu porownania profili 0-100:
    - dodano kompatybilny fallback dla `st.image` (`use_container_width` -> `use_column_width` -> bez parametru),
    - sekcja dwoch profili (polityk vs mieszkancy JST) nie wywala juz wyjatku.
  - uporzadkowano radar porownawczy 0-20:
    - wylaczono domyslna legende Plotly (ktora dublowala opisy i zasmiecala wykres),
    - dodano czytelny podpis linii (polityk vs mieszkancy) + pozostawiono legende TOP3.
- `jst_analysis.py`:
  - hash runa (`.source_hash.txt`) uwzglednia SHA pliku generatora
    `JST_Archetypy_Analiza/analyze_poznan_archetypes.py`,
  - efekt: po zmianie logiki generatora klikniecie `Generuj raport` wymusza aktualne przeliczenie,
    nawet gdy dane wejciowe JST sie nie zmienily.
- Test techniczny:
  - `python -m py_compile app.py jst_analysis.py` (OK).

### Start Hotfix H-005 (2026-04-09, pozny wieczor)
- Zgloszenie usera: wykresy w `🧭 Matching` sa nadal brzydko ulozone (nakladanie i niski poziom czytelnosci).
- Pierwszy krok wykonawczy:
  - przebudowac sekcje `Porownanie profili archetypowych` w `app.py`:
    kontrolowana wysokosc radaru + wyrazna separacja od profili 0-100 + bezpieczny rozmiar obrazow.

### Zrobione w Hotfix H-005 (estetyka i uklad wykresow Matching)
- `app.py` (`matching_view`, `Podsumowanie`):
  - radar porownawczy 0-20:
    - ustawiono stala wysokosc `height=560`,
    - wylaczono `displayModeBar`, aby usunac wizualny "szum",
    - zostawiono czytelny podpis linii (polityk vs mieszkancy).
  - legenda TOP3:
    - przebudowana na prosty, stabilny uklad w 2 kolumnach (`TOP3 polityka` / `TOP3 mieszkancow`),
    - usunieto poprzedni, bardziej podatny na kolizje blok HTML typu flex-wrap.
  - profile 0-100:
    - dodano oddzielajacy podtytul `Profile archetypowe 0-100`,
    - render obrazow ograniczono do `width=520` (bez nadmiernego rozlewania),
    - zachowano fallback kompatybilnosci dla starszych wersji Streamlit.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### BLOKERY / RYZYKA
- Brak blockerow technicznych.
- Ryzyko wdrozeniowe:
  - nowa funkcja RPC `get_jst_token_meta` musi zostac zastosowana w bazie (przez uruchomienie `ensure_jst_schema()` po deployu `archetypy-admin`).
  - do potwierdzenia na danych produkcyjnych: manualny E2E scenariusz resend SMS + ponowne wejscie tym samym tokenem.
  - do potwierdzenia na danych produkcyjnych: czy wszystkie badania JST maja uzupelnione cele poststratyfikacyjne (jesli nie, fallback jest surowy i komunikowany notka).

### Nastepny konkretny krok wykonawczy
- Rozpoczac `Krok 8`: naprawic zachowanie eksportu raportu (HTML/ZIP),
  z naciskiem na standalone HTML, osadzanie zasobow i UX przyciskow pobierania.
