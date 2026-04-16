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


class InputData(TypedDict):
    allArchetypes: list[ArchetypeResult]
    primary: ArchetypeResult
    supporting: ArchetypeResult
    tertiary: ArchetypeResult | None


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


DIM_LABELS_LOC = {
    "empatia": "empatii",
    "sprawczosc": "sprawczości",
    "racjonalnosc": "racjonalności",
    "niezaleznosc": "niezależności",
    "kreatywnosc": "kreatywności",
}

DIM_LABELS_ACC = {
    "empatia": "empatię",
    "sprawczosc": "sprawczość",
    "racjonalnosc": "racjonalność",
    "niezaleznosc": "niezależność",
    "kreatywnosc": "kreatywność",
}

DIM_LABELS_INS = {
    "empatia": "empatią",
    "sprawczosc": "sprawczością",
    "racjonalnosc": "racjonalnością",
    "niezaleznosc": "niezależnością",
    "kreatywnosc": "kreatywnością",
}


PAIR_INTERPRETATION: dict[str, str] = {
    "sprawczosc+niezaleznosc": "To wzmacnia obraz lidera decyzyjnego, samodzielnego i odpowiedzialnego za wynik.",
    "sprawczosc+racjonalnosc": "To wzmacnia obraz lidera rzeczowego, uporządkowanego i zdolnego przekładać diagnozę na działanie.",
    "empatia+sprawczosc": "To wzmacnia obraz lidera, który łączy troskę z realnym działaniem.",
    "empatia+kreatywnosc": "To wzmacnia obraz lidera relacyjnego, atrakcyjnego komunikacyjnie i łatwo budującego zaangażowanie.",
    "niezaleznosc+kreatywnosc": "To wzmacnia obraz lidera reformującego, który szuka nowych dróg i nie boi się wychodzić poza schemat.",
    "racjonalnosc+niezaleznosc": "To wzmacnia obraz lidera samodzielnego strategicznie, bardziej ufającego własnemu osądowi niż presji otoczenia.",
    "racjonalnosc+kreatywnosc": "To wzmacnia obraz lidera wizjonerskiego, który łączy wyobraźnię z myśleniem systemowym.",
    "empatia+racjonalnosc": "To wzmacnia obraz lidera rozważnego i społecznie uważnego.",
    "empatia+niezaleznosc": "To wzmacnia obraz lidera wyrazistego, ale nadal zakorzenionego w potrzebach ludzi.",
    "sprawczosc+kreatywnosc": "To wzmacnia obraz lidera, który nie tylko wymyśla zmianę, ale potrafi ją uruchomić.",
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


def _phrase_instrumental(value_phrase: str) -> str:
    prefix = "potrzeba "
    if value_phrase.startswith(prefix):
        return "potrzebą " + value_phrase[len(prefix):]
    return value_phrase


def _phrase_accusative(value_phrase: str) -> str:
    prefix = "potrzeba "
    if value_phrase.startswith(prefix):
        return "potrzebę " + value_phrase[len(prefix):]
    return value_phrase


def _phrase_locative(value_phrase: str) -> str:
    prefix = "potrzeba "
    if value_phrase.startswith(prefix):
        return "potrzebie " + value_phrase[len(prefix):]
    return value_phrase


def _axis_strength(value: float) -> str:
    abs_value = abs(value)
    if abs_value < 0.18:
        return "balanced"
    if abs_value < 0.45:
        return "soft"
    if abs_value < 0.75:
        return "clear"
    return "strong"


def _axis_x_description(x: float) -> str:
    strength = _axis_strength(x)
    if strength == "balanced":
        return "bez wyraźnego przechyłu między niezależnością a przynależnością"
    if x < 0:
        return {
            "soft": "lekko po stronie niezależności",
            "clear": "wyraźnie po stronie niezależności",
            "strong": "zdecydowanie po stronie niezależności",
        }[strength]
    return {
        "soft": "lekko po stronie przynależności",
        "clear": "wyraźnie po stronie przynależności",
        "strong": "zdecydowanie po stronie przynależności",
    }[strength]


def _axis_y_description(y: float) -> str:
    strength = _axis_strength(y)
    if strength == "balanced":
        return "bez wyraźnego przechyłu między zmianą a stabilnością"
    if y < 0:
        return {
            "soft": "lekko po stronie stabilności",
            "clear": "wyraźnie po stronie stabilności",
            "strong": "zdecydowanie po stronie stabilności",
        }[strength]
    return {
        "soft": "lekko po stronie zmiany",
        "clear": "wyraźnie po stronie zmiany",
        "strong": "zdecydowanie po stronie zmiany",
    }[strength]


def _axis_x_meaning(x: float) -> str:
    if _axis_strength(x) == "balanced":
        return "łączeniu samodzielności z pracą relacyjną"
    if x < 0:
        return "samodzielnym podejmowaniu decyzji i przejmowaniu odpowiedzialności za kierunek"
    return "budowaniu relacji, wspólnoty i dostrajaniu się do ludzi"


def _axis_y_meaning(y: float) -> str:
    if _axis_strength(y) == "balanced":
        return "łączeniu porządkowania z gotowością do zmiany"
    if y < 0:
        return "utrzymywaniu kursu, porządkowaniu działań i przewidywalności"
    return "uruchamianiu ruchu, reformie i testowaniu nowych rozwiązań"


def _generate_values_description(
    primary: _ResolvedResult,
    supporting: _ResolvedResult,
    tertiary: _ResolvedResult | None,
    has_tertiary: bool,
    dominance_type: str,
) -> str:
    primary_meta = ARCHETYPE_META[primary.id]
    supporting_meta = ARCHETYPE_META[supporting.id]
    primary_phrase_inst = _phrase_instrumental(primary_meta["valuePhrase"])
    primary_phrase_acc = _phrase_accusative(primary_meta["valuePhrase"])
    primary_phrase_loc = _phrase_locative(primary_meta["valuePhrase"])
    supporting_phrase_acc = _phrase_accusative(supporting_meta["valuePhrase"])

    if dominance_type == "co_dominant":
        text = (
            f"Rdzeń motywacyjny tego profilu tworzy niemal równorzędny duet: {primary_meta['valueKey']} i {supporting_meta['valueKey']}. "
            f"Oznacza to przywództwo napędzane przede wszystkim {primary_phrase_inst}, wzmacniane przez {supporting_phrase_acc}."
        )
    elif dominance_type == "dominant_with_strong_support":
        text = (
            f"Rdzeń tego profilu opiera się przede wszystkim na {primary_phrase_loc}, wyraźnie wzmacnianej przez {supporting_phrase_acc}. "
            f"W praktyce oznacza to styl budowany na {primary_phrase_acc}, z dodatkowym akcentem na {supporting_phrase_acc}."
        )
    else:
        text = (
            f"W tym profilu główną wartością jest {primary_meta['valueKey']}. "
            f"Archetyp wspierający wnosi {supporting_meta['valueKey']}, ale to {primary_meta['valueKey']} pozostaje głównym źródłem energii i kierunku działania."
        )

    if has_tertiary and tertiary is not None:
        tertiary_meta = ARCHETYPE_META[tertiary.id]
        tertiary_phrase_acc = _phrase_accusative(tertiary_meta["valuePhrase"])
        text += f" Dodatkowy ton wnosi tu także {tertiary_meta['valueKey']}, poszerzając profil o {tertiary_phrase_acc}."

    return text


def _generate_needs_description(
    primary: _ResolvedResult,
    supporting: _ResolvedResult,
    tertiary: _ResolvedResult | None,
    has_tertiary: bool,
) -> str:
    active = [primary, supporting] + ([tertiary] if has_tertiary and tertiary is not None else [])
    total = sum(item.score for item in active) or 1.0

    x = sum(item.score * ARCHETYPE_META[item.id]["needsX"] for item in active) / total
    y = sum(item.score * ARCHETYPE_META[item.id]["needsY"] for item in active) / total

    text = (
        f"Profil układa się {_axis_x_description(x)} oraz {_axis_y_description(y)}. "
        f"Oznacza to styl działania bardziej oparty na {_axis_x_meaning(x)} oraz {_axis_y_meaning(y)} niż na przeciwnej logice. "
        f"Ten kierunek budują przede wszystkim archetypy {primary.label} i {supporting.label}"
    )

    if has_tertiary and tertiary is not None:
        text += f", a dodatkowy akcent wnosi {tertiary.label}."
    else:
        text += "."
    return text


def _dominance_opening(
    primary: _ResolvedResult,
    supporting: _ResolvedResult,
    dominance_type: str,
) -> str:
    female_labels_norm = {
        _normalize_label("Niewinna"),
        _normalize_label("Mędrczyni"),
        _normalize_label("Odkrywczyni"),
        _normalize_label("Kochanka"),
        _normalize_label("Towarzyszka"),
        _normalize_label("Komiczka"),
        _normalize_label("Bohaterka"),
        _normalize_label("Buntowniczka"),
        _normalize_label("Czarodziejka"),
        _normalize_label("Opiekunka"),
        _normalize_label("Twórczyni"),
        _normalize_label("Władczyni"),
    }
    pronoun = "ją" if _normalize_label(primary.label) in female_labels_norm else "go"

    if dominance_type == "co_dominant":
        return f"Profil jest współdominowany przez archetypy {primary.label} i {supporting.label}."
    if dominance_type == "dominant_with_strong_support":
        return f"Profil główny buduje {primary.label}, a wyraźnie wzmacnia {pronoun} {supporting.label}."
    return f"Profil główny buduje {primary.label}, a {supporting.label} pełni rolę wspierającą."


def _pair_interpretation(dim_a: str, dim_b: str) -> str:
    key = f"{dim_a}+{dim_b}"
    reverse_key = f"{dim_b}+{dim_a}"
    text = PAIR_INTERPRETATION.get(key) or PAIR_INTERPRETATION.get(reverse_key)
    if text:
        return text
    return (
        f"To daje profil, który łączy {DIM_LABELS_ACC[dim_a]} z {DIM_LABELS_INS[dim_b]} i dzięki temu działa "
        "w sposób wyraźny oraz rozpoznawalny."
    )


def _generate_action_profile_description(
    primary: _ResolvedResult,
    supporting: _ResolvedResult,
    tertiary: _ResolvedResult | None,
    has_tertiary: bool,
    dominance_type: str,
) -> str:
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
    low_dim_1 = sorted_dims[-1][0]
    low_dim_2 = sorted_dims[-2][0]

    text = _dominance_opening(primary, supporting, dominance_type)
    if has_tertiary and tertiary is not None:
        text += f" Dodatkowy ton wnosi także {tertiary.label}."
    text += (
        f" W praktyce daje to układ oparty przede wszystkim na {DIM_LABELS_LOC[top_dim_1]} i {DIM_LABELS_LOC[top_dim_2]}, "
        f"przy słabszym nacisku na {DIM_LABELS_ACC[low_dim_1]} i {DIM_LABELS_ACC[low_dim_2]}."
    )
    text += f" {_pair_interpretation(top_dim_1, top_dim_2)}"
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
            primary=primary,
            supporting=supporting,
            tertiary=tertiary,
            has_tertiary=has_tertiary,
            dominance_type=dominance_type,
        ),
        "needsWheelDescription": _generate_needs_description(
            primary=primary,
            supporting=supporting,
            tertiary=tertiary,
            has_tertiary=has_tertiary,
        ),
        "actionProfileDescription": _generate_action_profile_description(
            primary=primary,
            supporting=supporting,
            tertiary=tertiary,
            has_tertiary=has_tertiary,
            dominance_type=dominance_type,
        ),
    }
