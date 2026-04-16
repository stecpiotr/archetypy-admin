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

### Hotfix H-056 [DONE]
Temat: `📊 Sprawdź wyniki badania archetypu` pokazywało starą kartę archetypu po podmianie PNG.
Kryteria ukończenia:
1. Po podmianie `assets/card/*.png` raport pokazuje aktualny plik bez restartu usługi.
2. Wybór pliku karty jest deterministyczny i preferuje dokładne dopasowanie nazwy.
Pierwszy krok wykonawczy:
- poprawić cache data URI kart (cache-buster po `mtime/size`) i utwardzić `_card_file_for(...)`.
Wynik:
- `admin_dashboard.py`:
  - `_card_file_for(...)` działa teraz dwuetapowo:
    - najpierw dokładne dopasowanie nazwy,
    - dopiero potem deterministyczny fallback prefiksowy,
  - `_file_to_data_uri(...)` otrzymało parametr `cache_buster`,
  - `_archetype_card_data_uri(...)` używa tokenu opartego o `mtime_ns` i `size` pliku,
  - dodano `_archetype_card_cache_token(...)` i podpięto go przy renderze sekcji kart (`5.1.2`).
- Smoke-check:
  - `python -m py_compile admin_dashboard.py` (OK).

### Hotfix H-057 [DONE]
Temat: Reguła kolejności przy remisach w tabeli `Podsumowanie archetypów (liczebność i natężenie)`.
Kryteria ukończenia:
1. Przy tej samej wartości `%` o kolejności decyduje kolejno:
   - `Główny archetyp`,
   - `Wspierający archetyp`,
   - `Poboczny archetyp`,
   - a na końcu alfabetycznie.
2. `%` porównywane jest tak, jak w tabeli (1 miejsce po przecinku).
Pierwszy krok wykonawczy:
- poprawić sortowanie w `admin_dashboard.py` i usunąć wtórne sortowanie DataFrame po samym `%`, które kasowało tie-break.
Wynik:
- `admin_dashboard.py`:
  - dodano `_summary_rank_key(...)` z logiką:
    `(-pct_1dp, -main_cnt, -aux_cnt, -supp_cnt, alpha)`,
  - usunięto dodatkowe sortowanie DataFrame po `_sort`.
- Smoke-check:
  - `python -m py_compile admin_dashboard.py` (OK).

### Hotfix H-058 [DONE]
Temat: iPhone 15 Pro — czytelność ekranu powitalnego i brak nakładania paska odpowiedzi + realna transliteracja SMS JST.
Kryteria ukończenia:
1. Ekran powitalny ankiety personalnej ma czytelny, ciemny tekst również przy dark mode iOS.
2. W `Pojedynczych ekranach` (mobile portrait) pasek odpowiedzi nie nachodzi na treść pytania.
3. Wysyłka SMS JST transliteruje polskie znaki w realnym payloadzie wysyłanym do bramki (nie tylko w podglądzie).
Pierwszy krok wykonawczy:
- poprawić punktowo `archetypy-ankieta/src/App.tsx`, `archetypy-ankieta/src/SingleQuestionnaire.css` i `archetypy-admin/send_link_jst.py`.
Wynik:
- `archetypy-ankieta/src/App.tsx`:
  - wymuszono ciemny kolor tekstu (`wrapperStyle.color`) na białym tle welcome screen,
  - doprecyzowano kolor bloku powitalnego treści.
- `archetypy-ankieta/src/SingleQuestionnaire.css`:
  - mobile portrait:
    - zmniejszono górny offset sekcji pytania,
    - wycofano `position: fixed` dla strefy odpowiedzi i akcji (`Dalej`),
    - odpowiedzi i przycisk są teraz w naturalnym flow pod pytaniem (z większym odstępem),
    - dzięki temu pasek odpowiedzi nie nakłada się na tekst pytania na iPhone.
- `archetypy-admin/send_link_jst.py`:
  - transliteracja `_strip_pl_diacritics(...)` jest stosowana przy:
    - wysyłce nowego SMS JST (`send_btn`),
    - zapisie treści SMS JST do rekordu wysyłki,
    - ponownej wysyłce (`_resend_sms_row`).
- Smoke-check:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK),
  - `python -m py_compile send_link_jst.py` (OK).

### Hotfix H-070 [DONE]
Temat: iPhone mobile — ucięcie końcówki pytania + korekta etykiet kafelków odpowiedzi.
Kryteria ukończenia:
1. W mobile portrait długie pytanie nie jest ucinane po prawej stronie.
2. W kafelku odpowiedzi etykieta `ani tak, ani nie` jest łamana do dwóch linii:
   - `ani tak,`
   - `ani nie`
3. Etykiety z długim słowem `zdecydowanie` nie wychodzą poza kafelek.
Pierwszy krok wykonawczy:
- punktowo dostroić render etykiety odpowiedzi w `Questionnaire.tsx` i mikrotypografię mobile w `SingleQuestionnaire.css`.
Wynik:
- `archetypy-ankieta/src/Questionnaire.tsx`:
  - dla single-screen etykieta `ani tak, ani nie` jest renderowana jawnie w 2 liniach (`ani tak,` + `<br />` + `ani nie`).
- `archetypy-ankieta/src/SingleQuestionnaire.css`:
  - przyciski skali mają `white-space: pre-line` (obsługa ręcznego złamania),
  - wymuszono bezpieczne łamanie (`word-break: break-word`, `overflow-wrap: anywhere`),
  - dla małych ekranów (`max-width:430px`) zmniejszono font i padding etykiet kafelków,
  - w mobile portrait dla pytania głównego dodano bezpieczne łamanie/hyphenation, żeby uniknąć ucięcia końcówki tekstu,
  - dołożono zabezpieczenie iOS pod ciasny viewport:
    - `overflow-x: hidden` dla roota,
    - `min-width: 0` dla kafelków,
    - ciaśniejszą typografię kafelków na `max-width: 430px`,
    - pełną szerokość + `box-sizing` + padding dla bloku pytania.
- Smoke-check:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Hotfix H-059 [DONE]
Temat: Powiadomienia e-mail po nowych odpowiedziach (personalne + JST) z poziomu `⚙️ Ustawienia ankiety`.
Kryteria ukończenia:
1. W ustawieniach ankiety jest opcja `Wysyłaj powiadomienie po uzyskaniu odpowiedzi`.
2. Po zaznaczeniu opcji aktywuje się pole adresu e-mail.
3. Dla nowych odpowiedzi system wysyła e-mail z tytułem badania, linkiem do ankiety i łączną liczbą odpowiedzi.
4. Rozwiązanie działa dla ankiet personalnych i JST.
Pierwszy krok wykonawczy:
- dodać pola konfiguracyjne do schematu `studies/jst_studies`, podpiąć je pod UI ustawień i uruchomić dispatcher e-mail.
Wynik:
- `db_jst_utils.py`:
  - rozszerzono schemat `jst_studies` i `studies` o pola:
    - `survey_notify_on_response`,
    - `survey_notify_email`,
    - `survey_notify_last_count`,
    - `survey_notify_last_sent_at`,
  - nowe pola są uwzględnione także przy `insert_jst_study(...)`.
- `db_utils.py`:
  - `insert_study(...)` ustawia domyślne wartości pól powiadomień.
- `app.py`:
  - w `personal_settings_view` i `jst_settings_view` dodano sekcję `Powiadomienia`:
    - checkbox aktywujący,
    - pole e-mail aktywne po zaznaczeniu checkboxa,
    - walidację poprawności adresu e-mail,
  - po aktywacji powiadomień baseline `survey_notify_last_count` ustawiany jest na aktualny licznik odpowiedzi (bez wysyłki historycznych alertów),
  - dodano dispatcher `_run_response_notifications_dispatcher()`:
    - działa dla badań personalnych i JST,
    - wykrywa wzrost licznika odpowiedzi,
    - wysyła e-mail:
      - `Została udzielona odpowiedź w badaniu {tytuł}, dostępnym pod adresem {link}.`
      - `Łączna liczba wypełnionych ankiet dla tego badania to: {N}.`
    - po sukcesie aktualizuje `survey_notify_last_count` i `survey_notify_last_sent_at`.
- Smoke-check:
  - `python -m py_compile app.py db_jst_utils.py db_utils.py` (OK).

### Hotfix H-060 [DONE]
Temat: Korekta treści powiadomień + natychmiastowość wysyłki + skróty klawiaturowe w ankiecie JST.
Kryteria ukończenia:
1. Powiadomienie nie wymaga ręcznego odświeżania panelu / ponownego logowania.
2. Personalne: tytuł i treść używają poprawnej formy (`archetypu {imię i nazwisko w dopełniaczu}`).
3. JST: tytuł i treść używają poprawnej formy (`mieszkańców {nazwa JST w dopełniaczu}`).
4. Ankieta JST (`jst.badania.pro`) wspiera desktopowe skróty klawiaturowe:
   - `Enter` = `Przejdź dalej` / `Wyślij`,
   - `ArrowRight` = dalej,
   - `ArrowLeft` = wstecz (jeśli wstecz włączone).
Pierwszy krok wykonawczy:
- przebudować dispatcher powiadomień w `app.py` na pętlę w tle + skorygować formatowanie etykiet badania i dodać keydown handler do `JstSurvey.tsx`.
Wynik:
- `app.py`:
  - powiadomienia działają przez dispatcher w tle uruchamiany raz per proces (`@st.cache_resource` + thread),
  - usunięto zależność od ręcznego odświeżenia panelu do wysłania alertu,
  - poprawiono składnię treści i tytułów:
    - personalne: `... w badaniu archetypu {imię+nazwisko gen} ({miasto})`,
    - JST: `... w badaniu mieszkańców {JST w dopełniaczu}`.
- `archetypy-ankieta/src/JstSurvey.tsx`:
  - dodano obsługę klawiatury na desktopie:
    - `Enter` i `ArrowRight` przechodzą do kolejnego kroku (z walidacją jak przy kliknięciu),
    - `ArrowLeft` uruchamia `Wstecz` (z poszanowaniem `allowBack`),
    - skróty nie działają podczas focusu w polach `input/textarea/select`, żeby nie psuć wpisywania danych.
- Smoke-check:
  - `python -m py_compile app.py db_jst_utils.py db_utils.py` (OK),
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Hotfix H-061 [DONE]
Temat: Fundament modelu `metryczka konfigurowalna` dla JST (rdzeń 5 pytań + pytania dodatkowe).
Kryteria ukończenia:
1. Jest jawny model danych metryczki z wersjonowaniem i walidacją.
2. Definicja metryczki jest przechowywana per badanie JST.
3. Nowe badania JST dostają domyślną konfigurację 5 pytań.
4. Aktualizacja badania normalizuje konfigurację i pilnuje spójności rdzenia.
Pierwszy krok wykonawczy:
- dodać moduł modelu metryczki + kolumny w `jst_studies` + podpiąć default/normalizację w warstwie DB.
Wynik:
- dodano nowy moduł `metryczka_config.py`:
  - domyślny model metryczki (`default_jst_metryczka_config`),
  - normalizator/walidator (`normalize_jst_metryczka_config`),
  - utrzymanie niezmiennego rdzenia 5 pytań (`M_PLEC`, `M_WIEK`, `M_WYKSZT`, `M_ZAWOD`, `M_MATERIAL`),
  - obsługa pytań dodatkowych (`scope=custom`) z kontrolą kolizji `db_column`.
- `db_jst_utils.py`:
  - `ensure_jst_schema()` rozszerza `jst_studies` o:
    - `metryczka_config JSONB`,
    - `metryczka_config_version INTEGER`,
  - `get_jst_study_public(...)` zwraca także pola konfiguracji metryczki,
  - `insert_jst_study(...)` ustawia domyślną konfigurację metryczki dla nowych badań JST,
  - `update_jst_study(...)` normalizuje `metryczka_config` przy zapisie,
  - `fetch_jst_studies(...)` i `fetch_jst_study_by_id(...)` mają fallback normalizacji dla starszych rekordów bez konfiguracji.
- dodano dokument projektowy `JST_METRYCZKA_MODEL.md`:
  - model JSON,
  - zasady mapowania do importu i raportów,
  - strategia spójności i kolejność wdrożenia kolejnych etapów.
- Smoke-check:
  - `python -m py_compile db_jst_utils.py metryczka_config.py app.py` (OK).

### Hotfix H-062 [DONE]
Temat: Osobny kafelek `Metryczka` + edytor metryczki dla JST i badań personalnych.
Kryteria ukończenia:
1. W panelach `Badania personalne` i `Badania mieszkańców` jest osobny kafelek `🧾 Metryczka` (nie w `⚙️ Ustawienia ankiety`).
2. Dla wybranego badania można edytować 5 pytań rdzeniowych metryczki (treść + odpowiedzi + kodowanie odpowiedzi).
3. Można dodać pytanie metryczkowe dodatkowe z polami:
   - `Pytanie`,
   - `Kodowanie`,
   - `Odpowiedzi` + `Kodowanie` odpowiedzi.
4. Konfiguracja zapisuje się per badanie dla JST i personalnych.
Pierwszy krok wykonawczy:
- dodać widoki `jst_metryczka_view` i `personal_metryczka_view`, podpiąć kafelki/routing oraz rozszerzyć model danych `studies`.
Wynik:
- `app.py`:
  - dodano osobne kafelki `🧾 Metryczka` w `home_jst_view` i `home_personal_view`,
  - dodano routing widoków:
    - `jst_metryczka_view`,
    - `personal_metryczka_view`,
  - dodano wspólny edytor metryczki:
    - 5 pytań rdzeniowych (stałe kodowanie kolumn),
    - dynamiczne dodawanie/usuwanie pytań dodatkowych,
    - edycja treści pytań i tabel odpowiedzi (`Odpowiedź` + `Kodowanie`),
    - walidacja konfiguracji przed zapisem.
- `metryczka_config.py`:
  - dodano aliasy dla badań personalnych:
    - `default_personal_metryczka_config`,
    - `normalize_personal_metryczka_config`.
- `db_utils.py`:
  - `fetch_studies(...)` zwraca znormalizowaną konfigurację metryczki,
  - `insert_study(...)` ustawia domyślną metryczkę personalną,
  - `update_study(...)` normalizuje `metryczka_config` przy zapisie.
- `db_jst_utils.py`:
  - `ensure_jst_schema()` rozszerza tabelę `studies` o:
    - `metryczka_config JSONB`,
    - `metryczka_config_version INTEGER`.
- Smoke-check:
  - `python -m py_compile app.py db_utils.py db_jst_utils.py metryczka_config.py` (OK).

### Hotfix H-063 [DONE]
Temat: Wklejanie `pytania + odpowiedzi` w edytorze metryczki (UX jak na nagraniu referencyjnym).
Kryteria ukończenia:
1. W każdej sekcji pytania metryczkowego jest przycisk `📋 Wklej pytanie i odpowiedzi`.
2. Po kliknięciu otwiera się panel z:
   - polem wklejania,
   - podglądem parsowania (`Treść pytania` + lista `Odpowiedzi`),
   - akcją `Wstaw`.
3. Parser usuwa numerację/bulety (`1.`, `-`, `•`) i potrafi rozdzielić pytanie od odpowiedzi.
4. `Wstaw` uzupełnia pytanie i odpowiedzi w metryczce, nadając kodowanie odpowiedzi sekwencyjnie (`1..N`).
Pierwszy krok wykonawczy:
- dodać parser tekstu i UI panelu w `_render_metryczka_editor` w `app.py`.
Wynik:
- `app.py`:
  - dodano parser wklejanej treści:
    - `_parse_pasted_question_and_answers(...)`,
    - normalizacja linii i prefiksów list (`_paste_line_normalize`, `_paste_line_as_option`, `_paste_is_option_like`),
  - w edytorze metryczki (dla JST i personalnych) dodano przycisk:
    - `📋 Wklej pytanie i odpowiedzi`,
  - po kliknięciu renderowany jest panel:
    - textarea z treścią,
    - podgląd parsowania po prawej,
    - przyciski `Wstaw` / `Anuluj`,
  - `Wstaw` aktualizuje bieżące pytanie:
    - ustawia treść pytania (jeśli wykryta),
    - wstawia odpowiedzi z auto-kodowaniem `1..N`,
    - odświeża edytor bez utraty spójności stanu.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-064 [DONE]
Temat: Korekta kodowania odpowiedzi dla 5 stałych pól metryczki (zgodność z historycznymi bazami).
Kryteria ukończenia:
1. Dla rdzenia metryczki (`M_PLEC`, `M_WIEK`, `M_WYKSZT`, `M_ZAWOD`, `M_MATERIAL`) kodowanie odpowiedzi jest zgodne z dotychczasową bazą (tekst odpowiedzi), a nie wymuszone `1..N`.
2. Wklejanie odpowiedzi (`Wklej pytanie i odpowiedzi`) dla pytań rdzeniowych zachowuje tę samą zasadę.
3. Dla pytań custom pozostaje auto-kodowanie `1..N` przy masowym wklejeniu.
Pierwszy krok wykonawczy:
- poprawić normalizację rdzenia w `metryczka_config.py` i logikę wstawiania/edycji opcji w `app.py`.
Wynik:
- `metryczka_config.py`:
  - domyślne opcje rdzeniowe mają `code` równe tekstowi odpowiedzi,
  - normalizacja rdzenia wymusza kompatybilność historyczną:
    `code = label` dla 5 stałych pytań.
- `app.py`:
  - parser opcji z tabeli (`_metryczka_options_from_df`) przestał wymuszać uppercase kodowania odpowiedzi,
  - przy `Wstaw` po wklejeniu:
    - rdzeń: `code = tekst odpowiedzi`,
    - custom: `code = 1..N`,
  - doprecyzowano opis przy kodowaniu rdzenia (zgodność z historyczną bazą).
- Smoke-check:
  - `python -m py_compile app.py metryczka_config.py db_utils.py db_jst_utils.py` (OK).

### Hotfix H-065 [DONE]
Temat: Dalsze obniżenie wysokości pola `Pytanie` w edytorze metryczki.
Kryteria ukończenia:
1. Pole `Pytanie` w metryczce startuje z wysokości ok. 1–2 linii.
2. Użytkownik może nadal ręcznie rozszerzać pole w dół.
Pierwszy krok wykonawczy:
- poprawić selektor CSS tak, by na pewno trafiał w pola `Pytanie` renderowane przez Streamlit.
Wynik:
- `app.py`:
  - selektor CSS zmieniono na `textarea[aria-label=\"Pytanie\"]`,
  - ustawiono startową geometrię:
    - `min-height: 38px`,
    - `height: 38px`,
    - `line-height: 1.25`,
    - `resize: vertical`.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-066 [DONE]
Temat: Stabilizacja panelu `Wklej pytanie i odpowiedzi` w edytorze metryczki (cancel + preview + scroll).
Kryteria ukończenia:
1. Kliknięcie `Anuluj` nie powoduje błędu `StreamlitAPIException` dla `paste_text_*`.
2. Otwarcie panelu wklejania nie robi dodatkowego, wymuszonego `rerun`, który pogarszał UX przewijania.
3. `Podgląd` przy pustym polu wklejania pokazuje aktualne pytanie i aktualne odpowiedzi edytowanego wiersza.
Pierwszy krok wykonawczy:
- poprawić zarządzanie `session_state` dla widgetu `paste_text_*` i fallback podglądu w `_render_metryczka_editor`.
Wynik:
- `app.py` (`_render_metryczka_editor`):
  - usunięto bezpośrednie czyszczenie `st.session_state[paste_text_key]` po instancjacji widgetu,
  - dodano bezpieczny mechanizm czyszczenia przez flagę `paste_clear_*` + `pop(...)` przed renderem textarea,
  - usunięto zbędny `st.rerun()` po kliknięciu `📋 Wklej pytanie i odpowiedzi` (mniej skoków widoku),
  - `Podgląd` ma fallback:
    - `Treść pytania` -> aktualna treść pytania, gdy parser nie wykryje nowej,
    - `Odpowiedzi` -> aktualna lista odpowiedzi, gdy pole wklejania jest puste.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-067 [DONE]
Temat: Korekta wysokości pola `Pytanie` w edytorze metryczki (za niska po H-065).
Kryteria ukończenia:
1. Pole `Pytanie` nie jest „ściśnięte” i startuje wizualnie bliżej 2 linii.
2. Nadal działa ręczne rozszerzanie pola w dół.
Pierwszy krok wykonawczy:
- podnieść wartości `height/min-height` dla `textarea[aria-label="Pytanie"]` w `app.py`.
Wynik:
- `app.py`:
  - `min-height`: `38px` -> `50px`,
  - `height`: `38px` -> `50px`,
  - `line-height`: `1.25` -> `1.3`,
  - zachowano `resize: vertical`.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-068 [DONE]
Temat: Metryczka — pole `Pytanie` nadal za niskie i brak możliwości ręcznego rozszerzania.
Kryteria ukończenia:
1. Pole `Pytanie` startuje od wysokości wygodnej do edycji (~2+ linie).
2. Użytkownik może przeciągać uchwyt i zwiększać wysokość pola w dół.
Pierwszy krok wykonawczy:
- zdjąć sztywne `height` z CSS i podnieść wysokość startową textarea w `_render_metryczka_editor`.
Wynik:
- `app.py`:
  - CSS dla `textarea[aria-label="Pytanie"]`:
    - `min-height` podniesione do `56px`,
    - usunięto sztywne `height: 50px`; wprowadzono `height: auto` + `max-height: none`,
    - pozostawiono `resize: vertical`.
  - widget `st.text_area("Pytanie", ...)`:
    - `height` zwiększone z `24` do `56`.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-069 [DONE]
Temat: Uspójnienie UX `Wklej pytanie i odpowiedzi` (prefill + zwarty podgląd).
Kryteria ukończenia:
1. Po kliknięciu `📋 Wklej pytanie i odpowiedzi` pole edycji jest wstępnie wypełnione bieżącą treścią pytania i istniejącymi odpowiedziami.
2. Gdy pytanie ma już odpowiedzi, użytkownik widzi je od razu w polu edycji bez ręcznego kopiowania.
3. Podgląd listy odpowiedzi ma zwarte odstępy (bez nadmiernych przerw między punktami).
Pierwszy krok wykonawczy:
- dodać seed tekstu przy otwarciu panelu i zmienić render wypunktowania w podglądzie na kompaktowy HTML list.
Wynik:
- `app.py` (`_render_metryczka_editor`):
  - przy otwarciu panelu ustawiany jest `seed` do `paste_text_*`:
    - 1. linia: bieżące pytanie,
    - kolejne linie: aktualne odpowiedzi,
  - fallback parsera/podglądu oparty o bieżące pytanie i odpowiedzi,
  - lista `Odpowiedzi` w podglądzie renderowana jako kompaktowe `<ul><li>` z mniejszym `line-height` i marginesami.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-071 [DONE]
Temat: iPhone mobile — łamanie etykiet `zdecydowanie ...` i większy odstęp przycisku `Dalej`.
Kryteria ukończenia:
1. W kafelkach odpowiedzi słowo `zdecydowanie` nie może być łamane na `zdecydowani` + `e`.
2. `ani tak, ani nie` pozostaje podzielone na dwie linie.
3. W mobile portrait przycisk `Dalej` jest niżej (większy odstęp od paska odpowiedzi).
Pierwszy krok wykonawczy:
- poprawić render etykiet w `Questionnaire.tsx` i mikrotypografię/odstępy w `SingleQuestionnaire.css`.
Wynik:
- `archetypy-ankieta/src/Questionnaire.tsx`:
  - etykiety skrajne renderowane jawnie dwuliniowo:
    - `zdecydowanie` + `nie`,
    - `zdecydowanie` + `tak`,
  - etykieta neutralna pozostaje jawnie dwuliniowa (`ani tak,` + `ani nie`).
- `archetypy-ankieta/src/SingleQuestionnaire.css`:
  - usunięto agresywne łamanie znak po znaku:
    - `word-break: normal`,
    - `overflow-wrap: normal`,
    - `hyphens: none`,
  - delikatnie zwiększono czytelność kafelków mobile (`max-width:430px`):
    - `font-size: 0.64rem`,
    - `line-height: 1.08`,
  - zwiększono odstęp `Dalej` od paska odpowiedzi w portrait:
    - `margin-top: 30px`.
- Smoke-check:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Hotfix H-072 [DONE]
Temat: Mobile iPhone — całkowite wyłączenie dzielenia wyrazów w treści pytania.
Kryteria ukończenia:
1. Pytanie główne nie dzieli wyrazów myślnikiem (`wy-`, `społeczny-` itd.).
2. Zawijanie działa wyłącznie między pełnymi wyrazami.
Pierwszy krok wykonawczy:
- wycofać hyphenację i agresywne łamanie dla `.single-question-text` w mobile portrait.
Wynik:
- `archetypy-ankieta/src/SingleQuestionnaire.css` (mobile portrait):
  - ustawiono:
    - `overflow-wrap: normal`,
    - `word-break: normal`,
    - `hyphens: none`.
- Smoke-check:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Hotfix H-076 [DONE]
Temat: iPhone mobile — nierozdzielna fraza `rozwiązać pokojowo` w pytaniu.
Kryteria ukończenia:
1. W pytaniu `Wierzy, że większość problemów można rozwiązać pokojowo.` fraza `rozwiązać pokojowo` jest trzymana razem.
2. Zmiana działa w `Pojedynczych ekranach` i nie psuje pozostałych pytań.
Pierwszy krok wykonawczy:
- dodać regułę frazy do `PHRASE_GLUE_PATTERNS` w `withHardSpaces(...)`.
Wynik:
- `archetypy-ankieta/src/Questionnaire.tsx`:
  - dodano regułę `\\brozwiązać\\s+pokojowo\\b` do listy fraz klejonych twardą spacją.
- Smoke-check:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Hotfix H-078 [DONE]
Temat: Poprawa klejenia krótkich słów — bez sklejania końcówek wyrazów (iPhone single-screen).
Kryteria ukończenia:
1. Reguła klejenia krótkich słów działa tylko dla pełnych, osobnych słów.
2. Nie dochodzi do błędów typu sklejenie końcówki w `można`, które prowadzi do obcinania.
Pierwszy krok wykonawczy:
- poprawić regex `SHORT_WORD_GLUE_RE` i sposób podmiany w `withHardSpaces(...)`.
Wynik:
- `archetypy-ankieta/src/Questionnaire.tsx`:
  - `SHORT_WORD_GLUE_RE` zmieniono z granicy słowa (`\\b...`) na wariant wymagający początku/whitespace (`(^|\\s)...`),
  - podmiana używa callbacka i zachowuje prefix (`prefix + shortWord + NBSP`).
- Smoke-check:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Hotfix H-073 [DONE]
Temat: Dopieszczenie panelu `Wklej pytanie i odpowiedzi` (format prefill + większe pole + ciaśniejszy podgląd).
Kryteria ukończenia:
1. Prefill panelu odpowiada workflow edycyjnemu (`Pytanie:` + `Odpowiedzi:` + numerowane opcje).
2. Parser rozumie prefiks `Pytanie:` i nie przepuszcza go do treści pytania.
3. Pole `Wklej treść` jest wyraźnie wyższe.
4. W podglądzie lista odpowiedzi ma ciaśniejsze odstępy.
Pierwszy krok wykonawczy:
- poprawić seed i parser w `_render_metryczka_editor` / `_parse_pasted_question_and_answers` oraz podnieść `height` textarea.
Wynik:
- `app.py`:
  - parser akceptuje i czyści prefiks `Pytanie:`,
  - prefill pola `Wklej treść`:
    - `Pytanie: ...`,
    - `Odpowiedzi:`,
    - `1. ...`, `2. ...`, ...,
  - wysokość pola `Wklej treść` podniesiona z `170` do `260`,
  - podgląd odpowiedzi renderowany bardziej kompaktowo (mniejsze marginesy i line-height `ul/li`).
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-074 [DONE]
Temat: Stopka build fallbackowała do `unknown-time | commit: unknown` na części deployów.
Kryteria ukończenia:
1. Stopka ma stabilny fallback nawet bez `.git` i bez odpowiedzi GitHub API.
2. `commit` nie pokazuje już `unknown` w scenariuszu awaryjnym.
3. `build_time` ma awaryjny fallback zamiast `unknown-time`, gdy to możliwe.
Pierwszy krok wykonawczy:
- rozszerzyć źródła env/secrets w `_app_build_signature()` i dodać fallback czasu po `mtime` pliku `app.py`.
Wynik:
- `app.py` (`_app_build_signature`):
  - dodano dodatkowe źródła SHA z env:
    - `SOURCE_VERSION`, `RENDER_GIT_COMMIT`, `RAILWAY_GIT_COMMIT_SHA`, `CI_COMMIT_SHA`, `HEROKU_SLUG_COMMIT`, `CF_PAGES_COMMIT_SHA`,
  - dodano dodatkowe źródła czasu commita:
    - `RAILWAY_GIT_COMMIT_TIME`, `CI_COMMIT_TIMESTAMP`, `BUILD_TIMESTAMP`,
  - dodano ostatni fallback czasu: `mtime` pliku `app.py`,
  - fallback `commit_short` zmieniono z `unknown` na `local`.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-075 [DONE]
Temat: Usunięcie numeracji odpowiedzi z prefill panelu `Wklej pytanie i odpowiedzi`.
Kryteria ukończenia:
1. W prefill nie ma `1.`, `2.`, `3.` przed odpowiedziami.
2. Numeracja nie jest sugerowana także w placeholderze pola wklejania.
Pierwszy krok wykonawczy:
- zmienić seed `paste_text_*` oraz placeholder textarea w `_render_metryczka_editor`.
Wynik:
- `app.py`:
  - prefill panelu zapisuje odpowiedzi jako czyste linie (bez numerów),
  - placeholder pokazuje wzorzec bez numeracji (`Odpowiedź 1`, `Odpowiedź 2`, `Odpowiedź 3`).
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-077 [DONE]
Temat: Kodowanie w metryczce wymagało podwójnego wpisania (data_editor nie commitował ostatniej komórki przed zapisem).
Kryteria ukończenia:
1. Jedno kliknięcie `💾 Zapisz metryczkę` zapisuje aktualne kodowanie bez potrzeby ponownej edycji.
2. Dotyczy widoków metryczki dla JST i personalnych.
Pierwszy krok wykonawczy:
- wprowadzić zapis 2-etapowy przez `save intent` + rerun, aby commit aktywnej komórki data_editor odbył się przed właściwym zapisem do bazy.
Wynik:
- `app.py`:
  - dodano helper `_metryczka_save_intent_key(...)`,
  - `jst_metryczka_view`:
    - klik `💾 Zapisz metryczkę` ustawia flagę intent i robi `st.rerun()`,
    - właściwy zapis wykonywany jest na kolejnym rerunie po pobraniu zatwierdzonych wartości z edytora,
  - `personal_metryczka_view`:
    - analogiczny mechanizm save-intent i zapis po rerunie.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-079 [DONE]
Temat: Metryczka — `Wklej pytanie i odpowiedzi` psuło UX i kodowanie.
Kryteria ukończenia:
1. Po `Wstaw`/`Anuluj` użytkownik wraca do edytowanego pytania (bez skoku na górę strony).
2. `Wklej pytanie i odpowiedzi` nie nadpisuje kodowania odpowiedzi (`1,2,3...`) dla pytań custom.
3. Wklejka modyfikuje tylko treść pytania i listę odpowiedzi.
Pierwszy krok wykonawczy:
- dodać kotwice pytania + mechanizm scroll-restoru po rerun oraz zmienić logikę `Wstaw`, aby zachowywała istniejące kody odpowiedzi.
Wynik:
- `app.py` (`_render_metryczka_editor`):
  - dodano kotwicę per pytanie (`_metryczka_anchor_id`) i klucz scroll-target (`_metryczka_scroll_target_key`),
  - po `Wstaw` i `Anuluj` zapisywany jest target i po rerunie wykonywany auto-scroll do danego pytania,
  - przy `Wstaw`:
    - `core`: `code = label` (jak dotychczas),
    - `custom`: kodowanie jest zachowane z istniejących opcji (najpierw po etykiecie, fallback po indeksie),
    - usunięto wymuszanie nowych kodów `1..N`.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-080 [DONE]
Temat: Metryczka — po `Wstaw` nadal skok na górę + nadal gubienie świeżo edytowanego kodowania.
Kryteria ukończenia:
1. Po `Wstaw`/`Anuluj` panel zostaje przy edytowanym pytaniu.
2. Operacja `Wstaw` korzysta z bieżącego stanu kodowania (z tabeli odpowiedzi) i nie resetuje świeżych zmian.
3. Brak wymuszonego resetu widgetów metryczki przy `Wstaw`/`Anuluj`.
Pierwszy krok wykonawczy:
- usunąć `nonce bump` z akcji panelu wklejki, przełączyć scroll-restore na `html_component`, a mapowanie kodów oprzeć o aktualne `options` z bieżącego przebiegu.
Wynik:
- `app.py` (`_render_metryczka_editor`):
  - `Wstaw` mapuje kodowanie na podstawie aktualnych `options` (fallback: stare `q_item["options"]`),
  - usunięto `_bump_metryczka_editor_nonce(...)` z `Wstaw` i `Anuluj` (koniec resetu całego zestawu widgetów),
  - scroll-restore po `Wstaw`/`Anuluj` wykonuje się przez `html_component(..., height=0)`.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-081 [DONE]
Temat: Dodatkowe uszczelnienie zapisu kodowania (`data_editor`) — commit fazowy.
Kryteria ukończenia:
1. Jedno kliknięcie `💾 Zapisz metryczkę` nie wymaga ponownego wpisywania kodowania.
2. Commit aktywnej komórki edytora jest domknięty przed właściwym zapisem do DB.
Pierwszy krok wykonawczy:
- zmienić `save intent` z bool na fazy `arm -> commit -> save` (2 reruny techniczne po jednym kliknięciu).
Wynik:
- `app.py`:
  - w `jst_metryczka_view` i `personal_metryczka_view` zapis metryczki działa fazowo:
    - klik przycisku ustawia `arm`,
    - kolejny przebieg przechodzi do `commit`,
    - następny przebieg wykonuje właściwy zapis i czyści flagę.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-082 [DONE]
Temat: Metryczka — nowe pytanie z wklejki gubiło odpowiedzi/kodowanie, a zapis kodowania nadal bywał niestabilny.
Kryteria ukończenia:
1. Wiersze odpowiedzi z pustym kodowaniem nie znikają z edytora.
2. Komunikat walidacji dla brakującego kodowania jest adekwatny (a nie „dodaj co najmniej 2 odpowiedzi”).
3. Scroll-restore po `Wstaw/Anuluj` działa stabilniej.
4. Zapis metryczki nie ma dodatkowych faz rerun, które mogły psuć commit pola kodowania.
Pierwszy krok wykonawczy:
- poprawić `_metryczka_options_from_df`, scroll script i uprościć flow zapisu metryczki (JST + personal).
Wynik:
- `app.py`:
  - `_metryczka_options_from_df(...)`:
    - zachowuje wiersze z niepustą etykietą nawet przy pustym kodowaniu,
    - deduplikacja kodów tylko dla niepustych wartości,
  - scroll-restore po wklejce:
    - wrócono do `st.markdown(<script>)` z retry (`setInterval`) i fallbackiem `location.hash + scrollIntoView`,
  - zapis metryczki (`jst_metryczka_view`, `personal_metryczka_view`) uproszczony do bezpośredniego zapisu po kliknięciu,
    bez faz `arm/commit` i dodatkowych rerunów technicznych.
- Smoke-check:
  - `python -m py_compile app.py` (OK).


### Hotfix H-083 [DONE]
Temat: Metryczka - stabilizacja scroll po akcjach edytora + stabilizacja pierwszego zapisu kodowania.
Kryteria ukończenia:
1. Po `➕ Dodaj pytanie metryczkowe` i `Wstaw` edytor wraca do właściwego pytania zamiast zostawać na górze.
2. Zapis metryczki nie wymaga dodatkowych faz rerun, które mogły gubić pierwszy wpis kodowania.
3. Przy `Wklej pytanie i odpowiedzi` brakujące kodowanie dla odpowiedzi ma domyślną propozycję `kodowanie = treść odpowiedzi` (edytowalne).
Pierwszy krok wykonawczy:
- poprawić skrypt scroll-restoru (obsługa zagnieżdżonych iframe), uprościć flow zapisu i domknąć mapowanie kodów w `Wstaw`.
Wynik:
- `app.py`:
  - scroll-restore w `_render_metryczka_editor` przebudowany:
    - wyszukiwanie kotwicy przez łańcuch `window -> parent -> ...` (do kilku poziomów),
    - przewijanie przez `scrollTo` z fallbackiem `scrollIntoView`,
    - retry-loop (40 prób) po rerunie,
  - zapis metryczki (`jst_metryczka_view`, `personal_metryczka_view`) uproszczony do bezpośredniego zapisu po kliknięciu `💾 Zapisz metryczkę`,
  - `Wstaw` dla pytań custom:
    - zachowuje istniejące kodowanie gdy da się je dopasować,
    - gdy brak dopasowania, proponuje `code = label` (treść odpowiedzi), bez narzucania numeracji.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-084 [DONE]
Temat: Metryczka - korekta układu przycisków akcji (pozycja i odstępy).
Kryteria ukończenia:
1. Przycisk `💾 Zapisz metryczkę` jest po prawej stronie sekcji.
2. `➕ Dodaj pytanie metryczkowe` ma większy odstęp od przycisku `📋 Wklej pytanie i odpowiedzi`.
3. Zmiana działa dla metryczki JST i personalnej.
Pierwszy krok wykonawczy:
- zmienić layout przycisku zapisu na kolumny (`prawa kolumna`) i dodać pionowy spacer przed przyciskiem dodawania pytania.
Wynik:
- `app.py`:
  - `_render_metryczka_editor`: dodano pionowy odstęp (`0.55rem`) przed `➕ Dodaj pytanie metryczkowe`,
  - `jst_metryczka_view` i `personal_metryczka_view`: `💾 Zapisz metryczkę` osadzony w prawej kolumnie, z `use_container_width=True`.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-085 [DONE]
Temat: Metryczka - twarda stabilizacja powrotu scrolla do edytowanego pytania po `Wstaw`/`Dodaj`.
Kryteria ukończenia:
1. Po `Wstaw` w `📋 Wklej pytanie i odpowiedzi` użytkownik zostaje na aktualnie edytowanym pytaniu (np. `7. M_POGLADY`), bez skoku do `1. M_PLEC`.
2. Po `➕ Dodaj pytanie metryczkowe` widok wraca do nowo dodanego pytania, a nie na górę listy.
3. Mechanizm scrolla uruchamia się niezawodnie także przy powtarzanych akcjach na tym samym pytaniu.
Pierwszy krok wykonawczy:
- dodać nonce dla akcji scroll-restoru i wymusić remount skryptu oraz rozszerzyć przewijanie o wewnętrzne kontenery Streamlit.
Wynik:
- `app.py` (`_render_metryczka_editor`):
  - dodano `_metryczka_scroll_nonce_key(...)`,
  - przy akcjach `Wstaw`, `Anuluj`, `Dodaj pytanie` zapisywany jest `scroll_target` + unikalny `scroll_nonce`,
  - skrypt scroll-restoru:
    - renderowany z unikalnym `key` (remount na każdą akcję),
    - przewija `window` oraz typowe kontenery przewijania Streamlit,
    - resetuje/ustawia hash kotwicy dla pewniejszego skoku także przy tym samym pytaniu.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-086 [DONE]
Temat: Metryczka - naprawa crasha `IframeMixin._html() got an unexpected keyword argument 'key'`.
Kryteria ukończenia:
1. Edytor metryczki nie rzuca błędu po `Wstaw`/`Dodaj` w scenariuszach scroll-restoru.
2. Scroll-restore nadal ma unikalny trigger per akcja.
Pierwszy krok wykonawczy:
- usunąć nieobsługiwany argument `key` z `html_component(...)` i pozostawić wymuszanie przez `scroll_nonce` w treści skryptu.
Wynik:
- `app.py`:
  - w wywołaniu `html_component` dla scroll-restoru usunięto parametr `key=...`,
  - `scroll_nonce` pozostał w JS (`runId`) jako część unikalnego payloadu skryptu.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-087 [DONE]
Temat: Metryczka - dodatkowy fallback scroll-restoru, żeby nie wracało do `1. M_PLEC`.
Kryteria ukończenia:
1. Po `Wstaw` w panelu `Wklej pytanie i odpowiedzi` widok utrzymuje pozycję na aktualnym pytaniu także wtedy, gdy iframe-scroll nie zadziała.
2. Mechanizm działa bez crashy i bez zmian w logice danych.
Pierwszy krok wykonawczy:
- zostawić `html_component` oraz dołożyć drugi, lokalny fallback JS przez `st.markdown(..., unsafe_allow_html=True)`.
Wynik:
- `app.py` (`_render_metryczka_editor`):
  - po `html_component(...)` dodano równoległy fallback skryptu w `st.markdown`,
  - fallback przewija `window` + typowe kontenery Streamlit i ustawia hash kotwicy.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-088 [DONE]
Temat: Podpięcie metryczki konfigurowalnej do runtime (`jst.badania.pro` + `archetypy.badania.pro`) oraz mapowania JST do importu/raportu.
Kryteria ukończenia:
1. Runtime JST renderuje metryczkę z `metryczka_config` (bez hardcodu 5 pytań) i zapisuje odpowiedzi (core + custom) do payloadu.
2. Runtime personalny ma krok metryczki po ekranie powitalnym i zapisuje odpowiedzi metryczki razem z ankietą.
3. Import/eksport JST obsługuje kolumny custom metryczki zgodnie z konfiguracją badania.
4. Dataset raportowy JST (`data.csv`) zawiera także custom kolumny metryczki (bez utraty kolumn kanonicznych).
Pierwszy krok wykonawczy:
- wdrożyć wspólny normalizator metryczki po stronie frontendu, a następnie podpiąć go do `JstSurvey.tsx` i `Questionnaire.tsx`; na końcu rozszerzyć `db_jst_utils.py` oraz call-site w `app.py` o dynamiczne kolumny.
Wynik:
- `archetypy-ankieta`:
  - dodano wspólny moduł `src/lib/metryczka.ts` (normalizacja configu, payload metryczki, helpery `M_ZAWOD`),
  - `JstSurvey.tsx` renderuje metryczkę dynamicznie z `study.metryczka_config`, waliduje wymagane pola i zapisuje `db_column -> code` + `M_ZAWOD_OTHER`,
  - `Questionnaire.tsx` dostał osobny krok metryczki przed pytaniami właściwymi (dla obu trybów ankiety), a zapis personalny wysyła metryczkę do `p_scores.metryczka`,
  - `lib/studies.ts` i `lib/jstStudies.ts` rozszerzone o pola `metryczka_config`.
- `archetypy-admin`:
  - `db_jst_utils.py`:
    - dodano `response_columns(...)` (kanoniczne + custom z configu),
    - `normalize_response_row(...)`, `response_rows_to_dataframe(...)`, `make_payload_from_row(...)` obsługują teraz `metryczka_config` i mapowanie custom kolumn,
  - `app.py`:
    - `jst_io_view` (import/eksport) przekazuje `study.metryczka_config` do normalizacji/payloadu/dataframe,
    - `jst_analysis_view` generuje raport z pełnego `out_df` (kanoniczne + custom), bez obcinania do samych kolumn kanonicznych.
- Smoke-check:
  - `python -m py_compile app.py db_jst_utils.py metryczka_config.py` (OK),
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Hotfix H-089 [DONE]
Temat: Uspójnienie wyglądu metryczki w ankiecie personalnej do stylu JST (z niebieskim akcentem).
Kryteria ukończenia:
1. Metryczka personalna ma układ „sekcje pytań + pionowe listy odpowiedzi” jak w JST (bez ciasnych kafelków siatkowych).
2. Zaznaczenie opcji i CTA są w tonacji niebieskiej (zgodnie z prośbą), nie zielonej.
3. Dalszy flow ankiety personalnej pozostaje bez regresji funkcjonalnej.
Pierwszy krok wykonawczy:
- przebudować markup sekcji metryczki w `Questionnaire.tsx` na dedykowane klasy i przenieść styling do CSS.
Wynik:
- `Questionnaire.tsx`:
  - metryczka personalna renderuje teraz blokami pytań i pionowymi opcjami (układ jak JST),
  - zachowana logika walidacji i `M_ZAWOD_OTHER`.
- `SingleQuestionnaire.css`:
  - dodano kompletny zestaw styli `pm-metry-*` dla metryczki personalnej,
  - styl opcji/radiomarków i przycisku `Przejdź dalej` ustawiony na niebieski akcent.
- Smoke-check:
  - `npx tsc -p tsconfig.app.json --noEmit` (OK),
  - `npm run build` (OK).

### Hotfix H-090 [DONE]
Temat: Punkt 3+4 — profile demograficzne (personal) + zakładka `Segmenty` w Matching.
Kryteria ukończenia:
1. W wynikach personalnych działa filtr wielocechowy metryczki (AND) i radar `Profile demograficzne`.
2. W `🧭 Matching` istnieje zakładka `Segmenty` porównująca polityka do segmentów JST wyłącznie na tej samej skali 12 archetypów.
3. Zakładka `Segmenty` ma kontrolę wiarygodności: minimalna liczebność `N` i komunikat niepewności dla segmentów poniżej progu.
Pierwszy krok wykonawczy:
- rozszerzyć loader personalnych odpowiedzi o `scores.metryczka` i dodać sekcję filtrowania+radaru w `admin_dashboard.py`; następnie dodać helper odczytu profili segmentów oraz nową zakładkę `Segmenty` w `app.py`.
Wynik:
- `admin_dashboard.py`:
  - `load(...)` pobiera teraz `scores` obok `answers` i parsuje JSON,
  - dodano helpery metryczki (`_extract_personal_metry_payload`, `_build_personal_metry_questions`, `_metry_value_label`),
  - w `show_report(...)` wdrożono sekcję `👥 Profile demograficzne (filtr wielocechowy + radar)`:
    - filtry wielocechowe (łączenie AND) po pytaniach z `metryczka_config`,
    - liczebność podgrupy, próg minimalnego N i komunikat o niepewności,
    - radar porównawczy: cała próba vs podgrupa filtrowana (skala 0-20).
- `app.py` (`matching_view`):
  - dodano nową zakładkę `Segmenty`,
  - dodano helper `_load_matching_segment_profiles(...)` czytający profile segmentów z raportu JST (`SEGMENTY_ULTRA_PREMIUM_profile.csv`),
  - porównanie segmentów do profilu polityka liczone na wspólnej skali 12 archetypów:
    - `Śr. luka |Δ| (pp)` oraz `Zgodność (%) = 100 - MAE`,
  - dodano kontrolę wiarygodności (`min N`) i ostrzeżenia dla segmentów niepewnych,
  - dodano radar porównawczy polityk vs wybrany segment.
- Smoke-check:
  - `python -m py_compile app.py admin_dashboard.py` (OK).

### Hotfix H-091 [DONE]
Temat: Segmenty w Matching — doprecyzowanie metodologii zgodności + dodanie bloku `📌 Statystyczny profil demograficzny segmentu`.
Kryteria ukończenia:
1. W `Segmentach` jest jasna informacja, że `Zgodność (%)` dla segmentu to `100 - MAE` (bez kar strategicznych z `Poziomu dopasowania`).
2. Dla wybranego segmentu, pod radarami, renderuje się profil demograficzny (karty + tabela) w stylistyce zgodnej z widokiem referencyjnym.
3. Profil segmentu liczony jest na podstawie przypisań respondentów do segmentów i metryczki JST, z zachowaniem wag poststratyfikacyjnych jeśli są aktywne.
Pierwszy krok wykonawczy:
- dodać loader przypisań `respondenci_segmenty_ultra_premium.csv`, podpiąć mapowanie `respondent_id -> segment` do danych JST w Matching i wyrenderować sekcję demograficzną segmentu.
Wynik:
- `app.py`:
  - dodano `_load_matching_segment_membership(...)` (odczyt przypisań respondentów do segmentów),
  - rozszerzono `matching_result` o `jst_demo_vectors` (`respondent_id`, `payload`, `weight`) i `_calc_jst_target_profile(...)` o przenoszenie `respondent_id`,
  - w `tab_segments`:
    - dopisano objaśnienie metodologii segmentowej (`Zgodność (%) = 100 - MAE`, bez kar strategicznych),
    - dołożono sekcję `📌 STATYSTYCZNY PROFIL DEMOGRAFICZNY SEGMENTU` (karty top kategorii + nadreprezentacja),
    - dołożono sekcję `👥 PROFIL DEMOGRAFICZNY SEGMENTU` (tabela % segment vs % ogół mieszkańców + różnica w pp),
    - dodano notę o pokryciu mapowania segmentów i notę o wagowaniu.
- Smoke-check:
  - `python -m py_compile app.py admin_dashboard.py` (OK).

### Hotfix H-092 [DONE]
Temat: Segmenty w Matching — przejście na metrykę strategiczną (jak w Podsumowaniu) i usunięcie zawyżonej zgodności `100-MAE`.
Kryteria ukończenia:
1. `Zgodność (%)` w tabeli Segmentów jest liczona tą samą logiką strategiczną co `Poziom dopasowania` (MAE/RMSE/TOP3/KEY + kary).
2. Opisy metodologii w zakładce Segmenty i pod radarem nie wprowadzają w błąd (brak opisu `100-MAE` jako finalnej zgodności).
3. W tabeli Segmentów liczby `Udział (%)`, `Śr. luka |Δ| (pp)` i `Zgodność (%)` są zawsze z 1 miejscem po przecinku.
Pierwszy krok wykonawczy:
- podmienić wyliczanie `match_pct` w pętli segmentów z `100 - MAE` na metrykę strategiczną i skorygować podpisy.
Wynik:
- `app.py`:
  - dodano lokalny kalkulator strategiczny segmentu (`_segment_strategic_score`) oparty o:
    - `base = 0.40*(100-MAE) + 0.20*(100-RMSE) + 0.20*(100-TOP3_MAE) + 0.20*(100-KEY_MAE)`,
    - `match = clamp(0,100, base - kara_kluczowa)`,
  - ranking i `Zgodność (%)` w tabeli Segmentów używają teraz `match` z tej metody,
  - zaktualizowano opisy metody na górze Segmentów i pod radarem,
  - utrzymano i dopięto formatowanie tabeli do stałego 1 miejsca po przecinku.
- Smoke-check:
  - `python -m py_compile app.py admin_dashboard.py` (OK).

### Hotfix H-093 [DONE]
Temat: Segmenty w Matching — metryka key-focused (TOP5+TOP5) + panel kontekstowy u góry + poprawa legendy radaru.
Kryteria ukończenia:
1. Zgodność segmentu liczona głównie po kluczowych archetypach (TOP5 polityka + TOP5 segmentu), z karami TOP3/TOP2.
2. Na górze zakładki Segmenty widoczny panel: kogo dotyczy segmentacja + poziom zgodności wybranego segmentu.
3. Górna legenda nad radarem nie ucina nazw (dłuższe etykiety mieszczą się czytelniej).
4. W tabeli Segmentów kolumny procentowe/luki/zgodność mają stałe 1 miejsce po przecinku.
Pierwszy krok wykonawczy:
- zmienić kalkulator segmentowy na key-focused i przebudować górny blok zakładki Segmenty pod wzór Podsumowania.
Wynik:
- `app.py`:
  - dodano key-focused scoring segmentu:
    - `base_global` (profil 12 archetypów),
    - `base_key` (TOP5 polityka + TOP5 segmentu),
    - finalnie: `0.25*base_global + 0.75*base_key - key_penalty`,
  - kary priorytetowe (TOP3/TOP2) wzmocnione dla segmentów:
    - większa kara za brak wspólnych priorytetów,
    - większa kara za rozjazd TOP1,
  - dołożono górny panel Segmentów:
    - selektor wybranego segmentu,
    - karty „Dla kogo liczona jest segmentacja”,
    - karta „Poziom zgodności wybranego segmentu” (wartość %, ocena, pasek),
  - poprawiono legendę radaru:
    - usunięto sztuczne paddingi z nazw,
    - usunięto sztywne `entrywidth`, zmniejszono ryzyko obcinania tekstu,
  - utrzymano formatowanie 1 miejsca po przecinku i doprecyzowano kolumnę tabeli:
    - `Śr. luka kluczowa |Δ| (pp)`.
- Smoke-check:
  - `python -m py_compile app.py admin_dashboard.py` (OK).

### Hotfix H-094 [DONE]
Temat: Segmenty w Matching — złagodzenie zbyt agresywnych kar (problem 0%) + przejście na TOP6 + szersza legenda nad radarem.
Kryteria ukończenia:
1. Segmentowy scoring nadal key-focused, ale rzadziej wpada w 0% przy dużych lukach.
2. Pula kluczowa liczona na `TOP6 polityka + TOP6 segmentu`.
3. Legenda nad radarem ma większą szerokość i nie ucina etykiet.
Pierwszy krok wykonawczy:
- dostroić wagi/kary w `segment_strategic_score` i zastąpić legendę Plotly szerszą legendą HTML.
Wynik:
- `app.py`:
  - key-pool zmieniony z TOP5 na TOP6,
  - złagodzone kary segmentowe (`key_penalty`, `shared_priority_penalty`, `main_priority_mismatch_penalty`),
  - zmieniony miks bazy (`global/key`) na mniej skrajny,
  - legenda nad radarem przeniesiona do szerszej wersji HTML (`match-seg-radar-legend` + pill), a legenda Plotly dla tego radaru wyłączona.
- Smoke-check:
  - `python -m py_compile app.py admin_dashboard.py` (OK).

### Hotfix H-095 [DONE]
Temat: Dynamiczna metryczka w tabelach demograficznych Matching + biblioteka zapisanych pytań + rozpoczęcie migracji generatora JST.
Kryteria ukończenia:
1. W `🧭 Matching` tabele demograficzne (`Demografia` i `Segmenty`) liczą zmienne z `metryczka_config` JST, a nie ze stałej piątki.
2. W edytorze metryczki można:
   - zapisać pytanie jako predefiniowane,
   - wstawić pytanie z listy zapisanych.
3. Generator raportu JST zaczyna obsługę dynamicznych pól `M_*` (nie tylko rdzeń 5 kolumn) w kluczowych funkcjach demograficznych.
Pierwszy krok wykonawczy:
- dodać tabelę i helpery backendowe dla zapisanych pytań metryczkowych, następnie przepiąć obie tabele demograficzne w `app.py`, a na końcu rozszerzyć dynamiczne kolumny `M_*` w `JST_Archetypy_Analiza/analyze_poznan_archetypes.py`.
Wynik:
- `db_jst_utils.py`:
  - dodano schemat i indeks dla `public.metryczka_question_templates`,
  - dodano API:
    - `list_metryczka_question_templates(...)`,
    - `save_metryczka_question_template(...)`.
- `app.py`:
  - edytor metryczki:
    - zapis pytania do biblioteki (`💾 Zapisz do zapisanych`),
    - panel `📚 Wybierz z zapisanych` i wstawianie do ankiety,
  - Matching:
    - dodano dynamiczny silnik specyfikacji demografii oparty o `metryczka_config`,
    - zakładka `Demografia` i sekcja demograficzna w `Segmentach` liczą i renderują zmienne dynamicznie (rdzeń + custom `M_*`),
    - zachowane noty o wagowaniu i pokryciu mapowania segmentów.
- `JST_Archetypy_Analiza/analyze_poznan_archetypes.py`:
  - `parse_metryczka(...)` przepuszcza dodatkowe kolumny `M_*` do ramki metryczki,
  - `_onehot_metry(...)` działa na dynamicznej liście kolumn `M_*`,
  - `_format_segment_demography_rows(...)` oraz `_format_demography_rows_between_masks(...)` liczą dynamicznie po `M_*`,
  - `_build_b2_declared_demo_payload(...)` buduje `var_order/cat_order` dynamicznie.
- Smoke-check:
  - `python -m py_compile app.py db_jst_utils.py JST_Archetypy_Analiza/analyze_poznan_archetypes.py` (OK).

### Hotfix H-096 [DONE]
Temat: Segmenty w Matching — suwak kalibracyjny siły kar + 100% bazy wyniku z puli kluczowej.
Kryteria ukończenia:
1. W zakładce `Segmenty` jest kontrolka `Siła kar segmentowych` (`łagodna` / `standard` / `ostra`).
2. Baza wyniku segmentowego liczona jest w 100% na puli kluczowej (`TOP6 polityka + TOP6 segmentu`), bez domieszki pełnego profilu 12 archetypów.
3. Opisy metody w UI są zgodne z nową logiką.
Pierwszy krok wykonawczy:
- dodać kontrolkę siły kar obok progu N i podpiąć ją do wzoru kar w `_segment_strategic_score`.
Wynik:
- `app.py` (`🧭 Matching > Segmenty`):
  - dodano selektor `Siła kar segmentowych` z 3 profilami (`łagodna`, `standard`, `ostra`),
  - `base_score` przestawiono na `base_key` (100% key-pool),
  - kary (`key_gap`, `key_max`, brak wspólnych priorytetów, mismatch TOP1) są skalowane profilem siły kar,
  - zaktualizowano podpisy metody (górny opis i podpis pod radarem).
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-097 [DONE]
Temat: Domknięcie warstwy prezentacyjnej generatora JST pod `custom M_*` + trwałe zapamiętywanie siły kar per badanie JST.
Kryteria ukończenia:
1. Sekcje raportu JST z tabelami demograficznymi nie gubią `custom M_*` i nie wracają do stałej piątki przy etykietach/kolejności.
2. Ikony demograficzne mają spójny mechanizm: mapy bazowe + heurystyki fallback dla zmiennych/kategorii custom.
3. Suwak `Siła kar segmentowych` w `🧭 Matching > Segmenty` zapamiętuje się per badanie JST (trwale, nie tylko w session state).
Pierwszy krok wykonawczy:
- ujednolicić metadane demografii (`var_order`, `cat_order`, ikony) we wspólnych helperach generatora, podpiąć pod wszystkie sekcje prezentacyjne korzystające z payloadu; następnie dodać kolumnę + normalizację + zapis preferencji siły kar w `jst_studies`.
Wynik:
- `JST_Archetypy_Analiza/analyze_poznan_archetypes.py`:
  - dodano wspólne helpery metadanych demograficznych (`_build_metry_demo_schema`, `_build_demo_schema_from_rows`) i ikon fallback,
  - uporządkowano kolejność `M_*` extras wg kolejności wejściowej (bez sortowania alfabetycznego),
  - segmentowe tabele demograficzne (`_render_demo_table`, `Demografia_Seg`) renderują teraz także custom zmienne/kategorie,
  - payloady `B2` i `TOP5` zawierają dynamiczne `var_order`, `cat_order`, `var_icons`, `cat_icons`,
  - panele JS (`B2`/`TOP5`) czytają mapy ikon z payloadu zamiast hardcodu.
- `db_jst_utils.py`:
  - schema `jst_studies` rozszerzona o `matching_segments_penalty_strength` z walidacją (`łagodna|standard|ostra`) i defaultem `standard`,
  - dodana normalizacja tej wartości i podpięcie jej do fetch/insert/update.
- `app.py`:
  - `🧭 Matching > Segmenty` używa i zapisuje `Siłę kar segmentowych` per `jst_study_id` (trwale przez `update_jst_study`),
  - klucz widgetu przeniesiony na poziom badania JST (`matching_segments_penalty_strength_{jst_sid}`).
- Smoke-check:
  - `python -m py_compile app.py db_jst_utils.py JST_Archetypy_Analiza/analyze_poznan_archetypes.py` (OK).

### Hotfix H-098 [DONE]
Temat: Raport archetypowy personalny — usunięcie poziomego paska przewijania tabeli + przeniesienie demografii metryczki do osobnej podstrony.
Kryteria ukończenia:
1. W tabeli podsumowania archetypów nie pojawia się dolny poziomy scrollbar na desktopie.
2. Blok `Profile demograficzne` nie jest już osadzony inline pod tabelą głównego raportu.
3. W raporcie dostępny jest przycisk otwierający osobną podstronę demograficzną (w tym samym oknie) z przyciskiem `Cofnij`.
4. Podstrona demograficzna używa układu zbliżonego do stylu JST `Symulacja` (karty + tabela + radar + filtr wielocechowy).
Pierwszy krok wykonawczy:
- wydzielić renderer demografii personalnej do osobnej funkcji i podpiąć przełączanie widoku po stanie sesji.
Wynik:
- `admin_dashboard.py`:
  - dodano osobny renderer ` _render_personal_demography_subpage(...)` (filtry AND, liczebność, ostrzeżenie niepewności, karty statystyczne, tabela różnic vs cała próba, radar 0-20),
  - podłączono przełączanie widoku przez `st.session_state[f"personal_demo_page_{study_id}"]` i przycisk `← Cofnij`,
  - usunięto stary inline-expander `👥 Profile demograficzne (filtr wielocechowy + radar)` z głównego raportu,
  - zmieniono wrapper tabeli archetypów (`.ap-table-wrap`) na desktopie na `overflow-x: hidden`, co usuwa dolny scrollbar.
- `app.py`:
  - dodano w widoku wyników (`results_view`) przycisk `👥 Raport demograficzny`, który otwiera dedykowaną podstronę demografii dla wybranej osoby.
- Smoke-check:
  - `python -m py_compile app.py admin_dashboard.py` (OK).

### Hotfix H-099 [DONE]
Temat: Metryczka JST + personal — predefiniowane pytania u góry + randomizacja odpowiedzi + odpowiedzi otwarte (wymagane).
Kryteria ukończenia:
1. W edytorze metryczki (JST i personal) jest przycisk u góry do predefiniowanych pytań oraz możliwość edycji zapisanych pozycji.
2. Każde pytanie metryczkowe ma opcje:
   - `Losowa kolejność odpowiedzi`,
   - `Nie losuj ostatniej odpowiedzi`.
3. Każda odpowiedź ma flagę `Otwarta`:
   - po zaznaczeniu respondent widzi wymagane pole tekstowe,
   - zapis obejmuje kod odpowiedzi oraz treść doprecyzowania (`*_OTHER`).
4. Runtime ankiet `jst.badania.pro` i `archetypy.badania.pro` respektuje randomizację i obsługę odpowiedzi otwartych.
Pierwszy krok wykonawczy:
- rozszerzyć model metryczki (Python + TypeScript), następnie podpiąć nowe pola w edytorze i runtime obu ankiet.
Wynik:
- `metryczka_config.py`:
  - dodano pola pytania: `randomize_options`, `randomize_exclude_last`,
  - dodano pole odpowiedzi: `is_open`,
  - normalizacja rdzenia i custom pytań obsługuje nowe pola (z kompatybilnym fallbackiem).
- `db_jst_utils.py`:
  - zapisane predefiniowane pytania (`metryczka_question_templates`) zachowują:
    - randomizację pytań,
    - flagi `is_open` dla odpowiedzi.
- `app.py`:
  - edytor metryczki:
    - nowy górny przycisk `📚 Predefiniowane metryczki` (JST + personal),
    - panel edycji zapisanych pytań (treść, kodowanie, randomizacja, `Otwarta`),
    - `st.data_editor` odpowiedzi ma nową kolumnę checkbox `Otwarta`,
    - pytania mają checkboxy randomizacji (`losuj`, `nie losuj ostatniej`),
    - wklejanie pytań i odpowiedzi zachowuje kodowanie i flagę `Otwarta` tam, gdzie to możliwe.
- `archetypy-ankieta`:
  - `src/lib/metryczka.ts`: rozszerzone typy/normalizacja o `randomize_options`, `randomize_exclude_last`, `is_open`,
  - `src/Questionnaire.tsx` (personal):
    - losowanie odpowiedzi metryczki zgodnie z konfiguracją,
    - obsługa odpowiedzi otwartych per pytanie (wymagane pole tekstowe),
    - zapis do payloadu `M_*_OTHER` (+ zgodność `M_ZAWOD_OTHER`).
  - `src/JstSurvey.tsx` (JST):
    - analogiczna obsługa randomizacji i odpowiedzi otwartych,
    - wymagane doprecyzowanie dla wybranej opcji otwartej,
    - zapis `M_*_OTHER` (+ zgodność `M_ZAWOD_OTHER`).
- Smoke-check:
  - `python -m py_compile app.py db_jst_utils.py metryczka_config.py` (OK),
  - `npm run build` w `archetypy-ankieta` (OK).

### Hotfix H-100 [DONE]
Temat: Raport personalny — pozycja przycisku demografii + czysty widok podstrony + selektory filtrów w stylu Segmentacji.
Kryteria ukończenia:
1. Przycisk `Raport demograficzny` jest w górnym rzędzie, przed szybkim menu (`| Opisy archetypów | Raport | Tabela | Udostępnij`).
2. Po wejściu do podstrony demograficznej nie renderuje się blok nagłówka raportu personalnego (`Archetypy ... panel administratora` + kafel liczebności).
3. W podstronie demograficznej wybór cech działa przez selektory jednokrotnego wyboru (single-select), zamiast multiselectów.
Pierwszy krok wykonawczy:
- przepiąć render przycisku i quicknav w `results_view`, a w `admin_dashboard.py` warunkowo ukryć header i przebudować filtry na `selectbox`.
Wynik:
- `app.py` (`results_view`):
  - przycisk `👥 Raport demograficzny` przeniesiony do górnego rzędu, przed quicknav,
  - usunięto dolny duplikat przycisku,
  - otwieranie podstrony demograficznej działa dla aktualnie wybranej osoby.
- `admin_dashboard.py`:
  - nagłówek raportu personalnego jest ukrywany, gdy aktywna jest podstrona demograficzna,
  - filtry wielocechowe działają jako single-select z opcją `— brak filtra —`, w układzie 2-kolumnowym.
- Smoke-check:
  - `python -m py_compile app.py admin_dashboard.py` (OK).

### Hotfix H-101 [DONE]
Temat: Błąd `NameError: _bool_from_any` przy wejściu w `Predefiniowane metryczki`.
Kryteria ukończenia:
1. Kliknięcie `Predefiniowane metryczki` nie wywala wyjątku.
2. Normalizacja zapisanego pytania metryczkowego poprawnie parsuje pola bool (`is_open`, `randomize_options`, `randomize_exclude_last`).
Pierwszy krok wykonawczy:
- dodać brakujący helper `_bool_from_any` do `db_jst_utils.py` i uruchomić smoke-check.
Wynik:
- `db_jst_utils.py`:
  - dodano helper `_bool_from_any(value, fallback)` wykorzystywany przez normalizację pytań predefiniowanych.
- Smoke-check:
  - `python -m py_compile db_jst_utils.py app.py` (OK).

### Hotfix H-102 [DONE]
Temat: Predefiniowane metryczki — potwierdzenie przy duplikacie kodowania pytania.
Kryteria ukończenia:
1. Gdy w metryczce istnieje już pytanie o tym samym kodowaniu (`M_*`), kliknięcie `Wstaw pytanie` wymaga potwierdzenia.
2. Komunikat ma treść: `Masz już to pytanie w metryczce. Czy chcesz na pewno je wstawić?`
3. `Tak` wstawia pytanie z unikalnym kodowaniem (`M_OBSZAR_2`, `M_OBSZAR_3`, ...), `Nie` anuluje operację.
Pierwszy krok wykonawczy:
- dodać stan oczekującego insertu i przyciski `Tak`/`Nie` w panelu `Predefiniowane metryczki` w `_render_metryczka_editor`.
Wynik:
- `app.py`:
  - przy `Wstaw pytanie` wykrywane są duplikaty kodowania względem pytań już obecnych w metryczce,
  - dla duplikatu pojawia się blok potwierdzenia (`Tak`/`Nie`),
  - `Tak` kontynuuje insert i używa istniejącej logiki nadawania unikalnego kodu (`_question_from_template_payload`),
  - `Nie` czyści stan oczekujący i nic nie wstawia.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-103 [DONE]
Temat: Randomizacja metryczki — blokady per odpowiedź zamiast opcji „Nie losuj ostatniej odpowiedzi”.
Kryteria ukończenia:
1. W tabeli odpowiedzi metryczki jest nowa kolumna `Blokuj losowanie` (za kolumną `Otwarta`).
2. Checkbox `Nie losuj ostatniej odpowiedzi` jest usunięty z edytora (JST i personal).
3. Przy `Losowa kolejność odpowiedzi`:
   - odpowiedzi z `Blokuj losowanie = true` pozostają na swoich pozycjach,
   - pozostałe odpowiedzi są losowane między sobą.
4. Mechanizm działa w runtime obu ankiet (`archetypy.badania.pro` i `jst.badania.pro`).
Pierwszy krok wykonawczy:
- rozszerzyć model opcji metryczki o `lock_randomization`, przebudować edytor i randomizację frontendu.
Wynik:
- `archetypy-admin/app.py`:
  - dodano kolumnę `Blokuj losowanie` do edytora odpowiedzi (pytania + predefiniowane),
  - usunięto checkbox `Nie losuj ostatniej odpowiedzi`,
  - zapisywanie opcji przenosi flagę `lock_randomization`,
  - utrzymana kompatybilność: stare `randomize_exclude_last=true` mapuje się na blokadę ostatniej odpowiedzi, jeśli brak innych blokad.
- `archetypy-admin/metryczka_config.py`:
  - normalizacja opcji obsługuje `lock_randomization`,
  - dodano migrację legacy (`randomize_exclude_last`) do blokady ostatniej odpowiedzi,
  - w znormalizowanym output `randomize_exclude_last` jest wygaszane (`False`).
- `archetypy-admin/db_jst_utils.py`:
  - normalizacja pytań predefiniowanych obsługuje `lock_randomization` i legacy-mapowanie.
- `archetypy-ankieta`:
  - `src/lib/metryczka.ts`: normalizacja opcji i migracja legacy do `lock_randomization`,
  - `src/Questionnaire.tsx` + `src/JstSurvey.tsx`: randomizacja z zachowaniem stałych pozycji opcji zablokowanych.
- Smoke-check:
  - `python -m py_compile app.py metryczka_config.py db_jst_utils.py` (OK),
  - `npm run build` w `archetypy-ankieta` (OK).

### Hotfix H-104 [DONE]
Temat: Metryczka — auto-rozszerzanie tabeli odpowiedzi + `Kodowanie do tabel` + kodowane kategorie w demografii.
Kryteria ukończenia:
1. Tabela odpowiedzi w edytorze metryczki rośnie w dół wraz z liczbą wierszy (bez stałego, niskiego viewportu i wewnętrznego scrollowania przy typowych zakresach).
2. Każde pytanie metryczkowe ma pole `Kodowanie do tabel`.
3. W tabelach demograficznych etykieta zmiennej pochodzi z `Kodowanie do tabel` (fallback: treść pytania).
4. W tabelach demograficznych kategorie odpowiedzi dla pytań konfigurowalnych są prezentowane jako kodowania odpowiedzi.
Pierwszy krok wykonawczy:
- rozszerzyć model metryczki (`table_label`) i podpiąć to pole w edytorze JST/personal + predefiniowanych pytaniach, a następnie przepiąć render etykiet w demografii.
Wynik:
- `archetypy-admin/app.py`:
  - dodano helper `_metryczka_data_editor_height(...)` i użycie `height=` w obu tabelach odpowiedzi (`st.data_editor`) — tabela rośnie razem z liczbą pozycji,
  - dodano pole UI `Kodowanie do tabel`:
    - w edycji pytania metryczki,
    - w panelu predefiniowanych pytań,
  - `table_label` jest zapisywane do konfiguracji pytań i do predefiniowanych,
  - Matching (`_matching_demo_build_specs`) używa `table_label` jako etykiety zmiennej (fallback: `prompt`),
  - Matching dla pytań custom pokazuje kategorie jako `code` (kodowanie odpowiedzi), nie jako pełny `label` respondenta.
- `archetypy-admin/metryczka_config.py`:
  - rozszerzono model pytania o `table_label`,
  - rdzeń ma domyślne krótkie etykiety tabelaryczne (`Płeć`, `Wiek`, `Wykształcenie`, `Status zawodowy`, `Sytuacja materialna`),
  - normalizacja custom pytań: `table_label` fallbackuje do `prompt`.
- `archetypy-admin/db_jst_utils.py`:
  - normalizacja predefiniowanego pytania (`_normalize_template_question_payload`) obsługuje `table_label`.
- `archetypy-admin/admin_dashboard.py`:
  - podstrona demografii personalnej używa `table_label` jako nazwy zmiennej,
  - kategorie w kartach i tabeli demograficznej są prezentowane jako kodowania (`code`).
- `archetypy-ankieta/src/lib/metryczka.ts`:
  - model/normalizacja metryczki rozszerzone o `table_label` (spójność kontraktu danych).
- Smoke-check:
  - `python -m py_compile app.py db_jst_utils.py metryczka_config.py admin_dashboard.py` (OK),
  - `npm run build` w `archetypy-ankieta` (OK).

### Hotfix H-105 [DONE]
Temat: Automatyczne kodowanie rdzenia metryczki + spójne ikonki + przebudowa radaru demografii personalnej.
Kryteria ukończenia:
1. Rdzeń metryczki (`M_PLEC`, `M_WIEK`, `M_WYKSZT`, `M_ZAWOD`, `M_MATERIAL`) ma automatyczne, skrócone kodowanie analityczne w tabelach demograficznych.
2. Ikony zmiennych i kategorii są spójne w tabelach demograficznych Matchingu/Segmentów i podstronie demografii personalnej.
3. Dla custom zmiennych dodane heurystyki ikon dla: preferencje polityczne, miejsce zamieszkania, orientacja/poglądy polityczne.
4. W podstronie `Profile demograficzne archetypu` radar jest zbliżony do stylu z Matchingu (2 profile + TOP2), a pod nim jest sekcja porównania kół 0-100.
Pierwszy krok wykonawczy:
- dopiąć mapowanie kodów/ikon w `app.py` i `admin_dashboard.py`, potem przebudować blok radarowy i dodać sekcję 0-100.
Wynik:
- `app.py`:
  - w `Matching` rdzeń metryczki nie nadpisuje już skróconych kodów długimi etykietami z pytania,
  - dodano heurystyki ikon dla custom zmiennych i kategorii (`preferencje`, `obszar/miejsce zamieszkania`, `orientacja/poglądy polityczne`).
- `admin_dashboard.py`:
  - dodano wspólną mapę kodowania rdzenia metryczki (kanonizacja wartości),
  - podstrona demografii personalnej używa kodów rdzenia (`60+`, `podst./gim./zaw.`, `prac. umysłowy`, `odmowa`, itd.),
  - ikony zmiennych i kategorii odpowiadają uzgodnionemu zestawowi,
  - radar `Podgląd radarowy podgrupy` przebudowany do stylu porównawczego (cała próba vs podgrupa + markery TOP2),
  - dodano sekcję `Profile archetypowe 0-100` z dwoma kołami profilowymi i legendą osi kolorów.
- Smoke-check:
  - `python -m py_compile app.py admin_dashboard.py metryczka_config.py db_jst_utils.py` (OK).

### Hotfix H-106 [DONE]
Temat: Radar demografii personalnej — poprawka TOP2/TOP3 zgodnie z progiem archetypu pobocznego.
Kryteria ukończenia:
1. `Podgląd radarowy podgrupy` nie jest na stałe TOP2.
2. TOP3 pojawia się tylko gdy 3. archetyp osiąga próg widoczności pobocznego (>=70% na skali 0-100), w przeciwnym razie TOP2.
3. Legenda pod radarem i markery na radarze respektują tę samą logikę.
Wynik:
- `archetypy-admin/admin_dashboard.py`:
  - dodano logikę `_priority_top_for_ui_demo(...)` opartą o próg 70% dla 3. archetypu,
  - markery i opisy pod radarem są dynamiczne (`TOP2` lub `TOP3`) dla obu profili,
  - legenda ról (`główny/wspierający/poboczny`) renderuje się zależnie od liczby aktywnych priorytetów.
- Smoke-check:
  - `python -m py_compile admin_dashboard.py app.py` (OK).

### Hotfix H-107 [DONE]
Temat: Picker ikon metryczki + globalna propagacja zmian predefiniowanych pytań po kodowaniu `M_*`.
Kryteria ukończenia:
1. W edytorze metryczki (JST + personal) można wybrać ikonę zmiennej z bazy oraz ustawić ikonę kategorii.
2. Domyślne ikonki dla rdzenia metryczki są uzupełnione automatycznie (zmienna + odpowiedzi), bez ręcznego klikania.
3. `Predefiniowane metryczki -> Zapisz zmiany` propaguje zmiany globalnie do wszystkich ankiet z tym samym kodowaniem pytania.
4. Lokalne zapisy metryczki per ankieta nadal działają wyłącznie na bieżące badanie.
Pierwszy krok wykonawczy:
- rozszerzyć model metryczki o pola ikon i podpiąć je w edytorze, a następnie dodać mechanizm globalnego „apply by db_column” przy zapisie predefiniowanego pytania.
Wynik:
- `app.py`:
  - dodano picker ikon (baza + własna ikona) dla zmiennej metryczkowej,
  - dodano kolumnę `Ikona` dla odpowiedzi (w edytorze pytania i predefiniowanych),
  - zapis/odczyt metryczki i szablonów obejmuje `variable_emoji` i `value_emoji`,
  - `Zapisz zmiany` w panelu predefiniowanych pytań uruchamia globalną propagację zmian do ankiet JST/personal po tym samym `db_column`.
- `metryczka_config.py`:
  - rdzeń metryczki ma pełne domyślne ikonki (zmienne + kategorie),
  - normalizacja obsługuje pola `variable_emoji` i `value_emoji`,
  - dodano heurystyki domyślnych ikon dla pytań/kategorii custom.
- `db_jst_utils.py`:
  - normalizacja predefiniowanego pytania obsługuje pola ikon i fallback heurystyczny.
- `admin_dashboard.py` + `app.py (Matching)`:
  - render tabel demograficznych respektuje ikonki z konfiguracji metryczki (z fallbackiem heurystycznym).
- `archetypy-ankieta/src/lib/metryczka.ts`:
  - model i normalizacja TS rozszerzone o pola ikon (zgodność kontraktu frontend-backend).
- Smoke-check:
  - `python -m py_compile app.py admin_dashboard.py db_jst_utils.py metryczka_config.py db_utils.py` (OK),
  - `npm run build` w `archetypy-ankieta` (OK).

### Hotfix H-108 [DONE]
Temat: Domknięcie metryczki dynamicznej: pełne kategorie 0%, krótkie kody rdzenia, własne ikony odpowiedzi, kolejność odpowiedzi i backfill.
Kryteria ukończenia:
1. `Profile demograficzne archetypu` pokazuje wszystkie zmienne i kategorie z `metryczka_config`, także te z wynikiem 0%, w kolejności konfiguracji.
2. Rdzeń metryczki ma finalne krótkie kody analityczne (`60+`, `podst./gim./zaw.`, `własna firma`, `inna`, skrócone wartości sytuacji materialnej) oraz ikonę wieku `⌛`.
3. Edytor metryczki pozwala wpisać własną ikonę także dla odpowiedzi i przesuwać odpowiedzi góra/dół bez pustego, nieedytowalnego wiersza.
4. Raport personalny ma ciaśniejszą legendę TOP2/TOP3, separator przed kołami 0-100, wycentrowane koła i kartę zgodności podgrupy z całą próbą.
5. Backfill uzupełnia historyczne konfiguracje o nowe kody/ikonki/etykiety bez ręcznej migracji.
Wynik:
- `admin_dashboard.py`:
  - demografia personalna buduje listę kategorii z konfiguracji metryczki, a nie wyłącznie z występujących danych,
  - kategorie 0% pozostają w tabelach,
  - brakujące historyczne kolumny `METRY_*` są traktowane jako puste serie,
  - dodano wizualizację poziomu dopasowania podgrupy do całej próby oraz dopieszczono radar/legendy/koła 0-100.
- `app.py`:
  - tabela odpowiedzi w edytorze i predefiniowanych ma stałą kontrolowaną liczbę wierszy,
  - dodano przyciski przesuwania/usuwania/dodawania odpowiedzi,
  - kolumna `Ikona` przy odpowiedziach jest polem tekstowym, więc można wpisać własną ikonę,
  - dodano jednorazowy backfill metryczek po zalogowaniu.
- `metryczka_config.py`, `db_jst_utils.py`, `archetypy-ankieta/src/lib/metryczka.ts`:
  - ujednolicono finalne kody rdzenia i ikonę wieku `⌛` po stronie admina, raportów i runtime ankiet.
- Smoke-check:
  - `python -m py_compile app.py admin_dashboard.py db_jst_utils.py metryczka_config.py` (OK),
  - `npm run build` w `archetypy-ankieta` (OK; tylko ostrzeżenie Vite o CJS Node API).

### Hotfix H-109 [DONE]
Temat: Korekta UX tabeli odpowiedzi metryczki (powrót do wygodnej edycji + przesuwanie checkboxem).
Kryteria ukończenia:
1. Dodawanie/usuwanie odpowiedzi wraca do natywnej edycji tabeli (bez osobnych przycisków „Dodaj/Usuń”).
2. Przesuwanie odpowiedzi działa po zaznaczeniu checkboxa w wierszu (`Przesuń`) i kliknięciu `↑/↓`.
3. Znikają sztuczne puste „martwe” wiersze wynikające z zawyżonej wysokości komponentu.
Wynik:
- `archetypy-admin/app.py`:
  - oba edytory (metryczka i predefiniowane) używają `st.data_editor(..., num_rows=\"dynamic\")`,
  - dodano kolumnę pomocniczą `Przesuń` do wyboru wiersza do ruchu,
  - usunięto osobne przyciski `Dodaj odpowiedź` i `Usuń` (wrót do prostszej edycji jak wcześniej),
  - wysokość tabeli liczona bez sztucznego zapasu pustych rzędów.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-110 [DONE]
Temat: Stabilizacja adnotacji typów w demografii personalnej (`admin_dashboard.py`).
Kryteria ukończenia:
1. Brak adnotacji `typing.Dict/List/Tuple` bez importu `typing` w krytycznym bloku liczenia zgodności podgrupy.
2. Brak ryzyka `NameError` podczas renderu raportu demograficznego personalnego.
Wynik:
- `archetypy-admin/admin_dashboard.py`:
  - zamieniono lokalne adnotacje `Dict/List/Tuple` na natywne `dict/list/tuple`.
- Smoke-check:
  - `python -m py_compile admin_dashboard.py app.py` (OK).

### Hotfix H-111 [DONE]
Temat: Etap 1 (metryczka) — stabilizacja dodawania pytań, zapisu tabel i propagacji szablonów.
Kryteria ukończenia:
1. `Dodaj pytanie metryczkowe` nie powoduje już automatycznego dokładania pustego `M_CUSTOM_*` podczas wstawiania z zapisanych.
2. Edycje w tabeli odpowiedzi (kodowanie/ikony) nie wymagają podwójnego wpisywania.
3. Po globalnym `Predefiniowane metryczki -> Zapisz zmiany` bieżący edytor metryczki od razu widzi zaktualizowane pola (np. `Kodowanie do tabel`).
4. Dodana zmiana kolejności pytań metryczkowych (custom) bez kasowania i dodawania od nowa.
5. Pusta ikonka odpowiedzi (brak emoji) jest trwałym stanem i nie wraca automatycznie do fallbacku.
Wynik:
- `archetypy-admin/app.py`:
  - dolny panel rozdzielony na:
    - `➕ Dodaj puste pytanie`,
    - szybkie `📥 Wstaw z zapisanych` (bez dorzucania pustego pytania),
  - dodano moduł `↕️ Zmień kolejność pytań metryczkowych` (przesuwanie custom pytań góra/dół),
  - data-editory odpowiedzi czytają stan „live” z `st.session_state` (eliminuje efekt utraty pierwszej edycji),
  - po globalnym zapisie predefiniowanego pytania aktualizowany jest też bieżący stan edytora w sesji,
  - logika ikon odpowiedzi respektuje jawnie pustą wartość.
- `archetypy-admin/metryczka_config.py` + `archetypy-admin/db_jst_utils.py`:
  - normalizacja nie nadpisuje już pustej ikonki odpowiedzi automatycznym fallbackiem.
- Smoke-check:
  - `python -m py_compile app.py metryczka_config.py db_jst_utils.py` (OK).

### Hotfix H-112 [DONE]
Temat: Naprawa błędu `ColumnDataKind.FLOAT` dla kolumny `Przesuń` w `st.data_editor`.
Kryteria ukończenia:
1. Kolumna `Przesuń` ma zawsze typ bool (także przy 0 wierszach).
2. Brak wyjątku `StreamlitAPIException` o niezgodnym typie kolumny checkbox.
Wynik:
- `archetypy-admin/app.py`:
  - `_metryczka_attach_move_marker(...)` wstawia `Przesuń` jako `pd.Series(..., dtype=\"bool\")`,
  - `_metryczka_extract_move_marker(...)` normalizuje `Przesuń` przez `_bool_from_any(...).astype(bool)`,
  - `_metryczka_editor_df_clean(...)` dodatkowo normalizuje kolumny tekstowe/boolean po rerunach.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-113 [DONE]
Temat: Krytyczny fix utraty odpowiedzi po zmianie kolejności pytań metryczki.
Kryteria ukończenia:
1. Przesuwanie pytania (`↑/↓`) nie może kasować odpowiedzi w innych pytaniach.
2. Edytor odpowiedzi nie może zapisywać pustego stanu po niestabilnym rerunie widgetu.
Wynik:
- `archetypy-admin/app.py`:
  - dodano helper `_editor_live_df(...)`, który ignoruje nie-DataFrame ze stanu widgetu `st.data_editor`,
  - odczyt danych tabeli odpowiedzi oparty o bezpieczny fallback (widget-state DataFrame -> returned DataFrame -> clean),
  - dodano bezpiecznik: jeśli bieżący odczyt opcji jest pusty, zachowujemy poprzednie odpowiedzi pytania zamiast je nadpisać.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-114 [DONE]
Temat: Etapy 2-5 równolegle — ikony metryczki, radar personalny, legenda Segmentów i domknięcie JST.
Kryteria ukończenia:
1. W tabelach odpowiedzi metryczki kolumna `Ikona` działa jako lista rozwijana emoji (jak dla ikony zmiennej).
2. W `Profile demograficzne archetypu`:
   - radar ma pogrubione etykiety TOP,
   - usunięty opis techniczny pod radarem,
   - dolna legenda ma ciaśniejszy, czytelniejszy układ,
   - pasek zgodności podgrupy renderuje poprawną szerokość.
3. W `🧭 Matching > Segmenty` górna legenda radaru jest natywna/interaktywna (włącz/wyłącz serie).
4. W `Badania mieszkańców - panel` wybór formy raportu usuwa opcję `Wartości` (zostają męskie/żeńskie).
5. Generator JST respektuje dynamiczną metryczkę z `metryczka_config`:
   - kolejność zmiennych jak w konfiguracji,
   - wszystkie kategorie z konfiguracji (także 0%),
   - etykiety i ikony z konfiguracji,
   - synchronizacja pliku generatora do `C:\Poznan_Archetypy_Analiza`.
Pierwszy krok wykonawczy:
- wdrożyć dropdown ikon w `app.py`, następnie podpiąć dynamiczną metryczkę do `settings.json -> analyze_poznan_archetypes.py` i domknąć warstwę wizualną radarów.
Wynik:
- `app.py`:
  - `Ikona` w edytorze odpowiedzi (metryczka + predefiniowane) działa jako `SelectboxColumn`,
  - `Segmenty` radar używa natywnej legendy Plotly (interaktywne show/hide),
  - w panelu generowania raportu JST usunięto opcję `Wartości` (pozostają: `Archetypy męskie`, `Archetypy żeńskie`),
  - poprawiono mapowanie label-mode dla fallbacków ASCII (lepsze podmiany nazw w HTML raportu).
- `admin_dashboard.py`:
  - radar podgrupy ma pogrubiane etykiety TOP,
  - usunięto podpis „Radar pokazuje średnią siłę…”,
  - dopieszczono dolną legendę TOP2/TOP3 (spacing/font),
  - pasek zgodności podgrupy używa bezpośredniego `width: xx%` (stabilny rendering).
- `jst_analysis.py`:
  - `settings.json` dostaje pełne `metryczka_config`,
  - hash źródła raportu uwzględnia `metryczka_config` (wymusza przeliczenie przy zmianach metryczki).
- `JST_Archetypy_Analiza/analyze_poznan_archetypes.py` (+ kopia w `C:\Poznan_Archetypy_Analiza`):
  - dynamiczna metryczka ładowana z `settings.metryczka_config`,
  - kolejność i etykiety zmiennych metryczki idą z konfiguracji,
  - kategorie w tabelach demograficznych zawierają pełną listę z konfiguracji (w tym 0%),
  - ikony zmiennych/kategorii respektują konfigurację (z fallbackiem heurystycznym),
  - korekta ikon domyślnych (`Wiek -> ⌛`, `trudno powiedzieć -> 🤷`, `poglądy/orientacja -> ⚖️`).
- Smoke-check:
  - `python -m py_compile app.py admin_dashboard.py metryczka_config.py jst_analysis.py JST_Archetypy_Analiza/analyze_poznan_archetypes.py` (OK),
  - `python -m py_compile C:\Poznan_Archetypy_Analiza\analyze_poznan_archetypes.py` (OK).

### Hotfix H-115 [DONE]
Temat: Etap 6 — pełny audyt i korekta form żeńskich w opisach archetypów (`opisy_archetypow`).
Kryteria ukończenia:
1. Usunięcie męskich form odnoszących się do archetypów żeńskich (opis, cień, ton, checklisty, pytania kontrolne).
2. Zachowanie sensu merytorycznego i struktury dokumentów `.docx`.
3. Kontrola końcowa regexem na najczęstsze męskie formy błędnie przypisane do żeńskich archetypów.
Pierwszy krok wykonawczy:
- wyeksportować treść dokumentów żeńskich do audytu i zbudować listę rzeczywistych kolizji językowych.
Wynik:
- poprawiono formy żeńskie w 11 dokumentach (`Bohaterka`, `Buntowniczka`, `Czarodziejka`, `Kochanka`, `Komiczka`, `Mędrczyni`, `Niewinna`, `Odkrywczyni`, `Opiekunka`, `Towarzyszka`, `Władczyni`),
- usunięto pozostałości typu: `postrzegany`, `skłonny`, `uzależniony`, `nieodpowiedzialny`, `zmienny`, `bezwzględny`, `agresywny`, `dumny`, `Kochanka/Kochanek` w złym kontekście,
- wykonano kontrolę końcową skanem regex (pozostały tylko neutralne użycia, np. `agresywnych kontrastów`),
- usunięto pliki pomocnicze audytu (`_audit_txt`) po zakończeniu prac.

### Hotfix H-116 [DONE]
Temat: Ikony metryczki + koło archetypów + radar podgrupy + stabilizacja pierwszego zapisu edycji.
Kryteria ukończenia:
1. Lista predefiniowanych ikonek zawiera: `centrowe ↔️`, `orientacja 🧭`, `poglądy ⚖️`, `trudno powiedzieć 🤷`, `nieważny ⭕`.
2. Podświetlenie koła archetypów nie zalewa całych trójkątnych sektorów poza pierścieniem.
3. `Podgląd radarowy podgrupy` renderuje poprawnie osie/archetypy (bez zlepienia etykiet w jednym punkcie).
4. Dolna legenda TOP2/TOP3 ma większe odstępy między rolami.
5. Edycja w tabeli odpowiedzi metryczki nie wymaga podwójnego wpisu.
Wynik:
- `app.py`:
  - rozszerzono bibliotekę ikon (`_METRY_ICON_LIBRARY`) o nowe pozycje,
  - heurystyki fallback w Matchingu (`_matching_guess_*_emoji`) uwzględniają nowe ikony (`↔️`, `🤷`, `⭕`),
  - `st.data_editor` odczytuje live-zmiany również ze stanu delta (`edited_rows/added_rows/deleted_rows`) w `_editor_live_df`, co eliminuje efekt „zapisuje się dopiero za drugim razem”.
- `metryczka_config.py`:
  - heurystyki ikon zmiennej/kategorii dopięte do nowego mapowania (`orientacja -> 🧭`, `poglądy -> ⚖️`, `centrowe -> ↔️`, `trudno -> 🤷`, `nieważny -> ⭕`).
- `admin_dashboard.py`:
  - `mask_for(...)` podświetla wyłącznie pierścień koła archetypów (bez dużych klinów od środka),
  - radar podgrupy używa osi kategorycznej (`theta` jako etykiety), co stabilizuje render etykiet,
  - dolna legenda TOP2/TOP3 ma większe odstępy i czytelniejszy układ.
- Smoke-check:
  - `python -m py_compile app.py admin_dashboard.py metryczka_config.py db_jst_utils.py` (OK).

### Hotfix H-117 [DONE]
Temat: Metryczka i wysyłka — custom ikony odpowiedzi, antyduplikaty, propagacja root `M_*`, czyszczenie odbiorców i fallback import/eksport.
Kryteria ukończenia:
1. W odpowiedziach metryczki można wpisać/wkleić własną ikonę (nie tylko wybór z listy).
2. `📥 Wstaw z zapisanych` respektuje kontrolę duplikatów jak panel predefiniowanych (`Tak/Nie`).
3. Globalna propagacja z predefiniowanych aktualizuje też pytania o kodach pochodnych (`M_X` oraz `M_X_2`, `M_X_3`).
4. Po wysyłce SMS/e-mail pole `Odbiorcy` czyści się automatycznie (personal + JST).
5. `Import/eksport` nie gubi custom kolumn metryczki `M_*` przy starszych payloadach.
Pierwszy krok wykonawczy:
- poprawić `app.py` (edytor metryczki + quick insert + propagacja), następnie `send_link*.py` i fallback warstwy danych (`db_jst_utils.py`).
Wynik:
- `archetypy-admin/app.py`:
  - `Ikona` w tabeli odpowiedzi (metryczka + predefiniowane) działa jako pole tekstowe emoji (obsługa własnych ikonek),
  - dodano kontrolę duplikatów również dla szybkiego `📥 Wstaw z zapisanych` z potwierdzeniem `Tak/Nie`,
  - propagacja predefiniowanego pytania działa po rdzeniu kodowania (`M_KOD` + sufiksy numeryczne, np. `M_KOD_2`),
  - stabilizacja live-edytora: obsługa `edited_cells` i twardsza normalizacja kolumny `Przesuń` do `bool`,
  - `jst_io_view` pobiera świeżą konfigurację metryczki badania przed importem/eksportem.
- `archetypy-admin/db_jst_utils.py`:
  - eksport DataFrame i payload importu uwzględniają dodatkowe kolumny `M_*` wykryte w historycznych payloadach (fallback).
- `archetypy-admin/metryczka_config.py` + fallbacki raportowe:
  - ikona `miasto` ustawiona na `🏬` (spójnie w heurystykach i pickerze).
- `archetypy-admin/send_link.py`, `archetypy-admin/send_link_jst.py`:
  - po wysyłce pole `Odbiorcy` jest czyszczone,
  - dodano flash-komunikat po rerunie.
- Smoke-check:
  - `python -m py_compile app.py admin_dashboard.py db_jst_utils.py metryczka_config.py send_link.py send_link_jst.py` (OK).

### Hotfix H-118 [DONE]
Temat: Domknięcie „Cofnij bez zapisu” + pełna żeńska forma archetypów w segmentach/klastrach/mapie.
Kryteria ukończenia:
1. W `Metryczka` (JST + personal) przy `← Powrót` pojawia się potwierdzenie dla niezapisanych zmian:
   - `Tak (bez zapisu)`,
   - `Nie (zapisz i opuść)`,
   - `Anuluj`.
2. Taki sam mechanizm działa w `⚙️ Ustawienia ankiety` (JST + personal).
3. W raporcie żeńskim nazwy archetypów są spójnie żeńskie w:
   - opisach segmentów (`Co ten segment ceni`, `Dominujące motywy`, `Deficyty`),
   - tabelach `Matryca segmentów` i `Segmenty - przewagi naprawdę istotne`,
   - sekcjach `Skupienia (k-średnich)` i mapach przewag.
Pierwszy krok wykonawczy:
- dodać wspólny guard wyjścia z widoku w `app.py`, następnie podpiąć żeńskie etykiety w krytycznych rendererach HTML/PNG w `analyze_poznan_archetypes.py`.
Wynik:
- `archetypy-admin/app.py`:
  - dodano `guarded_back_button(...)` z 3 akcjami (`Tak/Nie/Anuluj`),
  - podpięto guard dla:
    - `jst_metryczka_view`,
    - `personal_metryczka_view`,
    - `jst_settings_view`,
    - `personal_settings_view`,
  - `Nie (zapisz i opuść)` zapisuje zmiany tym samym torem co główny przycisk `💾` i dopiero potem wychodzi.
- `archetypy-admin/JST_Archetypy_Analiza/analyze_poznan_archetypes.py`:
  - opisy segmentów używają `_display_archetype_label(...)` dla nazw archetypów w tekście,
  - `Matryca segmentów` i `Segmenty - przewagi naprawdę istotne` renderują żeńskie etykiety w trybie żeńskim,
  - tabele TOP5 w sekcji skupień używają żeńskich etykiet archetypów,
  - mapa przewag segmentów (`SEGMENTY_META_MAPA_STALA*`) renderuje żeńskie etykiety punktów archetypów.
- Synchronizacja:
  - skopiowano generator także do `C:\Poznan_Archetypy_Analiza\analyze_poznan_archetypes.py`.
- Smoke-check:
  - `python -m py_compile app.py JST_Archetypy_Analiza/analyze_poznan_archetypes.py` (OK),
  - `python -m py_compile C:\Poznan_Archetypy_Analiza\analyze_poznan_archetypes.py` (OK).

### Hotfix H-119 [DONE]
Temat: Domknięcie guarda `Cofnij` dla przypadku „edytuję i od razu klikam wyjście”.
Kryteria ukończenia:
1. W `Metryczka` (JST + personal) wykrywanie `dirty` opiera się na aktualnym stanie live-edytora w tym samym rerunie.
2. `Cofnij` jest renderowane na górze widoku także w `Ustawienia ankiety` (JST + personal), bez zmiany logiki zapisu.
3. Brak regresji składni (`py_compile`).
Pierwszy krok wykonawczy:
- przepiąć obliczanie `dirty` po zebraniu `edited_cfg` oraz przenieść render `guarded_back_button(...)` do placeholdera osadzonego wyżej.
Wynik:
- `archetypy-admin/app.py`:
  - `jst_metryczka_view` i `personal_metryczka_view` liczą `dirty` po `_render_metryczka_editor(...)` z `edited_cfg` (ten sam klik),
  - guard `Cofnij` renderowany jest przez `st.empty()` osadzone wyżej (spójne miejsce przy długich formularzach),
  - `jst_settings_view` i `personal_settings_view` również renderują guard w górnym placeholderze.
- Smoke-check:
  - `python -m py_compile app.py` (OK).

### Hotfix H-120 [DONE]
Temat: Usunięcie technicznych kolumn `M_*_OTHER` z demografii raportu + przywrócenie fallbacku ikon kategorii.
Kryteria ukończenia:
1. W sekcjach demografii nie pojawiają się sztuczne zmienne typu `Plec Other`, `Wiek Other`, `Material Other`, `Obszar Other`.
2. Pomocnicze kolumny metryczki (np. `M_*_OTHER`, `M_*_TEXT`, `M_*_OPEN`) nie są traktowane jak osobne pytania demograficzne, chyba że są jawnie zdefiniowane w `metryczka_config`.
3. Puste `value_emoji` w konfiguracji odpowiedzi nie wyłącza fallbacku ikon (heurystyki/mapy).
Pierwszy krok wykonawczy:
- dodać filtr kolumn pomocniczych na etapie `parse_metryczka(...)` oraz skorygować wybór ikony kategorii w `analyze_poznan_archetypes.py`.
Wynik:
- `archetypy-admin/JST_Archetypy_Analiza/analyze_poznan_archetypes.py`:
  - dodano `_is_aux_metry_column(...)` + listę sufiksów technicznych (`OTHER`, `INNE`, `OPEN`, `TEXT`, `TXT`, ...),
  - `parse_metryczka(...)` pomija kolumny pomocnicze `M_*` przy dynamicznym dokładaniu zmiennych demograficznych,
  - `_demo_pick_cat_icon(...)` używa ikony dynamicznej tylko, gdy jest niepusta; przy pustej wraca do fallbacku.
- Synchronizacja:
  - skopiowano aktualny generator do `C:\Poznan_Archetypy_Analiza\analyze_poznan_archetypes.py`.
- Smoke-check:
  - `python -m py_compile JST_Archetypy_Analiza/analyze_poznan_archetypes.py` (OK),
  - `python -m py_compile C:\Poznan_Archetypy_Analiza\analyze_poznan_archetypes.py` (OK).

### Hotfix H-121 [DONE]
Temat: Ikony demografii po usunięciu w predef/metryczce + ujednolicenie `miasto -> 🏬`.
Kryteria ukończenia:
1. W raportach kategoria `miasto` ma `🏬` (nie `🏙️`).
2. Gdy w predef/metryczce ikona odpowiedzi jest celowo pusta, raport respektuje pustkę (nie dokleja fallbackowej ikony).
3. Dotyczy zarówno raportu JST (`analyze_poznan_archetypes.py`), jak i „Raportu wielocechowego” w panelu (`admin_dashboard.py`).
Pierwszy krok wykonawczy:
- poprawić logikę priorytetu ikon kategorii: obecność klucza z pustą wartością ma blokować fallback.
Wynik:
- `archetypy-admin/JST_Archetypy_Analiza/analyze_poznan_archetypes.py`:
  - `_demo_pick_cat_icon(...)` traktuje „ikona ustawiona na pusto” jako decyzję użytkownika (bez fallbacku),
  - fallback dla kategorii `miasto` zmieniony na `🏬`.
- `archetypy-admin/admin_dashboard.py`:
  - `_personal_metry_cat_icon(...)` respektuje pustą ikonę w `option_icon_map`,
  - budowanie `option_icons` zachowuje także puste wartości (`value_emoji=""`) zamiast je odrzucać.
- Synchronizacja:
  - zaktualizowano kopię generatora: `C:\Poznan_Archetypy_Analiza\analyze_poznan_archetypes.py`.
- Smoke-check:
  - `python -m py_compile admin_dashboard.py JST_Archetypy_Analiza/analyze_poznan_archetypes.py` (OK),
  - `python -m py_compile C:\Poznan_Archetypy_Analiza\analyze_poznan_archetypes.py` (OK).

### Hotfix H-122 [DONE]
Temat: Demografia (bold max), import-template per badanie, C↔D w imporcie, układ/nazwy sekcji profili.
Kryteria ukończenia:
1. W tabelach demograficznych pogrubienie działa dla realnego maksimum `%` w ramach zmiennej (z obsługą remisów), a nie dla pierwszego wiersza.
2. `💾 Import i eksport baz danych` ma generator szablonu importu oparty o bieżącą metryczkę badania.
3. Import akceptuje `C1..C13` jako alias `D1..D13`.
4. Podgląd/eksport nie pokazuje technicznych kolumn pomocniczych typu `M_*_OTHER`.
5. W raporcie personalnym:
   - nazewnictwo `Profil archetypowy ... (siła archetypu, skala: 0-100)` zostało zastąpione `Profil siły archetypów ... (skala: 0-100)`,
   - `Koło archetypów (pragnienia i wartości)` zostało zastąpione `Koło pragnień i wartości`,
   - sekcje `Koło` + `Rozkład` + `Profile działania archetypów ...` są ułożone pionowo w jednej kolumnie.
6. Gdy brak realnych odpowiedzi metryczkowych (same 0%), radar i profile 0-100 w podstronie demografii personalnej nie są renderowane.
Wynik:
- `archetypy-admin/admin_dashboard.py`:
  - fix boldowania max kategorii (`is_top` po wartości `%`, obsługa remisów),
  - blokada renderu radaru/profili 0-100 przy braku odpowiedzi metryczkowych,
  - nowy układ i nazwy sekcji (`Koło pragnień i wartości`, `Profile działania archetypów ...`, `Profil siły archetypów ...`),
  - tabela podsumowania archetypów: nagłówki `Główny / Wspierający / Poboczny` w stylu pionowym.
- `archetypy-admin/app.py`:
  - dodano `Wygeneruj szablon CSV/XLSX` (per badanie, z aktualnej metryczki),
  - poprawiono podświetlanie najwyższej kategorii w tabelach demografii Matchingu (z remisami),
  - ujednolicono nazwy sekcji profili 0-100 do wariantu `Profil siły ...`.
- `archetypy-admin/db_jst_utils.py`:
  - dodano `import_template_dataframe(...)`,
  - import obsługuje aliasy `C1..C13` <-> `D1..D13`,
  - odfiltrowano techniczne kolumny pomocnicze `M_*_OTHER/...` z podglądu/eksportu.
- `archetypy-admin/JST_Archetypy_Analiza/analyze_poznan_archetypes.py`:
  - normalizacja historycznej ikony `🏙️` -> `🏬` dla kategorii `miasto`.
- Synchronizacja:
  - generator skopiowano także do `C:\Poznan_Archetypy_Analiza\analyze_poznan_archetypes.py`.
- Smoke-check:
  - `python -m py_compile app.py admin_dashboard.py db_jst_utils.py JST_Archetypy_Analiza/analyze_poznan_archetypes.py` (OK),
  - `python -m py_compile C:\Poznan_Archetypy_Analiza\analyze_poznan_archetypes.py` (OK).

### Hotfix H-123 [DONE]
Temat: Deterministyczny moduł interpretacji pod trzema wizualizacjami archetypów w widoku personalnym.
Kryteria ukonczenia:
1. Dodany moduł generujący 3 krótkie opisy na bazie istniejących wyników TOP1/TOP2/(TOP3>=70), bez zmian scoringu.
2. Opisy renderowane pod sekcjami: `Koło pragnień i wartości`, `Koło potrzeb`, `Profil działania archetypu`.
3. Nazwy sekcji zaktualizowane do docelowych, bez przebudowy całego dashboardu.
4. Dodane testy jednostkowe generatora (co-dominacja, TOP3 >= 70, TOP3 < 70, osie balanced).
Pierwszy krok wykonawczy:
- zlokalizować istniejące miejsca renderu trzech wizualizacji oraz źródło wyników TOP1/TOP2/TOP3 i podpiąć pod nie nowy, deterministyczny generator opisów.
Wynik:
- dodano moduł `archetype_interpretation.py` z:
  - `ARCHETYPE_META` (12 archetypów),
  - `LABEL_TO_ID` (męskie/żeńskie etykiety),
  - `generate_archetype_descriptions(...)` zwracającą 3 opisy.
- `admin_dashboard.py`:
  - sekcja `Rozkład archetypów na osiach potrzeb` została nazwana `Koło potrzeb`,
  - pod 3 sekcjami renderowane są nowe opisy interpretacyjne,
  - sekcja kart zmieniona na `Profil działania archetypu`.
- dodano testy jednostkowe: `test_archetype_interpretation.py`.

### Hotfix H-124 [DONE]
Temat: Korekta językowa generatora opisów archetypowych (odmiana i składnia zdań).
Kryteria ukonczenia:
1. Usunięte nienaturalne formy typu `przede wszystkim potrzeba ...`.
2. Zdania raportowe są zrozumiałe i mają poprawną odmianę rzeczowników po przyimkach.
3. Logika generatora i deterministyczność pozostają bez zmian.
Wynik:
- `archetype_interpretation.py`:
  - dodano odmianę fraz wartości (`potrzebą ...` / `potrzebę ...`),
  - poprawiono składnię opisu osi potrzeb (czytelniejsza kolejność i znaczenia),
  - rozdzielono formy wymiarów dla kontekstów `na ...` (biernik) i `oparty na ...` (miejscownik),
  - fallback par wymiarów generuje poprawną polszczyznę (`łączy X z Y`).

### Hotfix H-125 [DONE]
Temat: Dopracowanie układu raportu personalnego + fallback „brak danych” w demografii + eksport kart działania.
Kryteria ukonczenia:
1. W tabeli `Podsumowanie archetypów (liczebność i natężenie)` nagłówki `Główny/Wspierający/Poboczny` używają tej samej rodziny pisma co reszta nagłówka.
2. Przycisk `Połącz i policz matching` jest po prawej stronie sekcji wyboru.
3. Widok 1920×1200 i mniejszy ma lżejsze rozmiary radaru/kół; emoji przy archetypach w tabeli podsumowania są ukrywane dla ≤1920×1200.
4. Tytuł `Koło pragnień i wartości` jest wycentrowany analogicznie do sekcji rozkładu.
5. Sekcje `Heurystyczna analiza koloru...` oraz `Profil siły archetypów ...` są renderowane pod tabelą podsumowania (bez dużej pustej przestrzeni).
6. Zwiększone odstępy pionowe między `Koło pragnień i wartości`, `Rozkład archetypów na osiach potrzeb` i `Profile działania archetypów ...`.
7. Etykiety kart działania mają formę:
   - `Archetyp główny: ... - profil działania`,
   - `Archetyp wspierający: ... - profil działania`,
   - `Archetyp poboczny: ... - profil działania`.
8. W tabelach demograficznych przy 0% we wszystkich kategoriach pojawia się fallback `brak danych` (zamiast błędnego pogrubiania wszystkich pozycji).
9. Full raport DOCX/PDF zawiera również pojedyncze grafiki `Profile działania archetypów`.
10. Podświetlenia w `Kole pragnień i wartości` są wydłużone.
Wynik:
- `archetypy-admin/app.py`:
  - przycisk `Połącz i policz matching` przeniesiony do prawej kolumny,
  - fallback `brak danych` i poprawka boldowania dla tabel demograficznych Matchingu i Segmentów.
- `archetypy-admin/admin_dashboard.py`:
  - tabela podsumowania: spójne fonty nagłówków + warunkowe ukrywanie emoji archetypu dla viewportu ≤1920×1200,
  - mniejsze domyślne rozmiary radaru/kół na desktopie,
  - sekcje `Heurystyczna analiza...` i `Profil siły archetypów ...` przeniesione pod tabelę (w lewej kolumnie),
  - większe odstępy między `Koło pragnień...`, `Rozkład...` i `Profile działania...`,
  - etykiety kart działania zmienione na `Archetyp główny/wspierający/poboczny: ... - profil działania`,
  - fallback `brak danych` dla tabel demografii personalnej,
  - wydłużone kliny podświetlenia w `Kole pragnień i wartości`,
  - eksport pełny DOCX/PDF rozszerzony o stronę z pojedynczymi grafikami `Profile działania archetypów`.
- Smoke-check:
  - `python -m py_compile app.py admin_dashboard.py` (OK).

### Hotfix H-125 [DONE]
Temat: Doprecyzowanie generatora opisów — pełna naturalność polszczyzny i spójność form żeńskich/męskich.
Kryteria ukonczenia:
1. Frazy wartości mają poprawną odmianę (`potrzebie` / `potrzebę` / `potrzebą`).
2. Zdania o dominacji nie mieszają form płci (`Kochanka ... wzmacnia ją Buntowniczka`).
3. Logika obliczeniowa pozostaje bez zmian.
Wynik:
- `archetype_interpretation.py`:
  - dodano odmianę lokatywną (`_phrase_locative`),
  - przebudowano szablon `dominant_with_strong_support` dla `Koło pragnień i wartości`,
  - zmieniono szablony otwarcia opisu działania tak, by nie tworzyć błędów rodzaju gramatycznego,
  - utrzymano bez zmian deterministykę i reguły wyliczania osi/wymiarów.

### Hotfix H-126 [DONE]
Temat: Korekty demografii bez filtrów + układ/typografia panelu archetypów + dopięcie opisów do full raportu.
Kryteria ukonczenia:
1. `brak danych` ma zawsze ikonę `❔` (także gdy w konfiguracji ikon jest pusty wpis).
2. W `Profile demograficzne archetypu` przy braku aktywnych filtrów nie renderujemy „profilu podgrupy filtrowanej” (radar + koła 0-100).
3. Tytuł tabeli podsumowania to `Liczebność i natężenie archetypów`; kolumny `Główny/Wspierający/Poboczny` są węższe, a kolumna `opis` szersza.
4. Radar archetypów skaluje się do szerokości kolumny (bez chowania się pod tabelę).
5. `Heurystyczna analiza koloru psychologicznego` i `Profil siły archetypów ...` są szersze (obszar lewej części raportu) i profil 0-100 jest wyraźnie większy.
6. Tytuł `Profile działania archetypów ...` jest wyrównany do lewej; opis tej sekcji jest pod wykresami.
7. Opisy pod `Koło pragnień i wartości` oraz `Rozkład archetypów na osiach potrzeb` są wyrównane do lewej jak sekcja `Profile działania...`.
8. Full raport DOCX/PDF zawiera także teksty interpretacyjne dla:
   - `Koło pragnień i wartości`,
   - `Rozkład archetypów na osiach potrzeb`,
   - `Profile działania archetypów ...`.
Wynik:
- `archetypy-admin/app.py`:
  - wymuszono `❔` dla kategorii `brak danych` w kartach i tabelach demografii Matchingu/Segmentów (niezależnie od pustej ikonki w mapie).
- `archetypy-admin/admin_dashboard.py`:
  - `_personal_metry_cat_icon(...)` zwraca `❔` dla `brak danych`,
  - przy braku aktywnych filtrów w podstronie demografii:
    - radar pokazuje tylko profil całej próby,
    - sekcja TOP pokazuje tylko całą próbę,
    - koła 0-100 pokazują tylko profil całej próby,
  - tabela podsumowania ma nową nazwę sekcji i nowe proporcje kolumn (`opis` poszerzony),
  - radar archetypów używa `use_container_width=True` na desktopie i automatycznego dopasowania szerokości,
  - sekcja heurystyki + profil siły renderowana w szerszym obszarze (`0.64` szerokości), a profil 0-100 ma większy render,
  - `Koło...`, `Rozkład...`, `Profile działania...` mają nagłówki wyrównane do lewej,
  - opis sekcji `Profile działania...` przeniesiono pod wykresy kart,
  - eksport full DOCX/PDF rozszerzono o stronę z tekstami interpretacyjnymi (3 sekcje jak w panelu).
- Smoke-check:
  - `python -m py_compile app.py admin_dashboard.py` (OK).

### Hotfix H-127 [DONE]
Temat: Dopięcie responsywności radaru + korekta podświetleń koła + usunięcie „dziury” przed heurystyką.
Kryteria ukonczenia:
1. Radar nie ucina etykiet na 1920x1200 i rośnie sensownie na większych ekranach (np. 2560x1440).
2. Podświetlenia `Koło pragnień i wartości` wychodzą od środka i są dłuższe (zbliżone do referencji `panel_bohater_władca_odkrywca.png`).
3. Tekst `Podświetlenie: główny – czerwony, wspierający – żółty, poboczny – zielony` jest wyśrodkowany pod wykresem.
4. `Heurystyczna analiza koloru psychologicznego` jest bezpośrednio pod sekcją tabela+radar (bez dużej pustej przestrzeni).
5. Tytuły `Koło pragnień i wartości` i `Rozkład archetypów na osiach potrzeb` są wycentrowane nad wykresami.
Wynik:
- `archetypy-admin/admin_dashboard.py`:
  - przebudowano layout na:
    - lewa strefa (`left_col`) dla tabeli + radaru + heurystyki + profilu 0-100,
    - prawa strefa (`col3`) dla koła/rozkładu/profili działania,
  - radar:
    - większa wysokość desktop (`radar_plot_size=620`),
    - większa przestrzeń wewnętrzna domeny (`polar.domain=[0.08,0.92]`),
    - łagodniejsze marginesy i mniejszy `tickfont` dla stabilności etykiet,
  - podświetlenie koła:
    - kliny wychodzą od środka (bez wycięcia środka),
    - wydłużono promień klina (`r_outer`),
  - `Koło pragnień i wartości`:
    - tytuł wycentrowany,
    - podpis o podświetleniu wycentrowany pod wykresem,
  - `Rozkład archetypów na osiach potrzeb`:
    - tytuł wycentrowany nad wykresem.
- Smoke-check:
  - `python -m py_compile admin_dashboard.py app.py` (OK).

### Hotfix H-128 [DONE]
Temat: Finalne domknięcie responsywności radaru i geometrii podświetleń koła wg screenów 3157/3158/3160/3161/3162.
Kryteria ukonczenia:
1. Radar ma większą realną szerokość roboczą (bez dodatkowych buforów), a etykiety nie są ucinane na 1920x1200.
2. Na większych ekranach radar nie zostaje sztucznie „mały” względem kolumny.
3. Podświetlenia w `Kole pragnień i wartości` są dłuższe i wychodzą od środka.
4. Podpis `Podświetlenie: ...` jest wycentrowany względem wykresu.
5. Układ sekcji zachowuje heurystykę bezpośrednio pod lewą częścią (tabela+radar), bez dodatkowych zwężeń.
Wynik:
- `archetypy-admin/admin_dashboard.py`:
  - zwiększono promień klina podświetlenia (`mask_for`: `r_outer=0.90 * min(w,h)`),
  - radar:
    - usunięto desktopowe bufory `padL/mid/padR` i renderujemy wykres bezpośrednio w kolumnie,
    - dostrojono `radar_tick_size` i `radar_margins` dla etykiet,
    - poszerzono udział kolumny radaru (`left_col/col3 = 0.70/0.30`, wewnątrz `col1/col2 = 0.34/0.66`),
  - podpis pod `Kołem pragnień i wartości` ma centrowanie przez `margin:auto` + `width:fit-content`.
- Smoke-check:
  - `python -m py_compile admin_dashboard.py app.py` (OK).

### Hotfix H-126 [DONE]
Temat: Personalizacja opisów (imię i nazwisko w dopełniaczu) + raportowy styl tekstu + korekty fleksji i rodzaju.
Kryteria ukonczenia:
1. Opisy przyjmują personalizację `personGenitive` i używają jej w zdaniach otwierających.
2. `Koło pragnień i wartości` zawsze zaczyna się od `Rdzeń motywacyjny ...`.
3. Opisy są mniej „generatorowe”: mniejsze nadużycie słowa `profil`, wyraźny podział na `co motywuje`, `w którą stronę układa się energia`, `jak to działa w praktyce`.
4. Formy żeńskie/męskie w opisie TOP1/TOP2 są poprawne (np. `wzmacniana przez Buntowniczkę`).
5. Dodane/odświeżone testy jednostkowe dla nowego stylu i fleksji.
Wynik:
- `archetype_interpretation.py`:
  - nowa warstwa personalizacji (`personGenitive`),
  - nowe, raportowe szablony opisów,
  - specjalizacje jakościowe dla zestawów `Kochanek/Kochanka + Buntownik/Buntowniczka` oraz `Bohater + Władca (+ Odkrywca)`,
  - poprawki fleksji i rodzaju (`wzmacniana/wzmacniany`, formy biernika etykiet).
- `admin_dashboard.py`:
  - generator dostaje `personGenitive` z bieżącego kontekstu raportu.
- `test_archetype_interpretation.py`:
  - testy pod nową składnię, personalizację i brak błędnych form.

### Hotfix H-129 [DONE]
Temat: Usunięcie zbędnych artefaktów plikowych (`color_ring.svg`, `SEGMENTY_ULTRA_PREMIUM_P_babelki*.png`).
Kryteria ukonczenia:
1. Eksport raportu nie tworzy pośredniego pliku `color_ring.svg`.
2. Pipeline JST nie generuje już `SEGMENTY_ULTRA_PREMIUM_P_babelki.png` ani `SEGMENTY_ULTRA_PREMIUM_P_babelki_values.png`.
3. Smoke-check składni przechodzi dla zmienionych modułów.
Wynik:
- `archetypy-admin/admin_dashboard.py`:
  - konwersja pierścienia koloru działa bez pliku pośredniego SVG (`bytestring -> color_ring.png`).
- `archetypy-admin/JST_Archetypy_Analiza/analyze_poznan_archetypes.py`:
  - wyłączono generowanie bąbelkowej macierzy TOP segmentów (`SEGMENTY_ULTRA_PREMIUM_P_babelki*.png`),
  - usunięto martwy wpis notki wykresu dla `SEGMENTY_ULTRA_PREMIUM_P_babelki.png`.
- Smoke-check:
  - `python -m py_compile admin_dashboard.py JST_Archetypy_Analiza/analyze_poznan_archetypes.py` (OK).

### Hotfix H-130 [DONE]
Temat: Korekta layoutu sekcji „Informacje na temat archetypów ...” + finalny tuning radaru/tabeli/koła.
Kryteria ukonczenia:
1. Usunięta martwa funkcja `_bubble_for_segments(...)`.
2. Radar ma większe etykiety archetypów i responsywną skalę bez degradacji czytelności.
3. Podświetlenia w `Kole pragnień i wartości` skrócone względem H-128.
4. Podpis `Podświetlenie: ...` ma `font-size: 0.88em`.
5. W tabeli `Liczebność i natężenie archetypów` komórka `opis` mieści etykietę z kwadracikiem w jednej linii.
6. Prawa kolumna (`Koło ... / Rozkład ... / Profile działania ...`) jest szersza; lewa sekcja heurystyki krótsza.
7. Opisy pod wykresami mają `font-size: 0.93em`.
Wynik:
- `archetypy-admin/JST_Archetypy_Analiza/analyze_poznan_archetypes.py`:
  - usunięto nieużywaną funkcję `_bubble_for_segments(...)`.
- `archetypy-admin/admin_dashboard.py`:
  - radar:
    - większa czcionka etykiet (`radar_tick_size=16`),
    - większy desktopowy render (`radar_plot_size=760`),
    - domena radaru zawężona (`0.14..0.86`) zamiast zmniejszania fontów,
  - layout kolumn:
    - `left_col/col3 = 0.65/0.35`,
    - `col1/col2 = 0.31/0.69`,
  - `Koło pragnień i wartości`:
    - skrócono klin podświetlenia (`r_outer=0.74`),
    - podpis pod kołem `font-size:0.88em`,
  - tabela podsumowania:
    - nowe szerokości kolumn (szersza kolumna `opis`),
    - `opis` wymuszony bez zawijania (`white-space: nowrap`),
    - dla 1920x1200 lżejszy font/padding tabeli,
  - opisy interpretacyjne: `font-size:0.93em`.
- Smoke-check:
  - `python -m py_compile admin_dashboard.py JST_Archetypy_Analiza/analyze_poznan_archetypes.py` (OK).

### Hotfix H-127 [DONE]
Temat: Rozszerzenie generatora opisów o kolejne wzorce jakościowe (Towarzysz+Błazen, Niewinny+Mędrzec+Twórca, Odkrywca+Opiekun, Opiekunka+Niewinna+Odkrywczyni).
Kryteria ukonczenia:
1. Dla nowych układów generator zwraca opisy zgodne ze stylem raportowym dostarczonym przez użytkownika.
2. Zachowana personalizacja `{imię i nazwisko w dopełniaczu}`.
3. Zachowana deterministyczność i brak zmian logiki scoringu.
4. Testy jednostkowe obejmują nowe przypadki.
Wynik:
- `archetype_interpretation.py`:
  - dodano dedykowane reguły tekstowe dla 4 nowych układów archetypów,
  - utrzymano fallback ogólny dla pozostałych kombinacji,
  - zachowano poprawność odmiany i rodzaju.
- `test_archetype_interpretation.py`:
  - dodano testy dla nowych scenariuszy i ochrony progu TOP3 < 70.

### Hotfix H-128 [DONE]
Temat: Przebudowa generatora na pełny model regułowy (bez twardych case'ów pod konkretne zestawienia).
Kryteria ukonczenia:
1. Generator działa na jednolitych regułach dla wszystkich kombinacji TOP archetypów.
2. Przykłady użytkownika są użyte jako styl i jakość języka, nie jako hardcoded mapowanie konkretnych par.
3. Zachowana personalizacja dopełniacza, próg TOP3 i poprawność fleksji.
4. Testy jednostkowe weryfikują reguły, nie pojedyncze zahardkodowane scenariusze.
Wynik:
- `archetype_interpretation.py`:
  - usunięto dedykowane bloki warunkowe pod konkretne zestawienia,
  - opisy wartości/potrzeb/działania są generowane na wspólnym silniku regułowym.
- `test_archetype_interpretation.py`:
  - testy sprawdzają logikę generatora (otwarcia sekcji, osie, TOP3, fleksja).
