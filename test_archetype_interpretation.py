from archetype_interpretation import (
    classifyArchetypeIntensity,
    classifyDimensionStrength,
    generate_archetype_descriptions,
    getNameAwareOpening,
    getPreferredGenitive,
)
from public_labels import (
    ARCHETYPE_PUBLIC_VALUES,
    PREFERENCES_P_DISPLAY_BY_INTERNAL_KEY,
    PREFERENCES_P_LABEL_ORDER,
)


def _result(label: str, score: float) -> dict[str, object]:
    return {"label": label, "score": score}


def _input(
    primary: dict[str, object],
    supporting: dict[str, object],
    tertiary: dict[str, object] | None,
    *,
    subject_forms: dict[str, object] | None = None,
    person_genitive: str | None = None,
) -> dict[str, object]:
    all_archetypes = [primary, supporting]
    if tertiary is not None:
        all_archetypes.append(tertiary)
    payload: dict[str, object] = {
        "allArchetypes": all_archetypes,
        "primary": primary,
        "supporting": supporting,
        "tertiary": tertiary,
    }
    if subject_forms is not None:
        payload["subjectForms"] = subject_forms
    if person_genitive:
        payload["personGenitive"] = person_genitive
    return payload


def test_1_interpreter_natezenia_archetypu():
    expected = [
        (22, "marginalne natężenie", "marginal"),
        (41, "słabe natężenie", "weak"),
        (55, "umiarkowane natężenie", "moderate"),
        (67, "znaczące natężenie", "significant"),
        (76, "wysokie natężenie", "high"),
        (84, "bardzo wysokie natężenie (rdzeń)", "very_high"),
        (93, "ekstremalne natężenie", "extreme"),
    ]
    for score, label, band in expected:
        out = classifyArchetypeIntensity(score)
        assert out["label"] == label
        assert out["band"] == band


def test_2_kolo_pragnien_i_wartosci_bohater_wladca_odkrywca():
    out = generate_archetype_descriptions(
        _input(
            _result("Bohater", 76.0),
            _result("Władca", 75.9),
            _result("Odkrywca", 70.1),
            subject_forms={"fullGen": "Krzysztofa Hetmana"},
        )
    )
    txt = out["valuesWheelDescription"]
    assert "Odwaga" in txt
    assert "Porządek" in txt
    assert "Wolność" in txt
    assert "mistrzostwo" not in txt.lower()
    assert "kontrola" not in txt.lower()


def test_3_kolo_potrzeb_bohater_wladca_odkrywca():
    out = generate_archetype_descriptions(
        _input(
            _result("Bohater", 76.0),
            _result("Władca", 75.9),
            _result("Odkrywca", 70.1),
            subject_forms={"fullGen": "Krzysztofa Hetmana"},
        )
    )
    txt = out["needsWheelDescription"]
    assert "niezależności" in txt
    assert "stabilności" in txt
    assert "Bohater i Władca" in txt
    assert "napięcie" not in txt.lower()


def test_4_profil_dzialania_bohater_wladca_odkrywca():
    out = generate_archetype_descriptions(
        _input(
            _result("Bohater", 76.0),
            _result("Władca", 75.9),
            _result("Odkrywca", 70.1),
            subject_forms={"fullGen": "Krzysztofa Hetmana"},
        )
    )
    txt = out["actionProfileDescription"].lower()
    assert "sprawczości" in txt
    assert "niezależności" in txt
    assert "umiarkowanej racjonalności" not in txt
    assert "bardzo niskiej kreatywności" not in txt


def test_5_niewinny_medrzec_tworca():
    out = generate_archetype_descriptions(
        _input(
            _result("Niewinny", 82.0),
            _result("Mędrzec", 79.0),
            _result("Twórca", 71.0),
            subject_forms={"fullGen": "Emila Steca"},
        )
    )
    needs = out["needsWheelDescription"].lower()
    action = out["actionProfileDescription"].lower()

    assert "lekko ciąży ku niezależności" in needs
    assert "z lekkim przechyłem ku stabilności" in needs
    assert "racjonalności" in action
    assert "niskiej empatii" not in action
    assert "umiarkowanej racjonalności" not in action


def test_6_opiekunka_niewinna_odkrywczyni():
    out = generate_archetype_descriptions(
        _input(
            _result("Opiekunka", 87.0),
            _result("Niewinna", 79.0),
            _result("Odkrywczyni", 70.0),
            subject_forms={"fullGen": "Emilii Oszust"},
        )
    )
    needs = out["needsWheelDescription"].lower()
    action = out["actionProfileDescription"].lower()
    assert "przynależności" in needs
    assert "stabilności" in needs
    assert "zdecydowanie po stronie stabilności" not in needs
    assert "empatii" in action
    assert "niskiej sprawczości" not in action


def test_7_personalizacja_pojawia_sie_maksymalnie_raz_w_opisie():
    forms = {"fullGen": "Krzysztofa Hetmana", "surnameGen": "Hetmana"}
    out = generate_archetype_descriptions(
        _input(
            _result("Bohater", 76.0),
            _result("Władca", 75.9),
            _result("Odkrywca", 70.1),
            subject_forms=forms,
        )
    )
    assert out["valuesWheelDescription"].count("Krzysztofa Hetmana") <= 1
    assert out["needsWheelDescription"].count("Krzysztofa Hetmana") <= 1
    assert out["actionProfileDescription"].count("Krzysztofa Hetmana") <= 1
    assert out["valuesWheelDescription"].startswith("Rdzeń motywacyjny Krzysztofa Hetmana")


def test_8_fallback_personalizacji_i_helpery():
    assert getPreferredGenitive({"fullGen": "Krzysztofa Hetmana", "surnameGen": "Hetmana"}) == "Krzysztofa Hetmana"
    assert getPreferredGenitive({"surnameGen": "Hetmana"}) == "Hetmana"
    assert getPreferredGenitive({}) is None
    assert getNameAwareOpening("needs", None) == "Układ potrzeb tego wyniku"
    assert classifyDimensionStrength(88)["band"] == "very_high"
    assert classifyDimensionStrength(52)["band"] == "mid"
    assert classifyDimensionStrength(27)["band"] == "low"

    out = generate_archetype_descriptions(
        _input(
            _result("Kochanka", 88.0),
            _result("Buntowniczka", 72.0),
            None,
        )
    )
    txt_values = out["valuesWheelDescription"]
    txt_needs = out["needsWheelDescription"]
    txt_action = out["actionProfileDescription"]
    assert "tego układu" in txt_values
    assert "tego wyniku" in txt_needs
    assert "tego układu" in txt_action
    assert "None" not in txt_values + txt_needs + txt_action


def test_9_wykres_preferencji_wartosci_publiczne_etykiety():
    assert ARCHETYPE_PUBLIC_VALUES["Mędrzec"] == "Rozsądek"
    assert ARCHETYPE_PUBLIC_VALUES["Władca"] == "Porządek"
    assert PREFERENCES_P_DISPLAY_BY_INTERNAL_KEY["racjonalnosc"] == "Rozsądek"
    assert PREFERENCES_P_DISPLAY_BY_INTERNAL_KEY["skutecznosc"] == "Porządek"
    assert "Rozsądek" in PREFERENCES_P_LABEL_ORDER
    assert "Porządek" in PREFERENCES_P_LABEL_ORDER
    assert "Racjonalność" not in PREFERENCES_P_LABEL_ORDER
    assert "Skuteczność" not in PREFERENCES_P_LABEL_ORDER
