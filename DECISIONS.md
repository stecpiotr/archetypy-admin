# DECISIONS.md

## 2026-04-09

### D-001: Lokalizacja plikow sterujacych
Decyzja:
- Pliki `AGENTS.md`, `PLANS.md`, `STATUS.md`, `DECISIONS.md` sa utrzymywane w `archetypy-admin` jako glownym repo dla panelu i raportow JST.
Uzasadnienie:
- Tu jest kod odpowiedzialny za wiekszosc zgloszonych problemow (wysylka linkow, matching, raporty).
- Minimalizuje to ryzyko rozjazdu dokumentacji miedzy repozytoriami.

### D-002: Kolejnosc realizacji
Decyzja:
- Najpierw realizujemy krok 1: poprawki krytyczne dla integralnosci tokenow i bezpieczenstwa procesu ankietowego.
Uzasadnienie:
- Bledny kontekst JST w SMS i mozliwosc ponownego wypelnienia po zakonczeniu to bledy krytyczne funkcjonalnie.

### D-003: Zrodlo prawdy dla resend SMS
Decyzja:
- Resend SMS wyznacza kontekst JST po `study_id` z rekordu (`jst_sms_messages`) i dopiero na tej podstawie buduje link oraz domyslny tekst.
Uzasadnienie:
- Eliminuje ryzyko wysylki z nieprawidlowa JST przy ewentualnym rozjechaniu stanu UI.

### D-004: Token JST jako nosnik kanalu i kontaktu
Decyzja:
- Dodano RPC `get_jst_token_meta`, ktore zwraca kanal (`sms`/`email`), kontakt i `study_slug` dla tokenu.
Uzasadnienie:
- Pozwala pokazac precyzyjny komunikat o ponownym wejsciu (`adres e-mail` vs `numer telefonu`) oraz wymusic zgodnosc sluga z tokenem.

### D-005: Polityka blokady po completed
Decyzja:
- Frontend ankiety JST sprawdza `completed` po tokenie i blokuje ponowne wypelnienie, pokazujac komunikat kontekstowy.
- Jesli nowe RPC metadanych nie jest jeszcze dostepne, frontend wraca do sprawdzenia `isJstTokenCompleted`.
Uzasadnienie:
- Spelnia wymaganie biznesowe "jedno zakonczenie ankiety na token" i poprawia czytelnosc dla uzytkownika koncowego.

### D-006: `Nie spelnia` traktujemy jako stan blokujacy token
Decyzja:
- Token z `rejected_at` jest traktowany jako zakonczony i nie moze ponownie uruchomic ankiety.
Uzasadnienie:
- To domyka wymaganie biznesowe: jeden token = jedna sesja, niezaleznie czy konczy sie pelnym wypelnieniem, czy odrzuceniem na screeningu.

### D-007: Rozszerzenie metryki dla zawodu
Decyzja:
- Dla opcji `M_ZAWOD = "inna (jaka?)"` wymagamy obowiazkowego doprecyzowania tekstowego i zapisujemy je jako `M_ZAWOD_OTHER`.
Uzasadnienie:
- Bez doprecyzowania odpowiedz jest niepelna analitycznie.

### D-008: Resend e-mail oparty o rekord i kontekst JST
Decyzja:
- Resend e-mail (i wysylka e-mail) wymusza link zgodny z tokenem i slugiem JST, a dla domyslnej tresci/tematu regeneruje je z kontekstu JST.
Uzasadnienie:
- Eliminuje przypadki przecieku tresci/sluga innej JST przy ponownej wysylce i starych rekordach.

### D-009: UX metryczki po bledzie
Decyzja:
- Po bledzie walidacji metryczki nie ukrywamy wypelnionych sekcji; respondent widzi caly formularz.
Uzasadnienie:
- Zapobiega mylacemu "pustemu ekranowi" i utracie orientacji w formularzu.

### D-010: Minimalna dlugosc dla `inna (jaka?)`
Decyzja:
- Pole doprecyzowania `M_ZAWOD_OTHER` wymaga minimum 3 znakow.
Uzasadnienie:
- Jeden znak nie daje wartosci analitycznej i powodowal pozorna poprawnosci odpowiedzi.

### D-011: Matching / Demografia renderowana stylem B2
Decyzja:
- Sekcja `🧭 Matching > Demografia` ma korzystac z tych samych proporcji i estetyki co `Demografia priorytetu (B2)`:
  karty (`b2x`-like), grube obramowania tabeli i separatorow, identyczna logika akcentowania TOP kategorii.
- Kontener tabeli ustawiony na `max-width: 100%`, by uniknac obcinania danych na szerszych ekranach.
Uzasadnienie:
- Wymaganie biznesowe to 1:1 spojnosc wizualna z B2 i czytelniejsza prezentacja demografii w Matching.

### D-012: Priorytet zgodnosci 1:1 tabeli Matching z B2
Decyzja:
- Dla `Matching > Demografia` preferujemy wierna zgodnosc wizualna z B2 nad "elastyczne" rozciaganie:
  - wrapper tabeli `max-width: 940px` i `min-width: 720px`,
  - obramowane boksy sekcji,
  - stale rozmiary fontow komorek i naglowkow,
  - pelne obramowanie prawej krawedzi tabeli.
Uzasadnienie:
- User wymaga 1:1 z referencja `Demografia priorytetu (B2)` i wskazal roznice w typografii oraz obramowaniach.

### D-013: Wazenie tabeli demograficznej w Matching
Decyzja:
- W `Matching > Demografia` obie kolumny procentowe (`% grupa dopasowana` oraz kolumna referencyjna JST) liczymy po tych samych wagach poststratyfikacyjnych (plec × wiek), jesli sa zdefiniowane.
- Naglowek kolumny referencyjnej jest dynamiczny i ma forme:
  `{nazwa JST} / (po wagowaniu)`.
- Kolumna roznicy ma etykiete `Róznica (w pp.)` oraz normalna (niepogrubiona) czcionke wartosci.
Uzasadnienie:
- Spojnosc metodyczna porownania wymaga tej samej skali wazenia po obu stronach roznicy.
- User zglosil blad merytoryczny: brak odzwierciedlenia wagowania w kolumnie referencyjnej.

### D-014: Finalna typografia Demografii 1:1
Decyzja:
- Dla sekcji `Matching > Demografia` przyjmujemy finalne rozmiary:
  - naglowki kart sekcji (`📌 ...`, `👥 ...`) wieksze,
  - naglowki kafelkow typu `💰 SYTUACJA MATERIALNA`: `12px`,
  - tekst procentowy kafelkow (`xx.x% • yy.y pp`): `12.5px`,
  - tabela `Profil demograficzny`: `13.5px`.
Uzasadnienie:
- Domkniecie zgodnosci wizualnej z referencja `Demografia priorytetu (B2)` zgodnie z finalna uwaga usera.

### D-015: Tabele bez pustych koncowych wierszy
Decyzja:
- Wysokosc `st.dataframe` dla:
  - `Badania mieszkancow - panel` oraz
  - `🧭 Matching / Podsumowanie`
  jest liczona ciasno od liczby rekordow, bez sztucznie wysokiego minimum generujacego puste koncowe wiersze.
Uzasadnienie:
- User wymaga, aby po ostatnim rekordzie byl tylko minimalny odstep i koniec tabeli.

### D-016: Wymuszenie formatu `x.y` w tabeli Matching / Podsumowanie
Decyzja:
- Kolumny procentowe i roznicy w `🧭 Matching / Podsumowanie` renderujemy jako string
  formatowany `f"{wartosc:.1f}"`, a sortowanie roznicy robimy po osobnej kolumnie numerycznej.
Uzasadnienie:
- Zaokraglenie numeryczne nie gwarantuje stalego pokazywania `.0`.
- Wymaganie biznesowe: zawsze jedno miejsce po przecinku, rowniez dla wartosci calkowitych.

### D-017: Transparentny audyt skladnikow A/B1/B2/D13
Decyzja:
- Funkcja `_calc_jst_target_profile` poza profilem zwraca tez audyt pokrycia i srednich skladowych:
  `A`, `B1`, `B2`, `D13`, `TOTAL` dla kazdego archetypu.
- Wynik audytu jest wyswietlany w sekcji opisu metryki dopasowania.
Uzasadnienie:
- User potrzebuje precyzyjnego wyjasnienia, skad biora sie wartosci `Oczekiwania mieszkancow (%)`
  i jak liczony jest komponent A.
- Audyt zmniejsza ryzyko "czarnej skrzynki" i przyspiesza wykrywanie anomalii danych.

### D-018: Tytul raportu z `N` + aktualizacja istniejacych runow
Decyzja:
- Generator raportu HTML przyjmuje `n_respondents` i dokleja do tytulu `(N=...)`.
- Przy uruchamianiu analizy aktualizujemy `analyze_poznan_archetypes.py` takze w istniejacym katalogu runa.
Uzasadnienie:
- User wymaga jawnej liczebnosci proby w naglowku raportu.
- Bez synchronizacji istniejacych runow poprawka mogla nie wejsc do raportu mimo aktualizacji kodu zrodlowego.

### D-019: Nowa metryka `Poziom dopasowania` (odporna na zawyzanie)
Decyzja:
- Rezygnujemy z prostego wzoru `100 - MAE`.
- Stosujemy metryke mieszana:
  `match = clamp(0,100, 0.40*(100-MAE) + 0.25*(100-RMSE) + 0.35*(100-TOP3_MAE))`,
  gdzie:
  - `MAE` = srednia `|Δ|` dla 12 archetypow,
  - `RMSE` = pierwiastek ze sredniej kwadratow `|Δ|`,
  - `TOP3_MAE` = srednia z 3 najwiekszych `|Δ|`.
Uzasadnienie:
- `MAE` samo w sobie bywa zbyt "lagodne" i maskuje duze luki.
- `RMSE` i `TOP3_MAE` podbijaja kare za skrajne rozjazdy, dzieki czemu wynik nie wychodzi sztucznie wysoki.

### D-020: Uporzadkowana prezentacja informacji o dopasowaniach
Decyzja:
- Sekcje `Najlepsze dopasowania` i `Największe luki` prezentujemy jako dwa boksy z chipami,
  a kazdy chip zawiera nazwe archetypu i konkretna wartosc `|Δ|` (w pp).
- Dodatkowo pokazujemy panel skladowych metryki (MAE, RMSE, TOP3 luk) oraz pasmo oceny.
Uzasadnienie:
- User zglosil niski poziom czytelnosci poprzedniej sekcji.
- Pokazanie liczb przy archetypach przyspiesza interpretacje i decyzje strategiczne.

### D-021: Liczniki TOP3/TOP1 raportujemy surowo, udzialy procentowe pozostaja wazone
Decyzja:
- W tabelach rankingowych B (`B1_top3`, `B2_top1`, `B1_trojki`) kolumna `liczba` jest liczona surowo
  (rzeczywista liczba wskazan/rekordow), a kolumna `%` dalej liczona na wagach.
Uzasadnienie:
- User oczekuje zgodnosci sum `liczba` z baza danych (1:1).
- Wcześniej `liczba` byla de facto zaokraglonym licznikiem wazonym, co powodowalo rozjazdy
  (np. `B1: 2745 vs 2741`, `B2: 1048 vs 1050`).

### D-022: Audyt agregacji pytan jako staly artefakt raportu
Decyzja:
- Generator zapisuje `question_aggregation_audit.csv` z kontrola:
  - `A1..A18`, `B1`, `B2`, `D13`,
  - `expected_raw`, `reported_raw`, `delta`.
- Dodatkowo loguje ostrzezenie, gdy `delta != 0`.
Uzasadnienie:
- Wymaganie biznesowe: "zero bledow" i mozliwosc szybkiego wykrycia regresji.
- Audyt jest powtarzalny i nie wymaga recznego liczenia po kazdej zmianie.

### D-023: Parser B1/B2/D13 odporny na warianty formatu importu
Decyzja:
- B1 parsujemy przez `_clean_binary_mark` (obsluga m.in. `1.0`, bool, dodatnich wartosci liczbowych).
- `_parse_archetype_index` rozszerzono o warianty numeryczne (`1..12`, `0..11`, `nr 1`).
Uzasadnienie:
- Zmniejsza ryzyko utraty poprawnych odpowiedzi przy importach z roznych formatow CSV/Excel.

### D-024: Krok 7 porownuje profile w module wynikow personalnych na jednym wyborze JST
Decyzja:
- W `📊 Sprawdz wyniki badania archetypu` dodajemy lokalny selektor:
  `Porownaj z badaniem mieszkancow (JST)`.
- Domyslny wybor probujemy dopasowac po nazwie miasta polityka (`city_nom` vs `jst_name/jst_full_nom`),
  ale user moze go swobodnie zmienic.
Uzasadnienie:
- User potrzebuje porownania "obok siebie" i "na jednym radarze" bez przechodzenia do osobnego modulu.
- Lokalny selektor skraca sciezke analityczna i upraszcza porownanie ad-hoc.

### D-025: Radar 0-20 i profil 0-100 dla mieszkancow liczymy z tej samej metodologii JST co w Matching
Decyzja:
- Profil mieszkancow do porownania liczony jest jako:
  `0.40*A + 0.20*B1 + 0.25*B2 + 0.15*D13` (skala 0..100) dla kazdego archetypu.
- Dla radaru 0-20 stosujemy liniowe przeskalowanie (`wartosc_0_100 / 5`), aby nakladac dane na os z raportu personalnego.
- TOP3 polityka i TOP3 mieszkancow dostaja osobne palety kolorow i wspolna legende.
Uzasadnienie:
- Zapewnia spojna metodyke pomiedzy Matching i nowym porownaniem w widoku personalnym.
- Pozwala utrzymac czytelny overlay 0-20 bez przebudowy calego modulu wykresow.

### D-026: Stopka build musi byc cross-platform (Windows/Linux)
Decyzja:
- W `app.py` wykrywamy `git` przez `shutil.which("git")` (z fallbackiem do `git`),
  zamiast sztywnej sciezki `/usr/bin/git`.
Uzasadnienie:
- Twarda sciezka linuksowa powodowala na Windows fallback `unknown-time | local`,
  mimo ze repo i historia commita byly dostepne.

### D-027: Lokalizacja porownan profili archetypowych
Decyzja:
- Porownanie `polityk vs mieszkancy` (radar 0-20 i profile 0-100 obok siebie)
  ma byc renderowane wyłącznie w module `🧭 Matching` (zakladka `Podsumowanie`),
  a nie w module `📊 Sprawdz wyniki badania archetypu`.
Uzasadnienie:
- To porownanie jest elementem procesu matchingu dwoch badan i ma byc osadzone
  przy metrykach dopasowania oraz tabeli roznic.

### D-028: Build badge musi dzialac bez lokalnego `.git` na deployu
Decyzja:
- `_app_build_signature()` stosuje kaskade zrodel metadanych:
  1) env/secrets (`*_COMMIT_SHA`, `*_COMMIT_TIME`),
  2) lokalny git (jesli dostepny),
  3) `DEPLOYED_SHA` / `.deployed_sha`,
  4) GitHub API (`repos/{repo}/commits/{branch}`).
- Wynikowy timestamp zawsze formatujemy do strefy `Europe/Warsaw`.
Uzasadnienie:
- W runtime deploy (panel) moze brakowac historii git, co dawalo `unknown-time | local`.
- GitHub API daje wiarygodny fallback zgodny z tym, co widac na stronie commitow.

### D-029: Kompatybilnosc renderu obrazow Streamlit w Matching
Decyzja:
- W sekcji porownania profili 0-100 (`🧭 Matching`) render obrazow idzie przez fallback:
  1) `st.image(..., use_container_width=True)`,
  2) fallback do `st.image(..., use_column_width=True)`,
  3) fallback do `st.image(...)`.
Uzasadnienie:
- Na czesci srodowisk (starszy Streamlit) parametr `use_container_width` dla `st.image` powoduje wyjatek,
  przez co znikalo cale porownanie profili.

### D-030: Cache raportu JST zalezy od wersji silnika generatora
Decyzja:
- Hash runa (`.source_hash.txt`) obejmuje nie tylko dane i parametry badania,
  ale takze SHA pliku `analyze_poznan_archetypes.py`.
Uzasadnienie:
- Wczesniej zmiany logiki raportu nie wymuszaly przeliczenia, jesli dane JST byly te same;
  user mogl widziec stare wyniki mimo aktualizacji kodu.

### D-031: Layout wykresow w Matching ma priorytet czytelnosci nad "upchaniem" elementow
Decyzja:
- W `🧭 Matching / Podsumowanie`:
  - radar 0-20 renderujemy ze stala wysokoscia (`height=560`),
  - legende TOP3 pokazujemy w prostym, dwukolumnowym ukladzie tekstowym,
  - profile 0-100 renderujemy z limitem szerokosci (`width=520`) i po wyraznym separatorze sekcji.
Uzasadnienie:
- W praktyce poprzedni uklad powodowal nakladanie i chaos wizualny na czesci ekranow.
- Celem tej sekcji jest porownanie analityczne, wiec najpierw musi byc czytelna i stabilna.

### D-032: Naglowki profili 0-100 w Matching wyswietlamy w dopelniaczu
Decyzja:
- W sekcji porownania kol 0-100 (`🧭 Matching`) etykiety sa:
  - `Profil archetypowy {osoby w dopelniaczu}`,
  - `Profil archetypowy mieszkańców {JST w dopelniaczu}`.
- Usuwamy z naglowkow dopisek o skali `(siła archetypu, skala: 0-100)`.
Uzasadnienie:
- User wymaga precyzyjnej formy jezykowej i krotszego, czystszego naglowka.
- Dane odmiany sa juz w modelu (`*_gen`) albo mozliwe do bezpiecznego wyliczenia fallbackiem.

### D-033: Standalone HTML raportu JST udostepniamy tylko, gdy jest realnie bezpieczny
Decyzja:
- Przycisk `📥 Pobierz raport HTML (pełny)` jest aktywny tylko, gdy jednoplikowy HTML
  (po osadzeniu zasobow) miesci sie w limicie `JST_REPORT_STANDALONE_HTML_LIMIT_BYTES`.
- Gdy limit jest przekroczony albo osadzanie sie nie powiedzie, UI jednoznacznie kieruje
  do pobrania `🧳 ZIP (WYNIKI)` i nie udaje, ze "sam HTML" bedzie dzialal.
Uzasadnienie:
- Dla duzych raportow osadzony HTML potrafi byc skrajnie ciezki i niestabilny.
- User wprost wskazal, ze mylacy przycisk HTML bez pelnej funkcjonalnosci wprowadza w blad.

### D-034: Pobieranie plikow nie moze wywolywac rerun z efektem "szarego zawieszenia"
Decyzja:
- Dla przyciskow `st.download_button` ustawiamy `on_click=\"ignore\"` (w raportach JST),
  aby klikniecie pobierania nie triggerowalo rerunu aplikacji.
Uzasadnienie:
- Usuwa to nieczytelny efekt wizualny (wyszarzenie/overlay) i poprawia UX pobierania.

### D-035: Pelny podglad online probujemy osadzic on-demand, a gdy to niemozliwe - pokazujemy jawny komunikat
Decyzja:
- Po wylaczeniu `Tryb lekki renderowania` aplikacja probuje osadzic zasoby raportu on-demand.
- Jesli wynik jest za duzy albo osadzanie konczy sie bledem, nie renderujemy "udawanego pelnego" widoku;
  zamiast tego pokazujemy jasny komunikat i rekomendujemy tryb lekki / ZIP.
Uzasadnienie:
- User oczekiwal, ze "pelny podglad" faktycznie osadzi obrazy; fallback do surowego HTML byl mylacy.

### D-036: Fonty wykresow JST maja byc deterministyczne miedzy srodowiskami
Decyzja:
- Generator raportu wybiera font bazowy z kolejki: najpierw fonty dostarczone z repo (`assets/fonts`),
  dopiero potem fonty systemowe.
- Dodano fonty `segoeui.ttf` i `segoeuib.ttf` do `assets/fonts`, aby zmniejszyc rozjazdy miedzy
  lokalnym wzorcem a raportami generowanymi na serwerze.
Uzasadnienie:
- Wczesniej wybor opieral sie glownie o dostepnosc systemowa, co dawalo inny wyglad PNG
  na roznych maszynach/deployach.

### D-037: `Oczekiwania mieszkańców (%)` liczymy z pelnych skladowych A/B1/B2/D13
Decyzja:
- W `🧭 Matching` wynik archetypu JST jest liczony jako srednia z 4 pelnych komponentow procentowych:
  `score = (A_pct + B1_pct + B2_pct + D13_pct) / 4`.
- Nie stosujemy juz wag komponentow `40/20/25/15`.
- W zakresie `🧭 Matching` decyzja ta nadpisuje starsze opisy wag komponentow.
Uzasadnienie:
- User jednoznacznie wymagal odejscia od wag i uzycia pelnych wartosci kazdego komponentu.
- Srednia 4 skladowych utrzymuje skale 0..100 i pozwala zachowac porownywalnosc z profilem polityka.

### D-038: Tytuly profili 0-100 w Matching sa centrowane nad wykresami
Decyzja:
- W sekcji `Profile archetypowe 0-100` tytuly obu profili renderujemy jako centralnie wyrownane naglowki HTML (`text-align:center`).
Uzasadnienie:
- Poprawia czytelnosc i spelnia wymaganie usera, aby tytuly byly na srodku wykresow.

### D-039: Build badge ma pokazywac czas ostatniego commita z `main` (GitHub HEAD)
Decyzja:
- `_app_build_signature()` ma priorytetowo pobierac SHA i czas z GitHub API dla HEAD wskazanej galezi (`main`),
  a dopiero potem uzywac lokalnego git i env/secrets fallback.
- Cache zapytania do GitHub API ustawiamy na `60s`, by odswiezenie stopki po deployu bylo szybkie.
Uzasadnienie:
- User oczekuje zgodnosci stopki z lista commitow na GitHub; stale env z poprzedniego deployu byly mylace.

### D-040: Wzor `match = ...` musi byc jawnie oddzielony od liczenia `Oczekiwań mieszkańców (%)`
Decyzja:
- W sekcji wyjasnienia metryk dodajemy explicite komunikat, ze wzor `match = ...` dotyczy tylko
  wskaznika `Poziom dopasowania`.
Uzasadnienie:
- User slusznie zglosil ryzyko pomylenia dwoch osobnych rzeczy: metryki dopasowania i profilu oczekiwan.

### D-041: Korekta typografii po regresji wizualnej Matching
Decyzja:
- Po centrowaniu tytulow profili 0-100 utrzymujemy stonowane rozmiary fontow:
  - naglowki sekcji: `17px`,
  - tytuly profili 0-100: `16px`.
Uzasadnienie:
- Poprzednie duze fonty pogarszaly odbior i czytelnosc (zgloszenie usera na zrzutach 2783/2784).

### D-042: Edytor `segment_hit_threshold_overrides` ma byc odporny na praktyczne wklejki
Decyzja:
- Parser progow przyjmuje nie tylko czysty JSON, ale tez format liniowy:
  - `segment: wartosc`,
  - `segment = wartosc`,
  z tolerancja na smart quotes i trailing commas.
Uzasadnienie:
- User wkleja progi z notatek/manuali i nie zawsze trzyma idealny JSON; narzedzie ma pomagac, nie blokowac.

### D-043: Reset progow nie modyfikuje aktywnego klucza widgetu w tej samej iteracji
Decyzja:
- W `jst_analysis_view` reset/zapis korzysta z klucza pomocniczego `pending` + `st.rerun()`,
  a nie bezposredniej zmiany `st.session_state[widget_key]` po utworzeniu widgetu.
Uzasadnienie:
- Eliminuje `StreamlitAPIException` (`cannot be modified after the widget ... is instantiated`).

### D-044: `Oczekiwania mieszkańców (%)` z premią dla pytan TOP1
Decyzja:
- W Matching stosujemy formule:
  `score = (A_pct + B1_pct + 2*B2_pct + 2*D13_pct) / 6`.
- `B2` i `D13` dostaja mnoznik x2 jako sygnal TOP1.
Uzasadnienie:
- User oczekuje mniejszego spłaszczenia profilu i mocniejszego docenienia pytan, gdzie wybierany jest najwazniejszy archetyp.

### D-045: Sekcje Matching maja byc wizualnie lekkie i spojne z reszta panelu
Decyzja:
- Naglowki sekcji `Porównanie...` i `Profile...` renderujemy bez pelnego obramowanego boxa;
  stosujemy prosty separator dolny i transparentne tlo.
Uzasadnienie:
- Poprzedni styl "kartowy" odstawal od reszty interfejsu i byl negatywnie oceniony przez usera.

### D-046: `Oczekiwania mieszkańców` przechodzą na indeks syntetyczny ISOA/ISOW
Decyzja:
- W `🧭 Matching` porzucamy wzor sredniej/prostych premii i liczymy indeks:
  - `E = 0.50*z(A) + 0.20*z(B1) + 0.30*z(B2)`,
  - `D = 0.70*z(N) + 0.30*z(MBAL)`,
  - `SEI_raw = 0.80*E + 0.20*D`,
  - `SEI_100` min-max do `0..100` (fallback `50`).
- Komponenty:
  - `A`: `% oczekujących` z versusów,
  - `B1`: TOP3 share,
  - `B2`: TOP1 share,
  - `N`: negatywne doświadczenie,
  - `MBAL`: `Mneg - Mpos`.
Uzasadnienie:
- User wymagał metody odpornej na różne skale komponentów oraz lepiej oddającej społeczne oczekiwanie niż prosta średnia.

### D-047: Nazewnictwo indeksu zależy od aktywnego trybu etykiet
Decyzja:
- W `🧭 Matching` dodajemy radio trybu etykiet (`Archetypy` / `Wartości`) i dynamicznie pokazujemy:
  - `ISOA` / `Indeks Społecznego Oczekiwania Archetypu`,
  - albo `ISOW` / `Indeks Społecznego Oczekiwania Wartości`.
- Logika liczenia pozostaje identyczna, zmienia się tylko nazewnictwo i etykiety.
Uzasadnienie:
- User wymaga dynamicznej nomenklatury bez duplikowania logiki obliczeń.

### D-048: Raport JST dostaje dedykowaną zakładkę ISOA/ISOW zaraz po `Podsumowanie`
Decyzja:
- W `raport.html` zakładka `tabW` została przebudowana na:
  - `ISOA` (tryb Archetypy),
  - `ISOW` (tryb Wartości),
  i ustawiona jako druga zakładka (zaraz po `Podsumowanie`).
- Zakładka zawiera: metodologię, podstawę danych, tabelę rankingową, wykres kołowy 0-100 oraz Top3/Bottom3.
Uzasadnienie:
- User oczekiwał osobnego, czytelnego miejsca dla nowego indeksu z pełnym kontekstem interpretacyjnym.

### D-049: Wykres ISOA/ISOW ma być zgodny wizualnie z kołem profilu (referencja 2786)
Decyzja:
- Do wizualizacji ISOA/ISOW używamy koła 0-100 (ten sam język wizualny co wykres profilu), z dynamicznymi podpisami:
  - archetypy w trybie `Archetypy`,
  - wartości w trybie `Wartości`.
Uzasadnienie:
- User wprost wskazał docelowy styl wykresu i wymóg dynamicznych podpisów.

### D-050: Duże pełne podglądy raportu w panelu nie mogą być blokowane zbyt niskim limitem sekretu
Decyzja:
- Hard limit podglądu panelowego wyznaczamy jako `max(secret, safe_limit, 260MB)`.
- Dla podglądu oznaczonego jako `too_large` domyślnie włączamy opcję uruchomienia pełnej wersji (z ostrzeżeniem o wydajności), zamiast prezentować to jako „niedziałający podgląd”.
Uzasadnienie:
- User zgłosił realny przypadek, w którym raport był poprawny, ale panel odrzucał podgląd przez zbyt niski limit konfiguracyjny.

### D-051: ISOA/ISOW ma byc zakotwiczony w A, bez finalnego min-max
Decyzja:
- Finalny indeks ISOA/ISOW liczymy tak:
  - `P = 0.35*z(B1) + 0.65*z(B2)`,
  - `D = 0.70*z(N) + 0.30*z(MBAL)`,
  - `P_adj = 8*tanh(P/1.5)`,
  - `D_adj = 4*tanh(D/1.5)`,
  - `SEI_raw = A + P_adj + D_adj`,
  - `SEI_100 = clamp(SEI_raw, 0..100)`.
- Rezygnujemy z koncowego min-max po 12 pozycjach.
Uzasadnienie:
- Min-max wymuszal sztuczne skrajnosci (100/0) niezaleznie od realnego poziomu oczekiwania.
- User wymaga indeksu bardziej "realnego", zakotwiczonego w `% oczekujacych` z pytania A.

### D-052: Sekcja A wraca jako osobna zakladka, ale pod nazwa PPP
Decyzja:
- Nie usuwamy osobnej zakladki dla sekcji A.
- Widoczne nazwy `IOA/IOW` podmieniamy na:
  - `Profil Preferencji Przywodztwa (PPP)`,
  - skrót `PPP`.
- ISOA/ISOW zostaje bez zmian (to oddzielny indeks syntetyczny).
Uzasadnienie:
- User zgłosił, ze usuniecie zakladki bylo niezgodne z oczekiwaniem.
- Jednoczesnie user wymagal unikniecia mylenia IOA z ISOA/ISOW.

### D-053: Limity podgladu online musza respektowac realny limit Streamlit
Decyzja:
- D-050 zostaje uszczelnione:
  - limity `safe` i `hard` sa wyliczane wzgledem `server.maxMessageSize`,
  - nie pozwalamy wymusic pelnego podgladu ponad `hard_limit`,
  - full preview jest blokowany wczesniej z jasnym komunikatem.
Uzasadnienie:
- User nadal dostawal `MessageSizeError` przy wymuszonym podgladzie.
- Sekretowy limit nie moze byc wyzszy niz realny limit serwera.

### D-054: Inline assets kompresujemy przy osadzaniu, z delikatnym downscale
Decyzja:
- W `jst_analysis.py` podczas zamiany obrazow na data URI:
  - stosujemy kompresje (JPEG/WEBP),
  - dla bardzo duzych obrazow delikatnie zmniejszamy rozdzielczosc (long edge max ~1900 px),
  - wybieramy mniejszy wariant tylko, gdy daje realny zysk.
Uzasadnienie:
- Redukuje rozmiar payloadu do przegladarki bez zmiany logiki raportu.
- Ogranicza ryzyko przekroczenia limitu komunikatu przy pelnym podgladzie.

### D-055: ISOA/ISOW finalnie przechodzi na wariant B (neutralne odchylenia, bez z-score i bez min-max)
Decyzja:
- Dla finalnego indeksu ISOA/ISOW stosujemy wariant B:
  - `delta_B1 = B1 - 25.0`,
  - `delta_B2 = B2 - 8.33`,
  - `delta_N = N - 50.0`,
  - `K_B = 0.35*delta_B1 + 0.90*delta_B2 + 0.08*delta_N + 0.20*MBAL`,
  - `SEI_B = A + K_B`,
  - `SEI_B_100 = clamp(SEI_B, 0..100)`.
- Nie stosujemy finalnego min-max, ani standaryzacji z-score dla wyniku końcowego.
Uzasadnienie:
- User wskazal, ze min-max i relatywne skale zbyt latwo produkowaly skrajnosci 0/100.
- Wariant B utrzymuje zakotwiczenie wyniku w realnym poziomie `% oczekujących` z pytania A.

### D-056: Rozdzielenie stylu tabel PPP i ISOA/ISOW
Decyzja:
- Tabela glowna PPP ma zachowac styl "bogaty":
  - ikony w kolumnie nazwy,
  - kolorowane naglowki wskaznikowe,
  - pogrubiona kolumna `% oczekujących`.
- Tabela glowna ISOA/ISOW ma miec jednolite czarne naglowki kolumn.
Uzasadnienie:
- User wymagal powrotu poprzedniej estetyki PPP, ale jednoczesnie zglaszal problemy z kolorystyka naglowkow w tabeli ISOA/ISOW.

### D-057: Fallback pobierania raportu, gdy panel chwilowo nie odnajduje `raport.html`
Decyzja:
- W `jst_analysis_view`, jesli raport jest policzony, ale nie udaje sie znalezc pliku `WYNIKI/raport.html`, panel pokazuje:
  - ostrzezenie diagnostyczne,
  - fallback pobrania HTML z cache sesji (jezeli dostepny),
  - wskazanie `Przelicz od nowa` dla odtworzenia brakujacego artefaktu runa.
Uzasadnienie:
- User zglosil przypadek "Raport gotowy", ale bez przyciskow pobierania; fallback eliminuje pusty stan.

### D-058: Domyslne progi segmentow rozszerzamy o brakujace reguly 0/2 i 1/1
Decyzja:
- Domyslny zestaw `segment_hit_threshold_overrides` rozszerzamy o:
  - `0 z 2 · #2: 4.0`,
  - `0 z 2 · #3: 4.0`,
  - `1 z 1 · #1: 3.0`,
  - `1 z 2 · #2: 3.0`.
- Zmiana obowiazuje:
  - runtime panelu (`app.py`),
  - domyslne `settings.json` w lokalizacji D: i C:.
Uzasadnienie:
- User podal docelowy komplet progow, ktory ma byc nowym baseline dla kolejnych przeliczen.

### D-059: `🧭 Matching` ma pokazac TOP3 polityk vs JST jako osobny, wizualny blok porownawczy
Decyzja:
- Pod sekcja `Najlepsze dopasowania / Największe luki` dodajemy nowy blok 2 kart:
  - `TOP3 archetypów/wartości dla {osoba w dopełniaczu}`,
  - `TOP3 archetypów/wartości dla {JST w dopełniaczu}`.
- Forma: nowoczesne karty z etykietami rangi (`Główny`, `Wspierający`, `Poboczny`), bez listy `1/2/3`.
Uzasadnienie:
- User wprost wymagал atrakcyjniejszej, bardziej "produktowej" prezentacji TOP3 i porownania obok siebie.

### D-060: Legenda radaru porownawczego ma byc dedykowana (nie surowa legenda Plotly)
Decyzja:
- Dla `Porównanie profili ...`:
  - wyłączamy standardowa legende Plotly,
  - renderujemy dedykowana legende UI z próbkami linii,
  - nazwy dynamiczne:
    - `profil polityka ({osoba})`,
    - `profil mieszkańców ({JST})`,
  - usuwamy tekstowy dopisek `Niebieska linia...`.
Uzasadnienie:
- Dotychczasowa legenda byla oceniona jako slaba wizualnie i dublowala informacje.

### D-061: Wariant B – precyzja neutralu B2 i jawna kontrola MBAL w eksporcie
Decyzja:
- Neutral dla B2 ustawiamy dokladnie na `8.3333333333` (zamiast `8.33`).
- Dodajemy pomocniczy eksport kontroli MBAL:
  - `Mneg`,
  - `Mpos`,
  - `MBAL = Mneg - Mpos`,
  w pliku `ISOA_ISOW_MBAL_control.csv`.
Uzasadnienie:
- User wymagal wiekszej precyzji i transparentnosci bez zmiany samej metodologii wariantu B.

### D-062: Widok `Strategia komunikacji` w Matching ma byc bardziej decyzyjny
Decyzja:
- Rozszerzamy zakladke `Strategia komunikacji` z 3 prostych linijek do 4 blokow:
  - os przekazu,
  - luki do domknięcia,
  - segment docelowy,
  - plan testow (14 dni).
Uzasadnienie:
- User poprosil o realnie bardziej rozbudowany widok, a nie tylko skróconą notatkę.

### D-063: Inliner standalone HTML nie moze zmieniac typu cudzyslowu dla `src/href`
Decyzja:
- W `jst_analysis.py` regex podmiany `src/href` przechwytuje i zachowuje oryginalny quote (`'` lub `"`), zamiast wymuszac zawsze `"..."`.
Uzasadnienie:
- Wymuszanie `"` uszkadzalo duze bloki JS/JSON osadzajace HTML w stringach (szczegolnie Segmenty/Skupienia/Filtry), przez co standalone/full HTML tracil interaktywnosc, mimo ze ZIP dzialal poprawnie.

### D-064: Podsumowanie PPP ma miec 4 boksy w jednym rzędzie, a ISOA/ISOW wheel ma byc przy lewej krawedzi
Decyzja:
- `ioa-summary-grid` ustawiono na 4 kolumny (desktop), aby wszystkie bloki Top/Bottom + PPP byly obok siebie.
- `isoa-wheel-wrap` pozostaje o szerokosci `85%`, ale bez centrowania (`margin:0`), czyli wyrównane do lewej.
Uzasadnienie:
- User wymagal bardziej zwartego ukladu podsumowania PPP i lewostronnego osadzenia glównego wykresu ISOA/ISOW.

### D-065: Matching UI — neutralniejsza nawigacja i mocniejsze wskazanie kontekstu porownania
Decyzja:
- Taby w `🧭 Matching` dostaly neutralniejsze, szare tło kontenera i ostre dolne rogi.
- Sekcja "dla kogo jest matching" jest renderowana jako wyrazna karta 2-kolumnowa (badanie personalne vs badanie mieszkańców).
- Dodatkowo zmniejszono globalny górny offset kontenera do `30px`.
Uzasadnienie:
- User zglosil zbyt duza pusta przestrzen na gorze i slabą czytelnosc informacji, kogo dotyczy aktualne porownanie.

### D-066: TOP3 polityk/JST w Matching ma utrzymywać stałą geometrię i ikonki
Decyzja:
- Wiersze TOP3 sa renderowane w siatce `118px + 1fr` (stala szerokosc etykiety roli), z ikoną przy nazwie i kolorami zgodnymi z rolą (`główny/wspierający/poboczny`).
Uzasadnienie:
- User wskazal problem "wciecia" drugiego wiersza (`Wspierający`) i brak ikon, przez co porownanie bylo mniej czytelne.

### D-067: Radar porownawczy odzyskuje klikalna legendę Plotly
Decyzja:
- Dla dwoch glownych linii (`profil polityka`, `profil mieszkańców`) wlaczono `showlegend=True` i `itemclick=toggle`, aby mozna bylo ukrywac/pokazywac linie kliknieciem.
- Jednoczesnie zmniejszono marginesy gorne/dolne, by legenda i blok TOP3 byly blizej wykresu.
Uzasadnienie:
- User oczekiwal powrotu funkcji klikania legendy i mniejszych "dziur" pionowych wokol radaru.

### D-068: Realizacja kolejnych poprawek Matching jest etapowa (pakietami), nie hurtowo
Decyzja:
- Po nowych uwagach usera dalsze poprawki dzielimy na etapy:
  - A: TOP3/tabs/radar (wizual),
  - B: metryka `Poziom dopasowania`,
  - C: demografia box + separacja sekcji 0-100.
Uzasadnienie:
- User jawnie poprosil o prace "krok po kroku", grupujac podobne zagadnienia, aby uniknac chaosu i problemow z kompaktowaniem.

### D-069: TOP3 w Matching uzywa ikon archetypow z tych samych assetow co kola
Decyzja:
- W kartach `TOP3 ... dla {osoba/JST}` nie uzywamy juz samych emoji.
- Ikony renderujemy z plikow `ikony/*.png` (te same assety, ktore sa uzywane na wykresach kolowych), osadzajac je jako data URI.
Uzasadnienie:
- User wymagal, aby ikony w TOP3 byly zgodne wizualnie z ikonami archetypow z wykresow.

### D-070: Radar i demografia — priorytet czytelnosci i braku kolizji layoutu
Decyzja:
- Na radarze porownawczym JST ma markery kwadratowe (linia i TOP3), a legenda profili dostaje wiekszy margines gorny, aby nie nachodzila na wykres.
- W `Demografia / 👥 PROFIL DEMOGRAFICZNY` przesuniecie (`padding-left:25px`, `padding-top:15px`) stosujemy do calego boxa, nie do samej tabeli.
- Sekcja `Profile archetypowe 0-100` dostaje dodatkowy odstep od dolnej legendy TOP3 pod radarem.
Uzasadnienie:
- To bezposrednio domyka zgloszone regresje: nachodzenie legendy, nieczytelne markery JST i bledne przesuniecie tylko tabeli zamiast calej ramki.

### D-071: Braki map i ikon w standalone/online raportu traktujemy jako osobny pakiet generatora (H-015 Etap 3)
Decyzja:
- Problemy:
  - brak `Mapa przewag segmentów`,
  - brak `Mapa skupień (projekcja dla K=...)`,
  - brak ikonek w `Filtry`,
  sa prowadzone jako osobny etap naprawczy po stronie generatora/inline assets, niezalezny od UI Matching.
Uzasadnienie:
- To osobna klasa regresji (raport HTML + podglad online), powiazana z mapowaniem obrazow i osadzaniem assetow po inline.
- Rozdzielenie od Etapu 2 (Matching) zmniejsza ryzyko mieszania zmian i latwiejsza diagnostyke.

### D-072: Drobne poprawki legend/tabs po nowych screenach trafiaja do dogrywki A2 (po Kroku B)
Decyzja:
- Nowe uwagi UI z kolejnych screenow (hover aktywnej zakladki, korekta polozenia legend i stylu dolnej legendy TOP3 w radarze) sa dodane jako `Dogrywka A2` w `H-015 / Etap 2`.
- Kolejnosc zostaje utrzymana: najpierw `Krok B` (metryka `Poziom dopasowania`), potem `Dogrywka A2`.
Uzasadnienie:
- User poprosil o dopisanie do listy i przejscie do kolejnego etapu, wiec nie przerywamy aktualnego strumienia prac metrycznych.

### D-073: `Poziom dopasowania` dostaje jawna kare za luki na archetypach kluczowych
Decyzja:
- W `🧭 Matching` finalna metryka dopasowania uwzglednia osobny komponent kluczowy:
  - kluczowe archetypy = unia `TOP3 polityka` i `TOP3 mieszkańców`,
  - liczony `KEY_MAE` (srednia |Δ| dla tej puli) i `KEY_MAX` (najwieksza |Δ|),
  - wynik:
    - `base = 0.40*(100-MAE) + 0.20*(100-RMSE) + 0.20*(100-TOP3_MAE) + 0.20*(100-KEY_MAE)`,
    - `kara_kluczowa = 0.22*KEY_MAE + 0.10*max(0, KEY_MAX - 15)`,
    - `match = clamp(0,100, base - kara_kluczowa)`.
Uzasadnienie:
- User zglosil, ze poprzednia metryka zbyt lagodnie ocenia przypadki, w ktorych archetypy kluczowe sa jednoczesnie najwiekszymi lukami.

### D-074: Dogrywka A2 domyka czytelnosc tabs i legend radaru bez zmiany logiki danych
Decyzja:
- W `🧭 Matching` poprawki Dogrywki A2 obejmuja tylko warstwe prezentacji:
  - kontrast aktywnej zakladki na hover,
  - pozycjonowanie i estetyke legendy górnej,
  - dolna legende TOP3 (normalna waga tytułów, kwadraty dla `TOP3 mieszkańców`),
  - zwiekszenie dolnego marginesu wykresu, aby nie ucinać etykiet osi.
Uzasadnienie:
- User zglosil problemy wizualne i czytelnosci; nie bylo potrzeby ingerencji w obliczenia.

### D-075: Premia za zgodnosc kluczowych archetypow jest na razie posrednia; jawna premia trafia do backlogu
Decyzja:
- Obecna metryka nie ma osobnego dodatniego bonusu; efekt "premii" wynika posrednio z nizszych wartosci `KEY_MAE` i `KEY_MAX` (czyli mniejszej kary).
- Ewaluacja jawnej premii dodatniej zostaje zaplanowana jako osobny punkt (`Dogrywka A3`), z oceną ryzyka sztucznego zawyzania wyniku.
Uzasadnienie:
- User dopytal o premie; chcemy najpierw zweryfikowac wplyw merytoryczny, zanim dodamy nowy skladnik do wzoru.

### D-076: Dynamiczne mapy/ikony raportu musza byc inlinowane rowniez poza `src/href`
Decyzja:
- W `jst_analysis.py` rozszerzono `inline_local_assets(...)` o zamiane lokalnych sciezek assetow zapisanych jako quoted-stringi w JS/JSON.
- Dotyczy to dynamicznie podmienianych obrazow (np. `SEGMENTY_META_MAPA_STALA_K*.png`, `SKUPIENIA_MAPA_PCA_K*.png`, `icons/*.png`), ktore nie wystepuja jako statyczne `src/href` w HTML.
Uzasadnienie:
- Standalone/full HTML tracil interaktywnosc wizualna mimo poprawnego JS, bo dynamiczne zasoby nie byly osadzane i przestawaly byc osiagalne w `srcdoc`/jednoplikiowym HTML.

### D-077: Segmenty dostaja jawny payload map per-K zamiast skladania nazw po stronie JS
Decyzja:
- `analyze_poznan_archetypes.py` dopisuje do `seg_pack_ultra` i `seg_packs_render["ultra_premium"]` slowniki:
  - `map_arche_by_k`,
  - `map_values_by_k`.
- JS `setDynamicSegMap(...)` korzysta najpierw z tych map, a dopiero potem z fallbacku nazwy konwencyjnej.
Uzasadnienie:
- To eliminuje kruchosc zaleznosci od samego wzorca nazwy i domyka brak `Mapa przewag segmentów` przy standalone/online.

### D-078: Rezygnujemy z jawnej premii za dopasowanie
Decyzja:
- Nie dodajemy dodatniego bonusu do `Poziom dopasowania` za bliskosc archetypow kluczowych.
- Metryka pozostaje modelem kar (w tym kara za luki kluczowe), bez komponentu dodatniej premii.
Uzasadnienie:
- Jawna premia latwo podwojnie policzylaby ten sam efekt (nizsza kara + dodatkowy bonus), co sztucznie zawyzaloby ocene.
- User jednoznacznie zdecydowal o rezygnacji z premii.

### D-079: Kalibracja komunikatu `Poziom dopasowania` musi uwzgledniac skrajne luki kluczowe
Decyzja:
- W kolejnym kroku kalibrujemy progi/opisy pasm oceny tak, aby werdykt nie brzmial `bardzo wysokie` przy duzych lukach na archetypach kluczowych (np. >20 pp).
Uzasadnienie:
- Zgloszony przypadek (duze luki na TOP3 polityka/JST) pokazal, ze obecna narracja werbalna moze byc zbyt optymistyczna wzgledem merytorycznej interpretacji.

### D-080: `Główne zalety / Główne problemy` w Matching są wyliczane z tej samej logiki luk i TOP3
Decyzja:
- W `🧭 Matching / Podsumowanie` dodajemy blok interpretacyjny:
  - `Główne zalety`,
  - `Główne problemy`,
  budowany automatycznie z:
  - zgodnosci/różnicy priorytetu głównego,
  - przecięcia TOP3,
  - `KEY_MAE` i `KEY_MAX`,
  - najlepiej dopasowanej pozycji (`min |Δ|`).
- W opisie metryki jawnie utrzymujemy zasadę:
  - brak dodatniej premii za dopasowanie,
  - poprawa wyniku wynika wyłącznie z mniejszych luk (czyli mniejszej kary).
Uzasadnienie:
- User chciał bardziej praktycznej, natychmiastowej interpretacji stanu dopasowania bez przechodzenia przez same liczby.
- Jednoznaczne zapisanie "model kar, bez bonusu" ogranicza ryzyko błędnej interpretacji wskaźnika.

### D-081: Opis pasma dopasowania jest dodatkowo ograniczany przez luki kluczowe
Decyzja:
- Pasmo opisowe (`Niskie / Umiarkowane / Umiarkowanie wysokie / Bardzo wysokie`) nie zależy już wyłącznie od `match_score`.
- Dla dużych luk kluczowych (`KEY_MAX`, `KEY_MAE`) stosujemy ogranicznik pasma opisowego:
  - bardzo duże luki (`KEY_MAX >= 25` lub `KEY_MAE >= 18`) limitują opis do `Umiarkowane`,
  - wysokie luki (`KEY_MAX >= 20` lub `KEY_MAE >= 14`) limitują opis do `Umiarkowanie wysokie`.
- Wynik liczbowy pozostaje bez sztucznej premii dodatniej; korekta dotyczy warstwy interpretacji.
Uzasadnienie:
- User pokazał przypadek, gdzie duże rozjazdy na TOP3 dawały zbyt optymistyczny opis (`bardzo wysokie`).
- Ogranicznik pasma lepiej odzwierciedla ryzyko strategiczne bez zmiany filozofii modelu kar.

### D-082: Kara kluczowa w `Poziom dopasowania` zostaje zaostrzona
Decyzja:
- Wzór kary kluczowej zmieniono z:
  - `0.22*KEY_MAE + 0.10*max(0, KEY_MAX - 15)`
  na:
  - `0.30*KEY_MAE + 0.14*max(0, KEY_MAX - 12)`.
Uzasadnienie:
- User wskazał przypadek z dużymi lukami kluczowymi, gdzie wynik pozostawał zbyt wysoki.
- Zmiana zwiększa czułość na strategiczne rozjazdy (zwłaszcza przy wysokim `KEY_MAX`) bez dodawania premii dodatniej.

### D-083: Radar — priorytet geometrii legend nad szerokością
Decyzja:
- Górna legenda radaru została:
  - podniesiona wyżej (`y`),
  - zawężona (`entrywidth`),
  - optycznie „oddychająca” (mniejszy font + padding tekstu przez NBSP),
  aby była bliżej tytułu i dalej od wykresu.
- Dolna legenda TOP3 została podciągnięta bliżej wykresu.
Uzasadnienie:
- User zgłosił zbyt duży dystans tytuł→legenda i zbyt mały legenda→radar oraz zbyt „długą” górną legendę.

### D-084: Kolejne zaostrzenie kary kluczowej + mikro-tuning legendy radaru
Decyzja:
- Kara kluczowa została ponownie podniesiona do:
  - `0.45*KEY_MAE + 0.22*max(0, KEY_MAX - 9)`.
- W radarze:
  - górna legenda: nieco niżej, większa czcionka, mniejsza szerokość wpisu (`entrywidth`),
  - większy lewy oddech wpisów legendy przez dodatkowy padding tekstu,
  - dolna legenda TOP3 bliżej wykresu.
- Globalny `padding-top` strony ustawiono na `3px`.
Uzasadnienie:
- User potwierdził, że kara nadal była zbyt łagodna dla dużych luk kluczowych i poprosił o dalsze dociśnięcie.
- Dodatkowo wymagana była precyzyjna korekta geometrii legend i top spacingu.

### D-085: 7-stopniowa skala opisowa `Poziomu dopasowania`
Decyzja:
- Zamiast 4 poziomów wprowadzono finalnie 8 poziomów opisowych:
  - `0–29` marginalne dopasowanie,
  - `30–39` bardzo niskie dopasowanie,
  - `40–49` niskie dopasowanie,
  - `50–59` umiarkowane dopasowanie,
  - `60–69` znaczące dopasowanie,
  - `70–79` wysokie dopasowanie,
  - `80–89` bardzo wysokie dopasowanie,
  - `90–100` ekstremalnie wysokie dopasowanie.
- Guard dla kluczowych luk (`KEY_MAE`/`KEY_MAX`) pozostaje aktywny i może obniżyć opisowe pasmo.
Uzasadnienie:
- User poprosił o bardziej rozróżnione progi i opis jakościowy zbliżony do tabeli interpretacji natężenia archetypu.
- 8-stopniowa skala daje czytelniejszy „język jakościowy” przy zachowaniu tej samej logiki obliczeń.

### D-086: Guard kluczowych luk nie nadpisuje już pasma progowego
Decyzja:
- Etykieta pasma `Poziom dopasowania` jest wyznaczana bezpośrednio z progów 0–100 (0–29, 30–39, ..., 90–100).
- Duże luki kluczowe (`KEY_MAE`/`KEY_MAX`) pozostają raportowane jako ostrzeżenie jakościowe (`band_desc`), ale bez ręcznego zbijania etykiety do niższego progu.
Uzasadnienie:
- User zgłosił niespójność interpretacyjną (np. wynik >50 wpadał w opis `Niskie`), mimo że progi były już jawnie zdefiniowane.
- Rozdzielenie „progu liczbowego” od „ostrzeżenia jakościowego” zwiększa czytelność.

### D-087: Kara kluczowa została wygładzona, aby ograniczyć skokowość oceny
Decyzja:
- Wzór kary kluczowej zmieniono z:
  - `0.45*KEY_MAE + 0.22*max(0, KEY_MAX - 9)`
  na:
  - `0.42*KEY_MAE + 0.16*max(0, KEY_MAX - 12)`.
Uzasadnienie:
- User zgłosił zbyt duże rozjazdy wyniku końcowego dla par wizualnie zbliżonych profili.
- Zmiana utrzymuje karę za luki kluczowe, ale osłabia efekt „jednego ekstremum”.

### D-088: Panel personalny dostaje osobny moduł łączenia badań
Decyzja:
- W `Badania personalne - panel` dodano dwa kafelki:
  - `Ustawienia ankiety`,
  - `Połącz badania`.
- `Połącz badania` realizuje kopiowanie odpowiedzi z wielu badań źródłowych do jednego badania głównego:
  - źródła wybierane dynamicznie (`Dodaj badanie`),
  - finalizacja przyciskiem `Dodaj`,
  - odpowiedzi źródłowe pozostają w swoich badaniach (brak przenoszenia/usuwania).
- Warstwa DB: dodano `merge_personal_study_responses(...)` na tabeli `responses`.
Uzasadnienie:
- User potrzebował operacji konsolidacji wyników personalnych bez utraty oryginalnych danych w badaniach źródłowych.

### D-089: `Status badania` przeniesiony do modułu `Ustawienia ankiety`
Decyzja:
- Panel statusu (`Zawieś/Odwieś/Zamknij/Usuń`) nie jest już renderowany w widokach edycji danych.
- Statusy są obsługiwane centralnie w:
  - `Badania personalne -> ⚙️ Ustawienia ankiety`,
  - `Badania mieszkańców -> ⚙️ Ustawienia ankiety`.
Uzasadnienie:
- User wskazał, że status ma być częścią ustawień ankiety, a nie formularzy edycji danych.
- Rozdzielenie upraszcza UX: edycja danych i administracja statusem są w osobnych modułach.

### D-090: Kara kluczowa liczy TOP3 warunkowo jako TOP2 przy niskiej 3. pozycji
Decyzja:
- Dla puli kluczowej (`KEY_MAE`, `KEY_MAX`) stosujemy regułę:
  - domyślnie TOP3 polityka i TOP3 mieszkańców,
  - jeśli 3. pozycja profilu ma wynik `<70`, archetyp z 3. pozycji nie wchodzi do puli kluczowej (dla tego profilu liczymy TOP2).
Uzasadnienie:
- User doprecyzował, że archetyp poniżej 70% nie powinien być klasyfikowany jako poboczny/kluczowy.
- Reguła zmniejsza ryzyko przeszacowania kary kluczowej dla tego konkretnego przypadku.

### D-091: W sekcji radaru/legendy zmienne palet kolorów muszą być inicjalizowane przed helperami HTML
Decyzja:
- `person_top_colors` i `jst_top_colors` są deklarowane przed wywołaniami helperów, które budują legendę (`_role_legend_html`).
Uzasadnienie:
- W przeciwnym razie Python zgłasza `UnboundLocalError` w runtime (`matching_view`) i cały `Podsumowanie` w Matching przestaje się renderować.

### D-092: Marker map w radarze musi być budowany bez bezpośredniego indeksowania TOP listy
Decyzja:
- W helperze `_marker_series` mapowanie `archetyp -> kolor roli` budujemy inkrementalnie:
  - dodajemy `top3[0]` tylko gdy `len(top3) > 0`,
  - dodajemy `top3[1]` tylko gdy `len(top3) > 1`,
  - dodajemy `top3[2]` tylko gdy `len(top3) > 2`.
- Nie tworzymy słownika z kluczami `top3[0..2]` w jednej literałowej instrukcji.
Uzasadnienie:
- Python ocenia klucze słownika natychmiast; przy TOP2 dostęp do `top3[2]` powodował `IndexError` mimo warunku w wartości.
- Wariant inkrementalny jest odporny zarówno dla TOP2, jak i TOP3.

### D-093: Każde pasmo `Poziomu dopasowania` ma mieć unikalny kolor pastylki
Decyzja:
- W karcie `Poziom dopasowania` rozdzielamy kolory pasm tak, aby `Znaczące` i `Wysokie` nie używały tego samego koloru.
- Aktualna korekta:
  - `60–69` (`Znaczące`) -> niebieski (`#1d4ed8`),
  - `70–79` (`Wysokie`) -> fiolet (`#6d28d9`).
Uzasadnienie:
- User zgłosił, że oba poziomy były wizualnie nieodróżnialne.
- Unikalna kolorystyka pasm poprawia czytelność szybkiej interpretacji w `🧭 Matching`.

### D-094: Kara kluczowa ma uwzględniać nie tylko lukę, ale też strukturę priorytetów
Decyzja:
- Zaostrzono bazową karę kluczową:
  - z `0.42*KEY_MAE + 0.16*max(0, KEY_MAX - 12)`,
  - na `0.56*KEY_MAE + 0.26*max(0, KEY_MAX - 10)`.
- Dodano składniki strukturalne:
  - kara za brak wspólnych priorytetów TOP:
    - `5.5` gdy brak wspólnych pozycji,
    - `2.0` gdy wspólna jest tylko 1 pozycja,
  - kara `2.5` za różny priorytet główny (TOP1 polityka vs TOP1 mieszkańców).
- Finalnie:
  - `key_penalty = penalty_key_gap + penalty_shared_priority + penalty_main_priority_mismatch`.
Uzasadnienie:
- User pokazał przypadek z bardzo wysokimi lukami kluczowymi (`KEY_MAE` i `KEY_MAX`) i jednocześnie relatywnie łagodną oceną.
- Sama kara amplitudowa była za słaba, bo nie odzwierciedlała jakościowego konfliktu priorytetów (brak części wspólnej i inny TOP1).

### D-095: `Główne zalety / Główne problemy` mają odzwierciedlać przecięcia TOP priorytetów z lukami i dopasowaniami
Decyzja:
- W `🧭 Matching / Podsumowanie` sekcja interpretacyjna ma dodatkowo raportować:
  - priorytety (`TOP2/TOP3`) obecne w `Najlepsze dopasowania` jako zaletę,
  - priorytety (`TOP2/TOP3`) obecne w `Największe luki` jako problem.
- Pula priorytetowa do tego sprawdzenia to unia TOP polityka i TOP mieszkańców (dynamicznie TOP2/TOP3 wg obowiązującej reguły).
Uzasadnienie:
- User wskazał, że strategicznie kluczowe jest jawne zaznaczenie sytuacji, gdy „ważny” archetyp jest jednocześnie dużą luką albo mocną zgodnością.
- Bez tej reguły sekcja zalet/problemów była mniej diagnostyczna i mogła pomijać najważniejszy kontekst decyzyjny.

### D-096: Przecięcia TOP liczymy z tych samych list, które są renderowane jako chipy
Decyzja:
- Dla sekcji `Główne zalety / Główne problemy` przecięcia TOP są wyznaczane z:
  - `result["strengths"]` (widoczne chipy `Najlepsze dopasowania`),
  - `result["gaps"]` (widoczne chipy `Największe luki`),
  zamiast z osobnego lokalnego sortowania pomocniczego.
- Wpisy o przecięciach TOP mają priorytet widoczności (`insert(0, ...)`) przed innymi punktami.
Uzasadnienie:
- User zgłosił, że wpisy nie pojawiały się mimo widocznego przecięcia na ekranie.
- Źródło „jedno do jednego z chipami” + priorytet pozycji eliminuje rozjazd narracji i ryzyko ucięcia przez limit 4 punktów.

### D-097: Przecięcia TOP vs chipy porównujemy po nazwach znormalizowanych
Decyzja:
- Wykrywanie przecięć (`priority_in_best`, `priority_in_gaps`) działa przez klucze znormalizowane:
  - `slugify(name).lower()`.
- Surowe stringi pozostają tylko do renderu etykiet w UI.
Uzasadnienie:
- User dalej widział brak wpisu mimo widocznego przecięcia; najbardziej prawdopodobna przyczyna to rozjazd formatu nazw (spacje/znaki).
- Normalizacja zamyka tę klasę błędów bez wpływu na prezentację nazw.

### D-098: Dane z chipów nie mogą być filtrowane po exact-match surowej nazwy
Decyzja:
- Nazwy z `result["strengths"]` / `result["gaps"]` pobieramy bez warunku `name in diff_by_entity`.
- Dopiero etap porównania przecięć wykorzystuje normalizację (`slugify(...).lower()`).
Uzasadnienie:
- Filtr exact-match potrafił wyczyścić listę źródłową przy drobnym rozjeździe zapisu i blokował wpisy, które powinny trafić do `Główne problemy`.
- Rozdzielenie „pobrania źródła” od „logiki porównania” usuwa ten punkt awarii.

### D-099: Przecięcia TOP w Matching mają bazować na `strengths_rows/gaps_rows` (źródło 1:1 z UI chipów)
Decyzja:
- W sekcji `Główne zalety / Główne problemy` przecięcia TOP liczymy na `strengths_rows` i `gaps_rows`, czyli tym samym payloadzie, który renderuje chipy `Najlepsze dopasowania/Największe luki`.
- Dodatkowo:
  - parser nazw jest odporny na typ `dict|string`,
  - przy pustym wyniku parsera działa fallback do lokalnego rankingu,
  - w trybie `Wartości` nazwy są mapowane do archetypów przed porównaniem.
Uzasadnienie:
- User pokazał przypadki, gdzie chipy wskazywały przecięcie TOP↔luki, a sekcja problemów tego nie raportowała.
- Ujednolicenie źródła danych z warstwą renderu eliminuje ten rozjazd.

### D-100: `archetypy-ankieta` utrzymujemy w zgodności z TS `ES2020`
Decyzja:
- W kodzie ankiety nie używamy API wymagających wyższego targetu niż `ES2020` (np. `String.prototype.replaceAll`) bez polyfilla.
- Przy czyszczeniu warningów utrzymujemy zasadę: usuwamy nieużywane stany/props i błędne pola typów, które podnoszą błędy w `tsc`.
Uzasadnienie:
- `tsconfig.app.json` ma `target/lib` na `ES2020`, więc użycie nowszych API powoduje błędy kompilacji.
- Dzięki temu `npx tsc -p tsconfig.app.json --noEmit` pozostaje zielony i łatwiej wychwycić prawdziwe regresje.

### D-101: Przecięcia TOP w `Główne zalety/problemy` liczymy na źródle łączonym (chipy + ranking live)
Decyzja:
- Dla wykrywania przecięć TOP z `Najlepsze dopasowania/Największe luki` używamy źródła łączonego:
  - nazwy z renderowanych chipów (`strengths_rows`, `gaps_rows`),
  - oraz nazwy z lokalnego rankingu live (`strongest_fit_entities`, `largest_gap_entities`).
- Finalne porównanie pozostaje po normalizacji nazw (`slugify(...).lower()`).
Uzasadnienie:
- User zgłosił przypadki, gdzie przecięcie było widoczne na ekranie, ale nie trafiało do sekcji `Główne problemy`.
- Źródło łączone eliminuje zależność od pojedynczego formatu danych i domyka ten typ regresji.

### D-102: Legenda kół 0-100 ma być stałym elementem sekcji oraz sortowanie tabeli ma działać liczbowo
Decyzja:
- W `🧭 Matching -> Podsumowanie` wspólna legenda pod dwoma wykresami 0-100 (`Zmiana/Ludzie/Porządek/Niezależność`) jest renderowana stale, niezależnie od trybu `Archetypy/Wartości`.
- W tabeli porównawczej wartości kolumn liczbowych przechowujemy jako liczby (`float` zaokrąglone do 1 miejsca), nie jako string.
Uzasadnienie:
- User zgłosił brak legendy dla `Profile archetypowe 0-100`.
- Sortowanie po kolumnach przy stringach dawało nieintuicyjny porządek (sort tekstowy zamiast numerycznego).

### D-103: `Ustawienia ankiety` dostają stałą sekcję `Parametry ankiety` między wyborem badania a statusem
Decyzja:
- W obu modułach:
  - `Badania personalne -> ⚙️ Ustawienia ankiety`,
  - `Badania mieszkańców -> ⚙️ Ustawienia ankiety`,
  po selektorze badania renderujemy sekcję `Parametry ankiety`, a dopiero niżej `Status badania`.
- Etykieta `Wybierz badanie` jest wizualnie mocniejsza (`+1px`, pogrubienie).
Uzasadnienie:
- User jednoznacznie wskazał docelową kolejność i hierarchię informacji na ekranie ustawień.

### D-104: Harmonogram start/koniec działa jako jednorazowe przejścia statusu (bez trwałego zamykania)
Decyzja:
- Dodano pola:
  - `survey_auto_start_enabled`, `survey_auto_start_at`, `survey_auto_start_applied_at`,
  - `survey_auto_end_enabled`, `survey_auto_end_at`, `survey_auto_end_applied_at`.
- Logika:
  - przed godziną startu badanie ma być nieaktywne (`suspended`),
  - po wybiciu startu może wrócić do `active`,
  - po wybiciu końca przechodzi do `suspended`,
  - przejścia harmonogramowe są jednorazowe (znaczniki `*_applied_at`), więc ręczne `Odwieś` po auto-końcu nie jest natychmiast nadpisywane.
Uzasadnienie:
- Wymóg biznesowy: zakończone czasowo badanie ma przejść w `Zawieszone`, ale pozostać odwracalne (nie `closed`).

### D-105: Personalna ankieta wspiera dwa tryby renderu: `Macierz` i `Pojedyncze ekrany`
Decyzja:
- `survey_display_mode` steruje trybem:
  - `matrix`: dotychczasowy widok tabeli Likerta,
  - `single`: jedno pytanie na ekranie, przyciski odpowiedzi, `Dalej/Wyślij`.
- W trybie `single`:
  - bez odpowiedzi nie można przejść dalej,
  - po pytaniu 48 przycisk zmienia się na `Wyślij`,
  - zapis odpowiedzi pozostaje identyczny jak wcześniej.
Uzasadnienie:
- User wymaga alternatywnego, mobilnego sposobu wypełniania przy zachowaniu tej samej logiki danych.

### D-106: Randomizacja pytań jest obsługiwana po stronie prezentacji, nie kodowania
Decyzja:
- Dodano flagę `survey_randomize_questions`.
- Randomizujemy wyłącznie kolejność wyświetlania pytań (matrix: kolejność wierszy, single: kolejność ekranów).
- Wewnętrzne mapowanie odpowiedzi pozostaje po indeksach pytań źródłowych, a payload wysyłany jest w stałej kolejności.
Uzasadnienie:
- To spełnia potrzebę randomizacji i jednocześnie chroni poprawne kodowanie archetypów oraz porównywalność analityki.

### D-107: Forma `polityka/polityczki` jest zależna od płci badanej osoby
Decyzja:
- W zdaniu instrukcyjnym ankiety personalnej używamy:
  - `(polityka)` dla `gender = M`,
  - `(polityczki)` dla `gender = F`.
Uzasadnienie:
- User wskazał potrzebę precyzji językowej i zgodności formy z płcią.

### D-108: W `Matching` doprecyzowujemy kontekst Demografii i stabilizujemy łamanie `(|Δ| ... pp)`
Decyzja:
- W zakładce `Demografia` renderujemy jawny kontekst (`polityk` + `JST`) nad tabelami/kaflami.
- Fragment `(|Δ| ... pp)` w sekcjach `Główne zalety/problemy` budujemy z niełamliwymi odstępami.
Uzasadnienie:
- User zgłosił brak orientacji „czego dotyczy Demografia” oraz nieczytelne łamanie końcówek metrycznych na dwa wiersze.

### D-109: Blok `(|Δ| ... pp)` w `Główne zalety/problemy` jest zabezpieczony niełamliwym wrapperem HTML
Decyzja:
- W sekcji `Główne zalety/problemy` fragment `(|Δ| ... pp)` renderujemy jako:
  - `<span class="match-delta-nowrap">...</span>` z `white-space: nowrap`.
- Nie polegamy wyłącznie na `NBSP` w surowym stringu.
Uzasadnienie:
- Sam `NBSP` nie był wystarczający w praktyce (ciąg nadal łamał się na części przy zawijaniu tekstu).
- Wrapper CSS daje deterministyczny brak łamania dla całego tokenu różnicy.

### D-110: Kontekst Demografii ma formę lekkiego chipa zamiast markdown z backtickami
Decyzja:
- W `🧭 Matching -> Demografia` kontekst (`Polityk` + `JST`) renderujemy jako estetyczny chip:
  - subtelne tło,
  - obramowanie,
  - czytelna typografia.
Uzasadnienie:
- Poprzednia wersja (`**Kontekst:** ... \`...\``) była wizualnie ciężka i nieczytelna dla użytkownika.

### D-111: Po zapisie parametrów ankiety używamy feedbacku typu toast (z fallbackiem)
Decyzja:
- Po `💾 Zapisz parametry ankiety` w personal/JST:
  - zapisujemy komunikat flash w `st.session_state`,
  - po `st.rerun()` pokazujemy `st.toast("Zapisano parametry ankiety")`,
  - gdy `toast` nie jest dostępny, fallback do `st.success(...)`.
Uzasadnienie:
- Użytkownik oczekuje natychmiastowego, widocznego potwierdzenia zapisu (preferencyjnie prawy górny róg).
- Flash + rerun zachowuje świeży stan widoku i jednocześnie nie gubi komunikatu.

### D-112: Paleta skali odpowiedzi wraca do referencji wizualnej z ekranu 2899
Decyzja:
- Kolory 5 poziomów skali (`zdecydowanie nie` ... `zdecydowanie tak`) są przywrócone do referencyjnej, jaśniejszej palety i używane spójnie:
  - w nagłówkach macierzy,
  - oraz w przyciskach trybu `Pojedyncze ekrany`.
Uzasadnienie:
- User zgłosił regresję kolorów i wymagał przywrócenia wyglądu 1:1 względem wcześniejszego wzorca.

### D-113: Desktop `Pojedyncze ekrany` ma zawężony layout i lżejszą nawigację
Decyzja:
- Tryb `Pojedyncze ekrany` na desktopie:
  - renderujemy w zawężonym shellu (bez rozciągania na pełną szerokość),
  - odpowiedzi są podniesione wyżej (nie przyklejone do dołu strony),
  - usuwamy etykiety nad skalą (`Zdecydowanie się nie zgadzam ...`),
  - `Pamiętaj: ...` jest u góry, wyśrodkowane i szare,
  - zdanie `Czy zgadzasz się ... na temat ...` bez pogrubienia nazwiska,
  - `Wstecz` i `Dalej` mają lżejszy, mniej agresywny styl.
Uzasadnienie:
- User jednoznacznie wskazał słaby odbiór desktopowego single-screen i podał konkretne wymagania kompozycyjne.

### D-114: `Pojedyncze ekrany` — finalny tuning CTA/spacing pod mobile i desktop
Decyzja:
- W trybie `Pojedyncze ekrany`:
  - `Dalej` jest zielonym CTA (spójny z innymi akcjami),
  - `Wstecz` ma tę samą typografię co `Dalej` oraz hover highlight,
  - licznik postępu ma `font-size: 0.95rem`,
  - zwiększamy dystans między blokiem pytania i blokiem odpowiedzi.
- Na mobile:
  - `Dalej` jest przypięty w prawym dolnym rogu z bezpiecznym marginesem (`safe-area`),
  - sekcja treści ma dodatkowy dolny padding,
  - etykiety odpowiedzi używają mniejszego fontu i ciaśniejszej siatki, żeby mieściły się w równych kafelkach.
Uzasadnienie:
- User zgłosił konkretne regresje po pierwszej iteracji (zbyt mały oddech pionowy, słaba ekspozycja CTA, zbyt duże fonty/licznik, ścinanie etykiet odpowiedzi na telefonie).

### D-115: `Pojedyncze ekrany` — odpowiedzi mobile są kotwiczone, a landscape ma dedykowany tryb
Decyzja:
- W mobile portrait pasek odpowiedzi działa jako stała strefa (`position: fixed`) nad przyciskiem `Dalej`, aby nie zmieniał pozycji między pytaniami.
- W mobile landscape używamy osobnego zestawu stylów (`@media (orientation: landscape)`), z mniejszymi fontami i ciaśniejszym spacingiem.
- Interakcja odpowiedzi:
  - hover (desktop) podświetla kafelek kolorem opcji,
  - selected utrzymuje kolor opcji,
  - `Dalej` jest bez cienia.
Uzasadnienie:
- User zgłosił dwa krytyczne problemy UX:
  - „skaczący” pasek odpowiedzi na telefonie,
  - brak czytelnego dopasowania widoku w orientacji poziomej.
- Dodatkowo poprosił o czytelniejszy stan hover/selected oraz usunięcie cienia CTA.

### D-116: Mobile `Pojedyncze ekrany` — fixed zone odpowiedzi wymaga `width:auto` dla uniknięcia obcinania kafelków
Decyzja:
- W media-query mobile (portrait i landscape) dla `.single-scale-zone` ustawiamy:
  - `position: fixed`,
  - `left/right` + `width:auto`,
  - `box-sizing:border-box`.
Uzasadnienie:
- Samo `left/right` przy odziedziczonym `width:100%` powodowało praktyczne przepełnienie szerokości i obcinanie ostatniego kafelka po prawej stronie.

### D-117: `🧭 Matching` — stały format jednego miejsca po przecinku bez utraty sortowania
Decyzja:
- W tabeli porównawczej profili używamy `st.column_config.NumberColumn(format="%.1f")` dla kolumn liczbowych.
- Dane pozostają numeryczne (`float`) i sortowanie kolumn działa liczbowo.
Uzasadnienie:
- User oczekuje formatu `76.0` / `x.y` w każdym wierszu.
- Konwersja na tekst psułaby sortowanie numeryczne, więc formatujemy warstwę prezentacji, nie typ danych.

### D-118: Matrix mobile używa reaktywnej detekcji viewport/orientacji
Decyzja:
- W `Questionnaire.tsx` orientacja i tryb mobile dla macierzy są liczone z bieżącego stanu viewport (`width/height`),
  aktualizowanego na `resize`, `orientationchange` oraz `visualViewport.resize`.
Uzasadnienie:
- Poprzednia logika oparta o jednorazowy odczyt i sam `resize` mogła zostawiać błędny stan po obrocie telefonu,
  co dawało niestabilne zachowanie (w tym biały ekran po przejściu do poziomu).

### D-119: W matrix mobile ukrywamy logo w prawym górnym rogu
Decyzja:
- W nagłówku macierzy logo `Badania.pro` renderujemy tylko poza mobile viewport.
Uzasadnienie:
- Na telefonie logo nie jest wymagane funkcjonalnie i zabiera cenne miejsce w górnej części ekranu.

### D-120: W mobile landscape `Pojedyncze ekrany` mają rozdzielone role nawigacji
Decyzja:
- Licznik postępu (`x/48`) jest wyśrodkowany pod paskiem postępu.
- `Dalej` jest umieszczony w prawym górnym obszarze nawigacji.
Uzasadnienie:
- Taki układ poprawia czytelność i ogranicza kolizje z długą treścią pytania w poziomie.

### D-121: Desktop `Pojedyncze ekrany` ma stałą geometrię paska odpowiedzi
Decyzja:
- Na desktopie (`>900px`) pasek odpowiedzi i strefa akcji `Dalej` są kotwiczone (`position: fixed`) względem viewport.
Uzasadnienie:
- User zgłosił „wędrowanie” paska odpowiedzi między pytaniami; stała kotwica eliminuje wpływ różnej wysokości tekstu pytania.

### D-122: Matrix mobile dostaje fallback odświeżenia po obrocie
Decyzja:
- W trybie `matrix` na mobile po `orientationchange` do poziomu wykonujemy kontrolowany reload bieżącej strony ankiety (z guardem czasowym).
Uzasadnienie:
- Na części urządzeń/przeglądarek po obrocie pojawiał się biały ekran; twardy reload stabilizuje render bez zmiany ścieżki URL.

### D-123: Stan wejścia do ankiety personalnej utrzymujemy przez hash `#q`
Decyzja:
- Po starcie ankiety URL dostaje hash `#q`; przy reloadzie tej samej strony aplikacja startuje od razu w ankiecie (bez ekranu powitalnego).
Uzasadnienie:
- To umożliwia bezpieczny fallback reload (np. po obrocie) bez cofania użytkownika do intro i bez ingerencji w backend.

### D-124: Ukrycie paska adresu mobile realizujemy jako best effort
Decyzja:
- Po kliknięciu `Zaczynamy` próbujemy wejść w Fullscreen API (`requestFullscreen` + vendor fallback).
- Dodatkowo ustawiamy meta dla mobile app-capable/viewport-fit.
Uzasadnienie:
- Przeglądarki mobile różnią się polityką UI; pełne ukrycie paska adresu nie zawsze jest wymuszalne kodem aplikacji webowej.

### D-125: W `Questionnaire` nie używamy hooków po warunkowym `return` ekranu orientacji
Decyzja:
- `singleProgress` liczymy bez `useMemo` (jako zwykłą wartość), aby nie mieć hooka za gałęzią warunkowego `return`.
Uzasadnienie:
- To eliminuje klasę błędów React z nierówną liczbą hooków między renderami (w praktyce `#310` przy przejściu portrait/landscape w macierzy).

### D-126: Fallback `orientationchange -> reload` został wycofany
Decyzja:
- Usunięto automatyczny reload strony z `Questionnaire` wykonywany przy obrocie.
Uzasadnienie:
- Rozwiązanie było zbyt inwazyjne i razem z układem hooków doprowadziło do regresji runtime na urządzeniach użytkownika.

### D-127: Desktop single-screen ma stabilny pasek odpowiedzi, ale nie przy dolnej krawędzi
Decyzja:
- W desktopie pozycja stała zostaje, ale z podniesioną geometrią (`bottom` przez `clamp`) zgodną z referencją 2944.
Uzasadnienie:
- User wymagał stałej pozycji paska odpowiedzi na konkretnej wysokości, nie „przyklejonej” do dołu.

### D-128: Typografia pytań używa automatycznego „klejenia” krótkich słów (NBSP)
Decyzja:
- W renderze pytań/leadów ankiety personalnej stosujemy helper, który zamienia spacje po krótkich słowach na twarde spacje.
Uzasadnienie:
- Eliminuje „sieroty” typograficzne (np. `i`, `z`, `na`, `by`) na końcach linii na desktopie i mobile.

### D-129: Matrix mobile po ukryciu logo ma pełną szerokość tekstu nagłówka
Decyzja:
- Lewy kontener nagłówka macierzy ma `flex:1` i `minWidth:0`, aby zajmował całą dostępną szerokość, gdy logo jest schowane.
Uzasadnienie:
- Zapobiega pozostawianiu pustej strefy po prawej stronie i poprawia kompozycję nagłówków na telefonie.

### D-130: Mobile landscape `Dalej` kotwimy nieco niżej (`top +58px`)
Decyzja:
- W landscape mobile `Dalej` jest pozycjonowane niżej niż w poprzedniej iteracji, ale nadal na wysokości nawigacji pod paskiem postępu.
Uzasadnienie:
- User zgłosił, że przycisk był zbyt wysoko i wizualnie odklejał się od linii `Wstecz`.

### D-131: Matrix mobile orientację wyznaczamy logiką wieloźródłową z priorytetem wymiarów viewport
Decyzja:
- W `Questionnaire.tsx` orientacja dla macierzy jest liczona w kolejności:
  1) relacja `viewport.width/viewport.height`,
  2) `screen.orientation.type`,
  3) `matchMedia("(orientation: portrait)")`.
- Stan `viewport` jest odczytywany helperem `readViewport()` z priorytetem `visualViewport`.
Uzasadnienie:
- Część przeglądarek mobile raportuje orientację niespójnie podczas sekwencji obrotów.
- Priorytet realnych wymiarów viewport zmniejsza ryzyko „fałszywego” ekranu `obróć telefon poziomo` w poziomie.

### D-132: Typograficzne klejenie fraz ma obejmować pełne sekwencje białych znaków
Decyzja:
- W helperze `withHardSpaces` zamiana dla fraz (`gdzie inni`, `nawet jeśli`) używa globalnej podmiany `\s+` na NBSP.
Uzasadnienie:
- Chroni przed rozbiciem fraz także wtedy, gdy w źródle pojawią się niestandardowe odstępy (np. wielokrotne spacje).

### D-133: Mobile single-screen — priorytet to ergonomia górnej nawigacji i wyżej osadzona skala
Decyzja:
- Mobile portrait:
  - pasek odpowiedzi podnosimy wyżej (`bottom +174px`) i zwiększamy bufor dolny treści.
- Mobile landscape:
  - `Dalej` pozycjonujemy wyżej (`top +44px`) tak, aby pozostawał pod paskiem postępu i na linii nawigacji.
Uzasadnienie:
- User konsekwentnie zgłaszał zbyt niskie osadzenie skali oraz `Dalej` poza oczekiwaną strefą nawigacji.

### D-134: Ekran orientacji macierzy nie może warunkowo omijać późniejszych hooków
Decyzja:
- `showOrientationWarning` liczymy jako flagę i renderujemy dopiero po wywołaniu wszystkich hooków komponentu.
- Nie stosujemy wczesnego `return` przed dalszymi hookami zależnie od orientacji.
Uzasadnienie:
- Sekwencja obrotów mobile prowadziła do zmiany liczby hooków między renderami i błędów React `#300/#310`.

### D-135: Desktopowe skróty klawiaturowe w single-screen
Decyzja:
- W trybie single-screen:
  - `Enter` uruchamia `Dalej/Wyślij` (po wybraniu odpowiedzi),
  - `ArrowLeft` uruchamia `Wstecz` (jeśli nawigacja wstecz jest włączona i to nie pierwsze pytanie).
Uzasadnienie:
- Użytkownik oczekuje szybszej obsługi ankiety na desktopie bez klikania myszą.

### D-136: Mobile landscape wymaga osobnego balansu: większa czytelność leadów i niższy „offset napięcia”
Decyzja:
- W landscape mobile:
  - zwiększamy fonty `Pamiętaj...` i `Czy zgadzasz...`,
  - zwiększamy lekko górny prześwit sekcji pytania,
  - `Dalej` przesuwamy bliżej linii nawigacji (`top +34px`).
Uzasadnienie:
- User zgłosił, że teksty były za małe i zbyt „przyklejone” do górnej strefy, a `Dalej` nadal bywał zbyt nisko.

### D-137: Mobile portrait ma osobny balans startu treści niż mobile landscape
Decyzja:
- W portrait zmniejszamy górny margines sekcji pytań (treści zaczynają się wcześniej), a jednocześnie podnosimy czytelność dwóch linii pomocniczych przez większy font.
Uzasadnienie:
- User wskazał, że w pionie treści są zbyt późno i jednocześnie słabo widoczne.

### D-138: `ArrowRight` w single-screen działa jako „Dalej” pod warunkiem zaznaczonej odpowiedzi
Decyzja:
- Rozszerzamy skróty klawiaturowe:
  - `ArrowLeft` = `Wstecz` (gdy dostępny),
  - `ArrowRight` = `Dalej/Wyślij` (tylko dla wypełnionego bieżącego ekranu).
Uzasadnienie:
- User potrzebuje szybkiego „odwijania” i „przewijania do przodu” po pytaniach bez klikania myszą.

### D-139: W mobile landscape przycisk `Dalej` ma priorytet pionowego wyrównania do linii nawigacji
Decyzja:
- `Dalej` kotwimy wyżej (`top +22px`), aby był optycznie na tej samej linii co obszar nawigacji pod paskiem postępu.
Uzasadnienie:
- User nadal raportował, że `Dalej` jest „za nisko”, mimo wcześniejszych korekt.

### D-140: Mobile landscape dostaje dodatkowy margines po `Czy zgadzasz...`
Decyzja:
- W `SingleQuestionnaire.css` dla landscape zwiększamy odstęp między leadem a pytaniem głównym:
  - przez `single-lead { margin-bottom: ... }`,
  - oraz większy `single-question-text { margin-top: ... }`.
Uzasadnienie:
- User poprosił o wyraźnie większy „oddech” po tekście `Czy zgadzasz...`.

### D-141: W landscape zwiększamy czytelność tekstów pomocniczych i pytania głównego
Decyzja:
- W obu wariantach landscape (`max-width:900` i `max-height:560`) podbijamy:
  - `single-sublead` i `single-lead` o ok. 1px,
  - `single-question-text` o ok. 2px.
Uzasadnienie:
- User wskazał, że górne teksty były zbyt małe i „ginęły” na ekranie poziomym.

### D-142: Auto-odmiana JST dla nazw kończących się na `-o` ma osobną regułę
Decyzja:
- W `app.py` (`_guess_word_cases`) nazwy miejscowe nijakie kończące się na `-o` odmieniamy przez:
  - `gen = base + "a"`,
  - `dat = base + "u"`,
  - `acc = nom`,
  - `ins = base + "em"`,
  - `loc = base + "ie"`,
  - `voc = nom`.
- Reguła jest wykonywana przed fallbackiem dla zakończeń spółgłoskowych.
Uzasadnienie:
- Bez tej reguły nazwy typu `Testowo` wpadały w fallback i dostawały błędne formy (`Testowoa`, `Testowoowi`).
- Poprawka domyka krytyczny błąd UX w formularzu `➕ Dodaj badanie mieszkańców` przy `Uzupełnij odmiany automatycznie`.

### D-143: Klejenie fraz NBSP rozszerzamy o pełne sekwencje „nawet jeśli ...”
Decyzja:
- W `Questionnaire.tsx` (`PHRASE_GLUE_PATTERNS`) dodajemy wzorce:
  - `nawet jeśli jest`,
  - `nawet jeśli koszt`.
Uzasadnienie:
- User wskazał konkretne pytania, gdzie samo klejenie `nawet jeśli` było niewystarczające i trzeci wyraz spadał do nowej linii.

### D-144: Auto-odmiana JST wspiera słownik wyjątków (word + phrase overrides)
Decyzja:
- W `app.py` wprowadzamy dwa słowniki override:
  - `JST_WORD_CASE_OVERRIDES` dla pojedynczych nazw nieregularnych,
  - `JST_PHRASE_CASE_OVERRIDES` dla pełnych nazw wielowyrazowych.
- Kolejność logiki:
  1) override,
  2) heurystyka końcówek.
Uzasadnienie:
- Sama heurystyka końcówek nie pokrywa poprawnie wszystkich nazw JST (zwłaszcza nieregularnych i wielowyrazowych).
- Słownik wyjątków podnosi jakość domyślnej auto-odmiany i pozostaje łatwy do dalszego rozszerzania.

### D-145: JST mobile — wymuszenie obrotu zostaje chwilowo wyłączone flagą
Decyzja:
- W `JstSurvey.tsx` dodajemy flagę `ENFORCE_JST_LANDSCAPE_ON_MOBILE` i ustawiamy ją tymczasowo na `false`.
- Logika ekranu `Proszę obrócić telefon poziomo...` pozostaje w kodzie, ale jest nieaktywna do czasu ponownego włączenia flagi.
Uzasadnienie:
- User poprosił o szybki UAT wyglądu ankiety JST bez blokady orientacji.
- Flaga umożliwia bezpieczny powrót do poprzedniego zachowania bez refaktoru komponentu.

### D-146: JST dark mode — tor suwaka musi być wysokokontrastowy
Decyzja:
- W `JstSurvey.css` dark mode tor suwaka (`::-webkit-slider-runnable-track`, `::-moz-range-track`) dostał jaśniejszy gradient i dodatkowy obrys.
- Ticki osi (`.jst-tick`) są renderowane jaśniejszym kolorem.
Uzasadnienie:
- W aktualnym ciemnym motywie oś suwaka była praktycznie niewidoczna na części ekranów.
- Wysoki kontrast osi poprawia czytelność i precyzję odpowiedzi w pytaniach suwakowych.

### D-147: Publiczny raport archetypowy pokazuje licznik uczestników
Decyzja:
- W `public_report_view` (token/email) renderujemy na górze raportu kafelek z liczbą uczestników badania.
- Licznik pobieramy przez `fetch_personal_response_count(...)`.
- Kafelek jest responsywny i ma wariant dark mode.
Uzasadnienie:
- W publicznym widoku brakowało kluczowego kontekstu skali badania, który jest obecny w panelu administracyjnym.
- Dodanie licznika zwiększa czytelność raportu dla odbiorców zewnętrznych.

### D-148: Licznik uczestników w publicznym raporcie jest częścią wiersza nagłówka sekcji
Decyzja:
- W publicznym `show_report(..., public_view=True)` licznik uczestników renderujemy w tej samej linii co nagłówek `Informacje na temat archetypów ...`:
  - tytuł po lewej,
  - licznik po prawej.
- Wycofujemy wcześniejsze globalne wstrzyknięcie kafelka nad raportem.
Uzasadnienie:
- Użytkownik zgłosił, że osobny kafelek „ucieka” wizualnie i zaburza kompozycję.
- Wspólny wiersz z nagłówkiem daje czytelniejszy, bardziej naturalny układ.

### D-149: W JST dark mode suwak ma priorytet kontrastu osi nad subtelną estetyką
Decyzja:
- Tor suwaka w dark mode otrzymuje jaśniejsze tło, obrys i mocniejszy kontrast.
- Ticki osi są grubsze i jaśniejsze.
Uzasadnienie:
- W praktyce użytkowej oś była nadal zbyt słabo widoczna, co utrudniało ocenę pozycji suwaka.

### D-150: Etykiety po stronie B pod suwakiem są zawsze wyrównane do prawej
Decyzja:
- W `.jst-slider-head` oba pola etykiet mają równy udział szerokości, a prawa etykieta (`span:last-child`) ma `text-align:right`.
Uzasadnienie:
- Wyrównanie do prawej stabilizuje kompozycję i poprawia czytelność par A/B, szczególnie przy dłuższych opisach.

### D-151: Streamlit widgety z `key` nie dostają równolegle `value`, gdy stan idzie przez `st.session_state`
Decyzja:
- W `send_link.py` dla pola `email_subject` usuwamy parametr `value=...` i zostawiamy wyłącznie `key="email_subject"` oraz kontrolę przez `st.session_state`.
Uzasadnienie:
- Równoległe ustawianie `value` i tego samego klucza sesji wywołuje warning Streamlit i może powodować niespójności inicjalizacji pola.

### D-152: Widoczność toru suwaka JST nie może zależeć tylko od pseudo-elementów `range` przeglądarki
Decyzja:
- W `JstSurvey.css` dodajemy własną warstwę toru (`.jst-range-wrap::before`) jako stałe tło osi suwaka.
- Styl pseudo-elementów `::-webkit-slider-runnable-track` / `::-moz-range-track` pozostaje dodatkowym wzmocnieniem, ale nie jedynym nośnikiem widoczności.
Uzasadnienie:
- Na części mobile browserów (szczególnie w dark mode) natywne pseudo-elementy `range` renderują się zbyt słabo lub niespójnie.
- Osobna warstwa toru daje przewidywalny, czytelny efekt.

### D-153: W JST dark mode priorytetem jest subtelność — unikamy „ciężkiej” warstwy toru
Decyzja:
- Wycofujemy dodatkową warstwę `.jst-range-wrap::before`, jeśli daje zbyt agresywny efekt wizualny.
- Tor suwaka dopieszczamy minimalnie: lekko jaśniejsze tło + cienkie obramowanie bez mocnych efektów.
Uzasadnienie:
- User wskazał, że poprzednia poprawka poprawiała kontrast kosztem estetyki.
- Docelowo tor ma być czytelny, ale nadal lekki i zgodny z resztą UI.

### D-154: Iteracyjnie rozjaśniamy tor suwaka JST w dark mode bez zmiany geometrii
Decyzja:
- Gdy tor nadal jest odbierany jako zbyt ciemny, podnosimy jasność wyłącznie przez kolory:
  - jaśniejszy `background`,
  - minimalnie jaśniejszy `border`,
  - subtelnie mocniejszy `inset`.
- Nie zmieniamy wysokości/układu suwaka.
Uzasadnienie:
- Pozwala poprawić czytelność na konkretnym ekranie użytkownika bez ponownego psucia estetyki całego komponentu.

### D-155: Dla JST dark mode stosujemy fallback toru na samym `.jst-range`
Decyzja:
- Oprócz stylu `::-webkit-slider-runnable-track` i `::-moz-range-track`, ustawiamy jasny kolor toru bezpośrednio na `.jst-range`.
Uzasadnienie:
- Część przeglądarek mobilnych renderuje pseudo-elementy `range` niekonsekwentnie.
- Fallback na bazowym elemencie gwarantuje, że oś suwaka nie „zniknie” nawet przy ograniczonym wsparciu silnika renderującego.

### D-156: Usuwanie odpowiedzi JST realizujemy przez zaznaczenie wierszy w tabeli eksportu
Decyzja:
- W `💾 Import i eksport baz danych` (JST) usuwanie rekordów odbywa się bezpośrednio w tabeli odpowiedzi:
  - checkbox `Usuń` przy wierszach,
  - akcja zbiorcza `🗑️ Usuń zaznaczone`,
  - obowiązkowe potwierdzenie operacji.
- Kasowanie backendowe wykonujemy po `respondent_id` w obrębie `study_id` (batch/chunk).
Uzasadnienie:
- User potrzebuje kasować pojedyncze i wiele wypełnień bez ręcznej edycji bazy.
- `respondent_id` jest stabilnym identyfikatorem w zakresie badania (`UNIQUE (study_id, respondent_id)`), więc nadaje się do bezpiecznego bulk-delete.

### D-157: Cache kart archetypów musi uwzględniać zmianę pliku na dysku
Decyzja:
- W `admin_dashboard.py` data URI kart archetypów (`assets/card/*.png`) cache’ujemy z tokenem opartym o metadane pliku (`mtime_ns`, `size`).
- Dobór pliku `_card_file_for(...)` ma priorytet dokładnego dopasowania nazwy; fallback prefiksowy działa tylko awaryjnie i deterministycznie.
Uzasadnienie:
- Użytkownik widział starą kartę mimo podmiany pliku na serwerze.
- Sam cache po nazwie archetypu/ścieżce nie odświeżał się po zmianie zawartości pliku o tej samej nazwie.
- Priorytet exact-match eliminuje ryzyko przypadkowego wyboru nieaktualnego wariantu pliku.

### D-158: Tie-break rankingu archetypów w tabeli podsumowania
Decyzja:
- W `Podsumowanie archetypów (liczebność i natężenie)` kolejność wierszy ustalamy przez klucz:
  `(-%_1dp, -główny, -wspierający, -poboczny, alfabetycznie)`.
- `%` do porównania liczymy po zaokrągleniu do jednego miejsca po przecinku (spójnie z tym, co widzi użytkownik).
Uzasadnienie:
- User wymaga jawnej reguły rozstrzygania remisów.
- Wtórne sortowanie po samym `%` mogło zaburzać kolejność przy remisach, więc ranking musi być nadawany jednokrotnie pełnym kluczem.

### D-159: Welcome screen ankiety personalnej ma jawnie zdefiniowany ciemny kolor tekstu
Decyzja:
- W `archetypy-ankieta/src/App.tsx` ustawiamy jawny kolor tekstu na kontenerze ekranu powitalnego (`#1f2937`) oraz na bloku treści (`#213547`).
Uzasadnienie:
- Na iPhone (dark mode) tekst powitalny dziedziczył jasny kolor z globalnego motywu i stawał się słabo czytelny na białym tle.
- Jawne kolory w tym widoku eliminują zależność od automatyki kolorystycznej przeglądarki.

### D-160: Mobile portrait `Pojedyncze ekrany` — strefa odpowiedzi działa w normalnym flow, nie jako fixed overlay
Decyzja:
- W mobile portrait dla `SingleQuestionnaire` wycofujemy `position: fixed` dla:
  - paska odpowiedzi (`.single-scale-zone`),
  - akcji `Dalej` (`.single-footer-actions`).
- Odpowiedzi i CTA renderują się pod pytaniem z kontrolowanym odstępem.
Uzasadnienie:
- Na iPhone 15 Pro fixed overlay nachodził na długie treści pytań.
- W tym wariancie ergonomia i brak kolizji treści mają priorytet nad stałym „przyklejeniem” paska odpowiedzi.

### D-161: Transliteracja SMS JST dotyczy realnie wysyłanego payloadu, nie tylko podglądu
Decyzja:
- W `send_link_jst.py` każda wysyłka SMS (nowa i ponowna) przekazuje do `send_sms(...)` treść po `_strip_pl_diacritics(...)`.
- Przy tworzeniu rekordu SMS zapisujemy tę samą transliterowaną wersję.
Uzasadnienie:
- Sam podgląd transliterowany bez transliteracji payloadu prowadził do „krzaków” u odbiorcy.
- Spójność `podgląd = zapis = realna wysyłka` usuwa klasę tych błędów.

### D-177: Single-screen mobile — neutralna etykieta odpowiedzi ma wymuszone dwie linie
Decyzja:
- W renderze single-screen etykietę `ani tak, ani nie` rozbijamy jawnie na dwie linie (`ani tak,` + `<br />` + `ani nie`).
- CSS przycisku utrzymuje poprawne zawijanie także dla pozostałych etykiet.
Uzasadnienie:
- User wymagał dokładnego, stałego podziału tej etykiety na dwie linie w mobile.

### D-178: iPhone portrait — priorytetem jest brak obcięć tekstu pytania i etykiet
Decyzja:
- W `SingleQuestionnaire.css` dla mobile stosujemy bezpieczne łamanie:
  - `word-break: break-word`,
  - `overflow-wrap: anywhere`,
  - dodatkowo `hyphens: auto` dla pytania głównego.
- Dla bardzo wąskich ekranów (`max-width:430px`) zmniejszamy font i padding etykiet odpowiedzi.
- Dodatkowo uszczelniamy layout iOS:
  - `overflow-x: hidden` na root kontenera ankiety,
  - `min-width: 0` na kafelkach odpowiedzi,
  - pełna szerokość + `box-sizing` + wewnętrzny padding bloku pytania.
Uzasadnienie:
- Na iPhone 15 Pro user raportował:
  - ucięcie końcówki pytania po prawej stronie,
  - wychodzenie słowa `zdecydowanie` poza kafelki.
- Ta decyzja celuje dokładnie w ten case i nie dotyka logiki ankiety.

### D-162: Powiadomienia e-mail po nowych odpowiedziach opieramy na liczniku odpowiedzi + baseline per badanie
Decyzja:
- Dodajemy konfigurację powiadomień do `studies` i `jst_studies`:
  - `survey_notify_on_response`,
  - `survey_notify_email`,
  - `survey_notify_last_count`,
  - `survey_notify_last_sent_at`.
- W `⚙️ Ustawienia ankiety` (personalne i JST) aktywacja checkboxa odblokowuje pole e-mail.
- Po włączeniu powiadomień (lub zmianie adresu) zapisujemy baseline `survey_notify_last_count` równy bieżącej liczbie odpowiedzi, żeby nie wysyłać alertów historycznych.
- Dispatcher w `app.py` monitoruje wzrost licznika odpowiedzi i po wzroście wysyła e-mail z:
  - tytułem badania,
  - linkiem do ankiety,
  - łączną liczbą wypełnionych ankiet.
Uzasadnienie:
- Ankiety publiczne zapisują odpowiedzi bezpośrednio przez RPC do bazy, więc najbezpieczniej było dołożyć mechanizm monitorowania po stronie panelu administracyjnego bez ingerencji w frontendowe flow zapisu.
- Baseline eliminuje ryzyko masowej wysyłki „wstecznej” przy pierwszym uruchomieniu opcji.

### D-163: Dispatcher notyfikacji działa jako pętla w tle procesu panelu
Decyzja:
- Notyfikacje po nowych odpowiedziach uruchamiamy w osobnym wątku tła (`survey-notify-dispatcher`), startowanym jednokrotnie przez `@st.cache_resource`.
- Fallback ręcznego dispatchera zostaje tylko gdy background jest wyłączony przez sekret.
Uzasadnienie:
- Sam dispatch uruchamiany wyłącznie przy interakcji UI (rerun Streamlit) powodował opóźnienie: mail pojawiał się dopiero po odświeżeniu panelu / ponownym logowaniu.
- Wątek cykliczny eliminuje ten efekt i umożliwia wysyłkę bez ręcznego triggera w UI.

### D-164: Treść i tytuł notyfikacji muszą używać jawnych form domenowych
Decyzja:
- Personalne: w copy notyfikacji używamy formy `archetypu {imię i nazwisko w dopełniaczu} ({miasto})`.
- JST: w copy notyfikacji używamy formy `mieszkańców {nazwa JST w dopełniaczu}`.
Uzasadnienie:
- User zgłosił nienaturalne i merytorycznie niespójne copy (`Miłosław Mirosław`, `Gmina Masoneria` bez kontekstu badania mieszkańców).
- Poprawa domyka spójność językową i kontekst raportowy.

### D-165: Ankieta JST dostaje desktopowe skróty klawiaturowe analogiczne do ankiety personalnej
Decyzja:
- W `JstSurvey.tsx`:
  - `Enter` i `ArrowRight` wykonują akcję `dalej`/`wyślij` z pełną walidacją bieżącego kroku,
  - `ArrowLeft` wykonuje `Wstecz` tylko gdy `allowBack`,
  - skróty są wyłączone przy focusie w `input/textarea/select`.
Uzasadnienie:
- User oczekuje spójnej ergonomii klawiatury między `archetypy.badania.pro` i `jst.badania.pro`.
- Blokada skrótów w polach edycyjnych zapobiega przypadkowym przejściom podczas wpisywania tekstu.

### D-166: Metryczka JST przechowuje konfigurację per badanie jako wersjonowany JSON
Decyzja:
- W `jst_studies` dodajemy:
  - `metryczka_config (JSONB)`,
  - `metryczka_config_version (INTEGER)`.
- Model jest normalizowany przy zapisie i odczycie.
Uzasadnienie:
- Pozwala utrzymać niezależną konfigurację metryczki dla każdego badania JST bez łamania historycznych danych.
- Wersjonowanie otwiera ścieżkę do przyszłych migracji parserów/importu.

### D-167: Rdzeń metryczki (5 zmiennych) jest niezmienny identyfikatorowo, edytowalne są treści i opcje
Decyzja:
- Pola rdzeniowe pozostają stałe:
  - `M_PLEC`, `M_WIEK`, `M_WYKSZT`, `M_ZAWOD`, `M_MATERIAL`.
- Dodatkowe pytania działają jako `scope=custom` i muszą mieć unikalny `db_column`.
Uzasadnienie:
- Raporty i ważenie poststratyfikacyjne opierają się na stabilnych identyfikatorach rdzenia; ich zmienność rozwaliłaby kompatybilność analityczną.
- Jednocześnie model musi pozwalać rozszerzać metryczkę o nowe zmienne demograficzne.

### D-168: Metryczka ma być osobnym modułem panelu (osobny kafelek), nie częścią `⚙️ Ustawienia ankiety`
Decyzja:
- W panelach `Badania personalne` i `Badania mieszkańców` dodajemy osobny kafelek `🧾 Metryczka`.
- Edycja metryczki działa w dedykowanych widokach:
  - `personal_metryczka_view`,
  - `jst_metryczka_view`.
Uzasadnienie:
- User wskazał, że metryczka w ustawieniach ankiety jest mniej czytelna.
- Oddzielenie metryczki od ustawień technicznych (nawigacja, harmonogram, powiadomienia) porządkuje UX.

### D-169: Ankiety personalne korzystają z tego samego modelu metryczki co JST
Decyzja:
- Tabela `studies` dostaje:
  - `metryczka_config (JSONB)`,
  - `metryczka_config_version (INTEGER)`.
- Konfiguracja metryczki personalnej jest normalizowana tak samo jak JST (wspólny rdzeń 5 pytań + custom).
Uzasadnienie:
- User wymaga, aby metryczka była dostępna również dla `archetypy.badania.pro`.
- Wspólny model minimalizuje ryzyko rozjazdu logiki między modułami i upraszcza dalsze wdrożenie raportowania demograficznego.

### D-170: Wklejanie treści do metryczki realizujemy przez panel „Wklej pytanie i odpowiedzi” z podglądem parsowania
Decyzja:
- W edytorze metryczki każde pytanie ma opcję `📋 Wklej pytanie i odpowiedzi`.
- UX panelu:
  - lewe pole: surowy tekst do wklejenia,
  - prawa strona: podgląd, jak parser rozumie `Treść pytania` i listę `Odpowiedzi`,
  - akcja `Wstaw` zapisuje wynik do edytowanego pytania.
- Przy `Wstaw` kodowanie odpowiedzi ustawiamy automatycznie sekwencją `1..N`.
Uzasadnienie:
- User pokazał referencyjny workflow na nagraniu i oczekiwał analogicznego, szybkiego sposobu masowego wprowadzania odpowiedzi.
- Podgląd przed zatwierdzeniem ogranicza ryzyko błędnego parsowania przy wklejkach z Word/Excel.

### D-171: Dla 5 stałych pól metryczki kodowanie odpowiedzi musi być zgodne z historycznym zapisem bazowym (`code = tekst odpowiedzi`)
Decyzja:
- W rdzeniu metryczki (`M_PLEC`, `M_WIEK`, `M_WYKSZT`, `M_ZAWOD`, `M_MATERIAL`) kodowanie odpowiedzi utrzymujemy jako wartość tekstową odpowiedzi (np. `mężczyzna`, `60 i więcej`), a nie `1..N`.
- Przy masowym wklejeniu (`Wklej pytanie i odpowiedzi`) ta sama zasada obowiązuje dla pytań rdzeniowych.
- Dla pytań dodatkowych (`scope=custom`) przy wklejeniu pozostaje auto-kodowanie `1..N`.
Uzasadnienie:
- User wskazał, że dotychczasowe bazy zapisują rdzeń metryczki tekstowo; zmiana na kody liczbowe groziłaby rozjazdem importu/raportów i kompatybilności historycznej.

### D-172: Pole `Pytanie` w edytorze metryczki ma startować z wysokości 1–2 linii
Decyzja:
- W CSS panelu admina pole `Pytanie` w metryczce targetujemy selektorem `textarea[aria-label=\"Pytanie\"]` i ustawiamy niski start (`height/min-height` ~38px) przy zachowaniu `resize: vertical`.
Uzasadnienie:
- User zgłosił, że pole jest zbyt wysokie i utrudnia szybkie przeglądanie wielu pytań.
- Selektor po `id` nie był wystarczająco niezawodny dla renderu Streamlit, więc potrzebny był bardziej stabilny target.

### D-173: Widget `paste_text_*` w metryczce czyścimy tylko przed renderem, nigdy po instancji
Decyzja:
- W `_render_metryczka_editor` pole tekstowe panelu `📋 Wklej pytanie i odpowiedzi` czyścimy przez flagę `paste_clear_*`.
- Faktyczne czyszczenie wykonujemy przed renderem widgetu (`st.session_state.pop(paste_text_key, None)`), a nie przez bezpośredni zapis do `st.session_state[paste_text_key]` po utworzeniu textarea.
- Dodatkowo usuwamy wymuszony `st.rerun()` przy samym otwieraniu panelu i utrzymujemy fallback podglądu do aktualnego pytania/odpowiedzi.
Uzasadnienie:
- Eliminuje `StreamlitAPIException` (`... cannot be modified after the widget ... is instantiated`) zgłoszony przy kliknięciu `Anuluj`.
- Ogranicza skoki widoku (mniej zbędnych rerunów) i poprawia czytelność podglądu, gdy użytkownik dopiero otwiera panel bez wklejonej treści.

### D-174: Metryczka — domyślna wysokość pola `Pytanie` ustawiona na wygodny wariant ~2 linii
Decyzja:
- W `app.py` dla `textarea[aria-label="Pytanie"]` przyjmujemy:
  - `min-height: 50px`,
  - `height: 50px`,
  - `line-height: 1.3`,
  - `resize: vertical`.
Uzasadnienie:
- Wariant `38px` po H-065 był zbyt niski w praktyce i utrudniał edycję dłuższych pytań.
- `50px` daje czytelny start (ok. 2 linie) bez utraty kompaktowości widoku.

### D-175: Pole `Pytanie` w metryczce nie może mieć sztywnego `height`, bo blokuje ręczny resize
Decyzja:
- Dla `textarea[aria-label="Pytanie"]` stosujemy:
  - `min-height: 56px`,
  - `height: auto`,
  - `max-height: none`,
  - `resize: vertical`.
- Dodatkowo `st.text_area("Pytanie")` ma wysokość startową `56`.
Uzasadnienie:
- Sztywne `height: 50px !important` powodowało brak realnej możliwości rozszerzania pola mimo widocznego uchwytu resize.
- Po zdjęciu sztywnej wysokości pole pozostaje kompaktowe, ale działa zgodnie z oczekiwanym UX edycji dłuższych pytań.

### D-176: Panel `Wklej pytanie i odpowiedzi` startuje z prefill aktualnej treści pytania i odpowiedzi
Decyzja:
- Przy otwarciu panelu `📋 Wklej pytanie i odpowiedzi` ustawiamy `paste_text_*` jako seed:
  - najpierw bieżące pytanie,
  - potem aktualne odpowiedzi (po jednej w linii).
- Podgląd odpowiedzi renderujemy jako kompaktową listę HTML (`<ul><li>`) z mniejszym spacingiem.
Uzasadnienie:
- User oczekuje workflow „edytuj istniejące” jak na nagraniu referencyjnym, a nie pustego pola wejściowego.
- Domyślny markdown list w tym miejscu dawał zbyt duże odstępy i obniżał czytelność podglądu.

### D-179: Etykiety skrajne Likerta w mobile mają jawne łamanie po słowach, nie automatyczne łamanie znakowe
Decyzja:
- W `Questionnaire.tsx` dla single-screen:
  - `zdecydowanie nie` renderujemy jako `zdecydowanie` + `<br />` + `nie`,
  - `zdecydowanie tak` renderujemy jako `zdecydowanie` + `<br />` + `tak`,
  - neutralne `ani tak, ani nie` pozostaje jawnie dwuliniowe.
- W `SingleQuestionnaire.css` wycofujemy łamanie „awaryjne” znak-po-znaku:
  - `word-break: normal`,
  - `overflow-wrap: normal`,
  - `hyphens: none`.
Uzasadnienie:
- User wymagał, by nie występował podział `zdecydowani` / `e` w kafelkach na iPhone.
- Jawne łamanie po słowach daje deterministyczny efekt niezależnie od przeglądarki.

### D-180: Mobile portrait — przycisk `Dalej` ma mieć większy oddech od paska odpowiedzi
Decyzja:
- W `SingleQuestionnaire.css` dla `@media (max-width: 900px) and (orientation: portrait)` zwiększamy `margin-top` sekcji `.single-footer-actions` z `20px` do `30px`.
Uzasadnienie:
- User zgłosił, że `Dalej` jest za blisko paska odpowiedzi; korekta ma poprawić czytelność i separację akcji.

### D-181: W mobile pytanie główne nie może używać dzielenia wyrazów
Decyzja:
- W `SingleQuestionnaire.css` (mobile portrait, `.single-question-text`) wyłączamy:
  - `hyphens`,
  - łamanie wewnątrz wyrazu (`word-break`),
  - awaryjne zawijanie znakowe (`overflow-wrap`).
- Docelowe ustawienia:
  - `hyphens: none`,
  - `word-break: normal`,
  - `overflow-wrap: normal`.
Uzasadnienie:
- User wymaga braku podziałów typu `wy-` / `cofywać` i `społeczny-` / `ch`; tekst ma zawijać się wyłącznie między pełnymi wyrazami.

### D-185: Dla krytycznego case iPhone fraza `rozwiązać pokojowo` jest traktowana jako nierozdzielna
Decyzja:
- Do `PHRASE_GLUE_PATTERNS` w `Questionnaire.tsx` dodajemy regułę:
  - `\\brozwiązać\\s+pokojowo\\b`
- Reguła zamienia spację wewnątrz frazy na twardą (`NBSP`) przez `withHardSpaces(...)`.
Uzasadnienie:
- User zgłosił, że właśnie to pytanie nadal obcina końcówkę; sklejenie tej pary słów wymusza bezpieczniejsze zawinięcie całej końcówki zdania.

### D-187: Reguła „krótkich słów” klei wyłącznie pełne tokeny, nigdy fragmenty końcówek wyrazów
Decyzja:
- W `Questionnaire.tsx` zmieniamy `SHORT_WORD_GLUE_RE` z:
  - `\\b(na|do|...|dla)\\s+`
  na:
  - `(^|\\s)(na|do|...|dla)\\s+`
- Zamiana wykonywana callbackiem zachowuje prefix i dokleja NBSP tylko po pełnym krótkim słowie.
Uzasadnienie:
- `\\b` w JS jest ASCII-centryczne i przy polskich znakach mogło błędnie wykrywać granice wewnątrz wyrazów (np. końcówka `...na` w `można`), co tworzyło nienaturalnie nierozdzielne bloki i obcinanie tekstu na iPhone.

### D-182: Prefill panelu `Wklej pytanie i odpowiedzi` ma być formatem edycyjnym, nie surową listą
Decyzja:
- Seed pola `Wklej treść` renderujemy jako:
  - `Pytanie: {treść}`,
  - `Odpowiedzi:`,
  - numerowane odpowiedzi (`1.`, `2.`, ...).
- Parser obsługuje i czyści prefiks `Pytanie:` analogicznie do `Treść pytania:`.
- Wysokość pola wejściowego zwiększamy do `260`.
- Podgląd odpowiedzi renderujemy kompaktowo (ciasne `ul/li`).
Uzasadnienie:
- Użytkownik oczekuje workflow zgodnego z nagraniem referencyjnym: po otwarciu od razu edytowalny „blok” pytanie+odpowiedzi.
- Większe pole wejściowe jest potrzebne przy realnych pytaniach z dłuższą listą odpowiedzi.
- Domyślny markdown list dawał zbyt duże odstępy, co pogarszało czytelność podglądu.

### D-183: Build badge ma degradację łagodną — `local + mtime` zamiast `unknown|unknown`
Decyzja:
- W `_app_build_signature()` rozszerzamy fallback SHA/czasu o dodatkowe env-y deployowe.
- Gdy nadal brak czasu commita, używamy `mtime` pliku `app.py` jako ostatniego fallbacku czasu buildu.
- Gdy nadal brak SHA, fallback skrótu commita to `local` (nie `unknown`).
Uzasadnienie:
- `unknown-time | commit: unknown` jest mylące operacyjnie i wygląda jak awaria aplikacji.
- `local + mtime` daje czytelny sygnał, że aplikacja działa i ma konkretny build runtime, nawet bez pełnych metadanych Git.

### D-184: Prefill w `Wklej pytanie i odpowiedzi` ma być bez numeracji opcji
Decyzja:
- W seedzie pola `Wklej treść` odpowiedzi zapisujemy jako czyste linie, bez prefiksów `1.`, `2.`, `3.`.
- Placeholder również nie sugeruje numeracji.
Uzasadnienie:
- User wskazał, że numeracja w prefill jest zbędna i zaśmieca edycję; numerowanie odpowiedzi ma być elementem UI listy odpowiedzi, nie treści roboczej do wklejania.

### D-186: Zapis metryczki działa przez `save intent` (rerun przed właściwym zapisem)
Decyzja:
- W widokach metryczki (`jst_metryczka_view`, `personal_metryczka_view`) zapis jest dwuetapowy technicznie:
  - klik przycisku zapisuje `save_intent` i robi `st.rerun()`,
  - właściwy zapis konfiguracji wykonujemy dopiero w kolejnym przebiegu.
Uzasadnienie:
- `st.data_editor` potrafi nie zatwierdzić aktywnie edytowanej komórki w tym samym przebiegu, w którym kliknięto przycisk zapisu.
- `save intent` eliminuje konieczność podwójnego wpisywania kodowania i stabilizuje UX edytora.

### D-188: `Wklej pytanie i odpowiedzi` nie zmienia kodowania custom i ma przywracać pozycję edycji
Decyzja:
- W edytorze metryczki operacja `Wklej pytanie i odpowiedzi`:
  - aktualizuje treść pytania i listę etykiet odpowiedzi,
  - dla pytań custom zachowuje istniejące kody odpowiedzi (match po etykiecie, fallback po indeksie),
  - nie generuje nowych kodów `1..N`.
- Po `Wstaw`/`Anuluj` stosujemy scroll-restore do kotwicy edytowanego pytania.
Uzasadnienie:
- User zgłosił krytyczny błąd UX (skok na górę) i błąd merytoryczny (nadpisywanie kodowania), które utrudniały bezpieczną edycję metryczki.
- Funkcja wklejki ma wspierać treść pytań/odpowiedzi, a nie zmieniać warstwę kodowania danych.

### D-189: `Wstaw` w metryczce nie może resetować widgetów ani opierać mapowania kodowania na starym snapshotcie
Decyzja:
- W operacji `Wstaw`:
  - mapowanie `label -> code` opieramy najpierw o aktualne `options` z bieżącego renderu,
  - usuwamy `_bump_metryczka_editor_nonce(...)` z `Wstaw` i `Anuluj`,
  - scroll-restore wykonujemy przez `html_component`.
Uzasadnienie:
- `nonce bump` po `Wstaw`/`Anuluj` resetował klucze widgetów i mógł dawać efekt utraty świeżej edycji oraz skoku pozycji.
- Mapa kodowania ze starego `q_item` mogła pomijać najnowsze zmiany użytkownika w tabeli odpowiedzi.

### D-190: Zapis metryczki używa faz `arm -> commit -> save` dla pewnego commitu `data_editor`
Decyzja:
- `save_intent` dla metryczki przechowuje stan tekstowy fazy (`arm`, `commit`), a nie sam bool.
- Właściwy zapis do DB wykonujemy dopiero w fazie `commit`.
Uzasadnienie:
- Na części interakcji `data_editor` potrzebuje dodatkowego przebiegu, by pewnie zatwierdzić aktywną komórkę.
- Fazy zapisu minimalizują ryzyko utraty ostatniej zmiany kodowania przy pojedynczym kliknięciu `💾 Zapisz metryczkę`.

### D-191: Edytor metryczki ma zachowywać etykiety odpowiedzi nawet przy pustym kodzie i unikać nadmiarowych rerunów zapisu
Decyzja:
- `_metryczka_options_from_df` zachowuje każdy wiersz z niepustą etykietą odpowiedzi; pusty kod nie usuwa wiersza.
- Deduplikacja działa tylko dla niepustych kodów.
- Zapis metryczki działa bez wielofazowego `save intent` (bez sztucznych rerunów).
- Scroll do edytowanego pytania po wklejce realizujemy skryptem z retry (`hash + scrollIntoView`).
Uzasadnienie:
- Usuwanie wierszy z pustym kodem dawało mylący błąd „co najmniej 2 odpowiedzi” zamiast informacji o brakującym kodowaniu.
- Nadmiarowe reruny w ścieżce zapisu pogarszały stabilność commitu pól edycyjnych.


### D-192: Scroll-restore w metryczce musi działać także przy zagnieżdżonych iframe
Decyzja:
- Mechanizm powrotu do aktualnie edytowanego pytania po rerunie działa przez skrypt, który:
  - przechodzi po łańcuchu `window -> parent -> ...`,
  - szuka kotwicy pytania (`id`) na każdym poziomie dokumentu,
  - przewija przez `scrollTo` z fallbackiem `scrollIntoView`,
  - wykonuje retry przez kilkadziesiąt prób po rerunie.
Uzasadnienie:
- W części środowisk produkcyjnych panel jest renderowany w dodatkowych warstwach osadzenia; prosty dostęp tylko do jednego `parent.document` bywa niewystarczający i powoduje powrót na górę strony.

### D-193: `Wklej pytanie i odpowiedzi` dla custom ma proponować kodowanie z treści odpowiedzi
Decyzja:
- W operacji `Wstaw` dla pytań custom:
  - najpierw zachowujemy istniejące kodowania, jeśli można je dopasować (po etykiecie / ostrożny fallback),
  - dla braków domyślnie proponujemy `kodowanie = treść odpowiedzi` (wartość edytowalna przez użytkownika).
Uzasadnienie:
- Użytkownik oczekuje szybkiej propozycji kodowania bez ręcznego przepisywania każdej pozycji, ale jednocześnie bez utraty już poprawionych kodów.

### D-194: Główna akcja zapisu metryczki jest po prawej stronie sekcji
Decyzja:
- Przycisk `💾 Zapisz metryczkę` renderujemy w prawej kolumnie (JST i personal), jako akcję wykonawczą kończącą edycję.
Uzasadnienie:
- Użytkownik oczekuje standardowego układu UX, gdzie finalna akcja potwierdzająca znajduje się po prawej stronie.

### D-195: Scroll-restore metryczki musi być „wymuszony” nonce + remount
Decyzja:
- Dla akcji, które mają utrzymać użytkownika na aktualnym pytaniu (`Wstaw`, `Anuluj`, `Dodaj pytanie`), zapisujemy:
  - `scroll_target`,
  - unikalny `scroll_nonce`.
- Komponent JS od przewijania renderujemy z kluczem zależnym od nonce, aby wymusić świeże wykonanie skryptu po każdej akcji.
Uzasadnienie:
- W praktyce UI Streamlit potrafi nie odpalić identycznego skryptu przewijania przy kolejnych interakcjach na tym samym pytaniu; nonce+remount usuwa ten problem klasy „zostaję zrzucony na górę”.

### D-196: Scroll-restore przez `html_component` musi być kompatybilny z produkcyjnym API Streamlit (bez `key`)
Decyzja:
- W wywołaniu `html_component(...)` nie używamy argumentu `key`, bo nie jest wspierany w używanej wersji API (`IframeMixin._html`).
- Unikalność kolejnych uruchomień skryptu przewijania zapewniamy przez zmienny payload JS (`scroll_nonce` / `runId`).
Uzasadnienie:
- Użytkownik trafił na runtime crash na produkcji, który blokował edycję metryczki; zgodność z API ma wyższy priorytet niż syntetyczny remount po `key`.

### D-197: Scroll-restore metryczki działa dwutorowo (`html_component` + lokalny fallback `st.markdown`)
Decyzja:
- Utrzymujemy główny scroll-restore w `html_component`, ale dokładamy równoległy fallback JS renderowany przez `st.markdown(..., unsafe_allow_html=True)`.
- Oba tory korzystają z tego samego `scroll_target`/`scroll_nonce`.
Uzasadnienie:
- W części osadzeń Streamlit przewijanie z poziomu iframe bywa niestabilne względem głównego kontenera strony; lokalny fallback zwiększa skuteczność utrzymania pozycji na edytowanym pytaniu.

### D-198: Runtime ankiet (JST + personal) renderuje metryczkę wyłącznie z `metryczka_config`
Decyzja:
- Frontend nie trzyma już hardcodu pytań metryczkowych; oba runtime (`JstSurvey`, `Questionnaire`) normalizują i renderują pytania z konfiguracji badania.
- Zapis metryczki idzie jako mapa `db_column -> code` (nie etykieta UI), z zachowaniem kompatybilności rdzenia (`code=label` dla 5 pól core).
Uzasadnienie:
- Tylko taki model pozwala wdrażać pytania custom bez kolejnych zmian kodu frontendu i utrzymać spójność zapisu z konfiguracją edytora metryczki.

### D-199: Metryczka personalna jest zapisywana w `responses.scores` pod kluczem `metryczka`
Decyzja:
- RPC `add_response_by_slug` otrzymuje `p_scores` jako obiekt JSON: `{ "metryczka": { ... } }`.
- Nie zmieniamy schematu odpowiedzi personalnych (`answers` pozostaje bez zmian).
Uzasadnienie:
- Pozwala to wdrożyć zapis metryczki dla `archetypy.badania.pro` bez migracji schematu i bez regresji istniejącej logiki liczenia archetypów.

### D-200: Import/eksport/raport JST używa dynamicznego zestawu kolumn metryczki (kanoniczne + custom)
Decyzja:
- `db_jst_utils` buduje kolumny odpowiedzi jako:
  - stałe `CANONICAL_COLUMNS`,
  - plus custom `M_*` wynikające z `metryczka_config`.
- `jst_io_view` i `jst_analysis_view` przekazują `metryczka_config` do normalizacji/payloadu/dataframe.
- Generowanie raportu JST dostaje pełny dataframe z kolumnami custom (bez obcinania do samego kanonu).
Uzasadnienie:
- Bez tego custom metryczka byłaby tracona przy imporcie/eksporcie i niewidoczna w `data.csv`, co blokowałoby dalszą analitykę demograficzną.

### D-201: Personalna metryczka przyjmuje układ wizualny JST (pionowe opcje), ale z niebieskim akcentem
Decyzja:
- W ankiecie personalnej (`Questionnaire`) metryczkę renderujemy w układzie:
  - blok pytania,
  - pionowa lista opcji,
  - czytelny znacznik radiowy,
  podobnie do JST.
- Kolor akcentu wyboru i CTA jest niebieski (nie zielony), aby zachować spójność z dotychczasową linią personalną.
Uzasadnienie:
- User oczekuje większej spójności UX między metryczką personalną i JST, przy jednoczesnym zachowaniu własnej kolorystyki personalnej.

### D-202: Profilowanie demograficzne w wynikach personalnych działa jako filtr AND po metryczce + radar porównawczy
Decyzja:
- W module wyników personalnych dodajemy sekcję `Profile demograficzne` opartą o `metryczka_config` badania.
- Każda wybrana cecha demograficzna działa koniunkcyjnie (AND), a wynik pokazujemy jako:
  - liczebność podgrupy,
  - radar `cała próba vs podgrupa` (skala 0-20).
- Wprowadzamy próg minimalnej liczebności podgrupy i ostrzeżenie o niepewności poniżej progu.
Uzasadnienie:
- User oczekuje analizy wielocechowej (np. kobieta + wyższe + 60+) oraz szybkiego podglądu profilu archetypowego dla takiej kombinacji.
- AND jest najbardziej jednoznaczną i operacyjnie czytelną semantyką filtra dla badań kampanijnych.

### D-203: Zakładka `Segmenty` w Matching porównuje profile wyłącznie na wspólnej skali 12 archetypów (0-100)
Decyzja:
- W `🧭 Matching` dodajemy zakładkę `Segmenty`, która czyta profile segmentów JST z `SEGMENTY_ULTRA_PREMIUM_profile.csv`.
- Metryka dopasowania segmentu do polityka:
  - `Śr. luka |Δ| (pp)` = MAE po 12 archetypach,
  - `Zgodność (%) = 100 - MAE`.
- Segmenty poniżej zadanego progu `N` dostają status `Niepewne` i komunikat ostrzegawczy.
Uzasadnienie:
- User wymaga porównania tylko „na tej samej skali 12 archetypów”, bez mieszania innych osi czy heurystyk.
- Kontrola wiarygodności (min N + ostrzeżenie) ogranicza ryzyko nadinterpretacji mikrosegmentów.

### D-204: `Zgodność (%)` w `Segmentach` to metryka lokalna i nie jest równoważna `Poziomowi dopasowania` z `Podsumowania`
Decyzja:
- W `Segmentach` utrzymujemy prostą metrykę:
  - `Zgodność (%) = 100 - MAE` (MAE po 12 archetypach) dla pojedynczego segmentu.
- Nie dokładamy tam kar strategicznych (TOP/KEY), które są używane wyłącznie w globalnym wskaźniku `Poziom dopasowania` w `Podsumowaniu`.
Uzasadnienie:
- To dwa różne poziomy analizy:
  - `Podsumowanie` ocenia dopasowanie do całego profilu mieszkańców (globalnie, z karami),
  - `Segmenty` ocenia lokalną zbieżność do konkretnej podgrupy.
- Dzięki temu można mieć niski globalny matching i jednocześnie wysoki matching dla części segmentów.

### D-205: Profil demograficzny segmentu w Matching liczymy z mapowania `respondent_id -> segment` + metryczki JST
Decyzja:
- Źródłem segmentu jest plik runa:
  - `WYNIKI/respondenci_segmenty_ultra_premium.csv`.
- Źródłem demografii są payloady odpowiedzi JST (z wagami poststratyfikacyjnymi, jeśli aktywne dla badania).
- Łączenie wykonujemy po `respondent_id`, a wynik pokazujemy jako:
  - karty top kategorii (`📌 ...`),
  - tabela `% segment` vs `% ogół mieszkańców (ważony)` + różnica w pp.
Uzasadnienie:
- Tylko połączenie po identyfikatorze respondenta daje poprawny, statystyczny profil segmentu zgodny z bieżącą próbą.
- Pokazanie pokrycia mapowania ogranicza ryzyko nadinterpretacji, gdy część respondentów nie ma przypisanego segmentu.

### D-206: `Segmenty` w Matching używają metryki strategicznej (tej samej rodziny co `Podsumowanie`)
Decyzja:
- Wskaźnik `Zgodność (%)` w zakładce `Segmenty` liczymy metryką strategiczną:
  - `base = 0.40*(100-MAE) + 0.20*(100-RMSE) + 0.20*(100-TOP3_MAE) + 0.20*(100-KEY_MAE)`,
  - `zgodność = clamp(0,100, base - kara_kluczowa)`.
- Oznacza to odejście od uproszczonego `100 - MAE` jako finalnej zgodności segmentu.
Uzasadnienie:
- Proste `100 - MAE` zawyżało wynik przy profilach z dużymi rozjazdami strategicznymi (zwłaszcza na priorytetach TOP/KEY).
- User zgłosił „absurdalnie wysokie” zgodności; metryka strategiczna usuwa ten efekt i ujednolica interpretację z `Podsumowaniem`.

Status:
- Decyzja D-204 zostaje zastąpiona przez D-206.

### D-207: Segmentowy scoring key-focused — 75% wagi dla puli kluczowej `TOP5 + TOP5`
Decyzja:
- W `Segmentach` finalny wynik zgodności liczony jest z przewagą puli kluczowej:
  - `base_global` na wszystkich 12 archetypach,
  - `base_key` na puli `TOP5 polityka + TOP5 segmentu`,
  - finalnie: `0.25*base_global + 0.75*base_key - key_penalty`.
- Kary priorytetowe TOP3/TOP2 są utrzymane i wzmocnione dla analizy segmentowej.
Uzasadnienie:
- User oczekuje, aby wynik segmentu był liczony „w głównej mierze po kluczowych archetypach”, a nie po pełnym profilu 12 archetypów.
- Taki układ ogranicza ryzyko sztucznie zawyżonej zgodności, gdy zgodność globalna maskuje rozjazdy w osiach kluczowych kampanijnie.

### D-208: Segmenty dostają własny panel kontekstowy u góry (kogo dotyczy + poziom wybranego segmentu)
Decyzja:
- Zakładka `Segmenty` renderuje na górze:
  - blok kontekstowy (badanie personalne + badanie mieszkańców),
  - kartę `Poziom zgodności wybranego segmentu` (%, ocena, pasek).
Uzasadnienie:
- User potrzebuje natychmiastowego kontekstu „dla kogo” i bieżącej oceny wybranego segmentu bez scrollowania do radaru i tabel pomocniczych.

### D-209: Segmentowy key-focused scoring przechodzi z TOP5 na TOP6 i ma łagodniejsze kary
Decyzja:
- Pula kluczowa dla `Segmentów`:
  - `TOP6 polityka + TOP6 segmentu` (zamiast TOP5).
- Dla segmentów obniżono agresywność kar:
  - mniejsza kara za rozjazd TOP1,
  - mniejsza kara za brak/wąską część wspólną TOP,
  - łagodniejsza kara od `KEY_MAE` i `KEY_MAX`.
- Miks bazowy:
  - `35% global + 65% key` (zamiast silniejszego dociążenia key).
Uzasadnienie:
- User wskazał przypadki, w których wynik spadał do `0%` mimo oczekiwania bardziej zniuansowanej oceny.
- Celem jest utrzymanie priorytetu osi kluczowych, ale bez „twardego zerowania” przy trudniejszych profilach.

### D-210: Legenda nad radarem segmentowym renderowana jako szeroka legenda HTML
Decyzja:
- Dla radaru w zakładce `Segmenty` wyłączamy legendę Plotly i renderujemy własną, szerszą legendę HTML (pill).
Uzasadnienie:
- Legenda Plotly przy dłuższych nazwach segmentów bywała obcinana.
- Wersja HTML daje stabilną szerokość i czytelność niezależnie od długości etykiet.

### D-211: Biblioteka predefiniowanych pytań metryczkowych jest wspólna dla JST i personalnych (`kind=both`)
Decyzja:
- Dodano tabelę `public.metryczka_question_templates` i API zapisu/odczytu szablonów pytań metryczkowych.
- W edytorze metryczki można:
  - zapisać pytanie do biblioteki,
  - wstawić pytanie z biblioteki do bieżącej ankiety.
- Szablony zapisywane z poziomu edytora trafiają domyślnie do wspólnego zakresu `both`.
Uzasadnienie:
- User chce wielokrotnie używać tych samych pytań (np. `M_OBSZAR`) między badaniami.
- Wspólna biblioteka upraszcza ponowne użycie także między JST i personalnymi.

### D-212: Tabele demograficzne w Matching liczone dynamicznie z `metryczka_config`
Decyzja:
- W `Matching` (`Demografia` i sekcja demografii w `Segmentach`) odchodzimy od stałej piątki pól.
- Specyfikacja zmiennych i kategorii jest budowana z `metryczka_config` JST:
  - rdzeń (`M_PLEC..M_MATERIAL`) zachowuje kanoniczną normalizację,
  - custom `M_*` są liczone i renderowane dynamicznie.
Uzasadnienie:
- Przy metryczce konfigurowalnej hardcoded 5 pól prowadziło do utraty części danych demograficznych w Matching.
- Dynamiczny mechanizm utrzymuje spójność z konfiguracją ankiety i umożliwia przyszłe rozszerzenia bez zmian kodu tabel.

### D-213: Generator JST zaczyna przejście na dynamiczne `M_*` (rdzeń + custom)
Decyzja:
- W skrypcie `JST_Archetypy_Analiza/analyze_poznan_archetypes.py`:
  - `parse_metryczka(...)` przepuszcza dodatkowe kolumny `M_*`,
  - `_onehot_metry(...)` i główne funkcje demograficzne iterują po dynamicznej liście `M_*`,
  - payload demografii (`var_order/cat_order`) budowany jest z aktualnych kolumn metryczki.
Uzasadnienie:
- To pierwszy bezpieczny etap migracji generatora do obsługi metryczki konfigurowalnej.
- Pozwala utrzymać działający pipeline raportu i jednocześnie włączać customowe zmienne do tabel demograficznych.

### D-214: Segmentowy wynik bazowy liczony w 100% z puli kluczowej (`TOP6 + TOP6`)
Decyzja:
- W zakładce `🧭 Matching > Segmenty` bazę wyniku zgodności liczymy wyłącznie z puli kluczowej:
  - `base_score = base_key`,
  - pula kluczowa = suma unii `TOP6 polityka + TOP6 segmentu`.
- Pełny profil 12 archetypów pozostaje metryką pomocniczą diagnostycznie (`mae_all`), ale nie wpływa już na bazę `% zgodności`.
Uzasadnienie:
- User wskazał, że w segmentacji archetypy z ogona rozkładu mają śladowe znaczenie i zaburzały interpretację dopasowania.
- Priorytet kampanijny ma zgodność na osiach kluczowych, więc baza wskaźnika ma być w pełni key-focused.

### D-215: Kalibracja „siły kar segmentowych” przez 3 profile (`łagodna`, `standard`, `ostra`)
Decyzja:
- Do Segmentów dodano kontrolkę `Siła kar segmentowych` sterującą zestawem współczynników kar:
  - kara od `key_gap_mae`,
  - kara od `key_gap_max` (z progiem),
  - kara za brak/wąską część wspólną priorytetów,
  - kara za rozjazd TOP1.
- Domyślny profil to `standard`.
Uzasadnienie:
- Użytkownik chce móc zmieniać czułość wskaźnika bez kolejnych zmian kodu.
- Trzy predefiniowane profile dają szybki kompromis między stabilnością metodologiczną a elastycznością analityczną.

Status:
- D-209 zostaje doprecyzowana przez D-214 i D-215 (finalnie: baza 100% key-pool + kalibrowalne kary).
