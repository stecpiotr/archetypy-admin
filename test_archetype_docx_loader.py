from archetype_docx_loader import _normalize_group_public_label


def test_group_label_normalization_to_final_public_names():
    assert _normalize_group_public_label("stabilizacja / kontrola") == "stabilność / zarządzanie"
    assert _normalize_group_public_label("niezależność / samorealizacja") == "niezależność / samodzielność"
    assert _normalize_group_public_label("przynależność / ludzie") == "relacje / współdziałanie"
    assert _normalize_group_public_label("ryzyko / mistrzostwo") == "zmiana / przywództwo"


def test_group_label_normalization_keeps_final_names():
    assert _normalize_group_public_label("stabilność / zarządzanie") == "stabilność / zarządzanie"
    assert _normalize_group_public_label("niezależność / samodzielność") == "niezależność / samodzielność"
    assert _normalize_group_public_label("relacje / współdziałanie") == "relacje / współdziałanie"
    assert _normalize_group_public_label("zmiana / przywództwo") == "zmiana / przywództwo"
