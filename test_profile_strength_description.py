import pytest

from profile_strength_description import (
    aggregateNeedGroups,
    classifyArchetypeIntensity,
    classify_profile_strength,
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
    assert ("umiarkowany" in first_paragraph.lower()) or ("słabo zarysowany" in first_paragraph.lower())
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
        "Odkrywczyni": 57.0,
        "Komiczka": 54.0,
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
    assert ("Zmiana i Ludzie" in txt) or ("Ludzie i Zmiana" in txt)
    assert "drugi w kolejności" not in txt_l
    assert "wyraźnie dominuje zmiana" not in txt_l
    assert "wyraźnie przechylony" not in txt_l


def test_profile_c_hetman_dwubiegunowy_dwa_archetypy():
    scores = {
        "Buntownik": 53.0,
        "Błazen": 54.0,
        "Kochanek": 67.0,
        "Opiekun": 65.0,
        "Towarzysz": 57.0,
        "Niewinny": 54.0,
        "Władca": 76.0,
        "Mędrzec": 62.0,
        "Czarodziej": 67.0,
        "Bohater": 76.0,
        "Twórca": 57.0,
        "Odkrywca": 66.0,
    }
    txt = generate_strength_profile_description(
        _payload(
            scores,
            primary="Bohater",
            supporting="Władca",
            tertiary=None,
            subject="Krzysztofa Hetmana",
        )
    )
    txt_l = txt.lower()
    first_paragraph = txt.split("\n\n")[0].lower()
    assert "silny i dwubiegunowy" in first_paragraph
    assert "archetypem głównym" in txt_l
    assert "archetypem wspierającym jest" in txt_l
    assert "archetypem pobocznym" not in txt_l
    assert "samosterowny" not in txt_l
    assert "niezależność i porządek" in txt_l
    assert "drugi w kolejności" not in txt_l
    assert "wzmacnia profil pobocznie" not in txt_l


def test_profile_d_hetman_trojbiegunowy_bez_degradacji_pobocznego():
    scores = {
        "Bohater": 75.0,
        "Władca": 73.0,
        "Odkrywca": 70.0,
        "Twórca": 43.0,
        "Czarodziej": 60.0,
        "Buntownik": 50.0,
        "Błazen": 50.0,
        "Niewinny": 37.0,
        "Mędrzec": 57.0,
        "Kochanek": 57.0,
        "Opiekun": 62.0,
        "Towarzysz": 50.0,
    }
    txt = generate_strength_profile_description(
        _payload(
            scores,
            primary="Bohater",
            supporting="Władca",
            tertiary=("Odkrywca", 70.0),
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
    assert "wszystkie trzy współtworzą wyraźny rdzeń profilu" in txt_l
    assert "wzmacnia profil pobocznie" not in txt_l
    assert "drugi w kolejności" not in txt_l
    assert "Niezależność i Zmiana" in txt
    assert "różnice między czterema grupami nie są duże" in txt_l


def test_profile_e_jozef_nie_myli_umiarkowanego_top1_z_sila_profilu():
    scores = {
        "Opiekun": 53.0,
        "Kochanek": 43.0,
        "Czarodziej": 40.0,
        "Błazen": 38.0,
        "Towarzysz": 33.0,
        "Mędrzec": 33.0,
        "Twórca": 32.0,
        "Niewinny": 28.0,
        "Odkrywca": 25.0,
        "Buntownik": 20.0,
        "Bohater": 15.0,
        "Władca": 13.0,
    }
    txt = generate_strength_profile_description(
        _payload(
            scores,
            primary="Opiekun",
            supporting="Kochanek",
            tertiary=None,
            subject="Józefa Józefaciółka",
        )
    )
    first_paragraph = txt.split("\n\n")[0].lower()
    txt_l = txt.lower()
    assert "archetypem głównym jest opiekun o umiarkowanym natężeniu" in txt_l
    assert "archetypem wspierającym jest kochanek o słabym natężeniu" in txt_l
    assert "jest umiarkowany" not in first_paragraph
    assert ("raczej słaby" in first_paragraph) or ("słabo zarysowany" in first_paragraph)
    assert "rozproszony" in first_paragraph
    assert "ludzie i niezależność" in txt_l


def test_profile_f_bardzo_silny_bez_powtorzenia_oceny():
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


def test_profile_strength_helper_distinguishes_top1_intensity_from_overall_strength():
    archetypes = [
        {"label": "Opiekun", "score": 53.0},
        {"label": "Kochanek", "score": 43.0},
        {"label": "Czarodziej", "score": 40.0},
        {"label": "Błazen", "score": 38.0},
        {"label": "Towarzysz", "score": 33.0},
        {"label": "Mędrzec", "score": 33.0},
        {"label": "Twórca", "score": 32.0},
        {"label": "Niewinny", "score": 28.0},
        {"label": "Odkrywca", "score": 25.0},
        {"label": "Buntownik", "score": 20.0},
        {"label": "Bohater", "score": 15.0},
        {"label": "Władca", "score": 13.0},
    ]
    out = classify_profile_strength(archetypes, tertiary=None)
    assert out["overall_strength_label"] in {"raczej słaby", "słabo zarysowany"}
    assert out["concentration_label"] == "spread"
    assert out["top1"] == pytest.approx(53.0)
    assert out["top2"] == pytest.approx(43.0)
