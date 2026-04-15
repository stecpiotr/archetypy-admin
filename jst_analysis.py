from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import os
from io import BytesIO
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Set, Tuple
import zipfile

import pandas as pd


_SEGMENT_HIT_THRESHOLD_DEFAULTS: Dict[str, float] = {
    "2 z 2 · #1": 3.94,
    "4 z 4 · #1": 3.0,
    "3 z 4 · #2": 2.1,
    "1 z 4 · #4": 2.1,
    "1 z 4 · #3": 2.1,
}


def _normalize_segment_threshold_overrides(raw: Any) -> Dict[str, float]:
    out: Dict[str, float] = {}
    if not isinstance(raw, dict):
        return out
    for k, v in raw.items():
        key = str(k or "").strip()
        if not key:
            continue
        try:
            val = float(str(v).replace(",", ".").strip())
        except Exception:
            continue
        out[key] = val
    return out


def _slugify_ascii(text: str) -> str:
    src = (text or "").strip().lower()
    repl = (
        ("ą", "a"),
        ("ć", "c"),
        ("ę", "e"),
        ("ł", "l"),
        ("ń", "n"),
        ("ó", "o"),
        ("ś", "s"),
        ("ż", "z"),
        ("ź", "z"),
    )
    for a, b in repl:
        src = src.replace(a, b)
    src = re.sub(r"[^a-z0-9]+", "-", src).strip("-")
    return src or "jst"


def _city_title_from_study(study: Dict[str, Any]) -> Tuple[str, str]:
    jst_type = str(study.get("jst_type") or "miasto").strip().lower()
    name = str(study.get("jst_name_nom") or study.get("jst_name") or "").strip()
    city = name or "Poznań"
    city_label = str(study.get("jst_full_nom") or f"{jst_type.title()} {city}".strip())
    return city, city_label


def _write_settings(path: Path, study: Dict[str, Any]) -> None:
    city, city_label = _city_title_from_study(study)
    pop_raw = str(study.get("population_15_plus") or "").strip().replace(",", ".")
    try:
        pop_15_plus = max(0, int(float(pop_raw))) if pop_raw else 0
    except Exception:
        pop_15_plus = 0
    segment_overrides = _normalize_segment_threshold_overrides(study.get("segment_hit_threshold_overrides"))
    if not segment_overrides:
        segment_overrides = dict(_SEGMENT_HIT_THRESHOLD_DEFAULTS)
    settings = {
        "city": city,
        "city_label": city_label,
        "population_15_plus": int(pop_15_plus),
        "bootstrap_reps": 700,
        "w_A": 1.0,
        "weight_column": "",
        "segments_k_min": 3,
        "segments_k_max": 9,
        "segments_k_default": 5,
        "clusters_k_min": 3,
        "clusters_k_max": 9,
        "clusters_k_default": 5,
        "require_metry": True,
        "random_seed": 2026,
        "segment_hit_threshold_overrides": segment_overrides,
        "metryczka_config": study.get("metryczka_config") or {},
        "segment_outline_style": "classic",
        "silhouette_sample_max": 1800,
    }
    path.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")


def _prepare_tool_run_dir(template_root: Path, run_root: Path) -> None:
    def _sync_report_fonts() -> None:
        repo_root = template_root.parent
        src_fonts_dir = repo_root / "assets" / "fonts"
        if not src_fonts_dir.exists() or not src_fonts_dir.is_dir():
            return
        dst_fonts_dir = run_root / "assets" / "fonts"
        dst_fonts_dir.mkdir(parents=True, exist_ok=True)
        preferred = [
            "segoeui.ttf",
            "segoeuib.ttf",
            "ArialNova.ttf",
            "ArialNova-Bold.ttf",
            "DejaVuSans.ttf",
            "DejaVuSans-Bold.ttf",
        ]
        for fname in preferred:
            src = src_fonts_dir / fname
            if src.exists() and src.is_file():
                try:
                    shutil.copy2(src, dst_fonts_dir / fname)
                except Exception:
                    continue

    if run_root.exists() and (run_root / "analyze_poznan_archetypes.py").exists():
        # Synchronizujemy silnik raportu także dla istniejących runów,
        # aby poprawki generatora działały bez ręcznego czyszczenia katalogu _runs.
        src_engine = template_root / "analyze_poznan_archetypes.py"
        dst_engine = run_root / "analyze_poznan_archetypes.py"
        if src_engine.exists():
            dst_engine.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_engine, dst_engine)
        for rel in ("requirements.txt", "README_PL.txt"):
            src = template_root / rel
            dst = run_root / rel
            if src.exists() and not dst.exists():
                shutil.copy2(src, dst)
        _sync_report_fonts()
        return

    ignore = shutil.ignore_patterns(
        ".venv",
        ".idea",
        "__pycache__",
        "*.pyc",
        "_runs",
        "_runs*",
        "tmp",
        "WYNIKI",
    )
    shutil.copytree(template_root, run_root, dirs_exist_ok=True, ignore=ignore)
    _sync_report_fonts()


def _python_exec(run_root: Path) -> str:
    venv_python = run_root / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def _norm_text(v: Any) -> str:
    txt = str(v or "").strip().lower()
    repl = (
        ("ą", "a"),
        ("ć", "c"),
        ("ę", "e"),
        ("ł", "l"),
        ("ń", "n"),
        ("ó", "o"),
        ("ś", "s"),
        ("ż", "z"),
        ("ź", "z"),
    )
    for a, b in repl:
        txt = txt.replace(a, b)
    return re.sub(r"\s+", " ", txt)


def _to_gender_code(v: Any) -> int:
    n = _norm_text(v)
    if n in {"1", "kobieta", "k"}:
        return 1
    if n in {"2", "mezczyzna", "m"}:
        return 2
    return 0


def _to_age_code(v: Any) -> int:
    n = _norm_text(v).replace(" ", "")
    if n in {"1", "15-39", "15_39", "15–39"}:
        return 1
    if n in {"2", "40-59", "40_59", "40–59"}:
        return 2
    if n in {"3", "60iwiecej", "60+wiecej", "60+", "60iwiecejlat", "60iwiecej"}:
        return 3
    return 0


def _present_cells_from_data(data_df: pd.DataFrame) -> Set[Tuple[int, int]]:
    present: Set[Tuple[int, int]] = set()
    if "M_PLEC" not in data_df.columns or "M_WIEK" not in data_df.columns:
        return present
    for _, row in data_df[["M_PLEC", "M_WIEK"]].iterrows():
        g = _to_gender_code(row.get("M_PLEC"))
        a = _to_age_code(row.get("M_WIEK"))
        if g > 0 and a > 0:
            present.add((g, a))
    return present


def _normalize_targets_rows(raw_rows: List[Tuple[int, int, float]], present: Set[Tuple[int, int]]) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for g, a, share in raw_rows:
        if g not in {1, 2} or a not in {1, 2, 3}:
            continue
        if present and (g, a) not in present:
            continue
        s = float(share or 0.0)
        if s <= 0:
            continue
        rows.append({"plec": int(g), "wiek": int(a), "udzial_docelowy": s})

    if not rows:
        return pd.DataFrame(columns=["plec", "wiek", "udzial_docelowy"])

    df = pd.DataFrame(rows).groupby(["plec", "wiek"], as_index=False)["udzial_docelowy"].sum()
    if df["udzial_docelowy"].max() > 1.0:
        df["udzial_docelowy"] = df["udzial_docelowy"] / 100.0
    total = float(df["udzial_docelowy"].sum())
    if total <= 0:
        return pd.DataFrame(columns=["plec", "wiek", "udzial_docelowy"])
    df["udzial_docelowy"] = df["udzial_docelowy"] / total
    return df


def _targets_from_study(study: Dict[str, Any], present: Set[Tuple[int, int]]) -> pd.DataFrame:
    raw = study.get("poststrat_targets")
    if not raw:
        return pd.DataFrame(columns=["plec", "wiek", "udzial_docelowy"])

    def _to_float(value: Any) -> float:
        txt = str(value or "").strip().replace(",", ".")
        try:
            return float(txt)
        except Exception:
            return 0.0

    def _parse_key_pair(key: Any) -> Tuple[int, int]:
        raw_key = str(key or "").strip()
        if not raw_key:
            return 0, 0
        m = re.match(r"^\s*([12])\s*[_:x|;/\-]\s*([123])\s*$", raw_key)
        if m:
            return int(m.group(1)), int(m.group(2))

        nk = _norm_text(raw_key)
        nk_sep = re.sub(r"[^a-z0-9]+", " ", nk).strip()
        g = 0
        a = 0
        if "kobieta" in nk_sep or nk_sep in {"k", "female"}:
            g = 1
        elif "mezczyzna" in nk_sep or nk_sep in {"m", "male"}:
            g = 2
        else:
            m_num = re.match(r"^\s*([12])\s+", nk_sep)
            if m_num:
                g = int(m_num.group(1))

        if re.search(r"\b15\b.*\b39\b", nk_sep):
            a = 1
        elif re.search(r"\b40\b.*\b59\b", nk_sep):
            a = 2
        elif re.search(r"\b60\b", nk_sep):
            a = 3
        else:
            m_num = re.search(r"\b([123])\b", nk_sep)
            if m_num:
                a = int(m_num.group(1))

        return g, a

    rows: List[Tuple[int, int, float]] = []
    if isinstance(raw, dict):
        for k, v in raw.items():
            if isinstance(v, dict):
                g = _to_gender_code(v.get("plec") or v.get("gender") or v.get("M_PLEC"))
                a = _to_age_code(v.get("wiek") or v.get("age") or v.get("M_WIEK"))
                s = _to_float(v.get("udzial_docelowy") or v.get("udzial") or v.get("share"))
                rows.append((g, a, s))
                continue
            g, a = _parse_key_pair(k)
            s = _to_float(v)
            rows.append((g, a, s))
    elif isinstance(raw, list):
        for item in raw:
            if not isinstance(item, dict):
                continue
            g = _to_gender_code(item.get("plec") or item.get("gender") or item.get("M_PLEC"))
            a = _to_age_code(item.get("wiek") or item.get("age") or item.get("M_WIEK"))
            s = _to_float(item.get("udzial_docelowy") or item.get("udzial") or item.get("share"))
            rows.append((g, a, s))
    # Dla ręcznie zadanych targetów NIE wycinamy brakujących komórek.
    # Dzięki temu narzędzie analityczne może precyzyjnie zastosować macierz
    # lub zwrócić czytelny błąd, zamiast "cicho" renormalizować proporcje.
    return _normalize_targets_rows(rows, present=set())


def _targets_from_template(run_root: Path, present: Set[Tuple[int, int]]) -> pd.DataFrame:
    path = run_root / "targets_poststrat.csv"
    if not path.exists():
        return pd.DataFrame(columns=["plec", "wiek", "udzial_docelowy"])
    try:
        src = pd.read_csv(path, encoding="utf-8-sig", sep=None, engine="python")
    except Exception:
        return pd.DataFrame(columns=["plec", "wiek", "udzial_docelowy"])

    src.columns = [str(c).replace("\ufeff", "").strip() for c in src.columns]
    c_gender = None
    c_age = None
    c_share = None
    for c in src.columns:
        n = _norm_text(c)
        if n in {"plec", "plec_", "płec", "gender", "m_plec"}:
            c_gender = c
        elif n in {"wiek", "age", "m_wiek"}:
            c_age = c
        elif n in {"udzial_docelowy", "udzial_docelowy", "udzial", "share", "target_share", "pct", "procent"}:
            c_share = c
    if not c_gender or not c_age or not c_share:
        return pd.DataFrame(columns=["plec", "wiek", "udzial_docelowy"])

    rows: List[Tuple[int, int, float]] = []
    for _, r in src.iterrows():
        g = _to_gender_code(r.get(c_gender))
        a = _to_age_code(r.get(c_age))
        try:
            s = float(r.get(c_share) or 0.0)
        except Exception:
            s = 0.0
        rows.append((g, a, s))
    # Dla pliku targetów z szablonu zachowujemy pełną macierz komórek.
    return _normalize_targets_rows(rows, present=set())


def _targets_from_sample(data_df: pd.DataFrame, present: Set[Tuple[int, int]]) -> pd.DataFrame:
    rows: List[Tuple[int, int, float]] = []
    if "M_PLEC" not in data_df.columns or "M_WIEK" not in data_df.columns:
        return pd.DataFrame(columns=["plec", "wiek", "udzial_docelowy"])

    counter: Dict[Tuple[int, int], int] = {}
    for _, row in data_df[["M_PLEC", "M_WIEK"]].iterrows():
        g = _to_gender_code(row.get("M_PLEC"))
        a = _to_age_code(row.get("M_WIEK"))
        if g > 0 and a > 0 and (not present or (g, a) in present):
            key = (g, a)
            counter[key] = int(counter.get(key, 0)) + 1
    for (g, a), n in counter.items():
        rows.append((g, a, float(n)))
    return _normalize_targets_rows(rows, present)


def _write_poststrat_targets(run_root: Path, study: Dict[str, Any], data_df: pd.DataFrame) -> None:
    present = _present_cells_from_data(data_df)
    if not present:
        return

    targets = _targets_from_study(study, present)
    if targets.empty:
        targets = _targets_from_template(run_root, present)
    if targets.empty:
        targets = _targets_from_sample(data_df, present)
    if targets.empty:
        return

    (run_root / "targets_poststrat.csv").write_text(
        targets.to_csv(index=False, encoding="utf-8"),
        encoding="utf-8",
    )


def _file_sha256(path: Path) -> str:
    try:
        blob = path.read_bytes()
        return hashlib.sha256(blob).hexdigest()
    except Exception:
        return ""


def _hash_payload(df: pd.DataFrame, study: Dict[str, Any], template_root: Path) -> str:
    poststrat = study.get("poststrat_targets")
    poststrat_serialized = json.dumps(poststrat, ensure_ascii=False, sort_keys=True, default=str)
    metryczka_serialized = json.dumps(study.get("metryczka_config") or {}, ensure_ascii=False, sort_keys=True, default=str)
    population_15_plus = study.get("population_15_plus")
    segment_overrides = _normalize_segment_threshold_overrides(study.get("segment_hit_threshold_overrides"))
    overrides_serialized = json.dumps(segment_overrides, ensure_ascii=False, sort_keys=True, default=str)
    engine_sha = _file_sha256(template_root / "analyze_poznan_archetypes.py")
    jst_analysis_schema = "jst_analysis_hash_v6"
    raw = (
        f"{jst_analysis_schema}|{study.get('id')}|{study.get('slug')}|{study.get('jst_full_nom')}|{study.get('jst_type')}|"
        f"{poststrat_serialized}|{metryczka_serialized}|{population_15_plus}|{overrides_serialized}|{engine_sha}\n"
        + df.to_csv(index=False)
    )
    return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()


def generate_jst_report(
    template_root: Path,
    run_base_dir: Path,
    study: Dict[str, Any],
    data_df: pd.DataFrame,
    force: bool = False,
) -> Path:
    if data_df.empty:
        raise ValueError("Brak odpowiedzi do analizy.")

    study_id = str(study.get("id") or _slugify_ascii(str(study.get("slug") or "study")))
    run_base_dir.mkdir(parents=True, exist_ok=True)
    run_root = run_base_dir / study_id
    _prepare_tool_run_dir(template_root, run_root)

    payload_hash = _hash_payload(data_df, study, template_root)
    hash_file = run_root / ".source_hash.txt"
    out_report = run_root / "WYNIKI" / "raport.html"

    needs_run = force or (not out_report.exists()) or (not hash_file.exists()) or (hash_file.read_text(encoding="utf-8").strip() != payload_hash)
    if needs_run:
        data_df.to_csv(run_root / "data.csv", index=False, encoding="utf-8-sig")
        _write_settings(run_root / "settings.json", study)
        _write_poststrat_targets(run_root, study, data_df)

        py_exec = _python_exec(run_root)
        cmd = [py_exec, str(run_root / "analyze_poznan_archetypes.py")]
        proc = subprocess.run(
            cmd,
            cwd=str(run_root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            timeout=1800,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                "Błąd generatora raportu JST.\n"
                f"stdout:\n{proc.stdout[-5000:]}\n\nstderr:\n{proc.stderr[-5000:]}"
            )
        hash_file.write_text(payload_hash, encoding="utf-8")

    if not out_report.exists():
        raise FileNotFoundError(f"Nie znaleziono raportu: {out_report}")
    return out_report


_ASSET_EXT = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".svg",
    ".ico",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
    ".eot",
}
_SRC_HREF_RE = re.compile(
    r'(?P<attr>src|href)=(?P<q>["\'])(?P<path>[^"\']+)(?P=q)',
    re.IGNORECASE,
)
_LINK_STYLESHEET_RE = re.compile(
    r'<link(?P<attrs>[^>]*?)href=["\'](?P<href>[^"\']+)["\'](?P<tail>[^>]*)>',
    re.IGNORECASE,
)
_SCRIPT_SRC_RE = re.compile(
    r'<script(?P<attrs>[^>]*?)src=["\'](?P<src>[^"\']+)["\'](?P<tail>[^>]*)>\s*</script>',
    re.IGNORECASE | re.DOTALL,
)
_CSS_URL_RE = re.compile(r"url\((?P<q>['\"]?)(?P<path>[^)\"']+)(?P=q)\)", re.IGNORECASE)
_QUOTED_LOCAL_ASSET_RE = re.compile(
    r'(?P<q>["\'])(?P<path>[^"\']+\.(?:png|jpe?g|gif|webp|svg|ico|woff2?|ttf|otf|eot))(?P=q)',
    re.IGNORECASE,
)


def _is_external_ref(ref: str) -> bool:
    low = (ref or "").strip().lower()
    return (
        not low
        or low.startswith(("http://", "https://", "data:", "javascript:", "#", "mailto:"))
        or "://" in low
    )


def _resolve_local_ref(ref: str, root: Path, base_dir: Optional[Path] = None) -> Optional[Path]:
    ref_clean = (ref or "").strip()
    if _is_external_ref(ref_clean):
        return None
    ref_clean = ref_clean.split("#", 1)[0].split("?", 1)[0].strip()
    if not ref_clean:
        return None
    candidate_base = (base_dir or root)
    candidate = (candidate_base / ref_clean).resolve()
    if not str(candidate).startswith(str(root)):
        return None
    if not candidate.exists() or not candidate.is_file():
        return None
    return candidate


def _to_data_uri(path: Path) -> Optional[str]:
    mime, _ = mimetypes.guess_type(path.name)
    if not mime:
        mime = "application/octet-stream"
    try:
        blob = path.read_bytes()
        if mime in {"image/png", "image/jpeg", "image/webp"} and len(blob) >= 120_000:
            try:
                from PIL import Image
            except Exception:
                Image = None
            if Image is not None:
                try:
                    with Image.open(BytesIO(blob)) as im:
                        has_alpha = "A" in (im.getbands() or ())
                        resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS", Image.LANCZOS)
                        max_edge = max(im.size or (0, 0))
                        if max_edge > 1900:
                            scale = 1900.0 / float(max_edge)
                            new_w = max(1, int(im.size[0] * scale))
                            new_h = max(1, int(im.size[1] * scale))
                            im = im.resize((new_w, new_h), resample=resample)

                        candidates: List[Tuple[str, bytes]] = []

                        def _encode_candidate(fmt: str, out_mime: str, **kwargs: Any) -> None:
                            try:
                                im_out = im
                                if fmt == "JPEG" and im_out.mode not in {"RGB", "L"}:
                                    im_out = im_out.convert("RGB")
                                buf = BytesIO()
                                if fmt == "JPEG":
                                    im_out.save(buf, format=fmt, optimize=True, progressive=True, **kwargs)
                                else:
                                    im_out.save(buf, format=fmt, **kwargs)
                                candidates.append((out_mime, buf.getvalue()))
                            except Exception:
                                return

                        if mime == "image/png":
                            _encode_candidate("WEBP", "image/webp", quality=78, method=6)
                            _encode_candidate("WEBP", "image/webp", quality=70, method=6)
                            if not has_alpha:
                                _encode_candidate("JPEG", "image/jpeg", quality=76)
                        elif mime == "image/webp":
                            _encode_candidate("WEBP", "image/webp", quality=76, method=6)
                            if not has_alpha:
                                _encode_candidate("JPEG", "image/jpeg", quality=76)
                                _encode_candidate("JPEG", "image/jpeg", quality=70)
                        else:  # image/jpeg
                            _encode_candidate("JPEG", "image/jpeg", quality=78)
                            _encode_candidate("JPEG", "image/jpeg", quality=70)
                            _encode_candidate("WEBP", "image/webp", quality=74, method=6)

                        if candidates:
                            best_mime, best_blob = min(candidates, key=lambda x: len(x[1]))
                            if len(best_blob) + 24_000 < len(blob):
                                blob = best_blob
                                mime = best_mime
                except Exception:
                    pass
        b64 = base64.b64encode(blob).decode("ascii")
        return f"data:{mime};base64,{b64}"
    except Exception:
        return None


def _inline_css_urls(css_text: str, css_file: Path, root: Path) -> str:
    def _replace_url(match: re.Match) -> str:
        ref = (match.group("path") or "").strip()
        if _is_external_ref(ref):
            return match.group(0)
        asset = _resolve_local_ref(ref, root=root, base_dir=css_file.parent)
        if asset is None:
            return match.group(0)
        data_uri = _to_data_uri(asset)
        if not data_uri:
            return match.group(0)
        return f"url('{data_uri}')"

    return _CSS_URL_RE.sub(_replace_url, css_text or "")


def inline_local_assets(html_text: str, base_dir: Path) -> str:
    root = base_dir.resolve()

    def _replace_stylesheet(match: re.Match) -> str:
        attrs = f"{match.group('attrs') or ''} {match.group('tail') or ''}".lower()
        href = match.group("href") or ""
        if "stylesheet" not in attrs:
            return match.group(0)
        css_path = _resolve_local_ref(href, root=root, base_dir=root)
        if css_path is None or css_path.suffix.lower() != ".css":
            return match.group(0)
        try:
            css_text = css_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return match.group(0)
        css_text = _inline_css_urls(css_text, css_path, root=root)
        return f"<style>\n{css_text}\n</style>"

    def _replace_script(match: re.Match) -> str:
        attrs = (match.group("attrs") or "") + (match.group("tail") or "")
        src = match.group("src") or ""
        js_path = _resolve_local_ref(src, root=root, base_dir=root)
        if js_path is None or js_path.suffix.lower() != ".js":
            return match.group(0)
        try:
            js_text = js_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return match.group(0)
        return f"<script{attrs}>\n{js_text}\n</script>"

    html_text = _LINK_STYLESHEET_RE.sub(_replace_stylesheet, html_text or "")
    html_text = _SCRIPT_SRC_RE.sub(_replace_script, html_text or "")

    def _replace(match: re.Match) -> str:
        attr = match.group("attr")
        quote = match.group("q") or '"'
        ref = match.group("path")
        ref_clean = (ref or "").strip()
        if _is_external_ref(ref_clean):
            return match.group(0)

        candidate = _resolve_local_ref(ref_clean, root=root, base_dir=root)
        if candidate is None:
            return match.group(0)

        ext = candidate.suffix.lower()
        if ext not in _ASSET_EXT:
            return match.group(0)

        data_uri = _to_data_uri(candidate)
        if not data_uri:
            return match.group(0)
        return f"{attr}={quote}{data_uri}{quote}"

    html_text = _SRC_HREF_RE.sub(_replace, html_text or "")

    def _replace_quoted_local_asset(match: re.Match) -> str:
        quote = match.group("q") or '"'
        ref = (match.group("path") or "").strip()
        if _is_external_ref(ref):
            return match.group(0)
        candidate = _resolve_local_ref(ref, root=root, base_dir=root)
        if candidate is None:
            return match.group(0)
        if candidate.suffix.lower() not in _ASSET_EXT:
            return match.group(0)
        data_uri = _to_data_uri(candidate)
        if not data_uri:
            return match.group(0)
        return f"{quote}{data_uri}{quote}"

    # W standalone część zasobów jest podmieniana dynamicznie przez JS (np. mapy po suwakach).
    # Te ścieżki nie występują w atrybutach src/href, więc inlinujemy także lokalne stringi
    # wyglądające jak referencje do plików graficznych/fontów.
    html_text = _QUOTED_LOCAL_ASSET_RE.sub(_replace_quoted_local_asset, html_text)
    return html_text


def bundle_report_dir_zip(report_dir: Path) -> bytes:
    root = Path(report_dir or "").resolve()
    if not root.exists() or not root.is_dir():
        return b""

    buf = BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for p in sorted(root.rglob("*")):
            if not p.is_file():
                continue
            arcname = (Path(root.name) / p.relative_to(root)).as_posix()
            zf.write(p, arcname=arcname)
    return buf.getvalue()
