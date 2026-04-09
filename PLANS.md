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

### Krok 8 [PENDING]
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
