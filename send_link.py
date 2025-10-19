# send_link.py — kafel „Wyślij link do ankiety”
from __future__ import annotations

from typing import List, Dict, Tuple, Optional, Callable
import os
import base64
import json
from datetime import datetime, timezone, timedelta
import time  # ⬅️ do auto-odświeżania (sleep + rerun)

import pandas as pd
import streamlit as st
import re

# Importy bezwzględne (plik leży obok app.py)
from db_utils import get_supabase, fetch_studies
from utils import make_token
from db_sms import create_sms_record, mark_sms_sent, list_sms_for_study, DuplicateTokenError as DuplicateSmsTokenError
from smsapi_client import send_sms  # send_sms(api_token, to_phone, text, sender=None)

# [NOWE – e-mail]
from db_email import create_email_record, mark_email_sent, list_email_for_study, DuplicateTokenError as DuplicateEmailTokenError
from email_client import send_email


# ──────────────────────────────────────────────────────────────────────────────
# USTAWIENIA MOCKUPU
# ──────────────────────────────────────────────────────────────────────────────
MOCKUP_PATH = "assets/phone_mockup.png"  # PNG telefonu (podany przez Ciebie)
# Dokładny prostokąt białego ekranu w PNG (zmierzone pod ten plik)
MOCKUP_TOP = 95
MOCKUP_LEFT = 38
MOCKUP_WIDTH = 229
MOCKUP_HEIGHT = 407

# [NOWE] MOCKUP MONITORA (PNG z białym „ekranem” w środku)
EMAIL_MOCKUP_PATH = "assets/komputer.png"  # wgraj plik do ./assets
EMAIL_TOP = 54        # dopasuj po otrzymaniu finalnego PNG
EMAIL_LEFT = 72
EMAIL_WIDTH = 409
EMAIL_HEIGHT = 255

# Plik z domyślnymi ustawieniami mockupów (lokalnie w repo)
MOCKUP_PREFS_FILE = os.path.join("assets", "mockup_prefs.json")

def _load_mockup_prefs() -> dict:
    """Wczytaj słownik ustawień mockupów z JSON (jeśli jest)."""
    try:
        if os.path.exists(MOCKUP_PREFS_FILE):
            with open(MOCKUP_PREFS_FILE, "r", encoding="utf-8") as f:
                return json.load(f) or {}
    except Exception:
        pass
    return {}

def _save_mockup_prefs(prefs: dict) -> None:
    """Zapisz słownik ustawień mockupów do JSON."""
    try:
        with open(MOCKUP_PREFS_FILE, "w", encoding="utf-8") as f:
            json.dump(prefs, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.warning(f"Nie udało się zapisać ustawień mockupu: {e}")


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

# [NOWE] Parsowanie i walidacja e-mail
_EMAIL_RE = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.I)

def _normalize_emails(s: str) -> List[str]:
    if not s:
        return []
    for ch in ("\n", ";", " "):
        s = s.replace(ch, ",")
    out = []
    for x in [x.strip() for x in s.split(",") if x.strip()]:
        if _EMAIL_RE.match(x):
            out.append(x)
    return out

def _email_env():
    host = st.secrets.get("SMTP_HOST", "")
    port = int(st.secrets.get("SMTP_PORT", 0) or 0)
    user = st.secrets.get("SMTP_USER", "")
    pwd  = st.secrets.get("SMTP_PASS", "")
    secure = (st.secrets.get("SMTP_SECURE", "ssl") or "ssl").lower()
    from_email = st.secrets.get("FROM_EMAIL", "")
    from_name  = st.secrets.get("FROM_NAME", "")
    base_url = (st.secrets.get("SURVEY_BASE_URL", "") or "").rstrip("/")
    if not all([host, port, user, pwd, from_email, base_url]):
        raise RuntimeError("Brak ustawień SMTP albo SURVEY_BASE_URL w st.secrets.")
    return host, port, user, pwd, secure, from_email, from_name, base_url


_PL_MAP = str.maketrans({
    "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n", "ó": "o", "ś": "s", "ż": "z", "ź": "z",
    "Ą": "A", "Ć": "C", "Ę": "E", "Ł": "L", "Ń": "N", "Ó": "O", "Ś": "S", "Ż": "Z", "Ź": "Z",
})


def _strip_pl_diacritics(text: str) -> str:
    """Zamień polskie znaki diakrytyczne na ASCII."""
    return (text or "").translate(_PL_MAP)

def _ensure_name_placeholders(subj: str) -> str:
    """
    Jeśli w temacie nie ma {fn_gen}/{ln_gen}, doklej ' dla {fn_gen} {ln_gen}'.
    Dzięki temu imię i nazwisko będą zawsze w wysyłanym temacie,
    nawet jeśli ktoś ręcznie usunie placeholdery w polu 'Temat (e-mail)'.
    """
    subj = (subj or "").strip()
    if "{fn_gen}" in subj or "{ln_gen}" in subj:
        return subj
    # brak placeholderów -> doklej
    return f"{subj} dla {{fn_gen}} {{ln_gen}}"

def _render_subject(user_subject: Optional[str], fn_gen: str, ln_gen: str) -> str:
    """
    Zwraca finalny temat e-maila:
    - jeśli zawiera placeholdery → podstaw,
    - jeśli już zawiera imię+nazwisko → zostaw jak jest,
    - w przeciwnym razie doklej 'dla <fn_gen> <ln_gen>'.
    """
    s = (user_subject or "").strip()

    if "{fn_gen}" in s or "{ln_gen}" in s:
        try:
            return s.format(fn_gen=fn_gen, ln_gen=ln_gen)
        except Exception:
            pass  # na wszelki wypadek, jeśli format się wysypie

    full = f"{fn_gen} {ln_gen}".strip()
    if full and full in s:
        return s

    base = s or "Prośba o wypełnienie ankiety"
    return f"{base} dla {fn_gen} {ln_gen}".strip()


def _fmt_dt(val: Optional[str]) -> str:
    """Na wejściu ISO; jeśli ma strefę – konwersja do Europe/Warsaw,
    jeśli jest 'naive' (bez strefy) – traktuj jako już lokalny i tylko sformatuj."""
    if not val:
        return ""
    try:
        ts = pd.to_datetime(val, errors="coerce", utc=False)
        if pd.isna(ts):
            return ""
        # tylko gdy jest strefowy (tz-aware), konwertuj do PL
        if getattr(ts, "tz", None) is not None:
            ts = ts.tz_convert("Europe/Warsaw")
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


def _logs_dataframe(sb, study_id: str, mode: str, cache_bust: Optional[int] = None) -> pd.DataFrame:
    """
    mode: 'sms' | 'email'
    """
    rows = (list_sms_for_study if mode == "sms" else list_email_for_study)(sb, study_id) or []
    out: List[Dict[str, str]] = []
    for r in rows:
        out.append(
            {
                "Data": _fmt_dt(r.get("created_at") or r.get("created_at_pl")),
                ("Telefon" if mode == "sms" else "E-mail"): r.get("phone", "") if mode == "sms" else r.get("email", ""),
                "Status": _status_icon(r),
                "Wysłano": "✓" if (r.get("status") or "").lower() in ("sent", "delivered") else "",
                "Kliknięto": _fmt_dt(r.get("clicked_at")),
                "Rozpoczęto": _fmt_dt(r.get("started_at")),
                "Zakończono": _fmt_dt(r.get("completed_at")),
                "Błąd": "✖" if (r.get("status") or "").lower() == "failed" else "",
            }
        )
    cols = ["Data", ("Telefon" if mode == "sms" else "E-mail"), "Status", "Wysłano", "Kliknięto", "Rozpoczęto", "Zakończono", "Błąd"]
    return pd.DataFrame(out, columns=cols)



def _mockup_css_bg(path: str) -> Optional[str]:
    """Zwraca data-URL PNG mockupu jeśli plik istnieje, inaczej None."""
    if not os.path.exists(path):
        return None
    try:
        with open(path, "rb") as f:
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

    # — jednorazowe wczytanie domyślnych ustawień mockupu e-mail z pliku —
    if not st.session_state.get("_e_prefs_loaded", False):
        _prefs = _load_mockup_prefs()
        _e = _prefs.get("email", {})
        # domyślne fallbacki z bieżących stałych
        st.session_state.setdefault("_e_wrap_w", int(_e.get("wrap_w", EMAIL_LEFT + EMAIL_WIDTH + 60)))
        st.session_state.setdefault("_e_wrap_h", int(_e.get("wrap_h", EMAIL_TOP + EMAIL_HEIGHT + 100)))
        st.session_state.setdefault("_e_top",     int(_e.get("top", EMAIL_TOP)))
        st.session_state.setdefault("_e_left",    int(_e.get("left", EMAIL_LEFT)))
        st.session_state.setdefault("_e_w",       int(_e.get("w", EMAIL_WIDTH)))
        st.session_state.setdefault("_e_h",       int(_e.get("h", EMAIL_HEIGHT)))
        st.session_state.setdefault("_e_pad",     int(_e.get("pad", 18)))
        st.session_state.setdefault("_e_pad_top", int(_e.get("pad_top", 18)))
        st.session_state["_e_prefs_loaded"] = True

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

    # Temat (e-mail) – automatyczne podstawienie {fn_gen}/{ln_gen} i „doklejka” jeśli brak
    if method == "E-mail":
        base_tpl = st.secrets.get("EMAIL_SUBJECT", "Prośba o wypełnienie ankiety")
        subject_tpl = _ensure_name_placeholders(base_tpl)
        auto_subject = subject_tpl.format(fn_gen=fn_gen, ln_gen=ln_gen)

        # auto-reset jak przy treści SMS (tylko gdy user nie edytował ręcznie)
        if "email_subject" not in st.session_state:
            st.session_state.email_subject = auto_subject
            st.session_state._auto_email_subject = auto_subject
            st.session_state._email_last_person_label = label
        else:
            if label != st.session_state.get("_email_last_person_label"):
                if st.session_state.email_subject == st.session_state.get("_auto_email_subject"):
                    st.session_state.email_subject = auto_subject
                st.session_state._auto_email_subject = auto_subject
                st.session_state._email_last_person_label = label
            else:
                st.session_state._auto_email_subject = auto_subject

        st.text_input("Temat (e-mail)", key="email_subject", label_visibility="visible")

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

        # licznik tylko dla SMS; e-mail nie pokazuje licznika i zachowuje polskie znaki
        if method == "SMS":
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

    # Podgląd po prawej: telefon (SMS) albo monitor (e-mail)
    with cols[1]:
        msg_preview = _strip_pl_diacritics(st.session_state.sms_body) if method == "SMS" else st.session_state.sms_body

        if method == "SMS":
            data_url = _mockup_css_bg(MOCKUP_PATH)

            with st.expander("Dopasuj mockup SMS (ręcznie)", expanded=False):
                _sms_top = st.number_input("Top (px)",
                                           value=st.session_state.get("_sms_top", MOCKUP_TOP),
                                           step=1)
                _sms_left = st.number_input("Left (px)",
                                            value=st.session_state.get("_sms_left", MOCKUP_LEFT),
                                            step=1)
                _sms_w = st.number_input("Szerokość (px)",
                                         value=st.session_state.get("_sms_w", MOCKUP_WIDTH), step=1)
                _sms_h = st.number_input("Wysokość (px)",
                                         value=st.session_state.get("_sms_h", MOCKUP_HEIGHT),
                                         step=1)
                _sms_pad = st.number_input("Padding wewnątrz (px)",
                                           value=st.session_state.get("_sms_pad", 50), step=1)
                st.session_state.update(_sms_top=_sms_top, _sms_left=_sms_left, _sms_w=_sms_w,
                                        _sms_h=_sms_h, _sms_pad=_sms_pad)

            if data_url:
                st.markdown(
                    f"""
                    <div class="mock-wrap">
                      <div class="mock-bg"></div>
                      <div class="mock-screen v2">{msg_preview.replace("\n", "<br/>")}</div>
                    </div>
                    <style>
                      .mock-wrap {{
                        position:relative; width:{st.session_state._sms_left + st.session_state._sms_w + 40}px;
                        height:{st.session_state._sms_top + st.session_state._sms_h + 80}px;
                      }}
                      .mock-bg {{
                        position:absolute; inset:0;
                        background-image:url('{data_url}');
                        background-size:contain; background-repeat:no-repeat; background-position:center top;
                      }}
                      .mock-screen.v2 {{
                        position:absolute;
                        top:{st.session_state._sms_top}px; left:{st.session_state._sms_left}px;
                        width:{st.session_state._sms_w}px; height:{st.session_state._sms_h}px;
                        background:transparent; border:none;
                        padding:{st.session_state._sms_pad}px 25px; overflow:auto;
                        font:13px/1.4 system-ui,-apple-system, Segoe UI, Roboto, Arial, sans-serif; color:#111;
                        white-space:pre-wrap; overflow-wrap:break-word; word-break:normal; word-break:break-word; hyphens:auto; line-break:auto;
                      }}
                    </style>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"""<div style="border:1px solid #e5e7eb;border-radius:8px;padding:18px;font:13px/1.5 system-ui;">
                           {msg_preview.replace("\n", "<br/>")}
                        </div>""",
                    unsafe_allow_html=True,
                )

        else:
            # E-MAIL – monitor
            data_url = _mockup_css_bg(EMAIL_MOCKUP_PATH)

            with st.expander("Dopasuj mockup E-mail (ręcznie)", expanded=False):
                # rozmiar całej grafiki (kontenera)
                _e_wrap_w = st.number_input(
                    "Szerokość mockupu (px)",
                    value=int(st.session_state.get("_e_wrap_w", EMAIL_LEFT + EMAIL_WIDTH + 60)),
                    step=10,
                )
                _e_wrap_h = st.number_input(
                    "Wysokość mockupu (px)",
                    value=int(st.session_state.get("_e_wrap_h", EMAIL_TOP + EMAIL_HEIGHT + 100)),
                    step=10,
                )

                # pozycja i „ekran”
                _e_top = st.number_input("Top (px)",  value=int(st.session_state.get("_e_top", EMAIL_TOP)),   step=1)
                _e_left = st.number_input("Left (px)", value=int(st.session_state.get("_e_left", EMAIL_LEFT)), step=1)
                _e_w = st.number_input("Szerokość ekranu (px)",  value=int(st.session_state.get("_e_w", EMAIL_WIDTH)),   step=1)
                _e_h = st.number_input("Wysokość ekranu (px)",   value=int(st.session_state.get("_e_h", EMAIL_HEIGHT)),  step=1)

                # paddingi
                _e_pad_top = st.number_input("Padding góra (px)",
                                             value=int(st.session_state.get("_e_pad_top", 18)), step=1)
                _e_pad = st.number_input("Padding wewnątrz (lewy/prawy/dolny) (px)",
                                         value=int(st.session_state.get("_e_pad", 18)), step=1)

                st.session_state.update(
                    _e_wrap_w=_e_wrap_w, _e_wrap_h=_e_wrap_h,
                    _e_top=_e_top, _e_left=_e_left, _e_w=_e_w, _e_h=_e_h,
                    _e_pad=_e_pad, _e_pad_top=_e_pad_top
                )

                # Przyciski zapisu/odczytu domyślnych ustawień (trwałe między odświeżeniami)
                c1, c2, c3 = st.columns([3,3,1])
                if c1.button("💾 Zapisz jako domyślne", use_container_width=True):
                    prefs = _load_mockup_prefs()
                    prefs.setdefault("email", {})
                    prefs["email"] = {
                        "wrap_w": int(st.session_state._e_wrap_w),
                        "wrap_h": int(st.session_state._e_wrap_h),
                        "top":     int(st.session_state._e_top),
                        "left":    int(st.session_state._e_left),
                        "w":       int(st.session_state._e_w),
                        "h":       int(st.session_state._e_h),
                        "pad":     int(st.session_state._e_pad),
                        "pad_top": int(st.session_state._e_pad_top),
                    }
                    _save_mockup_prefs(prefs)
                    st.success("Zapisano jako domyślne.")

                if c2.button("↩ Przywróć zapisane", use_container_width=True):
                    prefs = _load_mockup_prefs()
                    e = prefs.get("email", {})
                    if e:
                        st.session_state._e_wrap_w = int(e.get("wrap_w", st.session_state._e_wrap_w))
                        st.session_state._e_wrap_h = int(e.get("wrap_h", st.session_state._e_wrap_h))
                        st.session_state._e_top     = int(e.get("top",     st.session_state._e_top))
                        st.session_state._e_left    = int(e.get("left",    st.session_state._e_left))
                        st.session_state._e_w       = int(e.get("w",       st.session_state._e_w))
                        st.session_state._e_h       = int(e.get("h",       st.session_state._e_h))
                        st.session_state._e_pad     = int(e.get("pad",     st.session_state._e_pad))
                        st.session_state._e_pad_top = int(e.get("pad_top", st.session_state._e_pad_top))
                        st.experimental_rerun()
                    else:
                        st.info("Brak zapisanych ustawień – najpierw użyj „Zapisz jako domyślne”.")


            # temat do podglądu – bez duplikowania imienia/nazwiska
            _subject_preview = _render_subject(st.session_state.get("email_subject"), fn_gen, ln_gen)


            if data_url:
                st.markdown(
                    f"""
                    <div class="mock-wrap">
                      <div class="mock-bg-email"></div>
                      <div class="mock-screen-email">
                        <div style="opacity:.7;margin-bottom:8px">{_subject_preview}</div>
                        {msg_preview.replace("\n", "<br/>")}
                      </div>
                    </div>
                    <style>
                      .mock-wrap {{
                        position:relative;
                        width:{st.session_state._e_wrap_w}px;
                        height:{st.session_state._e_wrap_h}px;
                      }}
                      .mock-bg-email {{
                        position:absolute; inset:0;
                        background-image:url('{data_url}');
                        background-size:contain; background-repeat:no-repeat; background-position:center top;
                      }}
                      .mock-screen-email {{
                        position:absolute;
                        top:{st.session_state._e_top}px; left:{st.session_state._e_left}px;
                        width:{st.session_state._e_w}px; height:{st.session_state._e_h}px;
                        background:#fff; border:1px solid #e5e7eb; border-radius:2px;
                        padding:{st.session_state._e_pad_top}px {st.session_state._e_pad}px {st.session_state._e_pad}px {st.session_state._e_pad}px; overflow:auto;
                        font:13.5px/1.5 system-ui,-apple-system, Segoe UI, Roboto, Arial, sans-serif; color:#111;
                        white-space:pre-wrap; overflow-wrap:break-word; word-break:normal; word-break:break-word; hyphens:auto; line-break:auto;
                      }}
                    </style>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                # (fallback)
                _subject_preview = _render_subject(st.session_state.get("email_subject"), fn_gen, ln_gen)

                st.markdown(
                    f"""<div style="border:1px solid #e5e7eb;border-radius:8px;padding:18px;background:#fff;box-shadow:0 1px 2px rgb(0 0 0/0.04);font:13.5px/1.5 system-ui;">
                        <div style="opacity:.7;margin-bottom:8px">{_subject_preview}</div>
                        {msg_preview.replace("\n", "<br/>")}
                    </div>""",
                    unsafe_allow_html=True,
                )


    # ── Wysyłka ───────────────────────────────────────────────────────────────
    if 'send_btn' in locals() and send_btn:
        body = st.session_state.sms_body

        if method == "SMS":
            try:
                api_token, sender, base_url = _sms_env()
            except RuntimeError as e:
                st.error(str(e));
                st.stop()

            phones = _normalize_recipients(recipients)
            if not phones:
                st.warning("Podaj co najmniej jeden numer telefonu.");
                st.stop()

            sent_ok = 0
            for ph in phones:
                token = make_token(5)
                final_link = _build_link(base_url, slug, token)

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

                # zapis do DB
                for _ in range(5):
                    try:
                        rec = create_sms_record(sb, study_id=study["id"], phone=ph,
                                                text=_strip_pl_diacritics(msg), token=token)
                        break
                    except DuplicateSmsTokenError:
                        new_token = make_token(5)
                        new_link = _build_link(base_url, slug, new_token)
                        msg = msg.replace(final_link, new_link)
                        token, final_link = new_token, new_link
                else:
                    st.error(f"Nie udało się wygenerować unikalnego linku dla {ph}.");
                    continue

                ok, provider_id, err = send_sms(api_token=api_token, to_phone=ph,
                                                text=_strip_pl_diacritics(msg), sender=sender)
                if ok:
                    mark_sms_sent(sb, sms_id=rec["id"], provider_message_id=provider_id or "");
                    sent_ok += 1
                else:
                    st.error(f"Nie wysłano do {ph}: {err or 'unknown error'}")
            st.success(f"Wysłano {sent_ok} / {len(phones)}.")

        else:  # E-MAIL
            try:
                host, port, user, pwd, secure, from_email, from_name, base_url = _email_env()
            except RuntimeError as e:
                st.error(str(e));
                st.stop()

            emails = _normalize_emails(recipients)
            if not emails:
                st.warning("Podaj poprawne adresy e-mail (oddzielone przecinkami).");
                st.stop()

            # pokaż ewentualnie niepoprawne adresy (dla jasności)
            raw_parts = [x.strip() for x in re.split(r"[,\n; ]+", recipients) if x.strip()]
            invalid = [x for x in raw_parts if not _EMAIL_RE.match(x)]
            if invalid:
                st.error(f"Niepoprawne adresy: {', '.join(invalid)}");
                st.stop()

            # Finalny temat – bez podwajania, z automatycznym dopięciem imienia/nazwiska gdy brak
            subject = _render_subject(
                st.session_state.get("email_subject") or st.secrets.get("EMAIL_SUBJECT", "Prośba o wypełnienie ankiety"),
                fn_gen, ln_gen
            )

            sent_ok = 0
            for em in emails:
                token = make_token(5)
                final_link = _build_link(base_url, slug, token)

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

                # zapis do DB (e-mail)
                for _ in range(5):
                    try:
                        rec = create_email_record(sb, study_id=study["id"], email=em,
                                                  subject=subject, text=msg, token=token)
                        break
                    except DuplicateEmailTokenError:
                        new_token = make_token(5)
                        new_link = _build_link(base_url, slug, new_token)
                        msg = msg.replace(final_link, new_link)
                        token, final_link = new_token, new_link
                else:
                    st.error(f"Nie udało się wygenerować unikalnego linku dla {em}.");
                    continue

                ok, message_id, err = send_email(
                    host=host, port=port, username=user, password=pwd, secure=secure,
                    from_email=from_email, from_name=from_name,
                    to_email=em, subject=subject, text=msg
                )
                if ok:
                    mark_email_sent(sb, email_id=rec["id"], provider_message_id=message_id or "")
                    sent_ok += 1
                else:
                    st.error(f"Nie wysłano do {em}: {err or 'unknown error'}")
            st.success(f"Wysłano {sent_ok} / {len(emails)}.")

    # ── Statusy w tej samej sekcji ────────────────────────────────────────────
    st.markdown('<hr class="hr-thin status-top-tight">', unsafe_allow_html=True)

    label_status = "Statusy SMS" if method == "SMS" else "Statusy e-mail"
    st.markdown(
        f'<div class="form-label-strong" style="font-size:18px;margin-bottom:16px;">{label_status}</div>',
        unsafe_allow_html=True
    )

    # 🔄 Ręczne + auto odświeżanie
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("⟳ Odśwież statusy",
                     key=("refresh_sms" if method == "SMS" else "refresh_email")):
            st.session_state["_status_tick"] = st.session_state.get("_status_tick", 0) + 1
            st.rerun()
    with col2:
        auto_refresh_key = "auto_refresh_sms" if method == "SMS" else "auto_refresh_email"
        auto_refresh = st.checkbox("Auto-odśwież co 15 sekund",
                                   value=st.session_state.get(auto_refresh_key, False),
                                   key=auto_refresh_key)

    # Pobierz logi
    mode = "sms" if method == "SMS" else "email"
    df_logs = _logs_dataframe(sb, study_id=study["id"], mode=mode)

    # Wymuś kolumny i kolejność
    from streamlit import column_config as cc
    wanted_cols = ["Data", ("Telefon" if mode == "sms" else "E-mail"), "Status", "Wysłano",
                   "Kliknięto", "Rozpoczęto", "Zakończono", "Błąd"]
    for c in wanted_cols:
        if c not in df_logs.columns:
            df_logs[c] = ""
    df_logs = df_logs[wanted_cols]

    # ikony wg surowych danych
    raw_rows = (list_sms_for_study if mode == "sms" else list_email_for_study)(sb,
                                                                               study["id"]) or []

    def _status_icon_fixed(row: Dict) -> str:
        status = (row.get("status") or "").lower()
        if status == "failed": return "✖"
        if row.get("completed_at"): return "✅"
        if row.get("started_at"): return "🏁"
        if row.get("clicked_at"): return "🔗"
        if status == "delivered": return "📬"
        if status == "sent": return "📤"
        if status == "queued": return "⏳"
        return "•"

    icons = [_status_icon_fixed(r) for r in raw_rows]
    if len(icons) == len(df_logs):
        df_logs["Status"] = icons

    # wąska tabela
    st.markdown(
        """
        <style>.narrow-table { max-width: 920px; margin: 0 auto; }</style>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="narrow-table">', unsafe_allow_html=True)
    st.dataframe(
        df_logs, hide_index=True,
        column_config={
            "Data": cc.Column(width="medium"),
            ("Telefon" if mode == "sms" else "E-mail"): cc.Column(width="small"),
            "Status": cc.Column(width="small"),
            "Wysłano": cc.Column(width="small"),
            "Kliknięto": cc.Column(width="medium"),
            "Rozpoczęto": cc.Column(width="medium"),
            "Zakończono": cc.Column(width="medium"),
            "Błąd": cc.Column(width="small"),
        },
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # Legenda
    if mode == "sms":
        legenda = """
          📤 – SMS wysłany<br>
          📬 – SMS doręczony (jeśli provider zwróci potwierdzenie)<br>
          🔗 – Odbiorca kliknął w link<br>
          🏁 – Ankieta rozpoczęta<br>
          ✅ – Ankieta zakończona<br>
          ✖ – Błąd wysyłki<br>
          ⏳ – Oczekuje w kolejce<br>
          • – Inny / nieznany status
        """
    else:
        # SMTP nie daje real-time 'delivered', więc nie pokazujemy 📬
        legenda = """
          📤 – E-mail wysłany<br>
          🔗 – Odbiorca kliknął w link<br>
          🏁 – Ankieta rozpoczęta<br>
          ✅ – Ankieta zakończona<br>
          ✖ – Błąd wysyłki<br>
          ⏳ – Oczekuje w kolejce (wysłanie w toku)<br>
          • – Inny / nieznany status
        """
    st.markdown(
        f"""<div style="margin-top:18px;font-size:14px;line-height:1.6;"><b>Legenda statusów:</b><br>{legenda}</div><div style="margin-bottom:60px"></div>""",
        unsafe_allow_html=True)

    # --- AUTO-REFRESH NA KOŃCU: realny impuls (sleep → rerun) ---
    if auto_refresh:
        st.caption("Auto-odświeżanie aktywne (co 15 s)")
        time.sleep(15)
        st.session_state["_sms_tick"] = st.session_state.get("_sms_tick", 0) + 1
        st.rerun()