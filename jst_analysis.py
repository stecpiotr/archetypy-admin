from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any, Dict, Tuple

import pandas as pd


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
    settings = {
        "city": city,
        "city_label": city_label,
        "population_15_plus": 0,
        "bootstrap_reps": 1200,
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
    }
    path.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")


def _prepare_tool_run_dir(template_root: Path, run_root: Path) -> None:
    if run_root.exists() and (run_root / "analyze_poznan_archetypes.py").exists():
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


def _python_exec(run_root: Path) -> str:
    venv_python = run_root / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def _hash_payload(df: pd.DataFrame, study: Dict[str, Any]) -> str:
    raw = (
        f"{study.get('id')}|{study.get('slug')}|{study.get('jst_full_nom')}|{study.get('jst_type')}\n"
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

    payload_hash = _hash_payload(data_df, study)
    hash_file = run_root / ".source_hash.txt"
    out_report = run_root / "WYNIKI" / "raport.html"

    needs_run = force or (not out_report.exists()) or (not hash_file.exists()) or (hash_file.read_text(encoding="utf-8").strip() != payload_hash)
    if needs_run:
        data_df.to_csv(run_root / "data.csv", index=False, encoding="utf-8-sig")
        _write_settings(run_root / "settings.json", study)

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


_ASSET_EXT = {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".ico"}
_SRC_HREF_RE = re.compile(r'(?P<attr>src|href)=["\'](?P<path>[^"\']+)["\']', re.IGNORECASE)


def inline_local_assets(html_text: str, base_dir: Path) -> str:
    root = base_dir.resolve()

    def _replace(match: re.Match) -> str:
        attr = match.group("attr")
        ref = match.group("path")
        ref_clean = (ref or "").strip()
        low = ref_clean.lower()
        if (
            not ref_clean
            or low.startswith(("http://", "https://", "data:", "javascript:", "#", "mailto:"))
            or "://" in ref_clean
        ):
            return match.group(0)

        candidate = (root / ref_clean).resolve()
        if not str(candidate).startswith(str(root)):
            return match.group(0)
        if not candidate.exists() or not candidate.is_file():
            return match.group(0)

        ext = candidate.suffix.lower()
        if ext not in _ASSET_EXT:
            return match.group(0)

        mime, _ = mimetypes.guess_type(candidate.name)
        if not mime:
            mime = "application/octet-stream"
        try:
            blob = candidate.read_bytes()
            b64 = base64.b64encode(blob).decode("ascii")
            return f'{attr}="data:{mime};base64,{b64}"'
        except Exception:
            return match.group(0)

    return _SRC_HREF_RE.sub(_replace, html_text or "")
