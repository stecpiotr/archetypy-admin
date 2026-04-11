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

### D-090: Kara kluczowa liczy TOP3 warunkowo jako TOP2 przy wysokiej 3. pozycji
Decyzja:
- Dla puli kluczowej (`KEY_MAE`, `KEY_MAX`) stosujemy regułę:
  - domyślnie TOP3 polityka i TOP3 mieszkańców,
  - jeśli 3. pozycja profilu ma wynik `>70`, archetyp z 3. pozycji nie wchodzi do puli kluczowej (dla tego profilu liczymy TOP2).
Uzasadnienie:
- User wymagał, aby przy takim przypadku nie naliczać kary za „poboczny” archetyp z 3. miejsca.
- Reguła zmniejsza ryzyko przeszacowania kary kluczowej dla tego konkretnego przypadku.
