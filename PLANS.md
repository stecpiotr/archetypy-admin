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

### Hotfix H-015 [DONE]
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

Dogrywka A6 [DONE]:
1. Radar / legendy:
   - górna legenda ustawiona minimalnie niżej,
   - większa czcionka legendy górnej (`+1.5px`),
   - węższa legenda (`entrywidth`),
   - większy lewy „oddech” wewnętrzny wpisów legendy.
2. Dolna legenda TOP3:
   - przybliżona wyżej do wykresu.
3. Globalny layout:
   - `padding-top` kontenera głównego ustawiony na `3px`.
4. Metryka:
   - kolejny wzrost kary kluczowej:
     - było: `0.30*KEY_MAE + 0.14*max(0, KEY_MAX - 12)`,
     - jest: `0.45*KEY_MAE + 0.22*max(0, KEY_MAX - 9)`.

Wynik Dogrywki A6:
- `app.py`:
  - wdrożone poprawki legend/odstępów i top spacingu strony,
  - ponownie zaostrzona kara za brak dopasowania kluczowego.
- Smoke-check: `python -m py_compile app.py` (OK).

Dogrywka A7 [DONE]:
1. `Poziom dopasowania`:
   - bardziej zróżnicowane progi i nazwy pasm (7 poziomów, analogicznie do stylu interpretacji natężenia):
     - `0–29`, `30–49`, `50–59`, `60–69`, `70–79`, `80–89`, `90–100`,
   - opisy jakościowe dopasowane do tych przedziałów,
   - utrzymany guard kluczowych luk (`KEY_MAE`/`KEY_MAX`) ograniczający opis pasma.
2. UI:
   - doprecyzowano opis progów w expanderze `Jak liczony jest poziom dopasowania?`.

Wynik Dogrywki A7:
- `app.py`:
  - 7-stopniowa skala opisowa poziomu dopasowania,
  - dalej zaostrzona kara kluczowa (`0.45*KEY_MAE + 0.22*max(0, KEY_MAX - 9)`),
  - zaktualizowane opisy metodologii i spójne kolorowanie badge oceny.
- Smoke-check: `python -m py_compile app.py` (OK).

Dogrywka A8 [DONE]:
1. `Poziom dopasowania` — finalny podział progów:
   - `0–29` marginalne dopasowanie,
   - `30–39` bardzo niskie dopasowanie,
   - `40–49` niskie dopasowanie,
   - `50–59` umiarkowane dopasowanie,
   - `60–69` znaczące dopasowanie,
   - `70–79` wysokie dopasowanie,
   - `80–89` bardzo wysokie dopasowanie,
   - `90–100` ekstremalnie wysokie dopasowanie.
2. Zaktualizowano opis progów w expanderze metodologicznym i kolorowanie badge do nowego podziału.

Wynik Dogrywki A8:
- `app.py`: wdrożony finalny, 8-stopniowy podział progów z nazwami 1:1 wg wskazania usera.
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

### Hotfix H-016 [DONE]
Temat: Czyszczenie stanu `Matching` po zmianie badań + sekcja `Status badania` (personalne/JST) z blokadą ankiet dla statusów nieaktywnych.
Kryteria ukończenia:
1. W `🧭 Matching` po zmianie któregokolwiek badania nie zostaje zielony komunikat sugerujący policzony wynik.
2. W `✏️ Edytuj dane badania` i `✏️ Edytuj dane badania mieszkańców` jest sekcja `Status badania` z akcjami:
   - `Zawieś`,
   - `Odwieś`,
   - `Zamknij badanie` (nieodwracalne),
   - `Usuń badanie` (z dodatkowym potwierdzeniem).
3. Sekcja statusu pokazuje: bieżący status, datę uruchomienia, datę ostatniej zmiany statusu.
4. Wejście ankietowe po linku:
   - dla `suspended`: komunikat `Badanie jest nieaktywne`,
   - dla `closed`: komunikat `Badanie zakończone`.
5. JST RPC zapisu odpowiedzi odrzuca zapis, jeśli badanie nie ma statusu `active`.
Pierwszy krok wykonawczy:
- dopisać trwałe statusy badań (`study_status`, `status_changed_at`, `started_at`) w warstwie DB i podpiąć je do paneli edycji.
Wynik:
- `Matching`: selectboxy dostały callback unieważniający (`matching_result` + komunikat), więc po zmianie badania znika zielony komunikat i stary wynik.
- `app.py`:
  - dodano wspólny renderer sekcji `Status badania` (tabela + chipy + akcje z ikonami + potwierdzenia),
  - wdrożono akcje statusów w obu panelach edycji (personalne i JST),
  - `Zamknij badanie` jest trwałe (bez możliwości ponownego uruchomienia).
- `db_utils.py`:
  - dodano statusy dla badań personalnych (`study_status`) i API zmiany statusu (`set_study_status`),
  - `soft_delete_study` ustawia status `deleted`.
- `db_jst_utils.py`:
  - `ensure_jst_schema` rozszerzono o kolumny statusów dla `jst_studies` i `studies`,
  - `get_jst_study_public` zwraca status,
  - `add_jst_response_by_slug` blokuje zapis gdy status != `active` (`study_inactive`),
  - dodano `set_jst_study_status`, a soft-delete ustawia status `deleted`.
- `archetypy-ankieta`:
  - `studies.ts` i `jstStudies.ts` obsługują pola statusowe,
  - `App.tsx` pokazuje komunikat blokujący dla statusów `suspended/closed/deleted`,
  - `JstSurvey.tsx` zwraca precyzyjny komunikat po RPC `study_inactive`.
- Smoke-check:
  - `python -m py_compile app.py db_utils.py db_jst_utils.py` (OK),
  - `npm run build` w `archetypy-ankieta` (OK).

### Hotfix H-017 [DONE]
Temat: Kalibracja `Poziom dopasowania` + nowe moduły panelu personalnego (`Ustawienia ankiety`, `Połącz badania`).
Kryteria ukończenia:
1. Progi opisowe `Poziom dopasowania` działają spójnie z podziałem 0–29 / 30–39 / ... / 90–100 (bez niespodziewanego zbijania 50–59 do `Niskie`).
2. Wskaźnik dopasowania jest mniej skokowy przy pojedynczym ekstremalnym archetypie (łagodniejsza kara `KEY_MAX`).
3. W `Badania personalne - panel` są 2 nowe kafelki:
   - `Ustawienia ankiety`,
   - `Połącz badania`.
4. Moduł `Połącz badania` pozwala:
   - wybrać badanie główne,
   - dodać wiele badań źródłowych (`Dodaj badanie`),
   - skopiować odpowiedzi źródeł do badania głównego (`Dodaj`),
   - bez usuwania odpowiedzi ze źródłowych badań.
5. W `Matching` po zmianie badań nie zostaje zielony komunikat sugerujący stary wynik.
Pierwszy krok wykonawczy:
- dodać warstwę DB do kopiowania odpowiedzi personalnych (`responses`) i podpiąć nowy widok `Połącz badania` w `app.py`.
Wynik:
- `db_utils.py`:
  - dodano `fetch_personal_response_count(...)`,
  - dodano `merge_personal_study_responses(...)` (batch copy odpowiedzi `responses` ze źródeł do targetu),
  - dodano normalizację `answers` dla kopiowania.
- `app.py`:
  - `Poziom dopasowania`:
    - kara kluczowa przestawiona na mniej skokową:
      - było: `0.45*KEY_MAE + 0.22*max(0, KEY_MAX - 9)`,
      - jest: `0.42*KEY_MAE + 0.16*max(0, KEY_MAX - 12)`,
    - opis pasma nie jest już ręcznie zbijany guardem; duże luki kluczowe są raportowane jako ostrzeżenie jakościowe,
    - dodano metrykę `Maks. luka kluczowa`.
  - `Badania personalne - panel`:
    - dodano kafelki: `Ustawienia ankiety` i `Połącz badania`,
    - dodano widoki `personal_settings_view()` i `personal_merge_view()`.
  - `Połącz badania`:
    - wybór badania głównego,
    - dynamiczna lista badań źródłowych (`➕ Dodaj badanie` / `➖ Usuń ostatnie`),
    - finalne wykonanie przez `Dodaj` z podsumowaniem `inserted/skipped`,
    - źródłowe badania pozostają bez zmian.
  - `Matching`:
    - dodatkowy bezpiecznik czyści wynik/komunikat, jeśli aktualny wybór badań różni się od policzonego pairingu.
- Smoke-check:
  - `python -m py_compile app.py db_utils.py` (OK).

### Hotfix H-018 [DONE]
Temat: Ustawienia ankiety dla panelu mieszkańców + przeniesienie `Status badania` do ustawień + korekta etykiety RMSE.
Kryteria ukończenia:
1. W `Badania mieszkańców - panel` jest kafelek `⚙️ Ustawienia ankiety`.
2. `Status badania` nie jest już renderowany w:
   - `✏️ Edytuj dane badania`,
   - `✏️ Edytuj dane badania mieszkańców`;
   i jest dostępny w modułach ustawień.
3. W Matching podpis metryki RMSE nie ucina się w UI.
4. Reguła kluczowych luk: jeśli 3. pozycja ma wynik `>70`, nie wchodzi do puli kar kluczowych (kara liczona dla TOP2).
Pierwszy krok wykonawczy:
- przebudować `app.py`: dodać `jst_settings_view`, przepiąć routing i usunąć panel statusu z widoków edycji.
Wynik:
- `app.py`:
  - dodano kafelek `⚙️ Ustawienia ankiety` w `home_jst_view`,
  - dodano nowy widok `jst_settings_view()` z tabelą statusu/linkiem/liczbą odpowiedzi i pełnym panelem akcji statusu,
  - `Status badania` przeniesiono do ustawień:
    - `personal_settings_view()` dostał pełny panel akcji statusu,
    - usunięto panel statusu z `edit_view()` i `jst_edit_view()`,
  - skrócono etykietę metryki do `RMSE (kara odchyleń)`,
  - pula kluczowych archetypów do kary działa dynamicznie:
    - domyślnie TOP3,
    - jeśli 3. pozycja ma `>70`, do puli wchodzi TOP2 (dla polityka i/lub mieszkańców).
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-019 [DONE]
Temat: Korekta klasyfikacji TOP2/TOP3 dla kar kluczowych i UI Matching + poprawka frazy w ankiecie.
Kryteria ukończenia:
1. Archetyp 3. pozycji jest liczony jako `poboczny` tylko gdy ma `>=70`; przy `<70` profil traktujemy jako TOP2.
2. Kara kluczowa (`KEY_MAE/KEY_MAX`) nie uwzględnia 3. pozycji, gdy ta ma `<70`.
3. UI Matching nie sugeruje błędnie TOP3, jeśli faktycznie obowiązuje TOP2.
4. W ankiecie fraza `wyrazistość i brak kompromisów` jest zamieniona na `wyrazistość i bezkompromisowość`.
Pierwszy krok wykonawczy:
- poprawić próg w `app.py` (logika kar + render TOP list/legend) i zweryfikować kompilację.
Wynik:
- `app.py`:
  - odwrócono warunek puli kluczowej:
    - było: TOP2 przy `3. pozycja >70`,
    - jest: TOP2 przy `3. pozycja <70` (TOP3 tylko dla `>=70`),
  - analogicznie poprawiono listy TOP w sekcji wizualnej (`TOP2/TOP3`),
  - tytuły kart i legend są dynamiczne (`TOP{N}`),
  - opisy metodyki zaktualizowane do reguły `<70 -> TOP2`.
- `archetypy-ankieta/src/JstSurvey.tsx`:
  - podmieniono tekst: `wyrazistość i bezkompromisowość`.
- Smoke-check:
  - `python -m py_compile app.py` (OK),
  - `npm run build` w `archetypy-ankieta` (OK).

### Hotfix H-020 [DONE]
Temat: Szybki fix runtime `UnboundLocalError` w `🧭 Matching`.
Kryteria ukończenia:
1. `matching_view` nie wywala błędu `cannot access local variable 'person_top_colors'`.
2. Panel `Podsumowanie` renderuje się poprawnie po wejściu na radar i legendy TOP.
Pierwszy krok wykonawczy:
- skorygować kolejność inicjalizacji zmiennych kolorów legendy względem nowego helpera `_role_legend_html(...)`.
Wynik:
- `app.py`:
  - deklaracje `person_top_colors` i `jst_top_colors` przeniesiono nad pierwsze użycie (`p_role_legend` / `j_role_legend`),
  - usunięto duplikat deklaracji niżej w tej samej sekcji.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-021 [DONE]
Temat: Runtime fix `IndexError` dla TOP2/TOP3 w markerach radaru (`🧭 Matching`).
Kryteria ukończenia:
1. `matching_view` nie wywala błędu `IndexError: list index out of range` w `_marker_series`.
2. Render markerów TOP działa zarówno dla TOP3, jak i dla TOP2 (gdy 3. pozycja nie kwalifikuje się).
Pierwszy krok wykonawczy:
- zmienić budowanie mapy markerów tak, żeby nie indeksować `top3[2]` bezwarunkowo.
Wynik:
- `app.py`:
  - `_marker_series` buduje `mapping` inkrementalnie (`if len(top3) > 0/1/2`) zamiast przez słownik z bezpośrednimi odwołaniami `top3[0..2]`,
  - eliminuje to crash przy przypadkach TOP2.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-022 [DONE]
Temat: Rozróżnienie kolorów pastylki `Ocena` dla pasm `Znaczące` i `Wysokie` (`🧭 Matching`).
Kryteria ukończenia:
1. Poziomy `60–69` i `70–79` mają wyraźnie różne kolory pastylki.
2. Każde pasmo ma unikalny kolor (bez duplikatów kluczowych kolorów obramowania).
Pierwszy krok wykonawczy:
- skorygować paletę `score_color/score_bg` w bloku renderu `Poziom dopasowania`.
Wynik:
- `app.py`:
  - `70–79` (`Wysokie`) zmieniono na fiolet (`#6d28d9`, tło `#f5f3ff`),
  - `60–69` (`Znaczące`) pozostaje niebieskie (`#1d4ed8`, tło `#eff6ff`),
  - dodatkowo rozdzielono odcień dla `30–39` (`#be123c`) aby utrzymać unikalność pasm.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-023 [DONE]
Temat: Dalsze zaostrzenie kary kluczowej w `Poziom dopasowania` dla dużych rozjazdów strategicznych.
Kryteria ukończenia:
1. Wysokie `KEY_MAE/KEY_MAX` mocniej obniżają wynik końcowy.
2. Brak wspólnych priorytetów i różny TOP1 dodatkowo obniżają wynik.
3. Opis metodologii odzwierciedla nową logikę kary.
Pierwszy krok wykonawczy:
- podnieść współczynniki kary `KEY_MAE/KEY_MAX` i dodać składniki kar za brak wspólnych priorytetów.
Wynik:
- `app.py`:
  - nowa kara kluczowa:
    - `0.56*KEY_MAE + 0.26*max(0, KEY_MAX - 10)`,
    - `+ 5.5` gdy brak wspólnych pozycji TOP,
    - `+ 2.0` gdy wspólna jest tylko 1 pozycja TOP,
    - `+ 2.5` gdy polityk i mieszkańcy mają różny priorytet główny (TOP1),
  - zaktualizowano opis wzoru i sekcję metodologiczną w expanderze.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-024 [DONE]
Temat: Powiązanie sekcji `Główne zalety / Główne problemy` z listami `Najlepsze dopasowania / Największe luki`.
Kryteria ukończenia:
1. Jeśli archetyp priorytetowy (TOP2/TOP3) pojawia się w `Największe luki`, jest to jawnie pokazane w `Główne problemy`.
2. Jeśli archetyp priorytetowy (TOP2/TOP3) pojawia się w `Najlepsze dopasowania`, jest to jawnie pokazane w `Główne zalety`.
3. Logika działa dynamicznie dla Archetypów i Wartości.
Pierwszy krok wykonawczy:
- dopisać kontrolę przecięć pomiędzy pulą priorytetową (TOP2/TOP3 polityk + mieszkańcy) a top3 luk/dopasowań.
Wynik:
- `app.py`:
  - dodano wykrywanie przecięć:
    - `priority_in_best` (priorytety wśród najlepszych dopasowań),
    - `priority_in_gaps` (priorytety wśród największych luk),
  - dodano automatyczne wpisy do sekcji:
    - `Główne zalety`: lista priorytetów w top dopasowaniach z `|Δ|`,
    - `Główne problemy`: lista priorytetów w top lukach z `|Δ|`.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-025 [DONE]
Temat: Wymuszenie spójności sekcji `Główne zalety/problemy` z widocznymi chipami i priorytet widoczności wpisów TOP.
Kryteria ukończenia:
1. Przecięcia priorytetów TOP z `Najlepsze dopasowania` i `Największe luki` są liczone z tych samych list, które są renderowane jako chipy.
2. Wpisy o przecięciach TOP są widoczne nawet przy limicie 4 punktów (mają priorytet na początku listy).
Pierwszy krok wykonawczy:
- przepiąć źródło przecięć na `result['strengths']` / `result['gaps']` i wstawiać wpisy TOP na początek list `advantages/problems`.
Wynik:
- `app.py`:
  - przecięcia TOP są teraz liczone z `result['strengths']` i `result['gaps']` (te same dane co chipy na ekranie),
  - wpisy:
    - `Priorytetowe pozycje ... wśród najlepszych dopasowań`,
    - `Priorytetowe pozycje ... wśród największych luk`,
    są wstawiane przez `insert(0, ...)`, więc nie wypadają przy `[:4]`.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-026 [DONE]
Temat: Uodpornienie wykrywania przecięć TOP vs chipy (normalizacja nazw).
Kryteria ukończenia:
1. Wykrywanie przecięć działa nawet przy różnicach zapisu nazw (spacje/diakrytyki/warianty formatowania).
2. Wpisy o przecięciach TOP pojawiają się stabilnie w `Główne zalety/problemy`.
Pierwszy krok wykonawczy:
- porównywać listy przez znormalizowane klucze nazw.
Wynik:
- `app.py`:
  - dodano normalizację nazw (`_canon_name` przez `slugify(...).lower()`),
  - przecięcia `priority_in_best` / `priority_in_gaps` liczone są po znormalizowanych zbiorach nazw.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-027 [DONE]
Temat: Ostateczne domknięcie przecięć TOP vs chipy (bez filtrowania exact-match po surowych nazwach).
Kryteria ukończenia:
1. Przecięcia TOP z `Najlepsze dopasowania/Największe luki` działają nawet gdy nazwy źródłowe mają inny format.
2. Brak sytuacji, w której lista źródłowa z chipów staje się pusta przez zbyt restrykcyjny filtr.
Pierwszy krok wykonawczy:
- usunąć filtr `name in diff_by_entity` przy pobieraniu nazw z `result['strengths']/result['gaps']` i porównywać po znormalizowanych kluczach.
Wynik:
- `app.py`:
  - źródła chipów są czytane przez `_safe_src_names(...)` bez wymogu exact-match na surowym stringu,
  - przecięcia są liczone po `slugify(...).lower()` (`best_canon` / `gaps_canon`),
  - eliminuje to przypadki, gdzie przecięcie logicznie istnieje, ale nie pojawia się w `Główne problemy`.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-028 [DONE]
Temat: Jedna wspólna legenda kategorii pod wykresami `Profile wartości 0-100` w `🧭 Matching`.
Kryteria ukończenia:
1. W trybie `Wartości` pod dwoma wykresami 0-100 jest jedna wspólna, wyśrodkowana legenda.
2. Legenda ma układ i semantykę jak referencja (`Zmiana`, `Ludzie`, `Porządek`, `Niezależność`).
3. Brak duplikacji legendy pod każdym wykresem osobno.
Pierwszy krok wykonawczy:
- dopracować CSS legendy (`match-wheel-legend`) oraz render HTML po obu wykresach 0-100.
Wynik:
- `app.py`:
  - dodano wrapper `match-wheel-legend-wrap` i odświeżony styl legendy (ramka, padding, wyśrodkowanie),
  - w trybie `Wartość` renderowana jest jedna wspólna legenda pod oboma wykresami.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-029 [DONE]
Temat: Domknięcie wykrywania TOP-priorytetów w `Główne zalety / Główne problemy` zgodnie z realnie wyświetlanymi chipami.
Kryteria ukończenia:
1. Wpis o priorytetach obecnych w `Największe luki` pojawia się, gdy takie przecięcie jest widoczne na ekranie.
2. Źródło do przecięć jest identyczne jak źródło chipów (`strengths_rows/gaps_rows`), bez rozjazdu pól.
3. Działa poprawnie także dla trybu `Wartości`.
Pierwszy krok wykonawczy:
- przepiąć logikę przecięć na `strengths_rows/gaps_rows`, dodać bezpieczne pobieranie nazw + fallback.
Wynik:
- `app.py`:
  - przecięcia TOP są liczone na `strengths_rows/gaps_rows` (te same dane co chipy),
  - `_safe_src_names(...)` obsługuje zarówno dict, jak i string,
  - gdy lista źródłowa jest pusta po parsingu, działa fallback do lokalnego rankingu,
  - normalizacja nazw dla trybu `Wartości` mapuje etykiety wartości na archetypy przed porównaniem.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-030 [DONE]
Temat: Czyszczenie rzeczywistych błędów TypeScript w `archetypy-ankieta` (zgodnie ze screenami z PyCharm).
Kryteria ukończenia:
1. `tsc -p tsconfig.app.json --noEmit` przechodzi bez błędów.
2. Build frontendu przechodzi po poprawkach.
Pierwszy krok wykonawczy:
- naprawić wskazane błędy: `replaceAll`, nieużywane stany/props, błędne pole `item.text`.
Wynik:
- `archetypy-ankieta/src/App.tsx`:
  - usunięto nieużywany stan `personInstr` i jego setter.
- `archetypy-ankieta/src/Questionnaire.tsx`:
  - usunięto nieużywane stany (`fullAcc`, `fullIns`, `fullLoc`) i odpowiadające settery.
- `archetypy-ankieta/src/LikertRow.tsx`:
  - usunięto nieużywany prop `hoveredCol`,
  - poprawiono odczyt pytania z `item.text` na `item.textM` (zgodnie z typem `Ap48Item`).
- `archetypy-ankieta/src/lib/jstStudies.ts`:
  - zastąpiono `replaceAll(...)` wersją kompatybilną z ES2020 (`split/join` w helperze).
- Smoke-check:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Hotfix H-031 [DONE]
Temat: Domknięcie przecięć TOP vs `Najlepsze dopasowania/Największe luki` w `🧭 Matching` dla przypadków rozjazdu źródeł nazw.
Kryteria ukończenia:
1. Wpisy o przecięciach TOP pojawiają się także wtedy, gdy format nazw w źródle chipów różni się od formatu lokalnego rankingu.
2. `Główne problemy` pokazują priorytetowe archetypy obecne w `Największe luki` (przypadek ze screenów 2900/2901).
Pierwszy krok wykonawczy:
- połączyć źródła nazw do przecięć: `strengths_rows/gaps_rows` + lokalne rankingi live i porównywać je po tej samej normalizacji.
Wynik:
- `app.py`:
  - przecięcia TOP dla sekcji `Główne zalety/problemy` liczone są na łączonym źródle nazw:
    - z renderowanych chipów (`strengths_rows`, `gaps_rows`),
    - z rankingów live (`strongest_fit_entities`, `largest_gap_entities`),
  - redukuje to ryzyko „znikania” wpisu przy różnicach formatu źródłowej nazwy.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-032 [DONE]
Temat: Legenda pod `Profile archetypowe 0-100` + naprawa sortowania tabeli porównawczej.
Kryteria ukończenia:
1. W `🧭 Matching -> Podsumowanie` legenda kategorii pod dwoma wykresami 0-100 jest widoczna także w trybie `Archetypy`.
2. Sortowanie po kolumnach tabeli porównawczej (`Profil polityka`, `Oczekiwania mieszkańców`, `Różnica`) działa numerycznie.
Pierwszy krok wykonawczy:
- usunąć warunek renderu legendy tylko dla trybu `Wartość` i przełączyć wartości tabeli z tekstu na liczby `float`.
Wynik:
- `app.py`:
  - legenda `Zmiana/Ludzie/Porządek/Niezależność` renderuje się stale pod sekcją dwóch wykresów 0-100,
  - kolumny liczbowe tabeli porównawczej są trzymane jako liczby (`round(...,1)`), więc sortowanie działa poprawnie.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-033 [DONE]
Temat: `Ustawienia ankiety` (personalne + JST), tryb `Pojedyncze ekrany`, doprecyzowanie kontekstu Demografii i nierozbijanie `(|Δ| ... pp)`.
Kryteria ukończenia:
1. W `⚙️ Ustawienia ankiety` (personalne/JST) między wyborem badania a `Status badania` jest sekcja `Parametry ankiety`.
2. Personalne: sekcje `Wyświetlanie ankiety`, `Nawigacja ankiety`, `Automatyczny start i zakończenie badania`.
3. JST: sekcje `Nawigacja ankiety`, `Automatyczny start i zakończenie badania`.
4. Personalna ankieta ma nowy tryb `Pojedyncze ekrany` z przyciskami `Wstecz`/`Dalej` (opcjonalnie), postępem (opcjonalnie) i zapisem po 48. pytaniu.
5. Zdanie w ankiecie personalnej używa formy `polityka/polityczki` zgodnie z płcią.
6. W `🧭 Matching -> Demografia` jest jasny kontekst: jaki polityk i jaka JST.
7. Frazy `(|Δ| ... pp)` w `Główne zalety/problemy` nie rozbijają się na dwie linie.
Pierwszy krok wykonawczy:
- dodać trwałe pola ustawień ankiety w schemacie DB (studies + jst_studies), podpiąć zapis w panelu i odczyt w frontendzie ankiet.
Wynik:
- `app.py`:
  - `personal_settings_view()`:
    - pogrubiony nagłówek wyboru badania (`+1px`),
    - nowa sekcja `Parametry ankiety`:
      - `Wyświetlanie ankiety`: `Macierz` / `Pojedyncze ekrany`,
      - `Nawigacja ankiety`: `Pokaż pasek postępu`, `Wyświetlaj przycisk Wstecz`,
      - `Losuj kolejność pytań` (obsługa punktu randomizacji),
      - `Automatyczny start i zakończenie badania` (data + godzina),
    - zapis parametrów + jednorazowe przejścia statusu wg harmonogramu.
  - `jst_settings_view()`:
    - pogrubiony nagłówek wyboru badania (`+1px`),
    - nowa sekcja `Parametry ankiety`:
      - `Nawigacja ankiety`,
      - `Automatyczny start i zakończenie badania`,
    - zapis parametrów + jednorazowe przejścia statusu wg harmonogramu.
  - dodano helpery harmonogramu:
    - normalizacja bool/trybu,
    - konwersja data+godzina (Europe/Warsaw -> UTC),
    - automatyczne przejścia `active <-> suspended` dla startu i auto-zawieszenie dla końca (bez trwałego zamykania).
  - `🧭 Matching -> Demografia`: dopisano linię kontekstu `polityk + JST`.
  - `Główne zalety/problemy`: `(|Δ| ... pp)` budowane z NBSP, więc nie łamie linii.
- `db_jst_utils.py`:
  - rozszerzono `ensure_jst_schema()` o kolumny ustawień ankiety dla `jst_studies` i `studies`:
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
  - dodano constraint trybu (`matrix`/`single`) dla obu tabel,
  - `get_jst_study_public` zwraca parametry ankiety,
  - `add_jst_response_by_slug` uwzględnia harmonogram:
    - przed startem blokuje odpowiedzi (status efektywnie `suspended`),
    - po wybiciu startu może aktywować badanie (jednorazowo),
    - po wybiciu końca auto-zawiesza badanie (jednorazowo).
- `archetypy-ankieta/src/lib/studies.ts` i `src/lib/jstStudies.ts`:
  - dodano pola ustawień ankiety do modeli danych,
  - personalne `loadStudyBySlug` pobiera nowe pola (z fallbackiem przy brakach kolumn).
- `archetypy-ankieta/src/App.tsx`:
  - mapowanie ustawień ankiety z DB do stanu aplikacji,
  - status ankiety uwzględnia okna auto-start/auto-end,
  - przekazanie ustawień do `Questionnaire` i `JstSurvey`.
- `archetypy-ankieta/src/Questionnaire.tsx`:
  - przebudowa pod dwa tryby:
    - `matrix` (dotychczasowy układ, z opcjonalną randomizacją kolejności pytań),
    - `single` (jedno pytanie na ekranie, odpowiedzi na kolorowej skali, `Dalej`/`Wyślij`, opcjonalny `Wstecz`, opcjonalny pasek postępu),
  - zapisywanie odpowiedzi nadal idzie po indeksach pytań, więc randomizacja nie psuje kodowania archetypów,
  - fraza `... jako osoby publicznej (polityka/polityczki)` zależna od płci.
- `archetypy-ankieta/src/SingleQuestionnaire.css`:
  - nowy styl trybu `Pojedyncze ekrany`.
- `archetypy-ankieta/src/JstSurvey.tsx` + `src/JstSurvey.css`:
  - dodano sterowanie nawigacją JST z ustawień:
    - opcjonalny pasek postępu,
    - opcjonalny przycisk `Wstecz`.
- Smoke-check:
  - `python -m py_compile app.py db_jst_utils.py` (OK),
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Hotfix H-034 [DONE]
Temat: Smoke-check techniczny po H-033 + domknięcie kolejnego kroku jako UAT na środowisku użytkownika.
Kryteria ukończenia:
1. Lokalne smoke-checki backendu i frontendu przechodzą bez regresji.
2. W `STATUS.md` jest jasno zapisany zakres ręcznego UAT jako kolejny krok (bez restartu analizy repo).
Pierwszy krok wykonawczy:
- uruchomić ponownie minimalny zestaw testów technicznych i zaktualizować `STATUS.md` o bieżący stan i blokery wdrożeniowe.
Wynik:
- Testy lokalne:
  - `python -m py_compile app.py db_jst_utils.py` (OK),
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).
- Kolejny krok operacyjny pozostaje ręcznym UAT UI na środowisku użytkownika (po deployu).

### Hotfix H-035 [DONE]
Temat: Korekty UX po screenach UAT (no-wrap `|Δ|`, estetyka kontekstu Demografii, feedback zapisu, przywrócenie wyglądu macierzy, poprawa desktop `Pojedyncze ekrany`).
Kryteria ukończenia:
1. Fragmenty `(|Δ| ... pp)` w `Główne zalety/problemy` nie rozbijają się na dwie linie.
2. Linia `Kontekst` w `🧭 Matching -> Demografia` ma schludny, czytelny styl.
3. Po kliknięciu `💾 Zapisz parametry ankiety` użytkownik dostaje widoczny komunikat `Zapisano parametry ankiety`.
4. W macierzy wracają kolory nagłówków skali zgodne z referencją (2899) bez przebudowy układu tabeli.
5. Tryb `Pojedyncze ekrany` na desktopie ma zawężony layout, odpowiedzi wyżej, usunięte etykiety nad skalą i lżejsze przyciski `Wstecz/Dalej`.
Pierwszy krok wykonawczy:
- poprawić punktowo `app.py` i `archetypy-ankieta/src/Questionnaire.tsx` + `src/SingleQuestionnaire.css`, bez zmian w niepowiązanych modułach.
Wynik:
- `app.py`:
  - dodano `match-delta-nowrap` i bezpieczny render linii z automatycznym oplataniem `(|Δ| ... pp)` w niełamliwy `<span>`,
  - przebudowano linię `Kontekst` w Demografii na estetyczny chip/pill (bez brzydkiego markdown z backtickami),
  - dodano kompatybilny toast helper (`_toast_success_compat`) i flash po zapisie parametrów ankiety w obu widokach settings.
- `archetypy-ankieta/src/Questionnaire.tsx`:
  - przywrócono paletę kolorów skali pod referencję 2899 (dla nagłówków macierzy i przycisków single-screen),
  - w `Pojedyncze ekrany`:
    - usunięto etykiety `Zdecydowanie się nie zgadzam / ... zgadzam` nad odpowiedziami,
    - `Pamiętaj: ...` przeniesiono na górę i wystylowano na szaro,
    - usunięto pogrubienie nazwiska w zdaniu `Czy zgadzasz... na temat ...?`,
    - przebudowano strukturę pod nowy, zawężony shell desktop.
- `archetypy-ankieta/src/SingleQuestionnaire.css`:
  - zawężono desktopową szerokość treści,
  - podniesiono sekcję odpowiedzi (nieprzyklejona do dolnej krawędzi),
  - uproszczono styl przycisku `Dalej` (mniej dominujący),
  - dopracowano styl `Wstecz` pod referencję mobilną.
- Smoke-check:
  - `python -m py_compile app.py` (OK),
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Hotfix H-036 [DONE]
Temat: Dalsze dopracowanie `Pojedyncze ekrany` (desktop + mobile) po kolejnych screenach UAT.
Kryteria ukończenia:
1. `Dalej` jest zielony (jak pozostałe CTA), czytelny i osadzony niżej pod odpowiedziami.
2. `Wstecz` ma tę samą typografię co `Dalej` i wyraźny hover.
3. Odstępy pytanie ↔ odpowiedzi są większe (desktop i mobile).
4. `Pamiętaj...` jest mniejszy; `Czy zgadzasz...` ma mniejszy rozmiar i wagę `590`.
5. Licznik `1/48` ma `font-size: 0.95rem`.
6. Mobile:
   - większy dystans odpowiedzi od pytania,
   - `Dalej` w prawym dolnym rogu z marginesem od krawędzi,
   - etykiety odpowiedzi mieszczą się w równych kafelkach.
Pierwszy krok wykonawczy:
- dopracować wyłącznie `archetypy-ankieta/src/SingleQuestionnaire.css` (bez zmiany logiki ankiety).
Wynik:
- `SingleQuestionnaire.css`:
  - `Dalej`:
    - styl CTA zielony (`#14b8a6`), hover i cień,
    - desktop: większy odstęp od siatki odpowiedzi,
    - mobile: pozycjonowanie w prawym dolnym rogu z bezpiecznym marginesem (`safe-area`).
  - `Wstecz`:
    - ujednolicona typografia z `Dalej`,
    - dodany hover highlight.
  - typografia i spacing:
    - `single-counter` ustawiony na `0.95rem`,
    - mniejsze `Pamiętaj...`,
    - mniejsze `Czy zgadzasz...` z wagą `590`,
    - większy prześwit między tekstami wprowadzającymi a pytaniem głównym,
    - odpowiedzi przesunięte niżej (większy dystans od pytania).
  - mobile:
    - większy dolny padding treści (miejsce na fixed CTA),
    - ciaśniejsza siatka i mniejszy font etykiet odpowiedzi, by długie etykiety mieściły się w równych kafelkach.
- Smoke-check:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Hotfix H-037 [DONE]
Temat: Stabilizacja geometrii `Pojedyncze ekrany` (hover desktop, stały pasek odpowiedzi mobile, orientacja pozioma).
Kryteria ukończenia:
1. `Dalej` bez cienia.
2. Na desktopie hover odpowiedzi podświetla kafelek kolorem docelowym (lub zbliżonym), a klik utrzymuje stan docelowy.
3. Na mobile teksty i pytanie są niżej, z większym pionowym oddechem.
4. Pasek odpowiedzi na mobile jest w stałym miejscu (bez „skakania” między pytaniami).
5. Dla mobile landscape działa osobne formatowanie, by zmieścić całość na jednym ekranie.
Pierwszy krok wykonawczy:
- dopracować tylko warstwę CSS/UX `SingleQuestionnaire` + drobne style przycisków odpowiedzi (bez zmian w logice ankiety i backendzie).
Wynik:
- `archetypy-ankieta/src/Questionnaire.tsx`:
  - przyciski odpowiedzi przekazują kolory przez zmienne CSS (`--opt-*`) zamiast sztywnego inline `background/border`,
  - umożliwia to spójne style hover/selected sterowane przez CSS.
- `archetypy-ankieta/src/SingleQuestionnaire.css`:
  - usunięto cień z `Dalej` (desktop i mobile),
  - hover/selected dla odpowiedzi:
    - hover podświetla kafelek kolorem danej opcji,
    - selected utrzymuje kolor docelowy,
    - usunięto efekt „unoszenia” jako główny sygnał hover,
  - mobile portrait:
    - większe odsunięcie sekcji pytania w dół,
    - większy prześwit do odpowiedzi,
    - stały pasek odpowiedzi (`position: fixed`) nad przyciskiem `Dalej`,
  - mobile landscape:
    - osobny layout oparty o `@media (orientation: landscape)`,
    - mniejsze fonty i ciaśniejsze odstępy, żeby kluczowe elementy mieściły się na jednym ekranie,
    - stała pozycja paska odpowiedzi i CTA.
- Smoke-check:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Hotfix H-038 [DONE]
Temat: Podniesienie paska odpowiedzi w mobile + tuning landscape + format `x.0` w tabeli Matching bez utraty sortowania liczbowego.
Kryteria ukończenia:
1. Mobile portrait: pasek odpowiedzi jest wyżej i nie ucina ostatniego kafelka.
2. Mobile landscape: treść pytania jest lżejsza, pasek odpowiedzi nie ucina się; `Dalej` przeniesione na górę po prawej.
3. `🧭 Matching` tabela profili pokazuje zawsze 1 miejsce po przecinku (także `76.0`) i dalej sortuje liczbowo.
Pierwszy krok wykonawczy:
- poprawić tylko `SingleQuestionnaire.css`, `Questionnaire.tsx` i punktowo render tabeli w `app.py`.
Wynik:
- `archetypy-ankieta/src/SingleQuestionnaire.css`:
  - mobile portrait:
    - pasek odpowiedzi podniesiony wyżej,
    - dodane `width:auto` + `box-sizing:border-box` w fixed zone, aby uniknąć obcinania ostatniego kafelka,
    - większy oddech pionowy dla bloków tekstowych.
  - mobile landscape:
    - zmniejszona typografia (`Pamiętaj`, lead, pytanie główne),
    - stała strefa odpowiedzi z bezpieczną szerokością,
    - `Dalej` przeniesiony na górę po prawej.
  - utrzymano brak cienia CTA i kolorowe hover/selected odpowiedzi.
- `archetypy-ankieta/src/Questionnaire.tsx`:
  - zachowano sterowanie kolorami opcji przez CSS variables (`--opt-*`) dla hover/selected.
- `app.py`:
  - tabela porównawcza w `🧭 Matching` dostała `column_config` z `NumberColumn(format="%.1f")` dla trzech kolumn liczbowych:
    - `Profil polityka`,
    - `Oczekiwania mieszkańców (...)`,
    - `Różnica |Δ|`,
  - fallback kompatybilny dla starszego Streamlit (`TypeError` -> render bez `column_config`).
- Smoke-check:
  - `python -m py_compile app.py` (OK),
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Hotfix H-039 [DONE]
Temat: Mobile-only polish `Pojedyncze ekrany` + stabilizacja macierzy po obrocie + ukrycie logo na mobile w macierzy.
Kryteria ukończenia:
1. Mobile portrait: pasek odpowiedzi jest wyżej.
2. Mobile portrait: tekst `Czy zgadzasz się...` jest trochę większy.
3. Mobile landscape: `Dalej` jest w prawym górnym rogu, a licznik (`x/48`) na środku pod paskiem postępu.
4. Matrix mobile: po obrocie z pionu na poziom ankieta nie znika na biały ekran.
5. Matrix mobile: na ekranie macierzy nie pokazujemy logo w prawym górnym rogu.
Pierwszy krok wykonawczy:
- dopracować `Questionnaire.tsx` i `SingleQuestionnaire.css` bez zmian poza zakresem mobile/layout.
Wynik:
- `archetypy-ankieta/src/Questionnaire.tsx`:
  - detekcja viewport/orientacji została przepięta na reaktywny stan `viewport` (`width/height`) aktualizowany przez:
    - `resize`,
    - `orientationchange`,
    - `visualViewport.resize`.
  - warunek ekranu `obróć telefon` dla macierzy opiera się teraz o bieżący viewport (`isMobileViewport + orientation`),
    co stabilizuje przejście pion -> poziom na telefonie,
  - logo `Badania.pro` w nagłówku macierzy jest ukrywane na mobile (`isMobileViewport`).
- `archetypy-ankieta/src/SingleQuestionnaire.css`:
  - mobile portrait:
    - podniesiono fixed pasek odpowiedzi (`bottom`),
    - zwiększono rozmiar `Czy zgadzasz...`.
  - mobile landscape:
    - licznik ustawiono centralnie pod paskiem postępu,
    - `Dalej` przesunięto wyżej do prawego górnego rogu (strefa nawigacji).
- Smoke-check:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Hotfix H-040 [DONE]
Temat: Ustabilizowanie geometrii single-screen (desktop + mobile), tryb pełnego ekranu mobile (best effort) oraz fallback obrotu dla macierzy.
Kryteria ukończenia:
1. Desktop: pasek odpowiedzi ma stałą pozycję (bez „wędrowania” między pytaniami).
2. Mobile landscape: `Dalej` ustawione na wysokości `Wstecz`.
3. Mobile: po `Zaczynamy` uruchamiamy tryb pełnego ekranu (best effort), aby minimalizować widoczność paska adresu.
4. Matrix mobile: po obrocie do poziomu dodany fallback odświeżenia bieżącej strony ankiety (bez powrotu do ekranu powitalnego).
Pierwszy krok wykonawczy:
- poprawić `SingleQuestionnaire.css`, `App.tsx`, `Questionnaire.tsx` i punktowo meta viewport w `index.html`.
Wynik:
- `archetypy-ankieta/src/SingleQuestionnaire.css`:
  - desktop:
    - pasek odpowiedzi i strefa `Dalej` przypięte do stałych pozycji (fixed),
    - wyeliminowane przesuwanie paska odpowiedzi między pytaniami,
  - mobile:
    - poprawiono resety (`left/transform/width`) w media-query, żeby uniknąć konfliktu z desktop fixed,
    - w landscape `Dalej` podniesione do wysokości nawigacji (`Wstecz`).
- `archetypy-ankieta/src/App.tsx`:
  - dodano `tryEnterFullscreenMobile()` (Fullscreen API, best effort) wywoływane po kliknięciu `Zaczynamy` oraz po wejściu do trybu ankiety,
  - dodano hash `#q` dla stanu „ankieta uruchomiona”, aby po lokalnym reloadzie nie wracać do ekranu powitalnego,
  - `Questionnaire` opakowany `AppErrorBoundary` (koniec z „czystą białą stroną” przy runtime error).
- `archetypy-ankieta/src/Questionnaire.tsx`:
  - dla `displayMode === matrix` dodano fallback `orientationchange -> reload` (z guardem czasowym),
    aby po obrocie telefonu wymusić czysty render bieżącej strony ankiety.
- `archetypy-ankieta/index.html`:
  - dodano meta `viewport-fit=cover`, `mobile-web-app-capable`, `apple-mobile-web-app-capable`, `theme-color`.
- Smoke-check:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Hotfix H-041 [DONE]
Temat: Pilna naprawa regresji po H-040 (error #310 w macierzy mobile + korekta geometrii single-screen desktop/mobile).
Kryteria ukończenia:
1. Macierz mobile po obrocie nie wywala `Minified React error #310`.
2. W mobile landscape układ wraca do poprzedniego wzorca; `Dalej` tylko podniesione do linii `Wstecz`.
3. Desktop: pasek odpowiedzi jest stabilny, ale na wysokości referencyjnej (nie przy samym dole).
Pierwszy krok wykonawczy:
- usunąć problematyczny fallback obrotu i naprawić kolejność hooków, potem dostroić pozycjonowanie CSS.
Wynik:
- `archetypy-ankieta/src/Questionnaire.tsx`:
  - usunięto `useEffect` z `orientationchange -> reload` (regresyjny fallback),
  - usunięto `useMemo` dla `singleProgress` i zamieniono na zwykłą kalkulację,
  - dzięki temu zniknęła pułapka nierównej liczby hooków przy przejściu przez ekran `obróć telefon`.
- `archetypy-ankieta/src/SingleQuestionnaire.css`:
  - desktop:
    - strefę odpowiedzi podniesiono do wysokości referencyjnej (`bottom: clamp(180px, 24vh, 250px)`),
    - `Dalej` ustawiono pod paskiem odpowiedzi (`bottom: clamp(104px, 14vh, 156px)`),
  - mobile landscape:
    - `Dalej` podniesione do linii `Wstecz` (`top`),
    - dodano dodatkowy media-query `max-height:560px` dla telefonów poziomo z dużą szerokością viewport.
- Smoke-check:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Hotfix H-042 [DONE]
Temat: Dopięcie typografii i geometrii mobile + matrix mobile header po ukryciu logo.
Kryteria ukończenia:
1. Teksty pytań i leadów nie zostawiają jednoliterowych/dwuliterowych „sierot” na końcu linii.
2. Mobile landscape: `Dalej` jest niżej, tuż pod paskiem postępu i na linii nawigacji.
3. Mobile portrait: pasek odpowiedzi jest jeszcze wyżej.
4. Matrix mobile: po ukryciu logo nie zostaje pusta „bariera” po prawej stronie nagłówka.
Pierwszy krok wykonawczy:
- poprawić `Questionnaire.tsx` i `SingleQuestionnaire.css` bez zmian poza UI/typografią.
Wynik:
- `archetypy-ankieta/src/Questionnaire.tsx`:
  - dodano `withHardSpaces(...)` (klejenie krótkich słów przez NBSP),
  - zastosowano do: pytania single, lead/sublead single, lead/remember matrix oraz pytań wierszy macierzy,
  - nagłówek macierzy na mobile ma teraz pełną szerokość treści (`flex:1; minWidth:0`), więc znika puste miejsce po logo.
- `archetypy-ankieta/src/SingleQuestionnaire.css`:
  - mobile portrait: pasek odpowiedzi podniesiony (`bottom +150px`),
  - mobile landscape: `Dalej` obniżone do linii pod paskiem postępu (`top +58px`) w obu wariantach landscape.
- Smoke-check:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Hotfix H-043 [DONE]
Temat: Dalszy polish `Pojedyncze ekrany` (NBSP + Enter + mobile geometry) oraz stabilizacja orientacji macierzy.
Kryteria ukończenia:
1. Klejenie wyrazów obejmuje także: `do`, `dla`, `to`, `co`, `mu` oraz frazy `gdzie inni`, `nawet jeśli`.
2. W `Pojedyncze ekrany` klawisz `Enter` działa jak klik aktywnego `Dalej` (po zaznaczeniu odpowiedzi).
3. Mobile landscape: `Dalej` jest pod paskiem postępu, na linii nawigacji.
4. Matrix mobile: po sekwencji obrotów nie zostaje fałszywy ekran `obróć telefon poziomo`.
5. Mobile portrait: pasek odpowiedzi jest jeszcze wyżej.
Pierwszy krok wykonawczy:
- dopracować punktowo `archetypy-ankieta/src/Questionnaire.tsx` i `src/SingleQuestionnaire.css`, bez zmian poza zakresem UX/layout.
Wynik:
- `archetypy-ankieta/src/Questionnaire.tsx`:
  - helper `withHardSpaces` wzmacnia klejenie fraz przez zamianę wszystkich białych znaków w dopasowaniu na NBSP,
  - detekcja viewport/orientacji używa `readViewport()` (priorytet `visualViewport`) i bardziej odpornej logiki fallback,
  - odświeżanie viewport dla macierzy przyspieszone (`180ms`) dla szybszej reakcji po obrocie.
- `archetypy-ankieta/src/SingleQuestionnaire.css`:
  - mobile portrait: pasek odpowiedzi podniesiony (`bottom +174px`) i zwiększony bufor dolny treści,
  - mobile landscape: `Dalej` przesunięty wyżej (`top +44px`) w obu wariantach landscape.
- Smoke-check:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Hotfix H-044 [DONE]
Temat: Domknięcie regresji hooków przy obrocie macierzy + desktopowy skrót `←` oraz dalszy tuning mobile landscape.
Kryteria ukończenia:
1. Matrix mobile nie wywala już błędów React `#300/#310` przy sekwencji obrotów.
2. W single-screen `←` działa jak `Wstecz` (desktop/klawiatura).
3. Typografia mobile landscape (`Pamiętaj`, `Czy zgadzasz...`) jest większa i czytelna.
4. W mobile landscape `Dalej` wraca bliżej linii nawigacji pod paskiem postępu.
Pierwszy krok wykonawczy:
- poprawić punktowo `Questionnaire.tsx` i `SingleQuestionnaire.css`, bez zmian poza ankietą frontendową.
Wynik:
- `archetypy-ankieta/src/Questionnaire.tsx`:
  - usunięto warunkowy `return` orientacji sprzed części hooków (teraz `showOrientationWarning` renderowane dopiero po wszystkich hookach),
  - dodano dodatkowe sklejenia fraz: `których reprezentuje`, `jest podstawą`, `których głos`,
  - w keydown single-screen dodano `ArrowLeft => handleSingleBack()` (gdy `allowBack` i nie pierwszy ekran).
- `archetypy-ankieta/src/SingleQuestionnaire.css`:
  - mobile landscape: większe fonty `single-sublead` i `single-lead`,
  - zwiększono górny oddech treści (`single-question-zone`),
  - `Dalej` podniesione bliżej nawigacji (`top +34px`) w obu wariantach landscape.
- Smoke-check:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Hotfix H-045 [DONE]
Temat: Czytelność mobile (portrait/landscape) + `→` jako przejście do kolejnego pytania.
Kryteria ukończenia:
1. Mobile: `Pamiętaj...` i `Czy zgadzasz...` są wyraźniej czytelne.
2. Mobile portrait: pytanie startuje nieco wcześniej (mniejszy górny margines sekcji tekstu).
3. Mobile landscape: `Dalej` jest jeszcze wyżej (bliżej linii nawigacji).
4. Desktop/single-screen: `ArrowRight` działa jak przejście do następnego ekranu, o ile bieżące pytanie ma odpowiedź.
Pierwszy krok wykonawczy:
- punktowy tuning `SingleQuestionnaire.css` + rozszerzenie skrótów klawiaturowych w `Questionnaire.tsx`.
Wynik:
- `archetypy-ankieta/src/SingleQuestionnaire.css`:
  - portrait:
    - zmniejszony górny margines sekcji pytań (`single-question-zone`),
    - większe fonty `single-sublead` i `single-lead`,
  - landscape:
    - większe fonty `single-sublead` i `single-lead`,
    - lekko większy górny oddech treści,
    - `Dalej` podniesione (`top +22px`) w obu wariantach landscape.
- `archetypy-ankieta/src/Questionnaire.tsx`:
  - dodano obsługę `ArrowRight` (`→`) jako `Dalej/Wyślij` po zaznaczeniu odpowiedzi.
- Smoke-check:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Hotfix H-046 [DONE]
Temat: Mikro-typografia mobile landscape (większa czytelność leadów i większy odstęp po `Czy zgadzasz...`).
Kryteria ukończenia:
1. W mobile landscape `Pamiętaj...` i `Czy zgadzasz...` są większe i lepiej czytelne.
2. Po `Czy zgadzasz...` jest większy odstęp przed pytaniem głównym.
3. Pytanie główne jest dodatkowo powiększone (około +2px).
Pierwszy krok wykonawczy:
- wykonać punktowy tuning tylko `SingleQuestionnaire.css` w obu wariantach landscape (`max-width:900` i `max-height:560`).
Wynik:
- `archetypy-ankieta/src/SingleQuestionnaire.css`:
  - landscape:
    - `single-sublead` i `single-lead` zwiększone,
    - dodany większy `margin-bottom` po `single-lead`,
    - `single-question-text` powiększony i odsunięty niżej (`margin-top`),
  - low-height landscape:
    - analogiczne zwiększenie fontów i odstępu.
- Smoke-check:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Hotfix H-047 [DONE]
Temat: Poprawa automatycznej odmiany JST w `➕ Dodaj badanie mieszkańców` dla nazw zakończonych na `-o`.
Kryteria ukończenia:
1. Auto-uzupełnianie nie tworzy błędnych form typu `Testowoa`, `Testowoowi`.
2. Dla nazw typu `Testowo` generowane są poprawne formy:
   - dopełniacz `Testowa`,
   - celownik `Testowu`,
   - biernik `Testowo`,
   - narzędnik `Testowem`,
   - miejscownik `Testowie`.
Pierwszy krok wykonawczy:
- poprawić heurystykę w `app.py` (`_guess_word_cases`) przez dedykowaną gałąź dla nazw kończących się na `-o`.
Wynik:
- `app.py`:
  - dodano regułę dla nazw miejscowych nijakich kończących się na `-o` (np. `Testowo`, `Braniewo`, `Gniezno`),
  - reguła działa przed fallbackiem spółgłoskowym, więc nie powstają już formy z doklejonym `...oa/...owi`.
- Smoke-check:
  - `python -m py_compile app.py` (OK),
  - kontrolny probe funkcji dla `Testowo/Braniewo/Gniezno` (OK).

### Hotfix H-048 [DONE]
Temat: Dopięcie klejenia fraz w ankiecie + wyjątki dla nieregularnych nazw JST.
Kryteria ukończenia:
1. W pytaniach ankiety frazy:
   - `nawet jeśli jest`,
   - `nawet jeśli koszt`
   nie rozbijają się między liniami.
2. Auto-odmiana JST ma słownik wyjątków dla nieregularnych nazw (bardziej odporna niż sama heurystyka końcówek).
Pierwszy krok wykonawczy:
- dodać wzorce do `withHardSpaces` w `Questionnaire.tsx` i słownik override do odmiany JST w `app.py`.
Wynik:
- `archetypy-ankieta/src/Questionnaire.tsx`:
  - rozszerzono `PHRASE_GLUE_PATTERNS` o:
    - `nawet jeśli jest`,
    - `nawet jeśli koszt`.
- `app.py`:
  - dodano `JST_WORD_CASE_OVERRIDES` (m.in. `Ełk`, `Sopot`, `Kielce`, `Katowice`, `Suwałki`, `Tychy`, `Zakopane`),
  - dodano `JST_PHRASE_CASE_OVERRIDES` (m.in. `Zielona Góra`, `Nowy Sącz`),
  - `_guess_word_cases` i `_guess_phrase_cases` najpierw sprawdzają wyjątki, potem lecą heurystyki.
- Smoke-check:
  - `python -m py_compile app.py` (OK),
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK),
  - kontrolny probe funkcji odmiany dla wyjątków (OK).

### Hotfix H-049 [DONE]
Temat: JST mobile/dark mode + licznik uczestników w podglądzie raportu publicznego.
Kryteria ukończenia:
1. JST (`jst.badania.pro`) nie wymusza chwilowo obrotu do poziomu.
2. W pytaniach suwakowych JST oś suwaka jest czytelna w trybie ciemnym.
3. W publicznym podglądzie raportu (token/email) jest na górze estetyczny licznik uczestników badania.
Pierwszy krok wykonawczy:
- poprawić punktowo `archetypy-ankieta/src/JstSurvey.tsx`, `archetypy-ankieta/src/JstSurvey.css` i `archetypy-admin/app.py`.
Wynik:
- `archetypy-ankieta/src/JstSurvey.tsx`:
  - dodano flagę `ENFORCE_JST_LANDSCAPE_ON_MOBILE = false`,
  - warunek `shouldRotate` został podpięty pod tę flagę (obligo obrotu wyłączone tymczasowo).
- `archetypy-ankieta/src/JstSurvey.css`:
  - w dark mode zwiększono kontrast toru suwaka (`::-webkit-slider-runnable-track`, `::-moz-range-track`),
  - dodano obrys/box-shadow toru i jaśniejsze ticki (`.jst-tick`) dla lepszej widoczności osi.
- `archetypy-admin/app.py`:
  - w `public_report_view` dodano pobranie liczby odpowiedzi (`fetch_personal_response_count`),
  - dodano górny kafelek „X uczestników badania” (responsive + dark mode friendly).
- Smoke-check:
  - `python -m py_compile app.py` (OK),
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Hotfix H-050 [DONE]
Temat: Korekta układu licznika w raporcie publicznym + dopracowanie suwaka JST (dark + wyrównanie B).
Kryteria ukończenia:
1. W raporcie publicznym licznik uczestników jest w tej samej linii co nagłówek `Informacje na temat archetypów ...` (tytuł po lewej, licznik po prawej).
2. Oś suwaka JST w dark mode jest wyraźnie widoczna.
3. Teksty po stronie B pod suwakami są wyrównane do prawej.
Pierwszy krok wykonawczy:
- przenieść render licznika z `app.py` do `admin_dashboard.py::show_report(public_view=True)` i dopracować style suwaka w `JstSurvey.css`.
Wynik:
- `archetypy-admin/admin_dashboard.py`:
  - w `show_report(..., public_view=True)` nagłówek raportu ma teraz wspólny wiersz:
    - lewa strona: `Informacje na temat archetypów ...`,
    - prawa strona: licznik `X uczestnik(ów) badania`,
  - dodano responsywny i dark-mode-friendly styl dla tego wiersza.
- `archetypy-admin/app.py`:
  - usunięto wcześniejszy, globalnie wstrzyknięty kafelek licznika nad raportem publicznym (żeby nie „uciekał” w prawy górny róg).
- `archetypy-ankieta/src/JstSurvey.css`:
  - w dark mode wzmocniono tor suwaka (jaśniejszy kolor, obrys, mocniejszy kontrast),
  - ticki osi są grubsze i jaśniejsze,
  - prawa etykieta B pod suwakami wyrównana do prawej (`.jst-slider-head > span:last-child { text-align:right; }`).
- Smoke-check:
  - `python -m py_compile app.py admin_dashboard.py` (OK),
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Hotfix H-051 [DONE]
Temat: Eliminacja warningu `email_subject` w „Wyślij link do ankiety” + dalsze wzmocnienie toru suwaka JST w dark mode.
Kryteria ukończenia:
1. Przy przejściu na metodę `E-mail` nie pojawia się warning Streamlit:
   `The widget with key "email_subject" was created with a default value but also had its value set via the Session State API.`
2. Tor suwaka (linia, po której przesuwa się kropka) jest wyraźnie widoczny w dark mode na mobile.
Pierwszy krok wykonawczy:
- poprawić inicjalizację `email_subject` w `send_link.py`, a następnie dodać niezależną warstwę toru suwaka w `JstSurvey.css`.
Wynik:
- `archetypy-admin/send_link.py`:
  - `st.text_input(..., key="email_subject")` nie używa już jednocześnie parametru `value=...`,
  - źródłem wartości pola pozostaje wyłącznie `st.session_state`, więc warning zniknie.
- `archetypy-ankieta/src/JstSurvey.css`:
  - dodano stałą warstwę toru suwaka (`.jst-range-wrap::before`) widoczną niezależnie od stylowania pseudo-elementów przeglądarki,
  - tor ma wyższy kontrast w dark mode (jaśniejszy kolor, obrys, shadow),
  - input range ustawiony nad warstwą toru (`z-index`) tak, by interakcja działała bez zmian.
- Smoke-check:
  - `python -m py_compile send_link.py app.py` (OK),
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Hotfix H-052 [DONE]
Temat: Korekta estetyki toru suwaka JST po regresji wizualnej (dark mode mobile).
Kryteria ukończenia:
1. Tor suwaka wraca do subtelnego wyglądu (bez „ciężkiej” dodatkowej warstwy).
2. W dark mode zostaje tylko delikatnie jaśniejsze tło/obramowanie toru, zgodne z poprzednim stylem.
Pierwszy krok wykonawczy:
- cofnąć agresywną warstwę `.jst-range-wrap::before` i zostawić lekki tuning samych tracków `range`.
Wynik:
- `archetypy-ankieta/src/JstSurvey.css`:
  - usunięto dodatkową warstwę toru (`.jst-range-wrap::before`),
  - przywrócono klasyczny układ suwaka bez dodatkowego `z-index`,
  - dark mode: tor suwaka ma subtelnie jaśniejsze tło i cienkie obramowanie (bez mocnych gradientów/shadow),
  - ticki wróciły do cieńszego, lżejszego stylu.
- Smoke-check:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Hotfix H-053 [DONE]
Temat: Dalsze rozjaśnienie toru suwaka JST w dark mode (mobile).
Kryteria ukończenia:
1. Tor suwaka jest wyraźnie jaśniejszy niż w H-052, ale nadal subtelny.
Pierwszy krok wykonawczy:
- podnieść jasność `background` + lekko podbić `border` i `inset` toru `range` tylko w dark mode.
Wynik:
- `archetypy-ankieta/src/JstSurvey.css`:
  - dark mode:
    - `background` toru: `#315f7b`,
    - `border`: jaśniejszy (`rgba(170, 203, 226, 0.42)`),
    - delikatnie mocniejszy wewnętrzny highlight (`inset`).
- Smoke-check:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Hotfix H-054 [DONE]
Temat: Wymuszenie wysokiej widoczności toru suwaka JST w dark mode na mobile.
Kryteria ukończenia:
1. Tor suwaka jest wyraźnie widoczny nawet wtedy, gdy przeglądarka słabo wspiera stylowanie pseudo-elementów `range`.
Pierwszy krok wykonawczy:
- rozjaśnić jednocześnie `::-webkit-slider-runnable-track`, `::-moz-range-track` oraz bazowy `.jst-range` (fallback).
Wynik:
- `archetypy-ankieta/src/JstSurvey.css`:
  - dark mode:
    - tor suwaka ustawiony na wyraźnie jaśniejszy kolor (`#7394ac`),
    - jaśniejsze obramowanie i highlight wewnętrzny,
    - dodany fallback na samym `.jst-range` (ta sama jasna oś),
    - ticki osi dodatkowo rozjaśnione.
- Smoke-check:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Hotfix H-055 [DONE]
Temat: Usuwanie pojedynczych i wielu wypełnień JST w `💾 Import i eksport baz danych`.
Kryteria ukończenia:
1. W tabeli odpowiedzi JST można zaznaczyć rekordy checkboxami.
2. Dostępny jest przycisk `Usuń zaznaczone` z potwierdzeniem operacji.
3. Usuwanie działa dla wielu rekordów naraz i odświeża widok po operacji.
Pierwszy krok wykonawczy:
- dodać backendową funkcję kasowania odpowiedzi po `respondent_id` oraz podpiąć ją pod UI tabeli eksportu w `app.py`.
Wynik:
- `db_jst_utils.py`:
  - dodano `delete_jst_responses_by_respondent_ids(...)` (batch delete po `respondent_id` w obrębie `study_id`).
- `app.py` (`jst_io_view`):
  - tabela eksportu ma kolumnę `Usuń` (checkbox),
  - dodano akcję `🗑️ Usuń zaznaczone` + etap potwierdzenia,
  - po usunięciu rekordów widok odświeża się i pokazuje komunikat o liczbie usuniętych odpowiedzi.
- Smoke-check:
  - `python -m py_compile app.py db_jst_utils.py` (OK).
