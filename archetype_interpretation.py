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


class ArchetypeMeta(TypedDict):
    valueKey: str
    valuePhrase: str
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
    personGenitive: str


class GeneratedDescriptions(TypedDict):
    valuesWheelDescription: str
    needsWheelDescription: str
    actionProfileDescription: str


ARCHETYPE_META: dict[ArchetypeId, ArchetypeMeta] = {
    "niewinny": {
        "valueKey": "bezpieczeństwo",
        "valuePhrase": "potrzeba bezpieczeństwa, przejrzystości i normalności",
        "needsX": 0.5,
        "needsY": -0.866,
        "dimensions": {"empatia": 75, "sprawczosc": 30, "racjonalnosc": 50, "niezaleznosc": 30, "kreatywnosc": 50},
    },
    "medrzec": {
        "valueKey": "wiedza",
        "valuePhrase": "potrzeba rozumienia, faktów i trafnej diagnozy",
        "needsX": -0.5,
        "needsY": -0.866,
        "dimensions": {"empatia": 20, "sprawczosc": 70, "racjonalnosc": 95, "niezaleznosc": 80, "kreatywnosc": 30},
    },
    "odkrywca": {
        "valueKey": "wolność",
        "valuePhrase": "potrzeba autonomii, nowych dróg i przestrzeni do działania",
        "needsX": -0.5,
        "needsY": 0.866,
        "dimensions": {"empatia": 30, "sprawczosc": 55, "racjonalnosc": 45, "niezaleznosc": 90, "kreatywnosc": 80},
    },
    "buntownik": {
        "valueKey": "oswobodzenie",
        "valuePhrase": "potrzeba przełamania ograniczeń i zrzucenia tego, co skostniałe",
        "needsX": 0.0,
        "needsY": 1.0,
        "dimensions": {"empatia": 20, "sprawczosc": 60, "racjonalnosc": 25, "niezaleznosc": 95, "kreatywnosc": 85},
    },
    "czarodziej": {
        "valueKey": "moc",
        "valuePhrase": "potrzeba wpływu, transformacji i realnego kształtowania rzeczywistości",
        "needsX": -0.866,
        "needsY": -0.5,
        "dimensions": {"empatia": 45, "sprawczosc": 65, "racjonalnosc": 80, "niezaleznosc": 70, "kreatywnosc": 90},
    },
    "bohater": {
        "valueKey": "mistrzostwo",
        "valuePhrase": "potrzeba skuteczności, standardu działania i dowożenia wyniku",
        "needsX": -1.0,
        "needsY": 0.0,
        "dimensions": {"empatia": 30, "sprawczosc": 95, "racjonalnosc": 40, "niezaleznosc": 75, "kreatywnosc": 40},
    },
    "kochanek": {
        "valueKey": "intymność",
        "valuePhrase": "potrzeba bliskości, znaczenia i relacyjnej intensywności",
        "needsX": 0.866,
        "needsY": 0.5,
        "dimensions": {"empatia": 85, "sprawczosc": 45, "racjonalnosc": 30, "niezaleznosc": 25, "kreatywnosc": 60},
    },
    "blazen": {
        "valueKey": "przyjemność",
        "valuePhrase": "potrzeba lekkości, energii i przyciągania uwagi",
        "needsX": 0.5,
        "needsY": 0.866,
        "dimensions": {"empatia": 50, "sprawczosc": 45, "racjonalnosc": 20, "niezaleznosc": 45, "kreatywnosc": 90},
    },
    "towarzysz": {
        "valueKey": "przynależność",
        "valuePhrase": "potrzeba wspólnoty, swojskości i bycia \"jednym z nas\"",
        "needsX": 0.866,
        "needsY": -0.5,
        "dimensions": {"empatia": 85, "sprawczosc": 60, "racjonalnosc": 45, "niezaleznosc": 25, "kreatywnosc": 20},
    },
    "opiekun": {
        "valueKey": "troska",
        "valuePhrase": "potrzeba opieki, ochrony i niepozostawiania ludzi samych",
        "needsX": 1.0,
        "needsY": 0.0,
        "dimensions": {"empatia": 95, "sprawczosc": 60, "racjonalnosc": 60, "niezaleznosc": 20, "kreatywnosc": 25},
    },
    "wladca": {
        "valueKey": "kontrola",
        "valuePhrase": "potrzeba porządku, sterowności i utrzymania wpływu na bieg spraw",
        "needsX": 0.0,
        "needsY": -1.0,
        "dimensions": {"empatia": 25, "sprawczosc": 90, "racjonalnosc": 75, "niezaleznosc": 70, "kreatywnosc": 25},
    },
    "tworca": {
        "valueKey": "innowacja",
        "valuePhrase": "potrzeba tworzenia nowych rozwiązań i nadawania przyszłości konkretnej formy",
        "needsX": -0.866,
        "needsY": 0.5,
        "dimensions": {"empatia": 35, "sprawczosc": 75, "racjonalnosc": 40, "niezaleznosc": 80, "kreatywnosc": 95},
    },
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


LABEL_ACCUSATIVE = {
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


DIM_LABELS_LOC = {
    "empatia": "empatii",
    "sprawczosc": "sprawczości",
    "racjonalnosc": "racjonalności",
    "niezaleznosc": "niezależności",
    "kreatywnosc": "kreatywności",
}


PAIR_INTERPRETATION: dict[str, str] = {
    "sprawczosc+niezaleznosc": "To wzmacnia obraz osoby decyzyjnej, samodzielnej i odpowiedzialnej za wynik.",
    "sprawczosc+racjonalnosc": "To wzmacnia obraz osoby rzeczowej, uporządkowanej i zdolnej przekładać diagnozę na działanie.",
    "empatia+sprawczosc": "To wzmacnia obraz osoby, która łączy troskę z realnym działaniem.",
    "empatia+kreatywnosc": "To wzmacnia obraz osoby relacyjnej, atrakcyjnej komunikacyjnie i łatwo budującej zaangażowanie.",
    "niezaleznosc+kreatywnosc": "To wzmacnia obraz osoby reformującej, która szuka nowych dróg i nie boi się wychodzić poza schemat.",
    "racjonalnosc+niezaleznosc": "To wzmacnia obraz osoby samodzielnej strategicznie, bardziej ufającej własnemu osądowi niż presji otoczenia.",
    "racjonalnosc+kreatywnosc": "To wzmacnia obraz osoby wizjonerskiej, która łączy wyobraźnię z myśleniem systemowym.",
    "empatia+racjonalnosc": "To wzmacnia obraz osoby rozważnej i społecznie uważnej.",
    "empatia+niezaleznosc": "To wzmacnia obraz osoby wyrazistej, ale nadal zakorzenionej w potrzebach ludzi.",
    "sprawczosc+kreatywnosc": "To wzmacnia obraz osoby, która nie tylko wymyśla zmianę, ale potrafi ją uruchomić.",
}


VALUE_REPORT: dict[ArchetypeId, dict[str, str]] = {
    "niewinny": {
        "nom": "bezpieczeństwo",
        "main_need": "potrzebie bezpieczeństwa i przejrzystości",
        "sense": "porządkować rzeczywistość i budować poczucie przewidywalności",
    },
    "medrzec": {
        "nom": "wiedza",
        "main_need": "potrzebie wiedzy i rozumienia",
        "sense": "opierać decyzje na faktach i logicznym rozpoznaniu sytuacji",
    },
    "odkrywca": {
        "nom": "wolność",
        "main_need": "potrzebie wolności i autonomii",
        "sense": "szukać własnej drogi i nie zamykać się w utartych ramach",
    },
    "kochanek": {
        "nom": "relacje",
        "main_need": "potrzebie bliskości, znaczenia i relacyjnej intensywności",
        "sense": "budować emocjonalny kontakt i angażować ludzi",
    },
    "towarzysz": {
        "nom": "przynależność",
        "main_need": "potrzebie przynależności, współdziałania i bycia blisko ludzi",
        "sense": "budować wspólnotę i atmosferę bycia razem",
    },
    "blazen": {
        "nom": "lekkość",
        "main_need": "potrzebie lekkości, swobody i przyciągania uwagi",
        "sense": "obniżać temperaturę sporów i uruchamiać komunikacyjną energię",
    },
    "bohater": {
        "nom": "odwaga",
        "main_need": "potrzebie działania, skuteczności i dowożenia wyniku",
        "sense": "przejmować odpowiedzialność i skutecznie domykać sprawy",
    },
    "buntownik": {
        "nom": "odnowa",
        "main_need": "potrzebie przełamania ograniczeń i uruchamiania zmiany",
        "sense": "kwestionować zastój i otwierać nowe kierunki",
    },
    "czarodziej": {
        "nom": "wpływ",
        "main_need": "potrzebie wpływu i transformacji",
        "sense": "przekuwać wizję w realną zmianę",
    },
    "opiekun": {
        "nom": "troska",
        "main_need": "potrzebie troski i ochrony",
        "sense": "wzmacniać bezpieczeństwo ludzi i poczucie oparcia",
    },
    "tworca": {
        "nom": "innowacja",
        "main_need": "potrzebie innowacji i rozwoju",
        "sense": "szukać lepszych rozwiązań i nadawać im konkretną formę",
    },
    "wladca": {
        "nom": "porządek",
        "main_need": "potrzebie porządku i sterowności",
        "sense": "utrzymywać wpływ i kontrolę nad biegiem spraw",
    },
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


def _resolve_archetype_id(result: ArchetypeResult) -> ArchetypeId:
    raw_id = result.get("id")
    if isinstance(raw_id, str) and raw_id in ARCHETYPE_META:
        return raw_id  # type: ignore[return-value]

    raw_label = str(result.get("label") or "").strip()
    if raw_label in LABEL_TO_ID:
        return LABEL_TO_ID[raw_label]

    normalized_label = _normalize_label(raw_label)
    mapped = NORMALIZED_LABEL_TO_ID.get(normalized_label)
    if mapped:
        return mapped
    raise ValueError(f"Nieznana etykieta archetypu: {raw_label!r}")


def _resolve_result(result: ArchetypeResult) -> _ResolvedResult:
    score = float(result.get("score") or 0.0)
    label = str(result.get("label") or "").strip()
    return _ResolvedResult(id=_resolve_archetype_id(result), label=label, score=score)


def _dominance_type(primary_score: float, supporting_score: float) -> str:
    gap12 = float(primary_score) - float(supporting_score)
    if gap12 <= 3:
        return "co_dominant"
    if gap12 <= 10:
        return "dominant_with_strong_support"
    return "clear_dominant"


def _has_tertiary(tertiary: _ResolvedResult | None) -> bool:
    return bool(tertiary and tertiary.score >= 70.0)


def _subject_genitive(input_data: InputData) -> str:
    person = str(input_data.get("personGenitive") or "").strip()
    return person if person else "tej osoby"


def _is_female_label(label: str) -> bool:
    return label in FEMALE_LABELS


def _label_accusative(label: str) -> str:
    return LABEL_ACCUSATIVE.get(label, label)


def _support_participle(primary_label: str) -> str:
    return "wzmacniana" if _is_female_label(primary_label) else "wzmacniany"


def _axis_strength(value: float) -> str:
    abs_value = abs(value)
    if abs_value < 0.18:
        return "balanced"
    if abs_value < 0.45:
        return "soft"
    if abs_value < 0.75:
        return "clear"
    return "strong"


def _direction_x_text(x: float) -> str:
    strength = _axis_strength(x)
    if strength == "balanced":
        return "szuka równowagi między niezależnością a przynależnością"
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


def _x_meaning(x: float) -> str:
    if _axis_strength(x) == "balanced":
        return "łączeniu samodzielności z pracą relacyjną"
    if x < 0:
        return "samodzielnym podejmowaniu decyzji i przejmowaniu odpowiedzialności"
    return "budowaniu relacji, wspólnoty i poczucia bliskości"


def _y_meaning(y: float) -> str:
    if _axis_strength(y) == "balanced":
        return "utrzymywaniu kierunku przy gotowości do korekt"
    if y < 0:
        return "porządkowaniu działań i utrzymywaniu przewidywalności"
    return "uruchamianiu ruchu, przełamywaniu zastoju i nadawaniu zmianie tempa"


def _pair_interpretation(dim_a: str, dim_b: str) -> str:
    key = f"{dim_a}+{dim_b}"
    reverse_key = f"{dim_b}+{dim_a}"
    text = PAIR_INTERPRETATION.get(key) or PAIR_INTERPRETATION.get(reverse_key)
    if text:
        return text
    return (
        f"To daje układ, który łączy {DIM_LABELS_LOC[dim_a]} z {DIM_LABELS_LOC[dim_b]} "
        "i dzięki temu działa w sposób wyraźny oraz rozpoznawalny."
    )


def _dimension_level(value: float) -> str:
    if value >= 85:
        return "bardzo wysokiej"
    if value >= 70:
        return "wysokiej"
    if value >= 50:
        return "umiarkowanej"
    if value >= 35:
        return "niższej"
    return "wyraźnie słabszej"


def _match_exact(
    primary: _ResolvedResult,
    supporting: _ResolvedResult,
    tertiary: _ResolvedResult | None,
    case: tuple[ArchetypeId, ArchetypeId, ArchetypeId | None],
) -> bool:
    cp, cs, ct = case
    if primary.id != cp or supporting.id != cs:
        return False
    if ct is None:
        return tertiary is None
    return bool(tertiary and tertiary.id == ct)


def _generate_values_description(
    input_data: InputData,
    primary: _ResolvedResult,
    supporting: _ResolvedResult,
    tertiary: _ResolvedResult | None,
    dominance_type: str,
) -> str:
    subject = _subject_genitive(input_data)
    val1 = VALUE_REPORT[primary.id]
    val2 = VALUE_REPORT[supporting.id]
    if dominance_type == "co_dominant":
        text = (
            f"Rdzeń motywacyjny {subject} tworzy niemal równorzędny duet: {val1['nom']} i {val2['nom']}. "
            f"Oznacza to sposób przywództwa oparty na potrzebie, by {val1['sense']}, a jednocześnie {val2['sense']}."
        )
    elif dominance_type == "dominant_with_strong_support":
        text = (
            f"Rdzeń motywacyjny {subject} opiera się przede wszystkim na {val1['main_need']}, wyraźnie wzmacnianej przez {val2['main_need']}. "
            f"W praktyce oznacza to styl działania, który chce {val1['sense']}, ale równie mocno potrzebuje, by {val2['sense']}."
        )
    else:
        text = (
            f"Rdzeń motywacyjny {subject} opiera się głównie na {val1['main_need']}. Archetyp wspierający wnosi {val2['nom']}, "
            f"ale kierunek nadal wyznacza {val1['nom']}."
        )
    if tertiary is not None:
        val3 = VALUE_REPORT[tertiary.id]
        text += f" Dodatkowy ton wnosi {val3['nom']}, co poszerza ten układ o gotowość, by {val3['sense']}."
    return text


def _generate_needs_description(
    input_data: InputData,
    primary: _ResolvedResult,
    supporting: _ResolvedResult,
    tertiary: _ResolvedResult | None,
) -> str:
    subject = _subject_genitive(input_data)
    active = [primary, supporting] + ([tertiary] if tertiary else [])
    total = sum(item.score for item in active) or 1.0
    x = sum(item.score * ARCHETYPE_META[item.id]["needsX"] for item in active) / total
    y = sum(item.score * ARCHETYPE_META[item.id]["needsY"] for item in active) / total
    ys = _axis_strength(y)
    first = f"Układ potrzeb {subject} {_direction_x_text(x)}"
    if ys == "balanced":
        first += ", przy bardziej uporządkowanym niż rewolucyjnym stylu działania."
    elif y < 0:
        first += {"soft": ", z lekkim przechyłem ku stabilności.", "clear": ", z wyraźnym przechyłem ku stabilności.", "strong": ", zdecydowanie po stronie stabilności."}[ys]
    else:
        first += {"soft": ", ale równocześnie lekko otwiera się na zmianę.", "clear": ", ale równocześnie wyraźnie otwiera się na zmianę.", "strong": ", i równocześnie mocno otwiera się na zmianę."}[ys]
    direction = f"{first} W praktyce oznacza to styl działania oparty bardziej na {_x_meaning(x)} i {_y_meaning(y)} niż na przeciwnej logice."
    if tertiary is not None:
        return f"{direction} Ten kierunek budują przede wszystkim archetypy {primary.label} i {supporting.label}, a dodatkowy akcent wnosi {tertiary.label}."
    return f"{direction} Ten kierunek budują przede wszystkim archetypy {primary.label} i {supporting.label}."


def _generate_action_description(
    input_data: InputData,
    primary: _ResolvedResult,
    supporting: _ResolvedResult,
    tertiary: _ResolvedResult | None,
    dominance_type: str,
) -> str:
    subject = _subject_genitive(input_data)

    if dominance_type == "co_dominant":
        opening = f"Rdzeń działania {subject} tworzą {primary.label} i {supporting.label}."
    elif dominance_type == "dominant_with_strong_support":
        opening = f"Rdzeń działania {subject} buduje {primary.label}, wyraźnie {_support_participle(primary.label)} przez {_label_accusative(supporting.label)}."
    else:
        opening = f"Rdzeń działania {subject} buduje {primary.label}, a {supporting.label} stanowi wyraźne wsparcie."

    active = [primary, supporting] + ([tertiary] if tertiary else [])
    total = sum(item.score for item in active) or 1.0
    dims = ("empatia", "sprawczosc", "racjonalnosc", "niezaleznosc", "kreatywnosc")
    blended = {d: sum(item.score * ARCHETYPE_META[item.id]["dimensions"][d] for item in active) / total for d in dims}
    ranked = sorted(blended.items(), key=lambda item: item[1], reverse=True)
    top1, top2 = ranked[0][0], ranked[1][0]
    low1, low2 = ranked[-1][0], ranked[-2][0]
    text = f"{opening} "
    if tertiary is not None:
        text += f"Dodatkowy ton wnosi {tertiary.label}. "
    text += (
        "W praktyce daje to układ oparty na "
        f"{_dimension_level(blended[top1])} {DIM_LABELS_LOC[top1]} i {_dimension_level(blended[top2])} {DIM_LABELS_LOC[top2]}, "
        f"przy {_dimension_level(blended[low1])} {DIM_LABELS_LOC[low1]} oraz {_dimension_level(blended[low2])} {DIM_LABELS_LOC[low2]}. "
    )
    text += _pair_interpretation(top1, top2)
    return text


def generate_archetype_descriptions(input_data: InputData) -> GeneratedDescriptions:
    primary = _resolve_result(input_data["primary"])
    supporting = _resolve_result(input_data["supporting"])
    tertiary_raw = input_data.get("tertiary")
    tertiary = _resolve_result(tertiary_raw) if tertiary_raw else None
    if not _has_tertiary(tertiary):
        tertiary = None
    dominance_type = _dominance_type(primary.score, supporting.score)
    return {
        "valuesWheelDescription": _generate_values_description(input_data, primary, supporting, tertiary, dominance_type),
        "needsWheelDescription": _generate_needs_description(input_data, primary, supporting, tertiary),
        "actionProfileDescription": _generate_action_description(input_data, primary, supporting, tertiary, dominance_type),
    }
