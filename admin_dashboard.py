# admin_dashboard.py - raporty archetypów

import pandas as pd
import streamlit as st
import psycopg2
import ast
import plotly.graph_objects as go
'import study'
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
import streamlit.components.v1 as components
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

# === PDF (FPDF2) z osadzonymi fontami TTF ===
from fpdf import FPDF
from pathlib import Path

FONT_DIR = Path(__file__).with_name("assets") / "fonts"


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

# --- Ikony archetypów do Word (InlineImage) ---
def _icon_file_for(archetype_name: str, gender_code: str = "M"):
    """
    Zwraca ścieżkę do pliku ikony w assets/person_icons:
      <slug>_<M/K>.svg|png lub fallback <slug>.svg|png
    """
    import glob
    base_masc = base_masc_from_any(archetype_name)
    slug = ARCHETYPE_BASE_SLUGS.get(base_masc, _slug_pl(base_masc))
    g = (gender_code or "M").upper()
    candidates = [
        ARCHETYPE_ICON_DIR / f"{slug}_{g}.svg",
        ARCHETYPE_ICON_DIR / f"{slug}_{g}.png",
        ARCHETYPE_ICON_DIR / f"{slug}.svg",
        ARCHETYPE_ICON_DIR / f"{slug}.png",
    ]
    for c in candidates:
        if Path(c).exists():
            return Path(c)
        m = glob.glob(str(c))
        if m:
            return Path(m[0])
    return None

def arche_icon_inline_for_word(doc, archetype_name: str, gender_code: str = "M", height_mm: float = 18):
    """
    Zwraca InlineImage do docxtpl dla danego archetypu.
    Obsługuje SVG (konwersja do PNG) i PNG.
    """
    path = _icon_file_for(archetype_name, gender_code)
    if not path:
        return ""
    if path.suffix.lower() == ".svg":
        png_bytes = svg_to_png_bytes(str(path), height_mm=height_mm)
        return InlineImage(doc, BytesIO(png_bytes), height=Mm(height_mm))
    else:
        return InlineImage(doc, str(path), height=Mm(height_mm))


# --- Generowanie grafiki z paletą kolorów do Word ---
def _luma(hexcode: str) -> float:
    h = hexcode.lstrip('#')
    if len(h) == 3:
        h = ''.join(c*2 for c in h)
    r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
    return 0.2126*r + 0.7152*g + 0.0722*b

def make_palette_png(palette: list[str], box_w=260, box_h=160, pad=20, gap=18, font_pt=28):
    """
    Tworzy jeden rząd kafelków kolorów z podpisami 'nazwa (#HEX)'.
    Zwraca BytesIO (PNG).
    """
    if not palette:
        return None
    from PIL import ImageFont
    # spróbuj systemowych DejaVu (bezpieczny fallback)
    try:
        font_b = ImageFont.truetype("DejaVuSans-Bold.ttf", font_pt)
    except Exception:
        font_b = None

    n = len(palette)
    W = pad*2 + n*box_w + (n-1)*gap
    H = pad*2 + box_h
    img = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    drw = ImageDraw.Draw(img)

    x = pad
    for hexcode in palette:
        drw.rounded_rectangle([x, pad, x+box_w, pad+box_h], radius=22, fill=hexcode)
        label = f"{COLOR_NAME_MAP.get(hexcode.upper(), hexcode)}\n({hexcode.upper()})"
        # kolor napisu – biały dla bardzo ciemnych kafli
        tcol = (255, 255, 255) if _luma(hexcode) < 110 else (17, 17, 17)
        tw, th = drw.multiline_textbbox((0, 0), label, font=font_b or None, align="center")[2:]
        drw.multiline_text((x + box_w/2 - tw/2, pad + box_h/2 - th/2),
                           label, fill=tcol, font=font_b or None, align="center")
        x += box_w + gap

    out = BytesIO()
    img.save(out, "PNG")
    out.seek(0)
    return out

def palette_inline_for_word(doc, palette: list[str]):
    png = make_palette_png(palette)
    return InlineImage(doc, png, width=Mm(170)) if png else ""


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


from pathlib import Path
import base64

# --- IKONY ARCHETYPÓW (SVG) ---
ARCHETYPE_ICON_DIR = Path(__file__).with_name("assets") / "person_icons"

_PL_MAP = str.maketrans({
    "ą":"a","ć":"c","ę":"e","ł":"l","ń":"n","ó":"o","ś":"s","ź":"z","ż":"z",
    "Ą":"a","Ć":"c","Ę":"e","Ł":"l","Ń":"n","Ó":"o","Ś":"s","Ź":"z","Ż":"z",
    "’":"", "'":""
})

def _slug_pl(s: str) -> str:
    s = (s or "").strip().lower().translate(_PL_MAP)
    # normalizacje nazw używanych w danych
    s = s.replace(" / ", " ").replace("/", " ").replace(",", " ")
    s = " ".join(s.split())
    return s.replace(" ", "-")

# Gdyby Twoje pliki miały inne nazwy niż slug (opcjonalnie dopisz mapę wyjątków)
ARCHETYPE_FILENAME_MAP = {
    # "kochanelubwielbiciel": "kochanek.svg"  # przykład, jeśli trzeba
}

def arche_icon_img_html(archetype_name: str, height_px: int = 90, gender_code: str = "M") -> str:
    """
    Szuka w assets/person_icons pliku o nazwie:
      <slug>_<gender>.svg|png   (np. blazen_M.png, wladca_K.svg)
    a gdy go nie znajdzie – próbuje też <slug>.svg|png jako fallback.
    """
    import base64, glob, os
    # archetype_name może już być w formie żeńskiej – cofnij do męskiej bazy:
    base_masc = base_masc_from_any(archetype_name)
    slug = ARCHETYPE_BASE_SLUGS.get(base_masc, _slug_pl(base_masc))
    g = (gender_code or "M").upper()

    patterns = [
        ARCHETYPE_ICON_DIR / f"{slug}_{g}.svg",
        ARCHETYPE_ICON_DIR / f"{slug}_{g}.png",
        ARCHETYPE_ICON_DIR / f"{slug}.svg",   # fallback wspólny
        ARCHETYPE_ICON_DIR / f"{slug}.png",
    ]

    path = None
    for pat in patterns:
        matches = glob.glob(str(pat))
        if matches:
            path = Path(matches[0]); break
        if Path(pat).exists():
            path = Path(pat); break

    if path and path.exists():
        data = path.read_bytes()
        mime = "image/svg+xml" if path.suffix.lower() == ".svg" else "image/png"
        b64 = base64.b64encode(data).decode("ascii")
        return (
            f"<img src='data:{mime};base64,{b64}' alt='{archetype_name}' "
            f"style='height:{height_px}px; width:auto; display:block;'/>"
        )

    # Fallback (gdy nic nie ma)
    return f"<div style='font-size:{int(height_px*0.9)}px;line-height:1'>🔹</div>"


import cairosvg

# (page_config usunięty – ustawiany w app.py)

COLOR_NAME_MAP = {
    "#000000": "czerń",
    "#FFD700": "złoto",
    "#282C34": "granat (antracyt)",
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
    "#87CEEB": "błękit (sky blue)",
    "#43C6DB": "turkusowy błękit",
    "#A0E8AF": "seledyn",
    "#F9D371": "złocisty żółty",
    "#8F00FF": "fiolet intensywny",
    "#181C3A": "granat bardzo ciemny",
    "#E0BBE4": "pastelowy fiolet",
    "#F9F9F9": "biel bardzo jasna",
    "#6CA0DC": "błękit średni",
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
    "#FF7F0E": "jaskrawy pomarańcz",
    "#D5C6AF": "beż jasny",
    "#906C46": "brąz średni",
    "#696812": "oliwkowy ciemny",
    "#212809": "oliwkowy głęboki",
    "#B6019A": "fuksja",
    "#E10209": "czerwony żywy",
    "#1B1715": "brąz bardzo ciemny",
    "#F9ED06": "żółty intensywny",
    "#588A4F": "zielony średni",
    "#7AA571": "zielony jasny",
    "#AB3941": "czerwony wiśniowy",
    "#61681C": "oliwkowy",
    "#0070B5": "niebieski",
    "#8681E8": "fiolet jasny",
    "#FE89BE": "róż jasny",
    "#FD4431": "pomarańczowy żywy",
    "#5B6979": "grafitowy",
    "#A1B1C2": "szary jasny",
    "#0192D3": "turkus",
    "#2C7D78": "turkus ciemny",
    "#86725D": "brąz jasny",
    "#F4F1ED": "biały ciepły",
    "#BBBDA0": "khaki jasne",
    "#2D4900": "oliwkowy bardzo ciemny",
    "#0E0D13": "grafit bardzo ciemny",
    "#2B2D41": "granat ciemny",
    "#C2BCC1": "szary bardzo jasny",
    "#CC3E2F": "czerwony ceglasty",
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

# --- KOLORY: mapowanie pytań (1..48) do 4 kolorów i kalkulator % ---
COLOR_QUESTION_MAP = {
    "Niebieski": [9,10,11,12,37,38,39,40,41,42,43,44],
    "Zielony":   [13,14,15,16,17,18,19,20,21,22,23,24],
    "Żółty":     [25,26,27,28,33,34,35,36,29,30,31,32],
    "Czerwony":  [1,2,3,4,5,6,7,8,45,46,47,48],
}
COLOR_HEX = {  # kolory pierścieni
    "Czerwony":  "#E53935",
    "Zielony":   "#7ED321",
    "Żółty":     "#FFC107",
    "Niebieski": "#29ABE2",
}

# === 4 bąbelki w linii: średnica ~ udział % w całości, pierścień ~ % względem zwycięzcy ===
def _bubble_svg(value_pct: float, winner_pct: float, color: str,
                diameter_px: int, track="#FFFFFF", text_color="#111") -> str:
    import math
    value_pct  = max(0.0, float(value_pct or 0.0))
    winner_pct = max(0.0001, float(winner_pct or 0.0001))
    ring_pct   = max(0.0, min(100.0, 100.0 * value_pct / winner_pct))  # % względem zwycięzcy

    size   = int(diameter_px)
    stroke = max(10, int(size * 0.14))
    r      = (size - stroke) / 2
    c      = 2 * math.pi * r
    dash   = c * (ring_pct / 100.0)
    gap    = c - dash

    return f"""
    <svg width="{size}" height="{size}" viewBox="0 0 {size} {size}"
         style="display:block; shape-rendering:geometricPrecision;">
      <g transform="rotate(-90 {size/2} {size/2})">
        <circle cx="{size/2}" cy="{size/2}" r="{r}" fill="none"
                stroke="{track}" stroke-width="{stroke}" stroke-linecap="round"/>
        <circle cx="{size/2}" cy="{size/2}" r="{r}" fill="none"
                stroke="{color}" stroke-width="{stroke}" stroke-linecap="round"
                stroke-dasharray="{dash} {gap}"/>
      </g>
      <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle"
            style="font-family:'Segoe UI',system-ui,-apple-system,Arial;
                   font-size:{int(size*0.30)}px; font-weight:800; fill:{text_color};">
        {int(round(value_pct))}%
      </text>
    </svg>
    """

def color_bubbles_html(pcts: dict[str, float],
                       min_d: int = 110, max_d: int = 240,
                       map_mode: str = "diameter") -> str:
    items = sorted(pcts.items(), key=lambda kv: kv[1], reverse=True)
    if not items:
        return "<div></div>"
    winner_val = max(0.0001, items[0][1])

    def dia(val):
        frac = max(0.0, min(1.0, (val or 0.0) / 100.0))
        if map_mode == "area":
            frac = frac ** 0.5
        return int(min_d + frac * (max_d - min_d))

    blocks = []
    for name, val in items:
        d = dia(val)
        svg = _bubble_svg(val, winner_val, COLOR_HEX[name], d)
        blocks.append(f"""
          <div class="ap-bubble-wrap">
            <div class="ap-bubble" style="width:{d}px;height:{d}px;">{svg}</div>
            <div class="ap-chip">
              <span class="ap-dot" style="background:{COLOR_HEX[name]}"></span>{name}
            </div>
          </div>
        """)

    return f"""
    <style>
      .ap-bubbles-row{{display:flex;justify-content:center;align-items:flex-end;gap:26px;background:transparent;}}
    .ap-bubble-wrap{{display:flex;flex-direction:column;align-items:center;gap:16px;}}
      /* delikatny, neutralny cień tylko CSS – brak kolorowych smug */
      .ap-bubble{{filter: drop-shadow(0 6px 12px rgba(0,0,0,.12)); border-radius:50%;}}
    .ap-chip{{display:inline-flex;align-items:center;gap:8px;padding:6px 10px;
             border:1px solid #eceff3;border-radius:999px;margin-top:4px;
             font:600 13px/1.1 'Segoe UI',system-ui;background:#fff;}}
      .ap-dot{{width:10px;height:10px;border-radius:50%;display:inline-block}}
    </style>
    <div class="ap-bubbles-row">{''.join(blocks)}</div>
    """

def color_progress_bars_html(pcts: dict[str, float], order: str = "desc") -> str:
    """
    Paski 0–100% z szarym torem i kolorowym wypełnieniem.
    • % >= 10  → etykieta na końcu WEWNĘTRZNYM kolorowego paska.
    • % < 10   → etykieta na końcu ZEWNĘTRZNYM kolorowego paska (tuż za nim).
    order: 'asc' = najmniejszy na górze, 'desc' = największy na górze.
    """
    items = sorted(pcts.items(), key=lambda kv: kv[1], reverse=(order == "desc"))

    rows = []
    for name, val in items:
        pct = max(0.0, float(val or 0.0))
        pct_int = int(round(pct))
        width_css = f"{pct:.3f}%"
        color = COLOR_HEX[name]
        inside = pct >= 10.0

        rows.append(f"""
          <div class="cp-row">
            <div class="cp-label">
              <span class="cp-dot" style="background:{color}"></span>
              <b>{name}</b>
            </div>

            <div class="cp-track">
              <div class="cp-fill" style="width:{width_css}; background:{color}">
                <div class="cp-badge {'in' if inside else 'out'}">{pct_int}%</div>
              </div>
            </div>
          </div>
        """)

    return f"""
    <style>
      :root {{ --ff: "Arial Nova Cond","Roboto Condensed","Segoe UI",system-ui,-apple-system,Arial,sans-serif; }}

      .cp-wrap{{ font-family: var(--ff); }}
      .cp-row{{display:grid; grid-template-columns:140px 1fr; gap:12px;
               align-items:center; margin:14px 0;}}
      .cp-label{{display:flex; align-items:center; gap:8px; font-weight:700; font-size:15px;}}
      .cp-dot{{width:10px; height:10px; border-radius:50%; display:inline-block;}}

      .cp-track{{position:relative; height:42px; border-radius:999px;
                 background:#eef2f7; box-shadow: inset 0 0 0 1px #e1e7f0;}}
      .cp-fill{{position:relative; height:100%; border-radius:999px; overflow:visible;}}

      .cp-badge{{position:absolute; top:50%; transform:translateY(-50%);
                 font-family: var(--ff); font-weight:800; font-size:14px; color:#111; white-space:nowrap;}}
      .cp-badge.in{{right:12px;}}                    /* wewnątrz koloru (≥10%) */
      .cp-badge.out{{left:100%; margin-left:12px;}}  /* tuż za kolorem (<10%) */
    </style>

    <div class="cp-wrap">
      {''.join(rows)}
    </div>
    """



def _sum_color_points_for_answers(answers: list[int]) -> dict[str,int]:
    """Suma punktów na podstawie jednej odpowiedzi (48 pytań)."""
    out = {k: 0 for k in COLOR_QUESTION_MAP}
    if not isinstance(answers, list) or len(answers) < 48:
        return out
    for color, qs in COLOR_QUESTION_MAP.items():
        out[color] += sum(answers[i-1] for i in qs)
    return out

def calc_color_percentages_from_df(df: pd.DataFrame) -> dict[str, float]:
    """Średni % dla każdego koloru przy skali 0–100 per kolor (60 pkt max na kolor i osobę)."""
    totals = {k: 0 for k in COLOR_QUESTION_MAP}
    n = 0
    if "answers" not in df.columns or df.empty:
        return {k: 0.0 for k in COLOR_QUESTION_MAP}

    for _, row in df.iterrows():
        ans = row.get("answers")
        sums = _sum_color_points_for_answers(ans)
        if sums:
            for k, v in sums.items():
                totals[k] += v
            n += 1

    if n == 0:
        return {k: 0.0 for k in COLOR_QUESTION_MAP}

    max_per_color = {c: 5 * len(qs) for c, qs in COLOR_QUESTION_MAP.items()}
    return {
        c: round(100.0 * totals[c] / (max_per_color[c] * n), 1)
        for c in COLOR_QUESTION_MAP.keys()
    }

# --- Pierścień w SVG (transparentne tło + delikatna poświata) ---
def _ring_svg(percent: float, color: str, size: int = 180, stroke: int = 16,
              track="#FFFFFF", text_color="#333") -> str:
    import math, uuid
    pct = max(0.0, min(100.0, float(percent)))
    r = (size - stroke) / 2
    c = 2 * math.pi * r
    dash = c * pct / 100.0
    gap = c - dash

    uid = "g_" + uuid.uuid4().hex[:8]  # 👈 unikalny id filtra

    filter_def = ""
    return f"""
    <svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" style="display:block;">
      {filter_def}
      <g transform="rotate(-90 {size/2} {size/2})">
        <circle cx="{size/2}" cy="{size/2}" r="{r}" fill="none"
                stroke="{track}" stroke-width="{stroke}" stroke-linecap="round"/>
        <circle cx="{size/2}" cy="{size/2}" r="{r}" fill="none"
            stroke="{color}" stroke-width="{stroke}" stroke-linecap="round"
            stroke-dasharray="{dash} {gap}"/>
      </g>
      <g>
        <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle"
              style="font-family: 'Segoe UI', system-ui, -apple-system, Arial; font-size:{int(size*0.28)}px; font-weight:800; fill:{text_color};">
          {int(round(pct))}%
        </text>
      </g>
    </svg>
    """
def build_color_bars(pcts: dict[str, float], orientation: str = "h") -> go.Figure:
    # sort od największego
    items = sorted(pcts.items(), key=lambda kv: kv[1], reverse=True)
    labels = [k for k, _ in items]
    values = [v for _, v in items]
    colors = [COLOR_HEX[k] for k in labels]

    if orientation == "h":
        fig = go.Figure(go.Bar(
            x=values, y=labels, orientation="h",
            text=[f"{int(round(v))}%" for v in values],
            textposition="inside",
            insidetextanchor="middle",
            marker=dict(color=colors),
        ))
        fig.update_layout(
            xaxis=dict(range=[0, 100], showgrid=True, zeroline=False),
            yaxis=dict(tickfont=dict(size=14)),
            margin=dict(l=10, r=10, t=10, b=10),
            height=260,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
        )
    else:
        fig = go.Figure(go.Bar(
            x=labels, y=values,
            text=[f"{int(round(v))}%" for v in values],
            textposition="outside",
            marker=dict(color=colors),
        ))
        fig.update_layout(
            yaxis=dict(range=[0, 100], showgrid=True, zeroline=False),
            xaxis=dict(tickfont=dict(size=14)),
            margin=dict(l=10, r=10, t=10, b=10),
            height=320,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False,
        )
    return fig


def color_gauges_html(pcts: dict[str, float]) -> str:
    """Układ jak na screenie: 1 duży + 3 małe po prawej; full transparent."""
    # sort – pierwszy to największy (duży)
    items = sorted(pcts.items(), key=lambda kv: kv[1], reverse=True)
    big = items[0]
    small = items[1:]

    def chip(name, hex_):
        return (f"<span style='display:inline-flex;align-items:center;"
                f"gap:8px;padding:6px 10px;border:1px solid #e8e8ee;border-radius:999px;"
                f"font:600 13px/1.1 \"Segoe UI\",system-ui; background:rgba(255,255,255,.65)'>"
                f"<span style='width:10px;height:10px;border-radius:50%;background:{hex_};display:inline-block'></span>{name}</span>")

    big_svg = _ring_svg(big[1], COLOR_HEX[big[0]], size=220, stroke=20)
    small_svgs = "".join(
        f"<div style='display:flex;align-items:center;gap:12px'>"
        f"<div style='width:120px'>{_ring_svg(v, COLOR_HEX[k], size=120, stroke=14)}</div>"
        f"{chip(k, COLOR_HEX[k])}"
        f"</div>"
        for k, v in small
    )

    return f"""
    <div style="display:flex; gap:32px; align-items:center; background:transparent;">
      <div style="width:240px">{big_svg}</div>
      <div style="display:flex; flex-direction:column; gap:18px;">{small_svgs}</div>
    </div>
    """

# --- OPISY HEURYSTYCZNE 4 KOLORÓW (treści z Twojej specyfikacji) ---
COLOR_EMOJI = {"Czerwony":"🔴","Zielony":"🟢","Żółty":"🟡","Niebieski":"🔵"}

COLOR_LONG = {
    "Niebieski": {
        "title": "Niebieski – analityczny, proceduralny, precyzyjny",
        "orient": "fakty, dane, logikę i procedury",
        "body": (
            "Ceni fakty, logikę i stabilne procedury. Działa najlepiej, gdy ma jasno określone zasady, "
            "harmonogram i dostęp do danych. Nie lubi chaosu, nagłych zmian i improwizacji – woli działać "
            "według planu. Może sprawiać wrażenie zdystansowanego i nadmiernie ostrożnego, ale wnosi do "
            "zespołu rzetelność, sumienność i dbałość o szczegóły. Niebieski to myślenie."
        ),
        "politics": (
            "W polityce to typ eksperta – skrupulatny analityk, który zamiast haseł pokazuje liczby i tabele. "
            "Budzi zaufanie dzięki przygotowaniu merytorycznemu i pragmatycznym rozwiązaniom. Może być odbierany "
            "jako mało charyzmatyczny, ale daje wyborcom poczucie przewidywalności i bezpieczeństwa instytucjonalnego."
        ),
        "hex": COLOR_HEX["Niebieski"]
    },
    "Zielony": {
        "title": "Zielony – empatyczny, harmonijny, wspierający",
        "orient": "relacje, troskę, zaufanie, wspólnotę",
        "body": (
            "Kierują się wartościami, relacjami i potrzebą budowania poczucia bezpieczeństwa. Są empatyczni, "
            "uważni na innych i dążą do zgody. Nie lubią gwałtownych zmian i konfrontacji, czasem brakuje im "
            "asertywności, ale potrafią tworzyć atmosferę zaufania i współpracy. Wnoszą do zespołu stabilność, "
            "lojalność i umiejętność łagodzenia napięć. Zieloni to uczucia."
        ),
        "politics": (
            "W polityce to typ mediator-społecznik, który stawia na dialog, kompromis i dobro wspólne. Potrafi "
            "przekonać elektorat stylem „opiekuńczego lidera”, akcentując wartości społeczne, wspólnotowe i "
            "solidarnościowe. Może unikać ostrych sporów, ale umiejętnie buduje mosty i zdobywa poparcie przez "
            "bliskość i troskę o codzienne sprawy ludzi."
        ),
        "hex": COLOR_HEX["Zielony"]
    },
    "Żółty": {
        "title": "Żółty – kreatywny, pełny energii i spontaniczny",
        "orient": "wizję, innowację, możliwości, odkrywanie nowych dróg",
        "body": (
            "Osoba wizjonerska i entuzjastyczna – pełna pomysłów, które inspirują innych. Najlepiej czuje się w "
            "środowisku swobodnym, otwartym na eksperymenty i innowacje. Nie przepada za rutyną, schematami i "
            "nadmierną kontrolą. Jego mocną stroną jest umiejętność rozbudzania energii zespołu, improwizacja i "
            "znajdowanie nowych możliwości tam, gdzie inni widzą bariery. Żółty to intuicja."
        ),
        "politics": (
            "W polityce to typ showmana i wizjonera, który potrafi porwać tłumy hasłami zmiany i nowego otwarcia. "
            "Umie przekuć abstrakcyjne idee w obrazowe narracje, które przemawiają do emocji. Bywa odbierany jako "
            "idealista lub ryzykant, ale świetnie nadaje dynamikę kampanii i kreuje „nową nadzieję”."
        ),
        "hex": COLOR_HEX["Żółty"]
    },
    "Czerwony": {
        "title": "Czerwony – decyzyjny, nastawiony na wynik, dominujący",
        "orient": "działanie, sprawczość, szybkie decyzje, forsowanie kierunku",
        "body": (
            "Ma naturalne zdolności przywódcze i skłonność do szybkiego podejmowania decyzji. Jest niezależny, "
            "ambitny i skoncentrowany na rezultatach. Może być niecierpliwy, zbyt stanowczy i mało elastyczny, "
            "ale dzięki determinacji potrafi przeprowadzić projekt do końca mimo przeszkód. To osoba, która nadaje "
            "kierunek i mobilizuje innych do działania. Czerwony to doświadczenie."
        ),
        "politics": (
            "W polityce to typ lidera-wojownika, który buduje swoją pozycję na sile, determinacji i zdolności "
            "„dowiezienia” obietnic. Sprawdza się w kampaniach, gdzie liczy się mocne przywództwo i szybkie decyzje. "
            "Może odstraszać swoją twardością, ale równocześnie daje poczucie, że „trzyma ster”."
        ),
        "hex": COLOR_HEX["Czerwony"]
    },
}

COLOR_META = {
    name: {
        "emoji": COLOR_EMOJI[name],
        "title": COLOR_LONG[name]["title"],
        "orient": f"Orientacja na: {COLOR_LONG[name]['orient']}",
        "desc":   COLOR_LONG[name]["body"] + "\n\n" + " 👉 " + COLOR_LONG[name]["politics"],
    }
    for name in COLOR_LONG.keys()
}

def color_explainer_one_html(name: str, pct: float) -> str:
    """Jeden panel z opisem dominującego koloru."""
    meta = COLOR_LONG[name]
    emoji = COLOR_EMOJI[name]
    return f"""
      <div style="border:1px solid #ececf3; border-left:6px solid {meta['hex']};
                  border-radius:12px; padding:20px 22px; margin:4px 0 6px 0;
                  background:rgba(255,255,255,.65);">
        <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">
          <span style="font-size:20px">{emoji}</span>
          <div style="font:650 18px/1.2 'Segoe UI',system-ui">{meta['title']}</div>
          <div style="margin-left:auto;font:700 14px/1 'Segoe UI',system-ui;color:#333">{pct:.1f}%</div>
        </div>

        <div style="font:600 16px/1.45 'Segoe UI',system-ui; color:#444;">
          • <b>Orientacja na:</b> {meta['orient']}
        </div>

        <div style="margin-top:12px; font:400 14px/1.6 'Segoe UI',system-ui; color:#2a2a2a;">
          {meta['body']}
        </div>

        <div style="margin-top:12px; font:400 14px/1.6 'Segoe UI',system-ui; color:#2a2a2a;">
          👉 {meta['politics']}
        </div>
      </div>
    """


def color_explainer_html(pcts: dict[str, float]) -> str:
    """Render 4 akapity pod wykresem – kolejność wg udziału (%)."""
    items = sorted(pcts.items(), key=lambda kv: kv[1], reverse=True)
    blocks = []
    for name, val in items:
        meta = COLOR_LONG[name]
        emoji = COLOR_EMOJI[name]
        blocks.append(f"""
        <div style="border:1px solid #ececf3; border-left:6px solid {meta['hex']};
                    border-radius:12px; padding:16px 18px; margin-bottom:14px;
                    background:rgba(255,255,255,.65);">
          <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">
             <span style="font-size:20px">{emoji}</span>
             <div style="font:650 18px/1.2 'Segoe UI',system-ui">{meta['title']}</div>
             <div style="margin-left:auto;font:700 14px/1 'Segoe UI',system-ui;color:#333">{val:.1f}%</div>
          </div>
           <div style="font:600 16px/1.45 'Segoe UI',system-ui; color:#444;">
             • <b>Orientacja na:</b> {meta['orient']}<br/>
          </div>
          <div style="margin-top:12px; font:400 14px/1.6 'Segoe UI',system-ui; color:#2a2a2a;">{meta['body']}</div>
          <div style="margin-top:12px; font:400 14px/1.6 'Segoe UI',system-ui; color:#2a2a2a;">👉 {meta['politics']}</div>
        </div>
        """)
    return "<div style='background:transparent'>" + "".join(blocks) + "</div>"


def color_scores_from_answers(answers: list[int]) -> dict[str, int]:
    if not isinstance(answers, list) or len(answers) < 48:
        return {c: 0 for c in COLOR_QUESTION_MAP}
    out = {}
    for color, idxs in COLOR_QUESTION_MAP.items():
        out[color] = sum(answers[i-1] for i in idxs)  # pytania są 1-indexed
    return out

def color_percents_from_scores(scores: dict[str, int]) -> dict[str, float]:
    # 12 pytań × 5 pkt = 60; obliczaj z mapy dla odporności
    max_per_color = {c: 5 * len(qs) for c, qs in COLOR_QUESTION_MAP.items()}
    out = {}
    for c in COLOR_QUESTION_MAP.keys():
        v = max(0, int(scores.get(c, 0)))
        out[c] = round(100.0 * v / max_per_color[c], 1)
    return out


# --- PŁEĆ I ODWZOROWANIA NAZW/PLIKÓW ---

# Feminatywy, zgodnie z Twoją listą
GENDER_FEMININE_MAP = {
    "Władca": "Władczyni",
    "Bohater": "Bohaterka",
    "Mędrzec": "Mędrczyni",
    "Opiekun": "Opiekunka",
    "Kochanek": "Kochanka",
    "Błazen": "Komiczka",
    "Twórca": "Twórczyni",
    "Odkrywca": "Odkrywczyni",
    "Czarodziej": "Czarodziejka",
    "Towarzysz": "Towarzyszka",
    "Niewinny": "Niewinna",
    "Buntownik": "Buntowniczka",
}

# odwrotna mapa (z żeńskich na męskie), przydaje się, gdy wejściowo dostaniemy już żeńską formę
GENDER_MASC_FROM_FEM = {v: k for k, v in GENDER_FEMININE_MAP.items()}

# “bazowe” nazwy plików w assets/person_icons (bez sufiksu _M/_K i rozszerzenia)
# ← podajemy tu męskie formy jako klucz
ARCHETYPE_BASE_SLUGS = {
    "Władca": "wladca",
    "Bohater": "bohater",
    "Mędrzec": "medrzec",
    "Opiekun": "opiekun",
    "Kochanek": "kochanek",
    "Błazen": "blazen",
    "Twórca": "tworca",
    "Odkrywca": "odkrywca",
    "Czarodziej": "czarodziej",
    "Towarzysz": "towarzysz",
    "Niewinny": "niewinny",
    "Buntownik": "buntownik",
}

def normalize_gender(value) -> str:
    """
    Z dowolnej wartości („M”, „K”, „mężczyzna”, „kobieta”, True/False, itp.)
    zwraca kod 'M' albo 'K'. Domyślnie 'M'.
    """
    v = (str(value or "")).strip().lower()
    if v in ("k", "kobieta", "female", "f", "kob"):
        return "K"
    return "M"

def display_name_for_gender(base_masc_name: str, gender_code: str) -> str:
    """Zwraca nazwę do pokazania na ekranie zależnie od płci."""
    if gender_code == "K":
        return GENDER_FEMININE_MAP.get(base_masc_name, base_masc_name)
    return base_masc_name

def base_masc_from_any(name: str) -> str:
    """Jeśli dostaliśmy już żeńską formę – cofamy do męskiej; w innym wypadku zwracamy jak było."""
    if name in GENDER_MASC_FROM_FEM:
        return GENDER_MASC_FROM_FEM[name]
    return name


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
            "#E10600", "#2E3141", "#FFFFFF", "#D62728", "#0E0D13", "#2B2D41", "#C2BCC1", "#CC3E2F",
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
            "#4682B4", "#B0C4DE", "#6C7A89", "#1F77B4", "#86725D", "#F4F1ED", "#BBBDA0", "#2D4900",
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
            "#0192D3", "#B4D6B4", "#A7C7E7", "#FFD580", "#9467BD", "#5B6979", "#A1B1C2", "#2C7D78",
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
        "name": "Kochanek",
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
            "Old Spice", "M&Ms", "Fanta", "Łomża", "kabarety"
        ],
        "color_palette": [
            "#AB3941", "#F2A93B", "#FFB300", "#FFD93D", "#588A4F", "#7AA571", "#61681C", "#FF8300",
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
            "#7C53C3", "#3BE8B0", "#87CEEB", "#17BECF", "#B6019A", "#E10209", "#1B1715", "#F9ED06",
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
            "#212809", "#A0E8AF", "#F9D371", "#E377C2", "#D5C6AF", "#906C46", "#43C6DB", "#696812",
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
            "Intel", "Disney", "XBox", "Sony", "Polaroid", "Tesla",
        ],
        "color_palette": [
            "#181C3A", "#E0BBE4", "#8F00FF", "#7C46C5", "#0070B5", "#8681E8", "#FE89BE", "#FD4431",
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
        "name": "Towarzysz",
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
            "#A3C1AD", "#F9F9F9", "#6CA0DC", "#2CA02C"
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
            "#9BD6F4", "#FFF6C3", "#AAC9CE", "#FFF200",
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
            "#FF0000", "#FF6F61", "#000000", "#FF7F0E"
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

from pathlib import Path
from PIL import Image

# —— GLOBALNY STYL DLA NAGŁÓWKÓW, HR, PRZYCISKÓW I SELECTBOXA ——
st.markdown("""
<style>
/* delikatna, szara linia */
.soft-hr{
  height:1px; border:none; background:#e5e7eb; margin:28px 0 26px 0;
}

/* tytuły sekcji (np. „Udostępnij raport”, „Wybierz osobę/JST”) */
.section-title{
  font-family: "Segoe UI", system-ui, -apple-system, Arial, sans-serif;
  font-weight: 650;               /* grubość */
  font-size: 1.28em;              /* czcionka */
  margin: 15px 0 25px 0;           /* marginesy: góra/dół */
  line-height: 1.15;
  color:#182433;
}
.section-title--padTop{ margin-top:34px !important; }
.mt-28{ margin-top:28px !important; }

.section-title--blue{ color:#1a93e3; }

/* przyciski skoków (linki wyglądające jak przyciski) */
.jump-btns{ display:flex; flex-wrap:wrap; gap:8px; margin:8px 0 16px 0; }
.jump-btn{
  display:inline-block; padding:8px 14px; border-radius:10px; text-decoration:none;
  border:1px solid #1a93e3; color:#1a93e3; font-weight:600; font-size:0.95em;
  background:#f0f8ff;
}
.jump-btn:hover{ background:#e6f3ff; }

/* lepsze przewijanie do kotwic */
:target{ scroll-margin-top: 90px; }

/* niebieskie stylowanie selectboxa (jak „Wyślij link do ankiety”) */
div[data-testid="stSelectbox"] > div{
  border:1.5px solid #1a93e3 !important;
  border-radius:10px !important;
  box-shadow: 0 0 0 1px #1a93e333 inset;
}
div[data-testid="stSelectbox"] label{
  color:#1a93e3 !important;
  font-weight:700 !important;
}
</style>
""", unsafe_allow_html=True)

# (opcjonalnie) osadzenie własnych fontów w widoku Streamlit
import base64, pathlib
def _font_face_css(font_path, family_name, weight="normal", style="normal"):
    try:
        data = pathlib.Path(font_path).read_bytes()
        b64 = base64.b64encode(data).decode("ascii")
        return f"""
        @font-face {{
            font-family: '{family_name}';
            src: url(data:font/ttf;base64,{b64}) format('truetype');
            font-weight: {weight};
            font-style: {style};
            font-display: swap;
        }}
        """
    except Exception:
        return ""
css_ff = ""
css_ff += _font_face_css("fonts/ArialNovaCond.ttf", "Arial Nova Cond", "600")
css_ff += _font_face_css("fonts/ArialNovaCondLight.ttf", "Arial Nova Cond", "300")
css_ff += _font_face_css("fonts/RobotoCondensed-Regular.ttf", "Roboto Condensed", "400")
css_ff += _font_face_css("fonts/RobotoCondensed-Light.ttf", "Roboto Condensed", "300")
if css_ff:
    st.markdown(f"<style>{css_ff} body{{font-family:'Roboto','Segoe UI','Arial',sans-serif;}}</style>", unsafe_allow_html=True)


ARCHE_NAME_TO_IDX = {n.lower(): i for i, n in enumerate(ARCHE_NAMES_ORDER)}

@st.cache_data
def load_base_arche_img():
    p = Path(__file__).with_name("assets").joinpath("archetype_wheel.png")
    return Image.open(p).convert("RGBA")


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
        SELECT
            id,
            first_name_nom, first_name_gen, first_name_dat, first_name_acc, first_name_ins, first_name_loc, first_name_voc,
            last_name_nom,  last_name_gen,  last_name_dat,  last_name_acc,  last_name_ins,  last_name_loc,  last_name_voc,
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

def build_word_context(
    main_type, second_type, supplement_type, features, main, second, supplement,
    mean_scores=None, radar_image=None, archetype_table=None, num_ankiet=None,
    person: dict | None = None
):
    """
    person = {
        "NOM": "Imię Nazwisko",
        "GEN": "Imienia Nazwiska",
        "DAT": "Imieniowi Nazwiskowi",
        "ACC": "Imię Nazwisko",
        "INS": "Imieniem Nazwiskiem",
        "LOC": "o Imieniu Nazwisku",
        "VOC": "Imieniu Nazwisku!",
        "CITY_NOM": "Kraków"   # (opcjonalnie)
    }
    """
    COLOR_NAME_MAP = {
        "#000000": "Czerń", "#FFD700": "Złoto", "#282C34": "Granat (antracyt)",
        "#800020": "Burgund", "#E10600": "Czerwień", "#2E3141": "Grafitowy granat",
        "#FFFFFF": "Biel", "#4682B4": "Stalowy błękit", "#B0C4DE": "Jasny niebieskoszary",
        "#6C7A89": "Popielaty szary", "#B4D6B4": "Miętowa zieleń", "#A7C7E7": "Pastelowy błękit",
        "#FFD580": "Pastelowy żółty / beżowy", "#FA709A": "Róż malinowy", "#FEE140": "Jasny żółty",
        "#FFD6E0": "Bardzo jasny róż", "#FFB300": "Mocna żółć", "#FF8300": "Pomarańcz",
        "#FFD93D": "Pastelowa żółć", "#7C53C3": "Fiolet", "#3BE8B0": "Miętowy cyjan",
        "#87CEEB": "Błękit (Sky Blue)", "#43C6DB": "Turkusowy błękit", "#A0E8AF": "Seledyn",
        "#F9D371": "Złocisty żółty", "#8F00FF": "Fiolet (intensywny)", "#181C3A": "Granat bardzo ciemny",
        "#E0BBE4": "Pastelowy fiolet", "#F9F9F9": "Biel bardzo jasna", "#6CA0DC": "Pastelowy błękit",
        "#A3C1AD": "Pastelowa zieleń", "#FFF6C3": "Jasny kremowy", "#AAC9CE": "Pastelowy niebieskoszary",
        "#FFF200": "Żółty (cytrynowy)", "#FF0000": "Czerwień intensywna", "#FF6F61": "Łososiowy róż",
        "#8C564B": "Ciemy brąz", "#D62728": "Czerwień karmazynowa", "#1F77B4": "Chabrowy",
        "#9467BD": "Fiolet śliwkowy", "#F2A93B": "Miodowy żółty", "#17BECF": "Niebieski morski",
        "#E377C2": "Pastelowy róż fioletowy", "#7C46C5": "Fiolet szafirowy", "#2CA02C": "Zieleń trawiasta",
        "#9BD6F4": "Pastelowy błękit jasny", "#FF7F0E": "Jaskrawy pomarańcz",
    }

    person = person or {}
    def p(key, fallback=""):
        return (person.get(key) or fallback).strip()

    def person_links_plain(person_list):
        return person_list or []

    def kolor_label_list(palette):
        if not isinstance(palette, list):
            return ""
        out = []
        for code in palette:
            name = COLOR_NAME_MAP.get(code.upper(), code)
            out.append(f"{name} ({code})")
        return ', '.join(out)

    context = {
        # ——— Meta
        "TYTUL": "Raport Archetypów",
        "IMIE_NAZWISKO": p("GEN") or p("NOM"),   # zgodność wsteczna
        "IMIE_NAZWISKO_NOM": p("NOM"),
        "IMIE_NAZWISKO_GEN": p("GEN"),
        "IMIE_NAZWISKO_DAT": p("DAT"),
        "IMIE_NAZWISKO_ACC": p("ACC"),
        "IMIE_NAZWISKO_INST": p("INS"),
        "IMIE_NAZWISKO_LOC": p("LOC"),
        "IMIE_NAZWISKO_VOC": p("VOC"),
        "CITY_NOM": p("CITY_NOM"),
        "AUTOR": "Piotr Stec",
        "DATA": datetime.now().strftime("%Y-%m-%d"),

        # ——— Wstęp
        "WSTEP": (
            "Archetypy to uniwersalne wzorce osobowości, które od wieków pomagają ludziom rozumieć świat i budować autentyczną tożsamość. "
            "Współczesna psychologia i marketing potwierdzają, że trafnie zdefiniowany archetyp jest potężnym narzędziem komunikacji, pozwalającym budować rozpoznawalność, zaufanie i emocjonalny kontakt. Czas wykorzystać to także w polityce! "
            "\n\nW polityce archetyp pomaga wyeksponować najważniejsze cechy lidera, porządkuje przekaz, wzmacnia spójność strategii oraz wyraźnie różnicuje kandydata na tle konkurencji. "
            "Analiza archetypów pozwala lepiej zrozumieć sposób odbioru polityka przez otoczenie, a co się z tym wiąże także motywacje i aspiracje. "
            "Wyniki badań archetypowych stanowią istotny fundament do tworzenia skutecznej narracji wyborczej, strategii wizerunkowej i komunikacji z wyborcami.\n\n"
            "W modelu przez nas opracowanym wykorzystano klasyfikację Mark and Pearson, obejmującą 12 uniwersalnych typów osobowościowych. "
            f"Raport przedstawia wyniki i profil archetypowy dla {p('GEN') or '—'} w oparciu o dane z przeprowadzonego badania. "
            "Badanie to pozwoliło zidentyfikować archetyp główny i wspierający, a więc dwa najważniejsze wzorce, które mogą wzmocnić jego pozycjonowanie. "
            "Zaprezentowano także trzeci w kolejności ważności — archetyp poboczny.\n\n"
            "Dzięki analizie archetypów można precyzyjnie dopasować komunikację do oczekiwań wyborców, podkreślić atuty, a także przewidzieć skuteczność strategii politycznej w dynamicznym środowisku publicznym. "),

        # ——— Tabela + radar + liczebność
        "TABELA_LICZEBNOSCI": archetype_table.to_dict('records') if archetype_table is not None else [],
        "RADAR_IMG": radar_image if radar_image is not None else "",
        "LICZEBNOSC_OSOB": (
            f"W badaniu udział wzięło {num_ankiet} {'osób' if (num_ankiet is None or num_ankiet != 1) else 'osoba'}."
            if num_ankiet is not None else ""
        ),

        # ——— Główny / wspierający / poboczny (bez zmian merytorycznych)
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
    panel_img_path=None,
    person: dict | None = None,
    gender_code: str = "M",
):
    doc = DocxTemplate(TEMPLATE_PATH)

    # Radar image
    if radar_img_path and os.path.exists(radar_img_path):
        radar_image = InlineImage(doc, radar_img_path, width=Mm(140))
    else:
        radar_image = ""

    # Panel image
    panel_image = InlineImage(doc, panel_img_path, width=Mm(140)) if panel_img_path and os.path.exists(panel_img_path) else ""

    # Ikony archetypów do Word (główny/wspierający/poboczny)
    ARCHETYPE_MAIN_ICON = arche_icon_inline_for_word(doc, main_type, gender_code, height_mm=18) if main_type else ""
    ARCHETYPE_AUX_ICON = arche_icon_inline_for_word(doc, second_type, gender_code, height_mm=18) if second_type else ""
    ARCHETYPE_SUPP_ICON = arche_icon_inline_for_word(doc, supplement_type, gender_code, height_mm=18) if supplement_type else ""

    # Grafiki palet kolorów
    ARCHETYPE_MAIN_PALETTE_IMG = palette_inline_for_word(doc, main.get("color_palette", []))
    ARCHETYPE_AUX_PALETTE_IMG = palette_inline_for_word(doc, second.get("color_palette", []))
    ARCHETYPE_SUPP_PALETTE_IMG = palette_inline_for_word(doc, supplement.get("color_palette", []))

    # ——— najważniejsze: przekaż person →
    context = build_word_context(
        main_type, second_type, supplement_type, features, main, second, supplement,
        mean_scores, radar_image, archetype_table, num_ankiet,
        person=person
    )

    # Wstrzyknięcie ikon i palet do szablonu DOCX
    context["ARCHETYPE_MAIN_ICON"] = ARCHETYPE_MAIN_ICON
    context["ARCHETYPE_AUX_ICON"] = ARCHETYPE_AUX_ICON
    context["ARCHETYPE_SUPP_ICON"] = ARCHETYPE_SUPP_ICON

    context["ARCHETYPE_MAIN_PALETTE_IMG"] = ARCHETYPE_MAIN_PALETTE_IMG
    context["ARCHETYPE_AUX_PALETTE_IMG"] = ARCHETYPE_AUX_PALETTE_IMG
    context["ARCHETYPE_SUPP_PALETTE_IMG"] = ARCHETYPE_SUPP_PALETTE_IMG

    # Logotypy do Worda
    context["ARCHETYPE_MAIN_BRANDS_IMG"] = build_brands_for_word(doc, main.get("example_brands", []), logos_dir=logos_dir, height_mm=7)
    context["ARCHETYPE_AUX_BRANDS_IMG"] = build_brands_for_word(doc, second.get("example_brands", []), logos_dir=logos_dir, height_mm=7)
    context["ARCHETYPE_SUPPLEMENT_BRANDS_IMG"] = build_brands_for_word(doc, supplement.get("example_brands", []), logos_dir=logos_dir, height_mm=7)

    context["PANEL_IMG"] = panel_image

    context["COLOR_RING_IMG"] = InlineImage(doc, "color_ring.png", width=Mm(70))

    doc.render(context)

    # (opcja) hiperłącza do osób – jak było
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
    import tempfile, os, shutil
    from io import BytesIO
    from pathlib import Path
    if sys.platform.startswith("win32"):
        # --- WINDOWS: bez zmian, Word + docx2pdf (honoruje osadzone fonty) ---
        import pythoncom
        from docx2pdf import convert
        with tempfile.TemporaryDirectory() as tmpdir:
            docx_path = os.path.join(tmpdir, "raport.docx")
            pdf_path = os.path.join(tmpdir, "raport.pdf")
            with open(docx_path, "wb") as f:
                f.write(docx_bytes_io.getbuffer())
            pythoncom.CoInitialize()
            convert(docx_path, pdf_path)
            with open(pdf_path, "rb") as f:
                return BytesIO(f.read())
    else:
        # --- LINUX: najpierw do-instaluj fonty do ~/.local/share/fonts, odśwież fontconfig ---
        with tempfile.TemporaryDirectory() as tmpdir:
            docx_path = os.path.join(tmpdir, "raport.docx")
            pdf_path = os.path.join(tmpdir, "raport.pdf")
            with open(docx_path, "wb") as f:
                f.write(docx_bytes_io.getbuffer())

            # 1) Skopiuj TTF-y do prywatnego katalogu fontów
            project_font_dir = Path(__file__).with_name("assets") / "fonts"
            user_font_dir = Path.home() / ".local" / "share" / "fonts" / "ap48"
            user_font_dir.mkdir(parents=True, exist_ok=True)
            if project_font_dir.exists():
                for src in project_font_dir.glob("*.ttf"):
                    dst = user_font_dir / src.name
                    try:
                        shutil.copyfile(src, dst)
                    except Exception:
                        pass

            # 2) Odśwież cache fontów
            try:
                import subprocess
                subprocess.run(["fc-cache", "-f", "-v"], check=False, capture_output=True)
            except Exception:
                pass  # jeśli fc-cache niedostępny w środowisku, i tak próbujemy dalej

            # 3) Konwersja LibreOffice
            try:
                result = subprocess.run([
                    "soffice", "--headless", "--convert-to", "pdf",
                    "--outdir", tmpdir, docx_path
                ], capture_output=True)
                if result.returncode != 0 or not os.path.isfile(pdf_path):
                    raise RuntimeError("LibreOffice PDF error: " + result.stderr.decode(errors="ignore"))
            except FileNotFoundError:
                raise RuntimeError("LibreOffice (soffice) nie jest dostępny w systemie.")
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

def palette_boxes_html(palette, color_name_map=COLOR_NAME_MAP):
    if not isinstance(palette, list) or not palette:
        return ""

    def label_for(code):
        name = color_name_map.get(str(code).upper(), str(code))
        return f"{name} ({code})"

    boxes = []

    for hexcode in palette:
            txt = "#111111" if not is_color_dark(hexcode) else "#FFFFFF"
            shadow = ""  # ← zero cienia pod tekstem
            boxes.append(
                f"<div class='ap-box' style='background:{hexcode};'>"
                f"<span style='color:{txt};'>{label_for(hexcode)}</span>"
                f"</div>"
            )
    return (
                "<style>"
                ".ap-palette{display:flex;gap:10px;flex-wrap:wrap;margin:8px 0 12px 0;}"
                ".ap-palette .ap-box{width:110px;height:65px;border-radius:8px;"
                "display:flex;align-items:center;justify-content:center;"
                "text-align:center;padding:6px;border:1px solid rgba(0,0,0,.08);"
                "box-shadow:none;}"  # ← usunięty cień
                ".ap-palette .ap-box span{font-weight:700;font-size:12.5px;line-height:1.25}"
                "@media (max-width:700px){ .ap-palette .ap-box{width:120px;height:76px} }"
                "</style>"
                "<div class='ap-palette'>" + "".join(boxes) + "</div>"
        )


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


def render_archetype_card(archetype_data, main=True, supplement=False, gender_code="M"):
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

    icon_html = arche_icon_img_html(archetype_data.get('name', ''), height_px=56)

    width_card = "70vw"
    text_color = "#222"
    if main and is_color_dark(bg_color):
        text_color = "#fff"
        tagline_color = "#FFD22F" if archetype_data.get('name', '').lower() == "bohater" else "#fffbea"

    # --- paleta kolorów: kwadraty z nazwą w środku ---
    color_palette = archetype_data.get('color_palette') or []
    color_boxes_html = palette_boxes_html(color_palette) if color_palette else ""

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
            <div style="margin-right:23px; margin-top:1px; flex-shrink:0;">{arche_icon_img_html(archetype_data.get('name', '?'), height_px=130, gender_code=gender_code)}</div>
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
                {color_boxes_html}
                {"<div style='margin-top:22px;font-weight:600;'>Pytania archetypowe:</div>" if questions else ""}
                {questions_html}
            </div>
        </div>
    """, unsafe_allow_html=True)

# ============ RESZTA PANELU: nagłówki, kolumny, eksporty, wykres, tabele respondentów ============

def show_report(sb, study: dict, wide: bool = True) -> None:
    # --- NOWE: płeć + mapowanie nazw do żeńskich ---
    gender_raw = (study.get("gender") or study.get("sex") or study.get("plec") or "").strip().lower()
    IS_FEMALE = gender_raw in {"k", "kobieta", "female", "f"}

    FEM_NAME_MAP = {
        "Władca": "Władczyni",
        "Bohater": "Bohaterka",
        "Mędrzec": "Mędrczyni",
        "Opiekun": "Opiekunka",
        "Kochanek": "Kochanka",
        "Błazen": "Komiczka",
        "Twórca": "Twórczyni",
        "Odkrywca": "Odkrywczyni",
        "Czarodziej": "Czarodziejka",
        "Towarzysz": "Towarzyszka",
        "Niewinny": "Niewinna",
        "Buntownik": "Buntowniczka",
    }

    def disp_name(name: str) -> str:
        return FEM_NAME_MAP.get(name, name) if IS_FEMALE else name

    # personalizacja z przekazanego rekordu
    personNom = f"{study.get('first_name_nom') or study.get('first_name','')} {study.get('last_name_nom') or study.get('last_name','')}".strip()
    personGen = f"{study.get('first_name_gen') or (study.get('first_name_nom') or study.get('first_name',''))} {study.get('last_name_gen') or (study.get('last_name_nom') or study.get('last_name',''))}".strip()

    # ⬇️ NOWE – wszystkie pozostałe przypadki
    def _join(a, b):
        return f"{(a or '').strip()} {(b or '').strip()}".strip()

    personDat  = _join(study.get("first_name_dat"),  study.get("last_name_dat"))
    personAcc  = _join(study.get("first_name_acc"),  study.get("last_name_acc"))
    personInst = _join(study.get("first_name_ins"),  study.get("last_name_ins"))
    personLoc  = _join(study.get("first_name_loc"),  study.get("last_name_loc"))
    personVoc  = _join(study.get("first_name_voc"),  study.get("last_name_voc"))

    study_id = study["id"]
    data = load(study_id)

    # ❗️ZBIERAMY WSZYSTKIE PRZYPADKI DO SŁOWNIKA DLA WORDA
    person = {
        "NOM": personNom,
        "GEN": personGen,
        "DAT": personDat,
        "ACC": personAcc,
        "INS": personInst,
        "LOC": personLoc,
        "VOC": personVoc,
        "CITY_NOM": (study.get("city_nom") or "").strip(),
    }

    # ... tu dalej Twój kod (generowanie wykresów, budowanie contextu itd.)

    num_ankiet = len(data) if not data.empty else 0

    header_col1, header_col2 = st.columns([0.77, 0.23])
    with header_col1:
        st.markdown(
            f"""
            <div style="font-size:2.3em; font-weight:bold; background:#1a93e3; color:#fff; 
                padding:14px 32px 10px 24px; border-radius:2px; width:fit-content; display:inline-block;">
                Archetypy {personGen} – panel administratora
            </div>
            """,
            unsafe_allow_html=True
        )
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

            # --- kolory heurystyczne dla tej odpowiedzi ---
            col_scores = color_scores_from_answers(row["answers"])
            col_perc = color_percents_from_scores(col_scores)

            main_type, second_type, supplement_type = pick_top_3_archetypes(arcsums, ARCHE_NAMES_ORDER)
            main = archetype_extended.get(main_type, {})
            second = archetype_extended.get(second_type, {}) if second_type != main_type else {}
            supplement = archetype_extended.get(supplement_type, {}) if supplement_type not in [main_type, second_type] else {}

            # wersje do wyświetlania – podmień 'name' na żeńskie, jeśli IS_FEMALE
            main_disp = dict(main)
            main_disp["name"] = disp_name(main.get("name", main_type or ""))

            second_disp = dict(second)
            if second:
                second_disp["name"] = disp_name(second.get("name", second_type or ""))

            supplement_disp = dict(supplement)
            if supplement:
                supplement_disp["name"] = disp_name(supplement.get("name", supplement_type or ""))

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
                **{f"Kolor_{k}": v for k, v in col_scores.items()},
                **{f"Kolor_{k}_%": v for k, v in col_perc.items()},
            })

        results_df = pd.DataFrame(results)

        if not results_df.empty and "Czas ankiety" in results_df.columns:

            results_df = results_df.sort_values("Czas ankiety", ascending=True)

            st.markdown(f'<div style="font-size:2.1em;font-weight:600;margin-bottom:22px;">Informacje na temat archetypów {personGen}</div>', unsafe_allow_html=True)

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
                st.markdown(
                    '<div class="section-title mt-28">Liczebność archetypów głównych, wspierających i pobocznych</div>',
                    unsafe_allow_html=True)
                archetype_table = pd.DataFrame({
                    "Archetyp": [f"{get_emoji(n)} {disp_name(n)}" for n in archetype_names],
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
                        r'(<tr[^>]*>)(\s*<td style="text-align:center")',
                        lambda m: m.group(1) + m.group(2).replace('text-align:center', 'text-align:left;width:24%;"'), html
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
                    label = disp_name(n)
                    if n == main_type:
                        theta_labels.append(f"<b><span style='color:red;'>{label}</span></b>")
                    elif n == second_type:
                        theta_labels.append(f"<b><span style='color:#FFD22F;'>{label}</span></b>")
                    elif n == supplement_type:
                        theta_labels.append(f"<b><span style='color:#40b900;'>{label}</span></b>")
                    else:
                        theta_labels.append(f"<span style='color:#656565;'>{label}</span>")
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
                st.markdown(f'<div style="font-size:1.28em;font-weight:650;margin-bottom:13px; text-align:center;">Profil archetypów {personGen}</div>', unsafe_allow_html=True)
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
                # PRZEZROCZYSTE TŁO RADARU
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    polar=dict(
                        bgcolor="rgba(0,0,0,0)",
                        radialaxis=dict(visible=True, range=[0, 20]),
                        angularaxis=dict(tickfont=dict(size=19), tickvals=archetype_names, ticktext=theta_labels),
                    ),
                    showlegend=False,
                    width=550, height=550, margin=dict(l=20, r=20, t=32, b=32),
                )
                fig.write_image("radar.png", scale=4)
                st.plotly_chart(fig, use_container_width=True)

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

            # --- Heurystyczna analiza koloru (bąbelki OUT; słupki po LEWEJ; prawa pusta) ---
            color_pcts = calc_color_percentages_from_df(data)

            st.markdown("<div style='height:34px;'></div>", unsafe_allow_html=True)
            left_col, right_col = st.columns([0.58, 0.42], gap="large")

            with left_col:
                # tylko słupki
                st.markdown(
                    "<div class='section-title section-title--padTop'>Udział kolorów – wykres słupkowy</div>",
                    unsafe_allow_html=True
                )
                components.html(
                    color_progress_bars_html(color_pcts, order="desc"),
                    height=360,
                    scrolling=False
                )

                # opisy ZOSTAJĄ — dominujący kolor + opis
                dom_name, dom_pct = max(color_pcts.items(), key=lambda kv: kv[1])
                st.markdown(
                    f"<div style='text-align:center; font:700 20px/1.25 \"Segoe UI\",system-ui; color:#222; margin: 6px 0 -10px;'>"
                    f"Dominujący kolor: <span style='color:{COLOR_HEX[dom_name]}'>{dom_name}</span></div>",
                    unsafe_allow_html=True
                )
                st.markdown(color_explainer_one_html(dom_name, dom_pct), unsafe_allow_html=True)

            # prawa kolumna — NA RAZIE PUSTA (rezerwacja miejsca na inny wykres)
            # with right_col:
            #     st.markdown("&nbsp;", unsafe_allow_html=True)

            # tylko dominujący kolor
            dom_name, dom_pct = max(color_pcts.items(), key=lambda kv: kv[1])

            # zapisz PNG z dużego pierścienia do użycia w Wordzie
            big_color = max(color_pcts.items(), key=lambda kv: kv[1])[0]
            big_svg = _ring_svg(color_pcts[big_color], COLOR_HEX[big_color], size=600, stroke=48)
            with open("color_ring.svg", "w", encoding="utf-8") as f:
                f.write(big_svg)
            cairosvg.svg2png(url="color_ring.svg", write_to="color_ring.png")

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
            st.markdown("<div id='opisy'></div>", unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:2.1em;font-weight:700;margin-bottom:16px;">Archetyp główny {personGen}</div>', unsafe_allow_html=True)
            render_archetype_card(main_disp, main=True, gender_code=("K" if IS_FEMALE else "M"))

            if second_type and second_type != main_type:
                st.markdown("<div style='height:35px;'></div>", unsafe_allow_html=True)
                st.markdown("""<hr style="height:1.1px; border:none; background:#ddd; margin-top:6px; margin-bottom:18px;" />""", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size:1.63em;font-weight:700;margin-bottom:15px;'>Archetyp wspierający {personGen}</div>", unsafe_allow_html=True)
                render_archetype_card(second_disp, main=False, gender_code=("K" if IS_FEMALE else "M"))

            if supplement_type and supplement_type not in [main_type, second_type]:
                st.markdown("<div style='height:35px;'></div>", unsafe_allow_html=True)
                st.markdown("""<hr style="height:1.1px; border:none; background:#ddd; margin-top:6px; margin-bottom:18px;" />""", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size:1.63em;font-weight:700;margin-bottom:15px;'>Archetyp poboczny {personGen}</div>", unsafe_allow_html=True)
                render_archetype_card(supplement_disp, main=False, gender_code=("K" if IS_FEMALE else "M"))

            st.markdown("<div id='raport'></div>", unsafe_allow_html=True)

            st.markdown(f"""
            <div style='height:44px;'></div>
            <hr style="height:1px; border:none; background:#e5e5e5; margin-bottom:26px;" />
            <div style="font-size:1.2em; font-weight:600; margin-bottom:23px;">
                Pobierz raporty archetypu {personGen}
            </div>
            """, unsafe_allow_html=True)

            # GENEROWANIE OBRAZU PANELU DYNAMICZNIE
            idx_main = archetype_name_to_img_idx(main_type)
            idx_aux = archetype_name_to_img_idx(second_type) if second_type != main_type else None
            idx_supplement = archetype_name_to_img_idx(supplement_type) if supplement_type not in [main_type, second_type] else None

            panel_img = compose_archetype_highlight(idx_main, idx_aux, idx_supplement)
            panel_img_path = f"panel_{(main_type or '').lower()}_{(second_type or '') and second_type.lower()}_{(supplement_type or '') and supplement_type.lower()}.png"
            panel_img.save(panel_img_path)

            # ----------- EKSPORT WORD I PDF - pionowo, z ikonkami -----------
            docx_buf = export_word_docxtpl(
                main_type,
                second_type,
                supplement_type,
                archetype_features,
                main_disp,
                second_disp,
                supplement_disp,
                radar_img_path="radar.png",
                archetype_table=archetype_table,
                num_ankiet=num_ankiet,
                panel_img_path=panel_img_path,
                person=person,
                gender_code=("K" if IS_FEMALE else "M"),
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

            st.markdown("<div id='tabela'></div>", unsafe_allow_html=True)

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
