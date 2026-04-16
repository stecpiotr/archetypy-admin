from archetype_interpretation import generate_archetype_descriptions


def _result(label: str, score: float) -> dict[str, object]:
    return {"label": label, "score": score}


def _input(
    primary: dict[str, object],
    supporting: dict[str, object],
    tertiary: dict[str, object] | None,
    person_genitive: str = "Jana Testowego",
) -> dict[str, object]:
    all_archetypes = [primary, supporting]
    if tertiary is not None:
        all_archetypes.append(tertiary)
    return {
        "allArchetypes": all_archetypes,
        "primary": primary,
        "supporting": supporting,
        "tertiary": tertiary,
        "personGenitive": person_genitive,
    }


def test_values_section_has_report_opening_and_personalization():
    out = generate_archetype_descriptions(
        _input(_result("Towarzysz", 83.0), _result("Błazen", 78.0), None, "Janusza Testowego")
    )
    txt = out["valuesWheelDescription"]
    assert txt.startswith("Rdzeń motywacyjny Janusza Testowego")
    assert "potrzebie" in txt


def test_needs_section_has_direction_logic_and_named_archetypes():
    out = generate_archetype_descriptions(
        _input(_result("Odkrywca", 86.0), _result("Opiekun", 79.0), None, "Mściwoja Złego")
    )
    txt = out["needsWheelDescription"]
    assert "Układ potrzeb Mściwoja Złego" in txt
    assert "Ten kierunek budują przede wszystkim archetypy Odkrywca i Opiekun." in txt


def test_action_section_keeps_feminine_grammar():
    out = generate_archetype_descriptions(
        _input(_result("Kochanka", 88.0), _result("Buntowniczka", 72.0), None, "Kornelii Lemańskiej")
    )
    txt = out["actionProfileDescription"]
    assert "Kochanka" in txt
    assert "wzmacniana przez Buntowniczkę" in txt


def test_tertiary_below_threshold_is_not_mentioned():
    out = generate_archetype_descriptions(
        _input(_result("Bohater", 88.0), _result("Władca", 82.0), _result("Odkrywca", 69.9), "Jana Kowalskiego")
    )
    assert "Dodatkowy ton" not in out["valuesWheelDescription"]
    assert "Dodatkowy ton" not in out["actionProfileDescription"]


def test_tertiary_above_threshold_is_mentioned():
    out = generate_archetype_descriptions(
        _input(_result("Bohater", 88.0), _result("Władca", 82.0), _result("Odkrywca", 71.0), "Jana Kowalskiego")
    )
    assert "Dodatkowy ton wnosi" in out["valuesWheelDescription"]
    assert "Dodatkowy ton wnosi" in out["actionProfileDescription"]
