import pytest

from profile_strength_description import (
    aggregateNeedGroups,
    classifyArchetypeIntensity,
    generate_strength_profile_description,
)


ARCHETYPE_ORDER = [
    "Niewinny",
    "Mędrzec",
    "Odkrywca",
    "Kochanek",
    "Towarzysz",
    "Błazen",
    "Bohater",
    "Buntownik",
    "Czarodziej",
    "Opiekun",
    "Twórca",
    "Władca",
]

FEMALE_ARCHETYPE_ORDER = [
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
]


def _payload(
    scores: dict[str, float],
    *,
    primary: str,
    supporting: str,
    tertiary: tuple[str, float] | None = None,
    subject: str = "Miłosława Mirosława",
    label_order: list[str] | None = None,
) -> dict[str, object]:
    labels = label_order or ARCHETYPE_ORDER
    archetypes = [{"label": label, "score": float(scores.get(label, 0.0))} for label in labels]
    tertiary_obj = None
    if tertiary:
        tertiary_obj = {"label": tertiary[0], "score": float(tertiary[1])}
    return {
        "archetypes": archetypes,
        "primary": {"label": primary, "score": float(scores.get(primary, 0.0))},
        "supporting": {"label": supporting, "score": float(scores.get(supporting, 0.0))},
        "tertiary": tertiary_obj,
        "subjectGenitive": subject,
    }


def test_classify_archetype_intensity_boundaries():
    expected = [
        (0, "marginalne natężenie", "marginal"),
        (29, "marginalne natężenie", "marginal"),
        (30, "słabe natężenie", "weak"),
        (49, "słabe natężenie", "weak"),
        (50, "umiarkowane natężenie", "moderate"),
        (59, "umiarkowane natężenie", "moderate"),
        (60, "znaczące natężenie", "significant"),
        (69, "znaczące natężenie", "significant"),
        (70, "wysokie natężenie", "high"),
        (79, "wysokie natężenie", "high"),
        (80, "bardzo wysokie natężenie (rdzeń)", "very_high"),
        (89, "bardzo wysokie natężenie (rdzeń)", "very_high"),
        (90, "ekstremalne natężenie", "extreme"),
        (100, "ekstremalne natężenie", "extreme"),
    ]
    for score, label, band in expected:
        out = classifyArchetypeIntensity(score)
        assert out["label"] == label
        assert out["band"] == band


def test_aggregate_need_groups_uses_mean_for_each_triplet():
    out = aggregateNeedGroups(
        [
            {"label": "Odkrywca", "score": 30},
            {"label": "Buntownik", "score": 60},
            {"label": "Błazen", "score": 90},
            {"label": "Kochanek", "score": 10},
            {"label": "Opiekun", "score": 20},
            {"label": "Towarzysz", "score": 30},
            {"label": "Niewinny", "score": 40},
            {"label": "Władca", "score": 50},
            {"label": "Mędrzec", "score": 60},
            {"label": "Twórca", "score": 70},
            {"label": "Bohater", "score": 80},
            {"label": "Czarodziej", "score": 90},
        ]
    )
    assert out["zmiana"] == pytest.approx(60.0)
    assert out["ludzie"] == pytest.approx(20.0)
    assert out["porzadek"] == pytest.approx(50.0)
    assert out["niezaleznosc"] == pytest.approx(80.0)


def test_profile_a_miloslaw_rozproszony_bez_pobocznego():
    scores = {
        "Opiekun": 50.2,
        "Towarzysz": 48.0,
        "Władca": 46.1,
        "Bohater": 45.7,
        "Mędrzec": 44.8,
        "Niewinny": 44.4,
        "Buntownik": 41.9,
        "Czarodziej": 41.9,
        "Kochanek": 40.7,
        "Twórca": 40.2,
        "Odkrywca": 36.9,
        "Błazen": 35.6,
    }
    txt = generate_strength_profile_description(
        _payload(
            scores,
            primary="Opiekun",
            supporting="Towarzysz",
            tertiary=None,
            subject="Miłosława Mirosława",
        )
    )
    first_paragraph = txt.split("\n\n")[0]
    txt_l = txt.lower()
    assert "umiarkowany" in txt
    assert "rozproszony" in first_paragraph
    assert first_paragraph.lower().count("rozproszony") == 1
    assert "archetypem głównym" in txt_l
    assert "archetypem wspierającym" in txt_l
    assert "Opiekun" in txt
    assert "Towarzysz" in txt
    assert "Ludzie i Porządek" in txt
    assert "Zmiany" in txt
    assert "drugi w kolejności" not in txt_l
    assert "towarzyszy mu jeszcze archetyp" not in txt_l
    assert "napięcie" not in txt_l
    assert "tożsamość" not in txt_l
    assert "osobowość" not in txt_l


def test_profile_b_kornelia_rdzen_i_bliskie_zmiana_ludzie():
    scores = {
        "Kochanka": 64.0,
        "Buntowniczka": 58.0,
        "Odkrywczyni": 62.0,
        "Komiczka": 57.0,
        "Opiekunka": 56.0,
        "Towarzyszka": 55.0,
        "Niewinna": 44.0,
        "Władczyni": 51.0,
        "Mędrczyni": 46.0,
        "Twórczyni": 54.0,
        "Bohaterka": 53.0,
        "Czarodziejka": 52.0,
    }
    txt = generate_strength_profile_description(
        _payload(
            scores,
            primary="Kochanka",
            supporting="Buntowniczka",
            tertiary=None,
            subject="Kornelii Lemańskiej",
            label_order=FEMALE_ARCHETYPE_ORDER,
        )
    )
    txt_l = txt.lower()
    assert "wyraźny" in txt_l
    assert "czytelny rdzeń" in txt_l
    assert "archetypem głównym" in txt_l
    assert "archetypem wspierającym" in txt_l
    assert "Kochanka" in txt
    assert "Buntowniczka" in txt
    assert "Zmiana i Ludzie" in txt
    assert "drugi w kolejności" not in txt_l
    assert "wyraźnie dominuje zmiana" not in txt_l
    assert "wyraźnie przechylony" not in txt_l


def test_profile_c_hetman_trojbiegunowy_bez_degradacji_pobocznego():
    scores = {
        "Bohater": 76.0,
        "Władca": 75.9,
        "Odkrywca": 70.1,
        "Twórca": 58.0,
        "Czarodziej": 60.0,
        "Buntownik": 60.0,
        "Błazen": 59.0,
        "Niewinny": 45.0,
        "Mędrzec": 47.0,
        "Kochanek": 61.0,
        "Opiekun": 62.0,
        "Towarzysz": 60.0,
    }
    txt = generate_strength_profile_description(
        _payload(
            scores,
            primary="Bohater",
            supporting="Władca",
            tertiary=("Odkrywca", 70.1),
            subject="Krzysztofa Hetmana",
        )
    )
    txt_l = txt.lower()
    first_paragraph = txt.split("\n\n")[0].lower()
    assert "silny i trójbiegunowy" in first_paragraph
    assert first_paragraph.count("silny i trójbiegunowy") == 1
    assert "archetypem głównym" in txt_l
    assert "archetypem wspierającym jest" in txt_l
    assert "archetypem pobocznym jest" in txt_l
    assert "wzmacnia profil pobocznie" not in txt_l
    assert "drugi w kolejności" not in txt_l
    assert "Niezależność i Zmiana" in txt
    assert "różnice między czterema grupami nie są duże" in txt_l


def test_profile_d_bardzo_silny_bez_powtorzenia_oceny():
    scores = {
        "Twórca": 82.0,
        "Bohater": 79.0,
        "Czarodziej": 71.0,
        "Władca": 62.0,
        "Mędrzec": 58.0,
        "Opiekun": 54.0,
        "Towarzysz": 46.0,
        "Niewinny": 44.0,
        "Buntownik": 49.0,
        "Kochanek": 45.0,
        "Odkrywca": 60.0,
        "Błazen": 43.0,
    }
    txt = generate_strength_profile_description(
        _payload(
            scores,
            primary="Twórca",
            supporting="Bohater",
            tertiary=("Czarodziej", 71.0),
            subject="Anny Lis",
        )
    )
    first_paragraph = txt.split("\n\n")[0].lower()
    assert "bardzo silny i trójbiegunowy" in first_paragraph
    assert first_paragraph.count("bardzo silny i trójbiegunowy") == 1
    assert "drugi w kolejności" not in first_paragraph
