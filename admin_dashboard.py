import pandas as pd
import streamlit as st
import psycopg2
import ast
from fpdf import FPDF
from docx import Document
from io import BytesIO

st.set_page_config(page_title="AP-48 – panel administratora", layout="wide")

db_host = st.secrets["db_host"]
db_name = st.secrets["db_name"]
db_user = st.secrets["db_user"]
db_pass = st.secrets["db_pass"]
db_port = st.secrets.get("db_port", 5432)

archetypes = {
    "Władca":   [1, 2, 3, 4],
    "Bohater":  [5, 6, 7, 8],
    "Mędrzec":  [9, 10, 11, 12],
    "Opiekun":  [13, 14, 15, 16],
    "Kochanek": [17, 18, 19, 20],
    "Błazen":   [21, 22, 23, 24],
    "Twórca":   [25, 26, 27, 28],
    "Odkrywca": [29, 30, 31, 32],
    "Mag":      [33, 34, 35, 36],
    "Zwykły":   [37, 38, 39, 40],
    "Niewinny": [41, 42, 43, 44],
    "Buntownik":[45, 46, 47, 48],
}

archetype_features = {
    "Władca": "Potrzeba kontroli, organizacji, zarządzanie, wprowadzanie ładu.",
    "Bohater": "Odwaga, walka z przeciwnościami, mobilizacja do działania.",
    "Mędrzec": "Wiedza, analityczność, logiczne argumenty, racjonalność.",
    "Opiekun": "Empatia, dbanie o innych, ochrona, troska.",
    "Kochanek": "Relacje, emocje, bliskość, autentyczność uczuć.",
    "Błazen": "Poczucie humoru, dystans, lekkość, rozładowywanie napięć.",
    "Twórca": "Kreatywność, innowacja, wyrażanie siebie, estetyka.",
    "Odkrywca": "Niezależność, zmiany, nowe doświadczenia, ekspresja.",
    "Mag": "Transformacja, inspiracja, zmiana świata, przekuwanie idei w czyn.",
    "Zwykły": "Autentyczność, wspólnota, prostota, bycie częścią grupy.",
    "Niewinny": "Optymizm, ufność, unikanie konfliktów, pozytywne nastawienie.",
    "Buntownik": "Kwestionowanie norm, odwaga w burzeniu zasad, radykalna zmiana."
}

archetype_extended = {
    "Władca": {
        "name": "Władca",
        "tagline": "Autorytet. Kontrola. Doskonałość.",
        "description": (
            "Archetyp Władcy w polityce uosabia siłę przywództwa, stabilność i pewność działania. "
            "Jako kandydat na prezydenta Lublina Władca stawia na porządek, wyznaczanie standardów rozwoju i podejmowanie stanowczych decyzji dla dobra wspólnego. "
            "Jest symbolem autentycznego autorytetu, przewodzenia i skutecznego zarządzania miastem. "
            "Buduje zaufanie, komunikując skuteczność, odpowiedzialność i gwarantując bezpieczeństwo mieszkańcom."
        ),
        "storyline": (
            "Narracja kampanii oparta na Władcy podkreśla spójność działań, panowanie nad trudnymi sytuacjami i sprawność w zarządzaniu miastem. "
            "Władca nie podąża za modą – wyznacza nowe standardy w samorządzie. "
            "Akcentuje dokonania, referencje i doświadczenie. Buduje obraz lidera odpowiadającego za przyszłość i prestiż Lublina."
        ),
        "recommendations": [
            "Używaj kolorystyki kojarzącej się z autorytetem – czerń, złoto, ciemny granat, burgund.",
            "Projektuj symbole: sygnety, herby miasta Lublin, podkreślając prestiż i zarządzanie.",
            "Komunikuj się językiem odpowiedzialności i troski o przyszłość miasta.",
            "Przekazuj komunikaty stanowczo, jednoznacznie, jako gospodarz miasta.",
            "Pokazuj osiągnięcia, inwestycje, referencje mieszkańców.",
            "Zadbaj o trwałość i jakość działań – nie obniżaj standardów.",
            "Twórz aurę elitarności: zamknięte konsultacje, spotkania liderów opinii.",
            "Przyciągaj wyborców ceniących bezpieczeństwo, stabilizację i prestiż miasta.",
            "Unikaj luźnego, żartobliwego tonu – postaw na klasę i profesjonalizm."
        ],
        "core_traits": [
            "Autorytet", "Przywództwo", "Stabilność", "Prestiż", "Kontrola", "Inspiracja", "Mistrzostwo"
        ],
        "example_brands": [
            "Rolex", "Mercedes-Benz", "IBM", "British Airways", "Silny samorząd"
        ],
        "color_palette": [
            "#000000", "#FFD700", "#282C34", "#800020"
        ],
        "visual_elements": [
            "Korona", "Herb Lublina", "Sygnet", "Monogram", "Geometryczna, masywna typografia", "Symetria"
        ],
        "keyword_messaging": [
            "Lider Lublina", "Siła samorządu", "Stabilność", "Doskonałość działań", "Elita miasta", "Bezpieczeństwo"
        ],
        "questions": [
            "Jak komunikujesz mieszkańcom swoją pozycję lidera w Lublinie?",
            "W jaki sposób Twoje działania budują autorytet i zaufanie mieszkańców?",
            "Co robisz, by decyzje były stanowcze i jednoznaczne?",
            "Jak Twoje dokonania i inwestycje wzmacniają prestiż oraz bezpieczeństwo miasta?",
            "Jak zachęcasz wyborców do świadomego, silnego przywództwa?"
        ]
    },
    "Bohater": {
        "name": "Bohater",
        "tagline": "Determinacja. Odwaga. Sukces.",
        "description": (
            "Bohater w polityce to archetyp waleczności, determinacji i odwagi w podejmowaniu trudnych decyzji dla społeczności. "
            "Prezydent-Bohater mobilizuje mieszkańców do działania, bierze odpowiedzialność w najtrudniejszych momentach i broni interesów Lublina nawet pod presją."
        ),
        "storyline": (
            "Opowieść Bohatera to historia przezwyciężania kryzysów i stawania po stronie obywateli. "
            "Bohater nie rezygnuje nigdy, nawet w obliczu przeciwności. Jego postawa inspiruje i daje przykład innym samorządowcom."
        ),
        "recommendations": [
            "Komunikuj gotowość do działania, podkreślaj determinację w rozwiązywaniu problemów.",
            "Pokaż sukcesy i przykłady walki o interes mieszkańców.",
            "Stosuj dynamiczny język: zaznaczaj odwagę, mobilizację, sukces.",
            "Kolorystyka: czerwień, granat, biel.",
            "Pokazuj się w trudnych sytuacjach – reaguj natychmiast.",
            "Inspiruj współpracowników i mieszkańców do aktywności.",
            "Unikaj bierności, podkreślaj proaktywność."
        ],
        "core_traits": [
            "Odwaga", "Siła", "Determinacja", "Poświęcenie", "Sukces", "Inspiracja"
        ],
        "example_brands": [
            "Nike", "Polska Husaria", "ONG", "Patriotyczny samorząd"
        ],
        "color_palette": [
            "#E10600", "#2E3141", "#FFFFFF"
        ],
        "visual_elements": [
            "Peleryna", "Tarcza", "Aura odwagi", "Podniesiona dłoń", "Gwiazda"
        ],
        "keyword_messaging": [
            "Siła", "Zwycięstwo", "Poświęcenie", "Mobilizacja"
        ],
        "questions": [
            "Jak komunikujesz skuteczność w przezwyciężaniu kryzysów?",
            "Jak budujesz wizerunek walczącego o dobro mieszkańców?",
            "Jak pokazać determinację i niezłomność w działaniu publicznym?",
            "Które sukcesy świadczą o Twoim zaangażowaniu w trudnych sprawach?"
        ]
    },
    "Mędrzec": {
        "name": "Mędrzec",
        "tagline": "Wiedza. Racjonalność. Strategia.",
        "description": (
            "Mędrzec w polityce opiera komunikację na wiedzy, argumentacji i logicznym rozumowaniu. "
            "Kandydat na prezydenta wykorzystuje rozsądne analizy, doświadczenie oraz ekspercką wiedzę, by podejmować najlepsze decyzje dla całej społeczności."
        ),
        "storyline": (
            "Opowieść Mędrca to budowanie zaufania kompetencjami, przejrzystym uzasadnieniem propozycji i edukacją mieszkańców. "
            "Mędrzec nie działa pod wpływem impulsu; każda decyzja jest przemyślana i poparta faktami oraz wsłuchaniem się w potrzeby miasta."
        ),
        "recommendations": [
            "Wskazuj kompetencje, doświadczenie i eksperckość w zarządzaniu Lublinem.",
            "Komunikuj zrozumiale zawiłości miejskich inwestycji i decyzji.",
            "Stosuj wykresy, dane, analizy i argumenty – przemawiaj do rozumu obywateli.",
            "Zachowaj spokojny, opanowany ton.",
            "Używaj kolorystyki: błękit, szarość, granat.",
            "Podkreślaj racjonalność decyzji i transparentność działań.",
            "Unikaj populizmu – opieraj komunikację na faktach."
        ],
        "core_traits": [
            "Wiedza", "Rozwój", "Analiza", "Strategia", "Refleksja"
        ],
        "example_brands": [
            "Google", "Wikipedia", "MIT", "Think tanki"
        ],
        "color_palette": [
            "#4682B4", "#B0C4DE", "#6C7A89"
        ],
        "visual_elements": [
            "Okulary", "Księga", "Wykres", "Lupa", "Symbole nauki"
        ],
        "keyword_messaging": [
            "Wiedza", "Argument", "Racjonalność", "Rozwój miasta"
        ],
        "questions": [
            "Jak podkreślasz swoje doświadczenie i kompetencje?",
            "Jak przekonujesz mieszkańców argumentami i faktami?",
            "Jak edukujesz oraz tłumaczysz skomplikowane zmiany w mieście?",
            "W czym wyrażasz przewagę eksperckiej wiedzy nad populizmem?"
        ]
    },
    "Opiekun": {
        "name": "Opiekun",
        "tagline": "Empatia. Troska. Bezpieczeństwo.",
        "description": (
            "Opiekun w polityce to archetyp zaangażowania, wspierania i budowania poczucia wspólnoty. "
            "Kandydat–Opiekun dba o najsłabszych, promuje działania prospołeczne, wdraża programy pomocowe i społecznie odpowiedzialne."
        ),
        "storyline": (
            "Narracja Opiekuna podkreśla działania integrujące, troskę o seniorów, rodziny, niepełnosprawnych i osoby wykluczone. "
            "Buduje poczucie bezpieczeństwa oraz odpowiedzialności urzędu miasta za wszystkich obywateli."
        ),
        "recommendations": [
            "Akcentuj działania na rzecz integracji i wsparcia mieszkańców.",
            "Pokaż realne efekty programów prospołecznych i pomocowych.",
            "Stosuj ciepłą kolorystykę: zieleń, błękit, żółcie.",
            "Używaj symboliki: dłonie, serca, uścisk.",
            "Komunikuj empatię i autentyczną troskę o każdą grupę mieszkańców.",
            "Prowadź otwarte konsultacje społeczne.",
            "Unikaj twardego, technokratycznego tonu."
        ],
        "core_traits": [
            "Empatia", "Troska", "Wspólnota", "Bezpieczeństwo", "Solidarność"
        ],
        "example_brands": [
            "UNICEF", "Caritas", "WOŚP", "Hospicja"
        ],
        "color_palette": [
            "#B4D6B4", "#A7C7E7", "#FFD580"
        ],
        "visual_elements": [
            "Dłonie", "Serce", "Koło wspólnoty", "Symbol opieki"
        ],
        "keyword_messaging": [
            "Bezpieczeństwo mieszkańców", "Troska", "Wspólnota"
        ],
        "questions": [
            "Jak pokazujesz troskę i empatię wobec wszystkich mieszkańców?",
            "Jakie realne efekty mają wdrożone przez Ciebie programy pomocowe?",
            "W czym przejawia się Twoja polityka integrująca?",
            "Jak oceniasz skuteczność działań społecznych w mieście?"
        ]
    },
    "Kochanek": {
        "name": "Kochanek",
        "tagline": "Bliskość. Relacje. Pasja.",
        "description": (
            "Kochanek w polityce buduje pozytywne relacje z mieszkańcami, jest otwarty, komunikatywny i wzbudza zaufanie. "
            "Potrafi zbliżyć do siebie wyborców i sprawić, by czuli się zauważeni oraz docenieni."
        ),
        "storyline": (
            "Narracja Kochanka promuje serdeczność, ciepło i partnerskie traktowanie obywateli. "
            "Akcentuje jakość relacji z mieszkańcami, zespołem i innymi samorządami."
        ),
        "recommendations": [
            "Buduj relacje oparte na dialogu i wzajemnym szacunku.",
            "Stosuj ciepły, otwarty ton komunikacji.",
            "Promuj wydarzenia i inicjatywy integrujące społeczność.",
            "Używaj kolorystyki: czerwienie, róże, delikatne fiolety.",
            "Pokazuj, że wyborca jest dla Ciebie ważny.",
            "Doceniaj pozytywne postawy, sukcesy mieszkańców.",
            "Unikaj oficjalnego, zimnego tonu."
        ],
        "core_traits": [
            "Ciepło", "Relacje", "Bliskość", "Pasja", "Akceptacja"
        ],
        "example_brands": [
            "Allegro", "Santander", "Lubelskie Dni Róż"
        ],
        "color_palette": [
            "#FA709A", "#FEE140", "#FFD6E0"
        ],
        "visual_elements": [
            "Serce", "Uśmiech", "Gest bliskości"
        ],
        "keyword_messaging": [
            "Relacje", "Bliskość", "Społeczność"
        ],
        "questions": [
            "Jak komunikujesz otwartość i serdeczność wyborcom?",
            "Jakie działania podejmujesz, aby budować pozytywne relacje w mieście?",
            "Co robisz, by mieszkańcy czuli się ważni i zauważeni?"
        ]
    },
    "Błazen": {
        "name": "Błazen",
        "tagline": "Poczucie humoru. Dystans. Entuzjazm.",
        "description": (
            "Błazen w polityce wnosi lekkość, dystans i rozładowanie napięć. "
            "Kandydat-Błazen potrafi rozbawić, rozproszyć atmosferę, ale nigdy nie traci dystansu do siebie i powagi spraw publicznych."
        ),
        "storyline": (
            "Narracja Błazna to umiejętność śmiania się z problemów i codziennych wyzwań miasta, ale też dawania mieszkańcom nadziei oraz pozytywnej energii."
        ),
        "recommendations": [
            "Stosuj humor w komunikacji (ale z umiarem i klasą!).",
            "Rozluźniaj atmosferę podczas spotkań i debat.",
            "Podkreślaj pozytywne aspekty życia w mieście.",
            "Kolorystyka: żółcie, pomarańcze, intensywne kolory.",
            "Nie bój się autoironii.",
            "Promuj wydarzenia integrujące, rozrywkowe.",
            "Unikaj przesadnego formalizmu."
        ],
        "core_traits": [
            "Poczucie humoru", "Entuzjazm", "Dystans", "Optymizm"
        ],
        "example_brands": [
            "Allegro", "Łomża", "Kabarety"
        ],
        "color_palette": [
            "#FFB300", "#FF8300", "#FFD93D"
        ],
        "visual_elements": [
            "Uśmiech", "Czapka błazna", "Kolorowe akcenty"
        ],
        "keyword_messaging": [
            "Dystans", "Entuzjazm", "Radość"
        ],
        "questions": [
            "W jaki sposób wykorzystujesz humor w komunikacji publicznej?",
            "Jak rozładowujesz napięcia w sytuacjach kryzysowych?",
            "Co robisz, aby mieszkańcy mogli wspólnie się bawić i śmiać?"
        ]
    },
    "Twórca": {
        "name": "Twórca",
        "tagline": "Kreatywność. Innowacja. Wizja.",
        "description": (
            "Twórca w polityce to źródło nowych pomysłów, innowacji i niebanalnych rozwiązań dla miasta. "
            "Jako prezydent–Twórca nie boi się wdrażać oryginalnych, często nieszablonowych strategii."
        ),
        "storyline": (
            "Opowieść Twórcy jest oparta na zmianie, wprowadzaniu kreatywnych rozwiązań oraz inspirowaniu innych do współdziałania dla rozwoju Lublina."
        ),
        "recommendations": [
            "Proponuj i wdrażaj nietypowe rozwiązania w mieście.",
            "Pokazuj przykłady innowacyjnych projektów.",
            "Promuj kreatywność i otwartość na zmiany.",
            "Stosuj kolorystykę: zielenie, lazurowe błękity, fiolety.",
            "Doceniaj artystów, startupy, lokalne inicjatywy.",
            "Buduj wizerunek miasta-innowatora.",
            "Unikaj schematów i powtarzalnych projektów."
        ],
        "core_traits": [
            "Kreatywność", "Odwaga twórcza", "Inspiracja", "Wizja", "Nowatorstwo"
        ],
        "example_brands": [
            "Tesla", "Dyrekcja Lublin", "Startupy"
        ],
        "color_palette": [
            "#7C53C3", "#3BE8B0", "#87CEEB"
        ],
        "visual_elements": [
            "Kostka Rubika", "Żarówka", "Kolorowe fale"
        ],
        "keyword_messaging": [
            "Innowacja", "Twórczość", "Wizja rozwoju"
        ],
        "questions": [
            "Jak promujesz kreatywność i innowacyjność w mieście?",
            "Jakie oryginalne projekty wdrożyłeś lub planujesz wdrożyć?",
            "Jak inspirować mieszkańców do kreatywnego działania?"
        ]
    },
    "Odkrywca": {
        "name": "Odkrywca",
        "tagline": "Odwaga. Ciekawość. Nowe horyzonty.",
        "description": (
            "Odkrywca poszukuje nowych rozwiązań, jest otwarty na zmiany i śledzi światowe trendy, które wdraża w Lublinie. "
            "Wybiera nowatorskie, nieoczywiste drogi dla rozwoju miasta i jego mieszkańców."
        ),
        "storyline": (
            "Opowieść Odkrywcy to wędrowanie poza schematami, miasto bez barier, eksperymentowanie z nowościami oraz angażowanie mieszkańców w odkrywcze projekty."
        ),
        "recommendations": [
            "Inicjuj nowe projekty i szukaj innowacji także poza Polską.",
            "Promuj przełamywanie standardów i aktywność obywatelską.",
            "Stosuj kolorystykę: turkusy, błękity, odcienie zieleni.",
            "Publikuj inspiracje z innych miast i krajów.",
            "Wspieraj wymiany młodzieży, startupy, koła naukowe.",
            "Unikaj stagnacji i powielania dawnych schematów."
        ],
        "core_traits": [
            "Odwaga", "Ciekawość", "Niezależność", "Nowatorstwo"
        ],
        "example_brands": [
            "Red Bull", "National Geographic", "Nomadzi"
        ],
        "color_palette": [
            "#43C6DB", "#A0E8AF", "#F9D371"
        ],
        "visual_elements": [
            "Mapa", "Kompas", "Droga", "Lupa"
        ],
        "keyword_messaging": [
            "Odkrywanie", "Nowe horyzonty", "Zmiana"
        ],
        "questions": [
            "Jak zachęcasz do odkrywania nowości w mieście?",
            "Jakie projekty wdrażasz, które nie były jeszcze realizowane w innych miastach?",
            "Jak budujesz wizerunek Lublina jako miejsca wolnego od barier?"
        ]
    },
    "Mag": {
        "name": "Mag",
        "tagline": "Transformacja. Inspiracja. Przełom.",
        "description": (
            "Mag w polityce to wizjoner i transformator – wytycza nowy kierunek i inspiruje do zmian niemożliwych na pierwszy rzut oka. "
            "Dzięki jego inicjatywom Lublin przechodzi metamorfozy, w których niemożliwe staje się możliwe."
        ),
        "storyline": (
            "Opowieść Maga to zmiana wykraczająca poza rutynę, wyobraźnia, inspiracja, a także odwaga w stawianiu pytań i szukaniu odpowiedzi poza schematami."
        ),
        "recommendations": [
            "Wprowadzaj śmiałe, czasem kontrowersyjne pomysły w życie.",
            "Podkreślaj rolę wizji i inspiracji.",
            "Stosuj symbolikę: gwiazdy, zmiany, światło, 'magiczne' efekty.",
            "Stosuj kolorystykę: fiolety, granaty, akcent perłowy.",
            "Buduj wyobrażenie miasta jako miejsca możliwości.",
            "Unikaj banalnych, powtarzalnych rozwiązań."
        ],
        "core_traits": [
            "Inspiracja", "Przemiana", "Wyobraźnia", "Transcendencja"
        ],
        "example_brands": [
            "Apple", "Disney", "Nasa", "Nowoczesny Lublin"
        ],
        "color_palette": [
            "#8F00FF", "#181C3A", "#E0BBE4"
        ],
        "visual_elements": [
            "Gwiazda", "Iskra", "Łuk magiczny"
        ],
        "keyword_messaging": [
            "Zmiana", "Inspiracja", "Możliwość"
        ],
        "questions": [
            "Jak pokazujesz mieszkańcom, że niemożliwe jest możliwe?",
            "Jakie innowacje budują wizerunek miasta kreatywnego i nowoczesnego?",
            "Jak inspirujesz społeczność do patrzenia dalej?"
        ]
    },
    "Zwykły": {
        "name": "Zwykły",
        "tagline": "Wspólnota. Prostota. Bliskość.",
        "description": (
            "Zwykły w polityce stoi blisko ludzi, jest autentyczny, stawia na prostotę i tworzenie bezpiecznej wspólnoty społecznej. "
            "Nie udaje, nie buduje dystansu – jest 'swojakiem', na którym można polegać."
        ),
        "storyline": (
            "Opowieść Zwykłego koncentruje się wokół wartości rodzinnych, codziennych wyzwań, pracy od podstaw oraz pielęgnowania lokalnej tradycji."
        ),
        "recommendations": [
            "Podkreślaj prostotę i codzienność w komunikacji.",
            "Stosuj jasne, proste słowa i obrazy.",
            "Buduj atmosferę równości (każdy ma głos).",
            "Stosuj kolorystykę: beże, błękity, zielone akcenty.",
            "Doceniaj lokalność i rodzinność.",
            "Promuj wspólnotowe inicjatywy.",
            "Unikaj dystansu i języka eksperckiego."
        ],
        "core_traits": [
            "Autentyczność", "Wspólnota", "Prostota", "Równość"
        ],
        "example_brands": [
            "Sieci osiedlowe", "Społem", "Allegro"
        ],
        "color_palette": [
            "#F9F9F9", "#6CA0DC", "#A3C1AD"
        ],
        "visual_elements": [
            "Dom", "Krąg ludzi", "Prosta ikona dłoni"
        ],
        "keyword_messaging": [
            "Bliskość", "Razem", "Prostota"
        ],
        "questions": [
            "Jak podkreślasz autentyczność i codzienność?",
            "Jak pielęgnujesz lokalność i wspólnotę?",
            "Co robisz, by każdy mieszkaniec czuł się zauważony?"
        ]
    },
    "Niewinny": {
        "name": "Niewinny",
        "tagline": "Optymizm. Nadzieja. Nowy początek.",
        "description": (
            "Niewinny w polityce otwarcie komunikuje pozytywne wartości, niesie nadzieję i podkreśla wiarę w zmiany na lepsze. "
            "Kandydat–Niewinny buduje zaufanie szczerością i skutecznie apeluje o współpracę dla wspólnego dobra."
        ),
        "storyline": (
            "Opowieść Niewinnego buduje napięcie wokół pozytywnych emocji, odwołuje się do marzeń o lepszym Lublinie i wiary we wspólny sukces."
        ),
        "recommendations": [
            "Komunikuj optymizm, wiarę w ludzi i dobre intencje.",
            "Stosuj jasną kolorystykę: biele, pastele, żółcie.",
            "Dziel się sukcesami społeczności.",
            "Stawiaj na transparentność działań.",
            "Angażuj się w kampanie edukacyjne i społeczne.",
            "Unikaj negatywnego przekazu, straszenia, manipulacji."
        ],
        "core_traits": [
            "Optymizm", "Nadzieja", "Współpraca", "Szlachetność"
        ],
        "example_brands": [
            "Kinder", "Polska Akcja Humanitarna"
        ],
        "color_palette": [
            "#FFF6C3", "#AAC9CE", "#FFF200"
        ],
        "visual_elements": [
            "Gołąb", "Słońce", "Dziecko"
        ],
        "keyword_messaging": [
            "Nadzieja", "Optymizm", "Wspólnie"
        ],
        "questions": [
            "Jak budujesz wizerunek pozytywnego samorządowca?",
            "Jak zachęcasz mieszkańców do dzielenia się nadzieją?",
            "Jak komunikujesz szczerość i otwartość?"
        ]
    },
    "Buntownik": {
        "name": "Buntownik",
        "tagline": "Zmiana. Odwaga. Przełom.",
        "description": (
            "Buntownik w polityce odważnie kwestionuje zastane układy, nawołuje do zmiany i walczy o nowe, lepsze reguły gry w mieście. "
            "Potrafi ściągnąć uwagę i zjednoczyć mieszkańców wokół śmiałych idei."
        ),
        "storyline": (
            "Narracja Buntownika podkreśla walkę z niesprawiedliwością i stagnacją, wytykanie błędów władzy i radykalne pomysły na rozwój Lublina."
        ),
        "recommendations": [
            "Akcentuj odwagę do mówienia „nie” starym rozwiązaniom.",
            "Publikuj manifesty i odważne postulaty.",
            "Stosuj wyrazistą kolorystykę: czernie, czerwienie, ostre kolory.",
            "Inspiruj mieszkańców do aktywnego sprzeciwu wobec barier rozwojowych.",
            "Podkreślaj wolność słowa, swobody obywatelskie.",
            "Unikaj koncentrowania się wyłącznie na krytyce – pokazuj pozytywne rozwiązania."
        ],
        "core_traits": [
            "Odwaga", "Bezpardonowość", "Radykalizm", "Niepokorność"
        ],
        "example_brands": [
            "Harley Davidson", "Greenpeace", "Gazeta Wyborcza"
        ],
        "color_palette": [
            "#000000", "#FF0000", "#FF6F61"
        ],
        "visual_elements": [
            "Piorun", "Megafon", "Odwrócona korona"
        ],
        "keyword_messaging": [
            "Zmiana", "Rewolucja", "Nowe reguły"
        ],
        "questions": [
            "Jak komunikujesz odwagę i gotowość do zmiany?",
            "Jak mobilizujesz do zrywania z przeszłością?",
            "Co robisz, by mieszkańcy mieli w Tobie rzecznika zmiany?"
        ]
    }
}

def clean_pdf_text(text):
    if text is None:
        return ""
    return str(text).replace("–", "-").replace("—", "-")

@st.cache_data(ttl=30)
def load():
    conn = psycopg2.connect(
        host=db_host,
        database=db_name,
        user=db_user,
        password=db_pass,
        port=db_port,
        sslmode="require"
    )
    df = pd.read_sql("SELECT * FROM ap48_responses", con=conn)
    conn.close()
    if "created_at" in df.columns:
        df["created_at"] = pd.to_datetime(df["created_at"])

    def parse_scores(x):
        try:
            v = ast.literal_eval(x) if pd.notnull(x) else None
            if isinstance(v, dict): return [v[str(i)] for i in range(1, 49)]
            if isinstance(v, list): return v
            return None
        except Exception: return None

    if "scores" in df.columns:
        df["answers"] = df["scores"].apply(parse_scores)
    return df

def archetype_scores(answers):
    if not isinstance(answers, list) or len(answers) < 48:
        return {k: None for k in archetypes}
    out = {}
    for name, idxs in archetypes.items():
        out[name] = sum(answers[i-1] for i in idxs)
    return out

def archetype_percent(scoresum):
    if scoresum is None: return None
    return round(scoresum / 20 * 100, 1)

def interpret(arcsums):
    sorted_arcs = sorted(arcsums.items(), key=lambda x: x[1] or -99, reverse=True)
    max_typ, max_val = sorted_arcs[0]
    second_typ, second_val = sorted_arcs[1]
    result = max_typ
    if max_val is not None and second_val is not None and abs(max_val - second_val) <= 3:
        result = f"{max_typ} – {second_typ}"
    return result, max_typ, second_typ

def export_word(main_type, second_type, features, main, second):
    doc = Document()
    doc.add_heading("Raport AP-48 – Archetypy", 0)
    doc.add_heading(f"Główny archetyp: {main_type}", level=1)
    doc.add_paragraph(f"Cechy kluczowe: {features[main_type]}")
    doc.add_paragraph(main.get("description", ""))
    doc.add_paragraph("Storyline: " + main.get("storyline", ""))
    doc.add_paragraph("Rekomendacje: " + "\n".join(main.get("recommendations", [])))
    if second_type and second_type != main_type:
        doc.add_heading(f"Archetyp pomocniczy: {second_type}", level=2)
        doc.add_paragraph(f"Cechy kluczowe: {features[second_type]}")
        doc.add_paragraph(second.get("description", ""))
        doc.add_paragraph("Storyline: " + second.get("storyline", ""))
        doc.add_paragraph("Rekomendacje: " + "\n".join(second.get("recommendations", [])))
    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

def export_pdf(main_type, second_type, features, main, second):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, clean_pdf_text("Raport AP-48 – Archetypy"), ln=1)
    pdf.set_font("Arial", "B", 13)
    pdf.cell(0, 8, clean_pdf_text(f"Główny archetyp: {main_type}"), ln=1)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(
        0, 7, clean_pdf_text(
            f"Cechy kluczowe: {features[main_type]}\n\n"
            f"{main.get('description', '')}\n\n"
            f"Storyline: {main.get('storyline', '')}\n\n"
            f"Rekomendacje: " + "\n".join(main.get("recommendations", [])) + "\n"
        )
    )
    if second_type and second_type != main_type:
        pdf.set_font("Arial", "B", 12)
        pdf.cell(0, 8, clean_pdf_text(f"Archetyp pomocniczy: {second_type}"), ln=1)
        pdf.set_font("Arial", "", 11)
        pdf.multi_cell(
            0, 7, clean_pdf_text(
                f"Cechy kluczowe: {features[second_type]}\n\n"
                f"{second.get('description', '')}\n\n"
                f"Storyline: {second.get('storyline', '')}\n\n"
                f"Rekomendacje: " + "\n".join(second.get("recommendations", []))
            )
        )
    buf = BytesIO()
    pdf.output(buf)
    buf.seek(0)
    return buf

def render_archetype_card(archetype_data, main=True):
    if not archetype_data:
        st.warning("Brak danych o archetypie.")
        return

    border_color = archetype_data['color_palette'][0]
    symbol = archetype_data['visual_elements'][0] if archetype_data['visual_elements'] else ""
    symbol_emoji = {
        "Korona": "👑", "Herb Lublina": "🛡️", "Peleryna": "🦸", "Serce": "❤️",
        "Uśmiech": "😊", "Dłonie": "🤝", "Księga": "📖", "Mapa": "🗺️",
        "Gwiazda": "⭐", "Gołąb": "🕊️", "Piorun": "⚡", "Rubika": "🧩", "Dom": "🏡"
    }
    icon = symbol_emoji.get(symbol, "🔹")
    box_shadow = f"0 4px 14px 0 {border_color}44" if main else f"0 2px 6px 0 {border_color}22"
    bg_color = archetype_data['color_palette'][1] if main else "#FAFAFA"
    st.markdown(f"""
    <div style="
        border: 3px solid {border_color if main else '#CCC'};
        border-radius: 20px;
        background: {bg_color};
        box-shadow: {box_shadow};
        padding: 2.2em 2.2em 1.2em 2.2em;
        margin-bottom: 16px;
        display: flex; align-items: center;">
        <div style="font-size:3em; margin-right:30px;">
            {icon}
        </div>
        <div>
            <div style="font-size:2em;font-weight:bold;">{archetype_data['name']}</div>
            <div style="font-size:1.15em; font-style:italic; color:{border_color}">{archetype_data['tagline']}</div>
            <div style="margin-top:10px; color:#444;"><b>Opis:</b> {archetype_data['description']}</div>
            <div style="margin-top:7px;font-weight:600;color:#222;">Storyline:</div>
            <div style="margin-bottom:6px;">{archetype_data['storyline']}</div>
            <div style="color:#666;font-size:1em"><b>Cechy:</b> {", ".join(archetype_data['core_traits'])}</div>
            <div style="margin-top:7px;font-weight:600;color:#222;">Rekomendacje:</div>
            <ul style="padding-left:24px">
                {''.join(f'<li style="margin-bottom:2px;">{r}</li>' for r in archetype_data['recommendations'])}
            </ul>
            <div style="margin-top:7px;font-weight:600;">Słowa kluczowe:</div>
            <div>{', '.join(archetype_data['keyword_messaging'])}</div>
            <div style="margin-top:7px;font-weight:600;">Elementy wizualne:</div>
            <div>{', '.join(archetype_data['visual_elements'])}</div>
            <div style="margin-top:7px;font-weight:600;">Przykłady marek/organizacji:</div>
            <div>{', '.join(archetype_data['example_brands'])}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

st.title("AP-48 – panel administratora")

data = load()
st.metric("Łączna liczba ankiet", len(data))

if "answers" in data.columns:
    results = []
    for idx, row in data.iterrows():
        # WALIDACJA: tylko jeśli są odpowiedzi (list!)
        if not isinstance(row.get("answers", None), list):
            continue
        arcsums = archetype_scores(row["answers"])
        arcper = {k: archetype_percent(v) for k, v in arcsums.items()}
        archetypes_label, main_type, second_type = interpret(arcsums)
        main = archetype_extended.get(main_type, {})
        second = archetype_extended.get(second_type, {}) if second_type != main_type else {}
        results.append({
            "ID": row.get("id", idx + 1),
            **arcsums,
            **{f"{k}_%": v for k, v in arcper.items()},
            "Archetyp": archetypes_label,
            "Główny archetyp": main_type,
            "Cechy kluczowe": archetype_features[main_type],
            "Opis": main.get("description", ""),
            "Storyline": main.get("storyline", ""),
            "Rekomendacje": "\n".join(main.get("recommendations", [])),
            "Archetyp pomocniczy": second_type if second_type != main_type else "",
            "Cechy pomocniczy": archetype_features.get(second_type, "") if second_type != main_type else "",
            "Opis pomocniczy": second.get("description", "") if second_type != main_type else "",
            "Storyline pomocniczy": second.get("storyline", "") if second_type != main_type else "",
            "Rekomendacje pomocniczy": "\n".join(second.get("recommendations", [])) if second_type != main_type else "",
        })
    results_df = pd.DataFrame(results)
    if not results_df.empty and "ID" in results_df.columns:
        results_df = results_df.sort_values("ID")

    if len(results_df) > 0:
        st.subheader(f"Profil ostatniego respondenta: {results_df.iloc[-1]['Główny archetyp']}")
        render_archetype_card(archetype_extended.get(results_df.iloc[-1]['Główny archetyp'], {}), main=True)
        if results_df.iloc[-1]['Archetyp pomocniczy']:
            st.markdown(f"### Archetyp pomocniczy: {results_df.iloc[-1]['Archetyp pomocniczy']}")
            render_archetype_card(archetype_extended.get(results_df.iloc[-1]['Archetyp pomocniczy'], {}), main=False)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Pobierz raport Word"):
                buf = export_word(
                    results_df.iloc[-1]['Główny archetyp'],
                    results_df.iloc[-1]['Archetyp pomocniczy'],
                    archetype_features,
                    archetype_extended.get(results_df.iloc[-1]['Główny archetyp'], {}),
                    archetype_extended.get(results_df.iloc[-1]['Archetyp pomocniczy'], {})
                )
                st.download_button("Pobierz plik Word", data=buf, file_name="ap48_raport.docx")
        with col2:
            if st.button("Pobierz raport PDF"):
                buf = export_pdf(
                    results_df.iloc[-1]['Główny archetyp'],
                    results_df.iloc[-1]['Archetyp pomocniczy'],
                    archetype_features,
                    archetype_extended.get(results_df.iloc[-1]['Główny archetyp'], {}),
                    archetype_extended.get(results_df.iloc[-1]['Archetyp pomocniczy'], {})
                )
                st.download_button("Pobierz plik PDF", data=buf, file_name="ap48_raport.pdf")
    st.divider()
    st.dataframe(results_df)
    st.download_button("Pobierz wyniki archetypów (CSV)", results_df.to_csv(index=False), "ap48_archetypy.csv")