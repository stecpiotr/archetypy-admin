# admin_dashboard.py - raporty archetypów

import pandas as pd
import streamlit as st
import psycopg2
import sqlalchemy as sa

def _sa_engine():
    """
    Silnik SQLAlchemy do Postgresa z SSL. Używamy go w pd.read_sql.
    Wymaga pakietu SQLAlchemy (pip install SQLAlchemy).
    """
    url = sa.URL.create(
        "postgresql+psycopg2",
        username=st.secrets["db_user"],
        password=st.secrets["db_pass"],
        host=st.secrets["db_host"],
        port=int(st.secrets.get("db_port", 5432)),
        database=st.secrets["db_name"],
        query={"sslmode": "require"},
    )
    return sa.create_engine(url, pool_pre_ping=True)

import ast
import plotly.graph_objects as go
from fpdf import FPDF
import unicodedata
import colorsys
import requests
from PIL import Image, ImageDraw
import io
import re
import html
from textwrap import dedent
from datetime import datetime
import pytz
from functools import lru_cache
from urllib.parse import quote
from docx.shared import Pt
import os
from pathlib import Path
from docxtpl import DocxTemplate, InlineImage
from docx import Document
from io import BytesIO
import tempfile
import warnings
warnings.filterwarnings(
    "ignore",
    message="pkg_resources is deprecated as an API",
    category=UserWarning,
    module="docxcompose.properties",
)

import streamlit.components.v1 as components
import matplotlib.pyplot as plt
from matplotlib.offsetbox import OffsetImage, AnnotationBbox
import numpy as np
from archetype_docx_loader import load_archetype_extended

import sys
if sys.platform.startswith("linux"):
    import subprocess
else:
    from docx2pdf import convert

TEMPLATE_PATH = "ap48_raport_template.docx"
TEMPLATE_PATH_NOSUPP = "ap48_raport_template_nosupp.docx"  # szablon bez sekcji archetypu pobocznego
logos_dir = str(Path(__file__).with_name("logos_local"))

import plotly.io as pio
import shutil, os

# ====== Kaleido + Chrome/Chromium hardening (serwery/headless) ======
# Szukamy przeglądarki w popularnych lokalizacjach i nazwach (snap, deb, wrappery)
_CANDIDATES = [
    "/usr/bin/chromium-browser",
    "/usr/bin/chromium",
    "/snap/bin/chromium",            # snap (czasem PATH nie ma /snap/bin)
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "chromium-browser", "chromium", "google-chrome", "chrome"
]

_chrome = None
for c in _CANDIDATES:
    if os.path.isabs(c):
        if os.path.exists(c):
            _chrome = c; break
    else:
        p = shutil.which(c)
        if p:
            _chrome = p; break

# Ustaw ścieżkę Chromium dla Kaleido (jeśli API jest dostępne w tej wersji plotly)
try:
    if _chrome and hasattr(pio, "kaleido") and hasattr(pio.kaleido, "scope"):
        pio.kaleido.scope.chromium_executable = _chrome
        pio.kaleido.scope.chromium_args = ["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]
except Exception:
    pass

import os, streamlit as st
def _build_sha():
    try: return open(os.path.join(os.path.dirname(__file__), ".deployed_sha")).read().strip()[:7]
    except Exception: return "dev"
st.sidebar.caption(f"Build: {_build_sha()}")


def _logo_norm_key(value: str) -> str:
    if value is None:
        return ""
    normalized = unicodedata.normalize("NFKD", str(value)).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower().replace("&", "and")
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")
    return normalized


@lru_cache(maxsize=16)
def _logo_lookup_index(logos_dir: str) -> dict[str, str]:
    index: dict[str, str] = {}
    if not logos_dir or not os.path.isdir(logos_dir):
        return index

    for filename in os.listdir(logos_dir):
        if os.path.splitext(filename)[1].lower() not in {".svg", ".png", ".jpg", ".jpeg", ".webp"}:
            continue
        stem = os.path.splitext(filename)[0]
        abs_path = os.path.join(logos_dir, filename)
        keys = {
            stem.casefold(),
            stem.replace("-", "").casefold(),
            _logo_norm_key(stem),
            re.sub(r"[^a-z0-9]+", "", _logo_norm_key(stem)),
        }
        for key in keys:
            if key:
                index.setdefault(key, abs_path)
    return index


LOGO_BRAND_ALIASES = {
    "Victoria’s Secret": "Victorias Secrets",
    "Victoria's Secret": "Victorias Secrets",
    "PKN ORLEN": "Orlen",
    "PZU SA": "PZU",
}


def get_logo_svg_path(brand_name, logos_dir=None):
    if logos_dir is None:
        logos_dir = str(Path(__file__).with_name("logos_local"))

    if not brand_name:
        return None

    raw = str(brand_name).strip()
    if not raw:
        return None

    raw_variants = [raw]
    alias = LOGO_BRAND_ALIASES.get(raw)
    if alias:
        raw_variants.append(alias)

    # Próby "po staremu" (kompatybilność)
    candidate_filenames = []
    for variant in raw_variants:
        base_kebab = (
            variant.lower()
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
            .replace("ś", "s")
        )
        base_flat = variant.lower().replace(" ", "").replace("'", "").replace("’", "")
        for ext in (".svg", ".png", ".jpg", ".jpeg", ".webp"):
            candidate_filenames.append(base_kebab + ext)
            candidate_filenames.append(base_flat + ext)

    for filename in candidate_filenames:
        path = os.path.join(logos_dir, filename)
        if os.path.exists(path):
            return path

    # Fallback: dopasowanie odporne na case/diakrytyki/znaki specjalne.
    lookup = _logo_lookup_index(logos_dir)
    probe_keys = []
    for variant in raw_variants:
        probe_keys.extend(
            [
                variant.casefold(),
                variant.replace(" ", "").casefold(),
                _logo_norm_key(variant),
                re.sub(r"[^a-z0-9]+", "", _logo_norm_key(variant)),
            ]
        )
    for key in probe_keys:
        if key in lookup:
            return lookup[key]

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


def _person_norm_key(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode("ascii")
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized.lower())
    return re.sub(r"\s+", " ", normalized).strip()


PERSON_CANONICAL_BY_NORM = {_person_norm_key(name): name for name in person_wikipedia_links}
PERSON_LINK_BY_NORM = {_person_norm_key(name): url for name, url in person_wikipedia_links.items()}


def canonical_person_name(name: str) -> str:
    clean = str(name or "").strip().strip(".")
    if clean in person_wikipedia_links:
        return clean
    return PERSON_CANONICAL_BY_NORM.get(_person_norm_key(clean), clean)


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
    canonical = canonical_person_name(name)
    url = person_wikipedia_links.get(canonical) or PERSON_LINK_BY_NORM.get(_person_norm_key(name))
    if url:
        return f"<a href='{url}' target='_blank'>{canonical}</a>"
    return canonical

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

def _load_arche_icon_for_mpl(name: str, size_px: int = 160, tint: str = "#3B82F6", as_array: bool = True):
    """
    Wczytuje ikonę archetypu (PNG/SVG), zachowuje proporcje (contain) bez rozciągania,
    osadza na kwadratowym, przezroczystym płótnie i barwi na `tint`.
    Zwraca numpy array (domyślnie) albo PIL.Image gdy as_array=False.
    """
    from pathlib import Path
    from io import BytesIO
    from PIL import Image, ImageOps, ImageColor

    try:
        import numpy as np  # potrzebne, gdy chcemy array
    except Exception:
        np = None

    # --- Twoje utilsy/ścieżki (zostaw jak masz) ---
    base = base_masc_from_any(name)
    slug = ARCHETYPE_BASE_SLUGS.get(base, _slug_pl(base))
    svg = ARCHE_STACKED_ICON_DIR / f"{slug}.svg"
    png = ARCHE_STACKED_ICON_DIR / f"{slug}.png"
    # ------------------------------------------------

    # Pillow 10+
    RESAMPLE = getattr(Image, "Resampling", Image).LANCZOS

    canvas = Image.new("RGBA", (size_px, size_px), (255, 255, 255, 0))

    try:
        if png.exists():
            im = Image.open(png).convert("RGBA")
        elif svg.exists():
            import cairosvg
            buf = cairosvg.svg2png(url=str(svg), output_width=size_px * 4, output_height=size_px * 4)
            im = Image.open(BytesIO(buf)).convert("RGBA")
        else:
            return None

        # Bez deformacji: "contain" do kwadratu
        im = ImageOps.contain(im, (size_px, size_px), RESAMPLE)

        # Tint: bierzemy tylko alpha z ikony i wlewamy jednolity kolor pod maskę
        color_rgb = ImageColor.getrgb(tint)
        alpha = im.getchannel("A")
        colored = Image.new("RGBA", im.size, color_rgb + (0,))
        colored.putalpha(alpha)

        # Wklejamy na środek kwadratowego, przezroczystego płótna
        x = (size_px - colored.width) // 2
        y = (size_px - colored.height) // 2
        canvas.alpha_composite(colored, (x, y))

        if as_array:
            if np is None:
                raise RuntimeError("numpy is required when as_array=True")
            return np.array(canvas)
        return canvas

    except Exception:
        return None


def make_stacked_bar_png_for_word(
    archetype_names: list[str],
    counts_main: dict[str, int],
    counts_aux: dict[str, int],
    counts_supp: dict[str, int],
    out_path: str = "archetypes_stacked.png",
):
    import os
    import numpy as np
    import matplotlib as mpl
    import matplotlib.pyplot as plt
    from matplotlib import ticker
    from matplotlib.offsetbox import OffsetImage, AnnotationBbox
    from matplotlib import font_manager as fm
    from PIL import Image, ImageOps  # do „kwadratowania” ikon

    # ===== POKRĘTŁA =====
    FIG_SCALE  = 0.90
    FONT_SCALE = 1.25
    DPI = 300

    # Roboto Condensed
    FONT_DIR = "assets/fonts"
    for fname in ("RobotoCondensed-Regular.ttf", "RobotoCondensed-Bold.ttf"):
        p = os.path.join(FONT_DIR, fname)
        if os.path.exists(p):
            fm.fontManager.addfont(p)
    mpl.rcParams["font.family"] = "Roboto Condensed"

    base_fs = 9 * FONT_SCALE
    mpl.rcParams.update({
        "font.size": base_fs,
        "axes.labelsize": 0.85 * base_fs,
        "xtick.labelsize": 0.70 * base_fs,
        "ytick.labelsize": 0.85 * base_fs,
        "legend.fontsize": 0.80 * base_fs,
        "pdf.fonttype": 42, "ps.fonttype": 42,
    })

    # ===== Dane =====
    names = list(archetype_names)
    m = np.array([int(counts_main.get(n, 0) or 0) for n in names], dtype=int)
    a = np.array([int(counts_aux.get(n, 0) or 0)  for n in names], dtype=int)
    s = np.array([int(counts_supp.get(n, 0) or 0) for n in names], dtype=int)
    t = m + a + s

    order = np.argsort(-t)
    names, m, a, s, t = [[arr[i] for i in order] if isinstance(arr, list) else arr[order]
                         for arr in (names, m, a, s, t)]
    y = np.arange(len(names))

    # ===== Figura =====
    fig_w = 8.0 * FIG_SCALE
    HEIGHT_SCALE = 1.03  # wysokość wykresu
    fig_h = HEIGHT_SCALE * ((0.55 * FIG_SCALE) * len(names) + 0.9)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=DPI)
    fig.patch.set_alpha(0)
    ax.set_facecolor((1,1,1,0))
    fig.subplots_adjust(left=0.30, right=0.975, top=0.83, bottom=0.05)

    # ===== Osi / kolory =====
    c_main = COLOR_HEX["Czerwony"]
    c_aux  = COLOR_HEX["Żółty"]
    c_supp = COLOR_HEX["Zielony"]
    axis_col = "#4B5563"
    grid_col = "#E5E7EB"

    ax.xaxis.set_ticks_position("top")
    ax.xaxis.set_label_position("top")
    ax.set_xlabel("Liczba wskazań", fontsize=8.5, color="#8A94A6", labelpad=12)   # większy odstęp
    ax.xaxis.set_label_coords(0.5, 1.06)                             # wyżej nad osią
    ax.xaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    ax.grid(axis="x", color=grid_col, linewidth=0.7)
    ax.set_axisbelow(True)

    ax.tick_params(axis="x", colors=axis_col, labelsize=0.70 * base_fs, length=3, pad=2)
    ax.tick_params(axis="y", colors="#111827", pad=2)

    ax.spines["top"].set_color(axis_col)
    ax.spines["left"].set_color(axis_col)
    ax.spines["top"].set_linewidth(1.0)
    ax.spines["left"].set_linewidth(1.0)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_visible(False)

    # ===== Słupki =====
    bar_h = 0.70
    ax.barh(y, m, height=bar_h, color=c_main, edgecolor="white", linewidth=0.6, label="Główny")
    ax.barh(y, a, left=m, height=bar_h, color=c_aux,  edgecolor="white", linewidth=0.6, label="Wspierający")
    ax.barh(y, s, left=m+a, height=bar_h, color=c_supp, edgecolor="white", linewidth=0.6, label="Poboczny")

    ax.set_yticks(y)
    ax.set_yticklabels(names, ha="right")
    for lbl in ax.get_yticklabels():
        lbl.set_x(-0.012)  # ciut bliżej osi

    # ===== Ikony – mniejsze, dalej w lewo, zawsze kwadrat =====
    ICON_PX   = int(84 * FIG_SCALE)   # rozdzielczość pola
    ICON_ZOOM = 0.30 * FIG_SCALE      # faktyczna wielkość na wykresie
    ICON_X    = -0.17                 # bardziej ujemne = dalej w lewo

    for i, nme in enumerate(names):
        icon_arr = _load_arche_icon_for_mpl(nme, size_px=ICON_PX)
        if icon_arr is None:
            continue
        im = Image.fromarray(icon_arr)
        im = ImageOps.pad(im, (ICON_PX, ICON_PX), color=(255, 255, 255, 0), centering=(0.5, 0.5))
        icon_arr = np.array(im)

        img = OffsetImage(icon_arr, zoom=ICON_ZOOM)  # isotropowe skalowanie (brak spłaszczania)
        ab = AnnotationBbox(img, (ICON_X, i),
                            xycoords=("axes fraction", "data"),
                            box_alignment=(1.0, 0.5),
                            frameon=False, annotation_clip=False)
        ax.add_artist(ab)

    # ===== Etykiety wewnątrz =====
    def annotate_segment(left_arr, vals):
        for row, val in enumerate(vals):
            if val <= 0:
                continue
            ax.text(left_arr[row] + val/2.0, row, str(int(val)),
                    color="white", ha="center", va="center",
                    fontsize=0.65 * base_fs)

    annotate_segment(np.zeros_like(m, float), m)
    annotate_segment(m, a)
    annotate_segment(m + a, s)

    # ===== Suma na końcu =====
    gap = max(0.02 * (t.max() if t.max() > 0 else 1), 0.10)
    for i in range(len(y)):
        ax.text(float(t[i]) + gap, i, str(int(t[i])),
                color="#374151", ha="left", va="center",
                fontsize=0.80 * base_fs, fontweight="bold")

    # ===== Legenda =====
    leg = ax.legend(
        loc="upper center",
        bbox_to_anchor=(0, -0.03, 1, 0),  # (x, y, width, height) w ułamku osi
        #mode="expand",  # rozkłada etykiety równomiernie na całą szerokość
        ncol=3,
        frameon=False,
        handlelength=1.5,  # dłuższe próbki
        handletextpad=0.6,  # odstęp próbka–tekst
        columnspacing=3.0,  # większy rozstrzał między kolumnami
        borderaxespad=0.0
    )

    fig.subplots_adjust(bottom=0.085)  # ciaśniej na dole

    ax.invert_yaxis()
    fig.savefig(out_path, dpi=DPI, bbox_inches="tight", pad_inches=0.02, transparent=True)
    plt.close(fig)
    return out_path


# --- Generowanie grafiki z paletą kolorów do Word ---
def _luma(hexcode: str) -> float:
    h = hexcode.lstrip('#')
    if len(h) == 3:
        h = ''.join(c*2 for c in h)
    r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
    return 0.2126*r + 0.7152*g + 0.0722*b


def make_palette_png(
    palette: list[str],
    target_width_mm: float = 160,   # szerokość obrazka pod Worda
    cols: int = 5,                  # ile kafelków w rzędzie
    tile_w_mm: float = 36,          # SZEROKOŚĆ kafelka (mm) — ręcznie
    tile_h_mm: float = 28,          # WYSOKOŚĆ kafelka (mm) — ręcznie
    pad_mm: float = 6,
    gap_mm: float = 6,
    corner_mm: float = 3,           # zaokrąglenia rogów
    dpi: int = 300,
    name_font_px: int | None = None,  # ROZMIAR czcionki nazwy (px) — ręcznie
    hex_font_px:  int | None = None,  # ROZMIAR czcionki (#HEX) (px) — ręcznie
):
    if not palette:
        return None

    from PIL import Image, ImageDraw, ImageFont
    import math

    def _mm_to_px(mm): return int(round(mm * dpi / 25.4))

    W      = _mm_to_px(target_width_mm)
    pad    = _mm_to_px(pad_mm)
    gap    = _mm_to_px(gap_mm)
    corner = _mm_to_px(corner_mm)

    cell_w = _mm_to_px(tile_w_mm)
    cell_h = _mm_to_px(tile_h_mm)

    # policz rzędy na podstawie liczby elementów i kolumn
    n    = len(palette)
    rows = math.ceil(n / cols)

    # gdy szerokość 5×kafelek + przerwy przekracza obraz — zmniejsz cell_w proporcjonalnie
    total_w = 2*pad + cols*cell_w + (cols-1)*gap
    if total_w > W:
        scale = (W - 2*pad - (cols-1)*gap) / (cols*cell_w)
        cell_w = int(cell_w * scale)
        cell_h = int(cell_h * scale)

    H = 2*pad + rows*cell_h + (rows-1)*gap

    img = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    drw = ImageDraw.Draw(img)

    # FONTY — ręcznie, albo proporcjonalnie do wysokości kafelka
    def _font(paths, size):
        for p in paths:
            try: return ImageFont.truetype(p, size)
            except: pass
        return ImageFont.load_default()

    # --- STAŁE rozmiary czcionek (bez auto-fit) ---
    NAME_FONT_PX_DEFAULT = 26  # ← rozmiar NAZWY
    HEX_FONT_PX_DEFAULT = 18  # ← rozmiar #HEX

    NAME_FONT_PX = name_font_px if name_font_px is not None else NAME_FONT_PX_DEFAULT
    HEX_FONT_PX = hex_font_px if hex_font_px is not None else HEX_FONT_PX_DEFAULT

    # Jeśli chcesz nazwę pogrubioną, zostaw -Bold; jeśli zwykłą, zamień na Regular.
    name_font = _font(
        [
            "assets/fonts/RobotoCondensed-Bold.ttf",
            "assets/fonts/ArialNovaCond-Bold.ttf",
            "DejaVuSans-Bold.ttf",
        ],
        NAME_FONT_PX,
    )

    hex_font = _font(
        [
            "assets/fonts/RobotoCondensed-Regular.ttf",
            "assets/fonts/ArialNovaCond.ttf",
            "DejaVuSans.ttf",
        ],
        HEX_FONT_PX,
    )

    def _luma(hexcode: str) -> float:
        h = hexcode.lstrip('#')
        if len(h) == 3: h = ''.join(c*2 for c in h)
        r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
        return 0.2126*r + 0.7152*g + 0.0722*b

    def ellipsize_two_lines(text: str, max_w: int) -> list[str]:
        words = text.split()
        if not words: return [text]
        lines, cur = [], ""
        for w in words:
            test = (cur + " " + w).strip()
            if drw.textlength(test, font=name_font) <= max_w or not cur:
                cur = test
            else:
                lines.append(cur); cur = w
            if len(lines) == 1 and drw.textlength(cur, font=name_font) > max_w:
                while drw.textlength(cur + "…", font=name_font) > max_w and len(cur) > 1:
                    cur = cur[:-1]
                cur += "…"
        lines.append(cur)
        if len(lines) > 2:
            first, second = lines[0], " ".join(lines[1:])
            while drw.textlength(second + "…", font=name_font) > max_w and len(second) > 1:
                second = second[:-1]
            lines = [first, second + "…"]
        return lines[:2]

    for i, hexcode in enumerate(palette):
        r, c = divmod(i, cols)
        x0 = pad + c * (cell_w + gap)
        y0 = pad + r * (cell_h + gap)
        x1 = x0 + cell_w
        y1 = y0 + cell_h

        drw.rounded_rectangle([x0, y0, x1, y1], radius=corner, fill=hexcode)

        txt_col = (255, 255, 255) if _luma(hexcode) < 110 else (17, 17, 17)

        from_name = COLOR_NAME_MAP.get(str(hexcode).upper(), str(hexcode).upper())
        max_w = cell_w - _mm_to_px(6)
        lines = ellipsize_two_lines(from_name, max_w)

        # oblicz wysokości
        name_h = sum(drw.textbbox((0,0), ln, font=name_font)[3] - drw.textbbox((0,0), ln, font=name_font)[1] for ln in lines)
        gap_y  = _mm_to_px(1.2)
        hex_txt = f"({str(hexcode).upper()})"
        hb  = drw.textbbox((0,0), hex_txt, font=hex_font)
        hex_h = hb[3]-hb[1]

        total_h = name_h + gap_y + hex_h
        base_y  = y0 + (cell_h - total_h)//2
        cx      = x0 + cell_w//2

        # nazwy (wyśrodkowane)
        cur_y = base_y
        for ln in lines:
            nb = drw.textbbox((0,0), ln, font=name_font)
            nw = nb[2]-nb[0]
            drw.text((cx - nw/2, cur_y), ln, font=name_font, fill=txt_col)
            cur_y += nb[3]-nb[1]

        # hex (wyśrodkowany)
        drw.text((cx - (hb[2]-hb[0])/2, cur_y + gap_y), hex_txt, font=hex_font, fill=txt_col)

    out = BytesIO()
    img.save(out, "PNG"); out.seek(0)
    return out


def palette_inline_for_word(
    doc, palette: list[str],
    width_mm: float = 160,
    cols: int = 4,
    tile_w_mm: float = 36,
    tile_h_mm: float = 20,
    name_font_px: int = 38,
    hex_font_px: int = 34,
    gap_mm: float = 5,  # ← odstęp między kaflami
    pad_mm: float = 3,  # ← zewnętrzny margines obrazka
):
    png = make_palette_png(
        palette,
        target_width_mm=width_mm,
        cols=cols,
        tile_w_mm=tile_w_mm,
        tile_h_mm=tile_h_mm,
        name_font_px=name_font_px,
        hex_font_px=hex_font_px,
        pad_mm=pad_mm,
        gap_mm=gap_mm,
    )
    return InlineImage(doc, png, width=Mm(width_mm)) if png else ""

# === Logo → kafelek PNG o stałym rozmiarze (pod Word) ===
def _mm_to_px_logo(mm: float, dpi: int = 300) -> int:
    return int(round(mm * dpi / 25.4))

def _svg_viewbox_ratio(svg_path: str) -> float | None:
    """Spróbuj odczytać proporcje (szer/wys) ze viewBox lub width/height w pliku SVG."""
    try:
        import re
        with open(svg_path, "r", encoding="utf-8", errors="ignore") as f:
            s = f.read()
        m = re.search(r'viewBox\s*=\s*"([\d.\s-]+)"', s)
        if m:
            nums = [float(x) for x in m.group(1).split()]
            if len(nums) == 4 and nums[3] > 0:
                w, h = nums[2], nums[3]
                if h > 0:
                    return w / h
        mw = re.search(r'width\s*=\s*"([\d.]+)', s)
        mh = re.search(r'height\s*=\s*"([\d.]+)', s)
        if mw and mh:
            w, h = float(mw.group(1)), float(mh.group(1))
            if h > 0:
                return w / h
    except Exception:
        pass
    return None

def make_logo_tile_bytes(
    path: str,
    slot_w_mm: float = 25.0,     # szerokość kafelka (identyczna dla WSZYSTKICH)
    slot_h_mm: float = 21.0,     # wysokość kafelka (identyczna dla WSZYSTKICH)
    pad_mm: float = 10.0,         # wewnętrzny margines
    dpi: int = 300,
    bg_rgba=(255, 255, 255, 0)   # tło przezroczyste (PNG z alfą)
) -> bytes:
    """
    Renderuje logo (SVG/PNG) na płótno o stałym rozmiarze.
    Skalowanie proporcjonalne, centrowanie, padding. Zwraca bytes PNG.
    """
    from PIL import Image, ImageOps
    import os
    from io import BytesIO

    slot_w_px = _mm_to_px_logo(slot_w_mm, dpi)
    slot_h_px = _mm_to_px_logo(slot_h_mm, dpi)
    pad_px    = _mm_to_px_logo(pad_mm, dpi)
    box_w = max(1, slot_w_px - 2 * pad_px)
    box_h = max(1, slot_h_px - 2 * pad_px)

    ext = os.path.splitext(path)[1].lower()
    if ext == ".svg":
        # (opcjonalnie) dopasuj rasteryzację pod aspekt
        ar = _svg_viewbox_ratio(path) or 1.0
        # wyjściowy „cel” w pikselach (zmniejszamy aliasing)
        if ar >= 1.0:
            out_w = box_w
            out_h = max(1, int(round(out_w / ar)))
            if out_h > box_h:
                out_h = box_h
                out_w = max(1, int(round(out_h * ar)))
        else:
            out_h = box_h
            out_w = max(1, int(round(out_h * ar)))
            if out_w > box_w:
                out_w = box_w
                out_h = max(1, int(round(out_w / ar)))

        # rasteryzacja SVG → PNG (bez wymiarów – i tak dociśniemy contain)
        png_bytes = svg_to_png_bytes(path)
        im = Image.open(BytesIO(png_bytes)).convert("RGBA")
        im = ImageOps.contain(im, (out_w, out_h))
    else:
        im = Image.open(path).convert("RGBA")
        im = ImageOps.contain(im, (box_w, box_h))

    tile = Image.new("RGBA", (slot_w_px, slot_h_px), bg_rgba)
    x = (slot_w_px - im.width) // 2
    y = (slot_h_px - im.height) // 2
    tile.alpha_composite(im, (x, y))

    out = BytesIO()
    tile.save(out, "PNG")
    return out.getvalue()

def build_brands_for_word(
    doc,
    brand_list,
    logos_dir,
    slot_w_mm: float = 35.0,   # szerokość kafelka w Wordzie
    slot_h_mm: float = 21.0,   # wysokość kafelka w Wordzie
    pad_mm: float = 10.0,
    dpi: int = 300
):
    """
    Zwraca listę {brand, logo}, gdzie 'logo' to InlineImage kafelka
    o stałym „footprincie” – wszystkie znaki wyglądają spójnie.
    """
    out = []
    import os
    from io import BytesIO
    from docxtpl import InlineImage
    from docx.shared import Mm

    for brand in brand_list:
        logo_path = get_logo_svg_path(brand, logos_dir)
        if logo_path and os.path.exists(logo_path):
            try:
                png_bytes = make_logo_tile_bytes(
                    logo_path,
                    slot_w_mm=slot_w_mm,
                    slot_h_mm=slot_h_mm,
                    pad_mm=pad_mm,
                    dpi=dpi
                )
                img_stream = BytesIO(png_bytes)
                # USTALAMY *SZEROKOŚĆ* kafelka – wszystkie będą identyczne
                img = InlineImage(doc, img_stream, width=Mm(slot_w_mm))
                out.append({"brand": brand, "logo": img})
            except Exception:
                out.append({"brand": brand, "logo": ""})
        else:
            out.append({"brand": brand, "logo": ""})
    return out


import base64

# --- IKONY ARCHETYPÓW (SVG) ---
ARCHETYPE_ICON_DIR = Path(__file__).with_name("assets") / "person_icons"
# Ikony do etykiet wykresu skumulowanego (nie mylić z person_icons)
ARCHE_STACKED_ICON_DIR = Path(__file__).with_name("assets") / "arche_icons"

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

def build_report_filenames(study: dict) -> tuple[str, str]:
    """
    Zwraca ('raport_<nazwisko-imie>.docx', 'raport_<nazwisko-imie>.pdf').
    Korzysta z *_nom (mianownik), z fallbackiem na first_name / last_name.
    """
    last_nom  = (study.get("last_name_nom")  or study.get("last_name")  or "").strip()
    first_nom = (study.get("first_name_nom") or study.get("first_name") or "").strip()
    base = (f"{last_nom} {first_nom}").strip() or "raport"
    slug = _slug_pl(base)  # już masz zdefiniowane wyżej
    return (f"raport_{slug}.docx", f"raport_{slug}.pdf")


def build_short_report_filenames(study: dict) -> tuple[str, str]:
    docx_name, pdf_name = build_report_filenames(study)
    return (
        docx_name.replace(".docx", "_skrocony.docx"),
        pdf_name.replace(".pdf", "_skrocony.pdf"),
    )


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
    "#002366": "granat królewski",
    "#0070B5": "błękit corporate",
    "#0192D3": "turkus morski",
    "#0C223F": "granat atramentowy",
    "#0E0D13": "grafit bardzo ciemny",
    "#17BECF": "niebieski morski",
    "#181C3A": "granat nocny",
    "#1B1715": "brąz prawie czarny",
    "#1E90FF": "błękit dodger",
    "#1F77B4": "chabrowy",
    "#212809": "oliwkowy głęboki",
    "#282C34": "granat antracytowy",
    "#2B2D41": "granat ciemny",
    "#2C7D78": "turkus ciemny",
    "#2CA02C": "zieleń trawiasta",
    "#2D4900": "zieleń boru głęboka",
    "#2E3141": "grafitowy granat",
    "#2F4F4F": "grafit morski",
    "#3BE8B0": "mięta neonowa",
    "#40E0D0": "turkus świetlisty",
    "#43C6DB": "turkusowy błękit",
    "#4682B4": "stalowy błękit",
    "#4B0000": "bordo głębokie",
    "#4B0082": "indygo klasyczne",
    "#556B2F": "oliwka zgaszona",
    "#588A4F": "zieleń średnia",
    "#5B6979": "grafit stalowy",
    "#61681C": "oliwkowy",
    "#663399": "purpura rebeccy",
    "#696812": "oliwkowy ciemny",
    "#6C7A89": "popielaty szary",
    "#6CA0DC": "błękit średni",
    "#7AA571": "zieleń jasna",
    "#7C46C5": "fiolet szafirowy",
    "#7C53C3": "fiolet głęboki",
    "#7D0B0B": "czerwony krwisty",
    "#800020": "burgund",
    "#86725D": "taupe mineralny",
    "#8681E8": "fiolet lawendowy",
    "#87CEEB": "błękit nieba",
    "#8B4513": "brąz siodłowy",
    "#8C564B": "ciemny brąz",
    "#8F00FF": "fiolet intensywny",
    "#906C46": "brąz średni",
    "#9467BD": "fiolet śliwkowy",
    "#9BD6F4": "pastelowy błękit jasny",
    "#A0E8AF": "seledyn",
    "#A1B1C2": "szaroniebieski jasny",
    "#A3C1AD": "pastelowa zieleń",
    "#A7C7E7": "pastelowy błękit",
    "#A9A9A9": "szary ciemny",
    "#AAC9CE": "pastelowy niebieskoszary",
    "#AB3941": "czerwony wiśniowy",
    "#ACE7FF": "błękit lodowy",
    "#ADD8E6": "błękit pastelowy",
    "#B0C4DE": "niebieskoszary jasny",
    "#B22222": "czerwony ceglasty ciemny",
    "#B2F2BB": "mięta jasna",
    "#B4D6B4": "miętowa zieleń",
    "#B6019A": "fuksja",
    "#B8B8B8": "szary satynowy",
    "#BBBDA0": "khaki jasne",
    "#C0C0C0": "srebrny",
    "#C2BCC1": "szary perłowy",
    "#CC3E2F": "czerwony ceglasty",
    "#D3D3D3": "szary jasny",
    "#D4AF37": "złoty klasyczny",
    "#D5C6AF": "beż jasny",
    "#D62728": "czerwień karmazynowa",
    "#DAA520": "złoto stare",
    "#E0BBE4": "lawenda pudrowa",
    "#E10209": "czerwony żywy",
    "#E10600": "czerwień flagowa",
    "#E377C2": "róż fioletowy pastelowy",
    "#EEEEEE": "szary mglisty",
    "#F2A93B": "miodowy żółty",
    "#F4F1ED": "biały ciepły",
    "#F5F5DC": "beż kremowy",
    "#F8BBD0": "róż pudrowy",
    "#F9D371": "złocisty żółty",
    "#F9ED06": "żółty intensywny",
    "#F9F9F9": "biel lodowa",
    "#FA709A": "róż malinowy",
    "#FADADD": "róż blady",
    "#FD4431": "czerwony pomarańczowy żywy",
    "#FE89BE": "róż neonowy jasny",
    "#FEE140": "żółty cytrynowy jasny",
    "#FF0000": "czerwień intensywna",
    "#FF6F61": "łososiowy róż",
    "#FF7F0E": "pomarańcz jaskrawy",
    "#FF8300": "pomarańcz mocny",
    "#FF8C00": "pomarańcz ciemny",
    "#FFB300": "żółty bursztynowy",
    "#FFC0CB": "róż klasyczny",
    "#FFD580": "beż morelowy",
    "#FFD6E0": "róż bardzo jasny",
    "#FFD700": "złoto",
    "#FFD93D": "żółty pastelowy",
    "#FFF200": "żółty cytrynowy",
    "#FFF6C3": "krem waniliowy",
    "#FFF9B0": "żółty bananowy blady",
    "#FFFACD": "cytryna kremowa",
    "#FFFFFF": "biel",
}

ARCHETYPE_REQUIRED_PALETTES = {
    "Władca": ["#800020", "#FFD700", "#282C34", "#800020", "#000000", "#8C564B"],
    "Bohater": ["#E10600", "#2E3141", "#FFFFFF", "#D62728", "#0E0D13", "#2B2D41", "#C2BCC1", "#CC3E2F"],
    "Mędrzec": ["#4682B4", "#B0C4DE", "#6C7A89", "#1F77B4", "#86725D", "#F4F1ED", "#BBBDA0", "#2D4900"],
    "Opiekun": ["#0192D3", "#B4D6B4", "#A7C7E7", "#FFD580", "#9467BD", "#5B6979", "#A1B1C2", "#2C7D78"],
    "Kochanek": ["#FA709A", "#FEE140", "#FFD6E0", "#FA709A"],
    "Błazen": ["#AB3941", "#F2A93B", "#FFB300", "#FFD93D", "#588A4F", "#7AA571", "#61681C", "#FF8300"],
    "Twórca": ["#7C53C3", "#3BE8B0", "#87CEEB", "#17BECF", "#B6019A", "#E10209", "#1B1715", "#F9ED06"],
    "Odkrywca": ["#212809", "#A0E8AF", "#F9D371", "#E377C2", "#D5C6AF", "#906C46", "#43C6DB", "#696812"],
    "Czarodziej": ["#181C3A", "#E0BBE4", "#8F00FF", "#7C46C5", "#0070B5", "#8681E8", "#FE89BE", "#FD4431"],
    "Towarzysz": ["#A3C1AD", "#F9F9F9", "#6CA0DC", "#2CA02C"],
    "Niewinny": ["#9BD6F4", "#FFF6C3", "#AAC9CE", "#FFF200"],
    "Buntownik": ["#FF0000", "#FF6F61", "#000000", "#FF7F0E"],
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

CORE_TRIPLET_MAP = {
    "Bohater": "Odwaga. Determinacja. Wyzwanie.",
    "Władca": "Skuteczność. Autorytet. Kontrola.",
    "Mędrzec": "Racjonalność. Wiedza. Analiza.",
    "Opiekun": "Troska. Empatia. Bezpieczeństwo.",
    "Kochanek": "Relacje. Bliskość. Emocje.",
    "Błazen": "Otwartość. Poczucie humoru. Dystans.",
    "Twórca": "Rozwój. Kreatywność. Innowacja.",
    "Odkrywca": "Wolność. Ciekawość. Nowe horyzonty.",
    "Czarodziej": "Wizja. Transformacja. Inspiracja.",
    "Towarzysz": "Współpraca. Wspólnota. Swojskość.",
    "Niewinny": "Przejrzystość. Optymizm. Uczciwość.",
    "Buntownik": "Odnowa. Zmiana. Sprzeciw.",
}

# === Progi i opisy "🧭 Interpretacja natężenia procentowego archetypu" ===
AR_INTENSITY_SCHEME = [
    #  lo,  hi,  etykieta_krótka,                               etykieta_pełna,                         opis_jakościowy
    (0,  29, "marginalne",       "marginalne natężenie",
     "Archetyp prawie nie występuje. Obszar „cienia” — wzorce zachowań i motywacje tego typu są marginalne lub tłumione. Pojawia się incydentalnie, w stresie lub pod wpływem otoczenia. Brak wpływu na decyzje i styl komunikacji. Nie buduje wizerunku."),
    (30, 49, "słabe",            "słabe natężenie",
     "Archetyp widoczny tylko w tle. Ujawnia się w określonych sytuacjach społecznych — głównie gdy trzeba się dostosować. Ograniczony wpływ na komunikację, zachowania i wizerunek."),
    (50, 59, "umiarkowane",      "umiarkowane natężenie",
     "Archetyp częściowo aktywny – równoważy się z innymi. Poziom neutralny lub „potencjalny rdzeń”, który może się rozwinąć. Zaznacza się w komunikacji, ma wpływ pomocniczy."),
    (60, 69, "znaczące",         "znaczące natężenie",
     "Archetyp wyraźny, widoczny w zachowaniu, decyzjach, wartościach. Zauważalnie kształtuje styl działania i odbiór. Wzmacnia kluczowy archetyp, ale sam nie prowadzi decyzji."),
    (70, 79, "wysokie",          "wysokie natężenie",
     "Archetyp mocno ukształtowany. Centralny motyw sposobu myślenia, postrzegania świata i działania — buduje tożsamość. Nadaje ton komunikacji / przywództwu."),
    (80, 89, "bardzo wysokie",   "bardzo wysokie natężenie (rdzeń)",
     "Archetyp niemal jednoznacznie dominuje nad resztą i w dużym stopniu określa charakter oraz wizerunek. Zwykle prowadzi do jednoznacznego stylu (np. przywódczego, opiekuńczego, buntowniczego, wizjonerskiego). Typowe dla silnych osobowości."),
    (90,100, "ekstremalne",      "ekstremalne natężenie",
     "Archetyp w „czystej” postaci — rzadkie, często idealizowane lub przerysowane ujęcie (np. „czysty Bohater”, „czysty Władca”). Ogromna spójność i autentyczność, ale niska elastyczność i zamknięcie na inne perspektywy."),
]

def interpret_archetype_intensity(pct: float) -> dict:
    """
    Zwraca słownik:
      {'short': 'wysokie', 'full': 'Wysokie natężenie', 'desc': '...'}
    """
    try:
        v = float(pct)
    except Exception:
        v = 0.0
    v = max(0.0, min(100.0, v))
    for lo, hi, short, full, desc in AR_INTENSITY_SCHEME:
        if lo <= v <= hi:
            return {"short": short, "full": full, "desc": desc}
    return {"short": "-", "full": "-", "desc": ""}

def intensity_icon_color(short_label: str) -> str:
    """Kolor kwadracika przy opisie natężenia (większy kontrast między „szarym” i „stalowym”)."""
    m = (short_label or "").strip().lower()
    return {
        "marginalne":     "#9CA3AF",  # szary (jaśniejszy)
        "słabe":          "#6B7280",  # stalowy (wyraźnie ciemniejszy)
        "umiarkowane":    "#FBBF24",  # bursztyn
        "znaczące":       "#F59E0B",  # pomarańcz
        "wysokie":        "#EF4444",  # czerwony
        "bardzo wysokie": "#DC2626",  # ciemny czerwony
        "ekstremalne":    "#7F1D1D",  # bordo
    }.get(m, "#9CA3AF")

def intensity_icon_html(short_label: str) -> str:
    """Zwraca HTML: [kolorowy KWADRAT] + tekst (np. 'umiarkowane')."""
    c = intensity_icon_color(short_label)
    return f"<span class='ap-int-ico' style='background:{c}'></span>{short_label or ''}"

def intensity_help_modal_html() -> str:
    """Modal 'Interpretacja natężenia' – 3 kolumny: Przedział; Interpretacja; Znaczenie i opis jakościowy."""
    rows = "".join(
        (
            "<tr>"
            f"<td>{lo}–{hi}%</td>"
            f"<td><b>{full}</b></td>"
            f"<td><span style='color:#4b5563'>{desc}</span></td>"
            "</tr>"
        )
        for (lo, hi, short, full, desc) in AR_INTENSITY_SCHEME
    )
    return f"""
    <style>
      /* Modal + USTAWIENIA (tu zmieniasz marginesy i szerokości kolumn) */
      #ap-intensity-modal{{
        display:none; position:fixed; inset:0; background:rgba(0,0,0,.35); z-index:9999;
    
        /* 👉 marginesy wierszy tabeli w MODALU */
        --ap-row-pad-top: 16px;     /* góra */
        --ap-row-pad-bottom: 16px;  /* dół */
        --ap-cell-pad-h: 12px;      /* lewo/prawo */
    
        /* 👉 szerokości kolumn (px lub %) */
        --ap-col-w1: 110px;  /* „Przedział” */
        --ap-col-w2: 250px;  /* „Interpretacja” */
        --ap-col-w3: auto;   /* „Znaczenie i opis jakościowy” (reszta miejsca) */
    
        /* 👉 kolory kwadracików */
        --ap-col-1: #9CA3AF;  /* 0–29%   */
        --ap-col-2: #6B7280;  /* 30–49%  */
        --ap-col-3: #FBBF24;  /* 50–59%  */
        --ap-col-4: #F59E0B;  /* 60–69%  */
        --ap-col-5: #EF4444;  /* 70–79%  */
        --ap-col-6: #DC2626;  /* 80–89%  */
        --ap-col-7: #7F1D1D;  /* 90–100% */
      }}
      #ap-intensity-modal:target{{display:block;}}
    
      #ap-intensity-modal .ap-int-modal{{
        position:fixed; left:50%; top:8%; transform:translateX(-50%);
        max-width:980px; background:#fff; border-radius:16px;
        box-shadow:0 20px 60px rgba(0,0,0,.25); padding:22px 24px;
      }}
      #ap-intensity-modal .ap-int-head{{display:flex; align-items:center; gap:10px; margin-bottom:10px;}}
      #ap-intensity-modal .ap-int-title{{font:700 18px/1.2 'Segoe UI',system-ui,Arial;}}
      #ap-intensity-modal .ap-int-close{{margin-left:auto; text-decoration:none; cursor:pointer; font:700 18px/1 monospace; color:#111}}
    
      /* Tabela w MODALU – używa zmiennych powyżej */
      .ap-int-table{{
        width:100%; border-collapse:collapse; font:400 14px/1.45 'Segoe UI',system-ui;
        table-layout: fixed;   /* trzyma szerokości kolumn */
      }}
      .ap-int-table th,
      .ap-int-table td{{
        border-bottom:1px solid #eef2f7;
        padding: var(--ap-row-pad-top) var(--ap-cell-pad-h) var(--ap-row-pad-bottom) var(--ap-cell-pad-h);
        vertical-align:top;
      }}
      .ap-int-table th{{text-align:left; font-weight:700; color:#374151;}}
      .ap-intensity-modal .ap-int-table th:nth-child(1){{ font-weight:800; }}
      .ap-intensity-modal .ap-int-table td:nth-child(1){{ font-weight:700; color:#111; }}

        /* POGRUBIENIE pierwszej kolumny w MODALU */
        #ap-intensity-modal .ap-int-table th:nth-child(1){{ font-weight:800; }}
        #ap-intensity-modal .ap-int-table td:nth-child(1){{ font-weight:700; color:#111; }}
    
      /* Szerokości kolumn (łatwe do zmiany wyżej) */
      .ap-int-table th:nth-child(1), .ap-int-table td:nth-child(1){{ width: var(--ap-col-w1); text-align:center; }}
      .ap-int-table th:nth-child(2), .ap-int-table td:nth-child(2){{ width: var(--ap-col-w2); }}
      .ap-int-table th:nth-child(3), .ap-int-table td:nth-child(3){{ width: var(--ap-col-w3); }}
    
      /* Kwadracik + jego kolory */
      .ap-int-ico{{
        display:inline-block; width:12px; height:12px; border-radius:3px;
        border:1px solid #d1d5db; margin-right:6px; vertical-align:-2px;
      }}
      .ap-i--1{{ background:var(--ap-col-1); }}
      .ap-i--2{{ background:var(--ap-col-2); }}
      .ap-i--3{{ background:var(--ap-col-3); }}
      .ap-i--4{{ background:var(--ap-col-4); }}
      .ap-i--5{{ background:var(--ap-col-5); }}
      .ap-i--6{{ background:var(--ap-col-6); }}
      .ap-i--7{{ background:var(--ap-col-7); border-color:var(--ap-col-7); }}
    </style>

    <div id="ap-intensity-modal">
      <div class="ap-int-modal" role="dialog" aria-modal="true" aria-label="Interpretacja natężenia">
        <div class="ap-int-head">
          <div class="ap-int-title">🧭 Interpretacja natężenia procentowego archetypu</div>
          <a href="#" class="ap-int-close" title="Zamknij">×</a>
        </div>
        <table class="ap-int-table">
          <thead>
            <tr>
              <th>Przedział</th>
              <th>Interpretacja</th>
              <th>Znaczenie i opis jakościowy</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>0–29%</td>
              <td><span class="ap-int-ico ap-i--1"></span><span class="ap-int-label">Marginalne natężenie</span></td>
              <td>Archetyp prawie nie występuje. Obszar „cienia” — wzorce zachowań i motywacje tego typu są marginalne lub tłumione. Pojawia się incydentalnie, w stresie lub pod wpływem otoczenia. Brak wpływu na decyzje i styl komunikacji. Nie buduje wizerunku.</td>
            </tr>
            <tr>
              <td>30–49%</td>
              <td><span class="ap-int-ico ap-i--2"></span><span class="ap-int-label">Słabe natężenie</span></td>
              <td>Archetyp widoczny tylko w tle. Ujawnia się w określonych sytuacjach społecznych — głównie gdy trzeba się dostosować. Ograniczony wpływ na komunikację, zachowania i wizerunek.</td>
            </tr>
            <tr>
              <td>50–59%</td>
              <td><span class="ap-int-ico ap-i--3"></span><span class="ap-int-label">Umiarkowane natężenie</span></td>
              <td>Archetyp częściowo aktywny — równoważy się z innymi. Poziom neutralny lub „potencjalny rdzeń”, który może się rozwinąć. Zaznacza się w komunikacji, ma wpływ pomocniczy.</td>
            </tr>
            <tr>
              <td>60–69%</td>
              <td><span class="ap-int-ico ap-i--4"></span><span class="ap-int-label">Znaczące natężenie</span></td>
              <td>Archetyp wyraźny, widoczny w zachowaniu, decyzjach, wartościach. Zauważalnie kształtuje styl działania i odbiór. Wzmacnia kluczowy archetyp, ale sam nie prowadzi decyzji.</td>
            </tr>
            <tr>
              <td>70–79%</td>
              <td><span class="ap-int-ico ap-i--5"></span><span class="ap-int-label">Wysokie natężenie</span></td>
              <td>Archetyp mocno ukształtowany. Centralny motyw sposobu myślenia, postrzegania świata i działania — buduje tożsamość. Nadaje ton komunikacji / przywództwu.</td>
            </tr>
            <tr>
              <td>80–89%</td>
              <td><span class="ap-int-ico ap-i--6"></span><span class="ap-int-label">Bardzo wysokie natężenie (rdzeń)</span></td>
              <td>Archetyp niemal jednoznacznie dominuje nad resztą i w dużym stopniu określa charakter oraz wizerunek. Zwykle prowadzi do jednoznacznego stylu (np. przywódczego, opiekuńczego, buntowniczego, wizjonerskiego). Typowe dla silnych osobowości.</td>
            </tr>
            <tr>
              <td>90–100%</td>
              <td><span class="ap-int-ico ap-i--7"></span><span class="ap-int-label">Ekstremalne natężenie</span></td>
              <td>Archetyp w „czystej” postaci — rzadkie, często idealizowane lub przerysowane ujęcie (np. „czysty Bohater”, „czysty Władca”). Ogromna spójność i autentyczność, ale bardzo niska (często praktycznie zerowa) elastyczność i zamknięcie na inne perspektywy.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
    """

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

def color_progress_bars_html(
    pcts: dict[str, float],
    order: str = "desc",
    label_font: str = "'Roboto','Segoe UI',system-ui,Arial,sans-serif",
    label_size_px: int = 15,                  # mniejsze niż było
    label_color: str = "#31333F",
    row_vmargin_px: int = 17,
    track_height_px: int = 40,
    track_color: str = "#eef2f7",
    value_font: str = "'Roboto','Segoe UI',system-ui,Arial,sans-serif",
    value_size_px: int = 17,                  # większe %
):
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
                      <span class="cp-label-text">{name}</span>
                    </div>
                    <div class="cp-track" title="{COLOR_LONG.get(name, {}).get('title', '').replace('"', '&quot;')}">
                      <div class="cp-fill" style="width:{width_css}; background:{color}"
                           title="{COLOR_LONG.get(name, {}).get('title', '').replace('"', '&quot;')}">
                        <div class="cp-badge {'in' if inside else 'out'}">{pct_int}%</div>
                      </div>
                    </div>
                  </div>
                """)
    return f"""
    <style>
      .cp-row{{
        display:grid; grid-template-columns:110px 1fr; gap:8px;
        align-items:center; margin:{row_vmargin_px}px 0;
      }}
      .cp-label{{display:flex; align-items:center; gap:10px;}}
      .cp-label-text{{
        font-family:{label_font};
        font-size:{label_size_px}px;
        color:{label_color};
        font-weight:500;                /* lżej */
        letter-spacing:.0px;
      }}
      .cp-dot{{width:10px; height:10px; border-radius:50%; display:inline-block;}}
      .cp-track{{
        position:relative; height:{track_height_px}px; border-radius:999px;
        background:{track_color}; box-shadow: inset 0 0 0 1px #e1e7f0;
      }}
      .cp-fill{{position:relative; height:100%; border-radius:999px; overflow:visible;}}
      .cp-badge{{
        position:absolute; top:50%; transform:translateY(-50%);
        font-family:{value_font}; font-size:{value_size_px}px;
        font-weight:700;               /* grube % */
        color:#111; white-space:nowrap;
      }}
      .cp-badge.in{{ right:12px; }}    /* do wewnętrznej krawędzi */
      .cp-badge.out{{ left:100%; margin-left:12px; }}
    </style>
    <div class="cp-wrap">{''.join(rows)}</div>
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

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO

def make_color_progress_png_for_word(
    pcts: dict[str, float],
    out_path: str = "color_progress.png",
    # rozmiary/odstępy
    width_px: int = 1600,
    pad: int = 36,
    bar_h: int = 72,            # nieco wyższe pastylki → większe % bez ścisku
    bar_gap: int = 34,
    # etykieta (kropka + tekst) i odstęp do paska
    dot_radius: int = 10,
    label_gap_px: int = 40,
    # typografia (etykieta lżejsza, % duże i grube)
    label_font_size: int = 30,
    pct_font_size: int | None = None,   # auto: 50% wysokości paska
    pct_margin: int = 20                # odsunięcie % od krawędzi
):
    rows = sorted(pcts.items(), key=lambda kv: kv[1], reverse=True)
    n = len(rows)
    H = pad + pad + n * bar_h + (n - 1) * bar_gap
    W = width_px

    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    drw = ImageDraw.Draw(img)

    track = (238, 242, 247, 255)
    label_col = (33, 35, 47, 255)
    val_col = (17, 17, 17, 255)

    bold_paths = [
        "assets/fonts/RobotoCondensed-Bold.ttf",
        "assets/fonts/DejaVuSans-Bold.ttf",
        "assets/fonts/Arial Bold.ttf",
    ]
    reg_paths  = [
        "assets/fonts/RobotoCondensed-Regular.ttf",
        "assets/fonts/DejaVuSans.ttf",
        "assets/fonts/Arial.ttf",
    ]

    def _try_font(paths, size):
        for p in paths:
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
        return ImageFont.load_default()

    # etykieta – lżejsza
    f_label = _try_font(reg_paths,  label_font_size)

    def _luma(hexcode: str) -> float:
        h = hexcode.lstrip('#')
        if len(h) == 3:
            h = ''.join(c*2 for c in h)
        r, g, b = (int(h[i:i+2], 16) for i in (0, 2, 4))
        return 0.2126*r + 0.7152*g + 0.0722*b

    def draw_bold_text(drw, xy, txt, font, fill, stroke=1):
        """Proste pogrubienie tekstu przez dorysowanie 4 przesuniętych kopii."""
        x, y = xy
        if stroke > 0:
            for dx, dy in ((-stroke, 0), (stroke, 0), (0, -stroke), (0, stroke)):
                drw.text((x + dx, y + dy), txt, font=font, fill=fill)
        drw.text((x, y), txt, font=font, fill=fill)

    # maks. szerokość etykiety → stały odstęp od paska
    max_label_text_w = 0
    for name, _ in rows:
        bbox = drw.textbbox((0, 0), name, font=f_label)
        max_label_text_w = max(max_label_text_w, bbox[2]-bbox[0])

    dot_w   = 2*dot_radius
    dot_pad = 10
    label_block_w = 6 + dot_w + dot_pad + max_label_text_w
    x0_base = pad + label_block_w + label_gap_px
    bar_w   = W - x0_base - pad
    radius  = bar_h // 2

    y = pad

    # --- KONFIG WARTOŚCI % ---
    PCT_FONT_PX = 33  # rozmiar czcionki %
    PCT_BOLD = True  # True = pogrubiona, False = zwykła
    PCT_RIGHT_PAD = max(10, int(bar_h * 0.35))  # odstęp od prawej krawędzi wypełnienia (px)
    PCT_VSHIFT = 0  # ręczne przesunięcie w pionie (px, + w dół, - w górę)

    # załaduj font dla % (pogrubiony lub regularny)
    def _font(paths, size):
        from PIL import ImageFont
        for p in paths:
            try:
                return ImageFont.truetype(p, size)
            except:
                pass
        return ImageFont.load_default()

    _pct_font_paths_bold = [
        "assets/fonts/RobotoCondensed-Bold.ttf",
        "assets/fonts/ArialNovaCond-Bold.ttf",
        "DejaVuSans-Bold.ttf",
    ]
    _pct_font_paths_reg = [
        "assets/fonts/RobotoCondensed-Regular.ttf",
        "assets/fonts/ArialNovaCond.ttf",
        "DejaVuSans.ttf",
    ]
    f_pct = _font(_pct_font_paths_bold if PCT_BOLD else _pct_font_paths_reg, PCT_FONT_PX)

    for name, val in rows:
        ly = y + bar_h//2
        c_hex = COLOR_HEX[name]

        # kropka
        drw.ellipse([pad+6, ly-dot_radius, pad+6+dot_w, ly+dot_radius], fill=c_hex)

        # etykieta – idealnie na środku (anchor) z fallbackiem
        label_x = pad+6+dot_w+dot_pad
        try:
            drw.text((label_x, ly), name, fill=label_col, font=f_label, anchor="lm")
        except TypeError:
            tb = drw.textbbox((0, 0), name, font=f_label)
            th = tb[3]-tb[1]
            drw.text((label_x, ly - th/2), name, fill=label_col, font=f_label)

        # tor
        x0 = x0_base
        x1 = x0 + bar_w
        y0 = y
        y1 = y + bar_h
        drw.rounded_rectangle([x0, y0, x1, y1], radius=radius, fill=track)

        # wypełnienie
        pct_val = max(0.0, min(100.0, float(val)))
        fill_w = int(bar_w * pct_val / 100.0)
        if fill_w > 0:
            drw.rounded_rectangle([x0, y0, x0+fill_w, y1], radius=radius, fill=c_hex)

        # --- % na prawej wewnętrznej krawędzi wypełnienia, wyśrodkowane pionowo ---
        pct_text = f"{int(round(val))}%"

        # kolor napisu w środku; jasność wypełnienia decyduje o bieli/czerni
        text_fill_inside = (255, 255, 255, 255) if _luma(c_hex) < 110 else (17, 17, 17, 255)

        cy = y0 + bar_h / 2 + PCT_VSHIFT  # środek pionowy paska + ewentualny v-shift

        if fill_w > 0:
            # x przy prawej krawędzi wypełnienia z marginesem do środka (anchor='rm')
            cx = x0 + fill_w - PCT_RIGHT_PAD
            # nie pozwól wyjechać w lewo przy małych słupkach
            cx = max(cx, x0 + PCT_RIGHT_PAD)

            try:
                # right-middle = „przyklej” do prawej krawędzi wypełnienia, wyśrodkuj w pionie
                drw.text((cx, cy), pct_text, font=f_pct, fill=text_fill_inside, anchor="rm")
            except TypeError:
                # fallback dla starszego Pillow bez anchor
                pb = drw.textbbox((0, 0), pct_text, font=f_pct)
                tx = cx - (pb[2] - pb[0])  # prawa krawędź tekstu w cx
                ty = cy - (pb[3] - pb[1]) / 2
                drw.text((tx, ty), pct_text, font=f_pct, fill=text_fill_inside)
        else:
            # 0% – przy początku toru, lekko od lewej, wyśrodkowane pionowo
            try:
                drw.text((x0 + PCT_RIGHT_PAD, cy), pct_text, font=f_pct, fill=(17, 17, 17, 255),
                         anchor="lm")
            except TypeError:
                pb = drw.textbbox((0, 0), pct_text, font=f_pct)
                drw.text((x0 + PCT_RIGHT_PAD, cy - (pb[3] - pb[1]) / 2), pct_text, font=f_pct,
                         fill=(17, 17, 17, 255))

        y += bar_h + bar_gap

    img.save(out_path, "PNG")
    return out_path

from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
import math

# mapowanie archetyp → kolor „rodziny” (jak w całej appce)
ARCHETYPE_TO_COLOR_FAMILY = {
    "Władca":"Czerwony", "Bohater":"Czerwony", "Buntownik":"Czerwony",
    "Twórca":"Żółty", "Czarodziej":"Żółty", "Odkrywca":"Żółty",
    "Opiekun":"Zielony", "Kochanek":"Zielony", "Błazen":"Zielony",
    "Mędrzec":"Niebieski", "Towarzysz":"Niebieski", "Niewinny":"Niebieski",
}

def make_capsule_columns_png_for_word(
    means_pct_by_arche: dict[str, float],
    out_path: str = "arche_capsules.png",
    width_px: int = 1900,
    grid_height_px: int = 620,
    top_title: str | None = None,
):
    """
    Kolumny-kapsuły z osią Y oraz X; % nad kropką; siatka 10%.
    (Poprawki: wyższe % nad kropkami, niższe nazwy, kapsuły do 100%, oś X=Y.)
    """
    if not means_pct_by_arche:
        return None

    from PIL import Image, ImageDraw, ImageFont

    # render w 2× dla ostrości (geometria bez zmian)
    S = 2

    # ------- dane -------
    items = sorted(means_pct_by_arche.items(), key=lambda kv: kv[1], reverse=True)

    # ------- layout (logiczne px) -------
    pad_x = 84
    pad_title = 96 if top_title else 40
    axis_band = 62
    pad_bottom = 118
    grid_left  = pad_x + axis_band
    grid_right = width_px - pad_x
    n = len(items)

    col_w = max(68, int((grid_right - grid_left) / max(n, 1) * 0.72))
    gap   = max(30, int((grid_right - grid_left - n * col_w) / max(n - 1, 1))) if n > 1 else 0

    grid_h    = grid_height_px
    height_px = pad_title + grid_h + pad_bottom

    # przeskalowane płótno
    W, H = width_px * S, height_px * S
    img = Image.new("RGBA", (W, H), (255, 255, 255, 0))
    drw = ImageDraw.Draw(img)

    # ------- fonty -------
    def _try_font(paths, size):
        from PIL import ImageFont
        for p in paths:
            try: return ImageFont.truetype(p, size)
            except Exception: pass
        return ImageFont.load_default()

    f_title = _try_font(["assets/fonts/RobotoCondensed-Bold.ttf","DejaVuSans-Bold.ttf","Arial.ttf"], 42*S)
    f_name  = _try_font(["assets/fonts/RobotoCondensed-Regular.ttf","DejaVuSans.ttf","Arial.ttf"], 28*S)
    f_pct   = _try_font(["assets/fonts/RobotoCondensed-Bold.ttf","DejaVuSans-Bold.ttf","Arial.ttf"], 27*S)
    f_axis  = _try_font(["assets/fonts/RobotoCondensed-Regular.ttf","DejaVuSans.ttf","Arial.ttf"], 21*S)
    f_pct_big = _try_font(
        ["assets/fonts/RobotoCondensed-Bold.ttf", "DejaVuSans-Bold.ttf", "Arial.ttf"], (27 + 5) * S)

    # ------- kolory / linie -------
    label_color = (30, 32, 36, 255)
    axis_col = (138, 144, 153, 255)      # identyczny dla X i Y
    tick_col = (200, 205, 213, 255)
    grid_col = (226, 230, 236, 255)
    cap_bg = (234, 238, 243, 255)
    cap_border = (206, 210, 217, 255)
    AXIS_W = 2 * S

    # ------- tytuł -------
    if top_title:
        tb = drw.textbbox((0,0), top_title, font=f_title)
        drw.text(((W - (tb[2]-tb[0]))/2, 16*S), top_title, font=f_title, fill=label_color)

    # ------- osie -------
    y_top   = pad_title * S
    y_bot   = (pad_title + grid_h) * S
    x_axis_y = y_bot                     # oś X na dnie siatki
    axis_x   = (grid_left - 32) * S

    # Oś Y
    drw.line([(axis_x, y_top), (axis_x, x_axis_y)], fill=axis_col, width=AXIS_W)
    # Oś X (ten sam kolor i grubość co Y)
    drw.line([(grid_left * S, x_axis_y), (grid_right * S, x_axis_y)], fill=axis_col, width=AXIS_W)

    # Linie poziome co 10% + etykiety
    for p in range(0, 101, 10):
        yy = y_bot - int(round(grid_h * S * (p/100.0)))
        drw.line([(grid_left * S, yy), (grid_right * S, yy)], fill=grid_col, width=1 * S)
        drw.line([(axis_x - 6 * S, yy), (axis_x, yy)], fill=tick_col, width=1 * S)
        txt = f"{p}%"
        tb = drw.textbbox((0,0), txt, font=f_axis)
        drw.text((axis_x - 10 * S - (tb[2]-tb[0]), yy - (tb[3]-tb[1])//2), txt, font=f_axis, fill=axis_col)

    # ------- kapsuły (teraz DOCHODZĄ do 100%) -------
    col_w_S = col_w * S
    gap_S   = gap * S
    cap_r   = (col_w // 2) * S
    cap_top = y_top               # góra = dokładnie 100%
    cap_bot = x_axis_y            # dół = oś X (0%)

    def y_for_pct(p):
        p = max(0.0, min(100.0, float(p)))
        return cap_bot - int(round((cap_bot - cap_top) * (p/100.0)))

    # offsety wg Twoich uwag
    PCT_OFFSET_ABOVE_DOT = 42 * S     # % wyżej nad kropką
    NAME_OFFSET_BELOW_X  = 18 * S     # nazwy niżej od osi X

    x = grid_left * S
    for name, val in items:
        # tło kapsuły – top=100%, bottom=0%
        cap_left, cap_right = x, x + col_w_S
        drw.rounded_rectangle([cap_left, cap_top, cap_right, cap_bot],
                              radius=cap_r, fill=cap_bg, outline=cap_border, width=2 * S)

        fam = ARCHETYPE_TO_COLOR_FAMILY.get(name, "Niebieski")
        c_hex = COLOR_HEX[fam]
        c_rgb = tuple(int(c_hex[i:i+2], 16) for i in (1,3,5)) + (255,)

        cx    = (cap_left + cap_right) // 2
        y_val = y_for_pct(val)

        # linia od 0%
        drw.line([(cx, cap_bot), (cx, y_val)], fill=c_rgb, width=6 * S)

        # kropka
        dot_r = max(6 * S, int(col_w * 0.13) * S)
        drw.ellipse([cx-dot_r, y_val-dot_r, cx+dot_r, y_val+dot_r], fill=c_rgb)

        # % NAD kropką
        pct_value = float(val)
        pct_txt = f"{round(pct_value, 1):.1f}%"
        font_pct = f_pct_big if pct_value >= 70.0 else f_pct  # +2 px dla ≥ 70%

        pb = drw.textbbox((0, 0), pct_txt, font=font_pct)
        drw.text((cx - (pb[2] - pb[0]) / 2, y_val - dot_r - PCT_OFFSET_ABOVE_DOT),
                 pct_txt, font=font_pct, fill=c_rgb)

        # ticzki X i nazwa (niżej)
        drw.line([(cx, cap_bot), (cx, cap_bot + 7 * S)], fill=tick_col, width=1 * S)
        nb = drw.textbbox((0,0), name, font=f_name)
        drw.text((cx - (nb[2]-nb[0]) / 2, cap_bot + NAME_OFFSET_BELOW_X),
                 name, font=f_name, fill=label_color)

        x += col_w_S + gap_S

    img.save(out_path, "PNG", dpi=(300, 300))
    return out_path





def mean_pct_by_archetype_from_df(df: pd.DataFrame) -> dict[str, float]:
    """
    Zwraca {archetyp: średni % 0..100} dla całego df.
    Zakłada, że kolumna 'answers' ma listę 48 wartości 0..5.
    """
    if df.empty: return {k: 0.0 for k in archetypes.keys()}
    totals = {k: 0 for k in archetypes.keys()}
    n = 0
    for _, row in df.iterrows():
        ans = row.get("answers")
        if not isinstance(ans, list) or len(ans) < 48:
            continue
        sc = archetype_scores(ans)  # masz wyżej
        for k, v in sc.items():
            totals[k] += v
        n += 1
    if n == 0: return {k: 0.0 for k in archetypes.keys()}
    # 4 pytania na archetyp * 5 pkt = 20 maks → %:
    return {k: round((totals[k] / (20.0 * n)) * 100.0, 2) for k in archetypes.keys()}


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
        "arche": "Mędrzec, Towarzysz, Niewinny",
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
        "arche": "Opiekun, Kochanek, Błazen",
        "body": (
            "Kieruje się wartościami, relacjami i potrzebą budowania poczucia bezpieczeństwa. Jest empatyczny, "
            "uważny na innych i dąży do zgody. Nie lubi gwałtownych zmian i konfrontacji, czasem brakuje mu "
            "asertywności, ale potrafi tworzyć atmosferę zaufania i współpracy. Wnosi do zespołu stabilność, "
            "lojalność i umiejętność łagodzenia napięć. Zielony to uczucia."
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
        "arche": "Twórca, Czarodziej, Odkrywca",
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
        "arche": "Władca, Bohater, Buntownik",
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
        "arche": f"Archetypy: {COLOR_LONG[name]['arche']}",
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
        
        <div style="font:510 14px/1.40 'Segoe UI',system-ui; color:#444; margin-top:6px;">
          • <b>Archetypy:</b> {meta['arche']}
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
          <div style="font:510 14px/1.40 'Segoe UI',system-ui; color:#444; margin-top:6px;">
             • <b>Archetypy:</b> {meta['arche']}
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


def _dedupe_hex_palette(values) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in (values or []):
        code = str(raw or "").strip().upper()
        if not code:
            continue
        if not code.startswith("#"):
            code = f"#{code}"
        if not re.match(r"^#[0-9A-F]{6}$", code):
            continue
        if code in seen:
            continue
        seen.add(code)
        out.append(code)
    return out


def _enforce_required_palettes(arche_map: dict[str, dict]) -> None:
    for arche_name, required_palette in ARCHETYPE_REQUIRED_PALETTES.items():
        required = _dedupe_hex_palette(required_palette)
        if not required:
            continue

        for code in required:
            COLOR_NAME_MAP.setdefault(code, f"kolor-{code[1:].lower()}")

        payload = arche_map.get(arche_name)
        if not payload:
            continue

        existing = _dedupe_hex_palette(payload.get("color_palette", []))
        merged = list(existing)
        for code in required:
            if code not in merged:
                merged.append(code)

        payload["color_palette"] = merged

        metric_rows = payload.get("metric_rows") or []
        for row in metric_rows:
            if str(row.get("label", "")).strip().casefold() == "paleta kolorów (hex)":
                row["kind"] = "colors"
                row["value"] = merged
                break


# <<<--- TUTAJ WKLEJ własne archetype_extended = {...}
archetype_extended = load_archetype_extended(
    os.path.join(os.path.dirname(__file__), 'opisy_archetypow')
)
_enforce_required_palettes(archetype_extended)
# --- KONIEC archetype_extended ---

from pathlib import Path
from PIL import Image

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

# >>> BEGIN CSS INJECTOR (wklej po zbudowaniu css_ff) >>>
import streamlit.components.v1 as components  # masz już import wyżej, ale zostaw – jest idempotentne

# 1) Złóż jeden łańcuch CSS: @font-face (css_ff) + Twoje reguły globalne
GLOBAL_CSS = (css_ff or "") + """
/* delikatna, szara linia */
.soft-hr{ height:1px; border:none; background:#e5e7eb; margin:28px 0 26px 0; }

/* jednolity nagłówek sekcji */
.ap-h2{
  font-family: "Segoe UI", system-ui, -apple-system, Arial, sans-serif;
  font-weight: 600 !important;
  font-size: 1.21rem;
  line-height: 1.3;
  letter-spacing: 0;
  color:#1f2937;
  margin: 10px 0 25px 0;
  white-space: normal;
  word-break: keep-all;
}
.ap-h2.center{ text-align:center; }

/* wymuszone nagłówki sekcji raportu */
.ap-heading-force{
  font-family: "Segoe UI", system-ui, -apple-system, Arial, sans-serif !important;
  font-weight: 640 !important;
  font-size: 1.34rem !important;
  line-height: 1.27 !important;
  letter-spacing: 0 !important;
  color:#1f2937 !important;
  margin: 6px 0 10px 0 !important;
}
@media (max-width: 1280px){
  .ap-heading-force{
    font-size: 1.25rem !important;
  }
}
.ap-heading-force.ap-heading-center{ text-align:center !important; }
.ap-heading-force.ap-heading-left{ text-align:left !important; }

/* tytuły sekcji */
.section-title{
  font-family: "Segoe UI", system-ui, -apple-system, Arial, sans-serif;
  font-weight: 530 !important;
  font-size: 1.22em;
  margin: 15px 0 25px 0;
  line-height: 1.15;
  color:#182433;
}

.section-title--padTop{ margin-top:0px !important; }
.mt-28{ margin-top:0px !important; }
.section-title--blue{ color:#1a93e3; }

/* przyciski skoków */
.jump-btns{ display:flex; flex-wrap:wrap; gap:8px; margin:8px 0 16px 0; }
.jump-btn{
  display:inline-block; padding:8px 14px; border-radius:10px; text-decoration:none;
  border:1px solid #1a93e3; color:#1a93e3; font-weight:600; font-size:0.95em;
  background:#f0f8ff;
}
.jump-btn:hover{ background:#e6f3ff; }
:target{ scroll-margin-top: 90px; }

/* selectbox – ciaśniej pod spodem */
div[data-testid="stSelectbox"]{
  margin-bottom: 4px !important;   /* ← tu ściskasz odstęp (np. 4–10 px) */
}
/* zbicie odstępu pod selectem */
div[data-testid="stSelectbox"] { padding-bottom: 0 !important; margin-bottom: 6px !important; }
div[data-testid="stSelectbox"] label { margin-bottom: 2px !important; }
/* usuń dodatkowy margines pierwszego elementu po selekcie (czasem Streamlit dodaje „poduchę”) */
div[data-testid="stSelectbox"] + div { margin-top: 0 !important; }

div[data-testid="stSelectbox"] > div{
  border:1.5px solid #1a93e3 !important;
  border-radius:10px !important;
  box-shadow: 0 0 0 1px #1a93e333 inset;
}
div[data-testid="stSelectbox"] label{
  color:#1a93e3 !important;
  font-weight:700 !important;
}

/* Streamlitowe nagłówki (w tym st.subheader) */
.stHeading h1, .stHeading h2, .stHeading h3,
h1, h2, h3,
.stMarkdown h1, .stMarkdown h2, .stMarkdown h3 {
  font-family: "Segoe UI", system-ui, -apple-system, Arial, sans-serif !important;
  font-weight: 600 !important;
  font-size: 1.23rem !important;
  line-height: 1.3 !important;
  color:#1f2937 !important;
  margin: 10px 0 25px 0 !important;
  letter-spacing: 0 !important;
}

/* domyślna rodzina dla body */
body { font-family:'Roboto','Segoe UI','Arial',sans-serif; }
"""

def inject_global_css(css_text: str, style_id: str = "ap-global-css"):
    # Bez iframa z height=0 (potrafi generować artefakty typu "0" w UI).
    st.markdown(f"<style id='{style_id}'>{css_text}</style>", unsafe_allow_html=True)

# 2) Wołaj na każdym rerunie – jest szybkie i bezpieczne
inject_global_css(GLOBAL_CSS)
# <<< END CSS INJECTOR <<<


def ap_section_heading(
    title: str,
    center: bool = False,
    margin_bottom_px: int = 8,
    margin_top_px: int = 6,
) -> str:
    align_class = "ap-heading-center" if center else "ap-heading-left"
    align = "center" if center else "left"
    return (
        f"<div class='ap-heading-force {align_class}' "
        f"style='font-family:\"Segoe UI\",system-ui,-apple-system,Arial,sans-serif !important;"
        f"font-weight:640 !important;font-size:1.34rem !important;line-height:1.27 !important;"
        f"color:#1f2937 !important;letter-spacing:0 !important;"
        f"text-align:{align} !important;margin:{int(margin_top_px)}px 0 {int(margin_bottom_px)}px 0 !important;'>"
        f"{html.escape(str(title))}</div>"
    )


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

# ---- KOŁO „osi potrzeb” (inny porządek, start o 12:00) ----
KOLO_NAMES_ORDER = [
    "Buntownik","Błazen","Kochanek","Opiekun","Towarzysz","Niewinny",
    "Władca","Mędrzec","Czarodziej","Bohater","Twórca","Odkrywca"
]
ANGLE_OFFSET_DEG = -15  # przesunięcie o 2.5 min w lewo (2.5 × 6° = 15°)

@st.cache_data
def load_axes_wheel_img():
    base_dir = Path(__file__).with_name("assets")
    png = base_dir / "archetypy_kolo.png"
    if png.exists():
        return Image.open(png).convert("RGBA")
    svg = base_dir / "archetypy_kolo.svg"
    if svg.exists():
        import cairosvg
        from io import BytesIO
        buf = BytesIO(cairosvg.svg2png(url=str(svg)))
        return Image.open(buf).convert("RGBA")
    raise FileNotFoundError("Brak pliku assets/archetypy_kolo.(png|svg)")

def _mask_pie_ring(base: Image.Image, idx: int, rgba,
                   r_out_frac=0.39, r_in_frac=0.10):
    """
    Maluje półprzezroczysty 30° sektor TYLKO na pierścieniu (donut), nie na całym płótnie.
    r_out_frac / r_in_frac – promień zewnętrzny/wewnętrzny w ułamku szerokości obrazu
    (w razie potrzeby możesz lekko podregulować, np. 0.44 / 0.18).
    """
    if idx is None:
        return base
    w, h = base.size
    cx, cy = w//2, h//2
    R = int(min(w, h) * r_out_frac)
    r = int(min(w, h) * r_in_frac)

    start = -90 + ANGLE_OFFSET_DEG + idx * 30
    end   = start + 30

    # rysujemy na osobnej warstwie z alfą → potem alpha_composite
    layer = Image.new("RGBA", (w, h), (0,0,0,0))
    d = ImageDraw.Draw(layer, "RGBA")
    d.pieslice([cx-R, cy-R, cx+R, cy+R], start, end, fill=rgba)
    # wycinamy środek (donut)
    d.ellipse([cx-r, cy-r, cx+r, cy+r], fill=(0,0,0,0))
    base.alpha_composite(layer)
    return base

def compose_axes_wheel_highlight(main_name, aux_name=None, supp_name=None) -> Image.Image:
    """Koło z podświetleniem: zielony (poboczny), żółty (wspierający), czerwony (główny)."""
    img = load_axes_wheel_img().copy()

    def idx(n):
        try:
            return KOLO_NAMES_ORDER.index(n)
        except:
            return None

    # kolejność: poboczny → wspierający → główny (nakładanie)
    _mask_pie_ring(img, idx(supp_name), (64,185,0,110))
    _mask_pie_ring(img, idx(aux_name),  (255,210,47,110))
    _mask_pie_ring(img, idx(main_name), (255,0,0,110))
    return img


SEGMENT_PROFILE_ITEMS = [
    ("Buntownik", "Odnowa", "buntownik.png", "#c62828"),
    ("Błazen", "Otwartość", "blazen.png", "#ef5350"),
    ("Kochanek", "Relacje", "kochanek.png", "#90caf9"),
    ("Opiekun", "Troska", "opiekun.png", "#42a5f5"),
    ("Towarzysz", "Współpraca", "towarzysz.png", "#1565c0"),
    ("Niewinny", "Przejrzystość", "niewinny.png", "#81c784"),
    ("Władca", "Skuteczność", "wladca.png", "#43a047"),
    ("Mędrzec", "Racjonalność", "medrzec.png", "#1b5e20"),
    ("Czarodziej", "Wizja", "czarodziej.png", "#b39ddb"),
    ("Bohater", "Odwaga", "bohater.png", "#7e57c2"),
    ("Twórca", "Rozwój", "tworca.png", "#5e35b1"),
    ("Odkrywca", "Wolność", "odkrywca.png", "#8e0000"),
]


def _plot_segment_profile_wheel_from_scores(outpath: Path, mean_scores: dict[str, float]) -> None:
    from matplotlib.patches import Wedge, Circle
    import math

    values = np.asarray([float(mean_scores.get(name, 0.0)) for name, *_ in SEGMENT_PROFILE_ITEMS], dtype=float)
    values = np.where(np.isfinite(values), np.clip(values, 0.0, 100.0), 0.0)

    def _load_icon(path: Path):
        img = Image.open(path).convert("RGBA")
        alpha = img.getchannel("A")
        bbox = alpha.getbbox()
        if bbox:
            img = img.crop(bbox)
        return np.asarray(img)

    def _draw_text_on_arc(ax, text: str, center_deg: float, radius: float) -> None:
        text = str(text or "").upper()
        if not text:
            return
        n = len(text)
        span = min(24, max(11.5, 1.7 * n))
        center_rad = math.radians(center_deg)
        upper = math.sin(center_rad) >= 0
        if n == 1:
            angles = [center_deg]
        else:
            if upper:
                start = center_deg + span / 2
                end = center_deg - span / 2
            else:
                start = center_deg - span / 2
                end = center_deg + span / 2
            angles = np.linspace(start, end, n)
        for ch, ang in zip(text, angles):
            if ch == " ":
                continue
            ang_rad = math.radians(float(ang))
            rot = (ang - 90) if upper else (ang + 90)
            ax.text(
                radius * math.cos(ang_rad),
                radius * math.sin(ang_rad),
                ch,
                ha="center",
                va="center",
                rotation=rot,
                rotation_mode="anchor",
                fontsize=11.4,
                fontweight="bold",
                color="#363636",
                zorder=4,
            )

    fig, ax = plt.subplots(figsize=(10.8, 10.8), dpi=220)
    ax.set_aspect("equal")
    ax.axis("off")
    bg = (1, 1, 1, 0)
    fig.patch.set_alpha(0.0)
    ax.set_facecolor("none")

    r_hole = 0.115
    r_data_outer = 0.78
    n_cells = 10
    dr = (r_data_outer - r_hole) / n_cells
    r_label_inner = 0.80
    r_label_outer = 0.92
    r_accent_inner = 0.95
    r_accent_outer = 0.99
    edgecolor = "#d4d4d4"

    icon_dir = Path(__file__).with_name("ikony")
    icon_cache: dict[str, np.ndarray] = {}
    for arch, _value, icon_file, _color in SEGMENT_PROFILE_ITEMS:
        icon_path = icon_dir / icon_file
        if icon_path.exists():
            try:
                icon_cache[arch] = _load_icon(icon_path)
            except Exception:
                pass

    for k in range(n_cells + 1):
        r = r_hole + k * dr
        ax.add_patch(Circle((0, 0), r, facecolor="none", edgecolor="#dfdfdf", linewidth=0.7, zorder=0))

    for i in range(12):
        center = 75 - i * 30
        edge_ang = math.radians(center - 15)
        ax.plot(
            [r_hole * math.cos(edge_ang), r_accent_outer * math.cos(edge_ang)],
            [r_hole * math.sin(edge_ang), r_accent_outer * math.sin(edge_ang)],
            color="#d7d7d7",
            lw=0.7,
            zorder=0,
        )

    for i, (arch, value_label, _icon_file, color) in enumerate(SEGMENT_PROFILE_ITEMS):
        center = 75 - i * 30
        theta1 = center - 15
        theta2 = center + 15
        p = float(values[i])
        fill_outer = r_hole + (p / 100.0) * (r_data_outer - r_hole)

        for k in range(n_cells):
            r_outer = r_hole + (k + 1) * dr
            ax.add_patch(
                Wedge((0, 0), r_outer, theta1, theta2, width=dr, facecolor=bg, edgecolor=edgecolor, linewidth=0.8, zorder=1)
            )
        if fill_outer > r_hole + 1e-9:
            ax.add_patch(
                Wedge(
                    (0, 0),
                    fill_outer,
                    theta1,
                    theta2,
                    width=(fill_outer - r_hole),
                    facecolor=color,
                    edgecolor="none",
                    linewidth=0.0,
                    alpha=0.90,
                    zorder=2,
                )
            )
        for k in range(n_cells):
            r_outer = r_hole + (k + 1) * dr
            ax.add_patch(
                Wedge((0, 0), r_outer, theta1, theta2, width=dr, facecolor="none", edgecolor=edgecolor, linewidth=0.8, zorder=3)
            )
        ax.add_patch(
            Wedge(
                (0, 0),
                r_label_outer,
                theta1,
                theta2,
                width=(r_label_outer - r_label_inner),
                facecolor=bg,
                edgecolor=edgecolor,
                linewidth=0.8,
                zorder=3.2,
            )
        )
        ax.add_patch(
            Wedge(
                (0, 0),
                r_accent_outer,
                theta1,
                theta2,
                width=(r_accent_outer - r_accent_inner),
                facecolor=color,
                edgecolor=bg,
                linewidth=1.1,
                zorder=3.4,
            )
        )

        _draw_text_on_arc(ax=ax, text=arch, center_deg=center, radius=(r_label_inner + r_label_outer) / 2)

        ang = math.radians(center)
        if arch in icon_cache:
            ax.add_artist(
                AnnotationBbox(
                    OffsetImage(icon_cache[arch], zoom=0.26),
                    (1.14 * math.cos(ang), 1.14 * math.sin(ang)),
                    frameon=False,
                    zorder=5,
                )
            )

        filled_span = max(0.0, fill_outer - r_hole)
        label_r = (r_hole + filled_span * 0.52 + dr * 0.18) if p <= 25.0 else (r_hole + filled_span * 0.52)
        if filled_span <= 1e-9:
            label_r = r_hole + dr * 0.9
        ax.text(
            label_r * math.cos(ang),
            label_r * math.sin(ang),
            f"{p:.0f}",
            ha="center",
            va="center",
            fontsize=12.2,
            color="#2f2f2f",
            fontweight="bold",
            zorder=8,
            bbox=dict(boxstyle="round,pad=0.24,rounding_size=0.10", fc="white", ec=color, lw=1.0, alpha=0.68),
        )

    ax.add_patch(Circle((0, 0), r_hole * 0.98, facecolor=bg, edgecolor="#d0d0d0", linewidth=1.2, zorder=10))
    for angle_deg in [0, 90, 180, 270]:
        ang = math.radians(angle_deg)
        ax.plot([0, 1.02 * math.cos(ang)], [0, 1.02 * math.sin(ang)], color="#e1e1e1", lw=0.9, zorder=0)

    ax.set_xlim(-1.22, 1.22)
    ax.set_ylim(-1.22, 1.22)
    outpath = Path(outpath)
    outpath.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout(pad=0.06)
    fig.savefig(outpath, dpi=220, bbox_inches="tight", pad_inches=0.10, transparent=True)
    plt.close(fig)


def make_segment_profile_wheel_png(mean_scores: dict[str, float], out_path: str = "segment_profile_wheel.png") -> str:
    _plot_segment_profile_wheel_from_scores(Path(out_path), mean_scores or {})
    return out_path


@st.cache_data(ttl=30)
def load(study_id=None):
    import json
    try:
        engine = _sa_engine()
        base_sql = "SELECT created_at, answers FROM public.responses"
        if study_id:
            query = sa.text(base_sql + " WHERE study_id = :sid ORDER BY created_at")
            with engine.begin() as conn:
                df = pd.read_sql(query, con=conn, params={"sid": study_id})
        else:
            query = sa.text(base_sql + " ORDER BY created_at")
            with engine.begin() as conn:
                df = pd.read_sql(query, con=conn)
        engine.dispose()

        def parse_answers(x):
            if isinstance(x, list):
                return [int(v) for v in x] if x and isinstance(x[0], (int, str)) else x
            if isinstance(x, str):
                for loader in (json.loads, ast.literal_eval):
                    try:
                        val = loader(x)
                        return [int(v) for v in val] if isinstance(val, list) else None
                    except Exception:
                        pass
                return None
            return None

        if "answers" in df.columns:
            df["answers"] = df["answers"].apply(parse_answers)
        return df

    except Exception as e:
        st.warning(f"Błąd podczas ładowania danych: {e}")




@st.cache_data(ttl=30)
def fetch_studies_list():
    engine = _sa_engine()
    query = sa.text("""
        SELECT
            id,
            first_name_nom, first_name_gen, first_name_dat, first_name_acc, first_name_ins, first_name_loc, first_name_voc,
            last_name_nom,  last_name_gen,  last_name_dat,  last_name_acc,  last_name_ins,  last_name_loc,  last_name_voc,
            city_nom, slug
        FROM public.studies
        WHERE COALESCE(is_active, true)
        ORDER BY created_at DESC
    """)
    with engine.begin() as conn:
        df = pd.read_sql(query, con=conn)
    engine.dispose()
    return df


def archetype_scores(answers):
    if not isinstance(answers, list) or len(answers) < 48:
        return {k: None for k in archetypes}
    a = [int(v) for v in answers]  # 👈 twarde rzutowanie
    return {name: sum(a[i-1] for i in idxs) for name, idxs in archetypes.items()}


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

def should_show_supplement(third_name: str | None,
                           means_pct: dict[str, float],
                           threshold: float = 70.0) -> bool:
    """
    Zwraca True, jeśli trzeci archetyp ma % >= threshold.
    'means_pct' to słownik {archetyp: % 0..100}.
    """
    if not third_name:
        return False
    try:
        return float(means_pct.get(third_name, 0.0)) >= (threshold - 1e-9)
    except Exception:
        return False

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
    person = person or {}
    def p(key, fallback=""):
        return (person.get(key) or fallback).strip()

    def person_links_plain(person_list):
        cleaned = [canonical_person_name(name) for name in (person_list or []) if str(name or "").strip()]
        # zachowaj kolejność i usuń duplikaty
        return list(dict.fromkeys(cleaned))

    def kolor_label_list(palette):
        if not isinstance(palette, list):
            return ""
        out = []
        for code in palette:
            name = COLOR_NAME_MAP.get(str(code).upper(), str(code).upper())
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
        "ARCHETYPE_MAIN_CORE_TRIPLET": main.get("core_triplet") or CORE_TRIPLET_MAP.get(main_type, ""),
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
        "ARCHETYPE_MAIN_METRIC_TEXT": main.get("report_metric_text") or "",
        "ARCHETYPE_MAIN_EXPANDED_TEXT": main.get("report_expanded_text") or "",

        "ARCHETYPE_AUX_NAME": second.get("name") or "",
        "ARCHETYPE_AUX_CORE_TRIPLET": second.get("core_triplet") or CORE_TRIPLET_MAP.get(second_type, ""),
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
        "ARCHETYPE_AUX_METRIC_TEXT": second.get("report_metric_text") or "",
        "ARCHETYPE_AUX_EXPANDED_TEXT": second.get("report_expanded_text") or "",

        "ARCHETYPE_SUPPLEMENT_NAME": supplement.get("name") or "",
        "ARCHETYPE_SUPPLEMENT_CORE_TRIPLET": supplement.get("core_triplet") or CORE_TRIPLET_MAP.get(supplement_type, ""),
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
        "ARCHETYPE_SUPPLEMENT_METRIC_TEXT": supplement.get("report_metric_text") or "",
        "ARCHETYPE_SUPPLEMENT_EXPANDED_TEXT": supplement.get("report_expanded_text") or "",
    }
    return context


def _doc_has_style(doc_obj, style_name: str) -> bool:
    try:
        return any(style.name == style_name for style in doc_obj.styles)
    except Exception:
        return False


def _doc_add_paragraph(doc_obj, text: str, style_name: str | None = None):
    if style_name and _doc_has_style(doc_obj, style_name):
        return doc_obj.add_paragraph(text, style=style_name)
    return doc_obj.add_paragraph(text)


def _append_archetype_appendix(doc_tpl, appendix_items: list[tuple[str, dict]]):
    valid_items = []
    for role_label, arche_data in appendix_items:
        if not arche_data:
            continue
        if not (arche_data.get("metric_rows") or arche_data.get("expanded_sections")):
            continue
        valid_items.append((role_label, arche_data))

    if not valid_items:
        return

    doc_obj = doc_tpl.docx
    doc_obj.add_page_break()
    _doc_add_paragraph(doc_obj, "Załącznik: Rozbudowane opisy archetypów", "Heading 1")

    for role_label, arche_data in valid_items:
        arche_name = arche_data.get("name") or "Archetyp"
        _doc_add_paragraph(doc_obj, f"{role_label}: {arche_name}", "Heading 2")

        metric_rows = arche_data.get("metric_rows") or []
        if metric_rows:
            _doc_add_paragraph(doc_obj, "Metryka archetypu", "Heading 3")
            for row in metric_rows:
                label = str(row.get("label", "")).strip()
                kind = row.get("kind", "text")
                value = row.get("value")
                if not label:
                    continue
                if label.casefold() == "core triplet":
                    continue

                if kind == "examples":
                    _doc_add_paragraph(doc_obj, f"{label}:", "Heading 4")
                    examples_map = value or {}
                    for group in ("Politycy", "Marki/organizacje", "Popkultura/postacie"):
                        values = examples_map.get(group) or []
                        if values:
                            _doc_add_paragraph(doc_obj, f"- {group}: {', '.join(values)}")
                    continue

                if isinstance(value, list):
                    if not value:
                        continue
                    _doc_add_paragraph(doc_obj, f"{label}:", "Heading 4")
                    for item in value:
                        if str(item).strip():
                            _doc_add_paragraph(doc_obj, f"- {item}")
                    continue

                text_value = str(value or "").strip()
                if text_value:
                    _doc_add_paragraph(doc_obj, f"{label}: {text_value}")

        expanded_sections = arche_data.get("expanded_sections") or []
        if expanded_sections:
            _doc_add_paragraph(doc_obj, "Rozbudowany opis", "Heading 3")
            for section in expanded_sections:
                title = str(section.get("title", "")).strip()
                if title:
                    _doc_add_paragraph(doc_obj, title, "Heading 3")
                for subsection in section.get("subsections", []):
                    subtitle = str(subsection.get("title", "")).strip()
                    if subtitle:
                        _doc_add_paragraph(doc_obj, subtitle, "Heading 4")
                    for line in subsection.get("content", []):
                        if str(line).strip():
                            _doc_add_paragraph(doc_obj, str(line).strip())


def _append_segment_profile_page(doc_tpl, segment_profile_img_path: str | None, subject_gen: str = ""):
    if not segment_profile_img_path or not os.path.exists(segment_profile_img_path):
        return
    doc_obj = doc_tpl.docx
    doc_obj.add_page_break()
    title = re.sub(r"\s{2,}", " ", f"Profil archetypowy {subject_gen} (siła archetypu, skala: 0-100)").strip()
    _doc_add_paragraph(doc_obj, title, "Heading 1")
    p = doc_obj.add_paragraph()
    add_image(p, segment_profile_img_path, width=Mm(170))


def export_word_metrics_only(
    main_type,
    second_type,
    supplement_type,
    main,
    second,
    supplement,
    person: dict | None = None,
    show_supplement: bool = True,
    segment_profile_img_path: str | None = None,
):
    person = person or {}
    full_name = (person.get("GEN") or person.get("NOM") or "").strip()
    doc = Document()
    doc.add_heading(f"Raport skrócony – Metryka archetypów {full_name}".strip(), level=1)
    doc.add_paragraph(f"Data wygenerowania: {datetime.now().strftime('%Y-%m-%d')}")

    if segment_profile_img_path and os.path.exists(segment_profile_img_path):
        doc.add_paragraph("")
        prof_title = re.sub(r"\s{2,}", " ", f"Profil archetypowy {full_name} (siła archetypu, skala: 0-100)").strip()
        doc.add_heading(prof_title, level=2)
        p = doc.add_paragraph()
        add_image(p, segment_profile_img_path, width=Mm(165))

    roles = [
        ("Archetyp główny", main),
        ("Archetyp wspierający", second),
    ]
    if show_supplement:
        roles.append(("Archetyp poboczny", supplement))

    for role_label, arche_data in roles:
        if not arche_data:
            continue
        metric_rows = arche_data.get("metric_rows") or []
        if not metric_rows:
            continue
        doc.add_page_break()
        doc.add_heading(f"{role_label}: {arche_data.get('name') or ''}".strip(), level=2)
        doc.add_heading("Metryka archetypu", level=3)
        for row in metric_rows:
            label = str(row.get("label", "")).strip()
            kind = row.get("kind", "text")
            value = row.get("value")
            if not label:
                continue
            if label.casefold() == "core triplet":
                continue

            if kind == "examples":
                doc.add_heading(label, level=4)
                examples_map = value or {}
                for group in ("Politycy", "Marki/organizacje", "Popkultura/postacie"):
                    vals = [str(v).strip() for v in (examples_map.get(group) or []) if str(v).strip()]
                    if vals:
                        doc.add_paragraph(f"- {group}: {', '.join(vals)}")
                continue

            if isinstance(value, list):
                vals = [str(v).strip() for v in value if str(v).strip()]
                if not vals:
                    continue
                doc.add_heading(label, level=4)
                for item in vals:
                    doc.add_paragraph(f"- {item}")
                continue

            txt = str(value or "").strip()
            if txt:
                doc.add_heading(label, level=4)
                doc.add_paragraph(txt)

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf


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
    axes_wheel_img_path: str | None = None,
    dom_color: dict | None = None,
    color_progress_img_path: str | None = None,
    archetype_stacked_img_path: str | None = None,
    capsule_columns_img_path: str | None = None,
    segment_profile_img_path: str | None = None,
    show_supplement: bool = True,                       # ⬅️ NOWY ARGUMENT
    template_path: str | None = None,                   # ⬅️ (opcjonalny override)
):
    # Wybór szablonu zależnie od widoczności pobocznego
    _template = template_path or (TEMPLATE_PATH if show_supplement else TEMPLATE_PATH_NOSUPP)
    doc = DocxTemplate(_template)

    # [AUTO-FIT] policz pole składu i zaplanuj szerokości obrazków
    try:
        sect = doc.docx.part.document.sections[0]
        page_w_mm = sect.page_width.mm
        left_mm = sect.left_margin.mm
        right_mm = sect.right_margin.mm
        content_mm = page_w_mm - left_mm - right_mm  # efektywna szerokość wiersza

        # Załóż, że lewa kolumna (tabela z liczebnościami) ma ~55 mm.
        # Zostaje miejsce na 2 obrazki (radar + koło/panel) w jednym wierszu.
        left_col_mm = 55.0
        gap_between_imgs_mm = 6.0  # szpara między kolumnami w tabeli
        rest_mm = max(0.0, content_mm - left_col_mm)

        # Maksymalna szerokość jednego obrazka (po równo) – ale nie więcej niż 92 mm.
        one_img_mm = min(92.0, max(70.0, (rest_mm - gap_between_imgs_mm) / 2.0))
    except Exception:
        # Fallback gdyby sekcja nie była dostępna
        one_img_mm = 115.0

    # Radar image (mniejsze, żeby zmieściły się 3 elementy w wierszu Worda)
    if radar_img_path and os.path.exists(radar_img_path):
        radar_image = InlineImage(doc, radar_img_path, width=Mm(one_img_mm))
    else:
        radar_image = ""

    # Panel image (na bazie koła archetypów)
    panel_image = InlineImage(doc, panel_img_path, width=Mm(105)) if panel_img_path and os.path.exists(panel_img_path) else ""

    # Ikony archetypów do Word (główny/wspierający/poboczny)
    ARCHETYPE_MAIN_ICON = arche_icon_inline_for_word(doc, main_type, gender_code, height_mm=26) if main_type else ""
    ARCHETYPE_AUX_ICON = arche_icon_inline_for_word(doc, second_type, gender_code, height_mm=26) if second_type else ""
    ARCHETYPE_SUPP_ICON = arche_icon_inline_for_word(doc, supplement_type, gender_code, height_mm=26) if supplement_type else ""

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

    # Jeśli nie pokazujemy pobocznego – wyczyść jego pola (na wszelki wypadek)
    if not show_supplement:
        for k in list(context.keys()):
            if k.startswith("ARCHETYPE_SUPPLEMENT_"):
                context[k] = "" if not isinstance(context[k], list) else []
        context["ARCHETYPE_SUPP_ICON"] = ""
        context["ARCHETYPE_SUPP_PALETTE_IMG"] = ""

    # Logotypy do Worda
    context["ARCHETYPE_MAIN_BRANDS_IMG"] = build_brands_for_word(
        doc, main.get("example_brands", []), logos_dir=logos_dir, slot_w_mm=30.0, slot_h_mm=20.0,
        pad_mm=2.0)
    context["ARCHETYPE_AUX_BRANDS_IMG"] = build_brands_for_word(
        doc, second.get("example_brands", []), logos_dir=logos_dir, slot_w_mm=30.0, slot_h_mm=20.0,
        pad_mm=2.0)
    context["ARCHETYPE_SUPPLEMENT_BRANDS_IMG"] = build_brands_for_word(
        doc, supplement.get("example_brands", []), logos_dir=logos_dir, slot_w_mm=30.0,
        slot_h_mm=20.0, pad_mm=2.0)

    context["PANEL_IMG"] = panel_image

    # Grafikę pierścienia już masz:
    context["COLOR_RING_IMG"] = InlineImage(doc, "color_ring.png", width=Mm(105))

    # Tekstowy opis dominującego koloru:
    if dom_color:
        context["DOM_COLOR_NAME"] = dom_color["name"]
        context["DOM_COLOR_EMOJI"] = dom_color["emoji"]
        context["DOM_COLOR_TITLE"] = dom_color["title"]
        context["DOM_COLOR_PCT"] = f"{dom_color['pct']:.1f}%"
        context["DOM_COLOR_ORIENT"] = dom_color["orient"]
        context["DOM_COLOR_BODY"] = dom_color["body"]
        context["DOM_COLOR_POLITICS"] = dom_color["politics"]
        context["DOM_COLOR_ARCHE"] = dom_color.get("arche") or COLOR_LONG.get(dom_color["name"],
                                                                              {}).get("arche", "")
    else:
        # Bezpieczne puste wartości, gdyby kiedyś nie było danych
        for k in ("DOM_COLOR_NAME", "DOM_COLOR_EMOJI", "DOM_COLOR_TITLE",
                  "DOM_COLOR_PCT", "DOM_COLOR_ORIENT", "DOM_COLOR_BODY", "DOM_COLOR_POLITICS"):
            context[k] = ""

    AXES_WHEEL_IMG = (
        InlineImage(doc, axes_wheel_img_path, width=Mm(105))
        if (axes_wheel_img_path and os.path.exists(axes_wheel_img_path))
        else "")

    context["AXES_WHEEL_IMG"] = AXES_WHEEL_IMG

    # Wykres pigułek (PNG na przezroczystym tle)
    if color_progress_img_path and os.path.exists(color_progress_img_path):
        context["COLOR_PROGRESS_IMG"] = (
            InlineImage(doc, color_progress_img_path, width=Mm(160))
            if color_progress_img_path and os.path.exists(color_progress_img_path) else "")

    # Skumulowany wykres słupkowy archetypów (główny/ wspierający/ poboczny)
    context["ARCHETYPE_STACKED_IMG"] = (
        InlineImage(doc, archetype_stacked_img_path, width=Mm(160))
        if (archetype_stacked_img_path and os.path.exists(archetype_stacked_img_path))
        else "")

    context["ARCHETYPE_CAPSULES_IMG"] = (
        InlineImage(doc, capsule_columns_img_path, width=Mm(170))
        if (capsule_columns_img_path and os.path.exists(capsule_columns_img_path))
        else "")

    # === Natężenie archetypu: etykiety i opisy dla Worda ===
    # Używamy 'mean_scores' przekazanych do funkcji (to słownik {archetyp: %}).
    _ms = mean_scores or {}

    def _lab_desc_for(name: str):
        if not name:
            return {"short": "", "full": "", "desc": ""}
        pct = float(_ms.get(name, 0.0))
        return interpret_archetype_intensity(pct)

    _main = _lab_desc_for(main_type)
    _aux = _lab_desc_for(second_type)
    _supp = _lab_desc_for(supplement_type)

    # Krótkie linie „Natężenie archetypu: …”
    context["ARCHETYPE_MAIN_INTENSITY_LINE"] = f"Natężenie archetypu: {_main['short']}" if _main[
        "short"] else ""
    context["ARCHETYPE_AUX_INTENSITY_LINE"] = f"Natężenie archetypu: {_aux['short']}" if _aux[
        "short"] else ""
    context["ARCHETYPE_SUPP_INTENSITY_LINE"] = f"Natężenie archetypu: {_supp['short']}" if _supp[
        "short"] else ""

    # Same etykiety (np. „Wysokie natężenie”) — gdybyś wolał użyć oddzielnie
    context["ARCHETYPE_MAIN_INTENSITY_LABEL"] = _main["full"]
    context["ARCHETYPE_AUX_INTENSITY_LABEL"] = _aux["full"]
    context["ARCHETYPE_SUPP_INTENSITY_LABEL"] = _supp["full"]

    # Opisy jakościowe (kolumna „Znaczenie i opis jakościowy”)
    context["ARCHETYPE_MAIN_INTENSITY_DESC"] = _main["desc"]
    context["ARCHETYPE_AUX_INTENSITY_DESC"] = _aux["desc"]
    context["ARCHETYPE_SUPP_INTENSITY_DESC"] = _supp["desc"]

    doc.render(context)

    appendix_payload = [
        ("Archetyp główny", main),
        ("Archetyp wspierający", second),
    ]
    if show_supplement:
        appendix_payload.append(("Archetyp poboczny", supplement))
    _append_archetype_appendix(doc, appendix_payload)
    subject_gen = (person or {}).get("GEN") or (person or {}).get("NOM") or ""
    _append_segment_profile_page(doc, segment_profile_img_path, subject_gen=subject_gen)

    # Hiperłącza do osób: tylko jeśli akapit zawiera wyłącznie nazwisko (z opcjonalnym prefiksem "- ").
    for para in doc.paragraphs:
        raw_text = (para.text or "").strip()
        if not raw_text:
            continue

        bullet_prefix = ""
        candidate = raw_text
        if raw_text.startswith("- "):
            bullet_prefix = "- "
            candidate = raw_text[2:].strip()

        candidate = canonical_person_name(candidate)
        if candidate in person_wikipedia_links:
            para.clear()
            if bullet_prefix:
                para.add_run(bullet_prefix)
            add_hyperlink(para, candidate, person_wikipedia_links[candidate])

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf

def _find_soffice() -> str | None:
    """
    Znajdź binarkę 'soffice' dla LibreOffice (Linux). Na Windows zwraca None.
    Respektuje zmienną środowiskową SOFFICE_BIN.
    """
    import sys, os, shutil
    if sys.platform.startswith("win"):
        return None
    # 1) ręcznie wskazana ścieżka
    env = os.environ.get("SOFFICE_BIN")
    if env and os.path.isfile(env):
        return env
    # 2) PATH / najczęstsze lokalizacje
    candidates = [
        shutil.which("soffice"),
        "/usr/bin/soffice",
        "/usr/local/bin/soffice",
        "/usr/lib/libreoffice/program/soffice",
        "/snap/bin/libreoffice",
    ]
    for c in candidates:
        if c and os.path.exists(c):
            return c
    return None

def word_to_pdf(docx_bytes_io, soffice_bin: str | None = None):
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

            # 3) Konwersja LibreOffice (z możliwością podania ścieżki)
            try:
                cmd = [soffice_bin or "soffice", "--headless", "--convert-to", "pdf",
                       "--outdir", tmpdir, docx_path]
                result = subprocess.run(cmd, capture_output=True)
                if result.returncode != 0 or not os.path.isfile(pdf_path):
                    raise RuntimeError(
                        "LibreOffice PDF error: " + result.stderr.decode(errors="ignore"))
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

    def _sort_palette_logical(values: list[str]) -> list[str]:
        cleaned = _dedupe_hex_palette(values)
        if not cleaned:
            return []

        def _key(hexcode: str):
            h = hexcode.lstrip("#")
            r = int(h[0:2], 16) / 255.0
            g = int(h[2:4], 16) / 255.0
            b = int(h[4:6], 16) / 255.0
            hue, light, sat = colorsys.rgb_to_hls(r, g, b)
            # Najpierw kolory (po kole barw), na końcu neutrals (szarości/czerń/biel)
            if sat < 0.085:
                return (2, light, hue)
            hue_deg = (hue * 360.0) % 360.0
            hue_bucket = int((hue_deg + 15.0) // 30.0) % 12
            return (1, hue_bucket, -sat, light)

        return sorted(cleaned, key=_key)

    def label_for(code):
        name = color_name_map.get(str(code).upper(), str(code))
        return f"{name} ({code})"

    boxes = []
    logical_palette = _sort_palette_logical([str(c).upper() for c in palette])
    for hexcode in logical_palette:
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

@lru_cache(maxsize=512)
def _file_to_data_uri(path: str) -> str:
    ext = Path(path).suffix.lower()
    mime = {
        ".svg": "image/svg+xml",
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".tif": "image/tiff",
        ".tiff": "image/tiff",
    }.get(ext, "application/octet-stream")
    blob = Path(path).read_bytes()
    b64 = base64.b64encode(blob).decode("ascii")
    return f"data:{mime};base64,{b64}"


@lru_cache(maxsize=512)
def _photo_to_data_uri(path: str, max_px: int = 220) -> str:
    ext = Path(path).suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff"}:
        return _file_to_data_uri(path)
    try:
        with Image.open(path) as im:
            im = im.convert("RGB")
            resample = getattr(Image, "Resampling", Image).LANCZOS
            im.thumbnail((max_px, max_px), resample)
            out = BytesIO()
            im.save(out, format="JPEG", quality=82, optimize=True)
            b64 = base64.b64encode(out.getvalue()).decode("ascii")
            return f"data:image/jpeg;base64,{b64}"
    except Exception:
        return _file_to_data_uri(path)


def build_brand_icons_html(brand_names, logos_dir, label_color: str = "#f3f6ff"):
    import os
    out_html = (
        '<div style="display:flex;flex-wrap:wrap;gap:12px 18px;align-items:flex-start;'
        'margin-top:6px;margin-bottom:8px;">'
    )
    for brand in brand_names:
        path = get_logo_svg_path(brand, logos_dir)
        if path and os.path.exists(path):
            try:
                data_uri = _file_to_data_uri(path)
                img_tag = (
                    f"<img src='{data_uri}' alt='{html.escape(str(brand))}' "
                    "style='height:38px;max-width:96px;object-fit:contain;display:block;margin:0 auto 3px;'/>"
                )
                out_html += (
                    f"<span title='{html.escape(str(brand))}' style='display:flex;flex-direction:column;"
                    "align-items:center;min-width:56px;padding:2px 4px;'>"
                    f"{img_tag}"
                    f"<span style='font-size:0.86em;line-height:1.2;color:{label_color};'>{html.escape(str(brand))}</span>"
                    "</span>"
                )
            except Exception:
                out_html += (
                    f"<span style='font-size:0.93em;color:{label_color};opacity:.95;padding:2px 4px;'>"
                    f"{html.escape(str(brand))}</span>"
                )
        else:
            out_html += (
                f"<span style='font-size:0.93em;color:{label_color};opacity:.80;padding:2px 4px;'>"
                f"{html.escape(str(brand))}</span>"
            )
    out_html += '</div>'
    return out_html

def person_links_html(person_list):
    if not person_list:
        return ""
    return ', '.join(person_link(name) for name in person_list)


PHOTO_DIR_PERSON = Path(__file__).with_name("assets") / "foto_person"
PHOTO_DIR_POPCULTURE = Path(__file__).with_name("assets") / "foto_popculture"
PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".tif", ".tiff"}

POPCULTURE_IMAGE_ALIASES = {
    "Jaś Fasola": "Mr. Bean",
    "Morfeusz (z „Matrixa”)": "Morpheus (The Matrix)",
    "Mistrz Yoda": "Yoda",
    "Oprah": "Oprah Winfrey",
    "księżna Diana": "Diana Princess of Wales",
    "Matka Teresa": "Mother Teresa",
    "Forest Gump": "Forrest Gump",
    "Ojciec Chrzestny": "The Godfather",
    "Indiana Jones": "Indiana Jones (character)",
    "Rambo": "John Rambo",
    "Banksy": "Girl with Balloon",
    "Kuba Wojewódzki": "Kuba Wojewódzki",
    "Marilyn Monroe": "Marilyn Monroe",
    "Steven Spielberg": "Steven Spielberg",
    "Samwise Gamgee": "Sean Astin",
    'Samwise Gamgee ("Sam") towarzysz Frodo z Władcy Pierścieni': "Sean Astin",
}


def _photo_norm_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    normalized = normalized.lower()
    normalized = normalized.replace("’", "").replace("'", "").replace('"', "")
    normalized = re.sub(r"\(.*?\)", " ", normalized)
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def _photo_variants(name: str, category: str) -> list[str]:
    base = str(name or "").strip()
    variants = [base]
    stripped = re.sub(r"\(.*?\)", "", base).strip(" -")
    if stripped:
        variants.append(stripped)
    short = re.split(r"\s+-\s+|\s+towarzysz\s+", stripped, maxsplit=1)[0].strip()
    if short:
        variants.append(short)
    if category == "popculture":
        alias = POPCULTURE_IMAGE_ALIASES.get(base) or POPCULTURE_IMAGE_ALIASES.get(stripped)
        if alias:
            variants.append(alias)
    out: list[str] = []
    seen: set[str] = set()
    for item in variants:
        key = _photo_norm_key(item)
        if key and key not in seen:
            seen.add(key)
            out.append(item)
    return out


@lru_cache(maxsize=12)
def _photo_lookup_index(folder: str) -> dict[str, str]:
    idx: dict[str, tuple[int, int, str]] = {}
    folder_path = Path(folder)
    if not folder_path.exists():
        return {}
    for p in folder_path.iterdir():
        if p.suffix.lower() not in PHOTO_EXTS or not p.is_file():
            continue
        stem = p.stem
        stem_base = re.sub(r"-\d+$", "", stem)
        key = _photo_norm_key(stem_base.replace("_", " "))
        if not key:
            continue
        rank = (0 if stem == stem_base else 1, len(stem))
        current = idx.get(key)
        if current is None or rank < (current[0], current[1]):
            idx[key] = (rank[0], rank[1], str(p))
    return {k: v[2] for k, v in idx.items()}


def _find_local_photo(name: str, category: str) -> str | None:
    folder = PHOTO_DIR_POPCULTURE if category == "popculture" else PHOTO_DIR_PERSON
    index = _photo_lookup_index(str(folder))
    for variant in _photo_variants(name, category):
        key = _photo_norm_key(variant)
        path = index.get(key)
        if path:
            return path
    tokens = [t for t in _photo_norm_key(name).split(" ") if len(t) >= 4]
    if len(tokens) >= 2:
        for key, path in index.items():
            if all(token in key for token in tokens[:2]):
                return path
    return None


@lru_cache(maxsize=256)
def _download_wikipedia_photo(name: str, category: str) -> str | None:
    target_dir = PHOTO_DIR_POPCULTURE if category == "popculture" else PHOTO_DIR_PERSON
    target_dir.mkdir(parents=True, exist_ok=True)

    user_agent = {"User-Agent": "archetypy-admin/1.0 (image-fetch)"}
    for variant in _photo_variants(name, category):
        title = quote(variant.replace(" ", "_"))
        for lang in ("pl", "en"):
            summary_url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{title}"
            try:
                resp = requests.get(summary_url, headers=user_agent, timeout=3)
                if resp.status_code != 200:
                    continue
                payload = resp.json()
                thumb = (payload.get("thumbnail") or {}).get("source") or (payload.get("originalimage") or {}).get(
                    "source"
                )
                if not thumb:
                    continue
                img_resp = requests.get(thumb, headers=user_agent, timeout=6)
                if img_resp.status_code != 200 or not img_resp.content:
                    continue
                ext = Path(thumb.split("?")[0]).suffix.lower()
                if ext not in PHOTO_EXTS:
                    ext = ".jpg"
                filename = f"{_logo_norm_key(variant) or 'photo'}{ext}"
                out_path = target_dir / filename
                out_path.write_bytes(img_resp.content)
                _photo_lookup_index.cache_clear()
                return str(out_path)
            except Exception:
                continue
    return None


def _resolve_photo_path(name: str, category: str) -> str | None:
    local = _find_local_photo(name, category)
    if local:
        return local
    return _download_wikipedia_photo(name, category)


def _people_photo_grid_html(names: list[str], category: str = "person") -> str:
    unique_names = list(dict.fromkeys([str(x).strip() for x in (names or []) if str(x).strip()]))
    if not unique_names:
        return ""

    cards: list[str] = []
    for raw_name in unique_names:
        caption = canonical_person_name(raw_name) if category == "person" else raw_name
        path = _resolve_photo_path(raw_name, category=category)

        if path and Path(path).exists():
            try:
                data_uri = _photo_to_data_uri(path)
                avatar = f"<img src='{data_uri}' alt='{html.escape(caption)}' />"
            except Exception:
                avatar = "<div class='ap-face-ph'>?</div>"
        else:
            initials = "".join(part[0] for part in caption.split()[:2]).upper() or "?"
            avatar = f"<div class='ap-face-ph'>{html.escape(initials)}</div>"

        name_html = html.escape(caption)
        if category == "person":
            link_url = person_wikipedia_links.get(canonical_person_name(raw_name))
            if link_url:
                name_html = f"<a href='{link_url}' target='_blank'>{name_html}</a>"

        cards.append(
            "<div class='ap-face-card'>"
            f"<div class='ap-face-avatar'>{avatar}</div>"
            f"<div class='ap-face-name'>{name_html}</div>"
            "</div>"
        )

    if not cards:
        return ""
    return f"<div class='ap-face-grid'>{''.join(cards)}</div>"


def _fallback_metric_rows(archetype_data: dict) -> list[dict]:
    return [
        {"label": "Esencja", "kind": "text", "value": archetype_data.get("description", "")},
        {"label": "Rozbudowany opis", "kind": "text", "value": archetype_data.get("storyline", "")},
        {"label": "Kluczowe atrybuty", "kind": "list", "value": archetype_data.get("core_traits", [])},
        {"label": "Atuty", "kind": "list", "value": archetype_data.get("strengths", [])},
        {"label": "Słabości", "kind": "list", "value": archetype_data.get("weaknesses", [])},
        {
            "label": "Słowa-klucze (Talking points)",
            "kind": "list",
            "value": archetype_data.get("keyword_messaging", []),
        },
        {"label": "Sygnatury wizualne", "kind": "list", "value": archetype_data.get("visual_elements", [])},
        {
            "label": "Przykłady archetypów",
            "kind": "examples",
            "value": {
                "Politycy": archetype_data.get("examples_person", []),
                "Marki/organizacje": archetype_data.get("example_brands", []),
                "Popkultura/postacie": archetype_data.get("metric_examples", {}).get("Popkultura/postacie", []),
            },
        },
        {"label": "Paleta kolorów (HEX)", "kind": "colors", "value": archetype_data.get("color_palette", [])},
    ]


def _split_metric_line_items(text: str) -> list[str]:
    pieces: list[str] = []
    for chunk in re.split(r"\n+|[;]", str(text or "")):
        clean = re.sub(r"^[•\-\u2013\u2014]\s*", "", chunk.strip())
        clean = clean.strip(" ,.")
        if clean:
            pieces.append(clean)
    return pieces


def _story_antagonist_html(value: str) -> str:
    storyline: list[str] = []
    antagonist: list[str] = []
    mode = "storyline"
    for line in _split_metric_line_items(value):
        low = line.casefold()
        if low.startswith("storyline"):
            mode = "storyline"
            rest = line.split(":", 1)[1].strip() if ":" in line else ""
            if rest:
                storyline.append(rest)
            continue
        if low.startswith("antagonista"):
            mode = "antagonista"
            rest = line.split(":", 1)[1].strip() if ":" in line else ""
            if rest:
                antagonist.append(rest)
            continue
        if mode == "antagonista":
            antagonist.append(line)
        else:
            storyline.append(line)

    if not storyline and value:
        storyline = [str(value).strip()]

    story_html = (
        "<ul class='ap-simple-list'>"
        + "".join(f"<li>{html.escape(item)}</li>" for item in storyline if item)
        + "</ul>"
        if storyline
        else "<span style='color:#7c8799;'>—</span>"
    )
    ant_html = (
        "<ul class='ap-simple-list'>"
        + "".join(f"<li>{html.escape(item)}</li>" for item in antagonist if item)
        + "</ul>"
        if antagonist
        else "<span style='color:#7c8799;'>—</span>"
    )
    return (
        "<div class='ap-story-antag'>"
        "<div class='ap-story-head'>Storyline:</div>"
        f"{story_html}"
        "<div class='ap-story-head'>Antagonista (z czym walczy?):</div>"
        f"{ant_html}"
        "</div>"
    )


COMPACT_METRIC_LABELS_CF = {
    "grupa",
    "podstawowe pragnienie",
    "cel",
    "największa obawa",
    "strategia",
    "pułapka",
    "dar",
    "cień",
}


def _metric_text_plain(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    parts = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    return " ".join(parts).strip()


def _metric_row_html(row: dict, archetype_data: dict, text_color: str) -> str:
    label_raw = str(row.get("label", "")).strip()
    if label_raw.casefold() == "core triplet":
        return ""
    label = html.escape(label_raw)
    kind = row.get("kind", "text")
    value = row.get("value")

    if kind == "examples":
        examples = value or {}
        politicians = [canonical_person_name(x) for x in (examples.get("Politycy") or [])]
        brands = examples.get("Marki/organizacje") or []
        popculture = examples.get("Popkultura/postacie") or []

        pol_html = ", ".join(person_link(name) for name in politicians) if politicians else "—"
        pol_faces_html = _people_photo_grid_html(politicians, category="person")
        brands_html = (
            build_brand_icons_html(brands, logos_dir, label_color=text_color)
            if brands
            else "<span style='color:#7c8799;font-size:.97em;'>—</span>"
        )
        pop_faces_html = _people_photo_grid_html(popculture, category="popculture")
        pop_html = ", ".join(html.escape(x) for x in popculture) if popculture else "—"
        return f"""
        <div class="ap-metric-row">
            <div class="ap-metric-label">{label}</div>
            <div class="ap-metric-value">
                <div class="ap-example-head ap-example-head-first"><b>Politycy:</b></div>
                {pol_faces_html if pol_faces_html else f"<div>{pol_html}</div>"}
                <div class="ap-example-head"><b>Marki/organizacje:</b></div>
                {brands_html}
                <div class="ap-example-head"><b>Popkultura/postacie:</b></div>
                {pop_faces_html if pop_faces_html else f"<div>{pop_html}</div>"}
            </div>
        </div>
        """

    if kind == "colors":
        colors = [str(c).upper() for c in (value or archetype_data.get("color_palette", [])) if str(c).strip()]
        palette_html = palette_boxes_html(colors) if colors else "<span style='color:#7c8799;'>—</span>"
        return f"""
        <div class="ap-metric-row">
            <div class="ap-metric-label">{label}</div>
            <div class="ap-metric-value">
                {palette_html}
            </div>
        </div>
        """

    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
        label_cf = label_raw.casefold()
        row_extra_cls = ""

        if not items:
            value_html = "<span style='color:#7c8799;'>—</span>"
        elif label_cf in {"kluczowe atrybuty", "słowa-klucze (talking points)"}:
            row_extra_cls = " ap-metric-row-chips"
            chips = "".join(f"<span class='ap-pill'>{html.escape(item)}</span>" for item in items)
            value_html = f"<div class='ap-pill-wrap'>{chips}</div>"
        elif label_cf == "slogany (taglines)":
            value_html = (
                "<ul class='ap-simple-list'>"
                + "".join(f"<li><i>{html.escape(item)}</i></li>" for item in items)
                + "</ul>"
            )
        elif label_cf == "atuty":
            value_html = (
                "<ul class='ap-qual-list ap-qual-pos'>"
                + "".join(
                    f"<li><span class='ap-qual-ico'>✅</span><span>{html.escape(item)}</span></li>" for item in items
                )
                + "</ul>"
            )
        elif label_cf == "słabości":
            value_html = (
                "<ul class='ap-qual-list ap-qual-neg'>"
                + "".join(
                    f"<li><span class='ap-qual-ico'>❌</span><span>{html.escape(item)}</span></li>" for item in items
                )
                + "</ul>"
            )
        elif label_cf == "sygnatury wizualne":
            value_html = "<p>" + html.escape(", ".join(items)) + "</p>"
        else:
            bullets = "".join(f"<li>{html.escape(item)}</li>" for item in items)
            value_html = f"<ul class='ap-simple-list'>{bullets}</ul>"
    else:
        row_extra_cls = ""
        text = str(value or "").strip()
        if not text:
            value_html = "<span style='color:#7c8799;'>—</span>"
        elif label_raw.casefold() == "rozbudowany opis":
            paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
            value_html = "".join(f"<p><i>{html.escape(p)}</i></p>" for p in paragraphs)
        elif label_raw.casefold() == "slogany (taglines)":
            items = _split_metric_line_items(text) or [text]
            value_html = (
                "<ul class='ap-simple-list'>"
                + "".join(f"<li><i>{html.escape(item)}</i></li>" for item in items if str(item).strip())
                + "</ul>"
            )
        elif label_raw.casefold() == "oś narracyjna i antagonista":
            value_html = _story_antagonist_html(text)
        else:
            paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
            value_html = "".join(f"<p>{html.escape(p)}</p>" for p in paragraphs)

    return f"""
    <div class="ap-metric-row{row_extra_cls}">
        <div class="ap-metric-label">{label}</div>
        <div class="ap-metric-value">{value_html}</div>
    </div>
    """


SECTION_ICON_MAP = {
    "1": "🧠",
    "2": "🏛️",
    "3": "🗣️",
    "4": "✅",
    "5": "🎨",
    "6": "🧭",
    "7": "🛡️",
    "8": "⚖️",
    "9": "🧰",
}


def _expanded_subsection_content_html(content_lines: list[str], subsection_title: str = "") -> str:
    if not content_lines:
        return ""

    lines = []
    for raw in content_lines:
        txt = str(raw or "").strip()
        if not txt:
            continue
        txt = re.sub(r"^[•\-\u2013\u2014]\s*", "", txt).strip()
        if txt:
            lines.append(txt)
    if not lines:
        return ""

    subtitle = str(subsection_title or "").strip()
    m = re.match(r"^(\d+\.\d+(?:\.\d+)?)\.", subtitle)
    sub_prefix = (m.group(1) + ".") if m else ""

    bullet_only_prefixes = {
        "1.6.", "2.1.", "2.3.", "2.4.", "2.5.",
        "3.6.", "3.8.",
        "4.1.", "4.2.", "4.3.",
        "5.2.", "5.3.",
        "6.1.", "6.2.",
        "7.1.", "7.2.", "7.4.",
        "8.2.",
        "9.2.",
    }
    numbered_prefixes = {"3.4.", "3.5.5.", "9.3."}

    def p(text: str, cls: str = "") -> str:
        cls_attr = f" class='{cls}'" if cls else ""
        return f"<p{cls_attr}>{html.escape(text)}</p>"

    def p_bold_prefix(text: str, allowed_labels: set[str], cls: str = "") -> str:
        m_local = re.match(r"^([^:]{1,40}):\s*(.*)$", text)
        if not m_local:
            return p(text, cls=cls)
        label = m_local.group(1).strip()
        value = m_local.group(2).strip()
        if label not in allowed_labels:
            return p(text, cls=cls)
        cls_attr = f" class='{cls}'" if cls else ""
        return f"<p{cls_attr}><b>{html.escape(label)}:</b> {html.escape(value)}</p>"

    def split_semicolon_items(src_lines: list[str]) -> list[str]:
        out: list[str] = []
        for ln in src_lines:
            if ";" in ln:
                parts = [x.strip(" ;") for x in re.split(r"\s*;\s*", ln) if x.strip(" ;")]
                out.extend(parts if parts else [ln])
            else:
                out.append(ln)
        return [x for x in out if x]

    def ul(items: list[str], cls: str = "ap-ext-list") -> str:
        if not items:
            return ""
        return f"<ul class='{cls}'>" + "".join(f"<li>{html.escape(i)}</li>" for i in items if i.strip()) + "</ul>"

    def ol(items: list[str], cls: str = "ap-ext-ol") -> str:
        if not items:
            return ""
        return f"<ol class='{cls}'>" + "".join(f"<li>{html.escape(i)}</li>" for i in items if i.strip()) + "</ol>"

    if sub_prefix == "1.2.":
        return "".join(p(x) for x in lines)

    if sub_prefix == "1.3.":
        first_two = lines[:2]
        rest = lines[2:]
        return ul(first_two) + "".join(p(x) for x in rest)

    if sub_prefix in {"1.4.", "1.5.", "8.1."}:
        lead = lines[0]
        rest_items = split_semicolon_items(lines[1:])
        return p(lead) + ul(rest_items)

    if sub_prefix == "2.2.":
        allowed = {"Decyzje", "Tempo", "Priorytety"}
        return "".join(p_bold_prefix(x, allowed) for x in lines)

    if sub_prefix == "3.2.":
        allowed = {"Ton", "Emocja po kontakcie"}
        return "".join(p_bold_prefix(x, allowed) for x in lines)

    if sub_prefix == "3.3.":
        blocks: list[str] = []
        idx_limit = None
        for i, ln in enumerate(lines):
            if ln.casefold().startswith("do ograniczenia"):
                idx_limit = i
                break
        if idx_limit is None:
            return "".join(p(x) for x in lines)
        before = lines[:idx_limit]
        after = lines[idx_limit + 1:]
        if before:
            blocks.extend(p(x) for x in before)
        blocks.append("<div class='ap-ext-topic'><b>Do ograniczenia:</b></div>")
        blocks.append(ul(split_semicolon_items(after)))
        return "".join(blocks)

    if sub_prefix in numbered_prefixes:
        return ol(lines)

    if sub_prefix == "7.3.":
        num_items: list[str] = []
        tail: list[str] = []
        for ln in lines:
            if ln.casefold().startswith("zakaz:"):
                tail.append(ln)
            else:
                num_items.append(ln)
        out = ol(num_items)
        for t in tail:
            out += p_bold_prefix(t, {"Zakaz"})
        return out

    if sub_prefix == "9.1.":
        do_items: list[str] = []
        dont_items: list[str] = []
        mode: str | None = None
        for ln in lines:
            low = ln.casefold()
            if low.startswith("do:"):
                mode = "do"
                continue
            if ("don't" in low) or ("don’t" in low) or ("dont" in low):
                mode = "dont"
                continue
            if mode == "do":
                do_items.extend(split_semicolon_items([ln]))
            elif mode == "dont":
                dont_items.extend(split_semicolon_items([ln]))
        blocks = []
        if do_items:
            blocks.append("<div class='ap-ext-topic'><b>DO:</b></div>")
            blocks.append(ul(do_items))
        if dont_items:
            blocks.append("<div class='ap-ext-topic'><b>DON'T:</b></div>")
            blocks.append(ul(dont_items))
        return "".join(blocks) if blocks else "".join(p(x) for x in lines)

    if sub_prefix == "9.4.":
        diag_idx = None
        for i, ln in enumerate(lines):
            if ln.casefold().startswith("pytania diagnostyczne"):
                diag_idx = i
                break
        if diag_idx is None:
            return ul(split_semicolon_items(lines))
        first = split_semicolon_items(lines[:diag_idx])
        second = split_semicolon_items(lines[diag_idx + 1:])
        blocks = []
        if first:
            blocks.append(ul(first))
        blocks.append("<div class='ap-ext-topic'><b>Pytania diagnostyczne:</b></div>")
        if second:
            blocks.append(ul(second))
        return "".join(blocks)

    if sub_prefix == "8.2.":
        items = split_semicolon_items(lines)
        rendered = []
        for item in items:
            m_line = re.match(r"^([A-Za-zĄĆĘŁŃÓŚŹŻąćęłńóśźż]+)\s+[–-]\s+(.+)$", item)
            if m_line:
                rendered.append(f"<li><b>{html.escape(m_line.group(1))}</b> — {html.escape(m_line.group(2))}</li>")
            else:
                rendered.append(f"<li>{html.escape(item)}</li>")
        return "<ul class='ap-ext-list'>" + "".join(rendered) + "</ul>"

    if sub_prefix == "5.1.2.":
        groups: list[tuple[str, list[str]]] = []
        current_head = ""
        current_items: list[str] = []
        for ln in lines:
            if re.match(r"^Zestaw\s+\d+", ln, flags=re.IGNORECASE):
                if current_head or current_items:
                    groups.append((current_head, current_items))
                current_head = ln
                current_items = []
            else:
                current_items.extend(split_semicolon_items([ln]))
        if current_head or current_items:
            groups.append((current_head, current_items))

        out = []
        for head, items in groups:
            if head:
                out.append(p(head, cls="ap-ext-step-head"))
            if items:
                out.append(ul(items))
        return "".join(out)

    if sub_prefix == "3.7.":
        blocks: list[str] = []
        prev_technika = False
        for ln in lines:
            if re.match(r"^\d+\)\s+", ln):
                blocks.append(p(ln, cls="ap-ext-step-head"))
                prev_technika = False
                continue
            if ln.casefold().startswith("technika:"):
                blocks.append(p_bold_prefix(ln, {"Technika"}))
                prev_technika = True
                continue
            if ln.casefold().startswith("schemat:"):
                blocks.append(p_bold_prefix(ln, {"Schemat"}))
                prev_technika = False
                continue
            if ln.casefold().startswith("po co?"):
                blocks.append(p_bold_prefix(ln, {"Po co?"}))
                prev_technika = False
                continue
            if prev_technika and "," in ln and ("„" in ln or "\"" in ln):
                parts = [x.strip() for x in re.split(r"\s*,\s*", ln) if x.strip()]
                blocks.append(ul(parts))
                prev_technika = False
                continue
            blocks.append(p(ln))
            prev_technika = False
        return "".join(blocks)

    if sub_prefix in bullet_only_prefixes:
        return ul(split_semicolon_items(lines))

    # Domyślnie: akapity (bez agresywnego dzielenia po przecinkach)
    return "".join(p(x) for x in lines)


def _expanded_sections_html(archetype_data: dict) -> str:
    sections = archetype_data.get("expanded_sections") or []
    if not sections:
        return "<div class='ap-ext-empty'>Brak rozbudowanego opisu dla tego archetypu.</div>"

    section_blocks: list[str] = []
    for section in sections:
        sec_title_raw = str(section.get("title", "")).strip()
        sec_title = html.escape(sec_title_raw)
        icon = ""
        m_sec = re.match(r"^([1-9])\.\s+", sec_title_raw)
        if m_sec:
            icon = SECTION_ICON_MAP.get(m_sec.group(1), "")
        subsection_blocks: list[str] = []
        for subsection in section.get("subsections", []):
            sub_title_raw = str(subsection.get("title", "")).strip()
            sub_title = html.escape(sub_title_raw)
            content_lines = [str(line).strip() for line in subsection.get("content", []) if str(line).strip()]
            if not content_lines and not sub_title:
                continue
            content_html = _expanded_subsection_content_html(content_lines, sub_title_raw)

            subsection_blocks.append(
                f"""
                <div class="ap-ext-subsection">
                    {f"<div class='ap-ext-subtitle'>{sub_title}</div>" if sub_title else ""}
                    <div class="ap-ext-content">{content_html}</div>
                </div>
                """
            )

        section_blocks.append(
            f"""
            <section class="ap-ext-section">
                <div class="ap-ext-title">{f"<span class='ap-ext-title-icon'>{icon}</span>" if icon else ""}<span>{sec_title}</span></div>
                <div class="ap-ext-body">{''.join(subsection_blocks)}</div>
            </section>
            """
        )
    return "".join(section_blocks)


def render_archetype_card(archetype_data, main=True, supplement=False, gender_code="M"):
    if not archetype_data:
        st.warning("Brak danych o archetypie.")
        return

    palette = [str(c).upper() for c in (archetype_data.get("color_palette", []) or []) if str(c).strip()]
    if main:
        bg_color = palette[0] if len(palette) >= 1 else "#2B2D41"
        border_color = palette[1] if len(palette) >= 2 else (palette[0] if palette else "#E99836")
        text_color = "#F8FAFC" if is_color_dark(bg_color) else "#1F2937"
        tagline_color = "#FFE082" if is_color_dark(bg_color) else "#7A2037"
    else:
        bg_color = "#F3F4F6"
        border_color = palette[0] if palette else ("#40b900" if supplement else "#FFD22F")
        text_color = "#1F2937"
        tagline_color = border_color

    is_dark_card = is_color_dark(bg_color)
    link_color = "#DDEAFF" if is_color_dark(bg_color) else "#144FA8"
    details_border_color = "rgba(255,255,255,.30)" if is_dark_card else "rgba(17,24,39,.20)"
    details_bg_color = "rgba(255,255,255,.07)" if is_dark_card else "rgba(255,255,255,.74)"
    details_title_bg = (
        "linear-gradient(90deg, rgba(255,210,47,.20), rgba(255,255,255,.03))"
        if is_dark_card
        else "linear-gradient(90deg, rgba(17,24,39,.08), rgba(17,24,39,.02))"
    )
    details_subtitle_color = "#FFE082" if is_dark_card else "#1F2937"
    details_text_color = "#EDF2FF" if is_dark_card else "#1F2937"
    pill_bg = "rgba(255,255,255,.12)" if is_dark_card else "#F8FAFF"
    pill_border = "rgba(255,255,255,.35)" if is_dark_card else "#A4B4D4"
    pill_text = "#F8FAFF" if is_dark_card else "#1F355E"
    box_shadow = f"0 12px 28px 0 {border_color}33"

    base_name = base_masc_from_any(str(archetype_data.get("name", "")).strip())
    core_triplet = (
        archetype_data.get("core_triplet")
        or CORE_TRIPLET_MAP.get(base_name, "")
        or archetype_data.get("tagline")
        or ""
    )

    width_card = "86vw"
    min_h = "860px"

    metric_rows_src = list(archetype_data.get("metric_rows") or _fallback_metric_rows(archetype_data))
    metric_rows = [
        row for row in metric_rows_src
        if str((row or {}).get("label", "")).strip().casefold() != "core triplet"
    ]
    metric_blocks: list[str] = []
    compact_buffer: list[tuple[str, str]] = []

    def _flush_compact_metric_buffer() -> None:
        nonlocal compact_buffer
        if not compact_buffer:
            return
        tiles = "".join(
            f"<div class='ap-metric-tile'><div class='ap-metric-tile-label'>{html.escape(lbl)}</div>"
            f"<div class='ap-metric-tile-value'>{html.escape(val)}</div></div>"
            for lbl, val in compact_buffer
        )
        metric_blocks.append(f"<div class='ap-metric-grid'>{tiles}</div>")
        compact_buffer = []

    for row in metric_rows:
        label_raw = str((row or {}).get("label", "")).strip()
        label_cf = label_raw.casefold()
        kind = (row or {}).get("kind", "text")
        value = (row or {}).get("value")

        is_compact = (
            label_cf in COMPACT_METRIC_LABELS_CF
            and kind not in {"examples", "colors"}
            and not isinstance(value, list)
        )
        if is_compact:
            plain_value = _metric_text_plain(value)
            if plain_value:
                compact_buffer.append((label_raw, plain_value))
            continue

        _flush_compact_metric_buffer()
        row_html = _metric_row_html(row, archetype_data, text_color)
        if row_html.strip():
            metric_blocks.append(row_html)

    _flush_compact_metric_buffer()
    metric_rows_html = "".join(metric_blocks)
    expanded_html = _expanded_sections_html(archetype_data)
    name_slug = re.sub(r"[^a-z0-9]+", "-", _logo_norm_key(archetype_data.get("name", "archetyp"))).strip("-")
    role_slug = "main" if main else ("supp" if supplement else "aux")
    card_dom_id = f"ap-arch-{name_slug}-{role_slug}"

    card_html_raw = dedent(f"""
        <style>
            #{card_dom_id}.ap-card-wrap {{
                max-width:{width_card};
                border: 3px solid {border_color};
                border-radius: 22px;
                background: {bg_color};
                box-shadow: {box_shadow};
                min-height: {min_h};
                padding: 2.8em 2.3em 2.2em 4.7em;
                margin-bottom: 32px;
                color: {text_color};
            }}
            #{card_dom_id} .ap-card-head {{
                display:flex;
                align-items:flex-start;
                gap:24px;
                margin-bottom:18px;
            }}
            #{card_dom_id} .ap-card-name {{
                font-size:2.38em;
                font-weight:700;
                line-height:1.08;
                margin-top:12px;
                margin-bottom:7px;
                color:{text_color};
            }}
            #{card_dom_id} .ap-card-tagline {{
                font-size:1.32em;
                font-style:italic;
                color:{tagline_color};
                margin-top:4px;
                margin-bottom:8px;
                font-weight:600;
            }}
            #{card_dom_id} .ap-metric-title {{
                font-size:1.62em;
                font-weight:700;
                color:{text_color};
                margin:22px 0 16px;
                letter-spacing:.01em;
            }}
            #{card_dom_id} .ap-metric-row {{
                border:none;
                border-radius:0;
                padding:0;
                margin-top:40px;
                margin-bottom:0;
                background:transparent;
            }}
            #{card_dom_id} .ap-metric-row:first-child {{
                margin-top:0;
            }}
            #{card_dom_id} .ap-metric-label {{
                font-size:1.15em;
                font-weight:700;
                color:{text_color};
                margin-top:0;
                margin-bottom:1px;
                letter-spacing:.02em;
            }}
            #{card_dom_id} .ap-example-head {{
                margin-top:24px;
                margin-bottom:12px;
                font-weight:700;
            }}
            #{card_dom_id} .ap-example-head-first {{
                margin-top:8px;
            }}
            #{card_dom_id} .ap-metric-value {{
                font-size:1em;
                line-height:1.56;
                color:{text_color};
            }}
            #{card_dom_id} .ap-metric-value p {{
                margin:0 0 6px 0;
            }}
            #{card_dom_id} .ap-simple-list {{
                margin:2px 0 4px 0;
                padding-left:21px;
            }}
            #{card_dom_id} .ap-story-antag {{
                margin-top:2px;
            }}
            #{card_dom_id} .ap-story-head {{
                font-weight:700;
                margin-top:8px;
                margin-bottom:2px;
            }}
            #{card_dom_id} .ap-simple-list li {{
                margin-bottom:4px;
            }}
            #{card_dom_id} .ap-qual-list {{
                margin:4px 0 6px 0;
                padding:0;
                list-style:none;
            }}
            #{card_dom_id} .ap-qual-list li {{
                display:flex;
                align-items:flex-start;
                gap:8px;
                margin-bottom:5px;
                line-height:1.42;
            }}
            #{card_dom_id} .ap-qual-ico {{
                display:inline-block;
                width:20px;
                text-align:center;
            }}
            #{card_dom_id} .ap-pill-wrap {{
                display:flex;
                flex-wrap:wrap;
                gap:7px;
            }}
            #{card_dom_id} .ap-pill {{
                display:inline-block;
                border-radius:999px;
                padding:6px 12px;
                border:1px solid {pill_border};
                background:{pill_bg};
                color:{pill_text};
                box-shadow:0 1px 0 rgba(0,0,0,.08);
                font-size:.95em;
                line-height:1.2;
            }}
            #{card_dom_id} .ap-metric-row-chips .ap-metric-label {{
                margin-bottom:16px;
            }}
            #{card_dom_id} .ap-metric-grid {{
                display:grid;
                grid-template-columns:repeat(2,minmax(0,1fr));
                gap:12px 12px;
                margin-top:34px;
            }}
            #{card_dom_id} .ap-metric-tile {{
                border:1px solid {details_border_color};
                border-radius:12px;
                background:{details_bg_color};
                padding:12px 13px;
            }}
            #{card_dom_id} .ap-metric-tile-label {{
                font-size:.99em;
                font-weight:700;
                margin-bottom:4px;
                color:{text_color};
            }}
            #{card_dom_id} .ap-metric-tile-value {{
                font-size:.96em;
                line-height:1.42;
                color:{text_color};
            }}
            #{card_dom_id} .ap-face-grid {{
                display:flex;
                flex-wrap:wrap;
                gap:12px;
                margin-top:8px;
                align-items:flex-start;
            }}
            #{card_dom_id} .ap-face-card {{
                width:114px;
                text-align:center;
                display:flex;
                flex-direction:column;
                align-items:center;
                justify-content:flex-start;
            }}
            #{card_dom_id} .ap-face-avatar img,
            #{card_dom_id} .ap-face-avatar .ap-face-ph {{
                width:94px;
                height:94px;
                border-radius:12px;
                object-fit:cover;
                object-position:center 0%;
                border:1px solid rgba(0,0,0,.18);
                background:rgba(255,255,255,.85);
                margin:0 auto;
                display:flex;
                align-items:center;
                justify-content:center;
                font-weight:700;
            }}
            #{card_dom_id} .ap-face-name {{
                margin-top:4px;
                font-size:.80em;
                line-height:1.25;
            }}
            #{card_dom_id} .ap-face-name a {{
                color:{link_color};
                text-decoration:underline;
            }}
            #{card_dom_id} .ap-details {{
                margin-top:18px;
                border:1px solid {details_border_color};
                border-radius:14px;
                background:{details_bg_color};
                overflow:hidden;
            }}
            #{card_dom_id} .ap-details > summary {{
                cursor:pointer;
                list-style:none;
                padding:13px 14px;
                font-size:1em;
                font-weight:700;
                color:{text_color};
                border-bottom:1px solid {details_border_color};
                display:flex;
                align-items:center;
                justify-content:space-between;
            }}
            #{card_dom_id} .ap-details > summary::-webkit-details-marker {{ display:none; }}
            #{card_dom_id} .ap-details .ap-summary-close {{ display:none; }}
            #{card_dom_id} .ap-details[open] .ap-summary-open {{ display:none; }}
            #{card_dom_id} .ap-details[open] .ap-summary-close {{ display:inline; }}
            #{card_dom_id} .ap-expanded-wrap {{
                padding:12px 12px 8px;
            }}
            #{card_dom_id} .ap-ext-section {{
                border:1px solid {details_border_color};
                border-radius:12px;
                margin-bottom:10px;
                background:{details_bg_color};
                overflow:hidden;
            }}
            #{card_dom_id} .ap-ext-title {{
                background:{details_title_bg};
                border-left:4px solid {tagline_color};
                padding:10px 12px;
                font-size:1.03em;
                font-weight:700;
                color:{text_color};
                display:flex;
                align-items:center;
                gap:8px;
            }}
            #{card_dom_id} .ap-ext-title-icon {{
                font-size:1.08em;
                line-height:1;
            }}
            #{card_dom_id} .ap-ext-body {{
                padding:10px 12px 6px;
            }}
            #{card_dom_id} .ap-ext-subsection {{
                margin-bottom:12px;
                padding-bottom:11px;
                border-bottom:1px dashed {details_border_color};
            }}
            #{card_dom_id} .ap-ext-subsection:last-child {{
                border-bottom:none;
                margin-bottom:0;
                padding-bottom:4px;
            }}
            #{card_dom_id} .ap-ext-subtitle {{
                font-size:1.02em;
                font-weight:700;
                color:{details_subtitle_color};
                margin-top:12px;
                margin-bottom:4px;
            }}
            #{card_dom_id} .ap-ext-content p {{
                margin:0 0 6px 0;
                font-size:.95em;
                line-height:1.5;
                color:{details_text_color};
            }}
            #{card_dom_id} .ap-ext-content .ap-ext-step-head {{
                margin-top:13px;
                margin-bottom:6px;
                font-weight:700;
            }}
            #{card_dom_id} .ap-ext-content p:first-child.ap-ext-step-head {{
                margin-top:2px;
            }}
            #{card_dom_id} .ap-ext-topic {{
                margin:8px 0 5px 0;
                font-weight:600;
                color:{details_text_color};
            }}
            #{card_dom_id} .ap-ext-list {{
                margin:1px 0 10px 0;
                padding-left:20px;
            }}
            #{card_dom_id} .ap-ext-ol {{
                margin:1px 0 10px 0;
                padding-left:24px;
            }}
            #{card_dom_id} .ap-ext-list-nested {{
                margin-top:4px;
            }}
            #{card_dom_id} .ap-ext-list li,
            #{card_dom_id} .ap-ext-ol li {{
                margin-bottom:5px;
                font-size:.94em;
                line-height:1.42;
                color:{details_text_color};
            }}
            #{card_dom_id} .ap-ext-empty {{
                color:{details_text_color};
                font-size:.95em;
                padding:8px 2px 12px;
            }}
            @media (max-width: 900px) {{
                #{card_dom_id}.ap-card-wrap {{
                    padding:1.35em 1.0em 1.05em 2.15em;
                }}
                #{card_dom_id} .ap-card-head {{
                    flex-direction:column;
                    gap:8px;
                }}
                #{card_dom_id} .ap-card-name {{
                    margin-top:0;
                    font-size:1.82em;
                }}
                #{card_dom_id} .ap-metric-grid {{
                    grid-template-columns:1fr;
                }}
            }}
        </style>
        <div id="{card_dom_id}" class="ap-card-wrap">
            <div class="ap-card-head">
                <div style="flex-shrink:0;">
                    {arche_icon_img_html(archetype_data.get('name', '?'), height_px=146, gender_code=gender_code)}
                </div>
                <div>
                    <div class="ap-card-name">{html.escape(str(archetype_data.get('name', '?')))}</div>
                    <div class="ap-card-tagline">{html.escape(str(core_triplet))}</div>
                </div>
            </div>
            <div class="ap-metric-title">Metryka archetypu</div>
            {metric_rows_html}
            <details class="ap-details">
                <summary>
                    <span class="ap-summary-open">Pokaż rozbudowany opis</span>
                    <span class="ap-summary-close">Zwiń</span>
                </summary>
                <div class="ap-expanded-wrap">
                    {expanded_html}
                </div>
            </details>
        </div>
    """)
    # Usuń wcięcia na początku linii: inaczej markdown Streamlit traktuje HTML jak code block.
    card_html = "\n".join(line.lstrip() for line in card_html_raw.splitlines()).strip()
    st.markdown(card_html, unsafe_allow_html=True)

# ============ RESZTA PANELU: nagłówki, kolumny, eksporty, wykres, tabele respondentów ============

def show_report(sb, study: dict, wide: bool = True, public_view: bool = False) -> None:
    # stan przełącznika eksportu (bezpieczeństwo przy pierwszym renderze)
    st.session_state.setdefault("prep_docs", False)
    # CSS musi być doładowywany na każdym rerunie (zmiana osoby w selectboxie).
    inject_global_css(GLOBAL_CSS)
    # Szerokość raportu (również dla widoku publicznego).
    st.markdown(
        f"<style>.block-container{{max-width:{'98vw' if wide else '1160px'} !important;}}</style>",
        unsafe_allow_html=True,
    )

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

    if not public_view:
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

            # <<< UNIKALNE NAZWY TYLKO DLA TEGO RESPONDENTA >>>
            main_i, aux_i, supp_i = pick_top_3_archetypes(arcsums, ARCHE_NAMES_ORDER)

            main = archetype_extended.get(main_i, {})
            second = archetype_extended.get(aux_i, {}) if aux_i != main_i else {}
            supplement = archetype_extended.get(supp_i, {}) if supp_i not in [main_i, aux_i] else {}

            # wersje do wyświetlania – żeńskie/męskie
            main_disp = dict(main);
            main_disp["name"] = disp_name(main.get("name", main_i or ""))
            second_disp = dict(second)
            if second:
                second_disp["name"] = disp_name(second.get("name", aux_i or ""))

            supplement_disp = dict(supplement)
            if supplement:
                supplement_disp["name"] = disp_name(supplement.get("name", supp_i or ""))

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
                "Główny archetyp": main_i,
                "Cechy kluczowe": archetype_features.get(main_i, ""),
                "Opis": main.get("description", ""),
                "Storyline": main.get("storyline", ""),
                "Rekomendacje": "\n".join(main.get("recommendations", [])),
                "Archetyp wspierający": aux_i if aux_i != main_i else "",
                "Cechy wspierający": archetype_features.get(aux_i, "") if aux_i != main_i else "",
                "Opis wspierający": second.get("description", "") if aux_i != main_i else "",
                "Storyline wspierający": second.get("storyline", "") if aux_i != main_i else "",
                "Rekomendacje wspierający": "\n".join(second.get("recommendations", [])) if aux_i != main_i else "",
                "Archetyp poboczny": supp_i if supp_i not in [main_i, aux_i] else "",
                "Cechy poboczny": archetype_features.get(supp_i, "") if supp_i not in [main_i, aux_i] else "",
                "Opis poboczny": supplement.get("description", "") if supp_i not in [main_i, aux_i] else "",
                "Storyline poboczny": supplement.get("storyline", "") if supp_i not in [main_i, aux_i] else "",
                "Rekomendacje poboczny": "\n".join(supplement.get("recommendations", [])) if supp_i not in [main_i, aux_i] else "",
                **{f"Kolor_{k}": v for k, v in col_scores.items()},
                **{f"Kolor_{k}_%": v for k, v in col_perc.items()},
            })

        results_df = pd.DataFrame(results)

        if not results_df.empty and "Czas ankiety" in results_df.columns:

            results_df = results_df.sort_values("Czas ankiety", ascending=True)

            st.markdown(f'<div style="font-size:2.1em;font-weight:600;margin-bottom:22px;">Informacje na temat archetypów {personGen}</div>', unsafe_allow_html=True)

            # --- ⬇️ RANKING I WYKRES NA BAZIE ŚREDNIEJ (0–20), NIE LICZEBNOŚCI! ---
            # Kolejność zgodna z "Rozkład archetypów na osiach potrzeb"
            # (od godz. 12, zgodnie z ruchem wskazówek zegara).
            archetype_names = KOLO_NAMES_ORDER

            # 1) średnia suma punktów dla każdego archetypu (0–20)
            mean_archetype_scores = {
                k: float(results_df[k].mean()) if k in results_df.columns else 0.0
                for k in archetype_names
            }

            # <<< NAZWY „AVG” – tylko dla ŚREDNICH >>>
            main_avg, aux_avg, supp_avg = pick_top_3_archetypes(mean_archetype_scores,
                                                                archetype_names)

            # ——— PRÓG 70% dla archetypu pobocznego (liczony na średnich % z całego df)
            means_pct_for_threshold = mean_pct_by_archetype_from_df(data)  # {archetyp: %}
            SHOW_SUPP = should_show_supplement(supp_avg, means_pct_for_threshold, threshold=70.0)
            if not SHOW_SUPP:
                # wyłącz poboczny globalnie (radar, koła, karty)
                supp_avg = None


            # Progi widoczności pobocznego: używamy % (0..100) ze średnich
            means_pct_for_threshold = mean_pct_by_archetype_from_df(data)  # {archetyp: %}
            SHOW_SUPP = should_show_supplement(supp_avg, means_pct_for_threshold, threshold=70.0)
            if not SHOW_SUPP:
                # „Wyłącz” poboczny globalnie – dalszy kod dostanie None i nic nie namaluje
                supp_avg = None

            # >>> KARTY I OPISY: przygotuj dane archetypów na podstawie ŚREDNICH <<<
            main_data = archetype_extended.get(main_avg, {})
            second_data = archetype_extended.get(aux_avg,
                                                 {}) if aux_avg and aux_avg != main_avg else {}
            supp_data = archetype_extended.get(supp_avg, {}) if supp_avg and supp_avg not in [
                main_avg, aux_avg] else {}

            def _with_core_triplet(payload: dict, arche_name: str | None) -> dict:
                out = dict(payload or {})
                if arche_name and not out.get("core_triplet"):
                    out["core_triplet"] = CORE_TRIPLET_MAP.get(arche_name, "")
                return out

            # wersje z żeńskimi nazwami, jeśli trzeba
            main_disp = _with_core_triplet(main_data, main_avg)
            main_disp["name"] = disp_name(main_avg or "")
            second_disp = _with_core_triplet(second_data, aux_avg)
            if second_data:
                second_disp["name"] = disp_name(aux_avg or "")
            supp_disp = _with_core_triplet(supp_data, supp_avg)
            if supp_data:
                supp_disp["name"] = disp_name(supp_avg or "")

            col1, col2, col3 = st.columns([0.28, 0.36, 0.36], gap="small")
            means_pct = mean_pct_by_archetype_from_df(data)

            # --- LICZEBNOŚCI TYLKO DO TABELI (NIE DO RANKINGU/WYKRESU) ---
            counts_main = (
                results_df['Główny archetyp'].map(normalize)
                .value_counts().reindex(archetype_names, fill_value=0)
            )

            counts_aux = (
                results_df['Archetyp wspierający'].map(normalize)
                .value_counts().reindex(archetype_names, fill_value=0)
            )

            counts_supp = (
                results_df['Archetyp poboczny']
                .map(normalize)
                .value_counts()
                .reindex(archetype_names, fill_value=0)
            )

            # wykres skumulowany (PNG) dla Worda/PDF
            stacked_png_path = make_stacked_bar_png_for_word(
                archetype_names=ARCHE_NAMES_ORDER,  # lub Twoja lista 'archetype_names'
                counts_main=counts_main,
                counts_aux=counts_aux,
                counts_supp=counts_supp,
                out_path="archetypes_stacked.png",
            )

            with col1:
                st.markdown(
                    ap_section_heading("Podsumowanie archetypów (liczebność i natężenie)", center=False, margin_bottom_px=8),
                    unsafe_allow_html=True
                )

                # 2) kolejność wierszy – sortujemy malejąco po procencie
                ordered_names = sorted(
                    archetype_names,
                    key=lambda n: means_pct.get(n, 0.0),
                    reverse=True
                )

                # 3) budowa tabeli z nową kolumną „% natężenie archetypu”
                # 1) nagłówek grupy + link „i” (bez JS – otwiera modal CSS)
                NAT_GRP = (
                    "<a href='#ap-intensity-modal' class='ap-int-info' title='Co oznaczają progi?'>"
                    "<img src='https://cdn3.iconfinder.com/data/icons/thunderstorm-5/80/5-32-512.png' "
                    "alt='info' style='width:16px;height:16px'/>"
                    "</a>"
                )

                # 2) wartości % i opisy słowne (z ikonką – kolorowe KWADRATY, nie kółka)
                _pct_vals = [float(means_pct.get(n, 0.0)) for n in ordered_names]
                _pct_strs = [f"{v:.1f}%" for v in _pct_vals]
                _labels = [interpret_archetype_intensity(v)["short"] for v in _pct_vals]
                _labels_ico = [intensity_icon_html(s) for s in _labels]

                # 3) MultiIndex → powstaje nagłówek dwupoziomowy z 2 „podkolumnami”
                _cols = pd.MultiIndex.from_tuples([
                    ("", "Archetyp"),
                    ("", "Główny<br/>archetyp"),
                    ("", "Wspierający<br/>archetyp"),
                    ("", "Poboczny<br/>archetyp"),
                    (NAT_GRP, "%"),
                    (NAT_GRP, "opis"),
                ])

                archetype_table = pd.DataFrame({
                    ("", "Archetyp"): [f"{get_emoji(n)} {disp_name(n)}" for n in ordered_names],
                    ("", "Główny<br/>archetyp"): [zero_to_dash(counts_main.get(normalize(n), 0)) for
                                                  n in ordered_names],
                    ("", "Wspierający<br/>archetyp"): [zero_to_dash(counts_aux.get(normalize(n), 0))
                                                       for n in ordered_names],
                    ("", "Poboczny<br/>archetyp"): [zero_to_dash(counts_supp.get(normalize(n), 0))
                                                    for n in ordered_names],
                    (NAT_GRP, "%"): _pct_strs,
                    (NAT_GRP, "opis"): _labels_ico,
                }, columns=_cols)

                # 4) sortowanie po wartości %
                archetype_table["_sort"] = _pct_vals
                archetype_table = (
                    archetype_table.sort_values("_sort", ascending=False)
                    .drop(columns=["_sort"])
                    .reset_index(drop=True)
                )

                # 5) HTML + CSS tabeli
                # --- ŁATWE DO ZMIANY SZEROKOŚCI (procenty) ---
                COL_W = {"c1": "21%",
                         "c2": "12%",
                         "c3": "16%",
                         "c4": "12%",
                         "c5": "5%",
                         "c6": "36%"}

                # Budujemy body tabeli bez nagłówka (header=False), a nagłówek zrobimy ręcznie (rowspan/colspan).
                _body = (
                    archetype_table.to_html(index=False, header=False, escape=False, border=0)
                    .replace('class="dataframe"', 'class="ap-table"')
                    .replace('border="1"', 'border="0"')
                )

                # Ręcznie złożony nagłówek (scalenia jak na screenie: 4 kolumny z rowspan=2 i grupa 2-kolumnowa)
                thead_html = f"""
                <thead>
                  <tr>
                    <th rowspan="2" style="width:{COL_W['c1']}">Archetyp</th>
                    <th rowspan="2" style="width:{COL_W['c2']}">Główny archetyp</th>
                    <th rowspan="2" style="width:{COL_W['c3']}">Wspierający archetyp</th>
                    <th rowspan="2" style="width:{COL_W['c4']}">Poboczny archetyp</th>
                    <th colspan="2" style="width:calc({COL_W['c5']} + {COL_W['c6']})">
                      % natężenie archetypu&nbsp;{NAT_GRP}
                    </th>
                  </tr>
                  <tr>
                    <th style="width:{COL_W['c5']}">%</th>
                    <th style="width:{COL_W['c6']}">opis</th>
                  </tr>
                </thead>
                """

                # Wstrzykujemy thead przed <tbody>
                html_table = _body.replace("<tbody>", thead_html + "<tbody>", 1)

                st.markdown(f"""
                <style>
                  .ap-table {{
                    table-layout: fixed; width: 100%; border-collapse: collapse;
                    font-family: 'Segoe UI', system-ui, -apple-system, Arial, sans-serif;
                    font-size: 14px; margin-top: 3px;
                  }}
                  .ap-table th, .ap-table td {{
                    padding: 13px 10px; border-bottom: 1px solid #eaeaea;
                    vertical-align: middle; line-height: 1.22; text-align: center;
                  }}
                  .ap-table thead th {{ font-weight: 700; }}

                  /* Wyrównania tylko dla WIERZY (tbody) w kolumnach 1 i 6 */
                  .ap-table tbody td:nth-child(1),
                  .ap-table tbody td:nth-child(6) {{ text-align: left !important; }}

                  /* Delikatna, szara ikonka „info” */
                  .ap-int-info img {{
                    opacity:.65; filter:grayscale(100%); vertical-align:-3px;
                    width:16px; height:16px;
                  }}
                  .ap-int-info:hover img {{ opacity:1; filter:none; }}

                  /* Kwadracik przy opisie natężenia */
                  .ap-int-ico {{
                    display:inline-block; width:12px; height:12px; border-radius:3px;
                    border:1px solid #d1d5db; margin-right:6px; vertical-align:-2px;
                  }}
                </style>
                """, unsafe_allow_html=True)

                # 👉 Auto-wysokość i brak iframa (Streamlit ≥ 1.38 ma st.html)
                _table_rows = len(ordered_names) if isinstance(ordered_names, list) else 12
                # trochę większy zapas na nagłówek i odstępy
                _table_height = 240 + 56 * _table_rows

                # --- NOWY FRAGMENT DO WSTAWIENIA ---
                _html_block = f"""
                <style>
                  .ap-table {{
                    table-layout: fixed; width: 100%; border-collapse: collapse;
                    font-family: 'Segoe UI', system-ui, -apple-system, Arial, sans-serif;
                    font-size: 14px; margin-top: 3px;
                  }}
                  .ap-table th, .ap-table td {{
                    padding: 13px 10px; border-bottom: 1px solid #eaeaea;
                    vertical-align: middle; line-height: 1.22; text-align: center;
                  }}
                  .ap-table thead th {{ font-weight: 700; }}
                  .ap-table tbody td:nth-child(1),
                  .ap-table tbody td:nth-child(6) {{ text-align: left !important; }}

                  .ap-int-info img {{
                    opacity:.65; filter:grayscale(100%); vertical-align:-3px; width:16px; height:16px;
                  }}
                  .ap-int-info:hover img {{ opacity:1; filter:none; }}

                  .ap-int-ico {{
                    display:inline-block; width:12px; height:12px; border-radius:3px;
                    border:1px solid #d1d5db; margin-right:6px; vertical-align:-2px;
                  }}

                  /* 👉 KONFIGURACJA — tu zmieniasz marginesy/paddingi */
                  :root{{
                    --ap-tip-offset: 10px;   /* odległość dymka od ikonki */
                    --ap-tip-pad-v: 10px;    /* padding GÓRA/DÓŁ w dymku */
                    --ap-tip-pad-h: 12px;    /* padding LEWO/PRAWO w dymku */
                  }}

                  /* kontener tooltipa */
                  .ap-tip{{ position:relative; display:inline-block; }}

                  /* sam dymek */
                  .ap-tip-box{{
                    position:absolute;
                    left:50%; transform:translateX(-50%) translateY(4px);
                    top: calc(100% + var(--ap-tip-offset));
                    background:#111827; color:#fff;
                    padding: var(--ap-tip-pad-v) var(--ap-tip-pad-h);
                    border-radius:8px; box-shadow:0 6px 18px rgba(0,0,0,.18);
                    white-space:nowrap; font-size:12px; line-height:1.35;
                    z-index:15; opacity:0; pointer-events:none;
                    transition:opacity .15s ease, transform .15s ease;
                  }}

                  /* strzałka */
                  .ap-tip-box::after{{
                    content:""; position:absolute; top:-6px; left:50%; transform:translateX(-50%);
                    border:6px solid transparent; border-bottom-color:#111827;
                  }}

                  /* pokaż przy najechaniu */
                  .ap-tip:hover .ap-tip-box{{ opacity:1; transform:translateX(-50%) translateY(0); }}

                  /* opcja: dymek NAD ikoną */
                  .ap-tip.ap-tip--above .ap-tip-box{{
                    bottom: calc(100% + var(--ap-tip-offset)); top:auto;
                  }}
                  .ap-tip.ap-tip--above .ap-tip-box::after{{
                    top:auto; bottom:-6px; border-bottom-color:transparent; border-top-color:#111827;
                  }}

                  /* jeśli w tooltipie masz mini-tabelkę */
                    /* 👉 USTAWIENIA — tu ręcznie regulujesz odstępy w wierszach */
                    :root{{
                      --ap-row-pad-top: 18px;       /* górny akapit (padding TOP) w wierszu */
                      --ap-row-pad-bottom: 18px;    /* dolny akapit (padding BOTTOM) w wierszu */
                      --ap-cell-pad-h: 12px;        /* poziomy padding w komórkach tabeli */
                    
                      /* paleta kolorów dla kwadracików (natężenia) — możesz zmieniać */
                      --ap-col-1: #e5e7eb; /* 0–29%  */
                      --ap-col-2: #bfdbfe; /* 30–49% */
                      --ap-col-3: #fde68a; /* 50–59% */
                      --ap-col-4: #fdba74; /* 60–69% */
                      --ap-col-5: #f87171; /* 70–79% */
                      --ap-col-6: #c084fc; /* 80–89% */
                      --ap-col-7: #111827; /* 90–100% */
                    }}
                    
                    /* tabela w modalu z interpretacją */
                    .ap-tip-box .ap-int-table{{
                      border-collapse: collapse; margin-block: 6px; width: 100%;
                    }}
                    .ap-tip-box .ap-int-table th,
                    .ap-tip-box .ap-int-table td{{
                      padding: var(--ap-row-pad-top) var(--ap-cell-pad-h) var(--ap-row-pad-bottom) var(--ap-cell-pad-h);
                      border-bottom: 1px solid #e5e7eb;
                      vertical-align: top; text-align: left;
                    }}
                    .ap-tip-box .ap-int-table thead th{{ font-weight: 700; }}
                    
                    /* szerokości kolumn – opcjonalnie dopasuj pod siebie */
                    .ap-tip-box .ap-int-table th:nth-child(1),
                    .ap-tip-box .ap-int-table td:nth-child(1){{ width: 100px; text-align: center; }}
                    .ap-tip-box .ap-int-table th:nth-child(2),
                    .ap-tip-box .ap-int-table td:nth-child(2){{ width: 450px; }}
                    
                    /* kwadraciki natężenia */
                    .ap-tip-box .ap-int-ico{{
                      display:inline-block; width:12px; height:12px; border-radius:3px;
                      border:1px solid #d1d5db; margin-right:8px; vertical-align:-2px;
                    }}
                    .ap-tip-box .ap-i--1{{ background:var(--ap-col-1); }}
                    .ap-tip-box .ap-i--2{{ background:var(--ap-col-2); }}
                    .ap-tip-box .ap-i--3{{ background:var(--ap-col-3); }}
                    .ap-tip-box .ap-i--4{{ background:var(--ap-col-4); }}
                    .ap-tip-box .ap-i--5{{ background:var(--ap-col-5); }}
                    .ap-tip-box .ap-i--6{{ background:var(--ap-col-6); }}
                    .ap-tip-box .ap-i--7{{ background:var(--ap-col-7); border-color:var(--ap-col-7); }}
                    
                    .ap-tip-box .ap-int-label{{ font-weight: 600; }}

                    /* Tooltip nad kolorowym paskiem heurystyki */
                    .ap-hc-fill[data-tip]{{ position: relative; }}
                    .ap-hc-fill[data-tip]:hover::after{{
                      content: attr(data-tip);
                      position: absolute;
                      left: 14px;                 /* startuje lekko od lewej krawędzi paska */
                      bottom: calc(100% + 8px);   /* nad paskiem */
                      max-width: 520px;
                      background:#111827; color:#fff;
                      padding:8px 10px; border-radius:8px;
                      font:500 13px/1.35 'Segoe UI', system-ui, Arial;
                      box-shadow:0 8px 24px rgba(0,0,0,.2);
                      white-space:normal; z-index:10;
                    }}
                    .ap-hc-fill[data-tip]:hover::before{{
                      content:"";
                      position:absolute; left: 20px; bottom: 100%;
                      border:6px solid transparent;
                      border-top-color:#111827;   /* „trójkącik” */
                      transform: translateY(2px);
                    }}

                </style>
                """ + html_table + intensity_help_modal_html()

                # jeśli masz nowe Streamlit: prawdziwy, „wbudowany” HTML bez iframa
                if hasattr(st, "html"):
                    st.html(_html_block)  # auto-dopasowanie wysokości, brak dodatkowego scrolla
                else:
                    # starszy Streamlit – zostaje components, ale bez przewijania (duża wysokość)
                    components.html(_html_block, height=_table_height, scrolling=False)

            with col2:
                theta_labels = []
                for n in archetype_names:
                    label = disp_name(n)
                    if n == main_avg:
                        theta_labels.append(f"<b><span style='color:red;'>{label}</span></b>")
                    elif n == aux_avg:
                        theta_labels.append(f"<b><span style='color:#FFD22F;'>{label}</span></b>")
                    elif n == supp_avg:
                        theta_labels.append(f"<b><span style='color:#40b900;'>{label}</span></b>")
                    else:
                        theta_labels.append(f"<span style='color:#656565;'>{label}</span>")

                # markery TOP-3 z mean_archetype_scores
                highlight_r = []
                highlight_marker_color = []
                for name in archetype_names:
                    if name == main_avg:
                        highlight_r.append(mean_archetype_scores.get(name, 0.0))
                        highlight_marker_color.append("red")
                    elif name == aux_avg:
                        highlight_r.append(mean_archetype_scores.get(name, 0.0))
                        highlight_marker_color.append("#FFD22F")
                    elif name == supp_avg:
                        highlight_r.append(mean_archetype_scores.get(name, 0.0))
                        highlight_marker_color.append("#40b900")
                    else:
                        highlight_r.append(None)
                        highlight_marker_color.append("rgba(0,0,0,0)")

                # ŚREDNIE (0–20) w KOLEJNOŚCI archetype_names
                mean_vals_ordered = [mean_archetype_scores.get(n, 0.0) for n in archetype_names]

                fig = go.Figure(
                    data=[
                        go.Scatterpolar(
                            r=mean_vals_ordered + [mean_vals_ordered[0]],
                            theta=archetype_names + [archetype_names[0]],
                            fill='toself',
                            name='średnia wszystkich',
                            line=dict(color="royalblue", width=3),
                            marker=dict(size=6),
                            # 👇 własny tooltip: bez "r:" i "θ:", zaokrąglenie do 2 miejsc
                            hovertemplate="<b>%{theta}</b><br>średnia: %{r:.2f}<extra></extra>",
                        ),
                        go.Scatterpolar(
                            r=highlight_r,
                            theta=archetype_names,
                            mode='markers',
                            marker=dict(size=18, color=highlight_marker_color, opacity=0.90,
                                        line=dict(color="black", width=3)),
                            name='Archetyp główny/wspierający/poboczny',
                            showlegend=False,
                            # 👇 spójny tooltip z 2 miejscami po przecinku
                            hovertemplate="<b>%{theta}</b><br>wartość: %{r:.2f}<extra></extra>",
                        )
                    ],
                    layout=go.Layout(
                        polar=dict(
                            radialaxis=dict(visible=True, range=[0, 20]),
                            angularaxis=dict(
                                tickfont=dict(size=19),
                                tickvals=archetype_names,
                                ticktext=theta_labels,
                                rotation=90,
                                direction="clockwise",
                            )
                        ),
                        width=400, height=400,
                        margin=dict(l=20, r=20, t=32, b=32),
                        showlegend=False
                    )
                )

                # PRZEZROCZYSTE TŁO RADARU — bez zmian
                fig.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    polar=dict(
                        domain=dict(x=[0, 1], y=[0, 1]),  # pełna szerokość/wysokość domeny
                        bgcolor="rgba(0,0,0,0)",
                        radialaxis=dict(visible=True, range=[0, 20]),
                        angularaxis=dict(
                            tickfont=dict(size=17),
                            tickvals=archetype_names,
                            ticktext=theta_labels,
                            rotation=90,
                            direction="clockwise",
                        ),
                    ),
                    autosize=False,
                    width=550, height=550,
                    margin=dict(l=0, r=0, t=32, b=32),  # brak bocznych marginesów
                    showlegend=False,
                )

                # 👇 większa czcionka w dymkach hover
                fig.update_layout(hoverlabel=dict(font=dict(size=17)))

                # węższe boczne „bufory” + środkowa kolumna z wykresem → centrowanie
                padL, mid, padR = st.columns([0.05, 0.90, 0.05], gap="small")
                with mid:
                    st.markdown(
                        ap_section_heading(f"Profil archetypów {personGen}", center=True, margin_bottom_px=8),
                        unsafe_allow_html=True,
                    )
                    st.plotly_chart(
                        fig,
                        use_container_width=True, #width="content",
                        config={"displaylogo": False},
                        key=f"radar-{study_id}",
                    )
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

            st.markdown("<div style='height:50px;'></div>", unsafe_allow_html=True)
            left_col, right_col = st.columns([0.55, 0.45], gap="large")

            with left_col:
                # tylko słupki
                st.markdown(ap_section_heading("Heurystyczna analiza koloru psychologicznego", center=False, margin_bottom_px=8),
                            unsafe_allow_html=True)
                components.html(color_progress_bars_html(color_pcts, order="desc"),
                                height=280, scrolling=False)  # niższy iframe

                st.markdown("<style>.cp-row{margin:15px 0 !important}</style>",
                            unsafe_allow_html=True)  # mniejsze odstępy między wierszami

                # opisy ZOSTAJĄ — dominujący kolor + opis
                dom_name, dom_pct = max(color_pcts.items(), key=lambda kv: kv[1])
                st.markdown(
                    f"<div style='text-align:center; font:680 20px/1.30 \"Roboto\",\"Segoe UI\",\"Arial\",system-ui,sans-serif; color:#222; margin: -15px 0 60px;'>"
                    f"Dominujący kolor: <span style='color:{COLOR_HEX[dom_name]}'>{dom_name}</span></div>",
                    unsafe_allow_html=True
                )
                st.markdown(color_explainer_one_html(dom_name, dom_pct), unsafe_allow_html=True)

            # prawa kolumna — wykres archetypów
            with right_col:
                p_l, p_c, p_r = st.columns([0.06, 0.88, 0.06], gap="small")
                with p_c:
                    st.markdown(
                        ap_section_heading("Koło archetypów (pragnienia i wartości)", center=True, margin_bottom_px=8),
                        unsafe_allow_html=True,
                    )
                    if main_avg is not None:
                        idx_main_wheel = archetype_name_to_img_idx(main_avg)
                        idx_aux_wheel = archetype_name_to_img_idx(aux_avg) if aux_avg != main_avg else None
                        idx_supp_wheel = (
                            archetype_name_to_img_idx(supp_avg) if supp_avg not in [main_avg, aux_avg] else None
                        )
                        try:
                            kola_img = compose_archetype_highlight(idx_main_wheel, idx_aux_wheel, idx_supp_wheel)
                            if not isinstance(kola_img, Image.Image):
                                raise TypeError("compose_archetype_highlight nie zwrócił obrazu PIL")
                        except Exception:
                            kola_img = load_base_arche_img()
                        st.image(
                            kola_img,
                            caption="Podświetlenie: główny – czerwony, wspierający – żółty, poboczny – zielony",
                            width=640
                        )

            # tylko dominujący kolor
            dom_name, dom_pct = max(color_pcts.items(), key=lambda kv: kv[1])

            color_pcts = calc_color_percentages_from_df(data)


            # Dane opisowe dominującego koloru do Worda
            dom_meta = COLOR_LONG[dom_name]  # masz już COLOR_LONG w pliku
            dom_color = {
                "name": dom_name,
                "pct": dom_pct,
                "emoji": COLOR_EMOJI[dom_name],
                "title": dom_meta["title"],
                "orient": dom_meta["orient"],
                "body": dom_meta["body"],
                "politics": dom_meta["politics"],
                "hex": dom_meta["hex"],
            }


            with col3:
                k_pad_l, k_mid, k_pad_r = st.columns([0.06, 0.88, 0.06], gap="small")
                with k_mid:
                    st.markdown(
                        ap_section_heading("Rozkład archetypów na osiach potrzeb", center=True, margin_bottom_px=8),
                        unsafe_allow_html=True,
                    )
                    aux = aux_avg if aux_avg != main_avg else None
                    supp = supp_avg if supp_avg not in [main_avg, aux_avg] else None
                    kolo_axes_img = compose_axes_wheel_highlight(main_avg, aux, supp)
                    st.image(kolo_axes_img, width=650)

            segment_profile_png_path = make_segment_profile_wheel_png(
                mean_scores=means_pct,
                out_path=f"segment_profile_{study_id}.png",
            )
            st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)
            st.markdown(
                ap_section_heading(
                    f"Profil archetypowy {personGen} (siła archetypu, skala: 0-100)",
                    center=False,
                    margin_bottom_px=12,
                    margin_top_px=6,
                ),
                unsafe_allow_html=True,
            )
            st.image(segment_profile_png_path, width=713)
            st.markdown(
                """
                <div style="display:flex;gap:24px;flex-wrap:wrap;align-items:center;justify-content:flex-start;margin-top:8px;margin-bottom:6px;font-size:1.03em;font-weight:600;color:#475569;">
                  <span style="display:inline-flex;align-items:center;gap:7px;"><span style="width:11px;height:11px;background:#de4b43;border-radius:2px;display:inline-block;"></span>Zmiana</span>
                  <span style="display:inline-flex;align-items:center;gap:7px;"><span style="width:11px;height:11px;background:#2d5ad5;border-radius:2px;display:inline-block;"></span>Ludzie</span>
                  <span style="display:inline-flex;align-items:center;gap:7px;"><span style="width:11px;height:11px;background:#2f8a45;border-radius:2px;display:inline-block;"></span>Porządek</span>
                  <span style="display:inline-flex;align-items:center;gap:7px;"><span style="width:11px;height:11px;background:#6f53d4;border-radius:2px;display:inline-block;"></span>Niezależność</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown("""
            <hr style="height:1px; border:none; background:#eee; margin-top:34px; margin-bottom:19px;" />
            """, unsafe_allow_html=True)
            st.markdown("<div id='opisy'></div>", unsafe_allow_html=True)
            st.markdown(f'<div style="font-size:2.1em;font-weight:700;margin-bottom:16px;">Archetyp główny {personGen}</div>', unsafe_allow_html=True)
            render_archetype_card(main_disp, main=True, gender_code=("K" if IS_FEMALE else "M"))

            if aux_avg and aux_avg != main_avg:
                st.markdown("<div style='height:35px;'></div>", unsafe_allow_html=True)
                st.markdown("""<hr style="height:1.1px; border:none; background:#ddd; margin-top:6px; margin-bottom:18px;" />""", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size:1.63em;font-weight:700;margin-bottom:15px;'>Archetyp wspierający {personGen}</div>", unsafe_allow_html=True)
                render_archetype_card(second_disp, main=False, gender_code=("K" if IS_FEMALE else "M"))

            if supp_avg and supp_avg not in [main_avg, aux_avg]:
                st.markdown("<div style='height:35px;'></div>", unsafe_allow_html=True)
                st.markdown("""<hr style="height:1.1px; border:none; background:#ddd; margin-top:6px; margin-bottom:18px;" />""", unsafe_allow_html=True)
                st.markdown(f"<div style='font-size:1.63em;font-weight:700;margin-bottom:15px;'>Archetyp poboczny {personGen}</div>", unsafe_allow_html=True)
                render_archetype_card(supp_disp, main=False, supplement=True, gender_code=("K" if IS_FEMALE else "M"))

            if public_view:
                return

            st.markdown("<div id='raport'></div>", unsafe_allow_html=True)

            st.markdown(f"""
            <div style='height:44px;'></div>
            <hr style="height:1px; border:none; background:#e5e5e5; margin-bottom:26px;" />
            <div style="font-size:1.2em; font-weight:600; margin-bottom:23px;">
                Pobierz raporty archetypu {personGen}
            </div>
            """, unsafe_allow_html=True)

            # GENEROWANIE OBRAZU PANELU DYNAMICZNIE
            idx_main = archetype_name_to_img_idx(main_avg)
            idx_aux = archetype_name_to_img_idx(aux_avg) if aux_avg != main_avg else None
            idx_supplement = archetype_name_to_img_idx(supp_avg) if supp_avg not in [main_avg, aux_avg] else None

            # === Przygotowanie eksportów tylko na żądanie ===
            prep = st.toggle(
                "Przygotuj pliki Word/PDF (kliknij tylko gdy chcesz pobrać)",
                key="prep_docs",
                value=st.session_state.get("prep_docs", False)
            )

            # Ustal nazwy plików z góry (przydadzą się też przy cache)
            DOCX_FILENAME_FULL, PDF_FILENAME_FULL = build_report_filenames(study)
            DOCX_FILENAME_SHORT, PDF_FILENAME_SHORT = build_short_report_filenames(study)
            cache_key = f"exports_{study_id}"

            def _build_exports() -> dict[str, bytes]:
                """Liczy wszystkie obrazy do Worda, buduje raport full + short (DOCX/PDF)."""
                # 1) Zapisz PNG z radaru (do DOCX)
                try:
                    fig.write_image("radar.png", scale=4)
                except Exception:
                    pass

                # 2) Koło osi potrzeb → PNG
                aux = aux_avg if aux_avg != main_avg else None
                supp = supp_avg if supp_avg not in [main_avg, aux_avg] else None
                kolo_axes_img = compose_axes_wheel_highlight(main_avg, aux, supp)
                kolo_axes_img.save("axes_wheel.png")

                # 3) Dominujący pierścień koloru → SVG/PNG
                big_color = max(color_pcts.items(), key=lambda kv: kv[1])[0]
                big_svg = _ring_svg(color_pcts[big_color], COLOR_HEX[big_color], size=600,
                                    stroke=48)
                with open("color_ring.svg", "w", encoding="utf-8") as f:
                    f.write(big_svg)
                cairosvg.svg2png(url="color_ring.svg", write_to="color_ring.png")

                # 4) Pastylki kolorów (PNG)
                progress_png_path = make_color_progress_png_for_word(
                    color_pcts, width_px=1600, pad=32, bar_h=66, bar_gap=30,
                    dot_radius=10, label_gap_px=35, label_font_size=36, pct_font_size=32,
                    pct_margin=14
                )

                # 5) Skumulowany wykres liczebności (PNG)
                stacked_png_path = make_stacked_bar_png_for_word(
                    archetype_names=ARCHE_NAMES_ORDER,
                    counts_main=counts_main, counts_aux=counts_aux, counts_supp=counts_supp,
                    out_path="archetypes_stacked.png",
                )

                # 6) Kapsuły średnich (PNG)
                means_pct = mean_pct_by_archetype_from_df(data)
                capsules_path = make_capsule_columns_png_for_word(
                    means_pct, out_path="arche_capsules.png", top_title=None
                )

                # 7) Panel (czerwony/żółty/zielony) → PNG
                idx_main = archetype_name_to_img_idx(main_avg)
                idx_aux = archetype_name_to_img_idx(aux_avg) if aux_avg != main_avg else None
                idx_supp = archetype_name_to_img_idx(supp_avg) if supp_avg not in [main_avg,
                                                                                   aux_avg] else None
                panel_img = compose_archetype_highlight(idx_main, idx_aux, idx_supp)
                panel_img_path = f"panel_{(main_avg or '').lower()}_{(aux_avg or '').lower()}_{(supp_avg or '').lower()}.png"
                panel_img.save(panel_img_path)

                # 8) FULL DOCX
                docx_full_io = export_word_docxtpl(
                    main_avg,
                    aux_avg,
                    supp_avg,
                    archetype_features,
                    main_disp,
                    second_disp,
                    supp_disp,
                    mean_scores=means_pct,  # ⬅️ przekażemy % do wyliczenia natężenia
                    radar_img_path="radar.png",
                    archetype_table=archetype_table,
                    num_ankiet=num_ankiet,
                    panel_img_path=panel_img_path,
                    person=person,
                    gender_code=("K" if IS_FEMALE else "M"),
                    axes_wheel_img_path="axes_wheel.png",
                    dom_color=dom_color,
                    color_progress_img_path=progress_png_path,
                    archetype_stacked_img_path=stacked_png_path,
                    capsule_columns_img_path=capsules_path,
                    segment_profile_img_path=segment_profile_png_path,
                    show_supplement=SHOW_SUPP
                )

                # 9) SHORT DOCX (tylko metryka)
                docx_short_io = export_word_metrics_only(
                    main_avg,
                    aux_avg,
                    supp_avg,
                    main_disp,
                    second_disp,
                    supp_disp,
                    person=person,
                    show_supplement=SHOW_SUPP,
                    segment_profile_img_path=segment_profile_png_path,
                )

                # 10) PDF – platformowo:
                import sys as _sys
                if _sys.platform.startswith("win"):
                    pdf_full_io = word_to_pdf(docx_full_io)
                    pdf_short_io = word_to_pdf(docx_short_io)
                else:
                    soffice_path = _find_soffice()
                    if not soffice_path:
                        raise RuntimeError("LibreOffice (soffice) nie jest dostępny w systemie.")
                    pdf_full_io = word_to_pdf(docx_full_io, soffice_bin=soffice_path)
                    pdf_short_io = word_to_pdf(docx_short_io, soffice_bin=soffice_path)

                return {
                    "docx_full": docx_full_io.getvalue(),
                    "pdf_full": pdf_full_io.getvalue(),
                    "docx_short": docx_short_io.getvalue(),
                    "pdf_short": pdf_short_io.getvalue(),
                }

            # — logika UI — generuj tylko na żądanie, ale pozwól pobrać poprzednie
            if prep:
                with st.spinner("Przygotowuję raport Word/PDF…"):
                    try:
                        exports = _build_exports()
                        st.session_state[cache_key] = {
                            **exports,
                            "docx_name_full": DOCX_FILENAME_FULL,
                            "pdf_name_full": PDF_FILENAME_FULL,
                            "docx_name_short": DOCX_FILENAME_SHORT,
                            "pdf_name_short": PDF_FILENAME_SHORT,
                        }
                        st.success("Gotowe. Możesz pobrać pliki poniżej.")
                    except Exception as e:
                        st.error(f"Nie udało się przygotować raportu: {e}")

            cache = st.session_state.get(cache_key)

            word_icon = "<svg width='21' height='21' viewBox='0 0 32 32' style='vertical-align:middle;margin-right:7px;margin-bottom:2px;'><rect width='32' height='32' rx='4' fill='#185abd'/><text x='16' y='22' text-anchor='middle' font-family='Segoe UI,Arial' font-size='16' fill='#fff' font-weight='bold'>W</text></svg>"
            pdf_icon = "<svg width='21' height='21' viewBox='0 0 32 32' style='vertical-align:middle;margin-right:7px;margin-bottom:2px;'><rect width='32' height='32' rx='4' fill='#d32f2f'/><text x='16' y='22' text-anchor='middle' font-family='Segoe UI,Arial' font-size='16' fill='#fff' font-weight='bold'>PDF</text></svg>"

            st.markdown(
                f"<div style='margin-bottom:11px;'>{word_icon}<b>Raport pełny (.docx)</b></div>",
                unsafe_allow_html=True)
            st.download_button(
                "Pobierz raport pełny (Word)",
                data=(cache["docx_full"] if cache else b""),
                file_name=(cache["docx_name_full"] if cache else DOCX_FILENAME_FULL),
                disabled=not bool(cache),
                key="word_button_full"
            )

            st.markdown(
                f"<div style='margin-top:21px; margin-bottom:11px;'>{pdf_icon}<b>Raport pełny (.pdf)</b></div>",
                unsafe_allow_html=True)
            st.download_button(
                "Pobierz raport pełny (PDF)",
                data=(cache["pdf_full"] if cache else b""),
                file_name=(cache["pdf_name_full"] if cache else PDF_FILENAME_FULL),
                disabled=not bool(cache),
                key="pdf_button_full"
            )

            st.markdown(
                f"<div style='margin-top:21px; margin-bottom:11px;'>{word_icon}<b>Raport skrócony (.docx)</b></div>",
                unsafe_allow_html=True)
            st.download_button(
                "Pobierz raport skrócony (Word)",
                data=(cache["docx_short"] if cache else b""),
                file_name=(cache["docx_name_short"] if cache else DOCX_FILENAME_SHORT),
                disabled=not bool(cache),
                key="word_button_short"
            )

            st.markdown(
                f"<div style='margin-top:21px; margin-bottom:11px;'>{pdf_icon}<b>Raport skrócony (.pdf)</b></div>",
                unsafe_allow_html=True)
            st.download_button(
                "Pobierz raport skrócony (PDF)",
                data=(cache["pdf_short"] if cache else b""),
                file_name=(cache["pdf_name_short"] if cache else PDF_FILENAME_SHORT),
                disabled=not bool(cache),
                key="pdf_button_short"
            )

            if not cache and not prep:
                st.caption(
                    "Pliki nie są jeszcze przygotowane. Włącz przełącznik powyżej, żeby je wygenerować.")

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
        st.info("Brak danych – nie ma żadnych odpowiedzi w tym badaniu.")

