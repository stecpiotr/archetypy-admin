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

### Zrobione: Hotfix H-011 (2026-04-10, popołudnie)
- `app.py` (`🧭 Matching -> Podsumowanie`):
  - `Oczekiwania mieszkańców` liczone nową metodą ISOA/ISOW:
    - `E = 0.50*z(A) + 0.20*z(B1) + 0.30*z(B2)`,
    - `D = 0.70*z(N) + 0.30*z(MBAL)`,
    - `SEI_raw = 0.80*E + 0.20*D`,
    - `SEI_100` przez min-max do `0..100` (fallback `50`),
  - dodane helpery komponentowe (`compute_top3_share`, `compute_top1_share`, `compute_negative_experience_share`, `compute_most_important_experience_balance`),
  - dodane radio trybu etykiet (`Archetypy`/`Wartości`) i dynamiczne nazewnictwo `ISOA` / `ISOW`,
  - etykiety tabeli pozostają bez `"(%)"` przy `Profil polityka` i `Oczekiwania mieszkańców`,
  - audyt komponentów pokazuje brakujące składowe bez wywalania sekcji.
- `app.py` (`📊 Analiza badania mieszkańców`):
  - podniesiony techniczny limit podglądu panelowego (`max(secret, safe_limit, 260MB)`),
  - pełny podgląd dla dużych raportów można uruchamiać domyślnie z jasnym komunikatem (bez sugerowania błędu generowania).
- `JST_Archetypy_Analiza/analyze_poznan_archetypes.py`:
  - policzony i zapisany nowy indeks (`ISOA_ISOW_technical.csv`, `ISOA_ISOW_table.csv`),
  - dodana nowa zakładka raportowa zaraz po `Podsumowanie` z dynamiczną nazwą `ISOA`/`ISOW`,
  - zakładka zawiera: metodologię, podstawę danych, wykres główny kołowy 0-100, tabelę, Top3/Bottom3,
  - podpisy na wykresie kołowym zależne od trybu: archetypy (`Archetypy`) lub wartości (`Wartości`).
- Synchronizacja lokalizacji generatora:
  - zmiany skopiowane także do `C:\Poznan_Archetypy_Analiza\analyze_poznan_archetypes.py`.
- Testy:
  - `python -m py_compile app.py jst_analysis.py JST_Archetypy_Analiza/analyze_poznan_archetypes.py` (OK),
  - `python -m py_compile C:\Poznan_Archetypy_Analiza\analyze_poznan_archetypes.py` (OK).

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

### Start Hotfix H-006 (2026-04-09, pozny wieczor)
- Zgloszenie usera: naglowki profili 0-100 w `🧭 Matching` maja byc w dopelniaczu:
  - `Profil archetypowy {osoby w dopelniaczu}`,
  - `Profil archetypowy mieszkańców {JST w dopelniaczu}`,
  bez dopisku o skali.
- Pierwszy krok wykonawczy:
  - podmienic zrodlo etykiet w `matching_view` na pola `*_gen` z sensownym fallbackiem i zmienic render naglowkow.

### Zrobione w Hotfix H-006 (naglowki profili 0-100 w dopelniaczu)
- `app.py` (`matching_view`):
  - dodano `person_name_gen` do `matching_result` (z `_person_genitive(person)`),
  - dodano `jst_name_gen` do `matching_result`:
    - najpierw `jst_full_gen` ze studium JST,
    - fallback: auto-odmiana `_make_jst_defaults(...)["jst_full_gen"]`,
    - ostateczny fallback: `jst_name_nom`,
  - podmieniono naglowki sekcji kol 0-100 na:
    - `Profil archetypowy {person_name_gen}`,
    - `Profil archetypowy mieszkańców {jst_name_gen}`,
  - usunieto dopisek `(siła archetypu, skala: 0-100)` z obu naglowkow.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Start Kroku 8 (2026-04-09, noc)
- Przechodzimy do ostatniego otwartego etapu: stabilnosc eksportu raportu (`HTML/ZIP`), osadzanie zasobow, fonty i UX pobierania.
- Pierwszy krok wykonawczy:
  - audyt pipeline:
    - `app.py` (podglad raportu, przyciski pobierania, komunikaty UX),
    - `jst_analysis.py` (inline assets i bundlowanie ZIP),
    - generator raportu (fonty i zaleznosci zasobow).

### Zrobione w Kroku 8 (stabilnosc eksportu HTML/ZIP + fonty + UX pobierania)
- `app.py` (`jst_analysis_view`):
  - standalone HTML jest teraz jawnie kontrolowany limitem:
    - nowy limit `JST_REPORT_STANDALONE_HTML_LIMIT_BYTES` (domyslnie `85_000_000`),
    - przycisk `📥 Pobierz raport HTML (pełny)` jest aktywny tylko, gdy jednoplikowy HTML jest bezpieczny rozmiarowo,
    - dla raportow zbyt ciezkich UI pokazuje jednoznaczny komunikat i kieruje do `ZIP`, bez mylacego pobierania niepelnego HTML.
  - oba przyciski pobierania raportu (`HTML` i `ZIP`) maja `on_click=\"ignore\"`, co eliminuje rerun po kliknieciu i efekt "szarego zawieszenia",
  - podglad online:
    - po wylaczeniu `Tryb lekki renderowania` aplikacja probuje osadzic zasoby on-demand,
    - jesli osadzenie jest mozliwe i miesci sie w limicie, renderuje pelna wersje,
    - jesli nie (za duzy raport lub blad osadzania), pokazuje jasny komunikat zamiast mylacego niepelnego widoku.
- `app.py`:
  - dodano helper `_fmt_bytes_compact(...)` do czytelnych komunikatow o rozmiarze raportu.
- `JST_Archetypy_Analiza/analyze_poznan_archetypes.py`:
  - dodano deterministyczny dobor fontu (`_candidate_font_files`, `_register_font`, `_pick_base_font`),
  - `set_global_fonts()` korzysta z fontow repo (priorytet) i dopiero potem systemowych, aby wyrownac wyglad wykresow miedzy srodowiskami.
- `assets/fonts/`:
  - dodano `segoeui.ttf` i `segoeuib.ttf` jako fonty referencyjne.
- Testy techniczne:
  - `python -m py_compile app.py jst_analysis.py JST_Archetypy_Analiza\\analyze_poznan_archetypes.py` (OK),
  - kontrolny pomiar dla runa Poznania:
    - `raw_bytes = 6_014_713`,
    - `inlined_bytes = 188_178_230` (potwierdza, dlaczego dla duzych raportow wymuszamy ZIP zamiast mylacego standalone HTML).

### Start Hotfix H-007 (2026-04-10, noc)
- Zgloszone problemy po wdrozeniu:
  1. Ucinanie dolnej etykiety archetypu na radarze `Porównanie profili archetypowych`.
  2. Zlewanie sie sekcji `Porównanie profili archetypowych` i `Profile archetypowe 0-100`.
  3. Slaba czytelnosc interpretacji oceny dopasowania (`Ocena: ...`) i malo wyrazny pasek skali.
  4. Bład callbacka przy pobieraniu (`TypeError: 'str' object is not callable`) po kliknieciu ZIP/HTML.
  5. Komunikat o ciezkim standalone HTML odbierany jak blad generowania.
  6. Nadal niespojna typografia wykresow raportu wzgledem wzorca.
- Pierwszy krok wykonawczy:
  - poprawic `app.py` (UI Matching + bezpieczny wrapper download), a nastepnie
    domknac font pipeline w `jst_analysis.py` i `JST_Archetypy_Analiza/analyze_poznan_archetypes.py`.

### Start Hotfix H-008 (2026-04-10, rano)
- Zgloszenie usera:
  1. W sekcji `Profile archetypowe 0-100` tytuly profili maja byc wycentrowane na srodku wykresow.
  2. `Oczekiwania mieszkańców (%)` maja byc liczone z pelnych wartosci A/B1/B2/D13
     (bez wag komponentow 40/20/25/15).
- Pierwszy krok wykonawczy:
  - zmapowac miejsca renderu tytulow 0-100 i obliczen profilu JST w `app.py`,
    potem podmienic formule oraz zsynchronizowac opis metodologii.

### Zrobione w Hotfix H-008 (centrowanie tytulow 0-100 + nowa formula Oczekiwan mieszkancow)
- `app.py`:
  - w `🧭 Matching > Podsumowanie > Profile archetypowe 0-100` wycentrowano tytuly nad wykresami:
    - `Profil archetypowy {osoba w dopelniaczu}`,
    - `Profil archetypowy mieszkańców {JST w dopelniaczu}`.
  - render samych obrazow 0-100 ustawiono kompatybilnie centrowo
    (`use_container_width` -> `use_column_width` -> `width`), aby tytuly i wykresy byly osiowo spojne.
  - `_calc_jst_target_profile(...)` liczy teraz wynik archetypu jako srednia z pelnych skladowych:
    - `A_pct`, `B1_pct`, `B2_pct`, `D13_pct`,
    - `score = (A_pct + B1_pct + B2_pct + D13_pct) / 4`.
  - zaktualizowano opisy metodyki i etykiety tabeli audytu skladnikow
    (pelne % dla A/B1/B2/D13 + `Średnia 4 komponentów`).
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Start Hotfix H-009 (2026-04-10, rano)
- Zgloszenie usera:
  1. Za duze fonty po centrowaniu tytulow profili 0-100 (regresja wizualna).
  2. Niejednoznaczny odbior wzoru `match = ...` (mylony z liczeniem `Oczekiwań mieszkańców (%)`).
  3. Rozjazd czasu commita w stopce wzgledem GitHub `main`.
- Pierwszy krok wykonawczy:
  - skorygowac typografie Matching i podpis metryki,
  - zmienic priorytet danych w `_app_build_signature()` na GitHub HEAD.

### Zrobione w Hotfix H-009 (korekta typografii + stopka commita)
- `app.py`:
  - sekcja `🧭 Matching`:
    - zmniejszono fonty naglowkow sekcji i tytulow kol 0-100 (koniec efektu "wielkich czcionek"),
    - utrzymano centrowanie tytulow nad wykresami 0-100,
    - dopisano jasny komunikat: wzor `match = ...` dotyczy tylko `Poziomu dopasowania`,
      nie liczenia `Oczekiwań mieszkańców (%)`.
  - `_app_build_signature()`:
    - priorytet: GitHub HEAD (`main`) -> lokalny git -> env/secrets/`.deployed_sha`,
    - fallback czasu dla konkretnego SHA przez GitHub API, gdy brak lokalnej daty.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Start Hotfix H-010 (2026-04-10, rano)
- Zgloszenie usera:
  1. Edytor `segment_hit_threshold_overrides` wywala bledy parsera i `StreamlitAPIException` po probie zapisu/resetu.
  2. Sekcje `Porównanie profili archetypowych` oraz `Profile archetypowe 0-100` nadal wizualnie "odstaja".
  3. `Oczekiwania mieszkańców (%)` sa odbierane jako zbyt plaskie i wymagaja mocniejszego docenienia sygnalu TOP1.
- Pierwszy krok wykonawczy:
  - naprawic parser + reset edytora progow, nastepnie uproscic styl sekcji Matching i podmienic formule `Oczekiwań mieszkańców`.

### Zrobione w Hotfix H-010 (progi segmentow + Matching + nowa formula oczekiwan)
- `app.py`:
  - parser progow `segment_hit_threshold_overrides`:
    - obsluguje JSON oraz format liniowy `segment: wartosc` / `segment = wartosc`,
    - toleruje smart quotes i typowe wklejki z przecinkami,
    - przy bledzie pokazuje konkretna, problematyczna linie.
  - reset/zapis progow:
    - przeniesiono na mechanizm `pending` + `st.rerun()` (bez modyfikacji aktywnego klucza widgetu),
    - usunieto zrodlo `StreamlitAPIException` z ekranu 2787.
  - `Oczekiwania mieszkańców (%)`:
    - nowa formula z premia TOP1:
      `score = (A_pct + B1_pct + 2*B2_pct + 2*D13_pct) / 6`,
    - opisy metodyki i etykiety tabeli audytu dopasowano do nowej formuly.
  - UI Matching:
    - sekcje `Porównanie...` i `Profile...` maja prostszy, mniej "kartowy" styl (separator dolny zamiast pelnego boxa).
  - stopka build:
    - cache metadanych GitHub skrocony do `60s`, aby szybciej pokazywac najnowszy commit po deployu.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-012 (ISOA/ISOW anchored + PPP + C:/D: + podglad)
- `app.py`:
  - ISOA/ISOW przeliczone bez min-max:
    - `P = 0.35*z(B1) + 0.65*z(B2)`,
    - `D = 0.70*z(N) + 0.30*z(MBAL)`,
    - `P_adj = 8*tanh(P/1.5)`,
    - `D_adj = 4*tanh(D/1.5)`,
    - `SEI_raw = A + P_adj + D_adj`,
    - `SEI_100 = clamp(SEI_raw, 0..100)`.
  - opisy metodologii i audyt skladnikow zaktualizowane do modelu zakotwiczonego w A.
  - porownanie i profile 0-100 sa dynamiczne dla `Archetypy/Wartości` (tytuly + etykiety osi).
  - limity podgladu raportu sa spinane z realnym `server.maxMessageSize` i nie przepuszczaja wymuszenia ponad twardy limit.
- `admin_dashboard.py`:
  - wykres kola 0-100 obsluguje `label_mode` (`arche` / `values`), wiec w Matching tryb `Wartości` ma podpisy wartosci.
- `jst_analysis.py`:
  - osadzanie assetow do podgladu inline kompresuje obrazy (i delikatnie skaluje duze grafiki), co znaczaco zmniejsza payload.
  - pomiar po zmianie: dla raportu Poznania `inlined_bytes` spadlo do ~34.7 MB (zamiast >200 MB).
- `JST_Archetypy_Analiza/analyze_poznan_archetypes.py`:
  - ISOA/ISOW w raporcie liczone modelem zakotwiczonym w A (bez min-max),
  - dodana legenda osi pod glownym wykresem ISOA/ISOW,
  - przywrocona osobna zakladka sekcji A jako `PPP`,
  - widoczne etykiety `IOA/IOW` podmienione na `PPP`,
  - podtytul raportu: `Data wygenerowania raportu: ...`,
  - zmniejszona czcionka glownego naglowka zakladki ISOA/ISOW.
- C:/D: synchronizacja i rebuild:
  - generator zsynchronizowany do `C:\Poznan_Archetypy_Analiza\analyze_poznan_archetypes.py`,
  - wygenerowane nowe raporty:
    - `D:\PythonProject\archetypy\archetypy-admin\JST_Archetypy_Analiza\WYNIKI\raport.html`,
    - `C:\Poznan_Archetypy_Analiza\WYNIKI\raport.html`,
  - oba raporty zawieraja taby `ISOA/ISOW` oraz `PPP` i date generacji.
- Test techniczny:
  - `python -m py_compile app.py jst_analysis.py admin_dashboard.py JST_Archetypy_Analiza\analyze_poznan_archetypes.py` (OK),
  - `python -m py_compile C:\Poznan_Archetypy_Analiza\analyze_poznan_archetypes.py` (OK).

### Zrobione w Hotfix H-013 (wariant B + styl tabel + fallback pobierania + domyslne progi)
- `app.py`:
  - dopracowano wyglad tabow `🧭 Matching` (mocniejszy active/hover, bardziej czytelna nawigacja),
  - sekcyjne naglowki `Porównanie...` i `Profile 0-100...` sa renderowane w `21px`,
  - radar porownawczy ma wieksze etykiety osi i legende linii na gorze (`linia ciągła` vs `linia przerywana`),
  - legenda TOP3 pod radarem ma docelowy uklad dwuliniowy (opis normalny + druga linia pogrubiona),
  - poprawiono komunikat brakow komponentow (neutralna korekta zamiast wzmianki o `z=0`),
  - gdy panel nie odnajdzie `raport.html` po wygenerowaniu, pokazuje fallback pobrania HTML z cache panelu.
- `JST_Archetypy_Analiza/analyze_poznan_archetypes.py`:
  - domknieto tabelaryczne mapowanie wariantu B:
    - `Korekta wariantu B` zamiast starych kolumn `Korekta priorytetu`/`Presja doświadczenia`,
  - tabela glowna ISOA/ISOW ma teraz czarne naglowki kolumn,
  - przywrocono styl tabeli glównej PPP (ikony, kolorowane naglowki, pogrubienie `% oczekujących`),
  - zmniejszono typografie bloku `Jak czytać wskaźnik`,
  - utrzymano kolorowane Top/Bottom 3 (strzalki + barwienie ikon/list) dla ISOA/ISOW i PPP.
- Progi segmentow:
  - `app.py` (`_SEGMENT_HIT_THRESHOLD_DEFAULTS`) zawiera teraz domyslnie:
    - `0 z 2 · #2: 4.0`,
    - `0 z 2 · #3: 4.0`,
    - `1 z 1 · #1: 3.0`,
    - `1 z 2 · #2: 3.0`,
    - plus dotychczasowe progi (`2 z 2 · #1`, `3 z 4 · #2`, `4 z 4 · #1`, `1 z 4 · #3/#4`).
  - to samo ustawiono w:
    - `D:\PythonProject\archetypy\archetypy-admin\JST_Archetypy_Analiza\settings.json`,
    - `C:\Poznan_Archetypy_Analiza\settings.json`.
- Synchronizacja C:/D:
  - finalny `analyze_poznan_archetypes.py` skopiowano z D: do C:.
- Rebuild i testy:
  - `python -m py_compile app.py jst_analysis.py admin_dashboard.py JST_Archetypy_Analiza\analyze_poznan_archetypes.py` (OK),
  - `python -m py_compile C:\Poznan_Archetypy_Analiza\analyze_poznan_archetypes.py` (OK),
  - `python JST_Archetypy_Analiza\analyze_poznan_archetypes.py` (OK, raport na D:),
  - `python C:\Poznan_Archetypy_Analiza\analyze_poznan_archetypes.py` (OK, raport na C:).

### Zrobione w Hotfix H-014 (Matching UI + PPP/ISOA final polish + MBAL control export)
- `app.py`:
  - `🧭 Matching`:
    - dopracowany wyglad tabow (wyraźne "button-like" zakładki, mocniejszy aktywny stan i hover),
    - pod `Najlepsze dopasowania / Największe luki` dodano nowe porownanie TOP3 polityk vs JST w nowoczesnych kartach obok siebie,
    - radar porownawczy:
      - legenda wizualna zastapiona estetycznymi pillami z probkami linii,
      - etykiety dynamiczne: `profil polityka ({osoba})`, `profil mieszkańców ({JST})`,
      - usunieto stary opis `Niebieska linia...`,
    - TOP3 pod radarem dostaly nowy wyglad (karty, wycentrowanie, czytelniejszy podział),
    - pod kołami 0-100 w trybie `Wartości` dodano centralna legende osi (`Zmiana/Ludzie/Porządek/Niezależność`),
    - `Demografia`: wartosci w kolumnie `% grupa dopasowana` maja `font-size: 13.5px`,
    - `Strategia komunikacji`: rozbudowana do 4 kart (os przekazu, luki, segment docelowy, plan testów 14 dni).
  - wariant B:
    - opis metodyki w Matching pokazuje precyzyjnie `delta_B2 = B2 - 8.3333333333`,
    - audyt komponentow pokazuje dodatkowo `Mneg` i `Mpos` obok `MBAL`.
- `JST_Archetypy_Analiza/analyze_poznan_archetypes.py`:
  - wariant B liczy neutral B2 jako `8.3333333333`,
  - dodano pomocniczy eksport kontroli MBAL:
    - `ISOA_ISOW_MBAL_control.csv` z kolumnami `Mneg`, `Mpos`, `MBAL`, `Kontrola MBAL`,
  - `PPP`:
    - `% oczekujących` pozostaje pogrubione, ale czarne (zielony zostal tylko naglowek kolumny),
    - naglowek `PPP 0-100` jest czarny,
    - w podsumowaniu dodano brakujace `⬇ Bottom 3 (PPP)` (dla archetypow i wartosci),
  - `ISOA/ISOW`:
    - wykres glowny zmniejszony o ok. 15% (`isoa-wheel-wrap`).
- Synchronizacja C:/D:
  - finalny `analyze_poznan_archetypes.py` skopiowany D -> C,
  - przebudowane raporty:
    - `D:\PythonProject\archetypy\archetypy-admin\JST_Archetypy_Analiza\WYNIKI\raport.html`,
    - `C:\Poznan_Archetypy_Analiza\WYNIKI\raport.html`,
  - oba katalogi maja `ISOA_ISOW_MBAL_control.csv`.
- Testy:
  - `python -m py_compile app.py jst_analysis.py admin_dashboard.py JST_Archetypy_Analiza\analyze_poznan_archetypes.py` (OK),
  - `python -m py_compile C:\Poznan_Archetypy_Analiza\analyze_poznan_archetypes.py` (OK),
  - `python JST_Archetypy_Analiza\analyze_poznan_archetypes.py` (OK),
  - `python C:\Poznan_Archetypy_Analiza\analyze_poznan_archetypes.py` (OK).

### Start Hotfix H-015 (2026-04-11, noc)
- Zgloszenie usera:
  1. Standalone/full HTML z `📊 Analiza badania mieszkańców` traci interaktywnosc JS (radio trybu etykiet, Segmenty, Skupienia, Filtry, suwaki), podczas gdy ZIP dziala poprawnie.
  2. Dodatkowe poprawki UI w `🧭 Matching` + drobne poprawki układu w raporcie (PPP/ISOA).
- Pierwszy krok wykonawczy:
  - naprawic pipeline inline assets w `jst_analysis.py`, bo to najbardziej prawdopodobne źródło regresji standalone HTML.

### Zrobione w Hotfix H-015 — Etap 1 (stabilizacja standalone + pierwsze poprawki UI)
- `jst_analysis.py`:
  - naprawiono inliner `inline_local_assets(...)`:
    - regex `src/href` zachowuje oryginalny typ cudzyslowu (`'` lub `"`),
    - eliminacja uszkadzania duzych blokow JS/JSON podczas podmiany na data URI.
  - weryfikacja syntaktyczna:
    - przed poprawka: `node --check` dla skryptu #3 z inlined HTML zwracal blad skladni,
    - po poprawce: wszystkie 3 skrypty przechodza `node --check` poprawnie.
- `app.py` (`🧭 Matching`) — etap dopieszczen UI:
  - zmniejszono globalny gorny margines kontenera (`padding-top:30px`) dla mniejszej pustej przestrzeni na gorze,
  - karta "dla kogo jest matching" przebudowana na wyrazny box 2-kolumnowy (personalne vs mieszkancow),
  - taby Matching przestylizowane na bardziej neutralny (szaro-niebieski) kontener z ostrymi dolnymi rogami,
  - TOP3 polityk/JST:
    - dodane ikonki przy nazwach archetypow/wartosci,
    - rowna geometria rzedow (stala szerokosc etykiety roli, bez "wciecia" dla `Wspierający`),
    - kolory nazw zgodne z rola (główny/wspierający/poboczny),
  - radar porownawczy:
    - przywrocona klikalna legenda Plotly dla dwoch linii profili (`itemclick=toggle`),
    - zmniejszone odstepy pionowe (legenda i dolny blok TOP3 blizej wykresu),
  - profile 0-100: render obu obrazow ustawiony na stala szerokosc (`width=560`) dla 1:1 skali po obu stronach,
  - `Demografia > 👥 PROFIL DEMOGRAFICZNY`: dodano offset tabeli (`padding-top:15px`, `padding-left:25px`).
- `JST_Archetypy_Analiza/analyze_poznan_archetypes.py` (+ sync C:):
  - `PPP / Podsumowanie`: siatka podsumowania ustawiona na 4 kolumny (`Top3/Bottom3 oczekiwane` + `Top3/Bottom3 PPP` w jednej linii na desktopie),
  - `ISOA/ISOW`: `Wykres główny` wyrównany do lewej (`.isoa-wheel-wrap { margin:0; }`).
- Synchronizacja i rebuild:
  - `analyze_poznan_archetypes.py` skopiowany D -> C,
  - przebudowano raporty na obu lokalizacjach:
    - `D:\PythonProject\archetypy\archetypy-admin\JST_Archetypy_Analiza\WYNIKI\raport.html`,
    - `C:\Poznan_Archetypy_Analiza\WYNIKI\raport.html`.
- Smoke-check:
  - `python -m py_compile app.py jst_analysis.py JST_Archetypy_Analiza\analyze_poznan_archetypes.py C:\Poznan_Archetypy_Analiza\analyze_poznan_archetypes.py` (OK).

### Start Hotfix H-015 — Etap 2 (po nowych screenach usera)
- User dopisal nowe uwagi i poprosil o wpisanie ich do planu zamiast wdrazania wszystkiego naraz.
- Zakres dodany do `PLANS.md` jako `H-015 / Etap 2 [IN_PROGRESS]`, z podzialem na 3 kroki:
  1. TOP3/tabs/radar spacing (wizual i czytelnosc),
  2. korekta metryki `Poziom dopasowania` (kara za luki kluczowych archetypow),
  3. naprawa offsetu `👥 PROFIL DEMOGRAFICZNY` i separacji sekcji 0-100.

### Zrobione w Hotfix H-015 — Etap 2 (Krok A + C)
- `app.py`:
  - TOP3 polityk/JST:
    - usunieto niebieski gradient z kart (`background:#fff`),
    - podmieniono ikonki na realne ikony archetypow (PNG z `ikony/*.png`, osadzane jako data URI),
    - zachowano rowna geometrie wierszy i stale szerokosci etykiet ról.
  - Taby `🧭 Matching`:
    - mocniej podkreslony aktywny tab (niebieski, bialy tekst, wyzszy kontrast),
    - mocniejszy hover (wyrazniejsza obwodka + cień).
  - Radar `Porównanie profili ...`:
    - marker JST zmieniony na kwadrat (dla linii i punktow TOP3),
    - przesunieto legende i marginesy, aby nie nachodzila na wykres,
    - dolna legenda TOP3 bez przecinkow i z wiekszym spacingiem miedzy elementami.
  - Sekcja `Profile archetypowe 0-100 ...`:
    - dodany wiekszy odstep od bloku TOP3 pod radarem (`match-profile-header`).
  - `Demografia / 👥 PROFIL DEMOGRAFICZNY`:
    - offset przeniesiony na caly box (`.match-demo-box.match-demo-profile-box`),
    - usunieto przesuwanie samej tabeli wewnetrznej.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Dodane do planu po nowych screenach (H-015 / Etap 3)
- Zgloszone i dopisane do `PLANS.md`:
  1. `Segmenty`: brak renderu `Mapa przewag segmentów` mimo dzialajacego suwaka.
  2. `Skupienia (k-średnich)`: brak renderu `Mapa skupień (projekcja dla K=...)` mimo zmiany suwaka modelu.
  3. `Filtry`: brak ikonek archetypow/wartosci w wykresach porownawczych.
- Etap 3 jest zaplanowany jako kolejny pakiet po domknieciu Etapu 2 / Krok B.
- Na tym etapie nie wprowadzano jeszcze zmian kodu dla tych trzech punktow (tylko dopisanie do listy zadan).

### Dopisane do Etapu 2 po kolejnych screenach (dogrywka A2)
- Dodano do `PLANS.md` dodatkowe poprawki UI:
  1. aktywna zakladka Matching ma pozostac czytelna po hover,
  2. korekta polozenia legend i odstepow w `Porównanie profili archetypowych`,
  3. dolna legenda TOP3: tytuly bez bold oraz kwadraty dla `TOP3 mieszkańców`.
- Te poprawki sa oznaczone jako `Dogrywka A2` i beda robione po aktualnym `Kroku B`.

### Zrobione w Hotfix H-015 — Etap 2 (Krok B)
- `app.py`:
  - przebudowano metryke `Poziom dopasowania`, aby mocniej karala luki na archetypach kluczowych:
    - wyznaczana jest pula kluczowa = unia TOP3 polityka i TOP3 mieszkancow,
    - liczony `KEY_MAE` (srednia luki w puli kluczowej) i `KEY_MAX` (najwieksza luka w puli),
    - finalny wynik:
      - `base = 0.40*(100-MAE) + 0.20*(100-RMSE) + 0.20*(100-TOP3_MAE) + 0.20*(100-KEY_MAE)`,
      - `kara_kluczowa = 0.22*KEY_MAE + 0.10*max(0, KEY_MAX - 15)`,
      - `match = clamp(0,100, base - kara_kluczowa)`.
  - zaktualizowano opis metodyki i sekcje audytu:
    - nowa metryka `Luki kluczowe (TOP3 P+JST)`,
    - widoczne `KEY_MAE`, `KEY_MAX`, `kara kluczowa`,
    - lista archetypow kluczowych.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Dopisane po ostatniej wiadomosci usera (dogrywka A2 + legenda)
- Rozszerzono `Dogrywke A2` o dodatkowy punkt dla gornej legendy profili:
  - zaokraglenie rogów obramowania,
  - wiekszy odstep miedzy profilami,
  - wieksze marginesy boczne i pionowe.

### Zrobione w Hotfix H-015 — Etap 2 (Dogrywka A2)
- `app.py`:
  - tabs Matching: poprawiono czytelnosc aktywnej zakladki po hover (`selected:hover` utrzymuje wysoki kontrast),
  - `Porównanie profili archetypowych`:
    - gorna legenda przesunieta wyzej i odsunieta od wykresu,
    - zwiekszono odstep miedzy profilami w legendzie i padding legendy,
    - wykres z legendami przesuniety blizej tytulu sekcji,
    - zwiekszony dolny margines wykresu (bez ucinania etykiety `Władca`),
  - dolna legenda TOP3:
    - tytuly `TOP3 polityka`/`TOP3 mieszkańców` bez pogrubienia,
    - znaczniki dla `TOP3 mieszkańców` jako kwadraty.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Dopisane do planu po ostatniej wiadomosci usera (Dogrywka A3)
- Dodano nowy pakiet `Dogrywka A3`:
  1. nowa sekcja `Główne zalety` / `Główne problemy` w `🧭 Matching / Podsumowanie`,
  2. analiza ewentualnej jawnej premii za bliskosc kluczowych archetypow.
- Uwaga metodyczna zapisana do realizacji:
  - obecna metryka ma efekt "premii pośredniej" (niższy `KEY_MAE` i mniejsza kara),
    ale nie ma oddzielnej, jawnej premii dodatniej.

### Zrobione w Hotfix H-015 — Etap 3 (mapy Segmenty/Skupienia + ikony Filtry)
- `JST_Archetypy_Analiza/analyze_poznan_archetypes.py`:
  - `Segmenty`: dynamiczna podmiana map po suwaku korzysta z jawnych map per-K (`map_arche_by_k`, `map_values_by_k`) przekazywanych w payloadzie packa.
  - `Filtry`: dodano payload `FILTER_ICONS`; `iconSrc(...)` bierze ikonę z mapy i ma fallback do `icons/<slug>.png`.
  - `seg_pack_ultra` (oraz `seg_packs_render["ultra_premium"]`) jest wzbogacany o mapy plikow segmentowych per-K.
- `jst_analysis.py`:
  - `inline_local_assets(...)` inlinuje juz nie tylko `src/href`, ale tez lokalne sciezki assetow zapisane jako quoted-string w JS/JSON.
  - Efekt: dynamicznie przełączane mapy (`Segmenty`, `Skupienia`) i ikony (`Filtry`) działają po osadzaniu standalone/podglądu online.
- Weryfikacja:
  - `python -m py_compile jst_analysis.py JST_Archetypy_Analiza\\analyze_poznan_archetypes.py` (OK),
  - `python -m py_compile C:\\Poznan_Archetypy_Analiza\\analyze_poznan_archetypes.py` (OK),
  - kontrola inlinera: w wygenerowanym HTML inline nie pozostają literalne ścieżki
    `SEGMENTY_META_MAPA_STALA_K*.png`, `SKUPIENIA_MAPA_PCA_K*.png`, `icons/*.png`.
- Synchronizacja C/D:
  - skopiowano `analyze_poznan_archetypes.py` z D: do C:,
  - przebudowano raporty na obu lokalizacjach (`D:\\...\\WYNIKI\\raport.html`, `C:\\Poznan_Archetypy_Analiza\\WYNIKI\\raport.html`).

### Dopisane po ostatniej wiadomosci usera (Dogrywka A4 + decyzja o premii)
- Do `PLANS.md` dopisano `Dogrywka A4`:
  1. dopracowanie marginesow i legend sekcji `Porównanie profili archetypowych`,
  2. pogrubianie etykiet osi dla archetypow/wartosci z TOP3 na radarze,
  3. ponowna kalibracja komunikatu i pasm `Poziom dopasowania` dla przypadkow z duzymi lukami kluczowymi.
- Potwierdzono decyzje metodyczna usera:
  - rezygnujemy z jawnej premii za dopasowanie (brak dodatniego bonusu w score).

### Zrobione w Hotfix H-015 — Etap 2 (Dogrywka A3)
- `app.py` (`🧭 Matching / Podsumowanie`):
  - pod kartami `TOP3 ... dla ...` dodano nowy blok:
    - `Główne zalety`,
    - `Główne problemy`,
    liczony dynamicznie z faktycznych danych porownania (`TOP3`, `|Δ|`, `KEY_MAE`, `KEY_MAX`, najlepsza zgodność).
  - sekcja ma neutralny styl (`białe` karty, bez niebieskiego gradientu), ze zwięzłymi punktami interpretacyjnymi.
  - opisy metryki (`match_formula` + expander `Jak liczony jest poziom dopasowania?`) doprecyzowano:
    - brak jawnej premii dodatniej,
    - lepsza zgodność poprawia wynik wyłącznie przez mniejszą karę.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-015 — Etap 2 (Dogrywka A4)
- `app.py`:
  - `Porównanie profili archetypowych`:
    - zmniejszony odstęp pod tytułem sekcji,
    - dopracowana górna legenda (większy odstęp między profilami, lepsze pozycjonowanie),
    - dolna legenda TOP3 podciągnięta wyżej bez kolizji z wykresem,
    - zmniejszone pogrubienie etykiet `główny / wspierający / poboczny`.
  - radar:
    - etykiety osi dla pozycji z TOP3 (unia polityk + mieszkańcy) są wyróżnione pogrubieniem.
  - `Poziom dopasowania`:
    - kalibracja opisu pasm: duże luki kluczowe (`KEY_MAX` / `KEY_MAE`) obniżają werbalną ocenę,
      aby nie komunikować zbyt optymistycznie przy strategicznych rozjazdach.
  - utrzymano decyzję: brak jawnej premii dodatniej (model kar).
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-015 — Etap 2 (Dogrywka A5)
- `app.py`:
  - `Porównanie profili archetypowych`:
    - górna legenda podniesiona wyżej (bliżej tytułu, dalej od radaru),
    - legenda zawężona i czytelniejsza (mniejszy `entrywidth`, mniejszy font, większy oddech tekstu),
    - dolna legenda TOP3 przybliżona do wykresu.
  - globalny układ:
    - zmniejszono wolne miejsce na górze strony (`.block-container` z `30px` na `18px`).
  - `Poziom dopasowania`:
    - zwiększono karę kluczową:
      - było: `0.22*KEY_MAE + 0.10*max(0, KEY_MAX - 15)`,
      - jest: `0.30*KEY_MAE + 0.14*max(0, KEY_MAX - 12)`.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-015 — Etap 2 (Dogrywka A6)
- `app.py`:
  - radar `Porównanie profili ...`:
    - górna legenda ustawiona trochę niżej,
    - czcionka legendy górnej zwiększona (`+1.5px`),
    - legenda zawężona (`entrywidth`) i z większym lewym oddechem wpisów,
    - dolna legenda TOP3 podciągnięta wyżej.
  - globalny layout:
    - `padding-top` głównego kontenera ustawiony na `3px`.
  - metryka `Poziom dopasowania`:
    - kara kluczowa zaostrzona:
      - było: `0.30*KEY_MAE + 0.14*max(0, KEY_MAX - 12)`,
      - jest: `0.45*KEY_MAE + 0.22*max(0, KEY_MAX - 9)`.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-015 — Etap 2 (Dogrywka A7)
- `app.py`:
  - `Poziom dopasowania` ma teraz bardziej zróżnicowaną skalę opisową (7 poziomów):
    - `0–29` marginalne,
    - `30–49` słabe,
    - `50–59` umiarkowane,
    - `60–69` znaczące,
    - `70–79` wysokie,
    - `80–89` bardzo wysokie,
    - `90–100` ekstremalnie wysokie.
  - opisy jakościowe zostały dopasowane do nowych pasm,
  - guard kluczowych luk (`KEY_MAE`/`KEY_MAX`) nadal może obniżyć opisowe pasmo przy dużych rozjazdach,
  - dopisano te progi także do opisu w expanderze metodologicznym.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-015 — Etap 2 (Dogrywka A8)
- `app.py`:
  - finalny podział progów `Poziomu dopasowania` ustawiony na:
    - `0–29` marginalne,
    - `30–39` bardzo niskie,
    - `40–49` niskie,
    - `50–59` umiarkowane,
    - `60–69` znaczące,
    - `70–79` wysokie,
    - `80–89` bardzo wysokie,
    - `90–100` ekstremalnie wysokie.
  - opis progów w expanderze metodologicznym zaktualizowany do nowego podziału.
  - badge kolorystyczny ocen dostrojony do nowych przedziałów.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-016 (status badań + reset stanu Matching)
- `app.py`:
  - `🧭 Matching / Wybierz badania`:
    - selectboxy mają callback unieważniający (`matching_result` + `matching_result_notice`),
    - po zmianie badania znika zielony komunikat o policzonym dopasowaniu i stary wynik nie jest już sugerowany jako aktualny.
  - `✏️ Edytuj dane badania` i `✏️ Edytuj dane badania mieszkańców`:
    - dodano sekcję `Status badania` z tabelą:
      - status,
      - data uruchomienia,
      - data ostatniej zmiany statusu,
    - dodano akcje:
      - `⏸️ Zawieś`,
      - `▶️ Odwieś`,
      - `🔒 Zamknij badanie` (z potwierdzeniem, nieodwracalne),
      - `🗑️ Usuń badanie` (z dodatkowym potwierdzeniem).
- `db_utils.py`:
  - dodano obsługę statusu badań personalnych (`normalize_study_status`, `set_study_status`),
  - `insert_study` ustawia domyślnie `study_status=active` + znaczniki czasu,
  - `soft_delete_study` ustawia `study_status=deleted`.
- `db_jst_utils.py`:
  - `ensure_jst_schema` dodaje/uzupełnia kolumny statusów:
    - `study_status`,
    - `status_changed_at`,
    - `started_at`,
    dla `jst_studies` i `studies`,
  - `get_jst_study_public` zwraca status badania,
  - `add_jst_response_by_slug` odrzuca zapis przy statusie innym niż `active` (`study_inactive`),
  - dodano `set_jst_study_status`,
  - soft-delete JST ustawia `study_status=deleted`.
- `archetypy-ankieta`:
  - `src/lib/studies.ts` i `src/lib/jstStudies.ts` rozszerzone o pola statusowe,
  - `src/App.tsx`:
    - dla `suspended` pokazuje blokadę `Badanie jest nieaktywne`,
    - dla `closed` pokazuje blokadę `Badanie zakończone`,
    - dla `deleted` blokuje wejście i pokazuje komunikat niedostępności,
  - `src/JstSurvey.tsx`:
    - jeśli RPC zwróci `study_inactive`, wyświetlany jest dedykowany komunikat statusowy.
- Testy:
  - `python -m py_compile app.py db_utils.py db_jst_utils.py` (OK),
  - `npm run build` w `archetypy-ankieta` (OK).

### Zrobione w Hotfix H-017 (kalibracja dopasowania + nowe moduły personalne)
- `Poziom dopasowania` (`app.py`):
  - złagodzono skokowość kary kluczowej:
    - było: `0.45*KEY_MAE + 0.22*max(0, KEY_MAX - 9)`,
    - jest: `0.42*KEY_MAE + 0.16*max(0, KEY_MAX - 12)`,
  - utrzymano 8-stopniową skalę progów (`0–29`, `30–39`, ..., `90–100`),
  - usunięto wymuszone zbijanie etykiety pasma przez guard; duże luki kluczowe są teraz dopisywane jako ostrzeżenie jakościowe,
  - dodano dodatkowy KPI: `Maks. luka kluczowa`.
- `Matching` (`app.py`):
  - dodano dodatkową walidację pary badań; jeśli aktualny wybór różni się od policzonego, wynik i zielony komunikat są czyszczone.
- `Badania personalne - panel` (`app.py`):
  - dodano dwa kafelki:
    - `⚙️ Ustawienia ankiety`,
    - `🔗 Połącz badania`,
  - dodano nowe widoki:
    - `personal_settings_view()` (status/link/liczba odpowiedzi dla wybranego badania),
    - `personal_merge_view()` (łączenie wyników wielu badań do jednego badania głównego).
- `Połącz badania`:
  - wybór badania głównego,
  - dynamiczne dokładanie wielu badań źródłowych (`➕ Dodaj badanie`),
  - wykonanie operacji przyciskiem `Dodaj`,
  - kopiowanie odpowiedzi bez usuwania ich z badań źródłowych.
- Warstwa danych (`db_utils.py`):
  - dodano `fetch_personal_response_count(...)`,
  - dodano `merge_personal_study_responses(...)` (batch copy z `responses`),
  - dodano normalizację `answers` przy kopiowaniu.
- Test techniczny:
  - `python -m py_compile app.py db_utils.py` (OK).

### Zrobione w Hotfix H-018 (ustawienia JST + przeniesienie statusu + RMSE label + TOP2/TOP3 kara)
- `app.py`:
  - `Badania mieszkańców - panel`:
    - dodano kafelek `⚙️ Ustawienia ankiety` i routing do nowego widoku `jst_settings_view()`,
    - w `jst_settings_view()` dodano:
      - tabelę statusu/linku/liczby odpowiedzi,
      - pełny panel akcji statusu (`Zawieś`, `Odwieś`, `Zamknij badanie`, `Usuń badanie`).
  - `Status badania` przeniesiono z edycji do ustawień:
    - usunięto panel statusu z `✏️ Edytuj dane badania` i `✏️ Edytuj dane badania mieszkańców`,
    - `personal_settings_view()` rozszerzono o pełny panel statusu (akcje + potwierdzenia).
  - Matching:
    - etykieta metryki skrócona do `RMSE (kara odchyleń)` (bez ucinania),
    - reguła puli kluczowej do kary:
      - standardowo TOP3,
      - jeśli 3. archetyp ma `>70`, 3. pozycja nie wchodzi do puli kar (liczenie dla TOP2).
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-019 (TOP2/TOP3 próg i UI + ankieta)
- `app.py` (`🧭 Matching`):
  - naprawiono próg klasyfikacji 3. archetypu:
    - teraz 3. pozycja jest liczona do puli kluczowej tylko gdy ma `>=70`,
    - przy `<70` profil traktowany jest jako TOP2 (bez pozycji pobocznej),
  - reguła TOP2/TOP3 jest spójna w:
    - karze kluczowej (`KEY_MAE`, `KEY_MAX`),
    - kartach `TOP{N} ...`,
    - legendach i markerach radaru (`TOP{N} polityka/mieszkańców`),
    - opisie metodologicznym (`<70 -> TOP2`),
  - dopracowano teksty pomocnicze (`Wspólne priorytety ...`) pod dynamiczny TOP2/TOP3.
- `archetypy-ankieta/src/JstSurvey.tsx`:
  - podmieniono treść odpowiedzi A17:
    - `wyrazistość i brak kompromisów` -> `wyrazistość i bezkompromisowość`.
- Testy:
  - `python -m py_compile app.py` (OK),
  - `npm run build` w `archetypy-ankieta` (OK).

### Zrobione w Hotfix H-020 (runtime fix `person_top_colors`)
- `app.py`:
  - naprawiono błąd `UnboundLocalError: cannot access local variable 'person_top_colors'`,
  - przeniesiono deklaracje palet (`person_top_colors`, `jst_top_colors`) nad miejsce, gdzie budowana jest legenda ról (`_role_legend_html`),
  - usunięto późniejszy duplikat deklaracji.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-021 (runtime fix `IndexError` dla TOP2/TOP3)
- `app.py` (`matching_view`, helper `_marker_series`):
  - usunięto bezwarunkowe indeksowanie `top3[0]`, `top3[1]`, `top3[2]` w literałe słownika,
  - mapa markerów jest budowana bezpiecznie krokowo:
    - `if len(top3) > 0` -> kolor `main`,
    - `if len(top3) > 1` -> kolor `aux`,
    - `if len(top3) > 2` -> kolor `supp`,
  - dzięki temu przypadki TOP2 nie powodują już `IndexError: list index out of range`.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-022 (unikalne kolory pastylek pasm dopasowania)
- `app.py` (`🧭 Matching`, karta `Poziom dopasowania`):
  - rozdzielono kolory pasm:
    - `70–79` (`Wysokie`) -> `#6d28d9` / `#f5f3ff`,
    - `60–69` (`Znaczące`) -> `#1d4ed8` / `#eff6ff`,
  - utrzymano zasadę unikalnych barw i dodatkowo rozdzielono odcień pasma `30–39` (`#be123c`).
- Efekt:
  - pastylki `Znaczące` i `Wysokie` nie wyglądają już identycznie.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-023 (mocniejsza kara za rozjazdy kluczowe)
- `app.py` (`🧭 Matching`, obliczanie `Poziom dopasowania`):
  - zwiększono siłę kary kluczowej:
    - było: `0.42*KEY_MAE + 0.16*max(0, KEY_MAX - 12)`,
    - jest: `0.56*KEY_MAE + 0.26*max(0, KEY_MAX - 10)`.
  - dodano kary strategiczne:
    - `shared_priority_penalty`:
      - `5.5` przy braku wspólnych pozycji TOP,
      - `2.0` gdy wspólna jest tylko 1 pozycja TOP,
    - `main_priority_mismatch_penalty = 2.5` przy różnym TOP1.
  - finalna kara:
    - `key_penalty = base_key_penalty + shared_priority_penalty + main_priority_mismatch_penalty`.
- `app.py` (metodyka w UI):
  - wzór i opis w expanderze zaktualizowane o nowe składniki kar.
- Efekt:
  - przypadki z dużymi lukami kluczowymi i brakiem wspólnych priorytetów spadają wyraźniej z poziomu „przyzwoitego” do niższych pasm.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-024 (TOP2/TOP3 vs luki/dopasowania w sekcji zalet/problemów)
- `app.py` (`🧭 Matching`, `Podsumowanie`, blok `Główne zalety / Główne problemy`):
  - dodano dynamiczne wykrywanie przecięć:
    - `priority_in_best`: archetypy/wartości z puli priorytetowej (`TOP2/TOP3`) obecne w `Najlepsze dopasowania`,
    - `priority_in_gaps`: archetypy/wartości z puli priorytetowej (`TOP2/TOP3`) obecne w `Największe luki`,
  - dodano nowe automatyczne linie:
    - do `Główne zalety`: „Priorytetowe pozycje są też wśród najlepszych dopasowań: ...”,
    - do `Główne problemy`: „Priorytetowe pozycje są też wśród największych luk: ...”,
  - każda pozycja pokazuje również `|Δ|` w pp.
- Efekt:
  - przypadki takie jak `Władca/Bohater` z TOP polityka jednocześnie w największych lukach są teraz jawnie odnotowane.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-025 (spójność przecięć TOP z chipami + priorytet widoczności)
- `app.py` (`🧭 Matching`, `Podsumowanie`):
  - przecięcia priorytetów TOP są liczone już nie z lokalnie sortowanych list pomocniczych, tylko bezpośrednio z:
    - `result["strengths"]` (`Najlepsze dopasowania`),
    - `result["gaps"]` (`Największe luki`),
    czyli dokładnie z tych samych danych, które user widzi w chipach.
  - wpisy o przecięciach TOP są dodawane na początek list:
    - `advantages.insert(0, ...)`,
    - `problems.insert(0, ...)`,
    dzięki czemu nie wypadają przez limit renderu `[:4]`.
- Efekt:
  - przypadki jak na screenie (`Władca`, `Bohater` z TOP i jednocześnie w największych lukach) są teraz jawnie widoczne w `Główne problemy`.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### BLOKERY / RYZYKA
- Brak blockerow technicznych.
- Ryzyko wdrozeniowe:
  - nowa funkcja RPC `get_jst_token_meta` musi zostac zastosowana w bazie (przez uruchomienie `ensure_jst_schema()` po deployu `archetypy-admin`).
  - do potwierdzenia na danych produkcyjnych: manualny E2E scenariusz resend SMS + ponowne wejscie tym samym tokenem.
  - do potwierdzenia na danych produkcyjnych: czy wszystkie badania JST maja uzupelnione cele poststratyfikacyjne (jesli nie, fallback jest surowy i komunikowany notka).

### Nastepny konkretny krok wykonawczy
- Szybki smoke-test UI na środowisku użytkownika:
  - potwierdzić na parze `Hetman` że błąd runtime zniknął i widok `Podsumowanie` renderuje się do końca,
  - potwierdzić na parze `Hetman` że przy 3. pozycji `<70` widok pokazuje `TOP2` i nie liczy tej pozycji do `Maks. luki kluczowej`,
  - potwierdzić, że `Status badania` jest dostępny tylko w `⚙️ Ustawienia ankiety` (personalne + mieszkańców),
  - sprawdzić, że etykieta `RMSE (kara odchyleń)` nie ucina się dla różnych szerokości ekranu.
