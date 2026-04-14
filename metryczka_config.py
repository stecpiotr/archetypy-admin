from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Iterable, List, Tuple
import re


CORE_QUESTION_ORDER: Tuple[str, ...] = (
    "M_PLEC",
    "M_WIEK",
    "M_WYKSZT",
    "M_ZAWOD",
    "M_MATERIAL",
)

_SAFE_ID_RE = re.compile(r"^M_[A-Z0-9_]{2,40}$")


def _core_question_defaults() -> Dict[str, Dict[str, Any]]:
    return {
        "M_PLEC": {
            "id": "M_PLEC",
            "scope": "core",
            "db_column": "M_PLEC",
            "prompt": "Proszę o podanie płci.",
            "required": True,
            "multiple": False,
            "aliases": ["M_PLEC", "Płeć", "Plec"],
            "options": [
                {"label": "kobieta", "code": "1"},
                {"label": "mężczyzna", "code": "2"},
            ],
        },
        "M_WIEK": {
            "id": "M_WIEK",
            "scope": "core",
            "db_column": "M_WIEK",
            "prompt": "Jaki jest Pana/Pani wiek?",
            "required": True,
            "multiple": False,
            "aliases": ["M_WIEK", "Wiek"],
            "options": [
                {"label": "15-39", "code": "1"},
                {"label": "40-59", "code": "2"},
                {"label": "60 i więcej", "code": "3"},
            ],
        },
        "M_WYKSZT": {
            "id": "M_WYKSZT",
            "scope": "core",
            "db_column": "M_WYKSZT",
            "prompt": "Jakie ma Pan/Pani wykształcenie?",
            "required": True,
            "multiple": False,
            "aliases": ["M_WYKSZT", "Wykształcenie", "Wyksztalcenie"],
            "options": [
                {"label": "podstawowe, gimnazjalne, zasadnicze zawodowe", "code": "1"},
                {"label": "średnie", "code": "2"},
                {"label": "wyższe", "code": "3"},
            ],
        },
        "M_ZAWOD": {
            "id": "M_ZAWOD",
            "scope": "core",
            "db_column": "M_ZAWOD",
            "prompt": "Jaka jest Pana/Pani sytuacja zawodowa?",
            "required": True,
            "multiple": False,
            "aliases": ["M_ZAWOD", "Status zawodowy", "Sytuacja zawodowa"],
            "options": [
                {"label": "pracownik umysłowy", "code": "1"},
                {"label": "pracownik fizyczny", "code": "2"},
                {"label": "prowadzę własną firmę", "code": "3"},
                {"label": "student/uczeń", "code": "4"},
                {"label": "bezrobotny", "code": "5"},
                {"label": "rencista/emeryt", "code": "6"},
                {"label": "inna (jaka?)", "code": "7"},
            ],
        },
        "M_MATERIAL": {
            "id": "M_MATERIAL",
            "scope": "core",
            "db_column": "M_MATERIAL",
            "prompt": "Jak ocenia Pan/Pani własną sytuację materialną?",
            "required": True,
            "multiple": False,
            "aliases": ["M_MATERIAL", "Sytuacja materialna"],
            "options": [
                {"label": "powodzi mi się bardzo źle, jestem w ciężkiej sytuacji materialnej", "code": "1"},
                {"label": "powodzi mi się raczej źle", "code": "2"},
                {"label": "powodzi mi się przeciętnie, średnio", "code": "3"},
                {"label": "powodzi mi się raczej dobrze", "code": "4"},
                {"label": "powodzi mi się bardzo dobrze", "code": "5"},
                {"label": "odmawiam udzielenia odpowiedzi", "code": "6"},
            ],
        },
    }


def default_jst_metryczka_config() -> Dict[str, Any]:
    defaults = _core_question_defaults()
    ordered = [deepcopy(defaults[qid]) for qid in CORE_QUESTION_ORDER]
    return {
        "version": 1,
        "questions": ordered,
    }


def _safe_text(value: Any, fallback: str = "") -> str:
    txt = str(value or "").strip()
    return txt if txt else fallback


def _safe_bool(value: Any, fallback: bool) -> bool:
    if isinstance(value, bool):
        return value
    txt = str(value or "").strip().lower()
    if txt in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if txt in {"0", "false", "f", "no", "n", "off"}:
        return False
    return bool(fallback)


def _normalize_options(raw_options: Any, *, fallback: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    if not isinstance(raw_options, list):
        raw_options = []
    out: List[Dict[str, str]] = []
    seen_codes: set[str] = set()
    for item in raw_options:
        if not isinstance(item, dict):
            continue
        label = _safe_text(item.get("label"))
        code = _safe_text(item.get("code"))
        if not label or not code or code in seen_codes:
            continue
        out.append({"label": label, "code": code})
        seen_codes.add(code)
    if out:
        return out
    return [{"label": _safe_text(o.get("label")), "code": _safe_text(o.get("code"))} for o in fallback]


def _normalize_aliases(raw_aliases: Any) -> List[str]:
    if not isinstance(raw_aliases, list):
        return []
    out: List[str] = []
    seen: set[str] = set()
    for item in raw_aliases:
        txt = _safe_text(item)
        key = txt.lower()
        if not txt or key in seen:
            continue
        seen.add(key)
        out.append(txt)
    return out


def _normalize_custom_question(raw: Dict[str, Any], used_columns: set[str]) -> Dict[str, Any]:
    qid = _safe_text(raw.get("id")).upper()
    db_column = _safe_text(raw.get("db_column")).upper()
    if not qid and db_column:
        qid = db_column
    if not db_column and qid:
        db_column = qid
    if not _SAFE_ID_RE.fullmatch(qid) or not _SAFE_ID_RE.fullmatch(db_column):
        return {}
    if qid in CORE_QUESTION_ORDER or db_column in CORE_QUESTION_ORDER:
        return {}
    if db_column in used_columns:
        return {}

    prompt = _safe_text(raw.get("prompt"))
    if not prompt:
        return {}

    fallback_options: List[Dict[str, Any]] = []
    options = _normalize_options(raw.get("options"), fallback=fallback_options)
    if not options:
        return {}

    used_columns.add(db_column)
    return {
        "id": qid,
        "scope": "custom",
        "db_column": db_column,
        "prompt": prompt,
        "required": _safe_bool(raw.get("required"), True),
        "multiple": _safe_bool(raw.get("multiple"), False),
        "aliases": _normalize_aliases(raw.get("aliases")),
        "options": options,
    }


def normalize_jst_metryczka_config(raw: Any) -> Dict[str, Any]:
    defaults = _core_question_defaults()
    if not isinstance(raw, dict):
        return default_jst_metryczka_config()

    try:
        version = max(1, int(raw.get("version") or 1))
    except Exception:
        version = 1

    raw_questions = raw.get("questions")
    by_id: Dict[str, Dict[str, Any]] = {}
    if isinstance(raw_questions, list):
        for item in raw_questions:
            if not isinstance(item, dict):
                continue
            qid = _safe_text(item.get("id")).upper()
            if qid:
                by_id[qid] = item

    normalized_questions: List[Dict[str, Any]] = []
    used_columns: set[str] = set()

    for qid in CORE_QUESTION_ORDER:
        base = deepcopy(defaults[qid])
        src = by_id.get(qid) or {}
        base["prompt"] = _safe_text(src.get("prompt"), base["prompt"])
        base["required"] = True
        base["multiple"] = False
        base["aliases"] = _normalize_aliases(src.get("aliases")) or base["aliases"]
        base["options"] = _normalize_options(src.get("options"), fallback=base["options"])
        normalized_questions.append(base)
        used_columns.add(base["db_column"])

    for item in raw_questions if isinstance(raw_questions, list) else []:
        if not isinstance(item, dict):
            continue
        norm_custom = _normalize_custom_question(item, used_columns)
        if norm_custom:
            normalized_questions.append(norm_custom)

    return {
        "version": version,
        "questions": normalized_questions,
    }


def metryczka_questions(config: Any) -> List[Dict[str, Any]]:
    cfg = normalize_jst_metryczka_config(config)
    return list(cfg.get("questions") or [])


def metryczka_custom_columns(config: Any) -> List[str]:
    cols: List[str] = []
    for q in metryczka_questions(config):
        if str(q.get("scope") or "").strip().lower() != "custom":
            continue
        col = _safe_text(q.get("db_column")).upper()
        if not col:
            continue
        cols.append(col)
    return cols


def metryczka_core_columns() -> Tuple[str, ...]:
    return CORE_QUESTION_ORDER
