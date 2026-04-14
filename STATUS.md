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

### Zrobione w Hotfix H-098 (2026-04-14, wieczór)
- `admin_dashboard.py`:
  - wydzielono osobny widok `Profile demograficzne archetypu` (podstrona w tym samym oknie) z:
    - filtrem wielocechowym AND,
    - liczebnością podgrupy i progiem stabilności,
    - kartami `📌 STATYSTYCZNY PROFIL DEMOGRAFICZNY`,
    - tabelą `👥 PROFIL DEMOGRAFICZNY` (`% podgrupa`, `% cała próba`, `Różnica (w pp.)`),
    - radarem 0-20 (`cała próba` vs `podgrupa filtrowana`).
  - dodano obsługę nawigacji podstrony przez `st.session_state[f"personal_demo_page_{study_id}"]`
    oraz przycisk `← Cofnij`.
  - usunięto z głównego raportu inline-expander `👥 Profile demograficzne (filtr wielocechowy + radar)`.
  - usunięto poziomy scrollbar pod tabelą podsumowania archetypów na desktopie
    (`.ap-table-wrap { overflow-x: hidden; }`).
- `app.py` (`results_view`):
  - dodano przycisk `👥 Raport demograficzny` dla wybranej osoby, który otwiera dedykowaną podstronę demografii.
- Testy techniczne:
  - `python -m py_compile app.py admin_dashboard.py` (OK).

### Zrobione w Hotfix H-099 (2026-04-14, metryczka: predef + randomizacja + otwarte)
- `archetypy-admin/metryczka_config.py`:
  - rozszerzono model pytań metryczki o:
    - `randomize_options`,
    - `randomize_exclude_last`,
  - rozszerzono model odpowiedzi o:
    - `is_open`,
  - normalizacja rdzenia i custom pytań obsługuje nowe pola przy zachowaniu kompatybilności.
- `archetypy-admin/db_jst_utils.py`:
  - zapisane szablony pytań (`metryczka_question_templates`) przechowują i zwracają:
    - ustawienia randomizacji,
    - flagi `is_open` dla odpowiedzi.
- `archetypy-admin/app.py`:
  - edytor metryczki (`_render_metryczka_editor`) ma nowy górny przycisk:
    - `📚 Predefiniowane metryczki`,
  - panel predefiniowanych pytań pozwala:
    - edytować treść, kodowanie, randomizację,
    - oznaczać odpowiedzi jako `Otwarta`,
    - zapisać zmiany i/lub wstawić pytanie do bieżącej metryczki,
  - w tabeli odpowiedzi dodano kolumnę checkbox `Otwarta`,
  - w pytaniu dodano checkboxy:
    - `Losowa kolejność odpowiedzi`,
    - `Nie losuj ostatniej odpowiedzi`,
  - parser „Wklej pytanie i odpowiedzi” zachowuje także flagi `Otwarta` (gdy to możliwe).
- `archetypy-ankieta/src/lib/metryczka.ts`:
  - typy i normalizacja konfiguracji rozszerzone o nowe pola (`randomize_*`, `is_open`),
  - dodano helper `isOpenOptionSelected(...)`.
- `archetypy-ankieta/src/Questionnaire.tsx` (personal):
  - losowanie odpowiedzi metryczki per pytanie wg konfiguracji,
  - obsługa odpowiedzi otwartej dla dowolnego pytania metryczkowego (pole tekstowe wymagane),
  - zapis doprecyzowań do payloadu jako `M_*_OTHER` (+ `M_ZAWOD_OTHER` dla zgodności).
- `archetypy-ankieta/src/JstSurvey.tsx` (JST):
  - analogiczna obsługa randomizacji i odpowiedzi otwartych,
  - wymagane doprecyzowanie tekstowe dla zaznaczonej opcji otwartej,
  - zapis `M_*_OTHER` (+ zgodność `M_ZAWOD_OTHER`).
- Testy techniczne:
  - `python -m py_compile app.py db_jst_utils.py metryczka_config.py` (OK),
  - `npm run build` w `archetypy-ankieta` (OK).
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

### Zrobione w Hotfix H-026 (normalizacja nazw przy przecięciach TOP)
- `app.py` (`🧭 Matching`, sekcja zalet/problemów):
  - dodano normalizację porównań nazw (`_canon_name = slugify(...).lower()`),
  - przecięcia TOP vs chipy (`priority_in_best` / `priority_in_gaps`) liczone są po znormalizowanych kluczach,
    a nie po surowym porównaniu stringów 1:1.
- Efekt:
  - wpis o priorytetowych pozycjach w największych lukach nie ginie przez różnice zapisu nazw.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-027 (usunięcie restrykcyjnego filtra surowych nazw)
- `app.py` (`🧭 Matching`, sekcja zalet/problemów):
  - usunięto zbyt restrykcyjny filtr `name in diff_by_entity` przy zaciąganiu nazw z `result['strengths']` / `result['gaps']`,
  - dodano `_safe_src_names(...)` (pobieranie nazw bez exact-match po surowym stringu),
  - przecięcia TOP vs chipy finalnie liczone po znormalizowanych kluczach (`slugify(...).lower()`).
- Efekt:
  - przypadki `TOP` obecne jednocześnie w `Największe luki` nie znikają już z `Główne problemy` przez różnice formatu nazwy.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-028 (wspólna legenda pod `Profile wartości 0-100`)
- `app.py` (`🧭 Matching`, `Podsumowanie`, sekcja dwóch wykresów 0-100):
  - dodano jeden wspólny, wyśrodkowany blok legendy pod oboma wykresami (bez duplikacji per-wykres),
  - legenda w trybie `Wartości` pokazuje kategorie:
    - `Zmiana`,
    - `Ludzie`,
    - `Porządek`,
    - `Niezależność`,
    w układzie zbliżonym do referencji (ramka + padding + wyśrodkowanie).
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-029 (przecięcia TOP liczone z tych samych danych co chipy)
- `app.py` (`🧭 Matching`, sekcja `Główne zalety / Główne problemy`):
  - logikę przecięć TOP przepięto na `strengths_rows/gaps_rows` (czyli dokładnie to samo źródło, które renderuje chipy),
  - `_safe_src_names(...)` obsługuje zarówno rekordy dict, jak i stringi,
  - dodano fallback, jeśli lista źródłowa po parsingu jest pusta,
  - normalizacja nazw dla trybu `Wartości` mapuje etykietę wartości na archetyp przed porównaniem.
- Efekt:
  - wpisy typu `Priorytetowe pozycje ... wśród największych luk` nie znikają już przy faktycznym przecięciu widocznym na ekranie.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-030 (`archetypy-ankieta` — realne błędy TS ze screenów)
- `archetypy-ankieta/src/App.tsx`:
  - usunięto nieużywany stan `personInstr` i setter.
- `archetypy-ankieta/src/Questionnaire.tsx`:
  - usunięto nieużywane stany `fullAcc`, `fullIns`, `fullLoc` i odpowiadające settery.
- `archetypy-ankieta/src/LikertRow.tsx`:
  - usunięto nieużywany prop `hoveredCol`,
  - poprawiono pole pytania z `item.text` na `item.textM` (zgodnie z typem `Ap48Item`).
- `archetypy-ankieta/src/lib/jstStudies.ts`:
  - usunięto zależność od `replaceAll` (ES2021) na rzecz kompatybilnego helpera `split/join` (ES2020).
- Testy:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Zrobione w Hotfix H-031 (domknięcie przecięć TOP vs luki/dopasowania dla przypadków 2900/2901)
- `app.py` (`🧭 Matching`, sekcja `Główne zalety / Główne problemy`):
  - źródło porównań przecięć TOP zostało dodatkowo uodpornione:
    - łączone są nazwy z chipów (`strengths_rows`, `gaps_rows`) oraz rankingi live (`strongest_fit_entities`, `largest_gap_entities`),
    - porównanie nadal idzie po tej samej normalizacji nazw.
  - efekt: wpisy o priorytetach obecnych w `Największe luki` i `Najlepsze dopasowania` nie znikają przez różnice formatu źródeł.
- Dodatkowy smoke-check frontendu ankiety:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-032 (legenda pod profilem 0-100 + sortowanie tabeli)
- `app.py` (`🧭 Matching`, `Podsumowanie`):
  - legenda pod sekcją `Profile archetypowe 0-100 (siła archetypu, skala: 0-100)` nie jest już ograniczona do trybu `Wartość` — renderuje się również dla `Archetypów`,
  - tabela porównawcza profilu używa wartości liczbowych (`round(..., 1)`) zamiast stringów, więc sortowanie po kolumnach działa numerycznie.
- Efekt:
  - pod dwoma kołami 0-100 jest widoczna wspólna legenda,
  - klikane sortowanie kolumn (`↑/↓`) nie daje już losowego porządku przez sortowanie tekstowe.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-033 (ustawienia ankiety + single-screen + kontekst Demografii + `|Δ|` no-wrap)
- `app.py`:
  - `⚙️ Ustawienia ankiety` (personalne i JST):
    - nagłówek `Wybierz badanie` pogrubiony i większy (`+1px`),
    - dodano sekcję `Parametry ankiety` pomiędzy selektorem badania a `Status badania`,
    - personalne:
      - `Wyświetlanie ankiety`: `Macierz` / `Pojedyncze ekrany`,
      - `Nawigacja ankiety`: `Pokaż pasek postępu`, `Wyświetlaj przycisk Wstecz`,
      - `Losuj kolejność pytań`,
      - `Automatyczny start i zakończenie badania` (data + godzina),
    - JST:
      - `Nawigacja ankiety`,
      - `Automatyczny start i zakończenie badania` (data + godzina).
  - dodano helpery harmonogramu:
    - parsowanie dat UTC/local (Europe/Warsaw),
    - jednorazowe przejścia statusu wg planu:
      - przed startem (przy aktywnym harmonogramie) badanie przechodzi w `suspended`,
      - po wybiciu godziny startu może wrócić do `active`,
      - po wybiciu godziny końca przechodzi do `suspended` (bez trwałego `closed`).
  - `🧭 Matching -> Demografia`: dodano czytelną linię kontekstu (`polityk` + `JST`).
  - `Główne zalety/problemy`: frazy `(|Δ| ... pp)` sklejone NBSP, aby nie łamały się na dwie linie.
- `db_jst_utils.py`:
  - `ensure_jst_schema()` rozszerzony o pola ustawień ankiety dla `public.studies` i `public.jst_studies`:
    - `survey_display_mode`,
    - `survey_show_progress`,
    - `survey_allow_back`,
    - `survey_randomize_questions`,
    - `survey_auto_start_enabled`,
    - `survey_auto_start_at`,
    - `survey_auto_start_applied_at`,
    - `survey_auto_end_enabled`,
    - `survey_auto_end_at`,
    - `survey_auto_end_applied_at`,
  - dodano constrainty `survey_display_mode IN ('matrix','single')`,
  - `get_jst_study_public` zwraca nowe pola ustawień,
  - `add_jst_response_by_slug` respektuje harmonogram auto-start/auto-end i aktualizuje status przy pierwszym wejściu po przekroczeniu czasu.
- `archetypy-ankieta/src/App.tsx`:
  - odczyt ustawień ankiety z rekordu badania (personalne/JST),
  - status ankiety uwzględnia okna start/koniec,
  - przekazanie ustawień nawigacji do `Questionnaire` i `JstSurvey`.
- `archetypy-ankieta/src/Questionnaire.tsx` + `src/SingleQuestionnaire.css`:
  - nowy tryb `Pojedyncze ekrany`:
    - jedno pytanie na ekranie,
    - kolorowa skala 5 odpowiedzi,
    - `Dalej` (zablokowane bez odpowiedzi),
    - `Wyślij` po 48. pytaniu,
    - opcjonalny `Wstecz`,
    - opcjonalny pasek postępu,
  - tryb `Macierz` zachowany,
  - losowa kolejność pytań działa w obu trybach,
  - kodowanie odpowiedzi pozostaje poprawne (zapis po indeksach pytań źródłowych),
  - fraza `... (polityka/polityczki)` zależna od płci.
- `archetypy-ankieta/src/JstSurvey.tsx` + `src/JstSurvey.css`:
  - dodano opcjonalną górną nawigację JST:
    - pasek postępu,
    - przycisk `Wstecz`.
- `archetypy-ankieta/src/lib/studies.ts` i `src/lib/jstStudies.ts`:
  - modele rozszerzone o pola ustawień ankiety,
  - personalne `loadStudyBySlug` pobiera nowe kolumny z fallbackiem dla starszego schematu.
- Testy techniczne:
  - `python -m py_compile app.py db_jst_utils.py` (OK),
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Zrobione w Hotfix H-034 (2026-04-12, smoke-check po H-033)
- Potwierdzono brak regresji technicznej po zmianach H-033:
  - `python -m py_compile app.py db_jst_utils.py` (OK),
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).
- Zakres dalszego kroku pozostaje bez zmian:
  - ręczny smoke-test UI na środowisku użytkownika po deployu.

### Zrobione w Hotfix H-035 (2026-04-12, poprawki po screenach UAT)
- `app.py`:
  - domknięto no-wrap dla `(|Δ| ... pp)` w `Główne zalety/problemy` przez dedykowany `span.match-delta-nowrap`,
  - `Kontekst` w `🧭 Matching -> Demografia` dostał uporządkowany styl typu chip (bez brzydkiego kodowego markdown),
  - po `💾 Zapisz parametry ankiety` (personal/JST) działa widoczny feedback `Zapisano parametry ankiety` przez toast kompatybilny ze starszym Streamlit.
- `archetypy-ankieta/src/Questionnaire.tsx`:
  - przywrócono paletę kolorów skali zgodną z referencją 2899 (nagłówki macierzy + skala w single-screen),
  - `Pojedyncze ekrany`:
    - usunięto etykiety nad skalą (`Zdecydowanie się nie zgadzam ...`),
    - przeniesiono `Pamiętaj: ...` na górę i wystylowano na szaro,
    - usunięto pogrubienie nazwiska w zdaniu `Czy zgadzasz się ... na temat ...?`,
    - przebudowano strukturę pod zawężony desktopowy layout.
- `archetypy-ankieta/src/SingleQuestionnaire.css`:
  - zawężono obszar treści na desktopie,
  - podniesiono sekcję odpowiedzi (bez przyklejania do samego dołu),
  - przycisk `Dalej` ma lżejszy, mniej dominujący styl,
  - `Wstecz` dopasowano wizualnie do referencji mobilnej.
- Testy techniczne:
  - `python -m py_compile app.py` (OK),
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Zrobione w Hotfix H-036 (2026-04-13, druga iteracja `Pojedyncze ekrany`)
- `archetypy-ankieta/src/SingleQuestionnaire.css`:
  - `Dalej`:
    - zielony styl CTA + hover,
    - desktop: większy odstęp poniżej odpowiedzi,
    - mobile: stałe pozycjonowanie w prawym dolnym rogu z marginesem od krawędzi (`safe-area`).
  - `Wstecz`:
    - ta sama typografia co `Dalej`,
    - dodany efekt podświetlenia na hover.
  - dopracowano odstępy i typografię:
    - większy dystans pytanie ↔ odpowiedzi,
    - mniejszy tekst `Pamiętaj...`,
    - mniejszy `Czy zgadzasz...` z wagą `590`,
    - licznik `1/48` ustawiony na `0.95rem`.
  - mobile polish:
    - większy pionowy oddech między sekcjami,
    - mniejsze fonty etykiet odpowiedzi + ciaśniejsza siatka, żeby długie etykiety mieściły się w równych kafelkach.
- Testy techniczne:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Zrobione w Hotfix H-037 (2026-04-13, stabilizacja mobile + hover desktop)
- `archetypy-ankieta/src/Questionnaire.tsx`:
  - odpowiedzi w `Pojedyncze ekrany` korzystają ze zmiennych CSS (`--opt-color`, `--opt-bg`, `--opt-border`),
    co pozwala kontrolować kolor hover/selected po stronie CSS.
- `archetypy-ankieta/src/SingleQuestionnaire.css`:
  - `Dalej`:
    - usunięto cień (desktop i mobile),
  - odpowiedzi desktop:
    - hover podświetla kafelek kolorami opcji,
    - kliknięty kafelek zachowuje kolor docelowy,
    - usunięto dominujący efekt „unoszenia” jako jedyny sygnał hover,
  - mobile portrait:
    - obniżono sekcję tekstów/pytania (większy pionowy oddech),
    - odpowiedzi ustawione niżej i na stałej pozycji,
    - pasek odpowiedzi nie skacze między pytaniami (fixed zone),
  - mobile landscape:
    - dodano osobne style orientacji poziomej (mniejsze fonty/odstępy, stałe pozycje),
    - cel: kluczowe elementy widoczne jednocześnie na ekranie.
- Testy techniczne:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Zrobione w Hotfix H-038 (2026-04-13, geometra mobile + tabela Matching `x.0`)
- `archetypy-ankieta/src/SingleQuestionnaire.css`:
  - mobile portrait:
    - pasek odpowiedzi podniesiony wyżej,
    - fixed zone ma `width:auto` i `box-sizing:border-box`, co eliminuje obcinanie ostatniego kafelka,
    - większy pionowy oddech sekcji tekstowych.
  - mobile landscape:
    - mniejsza typografia pytania i tekstów pomocniczych,
    - stała strefa odpowiedzi z dopasowaną szerokością,
    - `Dalej` przeniesiony na górę po prawej.
- `archetypy-ankieta/src/Questionnaire.tsx`:
  - utrzymano kolorowanie opcji przez CSS variables (`--opt-*`) dla precyzyjnego hover/selected.
- `app.py` (`🧭 Matching`, tabela porównawcza profili):
  - dodano `column_config` z `NumberColumn(format="%.1f")` dla kolumn liczbowych,
  - efekt: wyświetlanie zawsze z 1 miejscem po przecinku (także `76.0`) przy zachowaniu sortowania liczbowego.
  - dodano fallback dla starszego Streamlit (`TypeError` -> render bez `column_config`).
- Testy techniczne:
  - `python -m py_compile app.py` (OK),
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### BLOKERY / RYZYKA
- BLOKER operacyjny:
  - brak możliwości pełnego UAT UI bez deployu i dostępu do środowiska użytkownika (weryfikacja finalnego wyglądu matrix/single + kontekst + toasty).
- Ryzyko wdrozeniowe:
  - nowe kolumny ustawień ankiety wymagają uruchomienia `ensure_jst_schema()` po deployu `archetypy-admin`.
  - do potwierdzenia na danych produkcyjnych: E2E dla harmonogramu (start/koniec, auto-przejście w `suspended`, ręczne odwieszenie po auto-końcu).
  - do potwierdzenia na danych produkcyjnych: E2E dla trybu `Pojedyncze ekrany` (desktop + mobile) oraz poprawność randomizacji przy eksporcie/analityce.

### Nastepny konkretny krok wykonawczy
- Smoke-test UI na środowisku użytkownika dla Hotfix H-033:
  - `Badania personalne -> ⚙️ Ustawienia ankiety`: sprawdzić zapis `Macierz/Pojedyncze ekrany`, pasek postępu, `Wstecz`, auto-start/auto-end,
  - `Badania mieszkańców -> ⚙️ Ustawienia ankiety`: sprawdzić zapis opcji nawigacji i harmonogramu,
  - ankieta personalna `/slug`: potwierdzić tryb pojedynczych ekranów (48 pytań, `Dalej`/`Wyślij`, blokada bez odpowiedzi),
  - `🧭 Matching -> Demografia`: potwierdzić widoczny kontekst polityk/JST i brak łamania `(|Δ| ... pp)` w `Główne zalety/problemy`.

### Zrobione w Hotfix H-039 (2026-04-13, mobile-only + matrix rotate fix)
- `archetypy-ankieta/src/Questionnaire.tsx`:
  - zastąpiono prostą detekcję orientacji stanem `viewport` (szer./wys.) aktualizowanym przez `resize`, `orientationchange` i `visualViewport.resize`,
  - ekran `Prosimy, obróć telefon poziomo` dla macierzy opiera się na bieżącym viewport i nie zalega po obrocie,
  - na mobile w trybie macierzy logo `Badania.pro` jest ukryte.
- `archetypy-ankieta/src/SingleQuestionnaire.css`:
  - mobile portrait:
    - pasek odpowiedzi podniesiony wyżej,
    - `Czy zgadzasz się...` delikatnie powiększone,
  - mobile landscape:
    - licznik `x/48` wyśrodkowany pod paskiem postępu,
    - `Dalej` przeniesiony do prawego górnego obszaru nawigacji.
- Testy techniczne:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### RYZYKO / do potwierdzenia UAT
- Zachowanie macierzy po obrocie (pion -> poziom) zostało naprawione logicznie w kodzie; wymaga potwierdzenia na realnym urządzeniu użytkownika, bo wcześniejszy biały ekran był zależny od konkretnej przeglądarki mobile.

### Zrobione w Hotfix H-040 (2026-04-13, desktop fixed bar + mobile nav/fullscreen + matrix rotate fallback)
- `archetypy-ankieta/src/SingleQuestionnaire.css`:
  - desktop: pasek odpowiedzi i akcja `Dalej` osadzone w stałym miejscu (`position: fixed`),
  - mobile: dopięto override `left/transform/width` w media-query, by nie dziedziczyć desktopowego kotwiczenia,
  - mobile landscape: `Dalej` podniesione na wysokość nawigacji (`Wstecz`).
- `archetypy-ankieta/src/App.tsx`:
  - dodano `tryEnterFullscreenMobile()` (best effort) uruchamiane po `Zaczynamy` i po wejściu do ankiety,
  - stan startu ankiety synchronizowany przez hash `#q`, żeby ewentualny reload nie cofał do ekranu powitalnego,
  - `Questionnaire` objęty `AppErrorBoundary`, więc ewentualny runtime error nie kończy się białym ekranem.
- `archetypy-ankieta/src/Questionnaire.tsx`:
  - matrix mobile: dodano fallback `orientationchange -> reload` z guardem czasowym, aby po obrocie do poziomu wymusić czysty render strony ankiety.
- `archetypy-ankieta/index.html`:
  - dodano meta pod mobile/fullscreen (`viewport-fit=cover`, `mobile-web-app-capable`, `apple-mobile-web-app-capable`, `theme-color`).
- Testy techniczne:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### RYZYKO / ograniczenie platformy
- Ukrycie paska adresu nie jest gwarantowane na każdej przeglądarce mobile; Fullscreen API działa jako best effort i zależy od polityki przeglądarki/OS.

### Zrobione w Hotfix H-041 (2026-04-13, rollback regresji i korekta pozycji)
- `archetypy-ankieta/src/Questionnaire.tsx`:
  - usunięto fallback `orientationchange -> reload` z H-040,
  - `singleProgress` nie używa już `useMemo`; liczony jest jako zwykła wartość,
  - to eliminuje ryzyko `Minified React error #310` przy zmianie orientacji i ekranie `obróć telefon`.
- `archetypy-ankieta/src/SingleQuestionnaire.css`:
  - desktop: pasek odpowiedzi i `Dalej` podniesione z dolnej krawędzi do poziomu referencyjnego (jak 2944),
  - mobile landscape: `Dalej` podniesione do linii nawigacji (`Wstecz`) bez rozwalania wcześniejszego układu,
  - dodano obsługę landscape dla niskiej wysokości (`max-height:560px`), niezależnie od szerokości.
- Testy techniczne:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Zrobione w Hotfix H-042 (2026-04-13, twarde spacje + finalne dosunięcia mobile)
- `archetypy-ankieta/src/Questionnaire.tsx`:
  - dodano helper `withHardSpaces` i podpięto go do głównych tekstów pytania (single + matrix),
  - dzięki temu krótkie słowa (`i`, `z`, `na`, `by` itd.) nie wiszą na końcach linii,
  - w matrix mobile kontener nagłówka ma `flex:1; minWidth:0`, więc po ukryciu logo tekst wypełnia wolne miejsce.
- `archetypy-ankieta/src/SingleQuestionnaire.css`:
  - mobile portrait: pasek odpowiedzi podniesiony wyżej,
  - mobile landscape: `Dalej` obniżony (bliżej `Wstecz`, pod paskiem postępu) w obu media-query landscape.
- Testy techniczne:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Zrobione w Hotfix H-043 (2026-04-13, orientacja matrix + dalsze dosunięcia mobile)
- `archetypy-ankieta/src/Questionnaire.tsx`:
  - `withHardSpaces` sklejający frazy (`gdzie inni`, `nawet jeśli`) działa teraz na wszystkich białych znakach w dopasowaniu (`\s+ -> NBSP` globalnie),
  - odczyt viewportu przeszedł na helper `readViewport()` (priorytet `visualViewport`, fallback `documentElement`, potem `innerWidth/innerHeight`),
  - orientacja macierzy jest wyznaczana odporniej (`dimensions first`, potem `screen.orientation`, na końcu `matchMedia`),
  - polling viewportu dla macierzy przyspieszono do `180ms`, żeby szybciej wychodzić ze stanu „obróć telefon”.
- `archetypy-ankieta/src/SingleQuestionnaire.css`:
  - mobile portrait:
    - pasek odpowiedzi podniesiony jeszcze wyżej (`bottom +174px`),
    - zwiększony bufor dolny treści (`padding-bottom +236px`), żeby uniknąć kolizji z fixed strefą,
  - mobile landscape:
    - `Dalej` przesunięty wyżej (`top +44px`) w obu media-query landscape.
- `Enter -> Dalej`:
  - logika jest aktywna w `Questionnaire.tsx` (single-screen, po zaznaczeniu odpowiedzi) i została utrzymana.
- Testy techniczne:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Zrobione w Hotfix H-044 (2026-04-13, fix #300/#310 + `←` + mobile landscape)
- `archetypy-ankieta/src/Questionnaire.tsx`:
  - naprawiono główną przyczynę `Minified React error #300/#310`:
    - warunkowy ekran `obróć telefon` nie przerywa już renderu przed kolejnymi hookami,
    - teraz jest liczony jako `showOrientationWarning`, a renderowany po wywołaniu wszystkich hooków,
  - dodano kolejne sklejenia fraz przez NBSP:
    - `których reprezentuje`,
    - `jest podstawą`,
    - `których głos`,
  - w trybie single-screen klawisz `ArrowLeft` działa jak `Wstecz` (z poszanowaniem `allowBack` i indeksu pytania).
- `archetypy-ankieta/src/SingleQuestionnaire.css`:
  - mobile landscape:
    - podniesiono czytelność `Pamiętaj...` i `Czy zgadzasz...` (większe fonty),
    - zwiększono delikatnie górny oddech sekcji pytania,
    - `Dalej` przesunięto wyżej (`top +34px`) bliżej linii nawigacji pod paskiem postępu.
- Testy techniczne:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Zrobione w Hotfix H-045 (2026-04-13, czytelność mobile + `→` do przodu)
- `archetypy-ankieta/src/SingleQuestionnaire.css`:
  - mobile portrait:
    - górny margines sekcji pytań zmniejszony (`single-question-zone`), więc treści startują wcześniej,
    - zwiększono czytelność tekstów:
      - `single-sublead` -> większy font,
      - `single-lead` -> większy font,
  - mobile landscape:
    - zwiększono fonty `single-sublead` i `single-lead`,
    - zwiększono lekko górny oddech sekcji pytań,
    - `Dalej` podniesiono jeszcze wyżej (`top +22px`) w obu media-query landscape.
- `archetypy-ankieta/src/Questionnaire.tsx`:
  - dodano skrót `ArrowRight`:
    - przejście do następnego pytania (`Dalej/Wyślij`) działa, jeśli bieżące pytanie jest zaznaczone.
- Testy techniczne:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Zrobione w Hotfix H-046 (2026-04-13, mikro-typografia mobile landscape)
- `archetypy-ankieta/src/SingleQuestionnaire.css`:
  - w mobile landscape (`max-width:900`) zwiększono:
    - `single-sublead`,
    - `single-lead`,
    - `single-question-text` (docelowo ~+2px),
  - dodano większy odstęp po linii `Czy zgadzasz...` przez:
    - `single-lead { margin-bottom: ... }`,
    - większy `single-question-text { margin-top: ... }`,
  - analogiczny tuning wykonano dla wariantu `max-height:560` (landscape low-height).
- Testy techniczne:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Zrobione w Hotfix H-047 (2026-04-13, auto-odmiana JST dla nazw `-o`)
- `app.py`:
  - w `_guess_word_cases(...)` dodano dedykowaną gałąź dla nazw miejscowych nijakich kończących się na `-o`,
  - nowe formy:
    - `gen = base + "a"`,
    - `dat = base + "u"`,
    - `acc = nom`,
    - `ins = base + "em"`,
    - `loc = base + "ie"`,
    - `voc = nom`,
  - dzięki temu auto-uzupełnianie w `➕ Dodaj badanie mieszkańców` nie generuje już błędów typu `Testowoa`, `Testowoowi`.
- Kontrola funkcjonalna (lokalny probe funkcji):
  - `Testowo` -> `Testowa / Testowu / Testowo / Testowem / Testowie`,
  - `Braniewo` -> `Braniewa / Braniewu / Braniewo / Braniewem / Braniewie`,
  - `Gniezno` -> `Gniezna / Gnieznu / Gniezno / Gnieznem / Gnieznie`.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-048 (2026-04-13, frazy NBSP + wyjątki JST)
- `archetypy-ankieta/src/Questionnaire.tsx`:
  - rozszerzono `PHRASE_GLUE_PATTERNS` o:
    - `nawet jeśli jest`,
    - `nawet jeśli koszt`,
  - dzięki temu wskazane frazy nie łamią się między wierszami.
- `app.py`:
  - dodano słownik wyjątków odmiany dla nieregularnych nazw JST:
    - `JST_WORD_CASE_OVERRIDES`,
    - `JST_PHRASE_CASE_OVERRIDES`,
  - `_guess_word_cases(...)` i `_guess_phrase_cases(...)` najpierw stosują override, a dopiero potem reguły heurystyczne.
- Kontrola funkcjonalna (lokalny probe):
  - poprawne formy m.in. dla:
    - `Ełk`,
    - `Sopot`,
    - `Kielce`,
    - `Zakopane`,
    - `Zielona Góra`,
    - `Nowy Sącz`.
- Testy techniczne:
  - `python -m py_compile app.py` (OK),
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Zrobione w Hotfix H-049 (2026-04-13, JST mobile rotate off + dark slider axis + public report participants)
- `archetypy-ankieta/src/JstSurvey.tsx`:
  - wymuszenie obrotu JST na mobile zostało tymczasowo wyłączone przez flagę `ENFORCE_JST_LANDSCAPE_ON_MOBILE = false`.
- `archetypy-ankieta/src/JstSurvey.css`:
  - poprawiono widoczność osi suwaka w dark mode:
    - jaśniejszy tor suwaka (WebKit + Firefox),
    - dodany kontrastujący obrys/shadow toru,
    - jaśniejsze ticki osi.
- `archetypy-admin/app.py`:
  - `public_report_view` pobiera liczbę uczestników badania i renderuje u góry raportu dedykowany kafelek:
    - wartość liczbowa,
    - podpis `uczestnik badania` / `uczestników badania`,
    - wersja responsywna i zgodna z dark mode.
- Testy techniczne:
  - `python -m py_compile app.py` (OK),
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Zrobione w Hotfix H-050 (2026-04-14, public heading row + slider dark contrast + B align)
- `archetypy-admin/admin_dashboard.py`:
  - licznik uczestników w publicznym raporcie został przeniesiony do tej samej linii co nagłówek `Informacje na temat archetypów ...`,
  - układ jest: tytuł po lewej, licznik po prawej (responsive + dark mode).
- `archetypy-admin/app.py`:
  - usunięto wcześniejszy kafelek licznika renderowany globalnie nad raportem (to on powodował „uciekanie” w prawy górny róg strony).
- `archetypy-ankieta/src/JstSurvey.css`:
  - tor suwaka w dark mode ma mocniejszy kontrast (jaśniejszy fill + obrys),
  - ticki są bardziej widoczne (grubsze i jaśniejsze),
  - opisy po prawej stronie suwaka (`B`) są wyrównane do prawej.
- Testy techniczne:
  - `python -m py_compile app.py admin_dashboard.py` (OK),
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Zrobione w Hotfix H-051 (2026-04-14, send_link warning + dark track visibility)
- `archetypy-admin/send_link.py`:
  - usunięto konflikt inicjalizacji pola `email_subject` (jednoczesne `value=` i `st.session_state`),
  - pole tematu e-mail działa teraz wyłącznie przez `key="email_subject"` + stan sesji.
- `archetypy-ankieta/src/JstSurvey.css`:
  - dodano niezależną warstwę toru suwaka (`.jst-range-wrap::before`) dla stabilnej widoczności na mobile,
  - w dark mode tor jest dodatkowo wzmocniony (kolor, obrys, shadow).
- Testy techniczne:
  - `python -m py_compile send_link.py app.py` (OK),
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Zrobione w Hotfix H-052 (2026-04-14, rollback ciężkiej osi suwaka JST)
- `archetypy-ankieta/src/JstSurvey.css`:
  - usunięto agresywną, dodatkową warstwę toru (`.jst-range-wrap::before`),
  - przywrócono lżejszy, wcześniejszy wygląd suwaka,
  - dark mode: zostawiono jedynie subtelne rozjaśnienie toru i cienkie obramowanie,
  - ticki osi wróciły do cienkiego wariantu.
- Testy techniczne:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Zrobione w Hotfix H-053 (2026-04-14, dodatkowe rozjaśnienie toru suwaka JST)
- `archetypy-ankieta/src/JstSurvey.css`:
  - tor suwaka w dark mode został jeszcze rozjaśniony (jaśniejsze tło + lżejsze obramowanie + mocniejszy wewnętrzny highlight).
- Testy techniczne:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Zrobione w Hotfix H-054 (2026-04-14, jasny tor suwaka + fallback na `.jst-range`)
- `archetypy-ankieta/src/JstSurvey.css`:
  - w dark mode tor suwaka został istotnie rozjaśniony,
  - dodano fallback jasnego toru na samym `.jst-range`, aby oś była widoczna także przy kapryśnym renderze pseudo-elementów `range` na mobile browserach,
  - ticki osi zostały dodatkowo rozjaśnione.
- Testy techniczne:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Zrobione w Hotfix H-055 (2026-04-14, usuwanie rekordów JST w Import/Eksport)
- `db_jst_utils.py`:
  - dodano funkcję `delete_jst_responses_by_respondent_ids(sb, study_id, respondent_ids)`,
  - funkcja:
    - normalizuje i deduplikuje `respondent_id`,
    - kasuje rekordy partiami (`chunk`) tylko w obrębie wskazanego `study_id`,
    - zwraca liczbę faktycznie usuniętych odpowiedzi.
- `app.py` (`jst_io_view`):
  - tabela `Eksport odpowiedzi` została rozbudowana o checkboxy (`Usuń`) w każdym wierszu,
  - dodano przycisk `🗑️ Usuń zaznaczone`,
  - dodano etap potwierdzenia (`✅ Tak, usuń zaznaczone` / `↩️ Anuluj`),
  - po usunięciu jest komunikat sukcesu i automatyczne odświeżenie widoku.
- Test techniczny:
  - `python -m py_compile app.py db_jst_utils.py` (OK).

### Zrobione w Hotfix H-056 (2026-04-14, stara karta archetypu po podmianie PNG)
- Objaw:
  - w `📊 Sprawdź wyniki badania archetypu` sekcja karty archetypu (`5.1.2`) potrafiła pokazywać starą wersję grafiki mimo podmienionego `assets/card/bohater.png`.
- Przyczyna:
  - cache data URI obrazka był trzymany po samej nazwie archetypu i ścieżce, bez uwzględnienia zmiany pliku (`mtime/size`),
  - dodatkowo dobór pliku w `_card_file_for(...)` mógł wejść w fallback prefiksowy zanim trafił idealny plik.
- `admin_dashboard.py`:
  - `_card_file_for(...)`:
    - etap 1: dokładne dopasowanie nazwy (priorytet),
    - etap 2: deterministyczny fallback prefiksowy (sort + minimalna różnica długości),
  - `_file_to_data_uri(...)`:
    - dodano opcjonalny `cache_buster` do klucza cache,
  - `_archetype_card_data_uri(...)`:
    - przy generowaniu data URI używa tokenu `mtime_ns:size`,
  - dodano `_archetype_card_cache_token(...)` i podpięto w renderze kart rozszerzonych.
- Efekt:
  - po podmianie `assets/card/*.png` aplikacja bierze nową wersję obrazu bez potrzeby restartu procesu.
- Test techniczny:
  - `python -m py_compile admin_dashboard.py` (OK).

### Zrobione w Hotfix H-057 (2026-04-14, tie-break kolejności archetypów przy tym samym %)
- `admin_dashboard.py` (`Podsumowanie archetypów (liczebność i natężenie)`):
  - wprowadzono nową regułę kolejności wierszy:
    1) `% natężenia` malejąco (po zaokrągleniu do 1 miejsca, jak w tabeli),
    2) `Główny archetyp` malejąco,
    3) `Wspierający archetyp` malejąco,
    4) `Poboczny archetyp` malejąco,
    5) alfabetycznie rosnąco.
  - usunięto wtórne sortowanie DataFrame po samym `%`, które mogło nadpisywać tie-break.
- Efekt:
  - przy remisie `%` kolejność jest stabilna i zgodna z regułą biznesową.
- Test techniczny:
  - `python -m py_compile admin_dashboard.py` (OK).

### Zrobione w Hotfix H-058 (2026-04-14, iPhone mobile + realna transliteracja SMS JST)
- `archetypy-ankieta/src/App.tsx`:
  - ekran powitalny ankiety personalnej ma wymuszony ciemny kolor tekstu na białym tle,
  - dodatkowo blok treści powitalnej dostał jawny kolor tekstu, aby iOS dark mode nie rozjaśniał liter.
- `archetypy-ankieta/src/SingleQuestionnaire.css`:
  - mobile portrait:
    - sekcja pytań startuje wyżej (mniejszy górny offset),
    - pasek odpowiedzi i strefa `Dalej` przeszły z `position: fixed` do normalnego flow pod pytaniem,
    - dodano większy odstęp nad odpowiedziami, żeby eliminować nakładanie się odpowiedzi na treść pytania na iPhone.
- `archetypy-admin/send_link_jst.py`:
  - transliteracja SMS (`_strip_pl_diacritics`) jest stosowana do realnie wysyłanego payloadu SMS,
  - transliterowana treść jest też zapisywana przy tworzeniu rekordu SMS,
  - ponowna wysyłka (`_resend_sms_row`) również wysyła transliterowaną treść.
- Testy techniczne:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK),
  - `python -m py_compile send_link_jst.py` (OK).

### Zrobione w Hotfix H-070 (2026-04-14, iPhone single-screen: pytanie + etykiety kafelków)
- `archetypy-ankieta/src/Questionnaire.tsx`:
  - w single-screen neutralna odpowiedź jest renderowana jako:
    - `ani tak,`
    - `ani nie`
    (wymuszone złamanie linii tylko dla tego kafelka, jawnie przez `<br />`).
- `archetypy-ankieta/src/SingleQuestionnaire.css`:
  - przyciski odpowiedzi mają teraz:
    - `white-space: pre-line`,
    - `word-break: break-word`,
    - `overflow-wrap: anywhere`,
  - dla `max-width:430px` zmniejszono font/padding etykiet, żeby słowo `zdecydowanie` mieściło się stabilnie w kafelku,
  - w mobile portrait dla głównego pytania dodano bezpieczne łamanie (`overflow-wrap/word-break/hyphens`) i pełną szerokość bloku (`max-width:100%`), żeby nie ucinało końcówki zdania na iPhone.
  - dogrywka iPhone 15 Pro:
    - `overflow-x: hidden` dla `.single-survey-root`,
    - `min-width: 0` dla `.single-scale-btn`,
    - dodatkowe uszczelnienie mobile portrait (`width: 100%`, `box-sizing`, wewnętrzny padding pytania),
    - mniejszy font kafelków dla `max-width:430px` (`0.62rem`), żeby `zdecydowanie` nie wychodziło poza ramkę.
- Testy techniczne:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Zrobione w Hotfix H-059 (2026-04-14, powiadomienia e-mail po nowych odpowiedziach)
- `db_jst_utils.py`:
  - `ensure_jst_schema()` rozszerza `jst_studies` i `studies` o pola powiadomień:
    - `survey_notify_on_response`,
    - `survey_notify_email`,
    - `survey_notify_last_count`,
    - `survey_notify_last_sent_at`,
  - `insert_jst_study(...)` ustawia domyślne wartości nowych pól.
- `db_utils.py`:
  - `insert_study(...)` ustawia domyślne wartości pól powiadomień dla badań personalnych.
- `app.py`:
  - `_extract_survey_settings(...)` odczytuje konfigurację powiadomień,
  - `personal_settings_view` i `jst_settings_view`:
    - nowa sekcja `Powiadomienia`,
    - checkbox `Wysyłaj powiadomienie po uzyskaniu odpowiedzi`,
    - aktywowane pole adresu e-mail,
    - walidacja e-mail przy zapisie,
    - baseline `survey_notify_last_count` ustawiany na bieżący licznik odpowiedzi przy aktywacji/zmianie adresu,
  - dodano dispatcher `_run_response_notifications_dispatcher()` uruchamiany przy pracy panelu:
    - monitoruje wzrost liczby odpowiedzi,
    - wysyła e-mail notyfikacyjny dla personalnych i JST,
    - po sukcesie aktualizuje `survey_notify_last_count` i `survey_notify_last_sent_at`.
- Treść wysyłanego e-maila:
  - `Została udzielona odpowiedź w badaniu {tytuł badania}, dostępnym pod adresem {link}.`
  - `Łączna liczba wypełnionych ankiet dla tego badania to: {N}.`
- Test techniczny:
  - `python -m py_compile app.py db_jst_utils.py db_utils.py` (OK).

### Zrobione w Hotfix H-060 (2026-04-14, copy + natychmiastowość powiadomień + klawiatura JST)
- `archetypy-admin/app.py`:
  - poprawiono opis badania używany w mailach:
    - personalne: `archetypu {imię i nazwisko w dopełniaczu} ({miasto})`,
    - JST: `mieszkańców {nazwa JST w dopełniaczu}`,
  - dzięki temu:
    - tytuł personalny ma formę `Nowa odpowiedź w badaniu archetypu ...`,
    - tytuł JST ma formę `Nowa odpowiedź w badaniu mieszkańców ...`,
    - treść maila ma analogicznie poprawione formy.
  - dispatcher notyfikacji dostał tryb pracy w tle:
    - uruchamiany raz przez `@st.cache_resource`,
    - działa cyklicznie w osobnym wątku (`survey-notify-dispatcher`),
    - nie wymaga ręcznego odświeżenia panelu, aby wysłać powiadomienie po nowej odpowiedzi.
- `archetypy-ankieta/src/JstSurvey.tsx`:
  - dodano desktopowe skróty klawiaturowe:
    - `Enter` = przejście dalej / wyślij,
    - `ArrowRight` = przejście dalej,
    - `ArrowLeft` = cofnięcie (`Wstecz`) przy `allowBack`,
  - skróty są blokowane, gdy fokus jest w polu edycji (`input`, `textarea`, `select`), żeby nie kolidować z wpisywaniem danych.
- Testy techniczne:
  - `python -m py_compile app.py db_jst_utils.py db_utils.py` (OK),
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Zrobione w Hotfix H-061 (2026-04-14, fundament modelu metryczki konfigurowalnej JST)
- Dodano moduł `metryczka_config.py`:
  - definicja rdzenia 5 pytań metryczkowych,
  - domyślny config metryczki per badanie JST,
  - normalizacja i walidacja konfiguracji (rdzeń + pytania custom),
  - zabezpieczenia: format ID, unikalność `db_column`, fallback do bezpiecznych defaultów.
- `db_jst_utils.py`:
  - `ensure_jst_schema()` rozszerza tabelę `jst_studies` o:
    - `metryczka_config`,
    - `metryczka_config_version`,
  - `get_jst_study_public(...)` zwraca konfigurację metryczki,
  - `insert_jst_study(...)` i `update_jst_study(...)` pracują na znormalizowanej konfiguracji,
  - `fetch_jst_studies(...)` oraz `fetch_jst_study_by_id(...)` normalizują config przy odczycie (kompatybilność ze starszymi rekordami).
- Dodano dokument `JST_METRYCZKA_MODEL.md`:
  - model JSON metryczki,
  - zasady mapowania do importu i raportów,
  - plan dalszego wdrożenia (UI admin + render ankiety + parser raportów dla custom zmiennych).
- Test techniczny:
  - `python -m py_compile db_jst_utils.py metryczka_config.py app.py` (OK).

### Zrobione w Hotfix H-062 (2026-04-14, osobny kafelek + edytor metryczki JST/personal)
- `app.py`:
  - dodano osobny kafelek `🧾 Metryczka` w panelach:
    - `Badania mieszkańców`,
    - `Badania personalne`,
  - dodano nowe widoki:
    - `jst_metryczka_view`,
    - `personal_metryczka_view`,
  - dodano wspólny edytor metryczki:
    - 5 pytań rdzeniowych (stałe kodowanie kolumn),
    - możliwość edycji treści pytań i list odpowiedzi,
    - możliwość dodawania/usuwania pytań dodatkowych z kodowaniem (`M_...`),
    - walidacja spójności kodowania i odpowiedzi przed zapisem.
- `metryczka_config.py`:
  - dodano funkcje dla badań personalnych:
    - `default_personal_metryczka_config(...)`,
    - `normalize_personal_metryczka_config(...)`.
- `db_utils.py`:
  - `fetch_studies(...)` normalizuje i zwraca `metryczka_config`,
  - `insert_study(...)` zapisuje domyślną konfigurację metryczki,
  - `update_study(...)` normalizuje konfigurację przy zapisie.
- `db_jst_utils.py`:
  - migracja schematu rozszerza także tabelę `studies` o:
    - `metryczka_config`,
    - `metryczka_config_version`.
- Test techniczny:
  - `python -m py_compile app.py db_utils.py db_jst_utils.py metryczka_config.py` (OK).

### Zrobione w Hotfix H-063 (2026-04-14, wklejanie pytania i odpowiedzi do metryczki)
- `app.py`:
  - w edytorze metryczki dodano przycisk `📋 Wklej pytanie i odpowiedzi` przy każdym pytaniu,
  - po kliknięciu otwiera się panel:
    - pole wklejania treści,
    - podgląd parsowania (`Treść pytania` + `Odpowiedzi`),
    - akcje `Wstaw` / `Anuluj`,
  - dodano parser treści wklejanej:
    - usuwa numerację i bulety (`1.`, `-`, `•`, `a)` itd.),
    - rozdziela pytanie od odpowiedzi heurystycznie (w tym przypadki wieloliniowego pytania),
    - działa także dla wariantu „same odpowiedzi” (zostawia istniejące pytanie),
  - `Wstaw`:
    - aktualizuje treść pytania (jeśli wykryta),
    - podmienia odpowiedzi,
    - nadaje kodowanie odpowiedzi sekwencyjnie `1..N`.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-064 (2026-04-14, kodowanie rdzenia metryczki zgodne z historyczną bazą)
- `metryczka_config.py`:
  - dla 5 pytań rdzeniowych (`M_PLEC`, `M_WIEK`, `M_WYKSZT`, `M_ZAWOD`, `M_MATERIAL`) domyślne `code` odpowiedzi ustawiono na tekst odpowiedzi,
  - normalizator rdzenia utrzymuje tę zasadę również przy odczycie/zapisie konfiguracji (`code = label`).
- `app.py`:
  - `_metryczka_options_from_df(...)` przestało wymuszać uppercase kodowania odpowiedzi,
  - w flow `Wklej pytanie i odpowiedzi`:
    - dla rdzenia kodowanie odpowiedzi = tekst odpowiedzi (zgodność z dotychczasową bazą),
    - dla pytań custom pozostaje auto-kodowanie `1..N`,
  - komunikat przy polu kodowania rdzenia doprecyzowany (zgodność historyczna).
- Test techniczny:
  - `python -m py_compile app.py metryczka_config.py db_utils.py db_jst_utils.py` (OK).

### Zrobione w Hotfix H-065 (2026-04-14, niższe pola `Pytanie` w metryczce)
- `app.py`:
  - poprawiono selektor CSS dla pól `Pytanie` w edytorze metryczki:
    - zamiast selektora po `id` użyto pewnego targetu `textarea[aria-label=\"Pytanie\"]`,
  - ustawiono niższą wysokość startową:
    - `min-height: 38px`,
    - `height: 38px`,
    - `line-height: 1.25`,
  - pozostawiono możliwość ręcznego rozszerzania pola w dół (`resize: vertical`).
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-066 (2026-04-14, metryczka paste panel: crash + preview + UX scroll)
- `archetypy-admin/app.py` (`_render_metryczka_editor`):
  - naprawiono crash po `Anuluj` w panelu `📋 Wklej pytanie i odpowiedzi`:
    - usunięto niedozwolone modyfikowanie `st.session_state[paste_text_key]` po utworzeniu widgetu,
    - dodano bezpieczne czyszczenie przez flagę `paste_clear_*` i `st.session_state.pop(...)` przed renderem pola.
  - usunięto wymuszony `st.rerun()` po kliknięciu przycisku otwierającego panel wklejania,
    co ogranicza „wystrzał” widoku na górę.
  - podgląd parsera dostał fallback do aktualnych wartości pytania:
    - gdy pole wklejania jest puste, `Treść pytania` pokazuje obecną treść pytania,
    - `Odpowiedzi` pokazują bieżącą listę odpowiedzi zamiast `(brak)`.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-067 (2026-04-14, metryczka: pole `Pytanie` było za niskie)
- `archetypy-admin/app.py`:
  - zwiększono wysokość startową pola `Pytanie` w edytorze metryczki:
    - `min-height: 50px`,
    - `height: 50px`,
    - `line-height: 1.3`,
  - pozostawiono `resize: vertical` (możliwość rozszerzania w dół).
- Efekt:
  - pole nie jest już zbyt „ściśnięte” i lepiej mieści pytanie już na starcie.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-068 (2026-04-14, metryczka: wysokość pola + odblokowanie resize)
- `archetypy-admin/app.py`:
  - usunięto efekt „zamrożenia” wysokości pola `Pytanie`:
    - CSS nie trzyma już stałego `height: 50px`,
    - zamiast tego: `min-height: 56px`, `height: auto`, `max-height: none`, `resize: vertical`.
  - podniesiono wysokość startową widgetu `st.text_area("Pytanie")` do `56`.
- Efekt:
  - pole jest odrobinę wyższe na starcie,
  - uchwyt w prawym dolnym rogu powinien znów pozwalać rozszerzać pole w dół.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-069 (2026-04-14, metryczka paste: prefill + zwarty podgląd)
- `archetypy-admin/app.py` (`_render_metryczka_editor`):
  - po kliknięciu `📋 Wklej pytanie i odpowiedzi` pole `Wklej treść` jest automatycznie zasilane bieżącą treścią pytania i istniejącymi odpowiedziami,
  - podgląd (`Podgląd -> Odpowiedzi`) przeszedł na kompaktowy render HTML listy (`<ul><li>`),
    co usuwa nadmierne odstępy między punktami.
- Efekt:
  - użytkownik od razu widzi i może edytować aktualny zestaw pytań/odpowiedzi,
  - podgląd jest czytelniejszy i bardziej zwarty wizualnie.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-071 (2026-04-14, iPhone: `zdecydowanie` + odstęp `Dalej`)
- `archetypy-ankieta/src/Questionnaire.tsx`:
  - w single-screen etykiety skrajne są łamane jawnie po słowie:
    - `zdecydowanie` / `nie`,
    - `zdecydowanie` / `tak`,
  - etykieta neutralna nadal:
    - `ani tak,`
    - `ani nie`.
- `archetypy-ankieta/src/SingleQuestionnaire.css`:
  - usunięto łamanie typu „dowolny znak”:
    - `word-break: normal`,
    - `overflow-wrap: normal`,
    - `hyphens: none`,
  - dla `max-width:430px` delikatnie dopracowano etykiety (`font-size: 0.64rem`, `line-height: 1.08`),
  - zwiększono odstęp przycisku `Dalej` od paska odpowiedzi w mobile portrait (`margin-top: 30px`).
- Testy techniczne:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Zrobione w Hotfix H-072 (2026-04-14, iPhone: bez dzielenia wyrazów w pytaniu)
- `archetypy-ankieta/src/SingleQuestionnaire.css`:
  - w mobile portrait dla `.single-question-text` wyłączono dzielenie i łamanie wewnątrz słów:
    - `overflow-wrap: normal`,
    - `word-break: normal`,
    - `hyphens: none`.
- Efekt:
  - pytanie główne zawija się wyłącznie między wyrazami (bez `wy-` / `cofywać` itp.).
- Testy techniczne:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Zrobione w Hotfix H-076 (2026-04-14, iPhone: `rozwiązać pokojowo` na twardej spacji)
- `archetypy-ankieta/src/Questionnaire.tsx`:
  - do `PHRASE_GLUE_PATTERNS` dodano frazę:
    - `rozwiązać pokojowo` (klejoną nierozdzielnie twardą spacją).
- Efekt:
  - w problematycznym pytaniu końcówka ma przechodzić w całości, bez rozdzielania `rozwiązać` i `pokojowo`.
- Testy techniczne:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Zrobione w Hotfix H-078 (2026-04-14, poprawa regexu klejenia krótkich słów)
- `archetypy-ankieta/src/Questionnaire.tsx`:
  - poprawiono `SHORT_WORD_GLUE_RE`, aby działał wyłącznie na osobnych słowach (`(^|\\s)...`) zamiast łapać fragmenty końcówki wyrazu przez `\\b`.
  - podmiana krótkich słów realizowana callbackiem:
    - zachowuje prefix (`początek/whitespace`),
    - dokleja NBSP tylko po prawidłowo wykrytym, pełnym krótkim słowie.
- Efekt:
  - usunięty mechanizm, który mógł tworzyć zbyt długie, nierozdzielne bloki i powodować obcinanie końcówki pytania na iPhone.
- Testy techniczne:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Zrobione w Hotfix H-073 (2026-04-14, metryczka paste: format edycyjny + wyższe pole)
- `archetypy-admin/app.py`:
  - panel `📋 Wklej pytanie i odpowiedzi` dostał prefill w formacie:
    - `Pytanie: ...`,
    - `Odpowiedzi:`,
    - numerowane odpowiedzi `1.`, `2.`, `3.` ...,
  - parser czyści teraz także prefiks `Pytanie:`,
  - pole `Wklej treść` zwiększono do `height=260`,
  - lista `Odpowiedzi` w podglądzie ma ciaśniejsze odstępy (`ul/li` inline style).
- Efekt:
  - edycja istniejącego pytania i odpowiedzi jest szybsza i bardziej przewidywalna,
  - obszar edycji jest wygodniejszy przy dłuższych zestawach odpowiedzi,
  - podgląd nie „rozciąga” listy.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-074 (2026-04-14, stopka build: brak `unknown|unknown`)
- `archetypy-admin/app.py` (`_app_build_signature`):
  - rozszerzono fallbacki SHA i czasu o dodatkowe zmienne środowiskowe używane przez różne platformy deploy,
  - dodano awaryjny fallback czasu po `mtime` pliku `app.py`,
  - fallback skrótu commita zmieniono z `unknown` na `local`.
- Efekt:
  - stopka nie powinna już wpadać w stan `build: unknown-time | commit: unknown` przy chwilowej niedostępności GitHub API lub braku `.git`.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-075 (2026-04-14, metryczka paste: bez numeracji w prefill)
- `archetypy-admin/app.py`:
  - usunięto automatyczne dodawanie numerów (`1.`, `2.`, `3.` ...) w prefill pola `Wklej treść`,
  - placeholder pola `Wklej treść` także bez numeracji.
- Efekt:
  - panel `Wklej pytanie i odpowiedzi` pokazuje czysty, prosty tekst odpowiedzi,
  - numeracja pozostaje tam, gdzie powinna (w samym edytorze listy odpowiedzi), a nie w treści do wklejania/edycji.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-077 (2026-04-14, metryczka: zapis kodowania bez podwójnego wpisywania)
- `archetypy-admin/app.py`:
  - wdrożono mechanizm `save intent` dla metryczki (JST + personal):
    - pierwsze kliknięcie `💾 Zapisz metryczkę` ustawia flagę i wymusza rerun,
    - na kolejnym przebiegu wykonywany jest właściwy zapis do DB,
    - dzięki temu ostatnio edytowana komórka `data_editor` jest już zatwierdzona.
- Efekt:
  - zniknął objaw „muszę wpisać kodowanie drugi raz”,
  - jedno zapisanie powinno utrwalać bieżące kodowanie.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-079 (2026-04-14, metryczka: scroll po wklejce + brak nadpisywania kodowania)
- `archetypy-admin/app.py`:
  - dodano mechanizm „powrotu do edytowanego pytania” po `Wstaw`/`Anuluj` w panelu `Wklej pytanie i odpowiedzi`:
    - kotwica HTML per pytanie,
    - zapamiętanie targetu w `session_state`,
    - auto-scroll po rerunie.
  - poprawiono `Wstaw`, aby nie zmieniało kodowania odpowiedzi dla pytań custom:
    - zachowanie kodów po etykiecie,
    - fallback po indeksie,
    - brak wymuszenia `1,2,3...`.
- Efekt:
  - użytkownik nie jest zrzucany na górę strony po operacji wklejki,
  - kodowanie odpowiedzi nie jest nadpisywane przez samą operację `Wklej pytanie i odpowiedzi`.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-080 (2026-04-14, metryczka: stabilizacja `Wstaw`)
- `archetypy-admin/app.py`:
  - przy `Wstaw` kodowanie odpowiedzi jest brane z bieżącego `options` (aktualnie edytowana tabela),
  - usunięto resetujący `_bump_metryczka_editor_nonce(...)` z `Wstaw` i `Anuluj`,
  - auto-scroll po operacji `Wstaw`/`Anuluj` przełączono na `html_component` (pewniejsze wykonanie JS po rerunie).
- Efekt:
  - mniejsze ryzyko utraty świeżo wpisanego kodowania,
  - brak pełnego resetu widgetów metryczki po operacji wklejki,
  - powinien zniknąć skok na górę strony.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-081 (2026-04-14, metryczka: fazowy commit zapisu)
- `archetypy-admin/app.py`:
  - zapis metryczki przeszedł z trybu jednoetapowego intent na tryb fazowy `arm -> commit -> save`,
  - wdrożone równolegle dla JST i personalnych.
- Efekt:
  - większa odporność na przypadek, gdy aktywna komórka `data_editor` nie była jeszcze zatwierdzona w momencie kliku zapisu,
  - redukcja objawu „muszę wpisać kodowanie drugi raz”.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-082 (2026-04-14, metryczka: stabilizacja odpowiedzi + zapisu)
- `archetypy-admin/app.py`:
  - parser tabeli odpowiedzi (`_metryczka_options_from_df`) nie wyrzuca już wierszy tylko dlatego, że kodowanie jest chwilowo puste,
  - scroll-restore po `Wstaw/Anuluj` w panelu wklejki ma retry i fallback hash,
  - wycofano fazowy zapis `arm/commit` — zapis metryczki wrócił do prostego trybu bez dodatkowych rerunów.
- Efekt:
  - po wklejce do nowego pytania odpowiedzi nie „znikają” z tabeli,
  - walidacja zgłasza właściwy problem brakującego kodowania (gdy dotyczy),
  - mniejsze ryzyko utraty świeżego wpisu kodowania przez nadmiarowy rerun flow zapisu.
- Test techniczny:
  - `python -m py_compile app.py` (OK).


### Zrobione w Hotfix H-083 (2026-04-14, metryczka: scroll + zapis kodowania + domyślne kodowanie z odpowiedzi)
- `archetypy-admin/app.py`:
  - przebudowano scroll-restore po rerunach w edytorze metryczki:
    - skrypt szuka kotwicy pytania przez kolejne poziomy `window.parent`,
    - przewija widok przez `scrollTo` (fallback `scrollIntoView`) i powtarza próbę w pętli retry,
  - uproszczono zapis metryczki (JST + personal) do bezpośredniego trybu po kliknięciu `💾 Zapisz metryczkę` (bez dodatkowych faz zapisu),
  - w `Wklej pytanie i odpowiedzi` dla pytań custom:
    - brakujące kodowanie otrzymuje propozycję `kodowanie = treść odpowiedzi`,
    - istniejące kodowania są zachowywane przy możliwym dopasowaniu.
- Efekt:
  - mniej przypadków skoku do góry po `Dodaj pytanie metryczkowe` i `Wstaw`,
  - mniejsze ryzyko "znikania" pierwszego wpisu kodowania przy zapisie,
  - szybsze uzupełnianie kodowania po wklejeniu odpowiedzi.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-084 (2026-04-14, metryczka: układ przycisków akcji)
- `archetypy-admin/app.py`:
  - `➕ Dodaj pytanie metryczkowe` odsunięty od przycisku `📋 Wklej pytanie i odpowiedzi` przez dodatkowy pionowy odstęp (`0.55rem`),
  - `💾 Zapisz metryczkę` przeniesiony wizualnie na prawą stronę (layout kolumnowy) w:
    - `jst_metryczka_view`,
    - `personal_metryczka_view`.
- Efekt:
  - przyciski wykonawcze są ustawione bardziej logicznie (główna akcja po prawej),
  - większa czytelność sekcji końca edytora metryczki.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-085 (2026-04-14, metryczka: stabilizacja pozostawania na edytowanym pytaniu)
- `archetypy-admin/app.py`:
  - dodano nonce scrolla (`_metryczka_scroll_nonce_key`) i ustawianie go przy:
    - `Wstaw`,
    - `Anuluj`,
    - `➕ Dodaj pytanie metryczkowe`,
  - scroll-restore renderowany z unikalnym kluczem komponentu (`key=...scroll_restore_{nonce}`), co wymusza jego świeże wykonanie,
  - logika scroll-restoru rozszerzona o przewijanie nie tylko `window`, ale też kontenerów przewijania Streamlit.
- Efekt:
  - znacząco mniejsze ryzyko skoku do `1. M_PLEC` po edycji pytania niżej na liście (np. `7. M_POGLADY`).
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-086 (2026-04-14, metryczka: usunięcie błędu `html_component(..., key=...)`)
- `archetypy-admin/app.py`:
  - usunięto parametr `key` z wywołania `html_component(...)` w scroll-restore metryczki (nieobsługiwany w środowisku produkcyjnym Streamlit),
  - zostawiono nonce (`runId`) w treści skryptu, by zachować unikalność uruchomienia scroll-restoru.
- Efekt:
  - znika błąd `TypeError: IframeMixin._html() got an unexpected keyword argument 'key'`,
  - flow `Wstaw`/`Dodaj` nie przerywa się wyjątkiem.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-087 (2026-04-14, metryczka: fallback scrolla po `Wstaw`)
- `archetypy-admin/app.py`:
  - do istniejącego scroll-restoru przez `html_component` dołożono drugi fallback przez `st.markdown(<script>, unsafe_allow_html=True)`,
  - fallback szuka kotwicy pytania w bieżącym dokumencie i przewija:
    - `window`,
    - oraz typowe przewijalne kontenery Streamlit,
  - ustawia hash kotwicy, by utrzymać pozycję także przy kolejnych akcjach na tym samym pytaniu.
- Efekt:
  - wyraźnie większa odporność na przypadek „po `Wstaw` wraca do `1. M_PLEC`”.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-088 (2026-04-14, runtime metryczki + mapowanie import/raport)
- `archetypy-ankieta/src/lib/metryczka.ts`:
  - dodano wspólny model i normalizator metryczki (`core + custom`) na frontend,
  - helpery do budowania payloadu (`db_column -> code`) i obsługi `M_ZAWOD = inna (jaka?)`.
- `archetypy-ankieta/src/JstSurvey.tsx`:
  - metryczka jest renderowana dynamicznie z `study.metryczka_config`,
  - walidacja metryczki działa po konfiguracji (`required`) + walidacja doprecyzowania `M_ZAWOD_OTHER`,
  - zapis do `add_jst_response_by_slug` zawiera:
    - odpowiedzi core/custom jako mapę `db_column -> code`,
    - `M_ZAWOD_OTHER` (jeśli dotyczy).
- `archetypy-ankieta/src/Questionnaire.tsx`:
  - dodano krok metryczki po ekranie powitalnym i przed pytaniami właściwymi (niezależnie od trybu matrix/single),
  - metryczka personalna zapisuje się wraz z odpowiedziami przez `p_scores: { metryczka: ... }`,
  - tryb single-screen działa tylko dla pytań właściwych; metryczka jest osobnym etapem.
- `archetypy-ankieta/src/lib/studies.ts` + `src/lib/jstStudies.ts`:
  - rozszerzono typy/odczyt o `metryczka_config` i `metryczka_config_version`.
- `archetypy-admin/db_jst_utils.py`:
  - dodano dynamiczne kolumny odpowiedzi `response_columns(...)` = kanoniczne + custom z configu,
  - `normalize_response_row(...)` obsługuje teraz `metryczka_config` (mapowanie kodowania dla core/custom),
  - `response_rows_to_dataframe(...)` i `make_payload_from_row(...)` przyjmują config i zachowują custom kolumny.
- `archetypy-admin/app.py`:
  - `jst_io_view` (import/eksport) przekazuje `study.metryczka_config` do normalizacji i zapisu payloadu,
  - `jst_analysis_view` generuje raport na pełnym dataframe (kanoniczne + custom), bez obcinania do stałego zestawu.
- Testy techniczne:
  - `python -m py_compile app.py db_jst_utils.py metryczka_config.py` (OK),
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Zrobione w Hotfix H-089 (2026-04-14, UI metryczki personalnej zbliżone do JST)
- `archetypy-ankieta/src/Questionnaire.tsx`:
  - sekcja metryczki personalnej została przebudowana z układu „siatkowych kafelków” na układ blokowy:
    - pytanie jako osobna sekcja,
    - odpowiedzi jako pionowa lista opcji (jak w JST),
    - zachowane radio-marki i walidacja,
    - zachowana obsługa pola doprecyzowania `M_ZAWOD_OTHER`.
- `archetypy-ankieta/src/SingleQuestionnaire.css`:
  - dodano dedykowane style `pm-metry-*` dla personalnej metryczki,
  - zaznaczenia opcji i przycisk `Przejdź dalej` mają niebieski akcent (zgodnie z wymaganiem),
  - dodano responsywne dopracowanie dla mobile.
- Testy techniczne:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Zrobione w Hotfix H-090 (2026-04-14, Punkt 3+4: profile demograficzne + segmenty matching)
- `archetypy-admin/admin_dashboard.py`:
  - `load(...)` pobiera teraz również `scores` z tabeli `responses` i parsuje je do dict,
  - dodano helpery do obsługi metryczki personalnej z `scores.metryczka`:
    - `_extract_personal_metry_payload(...)`,
    - `_build_personal_metry_questions(...)`,
    - `_metry_value_label(...)`,
  - w `show_report(...)` dodano sekcję:
    `👥 Profile demograficzne (filtr wielocechowy + radar)`
    - filtr wielocechowy (AND) oparty o `metryczka_config` badania,
    - liczebność podgrupy i próg minimalnego N,
    - ostrzeżenie o niepewności dla małych podgrup,
    - radar porównawczy: cała próba vs podgrupa filtrowana (skala 0-20).
- `archetypy-admin/app.py` (`🧭 Matching`):
  - dodano nową zakładkę `Segmenty` obok `Podsumowanie / Demografia / Strategia komunikacji`,
  - dodano helper `_load_matching_segment_profiles(...)` (odczyt `SEGMENTY_ULTRA_PREMIUM_profile.csv` z katalogu runa JST),
  - tabela segmentów w Matching liczy porównanie na tej samej skali 12 archetypów:
    - `Śr. luka |Δ| (pp)` oraz `Zgodność (%) = 100 - MAE`,
  - dodano kontrolę wiarygodności:
    - `Minimalna liczebność segmentu (N)`,
    - oznaczenie `Niepewne` i komunikaty ostrzegawcze dla segmentów poniżej progu,
  - dodano radar polityk vs wybrany segment.
- Test techniczny:
  - `python -m py_compile app.py admin_dashboard.py` (OK).

### Zrobione w Hotfix H-091 (2026-04-14, segmenty: metodologia + profil demograficzny segmentu)
- `archetypy-admin/app.py`:
  - rozszerzono normalizację metryczki (`_canon_demo_value`) o pola:
    - `M_WYKSZT`,
    - `M_ZAWOD`,
    - `M_MATERIAL`,
  - dodano loader przypisań respondentów do segmentów:
    - `_load_matching_segment_membership(...)` -> plik `respondenci_segmenty_ultra_premium.csv`,
  - w `matching_result` zapisujemy teraz `jst_demo_vectors` (`respondent_id`, `payload`, `weight`), a `_calc_jst_target_profile(...)` przenosi `respondent_id` do `respondent_vectors`,
  - w `🧭 Matching > Segmenty`:
    - dodano jawne objaśnienie metody:
      `Zgodność (%) = 100 - średnia luka |Δ|` dla pojedynczego segmentu,
      bez dodatkowych kar strategicznych z `Poziomu dopasowania`,
    - pod radarami dodano sekcje:
      - `📌 STATYSTYCZNY PROFIL DEMOGRAFICZNY SEGMENTU` (karty top kategorii + najsilniejsza nadreprezentacja),
      - `👥 PROFIL DEMOGRAFICZNY SEGMENTU` (tabela `% segment` vs `% ogół mieszkańców (ważony)` + różnica w pp),
    - profil segmentu liczony jest z mapowania `respondent_id -> segment` i metryczki respondentów JST, z wagowaniem poststratyfikacyjnym (jeśli aktywne),
    - dodano notę o pokryciu mapowania segmentów względem bieżącej próby JST.
- Test techniczny:
  - `python -m py_compile app.py admin_dashboard.py` (OK).

### Zrobione w Hotfix H-092 (2026-04-14, segmenty: metryka strategiczna zamiast `100-MAE`)
- `archetypy-admin/app.py` (`🧭 Matching > Segmenty`):
  - zmieniono wyliczanie `Zgodność (%)` dla segmentów:
    - było: `100 - MAE`,
    - jest: metryka strategiczna jak w `Podsumowaniu` (`MAE + RMSE + TOP3_MAE + KEY_MAE` oraz kary kluczowe),
  - dodano lokalne helpery:
    - `_segment_priority_pool(...)` (TOP2/TOP3 z progiem 70),
    - `_segment_strategic_score(...)` (finalny `match_pct` + metryki pomocnicze),
  - zaktualizowano opisy metodologii:
    - górny opis zakładki Segmenty,
    - podpis pod radarem (metoda strategiczna, nie `100-MAE`),
  - utrzymano stałe formatowanie 1 miejsca po przecinku dla:
    - `Udział (%)`,
    - `Śr. luka |Δ| (pp)`,
    - `Zgodność (%)`,
    oraz komunikatów/etykiet segmentu.
- Efekt:
  - znikają zawyżone wyniki zgodności wynikające z prostego `100-MAE`,
  - porównanie Segmentów jest spójne metodycznie z `Podsumowaniem`.
- Test techniczny:
  - `python -m py_compile app.py admin_dashboard.py` (OK).

### Zrobione w Hotfix H-093 (2026-04-14, segmenty: key-focused + panel górny + legenda radaru)
- `archetypy-admin/app.py` (`🧭 Matching > Segmenty`):
  - metryka zgodności segmentu została przestawiona na wariant key-focused:
    - kluczowa pula = `TOP5 polityka + TOP5 segmentu`,
    - baza finalna = `0.25*base_global + 0.75*base_key`,
    - kary TOP3/TOP2 (shared TOP + mismatch TOP1 + KEY luki) wzmocnione względem poprzedniej wersji segmentowej,
  - tabela segmentów pokazuje teraz:
    - `Śr. luka kluczowa |Δ| (pp)`,
    - `Zgodność (%)` z nowej metryki key-focused.
  - na górze zakładki Segmenty dodano panel:
    - selektor segmentu,
    - „Dla kogo liczona jest segmentacja” (personal + JST),
    - „Poziom zgodności wybranego segmentu” (duży % + ocena + pasek 0-100).
  - poprawiono legendę nad radarem:
    - usunięte sztywne `entrywidth`,
    - uproszczone etykiety legendy (bez sztucznych spacji), co zmniejsza obcinanie nazw.
  - zachowane i dopięte formatowanie do 1 miejsca po przecinku dla:
    - `Udział (%)`,
    - `Śr. luka kluczowa |Δ| (pp)`,
    - `Zgodność (%)`.
- Test techniczny:
  - `python -m py_compile app.py admin_dashboard.py` (OK).

### Zrobione w Hotfix H-094 (2026-04-14, segmenty: TOP6 + złagodzenie kar + szersza legenda)
- `archetypy-admin/app.py` (`🧭 Matching > Segmenty`):
  - segmentowa pula kluczowa zmieniona na `TOP6 polityka + TOP6 segmentu` (zamiast TOP5),
  - złagodzono agresywność kar, które powodowały częste zjazdy do `0,0%`:
    - niższa kara za rozjazd TOP1,
    - niższa kara za brak/wąską część wspólną TOP,
    - słabsza kara liniowa od `KEY_MAE` i od `KEY_MAX`,
  - miks bazowy zmieniono na mniej skrajny (`35% global`, `65% key`) zamiast silniejszego dociążenia key.
  - legenda nad radarem:
    - zastąpiona szeroką legendą HTML (`match-seg-radar-legend`),
    - wyłączona legenda Plotly dla radaru segmentowego (żeby uniknąć obcinania etykiet).
  - podpis metody pod radarem zaktualizowany do `TOP6 + TOP6` i nowego miksu wag.
- Test techniczny:
  - `python -m py_compile app.py admin_dashboard.py` (OK).

### Zrobione w Hotfix H-095 (2026-04-14, dynamiczna metryczka: Matching + biblioteka pytań + generator JST)
- `archetypy-admin/db_jst_utils.py`:
  - rozszerzono `ensure_jst_schema()` o tabelę `public.metryczka_question_templates` (z indeksem),
  - dodano helpery:
    - `list_metryczka_question_templates(...)`,
    - `save_metryczka_question_template(...)`.
- `archetypy-admin/app.py`:
  - edytor metryczki (`_render_metryczka_editor`):
    - przy pytaniu dodatkowym można zapisać szablon pytania (`💾 Zapisz do zapisanych`),
    - na dole dodano panel `📚 Wybierz z zapisanych` z możliwością wstawienia zapisanego pytania do bieżącej metryczki,
  - Matching:
    - dodano dynamiczne helpery demograficzne (`_matching_demo_build_specs`, `_matching_demo_build_rows`, itd.),
    - zakładka `Demografia` oraz demografia `Segmentów` przeszły z hardcoded 5 pól na dynamiczne `metryczka_config` (rdzeń + custom `M_*`),
    - zachowano noty o wagowaniu i pokryciu mapowania.
- `archetypy-admin/JST_Archetypy_Analiza/analyze_poznan_archetypes.py`:
  - `parse_metryczka(...)` zachowuje dodatkowe kolumny `M_*`,
  - `_onehot_metry(...)` i funkcje tabel demograficznych liczą po dynamicznej liście kolumn `M_*`,
  - payload demografii (`var_order/cat_order`) jest budowany dynamicznie.
- Test techniczny:
  - `python -m py_compile app.py db_jst_utils.py JST_Archetypy_Analiza/analyze_poznan_archetypes.py` (OK).

### Zrobione w Hotfix H-096 (2026-04-14, segmenty: suwak siły kar + 100% bazy z puli kluczowej)
- `archetypy-admin/app.py` (`🧭 Matching > Segmenty`):
  - dodano kontrolkę `Siła kar segmentowych` (`łagodna` / `standard` / `ostra`) obok progu `N` i przełącznika wiarygodności,
  - profil kar jest teraz parametryzowany (`penalty_profiles`) i wpływa na:
    - karę od średniej luki kluczowej,
    - karę od maksymalnej luki kluczowej,
    - karę za brak wspólnych priorytetów,
    - karę za rozjazd TOP1,
  - baza wyniku segmentowego została przestawiona na `100% key-pool`:
    - `base_score = base_key` (TOP6 polityka + TOP6 segmentu),
    - bez domieszki `base_global` z pełnych 12 archetypów,
  - zaktualizowano opisy metodologii (górny opis i podpis pod radarem), aby jasno komunikowały nową logikę.
- Test techniczny:
  - `python -m py_compile app.py` (OK).

### Zrobione w Hotfix H-097 (2026-04-14, generator JST custom M_* + pamięć siły kar per badanie)
- `archetypy-admin/JST_Archetypy_Analiza/analyze_poznan_archetypes.py`:
  - dodano wspólną warstwę metadanych demografii:
    - dynamiczne `var_order` i `cat_order`,
    - mapy ikon `var_icons` i `cat_icons` z fallbackami heurystycznymi dla custom `M_*`,
  - `extras` metryczki zachowują kolejność wejściową kolumn (`_ordered_metry_columns`), zamiast sortowania alfabetycznego,
  - sekcja kart segmentów (`_render_demo_table`) renderuje wszystkie dostępne zmienne/kategorie demograficzne (nie tylko stałą piątkę),
  - panel `Demografia_Seg` buduje porządek i ikony dynamicznie na podstawie realnych danych,
  - payloady `B2 declared` i `TOP5 simulation` niosą dynamiczne:
    - `var_order`,
    - `cat_order`,
    - `var_icons`,
    - `cat_icons`,
  - frontend JS w panelach `B2` i `TOP5` czyta mapy ikon z payloadu zamiast statycznych słowników.
- `archetypy-admin/db_jst_utils.py`:
  - schema `jst_studies` rozszerzona o:
    - `matching_segments_penalty_strength TEXT NOT NULL DEFAULT 'standard'`,
    - constraint wartości: `łagodna | standard | ostra`,
  - dodano normalizator `normalize_matching_segments_penalty_strength(...)`,
  - fetch/insert/update badania JST normalizują i zwracają to pole.
- `archetypy-admin/app.py` (`🧭 Matching > Segmenty`):
  - suwak `Siła kar segmentowych` został spięty z trwałym zapisem per badanie JST (`jst_study_id`),
  - wartość startowa jest odczytywana z DB, a zmiana suwaka zapisuje się przez `update_jst_study(...)`,
  - klucz widgetu zmieniono na per-JST:
    - `matching_segments_penalty_strength_{jst_sid}`.
- Test techniczny:
  - `python -m py_compile app.py db_jst_utils.py JST_Archetypy_Analiza/analyze_poznan_archetypes.py` (OK).

### Zrobione w Hotfix H-100 (2026-04-14, raport personalny: przycisk demografii + czysty widok + selektory cech)
- `archetypy-admin/app.py` (`results_view`):
  - przeniesiono przycisk `👥 Raport demograficzny` do górnego rzędu (przed quicknav),
  - usunięto dolny przycisk pod selectem,
  - otwieranie podstrony demograficznej jest spięte z aktualnie wybraną osobą.
- `archetypy-admin/admin_dashboard.py`:
  - gdy aktywna podstrona demograficzna (`personal_demo_page_*`), nie renderuje się blok nagłówka:
    - niebieski banner `Archetypy ... – panel administratora`,
    - kafel liczby uczestników,
    - separator pod tym blokiem,
  - filtry `FILTR WIELOCECHOWY` przebudowano z `multiselect` na `selectbox` (single-select) z opcją `— brak filtra —`,
  - zachowano logikę AND między aktywnymi cechami.
- Test techniczny:
  - `python -m py_compile app.py admin_dashboard.py` (OK).

### Zrobione w Hotfix H-101 (2026-04-14, fix NameError w predefiniowanych metryczkach)
- `archetypy-admin/db_jst_utils.py`:
  - dodano brakujący helper `_bool_from_any(...)` (parsowanie bool z różnych formatów),
  - normalizacja pytań predefiniowanych (`_normalize_template_question_payload`) ma już komplet zależności dla pól:
    - `is_open`,
    - `randomize_options`,
    - `randomize_exclude_last`.
- Efekt:
  - kliknięcie `Predefiniowane metryczki` nie kończy się błędem `NameError`.
- Test techniczny:
  - `python -m py_compile db_jst_utils.py app.py` (OK).
