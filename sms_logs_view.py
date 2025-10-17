# sms_logs_view.py — prosty podgląd logów (importy dopasowane do katalogu głównego)

from __future__ import annotations
from typing import List, Dict
import pandas as pd
import streamlit as st

from db_sms import list_sms_for_study
from db_utils import get_supabase


def render_sms_logs(studies: List[Dict]) -> None:
    sb = get_supabase()

    st.markdown('<div class="form-label-strong" style="font-size:24px;">📶 Statusy SMS</div>', unsafe_allow_html=True)
    if not studies:
        st.info("Brak rekordów w bazie.")
        return

    options = {
        f"{(s.get('last_name_nom') or s.get('last_name') or '')} "
        f"{(s.get('first_name_nom') or s.get('first_name') or '')} "
        f"({s.get('city') or ''}) – /{s.get('slug') or ''}": s
        for s in studies
    }
    choice = st.selectbox("Wybierz osobę/JST", options=list(options.keys()))
    study = options[choice]

    rows = list_sms_for_study(sb, study["id"])
    if not rows:
        st.info("Brak wysyłek.")
        return

    def _fmt(val: str) -> str:
        try:
            ts = pd.to_datetime(val, utc=True, errors="coerce")
            if pd.isna(ts):
                return ""
            return ts.tz_convert("Europe/Warsaw").strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return str(val or "")

    data = []
    for r in rows:
        status = (r.get("status") or "").lower()
        icon = "✅" if status in ("sent", "delivered") else ("✖" if status == "failed" else "•")
        data.append(
            {
                "Data": _fmt(r.get("created_at")),
                "Telefon": r.get("phone", ""),
                "Status": icon,
                "Kliknięto": _fmt(r.get("clicked_at")),
                "Rozpoczęto": _fmt(r.get("started_at")),
                "Zakończono": _fmt(r.get("completed_at")),
            }
        )

    df = pd.DataFrame(data, columns=["Data", "Telefon", "Status", "Kliknięto", "Rozpoczęto", "Zakończono"])
    st.dataframe(df, width="stretch", hide_index=True)
