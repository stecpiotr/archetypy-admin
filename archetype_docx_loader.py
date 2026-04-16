from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from docx import Document


METRIC_FIELDS_ORDER = (
    "Esencja",
    "Rozbudowany opis",
    "Grupa",
    "Podstawowe pragnienie",
    "Cel",
    "Największa obawa",
    "Strategia",
    "Pułapka",
    "Dar",
    "Cień",
    "Funkcja w polityce",
    "Obietnica dla ludzi",
    "Slogany (Taglines)",
    "Kluczowe atrybuty",
    "4 filary wartości",
    "Atuty",
    "Słabości",
    "Oś narracyjna i antagonista",
    "Słowa-klucze (Talking points)",
    "Sygnatury wizualne",
    "Przykłady archetypów",
    "Paleta kolorów (HEX)",
)

EXAMPLE_GROUPS = ("Politycy", "Marki/organizacje", "Popkultura/postacie")
TOP_SECTION_RE = re.compile(r"^([1-9])\.\s+")
SUBSECTION_RE = re.compile(r"^[1-9]\.\d+(?:\.\d+)?\.")
HEX_RE = re.compile(r"#[0-9A-Fa-f]{6}")

METRIC_FIELD_LOOKUP = {name.casefold(): name for name in METRIC_FIELDS_ORDER}
EXAMPLE_GROUP_LOOKUP = {name.casefold(): name for name in EXAMPLE_GROUPS}
EXAMPLE_GROUP_LOOKUP["popkultura/postaci"] = "Popkultura/postacie"

CORE_TRIPLET_MAP = {
    "Bohater": "Odwaga. Determinacja. Wyzwanie.",
    "Władca": "Porządek. Odpowiedzialność. Ramy.",
    "Mędrzec": "Rozsądek. Wiedza. Analiza.",
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


def _normalize_ws(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").replace("\xa0", " ")).strip()


def _clean_list_item(text: str) -> str:
    item = _normalize_ws(text)
    item = re.sub(r"^[•\-\u2013\u2014]\s*", "", item)
    item = item.strip()
    return item.rstrip(".") if item.endswith(".") and item.count(".") == 1 else item


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = _normalize_ws(item)
        if not key:
            continue
        key_cf = key.casefold()
        if key_cf in seen:
            continue
        seen.add(key_cf)
        out.append(key)
    return out


def _split_semicolon_lines(lines: list[str]) -> list[str]:
    out: list[str] = []
    for line in lines:
        parts = re.split(r"\s*;\s*", _normalize_ws(line))
        for part in parts:
            item = _clean_list_item(part)
            if item:
                out.append(item)
    return _dedupe_keep_order(out)


def _split_examples_lines(lines: list[str]) -> list[str]:
    out: list[str] = []
    for line in lines:
        parts = re.split(r"\s*[;,]\s*", _normalize_ws(line))
        for part in parts:
            item = _clean_list_item(part)
            if item:
                out.append(item)
    return _dedupe_keep_order(out)


def _split_comma_lines(lines: list[str]) -> list[str]:
    joined = " ".join(_normalize_ws(line) for line in lines if _normalize_ws(line))
    if not joined:
        return []
    parts = re.split(r"\s*[;,]\s*", joined)
    out = [_clean_list_item(part) for part in parts if _clean_list_item(part)]
    return _dedupe_keep_order(out)


def _join_paragraphs(lines: list[str]) -> str:
    parts = [_normalize_ws(line) for line in lines if _normalize_ws(line)]
    return "\n\n".join(parts)


def _extract_storyline(lines: list[str]) -> str:
    for line in lines:
        txt = _normalize_ws(line)
        if txt.casefold().startswith("storyline"):
            _, _, rest = txt.partition(":")
            return _normalize_ws(rest) if rest else txt
    return _normalize_ws(lines[0]) if lines else ""


def _extract_recommendations(expanded_sections: list[dict[str, Any]]) -> list[str]:
    for section in expanded_sections:
        for subsection in section.get("subsections", []):
            title = _normalize_ws(subsection.get("title", "")).casefold()
            if "9.1" not in title:
                continue
            mode: str | None = None
            recs: list[str] = []
            for line in subsection.get("content", []):
                txt = _normalize_ws(line)
                low = txt.casefold()
                if low.startswith("do:"):
                    mode = "do"
                    continue
                if ("don't" in low) or ("don’t" in low) or ("dont" in low):
                    mode = "dont"
                    continue
                if mode == "do":
                    item = _clean_list_item(txt)
                    if item:
                        recs.append(item)
            if recs:
                return _dedupe_keep_order(recs)
    return []


def _extract_questions(expanded_sections: list[dict[str, Any]]) -> list[str]:
    out: list[str] = []
    for section in expanded_sections:
        for subsection in section.get("subsections", []):
            title = _normalize_ws(subsection.get("title", "")).casefold()
            if "9.4" not in title and "pytania do autorefleksji" not in title:
                continue
            for line in subsection.get("content", []):
                txt = _normalize_ws(line)
                if not txt:
                    continue
                if txt.casefold().startswith("pytania diagnostyczne"):
                    continue
                if "?" in txt:
                    out.append(txt)
    return _dedupe_keep_order(out)


def _metric_field_from_text(text: str) -> str | None:
    return METRIC_FIELD_LOOKUP.get(_normalize_ws(text).casefold())


def _example_group_from_text(text: str) -> str | None:
    return EXAMPLE_GROUP_LOOKUP.get(_normalize_ws(text).casefold())


def _is_top_section(text: str) -> bool:
    return bool(TOP_SECTION_RE.match(_normalize_ws(text)))


def _is_subsection_heading(text: str, style_name: str) -> bool:
    norm = _normalize_ws(text)
    if SUBSECTION_RE.match(norm):
        return True
    if style_name in {"Heading 3", "Heading 4"}:
        return True
    if style_name == "Heading 2" and SUBSECTION_RE.match(norm):
        return True
    return False


def _build_metric_display(
    metric_raw: dict[str, list[str]],
    example_map: dict[str, list[str]],
    color_palette: list[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for label in METRIC_FIELDS_ORDER:
        if label == "Przykłady archetypów":
            rows.append(
                {
                    "label": label,
                    "kind": "examples",
                    "value": {
                        "Politycy": example_map.get("Politycy", []),
                        "Marki/organizacje": example_map.get("Marki/organizacje", []),
                        "Popkultura/postacie": example_map.get("Popkultura/postacie", []),
                    },
                }
            )
            continue
        if label == "Paleta kolorów (HEX)":
            rows.append({"label": label, "kind": "colors", "value": color_palette})
            continue

        lines = metric_raw.get(label, [])
        if label in {"Slogany (Taglines)", "4 filary wartości", "Atuty", "Słabości"}:
            value = _split_semicolon_lines(lines)
            kind = "list"
        elif label in {"Kluczowe atrybuty", "Słowa-klucze (Talking points)", "Sygnatury wizualne"}:
            value = _split_comma_lines(lines)
            kind = "list"
        else:
            value = _join_paragraphs(lines)
            kind = "text"
        rows.append({"label": label, "kind": kind, "value": value})
    return rows


def _format_metric_for_report(metric_rows: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for row in metric_rows:
        label = row.get("label", "")
        kind = row.get("kind", "text")
        value = row.get("value")
        if kind == "examples":
            lines.append(f"{label}:")
            for group, items in (value or {}).items():
                if items:
                    lines.append(f"- {group}: {', '.join(items)}")
        elif isinstance(value, list):
            if value:
                lines.append(f"{label}: {', '.join(value)}")
        else:
            text_value = _normalize_ws(str(value or ""))
            if text_value:
                lines.append(f"{label}: {text_value}")
    return "\n".join(lines).strip()


def _format_expanded_for_report(expanded_sections: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for section in expanded_sections:
        title = _normalize_ws(section.get("title", ""))
        if title:
            lines.append(title)
        for subsection in section.get("subsections", []):
            subtitle = _normalize_ws(subsection.get("title", ""))
            if subtitle:
                lines.append(subtitle)
            for content_line in subsection.get("content", []):
                clean = _normalize_ws(content_line)
                if clean:
                    lines.append(f"- {clean}")
        lines.append("")
    return "\n".join(lines).strip()


def _parse_single_docx(path: Path) -> dict[str, Any]:
    doc = Document(path)
    paragraphs: list[dict[str, str]] = []
    for para in doc.paragraphs:
        text = _normalize_ws(para.text)
        if not text:
            continue
        style_name = para.style.name if para.style is not None else ""
        paragraphs.append({"text": text, "style": style_name})

    archetype_name = (
        next((p["text"] for p in paragraphs if p["style"] == "Heading 1"), None)
        or path.stem.replace("opisy_", "").replace("_", " ").strip()
    )

    metric_raw: dict[str, list[str]] = {field: [] for field in METRIC_FIELDS_ORDER}
    examples_raw: dict[str, list[str]] = {group: [] for group in EXAMPLE_GROUPS}
    expanded_sections: list[dict[str, Any]] = []

    in_metric = False
    current_metric_field: str | None = None
    current_example_group: str | None = None
    current_section: dict[str, Any] | None = None
    current_subsection: dict[str, Any] | None = None

    for para in paragraphs:
        text = para["text"]
        style_name = para["style"]

        if _normalize_ws(text).casefold() == "metryka archetypu":
            in_metric = True
            current_metric_field = None
            current_example_group = None
            continue

        if _is_top_section(text):
            in_metric = False
            current_metric_field = None
            current_example_group = None
            current_section = {"title": text, "subsections": []}
            expanded_sections.append(current_section)
            current_subsection = None
            continue

        if in_metric:
            metric_field = _metric_field_from_text(text)
            if metric_field:
                current_metric_field = metric_field
                current_example_group = None
                continue

            if current_metric_field == "Przykłady archetypów":
                grp = _example_group_from_text(text)
                if grp:
                    current_example_group = grp
                    continue
                if current_example_group:
                    examples_raw[current_example_group].append(text)
                continue

            if current_metric_field:
                metric_raw[current_metric_field].append(text)
            continue

        if current_section is None:
            continue

        if _is_subsection_heading(text, style_name):
            current_subsection = {"title": text, "content": []}
            current_section["subsections"].append(current_subsection)
            continue

        if current_subsection is None:
            current_subsection = {"title": "", "content": []}
            current_section["subsections"].append(current_subsection)
        current_subsection["content"].append(text)

    color_palette = _dedupe_keep_order(HEX_RE.findall(" ".join(metric_raw["Paleta kolorów (HEX)"])))
    examples_person = _split_examples_lines(examples_raw.get("Politycy", []))
    example_brands = _split_examples_lines(examples_raw.get("Marki/organizacje", []))
    examples_pop = _split_examples_lines(examples_raw.get("Popkultura/postacie", []))

    core_traits = _split_comma_lines(metric_raw["Kluczowe atrybuty"])
    strengths = _split_semicolon_lines(metric_raw["Atuty"])
    weaknesses = _split_semicolon_lines(metric_raw["Słabości"])
    keyword_messaging = _split_comma_lines(metric_raw["Słowa-klucze (Talking points)"])
    visual_elements = _split_comma_lines(metric_raw["Sygnatury wizualne"])
    watchword = _split_semicolon_lines(metric_raw["Slogany (Taglines)"])

    description = _join_paragraphs(metric_raw["Esencja"]) or _join_paragraphs(metric_raw["Rozbudowany opis"])
    storyline = _extract_storyline(metric_raw["Oś narracyjna i antagonista"])
    recommendations = _extract_recommendations(expanded_sections) or _split_semicolon_lines(
        metric_raw["4 filary wartości"]
    )
    questions = _extract_questions(expanded_sections)

    metric_rows = _build_metric_display(
        metric_raw,
        {
            "Politycy": examples_person,
            "Marki/organizacje": example_brands,
            "Popkultura/postacie": examples_pop,
        },
        color_palette,
    )

    return {
        "name": archetype_name,
        "core_triplet": CORE_TRIPLET_MAP.get(archetype_name, ""),
        "tagline": watchword[0] if watchword else "",
        "description": description,
        "storyline": storyline,
        "recommendations": recommendations,
        "core_traits": core_traits,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "examples_person": examples_person,
        "example_brands": example_brands,
        "color_palette": color_palette,
        "visual_elements": visual_elements,
        "keyword_messaging": keyword_messaging,
        "watchword": watchword,
        "questions": questions,
        "metric_rows": metric_rows,
        "metric_examples": {
            "Politycy": examples_person,
            "Marki/organizacje": example_brands,
            "Popkultura/postacie": examples_pop,
        },
        "expanded_sections": expanded_sections,
        "report_metric_text": _format_metric_for_report(metric_rows),
        "report_expanded_text": _format_expanded_for_report(expanded_sections),
    }


@lru_cache(maxsize=4)
def load_archetype_extended(opisy_dir: str | Path) -> dict[str, dict[str, Any]]:
    base_dir = Path(opisy_dir)
    if not base_dir.exists():
        return {}

    out: dict[str, dict[str, Any]] = {}
    for docx_path in sorted(base_dir.glob("opisy_*.docx")):
        parsed = _parse_single_docx(docx_path)
        if parsed.get("name"):
            out[parsed["name"]] = parsed
    return out
