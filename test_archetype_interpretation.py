from archetype_interpretation import generate_archetype_descriptions


def _result(label: str, score: float) -> dict[str, object]:
    return {"label": label, "score": score}


def _input(primary: dict[str, object], supporting: dict[str, object], tertiary: dict[str, object] | None):
    all_archetypes = [
        primary,
        supporting,
    ]
    if tertiary is not None:
        all_archetypes.append(tertiary)
    return {
        "allArchetypes": all_archetypes,
        "primary": primary,
        "supporting": supporting,
        "tertiary": tertiary,
    }


def test_generator_hero_ruler_without_tertiary():
    descriptions = generate_archetype_descriptions(
        _input(
            primary=_result("Bohater", 76.0),
            supporting=_result("Władca", 75.9),
            tertiary=None,
        )
    )

    values = descriptions["valuesWheelDescription"].lower()
    needs = descriptions["needsWheelDescription"].lower()
    action = descriptions["actionProfileDescription"].lower()

    assert "mistrzostwo" in values
    assert "kontrola" in values
    assert "niezależności" in needs
    assert "stabilności" in needs
    assert "współdominowany" in action
    assert "sprawczości" in action
    assert "niezależności" in action
    assert "dodatkowy ton" not in values
    assert "dodatkowy ton" not in needs
    assert "dodatkowy ton" not in action


def test_generator_lover_companion_caregiver_with_tertiary():
    descriptions = generate_archetype_descriptions(
        _input(
            primary=_result("Kochanka", 88.0),
            supporting=_result("Towarzysz", 72.0),
            tertiary=_result("Opiekunka", 71.0),
        )
    )

    values = descriptions["valuesWheelDescription"].lower()
    needs = descriptions["needsWheelDescription"].lower()
    action = descriptions["actionProfileDescription"].lower()

    assert "intymność" in values
    assert "przynależność" in values
    assert "troska" in values
    assert "po stronie przynależności" in needs
    assert "empatii" in action
    assert "dodatkowy ton wnosi także opiekunka" in action


def test_generator_skips_tertiary_below_threshold():
    descriptions = generate_archetype_descriptions(
        _input(
            primary=_result("Kochanek", 88.0),
            supporting=_result("Towarzysz", 72.0),
            tertiary=_result("Opiekun", 69.9),
        )
    )

    assert "dodatkowy ton" not in descriptions["valuesWheelDescription"].lower()
    assert "dodatkowy akcent" not in descriptions["needsWheelDescription"].lower()
    assert "dodatkowy ton" not in descriptions["actionProfileDescription"].lower()


def test_generator_uses_balanced_phrase_when_axis_is_close_to_zero():
    descriptions = generate_archetype_descriptions(
        _input(
            primary=_result("Opiekun", 80.0),
            supporting=_result("Bohater", 80.0),
            tertiary=None,
        )
    )

    needs = descriptions["needsWheelDescription"].lower()
    assert "bez wyraźnego przechyłu między niezależnością a przynależnością" in needs
    assert "bez wyraźnego przechyłu między zmianą a stabilnością" in needs
