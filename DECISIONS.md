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
