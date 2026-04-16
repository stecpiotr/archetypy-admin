from archetype_interpretation import generate_archetype_descriptions


def _result(label: str, score: float) -> dict[str, object]:
    return {"label": label, "score": score}


def _input(
    primary: dict[str, object],
    supporting: dict[str, object],
    tertiary: dict[str, object] | None,
    person_genitive: str = "Kornelii Lemańskiej",
):
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


def test_values_description_is_natural_for_kochanka_buntowniczka():
    descriptions = generate_archetype_descriptions(
        _input(
            primary=_result("Kochanka", 88.0),
            supporting=_result("Buntowniczka", 72.0),
            tertiary=None,
        )
    )

    values = descriptions["valuesWheelDescription"]
    assert values.startswith("Rdzeń motywacyjny")
    assert "na relacjach" in values
    assert "wzmacnianych przez odnowę" in values
    assert "na intymność" not in values


def test_action_description_has_correct_feminine_form():
    descriptions = generate_archetype_descriptions(
        _input(
            primary=_result("Kochanka", 88.0),
            supporting=_result("Buntowniczka", 72.0),
            tertiary=None,
        )
    )

    action = descriptions["actionProfileDescription"]
    assert "Kochanka" in action
    assert "wzmacniana przez Buntowniczkę" in action


def test_no_tertiary_mention_when_score_is_below_threshold():
    descriptions = generate_archetype_descriptions(
        _input(
            primary=_result("Bohater", 88.0),
            supporting=_result("Władca", 82.0),
            tertiary=_result("Odkrywca", 69.9),
            person_genitive="Jana Kowalskiego",
        )
    )

    assert "dodatkowy ton wnosi" not in descriptions["valuesWheelDescription"].lower()
    assert "dodatkowy ton wnosi" not in descriptions["actionProfileDescription"].lower()


def test_balanced_axis_phrase_is_used():
    descriptions = generate_archetype_descriptions(
        _input(
            primary=_result("Opiekun", 80.0),
            supporting=_result("Bohater", 80.0),
            tertiary=None,
            person_genitive="Anny Nowak",
        )
    )

    needs = descriptions["needsWheelDescription"].lower()
    assert "równowagi między niezależnością a przynależnością" in needs
