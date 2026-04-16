# ===== archetypes_10.py =====
# ===== wersja: 10; 05.03.2026, godzina 14:20 =====
# -*- coding: utf-8 -*-

"""
Archetypy: analiza CAWI

"""

from __future__ import annotations
import os
import json
import math
import re
import textwrap
import webbrowser
import html as _html
import unicodedata
from datetime import datetime
from zoneinfo import ZoneInfo

# Alias zgodnościowy: część helperów używa html.escape(...),
# a część _html / _html_escape.
html = _html
from dataclasses import dataclass, field
from pathlib import Path

from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
# --- Spójna typografia wykresów (stałe dla całego projektu) ---

import matplotlib

PLOT_FS_TITLE = 18
PLOT_FS_SECTION = 13
PLOT_FS_LABEL = 11
PLOT_FS_TICK = 10
PLOT_FS_VALUE = 10
PLOT_FS_SMALL = 9

PLOT_FS_TINY = 8

PLOT_DPI = 160
from matplotlib.patches import Wedge
from matplotlib.lines import Line2D

from matplotlib import font_manager as fm


def _font_available(name: str) -> bool:
    try:
        path = fm.findfont(fm.FontProperties(family=name), fallback_to_default=False)
        return Path(path).exists()
    except Exception:
        return False


def _candidate_font_files() -> List[Path]:
    here = Path(__file__).resolve().parent
    rel_candidates = [
        Path("assets/fonts/segoeui.ttf"),
        Path("assets/fonts/segoeuib.ttf"),
        Path("assets/fonts/ArialNova.ttf"),
        Path("assets/fonts/ArialNova-Bold.ttf"),
        Path("assets/fonts/DejaVuSans.ttf"),
        Path("assets/DejaVuSans.ttf"),
    ]
    out: List[Path] = []
    seen: set[str] = set()
    for base in [here, *list(here.parents)]:
        for rel in rel_candidates:
            p = (base / rel).resolve()
            key = str(p).lower()
            if key in seen or (not p.exists()) or (not p.is_file()):
                continue
            seen.add(key)
            out.append(p)
    return out


def _register_font(path: Path) -> str:
    try:
        fm.fontManager.addfont(str(path))
        return str(fm.FontProperties(fname=str(path)).get_name() or "").strip()
    except Exception:
        return ""


def _pick_base_font() -> str:
    # Priorytet 1: fonty dostarczone razem z repo (spójny wygląd między środowiskami).
    # Priorytet 2: fonty systemowe.
    loaded_names: List[str] = []
    for font_path in _candidate_font_files():
        nm = _register_font(font_path)
        if nm and nm not in loaded_names:
            loaded_names.append(nm)
    for nm in loaded_names + ["Segoe UI", "Calibri", "Arial", "DejaVu Sans"]:
        if _font_available(nm):
            return nm
    return "DejaVu Sans"


def set_global_fonts() -> None:
    # Wybierz deterministycznie font bazowy (repo -> system), żeby raporty były
    # wizualnie spójne także po wygenerowaniu na innym serwerze.
    base_font = _pick_base_font()
    print(f"[fonts] matplotlib base font: {base_font}")

    matplotlib.rcParams.update({
        "font.family": [base_font],
        "font.sans-serif": [base_font, "Segoe UI", "Calibri", "Arial", "DejaVu Sans"],

        # spójna typografia (jedna „rodzina” dla wszystkich PNG)
        "font.size": 10,
        "axes.titlesize": 14,
        "axes.labelsize": 11,
        "xtick.labelsize": 10,
        "ytick.labelsize": 10,
        "legend.fontsize": 10,

        # lekki, spójny styl premium
        "axes.facecolor": "#fbfcfe",
        "figure.facecolor": "white",
        "savefig.facecolor": "white",
        "axes.edgecolor": "#b7c3d0",
        "axes.linewidth": 0.9,
        "grid.color": "#dbe4ee",
        "grid.linewidth": 0.8,
        "grid.alpha": 0.9,
        "axes.grid": False,
        "axes.axisbelow": True,
        "lines.solid_capstyle": "round",
        "lines.solid_joinstyle": "round",

        # spójne DPI
        "figure.dpi": 160,
        "savefig.dpi": 160,
    })


# =========================
# 0) STAŁE
# =========================

set_global_fonts()

ARCHETYPES = [
    "Władca", "Bohater", "Mędrzec", "Opiekun", "Kochanek", "Błazen",
    "Twórca", "Odkrywca", "Czarodziej", "Towarzysz", "Niewinny", "Buntownik"
]

ARCHETYPE_FEMININE_MAP: Dict[str, str] = {
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
ARCHETYPE_MASC_FROM_FEMININE: Dict[str, str] = {v: k for k, v in ARCHETYPE_FEMININE_MAP.items()}
ARCHETYPE_LABEL_MODE: str = "male"


def _normalize_archetype_label_mode(raw: Any) -> str:
    txt = str(raw or "").strip().lower()
    if txt.startswith("fem") or "żeń" in txt or txt in {"k", "kobieta", "female", "f"}:
        return "female"
    return "male"


def configure_archetype_label_mode(raw: Any) -> None:
    global ARCHETYPE_LABEL_MODE
    ARCHETYPE_LABEL_MODE = _normalize_archetype_label_mode(raw)


def _display_archetype_label(label: Any) -> str:
    s = str(label or "")
    if ARCHETYPE_LABEL_MODE != "female":
        return s
    return str(ARCHETYPE_FEMININE_MAP.get(s, s))


def _display_archetype_labels(labels: Any) -> List[str]:
    if labels is None:
        return []
    try:
        seq = list(labels)
    except Exception:
        seq = [labels]
    return [_display_archetype_label(x) for x in seq]

# Stałe osie potrzeb: kolory zgodne z wykresem "Profil liniowy wartości (18 par)".
NEED_AXIS_COLORS: Dict[str, str] = {
    "zmiana": "#d94841",
    "ludzie": "#1d4ed8",
    "porządek": "#2b8a3e",
    "niezależność": "#7048e8",
}
NEED_AXIS_LABELS: Dict[str, str] = {
    "zmiana": "Zmiana",
    "ludzie": "Ludzie",
    "porządek": "Porządek",
    "niezależność": "Niezależność",
}
ARCHETYPE_NEED_AXIS: Dict[str, str] = {
    "Odkrywca": "zmiana",
    "Buntownik": "zmiana",
    "Błazen": "zmiana",
    "Kochanek": "ludzie",
    "Opiekun": "ludzie",
    "Towarzysz": "ludzie",
    "Niewinny": "porządek",
    "Władca": "porządek",
    "Mędrzec": "porządek",
    "Czarodziej": "niezależność",
    "Bohater": "niezależność",
    "Twórca": "niezależność",
}

# Aktywne mapowanie archetyp -> wartość (nadpisywane przez load_brand_values()).
CURRENT_BRAND_VALUES: Dict[str, str] = {}

# Skala A (versusy): 1–7, środek = 4
A_SCALE_MIN = 1
A_SCALE_MAX = 7

A_SCALE_CENTER = 4
# A: 18 versusów (skala 1-7, środek = 4)

A_PAIRS = [
    ("A1", "Opiekun", "Odkrywca"),
    ("A2", "Towarzysz", "Władca"),
    ("A3", "Opiekun", "Twórca"),
    ("A4", "Mędrzec", "Bohater"),
    ("A5", "Władca", "Buntownik"),
    ("A6", "Niewinny", "Odkrywca"),
    ("A7", "Buntownik", "Kochanek"),
    ("A8", "Opiekun", "Bohater"),
    ("A9", "Towarzysz", "Czarodziej"),
    ("A10", "Kochanek", "Bohater"),
    ("A11", "Władca", "Błazen"),
    ("A12", "Niewinny", "Czarodziej"),
    ("A13", "Czarodziej", "Mędrzec"),
    ("A14", "Towarzysz", "Twórca"),
    ("A15", "Błazen", "Niewinny"),
    ("A16", "Odkrywca", "Mędrzec"),
    ("A17", "Kochanek", "Buntownik"),
    ("A18", "Błazen", "Twórca"),
]

# Jawna mapa 18 par (jedno źródło prawdy dla nowej sekcji oczekiwań mieszkańców).
PAIR_MAP = [
    {"id": "A1", "col": "A1", "left": "Opiekun", "right": "Odkrywca"},
    {"id": "A2", "col": "A2", "left": "Towarzysz", "right": "Władca"},
    {"id": "A3", "col": "A3", "left": "Opiekun", "right": "Twórca"},
    {"id": "A4", "col": "A4", "left": "Mędrzec", "right": "Bohater"},
    {"id": "A5", "col": "A5", "left": "Władca", "right": "Buntownik"},
    {"id": "A6", "col": "A6", "left": "Niewinny", "right": "Odkrywca"},
    {"id": "A7", "col": "A7", "left": "Buntownik", "right": "Kochanek"},
    {"id": "A8", "col": "A8", "left": "Opiekun", "right": "Bohater"},
    {"id": "A9", "col": "A9", "left": "Towarzysz", "right": "Czarodziej"},
    {"id": "A10", "col": "A10", "left": "Kochanek", "right": "Bohater"},
    {"id": "A11", "col": "A11", "left": "Władca", "right": "Błazen"},
    {"id": "A12", "col": "A12", "left": "Niewinny", "right": "Czarodziej"},
    {"id": "A13", "col": "A13", "left": "Czarodziej", "right": "Mędrzec"},
    {"id": "A14", "col": "A14", "left": "Towarzysz", "right": "Twórca"},
    {"id": "A15", "col": "A15", "left": "Błazen", "right": "Niewinny"},
    {"id": "A16", "col": "A16", "left": "Odkrywca", "right": "Mędrzec"},
    {"id": "A17", "col": "A17", "left": "Kochanek", "right": "Buntownik"},
    {"id": "A18", "col": "A18", "left": "Błazen", "right": "Twórca"},
]

# D: 12 par (+/-) + D13 top1

D_ITEMS = [
    ("D1", "Władca"),
    ("D2", "Bohater"),
    ("D3", "Mędrzec"),
    ("D4", "Opiekun"),
    ("D5", "Kochanek"),
    ("D6", "Błazen"),
    ("D7", "Twórca"),
    ("D8", "Odkrywca"),
    ("D9", "Czarodziej"),
    ("D10", "Towarzysz"),
    ("D11", "Niewinny"),
    ("D12", "Buntownik"),
]

SEG_KEYWORDS = {
    "Władca": "porządek",
    "Bohater": "sprawczość",
    "Mędrzec": "analiza",
    "Opiekun": "opieka",
    "Kochanek": "relacje",
    "Błazen": "lekkość",
    "Twórca": "rozwój",
    "Odkrywca": "swoboda",
    "Czarodziej": "energia",
    "Towarzysz": "współpraca",
    "Niewinny": "przejrzystość",
    "Buntownik": "odnowa",
}

SEG_DESCRIPT = {
    "Władca": ("porządek i reguły", "mów: jasno, konkretnie, terminowo", "odpycha: chaos, niekonsekwencja"),
    "Bohater": ("sprawczość i decyzje", "mów: szybkie reakcje, odpowiedzialność, skuteczność",
                "odpycha: bierność, zwlekanie"),
    "Mędrzec": ("logika i plan", "mów: analiza, uzasadnienia, scenariusze",
                "odpycha: przypadkowość, emocjonalne decyzje"),
    "Opiekun": ("bezpieczeństwo i wsparcie", "mów: usługi publiczne, dostępność, ochrona słabszych",
                "odpycha: obojętność, zostawianie ludzi samych"),
    "Kochanek": ("bliskość i wspólnota", "mów: relacje, sąsiedztwo, klimat miasta", "odpycha: chłód, anonimowość"),
    "Błazen": ("lekkość i pozytywna energia", "mów: integracja, radość, codzienny „oddech”",
               "odpycha: ponurość, sztuczność wydarzeń"),
    "Twórca": ("pomysły i realizacja", "mów: projekty, wdrożenia, kreatywne rozwiązania",
               "odpycha: rutyna, „papierologia”"),
    "Odkrywca": ("swoboda i inicjatywa", "mów: przestrzeń dla oddolnych działań, próbowanie",
                 "odpycha: bariery, kontrola, blokowanie"),
    "Czarodziej": ("impuls i inspiracja", "mów: wizja, energia, zmiana sposobu myślenia",
                   "odpycha: stagnacja, brak kierunku"),
    "Towarzysz": ("dialog i współpraca", "mów: konsultacje, współdecydowanie, słuchanie",
                  "odpycha: decyzje „po cichu”, pozorne konsultacje"),
    "Niewinny": ("prostota i uczciwość", "mów: przejrzyście, prosto, bez kruczków",
                 "odpycha: niejasność, „kombinowanie”"),
    "Buntownik": ("przełamywanie schematów", "mów: odwaga w odnowie, naprawianie nieskuteczności",
                  "odpycha: „nie da się”, blokowanie krytyki"),
}

# =========================
# 0a) WARTOŚCI MARKI (etykiety do raportu)
# =========================

D_WHEEL_ORDER = [
    "Buntownik",
    "Błazen",
    "Kochanek",
    "Opiekun",
    "Towarzysz",
    "Niewinny",
    "Władca",
    "Mędrzec",
    "Czarodziej",
    "Bohater",
    "Twórca",
    "Odkrywca",
]

DEFAULT_BRAND_VALUES = {
    "Władca": "Porządek",
    "Bohater": "Odwaga",
    "Mędrzec": "Rozsądek",
    "Opiekun": "Troska",
    "Kochanek": "Relacje",
    "Błazen": "Otwartość",
    "Twórca": "Rozwój",
    "Odkrywca": "Wolność",
    "Czarodziej": "Wizja",
    "Towarzysz": "Współpraca",
    "Niewinny": "Przejrzystość",
    "Buntownik": "Odnowa",
}


def load_brand_values(root: Path) -> Dict[str, str]:
    """
    Czyta mapowanie archetyp -> wartość z pliku archetype_values.json (jeśli istnieje).
    Braki uzupełnia domyślną listą DEFAULT_BRAND_VALUES.
    """
    mapping = dict(DEFAULT_BRAND_VALUES)
    p = Path(root) / "archetype_values.json"
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                user_map = json.load(f)
            if isinstance(user_map, dict):
                for k, v in user_map.items():
                    if k in mapping and isinstance(v, str) and v.strip():
                        mapping[k] = v.strip()
        except Exception:
            # jeśli plik jest uszkodzony – zostają domyślne wartości
            pass
    globals()["CURRENT_BRAND_VALUES"] = dict(mapping)
    return mapping


def _replace_archetypes_in_text(text: str, mapping: Dict[str, str]) -> str:
    out = text
    for a, v in mapping.items():
        out = out.replace(a, v)
    return out


def df_display_values(df: pd.DataFrame, brand_values: Dict[str, str], replace_inside: bool = False) -> pd.DataFrame:
    """Podmienia etykiety archetypów na etykiety wartości (komórki + indeks + nagłówki)."""
    d = df.copy()

    def _map_text(x: Any) -> Any:
        if not isinstance(x, str):
            return x
        out = brand_values.get(x, x)
        if replace_inside and out == x:
            for a, v in brand_values.items():
                out = out.replace(a, v)
        return out

    # 1) Komórki (bezpiecznie tylko kolumny tekstowe)
    for c in d.columns:
        try:
            col = d[c]
            dtype = col.dtype

            is_text_like = (
                    pd.api.types.is_object_dtype(dtype)
                    or pd.api.types.is_string_dtype(dtype)
                    or isinstance(dtype, pd.CategoricalDtype)
            )

            if is_text_like:
                d[c] = col.map(_map_text)
        except Exception:
            # gdyby kolumna miała nietypowy typ pandas extension
            pass

    # 2) Specjalny przypadek: kolumna "archetyp"
    if "archetyp" in d.columns:
        d["archetyp"] = d["archetyp"].map(_map_text)

    # 3) Nagłówki kolumn
    try:
        d.columns = pd.Index([_map_text(c) for c in d.columns],
                             name=_map_text(d.columns.name) if isinstance(d.columns.name, str) else d.columns.name)
    except Exception:
        d.columns = [_map_text(c) for c in d.columns]

    # 4) Indeks (bardzo ważne dla tabel, gdzie archetypy są w wierszach)
    if isinstance(d.index, pd.MultiIndex):
        new_tuples = []
        for tup in d.index.tolist():
            new_tuples.append(tuple(_map_text(x) for x in tup))
        d.index = pd.MultiIndex.from_tuples(new_tuples,
                                            names=[_map_text(n) if isinstance(n, str) else n for n in d.index.names])
    else:
        d.index = pd.Index(
            [_map_text(x) for x in d.index.tolist()],
            name=_map_text(d.index.name) if isinstance(d.index.name, str) else d.index.name
        )

    return d


# =========================
# 0b) HELPERY
# =========================

def series_with_value_index(s: pd.Series, mapping: Dict[str, str]) -> pd.Series:
    s2 = s.copy()
    s2.index = [mapping.get(str(i), str(i)) for i in s2.index]
    return s2


def _safe_float(x: Any) -> float:
    try:
        return float(x)
    except Exception:
        return float("nan")


def _clean_ab(x: Any) -> Optional[str]:
    if pd.isna(x):
        return None
    s = str(x).strip()
    if not s:
        return None
    s_up = s.upper()

    # najczęstsze przypadki
    if s_up in ("A", "B"):
        return s_up
    if s in ("1", "2"):
        return "A" if s == "1" else "B"

    # odporność na eksport typu: "A.", "A)", "A - ...", "B:" itp.
    if s_up.startswith("A"):
        return "A"
    if s_up.startswith("B"):
        return "B"

    return None


def _clean_1to7(x: Any) -> Optional[int]:
    if pd.isna(x):
        return None
    try:
        v = int(float(x))
        if A_SCALE_MIN <= v <= A_SCALE_MAX:
            return v
    except Exception:
        return None
    return None


def _clean_binary_mark(x: Any) -> float:
    """
    Normalizuje zaznaczenie 0/1 z różnych formatów importu.
    Zwraca 1.0 dla wartości prawdziwych, inaczej 0.0.
    """
    if x is None or (isinstance(x, float) and (not np.isfinite(x))):
        return 0.0
    s = str(x).strip().lower()
    if not s:
        return 0.0
    if s in {"1", "true", "t", "tak", "yes", "y", "on", "x"}:
        return 1.0
    if s in {"0", "false", "f", "nie", "no", "n", "off"}:
        return 0.0
    try:
        v = float(str(x).replace(",", "."))
        if np.isfinite(v) and v > 0:
            return 1.0
    except Exception:
        pass
    return 0.0


def _normalize_text_token(x: Any) -> str:
    if x is None or (isinstance(x, float) and (not np.isfinite(x))):
        return ""
    s = str(x).strip().lower()
    if not s:
        return ""
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^a-z0-9]+", " ", s).strip()
    return s


def _build_archetype_lookup() -> Dict[str, int]:
    lut: Dict[str, int] = {}
    for i, name in enumerate(ARCHETYPES):
        key = _normalize_text_token(name)
        if key:
            lut[key] = int(i)
            lut[key.replace(" ", "")] = int(i)
    return lut


ARCHETYPE_LOOKUP = _build_archetype_lookup()


def _parse_archetype_index(value: Any, lookup: Optional[Dict[str, int]] = None) -> int:
    lut = lookup or ARCHETYPE_LOOKUP
    key = _normalize_text_token(value)
    if not key:
        return -1
    # Numery archetypów: 1..12 (legacy) oraz 0..11 (indeksy)
    m_num = re.match(r"^(\d{1,2})$", key)
    if m_num:
        n = int(m_num.group(1))
        if 1 <= n <= len(ARCHETYPES):
            return int(n - 1)
        if 0 <= n < len(ARCHETYPES):
            return int(n)
    # Formaty typu "1 Władca", "nr 1" itp.
    m_pref = re.match(r"^(?:nr|no)?\s*(\d{1,2})\b", key)
    if m_pref:
        n = int(m_pref.group(1))
        if 1 <= n <= len(ARCHETYPES):
            return int(n - 1)
        if 0 <= n < len(ARCHETYPES):
            return int(n)
    if key in lut:
        return int(lut[key])
    key2 = key.replace(" ", "")
    if key2 in lut:
        return int(lut[key2])
    return -1


def _is_blank_like(x: Any) -> bool:
    key = _normalize_text_token(x)
    return key in ("", "nan", "none", "null", "brak", "na", "n a", "-")


def save_json(obj: Any, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)


def load_json(path: Path) -> dict:
    path = Path(path)
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _fmt_pct(x: Any) -> str:
    try:
        return f"{float(x):.1f}"
    except Exception:
        return "—"


def _fmt_int(x: Any) -> str:
    try:
        return str(int(round(float(x))))
    except Exception:
        return "—"


def _html_escape(s: Any) -> str:
    return _html.escape("" if s is None else str(s))


def ensure_outdir(root: Path) -> Path:
    outdir = root / "WYNIKI"
    outdir.mkdir(parents=True, exist_ok=True)
    return outdir


def save_parser_archetype_diagnostics(outdir: Path, diags: List[Dict[str, Any]]) -> None:
    rows: List[Dict[str, Any]] = []
    for d in (diags or []):
        field = str(d.get("field", "")).strip()
        miss = int(d.get("missing_or_unknown_count", 0) or 0)
        rec = float(d.get("recognized_rate_pct", 0.0) or 0.0)
        rows.append({
            "field": field,
            "row_type": "summary",
            "value": "",
            "count": miss,
            "recognized_rate_pct": round(rec, 2),
        })
        for item in (d.get("unknown_top") or []):
            rows.append({
                "field": field,
                "row_type": "unknown_value",
                "value": str(item.get("value", "")),
                "count": int(item.get("count", 0) or 0),
                "recognized_rate_pct": round(rec, 2),
            })

    if not rows:
        return

    pd.DataFrame(rows).to_csv(
        Path(outdir) / "diag_parser_archetypy.csv",
        index=False,
        encoding="utf-8-sig"
    )


# =========================
# 0c) USTAWIENIA
# =========================

def export_xlsx_for_csv_folder(outdir: Path) -> None:
    """
    Tworzy pliki .xlsx dla wszystkich .csv w folderze outdir.
    Nazwy: plik.csv -> plik.xlsx
    """
    outdir = Path(outdir)
    for csv_path in sorted(outdir.glob("*.csv")):
        xlsx_path = csv_path.with_suffix(".xlsx")

        try:
            df_tmp = pd.read_csv(csv_path, encoding="utf-8-sig")
        except Exception:
            try:
                df_tmp = pd.read_csv(csv_path, encoding="utf-8")
            except Exception:
                continue

        try:
            df_tmp.to_excel(xlsx_path, index=False, engine="openpyxl")
        except Exception:
            # jeśli np. plik jest otwarty w Excelu – pomijamy bez wywalania całego skryptu
            pass


@dataclass
class Settings:
    city: str = "Poznań"
    city_label: str = "Miasto Poznań"
    population_15_plus: float = 0.0
    bootstrap_reps: int = 2000
    w_A: float = 1.0
    weight_column: str = ""

    # =========================
    # PREMIUM: jedna segmentacja ultra premium (K w przedziale min–max)
    # =========================
    segments_k_min: int = 3
    segments_k_max: int = 9
    segments_max_segments: int = 9
    segments_k_default: int = 5

    # twarde minimum analityczne (ochrona przed mikro-segmentami)
    # to NIE jest już suwak UI
    segments_min_share_default: float = 0.10

    # =========================
    # KLASTRY (zakładka "Skupienia")
    # =========================
    clusters_k_min: int = 3
    clusters_k_max: int = 9
    clusters_k_default: int = 5
    clusters_min_share_default: float = 0.05

    # pola zgodnościowe po starym suwaku % zostają wyłącznie dla kompatybilności
    segments_min_share_slider_min: float = 0.05
    segments_min_share_slider_max: float = 0.25

    # czy metryczka jest wymagana (u Ciebie: TAK)
    require_metry: bool = True

    random_seed: int = 2026
    silhouette_sample_max: int = 1800

    # ręczne nadpisania progów dla sekcji
    # „Segmenty - przewagi naprawdę istotne”
    # format klucza: "X z Y · #R" (np. "2 z 2 · #1") albo "Y|X|R"
    # gdzie: X = liczba pokonanych segmentów, Y = liczba innych segmentów, R = pozycja w wierszu
    segment_hit_threshold_overrides: Dict[str, float] = field(default_factory=dict)
    # dynamiczna metryczka (pełna konfiguracja pytań M_*) przekazywana z panelu
    metryczka_config: Dict[str, Any] = field(default_factory=dict)
    # styl obrysu segmentu na mapie: "classic" (domyślny, opływowy) albo "smooth" (plamowy/concave)
    segment_outline_style: str = "classic"
    # tryb podpisów archetypów na wykresach/tabelach (male|female)
    archetype_label_mode: str = "male"

SEG_FORBIDDEN_ARCHETYPE_PAIRS: Tuple[Tuple[str, str], ...] = (
    ("Buntownik", "Władca"),
    ("Opiekun", "Bohater"),
)
SEG_FORBIDDEN_TOP_N: int = 4

# Specjalne progi "trafienia" dla małych/średnich modeli segmentacji.
# Klucz = (liczba innych segmentów, liczba pokonanych segmentów, pozycja w wierszu)
# Wartość = (minimalny wynik Pm, czy porównanie jest >=)
SEG_SMART_SPECIAL_RULES_DEFAULT: Dict[Tuple[int, int, int], Tuple[float, bool]] = {
    (2, 1, 2): (3.0, False),
    (2, 2, 1): (2.6, True),
    (2, 0, 3): (4.0, True),
    (2, 0, 2): (4.0, True),
    (3, 2, 2): (3.0, True),
    (3, 3, 1): (3.0, True),
    (4, 3, 2): (2.6, True),
    (4, 4, 1): (2.6, True),
    (5, 3, 3): (2.6, True),
    (5, 3, 2): (2.6, True),
    (5, 4, 2): (2.6, True),
    (5, 5, 1): (2.6, True),
    (6, 4, 3): (2.6, True),
    (6, 5, 2): (2.6, True),
    (6, 5, 1): (2.6, True),
    (6, 6, 1): (3.0, True),
}


def _segment_smart_rule_label(rule_key: Tuple[int, int, int]) -> str:
    other_cnt, beats, row_rank = [int(x) for x in rule_key]
    return f"{beats} z {other_cnt} · #{row_rank}"


def _parse_segment_smart_rule_key(raw_key: Any) -> Optional[Tuple[int, int, int]]:
    s = str(raw_key or "").strip()
    if not s:
        return None

    m = re.match(r"^\s*(\d+)\s*[|,:;/]\s*(\d+)\s*[|,:;/]\s*(\d+)\s*$", s)
    if m:
        other_cnt = int(m.group(1))
        beats = int(m.group(2))
        row_rank = int(m.group(3))
        if other_cnt >= 0 and beats >= 0 and row_rank >= 1:
            return other_cnt, beats, row_rank

    m = re.search(r"(\d+)\s*z\s*(\d+)\s*[·\-–]?\s*#\s*(\d+)", s, flags=re.IGNORECASE)
    if m:
        beats = int(m.group(1))
        other_cnt = int(m.group(2))
        row_rank = int(m.group(3))
        if other_cnt >= 0 and beats >= 0 and row_rank >= 1:
            return other_cnt, beats, row_rank

    return None


def _parse_segment_threshold_overrides(raw_overrides: Any) -> Dict[Tuple[int, int, int], float]:
    out: Dict[Tuple[int, int, int], float] = {}
    if not isinstance(raw_overrides, dict):
        return out

    for raw_key, raw_val in raw_overrides.items():
        key_tup = _parse_segment_smart_rule_key(raw_key)
        if key_tup is None:
            continue
        try:
            val = float(raw_val)
        except Exception:
            continue
        if np.isfinite(val):
            out[key_tup] = float(val)

    return out


def _resolve_segment_smart_rules(
        override_dict: Optional[Dict[Any, Any]] = None
) -> Dict[Tuple[int, int, int], Tuple[float, bool]]:
    rules = dict(SEG_SMART_SPECIAL_RULES_DEFAULT)
    parsed = _parse_segment_threshold_overrides(override_dict)

    for key_tup, min_val in parsed.items():
        if key_tup in rules:
            _old_min, old_ge = rules[key_tup]
            rules[key_tup] = (float(min_val), bool(old_ge))
        else:
            # dla nowych kluczy z settings.json domyślnie stosujemy >=
            rules[key_tup] = (float(min_val), True)

    return rules

# =========================
# 1) WCZYTANIE DANYCH
# =========================

def load_settings(path: Path) -> Settings:
    if not Path(path).exists():
        return Settings()
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
    except json.JSONDecodeError as e:
        msg = (
            f"Błąd składni JSON w pliku settings.json: linia {e.lineno}, kolumna {e.colno}. "
            "Sprawdź brakujące przecinki lub cudzysłowy."
        )
        raise ValueError(msg) from e

    s = Settings()
    unknown_keys: List[str] = []
    for k, v in d.items():
        if hasattr(s, k):
            setattr(s, k, v)
        else:
            unknown_keys.append(str(k))

    if unknown_keys:
        print(
            "[WARN] settings.json: zignorowano nieobsługiwane klucze: "
            + ", ".join(sorted(unknown_keys))
        )

    return s


def read_data_csv(path: Path) -> pd.DataFrame:
    # Autodetekcja separatora (, lub ;) + bezpieczne czytanie UTF-8 z BOM (Excel)
    df = pd.read_csv(path, encoding="utf-8-sig", sep=None, engine="python")
    df.columns = [str(c).replace("\ufeff", "").strip() for c in df.columns]
    return df


# =========================
# 2) PARSERY BLOKÓW
# =========================

def get_weights(df: pd.DataFrame, weight_column: str) -> np.ndarray:
    if weight_column and (weight_column in df.columns):
        w = df[weight_column].apply(_safe_float).values
        w = np.where(np.isfinite(w) & (w > 0), w, 1.0)
        return w.astype(float)
    return np.ones(len(df), dtype=float)


def parse_A_matrix(df: pd.DataFrame) -> np.ndarray:
    cols = [pid for pid, _, _ in A_PAIRS]
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"Brak kolumn A: {missing}")
    mat = np.full((len(df), len(cols)), np.nan, dtype=float)
    for j, c in enumerate(cols):
        mat[:, j] = df[c].apply(lambda x: _clean_1to7(x) if _clean_1to7(x) is not None else np.nan).astype(float).values
    return mat


def parse_B(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    b1_cols = [f"B1_{a}" for a in ARCHETYPES]
    missing = [c for c in b1_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Brak kolumn B1: {missing}")

    b1 = np.zeros((len(df), len(ARCHETYPES)), dtype=float)
    for j, c in enumerate(b1_cols):
        b1[:, j] = df[c].apply(_clean_binary_mark).values

    if "B2" not in df.columns:
        raise ValueError("Brak kolumny B2.")

    b2_raw = df["B2"].copy()
    b2 = np.full(len(df), -1, dtype=int)
    unknown_counter: Dict[str, int] = {}

    for i, val in enumerate(b2_raw.values):
        idx = _parse_archetype_index(val)
        if idx >= 0:
            b2[i] = int(idx)
            continue
        if not _is_blank_like(val):
            key = str(val).strip()
            unknown_counter[key] = int(unknown_counter.get(key, 0)) + 1

    unknown_top = sorted(unknown_counter.items(), key=lambda kv: (-int(kv[1]), str(kv[0])))[:12]
    diag = {
        "field": "B2",
        "missing_or_unknown_count": int(np.sum(b2 < 0)),
        "recognized_rate_pct": float((np.sum(b2 >= 0) / max(1, len(b2))) * 100.0),
        "unknown_top": [{"value": str(k), "count": int(v)} for k, v in unknown_top],
    }

    return b1, b2, diag


# =========================
# 3) A: STATY PARY + SIŁA (Bradley–Terry)
# =========================

def parse_D(df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray, Dict[str, Any]]:
    cols = [pid for pid, _ in D_ITEMS]
    missing = [c for c in cols if c not in df.columns]
    if missing:
        raise ValueError(f"Brak kolumn D1..D12: {missing}")

    d12 = np.full((len(df), 12), np.nan, dtype=float)  # A=+1, B=-1
    for j, c in enumerate(cols):
        d12[:, j] = df[c].apply(
            lambda x: 1.0 if _clean_ab(x) == "A" else (-1.0 if _clean_ab(x) == "B" else np.nan)
        ).values

    if "D13" not in df.columns:
        raise ValueError("Brak kolumny D13.")

    d13_raw = df["D13"].copy()
    d13 = np.full(len(df), -1, dtype=int)
    unknown_counter: Dict[str, int] = {}

    for i, val in enumerate(d13_raw.values):
        idx = _parse_archetype_index(val)
        if idx >= 0:
            d13[i] = int(idx)
            continue
        if not _is_blank_like(val):
            key = str(val).strip()
            unknown_counter[key] = int(unknown_counter.get(key, 0)) + 1

    unknown_top = sorted(unknown_counter.items(), key=lambda kv: (-int(kv[1]), str(kv[0])))[:12]
    diag = {
        "field": "D13",
        "missing_or_unknown_count": int(np.sum(d13 < 0)),
        "recognized_rate_pct": float((np.sum(d13 >= 0) / max(1, len(d13))) * 100.0),
        "unknown_top": [{"value": str(k), "count": int(v)} for k, v in unknown_top],
    }

    return d12, d13, diag


def D_sentiment(d12: np.ndarray, d13: np.ndarray, weights: np.ndarray,
                arch_names: List[str] = ARCHETYPES) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    D12: sentyment (+/-) dla każdego archetypu (w %).
    D13: udział wskazań priorytetowych + sentyment w ramach wyboru.
    """
    n_arch = len(arch_names)
    w = np.asarray(weights, dtype=float).reshape(-1)

    # ===== D12 (PLUS/MINUS) =====
    w_tot = np.zeros(n_arch, dtype=float)
    w_plus = np.zeros(n_arch, dtype=float)
    w_minus = np.zeros(n_arch, dtype=float)
    n_resp = np.zeros(n_arch, dtype=int)

    for j in range(n_arch):
        col = np.asarray(d12[:, j], dtype=float)
        m = np.isfinite(col)
        n_resp[j] = int(np.sum(m))
        if not np.any(m):
            continue

        ww = w[m]
        vv = col[m]
        w_tot[j] = float(np.sum(ww))
        w_plus[j] = float(np.sum(ww[vv > 0]))
        w_minus[j] = float(np.sum(ww[vv < 0]))

    pct_plus = np.where(w_tot > 0, w_plus / w_tot * 100.0, np.nan)
    pct_minus = np.where(w_tot > 0, w_minus / w_tot * 100.0, np.nan)

    df_D12 = pd.DataFrame({
        "archetyp": arch_names,
        "liczba": n_resp,
        "%PLUS": np.round(pct_plus, 1),
        "%MINUS": np.round(pct_minus, 1),
    }).sort_values("%PLUS", ascending=False).reset_index(drop=True)

    # ===== D13 (priorytet) =====
    d13 = np.asarray(d13, dtype=int).reshape(-1)
    m_all = d13 >= 0
    total_w = float(np.sum(w[m_all])) if np.any(m_all) else 0.0

    rows = []
    for i, arch in enumerate(arch_names):
        mi = (d13 == i) & m_all
        n_i = int(np.sum(mi))
        w_i = float(np.sum(w[mi])) if n_i > 0 else 0.0
        pct_i = (w_i / total_w * 100.0) if total_w > 0 else np.nan

        # sentyment tylko wśród tych, którzy wybrali ten archetyp w D13
        col = np.asarray(d12[:, i], dtype=float)
        si = mi & np.isfinite(col)
        w_si = float(np.sum(w[si])) if np.any(si) else 0.0
        w_plus_i = float(np.sum(w[si & (col > 0)])) if w_si > 0 else 0.0
        w_minus_i = float(np.sum(w[si & (col < 0)])) if w_si > 0 else 0.0

        pct_plus_w = (w_plus_i / w_si * 100.0) if w_si > 0 else np.nan
        pct_minus_w = (w_minus_i / w_si * 100.0) if w_si > 0 else np.nan

        rows.append({
            "archetyp": arch,
            "liczba": n_i,
            "%": pct_i,
            "%PLUS_wybor": pct_plus_w,
            "%MINUS_wybor": pct_minus_w,
        })

    df_D13 = pd.DataFrame(rows).sort_values("%", ascending=False).reset_index(drop=True)
    for c in ["%", "%PLUS_wybor", "%MINUS_wybor"]:
        df_D13[c] = df_D13[c].round(1)

    return df_D12, df_D13


# =========================
# 3b) METRYCZKA (profilowe zmienne): M_*
# =========================
# Kodowanie (format A):
# 1) M_PLEC:      1 kobieta, 2 mężczyzna
# 2) M_WIEK:      1 15-39, 2 40-59, 3 60+
# 3) M_WYKSZT:    1 podstawowe/gimnazjalne/zawodowe, 2 średnie, 3 wyższe
# 4) M_ZAWOD:     1 umysłowy, 2 fizyczny, 3 własna firma, 4 student/uczeń, 5 bezrobotny,
#                 6 rencista/emeryt, 7 inna
# 5) M_MATERIAL:  1 bardzo źle, 2 raczej źle, 3 przeciętnie, 4 raczej dobrze, 5 bardzo dobrze, 6 odmawia
#
# 0 = brak/nie rozpoznano

METRY_DEFS: Dict[str, Dict[int, str]] = {
    "M_PLEC": {0: "brak danych", 1: "kobieta", 2: "mężczyzna"},
    "M_WIEK": {0: "brak danych", 1: "15-39", 2: "40-59", 3: "60+"},
    "M_WYKSZT": {0: "brak danych", 1: "podst./gim./zaw.", 2: "średnie", 3: "wyższe"},
    "M_ZAWOD": {
        0: "brak danych",
        1: "prac. umysłowy",
        2: "prac. fizyczny",
        3: "własna firma",
        4: "student/uczeń",
        5: "bezrobotny",
        6: "rencista/emeryt",
        7: "inna",
    },
    "M_MATERIAL": {
        0: "brak danych",
        1: "bardzo zła",
        2: "raczej zła",
        3: "przeciętna",
        4: "raczej dobra",
        5: "bardzo dobra",
        6: "odmowa",
    },
}

# Dopuszczamy aliasy (gdy export ma pełną treść pytania w nagłówku)
METRY_ALIASES: Dict[str, List[str]] = {
    "M_PLEC": ["M_PLEC", "Płeć", "Plec", "płeć", "plec", "Proszę o podanie płci"],
    "M_WIEK": ["M_WIEK", "Wiek", "wiek", "Jaki jest Pana/Pani wiek"],
    "M_WYKSZT": ["M_WYKSZT", "Wykształcenie", "Wyksztalcenie", "Jakie ma Pan/Pani wykształcenie"],
    "M_ZAWOD": ["M_ZAWOD", "Sytuacja zawodowa", "Status zawodowy", "Jaka jest Pana/Pani sytuacja zawodowa"],
    "M_MATERIAL": ["M_MATERIAL", "Sytuacja materialna", "Jak ocenia Pan/Pani własną sytuację materialną"],
}


def _strip_accents_pl(s: str) -> str:
    return (
        s.replace("ą", "a").replace("ć", "c").replace("ę", "e").replace("ł", "l")
        .replace("ń", "n").replace("ó", "o").replace("ś", "s").replace("ż", "z").replace("ź", "z")
    )


def _norm_token(x: Any) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return ""
    s = str(x).strip().lower()
    s = _strip_accents_pl(s)
    s = re.sub(r"\s+", " ", s)
    return s


def _pick_column(df: pd.DataFrame, aliases: List[str]) -> Optional[str]:
    cols_norm = {c.strip().lower(): c for c in df.columns}
    for a in aliases:
        key = a.strip().lower()
        if key in cols_norm:
            return cols_norm[key]
    for a in aliases:
        a_norm = a.strip().lower()
        for c in df.columns:
            if a_norm and a_norm in c.strip().lower():
                return c
    return None


def _parse_gender(x: Any) -> int:
    v = _norm_token(x)
    if v in {"a", "1", "kobieta", "k", "f", "female", "woman"} or "kobiet" in v:
        return 1
    if v in {"b", "2", "mezczyzna", "mężczyzna", "m", "male", "man"} or "mezczyzn" in v:
        return 2
    return 0


def _parse_age_group(x: Any) -> int:
    v = _norm_token(x)
    if v in {"a", "1"}: return 1
    if v in {"b", "2"}: return 2
    if v in {"c", "3"}: return 3
    if "15" in v and "39" in v: return 1
    if "40" in v and "59" in v: return 2
    if "60" in v: return 3
    m = re.search(r"\b(\d{2})\b", v)
    if m:
        age = int(m.group(1))
        if 15 <= age <= 39: return 1
        if 40 <= age <= 59: return 2
        if age >= 60: return 3
    return 0


def _parse_education(x: Any) -> int:
    v = _norm_token(x)
    if v in {"a", "1"}: return 1
    if v in {"b", "2"}: return 2
    if v in {"c", "3"}: return 3

    # pełne + skróty typu: "podst./gim./zaw."
    if any(t in v for t in ["podstaw", "podst", "gimnaz", "gim", "zasadnicz", "zawod", "zaw"]):
        return 1

    if "srednie" in v or "średnie" in v: return 2
    if "wyzsze" in v or "wyższe" in v: return 3
    return 0


def _parse_employment(x: Any) -> int:
    v = _norm_token(x)
    if v in {"a", "1"}: return 1
    if v in {"b", "2"}: return 2
    if v in {"c", "3"}: return 3
    if v in {"d", "4"}: return 4
    if v in {"e", "5"}: return 5
    if v in {"f", "6"}: return 6
    if v in {"g", "7"}: return 7
    if "umys" in v: return 1
    if "fizycz" in v: return 2
    if "wlasn" in v and "firm" in v: return 3
    if "student" in v or "uczen" in v or "uczeń" in v: return 4
    if "bezrobot" in v: return 5
    if "emeryt" in v or "rencist" in v: return 6
    if "inna" in v: return 7
    return 0


def _parse_material(x: Any) -> int:
    v = _norm_token(x)
    if v in {"a", "1"}: return 1
    if v in {"b", "2"}: return 2
    if v in {"c", "3"}: return 3
    if v in {"d", "4"}: return 4
    if v in {"e", "5"}: return 5
    if v in {"f", "6"}: return 6
    if "odmaw" in v: return 6
    if "bardzo zle" in v or "ciezk" in v: return 1
    if "raczej zle" in v: return 2
    if "przeciet" in v or "sredni" in v: return 3
    if "raczej dobr" in v: return 4
    if "bardzo dobr" in v: return 5
    return 0


def parse_metryczka(
        df: pd.DataFrame,
        metryczka_config: Optional[Dict[str, Any]] = None
) -> Tuple[pd.DataFrame, Dict[str, Dict[int, str]]]:
    _set_dynamic_metry_schema_from_config(metryczka_config)
    col_map: Dict[str, str] = {}
    missing: List[str] = []
    for key, aliases in METRY_ALIASES.items():
        col = _pick_column(df, aliases)
        if col is None:
            missing.append(key)
        else:
            col_map[key] = col

    if missing:
        raise ValueError(
            "BRAK METRYCZKI w data.csv. Brakuje kolumn: "
            + ", ".join(missing)
            + ".\nWymagane nazwy (najprościej): M_PLEC, M_WIEK, M_WYKSZT, M_ZAWOD, M_MATERIAL."
        )

    out = pd.DataFrame(index=df.index)
    out["M_PLEC"] = df[col_map["M_PLEC"]].map(_parse_gender).astype(int)
    out["M_WIEK"] = df[col_map["M_WIEK"]].map(_parse_age_group).astype(int)
    out["M_WYKSZT"] = df[col_map["M_WYKSZT"]].map(_parse_education).astype(int)
    out["M_ZAWOD"] = df[col_map["M_ZAWOD"]].map(_parse_employment).astype(int)
    out["M_MATERIAL"] = df[col_map["M_MATERIAL"]].map(_parse_material).astype(int)

    # Dodatkowe pola metryczkowe (M_*) przepuszczamy dynamicznie.
    # Dzięki temu raport może pokazać także niestandardowe zmienne demograficzne.
    used_src_cols = {str(v) for v in col_map.values()}
    for src_col in list(df.columns):
        src_name = str(src_col or "").strip()
        src_upper = src_name.upper()
        if not src_upper.startswith("M_"):
            continue
        if _is_aux_metry_column(src_upper):
            continue
        if src_upper in out.columns:
            continue
        if src_name in used_src_cols:
            continue
        series_raw = df[src_col]
        series_num = pd.to_numeric(series_raw, errors="coerce")
        non_na_num = int(series_num.notna().sum())
        if non_na_num > 0 and non_na_num >= max(3, int(0.7 * max(1, len(series_num)))):
            out[src_upper] = series_num.fillna(0).astype(int)
        else:
            out[src_upper] = (
                series_raw.fillna("")
                .astype(str)
                .map(lambda x: " ".join(str(x).split()).strip())
            )

    return out, METRY_DEFS

def apply_poststrat_weights_from_targets(
        root: Path,
        metry: pd.DataFrame,
        base_weights: np.ndarray
) -> Tuple[np.ndarray, Optional[pd.DataFrame]]:
    """
    Jeśli istnieje plik targets_poststrat.csv w katalogu narzędzia,
    buduje wagę analityczną dla komórek płeć × wiek.

    Oczekiwane kolumny:
    - plec
    - wiek
    - udzial_docelowy

    Dopuszcza też procenty (np. 18 zamiast 0.18).
    """
    target_path = Path(root) / "targets_poststrat.csv"
    w0 = np.asarray(base_weights, dtype=float).reshape(-1)

    if not target_path.exists():
        return w0, None

    tgt = pd.read_csv(target_path, encoding="utf-8-sig", sep=None, engine="python")
    tgt.columns = [str(c).replace("\ufeff", "").strip() for c in tgt.columns]

    col_gender = _pick_column(tgt, ["plec", "płeć", "gender", "M_PLEC"])
    col_age = _pick_column(tgt, ["wiek", "age", "M_WIEK"])
    col_share = _pick_column(
        tgt,
        ["udzial_docelowy", "udział_docelowy", "udzial", "udział", "share", "target_share", "pct", "procent"]
    )

    if col_gender is None or col_age is None or col_share is None:
        raise ValueError(
            "Plik targets_poststrat.csv musi zawierać kolumny: "
            "plec, wiek, udzial_docelowy."
        )

    tgt_df = pd.DataFrame({
        "M_PLEC": tgt[col_gender].map(_parse_gender).astype(int),
        "M_WIEK": tgt[col_age].map(_parse_age_group).astype(int),
        "udzial_docelowy": pd.to_numeric(tgt[col_share], errors="coerce").fillna(0.0).astype(float),
    })

    tgt_df = tgt_df[
        (tgt_df["M_PLEC"] > 0)
        & (tgt_df["M_WIEK"] > 0)
        & (tgt_df["udzial_docelowy"] > 0)
    ].copy()

    if tgt_df.empty:
        raise ValueError(
            "Plik targets_poststrat.csv nie zawiera poprawnych, dodatnich komórek płeć × wiek."
        )

    # Dopuszczamy procenty, np. 18 zamiast 0.18
    if float(tgt_df["udzial_docelowy"].max()) > 1.0:
        tgt_df["udzial_docelowy"] = tgt_df["udzial_docelowy"] / 100.0

    tgt_df = (
        tgt_df.groupby(["M_PLEC", "M_WIEK"], as_index=False)["udzial_docelowy"]
        .sum()
        .copy()
    )

    tgt_sum = float(tgt_df["udzial_docelowy"].sum())
    if tgt_sum <= 0:
        raise ValueError("Suma udziałów w targets_poststrat.csv musi być większa od zera.")

    tgt_df["udzial_docelowy"] = tgt_df["udzial_docelowy"] / tgt_sum

    sample_df = pd.DataFrame({
        "M_PLEC": metry["M_PLEC"].astype(int).values,
        "M_WIEK": metry["M_WIEK"].astype(int).values,
        "w_bazowa": w0,
    })

    sample_df = sample_df[
        (sample_df["M_PLEC"] > 0)
        & (sample_df["M_WIEK"] > 0)
    ].copy()

    if sample_df.empty:
        raise ValueError(
            "Nie da się policzyć wag poststratyfikacyjnych: brak poprawnie rozpoznanej płci / wieku w próbie."
        )

    sample_df = (
        sample_df.groupby(["M_PLEC", "M_WIEK"], as_index=False)["w_bazowa"]
        .sum()
        .copy()
    )

    sample_sum = float(sample_df["w_bazowa"].sum())
    if sample_sum <= 0:
        raise ValueError("Suma wag bazowych w próbie musi być większa od zera.")

    sample_df["udzial_proby"] = sample_df["w_bazowa"] / sample_sum

    diag = tgt_df.merge(
        sample_df[["M_PLEC", "M_WIEK", "udzial_proby"]],
        on=["M_PLEC", "M_WIEK"],
        how="left",
    )

    if (diag["udzial_proby"].fillna(0.0) <= 0.0).any():
        bad = diag.loc[diag["udzial_proby"].fillna(0.0) <= 0.0, ["M_PLEC", "M_WIEK"]]
        bad_txt = ", ".join(
            f"({int(r['M_PLEC'])}, {int(r['M_WIEK'])})"
            for _, r in bad.iterrows()
        )
        raise ValueError(
            "Nie można zastosować wag poststratyfikacyjnych: w próbie brakuje komórek płeć × wiek "
            f"obecnych w targets_poststrat.csv: {bad_txt}. "
            "Scal przedziały wieku albo użyj większej próby."
        )

    diag["mnoznik"] = diag["udzial_docelowy"] / diag["udzial_proby"]

    factor_map = {
        (int(r.M_PLEC), int(r.M_WIEK)): float(r.mnoznik)
        for r in diag.itertuples(index=False)
    }

    w = w0.copy()
    plec_arr = metry["M_PLEC"].astype(int).values
    wiek_arr = metry["M_WIEK"].astype(int).values

    valid_mask = (plec_arr > 0) & (wiek_arr > 0)
    valid_idx = np.where(valid_mask)[0]

    for i in valid_idx:
        key = (int(plec_arr[i]), int(wiek_arr[i]))
        if key in factor_map:
            w[i] *= factor_map[key]

    # Bez clippingu: żeby marginesy (płeć × wiek) trafiały w target
    # Normalizacja: średnia waga = 1 (skaluje wszystkie wagi tym samym mnożnikiem)
    w_sum = float(w.sum())
    if w_sum > 0:
        w = w * (len(w) / w_sum)

    diag["plec"] = diag["M_PLEC"].map(lambda x: METRY_DEFS["M_PLEC"].get(int(x), str(x)))
    diag["wiek"] = diag["M_WIEK"].map(lambda x: METRY_DEFS["M_WIEK"].get(int(x), str(x)))

    diag = diag[["plec", "wiek", "udzial_docelowy", "udzial_proby", "mnoznik"]].copy()
    diag["udzial_docelowy"] = (diag["udzial_docelowy"] * 100.0).round(2)
    diag["udzial_proby"] = (diag["udzial_proby"] * 100.0).round(2)
    diag["mnoznik"] = diag["mnoznik"].round(4)

    return w, diag


def encode_pair_response(response_value: Any, side: str) -> float:
    """
    Kodowanie odpowiedzi 1-7 do punktów po stronie archetypu.
    left:  points_left  = 4 - r
    right: points_right = r - 4
    """
    v = _safe_float(response_value)
    if v is None:
        return float("nan")
    v = float(v)
    if not np.isfinite(v):
        return float("nan")
    if v < float(A_SCALE_MIN) or v > float(A_SCALE_MAX):
        return float("nan")

    side_norm = str(side or "").strip().lower()
    if side_norm == "left":
        return float(A_SCALE_CENTER - v)
    if side_norm == "right":
        return float(v - A_SCALE_CENTER)
    raise ValueError(f"Nieznana strona pary: {side}")


def _map_poststrat_error_reason(raw_error: str) -> str:
    txt = str(raw_error or "").strip().lower()
    if not txt:
        return "Nie udało się stabilnie wyznaczyć wag"
    if ("targets_poststrat.csv musi zawierać kolumny" in txt) or ("brakuje kolumn" in txt):
        return "Brak wymaganych zmiennych do wagowania"
    if "brak poprawnie rozpoznanej płci / wieku" in txt:
        return "Brak wymaganych zmiennych do wagowania"
    if "brakuje komórek płeć × wiek" in txt:
        return "Zbyt mała liczebność próby"
    if ("nie zawiera poprawnych" in txt) or ("suma udziałów" in txt):
        return "Brak targetów do wagowania"
    if "stabil" in txt:
        return "Nie udało się stabilnie wyznaczyć wag"
    return "Nie udało się stabilnie wyznaczyć wag"


def resolve_active_weighting_basis(
        root: Path,
        n_rows: int,
        weights: np.ndarray,
        poststrat_diag: Optional[pd.DataFrame],
        poststrat_error: str = ""
) -> Dict[str, Any]:
    """
    Ustala aktywną podstawę danych dla nowej sekcji:
    - weighted_poststrat (gdy poststratyfikacja działa i jest stabilna)
    - raw_unweighted (fallback)
    """
    n = int(max(0, n_rows))
    w = np.asarray(weights, dtype=float).reshape(-1)
    has_poststrat = poststrat_diag is not None and len(poststrat_diag) > 0
    target_exists = (Path(root) / "targets_poststrat.csv").exists()
    invalid_weight_mask = (~np.isfinite(w)) | (w <= 0)

    if (
            has_poststrat
            and len(w) == n
            and (not np.any(invalid_weight_mask))
            and float(np.sum(w)) > 0
    ):
        return {
            "weighting_applied_flag": True,
            "data_basis_status": "weighted_poststrat",
            "data_basis_label": "Podstawa prezentacji wyników: dane ważone poststratyfikacyjnie.",
            "data_basis_reason": "",
            "active_weight_col": "__active_weight_poststrat__",
            "weighted": True,
            "active_weights": w.copy(),
        }

    if has_poststrat and len(w) != n:
        reason = "Nie udało się stabilnie wyznaczyć wag (niezgodna długość wektora wag)."
    elif has_poststrat and np.any(invalid_weight_mask):
        reason = "Nie udało się stabilnie wyznaczyć wag (wykryto wagi <= 0 lub NaN)."
    elif str(poststrat_error or "").strip():
        reason = _map_poststrat_error_reason(poststrat_error)
    elif not target_exists:
        reason = "Brak targetów do wagowania"
    else:
        reason = "Wagowanie poststratyfikacyjne nie zostało zastosowane"

    return {
        "weighting_applied_flag": False,
        "data_basis_status": "raw_unweighted",
        "data_basis_label": (
            "Podstawa prezentacji wyników: dane surowe. "
            "Wagowanie poststratyfikacyjne nie zostało zastosowane."
        ),
        "data_basis_reason": reason,
        "active_weight_col": "",
        "weighted": False,
        "active_weights": np.ones(n, dtype=float),
    }


def get_weighting_status_message(weighting_meta: Dict[str, Any]) -> str:
    d = weighting_meta or {}
    label = str(d.get("data_basis_label", "")).strip()
    if label:
        return label
    status = str(d.get("data_basis_status", "raw_unweighted")).strip()
    if status == "weighted_poststrat":
        return "Podstawa prezentacji wyników: dane ważone poststratyfikacyjnie."
    return "Podstawa prezentacji wyników: dane surowe. Wagowanie poststratyfikacyjne nie zostało zastosowane."


def _strict_positive_weights(weights_arr: np.ndarray, *, context: str) -> np.ndarray:
    w = np.asarray(weights_arr, dtype=float).reshape(-1)
    bad = (~np.isfinite(w)) | (w <= 0)
    if np.any(bad):
        bad_n = int(np.sum(bad))
        raise ValueError(
            f"Niepoprawne wagi w kontekście '{context}': {bad_n} rekordów ma wagę <= 0 lub NaN."
        )
    return w


def _validate_pair_map(pair_map: List[Dict[str, str]]) -> None:
    if len(pair_map) != 18:
        raise ValueError("PAIR_MAP musi zawierać dokładnie 18 par.")
    required_keys = {"id", "col", "left", "right"}
    counts: Dict[str, int] = {}
    seen_ids: set = set()
    for row in pair_map:
        if set(row.keys()) != required_keys:
            raise ValueError("Każdy wpis PAIR_MAP musi mieć klucze: id, col, left, right.")
        pid = str(row["id"])
        if pid in seen_ids:
            raise ValueError(f"Duplikat ID pary w PAIR_MAP: {pid}")
        seen_ids.add(pid)
        left = str(row["left"])
        right = str(row["right"])
        counts[left] = int(counts.get(left, 0)) + 1
        counts[right] = int(counts.get(right, 0)) + 1

    bad = {k: v for k, v in counts.items() if int(v) != 3}
    if bad:
        raise ValueError(f"Każdy archetyp musi występować 3 razy w PAIR_MAP. Błędne: {bad}")


def build_pair_long_table(
        df: pd.DataFrame,
        pair_map: List[Dict[str, str]],
        respondent_id_col: str,
        weight_col: Optional[str] = None
) -> pd.DataFrame:
    _validate_pair_map(pair_map)

    if respondent_id_col not in df.columns:
        raise ValueError(f"Brak kolumny respondent_id: {respondent_id_col}")

    n = int(len(df))
    respondent_ids = df[respondent_id_col].copy()
    respondent_row_index = np.arange(n, dtype=int)

    if weight_col and (weight_col in df.columns):
        w_raw = pd.to_numeric(df[weight_col], errors="coerce").to_numpy(dtype=float)
        w = _strict_positive_weights(w_raw, context=f"build_pair_long_table:{weight_col}")
    else:
        w = np.ones(n, dtype=float)

    parts: List[pd.DataFrame] = []
    for p in pair_map:
        pair_id = str(p["id"])
        source_col = str(p["col"])
        left_arch = str(p["left"])
        right_arch = str(p["right"])

        if source_col in df.columns:
            responses = pd.to_numeric(df[source_col], errors="coerce").to_numpy(dtype=float)
        else:
            responses = np.full(n, np.nan, dtype=float)

        valid_mask = np.isfinite(responses) & (responses >= float(A_SCALE_MIN)) & (responses <= float(A_SCALE_MAX))
        points_left = np.array([encode_pair_response(v, "left") for v in responses], dtype=float)
        points_right = np.array([encode_pair_response(v, "right") for v in responses], dtype=float)

        part_left = pd.DataFrame({
            "respondent_id": respondent_ids.values,
            "respondent_row_index": respondent_row_index,
            "pair_id": pair_id,
            "source_column": source_col,
            "archetype": left_arch,
            "side": "left",
            "response_1_7": responses,
            "points": points_left,
            "valid_flag": valid_mask.astype(bool),
            "weight": w,
        })
        part_right = pd.DataFrame({
            "respondent_id": respondent_ids.values,
            "respondent_row_index": respondent_row_index,
            "pair_id": pair_id,
            "source_column": source_col,
            "archetype": right_arch,
            "side": "right",
            "response_1_7": responses,
            "points": points_right,
            "valid_flag": valid_mask.astype(bool),
            "weight": w,
        })
        parts.extend([part_left, part_right])

    if not parts:
        return pd.DataFrame(columns=[
            "respondent_id", "respondent_row_index", "pair_id", "source_column", "archetype",
            "side", "response_1_7", "points", "valid_flag", "weight"
        ])

    long_df = pd.concat(parts, axis=0, ignore_index=True)

    # Kontrola 1: points_left + points_right == 0 dla każdej ważnej odpowiedzi
    m_valid = long_df["valid_flag"].astype(bool).values
    if np.any(m_valid):
        chk = (
            long_df.loc[m_valid]
            .groupby(["respondent_row_index", "pair_id"], dropna=False)["points"]
            .sum()
            .astype(float)
            .values
        )
        if chk.size and (not np.allclose(chk, 0.0, atol=1e-9, rtol=0.0)):
            raise ValueError("Walidacja nie przeszła: dla części odpowiedzi points_left + points_right != 0.")

    return long_df


def compute_respondent_archetype_scores(long_table: pd.DataFrame) -> pd.DataFrame:
    if long_table is None or len(long_table) == 0:
        return pd.DataFrame(columns=[
            "respondent_row_index", "respondent_id", "archetype",
            "n_valid_pairs", "score_sum", "score_mean", "weight"
        ])

    valid = long_table[long_table["valid_flag"].astype(bool)].copy()
    if valid.empty:
        return pd.DataFrame(columns=[
            "respondent_row_index", "respondent_id", "archetype",
            "n_valid_pairs", "score_sum", "score_mean", "weight"
        ])

    grp = (
        valid
        .groupby(["respondent_row_index", "respondent_id", "archetype"], as_index=False)
        .agg(
            n_valid_pairs=("points", "count"),
            score_sum=("points", "sum"),
            weight=("weight", "first"),
        )
    )

    grp["n_valid_pairs"] = grp["n_valid_pairs"].astype(int)
    grp["score_sum"] = grp["score_sum"].astype(float)
    grp["score_mean"] = np.where(
        grp["n_valid_pairs"].values > 0,
        grp["score_sum"].values / grp["n_valid_pairs"].values,
        np.nan
    )

    return grp


def classify_respondent_archetype_support(scores_table: pd.DataFrame) -> pd.DataFrame:
    if scores_table is None or len(scores_table) == 0:
        return pd.DataFrame(columns=[
            "respondent_row_index", "respondent_id", "archetype", "n_valid_pairs",
            "score_sum", "score_mean", "weight",
            "expected_flag", "neutral_flag", "not_expected_flag", "strong_expected_flag"
        ])

    d = scores_table.copy()
    s = pd.to_numeric(d["score_mean"], errors="coerce").astype(float)
    d["expected_flag"] = (s > 0).astype(int)
    d["neutral_flag"] = (s == 0).astype(int)
    d["not_expected_flag"] = (s < 0).astype(int)
    d["strong_expected_flag"] = (s >= 1).astype(int)
    return d


def _weighted_or_unweighted_mean(values: np.ndarray, weights: np.ndarray, weighted: bool) -> float:
    v = np.asarray(values, dtype=float).reshape(-1)
    if v.size == 0:
        return float("nan")
    m = np.isfinite(v)
    if not np.any(m):
        return float("nan")
    if weighted:
        w = np.asarray(weights, dtype=float).reshape(-1)
        if len(w) != len(v):
            raise ValueError("Niezgodna długość wag i wartości w średniej ważonej.")
        w = _strict_positive_weights(w, context="_weighted_or_unweighted_mean")
        return float(np.average(v[m], weights=w[m]))
    return float(np.mean(v[m]))


def aggregate_archetype_support(
        scores_table: pd.DataFrame,
        weight_col: Optional[str] = None,
        weighted: bool = False
) -> pd.DataFrame:
    if scores_table is None or len(scores_table) == 0:
        return pd.DataFrame(columns=[
            "archetype", "expected_pct", "neutral_pct", "not_expected_pct", "strong_expected_pct",
            "n_respondents_valid", "avg_n_valid_pairs", "weighted_base"
        ])

    rows: List[Dict[str, Any]] = []
    for archetype, grp in scores_table.groupby("archetype", dropna=False):
        n_resp = int(len(grp))
        if n_resp <= 0:
            continue

        if weighted and weight_col and (weight_col in grp.columns):
            w_raw = pd.to_numeric(grp[weight_col], errors="coerce").to_numpy(dtype=float)
            w = _strict_positive_weights(w_raw, context=f"aggregate_archetype_support:{archetype}")
        else:
            w = np.ones(n_resp, dtype=float)

        denom = float(np.sum(w)) if weighted else float(n_resp)
        if denom <= 0:
            continue

        exp = float(np.sum(w * grp["expected_flag"].to_numpy(dtype=float)) / denom * 100.0)
        neu = float(np.sum(w * grp["neutral_flag"].to_numpy(dtype=float)) / denom * 100.0)
        not_exp = float(np.sum(w * grp["not_expected_flag"].to_numpy(dtype=float)) / denom * 100.0)
        strong = float(np.sum(w * grp["strong_expected_flag"].to_numpy(dtype=float)) / denom * 100.0)

        rows.append({
            "archetype": str(archetype),
            "expected_pct": exp,
            "neutral_pct": neu,
            "not_expected_pct": not_exp,
            "strong_expected_pct": strong,
            "n_respondents_valid": n_resp,
            "avg_n_valid_pairs": float(np.mean(pd.to_numeric(grp["n_valid_pairs"], errors="coerce").fillna(0.0))),
            "weighted_base": float(np.sum(w)),
        })

    out = pd.DataFrame(rows)
    if out.empty:
        return out

    # Kontrola 2: expected + neutral + not_expected = 100
    check_sum = (
        out["expected_pct"].astype(float)
        + out["neutral_pct"].astype(float)
        + out["not_expected_pct"].astype(float)
    )
    if not np.allclose(check_sum.values, 100.0, atol=1e-8, rtol=0.0):
        raise ValueError("Walidacja nie przeszła: expected_pct + neutral_pct + not_expected_pct != 100.")

    return out


def compute_ioa(
        scores_table: pd.DataFrame,
        weight_col: Optional[str] = None,
        weighted: bool = False
) -> pd.DataFrame:
    if scores_table is None or len(scores_table) == 0:
        return pd.DataFrame(columns=["archetype", "ioa_raw", "ioa_100"])

    rows: List[Dict[str, Any]] = []
    for archetype, grp in scores_table.groupby("archetype", dropna=False):
        if len(grp) <= 0:
            continue
        s = pd.to_numeric(grp["score_mean"], errors="coerce").to_numpy(dtype=float)

        if weighted and weight_col and (weight_col in grp.columns):
            w_raw = pd.to_numeric(grp[weight_col], errors="coerce").to_numpy(dtype=float)
            w = _strict_positive_weights(w_raw, context=f"compute_ioa:{archetype}")
        else:
            w = np.ones(len(grp), dtype=float)

        ioa_raw = _weighted_or_unweighted_mean(s, w, weighted=weighted)
        ioa_100 = float(((ioa_raw + 3.0) / 6.0) * 100.0) if np.isfinite(ioa_raw) else float("nan")

        rows.append({
            "archetype": str(archetype),
            "ioa_raw": float(ioa_raw) if np.isfinite(ioa_raw) else float("nan"),
            "ioa_100": float(ioa_100) if np.isfinite(ioa_100) else float("nan"),
        })

    return pd.DataFrame(rows)


def compute_top3_share(df_b1: pd.DataFrame, arch_names: List[str] = ARCHETYPES) -> Dict[str, float]:
    out = {str(a): float("nan") for a in arch_names}
    if df_b1 is None or len(df_b1) == 0:
        return out
    tmp = df_b1.copy()
    tmp["archetyp"] = tmp.get("archetyp", "").astype(str)
    tmp["%"] = pd.to_numeric(tmp.get("%", np.nan), errors="coerce")
    for a in arch_names:
        row = tmp[tmp["archetyp"] == str(a)]
        if len(row) > 0:
            out[str(a)] = float(row.iloc[0]["%"])
    return out


def compute_top1_share(df_b2: pd.DataFrame, arch_names: List[str] = ARCHETYPES) -> Dict[str, float]:
    out = {str(a): float("nan") for a in arch_names}
    if df_b2 is None or len(df_b2) == 0:
        return out
    tmp = df_b2.copy()
    tmp["archetyp"] = tmp.get("archetyp", "").astype(str)
    tmp["%"] = pd.to_numeric(tmp.get("%", np.nan), errors="coerce")
    for a in arch_names:
        row = tmp[tmp["archetyp"] == str(a)]
        if len(row) > 0:
            out[str(a)] = float(row.iloc[0]["%"])
    return out


def compute_negative_experience_share(df_d12: pd.DataFrame, arch_names: List[str] = ARCHETYPES) -> Dict[str, float]:
    out = {str(a): float("nan") for a in arch_names}
    if df_d12 is None or len(df_d12) == 0:
        return out
    tmp = df_d12.copy()
    tmp["archetyp"] = tmp.get("archetyp", "").astype(str)
    tmp["%MINUS"] = pd.to_numeric(tmp.get("%MINUS", np.nan), errors="coerce")
    for a in arch_names:
        row = tmp[tmp["archetyp"] == str(a)]
        if len(row) > 0:
            out[str(a)] = float(row.iloc[0]["%MINUS"])
    return out


def compute_most_important_experience_balance(
        d12: np.ndarray,
        d13: np.ndarray,
        weights: np.ndarray,
        arch_names: List[str] = ARCHETYPES,
) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, float], float]:
    n_arch = len(arch_names)
    out_mbal = {str(a): float("nan") for a in arch_names}
    out_mneg = {str(a): float("nan") for a in arch_names}
    out_mpos = {str(a): float("nan") for a in arch_names}

    d12_arr = np.asarray(d12, dtype=float)
    d13_arr = np.asarray(d13, dtype=int).reshape(-1)
    w = np.asarray(weights, dtype=float).reshape(-1)
    if d12_arr.shape[0] == 0 or d13_arr.shape[0] == 0 or w.shape[0] == 0:
        return out_mbal, out_mneg, out_mpos, 0.0

    n = min(d12_arr.shape[0], d13_arr.shape[0], w.shape[0])
    d12_arr = d12_arr[:n, :]
    d13_arr = d13_arr[:n]
    w = w[:n]
    valid_d13 = (d13_arr >= 0) & np.isfinite(w) & (w > 0)
    denom = float(np.sum(w[valid_d13])) if np.any(valid_d13) else 0.0
    if denom <= 0:
        return out_mbal, out_mneg, out_mpos, 0.0

    for idx, a in enumerate(arch_names):
        if idx >= d12_arr.shape[1]:
            continue
        col = np.asarray(d12_arr[:, idx], dtype=float)
        base = valid_d13 & (d13_arr == idx) & np.isfinite(col)
        w_base = float(np.sum(w[base])) if np.any(base) else 0.0
        if w_base <= 0:
            out_mneg[str(a)] = 0.0
            out_mpos[str(a)] = 0.0
            out_mbal[str(a)] = 0.0
            continue
        mneg = float(np.sum(w[base & (col < 0)]) / denom * 100.0)
        mpos = float(np.sum(w[base & (col > 0)]) / denom * 100.0)
        out_mneg[str(a)] = mneg
        out_mpos[str(a)] = mpos
        out_mbal[str(a)] = float(mneg - mpos)
    return out_mbal, out_mneg, out_mpos, denom


def safe_zscore_by_archetype(
        values: Dict[str, float],
        arch_names: List[str] = ARCHETYPES
) -> Tuple[Dict[str, float], float, float]:
    vals = [float(values.get(str(a), np.nan)) for a in arch_names]
    finite_vals = np.asarray([v for v in vals if np.isfinite(v)], dtype=float)
    if finite_vals.size < 2:
        return {str(a): 0.0 for a in arch_names}, float("nan"), 0.0
    mean_v = float(np.mean(finite_vals))
    std_v = float(np.std(finite_vals, ddof=0))
    if (not np.isfinite(std_v)) or std_v <= 1e-12:
        return {str(a): 0.0 for a in arch_names}, mean_v, 0.0
    out = {}
    for a in arch_names:
        v = float(values.get(str(a), np.nan))
        out[str(a)] = float((v - mean_v) / std_v) if np.isfinite(v) else 0.0
    return out, mean_v, std_v


def compute_variant_b_correction(
        b1_pct: Dict[str, float],
        b2_pct: Dict[str, float],
        n_pct: Dict[str, float],
        mbal_pp: Dict[str, float],
        arch_names: List[str] = ARCHETYPES
) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, float], Dict[str, float]]:
    delta_b1: Dict[str, float] = {}
    delta_b2: Dict[str, float] = {}
    delta_n: Dict[str, float] = {}
    k_b: Dict[str, float] = {}
    b2_neutral = 8.3333333333
    for a in arch_names:
        key = str(a)
        b1 = float(b1_pct.get(key, np.nan))
        b2 = float(b2_pct.get(key, np.nan))
        n = float(n_pct.get(key, np.nan))
        mbal = float(mbal_pp.get(key, np.nan))
        d_b1 = (b1 - 25.0) if np.isfinite(b1) else 0.0
        d_b2 = (b2 - b2_neutral) if np.isfinite(b2) else 0.0
        d_n = (n - 50.0) if np.isfinite(n) else 0.0
        mbal_safe = mbal if np.isfinite(mbal) else 0.0
        corr = float(0.35 * d_b1 + 0.90 * d_b2 + 0.08 * d_n + 0.20 * mbal_safe)
        delta_b1[key] = float(d_b1)
        delta_b2[key] = float(d_b2)
        delta_n[key] = float(d_n)
        k_b[key] = corr
    return delta_b1, delta_b2, delta_n, k_b


def compute_social_expectation_variant_b(
        a_pct: Dict[str, float],
        b1_pct: Dict[str, float],
        b2_pct: Dict[str, float],
        n_pct: Dict[str, float],
        mbal_pp: Dict[str, float],
        arch_names: List[str] = ARCHETYPES
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    delta_b1, delta_b2, delta_n, k_b = compute_variant_b_correction(
        b1_pct=b1_pct,
        b2_pct=b2_pct,
        n_pct=n_pct,
        mbal_pp=mbal_pp,
        arch_names=arch_names,
    )
    raw = {}
    scaled = {}
    for a in arch_names:
        key = str(a)
        aval = float(a_pct.get(key, np.nan))
        if np.isfinite(aval):
            raw_val = float(aval + float(k_b.get(key, 0.0)))
            raw[key] = raw_val
            scaled[key] = float(np.clip(raw_val, 0.0, 100.0))
        else:
            raw[key] = float("nan")
            scaled[key] = float("nan")

    rows = []
    for a in arch_names:
        key = str(a)
        rows.append({
            "archetype": key,
            "A_pct": float(a_pct.get(key, np.nan)),
            "B1_pct": float(b1_pct.get(key, np.nan)),
            "B2_pct": float(b2_pct.get(key, np.nan)),
            "N_pct": float(n_pct.get(key, np.nan)),
            "MBAL_pp": float(mbal_pp.get(key, np.nan)),
            "delta_B1": float(delta_b1.get(key, 0.0)),
            "delta_B2": float(delta_b2.get(key, 0.0)),
            "delta_N": float(delta_n.get(key, 0.0)),
            "K_B": float(k_b.get(key, 0.0)),
            "SEI_B": float(raw.get(key, np.nan)),
            "SEI_100": float(scaled.get(key, np.nan)),
        })
    out = pd.DataFrame(rows)
    out = out.sort_values(["SEI_100", "SEI_B"], ascending=[False, False], kind="mergesort", na_position="last").reset_index(drop=True)
    out.insert(0, "position", np.arange(1, len(out) + 1, dtype=int))

    meta = {
        "anchor_formula": "A_base = % oczekujących z pytania A",
        "delta_formula": "delta_B1=B1-25.0; delta_B2=B2-8.3333333333; delta_N=N-50.0; MBAL=Mneg-Mpos",
        "corr_formula": "K_B = 0.35*delta_B1 + 0.90*delta_B2 + 0.08*delta_N + 0.20*MBAL",
        "raw_formula": "SEI_B = A_base + K_B",
        "scale_formula": "SEI_B_100 = clamp(SEI_B, 0..100)",
    }
    return out, meta


def compute_social_expectation_index(
        a_pct: Dict[str, float],
        b1_pct: Dict[str, float],
        b2_pct: Dict[str, float],
        n_pct: Dict[str, float],
        mbal_pp: Dict[str, float],
        arch_names: List[str] = ARCHETYPES
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    return compute_social_expectation_variant_b(
        a_pct=a_pct,
        b1_pct=b1_pct,
        b2_pct=b2_pct,
        n_pct=n_pct,
        mbal_pp=mbal_pp,
        arch_names=arch_names,
    )


def build_main_expectation_table(summary_table: pd.DataFrame) -> pd.DataFrame:
    if summary_table is None or len(summary_table) == 0:
        return pd.DataFrame(columns=[
            "position", "archetype", "expected_pct", "neutral_pct", "not_expected_pct",
            "strong_expected_pct", "ioa_100", "ioa_raw", "n_respondents_valid", "avg_n_valid_pairs"
        ])

    d = summary_table.copy()
    d = d[pd.to_numeric(d["n_respondents_valid"], errors="coerce").fillna(0).astype(int) > 0].copy()
    if d.empty:
        return d

    d = d.sort_values(
        ["expected_pct", "ioa_100", "ioa_raw"],
        ascending=[False, False, False],
        kind="mergesort"
    ).reset_index(drop=True)
    d.insert(0, "position", np.arange(1, len(d) + 1, dtype=int))
    return d


def build_pair_detail_table(
        long_table: pd.DataFrame,
        weighted: bool = False,
        weight_col: Optional[str] = None
) -> pd.DataFrame:
    _ = weight_col  # long_table zawiera już gotową kolumnę "weight"

    if long_table is None or len(long_table) == 0:
        return pd.DataFrame(columns=[
            "pair_id", "left_archetype", "right_archetype", "mean_response_1_7",
            "pct_response_1_3", "pct_response_4", "pct_response_5_7",
            "mean_points_left", "mean_points_right", "n"
        ])

    valid = long_table[long_table["valid_flag"].astype(bool)].copy()
    if valid.empty:
        return pd.DataFrame(columns=[
            "pair_id", "left_archetype", "right_archetype", "mean_response_1_7",
            "pct_response_1_3", "pct_response_4", "pct_response_5_7",
            "mean_points_left", "mean_points_right", "n"
        ])

    left = valid.loc[valid["side"] == "left", [
        "respondent_row_index", "pair_id", "source_column", "archetype", "response_1_7", "points", "weight"
    ]].rename(columns={"archetype": "left_archetype", "points": "points_left"})
    right = valid.loc[valid["side"] == "right", [
        "respondent_row_index", "pair_id", "archetype", "points"
    ]].rename(columns={"archetype": "right_archetype", "points": "points_right"})

    pair_resp = left.merge(
        right,
        how="inner",
        on=["respondent_row_index", "pair_id"],
    )

    rows: List[Dict[str, Any]] = []
    for p in PAIR_MAP:
        pid = str(p["id"])
        g = pair_resp[pair_resp["pair_id"] == pid].copy()

        n_valid = int(len(g))
        if n_valid <= 0:
            rows.append({
                "pair_id": pid,
                "left_archetype": str(p["left"]),
                "right_archetype": str(p["right"]),
                "mean_response_1_7": np.nan,
                "pct_response_1_3": np.nan,
                "pct_response_4": np.nan,
                "pct_response_5_7": np.nan,
                "mean_points_left": np.nan,
                "mean_points_right": np.nan,
                "n": 0,
            })
            continue

        r = pd.to_numeric(g["response_1_7"], errors="coerce").to_numpy(dtype=float)
        pl = pd.to_numeric(g["points_left"], errors="coerce").to_numpy(dtype=float)
        pr = pd.to_numeric(g["points_right"], errors="coerce").to_numpy(dtype=float)
        if weighted:
            w_raw = pd.to_numeric(g["weight"], errors="coerce").to_numpy(dtype=float)
            w = _strict_positive_weights(w_raw, context=f"build_pair_detail_table:{pid}")
        else:
            w = np.ones(n_valid, dtype=float)

        denom = float(np.sum(w)) if weighted else float(n_valid)
        if denom <= 0:
            raise ValueError(f"Niepoprawna podstawa wag dla pary {pid}: suma wag <= 0.")

        pct_1_3 = float(np.sum(w[(r >= 1.0) & (r <= 3.0)]) / denom * 100.0)
        pct_4 = float(np.sum(w[r == 4.0]) / denom * 100.0)
        pct_5_7 = float(np.sum(w[(r >= 5.0) & (r <= 7.0)]) / denom * 100.0)

        mean_r = float(np.average(r, weights=w))
        mean_pl = float(np.average(pl, weights=w))
        mean_pr = float(np.average(pr, weights=w))

        rows.append({
            "pair_id": pid,
            "left_archetype": str(p["left"]),
            "right_archetype": str(p["right"]),
            "mean_response_1_7": mean_r,
            "pct_response_1_3": pct_1_3,
            "pct_response_4": pct_4,
            "pct_response_5_7": pct_5_7,
            "mean_points_left": mean_pl,
            "mean_points_right": mean_pr,
            "n": n_valid,
        })

    out = pd.DataFrame(rows)
    if out.empty:
        return out
    out["_pair_ord"] = out["pair_id"].astype(str).str.extract(r"(\d+)").astype(float)
    out = out.sort_values("_pair_ord", ascending=True).drop(columns=["_pair_ord"]).reset_index(drop=True)
    return out


def render_archetype_expectation_section(
        *,
        methodology_text_arche: str,
        methodology_text_values: str,
        data_basis_message: str,
        data_basis_reason: str,
        summary_block_html: str,
        main_table_html: str,
        pair_detail_table_html: str,
        balance_chart_html: str,
        expected_chart_html: str,
        ioa_chart_html: str
) -> str:
    reason_html = ""
    if str(data_basis_reason or "").strip():
        reason_html = (
            "<div class='small' style='margin-top:6px;'>"
            f"Powód fallbacku: {_html_escape(str(data_basis_reason).strip())}"
            "</div>"
        )

    return f"""
  <div class="panel pI">
    <h2><span class="mode-arche">Profil Preferencji Przywództwa (PPP)</span><span class="mode-values">Profil Preferencji Przywództwa (PPP)</span></h2>
    <div class="small">
      <span class="mode-arche">{_html_escape(methodology_text_arche)}</span><span class="mode-values">{_html_escape(methodology_text_values)}</span>
    </div>

    <div class="card ioa-status-card">
      <div><b>{_html_escape(data_basis_message)}</b></div>
      {reason_html}
    </div>

    <div class="chart-pair" style="margin-top:16px;">
      <div class="card" style="margin-top:0;">
        <h3><span class="mode-arche">Społeczne oczekiwanie archetypu (%)</span><span class="mode-values">Społeczne oczekiwanie wartości (%)</span></h3>
        {expected_chart_html}
      </div>
      <div class="card" style="margin-top:0;">
        <h3><span class="mode-arche">PPP 0-100</span><span class="mode-values">PPP 0-100</span></h3>
        {ioa_chart_html}
      </div>
    </div>

    <div class="card ioa-summary-card" style="margin-top:16px;">
      <h3>Podsumowanie</h3>
      {summary_block_html}
    </div>

    <div class="card chart-half ioa-balance-legend" style="margin-top:16px;">
      <div class="small" style="margin-bottom:6px;"><b><span class="mode-arche">Interpretacja bilansu respondenta dla archetypu</span><span class="mode-values">Interpretacja bilansu respondenta dla wartości</span></b></div>
      <div class="ioa-balance-row">
        <span class="ioa-pill ioa-pill-pos"><span class="mode-arche">Dodatni bilans → oczekiwanie archetypu</span><span class="mode-values">Dodatni bilans → oczekiwanie wartości</span></span>
        <span class="ioa-pill ioa-pill-neu">Bilans zerowy → neutralność</span>
        <span class="ioa-pill ioa-pill-neg"><span class="mode-arche">Ujemny bilans → relatywny brak oczekiwania archetypu</span><span class="mode-values">Ujemny bilans → relatywny brak oczekiwania wartości</span></span>
      </div>
      <div class="small" style="margin-top:8px;">
        <span class="mode-arche">Interpretacja dotyczy rozkładu respondentów w kategoriach: oczekujący / neutralni / nieoczekujący dla archetypu.</span><span class="mode-values">Interpretacja dotyczy rozkładu respondentów w kategoriach: oczekujący / neutralni / nieoczekujący dla wartości.</span>
      </div>
    </div>

    <div class="card chart-half ioa-balance-card" style="margin-top:16px;">
      <h3 style="margin-top:10px;"><span class="mode-arche">Bilans respondentów (oczekujący / neutralni / nieoczekujący)</span><span class="mode-values">Bilans respondentów (oczekujący / neutralni / nieoczekujący)</span></h3>
      {balance_chart_html}
    </div>

    <div class="card ioa-main-card" style="margin-top:16px;">
      <h3><span class="mode-arche">Tabela główna: oczekiwanie archetypów</span><span class="mode-values">Tabela główna: oczekiwanie wartości</span></h3>
      {main_table_html}
    </div>

    <div class="card" style="margin-top:16px;">
      <h3>Tabela szczegółowa par (18 porównań)</h3>
      {pair_detail_table_html}
    </div>
  </div>
"""


def render_isoa_isow_report_tab(
        *,
        data_basis_message: str,
        data_basis_reason: str,
        methodology_text_arche: str,
        methodology_text_values: str,
        table_html: str,
        chart_html: str,
        top_bottom_html: str,
) -> str:
    reason_html = ""
    if str(data_basis_reason or "").strip():
        reason_html = (
            "<div class='small' style='margin-top:6px;'>"
            f"Powód fallbacku: {_html_escape(str(data_basis_reason).strip())}"
            "</div>"
        )
    return f"""
  <div class="panel pW">
    <h2>
      <span class="mode-arche">Indeks Społecznego Oczekiwania Archetypu (ISOA)</span>
      <span class="mode-values">Indeks Społecznego Oczekiwania Wartości (ISOW)</span>
    </h2>
    <div class="small">
      <span class="mode-arche">{_html_escape(methodology_text_arche)}</span>
      <span class="mode-values">{_html_escape(methodology_text_values)}</span>
    </div>

    <div class="card ioa-status-card">
      <div><b>{_html_escape(data_basis_message)}</b></div>
      {reason_html}
    </div>

    <div class="card ioa-howto" style="margin-top:16px;">
      <h3>Jak czytać wskaźnik</h3>
      <ul style="margin:8px 0 0 18px;">
        <li><span class="mode-arche">Wysoki ISOA oznacza, że archetyp jest społecznie mocno oczekiwany w całym badaniu.</span><span class="mode-values">Wysoki ISOW oznacza, że wartość jest społecznie mocno oczekiwana w całym badaniu.</span></li>
        <li>Wysokie A + B2 oznacza szerokie oczekiwanie i wyraźny priorytet.</li>
        <li>C13/D13 działa jako umiarkowana korekta doświadczeniowa (nie dominuje rdzenia).</li>
        <li>Skala 0-100 jest indeksem syntetycznym, a nie odsetkiem respondentów.</li>
      </ul>
    </div>

    <div class="card chart-half" style="margin-top:16px;">
      <h3><span class="mode-arche">Wykres główny ISOA (0-100)</span><span class="mode-values">Wykres główny ISOW (0-100)</span></h3>
      <div class="isoa-wheel-wrap">{chart_html}</div>
      <div class="isoa-axis-legend">
        <span><i style="background:#e53935"></i>Zmiana</span>
        <span><i style="background:#1e88e5"></i>Ludzie</span>
        <span><i style="background:#2e7d32"></i>Porządek</span>
        <span><i style="background:#7e57c2"></i>Niezależność</span>
      </div>
    </div>

    <div class="card ioa-summary-card" style="margin-top:16px;">
      <h3>Top 3 / Bottom 3</h3>
      {top_bottom_html}
    </div>

    <div class="card ioa-main-card" style="margin-top:16px;">
      <h3><span class="mode-arche">Tabela główna ISOA</span><span class="mode-values">Tabela główna ISOW</span></h3>
      {table_html}
    </div>
  </div>
"""


def _run_manual_expectation_examples_validation() -> pd.DataFrame:
    examples = [
        ("Przykład A", [3, 2, 1], {"expected_flag": 1, "neutral_flag": 0, "not_expected_flag": 0, "strong_expected_flag": 1}),
        ("Przykład B", [-3, 0, 3], {"expected_flag": 0, "neutral_flag": 1, "not_expected_flag": 0, "strong_expected_flag": 0}),
        ("Przykład C", [-1, -2, 0], {"expected_flag": 0, "neutral_flag": 0, "not_expected_flag": 1, "strong_expected_flag": 0}),
        ("Przykład D", [1, 1, 1], {"expected_flag": 1, "neutral_flag": 0, "not_expected_flag": 0, "strong_expected_flag": 1}),
    ]

    rows: List[Dict[str, Any]] = []
    for case_name, pts, expected in examples:
        arr = np.asarray(pts, dtype=float).reshape(-1)
        score_mean = float(np.mean(arr)) if arr.size else float("nan")
        got = {
            "expected_flag": int(score_mean > 0),
            "neutral_flag": int(score_mean == 0),
            "not_expected_flag": int(score_mean < 0),
            "strong_expected_flag": int(score_mean >= 1),
        }
        ok = all(int(got[k]) == int(v) for k, v in expected.items())
        rows.append({
            "przyklad": case_name,
            "punkty": ", ".join(str(int(x)) for x in pts),
            "score_mean": score_mean,
            "expected_flag": got["expected_flag"],
            "neutral_flag": got["neutral_flag"],
            "not_expected_flag": got["not_expected_flag"],
            "strong_expected_flag": got["strong_expected_flag"],
            "walidacja_ok": bool(ok),
        })

    out = pd.DataFrame(rows)
    if not out.empty and not bool(out["walidacja_ok"].all()):
        raise ValueError("Walidacja ręcznych przykładów sekcji oczekiwań nie przeszła.")
    return out


def A_pair_stats(A: np.ndarray, weights: np.ndarray) -> pd.DataFrame:
    rows = []
    for j, (qid, left_arch, right_arch) in enumerate(A_PAIRS):
        col = A[:, j].astype(float)
        m = np.isfinite(col)
        if not np.any(m):
            rows.append({
                "item": qid,
                "lewy": left_arch,
                "prawy": right_arch,
                "liczba": 0,
                "%_lewy": 0.0,
                "%_neutral": 0.0,
                "%_prawy": 0.0,
                "mean_sign": 0.0,
                "winner": "",
            })
            continue

        w = weights[m].astype(float)
        sw = float(np.sum(w))
        if sw <= 0:
            sw = float(m.sum())
            w = np.ones(int(m.sum()), dtype=float)

        x = col[m]
        left_w = float(np.sum(w[x < 4]))
        neutral_w = float(np.sum(w[x == 4]))
        right_w = float(np.sum(w[x > 4]))

        pct_left = (left_w / sw) * 100.0
        pct_neutral = (neutral_w / sw) * 100.0
        pct_right = (right_w / sw) * 100.0

        # mean_sign: średnia pozycja względem 4 (ujemne = lewo, dodatnie = prawo)
        mean_val = float(np.sum(w * x) / sw)
        mean_signed = float(mean_val - 4.0)

        # Winner: brak zwycięzcy przy remisie / bardzo blisko remisu
        if abs(mean_signed) < 0.15:
            winner = "remis"
        elif mean_signed < 0:
            winner = left_arch
        else:
            winner = right_arch

        rows.append({
            "item": qid,
            "lewy": left_arch,
            "prawy": right_arch,
            "liczba": int(m.sum()),
            "%_lewy": pct_left,
            "%_neutral": pct_neutral,
            "%_prawy": pct_right,
            "mean_sign": mean_signed,
            "winner": winner
        })

    df_out = pd.DataFrame(rows)
    if df_out.empty:
        return df_out

    # wymagane formatowanie:
    df_out["%_lewy"] = df_out["%_lewy"].astype(float).round(1)
    df_out["%_neutral"] = df_out["%_neutral"].astype(float).round(1)
    df_out["%_prawy"] = df_out["%_prawy"].astype(float).round(1)
    df_out["mean_sign"] = df_out["mean_sign"].astype(float).round(2)

    return df_out


def _a_response_to_p_right(v: int) -> float:
    # skala 1–7 => 1→0.0, 4→0.5, 7→1.0
    return (v - A_SCALE_MIN) / float(A_SCALE_MAX - A_SCALE_MIN)


# =========================
# 4) RIDGE: preferencje P z A
# =========================

def A_bradley_terry(A: np.ndarray, weights: np.ndarray, max_iter: int = 400, tol: float = 1e-7) -> pd.DataFrame:
    idx = {a: i for i, a in enumerate(ARCHETYPES)}
    K = len(ARCHETYPES)
    W = np.zeros((K, K), dtype=float)
    N = np.zeros((K, K), dtype=float)

    for j, (pid, left, right) in enumerate(A_PAIRS):
        col = A[:, j]
        m = np.isfinite(col)
        if not np.any(m):
            continue
        w = weights[m]
        v = col[m].astype(int)
        pr = np.array([_a_response_to_p_right(x) for x in v], dtype=float)
        pl = 1.0 - pr
        i = idx[left]
        k = idx[right]
        W[k, i] += float(np.sum(w * pr))
        W[i, k] += float(np.sum(w * pl))
        N[i, k] += float(np.sum(w))
        N[k, i] += float(np.sum(w))

    a = np.ones(K, dtype=float)
    eps = 1e-12
    for _ in range(max_iter):
        a_old = a.copy()
        w_i = W.sum(axis=1)
        denom = np.zeros(K, dtype=float)
        for i in range(K):
            s = 0.0
            for j in range(K):
                if i == j:
                    continue
                nij = N[i, j]
                if nij <= 0:
                    continue
                s += nij / max(a[i] + a[j], eps)
            denom[i] = max(s, eps)
        a = w_i / denom
        a = a / np.exp(np.mean(np.log(np.maximum(a, eps))))
        if np.max(np.abs(a - a_old)) < tol:
            break

    loga = np.log(np.maximum(a, eps))
    z = (loga - loga.mean()) / (loga.std(ddof=0) + 1e-12)
    bt_scaled = 50 + 10 * z

    wins = W.sum(axis=1)
    losses = W.sum(axis=0)
    net = wins - losses

    out = pd.DataFrame({
        "archetyp": ARCHETYPES,
        "BT_scaled": bt_scaled,
        "wins": wins,
        "losses": losses,
        "net": net,
    }).sort_values("BT_scaled", ascending=False).reset_index(drop=True)
    out["liczba_wygranych"] = out["wins"].round(0).astype(int)
    out["liczba_przegranych"] = out["losses"].round(0).astype(int)
    out = out.drop(columns=["wins", "losses"])
    return out

def A_pair_outcome_balance(A: np.ndarray, weights: np.ndarray) -> pd.DataFrame:
    """
    Liczy bilans par na poziomie całego pojedynku A:
    - dla każdej pary wyznaczamy jednego zwycięzcę na podstawie sumy głosów ważonych,
    - zwycięzca dostaje +1, przegrany -1,
    - remis daje 0 obu stronom.

    Każdy archetyp występuje w 3 parach, więc wynik mieści się w zakresie [-3, 3].
    """
    pair_wins = {a: 0 for a in ARCHETYPES}
    pair_losses = {a: 0 for a in ARCHETYPES}

    for j, (_qid, left_arch, right_arch) in enumerate(A_PAIRS):
        col = A[:, j].astype(float)
        m = np.isfinite(col)
        if not np.any(m):
            continue

        w = weights[m].astype(float)
        if float(np.sum(w)) <= 0:
            w = np.ones(int(m.sum()), dtype=float)

        x = col[m]
        left_score = float(np.sum(w[x < A_SCALE_CENTER]))
        right_score = float(np.sum(w[x > A_SCALE_CENTER]))

        if left_score > right_score:
            pair_wins[left_arch] += 1
            pair_losses[right_arch] += 1
        elif right_score > left_score:
            pair_wins[right_arch] += 1
            pair_losses[left_arch] += 1

    return pd.DataFrame({
        "archetyp": ARCHETYPES,
        "zwycięstwa w parach": [pair_wins[a] for a in ARCHETYPES],
        "przegrane w parach": [pair_losses[a] for a in ARCHETYPES],
        "zwycięstwa vs przegrane": [pair_wins[a] - pair_losses[a] for a in ARCHETYPES],
    })



def A_raw_vote_balance(A: np.ndarray) -> pd.DataFrame:
    """
    Surowy bilans starć na podstawie odpowiedzi kierunkowych (bez wag):
    - odpowiedzi < środek skali liczymy jako wygraną strony lewej,
    - odpowiedzi > środek skali liczymy jako wygraną strony prawej,
    - środek skali pomijamy.
    """
    raw_wins = {a: 0 for a in ARCHETYPES}
    raw_losses = {a: 0 for a in ARCHETYPES}

    for j, (_qid, left_arch, right_arch) in enumerate(A_PAIRS):
        col = A[:, j].astype(float)
        m = np.isfinite(col)
        if not np.any(m):
            continue

        x = col[m]
        left_cnt = int(np.sum(x < A_SCALE_CENTER))
        right_cnt = int(np.sum(x > A_SCALE_CENTER))

        raw_wins[left_arch] += left_cnt
        raw_losses[left_arch] += right_cnt
        raw_wins[right_arch] += right_cnt
        raw_losses[right_arch] += left_cnt

    return pd.DataFrame({
        "archetyp": ARCHETYPES,
        "bilans starć (surowy)": [raw_wins[a] - raw_losses[a] for a in ARCHETYPES],
    })



# =========================
# 5) B: ranking + ranking trójek
# =========================

def B_rankings(b1: np.ndarray, b2: np.ndarray, weights: np.ndarray) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    # B1: archetyp w trójce
    w = np.asarray(weights, dtype=float).reshape(-1)
    b1_f = np.nan_to_num(np.asarray(b1, dtype=float), nan=0.0)
    if b1_f.shape[0] != len(w):
        raise ValueError("Niezgodna długość B1 i wag.")

    sel_counts_w = (b1_f * w.reshape(-1, 1)).sum(axis=0)
    sel_counts_raw = (b1_f > 0.5).sum(axis=0).astype(int)
    answered_b1 = np.isfinite(np.asarray(b1, dtype=float)).any(axis=1)
    denom_b1_w = float(w[answered_b1].sum()) if np.any(answered_b1) else float(w.sum())

    df_b1 = pd.DataFrame({
        "archetyp": ARCHETYPES,
        "liczba": sel_counts_raw,
        "%": np.where(denom_b1_w > 0, (sel_counts_w / denom_b1_w) * 100.0, np.nan),
    }).sort_values("%", ascending=False).reset_index(drop=True)

    if "%" in df_b1.columns:
        df_b1["%"] = pd.to_numeric(df_b1["%"], errors="coerce").round(1)

    # B1: ranking trójek (kombinacje)
    combos_w: Dict[str, float] = {}
    combos_raw: Dict[str, int] = {}
    total_w = float(w.sum())
    for i in range(b1.shape[0]):
        picked = [ARCHETYPES[j] for j in range(len(ARCHETYPES)) if b1[i, j] > 0.5]
        if len(picked) == 0:
            continue
        picked = sorted(picked)
        key = " + ".join(picked)
        combos_w[key] = combos_w.get(key, 0.0) + float(w[i])
        combos_raw[key] = int(combos_raw.get(key, 0)) + 1
    df_tr = pd.DataFrame(
        [{
            "trójka": k,
            "liczba": int(combos_raw.get(k, 0)),
            "%": ((float(v) / total_w) * 100.0) if total_w > 0 else np.nan
        } for k, v in combos_w.items()]
    )
    if len(df_tr) == 0:
        df_tr = pd.DataFrame(columns=["trójka", "liczba", "%"])
    df_tr = df_tr.sort_values("%", ascending=False).reset_index(drop=True)
    if "%" in df_tr.columns:
        df_tr["%"] = pd.to_numeric(df_tr["%"], errors="coerce").round(1)

    # B2: najważniejszy
    counts2_w = np.zeros(len(ARCHETYPES), dtype=float)
    counts2_raw = np.zeros(len(ARCHETYPES), dtype=int)
    m = (b2 >= 0)
    idxs = np.where(m)[0]
    denom_b2_w = float(w[m].sum()) if np.any(m) else float("nan")

    for i in idxs:
        counts2_w[b2[i]] += float(w[i])
        counts2_raw[b2[i]] += 1
    df_b2 = pd.DataFrame({
        "archetyp": ARCHETYPES,
        "liczba": counts2_raw,
        "%": np.where(denom_b2_w > 0, (counts2_w / denom_b2_w) * 100.0, np.nan),
    }).sort_values("%", ascending=False).reset_index(drop=True)

    if "%" in df_b2.columns:
        df_b2["%"] = pd.to_numeric(df_b2["%"], errors="coerce").round(1)

    return df_b1, df_b2, df_tr


def B1_combo_topk(b1: np.ndarray, arch_names: List[str] = ARCHETYPES, k: int = 5) -> pd.DataFrame:
    """
    B1 – TOP k najczęstszych trójek (kombinacji) archetypów.
    Liczy tylko odpowiedzi, gdzie zaznaczono DOKŁADNIE 3 archetypy.
    Kolumny: trójka, liczba (int), % (1 miejsce)
    """
    # tylko wiersze z dokładnie 3 wyborami
    mask3 = (np.sum(b1, axis=1) == 3)
    denom = int(np.sum(mask3))
    denom = max(denom, 1)

    counts: Dict[str, int] = {}
    for row in b1[mask3]:
        idx = np.where(row == 1)[0].tolist()
        names = [arch_names[i] for i in sorted(idx)]
        key = " + ".join(names)
        counts[key] = counts.get(key, 0) + 1

    items = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:k]
    df = pd.DataFrame(items, columns=["trójka", "liczba"])
    df["liczba"] = df["liczba"].astype(int)
    df["%"] = np.round(df["liczba"] / denom * 100.0, 1)
    return df


# =========================
# 6) B1: ranking kombinacji (trójki)
# =========================

def plot_B1_combo_bar(df_combo: pd.DataFrame, out_png: Path | str,
                      title: str = "B1 – 5 najczęstszych trójek (kombinacje)") -> None:
    col_pct = "%" if "%" in df_combo.columns else ("pct" if "pct" in df_combo.columns else None)
    if col_pct is None:
        raise ValueError("Brak kolumny z procentami: oczekuję '%' albo 'pct' w df_combo.")

    s = df_combo.set_index("trójka")[col_pct].astype(float).sort_values(ascending=False)
    s.index = [
        "\n".join([part.strip() for part in str(lbl).split("+")])
        for lbl in s.index
    ]
    bar_chart(s, outpath=Path(out_png), title=title, xlabel="Odsetek (%)", rotate=0)


# =========================
# 7) P/E/G Z A, B, D (ultra premium)
# =========================

def build_PEG_from_ABD(
        A: np.ndarray,
        b1: np.ndarray,
        b2: np.ndarray,
        d12: np.ndarray,
        d13: np.ndarray,
        w_A: float,
        weights: np.ndarray,
        archetypes: List[str] = ARCHETYPES
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Buduje indeksy P (preferencje idealne), E (doświadczenia), G = P - E.
    Zgodne z metodologią dokumentu Segmentacja-Archetypow.docx.
    """
    n_resp, n_arch = len(weights), len(archetypes)
    idx = {a: i for i, a in enumerate(archetypes)}

    # --- P: z A + B ---
    P = np.zeros((n_resp, n_arch), dtype=float)

    # A: bilans pojedynków (Y = A - 4, lewy -Y, prawy +Y)
    A_centered = (A - float(A_SCALE_CENTER)) * float(w_A)
    for j, (_pid, left, right) in enumerate(A_PAIRS):
        y = A_centered[:, j]
        y = np.where(np.isfinite(y), y, 0.0)
        li = idx[left]
        ri = idx[right]
        P[:, ri] += y
        P[:, li] -= y

    # B1, B2: preferencje deklaratywne
    w_b1, w_b2 = 1.0, 2.0
    for j, arch in enumerate(archetypes):
        P[:, j] += w_b1 * np.where(np.isfinite(b1[:, j]), b1[:, j], 0.0)
    for i in range(n_resp):
        if 0 <= b2[i] < n_arch:
            P[i, b2[i]] += w_b2

    # --- E: z D ---
    E = np.zeros((n_resp, n_arch), dtype=float)
    for j in range(min(d12.shape[1], n_arch)):
        col = np.where(np.isfinite(d12[:, j]), d12[:, j], 0.0)
        E[:, j] += col
    for i in range(n_resp):
        if 0 <= d13[i] < n_arch:
            E[i, d13[i]] += 1.0

    # --- G = P - E ---
    G = P - E

    return P, E, G


# =========================
# 8B) PREMIUM: segmentacja bez limitu 3 (k w przedziale min–max)
#     + profilowanie + „sygnatury” + top różnice
# =========================

def _zscore_matrix(X: np.ndarray) -> np.ndarray:
    X = np.asarray(X, dtype=float)
    mu = np.nanmean(X, axis=0)
    sd = np.nanstd(X, axis=0) + 1e-12
    Z = (X - mu) / sd
    Z[~np.isfinite(Z)] = 0.0
    return Z


def _wmean_cols_nan(mat: np.ndarray, w: np.ndarray) -> np.ndarray:
    mat = np.asarray(mat, dtype=float)
    w = np.asarray(w, dtype=float).reshape(-1)
    out = np.full(mat.shape[1], np.nan, dtype=float)
    for j in range(mat.shape[1]):
        xj = mat[:, j]
        m = np.isfinite(xj) & np.isfinite(w) & (w > 0)
        if not np.any(m):
            continue
        out[j] = float(np.average(xj[m], weights=w[m]))
    return out


def _wmean_cols(mat: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Alias kompatybilnościowy: dawny kod używał _wmean_cols()."""
    return _wmean_cols_nan(mat, w)


def _top_k(series: pd.Series, k: int = 3) -> List[Tuple[str, float]]:
    s = series.dropna().sort_values(ascending=False).head(k)
    return [(str(i), float(v)) for i, v in s.items()]


def _bottom_k(series: pd.Series, k: int = 3) -> List[Tuple[str, float]]:
    s = series.dropna().sort_values(ascending=True).head(k)
    return [(str(i), float(v)) for i, v in s.items()]


def _usefulness_score(deltaP: np.ndarray) -> float:
    """
    „Polityczna użyteczność”: im większe odchylenia od średniej (czytelny profil),
    tym segment bardziej „targetowalny”.
    """
    d = np.asarray(deltaP, dtype=float)
    d = d[np.isfinite(d)]
    if len(d) == 0:
        return 0.0
    # typowo sensowne delty ~0..15pp; skalujemy do 0..100
    score = float(np.mean(np.abs(d)) / 12.0 * 100.0)
    return float(max(0.0, min(100.0, score)))


def build_segmentation_solutions(
        X: np.ndarray,
        weights: np.ndarray,
        k_min: int,
        k_max: int,
        seed: int,
) -> Dict[int, Dict[str, Any]]:
    """
    Liczy rozwiązania k-means dla wszystkich k w [k_min, k_max],
    ALE używa tego samego, spójnego silnika co reszta kodu:
      - _weighted_kmeans
      - _silhouette_basic
    Dzięki temu nie ma zależności od zewnętrznych kmeans()/silhouette_score().
    """
    X = np.asarray(X, dtype=float)
    w = np.asarray(weights, dtype=float).reshape(-1)

    # spójna standaryzacja wagowa
    Xz = _wstandardize(X, w)
    Xz = np.nan_to_num(Xz, nan=0.0)

    n = Xz.shape[0]
    k_min = max(2, int(k_min))
    k_max = max(k_min, int(k_max))
    k_max = min(k_max, max(2, n - 1))

    sols: Dict[int, Dict[str, Any]] = {}
    for k in range(k_min, k_max + 1):
        labels, _ = _weighted_kmeans(
            Xz, w, k=int(k),
            seed=int(seed + 100 * int(k)),
            n_init=8, max_iter=260
        )
        sil = float(_silhouette_basic(Xz, labels, weights=w, sample_max=1800, seed=int(seed + 100 * int(k))))
        sols[int(k)] = {
            "k": int(k),
            "labels": labels.astype(int),
            "silhouette": sil,
        }
    return sols


def build_meta_features_from_P(P: np.ndarray) -> np.ndarray:
    """
    Buduje stabilne cechy segmentacyjne z profilu 12 archetypów (P).

    Kluczowa zmiana:
    - poprzednia wersja miała pozornie 4 cechy, ale 2 z nich były tylko rotacją
      dwóch pierwszych, więc realnie segmentacja działała prawie w 2D;
    - nowa wersja używa niezależnych harmonicznych koła (1., 2. i 3.),
      dzięki czemu zachowujemy logikę „koła archetypów”, ale bez sztucznego
      spłaszczenia.

    Wynik:
    - 6 rzeczywiście informacyjnych cech segmentacyjnych,
    - nadal wyłącznie z P,
    - nadal po centrowaniu wewnątrzosobniczym.
    """
    P = np.asarray(P, dtype=float)
    if P.ndim != 2:
        raise ValueError("build_meta_features_from_P(): oczekuję macierzy 2D")
    if P.shape[1] != len(ARCHETYPES):
        raise ValueError(
            f"build_meta_features_from_P(): oczekuję {len(ARCHETYPES)} kolumn, mam {P.shape[1]}"
        )

    row_mean = np.nanmean(P, axis=1, keepdims=True)
    Pc = P - row_mean
    Pc = np.nan_to_num(Pc, nan=0.0)

    coords, _meta = build_value_space_fixed_circle(list(ARCHETYPES))
    coords = np.asarray(coords, dtype=float)

    theta = np.arctan2(coords[:, 1], coords[:, 0])

    # 1. harmoniczna: główna oś koła
    b1x = np.cos(theta)
    b1y = np.sin(theta)

    # 2. harmoniczna: rozróżnia „podtypy” w obrębie przeciwległych ćwiartek
    b2x = np.cos(2.0 * theta)
    b2y = np.sin(2.0 * theta)

    # 3. harmoniczna: dodatkowa subtelna struktura, żeby nie sklejać zbyt szeroko
    b3x = np.cos(3.0 * theta)
    b3y = np.sin(3.0 * theta)

    X_meta = np.column_stack([
        Pc @ b1x,
        Pc @ b1y,
        Pc @ b2x,
        Pc @ b2y,
        Pc @ b3x,
        Pc @ b3y,
    ])

    X_meta = np.nan_to_num(X_meta, nan=0.0)
    return X_meta


def _segment_min_centroid_distance(Xz: np.ndarray, labels: np.ndarray, weights: np.ndarray) -> float:
    """
    Minimalna odległość między centroidami segmentów w przestrzeni standaryzowanej.
    Im wyżej, tym segmenty bardziej rozdzielone.
    """
    Xz = np.asarray(Xz, dtype=float)
    labels = np.asarray(labels, dtype=int).reshape(-1)
    w = np.asarray(weights, dtype=float).reshape(-1)

    uniq = [int(x) for x in np.unique(labels) if int(x) >= 0]
    if len(uniq) < 2:
        return 0.0

    centroids: List[np.ndarray] = []
    for sid in uniq:
        m = labels == sid
        if not np.any(m):
            continue
        ww = w[m]
        if np.sum(ww) <= 0:
            continue
        c = np.average(Xz[m], axis=0, weights=ww)
        centroids.append(np.asarray(c, dtype=float))

    if len(centroids) < 2:
        return 0.0

    best = float("inf")
    for i in range(len(centroids)):
        for j in range(i + 1, len(centroids)):
            d = float(np.linalg.norm(centroids[i] - centroids[j]))
            if d < best:
                best = d

    return 0.0 if not np.isfinite(best) else float(best)


def _segment_duplicate_stats(P: np.ndarray, labels: np.ndarray, weights: np.ndarray) -> Dict[str, float]:
    """
    Kontrola jakości: wykrywa pary segmentów zbyt podobnych profilowo.

    Liczymy to na surowych profilach Pm (kanoniczne źródło prawdy), a nie na nazwach.
    Dzięki temu „sobowtóry” są wyłapywane systemowo przy wyborze modelu.
    """
    try:
        X = np.asarray(P, dtype=float)
    except Exception:
        X = np.asarray([], dtype=float)

    labels = np.asarray(labels, dtype=int).reshape(-1)
    w = np.asarray(weights, dtype=float).reshape(-1)

    if X.ndim != 2 or X.shape[1] != len(ARCHETYPES) or X.shape[0] != labels.shape[0]:
        return {
            "duplicate_pairs": 0.0,
            "max_similarity": 0.0,
            "min_l2": 0.0,
        }

    uniq = [int(x) for x in np.unique(labels) if int(x) >= 0]
    if len(uniq) < 2:
        return {
            "duplicate_pairs": 0.0,
            "max_similarity": 0.0,
            "min_l2": 0.0,
        }

    profs = []
    for sid in uniq:
        m = labels == sid
        if not np.any(m):
            continue

        ww = np.asarray(w[m], dtype=float)
        if ww.shape[0] != int(np.sum(m)):
            ww = np.ones(int(np.sum(m)), dtype=float)
        ww = np.where(np.isfinite(ww) & (ww > 0), ww, 0.0)
        if float(np.sum(ww)) <= 1e-12:
            ww = np.ones(int(np.sum(m)), dtype=float)

        pm = _wmean_cols(X[m], ww)
        pm = np.asarray(pm, dtype=float).reshape(-1)
        if pm.shape[0] != len(ARCHETYPES):
            continue
        pm = np.where(np.isfinite(pm), pm, 0.0)

        pm_center = pm - float(np.mean(pm))
        pm_norm = float(np.linalg.norm(pm_center))
        if pm_norm <= 1e-12:
            pm_unit = np.zeros_like(pm_center)
        else:
            pm_unit = pm_center / pm_norm

        top3 = set(int(x) for x in np.argsort(-pm)[:3])
        top4 = set(int(x) for x in np.argsort(-pm)[:4])
        profs.append((pm, pm_unit, top3, top4))

    if len(profs) < 2:
        return {
            "duplicate_pairs": 0.0,
            "max_similarity": 0.0,
            "min_l2": 0.0,
        }

    duplicate_pairs = 0
    max_similarity = -1.0
    min_l2 = float("inf")

    for i in range(len(profs)):
        pm_i, unit_i, top3_i, top4_i = profs[i]
        for j in range(i + 1, len(profs)):
            pm_j, unit_j, top3_j, top4_j = profs[j]

            cos_sim = float(np.dot(unit_i, unit_j))
            l2 = float(np.linalg.norm(pm_i - pm_j))
            shared_top3 = len(top3_i & top3_j)
            shared_top4 = len(top4_i & top4_j)

            max_similarity = max(max_similarity, cos_sim)
            if l2 < min_l2:
                min_l2 = l2

            is_duplicate = (
                    (shared_top3 == 3)
                    or (shared_top3 >= 2 and cos_sim >= 0.985)
                    or (shared_top4 >= 3 and cos_sim >= 0.975 and l2 <= 3.0)
            )
            if is_duplicate:
                duplicate_pairs += 1

    if not np.isfinite(max_similarity):
        max_similarity = 0.0
    if not np.isfinite(min_l2):
        min_l2 = 0.0

    return {
        "duplicate_pairs": float(duplicate_pairs),
        "max_similarity": float(max_similarity),
        "min_l2": float(min_l2),
    }


def _segment_forbidden_pair_hits(
        P: np.ndarray,
        labels: np.ndarray,
        weights: np.ndarray,
        forbidden_pairs: Tuple[Tuple[str, str], ...] = SEG_FORBIDDEN_ARCHETYPE_PAIRS,
        top_n: int = SEG_FORBIDDEN_TOP_N,
) -> int:
    """
    Zwraca liczbę segmentów, w których jednocześnie występują zakazane pary archetypów
    w rdzeniu segmentu (TOP-N wg surowego profilu Pm).
    """
    X = np.asarray(P, dtype=float)
    labs = np.asarray(labels, dtype=int).reshape(-1)
    w = np.asarray(weights, dtype=float).reshape(-1)

    if X.ndim != 2 or X.shape[0] != labs.shape[0] or X.shape[1] != len(ARCHETYPES):
        return 0

    try:
        top_n_eff = max(2, min(int(top_n), len(ARCHETYPES)))
    except Exception:
        top_n_eff = 4

    idx_pairs: List[Tuple[int, int]] = []
    idx_map = {a: i for i, a in enumerate(ARCHETYPES)}
    for a, b in (forbidden_pairs or ()):
        if a in idx_map and b in idx_map:
            idx_pairs.append((int(idx_map[a]), int(idx_map[b])))

    if not idx_pairs:
        return 0

    hits = 0
    uniq = [int(x) for x in np.unique(labs) if int(x) >= 0]

    for sid in uniq:
        m = labs == sid
        if not np.any(m):
            continue

        ww = np.asarray(w[m], dtype=float)
        ww = np.where(np.isfinite(ww) & (ww > 0), ww, 0.0)
        if float(np.sum(ww)) <= 1e-12:
            ww = np.ones(int(np.sum(m)), dtype=float)

        pm = _wmean_cols(X[m], ww)
        pm = np.asarray(pm, dtype=float).reshape(-1)
        if pm.shape[0] != len(ARCHETYPES):
            continue

        top_idx = set(int(i) for i in np.argsort(-pm)[:top_n_eff])
        for ia, ib in idx_pairs:
            if ia in top_idx and ib in top_idx:
                hits += 1
                break

    return int(hits)


def _reorder_labels_by_weight(labels: np.ndarray, weights: np.ndarray) -> Tuple[np.ndarray, Dict[int, int]]:
    """
    Przestawia etykiety segmentów tak, aby:
    - Seg_1 = największy segment
    - Seg_2 = drugi największy
    itd.

    Ranking po wielkości:
    1) udział ważony malejąco
    2) liczebność surowa malejąco
    3) stary id rosnąco
    """
    labels = np.asarray(labels, dtype=int).reshape(-1)
    w = np.asarray(weights, dtype=float).reshape(-1)

    uniq = [int(x) for x in np.unique(labels) if int(x) >= 0]
    if not uniq:
        return labels.copy(), {}

    stats = []
    w_sum = float(np.sum(w)) + 1e-12

    for sid in uniq:
        m = labels == sid
        share = float(np.sum(w[m]) / w_sum)
        n_raw = int(np.sum(m))
        stats.append((sid, share, n_raw))

    stats_sorted = sorted(stats, key=lambda t: (-t[1], -t[2], t[0]))
    id_map: Dict[int, int] = {int(old): int(new) for new, (old, _share, _nraw) in enumerate(stats_sorted)}

    labels_ranked = np.asarray([id_map[int(v)] for v in labels], dtype=int)
    return labels_ranked, id_map


def _relabel_segments_by_weighted_share(
        segs: List[Dict[str, Any]],
        labels_ranked: Optional[np.ndarray] = None,
        labels_ranked_effective: Optional[np.ndarray] = None,
) -> Tuple[List[Dict[str, Any]], Optional[np.ndarray], Optional[np.ndarray], Dict[int, int]]:
    """
    Ujednolica numerację segmentów po końcowym udziale ważonym:
    Seg_1 = największy udział, Seg_2 = drugi itd.
    Dodatkowo remapuje etykiety respondentów (labels_ranked*), aby całość raportu
    używała tej samej numeracji we wszystkich zakładkach.
    """
    segs_in = [dict(s) for s in (segs or []) if isinstance(s, dict)]
    if not segs_in:
        return list(segs or []), labels_ranked, labels_ranked_effective, {}

    def _seg_rank(seg: Dict[str, Any], idx: int) -> int:
        try:
            return int(_safe_float(seg.get("segment_rank", seg.get("segment_id", idx))))
        except Exception:
            return int(idx)

    order = sorted(
        range(len(segs_in)),
        key=lambda i: (
            -float(_safe_float(segs_in[i].get("share_pct", 0.0))),
            -int(_safe_float(segs_in[i].get("n", 0))),
            _seg_rank(segs_in[i], i),
        )
    )

    rank_map: Dict[int, int] = {}
    segs_out: List[Dict[str, Any]] = []

    for new_rank, old_idx in enumerate(order):
        src = dict(segs_in[old_idx])
        old_rank = _seg_rank(src, old_idx)
        rank_map[int(old_rank)] = int(new_rank)

        src["segment_id"] = int(new_rank)
        src["segment_rank"] = int(new_rank)
        src["segment_label"] = f"Seg_{int(new_rank) + 1}"
        src["segment"] = f"Seg_{int(new_rank) + 1}"
        segs_out.append(src)

    def _remap_labels(arr: Optional[np.ndarray]) -> Optional[np.ndarray]:
        if not isinstance(arr, np.ndarray):
            return arr
        out = np.asarray(arr, dtype=int).reshape(-1).copy()
        if out.size == 0:
            return out
        valid = out >= 0
        if np.any(valid):
            out[valid] = np.asarray(
                [int(rank_map.get(int(v), int(v))) for v in out[valid]],
                dtype=int
            )
        return out

    return segs_out, _remap_labels(labels_ranked), _remap_labels(labels_ranked_effective), rank_map


def build_meta_seg_pack(tab_key: str,
                        metry: Optional[pd.DataFrame],
                        P: np.ndarray, E: np.ndarray, G: np.ndarray, w: np.ndarray,
                        settings: Settings,
                        brand_values: Dict[str, str],
                        outdir: Path,
                        seed_offset: int = 0) -> Dict[str, Any]:
    """
    Główny silnik segmentacji:
    - źródło prawdy = profil P (12 archetypów),
    - segmentacja = meta-cechy wyprowadzone z P,
    - klastrowanie = weighted k-means,
    - numeracja segmentów = po wielkości (malejąco),
    - raport pokazuje jedną stałą segmentację; suwak tylko ukrywa/pokazuje pierwsze N segmentów.
    """
    _ = outdir  # zostawiamy parametr dla zgodności architektury

    P = np.asarray(P, dtype=float)
    E = np.asarray(E, dtype=float)
    G = np.asarray(G, dtype=float)
    w = np.asarray(w, dtype=float).reshape(-1)

    if P.ndim != 2 or len(P) == 0:
        raise RuntimeError("build_meta_seg_pack(): brak poprawnej macierzy P do segmentacji.")
    if len(P) != len(w):
        raise RuntimeError("build_meta_seg_pack(): długość wag nie zgadza się z liczbą respondentów.")

    X_meta = build_meta_features_from_P(P)
    Xz = _wstandardize(X_meta, w)
    Xz = np.nan_to_num(Xz, nan=0.0)

    n = int(Xz.shape[0])

    # Trzymamy sensowny zakres do komunikacji politycznej,
    # ale bez twardego, zaszytego w kodzie limitu 8.
    k_floor = 3
    k_cap = max(k_floor, int(settings.segments_max_segments))

    req_k_min = max(k_floor, int(settings.segments_k_min))
    req_k_max = max(req_k_min, int(settings.segments_k_max))

    fit_k_min = min(req_k_min, max(2, n - 1))
    fit_k_max = min(req_k_max, max(2, n - 1), k_cap)
    fit_k_min = max(2, min(fit_k_min, fit_k_max))

    # Progi lekko zmiękczone:
    # - dalej nie wpuszczamy mikro-segmentów,
    # - ale nie ścinamy zbyt agresywnie sensownych 4–5 segmentów.
    min_share_required = max(0.06, float(settings.segments_min_share_default) * 0.80)
    min_centroid_dist_required = 0.42

    best_item: Optional[Dict[str, Any]] = None
    best_key: Optional[Tuple[Any, ...]] = None
    solutions: List[Dict[str, Any]] = []

    for k in range(int(fit_k_min), int(fit_k_max) + 1):
        labels_try, _cent = _weighted_kmeans(
            Xz, w,
            k=int(k),
            seed=int(settings.random_seed + seed_offset + 137 * int(k)),
            n_init=12,
            max_iter=320
        )

        labels_try = np.asarray(labels_try, dtype=int).reshape(-1)
        uniq = [int(x) for x in np.unique(labels_try) if int(x) >= 0]

        shares = []
        for sid in uniq:
            m = labels_try == sid
            shares.append(float(np.sum(w[m]) / (np.sum(w) + 1e-12)))

        min_share = float(min(shares)) if shares else 0.0
        min_centroid_dist = _segment_min_centroid_distance(Xz, labels_try, w)
        dup_stats = _segment_duplicate_stats(P, labels_try, w)
        duplicate_pairs = int(round(float(dup_stats.get("duplicate_pairs", 0.0))))
        max_profile_similarity = float(dup_stats.get("max_similarity", 0.0))
        min_profile_l2 = float(dup_stats.get("min_l2", 0.0))
        sil = float(_silhouette_basic(Xz, labels_try, weights=w, sample_max=int(settings.silhouette_sample_max), seed=int(settings.random_seed + seed_offset + 137 * int(k))))
        forbidden_pair_hits = int(_segment_forbidden_pair_hits(P, labels_try, w))

        is_valid = bool(
            len(uniq) == int(k)
            and min_share >= float(min_share_required)
            and min_centroid_dist >= float(min_centroid_dist_required)
            and duplicate_pairs == 0
            and forbidden_pair_hits == 0
        )

        # score wyłącznie informacyjny do raportu
        score = float((sil * 100.0) + (min_share * 100.0) + (min_centroid_dist * 10.0))

        solutions.append({
            "k": int(k),
            "score": score,
            "metric": "sil+share+dist",
            "silhouette": float(sil),
            "min_share_pct": float(min_share * 100.0),
            "min_centroid_dist": float(min_centroid_dist),
            "duplicate_pairs": int(duplicate_pairs),
            "max_profile_similarity": float(max_profile_similarity),
            "min_profile_l2": float(min_profile_l2),
            "forbidden_pair_hits": int(forbidden_pair_hits),
            "is_valid": bool(is_valid),
        })

        # Priorytet:
        # 1) model poprawny metodologicznie
        # 2) lepsza silhouette
        # 3) większa separacja centroidów
        # 4) większy min_share
        # 5) k bliżej domyślnego (nie premiujemy już mechanicznie maksymalnego k)
        # 6) przy remisie – mniejsze k
        k_pref = int(settings.segments_k_default)

        hard_dup = bool(
            int(k) > 3 and (
                    int(duplicate_pairs) > 0
                    or float(max_profile_similarity) >= 0.955
                    or float(min_profile_l2) <= 0.45
            )
        )
        hard_forbidden = bool(int(forbidden_pair_hits) > 0)

        rank_valid = bool(is_valid) and not hard_dup and not hard_forbidden

        soft_dup_penalty = (
                (5000.0 if hard_dup else 0.0)
                + (7000.0 * float(forbidden_pair_hits))
                + (max(0.0, float(max_profile_similarity) - 0.92) * 250.0)
                + (max(0.0, 0.55 - float(min_profile_l2)) * 120.0)
        )

        cand_key = (
            1 if rank_valid else 0,
            1 if not hard_dup else 0,
            1 if not hard_forbidden else 0,
            1 if is_valid else 0,
            -float(soft_dup_penalty),
            -int(forbidden_pair_hits),
            -int(duplicate_pairs),
            float(min_profile_l2),
            -float(max_profile_similarity),
            float(sil),
            float(min_centroid_dist),
            float(min_share),
            -abs(int(k) - k_pref),
            -int(k),
        )

        if best_key is None or cand_key > best_key:
            best_key = cand_key
            best_item = {
                "k": int(k),
                "labels": labels_try.copy(),
                "score": float(score),
                "silhouette": float(sil),
                "min_share": float(min_share),
                "min_centroid_dist": float(min_centroid_dist),
                "duplicate_pairs": int(duplicate_pairs),
                "max_profile_similarity": float(max_profile_similarity),
                "min_profile_l2": float(min_profile_l2),
                "forbidden_pair_hits": int(forbidden_pair_hits),
                "is_valid": bool(is_valid) and not hard_dup and not hard_forbidden,
            }

    if best_item is None:
        raise RuntimeError("build_meta_seg_pack(): nie udało się policzyć żadnego rozwiązania segmentacji.")

    if not bool(best_item.get("is_valid", False)):
        warn_bits: List[str] = ["minimalny udział / separacja"]
        if int(best_item.get("duplicate_pairs", 0)) > 0:
            warn_bits.append("duplikujące się profile segmentów")
        if int(best_item.get("forbidden_pair_hits", 0)) > 0:
            warn_bits.append("zakazane pary archetypów w jednym segmencie")

        print(
            "[WARN] build_meta_seg_pack(): żaden model nie spełnił twardych progów "
            f"({'; '.join(warn_bits)}). Wybrano najlepszy wariant zapasowy."
        )

    labels_raw = np.asarray(best_item["labels"], dtype=int).reshape(-1)
    labels_ranked, id_map_int = _reorder_labels_by_weight(labels_raw, w)

    segs = _segment_profiles_from_ranked_labels(
        labels_ranked=labels_ranked,
        metry=metry,
        P=P, E=E, G=G, w=w,
        brand_values=brand_values
    )

    if not segs:
        raise RuntimeError("build_meta_seg_pack(): nie udało się zbudować profili segmentów.")

    segs_base = [dict(s) for s in segs]

    labels_ranked_effective: Optional[np.ndarray] = None
    segs_recalc, labels_ranked_effective = _recompute_segment_sizes_from_active_hits(
        segs=segs_base,
        P=P,
        w=w,
        segment_threshold_overrides=settings.segment_hit_threshold_overrides,
    )
    if isinstance(labels_ranked_effective, np.ndarray) and labels_ranked_effective.size == labels_ranked.size:
        segs_effective = _segment_profiles_from_ranked_labels(
            labels_ranked=labels_ranked_effective,
            metry=metry,
            P=P, E=E, G=G, w=w,
            brand_values=brand_values
        )
        if isinstance(segs_effective, list) and len(segs_effective) == len(segs_base):
            base_by_rank: Dict[int, Dict[str, Any]] = {}
            for sb in segs_base:
                sr = int(_safe_float(sb.get("segment_rank", sb.get("segment_id", -1))))
                base_by_rank[sr] = sb

            recalc_by_rank: Dict[int, Dict[str, Any]] = {}
            for srx in (segs_recalc or []):
                if isinstance(srx, dict):
                    sr = int(_safe_float(srx.get("segment_rank", srx.get("segment_id", -1))))
                    recalc_by_rank[sr] = srx

            merged: List[Dict[str, Any]] = []
            for se in segs_effective:
                sr = int(_safe_float(se.get("segment_rank", se.get("segment_id", -1))))
                ss = dict(se)

                base_seg = base_by_rank.get(sr, {})
                recalc_seg = recalc_by_rank.get(sr, {})

                if recalc_seg:
                    ss["n"] = int(_safe_float(recalc_seg.get("n", ss.get("n", 0))))
                    ss["share_pct"] = float(_safe_float(recalc_seg.get("share_pct", ss.get("share_pct", 0.0))))
                    ss["segment_size_source"] = str(recalc_seg.get("segment_size_source", "active_hits"))
                    ss["active_hits_count"] = int(_safe_float(recalc_seg.get("active_hits_count", 0)))
                else:
                    ss["segment_size_source"] = "active_hits"

                ss["n_base"] = int(_safe_float(base_seg.get("n", ss.get("n", 0))))
                ss["share_pct_base"] = float(_safe_float(base_seg.get("share_pct", ss.get("share_pct", 0.0))))
                merged.append(ss)

            segs = merged
    elif isinstance(segs_recalc, list) and len(segs_recalc) == len(segs):
        segs = segs_recalc

    segs, labels_ranked, labels_ranked_effective, _rank_map_final = _relabel_segments_by_weighted_share(
        segs=segs,
        labels_ranked=labels_ranked,
        labels_ranked_effective=labels_ranked_effective,
    )
    if _rank_map_final:
        id_map_int = {
            int(old): int(_rank_map_final.get(int(new), int(new)))
            for old, new in id_map_int.items()
        }

    k_model = int(len(segs))
    avg_use = float(np.mean([float(s.get("usefulness", 0.0)) for s in segs])) if segs else 0.0

    matrix_html_arche = _render_segment_matrix_html(
        segs,
        brand_values,
        mode="arche",
        top_n=k_model,
        segment_threshold_overrides=settings.segment_hit_threshold_overrides
    )
    matrix_html_values = _render_segment_matrix_html(
        segs,
        brand_values,
        mode="values",
        top_n=k_model,
        segment_threshold_overrides=settings.segment_hit_threshold_overrides
    )

    by_k = {
        str(k_model): {
            "k": int(k_model),
            "k_requested": int(best_item["k"]),
            "avg_usefulness": float(avg_use),
            "profiles_html_arche": _profiles_to_html(segs, brand_values, mode="arche", city_label=settings.city_label, population_15_plus=settings.population_15_plus, segment_threshold_overrides=settings.segment_hit_threshold_overrides),
            "profiles_html_values": _profiles_to_html(segs, brand_values, mode="values", city_label=settings.city_label, population_15_plus=settings.population_15_plus, segment_threshold_overrides=settings.segment_hit_threshold_overrides),
            "segment_names_arche": [_segment_name_pair(s)[0] for s in segs],
            "segment_names_values": [_segment_name_pair(s)[1] for s in segs],
            "matrix_html_arche": matrix_html_arche,
            "matrix_html_values": matrix_html_values,
            "heatmap_arche": "",
            "heatmap_values": "",
            "id_map": {str(int(old)): int(new) for old, new in id_map_int.items()},
            "labels_ranked": labels_ranked.astype(int).tolist(),
            "labels_ranked_effective": (
                labels_ranked_effective.astype(int).tolist()
                if isinstance(labels_ranked_effective, np.ndarray) and labels_ranked_effective.size == labels_ranked.size
                else []
            ),
            "segment_size_mode": (
                "active_hits"
                if isinstance(labels_ranked_effective, np.ndarray) and labels_ranked_effective.size == labels_ranked.size
                else "cluster_kmeans"
            ),
            "profiles_payload": segs,
            "sig_html_arche": "",
            "sig_html_values": "",
            "sig_json": [],
            "bubble_arche": "",
            "bubble_values": "",
        }
    }

    pack = {
        "tab_key": tab_key,
        "solutions": solutions,
        "by_k": by_k,
        "best_k_default": int(k_model),
        "k_model": int(k_model),
        "k_requested": int(best_item["k"]),
        "k_min": 1,
        "k_max": int(k_model),
        "k_default_ui": int(min(max(1, settings.segments_k_default), k_model)),
        "default_min_share_pct": float(min_share_required * 100.0),
    }
    return pack


def _weighted_cluster_inertia(X: np.ndarray,
                              labels: np.ndarray,
                              centroids: np.ndarray,
                              weights: np.ndarray) -> float:
    X = np.asarray(X, dtype=float)
    labels = np.asarray(labels, dtype=int).reshape(-1)
    centroids = np.asarray(centroids, dtype=float)
    w = np.asarray(weights, dtype=float).reshape(-1)

    if X.ndim != 2 or X.shape[0] == 0:
        return float("nan")
    if labels.size != X.shape[0] or w.size != X.shape[0]:
        return float("nan")
    if centroids.ndim != 2 or centroids.shape[1] != X.shape[1]:
        return float("nan")

    valid = (
        np.isfinite(X).all(axis=1)
        & np.isfinite(w)
        & (w > 0)
        & np.isfinite(labels)
        & (labels >= 0)
        & (labels < centroids.shape[0])
    )
    if not np.any(valid):
        return float("nan")

    Xv = X[valid]
    lv = labels[valid].astype(int)
    wv = w[valid]
    diff = Xv - centroids[lv]
    d2 = np.sum(diff * diff, axis=1)
    return float(np.sum(wv * d2))


def _plot_cluster_k_diagnostics(quality_df: pd.DataFrame,
                                outdir: Path,
                                prefix: str = "SKUPIENIA") -> Dict[str, str]:
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    if quality_df is None or len(quality_df) == 0:
        return {}

    qdf = quality_df.copy()
    if "k" not in qdf.columns:
        return {}
    qdf = qdf.sort_values("k").reset_index(drop=True)

    k_vals = pd.to_numeric(qdf["k"], errors="coerce").to_numpy(dtype=float)
    sil_vals = pd.to_numeric(qdf.get("silhouette"), errors="coerce").to_numpy(dtype=float)
    wss_vals = pd.to_numeric(qdf.get("wss"), errors="coerce").to_numpy(dtype=float)

    fn_sil = f"{prefix}_DOBOR_K_SILHOUETTE.png"
    fn_elb = f"{prefix}_DOBOR_K_ELBOW.png"

    # Silhouette
    fig, ax = plt.subplots(figsize=(8.6, 4.8), dpi=PLOT_DPI)
    ax.plot(k_vals, sil_vals, marker="o", color="#1d4ed8", linewidth=2.2)
    ax.set_title("Dobór liczby skupień (silhouette)", fontsize=14, fontweight="bold")
    ax.set_xlabel("Liczba skupień (K)")
    ax.set_ylabel("Silhouette")
    ax.grid(alpha=0.25)
    ax.set_xticks([int(x) for x in k_vals if np.isfinite(x)])

    finite_mask = np.isfinite(sil_vals)
    if np.any(finite_mask):
        i_best = int(np.nanargmax(sil_vals))
        x_best = float(k_vals[i_best])
        y_best = float(sil_vals[i_best])
        ax.scatter([x_best], [y_best], color="#0f172a", s=70, zorder=4)
        ax.annotate(
            f"Najlepsze K={int(round(x_best))}\nSilhouette={y_best:.3f}",
            xy=(x_best, y_best),
            xytext=(10, 10),
            textcoords="offset points",
            fontsize=10,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#cbd5e1"),
        )

    fig.tight_layout()
    fig.savefig(outdir / fn_sil, dpi=PLOT_DPI, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)

    # Elbow / WSS
    fig, ax = plt.subplots(figsize=(8.6, 4.8), dpi=PLOT_DPI)
    ax.plot(k_vals, wss_vals, marker="o", color="#0f766e", linewidth=2.2)
    ax.set_title("Dobór liczby skupień (elbow / WSS)", fontsize=14, fontweight="bold")
    ax.set_xlabel("Liczba skupień (K)")
    ax.set_ylabel("Ważona suma kwadratów wewnątrz skupień (WSS)")
    ax.grid(alpha=0.25)
    ax.set_xticks([int(x) for x in k_vals if np.isfinite(x)])

    for i in range(1, len(k_vals)):
        prev_w = float(wss_vals[i - 1]) if np.isfinite(wss_vals[i - 1]) else float("nan")
        curr_w = float(wss_vals[i]) if np.isfinite(wss_vals[i]) else float("nan")
        if not (np.isfinite(prev_w) and np.isfinite(curr_w) and prev_w > 0):
            continue
        drop_pct = 100.0 * (prev_w - curr_w) / (prev_w + 1e-12)
        ax.annotate(
            f"-{drop_pct:.1f}%",
            xy=(k_vals[i], curr_w),
            xytext=(0, -12),
            textcoords="offset points",
            ha="center",
            fontsize=9,
            color="#0b5d56",
        )

    fig.tight_layout()
    fig.savefig(outdir / fn_elb, dpi=PLOT_DPI, bbox_inches="tight", pad_inches=0.15)
    plt.close(fig)

    return {
        "silhouette_png": fn_sil,
        "elbow_png": fn_elb,
    }


def _project_to_2d_weighted_pca(X: np.ndarray, w: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    X = np.asarray(X, dtype=float)
    w = np.asarray(w, dtype=float).reshape(-1)

    if X.ndim != 2 or X.shape[0] < 2 or w.size != X.shape[0]:
        return np.zeros((0, 2), dtype=float), np.zeros(0, dtype=bool), np.zeros(0, dtype=float)

    m_ok = np.isfinite(X).all(axis=1) & np.isfinite(w) & (w > 0)
    if int(np.sum(m_ok)) < 2:
        return np.zeros((0, 2), dtype=float), m_ok, np.zeros(0, dtype=float)

    Xv = X[m_ok]
    wv = w[m_ok]

    mu = np.average(Xv, axis=0, weights=wv)
    Xc = Xv - mu[None, :]
    Xc = np.nan_to_num(Xc, nan=0.0)

    try:
        Xw = Xc * np.sqrt(np.maximum(wv, 1e-12))[:, None]
        _U, _S, Vt = np.linalg.svd(Xw, full_matrices=False)
        comps = Vt[:2].T if Vt.shape[0] >= 2 else Vt[:1].T
        Y = np.dot(Xc, comps)
        if Y.ndim == 1:
            Y = Y.reshape(-1, 1)
        if Y.shape[1] == 1:
            Y = np.column_stack([Y[:, 0], np.zeros(Y.shape[0], dtype=float)])
        elif Y.shape[1] > 2:
            Y = Y[:, :2]
    except Exception:
        Y = np.zeros((Xc.shape[0], 2), dtype=float)

    return np.asarray(Y, dtype=float), m_ok, np.asarray(wv, dtype=float)


def _convex_hull_2d(points: np.ndarray) -> np.ndarray:
    pts = np.asarray(points, dtype=float).reshape(-1, 2)
    if pts.shape[0] <= 2:
        return pts

    pts = pts[np.isfinite(pts).all(axis=1)]
    if pts.shape[0] <= 2:
        return pts

    pts = np.unique(pts, axis=0)
    if pts.shape[0] <= 2:
        return pts

    order = np.lexsort((pts[:, 1], pts[:, 0]))
    pts = pts[order]

    def _cross(o: np.ndarray, a: np.ndarray, b: np.ndarray) -> float:
        return float((a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]))

    lower: List[np.ndarray] = []
    for p in pts:
        while len(lower) >= 2 and _cross(lower[-2], lower[-1], p) <= 0.0:
            lower.pop()
        lower.append(p)

    upper: List[np.ndarray] = []
    for p in pts[::-1]:
        while len(upper) >= 2 and _cross(upper[-2], upper[-1], p) <= 0.0:
            upper.pop()
        upper.append(p)

    hull = np.vstack(lower[:-1] + upper[:-1]) if (len(lower) + len(upper)) >= 3 else pts
    return hull


def _wrap_cluster_legend_labels(labels: List[str], width: int = 30) -> List[str]:
    out: List[str] = []
    try:
        wrap_width = max(16, int(width))
    except Exception:
        wrap_width = 30
    for lab in list(labels or []):
        s = str(lab or "").strip()
        if not s:
            out.append("")
            continue
        out.append(textwrap.fill(s, width=wrap_width, break_long_words=False, break_on_hyphens=False))
    return out


def _draw_cluster_scatter_2d(ax: Any,
                             Y: np.ndarray,
                             labels: np.ndarray,
                             weights: np.ndarray,
                             segment_names: Optional[Any] = None,
                             title: str = "",
                             show_legend: bool = True,
                             legend_outside: bool = False) -> None:
    Y = np.asarray(Y, dtype=float).reshape(-1, 2)
    labels = np.asarray(labels, dtype=int).reshape(-1)
    w = np.asarray(weights, dtype=float).reshape(-1)

    if Y.shape[0] == 0 or labels.size != Y.shape[0] or w.size != Y.shape[0]:
        ax.set_axis_off()
        return

    uniq = [int(x) for x in np.unique(labels) if int(x) >= 0]
    if not uniq:
        ax.set_axis_off()
        return

    rng = np.random.default_rng(2026 + int(Y.shape[0]) + int(len(uniq)) * 17)
    markers = ["o", "^", "s", "D", "P", "X", "v", "*", "<", ">"]

    def _seg_name_for_id(seg_id: int) -> str:
        try:
            if isinstance(segment_names, dict):
                return str(segment_names.get(int(seg_id), "") or "").strip()
            if isinstance(segment_names, (list, tuple)) and int(seg_id) < len(segment_names):
                return str(segment_names[int(seg_id)] or "").strip()
        except Exception:
            return ""
        return ""

    for sid in uniq:
        m = labels == sid
        idx_all = np.where(m)[0]
        if idx_all.size == 0:
            continue

        idx_plot = idx_all
        if idx_plot.size > 2200:
            p = w[idx_plot] / (np.sum(w[idx_plot]) + 1e-12)
            idx_plot = np.asarray(rng.choice(idx_plot, size=2200, replace=False, p=p), dtype=int)

        try:
            pal = _segment_ui_colors(int(sid) + 1)
            col_acc = str(pal.get("accent", "#1d4ed8"))
            col_fill = str(pal.get("accent", col_acc))
        except Exception:
            cmap = plt.get_cmap("tab10")
            col_acc = cmap(int(sid) % 10)
            col_fill = col_acc

        seg_name = str(_seg_name_for_id(int(sid)) or "").strip()

        hull = _convex_hull_2d(Y[idx_all, :])
        if hull.shape[0] >= 3:
            ax.fill(hull[:, 0], hull[:, 1], color=col_acc, alpha=0.10, zorder=1)
            ax.plot(
                np.r_[hull[:, 0], hull[0, 0]],
                np.r_[hull[:, 1], hull[0, 1]],
                color=col_acc, linewidth=1.4, alpha=0.9, zorder=2
            )

        ax.scatter(
            Y[idx_plot, 0], Y[idx_plot, 1],
            s=22, alpha=0.50,
            color=col_fill,
            marker=markers[int(sid) % len(markers)],
            edgecolors="white",
            linewidths=0.25,
            label=(
                f"Seg_{int(sid) + 1}: {seg_name}"
                if seg_name
                else f"Seg_{int(sid) + 1}"
            ),
            zorder=3
        )

        ww = w[idx_all]
        xy = np.average(Y[idx_all], axis=0, weights=ww) if np.sum(ww) > 0 else np.mean(Y[idx_all], axis=0)
        ax.scatter(
            [xy[0]], [xy[1]],
            s=180,
            color=col_acc,
            edgecolor="white",
            linewidth=1.5,
            zorder=5
        )
        ax.text(
            float(xy[0]), float(xy[1]),
            f"{int(sid) + 1}",
            ha="center", va="center",
            fontsize=9, fontweight="bold",
            color="white",
            zorder=6
        )

    x = Y[:, 0]
    y = Y[:, 1]
    if np.isfinite(x).any() and np.isfinite(y).any():
        x_lo, x_hi = float(np.nanmin(x)), float(np.nanmax(x))
        y_lo, y_hi = float(np.nanmin(y)), float(np.nanmax(y))
        rng_x = max(1e-6, (x_hi - x_lo))
        rng_y = max(1e-6, (y_hi - y_lo))
        dx = min(0.90, max(0.16, 0.05 * rng_x))
        dy = min(0.95, max(0.18, 0.06 * rng_y))
        ax.set_xlim(x_lo - dx, x_hi + dx)
        ax.set_ylim(y_lo - dy, y_hi + dy)

    ax.set_title(title, fontsize=12, fontweight="bold", pad=6)
    ax.set_xlabel("PCA1 (główna oś P)")
    ax.set_ylabel("PCA2 (druga oś P)")
    try:
        ax.set_aspect("auto")
    except Exception:
        pass
    ax.grid(alpha=0.20)

    if show_legend:
        if legend_outside:
            ax.legend(title="Skupienie", frameon=False, loc="center left", bbox_to_anchor=(1.02, 0.5), fontsize=9, title_fontsize=10)
        else:
            ax.legend(title="Skupienie", frameon=False, loc="best", fontsize=8, title_fontsize=9)


def _plot_cluster_projection_2d(Xz: np.ndarray,
                                labels_ranked: np.ndarray,
                                weights: np.ndarray,
                                segment_names: Optional[Any],
                                outpath: Path) -> None:
    X = np.asarray(Xz, dtype=float)
    labels = np.asarray(labels_ranked, dtype=int).reshape(-1)
    w = np.asarray(weights, dtype=float).reshape(-1)
    outpath = Path(outpath)

    Y, m_ok, wv = _project_to_2d_weighted_pca(X, w)
    if Y.shape[0] == 0 or labels.size != X.shape[0]:
        return
    lv = labels[m_ok]
    if lv.size != Y.shape[0]:
        return

    fig = plt.figure(figsize=(12.6, 6.9), dpi=PLOT_DPI)
    gs = fig.add_gridspec(1, 2, width_ratios=[6.5, 2.3], wspace=0.03)
    ax = fig.add_subplot(gs[0, 0])
    ax_leg = fig.add_subplot(gs[0, 1])
    ax_leg.set_axis_off()

    _draw_cluster_scatter_2d(
        ax=ax,
        Y=Y,
        labels=lv,
        weights=wv,
        segment_names=segment_names,
        title="Mapa skupień",
        show_legend=False,
        legend_outside=False,
    )

    handles, labels_leg = ax.get_legend_handles_labels()
    if handles:
        labels_wrapped = _wrap_cluster_legend_labels([str(x) for x in labels_leg], width=34)
        ax_leg.legend(
            handles,
            labels_wrapped,
            title="Skupienie",
            loc="center left",
            bbox_to_anchor=(0.0, 0.5),
            frameon=True,
            facecolor="#ffffff",
            edgecolor="#d1d9e6",
            fontsize=10.5,
            title_fontsize=12,
            borderaxespad=0.0,
            handlelength=1.6,
            labelspacing=0.55,
        )

    fig.subplots_adjust(left=0.055, right=0.994, top=0.93, bottom=0.09)
    fig.savefig(outpath, dpi=PLOT_DPI)
    plt.close(fig)


def _plot_cluster_k_panels(Xz: np.ndarray,
                           labels_by_k: Dict[int, np.ndarray],
                           segment_names_by_k: Optional[Dict[int, List[str]]],
                           weights: np.ndarray,
                           k_values: List[int],
                           outpath: Path) -> None:
    X = np.asarray(Xz, dtype=float)
    w = np.asarray(weights, dtype=float).reshape(-1)
    outpath = Path(outpath)

    kvals = [int(k) for k in (k_values or []) if int(k) in labels_by_k]
    kvals = sorted(list(dict.fromkeys(kvals)))
    if not kvals:
        return

    Y, m_ok, wv = _project_to_2d_weighted_pca(X, w)
    if Y.shape[0] == 0:
        return

    n_pan = len(kvals)
    n_cols = 2 if n_pan > 1 else 1
    n_rows = int(math.ceil(float(n_pan) / float(n_cols)))

    fig_w = 17.8 if n_cols > 1 else 13.2
    fig_h = 5.55 * n_rows
    fig = plt.figure(figsize=(fig_w, fig_h), dpi=PLOT_DPI)

    # W tym zestawieniu legendy muszą pomieścić pełne nazwy segmentów w jednym wierszu.
    outer = fig.add_gridspec(1, 2, width_ratios=[6.7, 2.5], wspace=0.03)
    plot_grid = outer[0, 0].subgridspec(n_rows, n_cols, wspace=0.14, hspace=0.23)
    legend_grid = outer[0, 1].subgridspec(max(1, n_pan), 1, hspace=0.28)

    legend_payload: List[Tuple[int, List[Any], List[str]]] = []

    for idx, k in enumerate(kvals):
        row = int(idx // n_cols)
        col = int(idx % n_cols)
        ax = fig.add_subplot(plot_grid[row, col])

        labels_full = np.asarray(labels_by_k.get(int(k), []), dtype=int).reshape(-1)
        if labels_full.size != X.shape[0]:
            ax.set_axis_off()
            legend_payload.append((int(k), [], []))
            continue
        lv = labels_full[m_ok]
        if lv.size != Y.shape[0]:
            ax.set_axis_off()
            legend_payload.append((int(k), [], []))
            continue

        _draw_cluster_scatter_2d(
            ax=ax,
            Y=Y,
            labels=lv,
            weights=wv,
            segment_names=(segment_names_by_k or {}).get(int(k), []),
            title=f"{int(k)} skupienia",
            show_legend=False,
            legend_outside=False,
        )
        handles, labels_leg = ax.get_legend_handles_labels()
        legend_payload.append((int(k), list(handles), [str(x) for x in labels_leg]))

    for idx in range(n_pan, n_rows * n_cols):
        row = int(idx // n_cols)
        col = int(idx % n_cols)
        ax_blank = fig.add_subplot(plot_grid[row, col])
        ax_blank.set_axis_off()

    for idx, (k_val, handles, labels_leg) in enumerate(legend_payload):
        ax_leg = fig.add_subplot(legend_grid[idx, 0])
        ax_leg.set_axis_off()
        ax_leg.text(
            0.0, 1.02,
            f"K={int(k_val)}",
            transform=ax_leg.transAxes,
            ha="left", va="bottom",
            fontsize=9.2, fontweight="bold", color="#0f172a",
        )
        if handles:
            ax_leg.legend(
                handles,
                labels_leg,
                title="Skupienie",
                loc="upper left",
                frameon=True,
                facecolor="#ffffff",
                edgecolor="#d1d9e6",
                fontsize=8.0,
                title_fontsize=9.0,
                borderaxespad=0.0,
                handlelength=1.5,
                labelspacing=0.50,
            )

    fig.suptitle("Analiza skupień metodą k-średnich (porównanie różnych K)", fontsize=16, fontweight="bold", y=0.995)
    fig.subplots_adjust(left=0.042, right=0.995, top=0.945, bottom=0.058)
    fig.savefig(outpath, dpi=PLOT_DPI)
    plt.close(fig)


def _cluster_quality_table_html(quality_df: pd.DataFrame, k_best: int) -> str:
    if quality_df is None or len(quality_df) == 0:
        return (
            "<div class='card' style='margin-top:12px;'>"
            "<div class='small'>Brak danych do doboru liczby skupień.</div>"
            "</div>"
        )

    qdf = quality_df.copy().sort_values("k").reset_index(drop=True)
    rows: List[Dict[str, Any]] = []

    def _sf(x: Any, default: float = float("nan")) -> float:
        try:
            v = float(x)
            return v if np.isfinite(v) else float(default)
        except Exception:
            return float(default)

    for _, row in qdf.iterrows():
        k = int(round(_sf(row.get("k"), 0.0)))
        k_txt = f"<b>{k}</b> (wybrane)" if int(k) == int(k_best) else str(k)

        sil = _sf(row.get("silhouette"), float("nan"))
        wss = _sf(row.get("wss"), float("nan"))
        min_share_pct = 100.0 * _sf(row.get("min_share"), 0.0)
        max_share_pct = 100.0 * _sf(row.get("max_share"), 0.0)
        drop = _sf(row.get("wss_drop_pct"), float("nan"))

        rows.append({
            "K": k_txt,
            "Silhouette": f"{sil:.3f}" if np.isfinite(sil) else "—",
            "WSS": f"{wss:.2f}" if np.isfinite(wss) else "—",
            "Min udział": f"{min_share_pct:.1f}%",
            "Max udział": f"{max_share_pct:.1f}%",
            "Spadek WSS vs K-1": f"{drop:.1f}%" if np.isfinite(drop) else "—",
        })

    tbl = pd.DataFrame(rows).to_html(index=False, border=0, classes="tbl", escape=False)
    return (
        "<div class='card' style='margin-top:12px;'>"
        "<h3 style='margin:0 0 8px 0;'>Dobór liczby skupień (k-średnich)</h3>"
        "<div class='small'>"
        "Wybieramy K na podstawie silhouette (im wyżej, tym lepiej) z kontrolą udziałów skupień "
        "i krzywej elbow (WSS)."
        "</div>"
        f"{tbl}"
        "</div>"
    )


def build_cluster_pack_kmeans(tab_key: str,
                              metry: Optional[pd.DataFrame],
                              P: np.ndarray, E: np.ndarray, G: np.ndarray, w: np.ndarray,
                              settings: Settings,
                              brand_values: Dict[str, str],
                              outdir: Path,
                              seed_offset: int = 0) -> Dict[str, Any]:
    """
    Klasyczna analiza skupień (k-średnich) dla profilu P:
    - cechy: standaryzowany profil 12 archetypów/wartości (P),
    - dobór K: najwyższa silhouette (z kontrolą min. udziału),
    - prezentacja: profile + matryca w tym samym stylu, co zakładka Segmenty.
    """
    _ = tab_key

    P = np.asarray(P, dtype=float)
    E = np.asarray(E, dtype=float)
    G = np.asarray(G, dtype=float)
    w = np.asarray(w, dtype=float).reshape(-1)
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    if P.ndim != 2 or P.shape[0] == 0:
        raise RuntimeError("build_cluster_pack_kmeans(): brak poprawnej macierzy P.")
    if P.shape[0] != w.size:
        raise RuntimeError("build_cluster_pack_kmeans(): długość wag nie zgadza się z liczbą respondentów.")

    Xz = _wstandardize(P, w)
    Xz = np.nan_to_num(Xz, nan=0.0)
    n = int(Xz.shape[0])

    k_floor = 2
    k_cap = max(k_floor, min(12, int(settings.clusters_k_max)))
    req_k_min = max(k_floor, int(settings.clusters_k_min))
    req_k_max = max(req_k_min, int(settings.clusters_k_max))

    fit_k_min = min(req_k_min, max(2, n - 1))
    fit_k_max = min(req_k_max, max(2, n - 1), k_cap)
    fit_k_min = max(2, min(fit_k_min, fit_k_max))

    if fit_k_max < fit_k_min:
        fit_k_max = fit_k_min

    quality_rows: List[Dict[str, Any]] = []
    labels_by_k: Dict[int, np.ndarray] = {}

    for k in range(int(fit_k_min), int(fit_k_max) + 1):
        labels_try, centroids_try = _weighted_kmeans(
            Xz, w,
            k=int(k),
            seed=int(settings.random_seed + seed_offset + 211 * int(k)),
            n_init=14,
            max_iter=320
        )
        labels_try = np.asarray(labels_try, dtype=int).reshape(-1)
        labels_by_k[int(k)] = labels_try.copy()

        uniq = [int(x) for x in np.unique(labels_try) if int(x) >= 0]
        shares: List[float] = []
        for sid in uniq:
            m = labels_try == sid
            shares.append(float(np.sum(w[m]) / (np.sum(w) + 1e-12)))

        min_share = float(min(shares)) if shares else 0.0
        max_share = float(max(shares)) if shares else 0.0

        sil = float(
            _silhouette_basic(
                Xz, labels_try,
                weights=w,
                sample_max=int(settings.silhouette_sample_max),
                seed=int(settings.random_seed + seed_offset + 223 * int(k))
            )
        )
        wss = float(_weighted_cluster_inertia(Xz, labels_try, centroids_try, w))

        quality_rows.append({
            "k": int(k),
            "silhouette": float(sil),
            "wss": float(wss),
            "min_share": float(min_share),
            "max_share": float(max_share),
        })

    if not quality_rows:
        raise RuntimeError("build_cluster_pack_kmeans(): brak rozwiązań k-means do oceny.")

    quality_rows = sorted(quality_rows, key=lambda x: int(x.get("k", 0)))
    prev_wss: Optional[float] = None

    def _sf(x: Any, default: float = float("nan")) -> float:
        try:
            v = float(x)
            return v if np.isfinite(v) else float(default)
        except Exception:
            return float(default)

    for row in quality_rows:
        curr_wss = _sf(row.get("wss"), float("nan"))
        if prev_wss is None or (not np.isfinite(prev_wss)) or prev_wss <= 0:
            row["wss_drop_pct"] = float("nan")
        else:
            row["wss_drop_pct"] = float(100.0 * (prev_wss - curr_wss) / (prev_wss + 1e-12))
        prev_wss = curr_wss

    k_pref = int(max(fit_k_min, min(fit_k_max, int(settings.clusters_k_default))))
    min_share_pref = max(0.02, float(settings.clusters_min_share_default))

    def _cand_key(row: Dict[str, Any]) -> Tuple[Any, ...]:
        min_share = _sf(row.get("min_share"), 0.0)
        sil = _sf(row.get("silhouette"), -1.0)
        k = int(round(_sf(row.get("k"), float(fit_k_min))))

        # Priorytet:
        # 1) silhouette
        # 2) brak mikro-skupień
        # 3) K bliżej domyślnego
        # 4) przy remisie mniejsze K
        return (
            sil,
            1 if min_share >= min_share_pref else 0,
            min_share,
            -abs(k - k_pref),
            -k,
        )

    best_row = max(quality_rows, key=_cand_key)
    k_best_requested = int(best_row.get("k", fit_k_min))
    quality_df = pd.DataFrame(quality_rows)

    # Wykresy diagnostyczne
    plot_files = _plot_cluster_k_diagnostics(quality_df, outdir=outdir, prefix="SKUPIENIA")
    panel_png = "SKUPIENIA_MAPY_K_POROWNANIE.png"
    by_k: Dict[str, Dict[str, Any]] = {}
    labels_by_k_ranked: Dict[int, np.ndarray] = {}
    segment_names_by_k: Dict[int, List[str]] = {}

    for kx in sorted(int(k0) for k0 in labels_by_k.keys()):
        labels_raw_k = np.asarray(labels_by_k.get(int(kx), np.zeros(n, dtype=int)), dtype=int).reshape(-1)
        labels_ranked_k, _id_map_k = _reorder_labels_by_weight(labels_raw_k, w)

        segs_k = _segment_profiles_from_ranked_labels(
            labels_ranked=labels_ranked_k,
            metry=metry,
            P=P, E=E, G=G, w=w,
            brand_values=brand_values
        )
        if not segs_k:
            continue

        segs_k, labels_ranked_k, _labels_eff_k, _rank_map_k = _relabel_segments_by_weighted_share(
            segs=segs_k,
            labels_ranked=labels_ranked_k,
            labels_ranked_effective=None,
        )

        seg_names_arche_k = [_segment_name_pair(s)[0] for s in segs_k]
        segment_names_by_k[int(kx)] = [str(x) for x in seg_names_arche_k]
        labels_by_k_ranked[int(kx)] = np.asarray(labels_ranked_k, dtype=int).reshape(-1)

        profile_prefix_k = f"CLUSTER_PROFILE_K{int(kx)}"
        for s in segs_k:
            seg_rank = int(_safe_float(s.get("segment_rank", s.get("segment_id", 0))))
            seg_num = seg_rank + 1

            try:
                profile_share = np.asarray(s.get("Pm_share_pct", []), dtype=float).reshape(-1)
            except Exception:
                profile_share = np.asarray([], dtype=float)

            if profile_share.shape[0] != len(ARCHETYPES):
                profile_share = np.asarray(_pm_profile_share_pct(s.get("Pm", [])), dtype=float)
            if profile_share.shape[0] != len(ARCHETYPES):
                profile_share = np.asarray([0.0] * len(ARCHETYPES), dtype=float)

            _plot_segment_profile_wheel(
                outpath=outdir / f"{profile_prefix_k}_{int(seg_num)}_values.png",
                pm_share_pct=profile_share,
                brand_values=brand_values,
                mode="values",
                value_suffix=""
            )

        projection_png_k = f"SKUPIENIA_MAPA_PCA_K{int(kx)}.png"
        try:
            _plot_cluster_projection_2d(
                Xz=Xz,
                labels_ranked=labels_ranked_k,
                weights=w,
                segment_names=segment_names_by_k.get(int(kx), []),
                outpath=outdir / projection_png_k
            )
        except Exception:
            projection_png_k = ""

        matrix_html_arche_k = _render_segment_matrix_html(
            segs_k,
            brand_values,
            mode="arche",
            top_n=int(len(segs_k)),
            segment_threshold_overrides=settings.segment_hit_threshold_overrides
        )
        matrix_html_values_k = _render_segment_matrix_html(
            segs_k,
            brand_values,
            mode="values",
            top_n=int(len(segs_k)),
            segment_threshold_overrides=settings.segment_hit_threshold_overrides
        )

        by_k[str(int(kx))] = {
            "k": int(kx),
            "projection_png": str(projection_png_k),
            "profiles_html_arche": _profiles_to_html(
                segs_k, brand_values, mode="arche",
                city_label=settings.city_label,
                population_15_plus=settings.population_15_plus,
                segment_threshold_overrides=settings.segment_hit_threshold_overrides,
                profile_chart_prefix=profile_prefix_k,
                profile_box_label="◎ Profil skupienia (siła wartości, skala: 0-100)"
            ),
            "profiles_html_values": _profiles_to_html(
                segs_k, brand_values, mode="values",
                city_label=settings.city_label,
                population_15_plus=settings.population_15_plus,
                segment_threshold_overrides=settings.segment_hit_threshold_overrides,
                profile_chart_prefix=profile_prefix_k,
                profile_box_label="◎ Profil skupienia (siła wartości, skala: 0-100)"
            ),
            "matrix_html_arche": matrix_html_arche_k,
            "matrix_html_values": matrix_html_values_k,
            "profiles_payload": [dict(s) for s in segs_k],
            "segment_names_arche": [str(x) for x in seg_names_arche_k],
            "labels_ranked": np.asarray(labels_ranked_k, dtype=int).reshape(-1).tolist(),
        }

    if not by_k:
        raise RuntimeError("build_cluster_pack_kmeans(): nie udało się zbudować profili skupień.")

    sel_key = str(int(k_best_requested))
    if sel_key not in by_k:
        avail_keys = sorted(by_k.keys(), key=lambda z: int(z))
        sel_key = str(avail_keys[0])
        k_best_requested = int(sel_key)

    sel_item = dict(by_k.get(sel_key, {}))
    segs = [dict(x) for x in (sel_item.get("profiles_payload", []) or [])]
    labels_ranked = np.asarray(sel_item.get("labels_ranked", []), dtype=int).reshape(-1)
    k_best = int(sel_item.get("k", len(segs)))

    projection_png = "SKUPIENIA_MAPA_PCA.png"
    try:
        _plot_cluster_projection_2d(
            Xz=Xz,
            labels_ranked=labels_ranked,
            weights=w,
            segment_names=segment_names_by_k.get(int(k_best), []),
            outpath=outdir / projection_png
        )
    except Exception:
        projection_png = str(sel_item.get("projection_png", "")) or "SKUPIENIA_MAPA_PCA.png"

    try:
        pref_k = [3, 4, 5, 6]
        avail_k = sorted(int(kx) for kx in labels_by_k_ranked.keys())
        k_show = [k for k in pref_k if k in avail_k]
        if len(k_show) < 2:
            if len(avail_k) <= 4:
                k_show = avail_k
            else:
                pick_idx = np.linspace(0, len(avail_k) - 1, 4)
                k_show = sorted({avail_k[int(round(i))] for i in pick_idx})

        _plot_cluster_k_panels(
            Xz=Xz,
            labels_by_k=labels_by_k_ranked,
            segment_names_by_k=segment_names_by_k,
            weights=w,
            k_values=k_show,
            outpath=outdir / panel_png
        )
    except Exception:
        panel_png = ""

    # Eksport tabeli jakości K
    quality_export = quality_df.copy().sort_values("k").reset_index(drop=True)
    quality_export["min_share_pct"] = 100.0 * pd.to_numeric(quality_export["min_share"], errors="coerce")
    quality_export["max_share_pct"] = 100.0 * pd.to_numeric(quality_export["max_share"], errors="coerce")
    quality_export.to_csv(outdir / "SKUPIENIA_kryteria_k.csv", index=False, encoding="utf-8-sig")

    return {
        "tab_key": tab_key,
        "k_best": int(k_best),
        "k_requested": int(k_best_requested),
        "k_pref": int(k_pref),
        "k_min": int(fit_k_min),
        "k_max": int(fit_k_max),
        "k_default_ui": int(k_best_requested),
        "solutions": quality_rows,
        "quality_html": _cluster_quality_table_html(quality_df, k_best=k_best_requested),
        "profiles_html_arche": str(sel_item.get("profiles_html_arche", "")),
        "profiles_html_values": str(sel_item.get("profiles_html_values", "")),
        "matrix_html_arche": str(sel_item.get("matrix_html_arche", "")),
        "matrix_html_values": str(sel_item.get("matrix_html_values", "")),
        "silhouette_png": str(plot_files.get("silhouette_png", "SKUPIENIA_DOBOR_K_SILHOUETTE.png")),
        "elbow_png": str(plot_files.get("elbow_png", "SKUPIENIA_DOBOR_K_ELBOW.png")),
        "projection_png": str(projection_png),
        "panel_png": str(panel_png),
        "labels_ranked": labels_ranked.astype(int).tolist(),
        "profiles_payload": segs,
        "by_k": by_k,
    }


def _compute_segment_smart_state(
        segs: List[Dict[str, Any]],
        top_n: Optional[int] = None,
        min_beats: int = 3,
        min_gap: float = 0.15,
        min_positive: float = 0.10,
        strong_min: float = 0.35,
        core_min: float = 0.70,
        top_rank_limit: int = 2,
        special_threshold_overrides: Optional[Dict[Any, Any]] = None
) -> Dict[str, Any]:
    """
    Wspólny stan porównawczy segmentów oparty WYŁĄCZNIE na Pm.
    To jest baza pod mapy przewag i dalsze matryce porównawcze.
    """
    segs = list(segs or [])
    if not segs:
        return {
            "segs": [],
            "values": np.zeros((len(ARCHETYPES), 0), dtype=float),
            "beats": np.zeros((len(ARCHETYPES), 0), dtype=int),
            "ranks": np.zeros((len(ARCHETYPES), 0), dtype=int),
            "hit": np.zeros((len(ARCHETYPES), 0), dtype=bool),
            "tier": np.zeros((len(ARCHETYPES), 0), dtype=int),
            "effective_min_beats": 0,
        }

    try:
        top_n = max(1, int(top_n)) if top_n is not None else len(segs)
    except Exception:
        top_n = len(segs)

    segs = segs[:top_n]
    k = len(segs)
    a_cnt = len(ARCHETYPES)

    other_cnt = max(0, k - 1)

    # Reguła „bije więcej niż 50% innych segmentów” ma sens dopiero od 4 segmentów.
    # Przy 3 segmentach (2 „inne”) wymagamy progu >=2, czyli segment musi pobić oba pozostałe.
    if other_cnt >= 3:
        effective_min_beats = max(1, int(math.floor(other_cnt * 0.5)) + 1)
    elif other_cnt == 2:
        effective_min_beats = 2
    else:
        effective_min_beats = max(1, other_cnt)

    effective_top_rank = max(1, min(int(top_rank_limit), k))

    values_matrix = np.zeros((a_cnt, k), dtype=float)
    beats_matrix = np.zeros((a_cnt, k), dtype=int)
    rank_matrix = np.zeros((a_cnt, k), dtype=int)
    hit_matrix = np.zeros((a_cnt, k), dtype=bool)
    tier_matrix = np.zeros((a_cnt, k), dtype=int)

    special_rules = _resolve_segment_smart_rules(special_threshold_overrides)

    vecs = [_segment_pm_vector(s) for s in segs]

    for a_idx in range(a_cnt):
        row_vals: List[float] = []

        for col_idx in range(k):
            v = float(vecs[col_idx][a_idx]) if np.isfinite(vecs[col_idx][a_idx]) else 0.0
            row_vals.append(v)
            values_matrix[a_idx, col_idx] = v

        order = sorted(range(k), key=lambda j: (row_vals[j], -j), reverse=True)
        for pos, col_idx in enumerate(order, start=1):
            rank_matrix[a_idx, col_idx] = pos

        other_cnt_max = max(0, k - 1)

        for col_idx, val in enumerate(row_vals):
            beats = 0
            for other_idx, other_val in enumerate(row_vals):
                if other_idx == col_idx:
                    continue
                if float(val) >= (float(other_val) + float(min_gap)):
                    beats += 1

            beats_matrix[a_idx, col_idx] = beats
            row_rank = int(rank_matrix[a_idx, col_idx])

            base_hit = (
                    (beats >= effective_min_beats)
                    and (float(val) >= float(min_positive))
                    and (
                            row_rank <= effective_top_rank
                            or float(val) >= float(strong_min)
                    )
            )

            hit = bool(base_hit)

            rule_key = (other_cnt_max, beats, row_rank)
            if rule_key in special_rules:
                min_val, use_ge = special_rules[rule_key]
                if use_ge:
                    hit = bool(float(val) >= float(min_val))
                else:
                    hit = bool(float(val) > float(min_val))

            hit_matrix[a_idx, col_idx] = bool(hit)

            if not hit:
                tier_matrix[a_idx, col_idx] = 0
            else:
                if (row_rank == 1) and (beats == other_cnt_max) and (float(val) >= float(core_min)):
                    tier_matrix[a_idx, col_idx] = 3
                elif (row_rank <= effective_top_rank) or (float(val) >= float(strong_min)):
                    tier_matrix[a_idx, col_idx] = 2
                else:
                    tier_matrix[a_idx, col_idx] = 1

    return {
        "segs": segs,
        "values": values_matrix,
        "beats": beats_matrix,
        "ranks": rank_matrix,
        "hit": hit_matrix,
        "tier": tier_matrix,
        "effective_min_beats": int(effective_min_beats),
    }


def _recompute_segment_sizes_from_active_hits(
        segs: List[Dict[str, Any]],
        P: np.ndarray,
        w: np.ndarray,
        segment_threshold_overrides: Optional[Dict[Any, Any]] = None
) -> Tuple[List[Dict[str, Any]], Optional[np.ndarray]]:
    """
    Jeśli użytkownik ustawi nadpisania progów hitów (segment_hit_threshold_overrides),
    przeliczamy udział i N segmentów na bazie realnego przypisania respondentów
    do segmentów wg aktywnych przewag.

    Dzięki temu zmiana progów wpływa spójnie na:
    - mapę przewag,
    - tabelę „Segmenty - przewagi naprawdę istotne”,
    - tabelę „Zestawienie segmentów” (N / udział).
    """
    segs_in = [dict(s) for s in (segs or []) if isinstance(s, dict)]
    if not segs_in:
        return list(segs or []), None

    parsed_overrides = _parse_segment_threshold_overrides(segment_threshold_overrides)
    if not parsed_overrides:
        return list(segs), None

    P_arr = np.asarray(P, dtype=float)
    if P_arr.ndim != 2 or P_arr.shape[1] != len(ARCHETYPES):
        return list(segs), None

    n_resp = int(P_arr.shape[0])
    if n_resp <= 0:
        return list(segs), None

    w_arr = np.asarray(w, dtype=float).reshape(-1)
    if w_arr.size != n_resp:
        w_arr = np.ones(n_resp, dtype=float)
    w_arr = np.where(np.isfinite(w_arr) & (w_arr > 0), w_arr, 1.0)

    state = _compute_segment_smart_state(
        segs=segs_in,
        top_n=len(segs_in),
        min_beats=1,
        min_gap=0.15,
        min_positive=0.10,
        strong_min=0.35,
        core_min=0.70,
        top_rank_limit=2,
        special_threshold_overrides=segment_threshold_overrides,
    )

    hit = np.asarray(state.get("hit"), dtype=bool)
    vals = np.asarray(state.get("values"), dtype=float)
    k = int(len(segs_in))

    if hit.shape != (len(ARCHETYPES), k):
        return list(segs), None
    if vals.shape != (len(ARCHETYPES), k):
        vals = np.zeros((len(ARCHETYPES), k), dtype=float)

    vals = np.where(np.isfinite(vals), vals, 0.0)
    P_num = np.where(np.isfinite(P_arr), P_arr, 0.0)

    idx_list: List[np.ndarray] = []
    wgt_list: List[np.ndarray] = []
    hit_count = np.zeros(k, dtype=int)

    for j in range(k):
        idx = np.where(hit[:, j])[0]
        if idx.size == 0:
            idx = np.asarray([int(np.argmax(vals[:, j]))], dtype=int)

        hit_count[j] = int(idx.size)
        vj = np.asarray(vals[idx, j], dtype=float)
        wj = np.clip(vj, 0.0, None)

        if float(np.sum(wj)) <= 1e-12:
            wj = np.abs(vj)
        if float(np.sum(wj)) <= 1e-12:
            wj = np.ones(len(idx), dtype=float)

        wj = wj / float(np.sum(wj))
        idx_list.append(idx.astype(int))
        wgt_list.append(wj.astype(float))

    scores = np.full((n_resp, k), -1e18, dtype=float)
    for j in range(k):
        idx = idx_list[j]
        wj = wgt_list[j]
        try:
            scores[:, j] = np.dot(P_num[:, idx], wj)
        except Exception:
            scores[:, j] = -1e18

    if not np.any(np.isfinite(scores)):
        return list(segs), None

    scores = np.where(np.isfinite(scores), scores, -1e18)
    labels_eff = np.argmax(scores, axis=1).astype(int)

    n_new = np.bincount(labels_eff, minlength=k).astype(int)
    total_w = float(np.sum(w_arr))
    share_new = np.zeros(k, dtype=float)
    if total_w > 1e-12:
        for j in range(k):
            share_new[j] = float(np.sum(w_arr[labels_eff == j])) / total_w * 100.0

    out: List[Dict[str, Any]] = []
    for j, s in enumerate(segs_in):
        ss = dict(s)
        ss["n_base"] = int(_safe_float(ss.get("n", 0)))
        ss["share_pct_base"] = float(_safe_float(ss.get("share_pct", 0.0)))
        ss["n"] = int(n_new[j])
        ss["share_pct"] = float(share_new[j])
        ss["segment_size_source"] = "active_hits"
        ss["active_hits_count"] = int(hit_count[j])
        out.append(ss)

    return out, labels_eff


def plot_segment_quadrant_map_fixed(segs: List[Dict[str, Any]],
                                    brand_values: Dict[str, str],
                                    outdir: Path,
                                    fname_base: str = "SEGMENTY_META_MAPA_STALA",
                                    P_source: Optional[np.ndarray] = None,
                                    segs_logic: Optional[List[Dict[str, Any]]] = None,
                                    segment_threshold_overrides: Optional[Dict[Any, Any]] = None,
                                    segment_outline_style: str = "classic") -> None:
    """
    Mapa segmentów oparta na tym samym źródle prawdy co macierze:
    - archetypy / wartości rysujemy w układzie DATA (jeśli P_source jest dostępne),
      a tylko awaryjnie w układzie stałego koła;
    - obrys segmentu obejmuje te archetypy / wartości, które są realnie
      wyróżnione w segmencie na bazie Pm;
    - logika obrysu jest liczona względem pełnego modelu (segs_logic),
      a nie tylko względem aktualnie widocznych pierwszych N segmentów.
    """
    segs = list(segs or [])
    if not segs:
        return

    segs_logic = list(segs_logic or segs)
    if not segs_logic:
        segs_logic = list(segs)

    outline_style_raw = str(segment_outline_style or "").strip().lower()
    outline_style = "smooth" if outline_style_raw in {"smooth", "plamowy", "plama", "concave", "blob"} else "classic"

    try:
        P_arr = np.asarray(P_source, dtype=float) if P_source is not None else None
    except Exception:
        P_arr = None

    axes_meta: Dict[str, str]
    if isinstance(P_arr, np.ndarray) and P_arr.ndim == 2 and P_arr.shape[1] == len(ARCHETYPES) and len(P_arr) >= 8:
        coords, meta = build_value_space_from_P(P_arr, list(ARCHETYPES))
        if isinstance(meta, dict):
            axes_meta = dict(meta.get("axes", {}))
        else:
            axes_meta = {}
    else:
        coords, _meta = build_value_space_fixed_circle(list(ARCHETYPES))
        axes_meta = {
            "x_left": "Niezależność",
            "x_right": "Ludzie",
            "y_up": "Zmiana",
            "y_down": "Porządek",
        }

    coords = np.asarray(coords, dtype=float)
    if coords.shape != (len(ARCHETYPES), 2):
        return

    # Źródło prawdy dla obrysu = pełny model segmentów, a nie tylko widoczny wycinek.
    smart_state = _compute_segment_smart_state(
        segs=segs_logic,
        top_n=len(segs_logic),
        min_beats=1,
        min_gap=0.15,
        min_positive=0.10,
        strong_min=0.35,
        core_min=0.70,
        top_rank_limit=2,
        special_threshold_overrides=segment_threshold_overrides
    )

    val_matrix_all = np.asarray(
        smart_state.get("values", np.zeros((len(ARCHETYPES), len(segs_logic)), dtype=float)),
        dtype=float
    )
    hit_matrix_all = np.asarray(
        smart_state.get("hit", np.zeros((len(ARCHETYPES), len(segs_logic)), dtype=bool)),
        dtype=bool
    )

    if val_matrix_all.shape != (len(ARCHETYPES), len(segs_logic)):
        val_matrix_all = np.zeros((len(ARCHETYPES), len(segs_logic)), dtype=float)
    if hit_matrix_all.shape != (len(ARCHETYPES), len(segs_logic)):
        hit_matrix_all = np.zeros((len(ARCHETYPES), len(segs_logic)), dtype=bool)

    x_vals = coords[:, 0]
    y_vals = coords[:, 1]
    xmin = float(np.nanmin(x_vals))
    xmax = float(np.nanmax(x_vals))
    ymin = float(np.nanmin(y_vals))
    ymax = float(np.nanmax(y_vals))
    xr = max(1.0, xmax - xmin)
    yr = max(1.0, ymax - ymin)

    q_tl = "TRANSFORMACJA"
    q_tr = "ENERGIA WSPÓLNOTY"
    q_bl = "SPRAWCZOŚĆ"
    q_br = "OPIEKUŃCZY ŁAD"

    def _logic_col_idx(seg_obj: Dict[str, Any], fallback_idx: int) -> int:
        try:
            seg_rank = int(seg_obj.get("segment_rank", fallback_idx))
        except Exception:
            seg_rank = fallback_idx

        for idx_logic, s_logic in enumerate(segs_logic):
            try:
                if int(s_logic.get("segment_rank", idx_logic)) == seg_rank:
                    return idx_logic
            except Exception:
                pass

        seg_label = str(seg_obj.get("segment_label", "") or "")
        if seg_label:
            for idx_logic, s_logic in enumerate(segs_logic):
                if str(s_logic.get("segment_label", "") or "") == seg_label:
                    return idx_logic

        if val_matrix_all.shape[1] <= 0:
            return 0
        return int(min(max(0, fallback_idx), val_matrix_all.shape[1] - 1))

    def _convex_hull(points_xy: np.ndarray) -> np.ndarray:
        pts = np.asarray(points_xy, dtype=float)
        if pts.ndim != 2 or pts.shape[1] != 2:
            return np.zeros((0, 2), dtype=float)

        uniq_pts = np.unique(np.round(pts, 10), axis=0)
        if len(uniq_pts) <= 1:
            return uniq_pts

        pts_list = sorted((float(px), float(py)) for px, py in uniq_pts)

        def _cross(o, a, b):
            return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

        lower = []
        for p in pts_list:
            while len(lower) >= 2 and _cross(lower[-2], lower[-1], p) <= 0:
                lower.pop()
            lower.append(p)

        upper = []
        for p in reversed(pts_list):
            while len(upper) >= 2 and _cross(upper[-2], upper[-1], p) <= 0:
                upper.pop()
            upper.append(p)

        hull = lower[:-1] + upper[:-1]
        return np.asarray(hull, dtype=float)

    def _smooth_closed_polygon(poly_xy: np.ndarray, passes: int = 2) -> np.ndarray:
        poly = np.asarray(poly_xy, dtype=float)
        if poly.ndim != 2 or poly.shape[1] != 2 or len(poly) < 3:
            return poly

        pts = poly[:-1].copy() if np.allclose(poly[0], poly[-1]) else poly.copy()

        for _ in range(max(1, int(passes))):
            if len(pts) < 3:
                break
            new_pts = []
            n_pts = len(pts)
            for i in range(n_pts):
                p0 = pts[i]
                p1 = pts[(i + 1) % n_pts]
                q = (0.75 * p0) + (0.25 * p1)
                r = (0.25 * p0) + (0.75 * p1)
                new_pts.extend([q, r])
            pts = np.asarray(new_pts, dtype=float)

        return np.vstack([pts, pts[:1]])


    def _simplify_closed_polygon(poly_xy: np.ndarray, eps: float) -> np.ndarray:
        poly = np.asarray(poly_xy, dtype=float)
        if poly.ndim != 2 or poly.shape[1] != 2 or len(poly) < 4:
            return poly

        pts = poly[:-1].copy() if np.allclose(poly[0], poly[-1]) else poly.copy()
        if len(pts) < 3:
            return np.vstack([pts, pts[:1]]) if len(pts) > 0 else np.zeros((0, 2), dtype=float)

        # usuń prawie-dupikaty kolejnych wierzchołków
        dedup = [pts[0]]
        for p in pts[1:]:
            if np.linalg.norm(np.asarray(p) - np.asarray(dedup[-1])) > 1e-9:
                dedup.append(p)
        pts = np.asarray(dedup, dtype=float)
        if len(pts) < 3:
            return np.vstack([pts, pts[:1]])

        def _rdp_open(arr: np.ndarray, epsilon: float) -> np.ndarray:
            n = int(arr.shape[0])
            if n <= 2:
                return arr

            a = arr[0]
            b = arr[-1]
            ab = b - a
            ab2 = float(np.dot(ab, ab))

            max_d = -1.0
            idx = -1
            for i in range(1, n - 1):
                p = arr[i]
                if ab2 <= 1e-18:
                    d = float(np.linalg.norm(p - a))
                else:
                    t = float(np.dot(p - a, ab) / ab2)
                    proj = a + (t * ab)
                    d = float(np.linalg.norm(p - proj))
                if d > max_d:
                    max_d = d
                    idx = i

            if max_d > float(epsilon) and idx > 0:
                left = _rdp_open(arr[:idx + 1], epsilon)
                right = _rdp_open(arr[idx:], epsilon)
                return np.vstack([left[:-1], right])
            return np.vstack([arr[0], arr[-1]])

        # otwieramy kontur od punktu najdalej od centroidu (stabilniejszy wynik)
        ctr = np.mean(pts, axis=0)
        idx0 = int(np.argmax(np.sum((pts - ctr) ** 2, axis=1)))
        open_pts = np.vstack([pts[idx0:], pts[:idx0], pts[idx0:idx0 + 1]])

        simp = _rdp_open(open_pts, max(1e-6, float(eps)))
        if len(simp) < 4:
            return np.vstack([pts, pts[:1]])

        simp_closed = simp.copy()
        if not np.allclose(simp_closed[0], simp_closed[-1]):
            simp_closed = np.vstack([simp_closed, simp_closed[:1]])

        # Dodatkowe odchudzenie kolinearności
        out = [simp_closed[0]]
        for i in range(1, len(simp_closed) - 1):
            p_prev = np.asarray(out[-1], dtype=float)
            p = np.asarray(simp_closed[i], dtype=float)
            p_next = np.asarray(simp_closed[i + 1], dtype=float)
            v1 = p - p_prev
            v2 = p_next - p
            n1 = np.linalg.norm(v1)
            n2 = np.linalg.norm(v2)
            if n1 <= 1e-9 or n2 <= 1e-9:
                continue
            cross = abs(float(v1[0] * v2[1] - v1[1] * v2[0]))
            if cross / (n1 * n2) < 1e-3:
                continue
            out.append(p)
        out.append(simp_closed[-1])

        out_arr = np.asarray(out, dtype=float)
        if len(out_arr) < 4:
            return simp_closed
        return out_arr

    def _circle_poly(center_xy: np.ndarray, radius: float, n_pts: int = 56) -> np.ndarray:
        c = np.asarray(center_xy, dtype=float).reshape(2)
        ang = np.linspace(0.0, 2.0 * math.pi, max(20, int(n_pts)), endpoint=False)
        poly = np.column_stack([
            c[0] + radius * np.cos(ang),
            c[1] + radius * np.sin(ang),
        ])
        return np.vstack([poly, poly[:1]])

    def _finalize_outline_polygon(poly_xy: np.ndarray) -> np.ndarray:
        poly = np.asarray(poly_xy, dtype=float)
        if poly.ndim != 2 or poly.shape[1] != 2 or len(poly) < 3:
            return poly

        base = poly.copy()
        if not np.allclose(base[0], base[-1]):
            base = np.vstack([base, base[:1]])

        # Wersja "oplywowa":
        # 1) odszumiamy kontur,
        # 2) wygladzamy kilkoma przejsciami Chaikina,
        # 3) lekko domykamy drobne zygzaki.
        simp_eps = max(0.0028 * max(xr, yr), 0.0028)
        p1 = _simplify_closed_polygon(base, eps=simp_eps)
        if p1.ndim != 2 or p1.shape[1] != 2 or len(p1) < 4:
            p1 = base

        pts = p1[:-1].copy() if np.allclose(p1[0], p1[-1]) else p1.copy()
        if len(pts) < 4:
            return _smooth_closed_polygon(p1, passes=3)

        p2 = _smooth_closed_polygon(p1, passes=3)
        p3 = _simplify_closed_polygon(p2, eps=max(0.0008 * max(xr, yr), 0.0008))
        if p3.ndim == 2 and p3.shape[1] == 2 and len(p3) >= 4:
            return _smooth_closed_polygon(p3, passes=2)
        return p2
    def _segment_outline_polygon(
            points_xy: np.ndarray,
            avoid_xy: Optional[np.ndarray] = None
    ) -> np.ndarray:
        pts = np.asarray(points_xy, dtype=float)
        if pts.ndim != 2 or pts.shape[1] != 2 or len(pts) == 0:
            return np.zeros((0, 2), dtype=float)

        uniq = np.unique(np.round(pts, 10), axis=0)
        if len(uniq) == 0:
            return np.zeros((0, 2), dtype=float)

        if len(uniq) == 1:
            return _circle_poly(
                center_xy=uniq[0],
                radius=max(0.044 * max(xr, yr), 0.034),
                n_pts=64,
            )

        def _poly_area(poly_xy: np.ndarray) -> float:
            p = np.asarray(poly_xy, dtype=float)
            if p.ndim != 2 or p.shape[1] != 2 or len(p) < 3:
                return 0.0
            if not np.allclose(p[0], p[-1]):
                p = np.vstack([p, p[:1]])
            x = p[:, 0]
            y = p[:, 1]
            return 0.5 * float(np.sum(x[:-1] * y[1:] - x[1:] * y[:-1]))

        pad_x = max(0.040 * xr, 0.030)
        pad_y = max(0.040 * yr, 0.030)
        ang = np.linspace(0.0, 2.0 * math.pi, 68, endpoint=False)

        # Szeroka baza wokol punktow segmentu (bardziej "plamowa" niz ostra linia).
        cloud_parts = []
        for px, py in uniq:
            cloud_parts.append(
                np.column_stack([
                    float(px) + pad_x * np.cos(ang),
                    float(py) + pad_y * np.sin(ang),
                ])
            )

        cloud = np.vstack(cloud_parts) if cloud_parts else np.zeros((0, 2), dtype=float)
        hull = _convex_hull(cloud)
        if len(hull) == 0:
            return np.zeros((0, 2), dtype=float)

        hull_closed = np.vstack([hull, hull[:1]])

        avoid_arr = np.asarray(avoid_xy, dtype=float) if avoid_xy is not None else np.zeros((0, 2), dtype=float)
        if avoid_arr.ndim != 2 or avoid_arr.shape[1] != 2:
            avoid_arr = np.zeros((0, 2), dtype=float)

        if outline_style == "classic":
            return _finalize_outline_polygon(hull_closed)

        if len(avoid_arr) == 0:
            return _finalize_outline_polygon(hull_closed)

        x0 = float(np.min(hull[:, 0]) - (1.55 * pad_x))
        x1 = float(np.max(hull[:, 0]) + (1.55 * pad_x))
        y0 = float(np.min(hull[:, 1]) - (1.55 * pad_y))
        y1 = float(np.max(hull[:, 1]) + (1.55 * pad_y))

        nx = int(min(260, max(150, 116 + (len(uniq) * 18))))
        ny = int(min(260, max(150, 116 + (len(uniq) * 18))))
        gx = np.linspace(x0, x1, nx)
        gy = np.linspace(y0, y1, ny)
        Xg, Yg = np.meshgrid(gx, gy)

        from matplotlib.path import Path as _MplPath

        pth = _MplPath(hull_closed)
        flat_xy = np.column_stack([Xg.ravel(), Yg.ravel()])
        mask_base = pth.contains_points(flat_xy, radius=max(pad_x, pad_y) * 0.12).reshape(Xg.shape)

        own_rx = 1.08 * pad_x
        own_ry = 1.08 * pad_y
        own_mask = np.zeros_like(mask_base, dtype=bool)
        for px, py in uniq:
            own_mask |= ((((Xg - float(px)) / own_rx) ** 2 + ((Yg - float(py)) / own_ry) ** 2) <= 1.0)

        # Carving: lokalnie odejmujemy tylko obce punkty blisko obrysu.
        avoid_rx = 0.72 * pad_x
        avoid_ry = 0.72 * pad_y
        avoid_mask = np.zeros_like(mask_base, dtype=bool)

        x_margin = 1.9 * pad_x
        y_margin = 1.9 * pad_y
        for qx, qy in avoid_arr:
            if (
                (float(qx) < x0 - x_margin) or (float(qx) > x1 + x_margin)
                or (float(qy) < y0 - y_margin) or (float(qy) > y1 + y_margin)
            ):
                continue

            hole = ((((Xg - float(qx)) / avoid_rx) ** 2 + ((Yg - float(qy)) / avoid_ry) ** 2) <= 1.0)
            avoid_mask |= hole

        mask = (mask_base & (~avoid_mask)) | own_mask

        try:
            from scipy import ndimage as _ndi
            st = np.ones((3, 3), dtype=bool)
            mask = _ndi.binary_closing(mask, structure=st, iterations=3)
            mask = _ndi.binary_dilation(mask, structure=st, iterations=2)
            mask = _ndi.binary_fill_holes(mask)

            lab, n_lab = _ndi.label(mask)
            if n_lab > 1:
                best_lab = 0
                best_key = (-1, -1)
                for lid in range(1, int(n_lab) + 1):
                    comp = (lab == lid)
                    overlap = int(np.count_nonzero(comp & own_mask))
                    area = int(np.count_nonzero(comp))
                    key = (overlap, area)
                    if key > best_key:
                        best_key = key
                        best_lab = int(lid)
                if best_lab > 0:
                    mask = (lab == best_lab)
        except Exception:
            pass

        if np.count_nonzero(mask) < 24:
            return _finalize_outline_polygon(hull_closed)

        contour_src = mask.astype(float)

        fig_tmp, ax_tmp = plt.subplots(figsize=(1.0, 1.0), dpi=72)
        seg_arrays: List[np.ndarray] = []
        try:
            cs = ax_tmp.contour(Xg, Yg, contour_src, levels=[0.5])
            all_segs = getattr(cs, "allsegs", None)
            if all_segs and len(all_segs) > 0:
                for seg in all_segs[0]:
                    arr = np.asarray(seg, dtype=float)
                    if arr.ndim == 2 and arr.shape[1] == 2 and len(arr) >= 3:
                        seg_arrays.append(arr)

            if (not seg_arrays) and getattr(cs, "collections", None):
                for coll in cs.collections:
                    for p_obj in coll.get_paths():
                        arr = np.asarray(p_obj.vertices, dtype=float)
                        if arr.ndim == 2 and arr.shape[1] == 2 and len(arr) >= 3:
                            seg_arrays.append(arr)
        except Exception:
            seg_arrays = []
        finally:
            plt.close(fig_tmp)

        if not seg_arrays:
            return _finalize_outline_polygon(hull_closed)

        best_poly = None
        best_area = -1.0
        for verts0 in seg_arrays:
            verts = np.asarray(verts0, dtype=float)
            if verts.ndim != 2 or verts.shape[1] != 2 or len(verts) < 3:
                continue
            if not np.allclose(verts[0], verts[-1]):
                verts = np.vstack([verts, verts[:1]])
            ar = abs(_poly_area(verts))
            if ar > best_area:
                best_area = float(ar)
                best_poly = verts

        if best_poly is None:
            return _finalize_outline_polygon(hull_closed)

        return _finalize_outline_polygon(best_poly)
    def _draw(mode: str, fname: str) -> None:
        labels = _display_archetype_labels(ARCHETYPES) if mode == "arche" else [str(brand_values.get(a, a)) for a in ARCHETYPES]

        map_scale = 0.80

        fig, ax = plt.subplots(figsize=(16.6 * map_scale, 10.8 * map_scale), dpi=PLOT_DPI)
        ax.set_facecolor("#ffffff")
        fig.subplots_adjust(left=0.055, right=0.80, top=0.90, bottom=0.09)

        from matplotlib.lines import Line2D

        ax.axhline(0.0, color="#adb5bd", lw=1.2, zorder=1)
        ax.axvline(0.0, color="#adb5bd", lw=1.2, zorder=1)

        quad_boxes = [
            (0.20, 0.975, q_tl, "top"),
            (0.80, 0.975, q_tr, "top"),
            (0.20, 0.025, q_bl, "bottom"),
            (0.80, 0.025, q_br, "bottom"),
        ]

        for bx, by, txt, vpos in quad_boxes:
            ax.text(
                bx, by, txt,
                transform=ax.transAxes,
                fontsize=15.0 * map_scale,      # wielkość czcionki etykiet ćwiartek
                fontweight="bold",
                ha="center",
                va=vpos,
                bbox=dict(
                    boxstyle="round,pad=0.28,rounding_size=0.05",
                    fc="#f1f3f5",
                    ec="#ced4da",
                ),
                color="#343a40",
                zorder=7,
                clip_on=False,
            )

        ax.scatter(coords[:, 0], coords[:, 1], s=48 * (map_scale ** 2), color="#2b6cb0", zorder=3.5)

        # Limity osi liczymy wcześniej, żeby antykolizyjne pozycjonowanie etykiet
        # działało na tym samym zakresie co finalny wykres.
        x_pad = max(0.22 * xr, 0.26)
        y_pad = max(0.16 * yr, 0.28)
        xlim_min = xmin - x_pad
        xlim_max = xmax + x_pad
        ylim_min = ymin - y_pad
        ylim_max = ymax + y_pad

        axis_w_px = max(320.0, (16.6 * map_scale * PLOT_DPI) * (0.80 - 0.055))
        axis_h_px = max(220.0, (10.8 * map_scale * PLOT_DPI) * (0.90 - 0.09))
        x_per_px = (xlim_max - xlim_min) / axis_w_px
        y_per_px = (ylim_max - ylim_min) / axis_h_px

        def _rect_overlap(a: Tuple[float, float, float, float], b: Tuple[float, float, float, float]) -> float:
            dx = min(float(a[1]), float(b[1])) - max(float(a[0]), float(b[0]))
            dy = min(float(a[3]), float(b[3])) - max(float(a[2]), float(b[2]))
            if dx <= 0.0 or dy <= 0.0:
                return 0.0
            return float(dx * dy)

        def _label_rect(
                x: float,
                y: float,
                text_lbl: str,
                ha: str,
                va: str,
                font_pt: float,
                pad_px: float = 8.0
        ) -> Tuple[float, float, float, float]:
            lines = str(text_lbl).split("\n")
            max_chars = max([len(line) for line in lines] + [1])
            n_lines = max(1, len(lines))

            font_px = max(8.0, float(font_pt) * (PLOT_DPI / 72.0))
            width_px = (max_chars * font_px * 0.58) + (2.0 * pad_px)
            height_px = (n_lines * font_px * 1.20) + (2.0 * pad_px)

            w_data = width_px * x_per_px
            h_data = height_px * y_per_px

            if ha == "left":
                x0 = x
                x1 = x + w_data
            elif ha == "right":
                x0 = x - w_data
                x1 = x
            else:
                x0 = x - 0.5 * w_data
                x1 = x + 0.5 * w_data

            if va == "bottom":
                y0 = y
                y1 = y + h_data
            elif va == "top":
                y0 = y - h_data
                y1 = y
            else:
                y0 = y - 0.5 * h_data
                y1 = y + 0.5 * h_data

            return float(x0), float(x1), float(y0), float(y1)

        def _clamp_label_with_rect(
                x: float,
                y: float,
                rect: Tuple[float, float, float, float]
        ) -> Tuple[float, float, Tuple[float, float, float, float]]:
            x0, x1, y0, y1 = rect
            margin_x = 0.01 * (xlim_max - xlim_min)
            margin_y = 0.01 * (ylim_max - ylim_min)

            shift_x = 0.0
            shift_y = 0.0

            if x0 < (xlim_min + margin_x):
                shift_x = (xlim_min + margin_x) - x0
            elif x1 > (xlim_max - margin_x):
                shift_x = (xlim_max - margin_x) - x1

            if y0 < (ylim_min + margin_y):
                shift_y = (ylim_min + margin_y) - y0
            elif y1 > (ylim_max - margin_y):
                shift_y = (ylim_max - margin_y) - y1

            if abs(shift_x) > 1e-12 or abs(shift_y) > 1e-12:
                x += shift_x
                y += shift_y
                x0 += shift_x
                x1 += shift_x
                y0 += shift_y
                y1 += shift_y

            return float(x), float(y), (float(x0), float(x1), float(y0), float(y1))

        def _pick_label_position(
                text_lbl: str,
                font_pt: float,
                anchor_x: float,
                anchor_y: float,
                candidates: List[Tuple[float, float, str, str]],
                occupied_rects: List[Tuple[float, float, float, float]],
                pad_px: float = 8.0,
                overlap_penalty: float = 2200.0,
        ) -> Tuple[float, float, str, str, Tuple[float, float, float, float]]:
            best: Optional[Tuple[float, float, str, str, Tuple[float, float, float, float]]] = None
            best_score: Optional[float] = None

            for cand_x, cand_y, cand_ha, cand_va in candidates:
                rect = _label_rect(
                    x=float(cand_x),
                    y=float(cand_y),
                    text_lbl=text_lbl,
                    ha=cand_ha,
                    va=cand_va,
                    font_pt=font_pt,
                    pad_px=pad_px,
                )
                cand_x2, cand_y2, rect = _clamp_label_with_rect(float(cand_x), float(cand_y), rect)

                overlap_area = 0.0
                for prev in occupied_rects:
                    overlap_area += _rect_overlap(rect, prev)

                dist = math.hypot(float(cand_x2) - float(anchor_x), float(cand_y2) - float(anchor_y))
                score = overlap_area * float(max(1.0, overlap_penalty)) + dist

                if (best is None) or (best_score is None) or (score < best_score):
                    best = (float(cand_x2), float(cand_y2), cand_ha, cand_va, rect)
                    best_score = float(score)
                    if overlap_area <= 1e-12:
                        break

            if best is None:
                rect = _label_rect(anchor_x, anchor_y, text_lbl, "center", "center", font_pt=font_pt)
                return float(anchor_x), float(anchor_y), "center", "center", rect

            return best

        # Ramki antykolizyjne: najpierw blokujemy okolice punktów archetypów/wartości.
        occupied_rects: List[Tuple[float, float, float, float]] = []
        for px, py in coords:
            occupied_rects.append(
                (
                    float(px) - 0.001 * xr,
                    float(px) + 0.001 * xr,
                    float(py) - 0.001 * yr,
                    float(py) + 0.001 * yr,
                )
            )

        # Rezerwa miejsca dla centroidów segmentów (żeby etykiety wartości nie wchodziły
        # w punkty segmentów rysowane później).
        for col_idx, s in enumerate(segs):
            logic_idx = _logic_col_idx(s, col_idx)

            hit_idx = np.where(hit_matrix_all[:, logic_idx])[0]
            if hit_idx.size == 0:
                col_vals = np.asarray(val_matrix_all[:, logic_idx], dtype=float)
                col_vals = np.where(np.isfinite(col_vals), col_vals, -np.inf)
                fallback_n = 4 if len(segs_logic) <= 3 else 3
                hit_idx = np.argsort(-col_vals)[:min(fallback_n, len(ARCHETYPES))]

            hx = coords[hit_idx, 0] if hit_idx.size > 0 else np.asarray([0.0], dtype=float)
            hy = coords[hit_idx, 1] if hit_idx.size > 0 else np.asarray([0.0], dtype=float)

            w_hit = []
            for a_idx in hit_idx:
                try:
                    vv = float(val_matrix_all[a_idx, logic_idx])
                except Exception:
                    vv = 0.0
                w_hit.append(max(0.01, vv if vv > 0 else 0.01))
            w_hit = np.asarray(w_hit, dtype=float)

            if (w_hit.size != len(hx)) or (np.sum(w_hit) <= 1e-12):
                w_hit = np.ones(len(hx), dtype=float)

            x_c = float(np.average(hx, weights=w_hit))
            y_c = float(np.average(hy, weights=w_hit))
            occupied_rects.append(
                (
                    x_c - (0.058 * xr),
                    x_c + (0.058 * xr),
                    y_c - (0.060 * yr),
                    y_c + (0.060 * yr),
                )
            )

        # 1) Etykiety archetypów / wartości
        for i, lab in enumerate(labels):
            px = float(coords[i, 0])
            py = float(coords[i, 1])
            txt = str(lab)
            font_pt = 12.0 * map_scale

            sign_x = 1.0 if px >= 0.0 else -1.0

            # Preferencje położenia etykiety:
            # - domyślnie blisko punktu i lekko nad nim,
            # - lokalne korekty dla nazw, które często się kolidują.
            custom_offsets: Dict[str, List[Tuple[float, float, str, str]]] = {
                "Twórca": [
                    (-0.018 * xr, 0.004 * yr, "right", "center"),
                    (-0.020 * xr, 0.010 * yr, "right", "bottom"),
                ],
                "Twórczyni": [
                    (-0.018 * xr, 0.004 * yr, "right", "center"),
                    (-0.020 * xr, 0.010 * yr, "right", "bottom"),
                ],
                "Odkrywca": [
                    (0.012 * xr, 0.016 * yr, "left", "bottom"),
                    (0.016 * xr, 0.012 * yr, "left", "bottom"),
                ],
                "Odkrywczyni": [
                    (0.012 * xr, 0.016 * yr, "left", "bottom"),
                    (0.016 * xr, 0.012 * yr, "left", "bottom"),
                ],
            }

            default_offsets: List[Tuple[float, float, str, str]] = [
                (0.000 * xr, 0.013 * yr, "center", "bottom"),
                (0.010 * xr * sign_x, 0.010 * yr, "left" if sign_x > 0 else "right", "bottom"),
                (-0.010 * xr * sign_x, 0.010 * yr, "right" if sign_x > 0 else "left", "bottom"),
                (0.013 * xr * sign_x, 0.000 * yr, "left" if sign_x > 0 else "right", "center"),
                (0.000 * xr, -0.012 * yr, "center", "top"),
            ]

            candidate_specs: List[Tuple[float, float, str, str]] = []
            for dx, dy, ha, va in custom_offsets.get(txt, []):
                candidate_specs.append((px + dx, py + dy, ha, va))
            for dx, dy, ha, va in default_offsets:
                candidate_specs.append((px + dx, py + dy, ha, va))

            forced = custom_offsets.get(txt, [])
            used_forced = False
            label_x = px
            label_y = py
            ha = "center"
            va = "bottom"
            rect = (px, px, py, py)

            if forced:
                fx, fy, fha, fva = forced[0]
                cand_x = px + fx
                cand_y = py + fy
                rect0 = _label_rect(
                    x=float(cand_x),
                    y=float(cand_y),
                    text_lbl=txt,
                    ha=fha,
                    va=fva,
                    font_pt=font_pt,
                    pad_px=4.5,
                )
                cand_x2, cand_y2, rect0 = _clamp_label_with_rect(float(cand_x), float(cand_y), rect0)
                overlap_area = 0.0
                for prev in occupied_rects:
                    overlap_area += _rect_overlap(rect0, prev)
                if overlap_area <= 1e-12:
                    label_x, label_y, ha, va, rect = float(cand_x2), float(cand_y2), fha, fva, rect0
                    used_forced = True

            if not used_forced:
                label_x, label_y, ha, va, rect = _pick_label_position(
                    text_lbl=txt,
                    font_pt=font_pt,
                    anchor_x=px,
                    anchor_y=py,
                    candidates=candidate_specs,
                    occupied_rects=occupied_rects,
                    pad_px=4.5,
                    overlap_penalty=1800.0,
                )

            occupied_rects.append(
                (
                    float(rect[0]) - (0.010 * xr),
                    float(rect[1]) + (0.010 * xr),
                    float(rect[2]) - (0.010 * yr),
                    float(rect[3]) + (0.010 * yr),
                )
            )

            if math.hypot(label_x - px, label_y - py) >= (0.020 * max(xr, yr)):
                ax.plot([px, label_x], [py, label_y], color="#94a3b8", lw=0.82, alpha=0.72, zorder=8.6)

            ax.text(
                label_x,
                label_y,
                txt,
                fontsize=font_pt,
                ha=ha,
                va=va,
                fontweight=575,
                zorder=9.2,
                clip_on=False,
            )

        # 2) Segmenty: obrys + centroid + etykieta segmentu
        for col_idx, s in enumerate(segs):
            seg_rank = int(s.get("segment_rank", col_idx))
            colors = _segment_ui_colors(seg_rank + 1)
            color = colors.get("accent", "#495057")

            logic_idx = _logic_col_idx(s, col_idx)

            hit_idx = np.where(hit_matrix_all[:, logic_idx])[0]
            if hit_idx.size == 0:
                col_vals = np.asarray(val_matrix_all[:, logic_idx], dtype=float)
                col_vals = np.where(np.isfinite(col_vals), col_vals, -np.inf)
                fallback_n = 4 if len(segs_logic) <= 3 else 3
                hit_idx = np.argsort(-col_vals)[:min(fallback_n, len(ARCHETYPES))]

            hx = coords[hit_idx, 0] if hit_idx.size > 0 else np.asarray([0.0], dtype=float)
            hy = coords[hit_idx, 1] if hit_idx.size > 0 else np.asarray([0.0], dtype=float)

            w_hit = []
            for a_idx in hit_idx:
                try:
                    vv = float(val_matrix_all[a_idx, logic_idx])
                except Exception:
                    vv = 0.0
                w_hit.append(max(0.01, vv if vv > 0 else 0.01))
            w_hit = np.asarray(w_hit, dtype=float)

            if (w_hit.size != len(hx)) or (np.sum(w_hit) <= 1e-12):
                w_hit = np.ones(len(hx), dtype=float)

            x = float(np.average(hx, weights=w_hit))
            y = float(np.average(hy, weights=w_hit))

            all_idx = np.arange(len(ARCHETYPES), dtype=int)
            hit_set = set(int(v) for v in np.asarray(hit_idx, dtype=int).tolist())
            avoid_idx = [int(i) for i in all_idx.tolist() if int(i) not in hit_set]
            avoid_pts = coords[avoid_idx, :] if len(avoid_idx) > 0 else np.zeros((0, 2), dtype=float)

            outline_pts = _segment_outline_polygon(
                np.column_stack([hx, hy]),
                avoid_xy=avoid_pts,
            )
            if outline_pts.shape[0] >= 2:
                ax.plot(
                    outline_pts[:, 0], outline_pts[:, 1],
                    color=color,
                    lw=1.8 * map_scale,
                    alpha=0.78,
                    linestyle=(0, (3.8, 3.2)),
                    solid_capstyle="round",
                    solid_joinstyle="round",
                    zorder=2
                )
                ax.fill(
                    outline_pts[:, 0], outline_pts[:, 1],
                    color=color,
                    alpha=0.06,
                    zorder=1.8
                )

            ax.scatter(
                [x], [y],
                s=158 * (map_scale ** 2),
                marker="s",
                color=color,
                edgecolor="white",
                linewidth=1.3,
                zorder=5.2
            )

            seg_label = str(s.get("segment_label", f"Seg_{seg_rank + 1}"))
            font_pt = 11.0 * map_scale

            x_sign = -1.0 if x <= (xmin + xmax) / 2.0 else 1.0

            candidate_specs = [
                (x, y + (0.020 * yr), "center", "bottom"),
                (x + (0.016 * xr * x_sign), y + (0.012 * yr), "left" if x_sign > 0 else "right", "bottom"),
                (x - (0.016 * xr * x_sign), y + (0.012 * yr), "right" if x_sign > 0 else "left", "bottom"),
                (x + (0.022 * xr * x_sign), y, "left" if x_sign > 0 else "right", "center"),
                (x, y - (0.018 * yr), "center", "top"),
            ]

            label_x, label_y, ha, va, rect = _pick_label_position(
                text_lbl=seg_label,
                font_pt=font_pt,
                anchor_x=x,
                anchor_y=y,
                candidates=candidate_specs,
                occupied_rects=occupied_rects,
                pad_px=12.0,
                overlap_penalty=4600.0,
            )
            occupied_rects.append(
                (
                    float(rect[0]) - (0.006 * xr),
                    float(rect[1]) + (0.006 * xr),
                    float(rect[2]) - (0.008 * yr),
                    float(rect[3]) + (0.008 * yr),
                )
            )

            ax.annotate(
                seg_label,
                xy=(x, y),
                xytext=(label_x, label_y),
                textcoords="data",
                fontsize=font_pt,
                fontweight="bold",
                ha=ha,
                va=va,
                bbox=dict(
                    boxstyle="round,pad=0.30,rounding_size=0.22",
                    fc="#ffffff",
                    ec=colors.get("line", "#dee2e6"),
                    lw=1.12,
                    alpha=0.97,
                ),
                arrowprops=dict(
                    arrowstyle="wedge,tail_width=0.78",
                    fc="#ffffff",
                    ec=colors.get("line", "#dee2e6"),
                    lw=1.12,
                    shrinkA=0,
                    shrinkB=2,
                    alpha=0.95,
                ),
                zorder=6.8,
            )

        legend_handles = []
        for col_idx, s in enumerate(segs):
            seg_rank = int(s.get("segment_rank", col_idx))
            colors = _segment_ui_colors(seg_rank + 1)
            seg_label = str(s.get("segment_label", f"Seg_{seg_rank + 1}"))
            seg_name = _segment_name_pair(s)[0]

            legend_handles.append(
                Line2D(
                    [0], [0],
                    marker="s",
                    color="none",
                    markerfacecolor=colors.get("accent", "#495057"),
                    markeredgecolor="white",
                    markeredgewidth=1.0,
                    markersize=9 * map_scale,
                    label=f"{seg_label}: {seg_name}"
                )
            )

        if legend_handles:
            leg = ax.legend(
                handles=legend_handles,
                loc="center left",
                bbox_to_anchor=(1.02, 0.50),
                ncol=1,
                frameon=True,
                fontsize=13.6 * map_scale,      # wielkość czcionki legendy
                framealpha=0.98,
                borderaxespad=0.35,
                borderpad=1.08,
                columnspacing=1.10,
                handletextpad=0.90,
                labelspacing=0.82,
                handlelength=1.35,
            )
            try:
                leg.get_frame().set_edgecolor("#cfd6de")
                leg.get_frame().set_linewidth(1.0)
            except Exception:
                pass

        x_pad = max(0.22 * xr, 0.26)
        y_pad = max(0.16 * yr, 0.28)
        ax.set_xlim(xmin - x_pad, xmax + x_pad)
        ax.set_ylim(ymin - y_pad, ymax + y_pad)
        ax.set_xticks([])
        ax.set_yticks([])

        title_txt = (
            "Wartości charakterystyczne dla segmentów"
            if mode == "values"
            else "Archetypy charakterystyczne dla segmentów"
        )
        ax.set_title(title_txt, fontsize=18.5 * map_scale, fontweight="bold", pad=max(8, int(round(12 * map_scale))))          # tu jest wielkość czcionki

        ax.set_aspect("auto")

        fig.subplots_adjust(left=0.055, right=0.80, top=0.90, bottom=0.09)
        fig.savefig(outdir / fname, dpi=PLOT_DPI, facecolor="white", bbox_inches="tight", pad_inches=0.08)
        plt.close(fig)

    _draw("arche", f"{fname_base}.png")
    _draw("values", f"{fname_base}_values.png")


# usunięto profile_segments_premium() — aktywny pipeline używa _segments_profiles_premium()
# usunięto martwe helpery historycznej segmentacji (choose_best_k_by_constraints / build_seg_pack)
# =========================
# NAZEWNICTWO SEGMENTÓW (wspólne)
# =========================

def make_segment_name(top2_archs: List[str]) -> str:
    """
    Krótka, techniczna nazwa segmentu na bazie TOP2 archetypów.
    Używana w kilku miejscach (profile / kompatybilność historyczna). Musi istnieć, żeby nie było
    Unresolved reference.
    """
    picks = [str(x).strip() for x in (top2_archs or []) if str(x).strip()]
    if len(picks) >= 2:
        return f"{picks[0]} + {picks[1]}"
    if len(picks) == 1:
        return f"{picks[0]}"
    return "Segment"


# =========================
# 9) WYKRESY
# =========================

def make_segment_profile(top_archs: List[str], bottom_archs: List[str]) -> Tuple[List[str], List[str], List[str]]:
    """
    Premiumowy opis segmentu:
    - opis = co ten segment ceni / czego oczekuje
    - komunikacja = jak do niego mówić
    - ryzyka = co go zniechęca / uruchamia opór
    Zwracamy listy punktów, żeby karty segmentów były bardziej czytelne.
    """
    top = [str(x) for x in (top_archs or []) if str(x).strip()]
    bottom = [str(x) for x in (bottom_archs or []) if str(x).strip()]

    if not top:
        return (
            ["Brak wystarczających danych do opisu segmentu."],
            ["Brak wystarczających danych do rekomendacji komunikacyjnej."],
            ["Brak wystarczających danych do oceny ryzyk."],
        )

    while len(top) < 3:
        top.append(top[-1])

    if not bottom:
        bottom = [top[-1]]
    while len(bottom) < 2:
        bottom.append(bottom[-1])

    t1, t2, t3 = top[0], top[1], top[2]
    b1, b2 = bottom[0], bottom[1]
    dt1, dt2, dt3 = _display_archetype_label(t1), _display_archetype_label(t2), _display_archetype_label(t3)
    db1, db2 = _display_archetype_label(b1), _display_archetype_label(b2)

    def _need(a: str) -> str:
        return str(SEG_DESCRIPT.get(a, ("czytelny kierunek", "prostą komunikację", "chaos"))[0])

    def _comm(a: str) -> str:
        return str(SEG_DESCRIPT.get(a, ("czytelny kierunek", "prostą komunikację", "chaos"))[1])

    def _risk(a: str) -> str:
        return str(SEG_DESCRIPT.get(a, ("czytelny kierunek", "prostą komunikację", "chaos"))[2])

    desc = [
        f"Rdzeń segmentu tworzą: {dt1} i {dt2}. To one najmocniej porządkują oczekiwania tej grupy.",
        f"Najsilniej działa na nich obietnica związana z: {_need(t1)} oraz {_need(t2)}.",
        f"Trzeci akcent ({dt3}) wzmacnia wrażliwość segmentu i dopowiada, czego ta grupa szuka w mieście oraz władzy.",
    ]

    msg = [
        f"Najlepiej działa język oparty o: {_comm(t1)} oraz {_comm(t2)}.",
        "Przekaz prowadź według prostego schematu: problem → decyzja → konkretny efekt dla mieszkańca.",
        f"Komunikację warto domknąć akcentem odnoszącym się także do: {_need(t3)}.",
    ]

    risks = [
        f"Pierwsze ryzyko oporu: {_risk(t1)}.",
        f"Drugie ryzyko oporu: {_risk(t2)}.",
        f"Silnie zniechęca też deficyt po stronie {db1} / {db2}: {_risk(b1)}; {_risk(b2)}.",
    ]

    return desc, msg, risks


PLOT_TITLE_FONTSIZE = 11.5  # → tytuł wykresu
PLOT_TITLE_PAD = 16  # margines tytułu wykresu od górnej krawędzi

# ręczne sterowanie wyglądem wykresów słupkowych
PLOT_AXIS_LABEL_FONTSIZE = 8  # → podpis osi
PLOT_XLABEL_PAD = 18  # większy odstęp podpisu osi X od etykiet kategorii
PLOT_BAR_FIG_H = 4.85  # wyższe wykresy słupkowe (góra-dół), ale bez przesady
PLOT_BAR_TIGHT_BOTTOM = 0.085  # mniejsza pusta strefa pod osią X
PLOT_X_TICK_FONTSIZE = 9  # → etykiety osi X
PLOT_Y_TICK_FONTSIZE = 7  # → etykiety osi Y
PLOT_VALUE_FONTSIZE = 9  # → liczby nad słupkami

PLOT_GRID_COLOR = "#dbe4ee"
PLOT_GRID_LINEWIDTH = 0.7

# ramka wykresu: cieńsza i bardziej szara
PLOT_FRAME_COLOR = "#b7c3d0"
PLOT_FRAME_LINEWIDTH = 0.8

# odstępy góra/dół, żeby liczby nad słupkami nie wpadały w ramkę
PLOT_BAR_TOP_PAD_FACTOR = 0.18
PLOT_BAR_TOP_PAD_MIN = 0.40

PLOT_BAR_BOTTOM_PAD_FACTOR = 0.10
PLOT_BAR_BOTTOM_PAD_MIN = 0.12

PLOT_BAR_LABEL_PAD_FACTOR = 0.035
PLOT_BAR_LABEL_PAD_MIN = 0.10
PLOT_BAR_LABEL_OFFSET_POS = 0.58  # etykieta bliżej końca dodatniego słupka
PLOT_BAR_LABEL_OFFSET_NEG = 0.50  # etykieta bliżej końca ujemnego słupka

PLOT_SAVE_DPI = 180


def set_plot_title(ax: Any, title: str) -> None:
    ax.set_title(title, fontsize=PLOT_TITLE_FONTSIZE, fontweight="bold", pad=PLOT_TITLE_PAD)


def _color_negative_axis_ticks(ax: Any) -> None:
    def _to_float(s: str) -> Optional[float]:
        t = str(s or "").strip().replace("%", "").replace("−", "-").replace(",", ".")
        if not t:
            return None
        try:
            return float(t)
        except Exception:
            return None

    for lbl in list(ax.get_xticklabels()) + list(ax.get_yticklabels()):
        v = _to_float(lbl.get_text())
        if v is not None and v < 0:
            lbl.set_color("#c92a2a")


def bar_chart(values: pd.Series, outpath: Path, title: str, xlabel: str = "", colors: Optional[List[Any]] = None,
              value_fmt: str = "{:.1f}", rotate: int = 45) -> None:
    s = values.copy()

    n = max(len(s), 1)

    # większy wykres niż dotąd
    fig_w = min(max(6.2, 0.50 * n + 1.8), 8.8)
    fig_h = PLOT_BAR_FIG_H
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_facecolor("#fbfcfe")

    x = np.arange(len(s))
    y = pd.to_numeric(s, errors="coerce").to_numpy(dtype=float)
    draw_vals = np.nan_to_num(y, nan=0.0)

    if colors is None:
        bar_colors = ["#2b6cb0" if (not np.isfinite(v) or v >= 0) else "#d13b3b" for v in draw_vals]
    else:
        bar_colors = colors
    bars = ax.bar(x, draw_vals, color=bar_colors, width=0.80, edgecolor="white", linewidth=0.9)

    ax.set_title(title, fontsize=PLOT_TITLE_FONTSIZE, fontweight="bold", pad=PLOT_TITLE_PAD)
    ax.set_xticks(x)
    ax.set_xticklabels(_display_archetype_labels(s.index.tolist()), rotation=rotate, ha="right")
    ax.tick_params(axis="x", labelsize=PLOT_X_TICK_FONTSIZE)
    ax.tick_params(axis="y", labelsize=PLOT_Y_TICK_FONTSIZE)

    if xlabel:
        ax.set_xlabel(xlabel, fontsize=PLOT_AXIS_LABEL_FONTSIZE, labelpad=PLOT_XLABEL_PAD)

    ax.grid(axis="y", color=PLOT_GRID_COLOR, linewidth=PLOT_GRID_LINEWIDTH)
    ax.axhline(0.0, color="#8ea0b3", linewidth=0.9, alpha=0.65, zorder=0)
    ax.set_axisbelow(True)

    # cieńsza, szara ramka zamiast ciężkiej czarnej
    for spine in ax.spines.values():
        spine.set_color(PLOT_FRAME_COLOR)
        spine.set_linewidth(PLOT_FRAME_LINEWIDTH)

    finite = y[np.isfinite(y)]
    if finite.size:
        y_min = float(np.min(finite))
        y_max = float(np.max(finite))
        span = max(y_max - y_min, 0.5)

        label_pad = max(PLOT_BAR_LABEL_PAD_MIN, PLOT_BAR_LABEL_PAD_FACTOR * span)
        top_pad = max(PLOT_BAR_TOP_PAD_MIN, PLOT_BAR_TOP_PAD_FACTOR * span)
        bottom_pad = max(PLOT_BAR_BOTTOM_PAD_MIN, PLOT_BAR_BOTTOM_PAD_FACTOR * span)

        # większy prześwit u góry + miejsce na etykiety nad słupkami
        bottom = y_min - bottom_pad - (label_pad * 0.70 if y_min < 0 else 0.0)
        top = y_max + top_pad + (label_pad * 1.35 if y_max >= 0 else 0.0)

        # jeśli cały wykres dodatni / ujemny, nie zostawiaj absurdalnego zapasu
        if y_min >= 0:
            bottom = 0.0
        if y_max <= 0:
            top = max(0.0, y_max + top_pad * 0.35)

        if top <= bottom:
            top = bottom + 1.0

        ax.set_ylim(bottom, top)

        for rect, v in zip(bars, y):
            if not np.isfinite(v):
                continue

            if v >= 0:
                y_text = float(v) + label_pad * PLOT_BAR_LABEL_OFFSET_POS
                va = "bottom"
            else:
                y_text = float(v) - label_pad * PLOT_BAR_LABEL_OFFSET_NEG
                va = "top"

            ax.text(
                rect.get_x() + rect.get_width() / 2,
                y_text,
                value_fmt.format(float(v)),
                ha="center",
                va=va,
                fontsize=PLOT_VALUE_FONTSIZE,
                fontweight="700",
                color=("#c92a2a" if float(v) < 0 else "#111111")
            )
    else:
        ax.set_ylim(-1.0, 1.0)

    _color_negative_axis_ticks(ax)
    ax.margins(x=0.028)

    fig.tight_layout(rect=[0.02, PLOT_BAR_TIGHT_BOTTOM, 0.988, 0.93], pad=0.75)
    fig.savefig(outpath, dpi=PLOT_SAVE_DPI)
    plt.close(fig)


def plot_horizontal_metric_chart(
        values: pd.Series,
        outpath: Path,
        title: str,
        xlabel: str = "",
        x_min: float = 0.0,
        x_max: float = 100.0,
        value_fmt: str = "{:.1f}",
        value_suffix: str = "",
        reference_line: Optional[float] = None
) -> None:
    s = pd.to_numeric(values.copy(), errors="coerce")
    s = s.dropna()
    if s.empty:
        return

    n = max(int(len(s)), 1)
    # Zachowujemy standardowe proporcje wykresów; tylko lekko dociągamy obszar w lewo.
    fig_w = min(max(6.2, 0.50 * n + 2.2), 8.8)
    fig_h = min(max(PLOT_BAR_FIG_H + 0.35, 0.38 * n + 1.8), 8.2)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_facecolor("#fbfcfe")

    y = np.arange(len(s))
    vals = s.to_numpy(dtype=float)
    labels = _display_archetype_labels([str(x) for x in s.index.tolist()])
    bars = ax.barh(y, vals, color="#2b6cb0", edgecolor="white", linewidth=0.9, height=0.72)

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=PLOT_X_TICK_FONTSIZE)
    ax.invert_yaxis()
    ax.tick_params(axis="y", pad=1.5)
    ax.tick_params(axis="x", labelsize=PLOT_Y_TICK_FONTSIZE)
    ax.grid(axis="x", color=PLOT_GRID_COLOR, linewidth=PLOT_GRID_LINEWIDTH)
    ax.set_axisbelow(True)
    ax.set_xlim(float(x_min), float(x_max))
    if xlabel:
        ax.set_xlabel(xlabel, fontsize=PLOT_AXIS_LABEL_FONTSIZE, labelpad=PLOT_XLABEL_PAD)

    set_plot_title(ax, title)

    if reference_line is not None and np.isfinite(reference_line):
        ax.axvline(float(reference_line), color="#cc2f2f", linestyle="--", linewidth=1.3, alpha=0.95)

    for spine in ax.spines.values():
        spine.set_color(PLOT_FRAME_COLOR)
        spine.set_linewidth(PLOT_FRAME_LINEWIDTH)

    rng = max(float(x_max) - float(x_min), 1.0)
    pad = 0.012 * rng
    for rect, v in zip(bars, vals):
        if not np.isfinite(v):
            continue
        x_text = min(float(v) + pad, float(x_max) - (0.02 * rng))
        ax.text(
            x_text,
            rect.get_y() + rect.get_height() / 2.0,
            f"{value_fmt.format(float(v))}{value_suffix}",
            ha="left",
            va="center",
            fontsize=PLOT_VALUE_FONTSIZE,
            fontweight="700",
            color="#111111",
        )

    max_label_len = max(len(str(lbl)) for lbl in labels) if labels else 8
    # Tylko lekkie dociągnięcie wykresu w lewo względem standardu; prawa strona bez poszerzania.
    left_margin = min(max(0.052, 0.034 + 0.0068 * float(max_label_len)), 0.145)
    fig.subplots_adjust(left=left_margin, right=0.972, bottom=0.13, top=0.90)
    fig.savefig(outpath, dpi=PLOT_SAVE_DPI)
    plt.close(fig)


def plot_expectation_balance_stacked(
        df_main: pd.DataFrame,
        outpath: Path,
        title: str,
) -> None:
    if df_main is None or len(df_main) == 0:
        return
    req = {"archetype", "expected_pct", "neutral_pct", "not_expected_pct"}
    if not req.issubset(set(df_main.columns)):
        return

    d = df_main.copy()
    d = d.sort_values(["expected_pct", "ioa_100"], ascending=[False, False], kind="mergesort")
    d = d.dropna(subset=["expected_pct", "neutral_pct", "not_expected_pct"])
    if d.empty:
        return

    n = len(d)
    fig_w = 7.8
    # Lekko wyższy wykres dla czytelności, ale z ograniczeniem wysokości.
    fig_h = min(max(4.9, 0.28 * n + 1.85), 6.0)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_facecolor("#fbfcfe")

    y = np.arange(n)
    labels = _display_archetype_labels([str(x) for x in d["archetype"].astype(str).tolist()])
    exp = pd.to_numeric(d["expected_pct"], errors="coerce").to_numpy(dtype=float)
    neu = pd.to_numeric(d["neutral_pct"], errors="coerce").to_numpy(dtype=float)
    not_exp = pd.to_numeric(d["not_expected_pct"], errors="coerce").to_numpy(dtype=float)

    ax.barh(y, exp, color="#2f7d32", edgecolor="white", linewidth=0.8, height=0.72, label="Oczekujący")
    ax.barh(y, neu, left=exp, color="#7b8a97", edgecolor="white", linewidth=0.8, height=0.72, label="Neutralni")
    ax.barh(
        y,
        not_exp,
        left=(exp + neu),
        color="#b42318",
        edgecolor="white",
        linewidth=0.8,
        height=0.72,
        label="Nieoczekujący",
    )

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=PLOT_X_TICK_FONTSIZE)
    ax.invert_yaxis()
    ax.tick_params(axis="y", pad=1.5)
    ax.tick_params(axis="x", labelsize=PLOT_Y_TICK_FONTSIZE)
    ax.set_xlim(0, 100)
    ax.set_xlabel("% respondentów", fontsize=PLOT_AXIS_LABEL_FONTSIZE, labelpad=8)
    ax.grid(axis="x", color=PLOT_GRID_COLOR, linewidth=PLOT_GRID_LINEWIDTH)
    ax.set_axisbelow(True)
    set_plot_title(ax, title)

    for spine in ax.spines.values():
        spine.set_color(PLOT_FRAME_COLOR)
        spine.set_linewidth(PLOT_FRAME_LINEWIDTH)

    # etykiety % na segmentach (dla czytelności tylko segmenty >= 6 p.p.)
    for yi in range(n):
        segs = [
            (exp[yi], 0.0),
            (neu[yi], exp[yi]),
            (not_exp[yi], exp[yi] + neu[yi]),
        ]
        for seg_w, seg_l in segs:
            if (not np.isfinite(seg_w)) or (seg_w < 6.0):
                continue
            ax.text(
                float(seg_l + seg_w / 2.0),
                float(yi),
                f"{float(seg_w):.1f}%",
                ha="center",
                va="center",
                fontsize=7.2,
                fontweight="700",
                color="#ffffff",
            )

    max_label_len = max(len(str(lbl)) for lbl in labels) if labels else 8
    left_margin = min(max(0.055, 0.034 + 0.0066 * float(max_label_len)), 0.135)
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.145),
        ncol=3,
        fontsize=7.9,
        frameon=False,
        handlelength=1.4,
        columnspacing=1.2,
    )
    fig.subplots_adjust(left=left_margin, right=0.972, bottom=0.215, top=0.90)
    fig.savefig(outpath, dpi=PLOT_SAVE_DPI)
    plt.close(fig)


def plot_pair_outcome_balance(values: pd.Series, outpath: Path, title: str, xlabel: str = "Bilans par (+1 / -1)",
                              rotate: int = 45) -> None:
    s = values.copy()
    n = max(len(s), 1)

    fig_w = min(max(6.2, 0.50 * n + 1.8), 8.8)
    fig_h = PLOT_BAR_FIG_H
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.set_facecolor("#fbfcfe")

    x = np.arange(len(s))
    y = pd.to_numeric(s, errors="coerce").to_numpy(dtype=float)
    draw_vals = np.nan_to_num(y, nan=0.0)
    bar_colors = ["#2b6cb0" if (not np.isfinite(v) or v >= 0) else "#d13b3b" for v in draw_vals]
    bars = ax.bar(x, draw_vals, color=bar_colors, width=0.80, edgecolor="white", linewidth=0.9)

    ax.set_title(title, fontsize=PLOT_TITLE_FONTSIZE, fontweight="bold", pad=PLOT_TITLE_PAD)
    ax.set_xticks(x)
    ax.set_xticklabels(_display_archetype_labels(s.index.tolist()), rotation=rotate, ha="right")
    ax.tick_params(axis="x", labelsize=PLOT_X_TICK_FONTSIZE)
    ax.tick_params(axis="y", labelsize=PLOT_Y_TICK_FONTSIZE)
    ax.set_xlabel(xlabel, fontsize=PLOT_AXIS_LABEL_FONTSIZE, labelpad=PLOT_XLABEL_PAD)
    ax.set_ylim(-3.6, 3.6)
    ax.set_yticks(np.arange(-3, 4, 1))
    ax.grid(axis="y", color=PLOT_GRID_COLOR, linewidth=PLOT_GRID_LINEWIDTH)
    ax.axhline(0.0, color="#8ea0b3", linewidth=0.9, alpha=0.65, zorder=0)
    ax.set_axisbelow(True)

    for spine in ax.spines.values():
        spine.set_color(PLOT_FRAME_COLOR)
        spine.set_linewidth(PLOT_FRAME_LINEWIDTH)

    for rect, v in zip(bars, y):
        if not np.isfinite(v):
            continue
        if v >= 0:
            y_text = min(float(v) + 0.18, 3.34)
            va = "bottom"
        else:
            y_text = max(float(v) - 0.18, -3.34)
            va = "top"
        ax.text(
            rect.get_x() + rect.get_width() / 2,
            y_text,
            f"{int(round(float(v))):+d}",
            ha="center",
            va=va,
            fontsize=PLOT_VALUE_FONTSIZE,
            fontweight="700",
            color=("#c92a2a" if float(v) < 0 else "#111111")
        )

    _color_negative_axis_ticks(ax)
    ax.margins(x=0.028)
    fig.tight_layout(rect=[0.02, PLOT_BAR_TIGHT_BOTTOM, 0.988, 0.93], pad=0.75)
    fig.savefig(outpath, dpi=PLOT_SAVE_DPI)
    plt.close(fig)


def plot_A_versus_profile_line(
    df_pairs: pd.DataFrame,
    outpath: Path,
    title: str = "Profil liniowy archetypów",
    brand_values: Optional[Dict[str, str]] = None
) -> None:
    if df_pairs is None or len(df_pairs) == 0:
        return

    from matplotlib import transforms as mtransforms

    def _smooth_polyline(xs: List[float], ys: List[float], points_per_seg: int = 28) -> Tuple[np.ndarray, np.ndarray]:
        pts = np.column_stack([np.asarray(xs, dtype=float), np.asarray(ys, dtype=float)])
        n_pts = len(pts)
        if n_pts < 3:
            return pts[:, 0], pts[:, 1]

        out: List[np.ndarray] = []
        for i in range(n_pts - 1):
            p1 = pts[i]
            p2 = pts[i + 1]
            p0 = pts[i - 1] if i > 0 else (p1 + (p1 - p2))
            p3 = pts[i + 2] if (i + 2) < n_pts else (p2 + (p2 - p1))

            tt = np.linspace(0.0, 1.0, max(6, int(points_per_seg)), endpoint=(i == (n_pts - 2)))
            for t in tt:
                t2 = t * t
                t3 = t2 * t
                c = 0.5 * (
                    (2.0 * p1)
                    + (-p0 + p2) * t
                    + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2
                    + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3
                )
                out.append(c)

        arr = np.asarray(out, dtype=float)
        if arr.ndim != 2 or arr.shape[1] != 2:
            return pts[:, 0], pts[:, 1]

        arr[:, 0] = np.clip(arr[:, 0], 1.0, 7.0)
        return arr[:, 0], arr[:, 1]

    left_raw_names: List[str] = []
    right_raw_names: List[str] = []
    left_labels: List[str] = []
    right_labels: List[str] = []
    mean_vals: List[float] = []

    for _, row in df_pairs.iterrows():
        left_raw = str(row.get("lewy", ""))
        right_raw = str(row.get("prawy", ""))

        left_label = (
            brand_values.get(left_raw, left_raw)
            if isinstance(brand_values, dict)
            else _display_archetype_label(left_raw)
        )
        right_label = (
            brand_values.get(right_raw, right_raw)
            if isinstance(brand_values, dict)
            else _display_archetype_label(right_raw)
        )

        mean_sign = _safe_float(row.get("mean_sign", 0.0))
        mean_val = float(np.clip(A_SCALE_CENTER + mean_sign, 1.0, 7.0))

        left_raw_names.append(left_raw)
        right_raw_names.append(right_raw)
        left_labels.append(left_label)
        right_labels.append(right_label)
        mean_vals.append(mean_val)

    winner_color_by_arche = {
        "Odkrywca": "#d94841",
        "Buntownik": "#d94841",
        "Błazen": "#d94841",
        "Kochanek": "#1d4ed8",
        "Opiekun": "#1d4ed8",
        "Towarzysz": "#1d4ed8",
        "Niewinny": "#2b8a3e",
        "Władca": "#2b8a3e",
        "Mędrzec": "#2b8a3e",
        "Czarodziej": "#7048e8",
        "Bohater": "#7048e8",
        "Twórca": "#7048e8",
    }

    n = len(mean_vals)
    ys = np.arange(n, 0, -1, dtype=float)

    # Delikatnie mniejszy format, aby wykres nie przytłaczał sekcji.
    fig_h = max(9.4, 2.2 + n * 0.48)
    fig, ax = plt.subplots(figsize=(12.4, fig_h), dpi=PLOT_DPI)

    # tło stref skali A
    ax.axvspan(1.0, 2.0, color="#d7e7ff", alpha=0.85, zorder=0)
    ax.axvspan(2.0, 3.0, color="#e8f5ea", alpha=0.85, zorder=0)
    ax.axvspan(5.0, 6.0, color="#e8f5ea", alpha=0.85, zorder=0)
    ax.axvspan(6.0, 7.0, color="#d7e7ff", alpha=0.85, zorder=0)

    for y in ys:
        ax.hlines(y, 1.0, 7.0, color="#d6dee8", linewidth=0.85, zorder=1)

    for x in range(1, 8):
        ax.axvline(float(x), color="#ccd6e2", linewidth=0.9, zorder=1)

    ax.axvline(4.0, color="#6f7f90", linewidth=1.7, zorder=2)

    sx, sy = _smooth_polyline(mean_vals, ys, points_per_seg=30)
    ax.plot(sx, sy, color="#1f5ea8", linewidth=4.2, alpha=0.93, zorder=4)
    ax.scatter(mean_vals, ys, s=174, color="#1f5ea8", edgecolor="white", linewidth=1.8, zorder=5)

    # etykiety liczbowe: większe i bliżej po bokach punktu
    for idx, (x, y) in enumerate(zip(mean_vals, ys)):
        if abs(x - 4.0) <= 0.18:
            side = -1 if (idx % 2 == 0) else 1
        else:
            side = 1 if x >= 4.0 else -1

        x_text = float(np.clip(x + (0.092 * side), 1.03, 6.97))
        ax.text(
            x_text,
            y,
            f"{x:.1f}",
            ha="left" if side > 0 else "right",
            va="center",
            fontsize=11.5,
            fontweight="800",
            bbox=dict(boxstyle="round,pad=0.20", facecolor="white", edgecolor="#c4d2e1", alpha=0.96),
            zorder=6,
            clip_on=False,
        )

    close_eps = 0.15
    y_axis_transform = mtransforms.blended_transform_factory(ax.transAxes, ax.transData)

    for i, y in enumerate(ys):
        mv = mean_vals[i]
        left_fw = "normal"
        right_fw = "normal"
        left_color = "#0f1720"
        right_color = "#0f1720"

        if mv <= (4.0 - close_eps):
            left_fw = "900"
            left_color = winner_color_by_arche.get(left_raw_names[i], "#0f1720")
        elif mv >= (4.0 + close_eps):
            right_fw = "900"
            right_color = winner_color_by_arche.get(right_raw_names[i], "#0f1720")

        ax.text(
            -0.02,
            y,
            left_labels[i],
            transform=y_axis_transform,
            ha="right",
            va="center",
            fontsize=12.2,
            fontweight=left_fw,
            color=left_color,
            zorder=6,
            clip_on=False,
        )
        ax.text(
            1.02,
            y,
            right_labels[i],
            transform=y_axis_transform,
            ha="left",
            va="center",
            fontsize=12.2,
            fontweight=right_fw,
            color=right_color,
            zorder=6,
            clip_on=False,
        )

    ax.set_xlim(1.0, 7.0)
    ax.set_ylim(0.35, n + 0.85)
    ax.set_xticks([1, 2, 3, 4, 5, 6, 7])
    ax.set_xticklabels(["1", "2", "3", "4", "5", "6", "7"], fontsize=11)
    ax.set_yticks([])

    # Delikatne, szare ticki zewnętrzne lewej/prawej osi (jak krótkie znaczniki skali).
    _tick_len_ax = 0.006
    for _y in ys:
        ax.plot([-_tick_len_ax, 0.0], [_y, _y], transform=y_axis_transform, color="#c7d0db", linewidth=0.95, zorder=3, clip_on=False)
        ax.plot([1.0, 1.0 + _tick_len_ax], [_y, _y], transform=y_axis_transform, color="#c7d0db", linewidth=0.95, zorder=3, clip_on=False)

    ax.set_xlabel("Skala odpowiedzi A (1 = lewa strona pary, 4 = środek, 7 = prawa strona pary)", fontsize=11, labelpad=16)
    ax.set_title(title, fontsize=17, fontweight="700", pad=22)

    legend_adv = [
        matplotlib.patches.Patch(facecolor="#d7e7ff", edgecolor="#c8d8eb", label="bardzo duża przewaga"),
        matplotlib.patches.Patch(facecolor="#e8f5ea", edgecolor="#cfdfd1", label="duża przewaga"),
    ]
    lg1 = ax.legend(
        handles=legend_adv,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.09),
        ncol=2,
        frameon=False,
        fontsize=10.5,
        handlelength=1.1,
        columnspacing=1.8,
    )
    ax.add_artist(lg1)

    legend_groups = [
        matplotlib.patches.Patch(facecolor="#d94841", edgecolor="#d94841", label="Zmiana"),
        matplotlib.patches.Patch(facecolor="#1d4ed8", edgecolor="#1d4ed8", label="Ludzie"),
        matplotlib.patches.Patch(facecolor="#2b8a3e", edgecolor="#2b8a3e", label="Porządek"),
        matplotlib.patches.Patch(facecolor="#7048e8", edgecolor="#7048e8", label="Niezależność"),
    ]
    ax.legend(
        handles=legend_groups,
        loc="upper center",
        bbox_to_anchor=(0.5, -0.145),
        ncol=4,
        frameon=False,
        fontsize=10.2,
        handlelength=0.95,
        columnspacing=1.2,
    )

    for spine in ax.spines.values():
        spine.set_color("#9eb0c2")
        spine.set_linewidth(0.95)

    fig.subplots_adjust(left=0.15, right=0.85, top=0.91, bottom=0.17)
    fig.savefig(outpath, dpi=PLOT_DPI, facecolor="white")
    plt.close(fig)

def total_mentions_counts(
        A: np.ndarray,
        A_cols: List[Tuple[str, str]],
        b1: np.ndarray,
        b2: np.ndarray,
        d13: np.ndarray,
        weights: np.ndarray,
        weighted_counts: bool = False,
) -> pd.DataFrame:
    """
    Zlicza „wskazania” archetypów w pytaniach wyboru (A, B1, B2, D13).
    Sekcja C została usunięta z analizy.
    W A neutralne (środek skali) są pomijane (dla skali 1–7: neutral = 4).
    Zwraca tabelę z rozbiciem na bloki + kolumną Razem.
    """
    if weighted_counts:
        w = np.asarray(weights, dtype=float).reshape(-1)
    else:
        w = np.ones(len(weights), dtype=float)

    out = pd.DataFrame(index=ARCHETYPES)
    out["A"] = 0.0
    out["B1"] = 0.0
    out["B2"] = 0.0
    out["D13"] = 0.0

    # A (1–7, środek = 4): 1–3 lewa, 5–7 prawa, 4 neutral (pomijamy)
    left_thr = A_SCALE_CENTER - 1  # 3
    right_thr = A_SCALE_CENTER + 1  # 5
    for j, (left_arch, right_arch) in enumerate(A_cols):
        v = A[:, j]
        m = np.isfinite(v)
        out.loc[left_arch, "A"] += w[m & (v <= left_thr)].sum()
        out.loc[right_arch, "A"] += w[m & (v >= right_thr)].sum()

    # B1: 0/1 zaznaczenia (NaN traktujemy jak 0)
    b1_f = np.nan_to_num(b1, nan=0.0)
    out["B1"] = (b1_f * w.reshape(-1, 1)).sum(axis=0)

    # B2: indeks archetypu (0..11), -1 pomijamy
    m_b2 = (b2 >= 0)
    for i, arch in enumerate(ARCHETYPES):
        out.loc[arch, "B2"] = w[m_b2 & (b2 == i)].sum()

    # D13: indeks archetypu (0..11), -1 pomijamy
    m_d13 = (d13 >= 0)
    for i, arch in enumerate(ARCHETYPES):
        out.loc[arch, "D13"] = w[m_d13 & (d13 == i)].sum()

    out["Razem"] = out[["A", "B1", "B2", "D13"]].sum(axis=1)
    out = out.sort_values("Razem", ascending=False)
    return out


def mentions_counts_by_question(
        A: np.ndarray,
        b1: np.ndarray,
        b2: np.ndarray,
        d13: np.ndarray,
        weights: np.ndarray,
        as_int: bool = True,
        weighted_counts: bool = False,
) -> pd.DataFrame:
    """
    Macierz: archetyp (wiersze) x pytanie (kolumny: A1–A18, B1, B2, D13).

    Definicja „wskazania”:
    - A1–A18 (1–7, środek = 4): liczymy tylko wybory NIE-neutralne:
        * 1–3 -> wskazanie LEWEGO archetypu
        * 5–7 -> wskazanie PRAWEGO archetypu
        * 4   -> pomijamy (brak wskazania)
    - B1: wielokrotny wybór (0–3). Każde zaznaczenie archetypu = 1 wskazanie.
    - B2: TOP1 (1 wskazanie).
    - D13: TOP1 (1 wskazanie).

    Wynik: DataFrame, gdzie 1. kolumna to 'archetyp', a kolejne to pytania.
    Wartości mogą być surowe (domyślnie) albo ważone.
    """
    if weighted_counts:
        w = np.asarray(weights, dtype=float).reshape(-1)
    else:
        w = np.ones(len(weights), dtype=float)
    idx = {a: i for i, a in enumerate(ARCHETYPES)}
    n_arch = len(ARCHETYPES)

    # przygotuj puste kolumny (float, potem zaokrąglimy do int)
    cols_order: List[str] = [pid for pid, _, _ in A_PAIRS] + ["B1", "B2", "D13"]
    mat = {c: np.zeros(n_arch, dtype=float) for c in cols_order}

    # ===== A (1–7, środek = 4): 1–3 lewy, 5–7 prawy, 4 neutral (pomijamy) =====
    left_thr = A_SCALE_CENTER - 1  # 3
    right_thr = A_SCALE_CENTER + 1  # 5

    for j, (pid, left_arch, right_arch) in enumerate(A_PAIRS):
        v = A[:, j]
        m = np.isfinite(v)
        if not np.any(m):
            continue
        mat[pid][idx[left_arch]] += float(w[m & (v <= left_thr)].sum())
        mat[pid][idx[right_arch]] += float(w[m & (v >= right_thr)].sum())

    # ===== B1: zaznaczenia 0/1 (NaN -> 0) =====
    b1_f = np.nan_to_num(b1, nan=0.0)
    mat["B1"] = (b1_f * w.reshape(-1, 1)).sum(axis=0)

    # ===== B2: indeks 0..11, -1 pomijamy =====
    m_b2 = (b2 >= 0)
    if np.any(m_b2):
        for i in range(n_arch):
            mat["B2"][i] = float(w[m_b2 & (b2 == i)].sum())

    # ===== D13: indeks 0..11, -1 pomijamy =====
    m_d13 = (d13 >= 0)
    if np.any(m_d13):
        for i in range(n_arch):
            mat["D13"][i] = float(w[m_d13 & (d13 == i)].sum())

    # zbuduj DF w kolejności kolumn: A1..A18, B1, B2, D13
    df = pd.DataFrame({"archetyp": ARCHETYPES})
    for c in cols_order:
        if as_int:
            df[c] = np.round(mat[c], 0).astype(int)
        else:
            df[c] = mat[c].astype(float)

    return df


def validate_mentions_by_question_counts(
        df_mentions_q: pd.DataFrame,
        A: np.ndarray,
        b1: np.ndarray,
        b2: np.ndarray,
        d13: np.ndarray
) -> pd.DataFrame:
    """
    Waliduje spójność liczebności tabeli A1..A18, B1, B2, D13 na poziomie surowych rekordów.
    """
    if df_mentions_q is None or len(df_mentions_q) == 0:
        return pd.DataFrame(columns=["kolumna", "expected_count", "observed_count", "delta"])

    rows: List[Dict[str, Any]] = []
    for j, (pid, _left_arch, _right_arch) in enumerate(A_PAIRS):
        v = np.asarray(A[:, j], dtype=float)
        expected = int(np.sum(np.isfinite(v) & ((v <= (A_SCALE_CENTER - 1)) | (v >= (A_SCALE_CENTER + 1)))))
        observed = int(pd.to_numeric(df_mentions_q.get(pid, pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
        rows.append({"kolumna": pid, "expected_count": expected, "observed_count": observed, "delta": observed - expected})

    b1_f = np.nan_to_num(np.asarray(b1, dtype=float), nan=0.0)
    expected_b1 = int(np.sum(b1_f > 0.5))
    observed_b1 = int(pd.to_numeric(df_mentions_q.get("B1", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
    rows.append({"kolumna": "B1", "expected_count": expected_b1, "observed_count": observed_b1, "delta": observed_b1 - expected_b1})

    expected_b2 = int(np.sum(np.asarray(b2, dtype=int) >= 0))
    observed_b2 = int(pd.to_numeric(df_mentions_q.get("B2", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
    rows.append({"kolumna": "B2", "expected_count": expected_b2, "observed_count": observed_b2, "delta": observed_b2 - expected_b2})

    expected_d13 = int(np.sum(np.asarray(d13, dtype=int) >= 0))
    observed_d13 = int(pd.to_numeric(df_mentions_q.get("D13", pd.Series(dtype=float)), errors="coerce").fillna(0).sum())
    rows.append({"kolumna": "D13", "expected_count": expected_d13, "observed_count": observed_d13, "delta": observed_d13 - expected_d13})

    out = pd.DataFrame(rows)
    if not out.empty and (out["delta"] != 0).any():
        bad = out[out["delta"] != 0].copy()
        raise ValueError(
            "Walidacja tabeli wskazań nie przeszła. Rozjazdy: "
            + "; ".join(
                f"{r.kolumna}: expected={int(r.expected_count)} observed={int(r.observed_count)}"
                for r in bad.itertuples(index=False)
            )
        )
    return out


def A_total_shares(
        A: np.ndarray,
        weights: np.ndarray,
        scale_center: int = A_SCALE_CENTER,
) -> pd.DataFrame:
    """
    A (18 versusów, 1–7, środek=4):
    - wskazanie lewego: 1–3
    - wskazanie prawego: 5–7
    - 4: brak wskazania, ale głos (do mianownika)
    Liczymy łącznie dla archetypu (każdy jest 3× w parach).
    """
    w = np.asarray(weights, dtype=float).reshape(-1)

    counts = pd.Series(0.0, index=ARCHETYPES)  # wskazania
    denom = pd.Series(0.0, index=ARCHETYPES)  # głosy (respondent × liczba par dla archetypu)

    left_thr = scale_center - 1  # 3
    right_thr = scale_center + 1  # 5

    for j, (_pid, left_arch, right_arch) in enumerate(A_PAIRS):
        v = A[:, j]
        m = np.isfinite(v)
        if not np.any(m):
            continue

        # do mianownika: każdy ważny głos w tej parze liczy się dla OBU archetypów z pary
        denom[left_arch] += w[m].sum()
        denom[right_arch] += w[m].sum()

        # do licznika: tylko wybory nieneutralne
        counts[left_arch] += w[m & (v <= left_thr)].sum()
        counts[right_arch] += w[m & (v >= right_thr)].sum()

    out = pd.DataFrame({
        "archetyp": ARCHETYPES,
        "wskazania": [counts[a] for a in ARCHETYPES],
        "glosy": [denom[a] for a in ARCHETYPES],
    })
    out["%"] = np.where(out["glosy"] > 0, out["wskazania"] / out["glosy"] * 100.0, np.nan)
    out["wskazania"] = out["wskazania"].round(0).astype(int)
    out["glosy"] = out["glosy"].round(0).astype(int)
    out["%"] = out["%"].round(1)
    out = out.sort_values("%", ascending=False).reset_index(drop=True)
    return out


def mentions_counts_by_question_for_report(df_mentions_q: pd.DataFrame) -> pd.DataFrame:
    d = df_mentions_q.copy()
    if "archetyp" not in d.columns:
        return d

    qcols = [c for c in d.columns if c != "archetyp"]

    num = d[qcols].apply(pd.to_numeric, errors="coerce").fillna(0).astype(int)

    out = d.copy()
    out["Razem"] = num.sum(axis=1).astype(int)

    total_row: Dict[str, Any] = {"archetyp": "RAZEM"}
    for c in qcols:
        total_row[c] = int(num[c].sum())
    total_row["Razem"] = int(out["Razem"].sum())

    out = pd.concat([out, pd.DataFrame([total_row])], ignore_index=True)

    # >>> KLUCZOWA ZMIANA: te kolumny będą mieszać int i "", więc od razu na object
    out[qcols + ["Razem"]] = out[qcols + ["Razem"]].astype(object)

    last_i = len(out) - 1
    for c in qcols + ["Razem"]:
        mask_data = out.index != last_i
        zeros = (
                pd.to_numeric(out.loc[mask_data, c], errors="coerce")
                .fillna(0)
                .astype(int) == 0
        )
        out.loc[mask_data, c] = out.loc[mask_data, c].where(~zeros, "")

    return out


def build_question_aggregation_audit(
        A: np.ndarray,
        b1: np.ndarray,
        b2: np.ndarray,
        d13: np.ndarray,
        df_B1: pd.DataFrame,
        df_B2: pd.DataFrame,
        df_D13: pd.DataFrame,
        df_mentions_q_raw: pd.DataFrame,
) -> pd.DataFrame:
    """
    Audyt spójności liczników pytań (surowe dane vs tabele raportowe).
    Zwraca tabelę z delta dla A1..A18 oraz bloków B1/B2/D13.
    """
    rows: List[Dict[str, Any]] = []
    q_ids = [pid for pid, _left, _right in A_PAIRS]

    # A1..A18: expected = liczba odpowiedzi nieneutralnych (1-3 / 5-7), reported = suma kolumny z tabeli raw.
    for j, qid in enumerate(q_ids):
        v = np.asarray(A[:, j], dtype=float)
        expected = int(np.sum(np.isfinite(v) & (v != float(A_SCALE_CENTER))))
        reported = 0
        if (df_mentions_q_raw is not None) and (qid in df_mentions_q_raw.columns):
            reported = int(pd.to_numeric(df_mentions_q_raw[qid], errors="coerce").fillna(0).sum())
        rows.append(
            {
                "pytanie": qid,
                "expected_raw": int(expected),
                "reported_raw": int(reported),
                "delta": int(reported - expected),
            }
        )

    # B1 (TOP3): suma zaznaczeń 0/1
    b1_flag = (np.nan_to_num(b1, nan=0.0) > 0.5)
    b1_expected = int(np.sum(b1_flag))
    b1_reported = int(pd.to_numeric(df_B1.get("liczba"), errors="coerce").fillna(0).sum()) if isinstance(df_B1, pd.DataFrame) else 0
    rows.append(
        {
            "pytanie": "B1",
            "expected_raw": int(b1_expected),
            "reported_raw": int(b1_reported),
            "delta": int(b1_reported - b1_expected),
        }
    )

    # B2 (TOP1): liczba odpowiedzi rozpoznanych
    b2_expected = int(np.sum(np.asarray(b2, dtype=int) >= 0))
    b2_reported = int(pd.to_numeric(df_B2.get("liczba"), errors="coerce").fillna(0).sum()) if isinstance(df_B2, pd.DataFrame) else 0
    rows.append(
        {
            "pytanie": "B2",
            "expected_raw": int(b2_expected),
            "reported_raw": int(b2_reported),
            "delta": int(b2_reported - b2_expected),
        }
    )

    # D13 (TOP1): liczba odpowiedzi rozpoznanych
    d13_expected = int(np.sum(np.asarray(d13, dtype=int) >= 0))
    d13_reported = int(pd.to_numeric(df_D13.get("liczba"), errors="coerce").fillna(0).sum()) if isinstance(df_D13, pd.DataFrame) else 0
    rows.append(
        {
            "pytanie": "D13",
            "expected_raw": int(d13_expected),
            "reported_raw": int(d13_reported),
            "delta": int(d13_reported - d13_expected),
        }
    )

    return pd.DataFrame(rows, columns=["pytanie", "expected_raw", "reported_raw", "delta"])


def top5_blocks_table(
        df_A_total: pd.DataFrame,
        df_B1: pd.DataFrame,
        df_B2: pd.DataFrame,
        df_D13: pd.DataFrame,
) -> pd.DataFrame:
    rows = []

    # A: TOP5 archetypów po % (łącznie)
    a_top = df_A_total.head(5)
    rows.append({
        "pytanie": "A (łącznie)",
        **{
            f"TOP{i + 1}": f"{_display_archetype_label(r.archetyp)} ({r['%']:.1f}%)"
            for i, r in enumerate(a_top.itertuples(index=False))
        }
    })

    # B1: TOP5 po %
    b1 = df_B1.sort_values("%", ascending=False).head(5)
    rows.append({
        "pytanie": "B1 (w trójce)",
        **{
            f"TOP{i + 1}": f"{_display_archetype_label(r.archetyp)} ({r['%']:.1f}%)"
            for i, r in enumerate(b1.itertuples(index=False))
        }
    })

    # B2: TOP5 po %
    b2 = df_B2.sort_values("%", ascending=False).head(5)
    rows.append({
        "pytanie": "B2 (TOP1)",
        **{
            f"TOP{i + 1}": f"{_display_archetype_label(r.archetyp)} ({r['%']:.1f}%)"
            for i, r in enumerate(b2.itertuples(index=False))
        }
    })

    # D13: TOP5 po %
    d13 = df_D13.sort_values("%", ascending=False).head(5)
    rows.append({
        "pytanie": "D13 (TOP1)",
        **{
            f"TOP{i + 1}": f"{_display_archetype_label(r.archetyp)} ({r['%']:.1f}%)"
            for i, r in enumerate(d13.itertuples(index=False))
        }
    })

    # uzupełnij brakujące TOP-y pustymi stringami
    for r in rows:
        for i in range(1, 6):
            r.setdefault(f"TOP{i}", "")
    return pd.DataFrame(rows, columns=["pytanie"] + [f"TOP{i}" for i in range(1, 6)])


def plot_B_bar(df_rank: pd.DataFrame, out_png: Path | str, title: str, xlabel: str = "Odsetek (%)") -> None:
    """
    Prosty wykres słupkowy dla rankingów B (TOP).
    Wspiera oba warianty nazw kolumn: '%' lub 'pct'.
    """
    if df_rank is None or len(df_rank) == 0:
        plt.figure(figsize=(10, 6))
        plt.title(title)
        plt.tight_layout()
        plt.savefig(Path(out_png), dpi=160)
        plt.close()
        return

    col_pct = "%" if "%" in df_rank.columns else ("pct" if "pct" in df_rank.columns else None)
    if col_pct is None:
        raise ValueError("Brak kolumny z procentami: oczekuję '%' albo 'pct' w df_rank.")

    s = df_rank.set_index("archetyp")[col_pct].astype(float).sort_values(ascending=False)
    bar_chart(s, outpath=Path(out_png), title=title, xlabel=xlabel)


def plot_corr_heatmap_clustered(
        scores: np.ndarray,
        archetypes: List[str],
        out_png: Path,
        title: str = "Korelacje archetypów (automatyczne grupowanie)"
) -> None:
    """
    Heatmapa korelacji z automatycznym ustawieniem podobnych archetypów obok siebie.
    - scores: macierz wyników respondentów (N x 12), np. P albo G
    - archetypes: lista nazw archetypów (12)
    """
    df = pd.DataFrame(scores, columns=archetypes)
    corr = df.corr().fillna(0.0).to_numpy()
    try:
        np.fill_diagonal(corr, 1.0)
    except Exception:
        pass

    order = _cluster_order_avg_linkage_from_corr(corr)
    labels = [str(archetypes[i]) for i in order]
    labels_display = _display_archetype_labels(labels)
    corr_ord = corr[np.ix_(order, order)]

    label_colors: List[str] = []
    for idx in order:
        base_name = ARCHETYPES[idx] if idx < len(ARCHETYPES) else str(archetypes[idx])
        label_colors.append(get_need_axis_color(base_name, index_hint=idx))

    fig, ax = plt.subplots(figsize=(10.2, 8.9))
    im = ax.imshow(corr_ord, vmin=-1, vmax=1, cmap="coolwarm", interpolation="nearest")

    ax.set_title(title, fontsize=14, fontweight="bold", pad=10)
    ax.set_xticks(range(len(labels)))
    ax.set_yticks(range(len(labels)))
    ax.set_xticklabels(labels_display, rotation=40, ha="right", fontsize=11.5, fontweight="600")
    ax.set_yticklabels(labels_display, fontsize=11.5, fontweight="600")
    ax.tick_params(axis="both", which="major", pad=2)

    for lbl, col in zip(ax.get_xticklabels(), label_colors):
        lbl.set_color(col)
    for lbl, col in zip(ax.get_yticklabels(), label_colors):
        lbl.set_color(col)

    # siatka komórek
    n = len(labels_display)
    ax.set_xticks(np.arange(-0.5, n, 1), minor=True)
    ax.set_yticks(np.arange(-0.5, n, 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=1)
    ax.tick_params(which="minor", bottom=False, left=False)

    cbar = fig.colorbar(im, ax=ax, fraction=0.038, pad=0.018)
    cbar.set_label("Korelacja (-1 … +1)", fontsize=10)
    cbar.ax.tick_params(labelsize=8)

    ax.legend(
        handles=axis_legend_handles(),
        loc="upper center",
        bbox_to_anchor=(0.5, -0.19),
        ncol=4,
        frameon=False,
        title="Legenda kolorów osi potrzeb",
        fontsize=9,
        title_fontsize=9,
    )

    fig.subplots_adjust(left=0.12, right=0.95, bottom=0.29, top=0.90)
    fig.savefig(out_png, dpi=160, bbox_inches="tight", pad_inches=0.06)
    plt.close(fig)


def plot_D13_top1(df_D13: pd.DataFrame, out_png: Path | str) -> None:
    """
    D13 – wybór najważniejszego:
    - długość słupka = udział wskazań priorytetowych (%)
    - słupek podzielony na MINUS (czerwony) i PLUS (zielony) wg sentymentu wśród wskazujących
    - etykiety wewnątrz segmentów tylko gdy segment ma dość miejsca (w pikselach)
    - format etykiety wewnątrz: % w 1. linii, a wartość w nawiasie w 2. linii (więcej miejsca)
    """
    d = df_D13.copy()

    col_total = "%" if "%" in d.columns else "pct"
    col_plus_w = "%PLUS_wybor" if "%PLUS_wybor" in d.columns else "pct_plus_wybor"
    col_minus_w = "%MINUS_wybor" if "%MINUS_wybor" in d.columns else "pct_minus_wybor"

    d = d[["archetyp", col_total, col_plus_w, col_minus_w]].copy()
    d[col_total] = d[col_total].astype(float)
    d[col_plus_w] = d[col_plus_w].astype(float)
    d[col_minus_w] = d[col_minus_w].astype(float)

    d = d.sort_values(col_total, ascending=False).reset_index(drop=True)

    total = d[col_total].to_numpy()
    plus_share = d[col_plus_w].to_numpy() / 100.0
    minus_share = d[col_minus_w].to_numpy() / 100.0

    plus_share = np.nan_to_num(plus_share, nan=0.0)
    minus_share = np.nan_to_num(minus_share, nan=0.0)

    s = plus_share + minus_share
    s[s == 0] = 1.0
    plus_share = plus_share / s
    minus_share = minus_share / s

    plus_abs = total * plus_share
    minus_abs = total * minus_share

    labels = _display_archetype_labels(d["archetyp"].astype(str).to_list())
    y = np.arange(len(labels))

    # Dynamiczna wysokość figury (łatwiej pomieścić więcej wierszy)
    fig_h = max(6.4, 0.62 * len(labels) + 1.8)
    fig, ax = plt.subplots(figsize=(12.8, fig_h))

    bar_h = 0.86
    ax.barh(y, minus_abs, height=bar_h, color="red", alpha=0.85, label="MINUS")
    ax.barh(y, plus_abs, left=minus_abs, height=bar_h, color="green", alpha=0.85, label="PLUS")

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=12, fontweight="600")
    ax.invert_yaxis()

    xmax = max(10, float(np.nanmax(total)) + 4.0)
    x_right_pad = max(0.45, 0.04 * xmax)
    ax.set_xlim(0, xmax + x_right_pad)
    ax.set_xlabel("Udział wskazań priorytetowych (%)", fontsize=12, labelpad=16)
    ax.set_title("Najważniejsze doświadczenie (udział doświadczeń pozytywnych i negatywnych)", fontsize=14, fontweight="bold", pad=12)

    # render do obliczeń w pikselach
    fig.canvas.draw()

    # (opcjonalnie) delikatny obrys tekstu, żeby był czytelny na czerwieni/zieleni
    try:
        from matplotlib import patheffects as pe
        txt_fx = [pe.withStroke(linewidth=2.2, foreground="white", alpha=0.65)]
    except Exception:
        txt_fx = None

    def _px_width(val: float) -> float:
        x0 = ax.transData.transform((0.0, 0.0))[0]
        x1 = ax.transData.transform((float(val), 0.0))[0]
        return abs(x1 - x0)

    MIN_SEG_PX = 34  # minimalna szerokość segmentu, by sensownie wsadzić tekst do środka
    MIN_SEG_VAL = 0.6  # minimalna wartość segmentu (w %), by w ogóle rozważać etykietę
    FS_IN = 11
    FS_OUT = 12

    x_pad = max(0.18, 0.012 * xmax)

    for i in range(len(labels)):
        total_val = float(total[i])
        if (not np.isfinite(total_val)) or (total_val <= 0):
            continue

        total_disp = round(total_val, 1)
        if total_disp == 0.0:
            continue

        pa = float(plus_abs[i])
        ma = float(minus_abs[i])
        psh = float(plus_share[i] * 100.0)
        msh = float(minus_share[i] * 100.0)

        # MINUS
        if (ma >= MIN_SEG_VAL) and (_px_width(ma) >= MIN_SEG_PX):
            txt = ax.text(
                ma / 2.0,
                i,
                f"{ma:.1f}%\n(-{msh:.1f}%)",
                ha="center",
                va="center",
                fontsize=FS_IN,
                color="black",
                linespacing=0.92
            )
            if txt_fx:
                txt.set_path_effects(txt_fx)

        # PLUS
        if (pa >= MIN_SEG_VAL) and (_px_width(pa) >= MIN_SEG_PX):
            txt = ax.text(
                ma + pa / 2.0,
                i,
                f"{pa:.1f}%\n(+{psh:.1f}%)",
                ha="center",
                va="center",
                fontsize=FS_IN,
                color="black",
                linespacing=0.92
            )
            if txt_fx:
                txt.set_path_effects(txt_fx)

        # Całość po prawej (etykieta łączna)
        ax.text(
            total_val + x_pad,
            i,
            f"{total_disp:.1f}%",
            ha="left",
            va="center",
            fontsize=FS_OUT,
            color="black"
        )

    plt.tight_layout(rect=[0.03, 0.07, 0.98, 0.93])
    fig.savefig(out_png, dpi=160)
    plt.close(fig)


def diverging_plus_minus_chart(df_D: pd.DataFrame, out_png: Path | str,
                               title: str = "Sentyment archetypów (pozytywne vs negatywne)") -> None:
    """
    Wykres rozbieżny: PLUS po prawej (zielony), MINUS po lewej (czerwony).
    """
    d = df_D.copy()

    col_plus = "%PLUS" if "%PLUS" in d.columns else ("pct_plus" if "pct_plus" in d.columns else None)
    col_minus = "%MINUS" if "%MINUS" in d.columns else ("pct_minus" if "pct_minus" in d.columns else None)
    if col_plus is None or col_minus is None:
        raise ValueError("Brak kolumn %PLUS/%MINUS (albo pct_plus/pct_minus) w df_D.")

    d = d[["archetyp", col_plus, col_minus]].copy()
    d = d.sort_values(col_plus, ascending=False).reset_index(drop=True)

    plus = d[col_plus].astype(float).to_numpy()
    minus = -d[col_minus].astype(float).to_numpy()  # ujemne do lewego ramienia
    labels = _display_archetype_labels(d["archetyp"].astype(str).to_list())

    y = np.arange(len(labels))

    fig_h = max(8.8, 0.64 * len(labels) + 2.2)
    fig, ax = plt.subplots(figsize=(12.0, fig_h))
    ax.axvline(0, color="black", linewidth=1)

    bar_h = 0.86
    bars_minus = ax.barh(y, minus, height=bar_h, color="red", alpha=0.85, label="MINUS")
    bars_plus = ax.barh(y, plus, height=bar_h, color="green", alpha=0.85, label="PLUS")

    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=12, fontweight="600")
    ax.invert_yaxis()

    ax.set_xlim(-100, 100)
    ax.set_xlabel("Odsetek (%)", fontsize=12, labelpad=16)
    ax.set_title(title, fontsize=14, fontweight="bold", pad=12)

    for rect, v in zip(bars_plus, plus):
        if np.isfinite(v) and v > 0:
            ax.text(v + 1.2, rect.get_y() + rect.get_height() / 2, f"{v:.1f}%",
                    va="center", ha="left", fontsize=11.5, color="black")

    for rect, v in zip(bars_minus, minus):
        if np.isfinite(v) and v < 0:
            ax.text(v - 1.2, rect.get_y() + rect.get_height() / 2, f"{abs(v):.1f}%",
                    va="center", ha="right", fontsize=11.5, color="#c92a2a")

    _color_negative_axis_ticks(ax)
    plt.tight_layout(rect=[0.03, 0.07, 0.98, 0.93])
    fig.savefig(Path(out_png), dpi=160)
    plt.close(fig)


def wheel_plus_minus_chart(
        df_pm: pd.DataFrame,
        title: str,
        outpath: str,
        order: Optional[List[str]] = None,
) -> None:
    """Koło archetypów: segment = 100%, grubość dzieli się na '-' i '+'.

    Zmiany:
    - wartości % są osobno: + w środku części PLUS, - w środku części MINUS
    - są linie wiodące do nazw
    - nazwy są bliżej wykresu
    """
    if order is None:
        order = ARCHETYPES

    tmp = df_pm.set_index("archetyp").reindex(order).reset_index()

    # Obsługa wariantów nazw kolumn
    if "%PLUS" in tmp.columns and "%MINUS" in tmp.columns:
        plus = (tmp["%PLUS"].fillna(0.0).values / 100.0)
        minus = (tmp["%MINUS"].fillna(0.0).values / 100.0)
    elif "pct_plus" in tmp.columns and "pct_minus" in tmp.columns:
        plus = (tmp["pct_plus"].fillna(0.0).values / 100.0)
        minus = (tmp["pct_minus"].fillna(0.0).values / 100.0)
    elif "plus_pct" in tmp.columns and "minus_pct" in tmp.columns:
        plus = tmp["plus_pct"].fillna(0.0).values
        minus = tmp["minus_pct"].fillna(0.0).values
    else:
        raise ValueError(
            "Brak kolumn sentymentu: oczekuję %PLUS/%MINUS albo pct_plus/pct_minus albo plus_pct/minus_pct")

    # Geometria pierścienia
    r_inner = 0.35
    thickness = 0.55
    r_outer = r_inner + thickness

    # Nazwy bliżej wykresu (było dalej)
    r_label = r_outer + 0.08

    fig = plt.figure(figsize=(9, 9))
    ax = fig.add_subplot(111, aspect="equal")
    ax.set_axis_off()
    ax.set_title(title, pad=36)

    # (opcjonalnie) lekki obrys napisów dla czytelności
    try:
        from matplotlib import patheffects as pe
        txt_fx = [pe.withStroke(linewidth=2.2, foreground="black", alpha=0.35)]
    except Exception:
        txt_fx = None

    n = len(order)
    start_angle = 90.0
    step = 360.0 / n

    for i, name in enumerate(order):
        name_disp = _display_archetype_label(name)
        a0 = start_angle - i * step
        a1 = a0 - step

        # gdzie jest granica między MINUS (czerwony) i PLUS (niebieski)
        m_share = float(minus[i])
        p_share = float(plus[i])

        # bezpieczeństwo: jeśli dane są „dziwne”
        m_share = 0.0 if (not np.isfinite(m_share)) else max(0.0, min(1.0, m_share))
        p_share = 0.0 if (not np.isfinite(p_share)) else max(0.0, min(1.0, p_share))

        r_split = r_inner + thickness * m_share

        # MINUS (czerwony) – od r_inner do r_split
        if r_split > r_inner + 1e-9:
            w_red = Wedge(
                (0, 0),
                r_split,
                a1,
                a0,
                width=r_split - r_inner,
                facecolor="red",
                alpha=0.75,
                edgecolor="white",
            )
            ax.add_patch(w_red)

        # PLUS (niebieski) – od r_split do r_outer
        if r_outer > r_split + 1e-9:
            w_blue = Wedge(
                (0, 0),
                r_outer,
                a1,
                a0,
                width=r_outer - r_split,
                facecolor="blue",
                alpha=0.75,
                edgecolor="white",
            )
            ax.add_patch(w_blue)

        # środek segmentu (kąt)
        ang_deg = (a0 + a1) / 2.0
        ang_rad = math.radians(ang_deg)

        # ===== Linie wiodące + etykieta (nazwa) =====
        x0 = r_outer * math.cos(ang_rad)
        y0 = r_outer * math.sin(ang_rad)

        x_lab = r_label * math.cos(ang_rad)
        y_lab = r_label * math.sin(ang_rad)

        ha = "left" if x_lab >= 0 else "right"
        label_color = get_need_axis_color(str(name), index_hint=i)

        ax.text(
            x_lab,
            y_lab,
            name_disp,
            ha=ha,
            va="center",
            fontsize=10,
            rotation=0,
            color=label_color,
            zorder=30
        )

        # ===== Wartości: osobno w środku MINUS i osobno w środku PLUS =====
        # MINUS – środek czerwonej części
        if m_share > 0.0005 and (r_split > r_inner + 1e-9):
            r_minus = (r_inner + r_split) / 2.0
            t = ax.text(
                r_minus * math.cos(ang_rad),
                r_minus * math.sin(ang_rad),
                f"-{m_share * 100:.1f}%",
                ha="center",
                va="center",
                fontsize=9,
                fontweight="bold",
                color="white",
                zorder=40
            )
            if txt_fx:
                t.set_path_effects(txt_fx)

        # PLUS – środek niebieskiej części
        if p_share > 0.0005 and (r_outer > r_split + 1e-9):
            r_plus = (r_split + r_outer) / 2.0
            t = ax.text(
                r_plus * math.cos(ang_rad),
                r_plus * math.sin(ang_rad),
                f"+{p_share * 100:.1f}%",
                ha="center",
                va="center",
                fontsize=9,
                fontweight="bold",
                color="white",
                zorder=40
            )
            if txt_fx:
                t.set_path_effects(txt_fx)

    ax.legend(
        handles=axis_legend_handles(),
        loc="upper center",
        bbox_to_anchor=(0.5, -0.08),
        ncol=4,
        frameon=False,
        title="Legenda kolorów osi potrzeb",
        fontsize=9,
        title_fontsize=9,
    )

    # limity + zapis (żeby nie obcinało nazw)
    lim = r_label + 0.16
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)

    plt.tight_layout(rect=[0.02, 0.06, 0.98, 0.98])
    plt.savefig(outpath, dpi=150, bbox_inches="tight", pad_inches=0.25)
    plt.close()


def _cluster_order_avg_linkage_from_corr(corr: np.ndarray) -> List[int]:
    """
    Zwraca kolejność indeksów (liści) tak, aby podobne archetypy były obok siebie.
    Metoda: aglomeracyjne łączenie klastrów (average linkage) na dystansie: dist = 1 - corr.
    Bez SciPy, działa dla małej liczby archetypów (np. 12).
    """
    corr = np.asarray(corr, dtype=float)
    n = corr.shape[0]
    dist = 1.0 - corr
    np.fill_diagonal(dist, 0.0)

    clusters = [{"items": [i], "order": [i]} for i in range(n)]

    def avg_linkage(a_items: List[int], b_items: List[int]) -> float:
        vals = []
        for i in a_items:
            for j in b_items:
                vals.append(dist[i, j])
        return float(np.mean(vals)) if len(vals) else 1e9

    def best_concat(orderA: List[int], orderB: List[int]) -> List[int]:
        # 4 warianty: A+B, A+rev(B), rev(A)+B, rev(A)+rev(B)
        cand = [
            orderA + orderB,
            orderA + list(reversed(orderB)),
            list(reversed(orderA)) + orderB,
            list(reversed(orderA)) + list(reversed(orderB)),
        ]
        best = cand[0]
        best_score = 1e9
        split = len(orderA)

        for c in cand:
            # ocena = „dystans na łączeniu” (ostatni z A vs pierwszy z B)
            i1 = c[split - 1]
            i2 = c[split]
            score = float(dist[i1, i2])
            if score < best_score:
                best_score = score
                best = c
        return best

    while len(clusters) > 1:
        best_i, best_j, best_d = 0, 1, 1e9
        for i in range(len(clusters)):
            for j in range(i + 1, len(clusters)):
                d = avg_linkage(clusters[i]["items"], clusters[j]["items"])
                if d < best_d:
                    best_d = d
                    best_i, best_j = i, j

        A = clusters[best_i]
        B = clusters[best_j]

        new_items = A["items"] + B["items"]
        new_order = best_concat(A["order"], B["order"])

        # usuń od końca, żeby nie popsuć indeksów
        for idx in sorted([best_i, best_j], reverse=True):
            clusters.pop(idx)
        clusters.append({"items": new_items, "order": new_order})

    return clusters[0]["order"]


# =========================
# 10) MAPA WARTOŚCI (DATA vs KOŁO)
# =========================

def _classical_mds_2d(D: np.ndarray) -> np.ndarray:
    D = np.asarray(D, dtype=float)
    n = D.shape[0]
    J = np.eye(n) - np.ones((n, n)) / n
    B = -0.5 * J @ (D ** 2) @ J
    eigvals, eigvecs = np.linalg.eigh(B)
    idx = np.argsort(eigvals)[::-1]
    eigvals = np.maximum(eigvals[idx], 0.0)
    eigvecs = eigvecs[:, idx]
    X = eigvecs[:, :2] @ np.diag(np.sqrt(eigvals[:2]))
    if np.allclose(X, 0):
        X = np.random.normal(scale=1e-3, size=(n, 2))
    return X


def _normalize(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=float)
    n = float(np.linalg.norm(v))
    return v if n == 0 else v / n


def build_value_space_from_P(P: np.ndarray, archetypes: List[str]) -> Tuple[np.ndarray, Dict[str, Any]]:
    dfP = pd.DataFrame(P, columns=archetypes)
    corr = dfP.corr().fillna(0.0).to_numpy()
    D = np.sqrt(np.clip(2 * (1 - corr), 0, None))
    raw = _classical_mds_2d(D)

    order_group = ["Władca", "Niewinny", "Opiekun"]
    change_group = ["Buntownik", "Odkrywca", "Twórca", "Czarodziej", "Błazen"]
    people_group = ["Towarzysz", "Opiekun", "Kochanek", "Błazen", "Niewinny"]
    indep_group = ["Odkrywca", "Buntownik", "Mędrzec", "Władca", "Twórca", "Bohater"]

    idx_map = {a: i for i, a in enumerate(archetypes)}

    def centroid(group: List[str]) -> np.ndarray:
        pts = [raw[idx_map[g]] for g in group if g in idx_map]
        if len(pts) == 0:
            return raw.mean(axis=0)
        return np.mean(np.vstack(pts), axis=0)

    c_order = centroid(order_group)
    c_change = centroid(change_group)
    c_people = centroid(people_group)
    c_indep = centroid(indep_group)

    v_y = c_change - c_order
    v_x = c_people - c_indep

    x_axis = _normalize(v_x)
    v_y_ort = v_y - np.dot(v_y, x_axis) * x_axis
    y_axis = _normalize(v_y_ort)

    if float(np.linalg.norm(y_axis)) == 0:
        Xc = raw - raw.mean(axis=0)
        _, _, VT = np.linalg.svd(Xc, full_matrices=False)
        x_axis = VT[0]
        y_axis = VT[1]

    coords = np.column_stack([raw @ x_axis, raw @ y_axis])

    # znaki: LUDZIE po prawej, ZMIANA u góry
    def tr(pt):
        return np.array([np.dot(pt, x_axis), np.dot(pt, y_axis)])

    if tr(c_people)[0] < tr(c_indep)[0]:
        coords[:, 0] *= -1
        x_axis *= -1
    if tr(c_change)[1] < tr(c_order)[1]:
        coords[:, 1] *= -1
        y_axis *= -1

    meta = {
        "axes": {"x_left": "niezależność", "x_right": "ludzie", "y_down": "porządek", "y_up": "zmiana"},
        "order_group": order_group, "change_group": change_group,
        "people_group": people_group, "indep_group": indep_group,
        "note": "Autorska mapa wartości Badania.pro®."
    }
    return coords, meta


def build_value_space_fixed_circle(archetypes: List[str]) -> Tuple[np.ndarray, Dict[str, Any]]:
    angles_deg = {
        "Buntownik": 90,
        "Błazen": 60,
        "Kochanek": 30,
        "Opiekun": 0,
        "Towarzysz": -30,
        "Niewinny": -60,
        "Władca": -90,
        "Mędrzec": -120,
        "Czarodziej": -150,
        "Bohater": 180,
        "Twórca": 150,
        "Odkrywca": 120,
    }
    coords = []
    for a in archetypes:
        ang = math.radians(angles_deg[a])
        coords.append([math.cos(ang), math.sin(ang)])
    coords = np.asarray(coords, dtype=float)
    meta = {"note": "Autorska mapa wartości Badania.pro (wariant KOŁO).", "angles_deg": angles_deg}
    return coords, meta


def _rankdata(x: np.ndarray) -> np.ndarray:
    x = np.asarray(x)
    order = np.argsort(x)
    ranks = np.empty_like(order, dtype=float)
    ranks[order] = np.arange(1, len(x) + 1, dtype=float)
    sorted_x = x[order]
    i = 0
    while i < len(x):
        j = i
        while j + 1 < len(x) and sorted_x[j + 1] == sorted_x[i]:
            j += 1
        if j > i:
            avg = (i + 1 + j + 1) / 2.0
            ranks[order[i:j + 1]] = avg
        i = j + 1
    return ranks


def compare_value_maps(coords_a: np.ndarray, coords_b: np.ndarray) -> Dict[str, Any]:
    A = np.asarray(coords_a, dtype=float)
    B = np.asarray(coords_b, dtype=float)

    A0 = A - A.mean(axis=0, keepdims=True)
    B0 = B - B.mean(axis=0, keepdims=True)

    M = B0.T @ A0
    U, _, Vt = np.linalg.svd(M)
    R = U @ Vt
    B1 = B0 @ R

    num = float((A0 * B1).sum())
    den = float((B1 * B1).sum())
    s = 0.0 if den == 0 else num / den
    B2 = B1 * s

    rms = float(np.sqrt(np.mean((A0 - B2) ** 2)))

    def pdist(X):
        d = []
        for i in range(len(X)):
            for j in range(i + 1, len(X)):
                d.append(float(np.linalg.norm(X[i] - X[j])))
        return np.asarray(d)

    dA = pdist(A)
    dB = pdist(B)
    rA = _rankdata(dA)
    rB = _rankdata(dB)
    rA0 = rA - rA.mean()
    rB0 = rB - rB.mean()
    denom = float(np.sqrt((rA0 * rA0).sum() * (rB0 * rB0).sum()))
    spearman = float((rA0 * rB0).sum() / denom) if denom > 0 else 0.0

    return {"procrustes_rms": rms, "dist_spearman": spearman, "scale": float(s)}


def respondent_positions(scores: np.ndarray, coords: np.ndarray) -> np.ndarray:
    S = np.asarray(scores, dtype=float)
    w = np.clip(S, 0, None)
    denom = np.sum(w, axis=1, keepdims=True)
    denom[denom == 0] = 1.0
    return (w @ coords) / denom


def weighted_centroid(pos: np.ndarray, weights: np.ndarray) -> np.ndarray:
    w = np.asarray(weights, dtype=float).reshape(-1)
    m = np.isfinite(pos).all(axis=1) & np.isfinite(w)
    if m.sum() == 0:
        return np.array([0.0, 0.0])
    return np.average(pos[m], axis=0, weights=w[m])


def build_segment_centroids(pos: np.ndarray, labels: np.ndarray, weights: np.ndarray, K: int) -> pd.DataFrame:
    rows = []
    for k in range(K):
        m = labels == k
        if m.sum() == 0:
            continue
        xy = weighted_centroid(pos[m], weights[m])
        rows.append({"segment_id": k, "x": float(xy[0]), "y": float(xy[1]), "liczba": int(m.sum()),
                     "waga": float(weights[m].sum())})
    return pd.DataFrame(rows)


def get_archetype_color(archetype: str) -> str:
    """
    Zwraca kolor dla archetypu.
    - Jeśli w pliku istnieje globalny słownik kolorów, użyje go (różne możliwe nazwy).
    - W przeciwnym razie użyje deterministycznego koloru z palety matplotlib (tab20).
    """
    a = str(archetype)

    # 1) Spróbuj użyć istniejącej mapy kolorów, jeśli gdzieś jest w pliku
    for key in ("ARCHETYPE_COLORS", "ARCHETYPES_COLORS", "ARCHETYPE_COLOR_MAP", "ARCHETYPES_COLOR_MAP"):
        mp = globals().get(key)
        if isinstance(mp, dict) and a in mp:
            return str(mp[a])

    # 2) Fallback: deterministyczny kolor z tab20 (stabilny między uruchomieniami)
    try:
        import matplotlib.pyplot as _plt

        arch_list = list(globals().get("ARCHETYPES", []))
        if a in arch_list:
            idx = arch_list.index(a)
        else:
            idx = abs(hash(a)) % 20

        cmap = _plt.get_cmap("tab20")
        r, g, b, _ = cmap(idx % cmap.N)
        return "#{:02x}{:02x}{:02x}".format(int(r * 255), int(g * 255), int(b * 255))
    except Exception:
        # absolutny awaryjny fallback
        return "#4c6ef5"


def _brand_values_reverse_map() -> Dict[str, str]:
    mp = globals().get("CURRENT_BRAND_VALUES")
    if not isinstance(mp, dict) or not mp:
        mp = globals().get("DEFAULT_BRAND_VALUES", {})
    rev: Dict[str, str] = {}
    if isinstance(mp, dict):
        for a, v in mp.items():
            rev[str(v)] = str(a)
    return rev


def _resolve_archetype_for_need_axis(label: Any, index_hint: Optional[int] = None) -> str:
    s = str(label or "")
    if s in ARCHETYPE_NEED_AXIS:
        return s
    if s in ARCHETYPE_MASC_FROM_FEMININE:
        return str(ARCHETYPE_MASC_FROM_FEMININE[s])

    rev = _brand_values_reverse_map()
    if s in rev:
        return str(rev[s])

    try:
        idx = int(index_hint) if index_hint is not None else -1
    except Exception:
        idx = -1
    if 0 <= idx < len(ARCHETYPES):
        return str(ARCHETYPES[idx])

    return s


def get_need_axis_key(label: Any, index_hint: Optional[int] = None) -> str:
    arch = _resolve_archetype_for_need_axis(label, index_hint=index_hint)
    return str(ARCHETYPE_NEED_AXIS.get(arch, "ludzie"))


def get_need_axis_color(label: Any, index_hint: Optional[int] = None) -> str:
    key = get_need_axis_key(label, index_hint=index_hint)
    return str(NEED_AXIS_COLORS.get(key, "#1d4ed8"))


def axis_legend_handles() -> List[Any]:
    order = ["zmiana", "ludzie", "porządek", "niezależność"]
    return [
        Line2D([0], [0], marker="o", linestyle="None", markersize=7,
               markerfacecolor=NEED_AXIS_COLORS[k], markeredgecolor=NEED_AXIS_COLORS[k],
               label=NEED_AXIS_LABELS[k])
        for k in order
    ]


def plot_value_map(outpath, title, coords, respondent_xy, seg_centroids, seg_names, point_labels):
    """
    Rysuje mapę wartości:
    - respondent_xy: (n,2) punkty respondentów
    - coords: albo dict[label]->(x,y), albo array (m,2) zgodny z point_labels
    - seg_centroids: może być:
        * numpy array (k,2)
        * DataFrame z kolumnami x,y (+ opcjonalnie segment_id)
        * iterable rekordów (dict/tuple) z segment_id,x,y
    - seg_names: dict {segment_id: nazwa}
    - point_labels: lista etykiet dla punktów archetypów
    """
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    import matplotlib.patheffects as pe
    from matplotlib.lines import Line2D

    # --- coords -> dict label -> (x,y)
    if isinstance(coords, dict):
        coord_map = {str(k): (float(v[0]), float(v[1])) for k, v in coords.items()}
    else:
        arr = np.asarray(coords, dtype=float)
        coord_map = {str(point_labels[i]): (float(arr[i, 0]), float(arr[i, 1])) for i in range(len(point_labels))}

    # --- respondenci (czyść NaN)
    X = np.asarray(respondent_xy, dtype=float)
    if X.ndim != 2 or X.shape[1] < 2:
        X = np.zeros((0, 2), dtype=float)
    else:
        m = np.isfinite(X[:, 0]) & np.isfinite(X[:, 1])
        X = X[m][:, :2]

    # --- figura
    fig, ax = plt.subplots(figsize=(12, 9))

    # miejsce po prawej na legendę
    fig.subplots_adjust(right=0.78, left=0.08, bottom=0.11, top=0.92)

    # tło: respondenci
    if X.size:
        ax.scatter(X[:, 0], X[:, 1], s=14, alpha=0.25, zorder=1)

    # osie krzyżowe (niebieskie)
    ax.axhline(0, color="#1c7ed6", lw=2, zorder=2)
    ax.axvline(0, color="#1c7ed6", lw=2, zorder=2)

    # ramka + zakres
    ax.set_xlim(-1.10, 1.10)
    ax.set_ylim(-1.10, 1.10)
    for spine in ax.spines.values():
        spine.set_linewidth(2)

    ax.set_title(title, fontsize=22, fontweight="bold", pad=18)

    # --- STRZAŁKI KIERUNKU OSI: NA ZEWNĄTRZ (axes fraction)
    arrow_color = "#868e96"  # szary
    ax.annotate(
        "", xy=(1.02, -0.06), xytext=(-0.02, -0.06),
        xycoords="axes fraction", textcoords="axes fraction",
        arrowprops=dict(arrowstyle="->", lw=2.2, color=arrow_color),
        clip_on=False, zorder=20
    )
    ax.annotate(
        "", xy=(-0.06, 1.02), xytext=(-0.06, -0.02),
        xycoords="axes fraction", textcoords="axes fraction",
        arrowprops=dict(arrowstyle="->", lw=2.2, color=arrow_color),
        clip_on=False, zorder=20
    )

    # --- NAZWY OSI: NA ŚRODKU BOKÓW (axes fraction)
    ax.text(-0.11, 0.75, "ZMIANA", transform=ax.transAxes,
            rotation=90, ha="center", va="center",
            fontsize=16, fontweight="bold", clip_on=False)
    ax.text(-0.11, 0.25, "PORZĄDEK", transform=ax.transAxes,
            rotation=90, ha="center", va="center",
            fontsize=16, fontweight="bold", clip_on=False)

    ax.text(0.25, -0.13, "NIEZALEŻNOŚĆ", transform=ax.transAxes,
            ha="center", va="center",
            fontsize=16, fontweight="bold", clip_on=False)
    ax.text(0.75, -0.13, "LUDZIE", transform=ax.transAxes,
            ha="center", va="center",
            fontsize=16, fontweight="bold", clip_on=False)

    # --- ETYKIETY ĆWIARTEK
    q1 = ax.text(-0.55, 1.02, "ZMIANA × NIEZALEŻNOŚĆ",
                 ha="center", va="center", fontsize=12, fontweight="bold",
                 bbox=dict(boxstyle="round,pad=0.25", fc="#d9dee5", ec="#b5bdc8"),
                 zorder=3)
    q2 = ax.text(0.55, 1.02, "ZMIANA × LUDZIE",
                 ha="center", va="center", fontsize=12, fontweight="bold",
                 bbox=dict(boxstyle="round,pad=0.25", fc="#d9dee5", ec="#b5bdc8"),
                 zorder=3)
    q3 = ax.text(-0.55, -1.02, "PORZĄDEK × NIEZALEŻNOŚĆ",
                 ha="center", va="center", fontsize=12, fontweight="bold",
                 bbox=dict(boxstyle="round,pad=0.25", fc="#d9dee5", ec="#b5bdc8"),
                 zorder=3)
    q4 = ax.text(0.55, -1.02, "PORZĄDEK × LUDZIE",
                 ha="center", va="center", fontsize=12, fontweight="bold",
                 bbox=dict(boxstyle="round,pad=0.25", fc="#d9dee5", ec="#b5bdc8"),
                 zorder=3)

    # --- ARCHETYPY: JEDEN KOLOR (żeby nie mieszały się z segmentami)
    ARCH_POINT_COLOR = "#4c6ef5"  # stały kolor archetypów / wartości
    ARCH_EDGE_COLOR = "white"
    ARCH_POINT_SIZE = 190

    # --- ETYKIETY ARCHETYPÓW: sterowanie odległością (w POINTS) + ręczne poprawki
    # Tip: przy dpi=180, 6 pt ≈ 15 px, 10 pt ≈ 25 px
    ARCH_LABEL_PAD_X = 10  # odległość pozioma etykiety od kropki
    ARCH_LABEL_PAD_Y = 10  # odległość pionowa etykiety od kropki

    # Ręczne wymuszenie (dx, dy) dla konkretnych archetypów:
    #  dx > 0 przesuwa w prawo, dx < 0 w lewo
    #  dy > 0 przesuwa do góry, dy < 0 w dół
    ARCH_LABEL_CUSTOM_OFFSETS = {
        # "Kochanek": (10, 0),
        # "Opiekun": (0, -10),
        # "Bohater": (10, -6),
        # "Twórca": (0, 10),
    }

    # --- anty-kolizja etykiet archetypów
    placed_bboxes = []

    def _renderer():
        fig.canvas.draw()
        return fig.canvas.get_renderer()

    def _bbox_of_text(txt):
        try:
            bb = txt.get_window_extent(renderer=_renderer())
            return bb.expanded(1.06, 1.18)
        except Exception:
            return None

    def _register_fixed_text(txt):
        bb = _bbox_of_text(txt)
        if bb is not None:
            placed_bboxes.append(bb)

    def _overlaps_any(bb):
        for b in placed_bboxes:
            try:
                if bb.overlaps(b):
                    return True
            except Exception:
                continue
        return False

    def _place_label(x, y, text, offsets, fontsize=12, fontweight="bold", zorder=5):
        for dx, dy in offsets:
            ha = "center" if dx == 0 else ("left" if dx > 0 else "right")
            va = "center" if dy == 0 else ("bottom" if dy > 0 else "top")

            txt = ax.annotate(
                str(text),
                (x, y),
                xytext=(dx, dy),
                textcoords="offset points",
                ha=ha, va=va,
                fontsize=fontsize,
                fontweight=fontweight,
                bbox=dict(boxstyle="round,pad=0.20", fc="white", ec="none", alpha=0.85),
                zorder=zorder,
            )
            try:
                txt.set_path_effects([pe.withStroke(linewidth=2.2, foreground="white")])
            except Exception:
                pass

            bb = _bbox_of_text(txt)
            if bb is not None and not _overlaps_any(bb):
                placed_bboxes.append(bb)
                return txt

            try:
                txt.remove()
            except Exception:
                pass

        dx, dy = offsets[-1]
        ha = "center" if dx == 0 else ("left" if dx > 0 else "right")
        va = "center" if dy == 0 else ("bottom" if dy > 0 else "top")
        txt = ax.annotate(
            str(text),
            (x, y),
            xytext=(dx, dy),
            textcoords="offset points",
            ha=ha, va=va,
            fontsize=fontsize,
            fontweight=fontweight,
            bbox=dict(boxstyle="round,pad=0.20", fc="white", ec="none", alpha=0.85),
            zorder=zorder,
        )
        try:
            txt.set_path_effects([pe.withStroke(linewidth=2.2, foreground="white")])
        except Exception:
            pass

        bb = _bbox_of_text(txt)
        if bb is not None:
            placed_bboxes.append(bb)
        return txt

    # stałe elementy jako przeszkody
    _register_fixed_text(q1)
    _register_fixed_text(q2)
    _register_fixed_text(q3)
    _register_fixed_text(q4)

    def _offsets_for_point(x, y):
        # Kierunek „na zewnątrz” względem środka mapy (0,0)
        sx = 1 if x >= 0 else -1
        sy = 1 if y >= 0 else -1

        dx = ARCH_LABEL_PAD_X * sx
        dy = ARCH_LABEL_PAD_Y * sy

        # Kolejność jest kluczowa: najpierw pozycje BLISKO punktu (góra/dół/bok),
        # dopiero potem dalsze awaryjne.
        return [
            (0, dy),
            (0, -dy),
            (dx, 0),
            (-dx, 0),

            (dx, dy),
            (dx, -dy),
            (-dx, dy),
            (-dx, -dy),

            (0, 2 * dy),
            (0, -2 * dy),
            (2 * dx, 0),
            (-2 * dx, 0),

            (2 * dx, dy),
            (2 * dx, -dy),
            (-2 * dx, dy),
            (-2 * dx, -dy),
        ]

    # --- archetypy (wszystkie w jednym kolorze)
    for lab in point_labels:
        lab_s = str(lab)
        x, y = coord_map.get(lab_s, (np.nan, np.nan))
        if not (np.isfinite(x) and np.isfinite(y)):
            continue

        ax.scatter(
            [x], [y],
            s=ARCH_POINT_SIZE,
            color=ARCH_POINT_COLOR,
            edgecolor=ARCH_EDGE_COLOR,
            linewidth=1.4,
            zorder=4
        )

        offsets = _offsets_for_point(x, y)
        if lab_s in ARCH_LABEL_CUSTOM_OFFSETS:
            offsets = [ARCH_LABEL_CUSTOM_OFFSETS[lab_s]] + offsets

        _place_label(x, y, _display_archetype_label(lab_s), offsets, fontsize=12, fontweight="bold", zorder=5)

    # --- segmenty: normalizacja do listy (sid, x, y)
    seg_points = []
    if seg_centroids is not None:
        try:
            if isinstance(seg_centroids, pd.DataFrame):
                dfc = seg_centroids.copy()
                cols = [c.lower() for c in dfc.columns]
                if ("x" in cols) and ("y" in cols):
                    xcol = dfc.columns[cols.index("x")]
                    ycol = dfc.columns[cols.index("y")]
                    sidcol = dfc.columns[cols.index("segment_id")] if "segment_id" in cols else None
                    for i in range(len(dfc)):
                        sid = int(dfc.loc[dfc.index[i], sidcol]) if sidcol else int(i)
                        sx = float(dfc.loc[dfc.index[i], xcol])
                        sy = float(dfc.loc[dfc.index[i], ycol])
                        seg_points.append((sid, sx, sy))
                else:
                    arrc = np.asarray(dfc.to_numpy(), dtype=float)
                    if arrc.ndim == 2 and arrc.shape[1] >= 2:
                        for i in range(arrc.shape[0]):
                            seg_points.append((i, float(arrc[i, 0]), float(arrc[i, 1])))
            else:
                arrc = np.asarray(seg_centroids)
                if arrc.ndim == 2 and arrc.shape[1] >= 2 and np.issubdtype(arrc.dtype, np.number):
                    arrc = np.asarray(arrc, dtype=float)
                    for i in range(arrc.shape[0]):
                        seg_points.append((i, float(arrc[i, 0]), float(arrc[i, 1])))
                else:
                    for r in list(seg_centroids):
                        if isinstance(r, dict):
                            sid = int(r.get("segment_id", r.get("segment", 0)))
                            sx = float(r.get("x", 0.0))
                            sy = float(r.get("y", 0.0))
                            seg_points.append((sid, sx, sy))
                        else:
                            rr = list(r)
                            if len(rr) >= 3:
                                seg_points.append((int(rr[0]), float(rr[1]), float(rr[2])))
                            elif len(rr) >= 2:
                                seg_points.append((len(seg_points), float(rr[0]), float(rr[1])))
        except Exception:
            seg_points = []

    # --- segmenty: STAŁE KOLORY, KOŁA, BEZ PODPISÓW NA MAPIE + POPRAWNA LEGENDA
    sids = [int(s[0]) for s in seg_points] if seg_points else []
    unique_sids = sorted(set(sids))
    zero_based = False
    if unique_sids:
        # heurystyka: jeśli wygląda na 0..n-1 => 0-based, w przeciwnym razie traktuj jako 1-based
        if min(unique_sids) == 0 and max(unique_sids) <= (len(unique_sids) - 1):
            zero_based = True

    def _seg_num(sid: int) -> int:
        return int(sid) + 1 if zero_based else int(sid)

    def _seg_desc(sid: int) -> str:
        # spróbuj klucza wprost, a jeśli nie ma – spróbuj „drugiej bazy”
        v = seg_names.get(sid, None)
        if v is None and zero_based:
            v = seg_names.get(int(sid) + 1, "")
        if v is None and (not zero_based):
            v = seg_names.get(int(sid) - 1, "")
        return str(v).strip() if v is not None else ""

    def _seg_color(seg_num: int):
        try:
            return str(_segment_ui_colors(int(seg_num)).get("accent", "#495057"))
        except Exception:
            return "#495057"

    seg_points_sorted = sorted(seg_points, key=lambda t: _seg_num(int(t[0])))

    legend_handles = []
    legend_labels = []

    for (sid, sx, sy) in seg_points_sorted:
        if not (np.isfinite(sx) and np.isfinite(sy)):
            continue

        seg_num = _seg_num(int(sid))
        c = _seg_color(seg_num)

        # najpierw ustal, czy ten segment w ogóle ma być pokazany
        desc = _seg_desc(int(sid))
        if seg_names is not None and not desc:
            continue

        # marker segmentu na mapie
        ax.scatter(
            [sx], [sy],
            s=220,
            marker="s",
            facecolor=c,
            edgecolor="white",
            linewidth=2.2,
            zorder=6
        )

        # legenda
        label = f"Seg_{seg_num}: {desc}" if desc else f"Seg_{seg_num}"

        legend_handles.append(
            Line2D([0], [0],
                   marker='s', linestyle='None',
                   markersize=9,
                   markerfacecolor=c,
                   markeredgecolor='white',
                   markeredgewidth=1.8)
        )
        legend_labels.append(label)


    if legend_handles:
        leg = ax.legend(
            legend_handles, legend_labels,
            loc="lower left",
            bbox_to_anchor=(1.01, 0.12),
            frameon=True,
            fancybox=True,
            framealpha=0.98,
            fontsize=11,
            borderpad=1.08,
            handletextpad=0.90,
            labelspacing=0.82
        )
        try:
            leg.get_frame().set_edgecolor("#cfd6de")
            leg.get_frame().set_linewidth(1.0)
        except Exception:
            pass

    ax.set_xticks([])
    ax.set_yticks([])
    ax.grid(False)

    fig.savefig(outpath, dpi=180, bbox_inches="tight", pad_inches=0.35)
    plt.close(fig)


# =========================
# 11) BĄBELKI: segmenty vs archetypy (odchylenie od średniej)
# =========================

def plot_segment_bubble_matrix(
        seg_means: pd.DataFrame,
        overall_mean: pd.Series,
        outpath: Path,
        title: str,
        highlight: Optional[Dict[Any, List[str]]] = None
) -> None:
    # seg_means: index=archetyp, columns=segment_id, values=mean (0..100)
    arch = list(seg_means.index)
    segs = list(seg_means.columns)

    # policz rozkład odchyleń, żeby dobrać skalowanie "z głową"
    deltas = []
    for a in arch:
        base = float(overall_mean.get(a, np.nan))
        for s in segs:
            v = float(seg_means.loc[a, s])
            if np.isfinite(base) and np.isfinite(v):
                deltas.append(abs(v - base))
    deltas = np.asarray(deltas, dtype=float)
    deltas = deltas[np.isfinite(deltas)]
    max_abs = float(np.nanmax(deltas)) if deltas.size else 0.0
    p50 = float(np.nanpercentile(deltas, 50)) if deltas.size else 0.0

    use_boost = (max_abs > 0) and (p50 > 0) and ((max_abs / p50) < 1.8)

    def bubble_size(absd: float) -> float:
        absd = float(absd)
        if not np.isfinite(absd) or absd <= 0:
            return 70.0
        if not use_boost:
            return 60.0 + min(1200.0, absd * 140.0)
        norm = min(1.0, absd / (max_abs + 1e-12))
        return 80.0 + min(1400.0, 1400.0 * (norm ** 1.7))

    fig, ax = plt.subplots(figsize=(1.6 * len(segs) + 4, 0.55 * len(arch) + 3))

    highlight = highlight or {}
    highlight_sets = {k: set(str(x) for x in v) for k, v in highlight.items()}

    for yi, a in enumerate(arch):
        base = float(overall_mean.get(a, np.nan))
        for xi, s in enumerate(segs):
            v = float(seg_means.loc[a, s])
            if not np.isfinite(base) or not np.isfinite(v):
                continue
            d = v - base

            size = bubble_size(abs(d))

            # czy to jest archetyp wyróżniony w tym segmencie?
            hi_set = highlight_sets.get(s, set())
            is_hi = (str(a) in hi_set)

            # kolory: wyróżnione = mocniejsze / inne niż pozostałe
            if d > 0.05:
                c = "darkgreen" if is_hi else "lightgreen"
            elif d < -0.05:
                c = "darkred" if is_hi else "salmon"
            else:
                c = "dimgray" if is_hi else "lightgray"

            alpha = 0.70 if is_hi else 0.45

            ax.scatter(xi, yi, s=size, alpha=alpha, color=c, clip_on=False)
            ax.text(xi, yi, f"{d:+.1f}", ha="center", va="center", fontsize=8, clip_on=False)

    ax.set_xticks(range(len(segs)))

    # Ujednolicone etykiety osi X (działa i dla int, i dla stringów)
    xlabels = []
    for s in segs:
        if isinstance(s, (int, np.integer)):
            xlabels.append(f"Seg_{int(s) + 1}")
        else:
            xlabels.append(str(s))
    ax.set_xticklabels(xlabels, fontsize=10, fontweight="bold")

    ax.set_yticks(range(len(arch)))
    ax.set_yticklabels(_display_archetype_labels(arch), fontsize=10)

    # Marginesy osi, żeby duże bąbelki nie były obcinane
    ax.set_xlim(-0.5, len(segs) - 0.5)
    ax.set_ylim(len(arch) - 0.5, -0.5)
    ax.margins(x=0.05, y=0.08)

    ax.grid(axis="x", alpha=0.18)
    ax.set_title(title, fontsize=14, fontweight="bold", pad=12)
    plt.tight_layout()
    plt.savefig(outpath, dpi=180, bbox_inches="tight", pad_inches=0.15)
    plt.close()


# =========================
# 12) RAPORT HTML (dashboard bez bibliotek JS)
# =========================

def df_to_html(df: pd.DataFrame, max_rows: int = 60) -> str:
    d = df.copy()
    if len(d) > max_rows:
        d = d.head(max_rows)
    return d.to_html(index=False, border=0, classes="tbl", escape=False)


CHART_NOTES = {
    "P_mean.png": "P (preferencje): średnia w skali centrowanej używanej przez model. 0 = punkt neutralny; wartości dodatnie = ponad neutralem, ujemne = poniżej.",
    "E_mean.png": "E (doświadczenie): średni bilans doświadczeń w skali centrowanej. Dodatnie = przewaga PLUS, ujemne = przewaga MINUS.",
    "G_mean.png": "G (priorytet): średni indeks priorytetu w skali centrowanej modelu. Wyżej = większa potrzeba działania.",
    "A_strength.png": "Bradley–Terry (~50±10): model porównań parami. Wyżej = silniejszy archetyp w całej sieci pojedynków A.",
    "A_strength_values.png": "Bradley–Terry (~50±10): model porównań parami. Wyżej = silniejsza wartość w całej sieci pojedynków A.",
    "A_bilans_starc.png": "Bilans starć (wygrane - przegrane): ważony bilans pojedynków archetypu / wartości w całej sieci A. Dodatnie = przewaga wygranych, ujemne = przewaga przegranych.",
    "A_zwyciestwa_przegrane.png": "Zwycięstwa vs przegrane: dla każdej pary wyznaczony końcowy zwycięzca. Zwycięzca dostaje +1, przegrany -1, remis = 0. Zakres wyniku: od -3 do +3.",
    "A_versusy_liniowy.png": "Versus (18 par): średnia pozycja odpowiedzi na skali 1–7 dla każdej pary. 1 = lewa strona, 4 = środek, 7 = prawa strona.",
    "A_expectation_expected_pct.png": "Wynik główny: odsetek mieszkańców, którzy netto oczekują danego archetypu po zbilansowaniu 3 porównań (score_mean > 0).",
    "A_expectation_expected_pct_values.png": "Wynik główny: odsetek mieszkańców, którzy netto oczekują danej wartości po zbilansowaniu 3 porównań (score_mean > 0).",
    "A_expectation_ioa_100.png": "PPP 0-100 (Profil Preferencji Przywództwa): wskaźnik siły preferencji przywództwa (nie jest procentem mieszkańców). Linia odniesienia: 50.",
    "A_expectation_ioa_100_values.png": "PPP 0-100 (Profil Preferencji Przywództwa): wskaźnik siły preferencji przywództwa (nie jest procentem mieszkańców). Linia odniesienia: 50.",
    "ISOA_ISOW_wheel.png": "ISOA 0-100: syntetyczny indeks społecznego oczekiwania archetypu (A, B1, B2, C13/D13), nie jest procentem mieszkańców.",
    "ISOA_ISOW_wheel_values.png": "ISOW 0-100: syntetyczny indeks społecznego oczekiwania wartości (A, B1, B2, C13/D13), nie jest procentem mieszkańców.",
    "B1_top3.png": "Odsetek osób, które umieściły archetyp w swojej „trójce” (maks. 3 wybory).",
    "B1_top3_values.png": "Odsetek osób, które umieściły wartość w swojej „trójce” (maks. 3 wybory).",
    "B2_top1.png": "Odsetek wskazań archetypu jako najważniejszego (TOP1).",
    "B2_top1_values.png": "Odsetek wskazań wartości jako najważniejszej (TOP1).",
    "B1_trojki_top5.png": "Najczęstsze kombinacje trzech archetypów (TOP5).",
    "D_plus_minus_diverging.png": "Doświadczenie mieszkańców: POZYTYWNE po prawej (zielony), NEGATYWNE po lewej (czerwony). To sentyment doświadczeń.",
    "D_kolo_plus_minus.png": "Wykres kołowy: dla każdego archetypu udział NEGATYWNY (czerwony) i POZYTYWNY (niebieski) w odpowiedziach.",
    "D_kolo_plus_minus_values.png": "Wykres kołowy: dla każdej wartości udział NEGATYWNY (czerwony) i POZYTYWNY (niebieski) w odpowiedziach.",
    "D13_top1.png": "Długość słupka = udział wskazań jako najważniejszego; podział kolorów = sentyment wśród wskazujących ten archetyp.",
    "D13_top1_values.png": "Długość słupka = udział wskazań jako najważniejszego; podział kolorów = sentyment wśród wskazujących tę wartość.",
    "mentions_total.png": "Suma ważonych wskazań archetypów we wszystkich pytaniach wyboru.",
    "SEGMENTY_META_MAPA_STALA.png": "Stała mapa ćwiartek segmentów: archetypy / wartości są osadzone w stałym układzie, a segmenty pokazujemy jako centroidy i obszary interpretacyjne.",
    "SEGMENTY_METRYCZKA_P_babelki.png": "Profile (deterministyczne): odchylenie P od średniej. Rozmiar bąbla = |odchylenie|.",
    "SEGMENTY_POSTAWY_P_babelki.png": "Postawy (P+E): odchylenie P od średniej. Rozmiar bąbla = |odchylenie|.",
    "SKUPIENIA_DOBOR_K_SILHOUETTE.png": "Dobór liczby skupień: wyższa silhouette oznacza lepsze rozdzielenie i większą spójność skupień.",
    "SKUPIENIA_DOBOR_K_ELBOW.png": "Dobór liczby skupień metodą elbow: WSS maleje wraz z K; szukamy punktu, po którym kolejne zwiększanie K daje już niewielką poprawę.",
    "SKUPIENIA_MAPA_PCA.png": "Mapa skupień (projekcja profilu P): punkty to respondenci, duże punkty to centroidy skupień (Seg_1..Seg_K).",
    "SKUPIENIA_MAPY_K_POROWNANIE.png": "Porównanie wizualizacji k-średnich dla kilku wartości K (np. 3–6): punkty respondentów, obrysy skupień i centroidy.",
    "HEATMAPA_KORELACJI_P.png": "Korelacje P: +1 = współwystępowanie, −1 = przeciwieństwo, 0 = brak zależności. Kolor nazwy oznacza oś potrzeb danego archetypu; legenda pod wykresem.",
    "HEATMAPA_KORELACJI_E.png": "Korelacje E: jak wyżej, ale dla doświadczeń (PLUS/MINUS). Kolor nazwy oznacza oś potrzeb danego archetypu; legenda pod wykresem.",
    "HEATMAPA_KORELACJI_G.png": "Korelacje G: jak wyżej, ale dla priorytetów. Kolor nazwy oznacza oś potrzeb danego archetypu; legenda pod wykresem.",
    "HEATMAPA_KORELACJI_P_values.png": "Korelacje P: +1 = współwystępowanie, −1 = przeciwieństwo, 0 = brak zależności. Kolor nazwy oznacza oś potrzeb, z której pochodzi dana wartość.",
    "HEATMAPA_KORELACJI_E_values.png": "Korelacje E: jak wyżej, ale dla doświadczeń (PLUS/MINUS). Kolor nazwy oznacza oś potrzeb, z której pochodzi dana wartość.",
    "HEATMAPA_KORELACJI_G_values.png": "Korelacje G: jak wyżej, ale dla priorytetów. Kolor nazwy oznacza oś potrzeb, z której pochodzi dana wartość.",
    "MAPA_WARTOSCI_P_DATA.png": "Mapa wartości dla P = preferencje. Pokazuje, które wartości są wybierane podobnie. Im bliżej siebie leżą punkty, tym częściej pojawiają się razem w podobnym układzie preferencji. Osie pokazują autorski model: ludzie ↔ niezależność oraz zmiana ↔ porządek.",
    "MAPA_WARTOSCI_E_DATA.png": "Mapa wartości dla E = doświadczenia. Pokazuje, które wartości są przeżywane w podobny sposób przez respondentów (na plus lub na minus). Im bliżej siebie leżą punkty, tym bardziej podobny jest wzór doświadczeń tych wartości.",
    "MAPA_WARTOSCI_G_DATA.png": "Mapa wartości dla G = priorytety. Pokazuje, które wartości trafiają do podobnej hierarchii ważności. Im bliżej siebie leżą punkty, tym częściej respondenci ustawiają je blisko siebie w rankingu priorytetów.",
}


def df_to_html_sig(df: pd.DataFrame, max_rows: int = 60) -> str:
    """
    Prosty wrapper do tabel „sygnatur” (premium).
    Używamy standardowego df_to_html, ale trzymamy osobną nazwę, bo w kodzie segmentacji
    występuje historycznie df_to_html_sig().
    """
    return df_to_html(df, max_rows=max_rows)


def img_tag(fname: str) -> str:
    """
    Zwraca <img> z poprawną ścieżką względem raport.html (plik raportu jest w katalogu WYNIKI).
    """
    src = Path(__file__).resolve().parent / "WYNIKI" / fname
    note = CHART_NOTES.get(fname, "")
    note_html = f"<div class='small chart-note'>{note}</div>" if note else ""

    if not src.exists():
        return f"<div class='small mono'>Brak pliku: {fname}</div>{note_html}"

    # raport.html leży w WYNIKI, więc w HTML podajemy samą nazwę pliku
    # + link do pliku (klik = pełny rozmiar)
    return f'<a href="{fname}" target="_blank" rel="noopener"><img class="img" src="{fname}" alt="{fname}"></a>{note_html}'


# ==============================================================
# 11Z) PREMIUM SEGMENTACJA — UI (jedna zakładka „Segmenty”, jeden suwak K) w raporcie HTML
# ==============================================================

def seg_panel_html(tab_key: str, title: str, subtitle: str, slider_min: int, slider_max: int, slider_default: int,
                   include_lca_sig: bool = False) -> str:
    """Zwraca HTML panelu segmentacji ultra premium dla jednej zakładki."""
    _ = include_lca_sig  # zostawiamy parametr tylko dla zgodności wywołań

    return f"""
    <div class="card" style="margin-top:12px;">
      <h3 style="margin:0 0 6px 0;">{title}</h3>
      <div class="small">{subtitle}</div>

      <div style="margin-top:10px;">
        <span class='seg-help'>Widoczne segmenty: <b><span id="seg_{tab_key}_kval">{slider_default}</span></b></span>
        &nbsp; / &nbsp; Model: <b><span id="seg_{tab_key}_kbest">--</span></b>
        &nbsp; / &nbsp; <span title="Jakość modelu segmentacji: łączy separację segmentów i stabilność profili (im wyżej, tym lepiej).">Jakość</span>: <b><span id="seg_{tab_key}_score">--</span></b>
        &nbsp; / &nbsp; <span title="Średnia użyteczność segmentów: praktyczna wyrazistość i interpretowalność profili (im wyżej, tym lepiej).">Śr. użyteczność</span>: <b><span id="seg_{tab_key}_use">--</span></b>
        <div class="small" style="margin:6px 0 4px 0;">Jakość = łączny wskaźnik separacji segmentów (silhouette + minimalny udział + dystans centroidów). Śr. użyteczność = średnia siła wyrazistości profili segmentów (im wyżej, tym lepiej).</div>

        <input id="seg_{tab_key}_slider" type="range" min="{slider_min}" max="{slider_max}" step="1" value="{slider_default}"
               style="width:100%; margin-top:8px;" />
      </div>
    </div>

    <div id="seg_{tab_key}_profiles" style="margin-top:16px;"></div>

    <div class="card" style="margin-top:16px;">
      <h3>Matryca segmentów</h3>
      <div id="seg_{tab_key}_matrix" style="margin-top:10px;"></div>
    </div>
    """


# martwy helper seg_js_snippet usunięty — aktywny JS składamy bezpośrednio w save_report

def save_report(outdir: Path, settings: Settings,
                df_group: pd.DataFrame,
                df_A_pairs: pd.DataFrame,
                df_A_strength: pd.DataFrame,
                df_A_pair_balance: pd.DataFrame,
                df_B1: pd.DataFrame,
                df_B2: pd.DataFrame,
                df_B_tr: pd.DataFrame,
                df_D12: pd.DataFrame,
                df_D13: pd.DataFrame,
                df_mentions_q: pd.DataFrame,
                df_top5_A: pd.DataFrame,
                df_B1_pct: pd.DataFrame,
                df_B2_pct: pd.DataFrame,
                df_D13_pct: pd.DataFrame,
                df_A_expectation_main: Optional[pd.DataFrame] = None,
                df_A_expectation_pair_detail: Optional[pd.DataFrame] = None,
                expectation_summary_payload: Optional[Dict[str, List[str]]] = None,
                expectation_weighting_meta: Optional[Dict[str, Any]] = None,
                df_social_expectation_index: Optional[pd.DataFrame] = None,
                social_expectation_meta: Optional[Dict[str, Any]] = None,
                filters_pct: Optional[Dict[str, Dict[str, float]]] = None,
                brand_values: Optional[Dict[str, str]] = None,
                seg_packs_render: Optional[Dict[str, Any]] = None,
                poststrat_diag: Optional[pd.DataFrame] = None,
                b2_declared_demo_payload: Optional[Dict[str, Any]] = None,
                top5_simulation_payload: Optional[Dict[str, Any]] = None,
                cluster_pack: Optional[Dict[str, Any]] = None,
                n_respondents_total: Optional[int] = None) -> None:
    brand_values = brand_values or dict(DEFAULT_BRAND_VALUES)
    filters_pct = filters_pct or {}
    cluster_pack = cluster_pack or {}
    expectation_summary_payload = expectation_summary_payload or {}
    expectation_weighting_meta = expectation_weighting_meta or {}
    social_expectation_meta = social_expectation_meta or {}
    n_respondents_total = int(max(0, int(n_respondents_total or 0)))
    df_A_expectation_main = (
        df_A_expectation_main.copy()
        if isinstance(df_A_expectation_main, pd.DataFrame)
        else pd.DataFrame()
    )
    df_A_expectation_pair_detail = (
        df_A_expectation_pair_detail.copy()
        if isinstance(df_A_expectation_pair_detail, pd.DataFrame)
        else pd.DataFrame()
    )
    df_social_expectation_index = (
        df_social_expectation_index.copy()
        if isinstance(df_social_expectation_index, pd.DataFrame)
        else pd.DataFrame()
    )
    has_poststrat = poststrat_diag is not None and len(poststrat_diag) > 0

    import json

    def _js_json(obj: Any) -> str:
        """
        Bezpieczny JSON do wklejenia w <script>.
        - ensure_ascii=True: ucieka znaki typu U+2028/U+2029, które potrafią ubić JS w HTML.
        - replace("</", "<\\/"): zabezpiecza przed przypadkowym zamknięciem tagu <script>.
        """
        s = json.dumps(obj, ensure_ascii=True)
        s = s.replace("</", "<\\/")
        return s

    _filter_blocks_json = _js_json(["A", "B1", "B2", "D13"])
    _filter_pct_json = _js_json(filters_pct)
    _brand_values_json = _js_json(brand_values)
    _feminine_labels_json = _js_json(ARCHETYPE_FEMININE_MAP)
    _archetype_label_mode_json = _js_json(
        _normalize_archetype_label_mode(getattr(settings, "archetype_label_mode", "male"))
    )

    def _slug_ascii_local(s: str) -> str:
        tr = str.maketrans({
            "ł": "l", "Ł": "L",
            "ą": "a", "Ą": "A",
            "ć": "c", "Ć": "C",
            "ę": "e", "Ę": "E",
            "ń": "n", "Ń": "N",
            "ó": "o", "Ó": "O",
            "ś": "s", "Ś": "S",
            "ż": "z", "Ż": "Z",
            "ź": "z", "Ź": "Z",
        })
        txt = str(s or "").translate(tr)
        txt = unicodedata.normalize("NFKD", txt)
        txt = "".join(ch for ch in txt if not unicodedata.combining(ch))
        txt = re.sub(r"[^a-zA-Z0-9]+", "_", txt).strip("_").lower()
        return txt

    filter_icons = {str(a): f"icons/{_slug_ascii_local(str(a))}.png" for a in ARCHETYPES}
    _filter_icons_json = _js_json(filter_icons)
    _seg_packs_json = _js_json(seg_packs_render or {})
    _cluster_pack_json = _js_json(cluster_pack or {})

    css = """
<style>
body { font-family: "Segoe UI", Calibri, Arial, sans-serif; margin: 18px; color:#1f2937; background: radial-gradient(circle at 12% 0%, #f4f8fd 0%, #f8fafc 35%, #ffffff 100%); }
h1 { margin: 0 0 8px 0; color:#0f172a; letter-spacing:.01em; }
.small { color: #5f6b7a; font-size: 13px; margin-bottom: 14px; }
.chart-note { margin-top: 18px !important; margin-bottom: 18px !important; line-height: 1.5; }
.tbl { border-collapse: collapse; width: 100%; margin-top: 10px; }
.tbl th, .tbl td { border: 1px solid #d6dee8; padding: 7px 9px; font-size: 13px; }
.tbl th { background: #eef3f9; text-align: left; color:#1e293b; font-weight:800; }
.grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.grid3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }
.card { border: 1px solid #dfe6ef; border-radius: 14px; padding: 12px 14px; background: #fff; box-shadow: 0 10px 22px rgba(15, 23, 42, .045); box-sizing:border-box; }
.card h3 { margin: 10px 0 10px 0; }
.card.chart-half { width: calc((100% - 16px) / 2); max-width: calc((100% - 16px) / 2); min-width:0; box-sizing:border-box; }
.chart-pair { display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:16px; align-items:start; }
.chart-pair .card.chart-half { width:100%; max-width:100%; }
.panel.pK .card.corr-tile { padding-bottom: 12px; }
.panel.pK .card.corr-tile .label-arche > a,
.panel.pK .card.corr-tile .label-values > a {
  display:block;
  border:1px solid #d6deea;
  border-radius:10px;
  box-shadow: 0 8px 22px rgba(15,23,42,.05);
  overflow:hidden;
  padding:36px 0;
}
.panel.pK .card.corr-tile .label-arche > a > img.img,
.panel.pK .card.corr-tile .label-values > a > img.img {
  border:none;
  box-shadow:none;
  border-radius:0;
}

.seg-card {
  border-left-width: 6px;
  border-left-style: solid;
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.06);
  overflow: hidden;
}
.seg-card + .seg-card { margin-top: 22px; }
.seg-card:last-child { margin-bottom: 0; }

.seg-top {
  display:flex;
  justify-content:space-between;
  gap:14px;
  align-items:flex-start;
  flex-wrap:wrap;
}
.seg-top-main { flex:1 1 420px; min-width:320px; }
.seg-top-side { flex:0 1 360px; min-width:280px; }

.seg-badge {
  display:inline-flex;
  align-items:center;
  gap:8px;
  padding:6px 10px;
  border:1px solid #dbe4ff;
  border-radius:999px;
  font-size:12px;
  font-weight:800;
  letter-spacing:.03em;
  text-transform:uppercase;
}

.seg-metrics {
  display:flex;
  flex-wrap:wrap;
  gap:8px;
  margin-top:10px;
}
.seg-metric-pill {
  display:inline-flex;
  gap:6px;
  align-items:center;
  padding:6px 10px;
  border:1px solid #e9ecef;
  border-radius:999px;
  background:#f8f9fa;
  font-size:12px;
}
.seg-metric-pill b { font-size:13px; }

.seg-mini-label {
  font-size:12px;
  font-weight:800;
  letter-spacing:.03em;
  text-transform:uppercase;
  color:#5f6b7a;
  margin-bottom:6px;
}

.seg-duo {
  display:grid;
  grid-template-columns:minmax(620px, 980px) minmax(320px, 1fr);
  gap:18px;
  margin-top:20px;
}

.seg-main-col {
  width:100%;
  max-width:980px;
}

.seg-row {
  display:grid;
  grid-template-columns:repeat(2, minmax(260px, 1fr));
  gap:14px;
  margin-top:14px;
}
.seg-three {
  display:grid;
  grid-template-columns:repeat(2, minmax(260px, 1fr));
  gap:16px;
  margin-top:18px;
}

.seg-wide {
  grid-column:1 / -1;
}

.seg-box {
  border:1px solid #e6e8ee;
  border-radius:10px;
  padding:14px;
  background:#fff;
}

.seg-demo-wrap {
  margin-top:20px;
  max-width:980px;
}

.seg-demo-scroll { overflow-x:auto; }
.seg-demo-wrap .tbl { width:100%; margin-top:6px; }

.seg-map-wrap { text-align:left; overflow:visible; }
.seg-map-wrap .label-arche, .seg-map-wrap .label-values { max-width: 1180px; }

hr { border: none; border-top: 1px solid #e4e9f0; margin: 18px 0; }
.mono { font-family: Consolas, monospace; font-size: 12px; }

/* obrazki wykresów: wypełniają kartę, bez centrowania "na wyspie" */
img { max-width: 100%; height: auto; }
img.img { display:block; width:100%; max-width:1380px; height:auto; margin:0; border:1px solid #d6deea; border-radius:10px; box-shadow: 0 8px 22px rgba(15,23,42,.05); }
img.img-profile-sm { width:64%; margin-left:0; margin-right:0; }
.cluster-figure-wrap { width:100%; max-width:1240px; margin:0; }
.cluster-figure-wrap.main { max-width:1120px; }
.cluster-legend-note { margin-top:6px; font-size:12px; color:#5f6b7a; }

@media (max-width: 1100px) {
  img.img-profile-sm { width:100%; }
  .cluster-figure-wrap.main { max-width:100%; }

  .seg-duo { grid-template-columns:1fr; }
  .seg-three { grid-template-columns:1fr; }
  .seg-row { grid-template-columns:1fr; }
  .seg-main-col { max-width:none; }
  .chart-pair { grid-template-columns:1fr; }
  .card.chart-half { width: 100%; max-width: 100%; }
  .ioa-summary-grid { grid-template-columns: 1fr; }
}

/* icons in TOP5 tables */
.aicon { display: inline-flex; align-items: center; gap: 6px; white-space: nowrap; }
.aico { width: 18px; height: 18px; vertical-align: -3px; object-fit: contain; border-radius: 0 !important; flex: 0 0 auto; }

/* TOP5 matrix */
.top5mat th, .top5mat td { text-align: center; vertical-align: middle; }
.top5mat td:first-child, .top5mat th:first-child { text-align: left; }
.rank { color:#888; font-size: 11px; margin-left: 6px; }

/* wyróżnienia miejsc (1–3) */
.rk { display:inline-block; padding:2px 6px; border-radius:8px; }
.rk1 { background:#fff3bf; }
.rk2 { background:#e9ecef; }
.rk3 { background:#ffd8a8; }
.rk4 { background:#dbe4ff; }  /* jasny niebiesko-lawendowy */
.rk5 { background:#edf2ff; }  /* jeszcze jaśniejszy */

/* DOT-matrix TOP5 */
.dotmat th, .dotmat td { text-align: center; vertical-align: middle; }
.dotmat td:first-child, .dotmat th:first-child { text-align: left; }
.dot { display:inline-block; width:11px; height:11px; border-radius:50%; }
.d1 { background:#ffd43b; }
.d2 { background:#adb5bd; }
.d3 { background:#ffa94d; }
.d4 { background:#748ffc; }   /* wyraźny fioletowo-niebieski */
.d5 { background:#bac8ff; }   /* jaśniejszy od #4 */

.dot-legend { display:flex; flex-wrap:wrap; gap:10px; align-items:center; }
.dot-legend span { display:inline-flex; align-items:center; gap:6px; font-size:13px; }

/* PPP / ISOA section */
.ioa-status-card {
  border-left: 6px solid #2b6cb0;
  background: linear-gradient(180deg, #f8fbff 0%, #ffffff 100%);
}
.panel.pW h2 {
  font-size: 22px;
  line-height: 1.2;
  margin-bottom: 6px;
}
.panel.pI h2 {
  font-size: 21px;
  line-height: 1.2;
  margin-bottom: 6px;
}
.ioa-balance-legend {
  margin-top: 12px;
  background: linear-gradient(180deg, #fbfdff 0%, #ffffff 100%);
  padding: 16px 18px;
}
.ioa-balance-row {
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  margin-top: 8px;
  margin-bottom: 10px;
}
.ioa-pill {
  display: inline-flex;
  align-items: center;
  padding: 9px 13px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  border: 1px solid transparent;
}
.ioa-pill-pos { background:#e8f5ea; color:#1b5e20; border-color:#cce3d0; }
.ioa-pill-neu { background:#f2f4f7; color:#475467; border-color:#d0d5dd; }
.ioa-pill-neg { background:#fdecec; color:#a61e1e; border-color:#f3cccc; }
.ioa-balance-legend .small { line-height: 1.58; margin-bottom: 0; }
.ioa-balance-card { min-height: 620px; }

.ioa-summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(220px, 1fr));
  gap: 14px;
}
.ioa-summary-item {
  border: 1px solid #dbe4ef;
  border-radius: 12px;
  padding: 12px 12px 10px 12px;
  background: linear-gradient(180deg, #fbfcff 0%, #ffffff 100%);
}
.ioa-summary-item h4 {
  margin: 0 0 8px 0;
  font-size: 16px;
  line-height: 1.28;
}
.sum-up-arrow { color:#1e40af; font-weight:900; margin-right:6px; }
.sum-down-arrow { color:#b42318; font-weight:900; margin-right:6px; }
.ioa-list {
  margin: 0;
  padding-left: 20px;
}
.ioa-list li {
  margin: 6px 0;
}
.ioa-list.tone-up li { color:#1e40af; font-weight:700; }
.ioa-list.tone-down li { color:#b42318; font-weight:700; }
.ioa-list.tone-up .aico { filter: invert(25%) sepia(66%) saturate(1329%) hue-rotate(202deg) brightness(90%) contrast(95%); }
.ioa-list.tone-down .aico { filter: invert(25%) sepia(94%) saturate(2283%) hue-rotate(344deg) brightness(92%) contrast(101%); }
.ioa-howto h3 { font-size: 18px; margin-bottom: 6px; }
.ioa-howto ul li { font-size: 12.5px; line-height: 1.33; }

.ioa-main-table td:nth-child(3) {
  font-weight: 800;
  color: #0f172a;
}
.ioa-main-table th { color:#0f172a !important; }
.ioa-main-table th:nth-child(1), .ioa-main-table td:nth-child(1) {
  width: 64px;
  max-width: 64px;
  text-align: center;
}
.ioa-main-table th:nth-child(2), .ioa-main-table td:nth-child(2) {
  min-width: 230px;
}
.ioa-main-table td:nth-child(8) {
  color: #556070;
}
.ppp-main-table td:nth-child(3) {
  font-weight: 800;
  color:#0f172a;
}
.ppp-main-table th:nth-child(1), .ppp-main-table td:nth-child(1) {
  width: 64px;
  max-width: 64px;
  text-align: center;
}
.ppp-main-table th:nth-child(2), .ppp-main-table td:nth-child(2) {
  min-width: 230px;
}
.ppp-main-table th:nth-child(3) { color:#0b6b2d; }
.ppp-main-table th:nth-child(4) { color:#334155; }
.ppp-main-table th:nth-child(5) { color:#c62000; }
.ppp-main-table th:nth-child(6) { color:#00509d; }
.ppp-main-table th:nth-child(7) { color:#0f172a; }
.isoa-wheel-wrap{
  width:85%;
  margin:0;
}
.isoa-axis-legend {
  margin-top: 10px;
  display: flex;
  flex-wrap: wrap;
  gap: 14px;
  align-items: center;
  font-size: 13px;
  color: #334155;
}
.isoa-axis-legend span {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.isoa-axis-legend i {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 3px;
}

/* tabs (pure CSS) */
.tabs { margin-top: 14px; }
/* ukrywamy tylko radiobuttony od zakładek (żeby nie chować suwaków / inputów w panelach) */
.tabs > input[type="radio"][name="tabs"] { display:none; }
.tabs label {
  display:inline-block; padding:10px 12px; margin-right:6px;
  border:1px solid #ddd; border-bottom:none; border-radius:10px 10px 0 0;
  background:#f8f8f8; cursor:pointer; font-weight:700; font-size:13px;
}
.tabs .panel {
  display:none; border:1px solid #ddd; border-radius:0 12px 12px 12px;
  padding:14px; background:#fff;
}
#tab0:checked ~ .labels label[for="tab0"],
#tabW:checked ~ .labels label[for="tabW"],
#tabA:checked ~ .labels label[for="tabA"],
#tabI:checked ~ .labels label[for="tabI"],
#tabB:checked ~ .labels label[for="tabB"],
#tabD:checked ~ .labels label[for="tabD"],
#tabK:checked ~ .labels label[for="tabK"],
#tabM:checked ~ .labels label[for="tabM"],
#tabR:checked ~ .labels label[for="tabR"],
#tabT:checked ~ .labels label[for="tabT"],
#tabS:checked ~ .labels label[for="tabS"],
#tabC:checked ~ .labels label[for="tabC"],
#tabG:checked ~ .labels label[for="tabG"],
#tabH:checked ~ .labels label[for="tabH"],
#tabY:checked ~ .labels label[for="tabY"] { background:#fff; border-bottom:1px solid #fff; }

#tab0:checked ~ .p0,
#tabW:checked ~ .pW,
#tabA:checked ~ .pA,
#tabI:checked ~ .pI,
#tabB:checked ~ .pB,
#tabD:checked ~ .pD,
#tabK:checked ~ .pK,
#tabM:checked ~ .pM,
#tabR:checked ~ .pR,
#tabT:checked ~ .pT,
#tabS:checked ~ .pS,
#tabC:checked ~ .pC,
#tabG:checked ~ .pG,
#tabH:checked ~ .pH,
#tabY:checked ~ .pY { display:block; }

/* tryb etykiet: archetypy vs wartości */
.label-values { display:none; }
.mode-values { display:none; }
body[data-label-mode="values"] .label-arche { display:none; }
body[data-label-mode="values"] .label-values { display:block; }
body[data-label-mode="values"] .mode-arche { display:none; }
body[data-label-mode="values"] .mode-values { display:inline; }
</style>
"""

    js = ("""
    <script>
    /* ====== DATA for "Filtry" tab (injected by Python) ====== */
    const FILTER_BLOCKS = __FILTER_BLOCKS__;
    const FILTER_PCT = __FILTER_PCT__;
    const BRAND_VALUES = __BRAND_VALUES__;
    const FILTER_ICONS = __FILTER_ICONS__;
    const FEMININE_LABELS = __FEMININE_LABELS__;
    const ARCHETYPE_LABEL_MODE = __ARCHETYPE_LABEL_MODE__;

    document.addEventListener("DOMContentLoaded", function() {
      /* ---------- localStorage (file:// bywa blokowane) ---------- */
      function _lsGet(key, defVal){
        try {
          const v = localStorage.getItem(key);
          return (v === null ? defVal : v);
        } catch(e){
          return defVal;
        }
      }
      function _lsSet(key, val){
        try { localStorage.setItem(key, val); } catch(e) {}
      }

      /* ---------- label mode (existing feature) ---------- */
      function applyMode(mode){
        document.body.setAttribute("data-label-mode", mode);
      }
      function getMode(){
        return document.body.getAttribute("data-label-mode") || "arche";
      }
      function labelForArche(a){
        if (getMode() === "values") return (BRAND_VALUES[a] || a);
        if (ARCHETYPE_LABEL_MODE === "female") return (FEMININE_LABELS[a] || a);
        return a;
      }

      const saved = _lsGet("labelMode", "arche");
      applyMode(saved);

      const rA = document.getElementById("mode_arche");
      const rV = document.getElementById("mode_values");
      if (rA && rV){
        if (saved === "values") { rV.checked = true; } else { rA.checked = true; }
      }

      /* ---------- helpers ---------- */
        function blockLabel(b){
          const m = {
            "A": "oczekujący\\n(A)",
            "B1": "3 priorytety\\n(B1)",
            "B2": "najważniejszy\\n(B2)",
            "D13": "doświadczenie\\n(D13)",
          };
          return m[b] || String(b);
        }

      function slugAscii(s){
        s = String(s || "");
        const map = {
          "ł":"l","Ł":"L","ą":"a","Ą":"A","ć":"c","Ć":"C","ę":"e","Ę":"E",
          "ń":"n","Ń":"N","ó":"o","Ó":"O","ś":"s","Ś":"S","ż":"z","Ż":"Z","ź":"z","Ź":"Z",
        };
        s = s.split("").map(ch => (map[ch] || ch)).join("");
        try { s = s.normalize("NFKD"); } catch(e) {}
        s = s.replace(/[\u0300-\u036f]/g, "");
        s = s.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_+|_+$/g, "");
        return s;
      }

      function iconSrc(archeKey){
        const key = String(archeKey || "");
        return (FILTER_ICONS && FILTER_ICONS[key]) || ("icons/" + slugAscii(key) + ".png");
      }
      function toNumOrNaN(x){
        if (x === null || x === undefined || x === "") return NaN;
        const n = Number(x);
        return (isFinite(n) ? n : NaN);
      }

      /* ---------- Filtry: dropdown + charts ---------- */
      const ARCHES = Object.keys(FILTER_PCT || {});
      const MAX_RANK = 12; // stała oś 1–12

      function buildRanks(){
        const ranks = {};
        FILTER_BLOCKS.forEach(function(b){
          const arr = ARCHES.map(function(a){
            const v = toNumOrNaN((FILTER_PCT[a] || {})[b]);
            const vv = (isFinite(v) ? v : -1e9); // braki danych zawsze na końcu rankingu
            return [a, vv];
          });
          arr.sort(function(x, y){ return y[1] - x[1]; });

          const mp = {};
          arr.forEach(function(pair, idx){
            mp[pair[0]] = idx + 1;
          });
          ranks[b] = mp;
        });
        return ranks;
      }
      const RANKS = buildRanks();

      function setSelectedLabel(a){
        const el = document.getElementById("filter_selected_label");
        if (!el) return;
        el.textContent = "Wybrano: " + labelForArche(a);
      }

      function setChartTitles(a){
        const t1 = document.getElementById("filter_title_pct");
        if (t1) t1.textContent = (getMode() === "values" ? "% oczekujących wartości " : "% oczekujących archetypu ") + labelForArche(a);

        const t2 = document.getElementById("filter_title_rank");
        if (t2) t2.textContent = (getMode() === "values" ? "Miejsce wartości " : "Miejsce archetypu ") + labelForArche(a);
      }

      function fillSelect(){
        const sel = document.getElementById("filter_archetype");
        if (!sel) return;

        const current = sel.value || (ARCHES.length ? ARCHES[0] : "");
        sel.innerHTML = "";

        ARCHES.forEach(function(a){
          const opt = document.createElement("option");
          opt.value = a;
          opt.textContent = labelForArche(a);
          sel.appendChild(opt);
        });

        if (ARCHES.indexOf(current) >= 0) sel.value = current;
        setSelectedLabel(sel.value);
        setChartTitles(sel.value);
      }

      function svgClear(svg){
        while (svg.firstChild) svg.removeChild(svg.firstChild);
      }
      function svgEl(name, attrs){
        const el = document.createElementNS("http://www.w3.org/2000/svg", name);
        Object.keys(attrs || {}).forEach(function(k){
          el.setAttribute(k, String(attrs[k]));
        });
        return el;
      }

        function svgTextMultiline(x, y, text, attrs){
          const t = svgEl("text", Object.assign({x:x, y:y}, (attrs || {})));
          const lines = String(text || "").split("\\n");
          lines.forEach(function(line, idx){
            const sp = svgEl("tspan", {x:x, dy: (idx === 0 ? 0 : 14)});
            sp.appendChild(document.createTextNode(line));
            t.appendChild(sp);
          });
          return t;
        }

        function svgAddIconTopRight(svg, W, archeKey){
          // pozwól rysować "nad" SVG (żeby ikona weszła w obszar nagłówka)
          try { svg.setAttribute("overflow", "visible"); } catch(e) {}
          try { svg.style.overflow = "visible"; } catch(e) {}

          // ujemne y = podniesienie ikony ponad górną krawędź SVG
          const img = svgEl("image",{x: W-55, y: -38, width: 34, height: 34, opacity: 0.95});
          const src = iconSrc(archeKey);

          img.setAttribute("href", src);
          try {
            img.setAttributeNS("http://www.w3.org/1999/xlink", "href", src);
          } catch(e) {}

          // kosmetyka: żeby nie "łapała" klików
          try { img.style.pointerEvents = "none"; } catch(e) {}

          svg.appendChild(img);
        }

      function renderPctChart(a){
        const svg = document.getElementById("chart_pct");
        if (!svg) return;
        svgClear(svg);

        const W=700, H=320, padL=55, padR=18, padT=18, padB=46;
        const plotW = W - padL - padR;
        const plotH = H - padT - padB;

        svgAddIconTopRight(svg, W, a);

        const vals = FILTER_BLOCKS.map(function(b){
          return toNumOrNaN((FILTER_PCT[a] || {})[b]); // <-- kluczowa zmiana
        });

        // axes
        svg.appendChild(svgEl("line",{x1:padL,y1:padT,x2:padL,y2:padT+plotH,stroke:"#999"}));
        svg.appendChild(svgEl("line",{x1:padL,y1:padT+plotH,x2:padL+plotW,y2:padT+plotH,stroke:"#999"}));

        // y ticks 0..100 step 20
        for (let t=0; t<=100; t+=20){
          const y = padT + plotH - (t/100)*plotH;
          svg.appendChild(svgEl("line",{x1:padL-4,y1:y,x2:padL,y2:y,stroke:"#999"}));
          svg.appendChild(svgEl("text",{x:padL-8,y:y+4,"text-anchor":"end",fill:"#666","font-size":"12"}))
            .appendChild(document.createTextNode(String(t)));
          svg.appendChild(svgEl("line",{x1:padL,y1:y,x2:padL+plotW,y2:y,stroke:"#eee"}));
        }

        const n = FILTER_BLOCKS.length;
        const slot = plotW / n;
        const barW = Math.min(70, slot * 0.55);

        for (let i=0; i<n; i++){
          const b = FILTER_BLOCKS[i];
          const v = vals[i];
          const vv = isFinite(v) ? Math.max(0, Math.min(100, v)) : 0;

          const cx = padL + slot*(i+0.5);
          const x = cx - barW/2;
          const h = (vv/100)*plotH;
          const y = padT + plotH - h;

          svg.appendChild(svgEl("rect",{x:x,y:y,width:barW,height:h,fill:"#cfe8cf",stroke:"#6aa56a"}));

          // value label
          const txt = isFinite(v) ? (v.toFixed(1) + "%") : "—";
          svg.appendChild(svgEl("text",{x:cx,y:y-6,"text-anchor":"middle",fill:"#333","font-size":"12","font-weight":"700"}))
            .appendChild(document.createTextNode(txt));

          // x label (mapped) - 2 linie
          svg.appendChild(
            svgTextMultiline(
              cx,
              padT+plotH+26,
              blockLabel(b),
              {"text-anchor":"middle",fill:"#333","font-size":"12","font-weight":"700"}
            )
          );
        }
      }

      function renderRankChart(a){
        const svg = document.getElementById("chart_rank");
        if (!svg) return;
        svgClear(svg);

        const W=700, H=320, padL=55, padR=18, padT=18, padB=46;
        const plotW = W - padL - padR;
        const plotH = H - padT - padB;

        svgAddIconTopRight(svg, W, a);

        // jeśli brak danych w bloku => pokaż "—" (a punkt ustaw na dół osi)
        const ranks = FILTER_BLOCKS.map(function(b){
          const v = toNumOrNaN((FILTER_PCT[a] || {})[b]);
          if (!isFinite(v)) return NaN;
          const r = Number(((RANKS[b] || {})[a]));
          return isFinite(r) ? r : MAX_RANK;
        });

        // axes
        svg.appendChild(svgEl("line",{x1:padL,y1:padT,x2:padL,y2:padT+plotH,stroke:"#999"}));
        svg.appendChild(svgEl("line",{x1:padL,y1:padT+plotH,x2:padL+plotW,y2:padT+plotH,stroke:"#999"}));

        // y ticks: 1..12 (pokazujemy 1,3,6,9,12)
        const ticks = [1,3,6,9,12];
        ticks.forEach(function(t){
          const y = padT + ((t-1)/(MAX_RANK-1))*plotH;
          svg.appendChild(svgEl("line",{x1:padL-4,y1:y,x2:padL,y2:y,stroke:"#999"}));
          svg.appendChild(svgEl("text",{x:padL-8,y:y+4,"text-anchor":"end",fill:"#666","font-size":"12"}))
            .appendChild(document.createTextNode(String(t)));
          svg.appendChild(svgEl("line",{x1:padL,y1:y,x2:padL+plotW,y2:y,stroke:"#eee"}));
        });

        const n = FILTER_BLOCKS.length;
        const slot = plotW / n;

        // polyline points
        const pts = [];
        for (let i=0; i<n; i++){
          const r0 = ranks[i];
          const r = isFinite(r0) ? Math.max(1, Math.min(MAX_RANK, r0)) : MAX_RANK;
          const cx = padL + slot*(i+0.5);
          const y = padT + ((r-1)/(MAX_RANK-1))*plotH;
          pts.push([cx,y]);
        }

        // line
        const d = pts.map(function(p){ return p[0].toFixed(1)+","+p[1].toFixed(1); }).join(" ");
        svg.appendChild(svgEl("polyline",{points:d,fill:"none",stroke:"#3b82f6","stroke-width":"3"}));

        // dots + labels + x labels
        for (let i=0; i<n; i++){
          const b = FILTER_BLOCKS[i];
          const r0 = ranks[i];
          const missing = !isFinite(r0);
          const r = missing ? MAX_RANK : Math.max(1, Math.min(MAX_RANK, r0));
          const cx = pts[i][0], cy = pts[i][1];

          svg.appendChild(svgEl("circle",{cx:cx,cy:cy,r:6,fill:(missing ? "#bbb" : "#3b82f6")}));
          svg.appendChild(svgEl("text",{x:cx,y:cy-10,"text-anchor":"middle",fill:"#111","font-size":"12","font-weight":"700"}))
            .appendChild(document.createTextNode(missing ? "—" : "#"+String(r)));

          // x label (mapped) - 2 linie
          svg.appendChild(
            svgTextMultiline(
              cx,
              padT+plotH+26,
              blockLabel(b),
              {"text-anchor":"middle",fill:"#333","font-size":"12","font-weight":"700"}
            )
          );
        }
      }

      function renderAll(){
        const sel = document.getElementById("filter_archetype");
        if (!sel) return;
        const a = sel.value;
        setSelectedLabel(a);
        setChartTitles(a);
        renderPctChart(a);
        renderRankChart(a);
      }

      // init select + charts
      fillSelect();
      renderAll();

      const sel = document.getElementById("filter_archetype");
      if (sel){
        sel.addEventListener("change", function(){ renderAll(); });
      }

      // when label mode changes: refresh select labels + keep selection + rerender
      document.querySelectorAll("input[name='labelmode']").forEach(function(el){
        el.addEventListener("change", function(){
          const newMode = el.value || "arche";
          _lsSet("labelMode", newMode);
          applyMode(newMode);

          const sel = document.getElementById("filter_archetype");
          const keep = sel ? sel.value : "";

          try { fillSelect(); } catch(e) {}
          if (sel && keep) sel.value = keep;

          try { renderAll(); } catch(e) {}
          try { if (window.__SEG_RENDER_ALL) window.__SEG_RENDER_ALL(); } catch(e) {}
          try { if (window.__CLUSTER_RENDER) window.__CLUSTER_RENDER(); } catch(e) {}
        });
      });

      // ---------- segmentacja ultra premium (1 zakładka, suwak widoczności 1..9; model stały K=9) ----------
(function(){
  const SEG_PACKS = __SEG_PACKS__;
  try { window.SEG_PACKS = SEG_PACKS; } catch(e) {}

  function _fmt(x){
    try { return (Math.round(parseFloat(x) * 10) / 10).toFixed(1); } catch(e) { return String(x); }
  }

  function resolveChosenVisibleK(tabKey, pack){
    const kMin = parseInt(pack.k_min || 1, 10);
    const kMax = parseInt(pack.k_max || 9, 10);
    const defK = parseInt(pack.k_default_ui || 5, 10);

    const key = "segChosenVisibleK_" + tabKey;
    let v = localStorage.getItem(key);
    v = v === null ? defK : parseInt(v, 10);
    if (isNaN(v)) v = defK;
    v = Math.max(kMin, Math.min(kMax, v));
    return v;
  }

  function setChosenVisibleK(tabKey, v){
    const key = "segChosenVisibleK_" + tabKey;
    try { localStorage.setItem(key, String(v)); } catch(e) {}
  }

  function applyVisibleSegmentCount(rootEl, visibleK){
    // karty segmentów
    rootEl.querySelectorAll(".seg-card").forEach(function(card){
      const rank = parseInt(card.getAttribute("data-seg-rank") || "999", 10);
      card.style.display = (rank < visibleK) ? "" : "none";
    });
  }

  function applyVisibleMatrixColumns(rootEl, visibleK){
    // kolumny macierzy (th/td)
    rootEl.querySelectorAll(".seg-mcol").forEach(function(cell){
      const rank = parseInt(cell.getAttribute("data-seg-rank") || "999", 10);
      cell.style.display = (rank < visibleK) ? "" : "none";
    });
  }

  function setDynamicSegMap(tabKey, shownK, pack){
    const mapA = document.getElementById("seg_" + tabKey + "_map_arche");
    const mapV = document.getElementById("seg_" + tabKey + "_map_values");
    const safeK = Math.max(1, parseInt(shownK || 1, 10));
    const p = (pack && typeof pack === "object") ? pack : (SEG_PACKS[tabKey] || {});
    const byKArche = (p && p.map_arche_by_k && typeof p.map_arche_by_k === "object") ? p.map_arche_by_k : {};
    const byKValues = (p && p.map_values_by_k && typeof p.map_values_by_k === "object") ? p.map_values_by_k : {};
    const srcA = byKArche[String(safeK)] || ("SEGMENTY_META_MAPA_STALA_K" + safeK + ".png");
    const srcV = byKValues[String(safeK)] || ("SEGMENTY_META_MAPA_STALA_K" + safeK + "_values.png");

    if (mapA){
      mapA.setAttribute("src", srcA);
    }
    if (mapV){
      mapV.setAttribute("src", srcV);
    }
  }

  function renderTab(tabKey){
    const pack = SEG_PACKS[tabKey];
    if (!pack) return;

    // Model jest stały (K=9); suwak reguluje tylko widoczność (1..9)
    const modelK = parseInt(pack.k_model || pack.best_k_default || 9, 10);
    const baseItem = (pack.by_k || {})[String(modelK)];
    if (!baseItem) return;

    const slider = document.getElementById("seg_" + tabKey + "_slider");
    const kValSpan = document.getElementById("seg_" + tabKey + "_kval");
    const kBestSpan = document.getElementById("seg_" + tabKey + "_kbest");
    const scoreSpan = document.getElementById("seg_" + tabKey + "_score");
    const useSpan = document.getElementById("seg_" + tabKey + "_use");

    const profilesDiv = document.getElementById("seg_" + tabKey + "_profiles");
    const matrixDiv = document.getElementById("seg_" + tabKey + "_matrix");
    const mapArche = document.getElementById("seg_" + tabKey + "_map_arche");
    const mapValues = document.getElementById("seg_" + tabKey + "_map_values");

    const visibleK = resolveChosenVisibleK(tabKey, pack);
    if (slider) slider.value = String(visibleK);

    const shownK = Math.min(visibleK, modelK);

    if (kValSpan) kValSpan.textContent = String(shownK);
    if (kBestSpan) kBestSpan.textContent = String(modelK);

    // score / use (informacyjnie)
    try {
      const sol = (pack.solutions || []).find(s => parseInt(s.k,10) === modelK);
      if (sol && scoreSpan) scoreSpan.textContent = _fmt(sol.score);
      if (sol && useSpan) useSpan.textContent = _fmt(baseItem.avg_usefulness || sol.usefulness || "");
    } catch(e) {}

    // wypełnij treści
    const hA = baseItem.profiles_html_arche || "";
    const hV = baseItem.profiles_html_values || "";
    const mA = baseItem.matrix_html_arche || "";
    const mV = baseItem.matrix_html_values || "";

    const wantValues = (getMode() === "values");

    if (profilesDiv){
      profilesDiv.innerHTML = wantValues ? (hV || hA) : hA;
    }

    if (matrixDiv){
      matrixDiv.innerHTML = wantValues ? (mV || mA) : mA;
    }

    try { applyMode(getMode()); } catch(e) {}

    // ukrywanie/pokazywanie wg suwaka
    if (profilesDiv) applyVisibleSegmentCount(profilesDiv, shownK);
    if (matrixDiv) applyVisibleMatrixColumns(matrixDiv, shownK);
    setDynamicSegMap(tabKey, shownK, pack);

    // obsługa suwaka
    if (slider && !slider.__bound){
      slider.__bound = true;
      slider.addEventListener("input", function(){
        const v = parseInt(slider.value || "5", 10);
        const vv = Math.max(parseInt(pack.k_min || 1,10), Math.min(parseInt(pack.k_max || 9,10), v));
        setChosenVisibleK(tabKey, vv);
        if (kValSpan) kValSpan.textContent = String(Math.min(vv, modelK));
        const shownNow = Math.min(vv, modelK);
        applyVisibleSegmentCount(profilesDiv, shownNow);
        applyVisibleMatrixColumns(matrixDiv, shownNow);
        setDynamicSegMap(tabKey, shownNow, pack);
      });
    }
  }

  window.__SEG_RENDER_ALL = function(){
    Object.keys(SEG_PACKS || {}).forEach(renderTab);
  };
})();
try { if (window.__SEG_RENDER_ALL) window.__SEG_RENDER_ALL(); } catch(e) {}

// ---------- skupienia k-średnich (suwak K = przełączanie całego modelu) ----------
(function(){
  const CLUSTER_PACK = __CLUSTER_PACK__;
  try { window.CLUSTER_PACK = CLUSTER_PACK; } catch(e) {}

  function _toInt(x, fallback){
    const v = parseInt(x, 10);
    return isNaN(v) ? fallback : v;
  }

  function _availableK(byK){
    return Object.keys(byK || {})
      .map(function(k){ return parseInt(k, 10); })
      .filter(function(k){ return isFinite(k) && k >= 2; })
      .sort(function(a,b){ return a-b; });
  }

  function _nearestK(target, avail){
    if (!avail || !avail.length) return null;
    let best = avail[0];
    let bestDist = Math.abs(best - target);
    for (let i=1; i<avail.length; i++){
      const d = Math.abs(avail[i] - target);
      if (d < bestDist){
        best = avail[i];
        bestDist = d;
      }
    }
    return best;
  }

  function _getChosenK(pack, avail){
    const key = "clusterChosenK";
    const defK = _toInt(pack.k_default_ui || pack.k_best || (avail[0] || 3), (avail[0] || 3));
    let v = null;
    try {
      const raw = localStorage.getItem(key);
      v = raw === null ? defK : _toInt(raw, defK);
    } catch(e) {
      v = defK;
    }
    return _nearestK(v, avail);
  }

  function _setChosenK(v){
    try { localStorage.setItem("clusterChosenK", String(v)); } catch(e) {}
  }

  function _projectionHtml(item){
    const png = String((item || {}).projection_png || "").trim();
    if (!png){
      return "<div class='small mono'>Brak pliku mapy dla wybranego K.</div>";
    }
    return "<a href='" + png + "' target='_blank' rel='noopener'><img class='img' src='" + png + "' alt='" + png + "'></a>";
  }

  function renderCluster(){
    if (!CLUSTER_PACK || typeof CLUSTER_PACK !== "object") return;

    const byK = CLUSTER_PACK.by_k || {};
    const avail = _availableK(byK);
    if (!avail.length) return;

    const kMin = Math.max(avail[0], _toInt(CLUSTER_PACK.k_min || avail[0], avail[0]));
    const kMax = Math.max(kMin, _toInt(CLUSTER_PACK.k_max || avail[avail.length - 1], avail[avail.length - 1]));

    const slider = document.getElementById("cluster_k_slider");
    const kValueEl = document.getElementById("cluster_k_value");
    const kBestEl = document.getElementById("cluster_k_best_label");
    const titleEl = document.getElementById("cluster_projection_title");
    const projWrap = document.getElementById("cluster_projection_wrap");
    const profilesWrap = document.getElementById("cluster_profiles_wrap");
    const matrixWrap = document.getElementById("cluster_matrix_wrap");

    let chosenK = _getChosenK(CLUSTER_PACK, avail);
    if (chosenK === null) return;
    chosenK = Math.max(kMin, Math.min(kMax, chosenK));
    chosenK = _nearestK(chosenK, avail);
    if (chosenK === null) return;

    if (slider){
      slider.min = String(kMin);
      slider.max = String(kMax);
      slider.value = String(chosenK);
    }

    const item = byK[String(chosenK)] || byK[String(_nearestK(chosenK, avail))] || {};

    if (kValueEl) kValueEl.textContent = String(chosenK);
    if (kBestEl) kBestEl.textContent = String(_toInt(CLUSTER_PACK.k_best || chosenK, chosenK));
    if (titleEl) titleEl.textContent = "Mapa skupień (projekcja dla K=" + String(chosenK) + ")";

    if (projWrap){
      projWrap.innerHTML = _projectionHtml(item);
    }

    const wantValues = (getMode() === "values");
    const hA = String(item.profiles_html_arche || "");
    const hV = String(item.profiles_html_values || "");
    const mA = String(item.matrix_html_arche || "");
    const mV = String(item.matrix_html_values || "");

    if (profilesWrap){
      profilesWrap.innerHTML = "<div class='label-arche'>" + hA + "</div><div class='label-values'>" + (hV || hA) + "</div>";
    }
    if (matrixWrap){
      matrixWrap.innerHTML =
        "<h3>Matryca skupień</h3>"
        + "<div class='small'>Wiersze pokazują surowy poziom Pm dla <span class='mode-arche'>archetypów</span><span class='mode-values'>wartości</span>, a kolumny odpowiadają skupieniom (Seg_1...Seg_K).</div>"
        + "<div class='label-arche'>" + mA + "</div><div class='label-values'>" + (mV || mA) + "</div>";
    }

    try { applyMode(getMode()); } catch(e) {}

    if (slider && !slider.__bound){
      slider.__bound = true;
      slider.addEventListener("input", function(){
        const raw = _toInt(slider.value || chosenK, chosenK);
        const kk = _nearestK(raw, avail);
        if (kk === null) return;
        _setChosenK(kk);
        renderCluster();
      });
    }
  }

  window.__CLUSTER_RENDER = renderCluster;
})();
try { if (window.__CLUSTER_RENDER) window.__CLUSTER_RENDER(); } catch(e) {}
    });
    </script>
    """) \
        .replace("__FILTER_BLOCKS__", _filter_blocks_json) \
        .replace("__FILTER_PCT__", _filter_pct_json) \
        .replace("__FILTER_ICONS__", _filter_icons_json) \
        .replace("__BRAND_VALUES__", _brand_values_json) \
        .replace("__FEMININE_LABELS__", _feminine_labels_json) \
        .replace("__ARCHETYPE_LABEL_MODE__", _archetype_label_mode_json) \
        .replace("__SEG_PACKS__", _seg_packs_json) \
        .replace("__CLUSTER_PACK__", _cluster_pack_json)

    def _values_mode_text(x: Any) -> Any:
        if not isinstance(x, str):
            return x
        s = str(x)

        phrase_replacements = [
            ("Archetyp / wartość", "Wartość"),
            ("archetyp / wartość", "wartość"),
            ("silniejszy archetyp", "silniejsza wartość"),
            ("Silniejszy archetyp", "Silniejsza wartość"),
            ("dla każdego archetypu", "dla każdej wartości"),
            ("Dla każdego archetypu", "Dla każdej wartości"),
            ("archetypu jako najważniejszego", "wartości jako najważniejszej"),
            ("Archetypu jako najważniejszego", "Wartości jako najważniejszej"),
            ("archetyp wskazany jako najważniejszy", "wartość wskazana jako najważniejsza"),
            ("Archetyp wskazany jako najważniejszy", "Wartość wskazana jako najważniejsza"),
            ("archetyp wskazany", "wartość wskazana"),
            ("Archetyp wskazany", "Wartość wskazana"),
        ]
        for old, new in phrase_replacements:
            s = s.replace(old, new)

        word_replacements = [
            ("Archetypami", "Wartościami"),
            ("Archetypach", "Wartościach"),
            ("Archetypów", "Wartości"),
            ("Archetypy", "Wartości"),
            ("Archetypu", "Wartości"),
            ("Archetypie", "Wartości"),
            ("Archetypem", "Wartością"),
            ("Archetyp", "Wartość"),
            ("archetypami", "wartościami"),
            ("archetypach", "wartościach"),
            ("archetypów", "wartości"),
            ("archetypy", "wartości"),
            ("archetypu", "wartości"),
            ("archetypie", "wartości"),
            ("archetypem", "wartością"),
            ("archetyp", "wartość"),
            ("archetypowa", "wartościowa"),
            ("archetypowe", "wartościowe"),
            ("archetypowy", "wartościowy"),
            ("archetypowych", "wartościowych"),
            ("archetypowego", "wartościowego"),
            ("archetypową", "wartościową"),
            ("archetypowym", "wartościowym"),
            ("Archetypowa", "Wartościowa"),
            ("Archetypowe", "Wartościowe"),
            ("Archetypowy", "Wartościowy"),
            ("Archetypowych", "Wartościowych"),
            ("Archetypowego", "Wartościowego"),
            ("Archetypową", "Wartościową"),
            ("Archetypowym", "Wartościowym"),
        ]
        for old, new in word_replacements:
            s = s.replace(old, new)
        return s

    def _values_mode_df(df: pd.DataFrame) -> pd.DataFrame:
        d = df.copy()

        for c in list(d.columns):
            try:
                col = d[c]
                dtype = col.dtype
                is_text_like = (
                    pd.api.types.is_object_dtype(dtype)
                    or pd.api.types.is_string_dtype(dtype)
                    or isinstance(dtype, pd.CategoricalDtype)
                )
                if is_text_like:
                    d[c] = col.map(_values_mode_text)
            except Exception:
                pass

        try:
            d.columns = pd.Index([
                _values_mode_text(c) if isinstance(c, str) else c
                for c in d.columns
            ], name=_values_mode_text(d.columns.name) if isinstance(d.columns.name, str) else d.columns.name)
        except Exception:
            d.columns = [
                _values_mode_text(c) if isinstance(c, str) else c
                for c in d.columns
            ]

        if isinstance(d.index, pd.MultiIndex):
            new_tuples = []
            for tup in d.index.tolist():
                new_tuples.append(tuple(_values_mode_text(x) for x in tup))
            d.index = pd.MultiIndex.from_tuples(
                new_tuples,
                names=[_values_mode_text(n) if isinstance(n, str) else n for n in d.index.names]
            )
        else:
            d.index = pd.Index(
                [_values_mode_text(x) for x in d.index.tolist()],
                name=_values_mode_text(d.index.name) if isinstance(d.index.name, str) else d.index.name,
            )

        return d

    def df_to_html_dual(df: pd.DataFrame, max_rows: int = 60) -> str:
        d_arche = df_to_html(df, max_rows=max_rows)
        d_val_df = df_display_values(df, brand_values, replace_inside=True)
        d_val_df = _values_mode_df(d_val_df)
        d_val = df_to_html(d_val_df, max_rows=max_rows)
        return f'<div class="label-arche">{d_arche}</div><div class="label-values">{d_val}</div>'
    def df_to_html_sig_dual(df: pd.DataFrame, max_rows: int = 60) -> str:
        import re
        import pandas as pd

        # wersja "values" podmienia nazwy archetypów wewnątrz tekstu (np. "Opiekun (+2.1pp)")
        def _replace_in_cell(x):
            if x is None:
                return ""
            s = str(x)
            for k in sorted(brand_values.keys(), key=lambda z: -len(str(z))):
                v = brand_values.get(k, k)
                s = re.sub(rf"\b{re.escape(str(k))}\b", str(v), s)
            return s

        d_arche = df.copy() if df is not None else pd.DataFrame()
        d_val = df.copy() if df is not None else pd.DataFrame()

        if len(d_val) > 0:
            for c in d_val.columns:
                d_val[c] = d_val[c].apply(_replace_in_cell)

            d_val = _values_mode_df(d_val)
        html_arche = df_to_html(d_arche, max_rows=max_rows) if len(d_arche) else '<div class="small">Brak danych.</div>'
        html_val = df_to_html(d_val, max_rows=max_rows) if len(d_val) else '<div class="small">Brak danych.</div>'

        return f'<div class="label-arche">{html_arche}</div><div class="label-values">{html_val}</div>'

    def img_tag_dual(filename: str, extra_img_class: str = "") -> str:
        fn_val = filename.replace(".png", "_values.png")
        note_base = CHART_NOTES.get(filename, "")
        note_val = CHART_NOTES.get(fn_val, _values_mode_text(note_base))
        note_html_val = f"<div class='small chart-note'>{note_val}</div>" if note_val else ""
        src_val = Path(__file__).resolve().parent / "WYNIKI" / fn_val

        if src_val.exists():
            _img_class = ("img " + str(extra_img_class).strip()).strip()
            html_val = f'<a href="{fn_val}" target="_blank" rel="noopener"><img class="{_img_class}" src="{fn_val}" alt="{fn_val}"></a>{note_html_val}'
        else:
            html_val = f"<div class='small mono'>Brak pliku: {fn_val}</div>{note_html_val}"

        _img_base = img_tag(filename)
        if extra_img_class:
            _img_base = _img_base.replace('class="img"', f'class="img {str(extra_img_class).strip()}"', 1)
        return f'<div class="label-arche">{_img_base}</div><div class="label-values">{html_val}</div>'

    def segment_legend_dual_from_pack(seg_pack: Optional[Dict[str, Any]]) -> str:
        """Legenda segmentów (spójna z zakładką segmentacji) do wstawienia pod mapami wartości."""
        try:
            if not seg_pack:
                return ""
            best_k = str(int(seg_pack.get("k_model", seg_pack.get("best_k_default", 0))))
            by_k = (seg_pack.get("by_k") or {}).get(best_k, {})
            show_n = int(seg_pack.get("k_default_ui", len(by_k.get("segment_names_arche") or [])))

            names_a = [str(x) for x in (by_k.get("segment_names_arche") or [])][:show_n]
            names_v = [str(x) for x in (by_k.get("segment_names_values") or [])][:show_n]
            if not names_a:
                return ""

            rows = []
            for i, name_a in enumerate(names_a):
                seg_label = f"Seg_{i + 1}"
                name_v = name_a
                rows.append(f"<tr><td><b>{seg_label}</b></td><td>{name_a}</td><td>{name_v}</td></tr>")

            table = (
                    "<div class='card' style='margin-top:16px;'>"
                    "<h3 style='margin:0 0 8px 0;'>Legenda segmentów (spójna z zakładką „Segmenty”)</h3>"
                    "<div class='small'>Te same segmenty i ta sama numeracja (Seg_1, Seg_2, ...). "
                    "Nazwy są pobierane z tej samej segmentacji, więc nie ma już rozjazdu nazewnictwa.</div>"
                    "<table style='width:100%; margin-top:8px;'>"
                    "<thead><tr><th>Segment</th><th>Nazwa (archetypy)</th><th>Nazwa (wartości)</th></tr></thead>"
                    "<tbody>" + "".join(rows) + "</tbody></table></div>"
            )
            return table
        except Exception:
            return ""

    def _slug_ascii(s: str) -> str:
        import re, unicodedata

        s = str(s)

        # PL znaki, których NFKD nie rozkłada (kluczowo: ł/Ł)
        tr = str.maketrans({
            "ł": "l", "Ł": "L",
            "ą": "a", "Ą": "A",
            "ć": "c", "Ć": "C",
            "ę": "e", "Ę": "E",
            "ń": "n", "Ń": "N",
            "ó": "o", "Ó": "O",
            "ś": "s", "Ś": "S",
            "ż": "z", "Ż": "Z",
            "ź": "z", "Ź": "Z",
        })
        s = s.translate(tr)

        s = unicodedata.normalize("NFKD", s)
        s = "".join(ch for ch in s if not unicodedata.combining(ch))
        s = s.lower()
        s = re.sub(r"[^a-z0-9]+", "_", s).strip("_")
        return s

    def _icon_cell(arche_key: str, label: str) -> str:
        # ikony trzymamy w WYNIKI/icons/*.png
        fn = _slug_ascii(arche_key) + ".png"
        src = f"icons/{fn}"
        # onerror chowa obrazek, gdyby brakło pliku
        return (
            f'<span class="aicon">'
            f'<img class="aico" src="{_html_escape(src)}" alt="" onerror="this.style.display=\'none\'">'
            f'{_html_escape(label)}'
            f"</span>"
        )

    def top5_table_dual(df: pd.DataFrame, brand_values: Dict[str, str], max_rows: int = 10) -> str:
        d = df.copy()
        if len(d) > max_rows:
            d = d.head(max_rows)

        # archetypy
        d_arche = d.copy()
        if "archetyp" in d_arche.columns:
            d_arche["archetyp"] = d_arche["archetyp"].astype(str).apply(lambda a: _icon_cell(a, a))
        html_arche = d_arche.to_html(index=False, border=0, classes="tbl", escape=False)

        # wartości
        d_val = d.copy()
        if "archetyp" in d_val.columns:
            d_val["archetyp"] = d_val["archetyp"].astype(str).apply(lambda a: _icon_cell(a, brand_values.get(a, a)))
        d_val = _values_mode_df(d_val)
        html_val = d_val.to_html(index=False, border=0, classes="tbl", escape=False)

        return f'<div class="label-arche">{html_arche}</div><div class="label-values">{html_val}</div>'

    def top5_legend_html() -> str:
        return (
            '<div class="dot-legend">'
            '<span><span class="dot d1"></span>#1</span>'
            '<span><span class="dot d2"></span>#2</span>'
            '<span><span class="dot d3"></span>#3</span>'
            '<span><span class="dot d4"></span>#4</span>'
            '<span><span class="dot d5"></span>#5</span>'
            '</div>'
            '<div class="small" style="margin-top:8px;">'
            'W macierzy tabelarycznej miejsca #1–#3 są dodatkowo podświetlone.'
            '</div>'
        )

    def top5_dot_matrix_dual(
            df_top5_A: pd.DataFrame,
            df_B1_pct: pd.DataFrame,
            df_B2_pct: pd.DataFrame,
            df_D13_pct: pd.DataFrame,
            brand_values: Dict[str, str]
    ) -> str:
        import pandas as pd

        def _map_block(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
            mp: Dict[str, Dict[str, Any]] = {}
            if df is None or len(df) == 0:
                return mp
            d = df.reset_index(drop=True).copy()
            if "archetyp" not in d.columns:
                return mp
            for i in range(len(d)):
                a = str(d.loc[i, "archetyp"])
                mp[a] = {"rank": i + 1}
            return mp

        blocks = [
            ("A (% oczekujących)", _map_block(df_top5_A)),
            ("B1 (3 priorytety)", _map_block(df_B1_pct)),
            ("B2 (najważniejszy)", _map_block(df_B2_pct)),
            ("D13 (doświadczenie)", _map_block(df_D13_pct)),
        ]

        try:
            all_arch = [str(a) for a in ARCHETYPES]
        except Exception:
            seen = set()
            all_arch = []
            for _bn, mp in blocks:
                for a in mp.keys():
                    if a not in seen:
                        seen.add(a)
                        all_arch.append(a)

        def _occ(a: str) -> int:
            return sum(1 for _bn, mp in blocks if a in mp)

        def _score(a: str):
            cnt = _occ(a)
            best_rank = 999
            for _bn, mp in blocks:
                if a in mp:
                    best_rank = min(best_rank, int(mp[a]["rank"]))
            return (-cnt, best_rank, a)

        all_arch_sorted = sorted(all_arch, key=_score)

        rows = []
        for a in all_arch_sorted:
            r: Dict[str, Any] = {"archetyp": a, "Suma wystąpień w TOP5": _occ(a)}
            for bn, mp in blocks:
                if a in mp:
                    rr = int(mp[a]["rank"])
                    r[bn] = f'<span class="dot d{rr}" title="#{rr}"></span>'
                else:
                    r[bn] = ""
            rows.append(r)

        col_order = ["archetyp", "Suma wystąpień w TOP5"] + [bn for bn, _mp in blocks]
        mat = pd.DataFrame(rows)[col_order]

        mat_arche = mat.copy()
        mat_arche["archetyp"] = mat_arche["archetyp"].astype(str).apply(
            lambda a: _icon_cell(a, _display_archetype_label(a))
        )
        html_arche = mat_arche.to_html(index=False, border=0, classes="tbl dotmat", escape=False)

        mat_val = mat.copy()
        mat_val["archetyp"] = mat_val["archetyp"].astype(str).apply(lambda a: _icon_cell(a, brand_values.get(a, a)))
        mat_val = _values_mode_df(mat_val)
        html_val = mat_val.to_html(index=False, border=0, classes="tbl dotmat", escape=False)

        return (
                '<div class="label-arche">' + top5_legend_html() + html_arche + '</div>'
                                                                                '<div class="label-values">' + top5_legend_html() + html_val + '</div>'
        )

    def top5_matrix_dual(
            df_top5_A: pd.DataFrame,
            df_B1_pct: pd.DataFrame,
            df_B2_pct: pd.DataFrame,
            df_D13_pct: pd.DataFrame,
            brand_values: Dict[str, str]
    ) -> str:
        import numpy as np
        import pandas as pd

        def _parse_pct(x: Any) -> float:
            if x is None:
                return float("nan")
            t = str(x).strip().replace("%", "").replace(",", ".")
            try:
                return float(t)
            except Exception:
                return float("nan")

        def _map_block(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
            mp: Dict[str, Dict[str, Any]] = {}
            if df is None or len(df) == 0:
                return mp
            d = df.reset_index(drop=True).copy()
            if "archetyp" not in d.columns:
                return mp
            for i in range(len(d)):
                a = str(d.loc[i, "archetyp"])
                pct = d.loc[i, "%"] if "%" in d.columns else ""
                pct_s = str(pct).strip()
                mp[a] = {"rank": i + 1, "pct": pct_s, "pct_f": _parse_pct(pct_s)}
            return mp

        blocks = [
            ("A (% oczekujących)", _map_block(df_top5_A)),
            ("B1 (3 priorytety)", _map_block(df_B1_pct)),
            ("B2 (najważniejszy)", _map_block(df_B2_pct)),
            ("D13 (doświadczenie)", _map_block(df_D13_pct)),
        ]

        # PREMIUM: pokaż wszystkie archetypy (również te, które nie weszły do TOP5 nigdzie)
        try:
            all_arch = [str(a) for a in ARCHETYPES]
        except Exception:
            # awaryjnie: bierz to, co występuje gdziekolwiek
            seen = set()
            all_arch = []
            for _bn, mp in blocks:
                for a in mp.keys():
                    if a not in seen:
                        seen.add(a)
                        all_arch.append(a)

        def _occ(a: str) -> int:
            return sum(1 for _bn, mp in blocks if a in mp)

        # sortowanie: (1) suma wystąpień (malejąco), (2) najlepsza pozycja (rosnąco),
        # (3) najwyższy % (malejąco), (4) nazwa
        def _score(a: str):
            cnt = 0
            best_rank = 999
            best_pct = -1e9
            for _bn, mp in blocks:
                if a in mp:
                    cnt += 1
                    best_rank = min(best_rank, int(mp[a]["rank"]))
                    if np.isfinite(mp[a]["pct_f"]):
                        best_pct = max(best_pct, float(mp[a]["pct_f"]))
            return (-cnt, best_rank, -best_pct, a)

        all_arch_sorted = sorted(all_arch, key=_score)

        rows = []
        for a in all_arch_sorted:
            r: Dict[str, Any] = {"archetyp": a, "Suma wystąpień w TOP5": _occ(a)}
            for bn, mp in blocks:
                if a in mp:
                    rr = int(mp[a]["rank"])
                    pct_s = mp[a]["pct"]

                    pct_html = _html_escape(pct_s)
                    if rr == 1:
                        pct_html = f"<b>{pct_html}</b>"

                    r[bn] = f'{pct_html} <span class="rank">#{rr}</span>'
                else:
                    r[bn] = ""
            rows.append(r)

        col_order = ["archetyp", "Suma wystąpień w TOP5"] + [bn for bn, _mp in blocks]
        mat = pd.DataFrame(rows)
        mat = mat[col_order]

        # wersja archetypy
        mat_arche = mat.copy()
        mat_arche["archetyp"] = mat_arche["archetyp"].astype(str).apply(
            lambda a: _icon_cell(a, _display_archetype_label(a))
        )

        # podświetlenie #1/#2/#3 realizujemy klasami na <td> (CSS), ale tu dodajemy znacznik ranku:
        def _wrap_rank_cell(v: Any) -> Any:
            s = str(v)
            if "#1" in s:
                return f'<span class="rk rk1">{s}</span>'
            if "#2" in s:
                return f'<span class="rk rk2">{s}</span>'
            if "#3" in s:
                return f'<span class="rk rk3">{s}</span>'
            if "#4" in s:
                return f'<span class="rk rk4">{s}</span>'
            if "#5" in s:
                return f'<span class="rk rk5">{s}</span>'
            return s

        for bn, _mp in blocks:
            mat_arche[bn] = mat_arche[bn].apply(_wrap_rank_cell)

        html_arche = mat_arche.to_html(index=False, border=0, classes="tbl top5mat", escape=False)

        # wersja wartości
        mat_val = mat.copy()
        mat_val["archetyp"] = mat_val["archetyp"].astype(str).apply(lambda a: _icon_cell(a, brand_values.get(a, a)))
        for bn, _mp in blocks:
            mat_val[bn] = mat_val[bn].apply(_wrap_rank_cell)

        mat_val = _values_mode_df(mat_val)
        html_val = mat_val.to_html(index=False, border=0, classes="tbl top5mat", escape=False)

        return f'<div class="label-arche">{html_arche}</div><div class="label-values">{html_val}</div>'

    # --- segmentacja ultra premium: suwak K ---
    ultra_pack = (seg_packs_render or {}).get("ultra_premium", {}) or {}

    slider_k_min = int(ultra_pack.get("k_min", settings.segments_k_min))
    slider_k_max = int(ultra_pack.get("k_max", min(settings.segments_k_max, settings.segments_max_segments)))
    slider_k_def = int(ultra_pack.get("k_default_ui", ultra_pack.get("best_k_default", slider_k_min)))

    slider_k_def = max(slider_k_min, min(slider_k_max, slider_k_def))
    ultra_k_model = int(ultra_pack.get("k_model", ultra_pack.get("best_k_default", slider_k_def)))
    ultra_base_item = (ultra_pack.get("by_k") or {}).get(str(ultra_k_model), {}) or {}
    ultra_profiles_payload = [dict(x) for x in (ultra_base_item.get("profiles_payload", []) or [])]
    demo_city_label = (
        f"{settings.city_label} / (po wagowaniu)"
        if has_poststrat
        else f"{settings.city_label} / próba"
    )

    demografia_seg_html = _render_demografia_seg_panel(
        ultra_profiles_payload,
        city_label=demo_city_label
    )
    b2_declared_demo_html = _render_b2_declared_demo_panel(
        b2_declared_demo_payload or {},
        city_label=demo_city_label
    )
    top5_simulation_html = _render_top5_simulation_panel(
        top5_simulation_payload or {},
        city_label=demo_city_label
    )

    cluster_quality_html = str(
        cluster_pack.get(
            "quality_html",
            "<div class='card' style='margin-top:12px;'><div class='small'>Brak danych dla analizy skupień.</div></div>",
        )
    )
    cluster_profiles_html_arche = str(
        cluster_pack.get("profiles_html_arche", "<div class='small'>Brak profili skupień.</div>")
    )
    cluster_profiles_html_values = str(
        cluster_pack.get("profiles_html_values", "<div class='small'>Brak profili skupień.</div>")
    )
    cluster_matrix_html_arche = str(
        cluster_pack.get("matrix_html_arche", "<div class='small'>Brak matrycy skupień.</div>")
    )
    cluster_matrix_html_values = str(
        cluster_pack.get("matrix_html_values", "<div class='small'>Brak matrycy skupień.</div>")
    )
    cluster_silhouette_png = str(cluster_pack.get("silhouette_png", "SKUPIENIA_DOBOR_K_SILHOUETTE.png"))
    cluster_elbow_png = str(cluster_pack.get("elbow_png", "SKUPIENIA_DOBOR_K_ELBOW.png"))
    cluster_projection_png = str(cluster_pack.get("projection_png", "SKUPIENIA_MAPA_PCA.png"))
    cluster_panel_png = str(cluster_pack.get("panel_png", ""))
    try:
        cluster_k_best = int(cluster_pack.get("k_best", 0))
    except Exception:
        cluster_k_best = 0
    try:
        cluster_k_min = int(cluster_pack.get("k_min", 0))
    except Exception:
        cluster_k_min = 0
    try:
        cluster_k_max = int(cluster_pack.get("k_max", 0))
    except Exception:
        cluster_k_max = 0
    cluster_k_best_txt = str(cluster_k_best) if cluster_k_best > 0 else "—"
    cluster_k_range_txt = (
        f"{cluster_k_min}–{cluster_k_max}" if cluster_k_min >= 2 and cluster_k_max >= cluster_k_min else "—"
    )
    cluster_by_k = cluster_pack.get("by_k", {}) if isinstance(cluster_pack.get("by_k", {}), dict) else {}
    try:
        cluster_k_default_ui = int(cluster_pack.get("k_default_ui", cluster_k_best or cluster_k_min))
    except Exception:
        cluster_k_default_ui = cluster_k_best if cluster_k_best > 0 else cluster_k_min
    if cluster_k_min > 0 and cluster_k_max >= cluster_k_min:
        cluster_k_default_ui = max(cluster_k_min, min(cluster_k_max, int(cluster_k_default_ui)))

    cluster_panel_html = ""
    if cluster_panel_png.strip():
        cluster_panel_html = (
            "<div class='card' style='margin-top:16px;'>"
            "<h3>Porównanie map skupień dla różnych K</h3>"
            "<div class='cluster-figure-wrap'>"
            f"{img_tag(cluster_panel_png)}"
            "</div>"
            "</div>"
        )

    isoa_methodology_text_arche = (
        "ISOA jest zakotwiczony w A (% oczekujących z versusów). "
        "B1 i B2 działają względem poziomów neutralnych (25% i 8.3333333333%), "
        "C13/D13 daje umiarkowaną korektę doświadczeniową. "
        "Wynik końcowy to A + korekta wariantu B, przycięty do zakresu 0-100 (bez min-max)."
    )
    isoa_methodology_text_values = (
        "ISOW jest zakotwiczony w A (% oczekujących z versusów). "
        "B1 i B2 działają względem poziomów neutralnych (25% i 8.3333333333%), "
        "C13/D13 daje umiarkowaną korektę doświadczeniową. "
        "Wynik końcowy to A + korekta wariantu B, przycięty do zakresu 0-100 (bez min-max)."
    )

    def _fmt_cell(v: Any, digits: int) -> str:
        try:
            fv = float(v)
        except Exception:
            return "—"
        if not np.isfinite(fv):
            return "—"
        return f"{fv:.{digits}f}"

    def _isoa_main_table_dual(df_main: pd.DataFrame) -> str:
        if df_main is None or len(df_main) == 0:
            return '<div class="small">Brak danych dla tabeli ISOA/ISOW.</div>'

        base_cols = [
            "Pozycja",
            "Archetyp",
            "ISOA 0-100",
            "A: % oczekujących",
            "B1: TOP3 (%)",
            "B2: TOP1 (%)",
            "C13/D13: negatywne doświadczenie (%)",
            "C13/D13: bilans najważniejszego doświadczenia",
            "Korekta wariantu B",
            "Różnica |Δ| vs profil polityka",
        ]
        d_a = df_main.copy()
        d_a = d_a[[c for c in base_cols if c in d_a.columns]].copy()
        if "Pozycja" in d_a.columns:
            d_a["Pozycja"] = pd.to_numeric(d_a["Pozycja"], errors="coerce").fillna(0).astype(int)
        for col, digits in [
            ("ISOA 0-100", 1),
            ("A: % oczekujących", 1),
            ("B1: TOP3 (%)", 1),
            ("B2: TOP1 (%)", 1),
            ("C13/D13: negatywne doświadczenie (%)", 1),
            ("C13/D13: bilans najważniejszego doświadczenia", 1),
            ("Korekta wariantu B", 2),
            ("Różnica |Δ| vs profil polityka", 1),
        ]:
            if col in d_a.columns:
                d_a[col] = d_a[col].apply(lambda x, d=digits: _fmt_cell(x, d))
        if "Archetyp" in d_a.columns:
            d_a["Archetyp"] = d_a["Archetyp"].astype(str).apply(lambda a: _icon_cell(a, a))
        h_a = d_a.to_html(index=False, border=0, classes="tbl ioa-main-table", escape=False)

        d_v = df_main.copy()
        d_v = d_v[[c for c in base_cols if c in d_v.columns]].copy()
        if "Pozycja" in d_v.columns:
            d_v["Pozycja"] = pd.to_numeric(d_v["Pozycja"], errors="coerce").fillna(0).astype(int)
        for col, digits in [
            ("ISOA 0-100", 1),
            ("A: % oczekujących", 1),
            ("B1: TOP3 (%)", 1),
            ("B2: TOP1 (%)", 1),
            ("C13/D13: negatywne doświadczenie (%)", 1),
            ("C13/D13: bilans najważniejszego doświadczenia", 1),
            ("Korekta wariantu B", 2),
            ("Różnica |Δ| vs profil polityka", 1),
        ]:
            if col in d_v.columns:
                d_v[col] = d_v[col].apply(lambda x, d=digits: _fmt_cell(x, d))
        if "Archetyp" in d_v.columns:
            d_v["Archetyp"] = d_v["Archetyp"].astype(str).apply(
                lambda a: _icon_cell(a, str(brand_values.get(a, a)))
            )
            d_v = d_v.rename(columns={"Archetyp": "Wartość"})
        d_v = d_v.rename(columns={"ISOA 0-100": "ISOW 0-100"})
        d_v = _values_mode_df(d_v)
        h_v = d_v.to_html(index=False, border=0, classes="tbl ioa-main-table", escape=False)
        return f'<div class="label-arche">{h_a}</div><div class="label-values">{h_v}</div>'

    def _ppp_main_table_dual(df_main: pd.DataFrame) -> str:
        if df_main is None or len(df_main) == 0:
            return '<div class="small">Brak danych dla tabeli PPP.</div>'
        base_cols = [
            "Pozycja",
            "Archetyp",
            "% oczekujących",
            "% neutralnych",
            "% nieoczekujących",
            "% silnie oczekujących",
            "PPP 0-100",
            "PPP raw (-3 do +3)",
            "Liczba respondentów",
        ]
        d_a = df_main.copy()
        d_a = d_a[[c for c in base_cols if c in d_a.columns]].copy()
        if "Pozycja" in d_a.columns:
            d_a["Pozycja"] = pd.to_numeric(d_a["Pozycja"], errors="coerce").fillna(0).astype(int)
        if "Liczba respondentów" in d_a.columns:
            d_a["Liczba respondentów"] = pd.to_numeric(d_a["Liczba respondentów"], errors="coerce").fillna(0).astype(int)
        for col, digits in [
            ("% oczekujących", 1),
            ("% neutralnych", 1),
            ("% nieoczekujących", 1),
            ("% silnie oczekujących", 1),
            ("PPP 0-100", 1),
            ("PPP raw (-3 do +3)", 2),
        ]:
            if col in d_a.columns:
                d_a[col] = d_a[col].apply(lambda x, d=digits: _fmt_cell(x, d))
        if "Archetyp" in d_a.columns:
            d_a["Archetyp"] = d_a["Archetyp"].astype(str).apply(lambda a: _icon_cell(a, a))
        h_a = d_a.to_html(index=False, border=0, classes="tbl ppp-main-table", escape=False)

        d_v = df_main.copy()
        d_v = d_v[[c for c in base_cols if c in d_v.columns]].copy()
        if "Pozycja" in d_v.columns:
            d_v["Pozycja"] = pd.to_numeric(d_v["Pozycja"], errors="coerce").fillna(0).astype(int)
        if "Liczba respondentów" in d_v.columns:
            d_v["Liczba respondentów"] = pd.to_numeric(d_v["Liczba respondentów"], errors="coerce").fillna(0).astype(int)
        for col, digits in [
            ("% oczekujących", 1),
            ("% neutralnych", 1),
            ("% nieoczekujących", 1),
            ("% silnie oczekujących", 1),
            ("PPP 0-100", 1),
            ("PPP raw (-3 do +3)", 2),
        ]:
            if col in d_v.columns:
                d_v[col] = d_v[col].apply(lambda x, d=digits: _fmt_cell(x, d))
        if "Archetyp" in d_v.columns:
            d_v["Archetyp"] = d_v["Archetyp"].astype(str).apply(
                lambda a: _icon_cell(a, str(brand_values.get(a, a)))
            )
            d_v = d_v.rename(columns={"Archetyp": "Wartość"})
        d_v = _values_mode_df(d_v)
        h_v = d_v.to_html(index=False, border=0, classes="tbl ppp-main-table", escape=False)
        return f'<div class="label-arche">{h_a}</div><div class="label-values">{h_v}</div>'

    def _top_bottom_dual(df_main: pd.DataFrame) -> str:
        if df_main is None or len(df_main) == 0 or "Archetyp" not in df_main.columns:
            return "<div class='small'>Brak danych rankingowych.</div>"
        d = df_main.copy()
        d["ISOA 0-100"] = pd.to_numeric(d.get("ISOA 0-100"), errors="coerce")
        d = d.dropna(subset=["ISOA 0-100"]).copy()
        if d.empty:
            return "<div class='small'>Brak danych rankingowych.</div>"
        d = d.sort_values(["ISOA 0-100"], ascending=False, kind="mergesort")
        top3 = d.head(3)["Archetyp"].astype(str).tolist()
        bottom3 = d.tail(3)["Archetyp"].astype(str).tolist()

        def _list_html(items: List[str], values_mode: bool, tone: str) -> str:
            if not items:
                return "<div class='small'>Brak danych.</div>"
            tone_class = "tone-up" if tone == "up" else "tone-down"
            out = [f"<ol class='ioa-list {tone_class}'>"]
            for a in items:
                lbl = str(brand_values.get(a, a)) if values_mode else str(a)
                out.append(f"<li>{_icon_cell(a, lbl)}</li>")
            out.append("</ol>")
            return "".join(out)

        return (
            '<div class="label-arche"><div class="ioa-summary-grid">'
            '<div class="ioa-summary-item"><h4><span class="sum-up-arrow">⬆</span> Top 3 archetypy (ISOA)</h4>'
            + _list_html(top3, values_mode=False, tone="up")
            + "</div>"
            '<div class="ioa-summary-item"><h4><span class="sum-down-arrow">⬇</span> Bottom 3 archetypy (ISOA)</h4>'
            + _list_html(bottom3, values_mode=False, tone="down")
            + "</div></div></div>"
            '<div class="label-values"><div class="ioa-summary-grid">'
            '<div class="ioa-summary-item"><h4><span class="sum-up-arrow">⬆</span> Top 3 wartości (ISOW)</h4>'
            + _list_html(top3, values_mode=True, tone="up")
            + "</div>"
            '<div class="ioa-summary-item"><h4><span class="sum-down-arrow">⬇</span> Bottom 3 wartości (ISOW)</h4>'
            + _list_html(bottom3, values_mode=True, tone="down")
            + "</div></div></div>"
        )

    def _ppp_summary_block_dual(payload: Dict[str, List[str]]) -> str:
        data = payload or {}
        top_expected = [str(x) for x in (data.get("top_expected") or []) if str(x).strip()]
        bottom_expected = [str(x) for x in (data.get("bottom_expected") or []) if str(x).strip()]
        top_ppp = [str(x) for x in (data.get("top_ioa") or []) if str(x).strip()]
        bottom_ppp = [str(x) for x in (data.get("bottom_ioa") or []) if str(x).strip()]

        def _list_html(items: List[str], values_mode: bool, tone: str) -> str:
            if not items:
                return "<div class='small'>Brak danych.</div>"
            tone_class = "tone-up" if tone == "up" else "tone-down"
            out = [f"<ol class='ioa-list {tone_class}'>"]
            for a in items:
                lbl = str(brand_values.get(a, a)) if values_mode else str(a)
                out.append(f"<li>{_icon_cell(a, lbl)}</li>")
            out.append("</ol>")
            return "".join(out)

        return (
            '<div class="label-arche"><div class="ioa-summary-grid">'
            '<div class="ioa-summary-item"><h4><span class="sum-up-arrow">⬆</span> Top 3 oczekiwane archetypy</h4>'
            + _list_html(top_expected, values_mode=False, tone="up")
            + "</div>"
            '<div class="ioa-summary-item"><h4><span class="sum-down-arrow">⬇</span> Bottom 3 oczekiwane archetypy</h4>'
            + _list_html(bottom_expected, values_mode=False, tone="down")
            + "</div>"
            '<div class="ioa-summary-item"><h4><span class="sum-up-arrow">⬆</span> Top 3 archetypy (PPP)</h4>'
            + _list_html(top_ppp, values_mode=False, tone="up")
            + "</div>"
            '<div class="ioa-summary-item"><h4><span class="sum-down-arrow">⬇</span> Bottom 3 archetypy (PPP)</h4>'
            + _list_html(bottom_ppp, values_mode=False, tone="down")
            + "</div></div></div>"
            '<div class="label-values"><div class="ioa-summary-grid">'
            '<div class="ioa-summary-item"><h4><span class="sum-up-arrow">⬆</span> Top 3 oczekiwane wartości</h4>'
            + _list_html(top_expected, values_mode=True, tone="up")
            + "</div>"
            '<div class="ioa-summary-item"><h4><span class="sum-down-arrow">⬇</span> Bottom 3 oczekiwane wartości</h4>'
            + _list_html(bottom_expected, values_mode=True, tone="down")
            + "</div>"
            '<div class="ioa-summary-item"><h4><span class="sum-up-arrow">⬆</span> Top 3 wartości (PPP)</h4>'
            + _list_html(top_ppp, values_mode=True, tone="up")
            + "</div>"
            '<div class="ioa-summary-item"><h4><span class="sum-down-arrow">⬇</span> Bottom 3 wartości (PPP)</h4>'
            + _list_html(bottom_ppp, values_mode=True, tone="down")
            + "</div></div></div>"
        )

    ppp_methodology_text_arche = (
        "PPP opisuje model preferencji przywództwa na podstawie pytania A: "
        "bilansu odpowiedzi w parach oraz odsetka mieszkańców oczekujących archetypu."
    )
    ppp_methodology_text_values = (
        "PPP opisuje model preferencji przywództwa na podstawie pytania A: "
        "bilansu odpowiedzi w parach oraz odsetka mieszkańców oczekujących wartości."
    )
    ppp_panel_html = render_archetype_expectation_section(
        methodology_text_arche=ppp_methodology_text_arche,
        methodology_text_values=ppp_methodology_text_values,
        data_basis_message=get_weighting_status_message(expectation_weighting_meta),
        data_basis_reason=str(expectation_weighting_meta.get("data_basis_reason", "")),
        summary_block_html=_ppp_summary_block_dual(expectation_summary_payload),
        main_table_html=_ppp_main_table_dual(df_A_expectation_main),
        pair_detail_table_html=df_to_html_dual(df_A_expectation_pair_detail, max_rows=60),
        balance_chart_html=img_tag_dual("A_expectation_balance_distribution.png"),
        expected_chart_html=img_tag_dual("A_expectation_expected_pct.png"),
        ioa_chart_html=img_tag_dual("A_expectation_ioa_100.png"),
    )

    isoa_isow_panel_html = render_isoa_isow_report_tab(
        data_basis_message=get_weighting_status_message(expectation_weighting_meta),
        data_basis_reason=str(expectation_weighting_meta.get("data_basis_reason", "")),
        methodology_text_arche=isoa_methodology_text_arche,
        methodology_text_values=isoa_methodology_text_values,
        table_html=_isoa_main_table_dual(df_social_expectation_index),
        chart_html=img_tag_dual("ISOA_ISOW_wheel.png"),
        top_bottom_html=_top_bottom_dual(df_social_expectation_index),
    )

    _months_pl = {
        1: "stycznia", 2: "lutego", 3: "marca", 4: "kwietnia", 5: "maja", 6: "czerwca",
        7: "lipca", 8: "sierpnia", 9: "września", 10: "października", 11: "listopada", 12: "grudnia",
    }
    try:
        _dt_report = datetime.now(ZoneInfo("Europe/Warsaw"))
    except Exception:
        _dt_report = datetime.now()
    report_generated_at = (
        f"{_dt_report.day} {_months_pl.get(int(_dt_report.month), str(_dt_report.month))} "
        f"{_dt_report.year}, godzina {_dt_report.strftime('%H:%M')}"
    )

    html_doc = f"""<html><head><meta charset="utf-8">{css}</head><body>
<h1><span class="mode-arche">Raport: Archetypy</span><span class="mode-values">Raport: Wartości</span> – {_html_escape(settings.city_label)} (N={n_respondents_total})</h1>
<div class="small">
Plik autorski Badania.pro (narzędzie analityczne). Data wygenerowania raportu: {_html_escape(report_generated_at)}.
</div>

<div class="card" style="margin-bottom:14px;">
  <b>Podpisy w raporcie:</b>
  <label style="margin-left:10px;"><input type="radio" name="labelmode" id="mode_arche" value="arche"> Archetypy</label>
  <label style="margin-left:10px;"><input type="radio" name="labelmode" id="mode_values" value="values"> Wartości</label>
  <span class="small" style="margin-left:10px;">(raport zapamięta wybór w tej przeglądarce)</span>
</div>

<div class="tabs">
  <input type="radio" name="tabs" id="tab0" checked>
  <input type="radio" name="tabs" id="tabW">
  <input type="radio" name="tabs" id="tabA">
  <input type="radio" name="tabs" id="tabI">
  <input type="radio" name="tabs" id="tabB">
  <input type="radio" name="tabs" id="tabD">
  <input type="radio" name="tabs" id="tabK">
  <input type="radio" name="tabs" id="tabM">
  <input type="radio" name="tabs" id="tabR">
  <input type="radio" name="tabs" id="tabT">
  <input type="radio" name="tabs" id="tabS">
  <input type="radio" name="tabs" id="tabC">
  <input type="radio" name="tabs" id="tabG">
  <input type="radio" name="tabs" id="tabH">
  <input type="radio" name="tabs" id="tabY">

  <div class="labels">
    <label for="tab0">Podsumowanie</label>
    <label for="tabW"><span class="mode-arche">ISOA</span><span class="mode-values">ISOW</span></label>
    <label for="tabA">Przywództwo</label>
    <label for="tabI">PPP</label>
    <label for="tabB">Oczekiwania</label>
    <label for="tabD">Doświadczenia</label>
    <label for="tabS">Segmenty</label>
    <label for="tabC">Skupienia</label>
    <label for="tabG">Demografia_Seg</label>
    <label for="tabH">Demografia</label>
    <label for="tabY">Symulacja</label>
    <label for="tabM">Mapy</label>
    <label for="tabK">Korelacje</label>
    <label for="tabR">Filtry</label>
    <label for="tabT">TOP5</label>
  </div>

  <div class="panel p0">
    <h2>P / E / G</h2>
    <div class="grid">
      <div class="card">
        <h3>Preferencje (P)</h3>
        {img_tag_dual("P_mean.png")}
      </div>
      <div class="card">
        <h3>Doświadczenia (E)</h3>
        {img_tag_dual("E_mean.png")}
      </div>
    </div>
    <div class="card chart-half" style="margin-top:16px;">
      <h3>Priorytety (G)</h3>
      {img_tag_dual("G_mean.png")}
    </div>
    <div class="card" style="margin-top:16px;">
        <h3>Tabela zbiorcza (P/E/G) – średnie (95% CI)</h3>
        {df_to_html_dual(df_group, max_rows=20)}
    </div>

    <div class="card chart-half" style="margin-top:16px;">
      <h3><span class="mode-arche">Łączne wskazania archetypów</span><span class="mode-values">Łączne wskazania wartości</span></h3>
      {img_tag_dual("mentions_total.png")}
      <div class="small" style="margin-top:12px;">
        Liczba wskazań w poszczególnych pytaniach.
      </div>
    </div>
    <div class="card" style="margin-top:16px;">
      <h3><span class="mode-arche">Łączne wskazania archetypów — tabela szczegółowa</span><span class="mode-values">Łączne wskazania wartości — tabela szczegółowa</span></h3>
      {df_to_html_dual(df_mentions_q, max_rows=60)}
    </div>
  </div>

  {isoa_isow_panel_html}

  <div class="panel pA">
    <h2>Model preferowanego podejścia do spraw miasta</h2>
    <div class="small">
      Poniżej znajdują się pary sformułowań opisujące dwa różne podejścia do spraw miasta.
      Proszę przesunąć suwak bliżej tego podejścia, które jest Panu/Pani bliższe?
      Ustawienie suwaka na środku oznacza, że oba podejścia są tak samo ważne.
    </div>
    <div class="card">
      <h3>Wygrane w parach</h3>
      {df_to_html_dual(df_A_pairs, max_rows=60)}
    </div>
    <div class="card" style="margin-top:16px;">
        <h3>
          Model podejścia do spraw miasta — 
          <span class="mode-arche">profil liniowy archetypów</span>
          <span class="mode-values">profil liniowy wartości</span>
          (18 par)
        </h3>
      {img_tag_dual("A_versusy_liniowy.png", "img-profile-sm")}
    </div>
    <div class="chart-pair" style="margin-top:16px;">
      <div class="card" style="margin-top:0;">
        <h3><span class="mode-arche">Siła archetypów (Bradley–Terry)</span><span class="mode-values">Siła wartości (Bradley–Terry)</span></h3>
        {img_tag_dual("A_strength.png")}
      </div>
      <div class="card" style="margin-top:0;">
        <h3>Zwycięstwa vs przegrane</h3>
        {img_tag_dual("A_zwyciestwa_przegrane.png")}
      </div>
    </div>
    <div class="card" style="margin-top:16px;">
      <h3><span class="mode-arche">Siła archetypów (Bradley–Terry) — tabela</span><span class="mode-values">Siła wartości (Bradley–Terry) — tabela</span></h3>
      {df_to_html_dual(df_A_strength, max_rows=20)}
    </div>
    <div class="card chart-half" style="margin-top:16px;">
      <h3>Bilans starć (wygrane - przegrane)</h3>
      {img_tag_dual("A_bilans_starc.png")}
    </div>
  </div>

  {ppp_panel_html}

  <div class="panel pB">
    <h2>Oczekiwania wobec miasta (TOP3 i TOP1)</h2>
    <div class="small">
      Poniżej znajduje się 12 opisów. Proszę wybrać maksymalnie 3, które najlepiej pasują do tego,
      jak – Pana/Pani zdaniem – powinno działać {_html_escape(settings.city_label)} w najbliższych latach.
    </div>
    <div class="grid">
      <div class="card">
        <h3>Kluczowe oczekiwania (najczęściej w trójce)</h3>
        {img_tag_dual("B1_top3.png")}
        {df_to_html_dual(df_B1, max_rows=20)}
      </div>
      <div class="card">
        <h3>Najważniejsze oczekiwanie</h3>
        {img_tag_dual("B2_top1.png")}
        {df_to_html_dual(df_B2, max_rows=20)}
      </div>
    </div>
    <div class="card chart-half" style="margin-top:16px;">
      <h3>Ranking trójek (kombinacje)</h3>
      {img_tag_dual("B1_trojki_top5.png")}
      {df_to_html_sig_dual(df_B_tr, max_rows=30)}
    </div>
  </div>

  <div class="panel pD">
    <h2>Doświadczanie miasta (+/–)</h2>
    <div class="small">
      Poniżej znajdują się pary stwierdzeń o różnych sferach funkcjonowania {_html_escape(settings.city_label)}, celowo ujęte w dwóch skrajnych wersjach.
      Proszę w każdej parze wybrać wariant (A albo B), który lepiej odpowiada Pana/Pani doświadczeniom i obserwacjom.
    </div>
    <div class="grid">
      <div class="card">
        <h3>Doświadczenia pozytywne vs negatywne</h3>
        {img_tag_dual("D_plus_minus_diverging.png")}
        {img_tag_dual("D_kolo_plus_minus.png")}
        {df_to_html_dual(df_D12, max_rows=20)}
      </div>
      <div class="card">
        <h3>Kluczowy obszar doświadczeń</h3>
        {img_tag_dual("D13_top1.png")}
        {df_to_html_dual(df_D13, max_rows=20)}
      </div>
    </div>
  </div>

  <div class="panel pS">
      <h2>Segmenty</h2>
      <div class="small">
        Jedna główna segmentacja <b>motywacyjna</b> oparta na <b>profilu 12 <span class="mode-arche">archetypów</span><span class="mode-values">wartości</span> (P)</b>.
        Segmenty budujemy na meta-osiach wyprowadzonych z P, a następnie porządkujemy je
        <b>od największego do najmniejszego</b>. Metryczka służy wyłącznie do opisu segmentów,
        nie do ich budowy.
      </div>
      {seg_panel_html("ultra_premium",
                      "Segmentacja - informacje",
                      "Model segmentacji jest stały dla tego raportu. Suwak <b>nie liczy nowych segmentów</b> — tylko ukrywa / pokazuje pierwsze <b>N</b> segmentów (domyślnie <b>5</b>).",
                      slider_k_min, slider_k_max, slider_k_def,
                      include_lca_sig=True)}

      <div class="card" style="margin-top:16px;">
        <h3>Mapa przewag segmentów</h3>
        <div class="small">
          Położenie <span class="mode-arche">archetypów</span><span class="mode-values">wartości</span> jest liczone z aktualnych danych, a obrys segmentu
          obejmuje te <span class="mode-arche">archetypy</span><span class="mode-values">wartości</span>, które są realnie wyróżnione w segmencie na bazie Pm.
          To jest mapa interpretacyjna spójna z porównaniami między segmentami.
          Wersja mapy zmienia się wraz z suwakiem — pokazujemy tylko pierwsze N segmentów.
        </div>
        <div id="seg_ultra_premium_map_wrap" class="seg-map-wrap">
          <div class="label-arche">
            <img id="seg_ultra_premium_map_arche"
                 src="SEGMENTY_META_MAPA_STALA_K{slider_k_def}.png"
                 alt="Mapa przewag segmentów"
                 style="width:100%; max-width:1180px; display:block; margin:10px 0 0 0;">
          </div>
          <div class="label-values">
            <img id="seg_ultra_premium_map_values"
                 src="SEGMENTY_META_MAPA_STALA_K{slider_k_def}_values.png"
                 alt="Mapa przewag segmentów"
                 style="width:100%; max-width:1180px; display:block; margin:10px 0 0 0;">
          </div>
        </div>
      </div>
  </div>

  <div class="panel pC">
    <h2>Skupienia (k-średnich)</h2>
    <div class="small">
      Klasyczna analiza skupień oparta na standaryzowanym profilu <b>P</b> (12 <span class="mode-arche">archetypów</span><span class="mode-values">wartości</span>).
      Najlepszy model: <b>K={cluster_k_best_txt}</b> (testowany zakres: <b>{cluster_k_range_txt}</b>).
    </div>

    {cluster_quality_html}

    <div class="grid" style="margin-top:16px;">
      <div class="card">
        <h3>Dobór K — silhouette</h3>
        {img_tag(cluster_silhouette_png)}
      </div>
      <div class="card">
        <h3>Dobór K — elbow (WSS)</h3>
        {img_tag(cluster_elbow_png)}
      </div>
    </div>

    {cluster_panel_html}

    <div class="card" style="margin-top:16px;">
      <h3>Wybrany model skupień (K)</h3>
      <div class="small">
        Każda wartość <b>K</b> oznacza inny model k-średnich (inne granice i liczebności skupień).
        Suwak poniżej przełącza cały model prezentowany w tej zakładce.
      </div>
      <div style="margin-top:10px;">
        <span class='seg-help'>Aktualny model: <b><span id="cluster_k_value">{cluster_k_default_ui}</span></b></span>
        &nbsp; / &nbsp; Najlepszy wg silhouette: <b><span id="cluster_k_best_label">{cluster_k_best_txt}</span></b>
        &nbsp; / &nbsp; Zakres testowany: <b>{cluster_k_range_txt}</b>
      </div>
      <input id="cluster_k_slider"
             type="range"
             min="{cluster_k_min if cluster_k_min >= 2 else 2}"
             max="{cluster_k_max if cluster_k_max >= 2 else 2}"
             step="1"
             value="{cluster_k_default_ui if cluster_k_default_ui >= 2 else 2}"
             style="width:100%; margin-top:10px;" />
    </div>

    <div class="card" style="margin-top:16px;">
      <h3 id="cluster_projection_title">Mapa skupień (projekcja dla wybranego K)</h3>
      <div id="cluster_projection_wrap" class="cluster-figure-wrap main">
        {img_tag(cluster_projection_png)}
      </div>
      <div class="cluster-legend-note">Legenda: <b>Seg_X: nazwa segmentu</b>.</div>
    </div>

    <div id="cluster_profiles_wrap" class="cluster-profiles" style="margin-top:16px;">
      <div class="label-arche">{cluster_profiles_html_arche}</div>
      <div class="label-values">{cluster_profiles_html_values}</div>
    </div>

    <div id="cluster_matrix_wrap" class="card" style="margin-top:16px;">
      <h3>Matryca skupień</h3>
      <div class="small">
        Wiersze pokazują surowy poziom Pm dla <span class="mode-arche">archetypów</span><span class="mode-values">wartości</span>,
        a kolumny odpowiadają skupieniom (Seg_1...Seg_K).
      </div>
      <div class="label-arche">{cluster_matrix_html_arche}</div>
      <div class="label-values">{cluster_matrix_html_values}</div>
    </div>
  </div>

  <div class="panel pG">
    <h2>Demografia_Seg</h2>
    <div class="small">
      Zbiorcza demografia wszystkich segmentów. W wierszach pokazujemy wszystkie zmienne i kategorie,
      a w kolumnach próbę ({_html_escape(settings.city)}) oraz segmenty. Długość paska = odsetek 0–100%.
    </div>
    {demografia_seg_html}
  </div>

  <div class="panel pH">
    <h2>Demografia priorytetu (B2)</h2>
    <div class="small">
      Widok strategiczny: profil demograficzny mieszkańców deklarujących najważniejszy <span class="mode-arche">archetyp</span><span class="mode-values">wartość</span>.
      Możesz jednocześnie filtrować segment i <span class="mode-arche">archetyp</span><span class="mode-values">wartość</span>, aby zobaczyć profil punktowo dla wybranego elektoratu.
    </div>
    {b2_declared_demo_html}
  </div>

  <div class="panel pY">
    <h2>Symulacja</h2>
    <div class="small">
      Wybierz od 1 do 3 <span class="mode-arche">archetypów</span><span class="mode-values">wartości</span>.
      Pokazujemy 4 wskaźniki: <b>Zasięg (% mieszkańców)</b>, <b>Siła priorytetu</b> (0-100),
      <b>Potencjał kampanijny</b> (0-100) i <b>Rdzeń mobilizacyjny</b> (0-100).
      Logika: <span class="mono">single = B1 * (0.60 + 0.30*B2 + 0.10*D13)</span>, a dla 2-3 wyborów:
      <span class="mono">1 - Π(1 - single)</span>.
    </div>
    {top5_simulation_html}
  </div>

  <div class="panel pK">
    <h2>Korelacje</h2>
    <div class="small">Korelacje <span class="mode-arche">archetypów</span><span class="mode-values">wartości</span> pokazane jako heatmapy z automatycznym grupowaniem podobnych etykiet obok siebie.</div>
    <div class="grid3">
      <div class="card corr-tile">
        <h3>Preferencje (P) – korelacje</h3>
        {img_tag_dual("HEATMAPA_KORELACJI_P.png")}
      </div>
      <div class="card corr-tile">
        <h3>Doświadczenie (E) – korelacje</h3>
        {img_tag_dual("HEATMAPA_KORELACJI_E.png")}
      </div>
      <div class="card corr-tile">
        <h3>Priorytety (G) – korelacje</h3>
        {img_tag_dual("HEATMAPA_KORELACJI_G.png")}
      </div>
    </div>
  </div>

  <div class="panel pM">
    <h2>Mapy wartości (autorski model)</h2>
    <div class="small">
      Mapy są wyliczane z danych (na podstawie podobieństw/korelacji).
      Dlatego położenie <span class="mode-arche">archetypów</span><span class="mode-values">wartości</span> może się zmieniać między badaniami oraz między próbami.
      Dla tych samych danych (ten sam plik) układ pozostaje stały.
    </div>
    <div class="grid">
      <div class="card">
        <h3>Mapa wartości dla P = preferencje</h3>
        {img_tag_dual("MAPA_WARTOSCI_P_DATA.png")}
      </div>
      <div class="card">
        <h3>Mapa wartości dla E = doświadczenia</h3>
        {img_tag_dual("MAPA_WARTOSCI_E_DATA.png")}
      </div>
    </div>
    <div class="card chart-half" style="margin-top:16px;">
      <h3>Mapa wartości dla G = priorytety</h3>
      {img_tag_dual("MAPA_WARTOSCI_G_DATA.png")}
    </div>

  </div>

  <div class="panel pR">
    <h2>Filtry</h2>

    <div class="card">
      <div style="display:flex; gap:12px; align-items:center; flex-wrap:wrap;">
        <b><span class="mode-arche">Archetyp:</span><span class="mode-values">Wartość:</span></b>
        <select id="filter_archetype" style="padding:8px 10px; border:1px solid #ddd; border-radius:10px; font-weight:700;"></select>
        <span class="small" id="filter_selected_label"></span>
      </div>

      <div class="small" style="margin-top:10px;">
        Po wyborze <span class="mode-arche">archetypu</span><span class="mode-values">wartości</span> pokazujemy:
        (1) <b>%</b> tego <span class="mode-arche">archetypu</span><span class="mode-values">wartości</span> w blokach A, B1, B2, D13 (oś Y stała 0–100%),
        (2) <b>miejsce</b> (ranking 1–12) w tych samych blokach (oś Y stała 1–12).
        W bloku A pokazujemy <b>% oczekujących</b> z sekcji PPP (netto: score_mean > 0 po zbilansowaniu 3 porównań).
        W blokach B1/B2/D13 pokazujemy % wskazań respondentów.
      </div>
    </div>

    <div class="grid" style="margin-top:16px;">
      <div class="card">
        <h3 id="filter_title_pct"><span class="mode-arche">% oczekujących archetypu</span><span class="mode-values">% oczekujących wartości</span></h3>
        <svg id="chart_pct" viewBox="0 0 700 320" style="width:100%;max-width:1380px;"></svg>
      </div>
      <div class="card">
        <h3 id="filter_title_rank"><span class="mode-arche">Miejsce archetypu</span><span class="mode-values">Miejsce wartości</span></h3>
        <svg id="chart_rank" viewBox="0 0 700 320" style="width:100%;max-width:1380px;"></svg>
      </div>
    </div>
  </div>

  <div class="panel pT">
    <h2>TOP5</h2>
    <div class="small">
      TOP5 w blokach A / B1 / B2 / D13. Wszędzie pokazujemy tylko % (bez liczebności).
      A liczone jako <b>% oczekujących</b> z sekcji PPP.
      B1/B2/D13 jako % respondentów.
    </div>

    <div class="card" style="margin-top:16px;">
      <h3>Macierz TOP5</h3>
      <div class="small">Wiersz = <span class="mode-arche">archetyp</span><span class="mode-values">wartość</span>, kolumny = bloki. Komórka: % oraz pozycja w TOP5 (#1–#5).</div>
      {top5_matrix_dual(df_top5_A, df_B1_pct, df_B2_pct, df_D13_pct, brand_values)}
    </div>

    <div class="card" style="margin-top:16px;">
      <h3>Macierz TOP5 – kropki (miejsce #1–#5)</h3>
      <div class="small">Kropka oznacza obecność w TOP5; kolor odpowiada miejscu. Legenda jest nad tabelą.</div>
      {top5_dot_matrix_dual(df_top5_A, df_B1_pct, df_B2_pct, df_D13_pct, brand_values)}
    </div>

    <div class="grid" style="margin-top:18px;">
      <div class="card">
        <h3><span class="mode-arche">% oczekujących archetypu (A) – TOP5</span><span class="mode-values">% oczekujących wartości (A) – TOP5</span></h3>
        {top5_table_dual(df_top5_A, brand_values, max_rows=10)}
      </div>
      <div class="card">
        <h3>doświadczenie – TOP5</h3>
        {top5_table_dual(df_D13_pct, brand_values, max_rows=10)}
      </div>
    </div>

    <div class="grid" style="margin-top:16px;">
      <div class="card">
        <h3>3 priorytety – TOP5</h3>
        {top5_table_dual(df_B1_pct, brand_values, max_rows=10)}
      </div>
      <div class="card">
        <h3>najważniejszy – TOP5</h3>
        {top5_table_dual(df_B2_pct, brand_values, max_rows=10)}
      </div>
    </div>

    <div class="grid" style="margin-top:16px;">
      <div class="card">
        <h3>Legenda</h3>
        {top5_legend_html()}
      </div>
      <div class="card" style="visibility:hidden;"></div>
    </div>
  </div>


</div>
{js}
</body></html>"""

    with open(outdir / "raport.html", "w", encoding="utf-8") as f:
        f.write(html_doc)


# 12B) HELPERY HISTORYCZNE / ZGODNOŚCIOWE: sygnatury i narzędzia po dawnej ścieżce LCA
# =========================

def lca_signatures_table(A: np.ndarray,
                         d12: np.ndarray,
                         b1: np.ndarray,
                         b2: np.ndarray,
                         d13: np.ndarray,
                         weights: np.ndarray,
                         seg_id_lca: np.ndarray,
                         ARCHETYPES: List[str],
                         A_PAIRS: List[Tuple[str, str, str]],
                         D_ITEMS: List[Tuple[str, str]],
                         A_center: float) -> pd.DataFrame:
    """
    Sygnatury klas LCA:
    - A: TOP dodatnich odchyleń vs cała próba (pp)
    - D12(+): TOP dodatnich odchyleń udziału PLUS vs cała próba (pp)
    - B1/B2/D13: TOP wskazań w klasie (%)
    """
    weights = np.asarray(weights, dtype=float).reshape(-1)
    seg = np.asarray(seg_id_lca)
    valid_seg = np.isfinite(seg)
    seg = np.where(valid_seg, seg, -1).astype(int)

    def _fmt_pct_val(x: float) -> str:
        if not np.isfinite(x):
            return "-"
        return f"{float(x):.1f}%"

    def _fmt_pp_val(x: float) -> str:
        if not np.isfinite(x):
            return "-"
        return f"{float(x):+.1f} pp"

    def _format_top(s: pd.Series, k: int = 3, fmt_pp: bool = False) -> str:
        if s is None or len(s) == 0:
            return "-"
        ss = s.dropna().sort_values(ascending=False).head(k)
        if len(ss) == 0:
            return "-"
        parts = []
        for idx, val in ss.items():
            label = str(idx)
            metric = _fmt_pp_val(float(val)) if fmt_pp else _fmt_pct_val(float(val))
            parts.append(f"{label} ({metric})")
        return " • ".join(parts) if parts else "-"

    def _A_pct(mask: np.ndarray) -> pd.Series:
        mask = np.asarray(mask, dtype=bool).reshape(-1)
        wins = {a: 0.0 for a in ARCHETYPES}
        votes = {a: 0.0 for a in ARCHETYPES}

        for j, (_pid, left_arch, right_arch) in enumerate(A_PAIRS):
            v = np.asarray(A[:, j], dtype=float)
            m = mask & np.isfinite(v)
            if not np.any(m):
                continue

            pair_w = float(weights[m].sum())
            votes[left_arch] += pair_w
            votes[right_arch] += pair_w

            wins[left_arch] += float(weights[m & (v < float(A_center))].sum())
            wins[right_arch] += float(weights[m & (v > float(A_center))].sum())

        return pd.Series(
            {
                a: ((wins[a] / votes[a]) * 100.0) if votes[a] > 0 else np.nan
                for a in ARCHETYPES
            },
            dtype=float
        )

    def _D_plus(mask: np.ndarray) -> pd.Series:
        mask = np.asarray(mask, dtype=bool).reshape(-1)
        out = {}

        for j, (_qid, arch) in enumerate(D_ITEMS):
            v = np.asarray(d12[:, j], dtype=float)
            m = mask & np.isfinite(v) & (v != 0)
            if not np.any(m):
                out[arch] = np.nan
                continue

            denom = float(weights[m].sum())
            plus_w = float(weights[m & (v > 0)].sum())
            out[arch] = (plus_w / denom) * 100.0 if denom > 0 else np.nan

        return pd.Series(out, dtype=float)

    def _B1_pct(mask: np.ndarray) -> pd.Series:
        mask = np.asarray(mask, dtype=bool).reshape(-1)
        if not np.any(mask):
            return pd.Series({a: np.nan for a in ARCHETYPES}, dtype=float)

        b1_seg = np.nan_to_num(np.asarray(b1[mask], dtype=float), nan=0.0)
        w_seg = weights[mask].reshape(-1, 1)

        answered = np.isfinite(np.asarray(b1[mask], dtype=float)).any(axis=1)
        denom = float(weights[mask][answered].sum()) if np.any(answered) else float(weights[mask].sum())
        if denom <= 0:
            return pd.Series({a: np.nan for a in ARCHETYPES}, dtype=float)

        counts = (b1_seg * w_seg).sum(axis=0)
        return pd.Series(counts / denom * 100.0, index=ARCHETYPES, dtype=float)

    def _TOP1_pct(top1_idx: np.ndarray, mask: np.ndarray) -> pd.Series:
        mask = np.asarray(mask, dtype=bool).reshape(-1)
        idx = np.asarray(top1_idx, dtype=float).reshape(-1)

        m = mask & np.isfinite(idx) & (idx >= 0)
        denom = float(weights[m].sum())
        if denom <= 0:
            return pd.Series({a: np.nan for a in ARCHETYPES}, dtype=float)

        counts = np.zeros(len(ARCHETYPES), dtype=float)
        idx_sel = idx[m].astype(int)
        w_sel = weights[m]

        for ii, ww in zip(idx_sel, w_sel):
            if 0 <= int(ii) < len(ARCHETYPES):
                counts[int(ii)] += float(ww)

        return pd.Series(counts / denom * 100.0, index=ARCHETYPES, dtype=float)

    mask_all = np.isfinite(seg) & (seg >= 0)
    A_all = _A_pct(mask_all)
    D_all = _D_plus(mask_all)

    rows = []
    for s in sorted([x for x in np.unique(seg) if x >= 0]):
        m = seg == s

        A_k = _A_pct(m)
        D_k = _D_plus(m)
        B1_k = _B1_pct(m)
        B2_k = _TOP1_pct(b2, m)
        D13_k = _TOP1_pct(d13, m)

        dA = (A_k - A_all).sort_values(ascending=False)
        dD = (D_k - D_all).sort_values(ascending=False)

        rows.append({
            "klasa": f"LCA_{int(s) + 1}",
            "Segment": f"Seg_{int(s) + 1}",
            "A: TOP +Δ": _format_top(dA, k=3, fmt_pp=True),
            "D12(+): TOP +Δ": _format_top(dD, k=3, fmt_pp=True),
            "B1: TOP w klasie": _format_top(B1_k, k=3, fmt_pp=False),
            "B2: TOP w klasie": _format_top(B2_k, k=3, fmt_pp=False),
            "D13: TOP w klasie": _format_top(D13_k, k=3, fmt_pp=False),
        })

    return pd.DataFrame(rows)


# =========================
# 13) BOOTSTRAP CI
# =========================

def bootstrap_ci(data: np.ndarray, weights: np.ndarray, reps: int, seed: int = 0) -> Tuple[np.ndarray, np.ndarray]:
    """
    Bootstrap CI dla średniej ważonej (wagi traktowane jako stałe).
    Poprawka: losowanie respondentów jest równomierne (klasyczny bootstrap),
    a estymator w każdej replice jest średnią ważoną wagami oryginalnymi.

    Dzięki temu NIE ma podwójnego ważenia (waga^2).
    """
    rng = np.random.default_rng(seed)
    n, k = data.shape
    w_all = np.asarray(weights, dtype=float).reshape(-1)

    means = np.full((reps, k), np.nan, dtype=float)

    for r in range(reps):
        # klasyczny bootstrap: losuj respondentów równomiernie
        idx = rng.integers(0, n, size=n)
        X = data[idx]
        w = w_all[idx]

        for j in range(k):
            xj = X[:, j]
            mj = np.isfinite(xj) & np.isfinite(w) & (w > 0)
            if not np.any(mj):
                continue
            means[r, j] = float(np.average(xj[mj], weights=w[mj]))

    lo = np.nanpercentile(means, 2.5, axis=0)
    hi = np.nanpercentile(means, 97.5, axis=0)
    return lo, hi


# =========================
# PREMIUM SEGMENTACJE (3x): metryczkowa / postawy / LCA
# =========================

def _wmean_1d(x: np.ndarray, w: np.ndarray) -> float:
    x = np.asarray(x, dtype=float).reshape(-1)
    w = np.asarray(w, dtype=float).reshape(-1)
    m = np.isfinite(x) & np.isfinite(w) & (w > 0)
    if not np.any(m):
        return float("nan")
    return float(np.sum(x[m] * w[m]) / np.sum(w[m]))


def _wvar_1d(x: np.ndarray, w: np.ndarray) -> float:
    mu = _wmean_1d(x, w)
    if not np.isfinite(mu):
        return float("nan")
    x = np.asarray(x, dtype=float).reshape(-1)
    w = np.asarray(w, dtype=float).reshape(-1)
    m = np.isfinite(x) & np.isfinite(w) & (w > 0)
    if not np.any(m):
        return float("nan")
    ww = w[m]
    xx = x[m] - mu
    return float(np.sum(ww * (xx ** 2)) / np.sum(ww))


def _wquantiles(x: np.ndarray, w: np.ndarray, qs: List[float]) -> List[float]:
    x = np.asarray(x, dtype=float).reshape(-1)
    w = np.asarray(w, dtype=float).reshape(-1)
    m = np.isfinite(x) & np.isfinite(w) & (w > 0)
    if not np.any(m):
        return [float("nan") for _ in qs]
    xx = x[m]
    ww = w[m]
    order = np.argsort(xx)
    xx = xx[order]
    ww = ww[order]
    cdf = np.cumsum(ww) / (np.sum(ww) + 1e-12)
    out = []
    for q in qs:
        q = float(q)
        idx = int(np.searchsorted(cdf, q, side="left"))
        idx = min(max(idx, 0), len(xx) - 1)
        out.append(float(xx[idx]))
    return out


def _wstandardize(X: np.ndarray, w: np.ndarray) -> np.ndarray:
    X = np.asarray(X, dtype=float)
    w = np.asarray(w, dtype=float).reshape(-1)
    Z = np.full_like(X, np.nan, dtype=float)
    for j in range(X.shape[1]):
        x = X[:, j]
        mu = _wmean_1d(x, w)
        sd = np.sqrt(_wvar_1d(x, w))
        if not np.isfinite(mu) or not np.isfinite(sd) or sd <= 1e-12:
            Z[:, j] = 0.0
        else:
            Z[:, j] = (x - mu) / (sd + 1e-12)
        Z[~np.isfinite(Z[:, j]), j] = 0.0
    return Z


def _weighted_kmeans(X: np.ndarray, w: np.ndarray, k: int = 3, seed: int = 0,
                     n_init: int = 6, max_iter: int = 200, tol: float = 1e-5) -> Tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    X = np.asarray(X, dtype=float)
    w = np.asarray(w, dtype=float).reshape(-1)
    n = X.shape[0]

    m_ok = np.isfinite(X).all(axis=1) & np.isfinite(w) & (w > 0)
    if m_ok.sum() < k:
        labels = np.zeros(n, dtype=int)
        cent = np.zeros((k, X.shape[1]), dtype=float)
        return labels, cent

    X0 = X[m_ok]
    w0 = w[m_ok]
    n0 = X0.shape[0]

    best_inertia = float("inf")
    best_labels_full = np.zeros(n, dtype=int)
    best_centroids = np.zeros((k, X.shape[1]), dtype=float)

    def _init_kpp() -> np.ndarray:
        centroids = np.zeros((k, X0.shape[1]), dtype=float)
        # 1st center: weighted random
        p = w0 / (np.sum(w0) + 1e-12)
        i0 = int(rng.choice(np.arange(n0), p=p))
        centroids[0] = X0[i0]

        d2 = np.sum((X0 - centroids[0]) ** 2, axis=1)
        for ci in range(1, k):
            probs = w0 * d2
            if np.sum(probs) <= 0:
                i = int(rng.integers(0, n0))
            else:
                probs = probs / (np.sum(probs) + 1e-12)
                i = int(rng.choice(np.arange(n0), p=probs))
            centroids[ci] = X0[i]
            d2 = np.minimum(d2, np.sum((X0 - centroids[ci]) ** 2, axis=1))
        return centroids

    for _run in range(n_init):
        centroids = _init_kpp()

        labels0 = np.zeros(n0, dtype=int)
        for it in range(max_iter):
            # assign
            dist = np.sum((X0[:, None, :] - centroids[None, :, :]) ** 2, axis=2)
            new_labels0 = np.argmin(dist, axis=1)

            # update
            new_centroids = centroids.copy()
            for ci in range(k):
                mm = new_labels0 == ci
                if not np.any(mm):
                    # reinit empty cluster
                    i = int(rng.choice(np.arange(n0), p=(w0 / (np.sum(w0) + 1e-12))))
                    new_centroids[ci] = X0[i]
                    continue
                ww = w0[mm]
                xx = X0[mm]
                new_centroids[ci] = np.sum(xx * ww[:, None], axis=0) / (np.sum(ww) + 1e-12)

            shift = float(np.nanmax(np.abs(new_centroids - centroids)))
            centroids = new_centroids
            labels0 = new_labels0
            if shift < tol:
                break

        # inertia (weighted)
        dist = np.sum((X0 - centroids[labels0]) ** 2, axis=1)
        inertia = float(np.sum(dist * w0))

        if inertia < best_inertia:
            best_inertia = inertia
            best_centroids = centroids.copy()
            labels_full = np.zeros(n, dtype=int)
            labels_full[m_ok] = labels0
            best_labels_full = labels_full

    return best_labels_full, best_centroids


def _guess_metryczka_cols(df: pd.DataFrame, weight_col: str) -> List[str]:
    import re
    cols = []
    for c in df.columns:
        if c == weight_col:
            continue
        cn = str(c).strip()
        if cn == "":
            continue
        # wytnij oczywiste bloki ankiety
        if re.match(r"^[ABCD]\d+", cn):
            continue
        if cn.startswith(("A_", "B_", "D_", "P_", "E_", "G_")):
            continue
        if cn.lower() in ("id", "uuid", "timestamp", "czas", "start", "end"):
            continue

        s = df[c]
        nun = int(s.nunique(dropna=True))
        # metryczka zwykle: mało kategorii (np. 2..20), albo liczby typu wiek
        if pd.api.types.is_numeric_dtype(s):
            if nun <= 40:
                cols.append(c)
        else:
            if 2 <= nun <= 25:
                cols.append(c)
    return cols


def _make_3_bins_from_numeric(x: np.ndarray, w: np.ndarray) -> Tuple[np.ndarray, List[str]]:
    q1, q2 = _wquantiles(x, w, [1 / 3, 2 / 3])
    if not np.isfinite(q1) or not np.isfinite(q2) or q1 == q2:
        # fallback: równe koszyki po indeksie sortowania
        order = np.argsort(np.nan_to_num(x, nan=0.0))
        labels = np.full(len(x), -1, dtype=int)
        n = len(x)
        cut1 = n // 3
        cut2 = 2 * n // 3
        labels[order[:cut1]] = 0
        labels[order[cut1:cut2]] = 1
        labels[order[cut2:]] = 2
        defs = ["niski", "średni", "wysoki"]
        return labels, defs

    labels = np.full(len(x), -1, dtype=int)
    m = np.isfinite(x)
    labels[m & (x <= q1)] = 0
    labels[m & (x > q1) & (x <= q2)] = 1
    labels[m & (x > q2)] = 2
    defs = [f"≤ {q1:.2f}", f"({q1:.2f}, {q2:.2f}]", f"> {q2:.2f}"]
    return labels, defs


def _make_3_bins_from_category(cat: pd.Series, y: np.ndarray, w: np.ndarray) -> Tuple[np.ndarray, List[str]]:
    # porządkuj kategorie po średniej y, potem dziel na 3 koszyki o podobnej wadze
    s = cat.astype("object")
    m = s.notna() & np.isfinite(y) & np.isfinite(w) & (w > 0)
    if not np.any(m):
        labels = np.zeros(len(s), dtype=int)
        defs = ["brak danych", "brak danych", "brak danych"]
        return labels, defs

    dfc = pd.DataFrame({"cat": s[m].astype(str), "y": y[m], "w": w[m]})
    g = dfc.groupby("cat", as_index=False).apply(
        lambda d: pd.Series({"w": float(d["w"].sum()), "mu": float(np.sum(d["y"] * d["w"]) / (d["w"].sum() + 1e-12))})
    ).reset_index(drop=True)

    g = g.sort_values("mu", ascending=True).reset_index(drop=True)
    total_w = float(g["w"].sum()) + 1e-12
    target = total_w / 3.0

    buckets = [[], [], []]
    b = 0
    acc = 0.0
    for i in range(len(g)):
        buckets[b].append(str(g.loc[i, "cat"]))
        acc += float(g.loc[i, "w"])
        if acc >= target and b < 2:
            b += 1
            acc = 0.0

    mp = {}
    for bi in range(3):
        for c in buckets[bi]:
            mp[c] = bi

    labels = np.full(len(s), -1, dtype=int)
    for i in range(len(s)):
        if pd.isna(s.iloc[i]):
            continue
        labels[i] = int(mp.get(str(s.iloc[i]), 1))  # nieznane -> środek

    defs = [
        " | ".join(buckets[0]) if buckets[0] else "(pusto)",
        " | ".join(buckets[1]) if buckets[1] else "(pusto)",
        " | ".join(buckets[2]) if buckets[2] else "(pusto)",
    ]
    return labels, defs


def build_metryczka_segments_3(df: pd.DataFrame, y_scalar: np.ndarray, w: np.ndarray, weight_col: str) -> Tuple[
    str, np.ndarray, List[str]]:
    """
    Deterministyczna segmentacja metryczkowa:
    - wybiera najlepszą kolumnę metryczkową (heurystycznie) pod kątem wyjaśniania y_scalar
    - buduje dokładnie 3 segmenty (koszyki)
    """
    cand = _guess_metryczka_cols(df, weight_col=weight_col)
    if not cand:
        # fallback: tniemy po tercylach y_scalar
        labels, defs = _make_3_bins_from_numeric(np.asarray(y_scalar, dtype=float), w)
        return "PRIORYTET_G (fallback)", labels, defs

    best_col = None
    best_r2 = -1e9
    best_labels = None
    best_defs = None

    y = np.asarray(y_scalar, dtype=float).reshape(-1)
    for c in cand:
        s = df[c]
        if pd.api.types.is_numeric_dtype(s):
            labels, defs = _make_3_bins_from_numeric(s.to_numpy(dtype=float, copy=False), w)
        else:
            labels, defs = _make_3_bins_from_category(s, y, w)

        m = (labels >= 0) & np.isfinite(y) & np.isfinite(w) & (w > 0)
        if m.sum() < 20:
            continue

        # R^2 ~ międzygrupowa wariancja / całkowita
        yv = y[m]
        wv = w[m]
        tot = _wvar_1d(yv, wv)
        if not np.isfinite(tot) or tot <= 1e-12:
            continue

        mu = _wmean_1d(yv, wv)
        bg = 0.0
        for seg_id in (0, 1, 2):
            mm = (labels[m] == seg_id)
            if not np.any(mm):
                continue
            mu_g = _wmean_1d(yv[mm], wv[mm])
            wg = float(np.sum(wv[mm]))
            bg += wg * ((mu_g - mu) ** 2)
        bg = bg / (float(np.sum(wv)) + 1e-12)
        r2 = bg / (tot + 1e-12)

        if r2 > best_r2:
            best_r2 = r2
            best_col = str(c)
            best_labels = labels
            best_defs = defs

    if best_col is None or best_labels is None:
        labels, defs = _make_3_bins_from_numeric(np.asarray(y_scalar, dtype=float), w)
        return "PRIORYTET_G (fallback)", labels, defs

    return best_col, best_labels, best_defs


def build_attitudinal_segments_3(P: np.ndarray, E: np.ndarray, w: np.ndarray, seed: int = 0) -> np.ndarray:
    """
    Segmentacja postaw: cechy ciągłe (P + E), standaryzacja ważona, k=3, KMeans (ważony).
    """
    Pz = _wstandardize(np.asarray(P, dtype=float), w)
    Ez = _wstandardize(np.nan_to_num(np.asarray(E, dtype=float), nan=50.0), w)
    X = np.hstack([Pz, Ez])
    labels, _cent = _weighted_kmeans(X, w, k=3, seed=seed, n_init=8, max_iter=250)
    return labels


def build_lca_input(A: np.ndarray, d12: np.ndarray, b1: np.ndarray, b2: np.ndarray, d13: np.ndarray,
                    a_center: float, n_arche: int) -> Tuple[np.ndarray, List[int], Dict[str, slice]]:
    """
    Skleja macierz kategoryczną pod LCA:
    - A: 3 kategorie (lewo / środek / prawo)
    - D12: 2 kategorie (-/+)
    - B1: 2 kategorie (nie/wybrane)
    - B2: 12 kategorii (TOP1)
    - D13: 12 kategorii (TOP1)
    Missing = -1
    """
    n = A.shape[0]
    blocks: Dict[str, slice] = {}
    mats = []
    cards: List[int] = []

    # A
    Ac = np.full_like(A, -1, dtype=int)
    m = np.isfinite(A)
    Ac[m & (A < a_center)] = 0
    Ac[m & (A == a_center)] = 1
    Ac[m & (A > a_center)] = 2
    blocks["A"] = slice(0, Ac.shape[1])
    mats.append(Ac)
    cards += [3] * Ac.shape[1]

    # D12
    Dc = np.full_like(d12, -1, dtype=int)
    m = np.isfinite(d12)
    Dc[m & (d12 < 0)] = 0
    Dc[m & (d12 > 0)] = 1
    start = sum(x.shape[1] for x in mats)
    blocks["D12"] = slice(start, start + Dc.shape[1])
    mats.append(Dc)
    cards += [2] * Dc.shape[1]

    # B1 (binary selections)
    B1c = np.full_like(b1, -1, dtype=int)
    m = np.isfinite(b1)
    B1c[m & (b1 <= 0)] = 0
    B1c[m & (b1 > 0)] = 1
    start = sum(x.shape[1] for x in mats)
    blocks["B1"] = slice(start, start + B1c.shape[1])
    mats.append(B1c)
    cards += [2] * B1c.shape[1]

    # B2
    B2c = np.full((n, 1), -1, dtype=int)
    m = np.isfinite(b2) & (b2 >= 0)
    B2c[m, 0] = b2[m].astype(int)
    start = sum(x.shape[1] for x in mats)
    blocks["B2"] = slice(start, start + 1)
    mats.append(B2c)
    cards += [n_arche]

    # D13
    D13c = np.full((n, 1), -1, dtype=int)
    m = np.isfinite(d13) & (d13 >= 0)
    D13c[m, 0] = d13[m].astype(int)
    start = sum(x.shape[1] for x in mats)
    blocks["D13"] = slice(start, start + 1)
    mats.append(D13c)
    cards += [n_arche]

    X = np.hstack(mats)
    return X, cards, blocks


def fit_lca_em(X: np.ndarray, cards: List[int], w: np.ndarray, k: int = 3, seed: int = 0,
               max_iter: int = 250, tol: float = 1e-6, alpha: float = 0.6) -> Tuple[
    np.ndarray, np.ndarray, np.ndarray, float]:
    """
    LCA (Latent Class Analysis) EM dla danych kategorycznych (missing=-1), z wagami.
    Zwraca: labels, gamma (posterior n×k), pi (k,)
    """
    rng = np.random.default_rng(seed)
    X = np.asarray(X, dtype=int)
    w = np.asarray(w, dtype=float).reshape(-1)
    n, p = X.shape

    # init pi
    pi = np.full(k, 1.0 / k, dtype=float)

    # init theta: k × p × card_j
    theta: List[np.ndarray] = []
    for j in range(p):
        cj = int(cards[j])
        t = rng.random((k, cj)) + 1e-3
        t = t / (np.sum(t, axis=1, keepdims=True) + 1e-12)
        theta.append(t)

    gamma = np.full((n, k), 1.0 / k, dtype=float)
    prev_ll = -1e99

    eps = 1e-12

    for it in range(max_iter):
        # ----- E-step -----
        logp = np.zeros((n, k), dtype=float)
        logp += np.log(pi[None, :] + eps)

        for j in range(p):
            xj = X[:, j]
            mj = xj >= 0
            if not np.any(mj):
                continue
            cj = int(cards[j])
            xvv = xj[mj].astype(int)
            xvv = np.clip(xvv, 0, cj - 1)

            for kk in range(k):
                logp[mj, kk] += np.log(theta[j][kk, xvv] + eps)

        # stabilize
        mx = np.max(logp, axis=1, keepdims=True)
        ex = np.exp(logp - mx)
        den = np.sum(ex, axis=1, keepdims=True) + eps
        gamma = ex / den

        # weighted loglik
        ll = float(np.sum(w * (mx.reshape(-1) + np.log(den.reshape(-1) + eps))))

        # ----- M-step -----
        wk = np.sum(gamma * w[:, None], axis=0) + eps
        pi = wk / (np.sum(wk) + eps)

        for j in range(p):
            xj = X[:, j]
            mj = xj >= 0
            cj = int(cards[j])
            if not np.any(mj):
                continue
            for kk in range(k):
                num = np.full(cj, alpha, dtype=float)  # Dirichlet smoothing
                gk = gamma[mj, kk] * w[mj]
                for c in range(cj):
                    mm = (xj[mj] == c)
                    if np.any(mm):
                        num[c] += float(np.sum(gk[mm]))
                theta[j][kk, :] = num / (np.sum(num) + eps)

        # convergence
        if np.isfinite(prev_ll) and abs(ll - prev_ll) < tol * (1.0 + abs(prev_ll)):
            break
        prev_ll = ll

    labels = np.argmax(gamma, axis=1).astype(int)
    return labels, gamma, pi, float(ll)


def _segment_profile_from_labels(labels: np.ndarray, P: np.ndarray, E: np.ndarray, G: np.ndarray,
                                 weights: np.ndarray) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Buduje:
    - seg_df: wiersze (segment_id, archetyp, P/E/G mean)
    - seg_profile: wiersze profilu segmentów (liczba, waga, top3, opis/sugestie/ryzyka)
    """
    labels = np.asarray(labels, dtype=int).reshape(-1)
    weights = np.asarray(weights, dtype=float).reshape(-1)
    k = int(np.max(labels)) + 1

    def wmean_cols_nan(mat: np.ndarray, w: np.ndarray) -> np.ndarray:
        out = np.full(mat.shape[1], np.nan, dtype=float)
        w = np.asarray(w, dtype=float).reshape(-1)
        for j in range(mat.shape[1]):
            xj = mat[:, j]
            mj = np.isfinite(xj) & np.isfinite(w) & (w > 0)
            if not np.any(mj):
                continue
            out[j] = float(np.average(xj[mj], weights=w[mj]))
        return out

    seg_rows = []
    seg_prof_rows = []
    seg_names: Dict[int, str] = {}

    for seg_id in range(k):
        m = labels == seg_id
        if m.sum() == 0:
            continue
        w = weights[m]
        Pm = wmean_cols_nan(P[m], w)
        Em = wmean_cols_nan(E[m], w)
        Gm = wmean_cols_nan(G[m], w)

        order = np.argsort(-Pm)
        top3 = [ARCHETYPES[i] for i in order[:3]]
        bottom = [ARCHETYPES[i] for i in order[-3:]]

        name = make_segment_name(top3[:2])
        seg_names[seg_id] = name
        opis, sugestie, ryzyka = make_segment_profile(top3, bottom)

        seg_prof_rows.append({
            "segment_id": seg_id,
            "liczba": int(m.sum()),
            "waga": float(w.sum()),
            "nazwa_segmentu": name,
            "top3_P": ", ".join(top3),
            "opis": opis,
            "sugestie_komunikacyjne": sugestie,
            "ryzyka": ryzyka
        })

        for i, arch in enumerate(ARCHETYPES):
            seg_rows.append({
                "segment_id": seg_id,
                "liczba": int(m.sum()),
                "waga": float(w.sum()),
                "archetyp": arch,
                "P_mean": float(Pm[i]),
                "E_mean": float(Em[i]) if np.isfinite(Em[i]) else np.nan,
                "G_mean": float(Gm[i]),
            })

    seg_df = pd.DataFrame(seg_rows)
    seg_profile = pd.DataFrame(seg_prof_rows).sort_values("segment_id", ascending=True).reset_index(drop=True)
    return seg_df, seg_profile


def _seg_df_from_ranked_profiles(segs: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Buduje kanoniczną tabelę long segment × archetyp dla P/E/G
    wyłącznie z payloadu już policzonych segmentów.
    """
    rows: List[Dict[str, Any]] = []

    for i, s in enumerate(segs or []):
        pm = _segment_pm_vector(s)

        try:
            em = np.asarray(s.get("Em", []), dtype=float).reshape(-1)
        except Exception:
            em = np.asarray([], dtype=float)

        try:
            gm = np.asarray(s.get("Gm", []), dtype=float).reshape(-1)
        except Exception:
            gm = np.asarray([], dtype=float)

        if em.shape[0] != len(ARCHETYPES):
            em = np.full(len(ARCHETYPES), np.nan, dtype=float)
        else:
            em = np.where(np.isfinite(em), em, np.nan)

        if gm.shape[0] != len(ARCHETYPES):
            gm = np.full(len(ARCHETYPES), np.nan, dtype=float)
        else:
            gm = np.where(np.isfinite(gm), gm, np.nan)

        seg_id = int(s.get("segment_id", i))

        for j, a in enumerate(ARCHETYPES):
            rows.append({
                "segment_id": seg_id,
                "archetyp": a,
                "P_mean": float(pm[j]),
                "E_mean": float(em[j]) if np.isfinite(em[j]) else np.nan,
                "G_mean": float(gm[j]) if np.isfinite(gm[j]) else np.nan,
            })

    return pd.DataFrame(rows)


# =========================
# 14) MAIN
# =========================

def top5_overall_A(A: np.ndarray, weights: np.ndarray, k: int = 5) -> pd.DataFrame:
    """
    A (A1–A18) łącznie – poprawna metryka:
    % = (ważone wygrane archetypu) / (ważona liczba odpowiedzi w parach z tym archetypem) * 100

    Zasada:
    - neutral (dokładnie środek skali) liczy się do mianownika, ale NIE do wygranych
    - lewa strona wygrywa gdy v < A_SCALE_CENTER
    - prawa strona wygrywa gdy v > A_SCALE_CENTER

    To działa bezpiecznie zarówno dla skali 1–5 (center=3) jak i 1–7 (center=4).
    """
    w = np.asarray(weights, dtype=float).reshape(-1)

    wins = {a: 0.0 for a in ARCHETYPES}
    votes = {a: 0.0 for a in ARCHETYPES}

    for j, (_pid, left_arch, right_arch) in enumerate(A_PAIRS):
        v = A[:, j]
        m = np.isfinite(v)
        if not np.any(m):
            continue

        pair_votes = float(w[m].sum())
        votes[left_arch] += pair_votes
        votes[right_arch] += pair_votes

        wins[left_arch] += float(w[m & (v < A_SCALE_CENTER)].sum())
        wins[right_arch] += float(w[m & (v > A_SCALE_CENTER)].sum())

    df = pd.DataFrame({
        "archetyp": list(wins.keys()),
        "%": [
            (wins[a] / votes[a] * 100.0) if votes[a] > 0 else np.nan
            for a in wins.keys()
        ],
    })

    df["%"] = df["%"].round(1)
    df = df.sort_values("%", ascending=False).head(k).reset_index(drop=True)
    return df


# ==============================================================
# 12Z) PREMIUM SEGMENTACJA — rdzeń segmentacji
#      - aktywna ścieżka raportu: ultra premium (weighted k-means na meta-cechach z P)
#      - historyczne helpery zgodnościowe zostają, ale nazewnictwo jest już wspólne
# ==============================================================

def _lca_behavioral_name_from_segment(mask: np.ndarray,
                                      A: np.ndarray, d12: np.ndarray, d13: np.ndarray,
                                      w: np.ndarray,
                                      brand_values: Dict[str, str]) -> Tuple[str, str]:
    """
    Behawioralna etykieta LCA (bez kopiowania nazw z segmentacji psychologicznej).
    Nazwa bazuje na wzorcu odpowiedzi: decyzyjność (A), ton doświadczeń (D12)
    oraz dominujący priorytet (D13).
    """
    w = np.asarray(w, dtype=float).reshape(-1)
    mrow = np.asarray(mask, dtype=bool).reshape(-1)
    if mrow.size == 0 or not np.any(mrow):
        return "„Segment ultra premium”", "„Segment ultra premium”"

    # 1) Decyzyjność z bloku A (odległość od środka skali)
    A_seg = np.asarray(A[mrow], dtype=float)
    if A_seg.size > 0:
        a_vals = np.abs(A_seg.reshape(-1) - float(A_SCALE_CENTER))
        a_w = np.repeat(w[mrow], A_seg.shape[1])
        ok = np.isfinite(a_vals) & np.isfinite(a_w) & (a_w > 0)
        dec_score = float(np.average(a_vals[ok], weights=a_w[ok])) if np.any(ok) else np.nan
    else:
        dec_score = np.nan

    if np.isfinite(dec_score):
        if dec_score >= 1.05:
            dec_label = "Decyzyjni"
        elif dec_score >= 0.70:
            dec_label = "Wyraziści"
        else:
            dec_label = "Wyważeni"
    else:
        dec_label = "Zróżnicowani"

    # 2) Ton doświadczeń z D12 (plus vs minus)
    D_seg = np.asarray(d12[mrow], dtype=float)
    if D_seg.size > 0:
        d_vals = D_seg.reshape(-1)
        d_w = np.repeat(w[mrow], D_seg.shape[1])
        ok = np.isfinite(d_vals) & np.isfinite(d_w) & (d_w > 0) & (d_vals != 0)
        denom = float(d_w[ok].sum()) if np.any(ok) else 0.0
        plus_share = float(d_w[ok & (d_vals > 0)].sum() / (denom + 1e-12) * 100.0) if denom > 0 else np.nan
    else:
        plus_share = np.nan

    if np.isfinite(plus_share):
        if plus_share >= 57.0:
            tone_label = "afirmujący"
        elif plus_share <= 43.0:
            tone_label = "krytyczni"
        else:
            tone_label = "ambiwalentni"
    else:
        tone_label = "mieszani"

    # 3) Dominujący priorytet z D13 (żeby nazwa w trybie values miała sens)
    d13_seg = np.asarray(d13[mrow], dtype=float).reshape(-1)
    w_seg = np.asarray(w[mrow], dtype=float).reshape(-1)
    ok_idx = np.isfinite(d13_seg) & np.isfinite(w_seg) & (w_seg > 0) & (d13_seg >= 0)
    dom_arch = None
    focus_label = "wielowątkowi"
    if np.any(ok_idx):
        counts = np.zeros(len(ARCHETYPES), dtype=float)
        idxs = d13_seg[ok_idx].astype(int)
        ws = w_seg[ok_idx]
        for ii, ww in zip(idxs, ws):
            if 0 <= int(ii) < len(ARCHETYPES):
                counts[int(ii)] += float(ww)
        if counts.sum() > 0:
            dom_i = int(np.argmax(counts))
            dom_arch = ARCHETYPES[dom_i]
            dom_share = float(counts[dom_i] / (counts.sum() + 1e-12) * 100.0)
            if dom_share >= 45.0:
                focus_label = "jednowątkowi"
            elif dom_share >= 34.0:
                focus_label = "skoncentrowani"

    base = f"{dec_label} {tone_label}"

    if dom_arch is not None:
        lead_a = _segment_brand_title(dom_arch, None, brand_values, mode="arche").replace("„", "").replace("”", "")
        lead_v = _segment_brand_title(dom_arch, None, brand_values, mode="values").replace("„", "").replace("”", "")
        name_arche = f"„{base} · {lead_a} ({focus_label})”"
        name_values = f"„{base} · {lead_v} ({focus_label})”"
    else:
        name_arche = f"„{base} ({focus_label})”"
        name_values = name_arche

    return name_arche, name_values


def _apply_lca_behavioral_names(segs: List[Dict[str, Any]],
                                labels_raw: np.ndarray,
                                A: np.ndarray, d12: np.ndarray, d13: np.ndarray,
                                w: np.ndarray,
                                brand_values: Dict[str, str]) -> List[Dict[str, Any]]:
    """Nadpisuje nazwy segmentów LCA nazwami behawioralnymi (ranking Seg_1.. zostaje bez zmian)."""
    if not segs:
        return segs
    labels_raw = np.asarray(labels_raw, dtype=int).reshape(-1)
    for s in segs:
        sid = int(s.get("segment_id", -1))
        mask = (labels_raw == sid)
        nm_a, nm_v = _lca_behavioral_name_from_segment(mask, A=A, d12=d12, d13=d13, w=w, brand_values=brand_values)
        s["name_marketing_arche"] = nm_a
        s["name_marketing_values"] = nm_v
        s["name_arche"] = nm_a.replace("„", "").replace("”", "")
    return segs


def _segment_female_share_pct(s: Dict[str, Any]) -> Optional[float]:
    """
    Zwraca % kobiet w segmencie na bazie tej samej tabeli demograficznej,
    którą pokazujemy w karcie segmentu.
    """
    try:
        demo_rows = _segment_demography_rows(s)
    except Exception:
        demo_rows = []

    for r in demo_rows:
        zm = str(r.get("zmienna", "")).strip().lower()
        kat = str(r.get("kategoria", "")).strip().lower()
        if zm == "płeć" and kat == "kobieta":
            try:
                return float(r.get("pct_seg", 0.0))
            except Exception:
                return None
    return None


def _segment_apply_feminine_form(name: str, female_share_pct: Optional[float]) -> str:
    """
    Gdy kobiety stanowią wyraźną większość (>= 60%), podmieniamy tylko
    sprawdzone, pełne nazwy marketingowe. Nie ruszamy nazw technicznych typu
    "Bohater / Twórca / Władca".
    """
    txt = str(name or "").strip()
    if not txt:
        return txt

    try:
        female_share = float(female_share_pct)
    except Exception:
        female_share = -1.0

    if female_share < 60.0:
        return txt

    fem_map = {
        "Stabilni opiekunowie": "Stabilne opiekunki",
        "Przejrzyści opiekunowie": "Przejrzyste opiekunki",
        "Sprawczy innowatorzy": "Sprawcze innowatorki",
        "Energetyczni reformatorzy": "Energetyczne reformatorki",
        "Niezależni reformatorzy": "Niezależne reformatorki",
        "Przejrzyści strażnicy": "Przejrzyste strażniczki",
        "Autonomiczni konserwatyści": "Autonomiczne konserwatystki",
        "Ambitni hedoniści": "Ambitne hedonistki",
        "Życzliwi tradycjonaliści": "Życzliwe tradycjonalistki",
        "Ulegli materialiści": "Uległe materialistki",
        "Kreatywni progresywiści": "Kreatywne progresywistki",
    }
    return fem_map.get(txt, txt)


def _segment_name_pair(s: Dict[str, Any]) -> Tuple[str, str]:
    """
    Zwraca parę nazw:
    - [0] nazwa archetypowa
    - [1] nazwa wartościowa
    Zawsze preferuje wersje marketingowe, jeśli istnieją.

    Dodatkowo: jeśli w segmencie kobiety stanowią co najmniej 60%,
    próbujemy użyć żeńskiej formy gotowej nazwy marketingowej.
    """
    name_arche = str(
        s.get("name_marketing_arche")
        or s.get("name_arche")
        or s.get("segment_label")
        or s.get("segment")
        or "Segment"
    )
    name_values = str(
        s.get("name_marketing_values")
        or s.get("name_values")
        or name_arche
    )

    female_share_pct = _segment_female_share_pct(s)
    name_arche = _segment_apply_feminine_form(name_arche, female_share_pct)
    name_values = _segment_apply_feminine_form(name_values, female_share_pct)
    # Nazwa segmentu ma być spójna w całym raporcie (archetypy i wartości).
    name_values = name_arche
    return name_arche, name_values


def _segment_unique_suffix(third_arch: Optional[str],
                           brand_values: Optional[Dict[str, str]] = None,
                           mode: str = "arche") -> str:
    """
    Krótki doprecyzowujący sufiks dla nazw zduplikowanych.
    Dzięki temu dwa różne segmenty nie kończą z identycznym brandingiem.
    """
    third_arch = str(third_arch or "").strip()
    brand_values = brand_values or {}

    if not third_arch:
        return "II"

    if mode == "values":
        return str(brand_values.get(third_arch, third_arch))

    suffix_map = {
        "Władca": "sprawczości",
        "Mędrzec": "racjonalności",
        "Buntownik": "buntu",
        "Twórca": "kreacji",
        "Bohater": "odwagi",
        "Odkrywca": "zmiany",
        "Towarzysz": "wspólnoty",
        "Niewinny": "przejrzystości",
        "Czarodziej": "wizji",
        "Opiekun": "opieki",
        "Kochanek": "relacji",
        "Błazen": "energii",
    }
    return suffix_map.get(third_arch, third_arch)


def _ensure_unique_segment_names(segs: List[Dict[str, Any]],
                                 brand_values: Dict[str, str],
                                 mode_values: bool = False) -> List[Dict[str, Any]]:
    """
    Nadaje segmentom unikalne, marketingowe nazwy.

    Zasada:
    - najpierw próbujemy nazwy podstawowej,
    - jeśli jest duplikat, sięgamy po alternatywne nazwy marketingowe
      dla danego wzorca,
    - dopiero na samym końcu dokładamy numer techniczny.
    """
    segs = list(segs or [])
    if not segs:
        return segs

    # Alternatywy dla najczęstszych wzorców.
    # Kolejność = priorytet użycia.
    alt_pair_names = {
        ("Bohater", "Twórca"): [
            "Sprawczy innowatorzy",
            "Kreatywni sprawcy",
            "Wizjonerscy innowatorzy",
            "Dynamiczni twórcy",
        ],
        ("Twórca", "Bohater"): [
            "Sprawczy innowatorzy",
            "Kreatywni sprawcy",
            "Wizjonerscy innowatorzy",
            "Dynamiczni twórcy",
        ],

        ("Bohater", "Czarodziej"): [
            "Wizjonerscy innowatorzy",
            "Kreatywni reformatorzy",
            "Sprawczy wizjonerzy",
            "Inspirujący sprawcy",
        ],
        ("Czarodziej", "Bohater"): [
            "Wizjonerscy innowatorzy",
            "Kreatywni reformatorzy",
            "Sprawczy wizjonerzy",
            "Inspirujący sprawcy",
        ],

        ("Bohater", "Buntownik"): [
            "Zaangażowani reformatorzy",
            "Obywatelscy reformatorzy",
            "Antysystemowi sprawcy",
            "Mobilizujący reformatorzy",
        ],
        ("Buntownik", "Bohater"): [
            "Zaangażowani reformatorzy",
            "Obywatelscy reformatorzy",
            "Antysystemowi sprawcy",
            "Mobilizujący reformatorzy",
        ],

        ("Odkrywca", "Buntownik"): [
            "Niezależni reformatorzy",
            "Swobodni reformatorzy",
            "Autonomiczni reformatorzy",
            "Niekonwencjonalni reformatorzy",
        ],
        ("Buntownik", "Odkrywca"): [
            "Niezależni reformatorzy",
            "Swobodni reformatorzy",
            "Autonomiczni reformatorzy",
            "Niekonwencjonalni reformatorzy",
        ],

        ("Odkrywca", "Towarzysz"): [
            "Energetyczni reformatorzy",
            "Wspólnotowi reformatorzy",
            "Społeczni reformatorzy",
            "Mobilizujący reformatorzy",
        ],
        ("Towarzysz", "Odkrywca"): [
            "Energetyczni reformatorzy",
            "Wspólnotowi reformatorzy",
            "Społeczni reformatorzy",
            "Mobilizujący reformatorzy",
        ],

        ("Buntownik", "Towarzysz"): [
            "Zaangażowani reformatorzy",
            "Obywatelscy reformatorzy",
            "Wspólnotowi reformatorzy",
            "Mobilizujący reformatorzy",
        ],
        ("Towarzysz", "Buntownik"): [
            "Zaangażowani reformatorzy",
            "Obywatelscy reformatorzy",
            "Wspólnotowi reformatorzy",
            "Mobilizujący reformatorzy",
        ],

        ("Władca", "Opiekun"): [
            "Przejrzyści opiekunowie",
            "Stabilni opiekunowie",
            "Strażnicy ładu",
            "Opiekuńczy zarządcy",
        ],
        ("Opiekun", "Władca"): [
            "Przejrzyści opiekunowie",
            "Stabilni opiekunowie",
            "Strażnicy ładu",
            "Opiekuńczy zarządcy",
        ],

        ("Władca", "Niewinny"): [
            "Przejrzyści opiekunowie",
            "Strażnicy przejrzystości",
            "Łagodni strażnicy",
            "Stabilni opiekunowie",
        ],
        ("Niewinny", "Władca"): [
            "Przejrzyści opiekunowie",
            "Strażnicy przejrzystości",
            "Łagodni strażnicy",
            "Stabilni opiekunowie",
        ],

        ("Mędrzec", "Kochanek"): [
            "Empatyczni analitycy",
            "Uważni gospodarze",
            "Relacyjni analitycy",
            "Wrażliwi moderatorzy",
        ],
        ("Kochanek", "Mędrzec"): [
            "Empatyczni analitycy",
            "Uważni gospodarze",
            "Relacyjni analitycy",
            "Wrażliwi moderatorzy",
        ],

        ("Mędrzec", "Błazen"): [
            "Przenikliwi optymiści",
            "Błyskotliwi obserwatorzy",
            "Lekcy analitycy",
            "Inteligentni improwizatorzy",
        ],
        ("Błazen", "Mędrzec"): [
            "Przenikliwi optymiści",
            "Błyskotliwi obserwatorzy",
            "Lekcy analitycy",
            "Inteligentni improwizatorzy",
        ],
    }

    # Dodatkowe warianty zależne od trzeciego archetypu.
    alt_by_third = {
        (("Bohater", "Twórca"), "Czarodziej"): [
            "Wizjonerscy innowatorzy",
            "Kreatywni reformatorzy",
        ],
        (("Bohater", "Twórca"), "Mędrzec"): [
            "Strategiczni innowatorzy",
            "Racjonalni innowatorzy",
        ],
        (("Władca", "Opiekun"), "Niewinny"): [
            "Przejrzyści opiekunowie",
            "Strażnicy przejrzystości",
        ],
        (("Odkrywca", "Buntownik"), "Towarzysz"): [
            "Niezależni reformatorzy",
            "Zaangażowani reformatorzy",
        ],
        (("Odkrywca", "Towarzysz"), "Buntownik"): [
            "Energetyczni reformatorzy",
            "Wspólnotowi reformatorzy",
        ],
        (("Buntownik", "Towarzysz"), "Odkrywca"): [
            "Zaangażowani reformatorzy",
            "Obywatelscy reformatorzy",
        ],
    }

    def _unique_append(bucket: List[str], value: str) -> None:
        v = str(value or "").strip()
        if v and v not in bucket:
            bucket.append(v)

    def _roman_suffix(n: int) -> str:
        roman = {
            2: "II",
            3: "III",
            4: "IV",
            5: "V",
            6: "VI",
            7: "VII",
            8: "VIII",
            9: "IX",
            10: "X",
        }
        return roman.get(int(n), str(int(n)))

    def _name_candidates_for(raw_top3: List[str]) -> List[str]:
        raw = [str(x).strip() for x in (raw_top3 or []) if str(x).strip()]
        marketing_base = str(
            _make_marketing_name_from_top3(
                raw,
                brand_values,
                mode="values" if mode_values else "arche"
            ) or ""
        ).strip() or "Segment"

        out: List[str] = []
        _unique_append(out, marketing_base)

        # W trybie wartości nie dokładamy dziwnych fallbacków —
        # tylko czytelne warianty numerowane.
        if mode_values:
            for idx in range(2, 9):
                _unique_append(out, f"{marketing_base} {_roman_suffix(idx)}")
            return out or ["Segment"]

        pair = tuple(raw[:2]) if len(raw) >= 2 else tuple(raw)
        third = raw[2] if len(raw) >= 3 else ""

        # Najpierw warianty dla pary
        for cand in alt_pair_names.get(pair, []):
            _unique_append(out, cand)

        # Potem warianty specyficzne dla pełnego wzorca TOP3
        if third:
            for cand in alt_by_third.get((pair, third), []):
                _unique_append(out, cand)

        # Na końcu alternatywy po nazwie bazowej, bez wracania do surowego TOP3
        generic_alt_by_base = {
            "Sprawczy innowatorzy": [
                "Skuteczni modernizatorzy",
                "Dynamiczni kreatorzy",
                "Impulsowi modernizatorzy",
            ],
            "Przejrzyści opiekunowie": [
                "Transparentni opiekunowie",
                "Uporządkowani opiekunowie",
                "Rzetelni opiekunowie",
            ],
            "Stabilni opiekunowie": [
                "Spokojni opiekunowie",
                "Odpowiedzialni opiekunowie",
                "Porządni opiekunowie",
            ],
            "Niezależni reformatorzy": [
                "Zaangażowani reformatorzy",
                "Obywatelscy reformatorzy",
                "Niekonwencjonalni reformatorzy",
            ],
            "Sprawczy reformatorzy": [
                "Ofensywni reformatorzy",
                "Zdecydowani reformatorzy",
                "Dynamiczni reformatorzy",
            ],
            "Empatyczni analitycy": [
                "Wrażliwi stratedzy",
                "Uważni stratedzy",
                "Empatyczni stratedzy",
            ],
            "Przejrzyści stratedzy": [
                "Precyzyjni stratedzy",
                "Uporządkowani stratedzy",
                "Racjonalni opiekunowie",
            ],
        }

        for cand in generic_alt_by_base.get(marketing_base, []):
            _unique_append(out, cand)

        # Ostateczny, neutralny fallback — numerowana wersja nazwy marketingowej,
        # nigdy surowe "Twórca / Władca".
        for idx in range(2, 9):
            _unique_append(out, f"{marketing_base} {_roman_suffix(idx)}")

        return out or ["Segment"]

    used_names = set()

    # Najpierw zachowujemy raw_top3
    for s in segs:
        raw_top3 = s.get("raw_top3")
        if not raw_top3:
            raw_top3 = list(s.get("top3_names", []) or [])
        raw_top3 = [str(x).strip() for x in raw_top3 if str(x).strip()]
        s["raw_top3"] = raw_top3

    # Potem nadajemy unikalne nazwy
    for idx, s in enumerate(segs, start=1):
        raw_top3 = list(s.get("raw_top3", []) or [])
        candidates = _name_candidates_for(raw_top3)

        chosen = None
        for cand in candidates:
            if cand not in used_names:
                chosen = cand
                break

        if chosen is None:
            base = candidates[0] if candidates else "Segment"
            nr = 2
            chosen = f"{base} ({nr})"
            while chosen in used_names:
                nr += 1
                chosen = f"{base} ({nr})"

        used_names.add(chosen)
        s["segment_name"] = chosen

    return segs


def _segment_demography_rows(s: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Normalizuje demografię segmentu do jednego formatu:
    zmienna / kategoria / pct_seg / pct_all / lift_pp
    """

    def _f(x: Any, default: float = 0.0) -> float:
        try:
            return float(x)
        except Exception:
            return default

    demo_src = s.get("demografia_rows", None)
    if demo_src is None:
        demo_src = s.get("demografia_table", None)

    if isinstance(demo_src, pd.DataFrame):
        recs = demo_src.to_dict("records")
    elif isinstance(demo_src, list):
        recs = demo_src
    else:
        recs = []

    out: List[Dict[str, Any]] = []
    for r in recs:
        if not isinstance(r, dict):
            continue

        kat = r.get("kategoria", None)
        if kat is None or str(kat).strip() == "":
            kat = r.get("dominanta", "")

        out.append({
            "zmienna": str(r.get("zmienna", r.get("wymiar", ""))),
            "kategoria": str(kat),
            "pct_seg": _f(r.get("pct_seg", r.get("udzial_segment_pct", 0.0))),
            "pct_all": _f(r.get("pct_all", r.get("udzial_ogol_pct", 0.0))),
            "lift_pp": _f(r.get("lift_pp", 0.0)),
        })

    return out


def _build_segment_payload(*,
                           sid: int,
                           seg_rank: Optional[int],
                           n_seg: int,
                           share_pct: float,
                           top3_arche: List[str],
                           bottom_arche: List[str],
                           brand_values: Dict[str, str],

                           # PROFIL segmentu (surowe średnie)
                           Pm: Any = None,
                           Em: Any = None,
                           Gm: Any = None,

                           # RÓŻNICE vs średnia próby (Δ)
                           deltaP: Any = None,
                           deltaE: Any = None,
                           deltaG: Any = None,

                           usefulness: float = 0.0,
                           opis: Any = None,
                           sugestie: Any = None,
                           ryzyka: Any = None,
                           demografia_rows: Optional[List[Dict[str, Any]]] = None,
                           name_marketing_arche: Optional[str] = None,
                           name_marketing_values: Optional[str] = None) -> Dict[str, Any]:
    """
    Jedna kanoniczna struktura segmentu dla HTML / CSV / map / legend.

    Uwaga:
    - Segmenty budujemy na surowych średnich (Pm) i to jest „prawda” do kart i macierzy.
    - ΔP/ΔE/ΔG zostawiamy pomocniczo (np. do analiz porównawczych), ale nie jest to baza opisów.
    """
    rank = int(sid if seg_rank is None else seg_rank)
    segment_label = f"Seg_{rank + 1}"

    top3_arche = [str(x) for x in (top3_arche or []) if str(x).strip()]
    bottom_arche = [str(x) for x in (bottom_arche or []) if str(x).strip()]
    top3_values = [str(brand_values.get(a, a)) for a in top3_arche[:3]]

    demo_rows = list(demografia_rows or [])
    demo_short = [
        f'{str(r.get("zmienna", ""))}: {str(r.get("kategoria", ""))} ({float(r.get("lift_pp", 0.0)):+.1f} pp)'
        for r in demo_rows[:3]
    ]

    base_name_arche = _segment_brand_title(
        top3_arche[0] if len(top3_arche) >= 1 else None,
        top3_arche[1] if len(top3_arche) >= 2 else None,
        brand_values,
        mode="arche"
    ) if top3_arche else segment_label

    base_name_values = _segment_brand_title(
        top3_arche[0] if len(top3_arche) >= 1 else None,
        top3_arche[1] if len(top3_arche) >= 2 else None,
        brand_values,
        mode="values"
    ) if top3_arche else segment_label

    name_arche_final = str(base_name_arche)
    name_values_final = str(base_name_arche)

    marketing_arche_final = str(name_marketing_arche or name_arche_final)
    marketing_values_final = str(name_marketing_arche or name_arche_final)

    payload = {
        "segment_id": int(sid),
        "segment_rank": int(rank),
        "segment_label": segment_label,

        # compat
        "segment": segment_label,

        "n": int(n_seg),
        "share_pct": float(share_pct),

        "name_arche": name_arche_final,
        "name_values": name_values_final,
        "name_marketing_arche": marketing_arche_final,
        "name_marketing_values": marketing_values_final,

        "top3_arche": top3_arche[:3],
        "top3_values": top3_values[:3],

        # compat
        "top3": top3_arche[:3],

        "bottom_arche": bottom_arche[:3],

        # --- SUROWE ŚREDNIE (to jest baza spójności kart vs macierzy) ---
        "Pm": list(np.asarray(Pm, dtype=float)) if Pm is not None else [],
        "Pm_share_pct": _pm_profile_share_pct(Pm) if Pm is not None else [0.0] * len(ARCHETYPES),
        "Em": list(np.asarray(Em, dtype=float)) if Em is not None else [],
        "Gm": list(np.asarray(Gm, dtype=float)) if Gm is not None else [],

        # --- RÓŻNICE vs średnia próby (pomocniczo) ---
        "deltaP": list(np.asarray(deltaP, dtype=float)) if deltaP is not None else [],
        "deltaE": list(np.asarray(deltaE, dtype=float)) if deltaE is not None else [],
        "deltaG": list(np.asarray(deltaG, dtype=float)) if deltaG is not None else [],

        "usefulness": float(usefulness),

        "opis": opis if opis is not None else "",
        "sugestie": sugestie if sugestie is not None else "",
        "ryzyka": ryzyka if ryzyka is not None else "",

        "demografia_rows": demo_rows,

        # compat
        "demografia_table": demo_rows,
        "demografia": demo_short,
    }

    return payload


def _segment_pm_vector(s: Dict[str, Any]) -> np.ndarray:
    """
    Jedyny kanoniczny nośnik profilu segmentu dla kart / macierzy / porównań.
    Źródło prawdy = surowe Pm zapisane w payloadzie segmentu.
    """
    try:
        pm = np.asarray(s.get("Pm", []), dtype=float)
    except Exception:
        pm = np.asarray([], dtype=float)

    if pm.shape[0] != len(ARCHETYPES):
        return np.zeros(len(ARCHETYPES), dtype=float)

    pm = np.where(np.isfinite(pm), pm, 0.0)
    return pm


SEG_MARKETING = {
    "Władca": "„Strażnicy ładu”",
    "Bohater": "„Ludzie sprawczości”",
    "Mędrzec": "„Rozważni analitycy”",
    "Opiekun": "„Obrońcy bezpieczeństwa”",
    "Kochanek": "„Ambasadorzy jakości życia”",
    "Błazen": "„Rzecznicy lekkości”",
    "Twórca": "„Projektanci nowego”",
    "Odkrywca": "„Poszukiwacze zmiany”",
    "Czarodziej": "„Autorzy przełomu”",
    "Towarzysz": "„Budowniczowie wspólnoty”",
    "Niewinny": "„Strażnicy spokoju”",
    "Buntownik": "„Impuls odnowy”",
}


def _segment_brand_title(primary: Optional[str],
                         secondary: Optional[str],
                         brand_values: Dict[str, str],
                         mode: str = "arche") -> str:
    """
    Krótka, jednoznaczna nazwa segmentu.
    Nie używamy już rozwlekłych form typu „w duchu ...”.
    """

    primary = str(primary or "").strip()
    secondary = str(secondary or "").strip()
    mode_values = (str(mode).lower() == "values")

    if mode_values:
        left = str(brand_values.get(primary, primary)).strip()
        right = str(brand_values.get(secondary, secondary)).strip()
    else:
        left = primary
        right = secondary

    if not left:
        return "Segment"

    if not right or right == left:
        return left

    return f"{left} + {right}"


_CORE_METRY_COL_ORDER = ["M_PLEC", "M_WIEK", "M_WYKSZT", "M_ZAWOD", "M_MATERIAL"]
_CORE_METRY_VAR_LABELS = {
    "M_PLEC": "Płeć",
    "M_WIEK": "Wiek",
    "M_WYKSZT": "Wykształcenie",
    "M_ZAWOD": "Status zawodowy",
    "M_MATERIAL": "Sytuacja materialna",
}
_DEMO_CORE_VAR_ORDER = [
    "Płeć",
    "Wiek",
    "Wykształcenie",
    "Status zawodowy",
    "Sytuacja materialna",
]
_DEMO_CORE_CAT_ORDER: Dict[str, List[str]] = {
    "Płeć": ["kobieta", "mężczyzna"],
    "Wiek": ["15-39", "40-59", "60+", "60 i więcej"],
    "Wykształcenie": [
        "podst./gim./zaw.",
        "podstawowe, gimnazjalne, zasadnicze zawodowe",
        "średnie",
        "wyższe",
    ],
    "Status zawodowy": [
        "prac. umysłowy",
        "pracownik umysłowy",
        "prac. fizyczny",
        "pracownik fizyczny",
        "własna firma",
        "prowadzę własną firmę",
        "student/uczeń",
        "bezrobotny",
        "rencista/emeryt",
        "inna",
        "inna (jaka?)",
    ],
    "Sytuacja materialna": [
        "bardzo dobra",
        "powodzi mi się bardzo dobrze",
        "raczej dobra",
        "powodzi mi się raczej dobrze",
        "przeciętna",
        "powodzi mi się przeciętnie, średnio",
        "raczej zła",
        "powodzi mi się raczej źle",
        "bardzo zła",
        "powodzi mi się bardzo źle, jestem w ciężkiej sytuacji materialnej",
        "odmowa",
        "odmawiam udzielenia odpowiedzi",
    ],
}
_DEMO_VAR_ICON_MAP: Dict[str, str] = {
    "płeć": "👫",
    "wiek": "⌛",
    "wykształcenie": "🎓",
    "status zawodowy": "💼",
    "sytuacja materialna": "💰",
}
_DEMO_CAT_ICON_MAP: Dict[str, str] = {
    "kobieta": "👩",
    "mężczyzna": "👨",
    "15-39": "🧑",
    "40-59": "🧑‍💼",
    "60+": "🧓",
    "60 i więcej": "🧓",
    "podst./gim./zaw.": "🛠️",
    "podstawowe, gimnazjalne, zasadnicze zawodowe": "🛠️",
    "średnie": "📘",
    "wyższe": "🎓",
    "prac. umysłowy": "🧠",
    "pracownik umysłowy": "🧠",
    "prac. fizyczny": "🛠️",
    "pracownik fizyczny": "🛠️",
    "własna firma": "🏢",
    "prowadzę własną firmę": "🏢",
    "student/uczeń": "🧑‍🎓",
    "bezrobotny": "🔎",
    "rencista/emeryt": "🌿",
    "inna": "🧩",
    "inna (jaka?)": "🧩",
    "bardzo dobra": "😄",
    "powodzi mi się bardzo dobrze": "😄",
    "raczej dobra": "🙂",
    "powodzi mi się raczej dobrze": "🙂",
    "przeciętna": "😐",
    "powodzi mi się przeciętnie, średnio": "😐",
    "raczej zła": "🙁",
    "powodzi mi się raczej źle": "🙁",
    "bardzo zła": "😟",
    "powodzi mi się bardzo źle, jestem w ciężkiej sytuacji materialnej": "😟",
    "odmowa": "🤐",
    "odmawiam udzielenia odpowiedzi": "🤐",
}

# Dynamiczna metryczka z settings.json (gdy dostępna).
_DYN_METRY_COL_ORDER: List[str] = []
_DYN_METRY_VAR_LABEL_BY_COL: Dict[str, str] = {}
_DYN_METRY_VAR_ICON_BY_VAR_NK: Dict[str, str] = {}
_DYN_METRY_CAT_ORDER_BY_COL: Dict[str, List[str]] = {}
_DYN_METRY_CAT_ORDER_BY_VAR_NK: Dict[str, List[str]] = {}
_DYN_METRY_CAT_ICON_BY_VAR_CAT_NK: Dict[Tuple[str, str], str] = {}

_METRY_AUX_SUFFIX_TOKENS: set[str] = {
    "OTHER",
    "INNA",
    "INNE",
    "OTWARTA",
    "OPEN",
    "OPEN_TEXT",
    "TEXT",
    "TXT",
    "COMMENT",
    "KOMENTARZ",
    "DESC",
    "OPIS",
    "JAKA",
}


def _is_aux_metry_column(col_name: Any) -> bool:
    cu = str(col_name or "").strip().upper()
    if not cu.startswith("M_"):
        return False
    # Kolumny jawnie skonfigurowane w metryczce traktujemy jako docelowe.
    if cu in _DYN_METRY_COL_ORDER:
        return False
    parts = [p for p in cu.split("_") if p]
    if len(parts) <= 2:
        return False
    suffix_tokens = set(parts[2:])
    return bool(suffix_tokens & _METRY_AUX_SUFFIX_TOKENS)


def _set_dynamic_metry_schema_from_config(raw_cfg: Any) -> None:
    global _DYN_METRY_COL_ORDER
    global _DYN_METRY_VAR_LABEL_BY_COL
    global _DYN_METRY_VAR_ICON_BY_VAR_NK
    global _DYN_METRY_CAT_ORDER_BY_COL
    global _DYN_METRY_CAT_ORDER_BY_VAR_NK
    global _DYN_METRY_CAT_ICON_BY_VAR_CAT_NK

    _DYN_METRY_COL_ORDER = []
    _DYN_METRY_VAR_LABEL_BY_COL = {}
    _DYN_METRY_VAR_ICON_BY_VAR_NK = {}
    _DYN_METRY_CAT_ORDER_BY_COL = {}
    _DYN_METRY_CAT_ORDER_BY_VAR_NK = {}
    _DYN_METRY_CAT_ICON_BY_VAR_CAT_NK = {}

    cfg = dict(raw_cfg or {}) if isinstance(raw_cfg, dict) else {}
    questions = cfg.get("questions")
    if not isinstance(questions, list):
        return

    def _nk(v: Any) -> str:
        return " ".join(str(v or "").split()).strip().lower()

    for q in list(questions):
        if not isinstance(q, dict):
            continue
        col = str(q.get("db_column") or q.get("id") or "").strip().upper()
        if not col.startswith("M_"):
            continue
        if col not in _DYN_METRY_COL_ORDER:
            _DYN_METRY_COL_ORDER.append(col)
        prompt = str(q.get("prompt") or "").strip()
        table_label = str(q.get("table_label") or prompt or col).strip()
        _DYN_METRY_VAR_LABEL_BY_COL[col] = table_label
        var_nk = _nk(table_label)
        if var_nk:
            _DYN_METRY_VAR_ICON_BY_VAR_NK[var_nk] = str(q.get("variable_emoji") or "").strip()

        opts = q.get("options") if isinstance(q.get("options"), list) else []
        seen_codes: set[str] = set()
        ordered_codes: List[str] = []
        for opt in opts:
            if not isinstance(opt, dict):
                continue
            code = str(opt.get("code") or opt.get("label") or "").strip()
            if not code:
                continue
            ckey = _nk(code)
            if ckey in seen_codes:
                continue
            seen_codes.add(ckey)
            ordered_codes.append(code)
            icon = str(opt.get("value_emoji") or "").strip()
            if icon in {"🏙️", "🏙", "🌆"}:
                icon = "🏬"
            if var_nk:
                _DYN_METRY_CAT_ICON_BY_VAR_CAT_NK[(var_nk, ckey)] = icon
        if ordered_codes:
            _DYN_METRY_CAT_ORDER_BY_COL[col] = list(ordered_codes)
            if var_nk:
                _DYN_METRY_CAT_ORDER_BY_VAR_NK[var_nk] = list(ordered_codes)


def _demo_nk(x: Any) -> str:
    return " ".join(str(x or "").split()).strip().lower()


def _demo_pick_var_icon(var_label: str) -> str:
    nk = _demo_nk(var_label)
    if nk in _DYN_METRY_VAR_ICON_BY_VAR_NK:
        return str(_DYN_METRY_VAR_ICON_BY_VAR_NK.get(nk) or "")
    icon = _DEMO_VAR_ICON_MAP.get(nk)
    if icon:
        return icon
    if any(k in nk for k in ["obszar", "miejsce", "lokaliz", "zamiesz", "wieś", "wies", "miasto"]):
        return "🗺️"
    if any(k in nk for k in ["pogląd", "poglad", "pogl", "orientac", "ideolog", "politycz"]):
        return "⚖️"
    if any(k in nk for k in ["relig", "wiar"]):
        return "⛪"
    if any(k in nk for k in ["doch", "zarob", "przych", "material"]):
        return "💸"
    if any(k in nk for k in ["rodzin", "dzieci", "gospod"]):
        return "🏠"
    return "📌"


def _demo_pick_cat_icon(var_label: str, cat_label: str) -> str:
    nk_cat = _demo_nk(cat_label)
    nk_var = _demo_nk(var_label)
    dyn_icon = _DYN_METRY_CAT_ICON_BY_VAR_CAT_NK.get((nk_var, nk_cat))
    if dyn_icon is not None:
        dyn_txt = str(dyn_icon or "")
        if dyn_txt in {"🏙️", "🏙", "🌆"}:
            return "🏬"
        return dyn_txt
    icon = _DEMO_CAT_ICON_MAP.get(nk_cat)
    if icon:
        return icon
    if nk_cat in {"tak", "zdecydowanie tak", "raczej tak"}:
        return "✅"
    if nk_cat in {"nie", "zdecydowanie nie", "raczej nie"}:
        return "❌"
    if "trudno powiedzieć" in nk_cat:
        return "🤷"
    if "nie wiem" in nk_cat:
        return "❓"
    if any(k in nk_var for k in ["obszar", "miejsce", "zamiesz", "lokaliz"]):
        if "miast" in nk_cat:
            return "🏬"
        if "wieś" in nk_cat or "wies" in nk_cat:
            return "🌾"
    if "wiek" in nk_var:
        if re.search(r"\b60\b", nk_cat):
            return "🧓"
        if "40" in nk_cat or "59" in nk_cat:
            return "🧑‍💼"
        if "15" in nk_cat or "39" in nk_cat:
            return "🧑"
    return _demo_pick_var_icon(var_label)


def _demo_merge_category_order(var_label: str, cats_present: List[str]) -> List[str]:
    ordered: List[str] = []
    seen: set[str] = set()
    var_nk = _demo_nk(var_label)
    for cat in list(_DYN_METRY_CAT_ORDER_BY_VAR_NK.get(var_nk, [])):
        nk = _demo_nk(cat)
        if nk in seen:
            continue
        if any(_demo_nk(c) == nk for c in cats_present):
            ordered.append(str(cat))
            seen.add(nk)
    for cat in list(_DEMO_CORE_CAT_ORDER.get(str(var_label), [])):
        nk = _demo_nk(cat)
        if nk in seen:
            continue
        if any(_demo_nk(c) == nk for c in cats_present):
            ordered.append(str(cat))
            seen.add(nk)
    for cat in cats_present:
        nk = _demo_nk(cat)
        if nk in seen:
            continue
        ordered.append(str(cat))
        seen.add(nk)
    return ordered


def _build_demo_schema_from_rows(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    grouped: Dict[str, List[str]] = {}
    var_seen_order: List[str] = []
    for r in list(rows or []):
        if not isinstance(r, dict):
            continue
        var_label = str(r.get("zmienna", "")).strip()
        cat_label = str(r.get("kategoria", "")).strip()
        if not var_label or not cat_label:
            continue
        if var_label not in grouped:
            grouped[var_label] = []
            var_seen_order.append(var_label)
        grouped[var_label].append(cat_label)

    var_order: List[str] = []
    seen_var: set[str] = set()
    for core_var in _DEMO_CORE_VAR_ORDER:
        if core_var in grouped and core_var not in seen_var:
            var_order.append(core_var)
            seen_var.add(core_var)
    for var_label in var_seen_order:
        if var_label not in seen_var:
            var_order.append(var_label)
            seen_var.add(var_label)

    cat_order: Dict[str, List[str]] = {}
    for var_label in var_order:
        cats = grouped.get(var_label, [])
        unique_cats: List[str] = []
        seen_cat: set[str] = set()
        for cat in cats:
            nk = _demo_nk(cat)
            if nk in seen_cat:
                continue
            seen_cat.add(nk)
            unique_cats.append(str(cat))
        cat_order[var_label] = _demo_merge_category_order(var_label, unique_cats)

    var_icons = {str(v).upper(): _demo_pick_var_icon(v) for v in var_order}
    cat_icons: Dict[str, str] = {}
    for var_label in var_order:
        for cat in cat_order.get(var_label, []):
            nk = _demo_nk(cat)
            if nk in cat_icons:
                continue
            cat_icons[nk] = _demo_pick_cat_icon(var_label, cat)

    return {
        "var_order": var_order,
        "cat_order": cat_order,
        "var_icons": var_icons,
        "cat_icons": cat_icons,
    }


def _build_metry_demo_schema(metry: Optional[pd.DataFrame]) -> Dict[str, Any]:
    if metry is None or len(metry) == 0:
        if _DYN_METRY_COL_ORDER:
            var_order = []
            cat_order: Dict[str, List[str]] = {}
            for col in _DYN_METRY_COL_ORDER:
                label = _metry_var_label(col)
                if label not in var_order:
                    var_order.append(label)
                cat_order[label] = list(_DYN_METRY_CAT_ORDER_BY_COL.get(col, []))
        else:
            var_order = list(_DEMO_CORE_VAR_ORDER)
            cat_order = {k: list(v) for k, v in _DEMO_CORE_CAT_ORDER.items()}
    else:
        var_order = []
        cat_order: Dict[str, List[str]] = {}
        for col in _ordered_metry_columns(metry):
            var_label = _metry_var_label(col)
            if var_label not in var_order:
                var_order.append(var_label)
            cats_raw = [str(lbl) for _raw, lbl, _mask in _metry_column_categories(metry, col)]
            unique_cats: List[str] = []
            seen_cats: set[str] = set()
            for cat in cats_raw:
                nk = _demo_nk(cat)
                if nk in seen_cats:
                    continue
                seen_cats.add(nk)
                unique_cats.append(cat)
            cat_order[var_label] = _demo_merge_category_order(var_label, unique_cats)

    var_icons = {str(v).upper(): _demo_pick_var_icon(v) for v in var_order}
    cat_icons: Dict[str, str] = {}
    for var_label, cats in cat_order.items():
        for cat in cats:
            nk = _demo_nk(cat)
            if nk in cat_icons:
                continue
            cat_icons[nk] = _demo_pick_cat_icon(var_label, cat)

    return {
        "var_order": var_order,
        "cat_order": cat_order,
        "var_icons": var_icons,
        "cat_icons": cat_icons,
    }


def _ordered_metry_columns(metry: pd.DataFrame) -> List[str]:
    if metry is None or len(metry.columns) == 0:
        return []
    by_upper: Dict[str, str] = {}
    encounter_order: List[str] = []
    for col in list(metry.columns):
        c = str(col or "").strip()
        cu = c.upper()
        if not cu.startswith("M_"):
            continue
        if cu not in by_upper:
            by_upper[cu] = c
            encounter_order.append(cu)
    ordered_upper: List[str] = []
    for c in _DYN_METRY_COL_ORDER:
        if c in by_upper and c not in ordered_upper:
            ordered_upper.append(c)
    for c in _CORE_METRY_COL_ORDER:
        if c in by_upper and c not in ordered_upper:
            ordered_upper.append(c)
    extras = [c for c in encounter_order if c not in ordered_upper]
    ordered_upper.extend(extras)
    return [by_upper[c] for c in ordered_upper]


def _metry_var_label(col_name: str) -> str:
    cu = str(col_name or "").strip().upper()
    dyn_lbl = str(_DYN_METRY_VAR_LABEL_BY_COL.get(cu) or "").strip()
    if dyn_lbl:
        return dyn_lbl
    if cu in _CORE_METRY_VAR_LABELS:
        return _CORE_METRY_VAR_LABELS[cu]
    txt = cu[2:] if cu.startswith("M_") else cu
    txt = txt.replace("_", " ").strip()
    return txt.title() if txt else cu


def _metry_column_categories(metry: pd.DataFrame, col_name: str) -> List[Tuple[Any, str, np.ndarray]]:
    if col_name not in metry.columns:
        return []

    cu = str(col_name or "").strip().upper()
    defs = METRY_DEFS.get(cu, {})
    series = metry[col_name]
    series_num = pd.to_numeric(series, errors="coerce")
    if defs and int(series_num.notna().sum()) > 0:
        x = series_num.to_numpy(dtype=float)
        m_x = np.isfinite(x)
        cats: List[int] = []
        for k in defs.keys():
            try:
                kv = int(k)
            except Exception:
                continue
            if kv == 0:
                continue
            cats.append(kv)
        if int(np.sum(m_x & (x == 0.0))) > 0 and 0 in defs:
            cats = [0] + cats
        out_num: List[Tuple[Any, str, np.ndarray]] = []
        for cat in cats:
            mask = m_x & (x == float(cat))
            out_num.append((cat, str(defs.get(int(cat), int(cat))), mask))
        return out_num

    s = series.fillna("").astype(str).map(lambda x: " ".join(str(x).split()).strip())
    arr = s.to_numpy(dtype=object)
    is_missing = np.array([len(str(v).strip()) == 0 for v in arr], dtype=bool)
    values_present: List[str] = []
    seen_vals: set[str] = set()
    for raw_v in arr:
        txt = str(raw_v).strip()
        if not txt:
            continue
        nk = _demo_nk(txt)
        if nk in seen_vals:
            continue
        seen_vals.add(nk)
        values_present.append(txt)

    values_ordered: List[str] = []
    seen_order: set[str] = set()
    for txt in list(_DYN_METRY_CAT_ORDER_BY_COL.get(cu, [])):
        nk = _demo_nk(txt)
        if nk in seen_order:
            continue
        seen_order.add(nk)
        values_ordered.append(str(txt))
    for txt in values_present:
        nk = _demo_nk(txt)
        if nk in seen_order:
            continue
        seen_order.add(nk)
        values_ordered.append(txt)
    out_txt: List[Tuple[Any, str, np.ndarray]] = []
    if bool(is_missing.any()):
        out_txt.append(("__MISSING__", "brak danych", is_missing))
    for val in values_ordered:
        nk = _demo_nk(val)
        mask = np.array([_demo_nk(v) == nk for v in arr], dtype=bool)
        out_txt.append((val, str(val), mask))
    return out_txt


def _onehot_metry(metry: pd.DataFrame) -> np.ndarray:
    """One-hot metryczki (M_*), z zachowaniem 'brak danych' jako osobnej kategorii."""
    cols = _ordered_metry_columns(metry)
    mats = []
    for c in cols:
        cat_defs = _metry_column_categories(metry, c)
        if not cat_defs:
            continue
        s = metry[c].fillna("").astype(str).map(lambda x: " ".join(str(x).split()).strip())
        s_key = s.copy()
        key_order: List[str] = []
        key_to_label: Dict[str, str] = {}
        for raw_key, disp_label, mask in cat_defs:
            _ = mask
            key = f"{c}::{raw_key}"
            key_order.append(key)
            key_to_label[key] = str(disp_label)
            if str(raw_key) == "__MISSING__":
                s_key = s_key.mask(s.str.len() == 0, key)
            else:
                s_key = s_key.mask(s == str(raw_key), key)
        d = pd.get_dummies(s_key, prefix="", prefix_sep="")
        for key in key_order:
            if key not in d.columns:
                d[key] = 0
        d = d[key_order]
        mats.append(d.to_numpy(dtype=float))
    if not mats:
        return np.zeros((len(metry), 1), dtype=float)
    return np.concatenate(mats, axis=1)


def _silhouette_basic(X: np.ndarray,
                      labels: np.ndarray,
                      weights: Optional[np.ndarray] = None,
                      sample_max: int = 1800,
                      seed: int = 2026) -> float:
    """
    Silhouette (spójny z wagami):
    - wyklucza self-distance (zgodnie z definicją),
    - używa średnich ważonych (a, b i agregacja końcowa),
    - dla dużych prób liczy na ważonej próbie bez O(n^2) dla pełnego N.
    """
    X = np.asarray(X, dtype=float)
    labels = np.asarray(labels, dtype=int).reshape(-1)
    n = int(X.shape[0])
    if n < 3:
        return -1.0

    if weights is None:
        w = np.ones(n, dtype=float)
    else:
        w = np.asarray(weights, dtype=float).reshape(-1)
        if w.size != n:
            w = np.ones(n, dtype=float)
    w = np.where(np.isfinite(w) & (w > 0), w, 1.0)

    uniq_labels = [int(x) for x in np.unique(labels) if int(x) >= 0]
    if len(uniq_labels) < 2:
        return -1.0

    sample_max = int(max(0, sample_max))
    if sample_max > 0 and n > sample_max:
        rng = np.random.default_rng(int(seed) + int(n) + int(len(uniq_labels)) * 17)
        p = w / (np.sum(w) + 1e-12)
        idx = np.asarray(rng.choice(np.arange(n), size=sample_max, replace=False, p=p), dtype=int)
        idx.sort()
        X = X[idx, :]
        labels = labels[idx]
        w = w[idx]
        n = int(X.shape[0])
        uniq_labels = [int(x) for x in np.unique(labels) if int(x) >= 0]
        if len(uniq_labels) < 2:
            return -1.0

    D = np.sqrt(((X[:, None, :] - X[None, :, :]) ** 2).sum(axis=2))
    cluster_idx = {int(k): np.where(labels == int(k))[0] for k in uniq_labels}

    svals = np.zeros(n, dtype=float)
    for i in range(n):
        own_k = int(labels[i])
        same = cluster_idx.get(own_k, np.zeros(0, dtype=int))
        same = same[same != i]

        if same.size > 0:
            a = float(np.average(D[i, same], weights=w[same]))
        else:
            a = 0.0

        b = float("inf")
        for kk in uniq_labels:
            if int(kk) == own_k:
                continue
            mm = cluster_idx.get(int(kk), np.zeros(0, dtype=int))
            if mm.size == 0:
                continue
            b_k = float(np.average(D[i, mm], weights=w[mm]))
            if b_k < b:
                b = b_k

        if (not np.isfinite(b)) or (max(a, b) <= 1e-12):
            svals[i] = 0.0
        else:
            svals[i] = float((b - a) / max(a, b))

    return float(np.average(svals, weights=w)) if n > 0 else -1.0


def _segment_usefulness_from_P(P_seg: np.ndarray, P_overall: np.ndarray) -> float:
    """Użyteczność polityczna: duże, spójne odchylenia P od średniej."""
    d = np.asarray(P_seg, dtype=float) - np.asarray(P_overall, dtype=float)
    if not np.all(np.isfinite(d)):
        d = np.nan_to_num(d, nan=0.0)
    # bierzemy 3 najmocniejsze odchylenia (absolut)
    idx = np.argsort(-np.abs(d))[:3]
    return float(np.mean(np.abs(d[idx])))


# usunięto martwy duplikat starej segmentacji:
# - _rank_segments_by_usefulness()
# - _segments_profiles_premium()
#
# Jedyna aktywna ścieżka budowy profili segmentów to:
# - _segment_profiles_from_ranked_labels()
# wywoływana z build_meta_seg_pack().


def _lca_behavioral_names(labels_ranked: np.ndarray,
                          b1: np.ndarray, b2: np.ndarray, d13: np.ndarray,
                          w: np.ndarray, brand_values: Dict[str, str]) -> Dict[int, Dict[str, str]]:
    """
    Nazwy LCA oparte o faktyczne wybory:
    - B1 = macierz 0/1 (TOP3)
    - B2 = wektor TOP1
    - D13 = wektor TOP1

    Wersja 8.7: nazwy są bardziej autorskie i mniej mechaniczne.
    """
    labels_ranked = np.asarray(labels_ranked, dtype=int).reshape(-1)
    w = np.asarray(w, dtype=float).reshape(-1)

    def _top1_scores(idx_arr: np.ndarray, mask: np.ndarray) -> np.ndarray:
        idx = np.asarray(idx_arr, dtype=float).reshape(-1)
        counts = np.zeros(len(ARCHETYPES), dtype=float)

        ok = mask & np.isfinite(idx) & (idx >= 0)
        if not np.any(ok):
            return counts

        idx_sel = idx[ok].astype(int)
        w_sel = w[ok]
        for ii, ww in zip(idx_sel, w_sel):
            if 0 <= int(ii) < len(ARCHETYPES):
                counts[int(ii)] += float(ww)

        return counts

    out: Dict[int, Dict[str, str]] = {}
    uniq = [int(x) for x in np.unique(labels_ranked) if int(x) >= 0]

    for sid in uniq:
        m = labels_ranked == sid
        if not np.any(m):
            continue

        ws = w[m]

        # B1 = macierz 0/1
        if b1 is not None and getattr(b1, "ndim", 0) == 2:
            b1_scores = np.nansum(np.asarray(b1[m], dtype=float) * ws[:, None], axis=0)
        else:
            b1_scores = np.zeros(len(ARCHETYPES), dtype=float)

        # B2 / D13 = wektory TOP1
        b2_scores = _top1_scores(b2, m)
        d13_scores = _top1_scores(d13, m)

        i_b2 = int(np.nanargmax(b2_scores)) if len(b2_scores) else 0
        i_d13 = int(np.nanargmax(d13_scores)) if len(d13_scores) else i_b2
        i_b1 = int(np.nanargmax(b1_scores)) if len(b1_scores) else i_b2

        a_prio = ARCHETYPES[i_b2]
        a_need = ARCHETYPES[i_d13]

        if a_need == a_prio:
            a_need = ARCHETYPES[i_b1]

        out[sid] = {
            "name_arche": _segment_brand_title(a_prio, a_need, brand_values, mode="arche"),
            "name_values": _segment_brand_title(a_prio, a_need, brand_values, mode="values"),
        }

    return out


def _segments_profiles_premium(labels: np.ndarray, metry: Optional[pd.DataFrame],
                               P: np.ndarray, E: np.ndarray, G: np.ndarray, w: np.ndarray,
                               brand_values: Dict[str, str]) -> Tuple[List[Dict[str, Any]], Dict[int, int], float]:
    """
    Wrapper zgodnościowy.

    Nie utrzymujemy już osobnej logiki segmentacji premium.
    Wszystko ma iść przez jedną kanoniczną ścieżkę:
    labels -> _reorder_labels_by_weight() -> _segment_profiles_from_ranked_labels()
    """
    labels = np.asarray(labels, dtype=int).reshape(-1)
    w = np.asarray(w, dtype=float).reshape(-1)

    if labels.size == 0:
        return [], {}, 0.0

    if w.size != labels.size:
        w = np.ones(labels.size, dtype=float)

    labels_ranked, id_map = _reorder_labels_by_weight(labels, w)

    segs = _segment_profiles_from_ranked_labels(
        labels_ranked=labels_ranked,
        metry=metry,
        P=P,
        E=E,
        G=G,
        w=w,
        brand_values=brand_values,
    )

    avg_use = float(np.mean([float(s.get("usefulness", 0.0)) for s in segs])) if segs else 0.0
    return segs, id_map, avg_use


def _profiles_to_html(profiles: List[Dict[str, Any]], brand_values: Optional[Dict[str, str]] = None,
                      mode: str = "arche",
                      city_label: str = "Miasto Poznań",
                      population_15_plus: Optional[float] = None,
                      segment_threshold_overrides: Optional[Dict[Any, Any]] = None,
                      profile_chart_prefix: str = "SEG_PROFILE",
                      profile_box_label: str = "◎ Profil segmentu (siła wartości, skala: 0-100)") -> str:
    """
    Karty segmentów czytane z jednej kanonicznej struktury segmentu.
    Wersja premium: estetyczna, kolorystycznie spójna z mapami segmentów
    i czytelna także przy większej liczbie kart.
    """
    import html
    import re

    brand_values = brand_values or {}

    def _to_items(x: Any) -> List[str]:
        if x is None:
            return []
        if isinstance(x, (list, tuple)):
            out = []
            for v in x:
                s = str(v).strip()
                if s:
                    out.append(s)
            return out
        s = str(x).strip()
        return [s] if s else []

    def _safe_float(x: Any, default: float = 0.0) -> float:
        try:
            return float(x)
        except Exception:
            return default

    def _fmt_int_space(x: Any) -> str:
        try:
            return f"{int(round(float(x))):,}".replace(",", " ")
        except Exception:
            return "—"

    city_label_txt = str(city_label or "").strip() or "Miasto Poznań"
    pop_15 = _safe_float(population_15_plus, 0.0)
    has_pop_15 = bool(pop_15 > 0.0)
    pop_15_txt = _fmt_int_space(pop_15) if has_pop_15 else "—"

    def _render_list(items: List[str], empty_text: str = "Brak danych.") -> str:
        if not items:
            return f"<div style='color:#6b7280; font-size:12px;'>{html.escape(empty_text)}</div>"
        lis = "".join(f"<li>{html.escape(i)}</li>" for i in items)
        return f"<ul style='margin:6px 0 0 18px; padding:0; font-size:12.2px; line-height:1.35;'>{lis}</ul>"

    def _chip(text: str, *, bg: str, bd: str, fg: str) -> str:
        return (
            f"<span style='display:inline-block; padding:5px 9px; margin:2px 6px 2px 0; "
            f"border:1px solid {bd}; border-radius:999px; background:{bg}; color:{fg}; "
            f"font-size:12px; font-weight:700;'>{html.escape(str(text))}</span>"
        )

    def _metric_pill(label: str, value: str) -> str:
        return (
            "<span class='seg-metric-pill'>"
            f"<span>{html.escape(str(label))}</span>"
            f"<b>{html.escape(str(value))}</b>"
            "</span>"
        )

    def _to_values_language(text: Any) -> str:
        s = str(text or "")
        if not s:
            return s

        # Najpierw mapujemy nazwy archetypów na nazwy wartości.
        for a in sorted(brand_values.keys(), key=lambda z: -len(str(z))):
            v = str(brand_values.get(a, a))
            s = re.sub(rf"\b{re.escape(str(a))}\b", v, s)

        # Potem korygujemy słownictwo na język wartości.
        phrase_replacements = [
            ("Archetyp / wartość", "Wartość"),
            ("archetyp / wartość", "wartość"),
            ("silniejszy archetyp", "silniejsza wartość"),
            ("Silniejszy archetyp", "Silniejsza wartość"),
            ("dla każdego archetypu", "dla każdej wartości"),
            ("Dla każdego archetypu", "Dla każdej wartości"),
            ("archetyp wskazany jako najważniejszy", "wartość wskazana jako najważniejsza"),
            ("Archetyp wskazany jako najważniejszy", "Wartość wskazana jako najważniejsza"),
        ]
        for old, new in phrase_replacements:
            s = s.replace(old, new)

        word_replacements = [
            ("Archetypami", "Wartościami"),
            ("Archetypach", "Wartościach"),
            ("Archetypów", "Wartości"),
            ("Archetypy", "Wartości"),
            ("Archetypu", "Wartości"),
            ("Archetypie", "Wartości"),
            ("Archetypem", "Wartością"),
            ("Archetyp", "Wartość"),
            ("archetypami", "wartościami"),
            ("archetypach", "wartościach"),
            ("archetypów", "wartości"),
            ("archetypy", "wartości"),
            ("archetypu", "wartości"),
            ("archetypie", "wartości"),
            ("archetypem", "wartością"),
            ("archetyp", "wartość"),
            ("archetypowa", "wartościowa"),
            ("archetypowe", "wartościowe"),
            ("archetypowy", "wartościowy"),
            ("archetypowych", "wartościowych"),
            ("archetypowego", "wartościowego"),
            ("archetypową", "wartościową"),
            ("archetypowym", "wartościowym"),
            ("Archetypowa", "Wartościowa"),
            ("Archetypowe", "Wartościowe"),
            ("Archetypowy", "Wartościowy"),
            ("Archetypowych", "Wartościowych"),
            ("Archetypowego", "Wartościowego"),
            ("Archetypową", "Wartościową"),
            ("Archetypowym", "Wartościowym"),
        ]
        for old, new in word_replacements:
            s = s.replace(old, new)

        return s

    def _render_demo_table(rows: List[Dict[str, Any]], palette: Dict[str, str]) -> str:
        line = html.escape(str(palette.get("line", "#dee2e6")))
        accent = html.escape(str(palette.get("accent", "#495057")))
        soft = html.escape(str(palette.get("soft", "#f8f9fa")))

        def _hex_to_rgb(_hex: str) -> Tuple[int, int, int]:
            h = str(_hex or "").strip().lstrip("#")
            if len(h) == 3:
                h = "".join(ch * 2 for ch in h)
            if len(h) != 6:
                return (56, 72, 89)
            try:
                return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
            except Exception:
                return (56, 72, 89)

        r_acc, g_acc, b_acc = _hex_to_rgb(accent)
        bar_fill_best = f"rgba({r_acc},{g_acc},{b_acc},0.74)"
        bar_fill_other = f"rgba({r_acc},{g_acc},{b_acc},0.30)"

        def _bar_td_for_segment(pct: float, is_best: bool, top_border: str = "") -> str:
            pct = max(0.0, min(100.0, float(pct)))
            fill = bar_fill_best if is_best else bar_fill_other
            pct_fw = "900" if is_best else "600"
            return (
                f"<td style='padding:0; min-width:176px; border:1px solid #dfe4ea; {top_border}'>"
                "<div style='position:relative; height:34px; background:#fff;'>"
                f"<div style='position:absolute; left:0; top:0; bottom:0; width:{pct:.1f}%; background:{fill};'></div>"
                f"<span style='position:absolute; right:6px; top:7px; z-index:2; background:rgba(255,255,255,0.88); padding:1px 5px; border-radius:4px; font-size:12px; font-weight:{pct_fw}; color:#111;'>{pct:.0f}%</span>"
                "</div>"
                "</td>"
            )

        grouped: Dict[str, List[Dict[str, float]]] = {}
        for r in rows:
            zm = str(r.get("zmienna", "")).strip()
            kat = str(r.get("kategoria", "")).strip()
            if not zm or not kat:
                continue

            grouped.setdefault(zm, []).append({
                "zmienna": zm,
                "kategoria": kat,
                "pct_seg": _safe_float(r.get("pct_seg", 0.0)),
                "pct_all": _safe_float(r.get("pct_all", 0.0)),
                "lift_pp": _safe_float(r.get("lift_pp", 0.0)),
            })

        demo_schema = _build_demo_schema_from_rows(
            [
                {"zmienna": rr.get("zmienna"), "kategoria": rr.get("kategoria")}
                for rr in list(rows or [])
                if isinstance(rr, dict)
            ]
        )
        summary_order = list(demo_schema.get("var_order") or [])
        detail_order = list(summary_order)
        cat_order = dict(demo_schema.get("cat_order") or {})

        if not grouped:
            return (
                "<div class='seg-demo-wrap'>"
                "<div class='seg-box'>"
                "<div class='seg-mini-label'>👥 Profil demograficzny segmentu</div>"
                "<div style='color:#6b7280; font-size:12px;'>Brak danych demograficznych.</div>"
                "</div>"
                "</div>"
            )

        summary_bits: List[str] = []
        for zm in summary_order:
            items = grouped.get(zm, [])
            if not items:
                continue

            items_sorted = sorted(
                items,
                key=lambda rr: (-float(rr.get("pct_seg", 0.0)), -abs(float(rr.get("lift_pp", 0.0))))
            )
            best = items_sorted[0]

            best_cat = str(best.get("kategoria", ""))
            best_icon = _demo_pick_cat_icon(zm, best_cat)

            summary_bits.append(
                "<div style='padding:8px 10px; border:1px solid {line}; border-radius:12px; "
                "background:linear-gradient(180deg, #ffffff 0%, {soft} 100%); box-shadow:0 4px 12px rgba(15,23,42,.04);'>"
                "<div style='font-size:11px; font-weight:700; color:#5f6b7a; text-transform:uppercase;'>{zm}</div>"
                "<div style='margin-top:3px; display:flex; align-items:center; gap:8px;'>"
                "<span style='font-size:18px; line-height:1;'>{icon}</span>"
                "<span style='font-size:13px; font-weight:800; color:{accent};'>{kat}</span>"
                "</div>"
                "<div style='margin-top:3px; font-size:12px; color:#495057;'>"
                "{pct_seg:.0f}% w segmencie • {lift_pp:+.1f} pp"
                "</div>"
                "</div>".format(
                    line=line,
                    soft=soft,
                    zm=html.escape(str(zm)),
                    icon=html.escape(str(best_icon)),
                    accent=accent,
                    kat=html.escape(best_cat),
                    pct_seg=float(best.get("pct_seg", 0.0)),
                    lift_pp=float(best.get("lift_pp", 0.0)),
                )
            )

        body_rows: List[str] = []

        for zm in detail_order:
            items = grouped.get(zm, [])
            if not items:
                continue

            wanted = cat_order.get(zm, [])
            wanted_norm = {_demo_nk(x): i for i, x in enumerate(wanted)}

            items_sorted = sorted(
                items,
                key=lambda rr: (
                    wanted_norm.get(_demo_nk(rr.get("kategoria", "")), 999),
                    -float(rr.get("pct_seg", 0.0)),
                )
            )

            best_pct = max(float(rr.get("pct_seg", 0.0)) for rr in items_sorted)
            row_count = len(items_sorted)

            for idx, rr in enumerate(items_sorted):
                zm_cell = ""
                if idx == 0:
                    zm_cell = (
                        f"<td rowspan='{row_count}' style='font-weight:800; vertical-align:top; background:#fafbfc;'>"
                        f"{html.escape(str(zm))}</td>"
                    )

                is_best = abs(float(rr.get("pct_seg", 0.0)) - best_pct) <= 1e-9
                top_border = "border-top:2px solid #9aa7b4;" if idx == 0 else ""
                cat_fw = "800" if is_best else "500"

                lift_val = float(rr.get("lift_pp", 0.0))
                lift_color = "#15803d" if lift_val >= 0 else "#b91c1c"
                pct_seg_cell = _bar_td_for_segment(
                    pct=float(rr.get("pct_seg", 0.0)),
                    is_best=is_best,
                    top_border=top_border,
                )

                if idx == 0:
                    zm_cell = (
                        f"<td rowspan='{row_count}' style='font-weight:800; vertical-align:top; background:#fafbfc; {top_border}'>"
                        f"{html.escape(str(zm))}</td>"
                    )

                body_rows.append(
                    "<tr>"
                    f"{zm_cell}"
                    f"<td style='{top_border} font-weight:{cat_fw};'><span style='display:inline-flex; align-items:center; gap:6px;'><span>{html.escape(str(_demo_pick_cat_icon(zm, str(rr.get('kategoria', '')))) )}</span><span>{html.escape(str(rr.get('kategoria', '')))}</span></span></td>"
                    f"{pct_seg_cell}"
                    f"<td style='text-align:right; {top_border}'>{float(rr.get('pct_all', 0.0)):.0f}%</td>"
                    f"<td style='text-align:right; color:{lift_color}; {top_border}'>{lift_val:+.1f} pp</td>"
                    "</tr>"
                )

        summary_html = ""
        if summary_bits:
            summary_html = (
                    f"<div class='seg-box' style='border-color:{line}; margin-bottom:10px;'>"
                    "<div class='seg-mini-label'>📌 Statystyczny profil demograficzny segmentu</div>"
                    "<div style='display:grid; grid-template-columns:repeat(auto-fit, minmax(180px, 1fr)); gap:8px; margin-top:8px;'>"
                    + "".join(summary_bits) +
                    "</div>"
                    "</div>"
            )

        table_html = (
                f"<div class='seg-box' style='border-color:{line};'>"
                "<div class='seg-mini-label'>👥 Profil demograficzny segmentu</div>"
                "<div style='color:#5f6b7a; font-size:12px; margin:2px 0 6px 0;'>"
                "Pokazujemy pełny rozkład w stałej kolejności. "
                "W kolumnie „% segment” podświetlamy najwyższą kategorię dla każdej zmiennej."
                "</div>"
                "<div class='seg-demo-scroll'>"
                "<table class='tbl' style='margin-top:0; border:3px solid #b8c2cc;'>"
                "<thead><tr>"
                "<th style='border-top:3px solid #b8c2cc; border-left:3px solid #b8c2cc;'>Zmienna</th><th style='border-top:3px solid #b8c2cc;'>Kategoria</th><th style='border-top:3px solid #b8c2cc; text-align:right;'>% segment</th><th style='border-top:3px solid #b8c2cc; text-align:right;'>% próba</th><th style='border-top:3px solid #b8c2cc; border-right:3px solid #b8c2cc; text-align:right;'>Różnica</th>"
                "</tr></thead>"
                "<tbody>" + "".join(body_rows) + "</tbody>"
                                                 "</table>"
                                                 "</div>"
                                                 "</div>"
        )

        return (
            "<div class='seg-demo-wrap'>"
            f"{summary_html}"
            f"{table_html}"
            "</div>"
        )

    mode_values = (str(mode).lower() == "values")
    parts: List[str] = []

    # --- Zestawienie wszystkich segmentów (numer, nazwa, udział, N, użyteczność) ---
    _profiles_sorted = sorted(
        [dict(pp) for pp in (profiles or []) if isinstance(pp, dict)],
        key=lambda pp: int(_safe_float(pp.get("segment_rank", pp.get("segment_id", 0))))
    )
    _profiles_overview_sorted = sorted(
        _profiles_sorted,
        key=lambda pp: (
            -float(_safe_float(pp.get("share_pct", 0.0))),
            int(_safe_float(pp.get("segment_rank", pp.get("segment_id", 0))))
        )
    )

    hit_count_by_rank: Dict[int, int] = {}
    try:
        _state = _compute_segment_smart_state(
            segs=_profiles_sorted,
            top_n=max(1, len(_profiles_sorted)),
            special_threshold_overrides=segment_threshold_overrides,
        )
        _hit = np.asarray(_state.get("hit"), dtype=bool)
        _state_segs = list(_state.get("segs", []) or [])
        if _hit.ndim == 2 and _hit.shape[1] == len(_state_segs):
            for _col, _seg in enumerate(_state_segs):
                _rank = int(_safe_float(_seg.get("segment_rank", _col)))
                hit_count_by_rank[_rank] = int(np.count_nonzero(_hit[:, _col]))
    except Exception:
        hit_count_by_rank = {}


    overview_rows: List[str] = []
    total_n_raw = int(sum(int(_safe_float(pp.get("n", 0))) for pp in _profiles_sorted))
    for disp_idx, pp in enumerate(_profiles_overview_sorted):
        sr = int(_safe_float(pp.get("segment_rank", 0)))
        sn = int(disp_idx) + 1
        share_pct0 = _safe_float(pp.get("share_pct", 0.0))
        n0 = int(_safe_float(pp.get("n", 0)))
        raw_share0 = (100.0 * float(n0) / float(max(1, total_n_raw)))
        resident_share_pct0_txt = f"{share_pct0:.1f}%"
        est_max0 = int(round((share_pct0 / 100.0) * pop_15)) if has_pop_15 else None
        est_max0_txt = _fmt_int_space(est_max0) if est_max0 is not None else "—"
        hit_count0 = int(hit_count_by_rank.get(sr, 0))
        use0 = _safe_float(pp.get("usefulness", 0.0))

        nm_a, _nm_v = _segment_name_pair(pp)
        _palette0 = _segment_ui_colors(sn)
        _name_color = html.escape(str(_palette0.get("accent", "#495057")))

        overview_rows.append(
            "<tr>"
            f"<td style='font-weight:400; white-space:nowrap;'>Seg_{sn}</td>"
            f"<td style='font-weight:600; color:{_name_color};'>{html.escape(str(nm_a))}</td>"
            f"<td style='text-align:right;'>{raw_share0:.1f}%</td>"
            f"<td style='text-align:right;'>{n0}</td>"
            f"<td style='text-align:right;'>{resident_share_pct0_txt}</td>"
            f"<td style='text-align:right;'>{est_max0_txt}</td>"
            f"<td style='text-align:right;'>{hit_count0}</td>"
            f"<td style='text-align:right;'>{use0:.1f}</td>"
            "</tr>"
        )

    overview_html = (
        "<div class='card' style='margin:0 0 14px 0; max-width:1380px; width:100%;'>"
        "<h3 style='margin:0 0 6px 0;'>Zestawienie segmentów</h3>"
        "<div class='small' style='margin-bottom:10px;'>Numer • nazwa • udział surowy (%) • N (surowe) • % udział mieszkańców 15+ (po wagowaniu) • szacowana maksymalna wielkość segmentu (15+) • przewagi istotne (N) • użyteczność. % udział mieszkańców 15+ (po wagowaniu) liczony jest na wagach badania; udział surowy wynika bezpośrednio z N. Dla " + html.escape(city_label_txt) + " przyjęto populację 15+: " + pop_15_txt + ". Progi przewag zmieniają mapę/macierze i licznik przewag; gdy ustawisz segment_hit_threshold_overrides, raport przelicza też udział i N segmentów na bazie aktywnych przewag.</div>"
        "<div style='overflow-x:auto;'><table class='tbl' style='margin-top:0; width:100%; min-width:1080px;'>"
        "<thead><tr>"
        "<th style='width:64px;'>Segment</th>"
        "<th style='width:300px;'>Nazwa</th>"
        "<th style='width:108px; text-align:right;'>Udział surowy</th>"
        "<th style='width:108px; text-align:right;'>N (surowe)</th>"
        "<th style='width:230px; text-align:right; line-height:1.25;'>% udział mieszkańców 15+<br>(po wagowaniu)</th>"
        "<th style='width:200px; text-align:right;'>Szac. max wielkość segmentu (15+)</th>"
        "<th style='width:110px; text-align:right;'>Przewagi istotne (N)</th>"
        "<th style='width:90px; text-align:right;'>Użyteczność</th>"
        "</tr></thead>"
        "<tbody>" + "".join(overview_rows) + "</tbody>"
        "</table></div>"
        "</div>"
    )

    parts.append(overview_html)

    _display_seg_num_by_rank: Dict[int, int] = {}
    for _disp_idx, _pp in enumerate(_profiles_overview_sorted):
        _sr = int(_safe_float(_pp.get("segment_rank", _pp.get("segment_id", _disp_idx))))
        _display_seg_num_by_rank[_sr] = int(_disp_idx) + 1

    for i, p in enumerate(_profiles_overview_sorted):
        seg_rank = int(_safe_float(p.get("segment_rank", p.get("segment_id", i))))
        seg_num = int(_display_seg_num_by_rank.get(seg_rank, i + 1))
        seg_num_src = seg_rank + 1
        seg_label = html.escape(f"Seg_{seg_num}")

        share_pct = _safe_float(p.get("share_pct", 0.0))
        n_seg = int(_safe_float(p.get("n", 0)))
        raw_share_seg = (100.0 * float(n_seg) / float(max(1, total_n_raw)))
        est_pop_seg = (share_pct / 100.0) * pop_15 if has_pop_15 else 0.0
        est_pop_seg_txt = _fmt_int_space(est_pop_seg) if has_pop_15 else "—"
        usefulness = _safe_float(p.get("usefulness", 0.0))

        name_arche, name_values = _segment_name_pair(p)

        top3_arche = [str(x) for x in (p.get("top3_arche") or p.get("top3") or [])]
        top3_values = [str(x) for x in (p.get("top3_values") or [])]
        if not top3_values:
            top3_values = [str(brand_values.get(x, x)) for x in top3_arche]

        bottom_arche = [str(x) for x in (p.get("bottom_arche") or [])]
        bottom_values = [str(brand_values.get(x, x)) for x in bottom_arche]

        # Nazwa segmentu ma być stała (jak w trybie archetypów), niezależnie od radio-buttona.
        title_txt = name_arche
        top3 = top3_values if mode_values else [_display_archetype_label(x) for x in top3_arche]
        bottom = bottom_values if mode_values else [_display_archetype_label(x) for x in bottom_arche]

        title_html = html.escape(str(title_txt))

        resident_share_pct_txt = f"{share_pct:.1f}%" if has_pop_15 else "—"
        hit_count_seg = int(hit_count_by_rank.get(seg_rank, 0))
        palette = _segment_ui_colors(seg_num)

        accent = html.escape(str(palette.get("accent", "#495057")))
        soft = html.escape(str(palette.get("soft", "#f8f9fa")))
        line = html.escape(str(palette.get("line", "#dee2e6")))
        chip_bg = html.escape(str(palette.get("chip_bg", "#f8f9fa")))
        chip_bd = html.escape(str(palette.get("chip_bd", "#dee2e6")))
        chip_fg = html.escape(str(palette.get("chip_fg", "#495057")))

        warn_bg = "#fff4e6"
        warn_bd = "#ffd8a8"
        warn_fg = "#8a4b08"

        top_chips_html = "".join(
            _chip(x, bg=chip_bg, bd=chip_bd, fg=chip_fg) for x in top3[:3]
        ) if top3 else "<span style='color:#6b7280; font-size:12px;'>Brak TOP3</span>"

        core_values: List[str] = []

        pm_share = p.get("Pm_share_pct")
        if isinstance(pm_share, (list, tuple)) and len(pm_share) == len(ARCHETYPES):
            pairs: List[Tuple[str, float]] = []
            for a_lbl, sc in zip(ARCHETYPES, pm_share):
                v_lbl = str(brand_values.get(a_lbl, a_lbl))
                try:
                    pairs.append((v_lbl, float(sc)))
                except Exception:
                    pairs.append((v_lbl, 0.0))

            pairs.sort(key=lambda t: -t[1])

            seen = set()
            for v_lbl, sc in pairs:
                if sc >= 80.0 and v_lbl not in seen:
                    core_values.append(v_lbl)
                    seen.add(v_lbl)

        if not core_values:
            core_values = list(top3_values[:3])

        top_core_html = "".join(
            _chip(x, bg=chip_bg, bd=chip_bd, fg=chip_fg) for x in core_values
        ) if core_values else "<span style='color:#6b7280; font-size:12px;'>Brak rdzenia</span>"

        bottom_chips_html = "".join(
            _chip(x, bg=warn_bg, bd=warn_bd, fg=warn_fg) for x in bottom[:2]
        ) if bottom else "<span style='color:#6b7280; font-size:12px;'>Brak wyraźnych deficytów</span>"

        opis_items = _to_items(p.get("opis"))
        sugestie_items = _to_items(p.get("sugestie"))
        ryzyka_items = _to_items(p.get("ryzyka"))
        if mode_values:
            opis_items = [_to_values_language(x) for x in opis_items]
            sugestie_items = [_to_values_language(x) for x in sugestie_items]
            ryzyka_items = [_to_values_language(x) for x in ryzyka_items]
        demo_rows = _segment_demography_rows(p)

        metrics_html = (
                _metric_pill("Udział ważony", f"{share_pct:.1f}%")
                + _metric_pill("Udział surowy", f"{raw_share_seg:.1f}%")
                + _metric_pill("% udział mieszkańców 15+", resident_share_pct_txt)
                + _metric_pill("N (surowe)", str(n_seg))
                + _metric_pill("Szac. max 15+", est_pop_seg_txt)
                + _metric_pill("Przewagi istotne", str(hit_count_seg))
                + _metric_pill("Użyteczność", f"{usefulness:.1f}")
        )

        profile_box_label_txt = str(profile_box_label or "◎ Profil segmentu (siła wartości, skala: 0-100)")
        if profile_chart_prefix:
            profile_img_name = f"{str(profile_chart_prefix).strip()}_{int(seg_num_src)}_values.png"
        else:
            profile_img_name = _segment_profile_chart_filename(seg_num_src, "values")

        profile_chart_html = (
            f"<div class='seg-box seg-profile-plot' style='border-color:{line}; background:#fff; margin-bottom:0; padding:12px;'>"
            f"<div class='seg-mini-label'>{html.escape(profile_box_label_txt)}</div>"
            "<div style='margin-top:6px;'>"
            f"<img src='{profile_img_name}' alt='Profil wartości {seg_label}' "
            "style='width:100%; display:block; margin:0 auto;' "
            "onerror=\"this.closest('.seg-profile-wrap').style.display='none';\">"
            "</div>"
            "<div class='small' style='margin:12px 0 2px 0; font-weight:600;'>"
            "<span style='display:inline-flex; align-items:center; gap:8px; margin-right:18px;'><span style='display:inline-block; width:10px; height:10px; border-radius:2px; background:#d94841;'></span>Zmiana</span>"
            "<span style='display:inline-flex; align-items:center; gap:8px; margin-right:18px;'><span style='display:inline-block; width:10px; height:10px; border-radius:2px; background:#1d4ed8;'></span>Ludzie</span>"
            "<span style='display:inline-flex; align-items:center; gap:8px; margin-right:18px;'><span style='display:inline-block; width:10px; height:10px; border-radius:2px; background:#2b8a3e;'></span>Porządek</span>"
            "<span style='display:inline-flex; align-items:center; gap:6px;'><span style='display:inline-block; width:10px; height:10px; border-radius:2px; background:#7048e8;'></span>Niezależność</span>"
            "</div>"
            "</div>"
        )

        card_html = (
            f"<div class='card seg-card' data-seg-rank='{i}' "
            f"style='margin-bottom:22px; border-left-color:{accent}; "
            f"background:linear-gradient(180deg, {soft} 0px, #ffffff 84px);'>"

            "<div class='seg-top'>"
            "<div class='seg-top-main'>"
            f"<div class='seg-badge' style='background:{chip_bg}; border-color:{line}; color:{chip_fg};'>◉ Segment {seg_num}</div>"
            f"<div style='font-weight:800; font-size:20px; margin-top:8px;'>{seg_label}</div>"
            f"<div style='margin-top:6px; font-weight:800; font-size:18px; line-height:1.35;'>{title_html}</div>"
            f"<div class='seg-metrics'>{metrics_html}</div>"
            "</div>"

            "<div class='seg-top-side'>"
            f"<div class='seg-box' style='border-color:{line}; background:{soft};'>"
            "<div class='seg-mini-label'>★ Rdzeń segmentu</div>"
            f"<div>{top_core_html}</div>"
            "</div>"
            "</div>"
            "</div>"

            "<div class='seg-duo' style='align-items:start; margin-top:22px;'>"

            "<div class='seg-main-col'>"

            "<div class='seg-row' style='margin-top:0;'>"
            f"<div class='seg-box' style='border-color:{line}; margin-top:0;'>"
            "<div class='seg-mini-label'>↗ Dominujące motywy</div>"
            f"<div>{top_chips_html}</div>"
            "</div>"

            f"<div class='seg-box' style='border-color:{warn_bd}; margin-top:0;'>"
            "<div class='seg-mini-label'>⚠ Deficyty / punkty napięcia</div>"
            f"<div>{bottom_chips_html}</div>"
            "</div>"
            "</div>"

            f"<div class='seg-box seg-wide' style='border-color:{line}; margin-top:14px;'>"
            "<div class='seg-mini-label'>✓ Co ten segment ceni</div>"
            f"{_render_list(opis_items)}"
            "</div>"

            "<div class='seg-row'>"
            f"<div class='seg-box' style='border-color:{line}; margin-top:0;'>"
            "<div class='seg-mini-label'>🗣 Jak do niego mówić</div>"
            f"{_render_list(sugestie_items)}"
            "</div>"

            f"<div class='seg-box' style='border-color:{line}; margin-top:0;'>"
            "<div class='seg-mini-label'>⛔ Na co uważać</div>"
            f"{_render_list(ryzyka_items)}"
            "</div>"
            "</div>"

            f"{_render_demo_table(demo_rows, palette)}"
            "</div>"

            f"<div class='seg-profile-wrap' style='min-width:320px;'>{profile_chart_html}</div>"

            "</div>"
            "</div>"
        )

        parts.append(card_html)

    return '\n'.join(parts) if parts else "<p class='small'>Brak danych segmentów.</p>"


def _render_segment_smart_group_matrix_html(
        segs: List[Dict[str, Any]],
        brand_values: Dict[str, str],
        mode: str = "arche",
        top_n: int = 5,
        min_beats: int = 3,
        min_gap: float = 0.15,
        min_positive: float = 0.10,
        strong_min: float = 0.35,
        core_min: float = 0.70,
        top_rank_limit: int = 2,
        segment_threshold_overrides: Optional[Dict[Any, Any]] = None
) -> str:
    """
    Smart-group:
    zaznaczamy tylko te pola, które są naprawdę warte podkreślenia.

    Logika liczenia jest wspólna z mapą przewag segmentów
    (jedno źródło prawdy = _compute_segment_smart_state()).
    """
    segs = list(segs or [])
    if not segs:
        return ""

    try:
        top_n = max(1, int(top_n))
    except Exception:
        top_n = 5

    state = _compute_segment_smart_state(
        segs=segs,
        top_n=top_n,
        min_beats=min_beats,
        min_gap=min_gap,
        min_positive=min_positive,
        strong_min=strong_min,
        core_min=core_min,
        top_rank_limit=top_rank_limit,
        special_threshold_overrides=segment_threshold_overrides,
    )

    segs = list(state.get("segs", []) or [])
    if not segs:
        return ""

    mode_values = (str(mode).lower() == "values")

    headers: List[str] = []
    for s in segs:
        nm_a, _nm_v = _segment_name_pair(s)
        headers.append(nm_a)

    k = len(segs)
    a_cnt = len(ARCHETYPES)
    other_cnt_max = max(0, k - 1)

    values_matrix = np.asarray(state.get("values"), dtype=float)
    beats_matrix = np.asarray(state.get("beats"), dtype=int)
    rank_matrix = np.asarray(state.get("ranks"), dtype=int)
    hit_matrix = np.asarray(state.get("hit"), dtype=bool)
    tier_matrix = np.asarray(state.get("tier"), dtype=int)

    if values_matrix.shape != (a_cnt, k):
        values_matrix = np.zeros((a_cnt, k), dtype=float)
    if beats_matrix.shape != (a_cnt, k):
        beats_matrix = np.zeros((a_cnt, k), dtype=int)
    if rank_matrix.shape != (a_cnt, k):
        rank_matrix = np.zeros((a_cnt, k), dtype=int)
    if hit_matrix.shape != (a_cnt, k):
        hit_matrix = np.zeros((a_cnt, k), dtype=bool)
    if tier_matrix.shape != (a_cnt, k):
        tier_matrix = np.zeros((a_cnt, k), dtype=int)

    effective_min_beats = int(
        state.get("effective_min_beats", max(1, min(int(min_beats), max(1, k - 1))))
    )
    effective_top_rank = max(1, min(int(top_rank_limit), k))

    active_special_rules = _resolve_segment_smart_rules(segment_threshold_overrides)
    active_rule_rows: List[str] = []
    for rule_key in sorted(active_special_rules.keys(), key=lambda t: (int(t[0]), int(t[1]), int(t[2]))):
        other_cnt_rule, beats_rule, rank_rule = [int(x) for x in rule_key]
        if other_cnt_rule != other_cnt_max:
            continue
        min_val, use_ge = active_special_rules[rule_key]
        op_txt = ">=" if bool(use_ge) else ">"
        active_rule_rows.append(
            "<tr>"
            f"<td style='padding:5px 8px; border:1px solid #e5e7eb; text-align:left; white-space:nowrap;'>"
            f"{_html.escape(_segment_smart_rule_label(rule_key))}</td>"
            f"<td style='padding:5px 8px; border:1px solid #e5e7eb; text-align:center; white-space:nowrap;'>{op_txt} {float(min_val):.1f}</td>"
            "</tr>"
        )

    if not active_rule_rows:
        active_rule_rows.append(
            "<tr><td colspan='2' style='padding:5px 8px; border:1px solid #e5e7eb; color:#64748b;'>"
            "Brak specjalnych progów dla aktualnej liczby segmentów.</td></tr>"
        )

    if k <= 5:
        col_min_w = 150
        label_col_w = 190
    elif k <= 7:
        col_min_w = 132
        label_col_w = 180
    elif k <= 9:
        col_min_w = 116
        label_col_w = 168
    else:
        col_min_w = 104
        label_col_w = 158

    head_html = [
        "<tr>",
        f"<th style='width:{label_col_w}px;'>{'Wartość' if mode_values else 'Archetyp'}</th>"
    ]

    for col_idx, h in enumerate(headers):
        pal = _segment_ui_colors(col_idx + 1)
        head_html.append(
            f"<th class='seg-mcol' data-seg-rank='{col_idx}' "
            f"style='text-align:center; min-width:{col_min_w}px; padding:6px 10px; "
            f"border:1px solid #d9dde3; "
            f"background:{pal.get('soft', '#f8fafc')}; "
            f"color:{pal.get('chip_fg', '#334155')}; "
            f"border-bottom:2px solid {pal.get('line', '#d9dde3')};'>"
            f"{_html.escape(str(h))}"
            "</th>"
        )
    head_html.append("</tr>")

    body_rows: List[str] = []

    for a_idx, arch in enumerate(ARCHETYPES):
        row_label = brand_values.get(arch, arch) if mode_values else _display_archetype_label(arch)

        row_cells: List[str] = [
            "<tr>",
            f"<td style='font-weight:700; padding:6px 10px; border:1px solid #e5e7eb; background:#ffffff;'>{_html.escape(str(row_label))}</td>"
        ]

        for col_idx in range(k):
            val = float(values_matrix[a_idx, col_idx])
            beats = int(beats_matrix[a_idx, col_idx])
            row_rank = int(rank_matrix[a_idx, col_idx])
            hit = bool(hit_matrix[a_idx, col_idx])
            tier = int(tier_matrix[a_idx, col_idx])

            if hit:
                if tier == 3:
                    bg = "#dcfce7"
                    num_fg = "#166534"
                    sub_fg = "#166534"
                elif tier == 2:
                    bg = "#ecfdf5"
                    num_fg = "#166534"
                    sub_fg = "#166534"
                else:
                    bg = "#f0fdf4"
                    num_fg = "#166534"
                    sub_fg = "#166534"

                inner_style = (
                    "min-height:40px; "
                    "display:flex; flex-direction:column; align-items:center; justify-content:center; "
                    "padding:2px 8px; "
                    f"background:{bg}; "
                    "border:2px dashed #15803d; "
                    "border-radius:10px;"
                )
                num_style = f"font-size:12px; font-weight:800; color:{num_fg};"
                sub_style = f"font-size:12px; margin-top:2px; color:{sub_fg};"
            else:
                inner_style = (
                    "min-height:40px; "
                    "display:flex; flex-direction:column; align-items:center; justify-content:center; "
                    "padding:2px 8px; "
                    "background:#f8fafc; "
                    "border:1px solid #e2e8f0; "
                    "border-radius:8px;"
                )
                num_style = "font-size:12px; font-weight:700; color:#64748b;"
                sub_style = "font-size:12px; margin-top:3px; color:#94a3b8;"

            row_cells.append(
                f"<td class='seg-mcol' data-seg-rank='{col_idx}' style='text-align:center; padding:0; border:0; background:#ffffff;'>"
                f"<div style='{inner_style}'>"
                f"<div style='{num_style}'>{val:+.1f}</div>"
                f"<div style='{sub_style}'>{beats} z {other_cnt_max} · #{row_rank}</div>"
                "</div>"
                "</td>"
            )

        row_cells.append("</tr>")
        body_rows.append("".join(row_cells))

    return (
            "<div style='max-width:1180px; margin:16px 0 0 0;'>"
            "<h4 style='margin:0 0 8px 0;'>Segmenty - przewagi naprawdę istotne</h4>"
            "<div style='display:flex; flex-wrap:wrap; gap:12px; align-items:stretch; margin-bottom:8px;'>"
            "<div style='flex:1 1 46%; border:1px solid #e2e8f0; border-radius:10px; padding:10px 12px; background:#ffffff; display:flex; align-items:flex-start;'>"
            "<div class='small' style='margin:0;'>"
            "Zaznaczamy tylko te pola, które jednocześnie: biją więcej niż 50% innych segmentów, "
            "są dodatnie oraz są TOP"
            f"{effective_top_rank}"
            " w wierszu albo mają wyraźną siłę wyniku. To odcina słabe, przypadkowe trafienia."
            "<br><br>"
            "Liczba pod wynikiem = ile innych segmentów dane pole przebija / ile jest wszystkich "
            "innych segmentów / pozycja w wierszu."
            "<br><br>"
            "Zmiana progów aktualizuje mapę i tę tabelę, a przy segment_hit_threshold_overrides "
            "raport przelicza także udział i N segmentów."
            "</div>"
            "</div>"
            "<div style='flex:1 1 46%; border:1px solid #e2e8f0; border-radius:10px; padding:10px 12px; background:#f8fafc;'>"
            "<div style='font-weight:800; margin:0 0 6px 0;'>Zmień wartości brzegowe segmentów</div>"
            "<div class='small' style='margin:0 0 8px 0;'>"
            "Edytuj klucz <span class='mono'>segment_hit_threshold_overrides</span> w pliku <span class='mono'>settings.json</span>, "
            "uruchom analizę ponownie i raport przeliczy tabelę oraz mapę przewag."
            "</div>"
            "<table style='width:100%; border-collapse:collapse; font-size:12px;'>"
            "<thead><tr>"
            "<th style='text-align:left; padding:5px 8px; border:1px solid #e5e7eb; background:#eef3f9;'>Reguła</th>"
            "<th style='text-align:center; padding:5px 8px; border:1px solid #e5e7eb; background:#eef3f9;'>Próg</th>"
            "</tr></thead>"
            "<tbody>" + "".join(active_rule_rows) + "</tbody>"
            "</table>"
            "<div class='small mono' style='margin:8px 0 0 0;'>"
            "Przykład: \"segment_hit_threshold_overrides\": {\"2 z 2 · #1\": 3.5}"
            "</div>"
            "</div>"
            "</div>"
            "<div style='overflow-x:auto;'>"
            "<table class='tbl' style='border-collapse:separate; border-spacing:0; width:100%; margin-top:6px;'>"
            "<thead>" + "".join(head_html) + "</thead>"
            "<tbody>" + "".join(body_rows) + "</tbody>"
            "</table>"
            "</div>"
            "</div>"
    )


# helper legacy _render_segment_advantage_matrix_html usunięty
# aktywna ścieżka macierzy korzysta wyłącznie z:
# - _render_segment_matrix_html()
# - _render_segment_smart_group_matrix_html()

def _render_segment_matrix_html(segs: List[Dict[str, Any]],
                                brand_values: Dict[str, str],
                                mode: str = "arche",
                                top_n: int = 5,
                                segment_threshold_overrides: Optional[Dict[Any, Any]] = None) -> str:
    """
    HTML-owa macierz segmentów PVQ-style:
    - kolumny = TOP segmenty
    - wiersze = archetypy / wartości
    - wielkość kropki = siła poziomu Pm w danym segmencie

    Pod spodem dokładamy Smart-group:
    - porównania między segmentami liczone są również na Pm,
    - sąsiadujące trafienia łączą się w jeden wspólny obrys.
    """
    segs = list(segs or [])
    if not segs:
        return "<div class='small'>Brak danych do macierzy segmentów.</div>"

    try:
        top_n = max(1, int(top_n))
    except Exception:
        top_n = 5

    segs = segs[:top_n]
    mode_values = (str(mode).lower() == "values")

    headers: List[str] = []
    all_abs_vals: List[float] = []

    for s in segs:
        nm_a, _nm_v = _segment_name_pair(s)
        headers.append(nm_a)

        pm = _segment_pm_vector(s)
        all_abs_vals.extend([abs(float(x)) for x in pm if np.isfinite(x)])

    max_abs = max(all_abs_vals) if all_abs_vals else 1.0
    if max_abs <= 1e-9:
        max_abs = 1.0

    k = len(segs)
    if k <= 5:
        col_min_w = 150
        label_col_w = 190
    elif k <= 7:
        col_min_w = 132
        label_col_w = 180
    elif k <= 9:
        col_min_w = 116
        label_col_w = 168
    else:
        col_min_w = 104
        label_col_w = 158

    head_html = [
        "<tr>",
        f"<th style='width:{label_col_w}px;'>{'Wartość' if mode_values else 'Archetyp'}</th>"
    ]
    for col_idx, h in enumerate(headers):
        pal = _segment_ui_colors(col_idx + 1)
        head_html.append(
            f"<th class='seg-mcol' data-seg-rank='{col_idx}' "
            f"style='text-align:center; min-width:{col_min_w}px; "
            f"background:{pal.get('soft', '#f8fafc')}; "
            f"color:{pal.get('chip_fg', '#334155')}; "
            f"border-bottom:2px solid {pal.get('line', '#d9dde3')};'>"
            f"{_html.escape(str(h))}"
            "</th>"
        )
    head_html.append("</tr>")

    body_rows: List[str] = []
    for a_idx, arch in enumerate(ARCHETYPES):
        row_label = brand_values.get(arch, arch) if mode_values else _display_archetype_label(arch)

        row_cells = [
            "<tr>",
            f"<td style='font-weight:700;'>{_html.escape(str(row_label))}</td>"
        ]

        for col_idx, s in enumerate(segs):
            pm = _segment_pm_vector(s)
            val = float(pm[a_idx]) if np.isfinite(pm[a_idx]) else 0.0

            rel = min(1.0, abs(val) / max_abs)
            if val >= 0:
                dot_size = int(round(10 + 26 * rel))
                dot_bg = "#16a34a" if rel >= 0.66 else "#0ea5e9" if rel >= 0.33 else "#cbd5e1"
                dot_bd = "#0f766e" if rel >= 0.33 else "#94a3b8"
                num_fg = "#111827"
            else:
                dot_size = int(round(8 + 18 * rel))
                dot_bg = "#f1f5f9"
                dot_bd = "#cbd5e1"
                num_fg = "#64748b"

            dot_html = (
                f"<span style='display:inline-block; width:{dot_size}px; height:{dot_size}px; "
                f"border-radius:50%; background:{dot_bg}; border:1px solid {dot_bd};'></span>"
            )

            row_cells.append(
                f"<td class='seg-mcol' data-seg-rank='{col_idx}' style='text-align:center;'>"
                "<div style='display:flex; align-items:center; justify-content:center; gap:8px;'>"
                f"{dot_html}"
                f"<span style='font-size:12px; color:{num_fg};'>{val:+.1f}</span>"
                "</div>"
                "</td>"
            )

        row_cells.append("</tr>")
        body_rows.append("".join(row_cells))

    matrix_subject = "każdej wartości" if mode_values else "każdego archetypu"
    base_html = (
            "<div style='max-width:1180px; margin:0;'>"
            "<div class='small' style='margin-bottom:8px;'>"
            f"Matryca segmentów: pokazuje surowy poziom Pm dla {matrix_subject} w danym segmencie. "
            "Im większa kropka, tym silniejszy wynik w segmencie."
            "</div>"
            "<div style='overflow-x:auto;'>"
            "<table class='tbl' style='margin-top:6px; width:100%;'>"
            "<thead>" + "".join(head_html) + "</thead>"
                                             "<tbody>" + "".join(body_rows) + "</tbody>"
                                                                              "</table>"
                                                                              "</div>"
                                                                              "</div>"
    )

    smart_html = _render_segment_smart_group_matrix_html(
        segs=segs,
        brand_values=brand_values,
        mode=mode,
        top_n=top_n,
        min_beats=3,
        min_gap=0.15,
        min_positive=0.10,
        strong_min=0.35,
        core_min=0.70,
        top_rank_limit=2,
        segment_threshold_overrides=segment_threshold_overrides
    )

    return base_html + smart_html


# usunięto build_kmeans_seg_pack() — aktywny raport używa build_meta_seg_pack(); build_lca_seg_pack() został tylko jako compat-wrapper

# usunięto _apply_lca_behavior_names_from_sig() — nazwy LCA nadaje _lca_behavioral_names()


def lca_signatures_table_dynamic(labels_ranked: np.ndarray,
                                 A: np.ndarray, d12: np.ndarray, b1: np.ndarray, b2: np.ndarray, d13: np.ndarray,
                                 w: np.ndarray, brand_values: Dict[str, str]) -> Tuple[
    str, str, Optional[pd.DataFrame]]:
    """
    Zwraca HTML tabel sygnatur (arche/values) dla LCA (dla wybranego k) + DataFrame źródłowy sygnatur.
    """
    try:
        df_sig = lca_signatures_table(A=A, d12=d12, b1=b1, b2=b2, d13=d13,
                                      weights=w, seg_id_lca=labels_ranked,
                                      ARCHETYPES=ARCHETYPES, A_PAIRS=A_PAIRS, D_ITEMS=D_ITEMS,
                                      A_center=float(A_SCALE_CENTER))
        hA = df_to_html_sig(df_sig, max_rows=10)
        hV = df_to_html_sig(df_display_values(df_sig, brand_values), max_rows=10)
        return hA, hV, df_sig
    except Exception:
        return (
            "<div class='small'>(Brak sygnatur — błąd w danych.)</div>",
            "<div class='small'>(Brak sygnatur — błąd w danych.)</div>",
            None,
        )


def build_lca_seg_pack(tab_key: str,
                       X_lca: np.ndarray, cards: List[int],
                       A: np.ndarray, d12: np.ndarray, b1: np.ndarray, b2: np.ndarray, d13: np.ndarray,
                       metry: Optional[pd.DataFrame],
                       P: np.ndarray, E: np.ndarray, G: np.ndarray, w: np.ndarray,
                       settings: Settings,
                       brand_values: Dict[str, str],
                       outdir: Path,
                       seed_offset: int = 0,
                       bubble_fname_base: Optional[str] = None) -> Dict[str, Any]:
    """
    COMPAT WRAPPER.

    Historyczna nazwa została zachowana wyłącznie po to, żeby nic starego nie wybuchło.
    Faktyczny silnik segmentacji NIE używa już LCA ani X_lca.

    Źródło prawdy:
    - profil P (12 archetypów)
    - meta-cechy z P
    - weighted k-means
    """
    _ = (X_lca, cards, A, d12, b1, b2, d13, bubble_fname_base)

    return build_meta_seg_pack(
        tab_key=tab_key,
        metry=metry,
        P=P,
        E=E,
        G=G,
        w=w,
        settings=settings,
        brand_values=brand_values,
        outdir=outdir,
        seed_offset=seed_offset,
    )


# usunięto build_segment_marketing_name() — aktywny pipeline używa _make_marketing_name_from_top3()


def _format_segment_demography_rows(metry: pd.DataFrame, seg_mask: np.ndarray, weights: np.ndarray) -> List[
    Dict[str, Any]]:
    """
    PVQ-style demografia segmentu:
    - udział w segmencie (%)
    - udział w próbie (%)
    - lift (pp) = seg% - próba%
    Zwraca listę rekordów posortowanych po |lift|.
    """
    if metry is None or len(metry) == 0:
        return []

    seg_mask = np.asarray(seg_mask, dtype=bool).reshape(-1)
    w = np.asarray(weights, dtype=float).reshape(-1)

    # bezpieczeństwo długości
    n = min(len(metry), len(seg_mask), len(w))
    if n <= 0:
        return []
    metry = metry.iloc[:n].copy()
    seg_mask = seg_mask[:n]
    w = w[:n]

    m_w = np.isfinite(w)
    total_w = float(w[m_w].sum())
    seg_w = float(w[m_w & seg_mask].sum())
    if total_w <= 0 or seg_w <= 0:
        return []

    rows: List[Dict[str, Any]] = []
    for col in _ordered_metry_columns(metry):
        for _cat_key, cat_label, cat_mask in _metry_column_categories(metry, col):
            m_cat = cat_mask & m_w
            w_all = float(w[m_cat].sum())
            w_seg_cat = float(w[m_cat & seg_mask].sum())

            pct_all = (w_all / total_w) * 100.0
            pct_seg = (w_seg_cat / seg_w) * 100.0
            lift_pp = pct_seg - pct_all

            rows.append({
                "zmienna": _metry_var_label(col),
                "kategoria": str(cat_label),
                "pct_seg": float(pct_seg),
                "pct_all": float(pct_all),
                "lift_pp": float(lift_pp),
            })

    rows.sort(
        key=lambda r: (-abs(float(r.get("lift_pp", 0.0))), str(r.get("zmienna", "")), -float(r.get("pct_seg", 0.0))))
    return rows


def _render_demografia_seg_panel(segs: List[Dict[str, Any]], city_label: str = "Poznań / próba") -> str:
    segs = [dict(s) for s in (segs or []) if isinstance(s, dict)]
    if not segs:
        return (
            "<div class='card'>"
            "<div class='small'>Brak danych do zakładki Demografia_Seg.</div>"
            "</div>"
        )

    segs = sorted(
        segs,
        key=lambda s: int(_safe_float(s.get("segment_rank", s.get("segment_id", 0))))
    )

    seg_labels: List[str] = []
    seg_titles: Dict[str, str] = {}
    seg_colors: Dict[str, Dict[str, str]] = {}
    seg_maps: Dict[str, Dict[Tuple[str, str], float]] = {}
    probe_map: Dict[Tuple[str, str], float] = {}

    for idx, s in enumerate(segs):
        seg_rank = int(_safe_float(s.get("segment_rank", s.get("segment_id", idx))))
        seg_label = str(s.get("segment_label", s.get("segment", f"Seg_{seg_rank + 1}")))

        seg_name_arche, _seg_name_values = _segment_name_pair(s)
        seg_title = str(seg_name_arche or s.get("name_arche") or seg_label)

        seg_labels.append(seg_label)
        seg_titles[seg_label] = seg_title
        seg_colors[seg_label] = _segment_ui_colors(seg_rank + 1)

        local_map: Dict[Tuple[str, str], float] = {}
        for r in _segment_demography_rows(s):
            zm = str(r.get("zmienna", "")).strip()
            kat = str(r.get("kategoria", "")).strip()
            if not zm or not kat:
                continue

            key = (zm, kat)
            local_map[key] = max(0.0, min(100.0, _safe_float(r.get("pct_seg", 0.0))))

            if key not in probe_map:
                probe_map[key] = max(0.0, min(100.0, _safe_float(r.get("pct_all", 0.0))))

        seg_maps[seg_label] = local_map

    schema_rows: List[Dict[str, Any]] = []
    for (zm, kat), _pct in probe_map.items():
        schema_rows.append({"zmienna": zm, "kategoria": kat})
    for seg_label in seg_labels:
        for (zm, kat), _pct in seg_maps.get(seg_label, {}).items():
            schema_rows.append({"zmienna": zm, "kategoria": kat})
    demo_schema = _build_demo_schema_from_rows(schema_rows)
    var_order = list(demo_schema.get("var_order") or [])
    cat_order = dict(demo_schema.get("cat_order") or {})

    def _ordered_categories(var_name: str) -> List[str]:
        return list(cat_order.get(var_name, []))

    def _max_cat_for_probe(var_name: str, cats: List[str]) -> str:
        best_cat = ""
        best_val = -1.0
        for cat in cats:
            val = float(probe_map.get((var_name, cat), 0.0))
            if val > best_val:
                best_val = val
                best_cat = cat
        return best_cat

    def _max_cat_for_seg(var_name: str, cats: List[str], seg_label: str) -> str:
        best_cat = ""
        best_val = -1.0
        local = seg_maps.get(seg_label, {})
        for cat in cats:
            val = float(local.get((var_name, cat), 0.0))
            if val > best_val:
                best_val = val
                best_cat = cat
        return best_cat

    def _bar_td(
            pct: float,
            fill: str,
            highlight: bool = False,
            bold_pct: bool = False,
            thick_top: bool = False,
            thick_left: bool = False,
            pct_decimals: int = 0
    ) -> str:
        pct = max(0.0, min(100.0, float(pct)))

        # Bez przerywanych obwódek: nie wyróżniamy kategorii ramką (tylko pogrubieniem %).
        _ = highlight
        border = "1px solid #dfe4ea"

        top_border = "3px solid #b8c2cc" if thick_top else border
        left_border = "3px solid #b8c2cc" if thick_left else border

        pct_fw = "900" if bold_pct else "500"
        if int(pct_decimals) <= 0:
            pct_txt = f"{pct:.0f}%"
        else:
            pct_txt = f"{pct:.1f}%"

        return (
            f"<td style='min-width:126px; padding:0; border:{border}; border-top:{top_border}; border-left:{left_border}; background:#fff;'>"
            "<div style='position:relative; height:34px; background:#ffffff;'>"
            f"<div style='position:absolute; left:0; top:0; bottom:0; width:{pct:.1f}%; background:{fill};'></div>"
            f"<span style='position:absolute; right:6px; top:7px; z-index:2; background:rgba(255,255,255,0.88); padding:1px 5px; border-radius:4px; font-size:12px; font-weight:{pct_fw}; color:#111;'>{pct_txt}</span>"
            "</div>"
            "</td>"
        )

    head_cells = [
        "<tr>",
        "<th style='min-width:140px; border-top:3px solid #b8c2cc; border-left:3px solid #b8c2cc;'>Zmienna</th>",
        "<th style='min-width:210px; border-top:3px solid #b8c2cc;'>Kategoria</th>",
        f"<th style='min-width:140px; text-align:center; border-top:3px solid #b8c2cc;'>{html.escape(str(city_label))}</th>",
    ]

    for seg_label in seg_labels:
        palette = seg_colors.get(seg_label, {})
        head_cells.append(
            "<th style='min-width:140px; text-align:center; vertical-align:bottom; border-top:3px solid #b8c2cc; border-left:3px solid #b8c2cc;'>"
            f"<div style='font-size:11px; color:#6b7280; font-weight:800; margin-bottom:4px;'>{html.escape(seg_label)}</div>"
            f"<div style='padding:8px 8px; border:1px solid {html.escape(str(palette.get('line', '#dfe4ea')))}; "
            f"background:{html.escape(str(palette.get('soft', '#f8f9fa')))}; color:#111; font-weight:900; line-height:1.25;'>"
            f"{html.escape(seg_titles.get(seg_label, seg_label))}"
            "</div>"
            "</th>"
        )
    head_cells.append("</tr>")

    body_rows: List[str] = []


    for var_name in var_order:
        cats = _ordered_categories(var_name)
        if not cats:
            continue

        probe_best = _max_cat_for_probe(var_name, cats)
        seg_best = {seg_label: _max_cat_for_seg(var_name, cats, seg_label) for seg_label in seg_labels}

        first_row = True
        for cat in cats:
            row_cells = ["<tr>"]
            if first_row:
                icon = _demo_pick_var_icon(var_name)
                row_cells.append(
                    f"<td rowspan='{len(cats)}' style='font-weight:700; text-transform:uppercase; vertical-align:middle; background:#fafafa; border-top:3px solid #b8c2cc; border-left:3px solid #b8c2cc;'>"
                    f"{icon} {html.escape(var_name)}"
                    "</td>"
                )
            else:
                row_cells[0] = "<tr>"

            cat_icon = _demo_pick_cat_icon(var_name, cat)
            row_cells.append(
                f"<td style='font-weight:700; border-top:{'3px solid #b8c2cc' if first_row else '1px solid #dfe4ea'};'>"
                f"<span style='display:inline-flex; align-items:center; gap:6px;'><span>{html.escape(cat_icon)}</span><span>{html.escape(cat)}</span></span>"
                "</td>"
            )

            row_cells.append(
                _bar_td(
                    probe_map.get((var_name, cat), 0.0),
                    "#cfd6df",
                    highlight=False,
                    bold_pct=False,
                    thick_top=first_row,
                    thick_left=False,
                    pct_decimals=1
                )
            )

            for seg_label in seg_labels:
                accent = str(seg_colors.get(seg_label, {}).get("accent", "#4c6ef5"))
                pct = seg_maps.get(seg_label, {}).get((var_name, cat), 0.0)
                row_cells.append(
                    _bar_td(
                        pct,
                        accent,
                        highlight=False,
                        bold_pct=(cat == seg_best.get(seg_label)),
                        thick_top=first_row,
                        thick_left=True
                    )
                )

            row_cells.append("</tr>")
            body_rows.append("".join(row_cells))
            first_row = False

    return (
            "<div class='card'>"
            "<div class='small' style='margin-bottom:10px;'>"
            "Układ zbiorczy: wszystkie zmienne i wszystkie dostępne kategorie w wierszach; "
            "kolumny pokazują próbę oraz segmenty. Długość paska = odsetek 0–100%."
            "</div>"
            "<div style='overflow-x:auto;'>"
            "<table class='tbl' style='margin-top:6px; width:auto; min-width:100%; border:3px solid #b8c2cc;'>"
            "<thead>" + "".join(head_cells) + "</thead>"
                                              "<tbody>" + "".join(body_rows) + "</tbody>"
                                                                               "</table>"
                                                                               "</div>"
                                                                               "</div>"
    )

def _format_demography_rows_between_masks(
        metry: pd.DataFrame,
        group_mask: np.ndarray,
        base_mask: np.ndarray,
        weights: np.ndarray
) -> List[Dict[str, Any]]:
    """
    Liczy profil demograficzny grupy (group_mask) względem bazy odniesienia (base_mask).
    Dzięki temu możemy porównać archetyp:
    - do całej próby (segment=ALL),
    - albo do konkretnego segmentu (segment=Seg_X).
    """
    if metry is None or len(metry) == 0:
        return []

    group_mask = np.asarray(group_mask, dtype=bool).reshape(-1)
    base_mask = np.asarray(base_mask, dtype=bool).reshape(-1)
    w = np.asarray(weights, dtype=float).reshape(-1)

    n = min(len(metry), len(group_mask), len(base_mask), len(w))
    if n <= 0:
        return []

    metry = metry.iloc[:n].copy()
    group_mask = group_mask[:n]
    base_mask = base_mask[:n]
    w = w[:n]

    m_w = np.isfinite(w) & (w > 0)
    base_w = float(w[m_w & base_mask].sum())
    group_w = float(w[m_w & group_mask].sum())

    if base_w <= 0 or group_w <= 0:
        return []

    rows: List[Dict[str, Any]] = []
    for col in _ordered_metry_columns(metry):
        for _cat_key, cat_label, cat_mask in _metry_column_categories(metry, col):
            m_cat = cat_mask & m_w
            w_base_cat = float(w[m_cat & base_mask].sum())
            w_group_cat = float(w[m_cat & group_mask].sum())

            pct_all = (w_base_cat / base_w) * 100.0
            pct_seg = (w_group_cat / group_w) * 100.0
            lift_pp = pct_seg - pct_all

            rows.append({
                "zmienna": _metry_var_label(col),
                "kategoria": str(cat_label),
                "pct_seg": float(pct_seg),
                "pct_all": float(pct_all),
                "lift_pp": float(lift_pp),
            })

    return rows


def _build_b2_declared_demo_payload(
        metry: pd.DataFrame,
        b2: np.ndarray,
        weights: np.ndarray,
        labels_ranked: Optional[np.ndarray] = None,
        seg_profiles: Optional[List[Dict[str, Any]]] = None,
        cluster_labels_ranked: Optional[np.ndarray] = None,
        cluster_profiles: Optional[List[Dict[str, Any]]] = None,
        brand_values: Optional[Dict[str, str]] = None,
        city_label: str = "Poznań / próba",
) -> Dict[str, Any]:
    demo_schema = _build_metry_demo_schema(metry)
    var_order: List[str] = list(demo_schema.get("var_order") or [])
    cat_order: Dict[str, List[str]] = dict(demo_schema.get("cat_order") or {})
    var_icons: Dict[str, str] = dict(demo_schema.get("var_icons") or {})
    cat_icons: Dict[str, str] = dict(demo_schema.get("cat_icons") or {})

    value_map = {a: str((brand_values or {}).get(a, a)) for a in ARCHETYPES}

    base_payload: Dict[str, Any] = {
        "order": list(ARCHETYPES),
        "items": {},
        "segments": [{
            "key": "ALL",
            "rank": -1,
            "label": "Wszystkie segmenty",
            "name_arche": "Wszystkie segmenty",
            "name_values": "Wszystkie segmenty",
        }],
        "value_map": value_map,
        "var_order": var_order,
        "cat_order": cat_order,
        "var_icons": var_icons,
        "cat_icons": cat_icons,
        "city_label": str(city_label),
    }

    if metry is None or len(metry) == 0 or b2 is None:
        return base_payload

    b2_arr = np.asarray(b2, dtype=int).reshape(-1)
    w = np.asarray(weights, dtype=float).reshape(-1)

    labels_arr: Optional[np.ndarray] = None
    cluster_labels_arr: Optional[np.ndarray] = None
    if labels_ranked is not None:
        try:
            labels_try = np.asarray(labels_ranked, dtype=int).reshape(-1)
            if labels_try.size > 0:
                labels_arr = labels_try
        except Exception:
            labels_arr = None
    if cluster_labels_ranked is not None:
        try:
            labels_try = np.asarray(cluster_labels_ranked, dtype=int).reshape(-1)
            if labels_try.size > 0:
                cluster_labels_arr = labels_try
        except Exception:
            cluster_labels_arr = None

    lens = [len(metry), len(b2_arr), len(w)]
    if labels_arr is not None:
        lens.append(len(labels_arr))
    if cluster_labels_arr is not None:
        lens.append(len(cluster_labels_arr))
    n = min(lens)
    if n <= 0:
        return base_payload

    metry_n = metry.iloc[:n].copy()
    b2_arr = b2_arr[:n]
    w = w[:n]
    if labels_arr is not None:
        labels_arr = labels_arr[:n]
    if cluster_labels_arr is not None:
        cluster_labels_arr = cluster_labels_arr[:n]

    valid = (b2_arr >= 0) & (b2_arr < len(ARCHETYPES)) & np.isfinite(w) & (w > 0)

    seg_name_arche: Dict[int, str] = {}
    seg_name_values: Dict[int, str] = {}
    for s in (seg_profiles or []):
        if not isinstance(s, dict):
            continue
        try:
            sid = int(float(s.get("segment_rank", s.get("segment_id", -1))))
        except Exception:
            sid = -1
        if sid < 0:
            continue
        nm_a, _nm_v = _segment_name_pair(s)
        seg_name_arche[sid] = str(nm_a or f"Seg_{sid + 1}")
        seg_name_values[sid] = str(seg_name_arche[sid])

    cluster_name_arche: Dict[int, str] = {}
    cluster_name_values: Dict[int, str] = {}
    for s in (cluster_profiles or []):
        if not isinstance(s, dict):
            continue
        try:
            sid = int(float(s.get("segment_rank", s.get("segment_id", -1))))
        except Exception:
            sid = -1
        if sid < 0:
            continue
        nm_a, nm_v = _segment_name_pair(s)
        cluster_name_arche[sid] = str(nm_a or f"SS_{sid + 1}")
        cluster_name_values[sid] = str(nm_v or cluster_name_arche[sid])

    base_masks: Dict[str, np.ndarray] = {"ALL": valid.copy()}

    if labels_arr is not None and labels_arr.shape[0] == n:
        seg_ids = [int(x) for x in np.unique(labels_arr) if int(x) >= 0]
        seg_ids = sorted(seg_ids)
        for sid in seg_ids:
            seg_key = f"Seg_{sid + 1}"
            seg_mask = valid & (labels_arr == sid)
            if not np.any(seg_mask):
                continue
            base_masks[seg_key] = seg_mask
            base_payload["segments"].append({
                "key": seg_key,
                "rank": int(sid),
                "label": seg_key,
                "name_arche": seg_name_arche.get(sid, seg_key),
                "name_values": seg_name_values.get(sid, seg_name_arche.get(sid, seg_key)),
            })

    if cluster_labels_arr is not None and cluster_labels_arr.shape[0] == n:
        cluster_ids = [int(x) for x in np.unique(cluster_labels_arr) if int(x) >= 0]
        cluster_ids = sorted(cluster_ids)
        for sid in cluster_ids:
            seg_key = f"SS_{sid + 1}"
            seg_mask = valid & (cluster_labels_arr == sid)
            if not np.any(seg_mask):
                continue
            base_masks[seg_key] = seg_mask
            base_payload["segments"].append({
                "key": seg_key,
                "rank": int(sid),
                "label": seg_key,
                "name_arche": cluster_name_arche.get(sid, seg_key),
                "name_values": cluster_name_values.get(sid, cluster_name_arche.get(sid, seg_key)),
            })

    def _nk(x: Any) -> str:
        return " ".join(str(x or "").split()).strip().lower()

    var_pos = {_nk(v): i for i, v in enumerate(var_order)}
    cat_pos = {
        _nk(v): {_nk(c): i for i, c in enumerate(cats)}
        for v, cats in cat_order.items()
    }

    def _sort_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return sorted(
            rows,
            key=lambda rr: (
                var_pos.get(_nk(rr.get("zmienna", "")), 999),
                cat_pos.get(_nk(rr.get("zmienna", "")), {}).get(_nk(rr.get("kategoria", "")), 999),
                -float(rr.get("pct_seg", 0.0)),
                str(rr.get("kategoria", "")),
            )
        )

    for idx, arche in enumerate(ARCHETYPES):
        per_segment: Dict[str, Any] = {}

        for seg_def in base_payload["segments"]:
            seg_key = str(seg_def.get("key", "ALL"))
            base_mask = np.asarray(base_masks.get(seg_key, valid), dtype=bool)
            group_mask = base_mask & (b2_arr == idx)

            rows = _format_demography_rows_between_masks(
                metry=metry_n,
                group_mask=group_mask,
                base_mask=base_mask,
                weights=w,
            )
            rows = _sort_rows(rows)

            positive_rows = [r for r in rows if float(r.get("lift_pp", 0.0)) > 0.0]
            best_positive = None
            if positive_rows:
                best0 = max(positive_rows, key=lambda rr: float(rr.get("lift_pp", 0.0)))
                best_positive = {
                    "zmienna": str(best0.get("zmienna", "")),
                    "kategoria": str(best0.get("kategoria", "")),
                    "lift_pp": round(float(best0.get("lift_pp", 0.0)), 1),
                }

            w_base = float(w[base_mask].sum()) if np.any(base_mask) else 0.0
            w_group = float(w[group_mask].sum()) if np.any(group_mask) else 0.0
            share_pct = (w_group / w_base * 100.0) if w_base > 0 else 0.0

            per_segment[seg_key] = {
                "archetyp": arche,
                "segment_key": seg_key,
                "n_raw": int(np.sum(group_mask)),
                "base_n_raw": int(np.sum(base_mask)),
                "share_pct": round(float(share_pct), 2),
                "rows": [
                    {
                        "zmienna": str(r.get("zmienna", "")),
                        "kategoria": str(r.get("kategoria", "")),
                        "pct_seg": round(float(r.get("pct_seg", 0.0)), 1),
                        "pct_all": round(float(r.get("pct_all", 0.0)), 1),
                        "lift_pp": round(float(r.get("lift_pp", 0.0)), 1),
                    }
                    for r in rows
                ],
                "best_positive": best_positive,
            }

        base_payload["items"][arche] = per_segment

    return base_payload


def _build_top5_simulation_payload(
        metry: pd.DataFrame,
        b1: np.ndarray,
        weights: np.ndarray,
        b2: np.ndarray,
        d13: np.ndarray,
        brand_values: Optional[Dict[str, str]] = None,
        city_label: str = "Poznań / próba",
        population_15_plus: float = 0.0,
) -> Dict[str, Any]:
    """
    Symulacja oparta o składanie singli (bez progów odcięcia):
    - single(v) = B1(v) * (0.60 + 0.30*B2(v) + 0.10*D13(v)),
    - combo(1..3) = 1 - Π(1 - single(v)).

    Główna miara to Zasięg (% mieszkańców 15+).
    Dodatkowo raportujemy:
    - Siłę priorytetu (0-100),
    - Potencjał kampanijny (0-100),
    - Rdzeń mobilizacyjny (0-100).
    """
    from itertools import combinations

    demo_schema = _build_metry_demo_schema(metry)
    var_order: List[str] = list(demo_schema.get("var_order") or [])
    cat_order: Dict[str, List[str]] = dict(demo_schema.get("cat_order") or {})
    var_icons: Dict[str, str] = dict(demo_schema.get("var_icons") or {})
    cat_icons: Dict[str, str] = dict(demo_schema.get("cat_icons") or {})

    pop15 = _safe_float(population_15_plus)
    if not np.isfinite(pop15) or pop15 <= 0:
        pop15 = 0.0

    value_map = {a: str((brand_values or {}).get(a, a)) for a in ARCHETYPES}
    b1_base = 0.60
    b2_boost = 0.30
    d13_boost = 0.10
    strength_weight_b2 = 0.70
    strength_weight_d13 = 0.30
    coalition_base = 0.60
    coalition_strength_weight = 0.40

    base_payload: Dict[str, Any] = {
        "order": list(ARCHETYPES),
        "items": {},
        "value_map": value_map,
        "var_order": var_order,
        "cat_order": cat_order,
        "var_icons": var_icons,
        "cat_icons": cat_icons,
        "city_label": str(city_label),
        "population_15_plus": float(pop15),
        "model": {
            "single_formula": "B1 * (0.60 + 0.30*B2 + 0.10*D13)",
            "combine_formula": "1 - Π(1 - single)",
            "single_weights": {
                "B1_base": float(b1_base),
                "B2_boost": float(b2_boost),
                "D13_boost": float(d13_boost),
            },
            "strength_weights": {
                "B2": float(strength_weight_b2),
                "D13": float(strength_weight_d13),
            },
            "campaign_formula": "reach * (0.60 + 0.40*strength)",
            "mobilization_formula": "reach * strength",
        },
    }

    if metry is None or len(metry) == 0 or b1 is None or b2 is None or d13 is None:
        return base_payload

    b1_arr = np.asarray(b1, dtype=float)
    w = np.asarray(weights, dtype=float).reshape(-1)
    try:
        b2_arr = np.asarray(b2, dtype=int).reshape(-1)
    except Exception:
        b2_arr = np.full(len(b1_arr), -1, dtype=int)
    try:
        d13_arr = np.asarray(d13, dtype=int).reshape(-1)
    except Exception:
        d13_arr = np.full(len(b1_arr), -1, dtype=int)

    if b1_arr.ndim != 2 or b1_arr.shape[1] != len(ARCHETYPES):
        return base_payload

    n = min(len(metry), int(b1_arr.shape[0]), len(w), len(b2_arr), len(d13_arr))
    if n <= 0:
        return base_payload

    metry_n = metry.iloc[:n].copy()
    b1_arr = b1_arr[:n, :]
    w = w[:n]
    b2_arr = b2_arr[:n]
    d13_arr = d13_arr[:n]

    b1_hit = np.where(np.isfinite(b1_arr), b1_arr, 0.0)
    b1_hit = (b1_hit > 0.5).astype(float)

    need_axis_by_idx = {
        int(i): str(ARCHETYPE_NEED_AXIS.get(ARCHETYPES[i], "") or "")
        for i in range(len(ARCHETYPES))
    }

    d13_component_by_idx: Dict[int, np.ndarray] = {}
    for i in range(len(ARCHETYPES)):
        axis_i = need_axis_by_idx.get(int(i), "")
        exact = (d13_arr == int(i))
        if axis_i:
            axis_match = np.array([
                (0 <= int(v) < len(ARCHETYPES))
                and (need_axis_by_idx.get(int(v), "") == axis_i)
                and (int(v) != int(i))
                for v in d13_arr
            ], dtype=bool)
        else:
            axis_match = np.zeros(n, dtype=bool)
        d13_component_by_idx[int(i)] = np.where(exact, 1.0, np.where(axis_match, 0.5, 0.0))

    valid = np.isfinite(w) & (w > 0)
    base_mask = valid.copy()

    w_base = float(np.sum(w[base_mask])) if np.any(base_mask) else 0.0
    if w_base <= 0.0:
        return base_payload

    def _nk(x: Any) -> str:
        return " ".join(str(x or "").split()).strip().lower()

    var_pos = {_nk(v): i for i, v in enumerate(var_order)}
    cat_pos = {
        _nk(v): {_nk(c): i for i, c in enumerate(cats)}
        for v, cats in cat_order.items()
    }

    def _sort_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return sorted(
            rows,
            key=lambda rr: (
                var_pos.get(_nk(rr.get("zmienna", "")), 999),
                cat_pos.get(_nk(rr.get("zmienna", "")), {}).get(_nk(rr.get("kategoria", "")), 999),
                -float(rr.get("pct_seg", 0.0)),
                str(rr.get("kategoria", "")),
            )
        )

    for r in (1, 2, 3):
        for combo in combinations(range(len(ARCHETYPES)), r):
            idx = np.asarray(combo, dtype=int)

            combo_non_hit = np.ones(n, dtype=float)
            d13_best = np.zeros(n, dtype=float)

            for j in idx:
                b2_j = (b2_arr == int(j)).astype(float)
                d13_j = d13_component_by_idx.get(int(j), np.zeros(n, dtype=float))
                single = b1_hit[:, int(j)] * (b1_base + b2_boost * b2_j + d13_boost * d13_j)
                single = np.clip(single, 0.0, 1.0)
                combo_non_hit *= (1.0 - single)
                d13_best = np.maximum(d13_best, d13_j)

            combo_score = np.clip(1.0 - combo_non_hit, 0.0, 1.0)
            combo_score = np.where(base_mask, combo_score, 0.0)
            group_mask = base_mask & (combo_score > 1e-12)

            weighted_combo_sum = float(np.sum(w * combo_score))
            share_pct = (weighted_combo_sum / w_base * 100.0) if w_base > 0 else 0.0

            eff_w = w * combo_score
            eff_w_sum = float(np.sum(eff_w))
            b2_any = np.isin(b2_arr, idx).astype(float)
            if eff_w_sum > 0.0:
                b2_power = float(np.sum(eff_w * b2_any) / eff_w_sum)
                d13_power = float(np.sum(eff_w * d13_best) / eff_w_sum)
            else:
                b2_power = 0.0
                d13_power = 0.0

            priority_strength = (
                strength_weight_b2 * b2_power
                + strength_weight_d13 * d13_power
            )
            priority_strength = float(np.clip(priority_strength, 0.0, 1.0))

            mobilization_core_pct = float(share_pct * priority_strength)
            campaign_potential_pct = float(
                share_pct * (coalition_base + coalition_strength_weight * priority_strength)
            )

            rows = _format_demography_rows_between_masks(
                metry=metry_n,
                group_mask=group_mask,
                base_mask=base_mask,
                weights=w,
            )
            rows = _sort_rows(rows)

            positive_rows = [rr for rr in rows if float(rr.get("lift_pp", 0.0)) > 0.0]
            best_positive = None
            if positive_rows:
                best0 = max(positive_rows, key=lambda rr: float(rr.get("lift_pp", 0.0)))
                best_positive = {
                    "zmienna": str(best0.get("zmienna", "")),
                    "kategoria": str(best0.get("kategoria", "")),
                    "lift_pp": round(float(best0.get("lift_pp", 0.0)), 1),
                }

            w_group_hard = float(np.sum(w[group_mask])) if np.any(group_mask) else 0.0
            hard_group_share_pct = (w_group_hard / w_base * 100.0) if w_base > 0 else 0.0
            est_pop = int(round((share_pct / 100.0) * pop15)) if pop15 > 0 else None

            key = "|".join(str(int(i)) for i in combo)
            base_payload["items"][key] = {
                "selected_arche": [ARCHETYPES[int(i)] for i in combo],
                "n_raw": int(np.sum(group_mask)),
                "base_n_raw": int(np.sum(base_mask)),
                "share_pct": round(float(share_pct), 2),
                "reach_pct": round(float(share_pct), 2),
                "priority_strength_idx": round(float(priority_strength * 100.0), 2),
                "campaign_potential_idx": round(float(campaign_potential_pct), 2),
                "mobilization_core_idx": round(float(mobilization_core_pct), 2),
                "b2_power_pct": round(float(b2_power * 100.0), 2),
                "d13_power_pct": round(float(d13_power * 100.0), 2),
                "hard_group_share_pct": round(float(hard_group_share_pct), 2),
                "est_pop_15": est_pop,
                "rows": [
                    {
                        "zmienna": str(rr.get("zmienna", "")),
                        "kategoria": str(rr.get("kategoria", "")),
                        "pct_seg": round(float(rr.get("pct_seg", 0.0)), 1),
                        "pct_all": round(float(rr.get("pct_all", 0.0)), 1),
                        "lift_pp": round(float(rr.get("lift_pp", 0.0)), 1),
                    }
                    for rr in rows
                ],
                "best_positive": best_positive,
            }

    return base_payload


def _render_top5_simulation_panel(payload: Dict[str, Any], city_label: str = "Poznań / próba") -> str:
    payload = dict(payload or {})

    order = [str(x) for x in (payload.get("order") or []) if str(x) in ARCHETYPES]
    if not order:
        order = list(ARCHETYPES)

    payload_obj = {
        "order": order,
        "items": payload.get("items") or {},
        "value_map": payload.get("value_map") or {a: a for a in ARCHETYPES},
        "opposing_pairs": [
            [str(a), str(b)]
            for a, b in SEG_FORBIDDEN_ARCHETYPE_PAIRS
            if str(a) in ARCHETYPES and str(b) in ARCHETYPES
        ],
        "var_order": payload.get("var_order") or list(_DEMO_CORE_VAR_ORDER),
        "cat_order": payload.get("cat_order") or {},
        "var_icons": payload.get("var_icons") or {},
        "cat_icons": payload.get("cat_icons") or {},
        "city_label": str(payload.get("city_label") or city_label),
        "population_15_plus": float(_safe_float(payload.get("population_15_plus", 0.0))),
    }

    payload_json = json.dumps(payload_obj, ensure_ascii=False).replace("</", "<\\/")
    city_json = json.dumps(str(city_label), ensure_ascii=False)

    tpl = """
    <style>
      .simx-hero {
        border: 1px solid #d4dbe5;
        border-radius: 12px;
        padding: 12px 14px;
        background: linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%);
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.9);
      }
      .simx-kicker {
        font-size: 11px;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: .04em;
        color: #5f6b7a;
      }
      .simx-title {
        margin-top: 3px;
        font-size: 22px;
        font-weight: 900;
        color: #0f172a;
      }
      .simx-controls {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        align-items: center;
        margin-top: 10px;
      }
      .simx-controls label {
        font-weight: 800;
      }
      .simx-controls select,
      .simx-controls button {
        padding: 7px 10px;
        border: 1px solid #cbd5e1;
        border-radius: 9px;
        background: #fff;
        font-weight: 700;
      }
      .simx-controls button {
        cursor: pointer;
      }
      .simx-controls button.alt {
        color: #9a3412;
        border-color: #f4c7b4;
        background: #fff7ed;
      }
      .simx-alert {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        margin-top: 8px;
        padding: 6px 10px;
        border: 1px solid #fecaca;
        border-radius: 10px;
        background: #fff1f2;
        color: #9f1239;
        font-size: 12px;
        font-weight: 900;
      }
      .simx-metrics {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 10px;
      }
      .simx-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 10px;
        border: 1px solid #d0d7de;
        border-radius: 999px;
        background: #fff;
        font-size: 12px;
        font-weight: 800;
      }
      .simx-pill-reach {
        border-color: #93c5fd;
        background: #eff6ff;
        color: #1e3a8a;
      }
      .simx-tiles {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(175px, 1fr));
        gap: 8px;
        margin: 10px 0 12px 0;
      }
      .simx-tile {
        border: 1px solid #dbe4ef;
        border-radius: 10px;
        background: #fff;
        padding: 8px 10px;
      }
      .simx-tile-k {
        font-size: 11px;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: .03em;
        color: #5f6b7a;
      }
      .simx-tile-v {
        margin-top: 2px;
        font-size: 14px;
        font-weight: 900;
        color: #111827;
      }
      .simx-tile-s {
        margin-top: 2px;
        font-size: 12px;
        color: #3f4954;
      }
          .simx-root .simx-hero {
        border-color: #f2c27a !important;
        background: linear-gradient(180deg, #fff7ed 0%, #ffedd5 100%) !important;
      }
      .simx-root .simx-kicker { color: #9a3412 !important; }
      .simx-root .simx-title { color: #7c2d12 !important; }
      .simx-root .simx-controls select,
      .simx-root .simx-controls button {
        border-color: #f2c27a !important;
        background: #fffdf7 !important;
      }
      .simx-root .simx-controls button.alt {
        color: #9f1239 !important;
        border-color: #f8b4c7 !important;
        background: #fff1f2 !important;
      }
      .simx-root .simx-pill {
        border-color: #f2c27a !important;
        background: #fff8eb !important;
        color: #7c2d12 !important;
      }
      .simx-root .simx-pill-reach {
        border-color: #93c5fd !important;
        background: #eff6ff !important;
        color: #1e3a8a !important;
      }
      .simx-root .simx-tile {
        border-color: #f6cf96 !important;
        background: #fffdf7 !important;
      }
      .simx-root .simx-tile-k,
      .simx-root .simx-tile-s { color: #7c2d12 !important; }
    </style>

    <div class='card simx-root'>
      <div class='simx-hero'>
        <div class='simx-kicker'>Centrum Strategii Demograficznej</div>
        <div class='simx-title'><span class='mode-arche'>Symulacja segmentów dla archetypów</span><span class='mode-values'>Symulacja segmentów dla wartości</span></div>
        <div class='small' style='margin-top:4px;'>
          Model potencjału: <span class='mono'>single = B1 * (0.60 + 0.30*B2 + 0.10*D13)</span>,
          a dla 2-3 wyborów <span class='mono'>1 - Π(1 - single)</span>.
        </div>

        <div class='simx-controls'>
          <label for='simx_arche_1'><span class='mode-arche'>Archetyp</span><span class='mode-values'>Wartość</span> #1:</label>
          <select id='simx_arche_1'></select>

          <button type='button' id='simx_add_2'>+ dodaj drugi</button>

          <span id='simx_wrap_2' style='display:none;'>
            <label for='simx_arche_2'><span class='mode-arche'>Archetyp</span><span class='mode-values'>Wartość</span> #2:</label>
            <select id='simx_arche_2'></select>
            <button type='button' class='alt' id='simx_remove_2'>usuń</button>
            <button type='button' id='simx_add_3'>+ dodaj trzeci</button>
          </span>

          <span id='simx_wrap_3' style='display:none;'>
            <label for='simx_arche_3'><span class='mode-arche'>Archetyp</span><span class='mode-values'>Wartość</span> #3:</label>
            <select id='simx_arche_3'></select>
            <button type='button' class='alt' id='simx_remove_3'>usuń</button>
          </span>
        </div>

        <div id='simx_conflict_alert' class='simx-alert' style='display:none;'></div>

        <div class='simx-metrics'>
          <span id='simx_selected' class='simx-pill'></span>
          <span id='simx_reach' class='simx-pill simx-pill-reach' title='Zasięg (% mieszkańców): średni poziom dopasowania wartości w całej populacji 15+.'></span>
          <span id='simx_hard' class='simx-pill' title='Twarda grupa (%): odsetek mieszkańców 15+, którzy wpadają do grupy po prostym warunku wejścia, bez ważenia siłą dopasowania.'></span>
          <span id='simx_strength' class='simx-pill' title='Siła priorytetu (0-100): jak mocno osoby z zasięgu wskazują te wartości jako TOP1 (B2) i potwierdzają je doświadczeniowo (D13).'></span>
          <span id='simx_campaign' class='simx-pill' title='Potencjał kampanijny (0-100): zasięg skorygowany o siłę priorytetu; główny wskaźnik do rankingu segmentów.'></span>
          <span id='simx_mobil' class='simx-pill' title='Rdzeń mobilizacyjny (0-100): część zasięgu o największej gotowości reakcji na komunikat wartościowy.'></span>
          <span id='simx_n' class='simx-pill'></span>
          <span id='simx_base' class='simx-pill'></span>
          <span id='simx_est_pop' class='simx-pill'></span>
        </div>
      </div>

      <div class='seg-box' style='margin-bottom:10px;'>
        <div class='seg-mini-label'>📌 Statystyczny profil demograficzny grupy</div>
        <div id='simx_tiles' class='simx-tiles'></div>
        <div id='simx_hint' class='small' style='margin:2px 0 0 0;'></div>
      </div>

      <div class='seg-box'>
        <div class='seg-mini-label'>👥 Profil demograficzny grupy</div>
        <div style='color:#5f6b7a; font-size:12px; margin:2px 0 6px 0;'>
          W tabeli pogrubiona najwyższa kategoria w każdej zmiennej.
        </div>

        <div style='overflow-x:auto; max-width:940px;'>
          <table class='tbl' style='margin-top:0; min-width:720px; max-width:940px; border:3px solid #d6a756;'>
            <thead>
              <tr>
                <th style='min-width:150px; border-top:3px solid #d6a756; border-left:3px solid #d6a756;'>Zmienna</th>
                <th style='min-width:220px; border-top:3px solid #d6a756;'>Kategoria</th>
                <th style='min-width:176px; text-align:center; border-top:3px solid #d6a756;'>% grupa</th>
                <th id='simx_ref_head' style='min-width:130px; text-align:center; border-top:3px solid #d6a756;'>__CITY_LABEL__</th>
                <th style='min-width:110px; text-align:center; border-top:3px solid #d6a756;'>Różnica</th>
              </tr>
            </thead>
            <tbody id='simx_body'></tbody>
          </table>
        </div>
      </div>
    </div>

    <script>
    (function() {
      const DATA = __PAYLOAD_JSON__;
      const CITY_LABEL = __CITY_JSON__;

      const VAR_ICONS = (DATA.var_icons && typeof DATA.var_icons === "object") ? DATA.var_icons : {};
      const CAT_ICONS = (DATA.cat_icons && typeof DATA.cat_icons === "object") ? DATA.cat_icons : {};

      function escHtml(x) {
        return String(x == null ? "" : x)
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/"/g, "&quot;")
          .replace(/'/g, "&#39;");
      }

      function nk(x) {
        return String(x == null ? "" : x).trim().toLowerCase().replace(/\\s+/g, " ");
      }

      function num(x) {
        const v = Number(x);
        return isFinite(v) ? v : 0;
      }

      function fmt1(x) {
        const v = Number(x);
        return isFinite(v) ? v.toFixed(1) : "0.0";
      }

      function fmtInt(x) {
        const v = Number(x);
        if (!isFinite(v)) return "0";
        return Math.round(v).toLocaleString("pl-PL").split("\u00A0").join(" ");
      }

      function getMode() {
        const m = document.body.getAttribute("data-label-mode");
        return (m === "values") ? "values" : "arche";
      }

      function labelArche(a) {
        if (getMode() === "values") {
          return (DATA.value_map || {})[a] || a;
        }
        return a;
      }

      const sel1 = document.getElementById("simx_arche_1");
      const sel2 = document.getElementById("simx_arche_2");
      const sel3 = document.getElementById("simx_arche_3");
      const wrap2 = document.getElementById("simx_wrap_2");
      const wrap3 = document.getElementById("simx_wrap_3");
      const add2 = document.getElementById("simx_add_2");
      const add3 = document.getElementById("simx_add_3");
      const rem2 = document.getElementById("simx_remove_2");
      const rem3 = document.getElementById("simx_remove_3");

      const selectedEl = document.getElementById("simx_selected");
      const reachEl = document.getElementById("simx_reach");
      const hardEl = document.getElementById("simx_hard");
      const strengthEl = document.getElementById("simx_strength");
      const campaignEl = document.getElementById("simx_campaign");
      const mobilEl = document.getElementById("simx_mobil");
      const nEl = document.getElementById("simx_n");
      const baseEl = document.getElementById("simx_base");
      const estPopEl = document.getElementById("simx_est_pop");
      const hintEl = document.getElementById("simx_hint");
      const bodyEl = document.getElementById("simx_body");
      const tilesEl = document.getElementById("simx_tiles");
      const refHeadEl = document.getElementById("simx_ref_head");
      const conflictAlertEl = document.getElementById("simx_conflict_alert");

      if (!sel1 || !sel2 || !sel3 || !wrap2 || !wrap3 || !add2 || !add3 || !rem2 || !rem3 || !selectedEl || !reachEl || !hardEl || !strengthEl || !campaignEl || !mobilEl || !nEl || !baseEl || !estPopEl || !hintEl || !bodyEl || !tilesEl || !refHeadEl || !conflictAlertEl) {
        return;
      }

      let show2 = false;
      let show3 = false;
      const opposingPairs = Array.isArray(DATA.opposing_pairs) ? DATA.opposing_pairs : [
        ["Buntownik", "Władca"],
        ["Opiekun", "Bohater"],
      ];

      function fillSelect(selectEl, keepValue, usedSet, allowBlank) {
        const keep = String(keepValue || "");
        selectEl.innerHTML = "";

        if (allowBlank) {
          const blank = document.createElement("option");
          blank.value = "";
          blank.textContent = "—";
          selectEl.appendChild(blank);
        }

        (DATA.order || []).forEach(function(a) {
          if (usedSet.has(a) && a !== keep) return;
          const opt = document.createElement("option");
          opt.value = a;
          opt.textContent = labelArche(a);
          selectEl.appendChild(opt);
        });

        if (keep && Array.from(selectEl.options).some(function(o) { return o.value === keep; })) {
          selectEl.value = keep;
        } else if (allowBlank) {
          selectEl.value = "";
        } else if ((DATA.order || []).length) {
          selectEl.value = DATA.order[0];
        }
      }

      function refreshSelectors() {
        const v1 = sel1.value || "";
        const v2 = sel2.value || "";
        const v3 = sel3.value || "";

        fillSelect(sel1, v1, new Set(), false);
        fillSelect(sel2, v2, new Set([sel1.value].filter(Boolean)), true);
        fillSelect(sel3, v3, new Set([sel1.value, sel2.value].filter(Boolean)), true);
      }

      function applyVisibility() {
        wrap2.style.display = show2 ? "" : "none";
        wrap3.style.display = show3 ? "" : "none";
        add2.style.display = show2 ? "none" : "";
        add3.style.display = (show2 && !show3) ? "" : "none";
      }

      function selectedList() {
        const out = [];
        if (sel1.value) out.push(sel1.value);
        if (show2 && sel2.value) out.push(sel2.value);
        if (show3 && sel3.value) out.push(sel3.value);

        const uniq = [];
        const seen = new Set();
        out.forEach(function(v) {
          if (!seen.has(v)) {
            seen.add(v);
            uniq.push(v);
          }
        });
        return uniq;
      }

      function getItem(archeList) {
        const idxs = archeList
          .map(function(a) { return (DATA.order || []).indexOf(a); })
          .filter(function(i) { return i >= 0; })
          .sort(function(a, b) { return a - b; });

        if (!idxs.length) return null;
        const key = idxs.join("|");
        return (DATA.items || {})[key] || null;
      }

      function hasOpposingPair(archeList) {
        if (!Array.isArray(archeList) || archeList.length < 2) return false;
        const picked = new Set(archeList.map(function(x) { return String(x || ""); }));
        return opposingPairs.some(function(pair) {
          if (!Array.isArray(pair) || pair.length !== 2) return false;
          return picked.has(String(pair[0] || "")) && picked.has(String(pair[1] || ""));
        });
      }

      function renderConflictWarning(archeList) {
        if (!hasOpposingPair(archeList)) {
          conflictAlertEl.style.display = "none";
          conflictAlertEl.textContent = "";
          return;
        }
        conflictAlertEl.textContent = (getMode() === "values")
          ? "⚠ uwaga przeciwstawne wartości"
          : "⚠ uwaga przeciwstawne archetypy";
        conflictAlertEl.style.display = "inline-flex";
      }

      function sortRows(rows) {
        const varOrder = Array.isArray(DATA.var_order) ? DATA.var_order : [];
        const catOrder = (DATA.cat_order && typeof DATA.cat_order === "object") ? DATA.cat_order : {};

        const varPos = {};
        varOrder.forEach(function(v, i) { varPos[nk(v)] = i; });

        const catPos = {};
        Object.keys(catOrder).forEach(function(v) {
          const mp = {};
          (catOrder[v] || []).forEach(function(c, i) { mp[nk(c)] = i; });
          catPos[nk(v)] = mp;
        });

        return (Array.isArray(rows) ? rows.slice() : []).sort(function(a, b) {
          const av = String(a.zmienna || "");
          const bv = String(b.zmienna || "");
          const ak = String(a.kategoria || "");
          const bk = String(b.kategoria || "");

          const dVar = (varPos[nk(av)] ?? 999) - (varPos[nk(bv)] ?? 999);
          if (dVar !== 0) return dVar;

          const aCatPos = ((catPos[nk(av)] || {})[nk(ak)] ?? 999);
          const bCatPos = ((catPos[nk(bv)] || {})[nk(bk)] ?? 999);
          if (aCatPos !== bCatPos) return aCatPos - bCatPos;

          const dPct = num(b.pct_seg) - num(a.pct_seg);
          if (Math.abs(dPct) > 1e-9) return dPct;

          return ak.localeCompare(bk, "pl");
        });
      }

      function render() {
        refreshSelectors();
        applyVisibility();

        const selected = selectedList();
        const selectedLabel = selected.map(function(a) { return labelArche(a); }).join(", ");
        selectedEl.textContent = selected.length ? ("Wybór: " + selectedLabel) : "Wybór: —";
        renderConflictWarning(selected);

        const item = getItem(selected);
        const refLabel = String(DATA.city_label || CITY_LABEL || "Poznań / próba");
        refHeadEl.innerHTML = escHtml(refLabel).replace(" / ", " /<br>");

        if (!item) {
          reachEl.textContent = "Zasięg (% mieszkańców): 0.0%";
          hardEl.textContent = "Twarda grupa (%): 0.0%";
          strengthEl.textContent = "Siła priorytetu: 0.0/100";
          campaignEl.textContent = "Potencjał kampanijny: 0.0/100";
          mobilEl.textContent = "Rdzeń mobilizacyjny: 0.0/100";
          nEl.textContent = "N grupy: 0";
          baseEl.textContent = "Baza: 0 respondentów";
          estPopEl.textContent = "Szac. max wielkość (15+): —";
          hintEl.textContent = "Brak danych dla wybranej kombinacji.";
          tilesEl.innerHTML = "";
          bodyEl.innerHTML = "<tr><td colspan='5'>Brak danych.</td></tr>";
          return;
        }

        const share = num(item.reach_pct || item.share_pct);
        const hardShare = num(item.hard_group_share_pct);
        const strength = num(item.priority_strength_idx);
        const campaign = num(item.campaign_potential_idx);
        const mobil = num(item.mobilization_core_idx);

        reachEl.textContent = "Zasięg (% mieszkańców): " + fmt1(share) + "%";
        hardEl.textContent = "Twarda grupa (%): " + fmt1(hardShare) + "%";
        strengthEl.textContent = "Siła priorytetu: " + fmt1(strength) + "/100";
        campaignEl.textContent = "Potencjał kampanijny: " + fmt1(campaign) + "/100";
        mobilEl.textContent = "Rdzeń mobilizacyjny: " + fmt1(mobil) + "/100";
        nEl.textContent = "N grupy: " + fmtInt(item.n_raw || 0);
        baseEl.textContent = "Baza: " + fmtInt(item.base_n_raw || 0) + " respondentów";

        const pop15 = num(DATA.population_15_plus);
        if (pop15 > 0) {
          estPopEl.textContent = "Szac. max wielkość (15+): " + fmtInt(item.est_pop_15 || 0);
        } else {
          estPopEl.textContent = "Szac. max wielkość (15+): —";
        }

        const bp = item.best_positive || null;
        if (bp) {
          const liftTxt = (num(bp.lift_pp) >= 0 ? "+" : "") + fmt1(bp.lift_pp) + " pp";
          hintEl.innerHTML = "Najmocniejsza nadreprezentacja: <b>" + escHtml(bp.zmienna || "") + " – " + escHtml(bp.kategoria || "") + "</b> (" + liftTxt + ").";
        } else {
          hintEl.textContent = "Brak wyraźnej nadreprezentacji. Profil jest zbliżony do struktury bazy odniesienia.";
        }

        const rows = sortRows(item.rows || []);

        const grouped = {};
        rows.forEach(function(r) {
          const v = String(r.zmienna || "");
          if (!grouped[v]) grouped[v] = [];
          grouped[v].push(r);
        });

        const varOrder = Array.isArray(DATA.var_order) ? DATA.var_order.slice() : [];
        Object.keys(grouped).forEach(function(v) {
          if (varOrder.indexOf(v) < 0) varOrder.push(v);
        });

        const tiles = [];
        varOrder.forEach(function(v) {
          const arr = grouped[v] || [];
          if (!arr.length) return;

          let best = arr[0];
          arr.forEach(function(r) {
            if (num(r.pct_seg) > num(best.pct_seg)) best = r;
          });

          const icon = VAR_ICONS[String(v).toUpperCase()] || "•";
          const catLabel = String(best.kategoria || "");
          const catIcon = CAT_ICONS[nk(catLabel)] || "📌";
          const liftTxt = (num(best.lift_pp) >= 0 ? "+" : "") + fmt1(best.lift_pp) + " pp";

          tiles.push(
            "<div class='simx-tile'>"
              + "<div class='simx-tile-k'>" + icon + " " + escHtml(v) + "</div>"
              + "<div class='simx-tile-v'>" + catIcon + " " + escHtml(catLabel) + "</div>"
              + "<div class='simx-tile-s'>" + fmt1(best.pct_seg) + "% • " + liftTxt + "</div>"
            + "</div>"
          );
        });
        tilesEl.innerHTML = tiles.join("");

        let bodyHtml = "";
        varOrder.forEach(function(v) {
          const arr = grouped[v] || [];
          if (!arr.length) return;

          const bestPct = Math.max.apply(null, arr.map(function(r) { return num(r.pct_seg); }));

          arr.forEach(function(r, idx) {
            const pctGroup = Math.max(0, Math.min(100, num(r.pct_seg)));
            const pctRef = num(r.pct_all);
            const lift = num(r.lift_pp);
            const isBest = Math.abs(pctGroup - bestPct) <= 1e-9;

            const topBorder = (idx === 0) ? "border-top:3px solid #d6a756;" : "";
            const varIcon = VAR_ICONS[String(v).toUpperCase()] || "📌";
            const varCell = (idx === 0)
              ? "<td rowspan='" + arr.length + "' style='font-weight:800; text-transform:uppercase; vertical-align:middle; background:#fff7e8; border-left:3px solid #d6a756; " + topBorder + "'><span style='display:inline-flex; align-items:center; gap:6px;'><span>" + escHtml(varIcon) + "</span><span>" + escHtml(v) + "</span></span></td>"
              : "";

            const catStyle = isBest ? "font-weight:800;" : "";
            const fill = isBest ? "#f59e0b" : "#fde7b0";
            const liftTxt = (lift >= 0 ? "+" : "") + fmt1(lift) + " pp";
            const catIcon = CAT_ICONS[nk(String(r.kategoria || ""))] || "📌";

            bodyHtml += "<tr>"
              + varCell
              + "<td style='" + topBorder + " " + catStyle + "'><span style='display:inline-flex; align-items:center; gap:6px;'><span>" + escHtml(catIcon) + "</span><span>" + escHtml(r.kategoria || "") + "</span></span></td>"
              + "<td style='padding:0; min-width:176px; border:1px solid #dfe4ea; " + topBorder + "'>"
                  + "<div style='position:relative; height:34px; background:#fff;'>"
                    + "<div style='position:absolute; left:0; top:0; bottom:0; width:" + pctGroup.toFixed(1) + "%; background:" + fill + "; opacity:0.96;'></div>"
                    + "<span style='position:absolute; right:6px; top:7px; z-index:2; background:rgba(255,255,255,0.88); padding:1px 5px; border-radius:4px; font-size:12px; font-weight:" + (isBest ? "900" : "600") + "; color:#111;'>" + fmt1(pctGroup) + "%</span>"
                  + "</div>"
                + "</td>"
              + "<td style='text-align:right; " + topBorder + "'>" + fmt1(pctRef) + "%</td>"
              + "<td style='text-align:right; color:" + (lift >= 0 ? "#0f766e" : "#9a3412") + "; " + topBorder + "'>" + liftTxt + "</td>"
              + "</tr>";
          });
        });

        bodyEl.innerHTML = bodyHtml || "<tr><td colspan='5'>Brak danych.</td></tr>";
      }

      add2.addEventListener("click", function() {
        show2 = true;
        show3 = false;
        sel2.value = sel2.value || "";
        sel3.value = "";
        render();
      });

      add3.addEventListener("click", function() {
        if (!show2) return;
        show3 = true;
        sel3.value = sel3.value || "";
        render();
      });

      rem2.addEventListener("click", function() {
        show2 = false;
        show3 = false;
        sel2.value = "";
        sel3.value = "";
        render();
      });

      rem3.addEventListener("click", function() {
        show3 = false;
        sel3.value = "";
        render();
      });

      [sel1, sel2, sel3].forEach(function(el) {
        el.addEventListener("change", render);
      });

      const modeRadios = document.querySelectorAll('input[name="labelmode"]');
      modeRadios.forEach(function(r) {
        r.addEventListener("change", render);
      });

      if (window.MutationObserver) {
        const obs = new MutationObserver(function(muts) {
          for (let i = 0; i < muts.length; i++) {
            if (muts[i].type === "attributes" && muts[i].attributeName === "data-label-mode") {
              render();
              break;
            }
          }
        });
        obs.observe(document.body, { attributes: true, attributeFilter: ["data-label-mode"] });
      }

      fillSelect(sel1, (DATA.order || [""])[0] || "", new Set(), false);
      fillSelect(sel2, "", new Set([sel1.value].filter(Boolean)), true);
      fillSelect(sel3, "", new Set([sel1.value].filter(Boolean)), true);
      render();
    })();
    </script>
    """

    return tpl.replace("__PAYLOAD_JSON__", payload_json).replace("__CITY_JSON__", city_json).replace(
        "__CITY_LABEL__", _html_escape(city_label)
    )


def _render_b2_declared_demo_panel(payload: Dict[str, Any], city_label: str = "Poznań / próba") -> str:
    payload = dict(payload or {})

    order = [str(x) for x in (payload.get("order") or []) if str(x) in ARCHETYPES]
    if not order:
        order = list(ARCHETYPES)

    payload_obj = {
        "order": order,
        "items": payload.get("items") or {},
        "segments": payload.get("segments") or [{
            "key": "ALL",
            "rank": -1,
            "label": "Wszystkie segmenty",
            "name_arche": "Wszystkie segmenty",
            "name_values": "Wszystkie segmenty",
        }],
        "value_map": payload.get("value_map") or {a: a for a in ARCHETYPES},

        "var_order": payload.get("var_order") or list(_DEMO_CORE_VAR_ORDER),
        "cat_order": payload.get("cat_order") or {},
        "var_icons": payload.get("var_icons") or {},
        "cat_icons": payload.get("cat_icons") or {},
        "city_label": str(payload.get("city_label") or city_label),
    }

    payload_json = json.dumps(payload_obj, ensure_ascii=False).replace("</", "<\\/")
    city_json = json.dumps(str(city_label), ensure_ascii=False)

    tpl = """
    <style>
      .b2x-hero {
        border: 1px solid #d4dbe5;
        border-radius: 12px;
        padding: 12px 14px;
        background: linear-gradient(180deg, #f8fafc 0%, #eef2f7 100%);
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.9);
      }
      .b2x-kicker {
        font-size: 11px;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: .04em;
        color: #5f6b7a;
      }
      .b2x-title {
        margin-top: 3px;
        font-size: 22px;
        font-weight: 900;
        color: #0f172a;
      }
      .b2x-controls {
        display: flex;
        flex-wrap: wrap;
        gap: 10px;
        align-items: center;
        margin-top: 10px;
      }
      .b2x-controls label {
        font-weight: 800;
      }
      .b2x-controls select {
        padding: 7px 10px;
        border: 1px solid #cbd5e1;
        border-radius: 9px;
        background: #fff;
        font-weight: 700;
      }
      .b2x-metrics {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin-top: 10px;
      }
      .b2x-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 10px;
        border: 1px solid #d0d7de;
        border-radius: 999px;
        background: #fff;
        font-size: 12px;
        font-weight: 800;
      }
      .b2x-tiles {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(175px, 1fr));
        gap: 8px;
        margin: 10px 0 12px 0;
      }
      .b2x-tile {
        border: 1px solid #dbe4ef;
        border-radius: 10px;
        background: #fff;
        padding: 8px 10px;
      }
      .b2x-tile-k {
        font-size: 11px;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: .03em;
        color: #5f6b7a;
      }
      .b2x-tile-v {
        margin-top: 2px;
        font-size: 14px;
        font-weight: 900;
        color: #111827;
      }
      .b2x-tile-s {
        margin-top: 2px;
        font-size: 12px;
        color: #3f4954;
      }
    </style>

    <div class='card'>
      <div class='b2x-hero'>
        <div class='b2x-kicker'>Centrum Strategii Demograficznej</div>
        <div class='b2x-title'>Profil demograficzny wyborców</div>
        <div class='small' style='margin-top:4px;'>
          Precyzyjny profil demograficzny deklaracji B2 z filtrem
          jednocześnie po segmencie i <span class="mode-arche">archetypie</span><span class="mode-values">wartości</span>.
        </div>

        <div class='b2x-controls'>
          <label for='b2_declared_segment'>Segment:</label>
          <select id='b2_declared_segment'></select>

          <label for='b2_declared_arche'><span class='mode-arche'>Archetyp:</span><span class='mode-values'>Wartość:</span></label>
          <select id='b2_declared_arche'></select>
        </div>

        <div class='b2x-metrics'>
          <span id='b2_declared_share' class='b2x-pill'></span>
          <span id='b2_declared_n' class='b2x-pill'></span>
          <span id='b2_declared_base' class='b2x-pill'></span>
        </div>
      </div>

      <div class='seg-box' style='margin-bottom:10px;'>
        <div class='seg-mini-label'>📌 Statystyczny profil demograficzny <span class='mode-arche'>archetypu</span><span class='mode-values'>wartości</span></div>
        <div id='b2_declared_tiles' class='b2x-tiles'></div>
        <div id='b2_declared_hint' class='small' style='margin:2px 0 0 0;'></div>
      </div>

      <div class='seg-box'>
        <div class='seg-mini-label'>👥 Profil demograficzny <span class='mode-arche'>archetypu</span><span class='mode-values'>wartości</span></div>
        <div style='color:#5f6b7a; font-size:12px; margin:2px 0 6px 0;'>
          W tabeli pogrubiona najwyższa kategoria w każdej zmiennej.
        </div>

        <div style='overflow-x:auto; max-width:940px;'>
          <table class='tbl' style='margin-top:0; min-width:720px; max-width:940px; border:3px solid #b8c2cc;'>
            <thead>
              <tr>
                <th style='min-width:150px; border-top:3px solid #b8c2cc; border-left:3px solid #b8c2cc;'>Zmienna</th>
                <th style='min-width:220px; border-top:3px solid #b8c2cc;'>Kategoria</th>
                <th style='min-width:176px; text-align:center; border-top:3px solid #b8c2cc;'>% grupa</th>
                <th id='b2_declared_ref_head' style='min-width:130px; text-align:center; border-top:3px solid #b8c2cc;'>__CITY_LABEL__</th>
                <th style='min-width:110px; text-align:center; border-top:3px solid #b8c2cc;'>Różnica</th>
              </tr>
            </thead>
            <tbody id='b2_declared_body'></tbody>
          </table>
        </div>
      </div>

      <div class='small' style='margin-top:8px;'>
        
      </div>
    </div>

    <script>
    (function() {
      const DATA = __PAYLOAD_JSON__;
      const CITY_LABEL = __CITY_JSON__;

      const VAR_ICONS = (DATA.var_icons && typeof DATA.var_icons === "object") ? DATA.var_icons : {};
      const CAT_ICONS = (DATA.cat_icons && typeof DATA.cat_icons === "object") ? DATA.cat_icons : {};

      function escHtml(x) {
        return String(x == null ? "" : x)
          .replace(/&/g, "&amp;")
          .replace(/</g, "&lt;")
          .replace(/>/g, "&gt;")
          .replace(/\"/g, "&quot;")
          .replace(/'/g, "&#39;");
      }

      function nk(x) {
        return String(x == null ? "" : x).trim().toLowerCase().replace(/\\s+/g, " ");
      }

      function num(x) {
        const v = Number(x);
        return isFinite(v) ? v : 0;
      }

      function fmt1(x) {
        const v = Number(x);
        return isFinite(v) ? v.toFixed(1) : "0.0";
      }

      function getMode() {
        const m = document.body.getAttribute("data-label-mode");
        return (m === "values") ? "values" : "arche";
      }

      function labelArche(a) {
        if (getMode() === "values") {
          return (DATA.value_map || {})[a] || a;
        }
        return a;
      }

      function segmentDisplayName(seg) {
        if (!seg || String(seg.key || "") === "ALL") {
          return "Wszystkie segmenty";
        }
        return String(seg.name_arche || seg.label || seg.key || "");
      }

      function fillArcheSelect() {
        const sel = document.getElementById("b2_declared_arche");
        if (!sel) return;

        const keep = sel.value;
        sel.innerHTML = "";

        (DATA.order || []).forEach(function(a) {
          const opt = document.createElement("option");
          opt.value = a;
          opt.textContent = labelArche(a);
          sel.appendChild(opt);
        });

        if (keep && (DATA.order || []).indexOf(keep) >= 0) {
          sel.value = keep;
        } else if ((DATA.order || []).length) {
          sel.value = DATA.order[0];
        }
      }

      function fillSegmentSelect() {
        const sel = document.getElementById("b2_declared_segment");
        if (!sel) return;

        const keep = sel.value;
        sel.innerHTML = "";

        const segs = Array.isArray(DATA.segments) ? DATA.segments : [];
        segs.forEach(function(seg) {
          const opt = document.createElement("option");
          const key = String(seg.key || "ALL");
          opt.value = key;
          if (key === "ALL") {
            opt.textContent = "Wszystkie segmenty";
          } else {
            opt.textContent = String(seg.label || key) + ": " + segmentDisplayName(seg);
          }
          sel.appendChild(opt);
        });

        const allKeys = segs.map(function(s) { return String(s.key || "ALL"); });
        if (keep && allKeys.indexOf(keep) >= 0) {
          sel.value = keep;
        } else if (allKeys.length) {
          sel.value = allKeys[0];
        } else {
          sel.value = "ALL";
        }
      }

      function getItem(arche, segKey) {
        const byArche = (DATA.items || {})[arche] || {};
        return byArche[segKey] || byArche["ALL"] || null;
      }

      function sortRows(rows) {
        const varOrder = Array.isArray(DATA.var_order) ? DATA.var_order : [];
        const catOrder = (DATA.cat_order && typeof DATA.cat_order === "object") ? DATA.cat_order : {};

        const varPos = {};
        varOrder.forEach(function(v, i) { varPos[nk(v)] = i; });

        const catPos = {};
        Object.keys(catOrder).forEach(function(v) {
          const mp = {};
          (catOrder[v] || []).forEach(function(c, i) { mp[nk(c)] = i; });
          catPos[nk(v)] = mp;
        });

        return (Array.isArray(rows) ? rows.slice() : []).sort(function(a, b) {
          const av = String(a.zmienna || "");
          const bv = String(b.zmienna || "");
          const ak = String(a.kategoria || "");
          const bk = String(b.kategoria || "");

          const dVar = (varPos[nk(av)] ?? 999) - (varPos[nk(bv)] ?? 999);
          if (dVar !== 0) return dVar;

          const aCatPos = ((catPos[nk(av)] || {})[nk(ak)] ?? 999);
          const bCatPos = ((catPos[nk(bv)] || {})[nk(bk)] ?? 999);
          if (aCatPos !== bCatPos) return aCatPos - bCatPos;

          const dPct = num(b.pct_seg) - num(a.pct_seg);
          if (Math.abs(dPct) > 1e-9) return dPct;

          return ak.localeCompare(bk, "pl");
        });
      }

      function render() {
        const archeSel = document.getElementById("b2_declared_arche");
        const segSel = document.getElementById("b2_declared_segment");
        const shareEl = document.getElementById("b2_declared_share");
        const nEl = document.getElementById("b2_declared_n");
        const baseEl = document.getElementById("b2_declared_base");
        const hintEl = document.getElementById("b2_declared_hint");
        const bodyEl = document.getElementById("b2_declared_body");
        const tilesEl = document.getElementById("b2_declared_tiles");
        const refHeadEl = document.getElementById("b2_declared_ref_head");

        if (!archeSel || !segSel || !shareEl || !nEl || !baseEl || !hintEl || !bodyEl || !tilesEl || !refHeadEl) {
          return;
        }

        const arche = archeSel.value || ((DATA.order || [])[0] || "");
        const segKey = segSel.value || "ALL";
        const item = getItem(arche, segKey);

        const segs = Array.isArray(DATA.segments) ? DATA.segments : [];
        const segObj = segs.find(function(s) { return String(s.key || "ALL") === segKey; }) || null;

        const refLabel = (segKey === "ALL")
          ? String(DATA.city_label || CITY_LABEL || "Poznań / próba")
          : segmentDisplayName(segObj);

        refHeadEl.innerHTML = escHtml(refLabel).replace(" / ", " /<br>");

        if (!item) {
          shareEl.textContent = "Udział ważony: 0.0%";
          nEl.textContent = "N grupy: 0";
          baseEl.textContent = "Baza: 0 respondentów";
          hintEl.textContent = "Brak danych dla wybranego filtra.";
          tilesEl.innerHTML = "";
          bodyEl.innerHTML = "<tr><td colspan='5'>Brak danych.</td></tr>";
          return;
        }

        shareEl.textContent = "Udział ważony: " + fmt1(item.share_pct) + "%";
        nEl.textContent = "N grupy: " + String(item.n_raw || 0);
        baseEl.textContent = "Baza: " + String(item.base_n_raw || 0) + " respondentów";

        const bp = item.best_positive || null;
        if (bp) {
          const liftTxt = (num(bp.lift_pp) >= 0 ? "+" : "") + fmt1(bp.lift_pp) + " pp";
          hintEl.innerHTML = "Najmocniejsza nadreprezentacja: <b>" + escHtml(bp.zmienna || "") + " – " + escHtml(bp.kategoria || "") + "</b> (" + liftTxt + ").";
        } else {
          hintEl.textContent = "Brak wyraźnej nadreprezentacji. Profil jest zbliżony do struktury bazy odniesienia.";
        }

        const rows = sortRows(item.rows || []);

        const grouped = {};
        rows.forEach(function(r) {
          const v = String(r.zmienna || "");
          if (!grouped[v]) grouped[v] = [];
          grouped[v].push(r);
        });

        const varOrder = Array.isArray(DATA.var_order) ? DATA.var_order.slice() : [];
        Object.keys(grouped).forEach(function(v) {
          if (varOrder.indexOf(v) < 0) varOrder.push(v);
        });

        const tiles = [];
        varOrder.forEach(function(v) {
          const arr = grouped[v] || [];
          if (!arr.length) return;

          let best = arr[0];
          arr.forEach(function(r) {
            if (num(r.pct_seg) > num(best.pct_seg)) best = r;
          });

          const icon = VAR_ICONS[String(v).toUpperCase()] || "•";
          const catLabel = String(best.kategoria || "");
          const catIcon = CAT_ICONS[nk(catLabel)] || "📌";
          const liftTxt = (num(best.lift_pp) >= 0 ? "+" : "") + fmt1(best.lift_pp) + " pp";

          tiles.push(
            "<div class='b2x-tile'>"
              + "<div class='b2x-tile-k'>" + icon + " " + escHtml(v) + "</div>"
              + "<div class='b2x-tile-v'>" + catIcon + " " + escHtml(catLabel) + "</div>"
              + "<div class='b2x-tile-s'>" + fmt1(best.pct_seg) + "% • " + liftTxt + "</div>"
            + "</div>"
          );
        });
        tilesEl.innerHTML = tiles.join("");

        let bodyHtml = "";
        varOrder.forEach(function(v) {
          const arr = grouped[v] || [];
          if (!arr.length) return;

          const bestPct = Math.max.apply(null, arr.map(function(r) { return num(r.pct_seg); }));

          arr.forEach(function(r, idx) {
            const pctGroup = Math.max(0, Math.min(100, num(r.pct_seg)));
            const pctRef = num(r.pct_all);
            const lift = num(r.lift_pp);
            const isBest = Math.abs(pctGroup - bestPct) <= 1e-9;

            const topBorder = (idx === 0) ? "border-top:3px solid #b8c2cc;" : "";
            const varIcon = VAR_ICONS[String(v).toUpperCase()] || "📌";
            const varCell = (idx === 0)
              ? "<td rowspan='" + arr.length + "' style='font-weight:800; text-transform:uppercase; vertical-align:middle; background:#fafafa; border-left:3px solid #b8c2cc; " + topBorder + "'><span style='display:inline-flex; align-items:center; gap:6px;'><span>" + escHtml(varIcon) + "</span><span>" + escHtml(v) + "</span></span></td>"
              : "";

            const catStyle = isBest ? "font-weight:800;" : "";
            const fill = isBest ? "#8ecae6" : "#d8e5f1";
            const liftTxt = (lift >= 0 ? "+" : "") + fmt1(lift) + " pp";
            const catIcon = CAT_ICONS[nk(String(r.kategoria || ""))] || "📌";

            bodyHtml += "<tr>"
              + varCell
              + "<td style='" + topBorder + " " + catStyle + "'><span style='display:inline-flex; align-items:center; gap:6px;'><span>" + escHtml(catIcon) + "</span><span>" + escHtml(r.kategoria || "") + "</span></span></td>"
              + "<td style='padding:0; min-width:176px; border:1px solid #dfe4ea; " + topBorder + "'>"
                  + "<div style='position:relative; height:34px; background:#fff;'>"
                    + "<div style='position:absolute; left:0; top:0; bottom:0; width:" + pctGroup.toFixed(1) + "%; background:" + fill + "; opacity:0.96;'></div>"
                    + "<span style='position:absolute; right:6px; top:7px; z-index:2; background:rgba(255,255,255,0.88); padding:1px 5px; border-radius:4px; font-size:12px; font-weight:" + (isBest ? "900" : "600") + "; color:#111;'>" + fmt1(pctGroup) + "%</span>"
                  + "</div>"
                + "</td>"
              + "<td style='text-align:right; " + topBorder + "'>" + fmt1(pctRef) + "%</td>"
              + "<td style='text-align:right; color:" + (lift >= 0 ? "#0f766e" : "#9a3412") + "; " + topBorder + "'>" + liftTxt + "</td>"
              + "</tr>";
          });
        });

        bodyEl.innerHTML = bodyHtml || "<tr><td colspan='5'>Brak danych.</td></tr>";
      }

      fillArcheSelect();
      fillSegmentSelect();
      render();

      const archeSel = document.getElementById("b2_declared_arche");
      const segSel = document.getElementById("b2_declared_segment");
      if (archeSel) archeSel.addEventListener("change", render);
      if (segSel) segSel.addEventListener("change", render);

      const modeRadios = document.querySelectorAll('input[name="labelmode"]');
      modeRadios.forEach(function(r) {
        r.addEventListener("change", function() {
          fillArcheSelect();
          fillSegmentSelect();
          render();
        });
      });

      if (window.MutationObserver) {
        const obs = new MutationObserver(function(muts) {
          for (let i = 0; i < muts.length; i++) {
            if (muts[i].type === "attributes" && muts[i].attributeName === "data-label-mode") {
              fillArcheSelect();
              fillSegmentSelect();
              render();
              break;
            }
          }
        });
        obs.observe(document.body, { attributes: true, attributeFilter: ["data-label-mode"] });
      }
    })();
    </script>
    """

    return tpl.replace("__PAYLOAD_JSON__", payload_json).replace("__CITY_JSON__", city_json).replace(
        "__CITY_LABEL__", _html_escape(city_label)
    )
def _pm_profile_share_pct(pm: Any) -> List[float]:
    """
    Zamienia surowy profil Pm segmentu na lokalną skalę 0–100
    liczona WYŁĄCZNIE w obrębie danego segmentu.

    To nie jest udział respondentów i to nie jest udział „z sumą = 100”.
    Każdy archetyp / wartość dostaje własny poziom 0–100:
    - minimum z profilu segmentu = 0,
    - maksimum z profilu segmentu = 100,
    - reszta proporcjonalnie pomiędzy nimi.

    Dzięki temu wykres „Profil segmentu (wszystkie 12 wartości, 0–100%)”
    pokazuje realną siłę każdego pola na tej samej osi, a nie udział w puli.
    """
    try:
        arr = np.asarray(pm, dtype=float).reshape(-1)
    except Exception:
        arr = np.asarray([], dtype=float)

    if arr.shape[0] != len(ARCHETYPES):
        return [0.0] * len(ARCHETYPES)

    arr = np.where(np.isfinite(arr), arr, np.nan)
    if not np.any(np.isfinite(arr)):
        return [0.0] * len(ARCHETYPES)

    amin = float(np.nanmin(arr))
    amax = float(np.nanmax(arr))
    span = float(amax - amin)

    if span <= 1e-12:
        return [0.0] * len(ARCHETYPES)

    out = (arr - amin) / span * 100.0
    out = np.where(np.isfinite(out), np.clip(out, 0.0, 100.0), 0.0)
    return [float(x) for x in out]


def _segment_profile_chart_filename(seg_num: int, mode: str = "arche") -> str:
    suffix = "_values" if str(mode).lower() == "values" else ""
    return f"SEG_PROFILE_{int(seg_num)}{suffix}.png"


def _cluster_profile_chart_filename(seg_num: int, mode: str = "arche") -> str:
    suffix = "_values" if str(mode).lower() == "values" else ""
    return f"CLUSTER_PROFILE_{int(seg_num)}{suffix}.png"


def _plot_segment_profile_wheel(outpath: Path,
                                pm_share_pct: np.ndarray,
                                brand_values: Dict[str, str],
                                mode: str = "arche",
                                value_suffix: str = "") -> None:
    """
    Wersja 1:1 na bazie generator_wykresu.py.
    Jedyna różnica:
    - procenty bierzemy z realnych danych segmentu (pm_share_pct),
    - podpis łuku respektuje radio (arche / values),
    - plik zapisujemy do outpath.
    """
    from pathlib import Path
    import math
    from PIL import Image
    import numpy as np
    from matplotlib.patches import Wedge, Circle
    from matplotlib.offsetbox import OffsetImage, AnnotationBbox

    vals = np.asarray(pm_share_pct, dtype=float).reshape(-1)
    if vals.shape[0] != len(ARCHETYPES):
        vals = np.zeros(len(ARCHETYPES), dtype=float)
    vals = np.where(np.isfinite(vals), np.clip(vals, 0.0, 100.0), 0.0)

    ITEMS = [
        ("Buntownik", "Odnowa", "buntownik.png", "#c62828"),
        ("Błazen", "Otwartość", "blazen.png", "#ef5350"),
        ("Kochanek", "Relacje", "kochanek.png", "#90caf9"),
        ("Opiekun", "Troska", "opiekun.png", "#42a5f5"),
        ("Towarzysz", "Współpraca", "towarzysz.png", "#1565c0"),
        ("Niewinny", "Przejrzystość", "niewinny.png", "#81c784"),
        ("Władca", "Porządek", "wladca.png", "#43a047"),
        ("Mędrzec", "Rozsądek", "medrzec.png", "#1b5e20"),
        ("Czarodziej", "Wizja", "czarodziej.png", "#b39ddb"),
        ("Bohater", "Odwaga", "bohater.png", "#7e57c2"),
        ("Twórca", "Rozwój", "tworca.png", "#5e35b1"),
        ("Odkrywca", "Wolność", "odkrywca.png", "#8e0000"),
    ]

    def _load_icon(path: Path):
        img = Image.open(path).convert("RGBA")
        alpha = img.getchannel("A")
        bbox = alpha.getbbox()
        if bbox:
            img = img.crop(bbox)
        return np.asarray(img)

    def _draw_text_on_arc(
            ax,
            text: str,
            center_deg: float,
            radius: float,
            max_span_deg: float = 24,
            fontsize: float = 11.4,
            color: str = "#363636",
            weight: str = "bold",
            zorder: int = 4,
    ) -> None:
        s = str(text or "").upper()
        if not s:
            return

        n = len(s)
        span = min(max_span_deg, max(11.5, 1.7 * n))
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

        for ch, ang in zip(s, angles):
            if ch == " ":
                continue

            ang_rad = math.radians(float(ang))
            x = radius * math.cos(ang_rad)
            y = radius * math.sin(ang_rad)
            rot = (ang - 90) if upper else (ang + 90)

            ax.text(
                x,
                y,
                ch,
                ha="center",
                va="center",
                rotation=rot,
                rotation_mode="anchor",
                fontsize=fontsize,
                fontweight=weight,
                color=color,
                zorder=zorder,
            )

    fig, ax = plt.subplots(figsize=(14.4, 14.4), dpi=220)
    ax.set_aspect("equal")
    ax.axis("off")

    bg = "#f6f6f6"
    fig.patch.set_facecolor(bg)
    ax.set_facecolor(bg)

    r_hole = 0.115
    r_data_outer = 0.78
    n_cells = 10
    dr = (r_data_outer - r_hole) / n_cells

    r_label_inner = 0.80
    r_label_outer = 0.92

    r_accent_inner = 0.95
    r_accent_outer = 0.99

    edgecolor = "#d4d4d4"

    value_by_arch = {a: float(vals[i]) for i, a in enumerate(ARCHETYPES)}

    # Ikony szukamy najpierw tam, gdzie działa generator_wykresu.py,
    # a dopiero potem w katalogu raportu.
    script_dir = Path(__file__).resolve().parent

    # Ikony trzymamy docelowo w WYNIKI/icons/*.png.
    # Dla zgodności wspieramy też stare lokalizacje obok skryptu.
    icon_dirs = [
        outpath.parent / "icons",
        outpath.parent / "archetypy_icons",
        script_dir / "icons",
        script_dir / "archetypy_icons",
    ]

    def _icon_name_variants(fname: str) -> List[str]:
        base = str(fname or "")
        if not base:
            return []
        variants = [base]
        # warianty z polskimi znakami (jeśli pliki są nazwane „po polsku”)
        variants.append(base.replace("blazen", "błazen"))
        variants.append(base.replace("wladca", "władca"))
        variants.append(base.replace("medrzec", "mędrzec"))
        variants.append(base.replace("tworca", "twórca"))
        # bez duplikatów
        out = []
        seen = set()
        for v in variants:
            if v and v not in seen:
                out.append(v)
                seen.add(v)
        return out

    icon_cache = {}
    for arch, _value, icon_file, _color in ITEMS:
        icon_path = None
        for icon_dir in icon_dirs:
            if not icon_dir.exists():
                continue

            for cand_name in _icon_name_variants(icon_file):
                cand = icon_dir / cand_name
                if cand.exists():
                    icon_path = cand
                    break
            if icon_path is not None:
                break

            # fallback: dopasowanie po nazwie bez rozszerzenia
            stem = Path(icon_file).stem.lower()
            for p in icon_dir.glob("*.png"):
                if p.stem.lower() == stem:
                    icon_path = p
                    break
            if icon_path is not None:
                break

        if icon_path is not None:
            try:
                icon_cache[arch] = _load_icon(icon_path)
            except Exception:
                pass

    for k in range(n_cells + 1):
        r = r_hole + k * dr
        ax.add_patch(
            Circle(
                (0, 0),
                r,
                facecolor="none",
                edgecolor="#dfdfdf",
                linewidth=0.7,
                zorder=0,
            )
        )

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

    mode_norm = str(mode or "arche").strip().lower()

    for i, (arch, value_label, icon_file, color) in enumerate(ITEMS):
        center = 75 - i * 30
        theta1 = center - 15
        theta2 = center + 15

        p = max(0.0, min(100.0, float(value_by_arch.get(arch, 0.0))))
        fill_outer = r_hole + (p / 100.0) * (r_data_outer - r_hole)

        for k in range(n_cells):
            r_outer = r_hole + (k + 1) * dr

            ax.add_patch(
                Wedge(
                    (0, 0),
                    r_outer,
                    theta1,
                    theta2,
                    width=dr,
                    facecolor=bg,
                    edgecolor=edgecolor,
                    linewidth=0.8,
                    zorder=1,
                )
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
                Wedge(
                    (0, 0),
                    r_outer,
                    theta1,
                    theta2,
                    width=dr,
                    facecolor="none",
                    edgecolor=edgecolor,
                    linewidth=0.8,
                    zorder=3,
                )
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

        ring_label = (
            str(brand_values.get(arch, value_label))
            if mode_norm == "values"
            else _display_archetype_label(arch)
        )
        _draw_text_on_arc(
            ax=ax,
            text=ring_label,
            center_deg=center,
            radius=(r_label_inner + r_label_outer) / 2,
        )

        ang = math.radians(center)

        if arch in icon_cache:
            ax.add_artist(
                AnnotationBbox(
                    OffsetImage(icon_cache[arch], zoom=0.30),
                    (1.14 * math.cos(ang), 1.14 * math.sin(ang)),
                    frameon=False,
                    zorder=5,
                )
            )

        filled_span = max(0.0, fill_outer - r_hole)
        if filled_span > 1e-9:
            label_r = r_hole + filled_span * 0.52
            if p <= 25.0:
                label_r += dr * 0.18
        else:
            label_r = r_hole + dr * 0.9

        ax.text(
            label_r * math.cos(ang),
            label_r * math.sin(ang),
            f"{p:.0f}{str(value_suffix or '')}",
            ha="center",
            va="center",
            fontsize=12.2,
            color="#2f2f2f",
            fontweight="bold",
            zorder=8,
            bbox=dict(
                boxstyle="round,pad=0.24,rounding_size=0.10",
                fc="white",
                ec=color,
                lw=1.0,
                alpha=0.68,
            ),
        )

    ax.add_patch(
        Circle(
            (0, 0),
            r_hole * 0.98,
            facecolor=bg,
            edgecolor="#d0d0d0",
            linewidth=1.2,
            zorder=10,
        )
    )

    for angle_deg in [0, 90, 180, 270]:
        ang = math.radians(angle_deg)
        ax.plot(
            [0, 1.02 * math.cos(ang)],
            [0, 1.02 * math.sin(ang)],
            color="#e1e1e1",
            lw=0.9,
            zorder=0,
        )

    ax.set_xlim(-1.22, 1.22)
    ax.set_ylim(-1.22, 1.22)

    plt.tight_layout(pad=0.06)
    fig.savefig(outpath, dpi=220, bbox_inches="tight", pad_inches=0.10, facecolor=bg)
    plt.close(fig)


def _make_marketing_name_from_top3(top3: List[str], brand_values: Dict[str, str], mode: str = "arche") -> str:
    """
    Krótkie, rozróżnialne nazwy UI.
    Budujemy je z TOP3, żeby dwa segmenty z tym samym TOP2 nie dostawały
    identycznych etykiet.
    """
    picks = [str(x).strip() for x in (top3 or []) if str(x).strip()]
    if not picks:
        return "Segment"

    mode_values = (str(mode).lower() == "values")

    if mode_values:
        vals = [str(brand_values.get(a, a)).strip() for a in picks]
        v1 = vals[0] if len(vals) >= 1 else ""
        v2 = vals[1] if len(vals) >= 2 else ""
        pair_map = {
            ("Porządek", "Troska"): "Sprawczy opiekunowie",
            ("Porządek", "Przejrzystość"): "Przejrzysty ład",
            ("Odwaga", "Rozwój"): "Sprawczy innowatorzy",
            ("Wolność", "Współpraca"): "Wspólnotowi reformatorzy",
            ("Wolność", "Odnowa"): "Niezależni reformatorzy",
            ("Wolność", "Wizja"): "Wizjonerzy zmiany",
        }

        if (v1, v2) in pair_map:
            return pair_map[(v1, v2)]
        if not v1:
            return "Segment"
        if not v2 or v2 == v1:
            return v1

        value_adj = {
            "Porządek": "Uporządkowani",
            "Odwaga": "Odważni",
            "Rozsądek": "Rozsądni",
            "Troska": "Opiekuńczy",
            "Relacje": "Relacyjni",
            "Otwartość": "Pozytywni",
            "Rozwój": "Progresywni",
            "Wolność": "Niezależni",
            "Wizja": "Wizjonerscy",
            "Współpraca": "Wspólnotowi",
            "Przejrzystość": "Przejrzyści",
            "Odnowa": "Reformatorscy",
        }
        value_noun = {
            "Porządek": "organizatorzy",
            "Odwaga": "mobilizatorzy",
            "Rozsądek": "stratedzy",
            "Troska": "opiekunowie",
            "Relacje": "wspólnotowcy",
            "Otwartość": "animatorzy",
            "Rozwój": "innowatorzy",
            "Wolność": "odkrywcy",
            "Wizja": "wizjonerzy",
            "Współpraca": "wspólnotowcy",
            "Przejrzystość": "strażnicy",
            "Odnowa": "reformatorzy",
        }
        return f"{value_adj.get(v1, v1)} {value_noun.get(v2, 'uczestnicy')}"

    a1 = picks[0] if len(picks) >= 1 else ""
    a2 = picks[1] if len(picks) >= 2 else ""
    a3 = picks[2] if len(picks) >= 3 else ""

    single_map = {
        "Władca": "Decyzyjni",
        "Opiekun": "Opiekuńczy",
        "Niewinny": "Przejrzyści",
        "Odkrywca": "Poszukujący",
        "Bohater": "Sprawczy",
        "Twórca": "Kreatywni",
        "Towarzysz": "Wspólnotowi",
        "Buntownik": "Antysystemowi",
        "Mędrzec": "Racjonalni",
        "Kochanek": "Relacyjni",
        "Czarodziej": "Wizjonerscy",
        "Błazen": "Improwizujący",
    }

    pair_map = {
        ("Władca", "Opiekun"): {
            "Niewinny": "Przejrzyści opiekunowie",
            "*": "Stabilni opiekunowie",
        },
        ("Władca", "Niewinny"): {
            "Opiekun": "Przejrzyści strażnicy",
            "*": "Spokojni zarządcy",
        },
        ("Bohater", "Twórca"): {
            "Czarodziej": "Wizjonerscy innowatorzy",
            "Mędrzec": "Racjonalni innowatorzy",
            "Towarzysz": "Wspólnotowi innowatorzy",
            "*": "Sprawczy innowatorzy",
        },
        ("Odkrywca", "Towarzysz"): {
            "Buntownik": "Energetyczni reformatorzy",
            "*": "Wspólnotowi reformatorzy",
        },
        ("Odkrywca", "Buntownik"): {
            "*": "Niezależni reformatorzy",
        },
        ("Buntownik", "Towarzysz"): {
            "*": "Zaangażowani reformatorzy",
        },
        ("Opiekun", "Niewinny"): {
            "*": "Spokojni opiekunowie",
        },
        ("Mędrzec", "Władca"): {
            "*": "Racjonalni decydenci",
        },
        ("Kochanek", "Towarzysz"): {
            "*": "Relacyjni wspólnotowcy",
        },
        ("Czarodziej", "Odkrywca"): {
            "*": "Wizjonerzy zmiany",
        },
        ("Bohater", "Odkrywca"): {
            "*": "Proaktywni odkrywcy",
        },
    }

    if not a1:
        return "Segment"
    if not a2 or a2 == a1:
        return single_map.get(a1, a1)

    rule = pair_map.get((a1, a2))
    if rule:
        return str(rule.get(a3) or rule.get("*") or "Segment")

    fallback_noun = {
        "Władca": "decydenci",
        "Bohater": "sprawcy",
        "Mędrzec": "stratedzy",
        "Opiekun": "opiekunowie",
        "Kochanek": "wspólnotowcy",
        "Błazen": "animatorzy",
        "Twórca": "innowatorzy",
        "Odkrywca": "odkrywcy",
        "Czarodziej": "wizjonerzy",
        "Towarzysz": "wspólnotowcy",
        "Niewinny": "strażnicy",
        "Buntownik": "reformatorzy",
    }
    return f"{single_map.get(a1, a1)} {fallback_noun.get(a2, 'uczestnicy')}"


def _dedupe_segment_marketing_names(
        segs: List[Dict[str, Any]],
        brand_values: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Compat-wrapper.
    Zostawiamy historyczną nazwę helpera, ale cała logika unikalności
    jest już skupiona wyłącznie w _ensure_unique_segment_names().
    """
    return _ensure_unique_segment_names(segs, brand_values)


def _segment_ui_colors(seg_num: int) -> Dict[str, str]:
    """
    Spójna paleta segmentów:
    - kolory segmentów NIE mogą zlewać się z niebieskimi punktami archetypów,
    - dlatego usuwamy niebieski akcent z segmentu nr 4.
    """
    palette: Dict[int, Dict[str, str]] = {
        1: {
            "accent": "#e03131",
            "soft": "#fff5f5",
            "line": "#ffc9c9",
            "chip_bg": "#fff5f5",
            "chip_bd": "#ffc9c9",
            "chip_fg": "#c92a2a",
        },
        2: {
            "accent": "#f08c00",
            "soft": "#fff4e6",
            "line": "#ffd8a8",
            "chip_bg": "#fff4e6",
            "chip_bd": "#ffd8a8",
            "chip_fg": "#a85b00",
        },
        3: {
            "accent": "#2f9e44",
            "soft": "#ebfbee",
            "line": "#b2f2bb",
            "chip_bg": "#ebfbee",
            "chip_bd": "#b2f2bb",
            "chip_fg": "#2b8a3e",
        },
        4: {
            "accent": "#8d6e63",
            "soft": "#f7f3f2",
            "line": "#d7ccc8",
            "chip_bg": "#f7f3f2",
            "chip_bd": "#d7ccc8",
            "chip_fg": "#6d4c41",
        },
        5: {
            "accent": "#5f3dc4",
            "soft": "#f3f0ff",
            "line": "#d0bfff",
            "chip_bg": "#f3f0ff",
            "chip_bd": "#d0bfff",
            "chip_fg": "#5f3dc4",
        },
        6: {
            "accent": "#0b7285",
            "soft": "#e3fafc",
            "line": "#99e9f2",
            "chip_bg": "#e3fafc",
            "chip_bd": "#99e9f2",
            "chip_fg": "#0b7285",
        },
        7: {
            "accent": "#343a40",
            "soft": "#f8f9fa",
            "line": "#dee2e6",
            "chip_bg": "#f8f9fa",
            "chip_bd": "#dee2e6",
            "chip_fg": "#343a40",
        },
        8: {
            "accent": "#c2255c",
            "soft": "#fff0f6",
            "line": "#fcc2d7",
            "chip_bg": "#fff0f6",
            "chip_bd": "#fcc2d7",
            "chip_fg": "#a61e4d",
        },
        9: {
            "accent": "#ae3ec9",
            "soft": "#f8f0fc",
            "line": "#e5dbff",
            "chip_bg": "#f8f0fc",
            "chip_bd": "#e5dbff",
            "chip_fg": "#862e9c",
        },
    }
    return dict(palette.get(int(seg_num), palette[1]))


def _demography_table_for_segment(metry: pd.DataFrame, seg_mask: np.ndarray, weights: np.ndarray) -> pd.DataFrame:
    """
    Zwraca tabelę PVQ-style: zmienna, kategoria, % segment, % próba, lift (pp).
    """
    rows = _format_segment_demography_rows(metry, seg_mask, weights)
    if not rows:
        return pd.DataFrame(columns=["zmienna", "kategoria", "pct_seg", "pct_all", "lift_pp"])

    df = pd.DataFrame(rows)
    # porządek kolumn (na potrzeby HTML)
    for col in ["zmienna", "kategoria", "pct_seg", "pct_all", "lift_pp"]:
        if col not in df.columns:
            df[col] = np.nan
    return df[["zmienna", "kategoria", "pct_seg", "pct_all", "lift_pp"]]


def _segment_profiles_from_ranked_labels(labels_ranked: np.ndarray,
                                         metry: Optional[pd.DataFrame],
                                         P: np.ndarray, E: np.ndarray, G: np.ndarray, w: np.ndarray,
                                         brand_values: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Buduje profile segmentów dla etykiet już zremapowanych do rankingu (Seg_1..Seg_k).
    Nie robi ponownego rankingu – zachowuje numerację przekazaną w labels_ranked.
    """
    labels = np.asarray(labels_ranked, dtype=int).reshape(-1)
    w = np.asarray(w, dtype=float).reshape(-1)

    if labels.size == 0:
        return []

    P_overall = _wmean_cols(P, w)
    E_overall = _wmean_cols(E, w)
    G_overall = _wmean_cols(G, w)

    segs: List[Dict[str, Any]] = []
    unique_ids = sorted([int(x) for x in np.unique(labels) if np.isfinite(x)])

    for sid in unique_ids:
        m = labels == sid
        if not np.any(m):
            continue

        ws = w[m]
        Pm = _wmean_cols(P[m], ws)
        Em = _wmean_cols(E[m], ws)
        Gm = _wmean_cols(G[m], ws)

        dP = Pm - P_overall
        dE = Em - E_overall
        dG = Gm - G_overall

        top_idx = np.argsort(-Pm)[:3]
        bot_idx = np.argsort(Pm)[:3]
        top3 = [ARCHETYPES[i] for i in top_idx]
        bot3 = [ARCHETYPES[i] for i in bot_idx]

        name_marketing_arche = _make_marketing_name_from_top3(top3, brand_values, mode="arche")
        name_marketing_values = _make_marketing_name_from_top3(top3, brand_values, mode="values")

        opis, sugestie, ryzyka = make_segment_profile(top3, bot3)

        if metry is not None and len(metry):
            demo_rows = _format_segment_demography_rows(metry, m, w)
        else:
            demo_rows = []

        segs.append(
            _build_segment_payload(
                sid=int(sid),
                seg_rank=int(sid),
                n_seg=int(m.sum()),
                share_pct=float((ws.sum() / (w.sum() + 1e-12)) * 100.0),
                top3_arche=top3,
                bottom_arche=bot3,
                brand_values=brand_values,
                Pm=Pm,
                Em=Em,
                Gm=Gm,
                deltaP=dP,
                deltaE=dE,
                deltaG=dG,
                usefulness=_segment_usefulness_from_P(Pm, P_overall),
                opis=opis,
                sugestie=sugestie,
                ryzyka=ryzyka,
                demografia_rows=demo_rows,
                name_marketing_arche=name_marketing_arche,
                name_marketing_values=name_marketing_values,
            )
        )

    segs = _ensure_unique_segment_names(segs, brand_values)
    return segs


def _export_segment_profiles_csv(segs: List[Dict[str, Any]], outpath: Path) -> None:
    rows: List[Dict[str, Any]] = []

    def _as_text(x: Any) -> str:
        if x is None:
            return ""
        if isinstance(x, (list, tuple)):
            parts = [str(v).strip() for v in x if str(v).strip()]
            return " | ".join(parts)
        return str(x)

    for s in segs:
        demo_rows = _segment_demography_rows(s)
        demo_short = " | ".join(
            [f'{r.get("zmienna", "")}: {r.get("kategoria", "")} ({float(r.get("lift_pp", 0.0)):+.1f} pp)' for r in
             demo_rows[:5]]
        )

        name_arche, name_values = _segment_name_pair(s)

        top3_arche = [str(x) for x in (s.get("top3_arche") or s.get("top3") or [])]
        top3_values = [str(x) for x in (s.get("top3_values") or s.get("top3_arche") or s.get("top3") or [])]
        bottom_arche = [str(x) for x in (s.get("bottom_arche") or [])]

        row = {
            "segment_id": int(s.get("segment_id", 0)),
            "segment": str(s.get("segment_label") or s.get("segment") or f'Seg_{int(s.get("segment_id", 0)) + 1}'),
            "n": int(_safe_float(s.get("n", 0))),
            "n_base": int(_safe_float(s.get("n_base", s.get("n", 0)))),
            "share_pct": float(s.get("share_pct", 0.0)),
            "share_pct_base": float(_safe_float(s.get("share_pct_base", s.get("share_pct", 0.0)))),
            "segment_size_source": str(s.get("segment_size_source", "cluster_kmeans")),
            "active_hits_count": int(_safe_float(s.get("active_hits_count", 0))),
            "name_marketing_arche": name_arche,
            "name_marketing_values": name_values,
            "top3_arche": " | ".join(top3_arche),
            "top3_values": " | ".join(top3_values),
            "bottom_arche": " | ".join(bottom_arche),
            "usefulness": float(s.get("usefulness", 0.0)),
            "opis": _as_text(s.get("opis", "")),
            "sugestie": _as_text(s.get("sugestie", "")),
            "ryzyka": _as_text(s.get("ryzyka", "")),
            "demografia_top": demo_short,
        }

        try:
            pm_share_arr = np.asarray(s.get("Pm_share_pct", []), dtype=float).reshape(-1)
        except Exception:
            pm_share_arr = np.asarray([], dtype=float)

        if pm_share_arr.shape[0] != len(ARCHETYPES):
            pm_share_arr = np.asarray(_pm_profile_share_pct(s.get("Pm", [])), dtype=float)

        for i, arch in enumerate(ARCHETYPES):
            row[f"pm_share_{arch}"] = float(pm_share_arr[i]) if i < len(pm_share_arr) else 0.0

        rows.append(row)

    pd.DataFrame(rows).to_csv(outpath, index=False, encoding="utf-8-sig")


def _export_segment_matrix_csv(seg_df: pd.DataFrame, outpath: Path, metric_key: str) -> None:
    """
    Eksport macierzy segment × archetyp dla P/E/G.

    Obsługuje:
    - format long: kolumny [segment_id, archetyp, P_mean/E_mean/G_mean]
    - format wide: index=Seg_*, kolumny=ARCHETYPES, wartości = surowe poziomy (nie delta)
    """
    metric_key = str(metric_key).upper().strip()

    # Long format (absolutne średnie)
    col_val = f"{metric_key}_mean"
    if {"segment_id", "archetyp", col_val}.issubset(set(seg_df.columns)):
        pivot = seg_df.pivot(index="segment_id", columns="archetyp", values=col_val).copy()
        pivot = pivot.reindex(columns=list(ARCHETYPES))
        pivot = pivot.reindex(sorted(pivot.index))
        pivot.index = [f"Seg_{int(i) + 1}" for i in pivot.index]
        pivot.index.name = "segment"
        pivot.reset_index().to_csv(outpath, index=False, encoding="utf-8-sig")
        return

    # Wide format (surowe poziomy)
    if all(a in seg_df.columns for a in ARCHETYPES):
        out = seg_df.copy()
        out = out.reindex(columns=list(ARCHETYPES))
        out.index.name = "segment"
        out.reset_index().to_csv(outpath, index=False, encoding="utf-8-sig")
        return

    # Fallback: pusty plik z nagłówkiem
    pd.DataFrame(columns=["segment"] + list(ARCHETYPES)).to_csv(outpath, index=False, encoding="utf-8-sig")


def plot_values_map_data(E: np.ndarray, w: np.ndarray, outdir: Path, fname_base: str,
                         brand_values: Dict[str, str],
                         seg_labels: Optional[np.ndarray] = None,
                         seg_profiles: Optional[List[Dict[str, Any]]] = None) -> None:
    """
    Rysuje mapę wartości (DATA) w 2 wersjach: archetypy i wartości.
    Jeśli podasz seg_labels + seg_profiles, centroidy segmentów dostaną spójne nazwy segmentów.
    """
    M = np.asarray(E, dtype=float)
    weights = np.asarray(w, dtype=float).reshape(-1)

    # układ DATA wyliczany z danych
    coords_xy, _meta = build_value_space_from_P(M, list(ARCHETYPES))
    coords_xy = np.asarray(coords_xy, dtype=float)

    # pozycje respondentów jako średnia ważona punktów archetypów
    resp_xy = respondent_positions(M, coords_xy)

    seg_centroids = None
    if seg_labels is not None:
        try:
            labs = np.asarray(seg_labels, dtype=int).reshape(-1)
            if len(labs) == len(resp_xy) and len(labs) > 0:
                k = int(np.nanmax(labs)) + 1
                if k >= 1:
                    seg_centroids = build_segment_centroids(resp_xy, labs, weights, K=k)
        except Exception:
            seg_centroids = None

    seg_names_arche: Optional[Dict[int, str]] = None
    seg_names_values: Optional[Dict[int, str]] = None
    if seg_profiles:
        seg_names_arche = {}
        seg_names_values = {}
        for s in seg_profiles:
            sid = int(s.get("segment_rank", s.get("segment_id", 0)))
            nm_a, _nm_v = _segment_name_pair(s)
            seg_names_arche[sid] = nm_a
            seg_names_values[sid] = nm_a

    if "_E_" in fname_base:
        title_base = "MAPA WARTOŚCI – doświadczenie (E)"
    elif "_P_" in fname_base:
        title_base = "MAPA WARTOŚCI –  preferencje (P)"
    elif "_G_" in fname_base:
        title_base = "MAPA WARTOŚCI – priorytety (G)"
    else:
        title_base = "MAPA WARTOŚCI"

    plot_value_map(
        outpath=outdir / f"{fname_base}.png",
        title=title_base,
        coords=coords_xy,
        respondent_xy=resp_xy,
        seg_centroids=seg_centroids,
        point_labels=list(ARCHETYPES),
        seg_names=seg_names_arche,
    )

    plot_value_map(
        outpath=outdir / f"{fname_base}_values.png",
        title=title_base,
        coords=coords_xy,
        respondent_xy=resp_xy,
        seg_centroids=seg_centroids,
        point_labels=[brand_values.get(a, a) for a in ARCHETYPES],
        seg_names=seg_names_values,
    )


def main() -> None:
    root = Path(__file__).resolve().parent
    settings = load_settings(root / "settings.json")
    configure_archetype_label_mode(settings.archetype_label_mode)
    brand_values = load_brand_values(root)
    value_labels = [brand_values[a] for a in ARCHETYPES]

    data_path = root / "data.csv"
    if not data_path.exists():
        raise FileNotFoundError("Brak pliku data.csv w folderze narzędzia.")

    df = read_data_csv(data_path)

    # metryczka (profilowe zmienne)
    metry, metry_defs = parse_metryczka(df, settings.metryczka_config)

    base_weights = get_weights(df, settings.weight_column)
    poststrat_error = ""
    try:
        weights, poststrat_diag = apply_poststrat_weights_from_targets(root, metry, base_weights)
    except Exception as e:
        poststrat_error = str(e)
        print(
            "[WARN] Nie udało się zastosować wag poststratyfikacyjnych. "
            "Analiza kontynuuje z wagą bazową. Powód: "
            + poststrat_error
        )
        weights = np.asarray(base_weights, dtype=float).reshape(-1)
        poststrat_diag = None

    outdir = ensure_outdir(root)

    if poststrat_diag is not None:
        poststrat_diag.to_csv(
            outdir / "weights_poststrat_report.csv",
            index=False,
            encoding="utf-8-sig"
        )

    # Parsowanie
    # Parsowanie
    A = parse_A_matrix(df)
    b1, b2, b2_diag = parse_B(df)
    d12, d13, d13_diag = parse_D(df)
    save_parser_archetype_diagnostics(outdir, [b2_diag, d13_diag])
    for _diag in [b2_diag, d13_diag]:
        miss_cnt = int(_diag.get("missing_or_unknown_count", 0) or 0)
        if miss_cnt <= 0:
            continue
        top_unknown = _diag.get("unknown_top") or []
        top_txt = ", ".join(f"{str(x.get('value', ''))}: {int(x.get('count', 0) or 0)}" for x in top_unknown[:5])
        print(
            f"[WARN] Parser {_diag.get('field', '?')}: {miss_cnt} wartości nierozpoznanych/braków. "
            + (f"Top nieznane: {top_txt}" if top_txt else "")
        )

    # ===== Nowa sekcja: A) Oczekiwanie archetypów — % mieszkańców (18 par) =====
    respondent_id_col = "respondent_id" if "respondent_id" in df.columns else "__respondent_id__"
    df_expect = df.copy()
    if respondent_id_col == "__respondent_id__":
        df_expect[respondent_id_col] = np.arange(1, len(df_expect) + 1, dtype=int)

    expectation_weighting_meta = resolve_active_weighting_basis(
        root=root,
        n_rows=len(df_expect),
        weights=weights,
        poststrat_diag=poststrat_diag,
        poststrat_error=poststrat_error,
    )
    active_weights_for_expectation = np.asarray(
        expectation_weighting_meta.get("active_weights", np.ones(len(df_expect), dtype=float)),
        dtype=float
    ).reshape(-1)
    active_weight_col = str(expectation_weighting_meta.get("active_weight_col", "") or "")
    if active_weight_col:
        df_expect[active_weight_col] = active_weights_for_expectation

    df_A_expectation_long = build_pair_long_table(
        df=df_expect,
        pair_map=PAIR_MAP,
        respondent_id_col=respondent_id_col,
        weight_col=active_weight_col if active_weight_col else None,
    )
    df_A_expectation_scores = compute_respondent_archetype_scores(df_A_expectation_long)
    df_A_expectation_scores = classify_respondent_archetype_support(df_A_expectation_scores)
    df_A_expectation_scores.to_csv(
        outdir / "A_expectation_respondent_archetype_scores.csv", index=False, encoding="utf-8-sig"
    )

    df_A_expectation_support = aggregate_archetype_support(
        scores_table=df_A_expectation_scores,
        weight_col="weight",
        weighted=bool(expectation_weighting_meta.get("weighted", False)),
    )
    df_A_expectation_ioa = compute_ioa(
        scores_table=df_A_expectation_scores,
        weight_col="weight",
        weighted=bool(expectation_weighting_meta.get("weighted", False)),
    )

    df_A_expectation_summary = df_A_expectation_support.merge(
        df_A_expectation_ioa,
        on="archetype",
        how="left"
    )
    df_A_expectation_main = build_main_expectation_table(df_A_expectation_summary)

    df_A_expectation_pair_detail = build_pair_detail_table(
        long_table=df_A_expectation_long,
        weighted=bool(expectation_weighting_meta.get("weighted", False)),
        weight_col="weight",
    )

    df_A_expectation_main_out = df_A_expectation_main[[
        "position",
        "archetype",
        "expected_pct",
        "neutral_pct",
        "not_expected_pct",
        "strong_expected_pct",
        "ioa_100",
        "ioa_raw",
        "n_respondents_valid",
    ]].rename(columns={
        "position": "Pozycja",
        "archetype": "Archetyp",
        "expected_pct": "% oczekujących",
        "neutral_pct": "% neutralnych",
        "not_expected_pct": "% nieoczekujących",
        "strong_expected_pct": "% silnie oczekujących",
        "ioa_100": "PPP 0-100",
        "ioa_raw": "PPP raw (-3 do +3)",
        "n_respondents_valid": "Liczba respondentów",
    }).copy()

    for c in ["% oczekujących", "% neutralnych", "% nieoczekujących", "% silnie oczekujących", "PPP 0-100"]:
        if c in df_A_expectation_main_out.columns:
            df_A_expectation_main_out[c] = pd.to_numeric(df_A_expectation_main_out[c], errors="coerce").round(1)
    if "PPP raw (-3 do +3)" in df_A_expectation_main_out.columns:
        df_A_expectation_main_out["PPP raw (-3 do +3)"] = pd.to_numeric(
            df_A_expectation_main_out["PPP raw (-3 do +3)"], errors="coerce"
        ).round(2)
    if "Liczba respondentów" in df_A_expectation_main_out.columns:
        df_A_expectation_main_out["Liczba respondentów"] = pd.to_numeric(
            df_A_expectation_main_out["Liczba respondentów"], errors="coerce"
        ).fillna(0).astype(int)

    df_A_expectation_pair_detail_out = df_A_expectation_pair_detail.rename(columns={
        "pair_id": "ID pary",
        "left_archetype": "Archetyp lewy",
        "right_archetype": "Archetyp prawy",
        "mean_response_1_7": "Średnia odpowiedź 1-7",
        "pct_response_1_3": "% odpowiedzi 1-3",
        "pct_response_4": "% odpowiedzi 4",
        "pct_response_5_7": "% odpowiedzi 5-7",
        "mean_points_left": "Średnie punkty lewego",
        "mean_points_right": "Średnie punkty prawego",
        "n": "N",
    }).copy()
    for c in [
        "Średnia odpowiedź 1-7",
        "% odpowiedzi 1-3",
        "% odpowiedzi 4",
        "% odpowiedzi 5-7",
        "Średnie punkty lewego",
        "Średnie punkty prawego",
    ]:
        if c in df_A_expectation_pair_detail_out.columns:
            df_A_expectation_pair_detail_out[c] = pd.to_numeric(
                df_A_expectation_pair_detail_out[c], errors="coerce"
            ).round(1 if "%" in c else 2)
    if "N" in df_A_expectation_pair_detail_out.columns:
        df_A_expectation_pair_detail_out["N"] = pd.to_numeric(
            df_A_expectation_pair_detail_out["N"], errors="coerce"
        ).fillna(0).astype(int)

    if not df_A_expectation_main.empty:
        s_expected_pct = (
            df_A_expectation_main
            .set_index("archetype")["expected_pct"]
            .astype(float)
            .sort_values(ascending=False)
        )
        plot_horizontal_metric_chart(
            s_expected_pct,
            outdir / "A_expectation_expected_pct.png",
            "Społeczne oczekiwanie archetypu (%)",
            xlabel="Mieszkańcy oczekujący archetypu (%)",
            x_min=0.0,
            x_max=100.0,
            value_fmt="{:.1f}",
            value_suffix="%",
        )
        plot_horizontal_metric_chart(
            series_with_value_index(s_expected_pct, brand_values),
            outdir / "A_expectation_expected_pct_values.png",
            "Społeczne oczekiwanie wartości (%)",
            xlabel="Mieszkańcy oczekujący wartości (%)",
            x_min=0.0,
            x_max=100.0,
            value_fmt="{:.1f}",
            value_suffix="%",
        )

        s_ioa_100 = (
            df_A_expectation_main
            .set_index("archetype")["ioa_100"]
            .astype(float)
            .sort_values(ascending=False)
        )
        df_balance_order = (
            df_A_expectation_main[["archetype", "expected_pct", "neutral_pct", "not_expected_pct", "ioa_100"]]
            .copy()
            .sort_values(["expected_pct", "ioa_100"], ascending=[False, False], kind="mergesort")
        )
        plot_expectation_balance_stacked(
            df_balance_order,
            outdir / "A_expectation_balance_distribution.png",
            "Bilans społecznego oczekiwania archetypów",
        )
        df_balance_values = df_balance_order.copy()
        df_balance_values["archetype"] = df_balance_values["archetype"].astype(str).map(
            lambda a: str(brand_values.get(a, a))
        )
        plot_expectation_balance_stacked(
            df_balance_values,
            outdir / "A_expectation_balance_distribution_values.png",
            "Bilans społecznego oczekiwania wartości",
        )
        plot_horizontal_metric_chart(
            s_ioa_100,
            outdir / "A_expectation_ioa_100.png",
            "Profil Preferencji Przywództwa (PPP)",
            xlabel="PPP 0-100",
            x_min=0.0,
            x_max=100.0,
            value_fmt="{:.1f}",
            reference_line=50.0,
        )
        plot_horizontal_metric_chart(
            series_with_value_index(s_ioa_100, brand_values),
            outdir / "A_expectation_ioa_100_values.png",
            "Profil Preferencji Przywództwa (PPP)",
            xlabel="PPP 0-100",
            x_min=0.0,
            x_max=100.0,
            value_fmt="{:.1f}",
            reference_line=50.0,
        )

    expectation_summary_payload = {
        "top_expected": (
            df_A_expectation_main.sort_values("expected_pct", ascending=False)["archetype"].head(3).astype(str).tolist()
            if not df_A_expectation_main.empty else []
        ),
        "bottom_expected": (
            df_A_expectation_main.sort_values("expected_pct", ascending=True)["archetype"].head(3).astype(str).tolist()
            if not df_A_expectation_main.empty else []
        ),
        "top_ioa": (
            df_A_expectation_main.sort_values("ioa_100", ascending=False)["archetype"].head(3).astype(str).tolist()
            if not df_A_expectation_main.empty else []
        ),
        "bottom_ioa": (
            df_A_expectation_main.sort_values("ioa_100", ascending=True)["archetype"].head(3).astype(str).tolist()
            if not df_A_expectation_main.empty else []
        ),
    }

    df_A_expectation_main.to_csv(
        outdir / "A_expectation_main_technical.csv", index=False, encoding="utf-8-sig"
    )
    df_A_expectation_main_out.to_csv(
        outdir / "A_expectation_main_table.csv", index=False, encoding="utf-8-sig"
    )
    df_A_expectation_pair_detail.to_csv(
        outdir / "A_expectation_pair_detail_technical.csv", index=False, encoding="utf-8-sig"
    )
    df_A_expectation_pair_detail_out.to_csv(
        outdir / "A_expectation_pair_detail_table.csv", index=False, encoding="utf-8-sig"
    )
    df_A_expectation_long.to_csv(
        outdir / "A_expectation_long_table.csv", index=False, encoding="utf-8-sig"
    )
    pd.DataFrame([{
        "weighting_applied_flag": bool(expectation_weighting_meta.get("weighting_applied_flag", False)),
        "data_basis_status": str(expectation_weighting_meta.get("data_basis_status", "raw_unweighted")),
        "data_basis_label": str(expectation_weighting_meta.get("data_basis_label", "")),
        "data_basis_reason": str(expectation_weighting_meta.get("data_basis_reason", "")),
        "active_weight_col": str(expectation_weighting_meta.get("active_weight_col", "")),
    }]).to_csv(outdir / "A_expectation_data_basis_status.csv", index=False, encoding="utf-8-sig")

    df_manual_validation = _run_manual_expectation_examples_validation()
    df_manual_validation.to_csv(
        outdir / "A_expectation_manual_validation.csv", index=False, encoding="utf-8-sig"
    )

    # Zbiorcze wskazania (A/B1/B2/D13) — tabela + wykres do podsumowania
    A_cols = [(left, right) for _, left, right in A_PAIRS]

    df_mentions = total_mentions_counts(
        A, A_cols, b1, b2, d13, weights, weighted_counts=False
    )
    df_mentions_out = df_mentions.reset_index().rename(columns={"index": "archetyp"})
    df_mentions_out.to_csv(outdir / "mentions_total.csv", index=False, encoding="utf-8-sig")

    # Tabela: ile wskazań było w poszczególnych pytaniach (A1–A18, B1, B2, D13)
    df_mentions_q = mentions_counts_by_question(
        A, b1, b2, d13, weights, as_int=True, weighted_counts=False
    )
    df_mentions_q.to_csv(outdir / "mentions_by_question.csv", index=False, encoding="utf-8-sig")
    df_mentions_diag = validate_mentions_by_question_counts(df_mentions_q, A, b1, b2, d13)
    df_mentions_diag.to_csv(outdir / "diag_mentions_by_question.csv", index=False, encoding="utf-8-sig")

    # Wersja do raportu: puste zamiast 0 + sumy wierszy/kolumn
    df_mentions_q_report = mentions_counts_by_question_for_report(df_mentions_q)

    # B: pełne tabele do zakładki B + wykresy
    df_B1, df_B2, df_B_tr = B_rankings(b1, b2, weights)
    df_B1.to_csv(outdir / "B1_top3.csv", index=False, encoding="utf-8-sig")
    df_B2.to_csv(outdir / "B2_top1.csv", index=False, encoding="utf-8-sig")
    df_B_tr.to_csv(outdir / "B1_trojki.csv", index=False, encoding="utf-8-sig")

    plot_B_bar(df_B1, outdir / "B1_top3.png", "Kluczowe oczekiwania od miasta (TOP3 archetypów)")
    plot_B_bar(
        df_display_values(df_B1, brand_values),
        outdir / "B1_top3_values.png",
        "Kluczowe oczekiwania od miasta (TOP3 wartości)"
    )

    plot_B_bar(df_B2, outdir / "B2_top1.png", "Najważniejsze oczekiwanie (archetyp wskazany jako najważniejszy)")
    plot_B_bar(
        df_display_values(df_B2, brand_values),
        outdir / "B2_top1_values.png",
        "Najważniejsze oczekiwanie (wartość wskazana jako najważniejsza)"
    )

    df_B_tr_plot = B1_combo_topk(b1, arch_names=ARCHETYPES, k=5)
    plot_B1_combo_bar(df_B_tr_plot, outdir / "B1_trojki_top5.png")
    plot_B1_combo_bar(
        df_display_values(df_B_tr_plot, brand_values, replace_inside=True),
        outdir / "B1_trojki_top5_values.png",
        title="5 najczęstszych trójek (kombinacje)"
    )

    # D: pełne tabele do zakładki D + wykresy
    df_D12, df_D13 = D_sentiment(d12, d13, weights)
    df_D12.to_csv(outdir / "D_sentiment.csv", index=False, encoding="utf-8-sig")
    df_D13.to_csv(outdir / "D13_rozkład.csv", index=False, encoding="utf-8-sig")

    diverging_plus_minus_chart(df_D12, outdir / "D_plus_minus_diverging.png", "Negatywne vs pozytywne")
    diverging_plus_minus_chart(
        df_display_values(df_D12, brand_values),
        outdir / "D_plus_minus_diverging_values.png",
        "Negatywne vs pozytywne"
    )

    d_wheel_order = [
        "Buntownik",
        "Błazen",
        "Kochanek",
        "Opiekun",
        "Towarzysz",
        "Niewinny",
        "Władca",
        "Mędrzec",
        "Czarodziej",
        "Bohater",
        "Twórca",
        "Odkrywca",
    ]
    d_wheel_value_order = [str(brand_values.get(a, a)) for a in d_wheel_order]

    wheel_plus_minus_chart(
        df_D12,
        "Koło Doświadczeń - pozytywne vs negatywne",
        str(outdir / "D_kolo_plus_minus.png"),
        order=d_wheel_order
    )
    wheel_plus_minus_chart(
        df_display_values(df_D12, brand_values),
        "Koło Doświadczeń - pozytywne vs negatywne",
        str(outdir / "D_kolo_plus_minus_values.png"),
        order=d_wheel_value_order
    )

    plot_D13_top1(df_D13, outdir / "D13_top1.png")
    plot_D13_top1(
        df_display_values(df_D13, brand_values),
        outdir / "D13_top1_values.png"
    )

    # ===== ISOA/ISOW: syntetyczny indeks społecznego oczekiwania (A, B1, B2, C13/D13) =====
    a_share_map = {str(a): float("nan") for a in ARCHETYPES}
    if isinstance(df_A_expectation_main, pd.DataFrame) and (len(df_A_expectation_main) > 0):
        _a_tmp = df_A_expectation_main.copy()
        _a_tmp["archetype"] = _a_tmp.get("archetype", "").astype(str)
        _a_tmp["expected_pct"] = pd.to_numeric(_a_tmp.get("expected_pct", np.nan), errors="coerce")
        for _a in ARCHETYPES:
            _row = _a_tmp[_a_tmp["archetype"] == str(_a)]
            if len(_row) > 0:
                a_share_map[str(_a)] = float(_row.iloc[0]["expected_pct"])

    b1_share_map = compute_top3_share(df_B1, arch_names=ARCHETYPES)
    b2_share_map = compute_top1_share(df_B2, arch_names=ARCHETYPES)
    neg_share_map = compute_negative_experience_share(df_D12, arch_names=ARCHETYPES)
    mbal_map, mneg_map, mpos_map, mbal_denom = compute_most_important_experience_balance(
        d12=d12,
        d13=d13,
        weights=weights,
        arch_names=ARCHETYPES,
    )

    df_social_expectation_index_tech, social_expectation_meta = compute_social_expectation_index(
        a_pct=a_share_map,
        b1_pct=b1_share_map,
        b2_pct=b2_share_map,
        n_pct=neg_share_map,
        mbal_pp=mbal_map,
        arch_names=ARCHETYPES,
    )
    if isinstance(df_social_expectation_index_tech, pd.DataFrame) and not df_social_expectation_index_tech.empty:
        df_social_expectation_index_tech["Mneg_pct"] = (
            df_social_expectation_index_tech["archetype"].astype(str).map(lambda a: float(mneg_map.get(a, np.nan)))
        )
        df_social_expectation_index_tech["Mpos_pct"] = (
            df_social_expectation_index_tech["archetype"].astype(str).map(lambda a: float(mpos_map.get(a, np.nan)))
        )
        df_social_expectation_index_tech["MBAL_check_pp"] = (
            pd.to_numeric(df_social_expectation_index_tech["Mneg_pct"], errors="coerce")
            - pd.to_numeric(df_social_expectation_index_tech["Mpos_pct"], errors="coerce")
        )
    social_expectation_meta["mbal_denominator_weight"] = float(mbal_denom)
    social_expectation_meta["mneg_pct"] = {str(k): float(v) for k, v in mneg_map.items()}
    social_expectation_meta["mpos_pct"] = {str(k): float(v) for k, v in mpos_map.items()}
    social_expectation_meta["components_aligned"] = bool(
        set(a_share_map.keys()) == set(ARCHETYPES)
        and set(b1_share_map.keys()) == set(ARCHETYPES)
        and set(b2_share_map.keys()) == set(ARCHETYPES)
        and set(neg_share_map.keys()) == set(ARCHETYPES)
        and set(mbal_map.keys()) == set(ARCHETYPES)
    )

    df_social_expectation_index = df_social_expectation_index_tech.rename(columns={
        "position": "Pozycja",
        "archetype": "Archetyp",
        "SEI_100": "ISOA 0-100",
        "A_pct": "A: % oczekujących",
        "B1_pct": "B1: TOP3 (%)",
        "B2_pct": "B2: TOP1 (%)",
        "N_pct": "C13/D13: negatywne doświadczenie (%)",
        "MBAL_pp": "C13/D13: bilans najważniejszego doświadczenia",
        "K_B": "Korekta wariantu B",
    }).copy()
    for col, digits in [
        ("ISOA 0-100", 1),
        ("A: % oczekujących", 1),
        ("B1: TOP3 (%)", 1),
        ("B2: TOP1 (%)", 1),
        ("C13/D13: negatywne doświadczenie (%)", 1),
        ("C13/D13: bilans najważniejszego doświadczenia", 1),
        ("Korekta wariantu B", 2),
    ]:
        if col in df_social_expectation_index.columns:
            df_social_expectation_index[col] = pd.to_numeric(
                df_social_expectation_index[col], errors="coerce"
            ).round(digits)
    if "Pozycja" in df_social_expectation_index.columns:
        df_social_expectation_index["Pozycja"] = pd.to_numeric(
            df_social_expectation_index["Pozycja"], errors="coerce"
        ).fillna(0).astype(int)

    df_social_expectation_index_tech.to_csv(
        outdir / "ISOA_ISOW_technical.csv", index=False, encoding="utf-8-sig"
    )
    if isinstance(df_social_expectation_index_tech, pd.DataFrame) and not df_social_expectation_index_tech.empty:
        df_mbal_control = df_social_expectation_index_tech[[
            "position", "archetype", "Mneg_pct", "Mpos_pct", "MBAL_pp", "MBAL_check_pp"
        ]].copy()
        df_mbal_control = df_mbal_control.rename(columns={
            "position": "Pozycja",
            "archetype": "Archetyp",
            "Mneg_pct": "Mneg (%)",
            "Mpos_pct": "Mpos (%)",
            "MBAL_pp": "MBAL (Mneg-Mpos)",
            "MBAL_check_pp": "Kontrola MBAL (Mneg-Mpos)",
        })
        for col in ["Mneg (%)", "Mpos (%)", "MBAL (Mneg-Mpos)", "Kontrola MBAL (Mneg-Mpos)"]:
            df_mbal_control[col] = pd.to_numeric(df_mbal_control[col], errors="coerce").round(3)
        df_mbal_control.to_csv(
            outdir / "ISOA_ISOW_MBAL_control.csv", index=False, encoding="utf-8-sig"
        )
    df_social_expectation_index.to_csv(
        outdir / "ISOA_ISOW_table.csv", index=False, encoding="utf-8-sig"
    )

    _isoa_series = (
        df_social_expectation_index_tech.set_index("archetype")["SEI_100"].astype(float)
        if ("archetype" in df_social_expectation_index_tech.columns and "SEI_100" in df_social_expectation_index_tech.columns)
        else pd.Series(dtype=float)
    )
    _isoa_vals = np.asarray([float(_isoa_series.get(str(a), np.nan)) for a in ARCHETYPES], dtype=float)
    _isoa_vals = np.where(np.isfinite(_isoa_vals), np.clip(_isoa_vals, 0.0, 100.0), 0.0)
    _plot_segment_profile_wheel(
        outpath=outdir / "ISOA_ISOW_wheel.png",
        pm_share_pct=_isoa_vals,
        brand_values=brand_values,
        mode="arche",
        value_suffix="",
    )
    _plot_segment_profile_wheel(
        outpath=outdir / "ISOA_ISOW_wheel_values.png",
        pm_share_pct=_isoa_vals,
        brand_values=brand_values,
        mode="values",
        value_suffix="",
    )

    # ===== TOP5 (A, B1, B2, D13) – poprawne % =====
    # + dodatkowo: pełne % dla WSZYSTKICH archetypów (dla zakładki "Filtry")

    # ---------- A: pełne % oczekujących (IOA; wszystkie archetypy) ----------
    df_A_pct_all = (
        df_A_expectation_main[["archetype", "expected_pct"]]
        .rename(columns={"archetype": "archetyp", "expected_pct": "%"})
        .copy()
    )
    df_A_pct_all["%"] = pd.to_numeric(df_A_pct_all["%"], errors="coerce")

    df_top5_A = df_A_pct_all.sort_values("%", ascending=False).head(5).reset_index(drop=True).copy()
    df_top5_A["%"] = df_top5_A["%"].astype(float).round(1).map(lambda v: f"{v:.1f}%")
    df_top5_A.to_csv(outdir / "top5_A.csv", index=False, encoding="utf-8-sig")

    # ---------- B1: pełne % respondentów ----------
    b1_f = np.nan_to_num(b1, nan=0.0)
    answered_b1 = np.isfinite(b1).any(axis=1)
    denom_b1 = float(weights[answered_b1].sum()) if np.any(answered_b1) else float(weights.sum())

    counts_b1 = (b1_f * weights.reshape(-1, 1)).sum(axis=0)
    df_B1_pct_all = pd.DataFrame({
        "archetyp": ARCHETYPES,
        "%": np.where(denom_b1 > 0, counts_b1 / denom_b1 * 100.0, np.nan)
    })

    df_B1_pct = df_B1_pct_all.sort_values("%", ascending=False).head(5).copy()
    df_B1_pct["%"] = df_B1_pct["%"].astype(float).round(1).map(lambda v: f"{v:.1f}%")
    df_B1_pct.to_csv(outdir / "top5_B1.csv", index=False, encoding="utf-8-sig")

    # ---------- B2: pełne % respondentów (TOP1) ----------
    m_b2 = (b2 >= 0)
    denom_b2 = float(weights[m_b2].sum()) if np.any(m_b2) else float("nan")

    counts_b2 = np.zeros(len(ARCHETYPES), dtype=float)
    for i in range(len(ARCHETYPES)):
        counts_b2[i] = float(weights[m_b2 & (b2 == i)].sum())

    df_B2_pct_all = pd.DataFrame({
        "archetyp": ARCHETYPES,
        "%": np.where(denom_b2 > 0, counts_b2 / denom_b2 * 100.0, np.nan)
    })

    df_B2_pct = df_B2_pct_all.sort_values("%", ascending=False).head(5).copy()
    df_B2_pct["%"] = df_B2_pct["%"].astype(float).round(1).map(lambda v: f"{v:.1f}%")
    df_B2_pct.to_csv(outdir / "top5_B2.csv", index=False, encoding="utf-8-sig")

    # ---------- D13: pełne % respondentów (TOP1) ----------
    m_d13 = (d13 >= 0)
    denom_d13 = float(weights[m_d13].sum()) if np.any(m_d13) else float("nan")

    counts_d13 = np.zeros(len(ARCHETYPES), dtype=float)
    for i in range(len(ARCHETYPES)):
        counts_d13[i] = float(weights[m_d13 & (d13 == i)].sum())

    df_D13_pct_all = pd.DataFrame({
        "archetyp": ARCHETYPES,
        "%": np.where(denom_d13 > 0, counts_d13 / denom_d13 * 100.0, np.nan)
    })

    df_D13_pct = df_D13_pct_all.sort_values("%", ascending=False).head(5).copy()
    df_D13_pct["%"] = df_D13_pct["%"].astype(float).round(1).map(lambda v: f"{v:.1f}%")
    df_D13_pct.to_csv(outdir / "top5_D13.csv", index=False, encoding="utf-8-sig")

    # ---------- payload do zakładki "Filtry" (JSON-friendly) ----------
    def _df_to_map(df_all: pd.DataFrame) -> Dict[str, Optional[float]]:
        mp: Dict[str, Optional[float]] = {}
        for _i in range(len(df_all)):
            a = str(df_all.iloc[_i]["archetyp"])
            v = df_all.iloc[_i]["%"]
            try:
                fv = float(v)
                mp[a] = fv if np.isfinite(fv) else None
            except Exception:
                mp[a] = None
        return mp

    _A_map = _df_to_map(df_A_pct_all)
    _B1_map = _df_to_map(df_B1_pct_all)
    _B2_map = _df_to_map(df_B2_pct_all)
    _D13_map = _df_to_map(df_D13_pct_all)

    filters_pct = {}
    for a in [str(x) for x in ARCHETYPES]:
        filters_pct[a] = {
            "A": _A_map.get(a),
            "B1": _B1_map.get(a),
            "B2": _B2_map.get(a),
            "D13": _D13_map.get(a),
        }

    s_mentions = df_mentions["Razem"].sort_values(ascending=False)

    bar_chart(
        s_mentions,
        outdir / "mentions_total.png",
        "Łączna liczba wskazań archetypów",
        xlabel="Liczba wskazań",
        rotate=45,
        value_fmt="{:.0f}",
    )
    bar_chart(
        series_with_value_index(s_mentions, brand_values),
        outdir / "mentions_total_values.png",
        "Łączna liczba wskazań wartości",
        xlabel="Liczba wskazań",
        rotate=45,
        value_fmt="{:.0f}",
    )
    # A
    df_A_pairs = A_pair_stats(A, weights)
    df_A_strength = A_bradley_terry(A, weights)
    df_A_pair_balance = A_pair_outcome_balance(A, weights)

    df_A_pairs.to_csv(outdir / "A_pary.csv", index=False, encoding="utf-8-sig")
    df_A_pair_balance.to_csv(outdir / "A_zwyciestwa_przegrane.csv", index=False, encoding="utf-8-sig")

    df_A_raw_balance = A_raw_vote_balance(A)

    df_A_strength_out = df_A_strength[[
        "archetyp",
        "BT_scaled",
        "net",
        "liczba_wygranych",
        "liczba_przegranych",
    ]].rename(columns={
        "BT_scaled": "skala Bradley-Terry",
        "net": "bilans starć (ważony)",
    }).copy()
    df_A_strength_out["skala Bradley-Terry"] = df_A_strength_out["skala Bradley-Terry"].round(1)
    df_A_strength_out["bilans starć (ważony)"] = df_A_strength_out["bilans starć (ważony)"].round(0).astype(int)
    df_A_strength_out = df_A_strength_out.merge(df_A_raw_balance, on="archetyp", how="left")
    df_A_strength_out = df_A_strength_out.sort_values("skala Bradley-Terry", ascending=False).reset_index(drop=True)
    df_A_strength_out.to_csv(outdir / "A_sila_archetypow.csv", index=False, encoding="utf-8-sig")

    s_pair_balance = df_A_pair_balance.set_index("archetyp")["zwycięstwa vs przegrane"].sort_values(ascending=False)
    plot_pair_outcome_balance(
        s_pair_balance,
        outdir / "A_zwyciestwa_przegrane.png",
        "Zwycięstwa vs przegrane",
        xlabel="Bilans par (+1 / -1)",
        rotate=45,
    )
    plot_pair_outcome_balance(
        series_with_value_index(s_pair_balance, brand_values),
        outdir / "A_zwyciestwa_przegrane_values.png",
        "Zwycięstwa vs przegrane",
        xlabel="Bilans par (+1 / -1)",
        rotate=45,
    )

    s_battle = df_A_strength_out.set_index("archetyp")["bilans starć (ważony)"].astype(float).sort_values(ascending=False)
    bar_chart(
        s_battle,
        outdir / "A_bilans_starc.png",
        "Bilans starć (wygrane - przegrane)",
        xlabel="Bilans (ważony)",
        colors=["#2b6cb0"] * len(s_battle),
        value_fmt="{:.0f}",
        rotate=45,
    )
    bar_chart(
        series_with_value_index(s_battle, brand_values),
        outdir / "A_bilans_starc_values.png",
        "Bilans starć (wygrane - przegrane)",
        xlabel="Bilans (ważony)",
        colors=["#2b6cb0"] * len(s_battle),
        value_fmt="{:.0f}",
        rotate=45,
    )

    sA = df_A_strength.set_index("archetyp")["BT_scaled"]
    bar_chart(sA, outdir / "A_strength.png", "Siła archetypów (model Bradley–Terry)", xlabel="")
    bar_chart(series_with_value_index(sA, brand_values), outdir / "A_strength_values.png",
              "Siła wartości (model Bradley–Terry)", xlabel="")

    plot_A_versus_profile_line(
        df_A_pairs,
        outdir / "A_versusy_liniowy.png",
        title="Model podejścia do spraw miasta — profil liniowy archetypów",
    )
    plot_A_versus_profile_line(
        df_A_pairs,
        outdir / "A_versusy_liniowy_values.png",
        title="Model podejścia do spraw miasta — profil liniowy wartości",
        brand_values=brand_values,
    )

    # WSPÓLNE P / E / G — jedno źródło prawdy dla całego raportu i segmentacji
    P, E, G = build_PEG_from_ABD(
        A=A, b1=b1, b2=b2, d12=d12, d13=d13,
        w_A=float(settings.w_A),
        weights=weights,
        archetypes=ARCHETYPES
    )

    def wmean(mat: np.ndarray) -> np.ndarray:
        out = np.full(mat.shape[1], np.nan, dtype=float)
        for j in range(mat.shape[1]):
            xj = mat[:, j]
            m = np.isfinite(xj)
            if m.sum() == 0:
                continue
            out[j] = float(np.average(xj[m], weights=weights[m]))
        return out

    P_mean = wmean(P)
    E_mean = wmean(E)
    G_mean = wmean(G)

    P_lo, P_hi = bootstrap_ci(P, weights, settings.bootstrap_reps, seed=settings.random_seed + 1)
    E_lo, E_hi = bootstrap_ci(E, weights, settings.bootstrap_reps, seed=settings.random_seed + 2)
    G_lo, G_hi = bootstrap_ci(G, weights, settings.bootstrap_reps, seed=settings.random_seed + 3)

    df_group = pd.DataFrame({
        "archetyp": ARCHETYPES,
        "P_mean": P_mean, "P_lo": P_lo, "P_hi": P_hi,
        "E_mean": E_mean, "E_lo": E_lo, "E_hi": E_hi,
        "G_mean": G_mean, "G_lo": G_lo, "G_hi": G_hi,
    }).sort_values("G_mean", ascending=False).reset_index(drop=True)

    for c in ["P_mean", "P_lo", "P_hi", "E_mean", "E_lo", "E_hi", "G_mean", "G_lo", "G_hi"]:
        if c in df_group.columns:
            df_group[c] = df_group[c].round(2)

    df_group.to_csv(outdir / "wyniki_grupowe.csv", index=False, encoding="utf-8-sig")

    P_series = pd.Series(P_mean, index=ARCHETYPES).sort_values(ascending=False)
    E_series = pd.Series(E_mean, index=ARCHETYPES).sort_values(ascending=False)
    G_series = pd.Series(G_mean, index=ARCHETYPES).sort_values(ascending=False)

    bar_chart(P_series, outdir / "P_mean.png", "Preferencje archetypowe (P)")
    bar_chart(series_with_value_index(P_series, brand_values), outdir / "P_mean_values.png",
              "Preferencje wartości (P)")

    bar_chart(E_series, outdir / "E_mean.png", "Doświadczanie miasta (E)")
    bar_chart(series_with_value_index(E_series, brand_values), outdir / "E_mean_values.png",
              "Doświadczanie wartości w mieście (E)")

    bar_chart(G_series, outdir / "G_mean.png", "Priorytet działania (G)")
    bar_chart(series_with_value_index(G_series, brand_values), outdir / "G_mean_values.png",
              "Priorytet działania (G)")

    plot_corr_heatmap_clustered(P, ARCHETYPES, outdir / "HEATMAPA_KORELACJI_P.png",
                                "Korelacje archetypów (preferencje - P) – grupowanie")
    plot_corr_heatmap_clustered(P, value_labels, outdir / "HEATMAPA_KORELACJI_P_values.png",
                                "Korelacje wartości (preferencje - P) – grupowanie")

    plot_corr_heatmap_clustered(np.nan_to_num(E, nan=0.0), ARCHETYPES, outdir / "HEATMAPA_KORELACJI_E.png",
                                "Korelacje archetypów (doświadczenia - E) – grupowanie")
    plot_corr_heatmap_clustered(np.nan_to_num(E, nan=0.0), value_labels, outdir / "HEATMAPA_KORELACJI_E_values.png",
                                "Korelacje wartości (doświadczenia - E) – grupowanie")

    plot_corr_heatmap_clustered(G, ARCHETYPES, outdir / "HEATMAPA_KORELACJI_G.png",
                                "Korelacje archetypów (priorytety - G) – grupowanie")
    plot_corr_heatmap_clustered(G, value_labels, outdir / "HEATMAPA_KORELACJI_G_values.png",
                                "Korelacje wartości (priorytety - G) – grupowanie")

    # --- ULTRA PREMIUM: jedna główna segmentacja motywacyjna (Pm -> META -> k-means) ---
    seg_pack_ultra = build_meta_seg_pack(
        tab_key="ultra_premium",
        metry=metry,  # metryczka tylko do opisu segmentów
        P=P, E=E, G=G,  # źródło prawdy = profil 12 archetypów / wartości
        w=weights,
        settings=settings,
        brand_values=brand_values,
        outdir=outdir,
        seed_offset=131,
    )

    seg_packs_render = {
        "ultra_premium": seg_pack_ultra
    }

    # --- SKUPIENIA: klasyczne k-średnich na profilu P ---
    cluster_pack = build_cluster_pack_kmeans(
        tab_key="skupienia_kmeans",
        metry=metry,
        P=P, E=E, G=G,
        w=weights,
        settings=settings,
        brand_values=brand_values,
        outdir=outdir,
        seed_offset=509,
    )

    # ---------- Eksport: przypisania respondentów (domyślny model ultra premium) ----------
    def _remap_labels(labels: np.ndarray, id_map: Dict[str, int]) -> np.ndarray:
        labels = np.asarray(labels, dtype=int).reshape(-1)
        out = np.zeros_like(labels)
        for i, v in enumerate(labels):
            out[i] = int(id_map.get(str(int(v)), int(v)))
        return out

    display_top_k = int(seg_pack_ultra.get("k_default_ui", 5))

    # źródło prawdy = dokładnie ten sam payload, który został już policzony w build_lca_seg_pack()
    base_k_model = int(seg_pack_ultra.get("k_model", seg_pack_ultra.get("best_k_default", 9)))
    base_item = (seg_pack_ultra.get("by_k") or {}).get(str(base_k_model), {}) or {}

    labels_ranked = np.asarray(base_item.get("labels_ranked", []), dtype=int).reshape(-1)
    labels_ranked_effective = np.asarray(base_item.get("labels_ranked_effective", []), dtype=int).reshape(-1)
    if labels_ranked_effective.size == len(df):
        labels_ranked = labels_ranked_effective

    if labels_ranked.size != len(df):
        raise RuntimeError("Brak spójnego labels_ranked w seg_pack_ultra['by_k'][k_model].")

    seg_prof_ultra = [dict(x) for x in (base_item.get("profiles_payload", []) or [])]
    if not seg_prof_ultra:
        raise RuntimeError("Brak spójnego profiles_payload w seg_pack_ultra['by_k'][k_model].")
    display_top_k = min(display_top_k, len(seg_prof_ultra), max(1, int(base_k_model)))

    # eksportowe macierze P/E/G liczymy z TYCH SAMYCH, kanonicznych payloadów segmentów
    seg_df = _seg_df_from_ranked_profiles(seg_prof_ultra)

    # ikony archetypów muszą być dostępne PRZED generacją PNG profilu
    icons_zip = root / "archetypy_ikony.zip"
    if icons_zip.exists():
        icons_dir = outdir / "icons"
        icons_dir.mkdir(parents=True, exist_ok=True)
        import zipfile
        with zipfile.ZipFile(icons_zip, "r") as zf:
            for name in zf.namelist():
                n = str(name)
                if n.lower().endswith(".png") and ("/" not in n) and ("\\" not in n):
                    zf.extract(n, icons_dir)

    # Stałe wykresy kołowe profilu segmentu: generujemy tylko jedną wersję,
    # zawsze z podpisami wartości (niezależnie od radio arche/wartości).
    for s in seg_prof_ultra:
        seg_rank = int(s.get("segment_rank", s.get("segment_id", 0)))
        seg_num = seg_rank + 1

        try:
            profile_share = np.asarray(s.get("Pm_share_pct", []), dtype=float).reshape(-1)
        except Exception:
            profile_share = np.asarray([], dtype=float)

        if profile_share.shape[0] != len(ARCHETYPES):
            profile_share = np.asarray(_pm_profile_share_pct(s.get("Pm", [])), dtype=float)

        if profile_share.shape[0] != len(ARCHETYPES):
            profile_share = np.asarray([0.0] * len(ARCHETYPES), dtype=float)

        _plot_segment_profile_wheel(
            outpath=outdir / _segment_profile_chart_filename(seg_num, "values"),
            pm_share_pct=profile_share,
            brand_values=brand_values,
            mode="values",
            value_suffix=""
        )

    # Mapy:
    # - plik bazowy = widok domyślny zgodny z suwakiem startowym,
    # - warianty K1..Kmodel = pełna skala dynamiczna pod suwak.
    seg_prof_ultra_maps = list(seg_prof_ultra)
    seg_map_arche_by_k: Dict[str, str] = {}
    seg_map_values_by_k: Dict[str, str] = {}

    def _remember_seg_map_names(k: int) -> None:
        kk = max(1, int(k))
        seg_map_arche_by_k[str(kk)] = f"SEGMENTY_META_MAPA_STALA_K{kk}.png"
        seg_map_values_by_k[str(kk)] = f"SEGMENTY_META_MAPA_STALA_K{kk}_values.png"

    try:
        _remember_seg_map_names(display_top_k)
        plot_segment_quadrant_map_fixed(
            segs=seg_prof_ultra_maps[:display_top_k],
            segs_logic=seg_prof_ultra_maps,
            brand_values=brand_values,
            outdir=outdir,
            fname_base=f"SEGMENTY_META_MAPA_STALA_K{display_top_k}",
            P_source=P,
            segment_threshold_overrides=settings.segment_hit_threshold_overrides,
            segment_outline_style=settings.segment_outline_style
        )

        for shown_k in range(1, len(seg_prof_ultra_maps) + 1):
            _remember_seg_map_names(shown_k)
            plot_segment_quadrant_map_fixed(
                segs=seg_prof_ultra_maps[:shown_k],
                segs_logic=seg_prof_ultra_maps,
                brand_values=brand_values,
                outdir=outdir,
                fname_base=f"SEGMENTY_META_MAPA_STALA_K{shown_k}",
                P_source=P,
                segment_threshold_overrides=settings.segment_hit_threshold_overrides,
                segment_outline_style=settings.segment_outline_style
            )

    except Exception as e:
        print(f"[WARN] Nie udało się zbudować stałej mapy ćwiartek segmentów: {e}")

    # Nazwy map per-K przekazujemy do JS, aby działało przełączanie suwaka
    # zarówno w raportach ZIP (relatywne pliki), jak i po osadzaniu standalone.
    if isinstance(seg_pack_ultra, dict):
        seg_pack_ultra["map_arche_by_k"] = dict(seg_map_arche_by_k)
        seg_pack_ultra["map_values_by_k"] = dict(seg_map_values_by_k)
    if isinstance(seg_packs_render, dict) and isinstance(seg_packs_render.get("ultra_premium"), dict):
        seg_packs_render["ultra_premium"]["map_arche_by_k"] = dict(seg_map_arche_by_k)
        seg_packs_render["ultra_premium"]["map_values_by_k"] = dict(seg_map_values_by_k)

    # Bąbelkowa macierz TOP segmentów została wyłączona:
    # pliki `SEGMENTY_ULTRA_PREMIUM_P_babelki.png` i
    # `SEGMENTY_ULTRA_PREMIUM_P_babelki_values.png` nie są używane w raporcie.

    _export_segment_profiles_csv(seg_prof_ultra, outdir / "SEGMENTY_ULTRA_PREMIUM_profile.csv")
    _export_segment_matrix_csv(seg_df, outdir / "SEGMENTY_ULTRA_PREMIUM_P_matrix.csv", "P")
    _export_segment_matrix_csv(seg_df, outdir / "SEGMENTY_ULTRA_PREMIUM_E_matrix.csv", "E")
    _export_segment_matrix_csv(seg_df, outdir / "SEGMENTY_ULTRA_PREMIUM_G_matrix.csv", "G")

    seg_name_arche_by_label = {}
    seg_name_values_by_label = {}

    for s in seg_prof_ultra:
        seg_label = str(s.get("segment", f"Seg_{int(s.get('segment_rank', s.get('segment_id', 0))) + 1}"))
        seg_name_arche_by_label[seg_label] = str(
            s.get("name_marketing_arche", s.get("name_arche", seg_label))
        )
        seg_name_values_by_label[seg_label] = str(
            s.get("name_marketing_values", s.get("name_marketing_arche", s.get("name_arche", seg_label)))
        )

    seg_labels = [f"Seg_{int(x) + 1}" for x in labels_ranked]

    out_assign = pd.DataFrame({
        "respondent_id": df["respondent_id"],
        "segment_id": labels_ranked.astype(int),
        "segment": seg_labels,
        "segment_name_arche": [seg_name_arche_by_label.get(lbl, lbl) for lbl in seg_labels],
        "segment_name_values": [seg_name_values_by_label.get(lbl, lbl) for lbl in seg_labels],
    })
    out_assign.to_csv(outdir / "respondenci_segmenty_ultra_premium.csv", index=False, encoding="utf-8-sig")

    # ---------- Eksport: przypisania i profile dla zakładki "Skupienia" ----------
    cluster_profiles = [dict(x) for x in (cluster_pack.get("profiles_payload", []) or [])]
    cluster_labels_ranked = np.asarray(cluster_pack.get("labels_ranked", []), dtype=int).reshape(-1)

    if cluster_profiles:
        cluster_seg_df = _seg_df_from_ranked_profiles(cluster_profiles)
        _export_segment_profiles_csv(cluster_profiles, outdir / "SKUPIENIA_KMEANS_profile.csv")
        _export_segment_matrix_csv(cluster_seg_df, outdir / "SKUPIENIA_KMEANS_P_matrix.csv", "P")
        _export_segment_matrix_csv(cluster_seg_df, outdir / "SKUPIENIA_KMEANS_E_matrix.csv", "E")
        _export_segment_matrix_csv(cluster_seg_df, outdir / "SKUPIENIA_KMEANS_G_matrix.csv", "G")

    if cluster_labels_ranked.size == len(df):
        cluster_name_arche_by_label: Dict[str, str] = {}
        cluster_name_values_by_label: Dict[str, str] = {}
        for s in cluster_profiles:
            seg_rank = int(_safe_float(s.get("segment_rank", s.get("segment_id", 0))))
            seg_label = str(s.get("segment", f"Seg_{seg_rank + 1}"))
            nm_a, nm_v = _segment_name_pair(s)
            cluster_name_arche_by_label[seg_label] = str(nm_a)
            cluster_name_values_by_label[seg_label] = str(nm_v)

        cluster_labels_txt = [f"Seg_{int(x) + 1}" for x in cluster_labels_ranked]
        out_cluster_assign = pd.DataFrame({
            "respondent_id": df["respondent_id"],
            "cluster_id": cluster_labels_ranked.astype(int),
            "cluster": cluster_labels_txt,
            "cluster_name_arche": [cluster_name_arche_by_label.get(lbl, lbl) for lbl in cluster_labels_txt],
            "cluster_name_values": [cluster_name_values_by_label.get(lbl, lbl) for lbl in cluster_labels_txt],
        })
        out_cluster_assign.to_csv(outdir / "respondenci_skupienia_kmeans.csv", index=False, encoding="utf-8-sig")

    # ===== MAPY WARTOŚCI (DATA) z overlay segmentów ultra_premium =====
    try:
        plot_values_map_data(
            E=E,
            w=weights,
            outdir=outdir,
            fname_base="MAPA_WARTOSCI_E_DATA",
            brand_values=brand_values,
            seg_labels=labels_ranked,
            seg_profiles=seg_prof_ultra_maps,
        )
        plot_values_map_data(
            E=P,
            w=weights,
            outdir=outdir,
            fname_base="MAPA_WARTOSCI_P_DATA",
            brand_values=brand_values,
            seg_labels=labels_ranked,
            seg_profiles=seg_prof_ultra_maps,
        )
        plot_values_map_data(
            E=G,
            w=weights,
            outdir=outdir,
            fname_base="MAPA_WARTOSCI_G_DATA",
            brand_values=brand_values,
            seg_labels=labels_ranked,
            seg_profiles=seg_prof_ultra_maps,
        )
    except Exception as e:
        print(f"[WARN] Nie udało się zbudować map wartości (DATA) dla ultra_premium: {e}")

    # XLSX dla wszystkich CSV w folderze WYNIKI
    export_xlsx_for_csv_folder(outdir)

    # ikony archetypów zostały już skopiowane wyżej — nie duplikujemy tej operacji drugi raz

    # (compat) map_cmp w tej wersji nie jest używany w raporcie — przekazujemy pusty słownik
    map_cmp = {}

    demo_city_label = (
        f"{settings.city_label} / (po wagowaniu)"
        if poststrat_diag is not None
        else f"{settings.city_label} / próba"
    )

    b2_declared_demo_payload = _build_b2_declared_demo_payload(
        metry=metry,
        b2=b2,
        weights=weights,
        labels_ranked=labels_ranked,
        seg_profiles=seg_prof_ultra,
        cluster_labels_ranked=np.asarray(cluster_pack.get("labels_ranked", []), dtype=int).reshape(-1),
        cluster_profiles=[dict(x) for x in (cluster_pack.get("profiles_payload", []) or [])],
        brand_values=brand_values,
        city_label=demo_city_label,
    )

    top5_simulation_payload = _build_top5_simulation_payload(
        metry=metry,
        b1=b1,
        weights=weights,
        b2=b2,
        d13=d13,
        brand_values=brand_values,
        city_label=demo_city_label,
        population_15_plus=settings.population_15_plus,
    )

    save_report(
        outdir, settings,
        df_group=df_group,
        df_A_pairs=df_A_pairs,
        df_A_strength=df_A_strength_out,
        df_A_pair_balance=df_A_pair_balance,
        df_B1=df_B1,
        df_B2=df_B2,
        df_B_tr=df_B_tr,
        df_D12=df_D12,
        df_D13=df_D13,
        df_mentions_q=df_mentions_q_report,
        df_top5_A=df_top5_A,
        df_B1_pct=df_B1_pct,
        df_B2_pct=df_B2_pct,
        df_D13_pct=df_D13_pct,
        df_A_expectation_main=df_A_expectation_main_out,
        df_A_expectation_pair_detail=df_A_expectation_pair_detail_out,
        expectation_summary_payload=expectation_summary_payload,
        expectation_weighting_meta=expectation_weighting_meta,
        df_social_expectation_index=df_social_expectation_index,
        social_expectation_meta=social_expectation_meta,
        seg_packs_render=seg_packs_render,
        filters_pct=filters_pct,
        brand_values=brand_values,
        poststrat_diag=poststrat_diag,
        b2_declared_demo_payload=b2_declared_demo_payload,
        top5_simulation_payload=top5_simulation_payload,
        cluster_pack=cluster_pack,
        n_respondents_total=len(df)
    )

    # Automatyczne otwarcie raportu w przeglądarce
    report_path = outdir / "raport.html"
    try:
        webbrowser.open(report_path.resolve().as_uri(), new=2)
    except Exception:
        try:
            webbrowser.open(str(report_path.resolve()), new=2)
        except Exception:
            pass

    print("OK. Wyniki zapisane w:", str(outdir))


if __name__ == "__main__":
    main()

















































































































































































































