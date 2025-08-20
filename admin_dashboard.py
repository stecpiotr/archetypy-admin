import pandas as pd
import streamlit as st
import psycopg2
import ast
import plotly.graph_objects as go
from fpdf import FPDF
import unicodedata
import requests
from PIL import Image, ImageDraw
import io
import re
from datetime import datetime
import pytz
from docx.shared import Pt
import os
from docxtpl import DocxTemplate, InlineImage
from io import BytesIO
import tempfile
import shutil
import sys
if sys.platform.startswith("linux"):
    import subprocess
else:
    from docx2pdf import convert

TEMPLATE_PATH = "ap48_raport_template.docx"
logos_dir = "logos_local"

def get_logo_svg_path(brand_name, logos_dir=None):
    if logos_dir is None:
        logos_dir = "logos_local"
    # Konwersja dla strategii zapisu plików: "Alfa Romeo" → "alfa-romeo.svg"
    filename = (
        brand_name.lower()
            .replace(" ", "-")
            .replace("'", "")
            .replace("’", "")
            .replace("ł", "l")
            .replace("ś", "s")
            .replace("ż", "z")
            .replace("ó", "o")
            .replace("ć", "c")
            .replace("ń", "n")
            .replace("ę", "e")
            .replace("ą", "a")
            .replace("ś", "s") +
        ".svg"
    )
    path = os.path.join(logos_dir, filename)
    if os.path.exists(path):
        return path
    # fallback: spróbuj bez myślnika, wersje alternatywne
    filename_nodash = brand_name.lower().replace(" ", "").replace("'", "").replace("’", "") + ".svg"
    path2 = os.path.join(logos_dir, filename_nodash)
    if os.path.exists(path2):
        return path2
    return None

from io import BytesIO
from docxtpl import InlineImage
from docx.shared import Mm

import subprocess
from io import BytesIO

person_wikipedia_links = {
    "Aleksandra Dulkiewicz": "https://pl.wikipedia.org/wiki/Aleksandra_Dulkiewicz",
    "Aleksiej Nawalny": "https://pl.wikipedia.org/wiki/Aleksiej_Nawalny",
    "Angela Merkel": "https://pl.wikipedia.org/wiki/Angela_Merkel",
    "Andrzej Duda": "https://pl.wikipedia.org/wiki/Andrzej_Duda",
    "Barack Obama": "https://pl.wikipedia.org/wiki/Barack_Obama",
    "Benito Juárez": "https://pl.wikipedia.org/wiki/Benito_Ju%C3%A1rez",
    "Bernie Sanders": "https://pl.wikipedia.org/wiki/Bernie_Sanders",
    "Boris Johnson": "https://pl.wikipedia.org/wiki/Boris_Johnson",
    "Bronisław Geremek": "https://pl.wikipedia.org/wiki/Bronis%C5%82aw_Geremek",
    "Clement Attlee": "https://pl.wikipedia.org/wiki/Clement_Attlee",
    "Donald Trump": "https://pl.wikipedia.org/wiki/Donald_Trump",
    "Elon Musk": "https://pl.wikipedia.org/wiki/Elon_Musk",
    "Emmanuel Macron": "https://pl.wikipedia.org/wiki/Emmanuel_Macron",
    "Eva Perón": "https://pl.wikipedia.org/wiki/Eva_Per%C3%B3n",
    "François Mitterrand": "https://pl.wikipedia.org/wiki/Fran%C3%A7ois_Mitterrand",
    "Franklin D. Roosevelt": "https://pl.wikipedia.org/wiki/Franklin_D._Roosevelt",
    "George Washington": "https://pl.wikipedia.org/wiki/George_Washington",
    "Jacek Kuroń": "https://pl.wikipedia.org/wiki/Jacek_Kuro%C5%84",
    "Jacinda Ardern": "https://pl.wikipedia.org/wiki/Jacinda_Ardern",
    "Jarosław Kaczyński": "https://pl.wikipedia.org/wiki/Jaros%C5%82aw_Kaczy%C5%84ski",
    "Jawaharlal Nehru": "https://pl.wikipedia.org/wiki/Jawaharlal_Nehru",
    "Janusz Palikot": "https://pl.wikipedia.org/wiki/Janusz_Palikot",
    "Jeremy Corbyn": "https://pl.wikipedia.org/wiki/Jeremy_Corbyn",
    "Jimmy Carter": "https://pl.wikipedia.org/wiki/Jimmy_Carter",
    "Joe Biden": "https://pl.wikipedia.org/wiki/Joe_Biden",
    "John F. Kennedy": "https://pl.wikipedia.org/wiki/John_F._Kennedy",
    "Józef Piłsudski": "https://pl.wikipedia.org/wiki/J%C3%B3zef_Pi%C5%82sudski",
    "Justin Trudeau": "https://pl.wikipedia.org/wiki/Justin_Trudeau",
    "Konrad Adenauer": "https://pl.wikipedia.org/wiki/Konrad_Adenauer",
    "Lee Kuan Yew": "https://pl.wikipedia.org/wiki/Lee_Kuan_Yew",
    "Lech Wałęsa": "https://pl.wikipedia.org/wiki/Lech_Wa%C5%82%C4%99sa",
    "Ludwik XIV": "https://pl.wikipedia.org/wiki/Ludwik_XIV_Burbonski",
    "Margaret Thatcher": "https://pl.wikipedia.org/wiki/Margaret_Thatcher",
    "Marine Le Pen": "https://pl.wikipedia.org/wiki/Marine_Le_Pen",
    "Martin Luther King": "https://pl.wikipedia.org/wiki/Martin_Luther_King",
    "Mustafa Kemal Atatürk": "https://pl.wikipedia.org/wiki/Mustafa_Kemal_Atat%C3%BCrk",
    "Napoleon Bonaparte": "https://pl.wikipedia.org/wiki/Napoleon_Bonaparte",
    "Nelson Mandela": "https://pl.wikipedia.org/wiki/Nelson_Mandela",
    "Olof Palme": "https://pl.wikipedia.org/wiki/Olof_Palme",
    "Pedro Sánchez": "https://pl.wikipedia.org/wiki/Pedro_S%C3%A1nchez",
    "Sanna Marin": "https://pl.wikipedia.org/wiki/Sanna_Marin",
    "Shimon Peres": "https://pl.wikipedia.org/wiki/Shimon_Peres",
    "Silvio Berlusconi": "https://pl.wikipedia.org/wiki/Silvio_Berlusconi",
    "Sławomir Mentzen": "https://pl.wikipedia.org/wiki/S%C5%82awomir_Mentzen",
    "Szymon Hołownia": "https://pl.wikipedia.org/wiki/Szymon_Ho%C5%82ownia",
    "Theodore Roosevelt": "https://pl.wikipedia.org/wiki/Theodore_Roosevelt",
    "Thomas Jefferson": "https://pl.wikipedia.org/wiki/Thomas_Jefferson",
    "Tony Blair": "https://pl.wikipedia.org/wiki/Tony_Blair",
    "Václav Havel": "https://pl.wikipedia.org/wiki/V%C3%A1clav_Havel",
    "Václav Klaus": "https://pl.wikipedia.org/wiki/V%C3%A1clav_Klaus",
    "Vladimir Putin": "https://pl.wikipedia.org/wiki/W%C5%82adimir_Putin",
    "Winston Churchill": "https://pl.wikipedia.org/wiki/Winston_Churchill",
    "Wołodymyr Zełenski": "https://pl.wikipedia.org/wiki/Wo%C5%82odymyr_Ze%C5%82enski",
    "Władysław Kosiniak-Kamysz": "https://pl.wikipedia.org/wiki/W%C5%82adys%C5%82aw_Kosiniak-Kamysz",
    "Xi Jinping": "https://pl.wikipedia.org/wiki/Xi_Jinping",
    "Deng Xiaoping": "https://en.wikipedia.org/wiki/Deng_Xiaoping",
}

from docx.oxml import OxmlElement
from docx.oxml.ns import qn

def add_hyperlink(paragraph, text, url):
    part = paragraph.part
    r_id = part.relate_to(url, 'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink', is_external=True)
    hyperlink = OxmlElement('w:hyperlink')
    hyperlink.set(qn('r:id'), r_id)
    new_run = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')
    c = OxmlElement('w:color')
    c.set(qn('w:val'), "0000FF")
    rPr.append(c)
    u = OxmlElement('w:u')
    u.set(qn('w:val'), "single")
    rPr.append(u)
    new_run.append(rPr)
    t = OxmlElement('w:t')
    t.text = text
    new_run.append(t)
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)
    return hyperlink

def person_link(name):
    url = person_wikipedia_links.get(name)
    if url:
        return f"<a href='{url}' target='_blank'>{name}</a>"
    return name

def svg_to_png_bytes(svg_path, width_mm=None, height_mm=None):
    import cairosvg

    with open(svg_path, "rb") as svg_file:
        svg_bytes = svg_file.read()

    # Przelicz mm na px (96 dpi ≈ 3.78 px/mm)
    arg_dict = {}
    if width_mm is not None:
        arg_dict['output_width'] = int(width_mm * 3.78 * 4)  # ×4 dla ostrości
    if height_mm is not None:
        arg_dict['output_height'] = int(height_mm * 3.78 * 4)

    png_bytes = cairosvg.svg2png(bytestring=svg_bytes, **arg_dict)
    return png_bytes

def build_brands_for_word(doc, brand_list, logos_dir, height_mm=20):
    out = []

    for brand in brand_list:
        logo_path = get_logo_svg_path(brand, logos_dir)

        if logo_path:
            # Wygeneruj PNG o wysokości 20 mm, szerokość liczy się automatycznie
            img_bytes = svg_to_png_bytes(logo_path, height_mm=height_mm)
            img_stream = BytesIO(img_bytes)
            img = InlineImage(doc, img_stream, height=Mm(height_mm))
            out.append({"brand": brand, "logo": img})
        else:
            out.append({"brand": brand, "logo": ""})

    return out


def zapobiegaj_wdowie(text):
    # Twarda spacja przed ostatnim wyrazem każdego akapitu
    # Obsługuje \n\n jako koniec akapitu
    paras = text.split('\n')
    out = []
    for para in paras:
        para = para.rstrip()
        # Jeśli za krótko, pomiń
        if len(para.split(' ')) < 2:
            out.append(para)
            continue
        before_last, last = para.rsplit(' ', 1)
        out.append(f"{before_last}\u00A0{last}")
    return '\n'.join(out)

import cairosvg

st.set_page_config(page_title="Archetypy – panel administratora", layout="wide")

COLOR_NAME_MAP = {
        "#000000": "czerń",
        "#FFD700": "złoto",
        "#282C34": "granat /antracyt/",
        "#800020": "burgund",
        "#E10600": "czerwień",
        "#2E3141": "grafitowy granat",
        "#FFFFFF": "biel",
        "#4682B4": "stalowy błękit",
        "#B0C4DE": "jasny niebieskoszary",
        "#6C7A89": "popielaty szary",
        "#B4D6B4": "miętowa zieleń",
        "#A7C7E7": "pastelowy błękit",
        "#FFD580": "pastelowy żółty / beżowy",
        "#FA709A": "róż malinowy",
        "#FEE140": "jasny żółty",
        "#FFD6E0": "bardzo jasny róż",
        "#FFB300": "mocna żółć",
        "#FF8300": "pomarańcz",
        "#FFD93D": "pastelowa żółć",
        "#7C53C3": "fiolet",
        "#3BE8B0": "miętowy cyjan",
        "#87CEEB": "błękit /sky blue/",
        "#43C6DB": "turkusowy błękit",
        "#A0E8AF": "seledyn",
        "#F9D371": "złocisty żółty",
        "#8F00FF": "fiolet intensywny",
        "#181C3A": "granat bardzo ciemny",
        "#E0BBE4": "pastelowy fiolet",
        "#F9F9F9": "biel bardzo jasna",
        "#6CA0DC": "pastelowy błękit",
        "#A3C1AD": "pastelowa zieleń",
        "#FFF6C3": "jasny kremowy",
        "#AAC9CE": "pastelowy niebieskoszary",
        "#FFF200": "żółty (cytrynowy)",
        "#FF0000": "czerwień intensywna",
        "#FF6F61": "łososiowy róż",
        "#8C564B": "ciemny brąz",
        "#D62728": "czerwień karmazynowa",
        "#1F77B4": "chabrowy",
        "#9467BD": "fiolet śliwkowy",
        "#F2A93B": "miodowy żółty",
        "#17BECF": "niebieski morski",
        "#E377C2": "pastelowy róż fioletowy",
        "#7C46C5": "fiolet szafirowy",
        "#2CA02C": "zieleń trawiasta",
        "#9BD6F4": "pastelowy błękit jasny",
        "#FF7F0E": "jaskrawy pomarańcz"
}

ARCHE_NAMES_ORDER = [
    "Niewinny", "Mędrzec", "Odkrywca", "Buntownik", "Czarodziej", "Bohater",
    "Kochanek", "Błazen", "Towarzysz", "Opiekun", "Władca", "Twórca"
]

def archetype_name_to_img_idx(name):
    try:
        return ARCHE_NAMES_ORDER.index(name)
    except ValueError:
        return None

archetypes = {
    "Władca":   [1, 2, 3, 4],
    "Bohater":  [5, 6, 7, 8],
    "Mędrzec":  [9, 10, 11, 12],
    "Opiekun":  [13, 14, 15, 16],
    "Kochanek": [17, 18, 19, 20],
    "Błazen":   [21, 22, 23, 24],
    "Twórca":   [25, 26, 27, 28],
    "Odkrywca": [29, 30, 31, 32],
    "Czarodziej": [33, 34, 35, 36],
    "Towarzysz": [37, 38, 39, 40],
    "Niewinny": [41, 42, 43, 44],
    "Buntownik": [45, 46, 47, 48],
}

# ---- MAPA EMOJI I FUNKCJE (DAJ JE TU, ZAWSZE PRZED CAŁĄ LOGIKĄ) ----
archetype_emoji = {
    "Władca": "👑", "Bohater": "🦸", "Mędrzec": "📖", "Opiekun": "🤝", "Kochanek": "❤️",
    "Błazen": "🤪", "Twórca": "🧩", "Odkrywca": "🗺️", "Czarodziej": "⭐", "Towarzysz": "🏡",
    "Niewinny": "🕊️", "Buntownik": "🔥"
}
def normalize(name):
    if not isinstance(name, str):
        return name
    return name.split("/")[0].split(",")[0].strip().title()

def get_emoji(name):
    """
    Zwraca emoji dla archetypu, nawet jeśli w nazwie pojawiają się ukośniki lub dodatki.
    """
    return archetype_emoji.get(normalize(name), "🔹")

def zero_to_dash(val):
    return "-" if val == 0 else str(val)

archetype_features = {
    "Władca": "Potrzeba kontroli, organizacji, zarządzanie, wprowadzanie ładu.",
    "Bohater": "Odwaga, walka z przeciwnościami, mobilizacja do działania.",
    "Mędrzec": "Wiedza, analityczność, logiczne argumenty, racjonalność.",
    "Opiekun": "Empatia, dbanie o innych, ochrona, troska.",
    "Kochanek": "Relacje, emocje, bliskość, autentyczność uczuć.",
    "Błazen": "Poczucie humoru, dystans, lekkość, rozładowywanie napięć.",
    "Twórca": "Kreatywność, innowacja, wyrażanie siebie, estetyka.",
    "Odkrywca": "Niezależność, zmiany, nowe doświadczenia, ekspresja.",
    "Czarodziej": "Transformacja, inspiracja, zmiana świata, przekuwanie idei w czyn.",
    "Towarzysz": "Autentyczność, wspólnota, prostota, bycie częścią grupy.",
    "Niewinny": "Optymizm, ufność, unikanie konfliktów, pozytywne nastawienie.",
    "Buntownik": "Kwestionowanie norm, odwaga w burzeniu zasad, radykalna zmiana."
}

# <<<--- TUTAJ WKLEJ własne archetype_extended = {...}
archetype_extended = {
    "Władca": {
        "name": "Władca",
        "tagline": "Autorytet. Kontrola. Doskonałość.",
        "description": (
            "Archetyp Władcy w polityce uosabia siłę przywództwa, stabilność, pewność działania, kontrolę i odpowiedzialność za porządek społeczny. "
            "Władcy dążą do stabilności, bezpieczeństwa i efektywnego zarządzania. Politycy o tym archetypie często podkreślają swoją zdolność do podejmowania trudnych decyzji i utrzymywania porządku, nawet w trudnych czasach. "
            "Władca stawia na porządek, wyznaczanie standardów rozwoju i podejmowanie stanowczych decyzji dla dobra wspólnego. "
            "Jest symbolem autentycznego autorytetu, przewodzenia i skutecznego zarządzania miastem. "
            "Buduje zaufanie, komunikując skuteczność, odpowiedzialność i gwarantując bezpieczeństwo mieszkańcom."
        ),
        "storyline": (
            "Narracja kampanii oparta na Władcy podkreśla spójność działań, panowanie nad trudnymi sytuacjami i sprawność w zarządzaniu miastem. "
            "Władca nie podąża za modą – wyznacza nowe standardy w samorządzie. "
            "Akcentuje dokonania, referencje i doświadczenie. Buduje obraz lidera odpowiadającego za przyszłość i prestiż miasta."
        ),
        "recommendations": [
            "Używaj kolorystyki kojarzącej się z autorytetem – czerń, złoto, ciemny granat, burgund.",
            "Projektuj symbole: sygnety, herby miasta, podkreślając prestiż i zarządzanie.",
            "Komunikuj się językiem odpowiedzialności i troski o przyszłość miasta.",
            "Przekazuj komunikaty stanowczo, jednoznacznie, jako gospodarz miasta.",
            "Pokazuj osiągnięcia, inwestycje, referencje mieszkańców.",
            "Zadbaj o trwałość i jakość działań – nie obniżaj standardów.",
            "Twórz aurę elitarności: zamknięte konsultacje, spotkania liderów opinii.",
            "Przyciągaj wyborców ceniących bezpieczeństwo, stabilizację i prestiż miasta.",
            "Unikaj luźnego, żartobliwego tonu – postaw na klasę i profesjonalizm."
        ],
        "core_traits": [
            "Przywództwo", "Autorytet", "Stabilność", "Prestiż", "Kontrola", "Inspiracja", "Mistrzostwo"
        ],
        "strengths": [
            "przywództwo", "zdecydowanie", "umiejętności organizacyjne"
        ],
        "weaknesses": [
            "autorytaryzm", "kontrola", "oderwanie od rzeczywistości"
        ],
        "examples_person": [
            "Vladimir Putin", "Margaret Thatcher", "Xi Jinping", "Ludwik XIV", "Napoleon Bonaparte",
            "Jarosław Kaczyński"
        ],
        "example_brands": [
            "Rolex", "Mercedes-Benz", "IBM", "Microsoft", "Hugo Boss", "BMW", "Silny samorząd"
        ],
        "color_palette": [
            "#000000", "#FFD700", "#282C34", "#800020", "#8C564B"
        ],
        "visual_elements": [
            "korona", "herb Miasta", "sygnet", "monogram", "geometryczna, masywna typografia", "symetria"
        ],
        "keyword_messaging": [
            "Lider miasta", "Siła samorządu", "Stabilność", "Doskonałość działań", "Elita miasta", "Bezpieczeństwo"
        ],
        "watchword": [
            "Silne przywództwo i stabilność w niepewnych czasach."
        ],
        "questions": [
            "Jak komunikujesz mieszkańcom swoją pozycję lidera w mieście?",
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
            "Bohaterowie są gotowi stawić czoła wyzwaniom, pokonywać przeszkody i walczyć o lepszą przyszłość dla wszystkich. Ich celem jest udowodnienie swojej wartości poprzez odważne działania i inspirowanie innych do przekraczania własnych granic. Politycy o tym archetypie często podkreślają swoją gotowość do podejmowania trudnych decyzji i stawiania czoła przeciwnościom w imię dobra wspólnego. "
            "Bohater mobilizuje mieszkańców do działania, bierze odpowiedzialność w najtrudniejszych momentach i broni interesów miasta nawet pod presją."
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
        "strengths": [
            "odwaga", "determinacja", "kompetencja", "inspirowanie innych"
        ],
        "weaknesses": [
            "arogancja", "obsesja na punkcie zwycięstwa", "skłonność do przechwalania się",
        ],
        "examples_person": [
            "Winston Churchill", "Wołodymyr Zełenski", "George Washington", "Józef Piłsudski"
        ],
        "example_brands": [
            "Nike", "Duracell", "FedEx", "Ferrari", "Polska Husaria", "Patriotyczny samorząd"
        ],
        "color_palette": [
            "#E10600", "#2E3141", "#FFFFFF", "#D62728"
        ],
        "visual_elements": [
            "peleryna", "tarcza", "aura odwagi", "podniesiona dłoń", "gwiazda"
        ],
        "keyword_messaging": [
            "Siła", "Zwycięstwo", "Poświęcenie", "Mobilizacja"
        ],
        "watchword": [
            "Odważne przywództwo dla lepszej przyszłości."
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
            "Mędrzec w polityce opiera komunikację na wiedzy, argumentacji i logicznym rozumowaniu oraz analitycznym podejściu. "
            "Mędrcy poszukują prawdy i wiedzy, wierząc, że informacja i zrozumienie są kluczem do rozwiązywania problemów. Politycy o tym archetypie często prezentują się jako eksperci, którzy podejmują decyzje w oparciu o fakty i analizy, a nie emocje czy ideologię. "
            "Mędrzec wykorzystuje rozsądne analizy, doświadczenie oraz ekspercką wiedzę, by podejmować najlepsze decyzje dla całej społeczności."
        ),
        "storyline": (
            "Opowieść Mędrca to budowanie zaufania kompetencjami, przejrzystym uzasadnieniem propozycji i edukacją mieszkańców. "
            "Mędrzec nie działa pod wpływem impulsu; każda decyzja jest przemyślana i poparta faktami oraz wsłuchaniem się w potrzeby miasta."
        ),
        "recommendations": [
            "Wskazuj kompetencje, doświadczenie i eksperckość w zarządzaniu miastem.",
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
        "strengths": [
            "inteligencja", "obiektywizm", "umiejętność analizy złożonych problemów"
        ],
        "weaknesses": [
            "nadmierna rozwaga", "brak zdecydowania", "oderwanie od codziennych problemów"
        ],
        "examples_person": [
            "Angela Merkel", "Thomas Jefferson", "Lee Kuan Yew", "Bronisław Geremek"
        ],
        "example_brands": [
            "BBC", "Google", "MIT", "CNN", "Audi", "think tanki"
        ],
        "color_palette": [
            "#4682B4", "#B0C4DE", "#6C7A89", "#1F77B4"
        ],
        "visual_elements": [
            "okulary", "księga", "wykres", "lupa", "symbole nauki"
        ],
        "keyword_messaging": [
            "Wiedza", "Argument", "Racjonalność", "Rozwój miasta"
        ],
        "watchword": [
            "Mądrość i wiedza w służbie społeczeństwa."
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
            "Archetyp Opiekuna reprezentuje troskę, empatię i chęć pomocy innym. "
            "Opiekunowie pragną chronić obywateli i zapewniać im bezpieczeństwo oraz wsparcie. Politycy o tym archetypie często skupiają się na polityce społecznej, ochronie zdrowia, edukacji i innych usługach publicznych, które poprawiają jakość życia obywateli. "
            "Opiekun dba o najsłabszych, promuje działania prospołeczne, wdraża programy pomocowe i społecznie odpowiedzialne."
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
        "strengths": [
            "empatia", "troska o innych", "budowanie zaufania"
        ],
        "weaknesses": [
            "nadopiekuńczość", "unikanie trudnych decyzji", "podatność na manipulację"
        ],
        "examples_person": [
            "Jacinda Ardern", "Franklin D. Roosevelt", "Clement Attlee", "Władysław Kosiniak-Kamysz", "Jacek Kuroń"
        ],
        "example_brands": [
            "UNICEF", "Nivea", "Caritas", "WOŚP", "Pampers", "Volvo", "hospicja"
        ],
        "color_palette": [
            "#B4D6B4", "#A7C7E7", "#FFD580", "#9467BD"
        ],
        "visual_elements": [
            "dłonie", "serce", "koło wspólnoty", "symbol opieki"
        ],
        "keyword_messaging": [
            "Bezpieczeństwo mieszkańców", "Troska", "Wspólnota"
        ],
        "watchword": [
            "Troska i wsparcie dla każdego obywatela."
        ],
        "questions": [
            "Jak pokazujesz troskę i empatię wobec wszystkich mieszkańców?",
            "Jakie realne efekty mają wdrożone przez Ciebie programy pomocowe?",
            "W czym przejawia się Twoja polityka integrująca?",
            "Jak oceniasz skuteczność działań społecznych w mieście?"
        ]
    },
    "Kochanek": {
        "name": "Kochanek / Wielbiciel",
        "tagline": "Bliskość. Relacje. Pasja.",
        "description": (
            "Kochanek w polityce buduje pozytywne relacje z mieszkańcami, jest otwarty, komunikatywny i wzbudza zaufanie. "
            "Politycy Kochankowie podkreślają bliskość, autentyczność i partnerski dialog, sprawiając, że wyborcy czują się zauważeni i docenieni. "
            "Kochanek potrafi zbliżyć do siebie wyborców i sprawić, by czuli się zauważeni oraz docenieni."
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
        "strengths": [
            "empatia", "bliskość", "autentyczność", "pasja"
        ],
        "weaknesses": [
            "nadmierna emocjonalność", "faworyzowanie bliskich grup", "podatność na krytykę"
        ],
        "examples_person": [
            "Justin Trudeau", "Sanna Marin", "Eva Perón", "John F. Kennedy", "Benito Juárez", "François Mitterrand",
            "Aleksandra Dulkiewicz"
        ],
        "example_brands": [
            "Playboy", "Magnum", "Victoria's Secrets", "Alfa Romeo"
        ],
        "color_palette": [
            "#FA709A", "#FEE140", "#FFD6E0", "#FA709A"
        ],
        "visual_elements": [
            "serce", "uśmiech", "gest bliskości"
        ],
        "keyword_messaging": [
            "Relacje", "Bliskość", "Społeczność"
        ],
        "watchword": [
            "Bliskość i pasja w służbie społeczeństwa."
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
            "Używa humoru i autoironii, by rozbrajać napięcia oraz tworzyć wrażenie bliskości z wyborcami."
            "Błazen potrafi rozbawić, rozproszyć atmosferę, ale nigdy nie traci dystansu do siebie i powagi spraw publicznych."
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
        "strengths": [
            "buduje rozpoznawalność", "umie odwrócić uwagę od trudnych tematów", "kreuje wizerunek 'swojskiego' lidera"
        ],
        "weaknesses": [
            "łatwo przekracza granicę powagi", "ryzyko, że wyborcy nie odbiorą go serio"
        ],
        "examples_person": [
            "Boris Johnson", "Silvio Berlusconi", "Janusz Palikot",
        ],
        "example_brands": [
            "Old Spice", "M&M's", "Fanta", "Łomża", "kabarety"
        ],
        "color_palette": [
            "#FFB300", "#FF8300", "#FFD93D", "#F2A93B"
        ],
        "visual_elements": [
            "uśmiech", "czapka błazna", "kolorowe akcenty"
        ],
        "keyword_messaging": [
            "Dystans", "Entuzjazm", "Radość"
        ],
        "watchword": [
            "Rozbraja śmiechem, inspiruje luzem."
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
            "Twórca charakteryzuje się innowacyjnością, kreatywnością i wizją. "
            "Twórcy dążą do budowania nowych rozwiązań i struktur, które odpowiadają na wyzwania przyszłości. Politycy o tym archetypie często podkreślają swoje innowacyjne podejście do rządzenia i zdolność do wprowadzania pozytywnych zmian. "
            "Jako polityk Twórca nie boi się wdrażać oryginalnych, często nieszablonowych strategii."
        ),
        "storyline": (
            "Opowieść Twórcy jest oparta na zmianie, wprowadzaniu kreatywnych rozwiązań oraz inspirowaniu innych do współdziałania dla rozwoju miasta."
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
        "strengths": [
            "innowacyjność", "wizjonerstwo", "kreatywność"
        ],
        "weaknesses": [
            "brak realizmu", "ignorowanie praktycznych ograniczeń", "perfekcjonizm"
        ],
        "examples_person": [
            "Emmanuel Macron", "Tony Blair", "Konrad Adenauer", "Deng Xiaoping", "Mustafa Kemal Atatürk"
        ],
        "example_brands": [
            "Apple", "Lego", "Adobe", "Toyota", "startupy"
        ],
        "color_palette": [
            "#7C53C3", "#3BE8B0", "#87CEEB", "#17BECF"
        ],
        "visual_elements": [
            "kostka Rubika", "żarówka", "kolorowe fale"
        ],
        "keyword_messaging": [
            "Innowacja", "Twórczość", "Wizja rozwoju"
        ],
        "watchword": [
            "Innowacyjne rozwiązania dla współczesnych wyzwań."
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
            "Archetyp Odkrywcy charakteryzuje się ciekawością, poszukiwaniem nowych możliwości i pragnieniem wolności. "
            "Odkrywcy pragną przełamywać granice i eksplorować nieznane terytoria. Politycy o tym archetypie często prezentują się jako wizjonerzy, którzy mogą poprowadzić społeczeństwo ku nowym horyzontom i możliwościom. "
            "Odkrywca poszukuje nowych rozwiązań, jest otwarty na zmiany i śledzi światowe trendy, które wdraża w polityce lokalnej czy krajowej. "
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
        "strengths": [
            "innowacyjność", "adaptacyjność", "odwaga w podejmowaniu ryzyka"
        ],
        "weaknesses": [
            "brak cierpliwości", "trudności z dokończeniem projektów", "ignorowanie tradycji"
        ],
        "examples_person": [
            "Olof Palme", "Shimon Peres", "Theodore Roosevelt", "Jawaharlal Nehru", "Elon Musk"
        ],
        "example_brands": [
            "NASA", "Jeep", "Red Bull", "National Geographic", "The North Face", "Amazon", "Nomadzi"
        ],
        "color_palette": [
            "#43C6DB", "#A0E8AF", "#F9D371", "#E377C2"
        ],
        "visual_elements": [
            "mapa", "kompas", "droga", "lupa"
        ],
        "keyword_messaging": [
            "Odkrywanie", "Nowe horyzonty", "Zmiana"
        ],
        "watchword": [
            "Odkrywanie nowych możliwości dla wspólnego rozwoju."
        ],
        "questions": [
            "Jak zachęcasz do odkrywania nowości w mieście?",
            "Jakie projekty wdrażasz, które nie były jeszcze realizowane w innych miastach?",
            "Jak budujesz wizerunek miasta jako miejsca wolnego od barier?"
        ]
    },
    "Czarodziej": {
        "name": "Czarodziej",
        "tagline": "Transformacja. Inspiracja. Przełom.",
        "description": (
            "Czarodziej w polityce to wizjoner i transformator – wytycza nowy kierunek i inspiruje do zmian niemożliwych na pierwszy rzut oka. "
            "Czarodziej obiecuje głęboką przemianę społeczeństwa i nadaje wydarzeniom niemal magiczny sens. "
            "Dzięki jego inicjatywom miasto przechodzi metamorfozy, w których niemożliwe staje się możliwe."
        ),
        "storyline": (
            "Opowieść Czarodzieja to zmiana wykraczająca poza rutynę, wyobraźnia, inspiracja, a także odwaga w stawianiu pytań i szukaniu odpowiedzi poza schematami."
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
        "strengths": [
            "porywa wielką ideą", "motywuje do zmian", "potrafi łączyć symbole i narracje w spójny mit założycielski"
        ],
        "weaknesses": [
            "oczekiwania mogą przerosnąć realne możliwości", "ryzyko oskarżeń o 'czcze zaklęcia'"
        ],
        "examples_person": [
            "Barack Obama", "Václav Klaus", "Nelson Mandela", "Martin Luther King"
        ],
        "example_brands": [
            "Intel", "Disney", "XBox", "Sony", "Polaroid", "Tesla", "Nowoczesne Miasto"
        ],
        "color_palette": [
            "#8F00FF", "#181C3A", "#E0BBE4", "#7C46C5"
        ],
        "visual_elements": [
            "gwiazda", "iskra", "łuk magiczny"
        ],
        "keyword_messaging": [
            "Zmiana", "Inspiracja", "Możliwość"
        ],
        "watchword": [
            "Zmieniam rzeczywistość w to, co dziś wydaje się niemożliwe."
        ],
        "questions": [
            "Jak pokazujesz mieszkańcom, że niemożliwe jest możliwe?",
            "Jakie innowacje budują wizerunek miasta kreatywnego i nowoczesnego?",
            "Jak inspirujesz społeczność do patrzenia dalej?"
        ]
    },
    "Towarzysz": {
        "name": "Towarzysz / Zwykły Człowiek",
        "tagline": "Wspólnota. Prostota. Bliskość.",
        "description": (
            "Towarzysz w polityce stoi blisko ludzi, jest autentyczny, stawia na prostotę, tworzenie bezpiecznej wspólnoty społecznej oraz zrozumienie codziennych problemów obywateli. "
            "Nie udaje, nie buduje dystansu – jest 'swojakiem', na którym można polegać. "
            "Politycy o tym archetypie podkreślają swoje zwyczajne pochodzenie i doświadczenia, pokazując, że rozumieją troski i aspiracje przeciętnych ludzi. "
            "Ich siłą jest umiejętność budowania relacji i tworzenia poczucia wspólnoty."
        ),
        "storyline": (
            "Opowieść Towarzysza koncentruje się wokół wartości rodzinnych, codziennych wyzwań, pracy od podstaw oraz pielęgnowania lokalnej tradycji."
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
        "strengths": [
            "autentyczność", "empatia", "umiejętność komunikacji z obywatelami"
        ],
        "weaknesses": [
            "brak wizji", "ograniczona perspektywa", "unikanie trudnych decyzji"
        ],
        "examples_person": [
            "Joe Biden", "Bernie Sanders", "Andrzej Duda", "Pedro Sánchez", "Jeremy Corbyn"
        ],
        "example_brands": [
            "Ikea", "Skoda", "Żabka", "Ford", "VW"
        ],
        "color_palette": [
            "#F9F9F9", "#6CA0DC", "#A3C1AD", "#2CA02C"
        ],
        "visual_elements": [
            "dom", "krąg ludzi", "prosta ikona dłoni"
        ],
        "keyword_messaging": [
            "Bliskość", "Razem", "Prostota"
        ],
        "watchword": [
            "Blisko ludzi i ich codziennych spraw."
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
            "Głosi prostą, pozytywną wizję dobra wspólnego i nadziei. "
            "Niewinny buduje zaufanie szczerością i skutecznie apeluje o współpracę dla wspólnego dobra."
        ),
        "storyline": (
            "Opowieść Niewinnego buduje napięcie wokół pozytywnych emocji, odwołuje się do marzeń o lepszym mieście i wiary we wspólny sukces."
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
        "strengths": [
            "łatwo zyskuje zaufanie", "łagodzi polaryzację", "odwołuje się do uniwersalnych wartości."
        ],
        "weaknesses": [
            "może być postrzegany jako naiwny", "trudniej mu prowadzić twarde negocjacje"
        ],
        "examples_person": [
            "Jimmy Carter", "Václav Havel", "Szymon Hołownia"
        ],
        "example_brands": [
            "Dove", "Milka", "Kinder", "Polska Akcja Humanitarna"
        ],
        "color_palette": [
            "#FFF6C3", "#AAC9CE", "#FFF200", "#9BD6F4"
        ],
        "visual_elements": [
            "gołąb", "słońce", "dziecko"
        ],
        "keyword_messaging": [
            "Nadzieja", "Optymizm", "Wspólnie"
        ],
        "watchword": [
            "Uczciwość i nadzieja prowadzą naprzód."
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
            "Buntownik w polityce odważnie kwestionuje zastane układy, nawołuje do zmiany i walczy o nowe, lepsze reguły gry. "
            "Archetyp Buntownika charakteryzuje się odwagą w kwestionowaniu status quo i dążeniem do fundamentalnych zmian. "
            "Buntownicy sprzeciwiają się istniejącym strukturom władzy i konwencjom, proponując radykalne rozwiązania."
            "Politycy o tym archetypie często prezentują się jako outsiderzy, którzy chcą zburzyć skorumpowany system i wprowadzić nowy porządek."
            "Buntownik odważnie kwestionuje zastane układy, nawołuje do zmiany i walczy o nowe, lepsze reguły gry w mieście. "
            "Potrafi ściągnąć uwagę i zjednoczyć mieszkańców wokół śmiałych idei. "
        ),
        "storyline": (
            "Narracja Buntownika podkreśla walkę z niesprawiedliwością i stagnacją, wytykanie błędów władzy i radykalne pomysły na rozwój miasta."
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
        "strengths": [
            "odwaga", "autentyczność", "zdolność inspirowania do zmian"
        ],
        "weaknesses": [
            "nadmierna konfrontacyjność", "brak kompromisu", "trudności w budowaniu koalicji"
        ],
        "examples_person": [
            "Donald Trump", "Marine Le Pen", "Sławomir Mentzen", "Lech Wałęsa", "Aleksiej Nawalny"
        ],
        "example_brands": [
            "Harley Davidson", "Jack Daniel's", "Greenpeace", "Virgin", "Bitcoin"
        ],
        "color_palette": [
            "#000000", "#FF0000", "#FF6F61", "#FF7F0E"
        ],
        "visual_elements": [
            "piorun", "megafon", "odwrócona korona"
        ],
        "keyword_messaging": [
            "Zmiana", "Rewolucja", "Nowe reguły"
        ],
        "watchword": [
            "Rewolucyjne zmiany dla lepszego jutra."
        ],
        "questions": [
            "Jak komunikujesz odwagę i gotowość do zmiany?",
            "Jak mobilizujesz do zrywania z przeszłością?",
            "Co robisz, by mieszkańcy mieli w Tobie rzecznika zmiany?"
        ]
    }
}
# --- KONIEC archetype_extended ---

ARCHE_IMG_URL = "https://justynakopec.pl/wp-content/uploads/2024/08/Archetypy-marki-Justyna-Kopec.png"
ARCHE_NAME_TO_IDX = {n.lower(): i for i, n in enumerate(ARCHE_NAMES_ORDER)}

@st.cache_data
def load_base_arche_img():
    resp = requests.get(ARCHE_IMG_URL, stream=True, timeout=30)
    resp.raise_for_status()
    img = Image.open(io.BytesIO(resp.content)).convert("RGBA")
    return img

def mask_for(idx, color):
    base = load_base_arche_img()
    w, h = base.size
    cx, cy = w//2, h//2
    rad = w//2
    mask = Image.new("RGBA", (w, h), (0,0,0,0))
    draw = ImageDraw.Draw(mask)
    start = -90 + idx*30
    end = start + 30
    draw.pieslice([cx-rad, cy-rad, cx+rad, cy+rad], start, end, fill=color)
    return mask

def compose_archetype_highlight(idx_main, idx_aux=None, idx_supplement=None):
    base = load_base_arche_img().copy()

    # Najpierw poboczny (żeby nakryło go potem żółte/czerwone, jeśli overlap)
    if idx_supplement is not None and idx_supplement not in [idx_main, idx_aux] and idx_supplement < 12:
        mask_supplement = mask_for(idx_supplement, (64,185,0,140))  # zielony półtransparentny
        base.alpha_composite(mask_supplement)

    # Potem wspierający
    if idx_aux is not None and idx_aux != idx_main and idx_aux < 12:
        mask_aux = mask_for(idx_aux, (255,210,47,140))  # żółty
        base.alpha_composite(mask_aux)

    # Na końcu główny (przykrywa wszystko)
    if idx_main is not None:
        mask_main = mask_for(idx_main, (255,0,0,140))  # czerwony
        base.alpha_composite(mask_main)

    return base

@st.cache_data(ttl=30)
def load(study_id=None):
    try:
        conn = psycopg2.connect(
            host=st.secrets["db_host"],
            database=st.secrets["db_name"],
            user=st.secrets["db_user"],
            password=st.secrets["db_pass"],
            port=st.secrets.get("db_port", 5432),
            sslmode="require"
        )

        base_sql = "SELECT created_at, answers FROM public.responses"
        if study_id:
            df = pd.read_sql(base_sql + " WHERE study_id = %s ORDER BY created_at",
                             con=conn, params=(study_id,))
        else:
            df = pd.read_sql(base_sql + " ORDER BY created_at", con=conn)

        conn.close()

        def parse_answers(x):
            if isinstance(x, (list, dict)):
                return x
            try:
                import json
                return json.loads(x)
            except:
                try:
                    return ast.literal_eval(x)
                except:
                    return None

        if "answers" in df.columns:
            df["answers"] = df["answers"].apply(parse_answers)
        return df

    except Exception as e:
        st.warning(f"Błąd podczas ładowania danych: {e}")



@st.cache_data(ttl=30)
def fetch_studies_list():
    conn = psycopg2.connect(
        host=st.secrets["db_host"],
        database=st.secrets["db_name"],
        user=st.secrets["db_user"],
        password=st.secrets["db_pass"],
        port=st.secrets.get("db_port", 5432),
        sslmode="require"
    )
    df = pd.read_sql(
        """
        SELECT id, first_name_nom, first_name_gen,
               last_name_nom,  last_name_gen,
               city_nom, slug
        FROM public.studies
        WHERE COALESCE(is_active, true)
        ORDER BY created_at DESC
        """,
        con=conn
    )
    conn.close()
    return df

def archetype_scores(answers):
    if not isinstance(answers, list) or len(answers) < 48:
        return {k: None for k in archetypes}
    out = {}
    for name, idxs in archetypes.items():
        out[name] = sum(answers[i-1] for i in idxs)
    return out

def archetype_percent(scoresum):
    if scoresum is None:
        return None
    return round(scoresum / 20 * 100, 1)

def pick_top_3_archetypes(archetype_means, archetype_order):
    """
    Zwraca trzy archetypy o najwyższych wynikach, w kolejności zgodnej z archetype_order.
    """
    # Sortuj po wartości malejąco, a przy remisie wg porządku archetype_order
    sorted_archetypes = sorted(
        archetype_means.items(),
        key=lambda kv: (-kv[1], archetype_order.index(kv[0]))
    )
    main_type = sorted_archetypes[0][0] if len(sorted_archetypes) > 0 else None
    aux_type = sorted_archetypes[1][0] if len(sorted_archetypes) > 1 else None
    supplement_type = sorted_archetypes[2][0] if len(sorted_archetypes) > 2 else None
    return main_type, aux_type, supplement_type

def add_image(paragraph, img, width):
    # img może być ścieżką lub BytesIO/file-like
    if img is None:
        return
    run = paragraph.add_run()
    try:
        if isinstance(img, (str, os.PathLike)) and os.path.exists(img):
            run.add_picture(img, width=width)
        elif hasattr(img, "read"):
            img.seek(0)
            run.add_picture(img, width=width)
    except Exception:
        pass

from docxtpl import DocxTemplate, InlineImage
from docx.shared import Mm
from io import BytesIO
import os

TEMPLATE_PATH = "ap48_raport_template.docx"

def build_word_context(
    main_type, second_type, supplement_type, features, main, second, supplement,
    mean_scores=None, radar_image=None, archetype_table=None, num_ankiet=None
):
    COLOR_NAME_MAP = {
        "#000000": "Czerń",
        "#FFD700": "Złoto",
        "#282C34": "Granat (antracyt)",
        "#800020": "Burgund",
        "#E10600": "Czerwień",
        "#2E3141": "Grafitowy granat",
        "#FFFFFF": "Biel",
        "#4682B4": "Stalowy błękit",
        "#B0C4DE": "Jasny niebieskoszary",
        "#6C7A89": "Popielaty szary",
        "#B4D6B4": "Miętowa zieleń",
        "#A7C7E7": "Pastelowy błękit",
        "#FFD580": "Pastelowy żółty / beżowy",
        "#FA709A": "Róż malinowy",
        "#FEE140": "Jasny żółty",
        "#FFD6E0": "Bardzo jasny róż",
        "#FFB300": "Mocna żółć",
        "#FF8300": "Pomarańcz",
        "#FFD93D": "Pastelowa żółć",
        "#7C53C3": "Fiolet",
        "#3BE8B0": "Miętowy cyjan",
        "#87CEEB": "Błękit (Sky Blue)",
        "#43C6DB": "Turkusowy błękit",
        "#A0E8AF": "Seledyn",
        "#F9D371": "Złocisty żółty",
        "#8F00FF": "Fiolet (intensywny)",
        "#181C3A": "Granat bardzo ciemny",
        "#E0BBE4": "Pastelowy fiolet",
        "#F9F9F9": "Biel bardzo jasna",
        "#6CA0DC": "Pastelowy błękit",
        "#A3C1AD": "Pastelowa zieleń",
        "#FFF6C3": "Jasny kremowy",
        "#AAC9CE": "Pastelowy niebieskoszary",
        "#FFF200": "Żółty (cytrynowy)",
        "#FF0000": "Czerwień intensywna",
        "#FF6F61": "Łososiowy róż",
        "#8C564B": "Ciemy brąz",
        "#D62728": "Czerwień karmazynowa",
        "#1F77B4": "Chabrowy",
        "#9467BD": "Fiolet śliwkowy",
        "#F2A93B": "Miodowy żółty",
        "#17BECF": "Niebieski morski",
        "#E377C2": "Pastelowy róż fioletowy",
        "#7C46C5": "Fiolet szafirowy",
        "#2CA02C": "Zieleń trawiasta",
        "#9BD6F4": "Pastelowy błękit jasny",
        "#FF7F0E": "Jaskrawy pomarańcz",
        # Dodaj kolejne w razie potrzeby
    }

    def person_links_html(person_list):
        if not person_list:
            return ""
        return ', '.join(person_link(name) for name in person_list)

    def person_links_plain(person_list):
        return person_list  # czysta lista nazwisk, bez HTML

    def kolor_label_list(palette):
        if not isinstance(palette, list):
            return ""
        out = []
        for code in palette:
            name = COLOR_NAME_MAP.get(code.upper(), code)
            out.append(f"{name} ({code})")
        return ', '.join(out)

    context = {
        "TYTUL": "Raport Archetypów",
        "IMIE_NAZWISKO": personGen,
        "AUTOR": "Piotr Stec",
        "DATA": datetime.now().strftime("%Y-%m-%d"),
        "WSTEP": zapobiegaj_wdowie(
            "Archetypy to uniwersalne wzorce osobowości, które od wieków pomagają ludziom rozumieć świat i budować autentyczną tożsamość. "
            "Współczesna psychologia i marketing potwierdzają, że trafnie zdefiniowany archetyp jest potężnym narzędziem komunikacji, pozwalającym budować rozpoznawalność, zaufanie i emocjonalny kontakt. Czas wykorzystać to także w polityce! "
            "\n\nW polityce archetyp pomaga wyeksponować najważniejsze cechy lidera, porządkuje przekaz, wzmacnia spójność strategii oraz wyraźnie różnicuje kandydata na tle konkurencji. "
            "Analiza archetypów pozwala lepiej zrozumieć sposób odbioru polityka przez otoczenie, a co się z tym wiąże także motywacje i aspiracje. "
            "Wyniki badań archetypowych stanowią istotny fundament do tworzenia skutecznej narracji wyborczej, strategii wizerunkowej i komunikacji z wyborcami.\n\n"
            "W modelu przez nas opracowanym wykorzystano klasyfikację Mark and Pearson, obejmującą 12 uniwersalnych typów osobowościowych. "
            "Raport przedstawia wyniki i profil archetypowy dla Marcina Gołka w oparciu o dane z przeprowadzonego badania. "
            "Badanie to pozwoliło zidentyfikować archetyp główny i wspierający, a więc dwa najważniejsze wzorce, które mogą wzmocnić jego pozycjonowanie w walce o urząd Prezydenta Poznania. Zaprezentowano także trzeci w kolejności ważności - archetyp poboczny.\n\n"
            "Dzięki analizie archetypów można precyzyjnie dopasować komunikację do oczekiwań wyborców, podkreślić atuty, a także przewidzieć skuteczność strategii politycznej w dynamicznym środowisku publicznym. "
        ),
        "TABELA_LICZEBNOSCI": archetype_table.to_dict('records') if archetype_table is not None else [],
        "RADAR_IMG": radar_image if radar_image is not None else "",
        # --- NOWOŚĆ: liczebność osób ---
        "LICZEBNOSC_OSOB": (
            f"W badaniu udział wzięło {num_ankiet} {'osób' if (num_ankiet is None or num_ankiet != 1) else 'osoba'}."
            if num_ankiet is not None else ""
        ),
        # --- GŁÓWNY ARCHETYP ---
        "ARCHETYPE_MAIN_NAME": main.get("name") or "",
        "ARCHETYPE_MAIN_TAGLINE": main.get("tagline") or "",
        "ARCHETYPE_MAIN_DESC": main.get("description") or "",
        "ARCHETYPE_MAIN_STORYLINE": main.get("storyline") or "",
        "ARCHETYPE_MAIN_TRAITS": main.get("core_traits") or [],
        "ARCHETYPE_MAIN_STRENGTHS": main.get("strengths") or [],
        "ARCHETYPE_MAIN_WEAKNESSES": main.get("weaknesses") or [],
        "ARCHETYPE_MAIN_RECOMMENDATIONS": main.get("recommendations") or [],
        "ARCHETYPE_MAIN_POLITICIANS": person_links_plain(main.get("examples_person", [])),
        "ARCHETYPE_MAIN_BRANDS_IMG": [],
        "ARCHETYPE_MAIN_COLORS": main.get("color_palette") or [],
        "ARCHETYPE_MAIN_COLORS_LABEL": kolor_label_list(main.get("color_palette", [])),
        "ARCHETYPE_MAIN_VISUALS": main.get("visual_elements") or [],
        "ARCHETYPE_MAIN_KEYWORDS": main.get("keyword_messaging") or [],
        "ARCHETYPE_MAIN_SLOGANS": main.get("watchword") or [],
        "ARCHETYPE_MAIN_QUESTIONS": main.get("questions") or [],
        # --- ARCHETYP WSPIERAJĄCY ---
        "ARCHETYPE_AUX_NAME": second.get("name") or "",
        "ARCHETYPE_AUX_TAGLINE": second.get("tagline") or "",
        "ARCHETYPE_AUX_DESC": second.get("description") or "",
        "ARCHETYPE_AUX_STORYLINE": second.get("storyline") or "",
        "ARCHETYPE_AUX_TRAITS": second.get("core_traits") or [],
        "ARCHETYPE_AUX_STRENGTHS": second.get("strengths") or [],
        "ARCHETYPE_AUX_WEAKNESSES": second.get("weaknesses") or [],
        "ARCHETYPE_AUX_RECOMMENDATIONS": second.get("recommendations") or [],
        "ARCHETYPE_AUX_POLITICIANS": person_links_plain(second.get("examples_person", [])),
        "ARCHETYPE_AUX_BRANDS_IMG": [],
        "ARCHETYPE_AUX_COLORS": second.get("color_palette") or [],
        "ARCHETYPE_AUX_COLORS_LABEL": kolor_label_list(second.get("color_palette", [])),
        "ARCHETYPE_AUX_VISUALS": second.get("visual_elements") or [],
        "ARCHETYPE_AUX_KEYWORDS": second.get("keyword_messaging") or [],
        "ARCHETYPE_AUX_SLOGANS": second.get("watchword") or [],
        "ARCHETYPE_AUX_QUESTIONS": second.get("questions") or [],
        # --- ARCHETYP POBOCZNY ---
        "ARCHETYPE_SUPPLEMENT_NAME": supplement.get("name") or "",
        "ARCHETYPE_SUPPLEMENT_TAGLINE": supplement.get("tagline") or "",
        "ARCHETYPE_SUPPLEMENT_DESC": supplement.get("description") or "",
        "ARCHETYPE_SUPPLEMENT_STORYLINE": supplement.get("storyline") or "",
        "ARCHETYPE_SUPPLEMENT_TRAITS": supplement.get("core_traits") or [],
        "ARCHETYPE_SUPPLEMENT_STRENGTHS": supplement.get("strengths") or [],
        "ARCHETYPE_SUPPLEMENT_WEAKNESSES": supplement.get("weaknesses") or [],
        "ARCHETYPE_SUPPLEMENT_RECOMMENDATIONS": supplement.get("recommendations") or [],
        "ARCHETYPE_SUPPLEMENT_POLITICIANS": person_links_plain(supplement.get("examples_person", [])),
        "ARCHETYPE_SUPPLEMENT_BRANDS_IMG": [],
        "ARCHETYPE_SUPPLEMENT_COLORS": supplement.get("color_palette") or [],
        "ARCHETYPE_SUPPLEMENT_COLORS_LABEL": kolor_label_list(supplement.get("color_palette", [])),
        "ARCHETYPE_SUPPLEMENT_VISUALS": supplement.get("visual_elements") or [],
        "ARCHETYPE_SUPPLEMENT_KEYWORDS": supplement.get("keyword_messaging") or [],
        "ARCHETYPE_SUPPLEMENT_SLOGANS": supplement.get("watchword") or [],
        "ARCHETYPE_SUPPLEMENT_QUESTIONS": supplement.get("questions") or [],
    }

    return context

def export_word_docxtpl(
    main_type,
    second_type,
    supplement_type,
    features,
    main,
    second,
    supplement,
    mean_scores=None,
    radar_img_path=None,
    archetype_table=None,
    num_ankiet=None,
    panel_img_path=None
):

    doc = DocxTemplate(TEMPLATE_PATH)

    # Radar image
    if radar_img_path and os.path.exists(radar_img_path):
        radar_image = InlineImage(doc, radar_img_path, width=Mm(150))
    else:
        radar_image = ""

    # Panel image
    panel_image = InlineImage(doc, panel_img_path, width=Mm(140)) if panel_img_path and os.path.exists(panel_img_path) else ""

    # UWAGA: przekazujemy wszystkie 3 archetypy
    context = build_word_context(
        main_type, second_type, supplement_type, features, main, second, supplement,
        mean_scores, radar_image, archetype_table, num_ankiet
    )

    # Najważniejsze! Przekaż doc do build_brands_for_word!
    context["ARCHETYPE_MAIN_BRANDS_IMG"] = build_brands_for_word(doc, main.get("example_brands", []), logos_dir=logos_dir, height_mm=7)
    context["ARCHETYPE_AUX_BRANDS_IMG"] = build_brands_for_word(doc, second.get("example_brands", []), logos_dir=logos_dir, height_mm=7)
    context["ARCHETYPE_SUPPLEMENT_BRANDS_IMG"] = build_brands_for_word(doc, supplement.get("example_brands", []), logos_dir=logos_dir, height_mm=7)

    context["PANEL_IMG"] = panel_image

    doc.render(context)

    # --- TU WSTAW PĘTLĘ PODMIENIAJĄCĄ NAZWISKA NA LINKI ---
    for para in doc.paragraphs:
        for name, url in person_wikipedia_links.items():
            if name in para.text:
                para.clear()
                add_hyperlink(para, name, url)

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


def word_to_pdf(docx_bytes_io):
    import sys
    import tempfile, os
    from io import BytesIO
    with tempfile.TemporaryDirectory() as tmpdir:
        docx_path = os.path.join(tmpdir, "raport.docx")
        pdf_path = os.path.join(tmpdir, "raport.pdf")
        with open(docx_path, "wb") as f:
            f.write(docx_bytes_io.getbuffer())
        if sys.platform.startswith("win32"):
            import pythoncom
            from docx2pdf import convert
            pythoncom.CoInitialize()     # ← TU!
            convert(docx_path, pdf_path)
        else:
            import subprocess
            result = subprocess.run([
                "soffice", "--headless", "--convert-to", "pdf", "--outdir", tmpdir, docx_path
            ], capture_output=True)
            if result.returncode != 0 or not os.path.isfile(pdf_path):
                raise RuntimeError("LibreOffice PDF error: " + result.stderr.decode())
        with open(pdf_path, "rb") as f:
            return BytesIO(f.read())


def is_color_dark(color_hex):
    if color_hex is None:
        return False
    if not color_hex.startswith('#') or len(color_hex) not in (7, 4):
        return False
    h = color_hex.lstrip('#')
    if len(h) == 3:
        h = ''.join([c*2 for c in h])
    r, g, b = tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    lum = 0.2126*r + 0.7152*g + 0.0722*b
    return lum < 110

import base64

def build_brand_icons_html(brand_names, logos_dir):
    import os
    html = '<div style="display:flex;flex-wrap:wrap;gap:18px 26px;align-items:center;margin-top:6px;margin-bottom:8px;">'
    for brand in brand_names:
        path = get_logo_svg_path(brand, logos_dir)
        if path and os.path.exists(path):
            with open(path, "rb") as f:
                svg_code = f.read().decode("utf-8", errors="replace")
            svg_b64 = base64.b64encode(svg_code.encode("utf-8")).decode("ascii")
            svg_img_tag = f'<img src="data:image/svg+xml;base64,{svg_b64}" alt="{brand}" style="height:32px;vertical-align:middle;margin-right:5px;">'
            html += f'<span title="{brand}" style="display:flex;flex-direction:column;align-items:center;min-width:55px;"><span>{svg_img_tag}</span><span style="font-size:0.93em; margin-top:1px;">{brand}</span></span>'
        else:
            html += f'<span style="font-size:1.05em;color:#aaa;margin-right:15px;">{brand}</span>'
    html += '</div>'
    return html

def person_links_html(person_list):
    if not person_list:
        return ""
    return ', '.join(person_link(name) for name in person_list)


def render_archetype_card(archetype_data, main=True, supplement=False):
    if not archetype_data:
        st.warning("Brak danych o archetypie.")
        return

    # Style zależne od typu archetypu

    if supplement:
        border_color = "#40b900"  # zielony, np. uzupełniający
        bg_color = "#F6FFE6"  # jasny zielony tła uzupełniającego
        tagline_color = "#40b900"
        box_shadow = f"0 3px 14px 0 {border_color}44"

    elif main:
        border_color = archetype_data.get('color_palette', ['#E99836'])[0]
        bg_color = archetype_data.get('color_palette', ['#FFF', '#FAFAFA'])[1] if len(
            archetype_data.get('color_palette', [])) > 1 else "#FFF8F0"

        def is_light(color):
            # color jako hex string #RRGGBB
            if color.startswith('#'):
                color = color[1:]
            if len(color) != 6:
                return True  # domyślnie traktuj błędny hex jako jasny
            r, g, b = int(color[0:2], 16), int(color[2:4], 16), int(color[4:6], 16)
            return (r * 299 + g * 587 + b * 114) / 1000 > 180

        # Obsługa specjalnego koloru dla Opiekuna:
        name = archetype_data.get('name', '').strip().lower()
        if name == 'opiekun':
            tagline_color = '#145A32'  # CIEMNOZIELONY tylko dla Opiekuna
        elif not is_light(bg_color):
            tagline_color = "#222222"  # mocny kontrast, jeżeli tło ciemne
        else:
            tagline_color = border_color

        box_shadow = f"0 4px 14px 0 {border_color}44"

    else:
        border_color = archetype_data.get('color_palette', ['#FFD22F'])[0]
        bg_color = "#FAFAFA"
        tagline_color = border_color
        box_shadow = f"0 2px 6px 0 {border_color}22"

    tagline = archetype_data.get('tagline', '')

    if (archetype_data.get('name', '').strip().lower() == 'niewinny') and not main:
        tagline = "Niesie nadzieję, inspiruje do współpracy, buduje zaufanie szczerością i apeluje o wspólne dobro, otwarcie komunikuje pozytywne wartości."

    def normalize_symbol(name):
        return str(name).strip().title() if isinstance(name, str) else name

    symbol_emoji = {
        "Korona": "👑",
        "Herb Miasta": "🛡️",
        "Peleryna": "🦸",
        "Serce": "❤️",
        "Uśmiech": "🤪",
        "Dłonie": "🤝",
        "Księga": "📖",
        "Mapa": "🗺️",
        "Gwiazda": "⭐",
        "Gołąb": "🕊️",
        "Piorun": "🔥",
        "Kostka Rubika": "🧩",
        "Dom": "🏡",
        "Czapka błazna": "🎩",
        "Krąg ludzi": "🫂",
        "Żarówka": "💡",
        "Kolorowe fale": "🌊",
        "Koło wspólnoty": "⭕",
        "Sygnet": "💍",
        "Monogram": "🔠",
        "Iskra": "✨",
        "Podniesiona dłoń": "✋",
        "Tarcza": "🛡️",
        "Aura odwagi": "🦁",
        "Okulary": "📖",
        "Lupa": "🔍",
        "Droga": "🛣️",
        "Prosta ikona dłoni": "🫱",
        "Dziecko": "🧒",
        "Słońce": "☀️"
    }

    # symbol musi być stringiem!
    symbol = archetype_data.get('visual_elements', [''])[0] if archetype_data.get('visual_elements') else ""
    icon = symbol_emoji.get(normalize_symbol(symbol), "🔹")

    width_card = "70vw"
    text_color = "#222"
    if main and is_color_dark(bg_color):
        text_color = "#fff"
        tagline_color = "#FFD22F" if archetype_data.get('name', '').lower() == "bohater" else "#fffbea"

    color_palette = archetype_data.get('color_palette', [])
    color_names = [COLOR_NAME_MAP.get(c.upper(), c).lower() for c in color_palette] if color_palette else []
    color_icons_html = ""
    if color_palette and isinstance(color_palette, list):
        color_icons_html = ''.join(
            f'<span style="display:inline-block;width:23px;height:23px;border-radius:50%;background:{c};margin-right:6px;border:2px solid #222;vertical-align:middle;"></span>'
            for c in color_palette
        )
    color_desc_html = ""
    if color_palette and isinstance(color_palette, list) and color_names:
        color_items = [f"{n} ({h})" for n, h in zip(color_names, color_palette)]
        color_desc_html = f'<div style="color:{text_color};font-size:0.98em;margin-top:3px;margin-bottom:7px;">' + ', '.join(
            color_items) + '</div>'

    questions = archetype_data.get('questions', [])
    questions_html = ""
    if questions and isinstance(questions, list):
        questions_html = "<ul style='margin-left:20px;margin-top:5px;'>"
        for q in questions:
            questions_html += f"<li style='margin-bottom:3px; font-size:1.07em;'>{q}</li>"
        questions_html += "</ul>"

    strengths = archetype_data.get('strengths', [])
    weaknesses = archetype_data.get('weaknesses', [])
    strengths_html = "" if not strengths else (
            "<div style='padding-left:24px;'>" +
            ''.join(
                "<div style='display:flex; align-items:center; margin-bottom:4px;'>"
                "<span style='color: green !important; font-size:1.14em; margin-right:9px; vertical-align:middle;'>✅</span>"
                f"<span style='font-size:1.07em; color:{text_color}'>{s[0].lower() + s[1:]}</span>"
                "</div>"
                for s in strengths
            ) + "</div>"
    )
    weaknesses_html = "" if not weaknesses else (
            "<div style='padding-left:24px;'>" +
            ''.join(
                "<div style='display:flex; align-items:center; margin-bottom:4px;'>"
                "<span style='color:#d32f2f !important; font-size:1.02em; margin-right:9px; vertical-align:middle;'>❌</span>"
                f"<span style='font-size:1.07em; color:{text_color}'>{w[0].lower() + w[1:]}</span>"
                "</div>"
                for w in weaknesses
            ) + "</div>"
    )

    watchword = archetype_data.get('watchword', [])
    watchword_html = ""
    if watchword and isinstance(watchword, list) and watchword[0].strip():
        watchword_html = (
            "<div style='margin-top:24px;font-weight:600;'>Slogan:</div>"
            f"<div style='margin-bottom:8px; margin-top:4px;'>{watchword[0]}</div>"
        )

    def smart_list(lst):
        return ', '.join(
            [lst[0][0].upper() + lst[0][1:]] +
            [x[0].lower() + x[1:] if x else "" for x in lst[1:]]
        ) if lst else ""

    traits_str = smart_list(archetype_data.get('core_traits', []))
    keywords_str = smart_list(archetype_data.get('keyword_messaging', []))
    visuals_str = smart_list(archetype_data.get('visual_elements', []))

    st.markdown(f"""
        <div style="
            max-width:{width_card};
            border: 3px solid {border_color};
            border-radius: 20px;
            background: {bg_color};
            box-shadow: {box_shadow};
            padding: 2.1em 2.2em 1.3em 2.2em;
            margin-bottom: 32px;
            color: {text_color};
            display: flex; align-items: flex-start;">
            <div style="font-size:2.6em; margin-right:23px; margin-top:1px; flex-shrink:0;">{icon}</div>
            <div>
                <div style="font-size:2.15em;font-weight:bold; line-height:1.08; margin-top:20px; margin-bottom:15px; color:{text_color};">
                    {archetype_data.get('name', '?')}
                </div>
                <div style="font-size:1.3em; font-style:italic; color:{tagline_color}; margin-bottom:38px; margin-top:4px;">
                    {tagline}
                </div>
                <div style="margin-top:21px; font-size:1.07em;">
                    <b>Opis:</b><br>
                    <span style="font-weight:400 !important;">
                        <i>{archetype_data.get('description', '')}</i>
                    </span>
                </div>
                <div style="color:{text_color};font-size:1.07em; margin-top:21px;">
                    <b>Cechy:</b> <span style="font-weight:400;">{traits_str}</span>
                </div>
                <div style="margin-top:24px;font-weight:600;">Storyline:</div>
                <div style="margin-bottom:9px; margin-top:4px; font-size:1.07em;">{archetype_data.get('storyline', '')}</div>
                <div style="margin-top:16px;font-weight:600;">Atuty:</div>
                {strengths_html if strengths_html else '<div style="color:#888; padding-left:24px;">-</div>'}
                <div style="margin-top:2px;font-weight:600;">Słabości:</div>
                {weaknesses_html if weaknesses_html else '<div style="color:#888; padding-left:24px;">-</div>'}
                <div style="margin-top:24px;font-weight:600;">Rekomendacje:</div>
                <ul style="padding-left:24px; margin-bottom:9px;">
                     {''.join(f'<li style="margin-bottom:2px; font-size:1.07em;">{r}</li>' for r in archetype_data.get('recommendations', []))}
                </ul>
                <div style="margin-top:29px;font-weight:600;">Słowa kluczowe:</div>
                <div style="margin-bottom:8px;">{keywords_str}</div>
                <div style="margin-top:24px;font-weight:600;">Elementy wizualne:</div>
                <div style="margin-bottom:8px;">{visuals_str}</div>
                {('<div style="margin-top:24px;font-weight:600;">Przykłady polityków:</div>'
                  '<div style="margin-bottom:8px;">' +
                  ', '.join(person_link(name) for name in archetype_data.get('examples_person', [])) +
                  '</div>')}
                <div style="margin-bottom:10px; margin-top:24px;font-weight:600;">Przykłady marek/organizacji:</div>
                {build_brand_icons_html(archetype_data.get('example_brands', []), logos_dir)}
                {watchword_html}
                {"<div style='margin-top:32px;font-weight:600;'>Kolory:</div>" if color_palette else ""}
                {"<div style='margin-bottom:2px; margin-top:7px;'>" + color_icons_html + "</div>" if color_icons_html else ""}
                {color_desc_html}
                {"<div style='margin-top:22px;font-weight:600;'>Pytania archetypowe:</div>" if questions else ""}
                {questions_html}
            </div>
        </div>
    """, unsafe_allow_html=True)

# ============ RESZTA PANELU: nagłówki, kolumny, eksporty, wykres, tabele respondentów ============

# ── WYBÓR BADANIA / OSOBY ──────────────────────────────────────────────
studies_df = fetch_studies_list()
if studies_df.empty:
    st.warning("Brak badań w bazie.")
    st.stop()

labels = [
    f"{row.first_name_nom} {row.last_name_nom} ({row.city_nom}) – /{row.slug}"
    for _, row in studies_df.iterrows()
]
sel = st.selectbox("Wybierz osobę/JST", options=labels)
sel_row = studies_df.iloc[labels.index(sel)]

personNom = f"{sel_row.first_name_nom} {sel_row.last_name_nom}"
personGen = f"{sel_row.first_name_gen} {sel_row.last_name_gen}"
study_id = sel_row.id


data = load(study_id)
num_ankiet = len(data) if not data.empty else 0

header_col1, header_col2 = st.columns([0.77, 0.23])
with header_col1:
    st.markdown("""
    <div style="font-size:2.3em; font-weight:bold; background:#1a93e3; color:#fff; 
        padding:14px 32px 10px 24px; border-radius:2px; width:fit-content; display:inline-block;">
        Archetypy Marcina Gołka – panel administratora
    </div>
    """, unsafe_allow_html=True)
with header_col2:
    st.markdown(f"""
    <div style="display:flex;align-items:center;justify-content:flex-end;height:100%;"><div style="font-size:1.23em;text-align:right;background:#f3f3fa;padding:12px 29px 8px 29px; border-radius:17px; border:2px solid #d1d9ed;color:#195299;font-weight:600;box-shadow:0 2px 10px 0 #b5c9e399;">
        <span style="font-size:1.8em;font-weight:bold;">{num_ankiet}</span><br/>uczestników badania
    </div></div>
    """, unsafe_allow_html=True)

st.markdown("""
<hr style="height:1.3px;background:#eaeaec; margin-top:1.8em; margin-bottom:3.8em; border:none;" />
""", unsafe_allow_html=True)

# --- Analiza respondentów i agregacja ---

if "answers" in data.columns and not data.empty:

    results = []

    for idx, row in data.iterrows():

        if not isinstance(row.get("answers", None), list):
            continue

        arcsums = archetype_scores(row["answers"])
        arcper = {k: archetype_percent(v) for k, v in arcsums.items()}

        main_type, second_type, supplement_type = pick_top_3_archetypes(arcsums, ARCHE_NAMES_ORDER)
        main = archetype_extended.get(main_type, {})
        second = archetype_extended.get(second_type, {}) if second_type != main_type else {}
        supplement = archetype_extended.get(supplement_type, {}) if supplement_type not in [main_type, second_type] else {}

        czas_ankiety = ""
        if pd.notna(row.get("created_at", None)):
            try:
                czas_ankiety = row["created_at"].astimezone(pytz.timezone('Europe/Warsaw')).strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                czas_ankiety = row["created_at"].strftime('%Y-%m-%d %H:%M:%S')

        results.append({
            "Czas ankiety": czas_ankiety,
            **arcsums,
            **{f"{k}_%": v for k, v in arcper.items()},
            "Główny archetyp": main_type,
            "Cechy kluczowe": archetype_features.get(main_type, ""),
            "Opis": main.get("description", ""),
            "Storyline": main.get("storyline", ""),
            "Rekomendacje": "\n".join(main.get("recommendations", [])),
            "Archetyp wspierający": second_type if second_type != main_type else "",
            "Cechy wspierający": archetype_features.get(second_type, "") if second_type != main_type else "",
            "Opis wspierający": second.get("description", "") if second_type != main_type else "",
            "Storyline wspierający": second.get("storyline", "") if second_type != main_type else "",
            "Rekomendacje wspierający": "\n".join(second.get("recommendations", [])) if second_type != main_type else "",
            "Archetyp poboczny": supplement_type if supplement_type not in [main_type, second_type] else "",
            "Cechy poboczny": archetype_features.get(supplement_type, "") if supplement_type not in [main_type, second_type] else "",
            "Opis poboczny": supplement.get("description", "") if supplement_type not in [main_type, second_type] else "",
            "Storyline poboczny": supplement.get("storyline", "") if supplement_type not in [main_type, second_type] else "",
            "Rekomendacje poboczny": "\n".join(supplement.get("recommendations", [])) if supplement_type not in [main_type, second_type] else "",
        })

    results_df = pd.DataFrame(results)

    if not results_df.empty and "Czas ankiety" in results_df.columns:

        results_df = results_df.sort_values("Czas ankiety", ascending=True)

        st.markdown('<div style="font-size:2.1em;font-weight:600;margin-bottom:22px;">Informacje na temat archetypów Marcina Gołka</div>', unsafe_allow_html=True)

        archetype_names = ARCHE_NAMES_ORDER

        counts_main = results_df['Główny archetyp'].value_counts().reindex(archetype_names, fill_value=0)
        counts_aux = results_df['Archetyp wspierający'].value_counts().reindex(archetype_names, fill_value=0)

        mean_archetype_scores = {k: results_df[k].mean() if k in results_df.columns else 0 for k in archetype_names}

        main_type, second_type, supplement_type = pick_top_3_archetypes(mean_archetype_scores, archetype_names)
        main = archetype_extended.get(main_type, {})
        second = archetype_extended.get(second_type, {}) if second_type != main_type else {}
        supplement = archetype_extended.get(supplement_type, {}) if supplement_type not in [main_type, second_type] else {}

        col1, col2, col3 = st.columns([0.23, 0.40, 0.42], gap="small")

        with col1:
            st.markdown('<div style="font-size:1.3em;font-weight:600;margin-bottom:13px;">Liczebność archetypów głównych, wspierających i pobocznych</div>', unsafe_allow_html=True)
            archetype_table = pd.DataFrame({
                "Archetyp": [f"{get_emoji(n)} {n}" for n in archetype_names],
                "Główny archetyp": [zero_to_dash(counts_main.get(normalize(k), 0)) for k in archetype_names],
                "Wspierający archetyp": [zero_to_dash(counts_aux.get(normalize(k), 0)) for k in archetype_names],
                "Poboczny archetyp": [
                    zero_to_dash(
                        results_df['Archetyp poboczny'].map(normalize)
                        .value_counts().reindex(archetype_names, fill_value=0).get(normalize(k), 0)
                    ) for k in archetype_names
                ]
            })
            archetype_table_html = archetype_table.to_html(escape=False, index=False)
            archetype_table_html = archetype_table_html.replace('<th>', '<th style="text-align:center">')
            archetype_table_html = archetype_table_html.replace('<td>', '<td style="text-align:center">')
            def align_first_column_to_left_with_width(html):
                html = re.sub(
                    r'(<tr[^>]*>)(\s*<td style="text-align:center">)',
                    lambda m: m.group(1) + m.group(2).replace('text-align:center', 'text-align:left;width:24%;'), html
                )
                html = html.replace(
                    '<th style="text-align:center">Archetyp</th>',
                    '<th style="text-align:center;width:24%;">Archetyp</th>'
                ).replace(
                    '<th style="text-align:center">Główny archetyp</th>',
                    '<th style="text-align:center;width:18%;">Główny archetyp</th>'
                ).replace(
                    '<th style="text-align:center">Wspierający archetyp</th>',
                    '<th style="text-align:center;width:18%;">Wspierający archetyp</th>'
                ).replace(
                    '<th style="text-align:center">Poboczny archetyp</th>',
                    '<th style="text-align:center;width:18%;">Poboczny archetyp</th>'
                )
                html = re.sub(
                    r'<tr>(\s*<td style="[^"]*left;?[^"]*">.*?</td>)'
                    r'(\s*<td style="text-align:center">)',
                    r'<tr>\1<td style="text-align:center;width:18%">', html
                )
                html = re.sub(
                    r'(<td style="text-align:center;width:18%">.*?</td>)'
                    r'(\s*<td style="text-align:center">)',
                    r'\1<td style="text-align:center;width:18%">', html
                )
                return html
            archetype_table_html = align_first_column_to_left_with_width(archetype_table_html)
            archetype_table_html = archetype_table_html.replace(
                '<table ',
                '<table style="margin-left:0px;margin-right:0px;width:99%;" '
            )
            st.markdown(archetype_table_html, unsafe_allow_html=True)

        with col2:
            theta_labels = []
            for n in archetype_names:
                if n == main_type:
                    theta_labels.append(f"<b><span style='color:red;'>{n}</span></b>")
                elif n == second_type:
                    theta_labels.append(f"<b><span style='color:#FFD22F;'>{n}</span></b>")
                elif n == supplement_type:
                    theta_labels.append(f"<b><span style='color:#40b900;'>{n}</span></b>")
                else:
                    theta_labels.append(f"<span style='color:#656565;'>{n}</span>")
            highlight_r = []
            highlight_marker_color = []
            for i, name in enumerate(archetype_names):
                if name == main_type:
                    highlight_r.append(mean_archetype_scores[name])
                    highlight_marker_color.append("red")
                elif name == second_type:
                    highlight_r.append(mean_archetype_scores[name])
                    highlight_marker_color.append("#FFD22F")
                elif name == supplement_type:
                    highlight_r.append(mean_archetype_scores[name])
                    highlight_marker_color.append("#40b900")
                else:
                    highlight_r.append(None)
                    highlight_marker_color.append("rgba(0,0,0,0)")
            st.markdown('<div style="font-size:1.3em;font-weight:600;margin-bottom:13px; text-align:center;">Profil archetypów Marcina Gołka</div>', unsafe_allow_html=True)
            fig = go.Figure(
                data=[
                    go.Scatterpolar(
                        r=list(mean_archetype_scores.values()) + [list(mean_archetype_scores.values())[0]],
                        theta=archetype_names + [archetype_names[0]],
                        fill='toself',
                        name='Średnia wszystkich',
                        line=dict(color="royalblue", width=3),
                        marker=dict(size=6)
                    ),
                    go.Scatterpolar(
                        r=highlight_r,
                        theta=archetype_names,
                        mode='markers',
                        marker=dict(size=18, color=highlight_marker_color, opacity=0.95, line=dict(color="black", width=2)),
                        name='Archetyp główny/wspierający/poboczny',
                        showlegend=False,
                    )
                ],
                layout=go.Layout(
                    polar=dict(
                        radialaxis=dict(visible=True, range=[0, 20]),
                        angularaxis=dict(tickfont=dict(size=19), tickvals=archetype_names, ticktext=theta_labels)
                    ),
                    width=550, height=550,
                    margin=dict(l=20, r=20, t=32, b=32),
                    showlegend=False
                )
            )
            fig.write_image("radar.png", scale=4)
            st.plotly_chart(fig, use_container_width=True)

        # ... (tabela w col1, radar w col2, diagram w col3)

            st.markdown("""
            <div style="display:flex;justify-content:center;align-items:center;margin-top:12px;margin-bottom:10px;">
              <span style="display:flex;align-items:center;margin-right:34px;">
                <span style="width:21px;height:21px;border-radius:50%;background:red;border:2px solid black;display:inline-block;margin-right:8px;"></span>
                <span style="font-size:0.85em;">Archetyp główny</span>
              </span>
              <span style="display:flex;align-items:center;margin-right:34px;">
                <span style="width:21px;height:21px;border-radius:50%;background:#FFD22F;border:2px solid black;display:inline-block;margin-right:8px;"></span>
                <span style="font-size:0.85em;">Archetyp wspierający</span>
              </span>
              <span style="display:flex;align-items:center;">
                <span style="width:21px;height:21px;border-radius:50%;background:#40b900;border:2px solid black;display:inline-block;margin-right:8px;"></span>
                <span style="font-size:0.85em;">Archetyp poboczny</span>
              </span>
            </div>
            """, unsafe_allow_html=True)

        with col3:
            if main_type is not None:
                kola_img = compose_archetype_highlight(
                    archetype_name_to_img_idx(main_type),
                    archetype_name_to_img_idx(second_type) if second_type != main_type else None,
                    archetype_name_to_img_idx(supplement_type) if supplement_type not in [main_type, second_type] else None
                )
                st.image(
                    kola_img,
                    caption="Podświetlenie: główny – czerwony, wspierający – żółty, poboczny – zielony",
                    width=700
                )

        st.markdown("""
        <hr style="height:1px; border:none; background:#eee; margin-top:34px; margin-bottom:19px;" />
        """, unsafe_allow_html=True)

        st.markdown(f'<div style="font-size:2.1em;font-weight:700;margin-bottom:16px;">Archetyp główny Marcina Gołka</div>', unsafe_allow_html=True)
        render_archetype_card(archetype_extended.get(main_type, {}), main=True)

        if second_type and second_type != main_type:
            st.markdown("<div style='height:35px;'></div>", unsafe_allow_html=True)
            st.markdown("""<hr style="height:1.1px; border:none; background:#ddd; margin-top:6px; margin-bottom:18px;" />""", unsafe_allow_html=True)
            st.markdown("<div style='font-size:1.63em;font-weight:700;margin-bottom:15px;'>Archetyp wspierający Marcina Gołka</div>", unsafe_allow_html=True)
            render_archetype_card(archetype_extended.get(second_type, {}), main=False)

        if supplement_type and supplement_type not in [main_type, second_type]:
            st.markdown("<div style='height:35px;'></div>", unsafe_allow_html=True)
            st.markdown("""<hr style="height:1.1px; border:none; background:#ddd; margin-top:6px; margin-bottom:18px;" />""", unsafe_allow_html=True)
            st.markdown("<div style='font-size:1.63em;font-weight:700;margin-bottom:15px;'>Archetyp poboczny Marcina Gołka</div>", unsafe_allow_html=True)
            render_archetype_card(archetype_extended.get(supplement_type, {}), main=False)

        st.markdown("""
        <div style='height:44px;'></div>
        <hr style="height:1px; border:none; background:#e5e5e5; margin-bottom:26px;" />
        <div style="font-size:1.2em; font-weight:600; margin-bottom:23px;">
            Pobierz raporty archetypu Marcina Gołka
        </div>
        """, unsafe_allow_html=True)

        # GENEROWANIE OBRAZU PANELU DYNAMICZNIE
        idx_main = archetype_name_to_img_idx(main_type)
        idx_aux = archetype_name_to_img_idx(second_type) if second_type != main_type else None
        idx_supplement = archetype_name_to_img_idx(supplement_type) if supplement_type not in [main_type, second_type] else None

        panel_img = compose_archetype_highlight(idx_main, idx_aux, idx_supplement)
        panel_img_path = f"panel_{main_type.lower()}_{second_type.lower() if second_type else ''}_{supplement_type.lower() if supplement_type else ''}.png"
        panel_img.save(panel_img_path)

        # ----------- EKSPORT WORD I PDF - pionowo, z ikonkami -----------
        docx_buf = export_word_docxtpl(
            main_type,  # str
            second_type,  # str
            supplement_type,  # str
            archetype_features,  # dict
            main,  # dict
            second,  # dict
            supplement,  # dict
            radar_img_path="radar.png",
            archetype_table=archetype_table,
            num_ankiet=num_ankiet,
            panel_img_path=panel_img_path
        )
        pdf_buf = word_to_pdf(docx_buf)

        word_icon = "<svg width='21' height='21' viewBox='0 0 32 32' style='vertical-align:middle;margin-right:7px;margin-bottom:2px;'><rect width='32' height='32' rx='4' fill='#185abd'/><text x='16' y='22' text-anchor='middle' font-family='Segoe UI,Arial' font-size='16' fill='#fff' font-weight='bold'>W</text></svg>"
        pdf_icon = "<svg width='21' height='21' viewBox='0 0 32 32' style='vertical-align:middle;margin-right:7px;margin-bottom:2px;'><rect width='32' height='32' rx='4' fill='#d32f2f'/><text x='16' y='22' text-anchor='middle' font-family='Segoe UI,Arial' font-size='16' fill='#fff' font-weight='bold'>PDF</text></svg>"

        st.markdown(
            f"""
            <div style="display:flex;flex-direction:column;align-items:flex-start;">
                <div style="margin-bottom:11px;">
                    {word_icon}
                    <span style="vertical-align:middle;">
                        <b>Eksport do Word (.docx)</b>
                    </span>
                </div>
            """, unsafe_allow_html=True)
        st.download_button(
            "Pobierz raport (Word)",
            data=docx_buf,
            file_name="ap48_raport.docx",
            key="word_button"
        )

        st.markdown(
            f"""
                <div style="margin-top:21px; margin-bottom:11px;">
                    {pdf_icon}
                    <span style="vertical-align:middle;">
                        <b>Eksport do PDF (.pdf)</b>
                    </span>
                </div>
            """, unsafe_allow_html=True)

        st.download_button(
            "Pobierz raport (PDF)",
            data=pdf_buf,
            file_name="ap48_raport.pdf",
            key="pdf_button"
        )

        st.markdown("""
        <hr style="height:1px; border:none; background:#eee; margin-top:38px; margin-bottom:24px;" />
        """, unsafe_allow_html=True)

        st.markdown('<div style="font-size:1.13em;font-weight:600;margin-bottom:13px;">Tabela odpowiedzi respondentów (pełne wyniki)</div>', unsafe_allow_html=True)
        final_df = results_df.copy()
        try:
            col_to_exclude = [
                "Czas ankiety", "Archetyp", "Główny archetyp", "Cechy kluczowe", "Opis", "Storyline",
                "Rekomendacje", "Archetyp wspierający", "Cechy wspierający", "Opis wspierający",
                "Storyline wspierający", "Rekomendacje wspierający"
            ]
            means = final_df.drop(columns=col_to_exclude, errors="ignore").mean(numeric_only=True)
            summary_row = {col: round(means[col], 2) if col in means else "-" for col in final_df.columns}
            summary_row["Czas ankiety"] = "ŚREDNIA"
            final_df = pd.concat([final_df, pd.DataFrame([summary_row])], ignore_index=True)
        except Exception as e:
            pass
        st.dataframe(final_df, hide_index=True)
        st.download_button("Pobierz wyniki archetypów (CSV)", final_df.to_csv(index=False), "ap48_archetypy.csv")
        buffer = io.BytesIO()
        final_df.to_excel(buffer, index=False)
        st.download_button(
            label="Pobierz wyniki archetypów (XLSX)",
            data=buffer.getvalue(),
            file_name="ap48_archetypy.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
else:
    st.info("Brak danych 'answers' – nie wykryto odpowiedzi w bazie danych.")