# PLANS.md

## Plan etapow naprawczych

### Krok 1 [DONE]
Temat: Poprawnosc ponownej wysylki SMS dla JST + blokada wielokrotnego wypelnienia ankiety po zakonczeniu.
Zakres:
- `send_link_jst.py` (ponowna wysylka "ten sam link"),
- logika walidacji tokenu i finalizacji wypelnienia (repo `archetypy-admin` i/lub `../archetypy-ankieta` - po potwierdzeniu miejsca wykonania).
Kryteria ukonczenia:
1. Ponowna wysylka SMS zawsze odnosi sie do JST przypisanej do tokenu/rekordu.
2. Token po pelnym zakonczeniu ankiety nie pozwala na ponowne wypelnienie.
3. Komunikat blokady zawiera kanal: `adres e-mail` albo `numer telefonu`.
4. E-mail flow pozostaje bez regresji.
5. Smoke-test scenariusza SMS i e-mail opisany w `STATUS.md`.
Wynik:
- Kryteria 1-5 zrealizowane w kodzie (backend + frontend) i sprawdzone buildem Python/TS.

### Krok 1A [DONE]
Temat: Dogrywka po testach uzytkownika (ankieta JST).
Zakres:
- obowiazkowe pole tekstowe dla opcji `M_ZAWOD = "inna (jaka?)"`,
- blokada ponownego wejscia tokenem takze po statusie `rejected` (`Nie spelnia`).
Kryteria ukonczenia:
1. Po wyborze `inna (jaka?)` pojawia sie pole tekstowe.
2. Bez uzupelnienia pola nie mozna przejsc dalej.
3. Po `completed` i po `rejected` kolejne wejscie tym samym tokenem jest blokowane.
4. Komunikat blokady pozostaje kontekstowy (`numer telefonu` / `adres e-mail`).
Wynik:
- Kryteria 1-4 zrealizowane i sprawdzone buildem frontendu + kompilacja Python.

### Krok 1B [DONE]
Temat: Dogrywka po kolejnym tescie uzytkownika (wysylka e-mail + UX formularza + stopka build).
Zakres:
- resend e-mail ma zawsze byc zgodny z JST rekordu (bez przecieku tresci/sluga z innego badania),
- stopka `build` ma pokazywac date ostatniego commita zamiast `commit: local`,
- metryczka: brak ukrywania "wypelnionych" sekcji po bledzie oraz stabilna walidacja `inna (jaka?)`.
Kryteria ukonczenia:
1. Ponowiona wysylka e-mail dla wybranego JST wysyla poprawna nazwe JST i poprawny link.
2. Stopka pokazuje hash i date ostatniego commita (jesli repo git dostepne).
3. Po bledzie walidacji respondent nie widzi pustego ekranu.
4. `inna (jaka?)` wymaga sensownego doprecyzowania (nie tylko 1 znak).
Wynik:
- Kryteria 1-4 zrealizowane i sprawdzone buildem Python/TS.

### Krok 2 [DONE]
Temat: Demografia w `🧭 Matching` ma byc wizualnie 1:1 jak `Demografia priorytetu (B2)`.
Kryteria ukonczenia:
1. Te same style kart i tabel, fonty, kolory, spacing, grube naglowki.
2. Brak utraty danych przy poszerzeniu kontenera.
3. Potwierdzenie porownawcze na zrzutach.
Wynik:
- Sekcja `Matching > Demografia` korzysta z layoutu i stylu B2 (karty + tabela),
  z poszerzonym wrapperem tabeli (`max-width:100%`) i zachowaniem danych.
- Smoke-check skladni `python -m py_compile app.py` przeszedl poprawnie.
- Iteracja dopieszczajaca (po uwagach usera):
  - dodane obramowane boksy sekcji (jak w B2),
  - uszczelniona typografia i obramowania tabeli (`font-size`, prawa krawedz, naglowki),
  - wrapper tabeli ustawiony jak w B2 (`max-width:940px`).
- Iteracja metodyczna:
  - tabela demografii w Matching liczona po wagach poststratyfikacyjnych (plec × wiek), jesli wagi sa zdefiniowane dla JST,
  - dynamiczny naglowek kolumny referencyjnej: `{nazwa JST} / (po wagowaniu)`,
  - zmiana etykiety kolumny roznicy na `Róznica (w pp.)` i stylu wartosci na normalna czcionke.
- Finalne dopieszczenie typografii:
  - naglowki kart `📌 ...` i `👥 ...` wieksze,
  - `STATYSTYCZNY PROFIL DEMOGRAFICZNY`: wartosci `xx.x% • yy.y pp` zwiekszone do `12.5px`,
  - naglowki kart typu `💰 SYTUACJA MATERIALNA` zwiekszone do `12px`,
  - tabela `Profil demograficzny` ustawiona na `13.5px`.

### Krok 3 [DONE]
Temat: Usuniecie pustych wierszy koncowych w tabelach panelu i Matching.
Kryteria ukonczenia:
1. Po ostatnim rekordzie brak sztucznych pustych linii.
2. Dotyczy `Badania mieszkancow - panel` i `🧭 Matching / Podsumowanie`.
Wynik:
- `Badania mieszkancow - panel`: wysokosc tabeli ustawiana ciasno do liczby rekordow (bez pustych koncowych wierszy).
- `🧭 Matching / Podsumowanie`: wysokosc tabeli porownawczej ustawiana ciasno do liczby archetypow (bez pustych koncowych wierszy).
- Smoke-check skladni `python -m py_compile app.py` przeszedl poprawnie.

### Krok 4 [DONE]
Temat: Spojnosc metryk i formatow liczbowych.
Zakres:
- dopisek `Raport: Archetypy - {JST} (N=...)`,
- stale 1 miejsce po przecinku dla: `Oczekiwania mieszkancow (%)`, `Roznica`, `Profil polityka`,
- precyzyjny opis i audyt liczenia komponentow A/B1/B2/D13.
Kryteria ukonczenia:
1. Jednoznaczna formula opisana i zgodna z implementacja.
2. Wartosci zawsze wyswietlane jako `x.y`.
3. Roznica miedzy raportem a surowymi danymi wyjasniona lub usunieta.
Pierwszy krok wykonawczy:
- zmapowac miejsca renderu tytulu raportu i tabeli `Matching / Podsumowanie` oraz audytowac implementacje `_calc_jst_target_profile`.
Wynik:
- `Raport: Archetypy – {JST} (N=...)` dodane w generatorze HTML raportu JST.
- W `🧭 Matching / Podsumowanie` kolumny:
  - `Profil polityka (%)`,
  - `Oczekiwania mieszkańców (%)`,
  - `Różnica |Δ|`
  sa renderowane zawsze z 1 miejscem po przecinku (`x.y`).
- W `Jak liczony jest poziom dopasowania?` dodano:
  - precyzyjny opis przeliczenia komponentu A (1–7 -> udział lewy/prawy),
  - pelna formule A/B1/B2/D13,
  - audyt pokrycia danych i tabele srednich skladowych dla archetypow.
- Synchronizacja generatora raportu dla istniejacych runow:
  `jst_analysis.py` odswieza `analyze_poznan_archetypes.py` w katalogu run przed uruchomieniem.

### Krok 5 [DONE]
Temat: Nowa metryka `Poziom dopasowania` + lepsza prezentacja informacji o dopasowaniach.
Kryteria ukonczenia:
1. Metryka nie zawyza wyniku przy duzych roznicach archetypow.
2. Uzasadnienie matematyczne zapisane w `DECISIONS.md`.
3. Sekcja dopasowan ma czytelny, nowoczesny UX.
Pierwszy krok wykonawczy:
- zamienic wzor `100 - MAE` na metryke mieszana (MAE + RMSE + kara za TOP3 luki) i przebudowac panel informacji o dopasowaniach.
Wynik:
- `Poziom dopasowania` liczony metryka mieszana:
  `0.40*(100-MAE) + 0.25*(100-RMSE) + 0.35*(100-TOP3_MAE)`, z ograniczeniem do zakresu `0..100`.
- Dodano czytelny panel diagnostyczny metryki:
  - MAE, RMSE, TOP3 luk (w pp),
  - opis pasma oceny dopasowania.
- Przebudowano sekcje dopasowan:
  - `Najlepsze dopasowania` i `Największe luki` jako wizualne boksy/chipy z konkretnym `|Δ|`.
- Opis wzoru i uzasadnienie metodyczne zapisane w `DECISIONS.md`.
- Smoke-check skladni `python -m py_compile app.py` przeszedl poprawnie.

### Krok 6 [DONE]
Temat: Audyt i korekta agregacji pytan (TOP3/TOP1 i pozostale).
Kryteria ukonczenia:
1. Suma wskazan w raportach zgadza sie z baza.
2. Obowiazkowe pytania maja pelna liczbe odpowiedzi (o ile brakow danych faktycznie nie ma).
3. Wynik audytu wszystkich pytan opisany w `STATUS.md`.
Pierwszy krok wykonawczy:
- zmapowac wszystkie agregacje raportowe i porownac ich sumy z wartosciami liczonymi bezposrednio z danych surowych.
Wynik:
- Naprawiono liczniki `TOP3/TOP1`:
  - kolumna `liczba` w `B1_top3.csv`, `B2_top1.csv` i tabeli `B1_trojki.csv` jest liczona surowo (bez wag), 1:1 z baza,
  - kolumna `%` pozostaje liczona na wagach.
- Uodporniono parser:
  - B1 akceptuje dodatkowe formaty flag (`1.0`, dodatnie liczby, warianty bool),
  - parser archetypu dla `B2/D13` obsluguje tez formaty numeryczne (`1..12`, `0..11`, `nr 1`).
- Dodano automatyczny audyt agregacji wszystkich pytan:
  - plik `WYNIKI/question_aggregation_audit.csv`,
  - obejmuje `A1..A18`, `B1`, `B2`, `D13` i raportuje `expected_raw`, `reported_raw`, `delta`.
- Dla danych Poznania po poprawce:
  - `TOP3` suma wskazan = `2741` (zgodna z baza),
  - `TOP1` suma wskazan = `1050` (zgodna z baza),
  - audyt pytan: `delta = 0` dla wszystkich pytan.
- Smoke-check:
  - `python -m py_compile JST_Archetypy_Analiza/analyze_poznan_archetypes.py jst_analysis.py app.py` (OK),
  - pelny run generatora na danych Poznania (OK).

### Krok 7 [DONE]
Temat: Porownania profili polityk vs mieszkancy (obok siebie + radar nakladany).
Kryteria ukonczenia:
1. Dwa profile 0-100 obok siebie.
2. Opcjonalny radar 0-20 na jednym wykresie (polityk + JST) z rozroznionymi kolorami kluczowych archetypow.
3. Czytelna legenda i brak konfliktu stylow.
Pierwszy krok wykonawczy:
- zlokalizowac render profilu polityka (0-100 i 0-20) oraz dodac zasilenie profilem JST dla wybranego badania mieszkancow.
Wynik:
- W `📊 Sprawdz wyniki badania archetypu` dodano selektor:
  `Porownaj z badaniem mieszkancow (JST)` z domyslnym dopasowaniem do miasta polityka (jesli znalezione).
- Radar 0-20 dziala w trybie nakladanym:
  - profil polityka + profil mieszkancow na jednym wykresie,
  - osobne kolory TOP3 dla polityka i mieszkancow,
  - legenda rozdzielajaca oba zestawy TOP3 oraz linie porownawcze.
- Sekcja `Profil archetypowy ... (skala: 0-100)` ma tryb porownawczy:
  - dwa kola obok siebie (polityk vs mieszkancy JST),
  - podpis JST z liczebnoscia `N`.
- Wyliczenie profilu JST w tym widoku bazuje na tej samej metodzie A/B1/B2/D13 co w Matching.
- Smoke-check skladni:
  - `python -m py_compile admin_dashboard.py app.py` (OK).

### Krok 8 [DONE]
Temat: Stabilnosc eksportu HTML/ZIP, osadzanie zasobow, fonty i UX pobierania.
Zakres:
- poprawa dzialania standalone HTML (albo jasne wymuszenie ZIP),
- osadzanie obrazow po wylaczeniu trybu lekkiego,
- fonty wykresow zgodne z wzorcem,
- overlay pobierania z loaderem/komunikatem.
Kryteria ukonczenia:
1. Uzytkownik wie, co pobrac i dlaczego.
2. Brak "szarego zawieszenia" bez informacji.
3. Raporty lokalne i online maja spojny wyglad.
Pierwszy krok wykonawczy:
- przeaudytowac aktualny pipeline renderu/eksportu w `app.py` i `jst_analysis.py` (inline assets, przyciski pobierania, tryb lekki) oraz wskazac minimalny zestaw zmian kodu, ktory domyka wszystkie 4 punkty.
Wynik:
- `app.py` (`jst_analysis_view`):
  - dodano polityke bezpiecznego exportu standalone HTML:
    - przycisk `📥 Pobierz raport HTML (pełny)` jest aktywny tylko wtedy, gdy jednoplikowy HTML z osadzonymi zasobami miesci sie w limicie (`JST_REPORT_STANDALONE_HTML_LIMIT_BYTES`, domyslnie 85 MB),
    - dla raportow zbyt ciezkich UI pokazuje jasny komunikat i rekomenduje ZIP (bez mylacego pobierania "samego HTML"),
  - oba przyciski pobierania raportu (`HTML`, `ZIP`) maja `on_click=\"ignore\"`, co eliminuje rerun i efekt szarego "zawieszenia" po kliknieciu,
  - `Podgląd raportu online` po wylaczeniu `Tryb lekki renderowania` probuje on-demand osadzic zasoby (`inline_local_assets`) i:
    - renderuje wersje pelna, gdy miesci sie w limicie,
    - albo pokazuje jednoznaczny komunikat, gdy pelny podglad jest zbyt duzy / osadzanie sie nie udalo.
- `app.py`:
  - dodano helper `_fmt_bytes_compact(...)` do czytelnych komunikatow o rozmiarach.
- `JST_Archetypy_Analiza/analyze_poznan_archetypes.py`:
  - dodano deterministyczny wybor fontu (repo -> system) przez rejestracje fontow z plikow,
  - `set_global_fonts()` korzysta teraz z `_pick_base_font()` i listy `font.sans-serif` dla spojnosci renderu PNG.
- `assets/fonts/`:
  - dodano `segoeui.ttf` i `segoeuib.ttf`, aby wyrownac wyglad wykresow miedzy srodowiskami.
- Smoke-check:
  - `python -m py_compile app.py jst_analysis.py JST_Archetypy_Analiza/analyze_poznan_archetypes.py` (OK).

### Hotfix H-001 [DONE]
Temat: Regresja stopki build na Windows (`unknown-time | local`).
Kryteria ukonczenia:
1. Stopka pobiera hash i date commita rowniez na Windows.
2. Brak twardej sciezki linuksowej do `git`.
Wynik:
- `app.py` korzysta z wykrywania `git` przez `shutil.which("git")` (fallback `git`),
  zamiast sztywnego `/usr/bin/git`.
- Smoke-check:
  - `python -m py_compile app.py` (OK),
  - `git rev-parse` + `git show --format=%cI` zwracaja poprawne dane w repo.

### Hotfix H-002 [DONE]
Temat: Korekta lokalizacji funkcji z Kroku 7 (porownanie profili ma byc w `🧭 Matching`, nie w `📊 Sprawdz wyniki`).
Kryteria ukonczenia:
1. `📊 Sprawdz wyniki badania archetypu` wraca do wersji sprzed dodatkow kroku 7.
2. Porownanie profili 0-100 oraz radar nakladany 0-20 dzialaja w `🧭 Matching`.
3. Brak regresji w kompilacji (`py_compile`).
Pierwszy krok wykonawczy:
- cofnac dodatki kroku 7 z `admin_dashboard.py` i odtworzyc poprzedni render profilu.
Wynik:
- `admin_dashboard.py`:
  - usunieto dodatki kroku 7 z widoku `📊 Sprawdz wyniki badania archetypu`,
  - przywrocono poprzedni radar i pojedynczy profil 0-100 bez porownania JST.
- `app.py` (`matching_view`, zakladka `Podsumowanie`):
  - dodano radar nakladany 0-20: polityk vs mieszkancy JST,
  - dodano rozdzielone kolory TOP3 dla polityka i mieszkancow + legende,
  - dodano profile 0-100 obok siebie:
    `Profil archetypowy {osoba}` i `Profil archetypowy mieszkancow {JST}`.
- Smoke-check:
  - `python -m py_compile app.py admin_dashboard.py` (OK).

### Hotfix H-003 [DONE]
Temat: Stopka build na deployu pokazywala `unknown-time | local` mimo aktualnych commitow na GitHub.
Kryteria ukonczenia:
1. Stopka pobiera poprawna date i hash takze gdy runtime nie ma `.git`.
2. Dziala fallback na metadane z GitHub (repo/branch).
Wynik:
- `app.py`:
  - dodano wielopoziomowy fallback metadanych build:
    - env/secrets (`*_COMMIT_SHA`, `*_COMMIT_TIME`),
    - lokalny git (jesli dostepny),
    - `DEPLOYED_SHA` / `.deployed_sha`,
    - GitHub API (`repos/{repo}/commits/{branch}`) z cache.
  - commit time jest konwertowany do `Europe/Warsaw` przed wyswietleniem.
  - gdy hash jest znany, stopka pokazuje `commit: <sha8>` zamiast `local`.
- Smoke-check:
  - `python -m py_compile app.py` (OK),
  - test API: `stecpiotr/archetypy-admin/main` zwraca SHA i date commita.

### Hotfix H-004 [DONE]
Temat: Regresja w `🧭 Matching` (wykres porownawczy + brak zestawienia profili) oraz niespojnosc TOP3/TOP1 w nowo generowanym raporcie.
Kryteria ukonczenia:
1. W `Matching` znika blad renderu obrazu (`use_container_width`) i wykresy sa poprawnie wyswietlane.
2. W `Matching` sekcja zestawienia profili (0-100 obok siebie) jest renderowana stabilnie.
3. Nowo wygenerowany raport dla Poznania ma zgodne sumy:
   - `TOP3 liczba = 2741`,
   - `TOP1 liczba = 1050`.
4. Potwierdzenie techniczne (kompilacja + test generacji) opisane w `STATUS.md`.
Pierwszy krok wykonawczy:
- zlokalizowac miejsca renderu wykresow w `app.py` i tor generacji `B1_top3/B2_top1` w `jst_analysis.py` + `analyze_poznan_archetypes.py`, a potem wykonac minimalne poprawki i rerun kontrolny.
Wynik:
- `app.py`:
  - usunieto konflikt renderu `st.image(..., use_container_width=True)` przez fallback kompatybilny ze starszym Streamlit (`use_column_width=True`),
  - dzieki temu sekcja porownania profili 0-100 w `🧭 Matching` renderuje sie bez wyjatku,
  - uproszczono legende wykresu radar (bez nakladania domyslnej legendy Plotly; zostaje czytelny opis + legenda TOP3).
- `jst_analysis.py`:
  - hash cache runa (`.source_hash.txt`) uwzglednia teraz SHA pliku `analyze_poznan_archetypes.py`,
  - zmiana silnika raportu automatycznie wymusza ponowne przeliczenie przy kliknieciu `Generuj raport` (bez koniecznosci `Przelicz od nowa`).
- Smoke-check:
  - `python -m py_compile app.py jst_analysis.py` (OK).

### Hotfix H-005 [DONE]
Temat: Dopracowanie wizualne wykresow w `🧭 Matching` (nakladanie i nieczytelny uklad).
Kryteria ukonczenia:
1. Radar porownawczy 0-20 jest czytelny i nie nachodzi na sekcje nizej.
2. Dwa profile 0-100 (polityk vs mieszkancy) maja stabilny uklad i nie nakladaja sie wizualnie na radar.
3. Sekcja pozostaje kompatybilna ze starszym Streamlit.
Pierwszy krok wykonawczy:
- przebudowac layout sekcji `Porownanie profili archetypowych` w `app.py`:
  zwiekszyc kontrolowana wysokosc radaru, dodac separacje sekcji i ograniczyc rozmiar renderu kol 0-100.
Wynik:
- `app.py` (`matching_view`, `Podsumowanie`):
  - radar 0-20 ma teraz kontrolowana wysokosc (`height=560`), co zapobiega wizualnemu nachodzeniu na kolejne elementy,
  - uproszczono i ustabilizowano legende (dwie czytelne linie: TOP3 polityka / TOP3 mieszkancow),
  - wylaczono pasek narzedzi Plotly (`displayModeBar=False`) dla czystszego widoku,
  - sekcja profili 0-100 dostala osobny podtytul i odstep od radaru,
  - render kol 0-100 jest ograniczony szerokoscia (`width=520`) i pozostaje kompatybilny ze starszym Streamlit przez fallback.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-006 [DONE]
Temat: Nazwy profili 0-100 w `🧭 Matching` w dopełniaczu.
Kryteria ukonczenia:
1. Naglowek osoby ma forme: `Profil archetypowy {imie i nazwisko w dopelniaczu}`.
2. Naglowek JST ma forme: `Profil archetypowy mieszkańców {nazwa JST w dopelniaczu}`.
3. Usuniety dopisek `(siła archetypu, skala: 0-100)` z obu naglowkow.
Pierwszy krok wykonawczy:
- zasilic `matching_view` polami `person_name_gen` i `jst_name_gen` (z fallbackiem), a nastepnie podmienic naglowki sekcji 0-100.
Wynik:
- `app.py` (`matching_view`):
  - do wyniku dopasowania dodano pola:
    - `person_name_gen` (z `_person_genitive(person)`),
    - `jst_name_gen` (priorytet: `jst_full_gen`, fallback: auto-odmiana z `_make_jst_defaults`, potem `jst_name_nom`),
  - naglowki dwoch profili 0-100 zmieniono na:
    - `Profil archetypowy {person_name_gen}`,
    - `Profil archetypowy mieszkańców {jst_name_gen}`,
  - usunieto dopisek `(siła archetypu, skala: 0-100)` z obu etykiet.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-007 [DONE]
Temat: Dopracowanie UI Matching + stabilizacja pobierania + domkniecie fontow raportu.
Kryteria ukonczenia:
1. W radarze `Porównanie profili archetypowych` nie ucina dolnej etykiety archetypu.
2. Sekcje `Porównanie profili archetypowych` oraz `Profile archetypowe 0-100` sa wyraznie oddzielone wizualnie.
3. Blok interpretacji oceny dopasowania (`Ocena: ...`) jest bardziej czytelny, a pasek postepu wyzszy i wyrazniejszy.
4. Pobieranie ZIP/HTML nie wywoluje bledu callbacka (`TypeError: 'str' object is not callable`) i nie wylogowuje usera.
5. Komunikat o zbyt ciezkim standalone HTML jest informacyjny (nie myli z awaria generowania raportu).
6. Fonty i typografia wykresow raportu sa blizsze wzorcowi z `C:\Poznan_Archetypy_Analiza`.
Pierwszy krok wykonawczy:
- poprawic `app.py` (layout Matching, panel oceny, kompatybilny wrapper dla `download_button`) oraz `jst_analysis.py` + `analyze_poznan_archetypes.py` (pewne dostarczenie i wybor fontow w runie).
Wynik:
- `app.py`:
  - dodano kompatybilny wrapper `_download_button_compat(...)`, ktory:
    - na nowszym Streamlit ustawia `on_click="ignore"`,
    - na starszym Streamlit usuwa ten parametr (eliminuje blad `TypeError: 'str' object is not callable` przy pobieraniu),
  - podmieniono krytyczne przyciski pobierania (`CSV/XLSX` i `HTML/ZIP`) na wrapper kompatybilny,
  - komunikat o zbyt ciezkim standalone HTML zmieniono na informacyjny (`To nie jest błąd generowania raportu...`),
  - sekcja `Poziom dopasowania` przebudowana:
    - wyrazny panel z duza wartoscia `%`,
    - badge `Ocena: ...`,
    - wyzszy pasek postepu z ciemniejszym torem i obramowaniem,
  - sekcja `Porównanie profili archetypowych`:
    - dodane wizualne separatory/naglowki blokow,
    - radar dostal wieksza wysokosc (`640`) i wiekszy dolny margines (`b=86`), co zapobiega ucinaniu etykiety dolnej.
- `jst_analysis.py`:
  - `_prepare_tool_run_dir(...)` synchronizuje teraz wybrane fonty do katalogu runa (`run/assets/fonts`), aby generator mial stabilny zestaw czcionek niezaleznie od hosta.
- `JST_Archetypy_Analiza/analyze_poznan_archetypes.py`:
  - dodano logowanie wybranego fontu bazowego (`[fonts] matplotlib base font: ...`) dla latwiejszej diagnostyki,
  - utrzymano deterministyczny wybor fontu z priorytetem fontow repo.
- Smoke-check:
  - `python -m py_compile app.py jst_analysis.py JST_Archetypy_Analiza/analyze_poznan_archetypes.py` (OK).

### Hotfix H-008 [DONE]
Temat: Dopracowanie sekcji `Profile archetypowe 0-100` + nowa metoda liczenia `Oczekiwania mieszkańców (%)`.
Kryteria ukonczenia:
1. Na wykresach 0-100 tytuly:
   - `Profil archetypowy Krzysztofa Hetmana`,
   - `Profil archetypowy mieszkańców Miasta Poznania`
   sa centrowane wzgledem wykresu (na srodku obszaru wykresu, nie "uciekaja" na bok).
2. `Oczekiwania mieszkańców (%)` sa liczone z pelnych skladowych A/B1/B2/D13
   (bez wag komponentow 40/20/25/15).
3. Opis metodologii w UI dopasowania jest zgodny z nowa formula.
4. Smoke-check skladni przechodzi bez bledow.
Pierwszy krok wykonawczy:
- zlokalizowac miejsca:
  - renderu tytulow w sekcji 0-100 (`app.py`),
  - liczenia profilu JST (`_calc_jst_target_profile`) i opisu formuly w `matching_view`,
  a nastepnie wdrozyc zmiany jednym spójnym patchem.
Wynik:
- `app.py`:
  - sekcja `🧭 Matching > Podsumowanie > Profile archetypowe 0-100` ma teraz wycentrowane tytuly nad kazdym wykresem:
    - `Profil archetypowy {osoba w dopelniaczu}`,
    - `Profil archetypowy mieszkańców {JST w dopelniaczu}`,
    renderowane jako centralny naglowek HTML (`text-align:center`).
  - render obrazow 0-100 ustawiony kompatybilnie centrowo (`use_container_width` -> `use_column_width` -> `width`),
    aby tytul i wykres byly osiowo spojne takze na starszych wersjach Streamlit.
  - `_calc_jst_target_profile(...)` przelicza teraz `Oczekiwania mieszkańców (%)` jako srednia z pelnych skladowych:
    - `A_pct` (pelna wartosc komponentu A),
    - `B1_pct`, `B2_pct`, `D13_pct` (pelne trafienia %),
    - formula: `score = (A_pct + B1_pct + B2_pct + D13_pct) / 4`.
  - opis metodologii i etykiety audytu zostaly zsynchronizowane z nowa formula:
    - nowy opis pod tabela i w expanderze,
    - kolumny audytu: `A/B1/B2/D13 (pełne %)` + `Średnia 4 komponentów`.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-009 [DONE]
Temat: Korekta UX Matching po regresji wizualnej + uszczelnienie stopki commita.
Kryteria ukonczenia:
1. Sekcja `Profile archetypowe 0-100` ma wycentrowane, ale normalnej wielkosci tytuly (bez "wielkich" fontow i bez efektu jak na zrzutach 2783/2784).
2. Sekcja `Porównanie profili archetypowych` ma bardziej stonowana typografie naglowka.
3. W expanderze metryki dopasowania jest jednoznaczna informacja, ze wzor `match = ...` NIE liczy `Oczekiwan mieszkańców (%)`.
4. Stopka build pokazuje czas ostatniego commita z `main` (GitHub HEAD), z fallbackiem gdy API niedostepne.
5. Smoke-check skladni przechodzi.
Pierwszy krok wykonawczy:
- poprawic style i opisy w `app.py` (Matching), nastepnie zaktualizowac `_app_build_signature()` tak, aby priorytetem byl GitHub HEAD.
Wynik:
- `app.py` (`🧭 Matching`):
  - zmniejszono przeskalowane fonty po poprzedniej iteracji:
    - naglowki boxow sekcji (`.match-section-header h3`) do `18px`,
    - tytuly profili 0-100 do `20px` (`.match-profile-title`) z zachowanym centrowaniem,
  - dodano jednoznaczny komunikat w expanderze metryki:
    - wzor `match = ...` dotyczy tylko `Poziomu dopasowania`,
    - nie dotyczy liczenia `Oczekiwań mieszkańców (%)`.
- `app.py` (`_app_build_signature`):
  - zmieniono priorytet zrodla metadanych builda:
    1) GitHub HEAD wskazanej galezi (`main`),
    2) lokalny git HEAD,
    3) env/secrets/`.deployed_sha`,
    4) fallback czasu po SHA przez GitHub API.
  - efekt: stopka ma pokazywac czas ostatniego commita z `main`, a nie stale env z poprzedniego deployu.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-010 [DONE]
Temat: Naprawa edytora progow segmentow + dopracowanie sekcji Matching + mocniejsze rozroznienie `Oczekiwań mieszkańców (%)`.
Kryteria ukonczenia:
1. `segment_hit_threshold_overrides` akceptuje wklejki w praktycznym formacie (JSON i `segment: wartosc`) bez kruchych bledow parsera.
2. `Przywróć domyślne` w edytorze progow nie wywoluje `StreamlitAPIException` o modyfikacji `session_state` po instancjacji widgetu.
3. Sekcje `Porównanie profili archetypowych` i `Profile archetypowe 0-100` w Matching nie wygladaja jak obce, "kartowe" boksy.
4. `Oczekiwania mieszkańców (%)` wzmacniaja sygnal TOP1 (B2/D13), aby ograniczyc odczucie sztucznego spłaszczenia.
5. Smoke-check skladni przechodzi.
Pierwszy krok wykonawczy:
- poprawic parser i logike resetu progow w `jst_analysis_view`, nastepnie zmienic formule A/B1/B2/D13 i opisy metodyki oraz uproscic styl naglowkow sekcji Matching.
Wynik:
- `app.py`:
  - `_parse_segment_threshold_overrides_text(...)`:
    - akceptuje smart quotes i format liniowy `segment: wartosc` / `segment = wartosc`,
    - zwraca czytelny blad z wskazaniem problematycznej linii, zamiast niejasnego `Invalid control character`,
  - `jst_analysis_view`:
    - reset i zapis progow dzialaja przez klucze pomocnicze (`pending` + `rerun`), bez bezposredniej modyfikacji klucza aktywnego widgetu,
    - usunieto crash `StreamlitAPIException: ... cannot be modified after the widget ... is instantiated`,
  - `matching_view`:
    - odchudzono styl `match-section-header` (bez "pudelek", z prostym separatorem dolnym),
    - formuła `Oczekiwań mieszkańców (%)` ma teraz premie TOP1:
      `score = (A_pct + B1_pct + 2*B2_pct + 2*D13_pct) / 6`,
    - opisy w UI i tabela audytu skladnikow zostaly zsynchronizowane z nowa formula,
  - doprecyzowano, ze `match = ...` dotyczy wyłącznie `Poziomu dopasowania`.
  - skrocono cache metadanych commita z GitHub do `60s`, aby stopka szybciej odswiezala czas/SHA po nowym deployu.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-011 [DONE]
Temat: Przebudowa metodologii `Oczekiwań mieszkańców` do ISOA/ISOW + nowa zakładka raportowa + poprawki UI Matching i podglądu raportu.
Kryteria ukonczenia:
1. W `🧭 Matching -> Podsumowanie` stara metodologia i stary wzor sa usuniete; dziala nowy indeks:
   - rdzen oczekiwania `E = 0.50*z(A) + 0.20*z(B1) + 0.30*z(B2)`,
   - presja doswiadczenia `D = 0.70*z(N) + 0.30*z(MBAL)`,
   - wynik surowy `SEI_raw = 0.80*E + 0.20*D`,
   - skala finalna `SEI_100` w zakresie `0..100` (lub `50` przy braku rozstepu).
2. W UI Matching nazewnictwo jest dynamiczne:
   - `ISOA` / `Indeks Społecznego Oczekiwania Archetypu` dla trybu Archetypy,
   - `ISOW` / `Indeks Społecznego Oczekiwania Wartości` dla trybu Wartości.
3. W raporcie JST pojawia sie nowa zakladka zaraz po `Podsumowanie`:
   - nazwa zakladki dynamiczna `ISOA`/`ISOW`,
   - tresc: opis metodologii, baza danych (wazone/surowe), tabela rankingowa, wykres, Top3/Bottom3.
4. Etykiety w tabeli Matching sa poprawione:
   - bez `"(%)"` przy `Profil polityka` i `Oczekiwania mieszkańców` (to skala sily 0-100),
   - separator sekcji (`szara linia`) jest przed naglowkami `Porównanie...` i `Profile archetypowe 0-100`.
5. `📊 Analiza badania mieszkańców` nie traktuje limitu panelu jako "blad generowania"; komunikat i flow sa jednoznaczne oraz nie myla usera.
6. Zakladki w `🧭 Matching` dostaja czytelniejszy, atrakcyjniejszy styl zgodny z reszta panelu.
7. Zmiany generatora sa wdrozone w obu lokalizacjach:
   - `archetypy-admin/JST_Archetypy_Analiza/analyze_poznan_archetypes.py`,
   - `C:\Poznan_Archetypy_Analiza\analyze_poznan_archetypes.py`.
8. Smoke-check skladni przechodzi:
   - `python -m py_compile app.py jst_analysis.py JST_Archetypy_Analiza/analyze_poznan_archetypes.py`.
Pierwszy krok wykonawczy:
- zlokalizowac i podmienic centralna funkcje liczenia profilu JST w Matching (`_calc_jst_target_profile`) oraz miejsca renderu opisu/metryk, tak aby od razu przejsc na ISOA/ISOW i od tego samego obiektu zasilić nową zakładkę raportową.
Wynik:
- `app.py`:
  - `🧭 Matching` liczy teraz indeks syntetyczny przez standaryzacje komponentow:
    - `E = 0.50*z(A) + 0.20*z(B1) + 0.30*z(B2)`,
    - `D = 0.70*z(N) + 0.30*z(MBAL)`,
    - `SEI_raw = 0.80*E + 0.20*D`,
    - `SEI_100` min-max do `0..100` (fallback `50`),
  - dodano helpery:
    - `compute_top3_share`,
    - `compute_top1_share`,
    - `compute_negative_experience_share`,
    - `compute_most_important_experience_balance`,
    - `safe_zscore_by_archetype`,
    - `build_social_expectation_core`,
    - `build_experience_pressure`,
    - `compute_social_expectation_index`,
    - `update_matching_summary_description`,
  - dodano radio trybu etykiet (`Archetypy` / `Wartości`) i dynamiczne nazwy `ISOA` / `ISOW` w `Podsumowaniu`,
  - w tabelach Matching etykiety pozostaja bez `"(%)"` dla `Profil polityka` i `Oczekiwania mieszkańców`,
  - sekcja tabow Matching dostala mocniejszy styl (czytelniejsze i bardziej "przyklejone" zakladki),
  - `📊 Analiza badania mieszkańców`: podniesiono bezpieczny limit hard dla podgladu panelowego (`max(secret, safe_limit, 260MB)`) oraz domyslnie wlaczono "pokaz mimo duzego rozmiaru" dla pelnego podgladu.
- `JST_Archetypy_Analiza/analyze_poznan_archetypes.py`:
  - dodano i wpięto nowe liczenie ISOA/ISOW do pipeline (`ISOA_ISOW_technical.csv`, `ISOA_ISOW_table.csv`),
  - dodano zakladke raportowa `ISOA/ISOW` zaraz po `Podsumowanie`,
  - tresc zakladki: metodologia, podstawa danych, tabela, wykres, Top3/Bottom3,
  - wykres glowny ISOA/ISOW renderowany kolem 0-100 (styl jak referencyjny wykres profilu),
  - podpisy na kole sa dynamiczne:
    - archetypy w trybie `Archetypy`,
    - wartosci w trybie `Wartości`.
- Zmiany generatora zsynchronizowano rowniez do:
  - `C:\Poznan_Archetypy_Analiza\analyze_poznan_archetypes.py`.
- Smoke-check:
  - `python -m py_compile app.py jst_analysis.py JST_Archetypy_Analiza/analyze_poznan_archetypes.py` (OK),
  - `python -m py_compile C:\Poznan_Archetypy_Analiza\analyze_poznan_archetypes.py` (OK).

### Hotfix H-012 [DONE]
Temat: Korekta ISOA/ISOW do modelu zakotwiczonego w A + przywrocenie sekcji A jako PPP + domkniecie C:/D: oraz stabilizacja pelnego podgladu.
Kryteria ukonczenia:
1. ISOA/ISOW nie uzywa finalnego min-max; wynik koncowy to:
   - `P = 0.35*z(B1) + 0.65*z(B2)`,
   - `D = 0.70*z(N) + 0.30*z(MBAL)`,
   - `P_adj = 8*tanh(P/1.5)`,
   - `D_adj = 4*tanh(D/1.5)`,
   - `SEI_raw = A + P_adj + D_adj`,
   - `SEI_100 = clamp(SEI_raw, 0..100)`.
2. W raporcie jest ponownie osobna zakladka sekcji A (bez usuwania), ale pod nazwa `PPP` (`Profil Preferencji Przywodztwa`), bez zmiany logiki A.
3. W `🧭 Matching` tryb `Wartości` pokazuje etykiety wartosci na wykresach 0-100 i radarze.
4. `raport.html` w obu lokalizacjach (`D:` i `C:`) zawiera zakladke `ISOA/ISOW` oraz `PPP`.
5. Sekcja metadanych raportu pokazuje `Data wygenerowania raportu: ...` zamiast `Folder wyników: WYNIKI`.
6. Pelny podglad raportu jest stabilniejszy:
   - kompresja obrazow przy osadzaniu inline,
   - limity podgladu zsynchronizowane z `server.maxMessageSize`,
   - blokada wymuszenia, gdy przekroczony jest twardy limit panelu.
Pierwszy krok wykonawczy:
- przejsc po `app.py`, `admin_dashboard.py`, `jst_analysis.py`, `JST_Archetypy_Analiza/analyze_poznan_archetypes.py` i domknac tylko zgłoszone regresje bez restartu analizy repo.
Wynik:
- `app.py`:
  - ISOA/ISOW przeliczone na model zakotwiczony w `A` z ograniczonymi korektami `P_adj` i `D_adj`,
  - usuniety finalny min-max,
  - sekcja metodologii i tabela audytu zsynchronizowane z nowymi wzorami,
  - dynamiczne podpisy radaru i kol 0-100 dla trybu `Archetypy/Wartości`,
  - profile 0-100 w trybie `Wartości` maja etykiety wartosci (przez `label_mode="values"`),
  - limity podgladu raportu oparte o realne `server.maxMessageSize`.
- `admin_dashboard.py`:
  - `_plot_segment_profile_wheel_from_scores(...)` oraz `make_segment_profile_wheel_png(...)` wspieraja `label_mode`,
  - podpisy na pierscieniu kola sa dynamiczne (archetypy vs wartosci).
- `jst_analysis.py`:
  - `_to_data_uri(...)` kompresuje i w razie potrzeby delikatnie skaluje duze obrazy przy osadzaniu inline.
- `JST_Archetypy_Analiza/analyze_poznan_archetypes.py`:
  - ISOA/ISOW liczone wg modelu zakotwiczonego w A (bez min-max),
  - dodana legenda osi pod glownym wykresem ISOA/ISOW,
  - przywrocona osobna zakladka sekcji A jako `PPP`,
  - podmienione widoczne etykiety `IOA/IOW` -> `PPP`,
  - pod tytulem raportu: `Data wygenerowania raportu: dzien miesiac rok, godzina HH:MM`,
  - zmniejszona typografia naglowka w zakladce ISOA/ISOW.
- Synchronizacja:
  - `D:\PythonProject\archetypy\archetypy-admin\JST_Archetypy_Analiza\analyze_poznan_archetypes.py`
  - `C:\Poznan_Archetypy_Analiza\analyze_poznan_archetypes.py`
- Rebuild raportow:
  - `python JST_Archetypy_Analiza\analyze_poznan_archetypes.py` (D:)
  - `python analyze_poznan_archetypes.py` (C:)
- Smoke-check:
  - `python -m py_compile app.py jst_analysis.py admin_dashboard.py JST_Archetypy_Analiza\analyze_poznan_archetypes.py` (OK),
  - `python -m py_compile C:\Poznan_Archetypy_Analiza\analyze_poznan_archetypes.py` (OK).

### Hotfix H-013 [DONE]
Temat: Domkniecie uwag po H-012 (wariant B w raportach, styl tabel/legend, tabs Matching, fallback pobierania raportu i progi domyslne segmentow).
Kryteria ukonczenia:
1. ISOA/ISOW w raporcie i Matching korzysta z wariantu B (bez min-max i bez z-score w finale).
2. Tabela glowna PPP wraca wizualnie do wariantu z ikonami, kolorami naglowkow i pogrubieniem kluczowej kolumny.
3. Tabela glowna ISOA/ISOW ma czarne naglowki kolumn (bez przypadkowej wielokolorowosci).
4. `🧭 Matching`: naglowki sekcji `Porównanie...` i `Profile 0-100...` sa po `21px`, radar ma czytelniejsza legende linii i wieksze etykiety osi, a dolna legenda TOP3 jest dwuliniowa.
5. `📊 Analiza badania mieszkańców`: gdy `raport.html` nie jest odnaleziony w runie, panel pokazuje fallback pobierania HTML z cache (zamiast pustego stanu bez przyciskow).
6. Domyslne `segment_hit_threshold_overrides` zawieraja nowe progi wskazane przez usera.
7. Zmiany generatora sa zsynchronizowane i przebudowane raporty w obu lokalizacjach (`D:` i `C:`).
Pierwszy krok wykonawczy:
- domknac mapowanie tabel ISOA/ISOW po przejsciu na wariant B, przywrocic docelowy styl PPP, a nastepnie zsynchronizowac `analyze_poznan_archetypes.py` na C: i wykonac rebuild.
Wynik:
- `app.py`:
  - utrzymano wariant B (`K_B` + clamp) w Matching,
  - poprawiono komunikat o brakach komponentow (neutralna korekta zamiast wzmianki o `z=0`),
  - odswiezono styl tabow w Matching (bardziej wyrazny active/hover),
  - sekcje `Porównanie...` i `Profile 0-100...` pracuja z naglowkiem `21px`,
  - radar ma legende linii na gorze (`linia ciągła` vs `linia przerywana`) i wieksze etykiety osi,
  - legenda TOP3 pod radarem jest dwuliniowa (opis zwykly + pogrubione znaczniki),
  - dodano fallback pobierania HTML z cache, gdy panel nie znajdzie `raport.html` w runie.
- `JST_Archetypy_Analiza/analyze_poznan_archetypes.py`:
  - domknieto mapowanie danych wariantu B w tabeli wyjsciowej (`Korekta wariantu B`, bez starych kolumn `Korekta priorytetu/Presja doświadczenia`),
  - tabela glowna ISOA/ISOW ma czarne naglowki kolumn,
  - przywrocono styl tabeli PPP (ikony + kolory naglowkow + pogrubienie `% oczekujących`),
  - zmniejszono typografie sekcji `Jak czytać wskaźnik`,
  - zachowano strzalki i kolorowanie Top/Bottom 3 dla ISOA/ISOW i PPP.
- `JST_Archetypy_Analiza/settings.json`:
  - rozszerzono domyslne `segment_hit_threshold_overrides` o:
    `0 z 2 · #2`, `0 z 2 · #3`, `1 z 1 · #1`, `1 z 2 · #2`.
- Synchronizacja C:/D:
  - `analyze_poznan_archetypes.py` skopiowany D -> C,
  - `settings.json` zaktualizowany tez w `C:\Poznan_Archetypy_Analiza`.
- Rebuild i smoke-check:
  - `python -m py_compile app.py jst_analysis.py admin_dashboard.py JST_Archetypy_Analiza\analyze_poznan_archetypes.py` (OK),
  - `python -m py_compile C:\Poznan_Archetypy_Analiza\analyze_poznan_archetypes.py` (OK),
  - `python JST_Archetypy_Analiza\analyze_poznan_archetypes.py` (OK, WYNIKI na D:),
  - `python C:\Poznan_Archetypy_Analiza\analyze_poznan_archetypes.py` (OK, WYNIKI na C:).

### Hotfix H-014 [DONE]
Temat: Dopracowanie UI Matching + korekty transparentnosci wariantu B + finalne poprawki raportu PPP/ISOA.
Kryteria ukonczenia:
1. `🧭 Matching > Demografia`: kolumna `% grupa dopasowana` ma czytelna typografie `13.5px`.
2. `🧭 Matching > Podsumowanie`: pod kolami 0-100 w trybie `Wartości` jest centralna legenda osi (`Zmiana/Ludzie/Porządek/Niezależność`).
3. `🧭 Matching > Podsumowanie`: dodany nowoczesny blok porownania TOP3 polityk vs JST obok siebie (przed sekcja `Porównanie profili ...`).
4. Radar porownawczy ma poprawiona estetyke legendy i dynamiczne etykiety:
   - `profil polityka ({osoba})`,
   - `profil mieszkańców ({JST})`,
   oraz usuniety zbedny opis tekstowy pod wykresem.
5. `🧭 Matching` taby (`Wybierz badania`, `Podsumowanie`, `Demografia`, `Strategia komunikacji`) sa jednoznacznie klikalne i bardziej "tabowe" wizualnie.
6. `Strategia komunikacji` jest rozbudowana o bardziej praktyczny plan dzialan (os przekazu, luki, segment docelowy, plan testow).
7. Raport:
   - tabela PPP: `% oczekujących` pogrubione na czarno; zielony tylko naglowek kolumny,
   - naglowek `PPP 0-100` w kolorze czarnym,
   - w podsumowaniu PPP pojawia sie brakujace `⬇ Bottom 3 (PPP)`.
8. Wykres glowny ISOA/ISOW w raporcie jest zmniejszony o ok. 15%.
9. Wariant B:
   - neutralny poziom B2 = `8.3333333333`,
   - eksport pomocniczy zawiera kontrolke MBAL: `Mneg`, `Mpos`, `MBAL`.
10. Zmiany obliczeniowe mieszkancow sa wdrozone i przebudowane na obu lokalizacjach (D + C).
Pierwszy krok wykonawczy:
- zrobic komplet zmian w `app.py` (Matching UI) i `JST_Archetypy_Analiza/analyze_poznan_archetypes.py` (raport + eksport), potem synchronizacja pliku analizujacego na C i rebuild obu raportow.
Wynik:
- `app.py`:
  - dopracowano taby Matching (mocniejsze style aktywne/hover, bardziej czytelna klikalnosc),
  - sekcja `Podsumowanie` ma nowy blok TOP3 (polityk vs JST) w kartach obok siebie,
  - radar ma ladniejsza, dedykowana legende i dynamiczne etykiety profili; usunieto zbedny opis pod wykresem,
  - TOP3 pod radarem dostaly estetyczne karty i wycentrowany uklad,
  - pod kolami 0-100 w trybie `Wartości` dodano centralna legende osi jak na wzorcu,
  - `Demografia`: wartosci w kolumnie `% grupa dopasowana` maja rozmiar `13.5px`,
  - `Strategia komunikacji` rozbudowana do 4 kart rekomendacyjnych (os przekazu, luki, segment docelowy, plan testow),
  - doprecyzowano wzor wariantu B w opisie (`delta_B2 = B2 - 8.3333333333`) i dodano w audycie kolumny `Mneg/Mpos`.
- `JST_Archetypy_Analiza/analyze_poznan_archetypes.py`:
  - wariant B liczy `delta_B2` z neutralem `8.3333333333`,
  - dodano eksport pomocniczy: `ISOA_ISOW_MBAL_control.csv` (`Mneg`, `Mpos`, `MBAL` + kontrola),
  - tabela PPP: `% oczekujących` pogrubione czarne, naglowek `PPP 0-100` czarny,
  - podsumowanie PPP zawiera teraz `Bottom 3 (PPP)` (archetypy i wartości),
  - wykres glowny ISOA/ISOW opakowany w kontener `85%` szerokosci (`~15%` mniejszy).
- Synchronizacja C:/D:
  - plik `analyze_poznan_archetypes.py` skopiowany D -> C,
  - raporty przebudowane na obu lokalizacjach.
- Rebuild i smoke-check:
  - `python -m py_compile app.py jst_analysis.py admin_dashboard.py JST_Archetypy_Analiza\analyze_poznan_archetypes.py` (OK),
  - `python -m py_compile C:\Poznan_Archetypy_Analiza\analyze_poznan_archetypes.py` (OK),
  - `python JST_Archetypy_Analiza\analyze_poznan_archetypes.py` (OK),
  - `python C:\Poznan_Archetypy_Analiza\analyze_poznan_archetypes.py` (OK).

### Hotfix H-015 [IN_PROGRESS]
Temat: Naprawa regresji interaktywnosci standalone HTML raportu + kolejny pakiet dopieszczen UI Matching i raportu.
Kryteria ukonczenia:
1. `📊 Analiza badania mieszkańców`:
   - standalone/full HTML zachowuje interaktywnosc JS jak wersja ZIP (`Archetypy/Wartości`, Segmenty, Skupienia, Filtry, suwaki).
2. Raport:
   - `PPP / Podsumowanie`: 4 boksy (`Top3/Bottom3 oczekiwane` + `Top3/Bottom3 PPP`) w jednej linii na desktopie,
   - `Wykres główny ISOA/ISOW`: wyrównany do lewej (bez centrowania).
3. `🧭 Matching`:
   - poprawiony layout topu (mniejsza pusta przestrzeń),
   - mocniej czytelna karta "dla kogo jest matching",
   - dopracowany styl tabów (bardziej neutralny kolor + ostre dolne rogi),
   - radar: przywrócona klikalna legenda profili i mniejsze odstępy od wykresu,
   - TOP3 polityk/JST: ikonki przy nazwach, rowna geometria "pastylek", kolory zgodne z rolą (główny/wspierający/poboczny),
   - Demografia: offset tabeli `👥 PROFIL DEMOGRAFICZNY` (`padding-left:25px`, `padding-top:15px`).
4. Synchronizacja i testy:
   - zmiany obliczeniowe/generatorowe mieszkancow zsynchronizowane na D: i C:,
   - `py_compile` oraz rebuild raportow D/C wykonane.
Pierwszy krok wykonawczy:
- uszczelnic `inline_local_assets(...)` w `jst_analysis.py`, aby inliner nie uszkadzal skryptow JS podczas zamiany `src/href` na data URI.

#### H-015 / Etap 2 [DONE]
Temat: Korekty wizualne Matching + dopracowanie metryki `Poziom dopasowania` (po nowych screenach usera).
Zakres (zgrupowany krok po kroku):

Krok A [DONE] — TOP3 + tabs + radar spacing
1. `TOP3 ... dla {osoba}` i `TOP3 ... dla {JST}`:
   - odejsc od obecnego niebieskiego gradientu (preferencja: biale tło / neutralny styl),
   - ikonki musza byc zgodne z ikonami archetypow z wykresow kolowych,
   - zachowac rowna geometrie wierszy i stala szerokosc etykiet roli.
2. `🧭 Matching` tabs:
   - mocniejsze zaznaczenie aktywnej zakladki (moze zostac niebieskie),
   - wyrazniejszy hover.
3. Radar (`Porównanie profili archetypowych`):
   - legenda nie moze nachodzic na wykres,
   - mniejsze odstepy pionowe: legenda i dolny blok TOP3 blizej radaru,
   - markery JST zmienic z kropek na kwadraty,
   - dopracowac zapis legendy TOP3 (bez przecinkow, wieksze odstepy).

Krok B [DONE] — metryka `Poziom dopasowania`
1. Przebudowac metryke dopasowania tak, aby mocniej karala rozjazdy archetypow kluczowych (TOP3 polityka i TOP3 JST),
   bo obecnie przypadki z duzymi lukami na archetypach kluczowych sa oceniane zbyt wysoko.
2. Zaktualizowac opis metryki w Matching i audyt, aby bylo jasne, jak liczona jest kara za luki kluczowe.

Krok C [DONE] — Demografia box + separacja sekcji 0-100
1. Cofnac blad z `👥 PROFIL DEMOGRAFICZNY`:
   - przesuniecie ma dotyczyc calej ramki/boxa, a nie samej tabeli.
   - docelowy offset jak na referencji usera (`left: 25px`, `top: 15px`) dla kontenera boxa.
2. Dodac wiekszy odstep miedzy dolnym blokiem TOP3 pod radarem a sekcja
   `Profile archetypowe 0-100`, aby sekcje sie nie zlewaly.

Wynik Etapu 2 (czesc 1):
- `app.py`:
  - TOP3 polityk/JST: biale tlo kart (bez niebieskiego gradientu), ikony archetypow jako realne ikony PNG (te same co na kolach), rowna geometria rolek i nazw.
  - tabs Matching: mocniejsze zaznaczenie active (niebieski), wyrazniejszy hover i bardziej neutralny kontener.
  - radar porownawczy: markery JST zmienione na kwadraty, legenda odsunięta od wykresu (bez nachodzenia), dolna legenda TOP3 bez przecinkow i z wiekszym spacingiem.
  - sekcja `Profile archetypowe 0-100`: dodany wiekszy odstep od dolnej legendy radaru.
  - `Demografia`: offset `👥 PROFIL DEMOGRAFICZNY` przeniesiony na caly box (padding-left:25, padding-top:15), nie tylko na sama tabele.
- Smoke-check: `python -m py_compile app.py` (OK).

Wynik Etapu 2 (czesc 2):
- `app.py` (`Krok B`):
  - metryka `Poziom dopasowania` przelicza teraz osobno luki kluczowe (unia TOP3 polityka + TOP3 mieszkancow),
  - finalny wynik ma jawna kare kluczowa:
    - `base = 0.40*(100-MAE) + 0.20*(100-RMSE) + 0.20*(100-TOP3_MAE) + 0.20*(100-KEY_MAE)`,
    - `kara_kluczowa = 0.22*KEY_MAE + 0.10*max(0, KEY_MAX - 15)`,
    - `match = clamp(0,100, base - kara_kluczowa)`,
  - metryki w UI rozszerzone o `Luki kluczowe (TOP3 P+JST)`,
  - w expanderze dopisano nowy opis wzoru i listę archetypow kluczowych.
- Smoke-check: `python -m py_compile app.py` (OK).

Dogrywka A2 [DONE]:
1. `🧭 Matching` tabs:
   - poprawic nieczytelnosc aktywnej zakladki po najechaniu (hover nie moze "zjadac" kontrastu tekstu).
2. `Porównanie profili archetypowych`:
   - podniesc wyzej gorna legende profili i zblizyc caly blok wykresu/legend do tytulu sekcji,
   - dolna legenda ma nie ucinać etykiety archetypu na radarze (`Władca`),
   - napisy `TOP3 polityka` i `TOP3 mieszkańców` w dolnej legendzie bez pogrubienia,
   - w legendzie `TOP3 mieszkańców` znaczniki `główny/wspierający/poboczny` jako kwadraty (nie kółka).
3. Gorna legenda profili:
   - zaokraglic rogi obramowania,
   - odrobine zwiekszyc odstep miedzy profilem polityka i mieszkancow,
   - zwiekszyc marginesy wewnetrzne (boczne oraz gorny/dolny).

Wynik Dogrywki A2:
- `app.py`:
  - taby Matching: aktywny tab pozostaje czytelny po hover (wymuszone kolory i kontrast dla stanu `selected:hover`),
  - radar porownawczy:
    - gorna legenda przesunieta wyzej, z wiekszym odstępem między pozycjami i wiekszymi marginesami wewnetrznymi,
    - caly blok wykresu z legendami zblizony do tytulu sekcji,
    - dolny margines wykresu zwiekszony (koniec ucinania etykiety `Władca`),
  - dolna legenda TOP3:
    - `TOP3 polityka` i `TOP3 mieszkańców` bez pogrubienia,
    - znaczniki dla `TOP3 mieszkańców` zmienione na kwadraty.
- Smoke-check: `python -m py_compile app.py` (OK).

Dogrywka A3 [DONE]:
1. `🧭 Matching / Podsumowanie`:
   - pod blokami `TOP3 archetypów dla ...` dodac nowa sekcje:
     - `Główne zalety`,
     - `Główne problemy`,
   - logika ma wyciagac wnioski z rozjazdow i zgodnosci (szczegolnie na kluczowych archetypach) i prezentowac je atrakcyjnie wizualnie (bez niebieskich gradientow).
2. Metryka dopasowania:
   - utrzymac model bez jawnej premii dodatniej (tylko model kar),
   - uszczelnic opisy metodyki i UI tak, by bylo to jednoznaczne.

Wynik Dogrywki A3:
- `app.py`:
  - pod kartami `TOP3 ... dla ...` dodano nowy, dwukolumnowy blok:
    - `Główne zalety`,
    - `Główne problemy`,
    liczony dynamicznie z:
    - zgodnosci/różnicy priorytetu głównego,
    - wspólnego TOP3 (część wspólna),
    - średniej luki kluczowej (`KEY_MAE`),
    - największej luki kluczowej (`KEY_MAX`),
    - najlepiej dopasowanej pozycji (`min |Δ|`).
  - sekcja ma neutralny, biały styl (bez niebieskich gradientów) i czytelne badge/listy.
  - doprecyzowano opisy metryki (`match_formula` + expander), że model **nie ma jawnej premii dodatniej** i działa wyłącznie przez mechanizm kar.
- Smoke-check: `python -m py_compile app.py` (OK).

Dogrywka A4 [DONE]:
1. `Porównanie profili archetypowych` (UI radar):
   - zmniejszyc margines dolny pod tytulem sekcji,
   - gora legenda: wycentrowac teksty i zwiekszyc czytelny odstep miedzy:
     - `profil polityka (...)`,
     - `profil mieszkańców (...)`,
   - dolna legenda TOP3 podciagnac nieco do gory (bez kolizji z wykresem),
   - oslabic pogrubienie tekstow `główny / wspierający / poboczny`.
2. Radar:
   - pogrubic etykiety osi (nazwy archetypow/wartosci), ktore naleza do TOP3
     (z unii TOP3 polityka i TOP3 mieszkańców).
3. `Poziom dopasowania`:
   - sprawdzic kalibracje pasm oceny vs realne duze luki na archetypach kluczowych
     (przypadek: wysoka ocena przy duzych lukach na TOP3 polityka/JST),
   - dopracowac opis werbalny tak, aby nie komunikowal "niskich i stabilnych różnic"
     przy wysokich wartościach `KEY_MAX` lub dużych lukach TOP3.
4. Metryka:
   - potwierdzic decyzje: rezygnujemy z jawnej premii za dopasowanie
     (zostaje model oparty o kare, bez dodatniego bonusu).

Wynik Dogrywki A4:
- `app.py`:
  - radar `Porównanie profili ...`:
    - zmniejszony odstęp pod tytułem sekcji (`match-compare-header`),
    - dopracowane pozycjonowanie górnej legendy i większy odstęp między profilami (`entrywidth`, `tracegroupgap`, `y`),
    - dolna legenda TOP3 podciągnięta wyżej (`margin` bloku stylu),
    - osłabione pogrubienie etykiet `główny / wspierający / poboczny`.
  - etykiety osi radaru dla pozycji z TOP3 (unia polityk + mieszkańcy) są wyróżnione pogrubieniem (styl `ticktext`).
  - `Poziom dopasowania`:
    - kalibracja opisu pasm: wysoka luka kluczowa (`KEY_MAX` / `KEY_MAE`) obniża opisową ocenę pasma,
      nawet gdy sam wynik liczbowy jest relatywnie wysoki,
    - utrzymano model bez jawnej premii dodatniej.
- Smoke-check: `python -m py_compile app.py` (OK).

Dogrywka A5 [DONE]:
1. `Porównanie profili archetypowych`:
   - górna legenda przeniesiona wyżej (dalej od radaru, bliżej tytułu),
   - legenda zawężona (`entrywidth`) i z większym „oddechem” wewnętrznym (padding przez NBSP + mniejszy font),
   - dolna legenda TOP3 podciągnięta bliżej wykresu.
2. Globalny layout:
   - zmniejszony górny margines strony (`.block-container padding-top`), by podnieść cały widok.
3. `Poziom dopasowania`:
   - zwiększona kara za luki kluczowe:
     - było: `0.22*KEY_MAE + 0.10*max(0, KEY_MAX - 15)`,
     - jest: `0.30*KEY_MAE + 0.14*max(0, KEY_MAX - 12)`.

Wynik Dogrywki A5:
- `app.py`:
  - dopracowano pozycjonowanie i geometrię legend przy radarze,
  - zmniejszono wolne miejsce na górze strony,
  - zaostrzono karę kluczową w metryce `Poziom dopasowania`.
- Smoke-check: `python -m py_compile app.py` (OK).

Kryteria ukonczenia Etapu 2:
1. Wszystkie elementy z punktow 1-8 usera odwzorowane 1:1 na zrzutach.
2. Brak regresji dzialania i wygladu pozostalych sekcji Matching.
3. `py_compile` dla `app.py` przechodzi poprawnie.

#### H-015 / Etap 3 [DONE]
Temat: Domkniecie brakow renderu w raporcie HTML (`Segmenty`, `Skupienia`, `Filtry`) dla standalone i podgladu online.
Zakres:

Krok D [DONE] — mapy Segmentow i Skupien sterowane suwakiem
1. `Segmenty`:
   - naprawic brak renderu `Mapa przewag segmentów`,
   - mapa ma sie aktualizowac wraz ze zmiana suwaka widocznych segmentow.
2. `Skupienia (k-średnich)`:
   - naprawic brak renderu `Mapa skupień (projekcja dla K=...)`,
   - mapa ma sie aktualizowac po zmianie suwaka `Wybrany model skupień (K)`.
3. Zweryfikowac, czy problem dotyczy:
   - mapowania indeksu suwaka -> nazwa pliku mapy,
   - czy tylko osadzania obrazow po inline (standalone/podglad online).

Krok E [DONE] — ikony w zakladce Filtry
1. Przywrocic ikonki archetypu/wartosci w zakladce `Filtry` (jak w wersji referencyjnej).
2. Potwierdzic dzialanie identycznie w:
   - `raport.html` otwieranym lokalnie,
   - `Podgląd raportu online w panelu`.

Kryteria ukonczenia Etapu 3:
1. `Mapa przewag segmentów` i `Mapa skupień` sa widoczne i reaguja na suwaki.
2. `Filtry` pokazuja ikonki jak na referencji usera.
3. Zmiany dzialaja tak samo w standalone HTML i podgladzie online.
4. Rebuild + smoke-check po stronie generatora:
   - `python -m py_compile jst_analysis.py JST_Archetypy_Analiza/analyze_poznan_archetypes.py`,
   - synchronizacja `analyze_poznan_archetypes.py` D -> C i rebuild raportow w obu lokalizacjach.

Wynik Etapu 3:
- `JST_Archetypy_Analiza/analyze_poznan_archetypes.py`:
  - `Segmenty`: JS przelaczania map korzysta teraz z jawnych map plikow per-K (`map_arche_by_k`, `map_values_by_k`) zamiast skladania samego stringu nazwy;
    to domyka brak renderu map przy standalone/online.
  - `Filtry`: dodano payload `FILTER_ICONS` i `iconSrc(...)` bierze ikony z mapy (fallback do `icons/<slug>.png`), co przywraca ikony na wykresach.
  - do `seg_pack_ultra` i `seg_packs_render["ultra_premium"]` dopisywane sa mapy plikow segmentowych per-K.
- `jst_analysis.py`:
  - `inline_local_assets(...)` rozszerzono o inlining lokalnych sciezek zasobow pojawiajacych sie jako quoted-string w JS/JSON
    (nie tylko atrybuty `src/href`), dzieki czemu dynamicznie podmieniane mapy/ikony dzialaja tez po osadzeniu standalone.
- Smoke-check + rebuild:
  - `python -m py_compile jst_analysis.py JST_Archetypy_Analiza\\analyze_poznan_archetypes.py` (OK),
  - `python -m py_compile C:\\Poznan_Archetypy_Analiza\\analyze_poznan_archetypes.py` (OK),
  - synchronizacja D -> C (`analyze_poznan_archetypes.py`),
  - rebuild raportow:
    - `python D:\\PythonProject\\archetypy\\archetypy-admin\\JST_Archetypy_Analiza\\analyze_poznan_archetypes.py` (OK),
    - `python C:\\Poznan_Archetypy_Analiza\\analyze_poznan_archetypes.py` (OK).
