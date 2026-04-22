from __future__ import annotations

from typing import Literal, Mapping, TypedDict
import unicodedata

ArchetypeIntensityBand = Literal["marginal", "weak", "moderate", "significant", "high", "very_high", "extreme"]


class ArchetypeStrength(TypedDict, total=False):
    label: str
    score: float


class IntensityResult(TypedDict):
    label: str
    band: ArchetypeIntensityBand


class NeedGroupsResult(TypedDict):
    zmiana: float
    ludzie: float
    porzadek: float
    niezaleznosc: float


class ProfileStrengthInput(TypedDict, total=False):
    archetypes: list[ArchetypeStrength]
    primary: ArchetypeStrength
    supporting: ArchetypeStrength
    tertiary: ArchetypeStrength | None
    subjectGenitive: str | None


_LABEL_TO_ID: dict[str, str] = {
    "niewinny": "niewinny",
    "niewinna": "niewinny",
    "medrzec": "medrzec",
    "medrczyni": "medrzec",
    "odkrywca": "odkrywca",
    "odkrywczyni": "odkrywca",
    "kochanek": "kochanek",
    "kochanka": "kochanek",
    "towarzysz": "towarzysz",
    "towarzyszka": "towarzysz",
    "blazen": "blazen",
    "komiczka": "blazen",
    "bohater": "bohater",
    "bohaterka": "bohater",
    "buntownik": "buntownik",
    "buntowniczka": "buntownik",
    "czarodziej": "czarodziej",
    "czarodziejka": "czarodziej",
    "opiekun": "opiekun",
    "opiekunka": "opiekun",
    "tworca": "tworca",
    "tworczyni": "tworca",
    "wladca": "wladca",
    "wladczyni": "wladca",
}

_ID_TO_DISPLAY_LABEL: dict[str, str] = {
    "zmiana": "Zmiana",
    "ludzie": "Ludzie",
    "porzadek": "Porządek",
    "niezaleznosc": "Niezależność",
}

_GROUP_BY_ARCHETYPE_ID: dict[str, str] = {
    "odkrywca": "zmiana",
    "buntownik": "zmiana",
    "blazen": "zmiana",
    "kochanek": "ludzie",
    "opiekun": "ludzie",
    "towarzysz": "ludzie",
    "niewinny": "porzadek",
    "wladca": "porzadek",
    "medrzec": "porzadek",
    "tworca": "niezaleznosc",
    "bohater": "niezaleznosc",
    "czarodziej": "niezaleznosc",
}

_GROUP_STYLE: dict[str, str] = {
    "zmiana": "zmianowy i nastawiony na przełamywanie schematów",
    "ludzie": "wspólnotowy i relacyjny",
    "porzadek": "uporządkowany i instytucjonalny",
    "niezaleznosc": "autonomiczny i samodzielny",
}

_GROUP_LABEL_GENITIVE: dict[str, str] = {
    "zmiana": "Zmiany",
    "ludzie": "Ludzi",
    "porzadek": "Porządku",
    "niezaleznosc": "Niezależności",
}

_GROUP_STYLE_SHORT: dict[str, str] = {
    "zmiana": "zmianowy",
    "ludzie": "relacyjny i wspólnotowy",
    "porzadek": "porządkujący",
    "niezaleznosc": "autonomiczny i samodzielny",
}

_GROUP_WEAK_CONTRAST: dict[str, str] = {
    "zmiana": "wyraziście zmianowy",
    "ludzie": "wyraziście wspólnotowy",
    "porzadek": "uporządkowany i instytucjonalny",
    "niezaleznosc": "skrajnie autonomiczny",
}

_GROUP_WEAK_CONTRAST_SOFT: dict[str, str] = {
    "zmiana": "wyraziście zmianowy",
    "ludzie": "wyraziście wspólnotowy",
    "porzadek": "czysto administracyjno-porządkujący",
    "niezaleznosc": "skrajnie autonomiczny",
}


def _normalize_label(value: str) -> str:
    raw = str(value or "")
    # `ł/Ł` nie przechodzą poprawnie przez samo NFKD->ASCII, więc normalizujemy je ręcznie.
    raw = raw.replace("ł", "l").replace("Ł", "L")
    ascii_value = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_value.lower().split())


def _to_score(value: object) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _normalize_archetype(item: Mapping[str, object] | None) -> ArchetypeStrength | None:
    if not isinstance(item, Mapping):
        return None
    raw_label = str(item.get("label") or "").strip()
    if not raw_label:
        return None
    return {"label": raw_label, "score": _to_score(item.get("score"))}


def _as_profile_strength_input(raw: Mapping[str, object]) -> ProfileStrengthInput:
    archetypes_src = raw.get("archetypes")
    if not isinstance(archetypes_src, list):
        archetypes_src = raw.get("allArchetypes")
    archetypes: list[ArchetypeStrength] = []
    if isinstance(archetypes_src, list):
        for item in archetypes_src:
            normalized = _normalize_archetype(item if isinstance(item, Mapping) else None)
            if normalized:
                archetypes.append(normalized)

    primary_raw = _normalize_archetype(raw.get("primary") if isinstance(raw.get("primary"), Mapping) else None)
    supporting_raw = _normalize_archetype(raw.get("supporting") if isinstance(raw.get("supporting"), Mapping) else None)
    tertiary_raw = _normalize_archetype(raw.get("tertiary") if isinstance(raw.get("tertiary"), Mapping) else None)

    ordered = sorted(archetypes, key=lambda item: (-float(item.get("score") or 0.0), str(item.get("label") or "")))
    if primary_raw is None and ordered:
        primary_raw = ordered[0]
    if supporting_raw is None and len(ordered) > 1:
        supporting_raw = ordered[1]
    if tertiary_raw is None and len(ordered) > 2 and float(ordered[2].get("score") or 0.0) >= 70.0:
        tertiary_raw = ordered[2]

    tertiary_effective = tertiary_raw if tertiary_raw and float(tertiary_raw.get("score") or 0.0) >= 70.0 else None
    subject_gen = str(raw.get("subjectGenitive") or raw.get("personGenitive") or "").strip() or None
    return {
        "archetypes": archetypes,
        "primary": primary_raw or {"label": "", "score": 0.0},
        "supporting": supporting_raw or {"label": "", "score": 0.0},
        "tertiary": tertiary_effective,
        "subjectGenitive": subject_gen,
    }


def classifyArchetypeIntensity(score: float) -> IntensityResult:
    value = max(0.0, min(100.0, float(score)))
    if value < 30:
        return {"label": "marginalne natężenie", "band": "marginal"}
    if value < 50:
        return {"label": "słabe natężenie", "band": "weak"}
    if value < 60:
        return {"label": "umiarkowane natężenie", "band": "moderate"}
    if value < 70:
        return {"label": "znaczące natężenie", "band": "significant"}
    if value < 80:
        return {"label": "wysokie natężenie", "band": "high"}
    if value < 90:
        return {"label": "bardzo wysokie natężenie (rdzeń)", "band": "very_high"}
    return {"label": "ekstremalne natężenie", "band": "extreme"}


def aggregateNeedGroups(archetypes: list[ArchetypeStrength]) -> NeedGroupsResult:
    buckets: dict[str, list[float]] = {
        "zmiana": [],
        "ludzie": [],
        "porzadek": [],
        "niezaleznosc": [],
    }
    for item in archetypes:
        label = str(item.get("label") or "").strip()
        archetype_id = _LABEL_TO_ID.get(_normalize_label(label))
        if not archetype_id:
            continue
        group_key = _GROUP_BY_ARCHETYPE_ID.get(archetype_id)
        if not group_key:
            continue
        buckets[group_key].append(_to_score(item.get("score")))

    def _mean(values: list[float]) -> float:
        return float(sum(values) / len(values)) if values else 0.0

    return {
        "zmiana": _mean(buckets["zmiana"]),
        "ludzie": _mean(buckets["ludzie"]),
        "porzadek": _mean(buckets["porzadek"]),
        "niezaleznosc": _mean(buckets["niezaleznosc"]),
    }


def _strength_label(primary_score: float) -> str:
    if primary_score < 50:
        return "słaby"
    if primary_score < 60:
        return "umiarkowany"
    if primary_score < 70:
        return "wyraźny"
    if primary_score < 80:
        return "silny"
    return "bardzo silny"


def _profile_shape(top1: float, top2: float, tertiary: ArchetypeStrength | None) -> str:
    diff = float(top1) - float(top2)
    has_tri_core = bool(tertiary and _to_score(tertiary.get("score")) >= 70.0)
    if has_tri_core:
        return "tri"
    if diff <= 5.0 and top1 < 60.0:
        return "soft"
    if diff <= 5.0:
        return "bi"
    if top1 < 50.0:
        return "spread"
    return "core"


def _opening_sentence(subject_genitive: str | None, strength: str, shape: str) -> str:
    subject_txt = str(subject_genitive or "").strip()
    base = f"Układ siły archetypów {subject_txt}" if subject_txt else "Układ siły archetypów"
    if shape == "tri":
        return f"{base} jest {strength} i trójbiegunowy."
    if shape == "bi":
        return f"{base} jest {strength} i dwubiegunowy."
    if shape == "core":
        return f"{base} jest {strength} i ma czytelny rdzeń."
    return f"{base} jest {strength} i dość rozproszony."


def _roles_sentence(
    shape: str,
    primary_label: str,
    primary_intensity: str,
    supporting_label: str,
    supporting_intensity: str,
    tertiary: ArchetypeStrength | None,
) -> str:
    if shape == "tri" and tertiary is not None and _to_score(tertiary.get("score")) >= 70.0:
        tertiary_label = str(tertiary.get("label") or "").strip() or "archetyp poboczny"
        return (
            f"Archetypem głównym jest {primary_label}, archetypem wspierającym jest {supporting_label}, "
            f"a archetypem pobocznym jest {tertiary_label} — wszystkie trzy współtworzą wyraźny rdzeń profilu."
        )

    def _intensity_locative(label: str) -> str:
        mapping = {
            "marginalne natężenie": "marginalnym natężeniu",
            "słabe natężenie": "słabym natężeniu",
            "umiarkowane natężenie": "umiarkowanym natężeniu",
            "znaczące natężenie": "znaczącym natężeniu",
            "wysokie natężenie": "wysokim natężeniu",
            "bardzo wysokie natężenie (rdzeń)": "bardzo wysokim natężeniu (rdzeń)",
            "ekstremalne natężenie": "ekstremalnym natężeniu",
        }
        return mapping.get(label, label)

    sentence = (
        f"Archetypem głównym jest {primary_label} o {_intensity_locative(primary_intensity)}, "
        f"natomiast archetypem wspierającym jest {supporting_label} o {_intensity_locative(supporting_intensity)}"
    )
    if shape in {"soft", "spread"}:
        sentence += ", co pokazuje profil bez jednego bardzo dominującego rdzenia."
    else:
        sentence += "."
    return sentence


def _pair_style_phrase(top: str, second: str) -> str:
    pair = {top, second}
    if pair == {"niezaleznosc", "zmiana"}:
        return "autonomiczny i nastawiony na uruchamianie ruchu"
    if pair == {"ludzie", "porzadek"}:
        return "wspólnotowy, relacyjny i porządkujący"
    if pair == {"zmiana", "ludzie"}:
        return "zmianowy i relacyjny"
    if pair == {"niezaleznosc", "porzadek"}:
        return "autonomiczny, samodzielny i porządkujący"
    return f"{_GROUP_STYLE_SHORT[top]} oraz {_GROUP_STYLE_SHORT[second]}"


def _should_mention_weakest(shape: str, spread: float, top_gap: float) -> bool:
    if spread > 10.0:
        return True
    if spread >= 8.0 and shape in {"soft", "spread"}:
        return True
    if spread >= 8.0 and top_gap > 3.0:
        return True
    return False


def _needs_balance_sentence(group_values: NeedGroupsResult, ordered_keys: list[str], shape: str) -> tuple[str, str]:
    top = ordered_keys[0]
    second = ordered_keys[1]
    third = ordered_keys[2]
    weakest = ordered_keys[-1]
    spread = float(group_values[top] - group_values[weakest])
    top_gap = float(group_values[top] - group_values[second])
    top_to_third_gap = float(group_values[top] - group_values[third])
    top_label = _ID_TO_DISPLAY_LABEL[top]
    second_label = _ID_TO_DISPLAY_LABEL[second]
    top_gen = _GROUP_LABEL_GENITIVE[top]
    weakest_gen = _GROUP_LABEL_GENITIVE[weakest]

    if top_gap < 1.5:
        lead_txt = ", na zbliżonym poziomie"
    elif top_gap <= 5.0:
        lead_txt = f", z lekką przewagą {top_gen}"
    else:
        lead_txt = f", z wyraźną przewagą {top_gen}"

    weakest_txt = ""
    if _should_mention_weakest(shape, spread, top_gap):
        weakest_txt = f", przy słabszym akcencie {weakest_gen}"

    intro_txt = f"W układzie potrzeb najmocniej zaznaczają się obszary {top_label} i {second_label}{lead_txt}{weakest_txt}."

    pair_style = _pair_style_phrase(top, second)
    weak_contrast = _GROUP_WEAK_CONTRAST[weakest]

    if spread < 5.0:
        balance_txt = (
            "Różnice między grupami nie są duże, a profil jest dość zrównoważony między czterema obszarami potrzeb. "
            f"W praktyce oznacza to połączenie akcentu {_GROUP_STYLE_SHORT[top]} i {_GROUP_STYLE_SHORT[second]} bez wyraźnych skrajności."
        )
    elif spread <= 10.0:
        weak_contrast_soft = _GROUP_WEAK_CONTRAST_SOFT[weakest]
        if {top, second} == {"niezaleznosc", "zmiana"}:
            practical_txt = (
                "W praktyce oznacza to profil bardziej autonomiczny i nastawiony na uruchamianie ruchu "
                "niż czysto administracyjno-porządkujący, przy zachowaniu wyraźnego komponentu porządkowego i relacyjnego."
            )
        else:
            practical_txt = (
                f"W praktyce oznacza to profil bardziej {pair_style} niż {weak_contrast_soft}, "
                "przy zachowaniu obecności pozostałych obszarów."
            )
        balance_txt = (
            "Układ jest lekko przechylony, ale różnice między czterema grupami nie są duże. "
            f"{practical_txt}"
        )
    else:
        # Jeśli TOP1/TOP2 są bardzo blisko, a TOP3 nadal jest blisko czołówki,
        # unikamy opisu „wyraźnie przechylony” mimo większego rozstępu TOP1->najsłabsza grupa.
        if top_gap <= 3.0 and top_to_third_gap <= 6.5:
            weak_contrast_soft = _GROUP_WEAK_CONTRAST_SOFT[weakest]
            balance_txt = (
                "Układ jest lekko przechylony i bez jednego całkowicie dominującego obszaru. "
                f"W praktyce oznacza to profil bardziej {pair_style} niż {weak_contrast_soft}, przy zachowaniu obecności pozostałych obszarów."
            )
        elif top_gap <= 3.0:
            balance_txt = (
                "Układ jest wyraźnie przechylony, ale bez jednego całkowicie dominującego obszaru. "
                f"W praktyce oznacza to profil bardziej {pair_style} niż {weak_contrast}."
            )
        else:
            balance_txt = (
                "Układ jest wyraźnie przechylony. "
                f"W praktyce oznacza to profil bardziej {_GROUP_STYLE[top]} niż {weak_contrast}."
            )
    return intro_txt, balance_txt


def generate_strength_profile_description(raw_input: Mapping[str, object]) -> str:
    prepared = _as_profile_strength_input(raw_input)
    archetypes = list(prepared.get("archetypes") or [])
    primary = prepared.get("primary") or {"label": "", "score": 0.0}
    supporting = prepared.get("supporting") or {"label": "", "score": 0.0}
    tertiary = prepared.get("tertiary")
    subject_gen = prepared.get("subjectGenitive")

    primary_score = _to_score(primary.get("score"))
    supporting_score = _to_score(supporting.get("score"))
    primary_label = str(primary.get("label") or "").strip() or "archetyp główny"
    supporting_label = str(supporting.get("label") or "").strip() or "archetyp wspierający"
    primary_int = classifyArchetypeIntensity(primary_score)["label"]
    supporting_int = classifyArchetypeIntensity(supporting_score)["label"]

    strength = _strength_label(primary_score)
    shape = _profile_shape(primary_score, supporting_score, tertiary)

    first_parts: list[str] = [
        _opening_sentence(subject_gen, strength, shape),
        _roles_sentence(shape, primary_label, primary_int, supporting_label, supporting_int, tertiary),
    ]
    first_paragraph = " ".join(first_parts)

    group_values = aggregateNeedGroups(archetypes)
    ordered_group_keys = sorted(group_values.keys(), key=lambda key: (-float(group_values[key]), key))
    intro_txt, balance_txt = _needs_balance_sentence(group_values, ordered_group_keys, shape)
    second_paragraph = f"{intro_txt} {balance_txt}"

    return f"{first_paragraph}\n\n{second_paragraph}".strip()
