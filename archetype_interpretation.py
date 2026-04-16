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


VALUE_REPORT: dict[ArchetypeId, dict[str, str]] = {
    "niewinny": {
        "nom": "bezpieczeństwo",
        "loc": "bezpieczeństwie",
        "sense": "utrzymywać przewidywalność i poczucie stabilnego gruntu",
    },
    "medrzec": {
        "nom": "diagnoza",
        "loc": "diagnozie",
        "sense": "opierać decyzje na faktach i trafnym rozpoznaniu sytuacji",
    },
    "odkrywca": {
        "nom": "wolność",
        "loc": "wolności",
        "sense": "zachować autonomię i szukać własnej drogi",
    },
    "kochanek": {
        "nom": "relacje",
        "loc": "relacjach",
        "sense": "budować bliskość, znaczenie i emocjonalne zaangażowanie",
    },
    "towarzysz": {
        "nom": "wspólnota",
        "loc": "wspólnocie",
        "sense": "wzmacniać więź i poczucie bycia razem",
    },
    "blazen": {
        "nom": "energia",
        "loc": "energii",
        "sense": "uruchamiać lekkość, uwagę i kontakt",
    },
    "bohater": {
        "nom": "odwaga",
        "loc": "odwadze",
        "sense": "działać skutecznie, przejmować odpowiedzialność i dowozić efekt",
    },
    "buntownik": {
        "nom": "odnowa",
        "loc": "odnowie",
        "sense": "przełamywać zastój i uruchamiać zmianę",
    },
    "czarodziej": {
        "nom": "wpływ",
        "loc": "wpływie",
        "sense": "przekuwać wizję w realną zmianę",
    },
    "opiekun": {
        "nom": "troska",
        "loc": "trosce",
        "sense": "chronić ludzi i wzmacniać bezpieczeństwo relacji",
    },
    "tworca": {
        "nom": "innowacja",
        "loc": "innowacji",
        "sense": "szukać nowych rozwiązań i nadawać im konkretną formę",
    },
    "wladca": {
        "nom": "porządek",
        "loc": "porządku",
        "sense": "utrzymywać sterowność i kontrolę nad biegiem spraw",
    },
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
    if person:
        return person
    return "tej osoby"


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
    return "relacji z ludźmi, emocjonalnym kontakcie i przyciąganiu uwagi"


def _y_meaning(y: float) -> str:
    if _axis_strength(y) == "balanced":
        return "utrzymywaniu kierunku przy gotowości do korekt"
    if y < 0:
        return "utrzymywaniu kierunku i porządkowaniu działań"
    return "poruszaniu ludzi, przełamywaniu zastoju i nadawaniu energii nowy kierunek"


def _is_pair(primary: _ResolvedResult, supporting: _ResolvedResult, id_a: ArchetypeId, id_b: ArchetypeId) -> bool:
    return {primary.id, supporting.id} == {id_a, id_b}


def _is_female_label(label: str) -> bool:
    return label in FEMALE_LABELS


def _label_accusative(label: str) -> str:
    return LABEL_ACCUSATIVE.get(label, label)


def _support_participle(primary_label: str) -> str:
    return "wzmacniana" if _is_female_label(primary_label) else "wzmacniany"


def _dimension_level(value: float) -> str:
    if value >= 80:
        return "bardzo wysokiej"
    if value >= 65:
        return "wysokiej"
    if value >= 50:
        return "umiarkowanej"
    if value >= 35:
        return "niższej"
    return "wyraźnie słabszej"


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


def _generate_values_description(
    input_data: InputData,
    primary: _ResolvedResult,
    supporting: _ResolvedResult,
    tertiary: _ResolvedResult | None,
    has_tertiary: bool,
    dominance_type: str,
) -> str:
    subject_gen = _subject_genitive(input_data)

    if _is_pair(primary, supporting, "kochanek", "buntownik"):
        return (
            f"Rdzeń motywacyjny {subject_gen} opiera się przede wszystkim na relacjach, wyraźnie wzmacnianych przez odnowę. "
            "Oznacza to styl przywództwa, który chce budować bliskość, znaczenie i emocjonalne zaangażowanie, ale nie po to, "
            "by tylko podtrzymywać zgodę — raczej po to, by poruszać ludzi i uruchamiać zmianę. "
            "To układ łączący więź z wyrazistością."
        )

    if _is_pair(primary, supporting, "bohater", "wladca") and has_tertiary and tertiary and tertiary.id == "odkrywca":
        return (
            f"Rdzeń motywacyjny {subject_gen} tworzy niemal równorzędny duet: odwaga i porządek. "
            "Oznacza to przywództwo napędzane potrzebą działania, skuteczności i utrzymywania steru nad biegiem spraw. "
            "Dodatkowy ton wnosi wolność, która poszerza ten układ o potrzebę autonomii, samodzielności i gotowości do szukania własnej drogi."
        )

    val_primary = VALUE_REPORT[primary.id]
    val_supporting = VALUE_REPORT[supporting.id]

    if dominance_type == "co_dominant":
        text = (
            f"Rdzeń motywacyjny {subject_gen} tworzy niemal równorzędny duet: {val_primary['nom']} i {val_supporting['nom']}. "
            f"Oznacza to sposób działania, który chce {val_primary['sense']}, a jednocześnie {val_supporting['sense']}."
        )
    elif dominance_type == "dominant_with_strong_support":
        text = (
            f"Rdzeń motywacyjny {subject_gen} opiera się przede wszystkim na {val_primary['loc']}. "
            f"Wyraźnie wzmacnia go {val_supporting['nom']}. "
            f"W praktyce oznacza to styl przywództwa, który chce {val_primary['sense']}, a jednocześnie {val_supporting['sense']}."
        )
    else:
        text = (
            f"Rdzeń motywacyjny {subject_gen} opiera się głównie na {val_primary['loc']}. "
            f"Archetyp wspierający wnosi {val_supporting['nom']}, ale kierunek nadal wyznacza {val_primary['nom']}."
        )

    if has_tertiary and tertiary is not None:
        val_tertiary = VALUE_REPORT[tertiary.id]
        text += f" Dodatkowy ton wnosi {val_tertiary['nom']}. To poszerza układ o gotowość, by {val_tertiary['sense']}."

    return text


def _generate_needs_description(
    input_data: InputData,
    primary: _ResolvedResult,
    supporting: _ResolvedResult,
    tertiary: _ResolvedResult | None,
    has_tertiary: bool,
) -> str:
    subject_gen = _subject_genitive(input_data)

    if _is_pair(primary, supporting, "kochanek", "buntownik"):
        return (
            f"Układ potrzeb {subject_gen} ciąży ku przynależności, ale równocześnie wyraźnie otwiera się na zmianę. "
            "W praktyce oznacza to styl działania oparty na relacji z ludźmi, emocjonalnym kontakcie i przyciąganiu uwagi, "
            "ale nie po to, by tylko stabilizować sytuację — raczej po to, by poruszać, przełamywać zastój i nadawać energii nowy kierunek."
        )

    if _is_pair(primary, supporting, "bohater", "wladca") and has_tertiary and tertiary and tertiary.id == "odkrywca":
        return (
            f"Układ potrzeb {subject_gen} wyraźnie ciąży ku niezależności, przy bardziej uporządkowanym niż rewolucyjnym stylu działania. "
            "W praktyce oznacza to sposób funkcjonowania oparty na samodzielnym podejmowaniu decyzji, przejmowaniu odpowiedzialności i utrzymywaniu kierunku, "
            "ale z widoczną gotowością do wyjścia poza rutynę, gdy wymaga tego sytuacja."
        )

    active = [primary, supporting] + ([tertiary] if has_tertiary and tertiary is not None else [])
    total = sum(item.score for item in active) or 1.0

    x = sum(item.score * ARCHETYPE_META[item.id]["needsX"] for item in active) / total
    y = sum(item.score * ARCHETYPE_META[item.id]["needsY"] for item in active) / total
    y_strength = _axis_strength(y)

    first_sentence = f"Układ potrzeb {subject_gen} {_direction_x_text(x)}"
    if y_strength == "balanced":
        first_sentence += ", przy bardziej uporządkowanym niż rewolucyjnym stylu działania."
    elif y < 0:
        y_part = {
            "soft": "z lekkim przechyłem ku stabilności",
            "clear": "z wyraźnym przechyłem ku stabilności",
            "strong": "zdecydowanie po stronie stabilności",
        }[y_strength]
        first_sentence += f", {y_part}."
    else:
        y_part = {
            "soft": "ale równocześnie lekko otwiera się na zmianę",
            "clear": "ale równocześnie wyraźnie otwiera się na zmianę",
            "strong": "i równocześnie mocno otwiera się na zmianę",
        }[y_strength]
        first_sentence += f", {y_part}."

    text = (
        f"{first_sentence} "
        f"W praktyce oznacza to sposób działania oparty bardziej na {_x_meaning(x)} oraz {_y_meaning(y)} niż na przeciwnej logice."
    )
    return text


def _generate_action_profile_description(
    input_data: InputData,
    primary: _ResolvedResult,
    supporting: _ResolvedResult,
    tertiary: _ResolvedResult | None,
    has_tertiary: bool,
    dominance_type: str,
) -> str:
    subject_gen = _subject_genitive(input_data)

    if _is_pair(primary, supporting, "kochanek", "buntownik"):
        return (
            f"U {subject_gen} rdzeń działania buduje {primary.label}, wyraźnie {_support_participle(primary.label)} przez {_label_accusative(supporting.label)}. "
            "W praktyce daje to układ oparty na bardzo wysokiej empatii i kreatywności, przy jednocześnie silnym komponencie niezależności oraz umiarkowanej sprawczości. "
            "Taki zestaw sprzyja budowaniu silnej więzi z ludźmi i wyrazistej komunikacji, ale wymaga pilnowania, by emocja i impuls zmiany nie osłabiły porządku działania."
        )

    if _is_pair(primary, supporting, "bohater", "wladca") and has_tertiary and tertiary and tertiary.id == "odkrywca":
        return (
            f"U {subject_gen} rdzeń działania tworzą {primary.label} i {supporting.label}, a dodatkowy ton wnosi {tertiary.label}. "
            "W praktyce daje to bardzo wysoką sprawczość, wysoką niezależność i solidne zaplecze racjonalności, przy wyraźnie słabszym nacisku na empatię i kreatywność. "
            "To układ sprzyjający wizerunkowi osoby zdecydowanej, odpowiedzialnej i skutecznej, która najlepiej wypada tam, gdzie trzeba przejąć ster i dowieźć efekt."
        )

    if dominance_type == "co_dominant":
        opening = f"U {subject_gen} rdzeń działania tworzą {primary.label} i {supporting.label}."
    elif dominance_type == "dominant_with_strong_support":
        opening = (
            f"U {subject_gen} rdzeń działania buduje {primary.label}, "
            f"wyraźnie {_support_participle(primary.label)} przez {_label_accusative(supporting.label)}."
        )
    else:
        opening = f"U {subject_gen} rdzeń działania buduje {primary.label}, a {supporting.label} stanowi wyraźne wsparcie."

    active = [primary, supporting] + ([tertiary] if has_tertiary and tertiary is not None else [])
    total = sum(item.score for item in active) or 1.0
    dims = ("empatia", "sprawczosc", "racjonalnosc", "niezaleznosc", "kreatywnosc")
    blended = {
        dim: sum(item.score * ARCHETYPE_META[item.id]["dimensions"][dim] for item in active) / total
        for dim in dims
    }
    sorted_dims = sorted(blended.items(), key=lambda item: item[1], reverse=True)
    top_dim_1 = sorted_dims[0][0]
    top_dim_2 = sorted_dims[1][0]
    third_dim = sorted_dims[2][0]
    low_dim = sorted_dims[-1][0]

    middle = (
        "W praktyce daje to układ oparty na "
        f"{_dimension_level(blended[top_dim_1])} {DIM_LABELS_LOC[top_dim_1]} i "
        f"{_dimension_level(blended[top_dim_2])} {DIM_LABELS_LOC[top_dim_2]}, "
        f"przy {_dimension_level(blended[third_dim])} {DIM_LABELS_LOC[third_dim]} "
        f"oraz {_dimension_level(blended[low_dim])} {DIM_LABELS_LOC[low_dim]}."
    )

    ending = _pair_interpretation(top_dim_1, top_dim_2)
    text = f"{opening} "
    if has_tertiary and tertiary is not None:
        text += f"Dodatkowy ton wnosi {tertiary.label}. "
    text += f"{middle} {ending}"
    return text


def generate_archetype_descriptions(input_data: InputData) -> GeneratedDescriptions:
    primary = _resolve_result(input_data["primary"])
    supporting = _resolve_result(input_data["supporting"])
    tertiary_raw = input_data.get("tertiary")
    tertiary = _resolve_result(tertiary_raw) if tertiary_raw else None

    dominance_type = _dominance_type(primary.score, supporting.score)
    has_tertiary = _has_tertiary(tertiary)

    return {
        "valuesWheelDescription": _generate_values_description(
            input_data=input_data,
            primary=primary,
            supporting=supporting,
            tertiary=tertiary,
            has_tertiary=has_tertiary,
            dominance_type=dominance_type,
        ),
        "needsWheelDescription": _generate_needs_description(
            input_data=input_data,
            primary=primary,
            supporting=supporting,
            tertiary=tertiary,
            has_tertiary=has_tertiary,
        ),
        "actionProfileDescription": _generate_action_profile_description(
            input_data=input_data,
            primary=primary,
            supporting=supporting,
            tertiary=tertiary,
            has_tertiary=has_tertiary,
            dominance_type=dominance_type,
        ),
    }
