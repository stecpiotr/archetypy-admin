import sys
import types

supabase_stub = types.ModuleType("supabase")
supabase_stub.create_client = lambda *args, **kwargs: None
supabase_stub.Client = object
sys.modules.setdefault("supabase", supabase_stub)

from db_jst_utils import import_template_dataframe, make_payload_from_row, response_columns
from metryczka_config import default_jst_metryczka_config


def _cfg_with_party_open():
    cfg = default_jst_metryczka_config()
    questions = list(cfg.get("questions") or [])
    questions.append(
        {
            "id": "M_PARTIA",
            "scope": "custom",
            "db_column": "M_PARTIA",
            "prompt": "Na jaką partię zagłosujesz?",
            "table_label": "Partia",
            "variable_emoji": "🗳️",
            "required": False,
            "multiple": False,
            "randomize_options": False,
            "randomize_exclude_last": False,
            "aliases": [],
            "options": [
                {"label": "PiS", "code": "PiS", "is_open": False, "lock_randomization": False},
                {"label": "KO", "code": "KO", "is_open": False, "lock_randomization": False},
                {"label": "inna (jaka?)", "code": "inna", "is_open": True, "lock_randomization": False},
            ],
        }
    )
    cfg["questions"] = questions
    return cfg


def test_jst_template_includes_m_zawod_other():
    cfg = default_jst_metryczka_config()
    cols = response_columns(cfg)
    assert "M_ZAWOD" in cols
    assert "M_ZAWOD_OTHER" in cols
    df = import_template_dataframe(cfg)
    assert "M_ZAWOD_OTHER" in df.columns


def test_jst_template_includes_party_other_when_open_option_exists():
    cfg = _cfg_with_party_open()
    cols = response_columns(cfg)
    assert "M_PARTIA" in cols
    assert "M_PARTIA_OTHER" in cols
    df = import_template_dataframe(cfg)
    assert "M_PARTIA_OTHER" in df.columns


def test_jst_payload_requires_other_for_open_answers():
    cfg = default_jst_metryczka_config()
    try:
        make_payload_from_row({"M_ZAWOD": "inna"}, metryczka_config=cfg)
        assert False, "Expected validation error for missing M_ZAWOD_OTHER"
    except ValueError as exc:
        assert "M_ZAWOD_OTHER" in str(exc)

    payload = make_payload_from_row(
        {"M_ZAWOD": "inna", "M_ZAWOD_OTHER": "wolny zawód"},
        metryczka_config=cfg,
    )
    assert payload.get("M_ZAWOD") == "inna"
    assert payload.get("M_ZAWOD_OTHER") == "wolny zawód"

