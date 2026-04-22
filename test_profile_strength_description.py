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


def _payload(
    scores: dict[str, float],
    *,
    primary: str,
    supporting: str,
    tertiary: tuple[str, float] | None = None,
    subject: str = "Miłosława Mirosława",
) -> dict[str, object]:
    archetypes = [{"label": label, "score": float(scores.get(label, 0.0))} for label in ARCHETYPE_ORDER]
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
    assert "umiarkowany" in txt
    assert "rozproszony" in txt
    assert "Opiekun" in txt
    assert "Towarzysz" in txt
    assert "Ludzie i Porządek" in txt
    assert "Zmiana" in txt
    assert "Towarzyszy mu jeszcze archetyp" not in txt
    assert "napięcie" not in txt.lower()
    assert "tożsamość" not in txt.lower()
    assert "osobowość" not in txt.lower()


def test_profile_b_silny_top1_ge_70_and_no_tertiary_below_70():
    scores = {
        "Opiekun": 74.0,
        "Towarzysz": 61.0,
        "Władca": 69.4,
        "Bohater": 55.0,
        "Mędrzec": 50.0,
        "Niewinny": 48.0,
        "Buntownik": 45.0,
        "Czarodziej": 43.0,
        "Kochanek": 46.0,
        "Twórca": 47.0,
        "Odkrywca": 42.0,
        "Błazen": 40.0,
    }
    txt = generate_strength_profile_description(
        _payload(
            scores,
            primary="Opiekun",
            supporting="Towarzysz",
            tertiary=("Władca", 69.4),
            subject="Adama Krawca",
        )
    )
    assert "silny" in txt
    assert "rdzeń" in txt.lower()
    assert "Towarzyszy mu jeszcze archetyp Władca" not in txt


def test_profile_c_dwubiegunowy_when_top1_top2_are_close():
    scores = {
        "Bohater": 67.0,
        "Władca": 64.0,
        "Mędrzec": 58.0,
        "Opiekun": 52.0,
        "Towarzysz": 50.0,
        "Niewinny": 47.0,
        "Buntownik": 42.0,
        "Czarodziej": 40.0,
        "Kochanek": 39.0,
        "Twórca": 45.0,
        "Odkrywca": 41.0,
        "Błazen": 38.0,
    }
    txt = generate_strength_profile_description(
        _payload(
            scores,
            primary="Bohater",
            supporting="Władca",
            tertiary=None,
            subject="Jana Nowaka",
        )
    )
    assert "dwubiegunowy" in txt
    assert "trójbiegunowy" not in txt


def test_profile_d_trojbiegunowy_when_top3_ge_70():
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
    assert "trójbiegunowy" in txt
    assert "Towarzyszy mu jeszcze archetyp Czarodziej" in txt
    assert "wzmacnia profil pobocznie" in txt
