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
            "randomize_options": False,
            "randomize_exclude_last": False,
            "aliases": ["M_PLEC", "Płeć", "Plec"],
            "options": [
                {"label": "kobieta", "code": "kobieta", "is_open": False},
                {"label": "mężczyzna", "code": "mężczyzna", "is_open": False},
            ],
        },
        "M_WIEK": {
            "id": "M_WIEK",
            "scope": "core",
            "db_column": "M_WIEK",
            "prompt": "Jaki jest Pana/Pani wiek?",
            "required": True,
            "multiple": False,
            "randomize_options": False,
            "randomize_exclude_last": False,
            "aliases": ["M_WIEK", "Wiek"],
            "options": [
                {"label": "15-39", "code": "15-39", "is_open": False},
                {"label": "40-59", "code": "40-59", "is_open": False},
                {"label": "60 i więcej", "code": "60 i więcej", "is_open": False},
            ],
        },
        "M_WYKSZT": {
            "id": "M_WYKSZT",
            "scope": "core",
            "db_column": "M_WYKSZT",
            "prompt": "Jakie ma Pan/Pani wykształcenie?",
            "required": True,
            "multiple": False,
            "randomize_options": False,
            "randomize_exclude_last": False,
            "aliases": ["M_WYKSZT", "Wykształcenie", "Wyksztalcenie"],
            "options": [
                {
                    "label": "podstawowe, gimnazjalne, zasadnicze zawodowe",
                    "code": "podstawowe, gimnazjalne, zasadnicze zawodowe",
                    "is_open": False,
                },
                {"label": "średnie", "code": "średnie", "is_open": False},
                {"label": "wyższe", "code": "wyższe", "is_open": False},
            ],
        },
        "M_ZAWOD": {
            "id": "M_ZAWOD",
            "scope": "core",
            "db_column": "M_ZAWOD",
            "prompt": "Jaka jest Pana/Pani sytuacja zawodowa?",
            "required": True,
            "multiple": False,
            "randomize_options": False,
            "randomize_exclude_last": False,
            "aliases": ["M_ZAWOD", "Status zawodowy", "Sytuacja zawodowa"],
            "options": [
                {"label": "pracownik umysłowy", "code": "pracownik umysłowy", "is_open": False},
                {"label": "pracownik fizyczny", "code": "pracownik fizyczny", "is_open": False},
                {"label": "prowadzę własną firmę", "code": "prowadzę własną firmę", "is_open": False},
                {"label": "student/uczeń", "code": "student/uczeń", "is_open": False},
                {"label": "bezrobotny", "code": "bezrobotny", "is_open": False},
                {"label": "rencista/emeryt", "code": "rencista/emeryt", "is_open": False},
                {"label": "inna (jaka?)", "code": "inna (jaka?)", "is_open": True},
            ],
        },
        "M_MATERIAL": {
            "id": "M_MATERIAL",
            "scope": "core",
            "db_column": "M_MATERIAL",
            "prompt": "Jak ocenia Pan/Pani własną sytuację materialną?",
            "required": True,
            "multiple": False,
            "randomize_options": False,
            "randomize_exclude_last": False,
            "aliases": ["M_MATERIAL", "Sytuacja materialna"],
            "options": [
                {
                    "label": "powodzi mi się bardzo źle, jestem w ciężkiej sytuacji materialnej",
                    "code": "powodzi mi się bardzo źle, jestem w ciężkiej sytuacji materialnej",
                    "is_open": False,
                },
                {"label": "powodzi mi się raczej źle", "code": "powodzi mi się raczej źle", "is_open": False},
                {
                    "label": "powodzi mi się przeciętnie, średnio",
                    "code": "powodzi mi się przeciętnie, średnio",
                    "is_open": False,
                },
                {"label": "powodzi mi się raczej dobrze", "code": "powodzi mi się raczej dobrze", "is_open": False},
                {"label": "powodzi mi się bardzo dobrze", "code": "powodzi mi się bardzo dobrze", "is_open": False},
                {"label": "odmawiam udzielenia odpowiedzi", "code": "odmawiam udzielenia odpowiedzi", "is_open": False},
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


def default_personal_metryczka_config() -> Dict[str, Any]:
    return default_jst_metryczka_config()


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


def _looks_like_open_label(text: str) -> bool:
    t = str(text or "").strip().lower()
    return "inna (jaka?)" in t or "inne (jakie?)" in t


def _normalize_options(raw_options: Any, *, fallback: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(raw_options, list):
        raw_options = []
    out: List[Dict[str, Any]] = []
    seen_codes: set[str] = set()
    for item in raw_options:
        if not isinstance(item, dict):
            continue
        label = _safe_text(item.get("label"))
        code = _safe_text(item.get("code"))
        if not label or not code or code in seen_codes:
            continue
        is_open = _safe_bool(item.get("is_open"), _looks_like_open_label(label))
        out.append({"label": label, "code": code, "is_open": bool(is_open)})
        seen_codes.add(code)
    if out:
        return out
    fallback_out: List[Dict[str, Any]] = []
    for o in fallback:
        label = _safe_text(o.get("label"))
        code = _safe_text(o.get("code"))
        if not label or not code:
            continue
        fallback_out.append(
            {
                "label": label,
                "code": code,
                "is_open": _safe_bool(o.get("is_open"), _looks_like_open_label(label)),
            }
        )
    return fallback_out


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
        "randomize_options": _safe_bool(raw.get("randomize_options"), False),
        "randomize_exclude_last": _safe_bool(raw.get("randomize_exclude_last"), False),
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
        base["randomize_options"] = _safe_bool(src.get("randomize_options"), False)
        base["randomize_exclude_last"] = _safe_bool(src.get("randomize_exclude_last"), False)
        base["aliases"] = _normalize_aliases(src.get("aliases")) or base["aliases"]
        core_opts = _normalize_options(src.get("options"), fallback=base["options"])
        normalized_core_opts: List[Dict[str, Any]] = []
        seen_labels: set[str] = set()
        for opt in core_opts:
            label = _safe_text(opt.get("label"))
            key = label.lower()
            if not label or key in seen_labels:
                continue
            seen_labels.add(key)
            # Zgodność historyczna: dla 5 stałych pytań kodowanie odpowiedzi = tekst odpowiedzi.
            normalized_core_opts.append(
                {
                    "label": label,
                    "code": label,
                    "is_open": _safe_bool(opt.get("is_open"), _looks_like_open_label(label)),
                }
            )
        if not normalized_core_opts:
            normalized_core_opts = [
                {
                    "label": _safe_text(o.get("label")),
                    "code": _safe_text(o.get("label")),
                    "is_open": _safe_bool(o.get("is_open"), _looks_like_open_label(_safe_text(o.get("label")))),
                }
                for o in base["options"]
            ]
        base["options"] = normalized_core_opts
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


def normalize_personal_metryczka_config(raw: Any) -> Dict[str, Any]:
    return normalize_jst_metryczka_config(raw)


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
