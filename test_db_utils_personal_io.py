import json
import sys
import types

supabase_stub = types.ModuleType("supabase")
supabase_stub.create_client = lambda *args, **kwargs: None
supabase_stub.Client = object
sys.modules.setdefault("supabase", supabase_stub)

from db_utils import (
    make_personal_payload_from_row,
    normalize_personal_response_row,
    personal_import_template_dataframe,
    personal_response_rows_to_dataframe,
)


def _answers_48():
    return [i % 6 for i in range(48)]


def _sample_metry_cfg():
    return {
        "version": 1,
        "questions": [
            {
                "id": "M_PLEC",
                "db_column": "M_PLEC",
                "table_label": "Płeć",
                "prompt": "Płeć",
                "options": [
                    {"code": "kobieta", "label": "kobieta"},
                    {"code": "mężczyzna", "label": "mężczyzna"},
                ],
            },
            {
                "id": "M_ZAWOD",
                "db_column": "M_ZAWOD",
                "table_label": "Zawód",
                "prompt": "Zawód",
                "options": [
                    {"code": "student/uczeń", "label": "student/uczeń"},
                    {"code": "inna", "label": "inna (jaka?)", "is_open": True},
                ],
            },
            {
                "id": "M_OBSZAR",
                "db_column": "M_OBSZAR",
                "table_label": "Obszar",
                "prompt": "Obszar",
                "scope": "custom",
                "options": [
                    {"code": "miasto", "label": "miasto"},
                    {"code": "wieś", "label": "wieś"},
                ],
            },
        ],
    }


def test_personal_template_uses_db_like_columns_and_metry_fields():
    df = personal_import_template_dataframe(_sample_metry_cfg())
    cols = list(df.columns)
    assert cols[:4] == ["respondent_id", "created_at", "answers", "raw_total"]
    assert "M_PLEC" in cols
    assert "M_ZAWOD" in cols
    assert "M_ZAWOD_OTHER" in cols
    assert "M_OBSZAR" in cols


def test_normalize_personal_row_accepts_answers_blob_and_metry_aliases():
    answers = _answers_48()
    row = {
        "respondent_id": "R0007",
        "answers": json.dumps(answers, ensure_ascii=False),
        "M_PLEC": "kobieta",
        "METRY_M_WIEK": "40-59",
    }
    norm = normalize_personal_response_row(row)
    assert norm["answers_complete"] is True
    assert norm["answers"] == answers
    assert norm["scores"]["metryczka"]["M_PLEC"] == "kobieta"
    assert norm["scores"]["metryczka"]["M_WIEK"] == "40-59"


def test_normalize_personal_row_keeps_legacy_q_columns_compatibility():
    row = {"respondent_id": "R0008", **{f"Q{i}": (i - 1) % 6 for i in range(1, 49)}}
    norm = normalize_personal_response_row(row)
    assert norm["answers_complete"] is True
    assert len(norm["answers"]) == 48
    assert norm["raw_total"] == sum((i - 1) % 6 for i in range(1, 49))


def test_make_personal_payload_embeds_metryczka_in_scores():
    answers = _answers_48()
    row = {
        "respondent_id": "R0009",
        "answers": answers,
        "M_PLEC": "mężczyzna",
        "M_ZAWOD": "inna",
        "M_ZAWOD_OTHER": "freelancer",
    }
    payload = make_personal_payload_from_row(row)
    assert payload["answers"] == answers
    assert payload["scores"]["respondent_id"] == "R0009"
    assert payload["scores"]["metryczka"]["M_PLEC"] == "mężczyzna"
    assert payload["scores"]["metryczka"]["M_ZAWOD_OTHER"] == "freelancer"


def test_personal_export_dataframe_uses_answers_and_metry_columns():
    answers = _answers_48()
    rows = [
        {
            "id": "resp-1",
            "created_at": "2026-04-17T01:00:00+00:00",
            "answers": answers,
            "raw_total": sum(answers),
            "scores": {
                "respondent_id": "R0010",
                "metryczka": {
                    "M_PLEC": "kobieta",
                    "M_ZAWOD": "inna",
                    "M_ZAWOD_OTHER": "badaczka",
                },
            },
        }
    ]
    df = personal_response_rows_to_dataframe(rows, metryczka_config=_sample_metry_cfg())
    assert "answers" in df.columns
    assert "M_PLEC" in df.columns
    assert "M_ZAWOD_OTHER" in df.columns
    assert "Q1" not in df.columns
    assert str(df.loc[0, "answers"]).startswith("[")
    assert df.loc[0, "M_PLEC"] == "kobieta"
