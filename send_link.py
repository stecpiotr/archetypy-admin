# send_link.py — kafel „Wyślij link do ankiety”
from __future__ import annotations

from typing import List, Dict, Tuple, Optional, Callable
import os
import base64
from datetime import datetime, timezone, timedelta
import time  # ⬅️ do auto-odświeżania (sleep + rerun)

import body
import pandas as pd
import streamlit as st
import re

# Importy bezwzględne (plik leży obok app.py)
from db_utils import get_supabase, fetch_studies
from utils import make_token
from db_sms import create_sms_record, mark_sms_sent, list_sms_for_study, DuplicateTokenError
from smsapi_client import send_sms  # send_sms(api_token, to_phone, text, sender=None)


# ──────────────────────────────────────────────────────────────────────────────
# USTAWIENIA MOCKUPU
# ──────────────────────────────────────────────────────────────────────────────
MOCKUP_PATH = "assets/phone_mockup.png"  # PNG telefonu (podany przez Ciebie)
# Dokładny prostokąt białego ekranu w PNG (zmierzone pod ten plik)
MOCKUP_TOP = 95
MOCKUP_LEFT = 38
MOCKUP_WIDTH = 229
MOCKUP_HEIGHT = 407


# ──────────────────────────────────────────────────────────────────────────────
# Pomocnicze
# ──────────────────────────────────────────────────────────────────────────────
def _normalize_recipients(s: str) -> List[str]:
    """Akceptuj przecinki / średniki / nowe linie / spacje i zrób listę numerów."""
    if not s:
        return []
    for ch in ("\n", ";", " "):
        s = s.replace(ch, ",")
    return [x.strip() for x in s.split(",") if x.strip()]


def _sms_env() -> Tuple[str, Optional[str], str]:
    """
    Czyta ustawienia SMS z secrets.
    Zwraca: (SMSAPI_TOKEN, SMS_SENDER|None, SURVEY_BASE_URL)
    """
    token = st.secrets.get("SMSAPI_TOKEN", "")
    sender = st.secrets.get("SMS_SENDER", None)
    base_url = (st.secrets.get("SURVEY_BASE_URL", "") or "").rstrip("/")
    if not token:
        raise RuntimeError("Brak SMSAPI_TOKEN w st.secrets.")
    if not base_url:
        raise RuntimeError("Brak SURVEY_BASE_URL w st.secrets.")
    return token, sender, base_url


_PL_MAP = str.maketrans({
    "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n", "ó": "o", "ś": "s", "ż": "z", "ź": "z",
    "Ą": "A", "Ć": "C", "Ę": "E", "Ł": "L", "Ń": "N", "Ó": "O", "Ś": "S", "Ż": "Z", "Ź": "Z",
})


def _strip_pl_diacritics(text: str) -> str:
    """Zamień polskie znaki diakrytyczne na ASCII."""
    return (text or "").translate(_PL_MAP)


def _fmt_dt(val: Optional[str]) -> str:
    """ISO → 'YYYY-MM-DD HH:MM:SS' (próba konwersji; puste gdy None)."""
    if not val:
        return ""
    try:
        ts = pd.to_datetime(val, utc=True, errors="coerce")
        if pd.isna(ts):
            return ""
        return ts.tz_convert("Europe/Warsaw").strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        try:
            ts = pd.to_datetime(val, errors="coerce")
            if pd.isna(ts):
                return ""
            return ts.strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            return str(val)


def _status_icon(row: Dict) -> str:
    """
    Kolejność priorytetu:
      completed_at → ✅
      started_at   → 🏁
      clicked_at   → 🔗
      failed       → ✖
      delivered    → 📬
      sent         → 📤
      queued       → ⏳
      inne         → •
    """
    status = (row.get("status") or "").lower()

    if row.get("completed_at"):
        return "✅"
    if row.get("started_at"):
        return "🏁"
    if row.get("clicked_at"):
        return "🔗"

    if status == "failed":
        return "✖"
    if status == "delivered":
        return "📬"   # pojawi się tylko jeśli provider zwróci taki status
    if status == "sent":
        return "📤"
    if status == "queued":
        return "⏳"
    return "•"


def _build_link(base_url: str, slug: str, token: str) -> str:
    """https://host/<slug>?t=<token> (bez podwójnych //)."""
    base = (base_url or "").rstrip("/")
    s = (slug or "").lstrip("/")
    return f"{base}/{s}?t={token}" if s else f"{base}/?t={token}"


def _logs_dataframe(sb, study_id: str) -> pd.DataFrame:
    rows = list_sms_for_study(sb, study_id) or []
    out: List[Dict[str, str]] = []
    for r in rows:
        out.append(
            {
                "Data": _fmt_dt(r.get("created_at")),
                "Telefon": r.get("phone", ""),
                "Status": _status_icon(r),
                "Wysłano": "✓" if (r.get("status") or "").lower() in ("sent", "delivered") else "",
                "Kliknięto": _fmt_dt(r.get("clicked_at")),
                "Rozpoczęto": _fmt_dt(r.get("started_at")),
                "Zakończono": _fmt_dt(r.get("completed_at")),
                "Błąd": "✖" if (r.get("status") or "").lower() == "failed" else "",
            }
        )
    return pd.DataFrame(
        out,
        columns=[
            "Data",
            "Telefon",
            "Status",
            "Wysłano",
            "Kliknięto",
            "Rozpoczęto",
            "Zakończono",
            "Błąd",
        ],
    )


def _mockup_css_bg() -> Optional[str]:
    """Zwraca data-URL PNG mockupu jeśli plik istnieje, inaczej None."""
    if not os.path.exists(MOCKUP_PATH):
        return None
    try:
        with open(MOCKUP_PATH, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        return f"data:image/png;base64,{b64}"
    except Exception:
        return None


def _reset_body(default_text: str) -> None:
    st.session_state.sms_body = default_text
    st.session_state.auto_sms_template = default_text
    # [NOWE] odśwież też link podglądu
    try:
        base_url = (st.secrets.get("SURVEY_BASE_URL") or "").rstrip("/")
        # ze slugiem z aktualnie wybranego rekordu:
        # (funkcja jest wywoływana w kontekście aktywnego "study")
        # jeśli nie masz tu "study", można to pominąć – nie jest krytyczne
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────────────────
# PUBLICZNY RENDER – wywoływany z app.py
# ──────────────────────────────────────────────────────────────────────────────
def render(back_btn: Callable[[], None]) -> None:
    """Cały kafel „Wyślij link do ankiety”."""
    sb = get_supabase()

    # przycisk „Cofnij”
    back_btn()

    # ── Style etykiet + przycisków ────────────────────────────────────────────
    st.markdown(
        """
        <style>
          /* === KONTROLA ETYKIET (zmień wartości poniżej) === */
          :root{
            --label-font-size: 16px;   /* rozmiar */
            --label-font-weight: 600;    /* 400–700 */
            --label-margin-top: 16px;     /* górny margines */
            --label-margin-bottom: 9px;  /* dolny margines */
          }
          .field-label{
            font-weight: var(--label-font-weight);
            font-size: var(--label-font-size);
            margin: var(--label-margin-top) 0 var(--label-margin-bottom) 0;
          }

          .sms-counter{ text-align:right; color:#6b7280; font-size:13px; margin-top:4px; }

          /* Primary niebieski + ładniejsze przyciski (bez zmian funkcji) */
          .stButton > button[kind="primary"],
          div[data-testid="stButton"] button {
            background-color:#2563eb !important;
            color:#fff !important;
            border:none !important;
            border-radius:6px !important;
          }

          /* Stos przycisków pod polem */
          .btn-stack{ margin-top:30px; margin-bottom:30px; }

          /* Pojedyncze wrappery dla precyzyjnych odstępów */
          .btn-stack .btn-reset{ margin-bottom:10px; }     /* "Przywróć" WYŻEJ */
          .btn-stack .btn-send{  margin-top:500px;         /* "Wyślij" DUŻO NIŻEJ */
                                  margin-bottom:50px; }    /* duży dolny margines */

          /* Statusy SMS bliżej góry i większy dół po tytule */
          .status-top-tight{ margin-top:0 !important; }
          .status-bottom-gap{ height:80px; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # ── Wybór osoby/JST ───────────────────────────────────────────────────────
    studies = fetch_studies(sb)
    if not studies:
        st.info("Brak badań w bazie.")
        return

    options = {
        f"{(s.get('last_name_nom') or s.get('last_name') or '')} "
        f"{(s.get('first_name_nom') or s.get('first_name') or '')} "
        f"({s.get('city') or ''}) – /{s.get('slug') or ''}": s
        for s in studies
    }

    # Etykieta nad polem
    st.markdown(
        '<div style="font-size:17.5px; font-weight:675; margin-top:20px; margin-bottom:0px;">'
        'Wybierz osobę:'
        '</div>',
        unsafe_allow_html=True
    )

    # Własne style selectboxa
    st.markdown("""
    <style>
    /* Główne pole selectbox (niewybrane) */
    div[data-baseweb="select"] > div {
        background-color: #f9fafb !important;   /* jasnoszare tło */
        color: #111827 !important;              /* ciemny tekst */
        border: 1px solid #d1d5db !important;   /* ramka */
        border-radius: 6px !important;          /* zaokrąglenie rogów */
        min-height: 42px !important;            /* wyższe pole */
    }

    /* Tekst w środku selectboxa */
    div[data-baseweb="select"] span {
        color: #111827 !important;
        font-weight: 500 !important;
    }

    /* Lista rozwiniętych opcji */
    ul[role="listbox"] {
        background-color: #ffffff !important;
        border: 1px solid #d1d5db !important;
        border-radius: 6px !important;
    }

    /* Hover nad opcją */
    ul[role="listbox"] li:hover {
        background-color: #e5e7eb !important;  /* szare podświetlenie */
        color: #111827 !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # Sam selectbox
    label = st.selectbox(
        label="Wybierz osobę:",
        options=list(options.keys()),
        label_visibility="collapsed",
        key="sendlink_person",
    )
    study = options[label]


    # ── Metoda i odbiorcy ─────────────────────────────────────────────────────
    st.markdown(
        '<div style="font-size:16px; font-weight:600; margin-top:35px; margin-bottom:5px;">'
        'Metoda wysyłki'
        '</div>',
        unsafe_allow_html=True
    )
    method = st.radio("Metoda wysyłki", ["SMS", "E-mail"], horizontal=True, index=0, label_visibility="collapsed")

    st.markdown('<div class="field-label">Odbiorcy</div>', unsafe_allow_html=True)
    placeholder = "48500123456, 48600111222" if method == "SMS" else "jan@firma.pl, ola@urzad.gov.pl"
    recipients = st.text_area("Odbiorcy", placeholder=placeholder, height=100, label_visibility="collapsed")

    # ── Treść (podgląd) ───────────────────────────────────────────────────────
    ln = study.get("last_name_nom") or study.get("last_name") or ""
    fn = study.get("first_name_nom") or study.get("first_name") or ""
    ln_gen = study.get("last_name_gen") or ln
    fn_gen = study.get("first_name_gen") or fn

    # Placeholder linku do podglądu
    base_url = (st.secrets.get("SURVEY_BASE_URL") or "").rstrip("/")
    slug = study.get("slug") or ""

    # Trzymaj stabilny podgląd w session_state dopóki nie zmienisz osoby/rekordu
    sess_key_lp = "sms_link_preview"
    sess_key_person = "sms_last_person_label"

    if st.session_state.get(sess_key_person) != label:
        # zmiana osoby → zrób nowy preview
        token_preview = make_token(5)
        st.session_state[sess_key_lp] = _build_link(base_url, slug, token_preview) if base_url else "<link>"
        st.session_state[sess_key_person] = label
    elif sess_key_lp not in st.session_state:
        token_preview = make_token(5)
        st.session_state[sess_key_lp] = _build_link(base_url, slug, token_preview) if base_url else "<link>"

    link_preview = st.session_state[sess_key_lp]

    default_body = (
        f"Zwracamy sie z prosba o wypelnienie ankiety dla {fn_gen} {ln_gen}."
        f"\n\nLink do ankiety: {link_preview}"
        f"\n\nDziekujemy!"
    )

    # Personalizacja: auto-reset jeśli brak edycji
    if "sms_body" not in st.session_state:
        st.session_state.sms_body = default_body
        st.session_state.auto_sms_template = default_body
        st.session_state.last_person_label = label
    else:
        if label != st.session_state.get("last_person_label"):
            if st.session_state.sms_body == st.session_state.get("auto_sms_template"):
                st.session_state.sms_body = default_body
            st.session_state.auto_sms_template = default_body
            st.session_state.last_person_label = label
        else:
            st.session_state.auto_sms_template = default_body

    cols = st.columns([3, 2], gap="large")
    with cols[0]:
        st.markdown('<div class="field-label">Treść wiadomości</div>', unsafe_allow_html=True)
        st.text_area("Treść wiadomości", key="sms_body", height=180, label_visibility="collapsed")

        # licznik
        ascii_msg = _strip_pl_diacritics(st.session_state.sms_body)
        seg_len = 160
        msg_len = len(ascii_msg)
        segments = (msg_len + seg_len - 1) // seg_len
        remain = seg_len - (msg_len % seg_len or seg_len)
        coding = "GSM-7" if all(ord(c) < 128 for c in ascii_msg) else "Unicode"
        st.markdown(
            f'<div class="sms-counter">Długość: {msg_len} znaków • Segmenty: {segments} • Pozostało w bieżącym: {remain} • Kodowanie: {coding}</div>',
            unsafe_allow_html=True,
        )

        # przyciski – „Przywróć” wyżej, „Wyślij” dużo niżej
        st.markdown('<div class="btn-stack">', unsafe_allow_html=True)

        st.markdown('<div class="btn-reset">', unsafe_allow_html=True)
        st.button("Przywróć domyślną treść", key="reset_btn",
                  on_click=_reset_body, args=(default_body,))
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="btn-send">', unsafe_allow_html=True)
        send_btn = st.button("Wyślij", key="send_btn", type="primary")
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)

    # Podgląd telefonu (marginesy + ŁAMANIE: całe wyrazy, linki łamane gdy muszą)
    with cols[1]:
        ascii_msg = _strip_pl_diacritics(st.session_state.sms_body)
        data_url = _mockup_css_bg()
        if data_url:
            st.markdown(
                f"""
                <div class="mock-wrap">
                  <div class="mock-bg"></div>
                  <div class="mock-screen v2">{ascii_msg.replace("\n","<br/>")}</div>
                </div>
                <style>
                  .mock-wrap {{
                    position:relative; width:{MOCKUP_LEFT + MOCKUP_WIDTH + 40}px;
                    height:{MOCKUP_TOP + MOCKUP_HEIGHT + 80}px;  /* mniejszy zapas → Statusy wyżej */
                  }}
                  .mock-bg {{
                    position:absolute; inset:0;
                    background-image:url('{data_url}');
                    background-size:contain; background-repeat:no-repeat; background-position:center top;
                  }}
                  .mock-screen.v2 {{
                    position:absolute;
                    top:{MOCKUP_TOP}px; left:{MOCKUP_LEFT}px;
                    width:{MOCKUP_WIDTH}px; height:{MOCKUP_HEIGHT}px;
                    background:transparent; border:none;
                    padding:50px 25px; overflow:auto;     /* marginesy wewnętrzne: góra/dół 40, boki 22 */
                    font:13px/1.4 system-ui,-apple-system, Segoe UI, Roboto, Arial, sans-serif; color:#111;

                    /* ŁAMANIE TEKSTU:
                       - preferuj przenoszenie CAŁYCH WYRAZÓW
                       - bardzo długie ciągi (np. URL) mogą się złamać, aby nie wyjść poza ekran
                    */
                    white-space:pre-wrap;
                    overflow-wrap:break-word;  /* przenosi długie niełamalne ciągi, ale preferuje całe wyrazy */
                    word-break:normal;         /* nie rozrywa zwykłych słów */
                    word-break:break-word;     /* fallback dla WebKit/Safari */
                    hyphens:auto;
                    line-break:auto;
                </style>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"""
                <div class="phone-wrap">
                  <div class="phone">
                    <div class="speaker"></div>
                    <div class="screen" style="white-space:pre-wrap; overflow-wrap:break-word; word-break:normal; word-break:break-word; hyphens:auto; line-break:auto; font:12.5px/1.4 system-ui,-apple-system, Segoe UI, Roboto, Arial, sans-serif; padding:40px 22px;">
                      {ascii_msg.replace("\n","<br/>")}
                    </div>
                    <div class="homebtn"></div>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── Wysyłka ───────────────────────────────────────────────────────────────
    if 'send_btn' in locals() and send_btn:
        if method != "SMS":
            st.warning("Obsługa e-mail będzie dodana osobno. Aktualnie wysyłamy tylko SMS.")
            return

        try:
            api_token, sender, base_url = _sms_env()
        except RuntimeError as e:
            st.error(str(e))
            return

        phones = _normalize_recipients(recipients)
        if not phones:
            st.warning("Podaj co najmniej jeden numer telefonu.")
            return

        body = st.session_state.sms_body

        sent_ok = 0
        for ph in phones:
            # 1) token + link docelowy
            token = make_token(5)
            final_link = _build_link(base_url, slug, token)

            # 2) zbuduj treść z podmianą podglądu lub starych linków
            preview = st.session_state.get("sms_link_preview", link_preview)
            msg = body
            if preview and preview in msg:
                msg = msg.replace(preview, final_link)
            else:
                if base_url and slug:
                    pattern = re.compile(
                        rf"{re.escape(base_url.rstrip('/'))}/{re.escape(slug.lstrip('/'))}\?t=[A-Za-z0-9]+")
                    msg = pattern.sub(final_link, msg)
                if final_link not in msg:
                    msg = (msg.rstrip() + "\n" + final_link)

            # 3) zapis do DB z obsługą kolizji tokenu (retry do 5 razy)
            for _ in range(5):
                try:
                    msg_ascii = _strip_pl_diacritics(msg)
                    rec = create_sms_record(
                        sb,
                        study_id=study["id"],
                        phone=ph,
                        text=msg_ascii,
                        token=token,
                    )
                    break  # OK
                except DuplicateTokenError:
                    # wygeneruj nowy token i link; podmień w treści i ponów
                    new_token = make_token(5)
                    new_link = _build_link(base_url, slug, new_token)
                    msg = msg.replace(final_link, new_link)
                    token, final_link = new_token, new_link
            else:
                st.error(f"Nie udało się wygenerować unikalnego linku dla {ph}.")
                continue

            # 4) wysyłka do SMS API
            ok, provider_id, err = send_sms(
                api_token=api_token,
                to_phone=ph,
                text=_strip_pl_diacritics(msg),
                sender=sender,
            )

            if ok:
                mark_sms_sent(sb, sms_id=rec["id"], provider_message_id=provider_id or "")
                sent_ok += 1
            else:
                st.error(f"Nie wysłano do {ph}: {err or 'unknown error'}")

        st.success(f"Wysłano {sent_ok} / {len(phones)}.")

    # ── Statusy w tej samej sekcji ────────────────────────────────────────────
    st.markdown('<hr class="hr-thin status-top-tight">', unsafe_allow_html=True)
    st.markdown(
        '<div class="form-label-strong" style="font-size:18px;margin-bottom:16px;">Statusy SMS</div>',
        unsafe_allow_html=True
    )

    # 🔄 Ręczne i automatyczne odświeżanie (bez JS, bez experimental_set_query_params)
    c1, c2 = st.columns([1, 5])
    with c1:
        if st.button("⟳ Odśwież statusy", key="refresh_sms"):
            st.rerun()

    with c2:
        auto_refresh = st.checkbox("Auto-odśwież co 15 sekund", value=False, key="auto_refresh_sms")
        if auto_refresh:
            # prosty licznik w session_state, żadnego przeładowania strony
            last = st.session_state.get("sms_last_refresh_ts", 0.0)
            now = time.time()
            st.caption("Auto-odświeżanie aktywne (co 15 s)")
            if now - last >= 15:
                st.session_state["sms_last_refresh_ts"] = now
                st.rerun()

    # 🔧 poprawiona kolejność ikon (failed > completed > started > clicked > delivered > sent > queued)
    def _status_icon_fixed(row: Dict) -> str:
        status = (row.get("status") or "").lower()
        if status == "failed":
            return "✖"
        if row.get("completed_at"):
            return "✅"
        if row.get("started_at"):
            return "🏁"
        if row.get("clicked_at"):
            return "🔗"
        if status == "delivered":
            return "📬"  # pojawi się tylko gdy provider zwróci „delivered”
        if status == "sent":
            return "📤"
        if status == "queued":
            return "⏳"
        return "•"

    # pobranie danych
    df_logs = _logs_dataframe(sb, study_id=study["id"])
    # podmień kolumnę z ikoną na nową logikę (jeśli istnieje)
    if not df_logs.empty and "Aktualny status" in df_logs.columns:
        # odczytaj surowe rekordy jeszcze raz aby mieć oryginalne pola status/started/clicked etc.
        raw_rows = list_sms_for_study(sb, study["id"]) or []
        icons = []
        for r in raw_rows:
            icons.append(_status_icon_fixed(r))
        # dopasuj długości (na wszelki wypadek)
        if len(icons) == len(df_logs):
            df_logs["Aktualny status"] = icons

    # tabela z szerokościami kolumn (small/medium/large to jedyne dostępne)
    from streamlit import column_config as cc
    st.dataframe(
        df_logs,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Data": cc.Column(width="large"),
            "Telefon": cc.Column(width="small"),
            "Aktualny status": cc.Column(width="small"),
            "Wysłano": cc.Column(width="small"),
            "Kliknięto": cc.Column(width="large"),
            "Rozpoczęto": cc.Column(width="large"),
            "Zakończono": cc.Column(width="large"),
            "Błąd": cc.Column(width="small"),
        }
    )

    # Legenda (większy odstęp po tytule)
    st.markdown("""
    <div style="margin-top:18px"></div>
    <div style="font-size:14px; line-height:1.6;">
      <b>Legenda statusów:</b><br>
      📤 – SMS wysłany<br>
      📬 – SMS doręczony (jeśli provider zwróci potwierdzenie)<br>
      🔗 – Odbiorca kliknął w link<br>
      🏁 – Ankieta rozpoczęta<br>
      ✅ – Ankieta zakończona<br>
      ✖ – Błąd wysyłki<br>
      ⏳ – Oczekuje w kolejce<br>
      • – Inny / nieznany status
    </div>
    <div style="margin-bottom:60px"></div>
    """, unsafe_allow_html=True)
