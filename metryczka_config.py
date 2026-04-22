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


def _norm_icon_token(value: Any) -> str:
    txt = str(value or "").strip().lower()
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
    for src, dst in repl:
        txt = txt.replace(src, dst)
    return re.sub(r"\s+", " ", txt).strip()


def guess_metry_variable_emoji(db_column: Any, table_label: Any = "", prompt: Any = "") -> str:
    db_col = str(db_column or "").strip().upper()
    token = _norm_icon_token(f"{db_col} {table_label} {prompt}")
    if "M_PLEC" in db_col or "plec" in token:
        return "👫"
    if "M_WIEK" in db_col or "wiek" in token:
        return "⌛"
    if "M_WYKSZT" in db_col or "wykszt" in token:
        return "🎓"
    if "M_ZAWOD" in db_col or "zawod" in token:
        return "💼"
    if "M_MATERIAL" in db_col or "material" in token:
        return "💰"
    if any(k in token for k in ("obszar", "miejsce", "zamiesz", "lokaliz", "wies", "miasto")):
        return "📍"
    if any(k in token for k in ("preferencj", "komitet", "wybor", "glos", "parti", "sejm")):
        return "🗳️"
    if "orientac" in token:
        return "🧭"
    if any(k in token for k in ("poglad", "politycz", "ideolog")):
        return "⚖️"
    return "📌"


def guess_metry_value_emoji(variable_label: Any, code: Any, db_column: Any = "") -> str:
    var_token = _norm_icon_token(f"{db_column} {variable_label}")
    code_token = _norm_icon_token(code)
    code_sp = code_token.replace("-", " ")
    if not code_token:
        return ""
    if "M_PLEC" in str(db_column or "").upper() or "plec" in var_token:
        if "kobiet" in code_token:
            return "👩"
        if "mezczyzn" in code_token:
            return "👨"
    if "M_WIEK" in str(db_column or "").upper() or "wiek" in var_token:
        if re.search(r"\b60\b", code_token):
            return "🧓"
        if re.search(r"40\D*59", code_token):
            return "🧑‍💼"
        if re.search(r"15\D*39", code_token):
            return "🧑"
    if "M_WYKSZT" in str(db_column or "").upper() or "wykszt" in var_token:
        if "wyzsze" in code_token:
            return "🎓"
        if "srednie" in code_token:
            return "📘"
        if any(k in code_token for k in ("podstaw", "gimnaz", "zawod")):
            return "🛠️"
    if "M_ZAWOD" in str(db_column or "").upper() or "zawod" in var_token:
        if "umysl" in code_token:
            return "🧠"
        if "fizycz" in code_token:
            return "🛠️"
        if "wlasn" in code_token and "firm" in code_token:
            return "🏢"
        if "student" in code_token or "uczen" in code_token:
            return "🧑‍🎓"
        if "bezrobot" in code_token:
            return "🔎"
        if "renc" in code_token or "emery" in code_token:
            return "🌿"
        if "inna" in code_token:
            return "🧩"
    if "M_MATERIAL" in str(db_column or "").upper() or "material" in var_token:
        if "odmaw" in code_token:
            return "🤐"
        if "bardzo dobra" in code_token or "bardzo dobrze" in code_token:
            return "😄"
        if "raczej dobra" in code_token or "raczej dobrze" in code_token:
            return "🙂"
        if "przeciet" in code_token or "srednio" in code_token:
            return "😐"
        if "raczej zla" in code_token or "raczej zle" in code_token:
            return "🙁"
        if "bardzo zla" in code_token or "bardzo zle" in code_token:
            return "😟"
    if any(k in var_token for k in ("obszar", "miejsce", "zamiesz", "lokaliz", "wies", "miasto")):
        if "miasto" in code_token:
            return "🏬"
        if "wies" in code_token:
            return "🌾"
        return "📍"
    if any(k in var_token for k in ("orientac", "poglad", "politycz", "ideolog")):
        if "centro prawic" in code_sp:
            return "↗️"
        if "prawic" in code_token:
            return "➡️"
        if "centro lewic" in code_sp:
            return "↖️"
        if "lewic" in code_token:
            return "⬅️"
        if "centr" in code_token:
            return "↔️"
        if "odmow" in code_token:
            return "🤐"
        if "trudno" in code_token:
            return "🤷"
        if "niewaz" in code_token:
            return "⭕"
        if "nie wiem" in code_token:
            return "❓"
        return "🧭"
    if any(k in var_token for k in ("preferencj", "komitet", "wybor", "glos", "parti", "sejm")):
        if "odmow" in code_token:
            return "🤐"
        if "trudno" in code_token:
            return "🤷"
        if "niewaz" in code_token:
            return "⭕"
        if "nie wiem" in code_token or "niezdecyd" in code_token:
            return "❓"
        return "🗳️"
    return ""


def _core_question_defaults() -> Dict[str, Dict[str, Any]]:
    return {
        "M_PLEC": {
            "id": "M_PLEC",
            "scope": "core",
            "db_column": "M_PLEC",
            "prompt": "Proszę o podanie płci.",
            "table_label": "Płeć",
            "variable_emoji": "👫",
            "required": True,
            "multiple": False,
            "randomize_options": False,
            "randomize_exclude_last": False,
            "aliases": ["M_PLEC", "Płeć", "Plec"],
            "options": [
                {"label": "kobieta", "code": "kobieta", "is_open": False, "value_emoji": "👩"},
                {"label": "mężczyzna", "code": "mężczyzna", "is_open": False, "value_emoji": "👨"},
            ],
        },
        "M_WIEK": {
            "id": "M_WIEK",
            "scope": "core",
            "db_column": "M_WIEK",
            "prompt": "Jaki jest Pana/Pani wiek?",
            "table_label": "Wiek",
            "variable_emoji": "⌛",
            "required": True,
            "multiple": False,
            "randomize_options": False,
            "randomize_exclude_last": False,
            "aliases": ["M_WIEK", "Wiek"],
            "options": [
                {"label": "15-39", "code": "15-39", "is_open": False, "value_emoji": "🧑"},
                {"label": "40-59", "code": "40-59", "is_open": False, "value_emoji": "🧑‍💼"},
                {"label": "60 i więcej", "code": "60+", "is_open": False, "value_emoji": "🧓"},
            ],
        },
        "M_WYKSZT": {
            "id": "M_WYKSZT",
            "scope": "core",
            "db_column": "M_WYKSZT",
            "prompt": "Jakie ma Pan/Pani wykształcenie?",
            "table_label": "Wykształcenie",
            "variable_emoji": "🎓",
            "required": True,
            "multiple": False,
            "randomize_options": False,
            "randomize_exclude_last": False,
            "aliases": ["M_WYKSZT", "Wykształcenie", "Wyksztalcenie"],
            "options": [
                {
                    "label": "podstawowe, gimnazjalne, zasadnicze zawodowe",
                    "code": "podst./gim./zaw.",
                    "is_open": False,
                    "value_emoji": "🛠️",
                },
                {"label": "średnie", "code": "średnie", "is_open": False, "value_emoji": "📘"},
                {"label": "wyższe", "code": "wyższe", "is_open": False, "value_emoji": "🎓"},
            ],
        },
        "M_ZAWOD": {
            "id": "M_ZAWOD",
            "scope": "core",
            "db_column": "M_ZAWOD",
            "prompt": "Jaka jest Pana/Pani sytuacja zawodowa?",
            "table_label": "Status zawodowy",
            "variable_emoji": "💼",
            "required": True,
            "multiple": False,
            "randomize_options": False,
            "randomize_exclude_last": False,
            "aliases": ["M_ZAWOD", "Status zawodowy", "Sytuacja zawodowa"],
            "options": [
                {"label": "pracownik umysłowy", "code": "pracownik umysłowy", "is_open": False, "value_emoji": "🧠"},
                {"label": "pracownik fizyczny", "code": "pracownik fizyczny", "is_open": False, "value_emoji": "🛠️"},
                {"label": "prowadzę własną firmę", "code": "własna firma", "is_open": False, "value_emoji": "🏢"},
                {"label": "student/uczeń", "code": "student/uczeń", "is_open": False, "value_emoji": "🧑‍🎓"},
                {"label": "bezrobotny", "code": "bezrobotny", "is_open": False, "value_emoji": "🔎"},
                {"label": "rencista/emeryt", "code": "rencista/emeryt", "is_open": False, "value_emoji": "🌿"},
                {"label": "inna (jaka?)", "code": "inna", "is_open": True, "value_emoji": "🧩"},
            ],
        },
        "M_MATERIAL": {
            "id": "M_MATERIAL",
            "scope": "core",
            "db_column": "M_MATERIAL",
            "prompt": "Jak ocenia Pan/Pani własną sytuację materialną?",
            "table_label": "Sytuacja materialna",
            "variable_emoji": "💰",
            "required": True,
            "multiple": False,
            "randomize_options": False,
            "randomize_exclude_last": False,
            "aliases": ["M_MATERIAL", "Sytuacja materialna"],
            "options": [
                {
                    "label": "powodzi mi się bardzo źle, jestem w ciężkiej sytuacji materialnej",
                    "code": "bardzo zła",
                    "is_open": False,
                    "value_emoji": "😟",
                },
                {"label": "powodzi mi się raczej źle", "code": "raczej zła", "is_open": False, "value_emoji": "🙁"},
                {
                    "label": "powodzi mi się przeciętnie, średnio",
                    "code": "przeciętna",
                    "is_open": False,
                    "value_emoji": "😐",
                },
                {"label": "powodzi mi się raczej dobrze", "code": "raczej dobra", "is_open": False, "value_emoji": "🙂"},
                {"label": "powodzi mi się bardzo dobrze", "code": "bardzo dobra", "is_open": False, "value_emoji": "😄"},
                {"label": "odmawiam udzielenia odpowiedzi", "code": "odmowa", "is_open": False, "value_emoji": "🤐"},
            ],
        },
    }


def default_jst_metryczka_config() -> Dict[str, Any]:
    defaults = _core_question_defaults()
    ordered = [deepcopy(defaults[qid]) for qid in CORE_QUESTION_ORDER]
    return {
        "version": 1,
        "enabled": True,
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


def _safe_value_emoji(raw_opt: Any, fallback: str = "") -> str:
    if isinstance(raw_opt, dict) and "value_emoji" in raw_opt:
        return _safe_text(raw_opt.get("value_emoji"), "")
    return _safe_text(fallback, "")


def _looks_like_open_label(text: str) -> bool:
    t = str(text or "").strip().lower()
    return "inna (jaka?)" in t or "inne (jakie?)" in t


def _canonical_core_option_code(field: str, raw_code: Any, raw_label: Any) -> str:
    field_u = str(field or "").strip().upper()
    source = _safe_text(raw_code) or _safe_text(raw_label)
    if not source:
        return ""
    n = _norm_icon_token(source)
    if field_u == "M_PLEC":
        if "kobiet" in n:
            return "kobieta"
        if "mezczyzn" in n:
            return "mężczyzna"
    elif field_u == "M_WIEK":
        if re.search(r"15\D*39", n):
            return "15-39"
        if re.search(r"40\D*59", n):
            return "40-59"
        if "60" in n:
            return "60+"
    elif field_u == "M_WYKSZT":
        if "wyzsze" in n:
            return "wyższe"
        if "srednie" in n:
            return "średnie"
        if any(k in n for k in ("podstaw", "gimnaz", "zawod", "podst./gim./zaw")):
            return "podst./gim./zaw."
    elif field_u == "M_ZAWOD":
        if "umysl" in n:
            return "prac. umysłowy"
        if "fizycz" in n:
            return "prac. fizyczny"
        if "wlasn" in n and "firm" in n:
            return "własna firma"
        if "student" in n or "uczen" in n:
            return "student/uczeń"
        if "bezrobot" in n:
            return "bezrobotny"
        if "renc" in n or "emery" in n:
            return "rencista/emeryt"
        if "inna" in n or "jaka" in n:
            return "inna"
    elif field_u == "M_MATERIAL":
        if "odmaw" in n:
            return "odmowa"
        if "bardzo dobrze" in n or "bardzo dobra" in n:
            return "bardzo dobra"
        if "raczej dobrze" in n or "raczej dobra" in n:
            return "raczej dobra"
        if "przeciet" in n or "srednio" in n:
            return "przeciętna"
        if "raczej zle" in n or "raczej zla" in n:
            return "raczej zła"
        if "bardzo zle" in n or "bardzo zla" in n or "ciezk" in n:
            return "bardzo zła"
    return source


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
        lock_randomization = _safe_bool(item.get("lock_randomization"), False)
        value_emoji = _safe_text(item.get("value_emoji"), "")
        out.append(
            {
                "label": label,
                "code": code,
                "is_open": bool(is_open),
                "lock_randomization": bool(lock_randomization),
                "value_emoji": value_emoji,
            }
        )
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
                "lock_randomization": _safe_bool(o.get("lock_randomization"), False),
                "value_emoji": _safe_text(o.get("value_emoji"), ""),
            }
        )
    return fallback_out


def _apply_legacy_exclude_last_lock(
    options: List[Dict[str, Any]],
    *,
    randomize_options: bool,
    randomize_exclude_last: bool,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    has_locked = False
    for opt in options:
        if not isinstance(opt, dict):
            continue
        cloned = dict(opt)
        locked = _safe_bool(cloned.get("lock_randomization"), False)
        if locked:
            has_locked = True
        cloned["lock_randomization"] = bool(locked)
        out.append(cloned)
    if not out:
        return out
    if randomize_options and randomize_exclude_last and not has_locked:
        out[-1]["lock_randomization"] = True
    return out


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
    table_label = _safe_text(raw.get("table_label"), prompt)
    variable_emoji = _safe_text(
        raw.get("variable_emoji"),
        guess_metry_variable_emoji(db_column, table_label, prompt),
    )

    fallback_options: List[Dict[str, Any]] = []
    randomize_options = _safe_bool(raw.get("randomize_options"), False)
    randomize_exclude_last = _safe_bool(raw.get("randomize_exclude_last"), False)
    options = _normalize_options(raw.get("options"), fallback=fallback_options)
    options = _apply_legacy_exclude_last_lock(
        options,
        randomize_options=randomize_options,
        randomize_exclude_last=randomize_exclude_last,
    )
    normalized_opts: List[Dict[str, Any]] = []
    for opt in options:
        if not isinstance(opt, dict):
            continue
        opt_copy = dict(opt)
        code = _safe_text(opt_copy.get("code"), _safe_text(opt_copy.get("label")))
        if not code:
            continue
        opt_copy["value_emoji"] = _safe_value_emoji(
            opt_copy,
            guess_metry_value_emoji(table_label, code, db_column),
        )
        normalized_opts.append(opt_copy)
    options = normalized_opts
    if not options:
        return {}

    used_columns.add(db_column)
    return {
        "id": qid,
        "scope": "custom",
        "db_column": db_column,
        "prompt": prompt,
        "table_label": table_label,
        "variable_emoji": variable_emoji,
        "required": _safe_bool(raw.get("required"), True),
        "multiple": _safe_bool(raw.get("multiple"), False),
        "randomize_options": randomize_options,
        "randomize_exclude_last": False,
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
    enabled = _safe_bool(raw.get("enabled"), True)

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
        randomize_options = _safe_bool(src.get("randomize_options"), False)
        randomize_exclude_last = _safe_bool(src.get("randomize_exclude_last"), False)
        base["prompt"] = _safe_text(src.get("prompt"), base["prompt"])
        base["table_label"] = _safe_text(src.get("table_label"), _safe_text(base.get("table_label"), base["prompt"]))
        base["variable_emoji"] = _safe_text(
            src.get("variable_emoji"),
            _safe_text(base.get("variable_emoji"), guess_metry_variable_emoji(qid, base.get("table_label"), base.get("prompt"))),
        )
        base["required"] = True
        base["multiple"] = False
        base["randomize_options"] = randomize_options
        base["randomize_exclude_last"] = False
        base["aliases"] = _normalize_aliases(src.get("aliases")) or base["aliases"]
        core_opts = _normalize_options(src.get("options"), fallback=base["options"])
        core_opts = _apply_legacy_exclude_last_lock(
            core_opts,
            randomize_options=randomize_options,
            randomize_exclude_last=randomize_exclude_last,
        )
        normalized_core_opts: List[Dict[str, Any]] = []
        seen_labels: set[str] = set()
        base_emoji_by_label: Dict[str, str] = {
            _safe_text(o.get("label")).lower(): _safe_text(o.get("value_emoji"), "")
            for o in list(base.get("options") or [])
            if isinstance(o, dict)
        }
        for opt in core_opts:
            label = _safe_text(opt.get("label"))
            canon_code = _canonical_core_option_code(qid, _safe_text(opt.get("code")), label)
            key = label.lower()
            if not label or not canon_code or key in seen_labels:
                continue
            seen_labels.add(key)
            normalized_core_opts.append(
                {
                    "label": label,
                    "code": canon_code,
                    "is_open": _safe_bool(opt.get("is_open"), _looks_like_open_label(label)),
                    "lock_randomization": _safe_bool(opt.get("lock_randomization"), False),
                    "value_emoji": _safe_value_emoji(
                        opt,
                        base_emoji_by_label.get(key, guess_metry_value_emoji(base.get("table_label"), label, qid)),
                    ),
                }
            )
        if not normalized_core_opts:
            normalized_core_opts = [
                {
                    "label": _safe_text(o.get("label")),
                    "code": _canonical_core_option_code(qid, _safe_text(o.get("code")), _safe_text(o.get("label"))),
                    "is_open": _safe_bool(o.get("is_open"), _looks_like_open_label(_safe_text(o.get("label")))),
                    "lock_randomization": _safe_bool(o.get("lock_randomization"), False),
                    "value_emoji": _safe_value_emoji(
                        o,
                        guess_metry_value_emoji(base.get("table_label"), _safe_text(o.get("label")), qid),
                    ),
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
        "enabled": bool(enabled),
        "questions": normalized_questions,
    }


def normalize_personal_metryczka_config(raw: Any) -> Dict[str, Any]:
    return normalize_jst_metryczka_config(raw)


def metryczka_enabled(config: Any) -> bool:
    cfg = normalize_jst_metryczka_config(config)
    return _safe_bool(cfg.get("enabled"), True)


def metryczka_questions(config: Any) -> List[Dict[str, Any]]:
    cfg = normalize_jst_metryczka_config(config)
    if not _safe_bool(cfg.get("enabled"), True):
        return []
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
