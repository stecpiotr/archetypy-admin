from archetype_interpretation import (
    classifyArchetypeIntensity,
    classifyDimensionBand,
    classifyDimensionStrength,
    generate_archetype_descriptions,
    getNameAwareOpening,
    getPreferredGenitive,
    splitActionDimensionRoles,
)
from public_labels import (
    ARCHETYPE_PUBLIC_VALUES,
    PREFERENCES_P_DISPLAY_BY_INTERNAL_KEY,
    PREFERENCES_P_LABEL_ORDER,
)
import re


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
    assert "potrzebą działania" in txt
    assert "potrzebę ładu" in txt
    assert "o potrzebę autonomii" in txt
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
    assert "łączy niezależność ze stabilnością" in txt
    assert "Bohatera i Władcy" in txt
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
    assert "racjonalność" in txt
    assert "po dołożeniu odkrywcy wyraźniej zaznacza się komponent kreatywności" in txt
    assert "a niezależność pozostaje jednym z głównych filarów tego układu" in txt
    assert "w praktyce daje to profil oparty przede wszystkim na sprawczości i niezależności" in txt
    assert "kreatywność pozostaje obecna w wyraźnym, ale niedominującym stopniu" in txt
    assert "najsłabszym wymiarem pozostaje empatia" in txt
    assert "empatia i kreatywność pozostają słabszymi wymiarami działania" not in txt
    assert "\n\ncałość wzmacnia obraz" in txt
    assert "to wzmacnia obraz" not in txt
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

    assert "jest przede wszystkim zakorzeniony w stabilności" in needs
    assert "z lekkim przechyłem ku niezależności" in needs
    assert "porządkowaniu rzeczywistości, utrzymywaniu kursu i przewidywalności" in needs
    assert "archetypy niewinnego i mędrca" in needs
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
    assert "jest przede wszystkim zakorzeniony w przynależności" in needs
    assert "zrównoważonym układzie na drugiej osi" in needs
    assert "zdecydowanie po stronie stabilności" not in needs
    assert "empatii" in action
    assert "niskiej sprawczości" not in action


def test_6b_odkrywczyni_tworczyni_nie_zawyza_racjonalnosci():
    out = generate_archetype_descriptions(
        _input(
            _result("Odkrywczyni", 90.0),
            _result("Twórczyni", 80.0),
            None,
            subject_forms={"fullGen": "Januszy Kowalskiej"},
        )
    )
    action = out["actionProfileDescription"].lower()
    assert "kreatywności" in action
    assert "niezależności" in action
    assert "racjonalność pozostaje obecna w wyraźnym, ale niedominującym stopniu" in action
    assert "najsłabszym wymiarem pozostaje empatia" in action
    assert "racjonalności pozostających słabszymi wymiarami działania" not in action
    assert "umiarkowanej racjonalności" not in action


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
    assert classifyDimensionBand(48) == "visible_non_dominant"
    assert classifyDimensionBand(28) == "weaker"

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
    assert "wnosi tu Odnowę" in txt_values
    assert "jest przede wszystkim zakorzeniony w zmianie" in txt_needs.lower()
    assert "szukaniu nowych dróg, uruchamianiu ruchu i przełamywaniu stagnacji" in txt_needs
    assert "ale realizowany bardziej w relacji z ludźmi, bliskości i budowaniu wspólnoty niż w samotnej autonomii" in txt_needs
    assert "szukaniu nowych dróg, uruchamianiu ruchu i przełamywaniu stagnacji. Ten kierunek" not in txt_needs
    assert "Rdzeń działania tego układu tworzą Kochanka i Buntowniczka" in txt_action
    assert "Kochanki i Buntowniczki" in txt_needs
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


def test_10_clear_dominant_wartosci_uzywa_wnosi_i_poprawnego_przypadku():
    out = generate_archetype_descriptions(
        _input(
            _result("Odkrywca", 90.0),
            _result("Opiekun", 70.0),
            None,
            subject_forms={"fullGen": "Mściwoja Złego"},
        )
    )
    txt = out["valuesWheelDescription"]
    assert "Archetyp wspierający wnosi tu Troskę" in txt
    assert "dodaje tu Troska" not in txt


def test_11_needs_balanced_x_ma_czasownik_pozostaje():
    out = generate_archetype_descriptions(
        _input(
            _result("Odkrywca", 90.0),
            _result("Opiekun", 70.0),
            None,
            subject_forms={"fullGen": "Mściwoja Złego"},
        )
    )
    txt = out["needsWheelDescription"]
    assert "łączy zmianę z przynależnością" in txt


def test_12_dominant_with_support_ma_naturalne_otwarcie_i_wartosc_publiczna():
    out = generate_archetype_descriptions(
        _input(
            _result("Kochanka", 88.0),
            _result("Buntowniczka", 80.0),
            None,
            subject_forms={"fullGen": "Kornelii Lemańskiej"},
        )
    )
    txt_values = out["valuesWheelDescription"]
    txt_action = out["actionProfileDescription"]
    assert "na wartości Relacje" in txt_values
    assert "wzmacnianej przez Odnowę" in txt_values
    assert "Rdzeń działania Kornelii Lemańskiej tworzą Kochanka i Buntowniczka" in txt_action


def test_13_buntownik_top_empatia_sprawczosc_ma_mocniejsza_puente():
    out = generate_archetype_descriptions(
        _input(
            _result("Buntownik", 90.0),
            _result("Towarzysz", 85.0),
            _result("Opiekun", 75.0),
            subject_forms={"fullGen": "Mściwoja Pokemona"},
        )
    )
    txt_action = out["actionProfileDescription"]
    assert "przywództwa wyrazistego, społecznie zakorzenionego" in txt_action
    assert "gotowego przekuwać energię zmiany w konkretne działanie" in txt_action
    assert "\n\nCałość wzmacnia obraz" in txt_action
    assert " To wzmacnia obraz" not in txt_action


def test_14_bohater_wladca_bez_top3_ma_empatie_i_kreatywnosc_jako_slabsze():
    out = generate_archetype_descriptions(
        _input(
            _result("Bohater", 76.0),
            _result("Władca", 75.9),
            None,
            subject_forms={"fullGen": "Krzysztofa Hetmana"},
        )
    )
    txt_action = out["actionProfileDescription"].lower()
    assert "najsłabszym wymiarem pozostaje empatia" in txt_action
    assert "kreatywność pozostaje słabszym wymiarem działania" in txt_action
    assert "\n\ncałość wzmacnia obraz" in txt_action
    assert "to wzmacnia obraz" not in txt_action


def test_15_top3_zmienia_opis_wiecej_niz_o_dopisek_o_trzecim_archetypie():
    out_2 = generate_archetype_descriptions(
        _input(
            _result("Bohater", 76.0),
            _result("Władca", 75.9),
            None,
            subject_forms={"fullGen": "Krzysztofa Hetmana"},
        )
    )
    out = generate_archetype_descriptions(
        _input(
            _result("Bohater", 76.0),
            _result("Władca", 75.9),
            _result("Odkrywca", 70.1),
            subject_forms={"fullGen": "Krzysztofa Hetmana"},
        )
    )
    txt_2 = out_2["actionProfileDescription"]
    txt_3 = out["actionProfileDescription"]
    assert "Dodatkowy ton wnosi Odkrywca." in txt_3
    assert "po dołożeniu odkrywcy wyraźniej zaznacza się komponent kreatywności" in txt_3.lower()
    assert "a niezależność pozostaje jednym z głównych filarów tego układu" in txt_3.lower()
    assert "kreatywność pozostaje słabszym wymiarem działania" in txt_2.lower()
    assert "kreatywność pozostaje obecna w wyraźnym, ale niedominującym stopniu" in txt_3.lower()
    assert "dodatkowym ważnym komponentem pozostaje racjonalność" in txt_3.lower()
    assert "to wzmacnia obraz" not in txt_3.lower()
    assert "\n\ncałość wzmacnia obraz" in txt_3.lower()
    assert txt_3.replace(" Dodatkowy ton wnosi Odkrywca.", "") != txt_2


def test_16_niewinny_medrzec_tworca_rozdziela_role_wymiarow_bez_dublowania():
    out = generate_archetype_descriptions(
        _input(
            _result("Niewinny", 82.0),
            _result("Mędrzec", 79.0),
            _result("Twórca", 71.0),
            subject_forms={"fullGen": "Emila Steca"},
        )
    )
    txt = out["actionProfileDescription"]
    txt_l = txt.lower()
    assert "oparty przede wszystkim na niezależności i racjonalności" in txt_l
    assert "dodatkowymi ważnymi komponentami pozostają sprawczość i kreatywność" in txt_l
    assert "przy solidnym wsparciu niezależności, racjonalności" not in txt_l
    assert "empatia pozostaje obecna w wyraźnym, ale niedominującym stopniu" in txt_l
    assert "\n\nCałość wzmacnia obraz" in txt


def test_17_split_action_dimension_roles_jest_rozlaczny_i_bez_duplikatow():
    roles = splitActionDimensionRoles(
        {
            "empatia": 44.03,
            "sprawczosc": 57.39,
            "racjonalnosc": 62.26,
            "niezaleznosc": 62.33,
            "kreatywnosc": 56.96,
        }
    )

    assert roles["dominantDims"] == ["niezaleznosc", "racjonalnosc"]
    assert roles["supportingDims"] == ["sprawczosc", "kreatywnosc"]
    assert roles["visibleButNonDominantDims"] == ["empatia"]
    assert roles["weakestDims"] == []

    all_dims = (
        roles["dominantDims"]
        + roles["supportingDims"]
        + roles["visibleButNonDominantDims"]
        + roles["weakestDims"]
    )
    assert len(all_dims) == len(set(all_dims))


def test_18_redakcyjny_brak_urwanych_pseudo_zdan():
    cases = [
        _input(
            _result("Niewinny", 82.0),
            _result("Mędrzec", 79.0),
            _result("Twórca", 71.0),
            subject_forms={"fullGen": "Emila Steca"},
        ),
        _input(
            _result("Bohater", 76.0),
            _result("Władca", 75.9),
            _result("Odkrywca", 70.1),
            subject_forms={"fullGen": "Krzysztofa Hetmana"},
        ),
    ]
    forbidden_starts = re.compile(r"(?:^|[.\n]\s*)(Z |Przy |Oraz |Podczas gdy )", flags=re.IGNORECASE)

    for payload in cases:
        txt = generate_archetype_descriptions(payload)["actionProfileDescription"]
        assert forbidden_starts.search(txt) is None


def test_19_emil_i_hetman_drugi_akapit_ma_pelne_zdanie_syntetyzujace():
    emil = generate_archetype_descriptions(
        _input(
            _result("Niewinny", 82.0),
            _result("Mędrzec", 79.0),
            _result("Twórca", 71.0),
            subject_forms={"fullGen": "Emila Steca"},
        )
    )["actionProfileDescription"]
    hetman = generate_archetype_descriptions(
        _input(
            _result("Bohater", 76.0),
            _result("Władca", 75.9),
            _result("Odkrywca", 70.1),
            subject_forms={"fullGen": "Krzysztofa Hetmana"},
        )
    )["actionProfileDescription"]

    emil_parts = [p.strip() for p in emil.split("\n\n") if p.strip()]
    hetman_parts = [p.strip() for p in hetman.split("\n\n") if p.strip()]
    assert len(emil_parts) >= 2
    assert len(hetman_parts) >= 2
    assert emil_parts[1].startswith("Całość wzmacnia")
    assert hetman_parts[1].startswith("Całość wzmacnia")


def test_20_kolo_potrzeb_hierarchia_stabilnosc_ma_pierwszenstwo_nad_centroidem_emil():
    out = generate_archetype_descriptions(
        _input(
            _result("Niewinny", 82.0),
            _result("Mędrzec", 79.0),
            _result("Twórca", 71.0),
            subject_forms={"fullGen": "Emila Steca"},
        )
    )
    txt = out["needsWheelDescription"].lower()
    assert txt.startswith("układ potrzeb emila steca jest przede wszystkim zakorzeniony w stabilności")
    assert "z lekkim przechyłem ku niezależności" in txt
    assert "układ potrzeb emila steca lekko ciąży ku niezależności" not in txt


def test_21_kolo_potrzeb_hierarchia_para_niezaleznosc_stabilnosc_hetman():
    out = generate_archetype_descriptions(
        _input(
            _result("Bohater", 76.0),
            _result("Władca", 75.9),
            _result("Odkrywca", 70.1),
            subject_forms={"fullGen": "Krzysztofa Hetmana"},
        )
    )
    txt = out["needsWheelDescription"].lower()
    assert "łączy niezależność ze stabilnością" in txt
    assert "zakorzeniony w zmianie" not in txt
    assert "a dodatkowy akcent wnosi odkrywca" in txt


def test_22_kolo_wartosci_hierarchia_rdzen_glowny_plus_wspierajacy_hetman():
    out = generate_archetype_descriptions(
        _input(
            _result("Bohater", 76.0),
            _result("Władca", 75.9),
            _result("Odkrywca", 70.1),
            subject_forms={"fullGen": "Krzysztofa Hetmana"},
        )
    )
    txt = out["valuesWheelDescription"]
    assert "duet: Odwaga i Porządek" in txt
    assert "Dodatkowy ton wnosi tu także Wolność" in txt


def test_23_kolo_potrzeb_kornelia_zachowuje_styl_glownego_archetypu():
    out = generate_archetype_descriptions(
        _input(
            _result("Kochanka", 88.0),
            _result("Buntowniczka", 80.0),
            None,
            subject_forms={"fullGen": "Kornelii Lemańskiej"},
        )
    )
    txt = out["needsWheelDescription"]
    txt_l = txt.lower()

    assert txt.startswith(
        "Układ potrzeb Kornelii Lemańskiej jest przede wszystkim zakorzeniony w zmianie, z wyraźnym przechyłem ku przynależności."
    )
    assert "styl działania oparty na szukaniu nowych dróg, uruchamianiu ruchu i przełamywaniu stagnacji" in txt_l
    assert "ale realizowany bardziej w relacji z ludźmi, bliskości i budowaniu wspólnoty niż w samotnej autonomii" in txt_l
    assert "archetypy kochanki i buntowniczki" in txt_l
