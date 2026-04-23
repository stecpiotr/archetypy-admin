from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypedDict
import unicodedata

ArchetypeId = Literal[
    "niewinny",
    "medrzec",
    "odkrywca",
    "kochanek",
    "towarzysz",
    "blazen",
    "bohater",
    "buntownik",
    "czarodziej",
    "opiekun",
    "tworca",
    "wladca",
]

ArchetypeIntensityBand = Literal["marginal", "weak", "moderate", "significant", "high", "very_high", "extreme"]
DimensionBand = Literal["very_high", "high", "mid_high", "mid", "low_mid", "low"]
ActionDimensionBand = Literal["dominant", "supporting", "visible_non_dominant", "weaker"]


class SubjectForms(TypedDict, total=False):
    fullNom: str | None
    fullGen: str | None
    surnameNom: str | None
    surnameGen: str | None
    firstNameNom: str | None
    firstNameGen: str | None


class ArchetypeMeta(TypedDict):
    valueKey: str
    valuePhrase: str
    publicValue: str
    publicValuePhrase: str
    needsX: float
    needsY: float
    dimensions: dict[str, float]


class ArchetypeResult(TypedDict, total=False):
    id: ArchetypeId
    label: str
    score: float


class InputData(TypedDict, total=False):
    allArchetypes: list[ArchetypeResult]
    primary: ArchetypeResult
    supporting: ArchetypeResult
    tertiary: ArchetypeResult | None
    subjectForms: SubjectForms | None
    personGenitive: str


class GeneratedDescriptions(TypedDict):
    valuesWheelDescription: str
    needsWheelDescription: str
    actionProfileDescription: str


class IntensityResult(TypedDict):
    label: str
    band: ArchetypeIntensityBand


class DimensionStrengthResult(TypedDict):
    label: str
    band: DimensionBand


class ActionDescriptionValidationResult(TypedDict):
    ok: bool
    issues: list[str]


class ActionProfileComparison(TypedDict):
    changed_by_5_or_more: list[str]
    changed_band: list[str]


class ActionTopArchetypes(TypedDict):
    primary: "_ResolvedResult"
    supporting: "_ResolvedResult"
    tertiary: "_ResolvedResult | None"
    subjectForms: SubjectForms | None


class ActionDimensionRoles(TypedDict):
    dominantDims: list[str]
    supportingDims: list[str]
    visibleButNonDominantDims: list[str]
    weakestDims: list[str]


class NeedAxisPriority(TypedDict):
    mode: Literal["axis_priority", "pair_priority"]
    priority_axis: Literal["x", "y"] | None
    priority_side: str | None
    secondary_side: str | None
    secondary_strength: str | None
    primary_side: str | None
    supporting_side: str | None


class ValueCore(TypedDict):
    primaryValue: str
    supportingValue: str
    tertiaryValue: str | None
    primaryPhrase: str
    supportingPhrase: str
    tertiaryPhrase: str | None


ARCHETYPE_META: dict[ArchetypeId, ArchetypeMeta] = {
    "niewinny": {
        "valueKey": "bezpieczeństwo",
        "valuePhrase": "potrzeba bezpieczeństwa, przejrzystości i normalności",
        "publicValue": "Przejrzystość",
        "publicValuePhrase": "potrzeba jasnych zasad, czytelności i normalnego porządku",
        "needsX": 0.5,
        "needsY": -0.866,
        "dimensions": {"empatia": 75, "sprawczosc": 30, "racjonalnosc": 50, "niezaleznosc": 30, "kreatywnosc": 50},
    },
    "medrzec": {
        "valueKey": "wiedza",
        "valuePhrase": "potrzeba rozumienia, faktów i trafnej diagnozy",
        "publicValue": "Rozsądek",
        "publicValuePhrase": "potrzeba rozumnego osądu, proporcji i decyzji opartych na faktach",
        "needsX": -0.5,
        "needsY": -0.866,
        "dimensions": {"empatia": 20, "sprawczosc": 70, "racjonalnosc": 95, "niezaleznosc": 80, "kreatywnosc": 30},
    },
    "odkrywca": {
        "valueKey": "wolność",
        "valuePhrase": "potrzeba autonomii, nowych dróg i przestrzeni do działania",
        "publicValue": "Wolność",
        "publicValuePhrase": "potrzeba autonomii, własnej drogi i przestrzeni do działania",
        "needsX": -0.5,
        "needsY": 0.866,
        "dimensions": {"empatia": 30, "sprawczosc": 55, "racjonalnosc": 45, "niezaleznosc": 90, "kreatywnosc": 80},
    },
    "buntownik": {
        "valueKey": "oswobodzenie",
        "valuePhrase": "potrzeba przełamania ograniczeń i zrzucenia tego, co skostniałe",
        "publicValue": "Odnowa",
        "publicValuePhrase": "potrzeba przełamywania tego, co skostniałe, i otwierania nowego początku",
        "needsX": 0.0,
        "needsY": 1.0,
        "dimensions": {"empatia": 20, "sprawczosc": 60, "racjonalnosc": 25, "niezaleznosc": 95, "kreatywnosc": 85},
    },
    "czarodziej": {
        "valueKey": "moc",
        "valuePhrase": "potrzeba wpływu, transformacji i realnego kształtowania rzeczywistości",
        "publicValue": "Wizja",
        "publicValuePhrase": "potrzeba nadawania kierunku zmianie i przekuwania wizji w realny wpływ",
        "needsX": -0.866,
        "needsY": -0.5,
        "dimensions": {"empatia": 45, "sprawczosc": 65, "racjonalnosc": 80, "niezaleznosc": 70, "kreatywnosc": 90},
    },
    "bohater": {
        "valueKey": "mistrzostwo",
        "valuePhrase": "potrzeba skuteczności, standardu działania i dowożenia wyniku",
        "publicValue": "Odwaga",
        "publicValuePhrase": "potrzeba działania, mierzenia się z trudnością i brania odpowiedzialności",
        "needsX": -1.0,
        "needsY": 0.0,
        "dimensions": {"empatia": 30, "sprawczosc": 95, "racjonalnosc": 40, "niezaleznosc": 75, "kreatywnosc": 40},
    },
    "kochanek": {
        "valueKey": "intymność",
        "valuePhrase": "potrzeba bliskości, znaczenia i relacyjnej intensywności",
        "publicValue": "Relacje",
        "publicValuePhrase": "potrzeba bliskości, znaczenia i prawdziwego kontaktu z ludźmi",
        "needsX": 0.866,
        "needsY": 0.5,
        "dimensions": {"empatia": 85, "sprawczosc": 45, "racjonalnosc": 30, "niezaleznosc": 25, "kreatywnosc": 60},
    },
    "blazen": {
        "valueKey": "przyjemność",
        "valuePhrase": "potrzeba lekkości, energii i przyciągania uwagi",
        "publicValue": "Otwartość",
        "publicValuePhrase": "potrzeba lekkości, świeżości i przyciągania uwagi energią oraz dystansem",
        "needsX": 0.5,
        "needsY": 0.866,
        "dimensions": {"empatia": 50, "sprawczosc": 45, "racjonalnosc": 20, "niezaleznosc": 45, "kreatywnosc": 90},
    },
    "towarzysz": {
        "valueKey": "przynależność",
        "valuePhrase": "potrzeba wspólnoty, swojskości i bycia jednym z nas",
        "publicValue": "Współpraca",
        "publicValuePhrase": "potrzeba wspólnoty, swojskości i działania razem z ludźmi",
        "needsX": 0.866,
        "needsY": -0.5,
        "dimensions": {"empatia": 85, "sprawczosc": 60, "racjonalnosc": 45, "niezaleznosc": 25, "kreatywnosc": 20},
    },
    "opiekun": {
        "valueKey": "troska",
        "valuePhrase": "potrzeba opieki, ochrony i niepozostawiania ludzi samych",
        "publicValue": "Troska",
        "publicValuePhrase": "potrzeba ochrony, wsparcia i niepozostawiania ludzi samych",
        "needsX": 1.0,
        "needsY": 0.0,
        "dimensions": {"empatia": 95, "sprawczosc": 60, "racjonalnosc": 60, "niezaleznosc": 20, "kreatywnosc": 25},
    },
    "wladca": {
        "valueKey": "kontrola",
        "valuePhrase": "potrzeba porządku, sterowności i utrzymania wpływu na bieg spraw",
        "publicValue": "Porządek",
        "publicValuePhrase": "potrzeba ładu, odpowiedzialności i utrzymania spraw we właściwych ramach",
        "needsX": 0.0,
        "needsY": -1.0,
        "dimensions": {"empatia": 25, "sprawczosc": 90, "racjonalnosc": 75, "niezaleznosc": 70, "kreatywnosc": 25},
    },
    "tworca": {
        "valueKey": "innowacja",
        "valuePhrase": "potrzeba tworzenia nowych rozwiązań i nadawania przyszłości konkretnej formy",
        "publicValue": "Rozwój",
        "publicValuePhrase": "potrzeba tworzenia lepszych rozwiązań i nadawania przyszłości konkretnej formy",
        "needsX": -0.866,
        "needsY": 0.5,
        "dimensions": {"empatia": 35, "sprawczosc": 75, "racjonalnosc": 40, "niezaleznosc": 80, "kreatywnosc": 95},
    },
}

PUBLIC_VALUE_BY_LABEL: dict[str, str] = {
    "Niewinny": "Przejrzystość",
    "Niewinna": "Przejrzystość",
    "Mędrzec": "Rozsądek",
    "Mędrczyni": "Rozsądek",
    "Odkrywca": "Wolność",
    "Odkrywczyni": "Wolność",
    "Buntownik": "Odnowa",
    "Buntowniczka": "Odnowa",
    "Czarodziej": "Wizja",
    "Czarodziejka": "Wizja",
    "Bohater": "Odwaga",
    "Bohaterka": "Odwaga",
    "Kochanek": "Relacje",
    "Kochanka": "Relacje",
    "Błazen": "Otwartość",
    "Komiczka": "Otwartość",
    "Towarzysz": "Współpraca",
    "Towarzyszka": "Współpraca",
    "Opiekun": "Troska",
    "Opiekunka": "Troska",
    "Władca": "Porządek",
    "Władczyni": "Porządek",
    "Twórca": "Rozwój",
    "Twórczyni": "Rozwój",
}

LABEL_TO_ID: dict[str, ArchetypeId] = {
    "Niewinny": "niewinny",
    "Niewinna": "niewinny",
    "Mędrzec": "medrzec",
    "Mędrczyni": "medrzec",
    "Odkrywca": "odkrywca",
    "Odkrywczyni": "odkrywca",
    "Kochanek": "kochanek",
    "Kochanka": "kochanek",
    "Towarzysz": "towarzysz",
    "Towarzyszka": "towarzysz",
    "Błazen": "blazen",
    "Komiczka": "blazen",
    "Bohater": "bohater",
    "Bohaterka": "bohater",
    "Buntownik": "buntownik",
    "Buntowniczka": "buntownik",
    "Czarodziej": "czarodziej",
    "Czarodziejka": "czarodziej",
    "Opiekun": "opiekun",
    "Opiekunka": "opiekun",
    "Twórca": "tworca",
    "Twórczyni": "tworca",
    "Władca": "wladca",
    "Władczyni": "wladca",
}

LABEL_ACCUSATIVE: dict[str, str] = {
    "Niewinny": "Niewinnego",
    "Niewinna": "Niewinną",
    "Mędrzec": "Mędrca",
    "Mędrczyni": "Mędrczynię",
    "Odkrywca": "Odkrywcę",
    "Odkrywczyni": "Odkrywczynię",
    "Kochanek": "Kochanka",
    "Kochanka": "Kochankę",
    "Towarzysz": "Towarzysza",
    "Towarzyszka": "Towarzyszkę",
    "Błazen": "Błazna",
    "Komiczka": "Komiczkę",
    "Bohater": "Bohatera",
    "Bohaterka": "Bohaterkę",
    "Buntownik": "Buntownika",
    "Buntowniczka": "Buntowniczkę",
    "Czarodziej": "Czarodzieja",
    "Czarodziejka": "Czarodziejkę",
    "Opiekun": "Opiekuna",
    "Opiekunka": "Opiekunkę",
    "Twórca": "Twórcę",
    "Twórczyni": "Twórczynię",
    "Władca": "Władcę",
    "Władczyni": "Władczynię",
}

LABEL_GENITIVE: dict[str, str] = {
    "Niewinny": "Niewinnego",
    "Niewinna": "Niewinnej",
    "Mędrzec": "Mędrca",
    "Mędrczyni": "Mędrczyni",
    "Odkrywca": "Odkrywcy",
    "Odkrywczyni": "Odkrywczyni",
    "Kochanek": "Kochanka",
    "Kochanka": "Kochanki",
    "Towarzysz": "Towarzysza",
    "Towarzyszka": "Towarzyszki",
    "Błazen": "Błazna",
    "Komiczka": "Komiczki",
    "Bohater": "Bohatera",
    "Bohaterka": "Bohaterki",
    "Buntownik": "Buntownika",
    "Buntowniczka": "Buntowniczki",
    "Czarodziej": "Czarodzieja",
    "Czarodziejka": "Czarodziejki",
    "Opiekun": "Opiekuna",
    "Opiekunka": "Opiekunki",
    "Twórca": "Twórcy",
    "Twórczyni": "Twórczyni",
    "Władca": "Władcy",
    "Władczyni": "Władczyni",
}

FEMALE_LABELS = {
    "Niewinna",
    "Mędrczyni",
    "Odkrywczyni",
    "Kochanka",
    "Towarzyszka",
    "Komiczka",
    "Bohaterka",
    "Buntowniczka",
    "Czarodziejka",
    "Opiekunka",
    "Twórczyni",
    "Władczyni",
}

DIM_LABELS: dict[str, str] = {
    "empatia": "empatii",
    "sprawczosc": "sprawczości",
    "racjonalnosc": "racjonalności",
    "niezaleznosc": "niezależności",
    "kreatywnosc": "kreatywności",
}

DIM_LABELS_NOMINATIVE: dict[str, str] = {
    "empatia": "empatia",
    "sprawczosc": "sprawczość",
    "racjonalnosc": "racjonalność",
    "niezaleznosc": "niezależność",
    "kreatywnosc": "kreatywność",
}

DIM_LABELS_INSTRUMENTAL: dict[str, str] = {
    "empatia": "empatią",
    "sprawczosc": "sprawczością",
    "racjonalnosc": "racjonalnością",
    "niezaleznosc": "niezależnością",
    "kreatywnosc": "kreatywnością",
}

ACTION_DIMENSIONS: tuple[str, ...] = (
    "empatia",
    "sprawczosc",
    "racjonalnosc",
    "niezaleznosc",
    "kreatywnosc",
)

ACTION_BAND_RANK: dict[ActionDimensionBand, int] = {
    "weaker": 0,
    "visible_non_dominant": 1,
    "supporting": 2,
    "dominant": 3,
}

PAIR_INTERPRETATION: dict[str, str] = {
    "sprawczosc+niezaleznosc": "To wzmacnia obraz przywództwa decyzyjnego, samodzielnego i odpowiedzialnego za wynik.",
    "sprawczosc+racjonalnosc": "To wzmacnia obraz przywództwa rzeczowego, uporządkowanego i zdolnego przekładać diagnozę na działanie.",
    "empatia+sprawczosc": "To wzmacnia obraz przywództwa, które łączy troskę z realnym działaniem.",
    "empatia+kreatywnosc": "To wzmacnia obraz przywództwa relacyjnego, atrakcyjnego komunikacyjnie i łatwo budującego zaangażowanie.",
    "niezaleznosc+kreatywnosc": "To wzmacnia obraz przywództwa reformującego, które szuka nowych dróg i nie boi się wychodzić poza schemat.",
    "racjonalnosc+niezaleznosc": "To wzmacnia obraz przywództwa samodzielnego strategicznie, bardziej ufającego własnemu osądowi niż presji otoczenia.",
    "racjonalnosc+kreatywnosc": "To wzmacnia obraz przywództwa wizjonerskiego, które łączy wyobraźnię z myśleniem systemowym.",
    "empatia+racjonalnosc": "To wzmacnia obraz przywództwa rozważnego i społecznie uważnego.",
    "empatia+niezaleznosc": "To wzmacnia obraz przywództwa wyrazistego, ale nadal zakorzenionego w potrzebach ludzi.",
    "sprawczosc+kreatywnosc": "To wzmacnia obraz przywództwa, które nie tylko wymyśla zmianę, ale potrafi ją uruchomić.",
}

INTENSITY_BANDS: list[tuple[float, ArchetypeIntensityBand, str]] = [
    (30.0, "marginal", "marginalne natężenie"),
    (50.0, "weak", "słabe natężenie"),
    (60.0, "moderate", "umiarkowane natężenie"),
    (70.0, "significant", "znaczące natężenie"),
    (80.0, "high", "wysokie natężenie"),
    (90.0, "very_high", "bardzo wysokie natężenie (rdzeń)"),
    (101.0, "extreme", "ekstremalne natężenie"),
]

DIMENSION_LABELS_BY_BAND: dict[DimensionBand, str] = {
    "very_high": "bardzo wysoka",
    "high": "wysoka",
    "mid_high": "umiarkowanie wysoka",
    "mid": "umiarkowana",
    "low_mid": "obniżona",
    "low": "niska",
}


@dataclass(frozen=True)
class _ResolvedResult:
    id: ArchetypeId
    label: str
    score: float


def _normalize_label(value: str) -> str:
    ascii_value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return " ".join(ascii_value.lower().split())


NORMALIZED_LABEL_TO_ID = {_normalize_label(label): arche_id for label, arche_id in LABEL_TO_ID.items()}


def classifyArchetypeIntensity(score: float) -> IntensityResult:
    value = max(0.0, min(100.0, float(score)))
    for upper_bound, band, label in INTENSITY_BANDS:
        if value < upper_bound:
            return {"label": label, "band": band}
    return {"label": "ekstremalne natężenie", "band": "extreme"}


def classifyDimensionStrength(value: float) -> DimensionStrengthResult:
    v = float(value)
    if v >= 85:
        band: DimensionBand = "very_high"
    elif v >= 70:
        band = "high"
    elif v >= 55:
        band = "mid_high"
    elif v >= 45:
        band = "mid"
    elif v >= 30:
        band = "low_mid"
    else:
        band = "low"
    return {"label": DIMENSION_LABELS_BY_BAND[band], "band": band}


def getDimensionPhrase(value: float, role: Literal["top", "middle", "low"]) -> str:
    band = classifyDimensionStrength(value)["band"]
    if role == "top":
        return {
            "very_high": "bardzo wysokiej",
            "high": "wysokiej",
            "mid_high": "umiarkowanie wysokiej",
            "mid": "umiarkowanej",
            "low_mid": "obniżonej",
            "low": "niskiej",
        }[band]
    if role == "middle":
        return {
            "very_high": "bardzo mocnym wsparciu",
            "high": "mocnym wsparciu",
            "mid_high": "solidnym wsparciu",
            "mid": "dodatkowym ważnym komponencie",
            "low_mid": "drugoplanowym komponencie",
            "low": "marginalnym komponencie",
        }[band]
    return {
        "very_high": "wyraźnej",
        "high": "wyraźnej",
        "mid_high": "wyraźnej",
        "mid": "obecnej w wyraźnym, ale niedominującym stopniu",
        "low_mid": "obniżonej",
        "low": "obniżonej",
    }[band]


def classifyDimensionBand(value: float) -> ActionDimensionBand:
    v = float(value)
    if v >= 70:
        return "dominant"
    if v >= 50:
        return "supporting"
    if v >= 40:
        return "visible_non_dominant"
    return "weaker"


def _blend_action_dimensions(active: list[_ResolvedResult]) -> dict[str, float]:
    total = sum(item.score for item in active) or 1.0
    return {
        dim: sum(item.score * ARCHETYPE_META[item.id]["dimensions"][dim] for item in active) / total for dim in ACTION_DIMENSIONS
    }


def _join_with_and(parts: list[str]) -> str:
    cleaned = [str(item).strip() for item in parts if str(item).strip()]
    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        return f"{cleaned[0]} i {cleaned[1]}"
    return f"{', '.join(cleaned[:-1])} i {cleaned[-1]}"


def _format_dimension_names(dims: list[str], case: Literal["genitive", "nominative", "instrumental"]) -> str:
    if case == "genitive":
        labels = DIM_LABELS
    elif case == "instrumental":
        labels = DIM_LABELS_INSTRUMENTAL
    else:
        labels = DIM_LABELS_NOMINATIVE
    return _join_with_and([labels[dim] for dim in dims if dim in labels])


def _sentence_case(text: str) -> str:
    if not text:
        return text
    return text[0].upper() + text[1:]


def splitActionDimensionRoles(blendedDims: dict[str, float]) -> ActionDimensionRoles:
    ranked = sorted(blendedDims.items(), key=lambda item: item[1], reverse=True)
    dominant = [dim for dim, value in ranked if classifyDimensionBand(value) == "dominant"]
    supporting = [dim for dim, value in ranked if classifyDimensionBand(value) == "supporting"]
    visible = [dim for dim, value in ranked if classifyDimensionBand(value) == "visible_non_dominant"]
    weakest = [dim for dim, value in ranked if classifyDimensionBand(value) == "weaker"]

    # Gdy brak twardych dominantów, bierzemy dwa najwyższe jako filary opisu.
    if not dominant and ranked:
        dominant = [dim for dim, _ in ranked[:2]]

    seen: set[str] = set()
    dominant = [dim for dim in dominant if dim not in seen and not seen.add(dim)]
    supporting = [dim for dim in supporting if dim not in seen and not seen.add(dim)]
    visible = [dim for dim in visible if dim not in seen and not seen.add(dim)]
    weakest = [dim for dim in weakest if dim not in seen and not seen.add(dim)]

    return {
        "dominantDims": dominant,
        "supportingDims": supporting,
        "visibleButNonDominantDims": visible,
        "weakestDims": weakest,
    }


def compareTwoVsThreeArchetypes(blend2: dict[str, float], blend3: dict[str, float]) -> ActionProfileComparison:
    changed_by_5_or_more: list[str] = []
    changed_band: list[str] = []
    for dim in ACTION_DIMENSIONS:
        value2 = float(blend2.get(dim, 0.0))
        value3 = float(blend3.get(dim, 0.0))
        if (value3 - value2) >= 5.0:
            changed_by_5_or_more.append(dim)
        band2 = classifyDimensionBand(value2)
        band3 = classifyDimensionBand(value3)
        if ACTION_BAND_RANK[band3] > ACTION_BAND_RANK[band2]:
            changed_band.append(dim)

    changed_by_5_or_more.sort(key=lambda dim: float(blend3.get(dim, 0.0)) - float(blend2.get(dim, 0.0)), reverse=True)
    changed_band.sort(
        key=lambda dim: (
            ACTION_BAND_RANK[classifyDimensionBand(float(blend3.get(dim, 0.0)))],
            float(blend3.get(dim, 0.0)) - float(blend2.get(dim, 0.0)),
        ),
        reverse=True,
    )
    return {
        "changed_by_5_or_more": changed_by_5_or_more,
        "changed_band": changed_band,
    }


def buildActionProfileNarrative(
    blendedDims: dict[str, float],
    topArchetypes: ActionTopArchetypes,
    maybeComparisonToTwoArchetypes: ActionProfileComparison | None = None,
) -> str:
    primary = topArchetypes["primary"]
    supporting = topArchetypes["supporting"]
    tertiary = topArchetypes["tertiary"]
    subject_forms = topArchetypes.get("subjectForms")
    subject = getPreferredGenitive(subject_forms) or "tego układu"
    ranked = sorted(blendedDims.items(), key=lambda item: item[1], reverse=True)
    roles = splitActionDimensionRoles(blendedDims)
    dominant_list = list(roles["dominantDims"])
    supporting_dims = list(roles["supportingDims"])
    visible_dims = list(roles["visibleButNonDominantDims"])
    weaker_dims = list(roles["weakestDims"])
    if not dominant_list and ranked:
        dominant_list = [dim for dim, _ in ranked[:2]]

    sentence1 = f"Rdzeń działania {subject} tworzą {primary.label} i {supporting.label}."
    if tertiary is not None:
        sentence1 += f" Dodatkowy ton wnosi {tertiary.label}."
        tertiary_gen = _label_genitive(tertiary.label)
        if maybeComparisonToTwoArchetypes:
            changed_by_5 = [dim for dim in list(maybeComparisonToTwoArchetypes.get("changed_by_5_or_more", [])) if dim in DIM_LABELS]
            changed_band = [dim for dim in list(maybeComparisonToTwoArchetypes.get("changed_band", [])) if dim in DIM_LABELS]
            focus_dim = (changed_band[0] if changed_band else (changed_by_5[0] if changed_by_5 else None))
            anchor_dim = None
            if "niezaleznosc" in dominant_list and focus_dim != "niezaleznosc":
                anchor_dim = "niezaleznosc"
            for dim in dominant_list:
                if anchor_dim is None and dim != focus_dim:
                    anchor_dim = dim
                    break
            if anchor_dim is None and dominant_list:
                anchor_dim = dominant_list[0]

            if focus_dim:
                sentence1 += (
                    f" Po dołożeniu {tertiary_gen} wyraźniej zaznacza się komponent "
                    f"{DIM_LABELS[focus_dim]}"
                )
                if anchor_dim is not None:
                    sentence1 += (
                        f", a {DIM_LABELS_NOMINATIVE[anchor_dim]} "
                        "pozostaje jednym z głównych filarów tego układu."
                    )
                else:
                    sentence1 += "."

    sentence2 = f"W praktyce daje to profil oparty przede wszystkim na {_format_dimension_names(dominant_list, 'genitive')}."

    sentence_support = ""
    if supporting_dims:
        support_text = _format_dimension_names(supporting_dims, "nominative")
        if min(float(blendedDims.get(dim, 0.0)) for dim in supporting_dims) >= 60.0:
            if len(supporting_dims) == 1:
                sentence_support = f"Istotne wsparcie w tym układzie daje {support_text}."
            else:
                sentence_support = f"Istotne wsparcie w tym układzie dają {support_text}."
        else:
            if len(supporting_dims) == 1:
                sentence_support = f"Dodatkowym ważnym komponentem pozostaje {support_text}."
            else:
                sentence_support = f"Dodatkowymi ważnymi komponentami pozostają {support_text}."

    sentence_visible = ""
    if visible_dims:
        if len(visible_dims) == 1:
            sentence_visible = (
                f"{_sentence_case(DIM_LABELS_NOMINATIVE[visible_dims[0]])} "
                "pozostaje obecna w wyraźnym, ale niedominującym stopniu."
            )
        else:
            sentence_visible = (
                f"{_sentence_case(_format_dimension_names(visible_dims, 'nominative'))} "
                "pozostają obecne w wyraźnym, ale niedominującym stopniu."
            )

    sentence_weak = ""
    weak_sorted = sorted(weaker_dims, key=lambda dim: blendedDims.get(dim, 0.0))
    if len(weak_sorted) == 1:
        sentence_weak = f"Najsłabszym wymiarem pozostaje {DIM_LABELS_NOMINATIVE[weak_sorted[0]]}."
    elif len(weak_sorted) >= 2:
        lowest = weak_sorted[0]
        second_lowest = weak_sorted[1]
        if blendedDims.get(second_lowest, 0.0) - blendedDims.get(lowest, 0.0) >= 5.0:
            sentence_weak = f"Najsłabszym wymiarem pozostaje {DIM_LABELS_NOMINATIVE[lowest]}."
            remaining = weak_sorted[1:]
            if remaining:
                remaining_text = _format_dimension_names(remaining, "nominative")
                verb = "pozostaje słabszym wymiarem działania" if len(remaining) == 1 else "pozostają słabszymi wymiarami działania"
                sentence_weak += f" {_sentence_case(remaining_text)} {verb}."
        else:
            weak_text = _format_dimension_names(weak_sorted, "nominative")
            verb = "pozostaje słabszym wymiarem działania" if len(weak_sorted) == 1 else "pozostają słabszymi wymiarami działania"
            sentence_weak = f"{_sentence_case(weak_text)} {verb}."

    top_dim_a, top_dim_b = ranked[0][0], ranked[1][0]
    summary_base = _pair_interpretation(top_dim_a, top_dim_b)
    if primary.id == "buntownik" and {top_dim_a, top_dim_b} == {"empatia", "sprawczosc"}:
        summary_base = (
            "To wzmacnia obraz przywództwa wyrazistego, społecznie zakorzenionego "
            "i gotowego przekuwać energię zmiany w konkretne działanie."
        )
    summary_sentence = _build_action_summary_sentence(top_dim_a, top_dim_b, summary_base)

    first_paragraph_segments = [sentence1, sentence2]
    if sentence_support:
        first_paragraph_segments.append(sentence_support)
    if sentence_visible:
        first_paragraph_segments.append(sentence_visible)
    if sentence_weak:
        first_paragraph_segments.append(sentence_weak)
    first_paragraph = " ".join(segment.strip() for segment in first_paragraph_segments if segment.strip())
    return f"{first_paragraph}\n\n{summary_sentence}"


def validateGeneratedActionDescription(meta: dict[str, object]) -> ActionDescriptionValidationResult:
    issues: list[str] = []
    blended = meta.get("blended")
    used_phrases = meta.get("used_phrases")
    top_dims = meta.get("top_dims")
    joint_dominance = bool(meta.get("joint_dominance"))
    third_support_used = bool(meta.get("third_support_used"))
    third_value = float(meta.get("third_value") or 0.0)

    if isinstance(blended, dict) and isinstance(used_phrases, dict):
        for dim, phrase in used_phrases.items():
            if not isinstance(dim, str) or dim not in blended:
                continue
            value = float(blended[dim])
            phrase_l = str(phrase).lower()
            if 45 <= value < 55 and any(word in phrase_l for word in ("niska", "słaba", "obniżona", "marginalna")):
                issues.append(f"Wymiar {dim}={value:.1f} opisany jako zbyt niski.")
            if value >= 70 and "umiarkowan" in phrase_l:
                issues.append(f"Wymiar {dim}={value:.1f} opisany zbyt miękko jako umiarkowany.")
            if value >= 85 and any(word in phrase_l for word in ("niska", "słaba", "obniżona", "marginalna")):
                issues.append(f"Wymiar {dim}={value:.1f} opisany jako niski mimo bardzo wysokiego poziomu.")

    if isinstance(blended, dict) and isinstance(top_dims, (list, tuple)) and len(top_dims) >= 2:
        d1 = str(top_dims[0])
        d2 = str(top_dims[1])
        if d1 in blended and d2 in blended:
            diff = abs(float(blended[d1]) - float(blended[d2]))
            if diff <= 7 and not joint_dominance:
                issues.append("Brak sygnału wspólnej dominacji przy różnicy <= 7 pkt.")
    if third_value >= 55 and not third_support_used:
        issues.append("Brak wzmianki o istotnym wsparciu trzeciego wymiaru >= 55.")

    return {"ok": not issues, "issues": issues}


def getPreferredGenitive(subjectForms: SubjectForms | None = None) -> str | None:
    if not subjectForms:
        return None
    for field in ("fullGen", "surnameGen"):
        value = str(subjectForms.get(field) or "").strip()
        if value:
            return value
    return None


def getNameAwareOpening(type: Literal["values", "needs", "action"], subjectForms: SubjectForms | None = None) -> str:
    genitive = getPreferredGenitive(subjectForms)
    if type == "values":
        return f"Rdzeń motywacyjny {genitive}" if genitive else "Rdzeń motywacyjny tego układu"
    if type == "needs":
        return f"Układ potrzeb {genitive}" if genitive else "Układ potrzeb tego wyniku"
    return f"Rdzeń działania {genitive}" if genitive else "Rdzeń działania tego układu"


def _resolve_subject_forms(input_data: InputData) -> SubjectForms | None:
    forms = input_data.get("subjectForms")
    if forms:
        return forms
    legacy = str(input_data.get("personGenitive") or "").strip()
    if legacy:
        return {"fullGen": legacy}
    return None


def _resolve_archetype_id(result: ArchetypeResult) -> ArchetypeId:
    raw_id = result.get("id")
    if isinstance(raw_id, str) and raw_id in ARCHETYPE_META:
        return raw_id  # type: ignore[return-value]

    raw_label = str(result.get("label") or "").strip()
    if raw_label in LABEL_TO_ID:
        return LABEL_TO_ID[raw_label]

    normalized = _normalize_label(raw_label)
    mapped = NORMALIZED_LABEL_TO_ID.get(normalized)
    if mapped:
        return mapped
    raise ValueError(f"Nieznana etykieta archetypu: {raw_label!r}")


def _resolve_result(result: ArchetypeResult) -> _ResolvedResult:
    score = float(result.get("score") or 0.0)
    label = str(result.get("label") or "").strip()
    return _ResolvedResult(id=_resolve_archetype_id(result), label=label, score=score)


def _dominance_type(primary_score: float, supporting_score: float) -> str:
    gap = float(primary_score) - float(supporting_score)
    if gap <= 3:
        return "co_dominant"
    if gap <= 10:
        return "dominant_with_strong_support"
    return "clear_dominant"


def _has_tertiary(tertiary: _ResolvedResult | None) -> bool:
    return bool(tertiary and tertiary.score >= 70.0)


def _axis_strength(value: float) -> str:
    abs_value = abs(value)
    if abs_value < 0.18:
        return "balanced"
    if abs_value < 0.45:
        return "soft"
    if abs_value < 0.75:
        return "clear"
    return "strong"


def _x_description(x: float) -> str:
    strength = _axis_strength(x)
    if strength == "balanced":
        return "pozostaje bez wyraźnego przechyłu między niezależnością a przynależnością"
    if x < 0:
        return {
            "soft": "lekko ciąży ku niezależności",
            "clear": "wyraźnie ciąży ku niezależności",
            "strong": "zdecydowanie ciąży ku niezależności",
        }[strength]
    return {
        "soft": "lekko ciąży ku przynależności",
        "clear": "wyraźnie ciąży ku przynależności",
        "strong": "zdecydowanie ciąży ku przynależności",
    }[strength]


def _y_description(y: float) -> str:
    strength = _axis_strength(y)
    if strength == "balanced":
        return "przy bardziej zrównoważonym układzie między zmianą a stabilnością"
    if y < 0:
        return {
            "soft": "z lekkim przechyłem ku stabilności",
            "clear": "z wyraźnym przechyłem ku stabilności",
            "strong": "zdecydowanie po stronie stabilności",
        }[strength]
    return {
        "soft": "z lekkim przechyłem ku zmianie",
        "clear": "z wyraźnym przechyłem ku zmianie",
        "strong": "zdecydowanie po stronie zmiany",
    }[strength]


def _x_meaning(x: float) -> str:
    if _axis_strength(x) == "balanced":
        return "łączeniu samodzielnego podejmowania decyzji z byciem blisko ludzi i współdziałaniem"
    if x < 0:
        return "samodzielnym podejmowaniu decyzji i opieraniu się na własnym kierunku"
    return "relacji z ludźmi, budowaniu wspólnoty i dostrajaniu się do otoczenia"


def _y_meaning(y: float) -> str:
    if _axis_strength(y) == "balanced":
        return "łączeniu porządkowania rzeczywistości z gotowością do korekt i zmiany"
    if y < 0:
        return "porządkowaniu rzeczywistości, utrzymywaniu kursu i przewidywalności"
    return "szukaniu nowych dróg, uruchamianiu ruchu i przełamywaniu stagnacji"


def _x_opposite_meaning(x: float) -> str:
    if _axis_strength(x) == "balanced":
        return "jednostronnym forsowaniu tylko jednej strony osi"
    if x < 0:
        return "silnym dostrajaniu się do otoczenia"
    return "dystansie i pełnej autonomii"


def _y_opposite_meaning(y: float) -> str:
    if _axis_strength(y) == "balanced":
        return "szukaniu skrajności zamiast równowagi"
    if y < 0:
        return "biernym trwaniu przy tym, co zastane"
    return "trzymaniu się rutyny i przewidywalności"


def _need_side_from_axis(value: float, axis: Literal["x", "y"]) -> str:
    threshold = 0.15
    if axis == "x":
        if value <= -threshold:
            return "niezaleznosc"
        if value >= threshold:
            return "przynaleznosc"
        return "balanced"
    if value <= -threshold:
        return "stabilnosc"
    if value >= threshold:
        return "zmiana"
    return "balanced"


def _need_side_locative(side: str) -> str:
    return {
        "niezaleznosc": "niezależności",
        "przynaleznosc": "przynależności",
        "stabilnosc": "stabilności",
        "zmiana": "zmianie",
    }.get(side, "równowadze")


def _need_side_nominative(side: str) -> str:
    return {
        "niezaleznosc": "niezależność",
        "przynaleznosc": "przynależność",
        "stabilnosc": "stabilność",
        "zmiana": "zmiana",
    }.get(side, "równowaga")


def _need_side_accusative(side: str) -> str:
    return {
        "niezaleznosc": "niezależność",
        "przynaleznosc": "przynależność",
        "stabilnosc": "stabilność",
        "zmiana": "zmianę",
    }.get(side, "równowagę")


def _need_side_instrumental(side: str) -> str:
    return {
        "niezaleznosc": "niezależnością",
        "przynaleznosc": "przynależnością",
        "stabilnosc": "stabilnością",
        "zmiana": "zmianą",
    }.get(side, "równowagą")


def _z_preposition(word: str) -> str:
    normalized = str(word or "").lower()
    if normalized.startswith(("s", "z", "sz", "cz", "ś", "ź", "ż")):
        return "ze"
    return "z"


def _need_side_meaning(side: str) -> str:
    return {
        "niezaleznosc": "samodzielnym podejmowaniu decyzji i opieraniu się na własnym kierunku",
        "przynaleznosc": "relacjach z ludźmi, budowaniu wspólnoty i dostrajaniu się do otoczenia",
        "stabilnosc": "porządkowaniu rzeczywistości, utrzymywaniu kursu i przewidywalności",
        "zmiana": "szukaniu nowych dróg, uruchamianiu ruchu i przełamywaniu stagnacji",
    }.get(side, "łączeniu skrajności w bardziej zrównoważony sposób")


def _need_side_counter_meaning(side: str) -> str:
    return {
        "niezaleznosc": "silnym dostrajaniu się do otoczenia",
        "przynaleznosc": "samotnej autonomii i utrzymywaniu dystansu wobec otoczenia",
        "stabilnosc": "ciągłym uruchamianiu zmiany",
        "zmiana": "zachowawczym trzymaniu się tego, co zastane",
    }.get(side, "pomijaniu drugiego bieguna potrzeb")


def _primary_needs_style_clause(primary_id: ArchetypeId, core_side: str) -> str | None:
    relational_core = {"kochanek", "towarzysz", "opiekun"}
    order_core = {"niewinny", "medrzec", "wladca"}
    dynamic_core = {"bohater", "odkrywca", "buntownik", "tworca", "czarodziej", "blazen"}

    if primary_id in relational_core and core_side != "przynaleznosc":
        return "realizowany bardziej w relacji z ludźmi, bliskości i budowaniu wspólnoty niż w samotnej autonomii"
    if primary_id in order_core and core_side != "stabilnosc":
        return "osadzony bardziej w zasadach, odpowiedzialnym osądzie i przewidywalności niż w ciągłym eksperymentowaniu"
    if primary_id in dynamic_core and core_side not in {"zmiana", "niezaleznosc"}:
        return "prowadzony bardziej przez sprawczość, własny kierunek i uruchamianie zmiany niż przez zachowawczość"
    return None


def _need_tilt_phrase(side: str, strength: str) -> str:
    if side == "balanced" or strength == "balanced":
        return "przy bardziej zrównoważonym układzie na drugiej osi"
    adjective = {
        "soft": "lekkim",
        "clear": "wyraźnym",
        "strong": "silnym",
    }.get(strength, "wyraźnym")
    return f"z {adjective} przechyłem ku {_need_side_locative(side)}"


def _dominant_need_side_for_archetype(archetype: _ResolvedResult) -> str:
    meta = ARCHETYPE_META[archetype.id]
    x = float(meta["needsX"])
    y = float(meta["needsY"])
    side_x = _need_side_from_axis(x, "x")
    side_y = _need_side_from_axis(y, "y")
    if side_x == "balanced" and side_y != "balanced":
        return side_y
    if side_y == "balanced" and side_x != "balanced":
        return side_x
    if abs(x) >= abs(y):
        return side_x
    return side_y


def resolve_need_axis_priority(
    primary: _ResolvedResult,
    supporting: _ResolvedResult,
    tertiary: _ResolvedResult | None,
    centroid: tuple[float, float],
) -> NeedAxisPriority:
    _ = tertiary
    primary_meta = ARCHETYPE_META[primary.id]
    supporting_meta = ARCHETYPE_META[supporting.id]
    px = float(primary_meta["needsX"])
    py = float(primary_meta["needsY"])
    sx = float(supporting_meta["needsX"])
    sy = float(supporting_meta["needsY"])
    cx, cy = centroid

    px_side = _need_side_from_axis(px, "x")
    sx_side = _need_side_from_axis(sx, "x")
    py_side = _need_side_from_axis(py, "y")
    sy_side = _need_side_from_axis(sy, "y")

    same_y = py_side == sy_side and py_side != "balanced"
    same_x = px_side == sx_side and px_side != "balanced"

    if same_y or same_x:
        if same_y and same_x:
            y_power = abs(py) + abs(sy)
            x_power = abs(px) + abs(sx)
            priority_axis: Literal["x", "y"] = "y" if y_power >= x_power else "x"
        elif same_y:
            priority_axis = "y"
        else:
            priority_axis = "x"

        priority_side = py_side if priority_axis == "y" else px_side
        secondary_axis: Literal["x", "y"] = "x" if priority_axis == "y" else "y"
        secondary_value = cx if secondary_axis == "x" else cy
        secondary_side = _need_side_from_axis(secondary_value, secondary_axis)
        secondary_strength = _axis_strength(secondary_value)
        return {
            "mode": "axis_priority",
            "priority_axis": priority_axis,
            "priority_side": priority_side,
            "secondary_side": secondary_side,
            "secondary_strength": secondary_strength,
            "primary_side": None,
            "supporting_side": None,
        }

    return {
        "mode": "pair_priority",
        "priority_axis": None,
        "priority_side": None,
        "secondary_side": None,
        "secondary_strength": None,
        "primary_side": _dominant_need_side_for_archetype(primary),
        "supporting_side": _dominant_need_side_for_archetype(supporting),
    }


def resolve_need_description_from_hierarchy(
    subject_forms: SubjectForms | None,
    primary: _ResolvedResult,
    supporting: _ResolvedResult,
    tertiary: _ResolvedResult | None,
    centroid: tuple[float, float],
) -> str:
    opening = getNameAwareOpening("needs", subject_forms)
    priority = resolve_need_axis_priority(primary, supporting, tertiary, centroid)

    if priority["mode"] == "axis_priority":
        core_side = str(priority.get("priority_side") or "balanced")
        secondary_side = str(priority.get("secondary_side") or "balanced")
        first_sentence = f"{opening} jest przede wszystkim zakorzeniony w {_need_side_locative(core_side)}"
        tilt = _need_tilt_phrase(secondary_side, str(priority.get("secondary_strength") or "balanced"))
        if tilt:
            first_sentence += f", {tilt}"
        first_sentence += "."
        if primary.id in {"niewinny", "medrzec", "wladca"} and secondary_side != "balanced":
            second_sentence = (
                "W praktyce oznacza to styl działania oparty bardziej na "
                f"{_need_side_meaning(core_side)} niż na {_need_side_counter_meaning(core_side)}, "
                f"a zarazem bardziej na {_need_side_meaning(secondary_side)} niż na {_need_side_counter_meaning(secondary_side)}."
            )
        else:
            second_sentence = f"W praktyce oznacza to styl działania oparty na {_need_side_meaning(core_side)}"
            style_clause = _primary_needs_style_clause(primary.id, core_side)
            if style_clause:
                second_sentence += f", ale {style_clause}"
            second_sentence += "."
    else:
        primary_side = str(priority.get("primary_side") or "niezaleznosc")
        supporting_side = str(priority.get("supporting_side") or "stabilnosc")
        supporting_instr = _need_side_instrumental(supporting_side)
        first_sentence = (
            f"{opening} łączy {_need_side_accusative(primary_side)} "
            f"{_z_preposition(supporting_instr)} {supporting_instr}."
        )
        second_sentence = (
            f"W praktyce oznacza to styl działania oparty na {_need_side_meaning(primary_side)} "
            f"oraz {_need_side_meaning(supporting_side)}."
        )

    primary_gen = _label_genitive(primary.label)
    supporting_gen = _label_genitive(supporting.label)
    if tertiary is not None:
        third_sentence = (
            f"Ten kierunek budują przede wszystkim archetypy {primary_gen} i {supporting_gen}, "
            f"a dodatkowy akcent wnosi {tertiary.label}."
        )
    else:
        third_sentence = f"Ten kierunek budują przede wszystkim archetypy {primary_gen} i {supporting_gen}."

    return f"{first_sentence} {second_sentence} {third_sentence}"


def resolve_value_core_from_hierarchy(
    primary: _ResolvedResult,
    supporting: _ResolvedResult,
    tertiary: _ResolvedResult | None,
) -> ValueCore:
    primary_meta = ARCHETYPE_META[primary.id]
    supporting_meta = ARCHETYPE_META[supporting.id]
    tertiary_meta = ARCHETYPE_META[tertiary.id] if tertiary is not None else None
    return {
        "primaryValue": str(primary_meta["publicValue"]),
        "supportingValue": str(supporting_meta["publicValue"]),
        "tertiaryValue": (str(tertiary_meta["publicValue"]) if tertiary_meta else None),
        "primaryPhrase": str(primary_meta["publicValuePhrase"]),
        "supportingPhrase": str(supporting_meta["publicValuePhrase"]),
        "tertiaryPhrase": (str(tertiary_meta["publicValuePhrase"]) if tertiary_meta else None),
    }


def resolve_value_description_from_hierarchy(
    subject_forms: SubjectForms | None,
    primary: _ResolvedResult,
    supporting: _ResolvedResult,
    tertiary: _ResolvedResult | None,
    dominance_type: str,
) -> str:
    core = resolve_value_core_from_hierarchy(primary, supporting, tertiary)
    opening = getNameAwareOpening("values", subject_forms)
    subject = getPreferredGenitive(subject_forms) or "tego układu"

    if dominance_type == "co_dominant":
        text = (
            f"{opening} tworzy niemal równorzędny duet: {core['primaryValue']} i {core['supportingValue']}. "
            f"Oznacza to przywództwo napędzane przede wszystkim {_phrase_case(core['primaryPhrase'], 'instrumental')}, "
            f"wzmacnianą przez {_phrase_case(core['supportingPhrase'], 'accusative')}."
        )
    elif dominance_type == "dominant_with_strong_support":
        supporting_acc = _public_value_accusative(str(core["supportingValue"]))
        text = (
            f"{opening} opiera się przede wszystkim na wartości {core['primaryValue']}, "
            f"wyraźnie wzmacnianej przez {supporting_acc}. "
            f"W praktyce oznacza to styl budowany na {_phrase_case(core['primaryPhrase'], 'locative')}, "
            f"z dodatkowym akcentem na {_phrase_case(core['supportingPhrase'], 'accusative')}."
        )
    else:
        supporting_acc = _public_value_accusative(str(core["supportingValue"]))
        text = (
            f"Najsilniejszą motywacją {subject} jest {core['primaryValue']}. "
            f"Archetyp wspierający wnosi tu {supporting_acc}, "
            f"ale to {core['primaryValue']} pozostaje głównym źródłem energii i kierunku działania, "
            f"wzmacniając {_phrase_case(core['primaryPhrase'], 'accusative')}."
        )

    if tertiary is not None:
        tertiary_value = str(core["tertiaryValue"] or "")
        tertiary_phrase = str(core["tertiaryPhrase"] or "")
        pronoun = PUBLIC_VALUE_PRONOUN.get(tertiary_value, "która")
        text += (
            f" Dodatkowy ton wnosi tu także {tertiary_value}, "
            f"{pronoun} poszerza ten układ o {_phrase_case(tertiary_phrase, 'accusative')}."
        )
    return text


def _is_female_label(label: str) -> bool:
    return label in FEMALE_LABELS


def _label_accusative(label: str) -> str:
    return LABEL_ACCUSATIVE.get(label, label)


def _label_genitive(label: str) -> str:
    return LABEL_GENITIVE.get(label, label)


def _phrase_case(value_phrase: str, case: Literal["instrumental", "accusative", "locative"]) -> str:
    phrase = str(value_phrase or "").strip()
    if phrase.startswith("potrzeba "):
        tail = phrase[len("potrzeba ") :]
        if case == "instrumental":
            return f"potrzebą {tail}"
        if case == "accusative":
            return f"potrzebę {tail}"
        return f"potrzebie {tail}"
    return phrase


PUBLIC_VALUE_LOCATIVE: dict[str, str] = {
    "Przejrzystość": "Przejrzystości",
    "Rozsądek": "Rozsądku",
    "Wolność": "Wolności",
    "Odnowa": "Odnowie",
    "Wizja": "Wizji",
    "Odwaga": "Odwadze",
    "Relacje": "Relacjach",
    "Otwartość": "Otwartości",
    "Współpraca": "Współpracy",
    "Troska": "Trosce",
    "Porządek": "Porządku",
    "Rozwój": "Rozwoju",
}

PUBLIC_VALUE_ACCUSATIVE: dict[str, str] = {
    "Przejrzystość": "Przejrzystość",
    "Rozsądek": "Rozsądek",
    "Wolność": "Wolność",
    "Odnowa": "Odnowę",
    "Wizja": "Wizję",
    "Odwaga": "Odwagę",
    "Relacje": "Relacje",
    "Otwartość": "Otwartość",
    "Współpraca": "Współpracę",
    "Troska": "Troskę",
    "Porządek": "Porządek",
    "Rozwój": "Rozwój",
}

PUBLIC_VALUE_PRONOUN: dict[str, str] = {
    "Przejrzystość": "która",
    "Rozsądek": "który",
    "Wolność": "która",
    "Odnowa": "która",
    "Wizja": "która",
    "Odwaga": "która",
    "Relacje": "które",
    "Otwartość": "która",
    "Współpraca": "która",
    "Troska": "która",
    "Porządek": "który",
    "Rozwój": "który",
}

def _public_value_accusative(value: str) -> str:
    return PUBLIC_VALUE_ACCUSATIVE.get(value, value)


def _support_participle(primary_label: str) -> str:
    return "wzmacniana" if _is_female_label(primary_label) else "wzmacniany"


def _pair_interpretation(dim_a: str, dim_b: str) -> str:
    key = f"{dim_a}+{dim_b}"
    reverse = f"{dim_b}+{dim_a}"
    text = PAIR_INTERPRETATION.get(key) or PAIR_INTERPRETATION.get(reverse)
    if text:
        return text
    return (
        f"To daje układ, który łączy {DIM_LABELS[dim_a]} z {DIM_LABELS[dim_b]} "
        "i dzięki temu działa w sposób wyraźny oraz rozpoznawalny."
    )


def _build_action_summary_sentence(dim_a: str, dim_b: str, base_text: str) -> str:
    raw = str(base_text or "").strip()
    if not raw:
        return (
            "Całość wzmacnia obraz przywództwa, które łączy "
            f"{DIM_LABELS[dim_a]} z {DIM_LABELS[dim_b]} i działa w sposób wyraźny oraz rozpoznawalny."
        )

    raw_l = raw.lower()
    if raw_l.startswith("to wzmacnia obraz"):
        tail = raw[len("To wzmacnia obraz") :].strip()
        sentence = f"Całość wzmacnia obraz {tail}" if tail else "Całość wzmacnia obraz przywództwa."
    elif raw_l.startswith("to daje układ, który"):
        tail = raw[len("To daje układ, który") :].strip()
        if tail:
            sentence = f"Całość wzmacnia obraz przywództwa, które {tail}"
        else:
            sentence = "Całość wzmacnia obraz przywództwa."
    elif raw_l.startswith("całość wzmacnia obraz") or raw_l.startswith("taki układ wzmacnia obraz") or raw_l.startswith("ten profil wzmacnia obraz"):
        sentence = raw
    else:
        sentence = (
            "Całość wzmacnia obraz przywództwa, które łączy "
            f"{DIM_LABELS[dim_a]} z {DIM_LABELS[dim_b]} i działa w sposób wyraźny oraz rozpoznawalny."
        )

    sentence = sentence.strip()
    if sentence and not sentence.endswith("."):
        sentence += "."
    return sentence


def _generate_values_description(
    subject_forms: SubjectForms | None,
    primary: _ResolvedResult,
    supporting: _ResolvedResult,
    tertiary: _ResolvedResult | None,
    dominance_type: str,
) -> str:
    return resolve_value_description_from_hierarchy(subject_forms, primary, supporting, tertiary, dominance_type)


def _generate_needs_description(
    subject_forms: SubjectForms | None,
    primary: _ResolvedResult,
    supporting: _ResolvedResult,
    tertiary: _ResolvedResult | None,
) -> str:
    active = [primary, supporting] + ([tertiary] if tertiary else [])
    total = sum(item.score for item in active) or 1.0
    x = sum(item.score * ARCHETYPE_META[item.id]["needsX"] for item in active) / total
    y = sum(item.score * ARCHETYPE_META[item.id]["needsY"] for item in active) / total
    return resolve_need_description_from_hierarchy(subject_forms, primary, supporting, tertiary, (x, y))


def _generate_action_description(
    subject_forms: SubjectForms | None,
    primary: _ResolvedResult,
    supporting: _ResolvedResult,
    tertiary: _ResolvedResult | None,
    dominance_type: str,
) -> str:
    _ = dominance_type
    blend_2 = _blend_action_dimensions([primary, supporting])
    blend_current = _blend_action_dimensions([primary, supporting] + ([tertiary] if tertiary else []))
    comparison = compareTwoVsThreeArchetypes(blend_2, blend_current) if tertiary is not None else None
    return buildActionProfileNarrative(
        blend_current,
        {
            "primary": primary,
            "supporting": supporting,
            "tertiary": tertiary,
            "subjectForms": subject_forms,
        },
        comparison,
    )


def generate_archetype_descriptions(input_data: InputData) -> GeneratedDescriptions:
    primary = _resolve_result(input_data["primary"])
    supporting = _resolve_result(input_data["supporting"])
    tertiary_raw = input_data.get("tertiary")
    tertiary = _resolve_result(tertiary_raw) if tertiary_raw else None
    if not _has_tertiary(tertiary):
        tertiary = None
    dominance_type = _dominance_type(primary.score, supporting.score)
    subject_forms = _resolve_subject_forms(input_data)

    return {
        "valuesWheelDescription": _generate_values_description(subject_forms, primary, supporting, tertiary, dominance_type),
        "needsWheelDescription": _generate_needs_description(subject_forms, primary, supporting, tertiary),
        "actionProfileDescription": _generate_action_description(subject_forms, primary, supporting, tertiary, dominance_type),
    }
