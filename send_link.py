# send_link.py — kafel „Wyślij link do ankiety”
from __future__ import annotations

from typing import Any, List, Dict, Tuple, Optional, Callable
import os
import base64
import json
from io import BytesIO
from datetime import datetime, timezone, timedelta
import time  # ⬅️ do auto-odświeżania (sleep + rerun)

import pandas as pd
import streamlit as st
import re
from streamlit.components.v1 import html as html_component

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
    host = (
        st.secrets.get("SMTP_HOST", "")
        or st.secrets.get("EMAIL_HOST", "")
        or st.secrets.get("MAIL_HOST", "")
    )
    port_raw = (
        st.secrets.get("SMTP_PORT", 0)
        or st.secrets.get("EMAIL_PORT", 0)
        or st.secrets.get("MAIL_PORT", 0)
    )
    port = int(port_raw or 0)
    user = (
        st.secrets.get("SMTP_USER", "")
        or st.secrets.get("EMAIL_USER", "")
        or st.secrets.get("MAIL_USER", "")
    )
    pwd = (
        st.secrets.get("SMTP_PASS", "")
        or st.secrets.get("EMAIL_PASS", "")
        or st.secrets.get("MAIL_PASS", "")
    )
    secure = (
        st.secrets.get("SMTP_SECURE", "")
        or st.secrets.get("EMAIL_SECURE", "")
        or st.secrets.get("MAIL_SECURE", "")
    )
    secure = (secure or ("ssl" if port == 465 else "starttls")).lower()
    from_email = (
        st.secrets.get("FROM_EMAIL", "")
        or st.secrets.get("SMTP_FROM", "")
        or user
    )
    from_name  = st.secrets.get("FROM_NAME", "") or st.secrets.get("SMTP_FROM_NAME", "")
    base_url = (st.secrets.get("SURVEY_BASE_URL", "") or "").rstrip("/")

    missing = []
    if not host:
        missing.append("SMTP_HOST")
    if not port:
        missing.append("SMTP_PORT")
    if not user:
        missing.append("SMTP_USER")
    if not pwd:
        missing.append("SMTP_PASS")
    if not from_email:
        missing.append("FROM_EMAIL")
    if not base_url:
        missing.append("SURVEY_BASE_URL")
    if missing:
        raise RuntimeError("Brak ustawień SMTP/SURVEY w st.secrets: " + ", ".join(missing))
    return host, port, user, pwd, secure, from_email, from_name, base_url


_PL_MAP = str.maketrans({
    "ą": "a", "ć": "c", "ę": "e", "ł": "l", "ń": "n", "ó": "o", "ś": "s", "ż": "z", "ź": "z",
    "Ą": "A", "Ć": "C", "Ę": "E", "Ł": "L", "Ń": "N", "Ó": "O", "Ś": "S", "Ż": "Z", "Ź": "Z",
})


def _strip_pl_diacritics(text: str) -> str:
    """Zamień polskie znaki diakrytyczne na ASCII."""
    return (text or "").translate(_PL_MAP)


def _render_live_sms_counter(
    current_body: str,
    *,
    counter_id: str,
    textarea_placeholder: str = "",
) -> None:
    """Licznik SMS aktualizowany live (input), bez czekania na blur/rerun Streamlit."""
    ascii_msg = _strip_pl_diacritics(current_body or "")
    seg_len = 160
    msg_len = len(ascii_msg)
    segments = (msg_len + seg_len - 1) // seg_len
    remain = seg_len - (msg_len % seg_len or seg_len)
    coding = "GSM-7" if all(ord(c) < 128 for c in ascii_msg) else "Unicode"
    initial_line = (
        f"Długość: {msg_len} znaków • Segmenty: {segments} • "
        f"Pozostało w bieżącym: {remain} • Kodowanie: {coding}"
    )
    html_component(
        f"""
        <div id="sms-live-counter" class="sms-counter">{initial_line}</div>
        <style>
          html, body {{
            margin: 0;
            padding: 0;
            background: transparent;
            overflow: hidden;
          }}
          .sms-counter {{
            text-align: right;
            color: #6b7280;
            font-size: 13px;
            margin-top: 4px;
            font-family: system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;
            white-space: nowrap;
          }}
        </style>
        <script>
        (function() {{
          const COUNTER_ID = {json.dumps(str(counter_id or "sms_counter_live"))};
          const TARGET_PLACEHOLDER = {json.dumps(str(textarea_placeholder or "").strip())};
          const getRootDoc = () => {{
            try {{
              if (window.parent && window.parent.document) return window.parent.document;
            }} catch (e) {{
              /* fallback do własnego iframe, jeśli parent niedostępny */
            }}
            return document;
          }};
          const rootDoc = getRootDoc();
          const counter = document.getElementById("sms-live-counter");
          let boundTextarea = null;
          const plMap = {{
            "ą":"a","ć":"c","ę":"e","ł":"l","ń":"n","ó":"o","ś":"s","ż":"z","ź":"z",
            "Ą":"A","Ć":"C","Ę":"E","Ł":"L","Ń":"N","Ó":"O","Ś":"S","Ż":"Z","Ź":"Z"
          }};
          const toAscii = (txt) => Array.from(String(txt || "")).map((ch) => plMap[ch] || ch).join("");
          const norm = (txt) => toAscii(String(txt || "").trim().toLowerCase());
          const buildLine = (txt) => {{
            const ascii = toAscii(txt || "");
            const chars = Array.from(ascii);
            const msgLen = chars.length;
            const segLen = 160;
            const segments = Math.floor((msgLen + segLen - 1) / segLen);
            const remain = segLen - ((msgLen % segLen) || segLen);
            const coding = chars.every((ch) => (ch.codePointAt(0) || 0) < 128) ? "GSM-7" : "Unicode";
            return `Długość: ${{msgLen}} znaków • Segmenty: ${{segments}} • Pozostało w bieżącym: ${{remain}} • Kodowanie: ${{coding}}`;
          }};
          const isVisible = (el) => !!el && el.offsetParent !== null;
          const pickTargetTextarea = () => {{
            const allVisible = Array.from(rootDoc.querySelectorAll("textarea")).filter(isVisible);
            if (!allVisible.length) return null;
            if (TARGET_PLACEHOLDER) {{
              const byPlaceholder = allVisible.filter((ta) => String(ta.getAttribute("placeholder") || "").trim() === TARGET_PLACEHOLDER);
              if (byPlaceholder.length) return byPlaceholder[byPlaceholder.length - 1];
            }}
            const byLabel = allVisible.filter((ta) => norm(ta.getAttribute("aria-label")) === "tresc wiadomosci");
            if (byLabel.length) return byLabel[byLabel.length - 1];
            allVisible.sort((a, b) => (b.offsetWidth * b.offsetHeight) - (a.offsetWidth * a.offsetHeight));
            return allVisible[0];
          }};
          const renderFromText = (txt) => {{
            if (!counter) return false;
            counter.textContent = buildLine(txt || "");
            return true;
          }};
          const onInput = () => {{
            if (!boundTextarea) return;
            renderFromText(boundTextarea.value || "");
          }};
          const bindAndRefresh = () => {{
            const ta = pickTargetTextarea();
            if (!counter || !ta) return false;
            if (boundTextarea !== ta) {{
              if (boundTextarea) {{
                boundTextarea.removeEventListener("input", onInput);
                boundTextarea.removeEventListener("keyup", onInput);
                boundTextarea.removeEventListener("change", onInput);
              }}
              boundTextarea = ta;
              boundTextarea.addEventListener("input", onInput, {{ passive: true }});
              boundTextarea.addEventListener("keyup", onInput, {{ passive: true }});
              boundTextarea.addEventListener("change", onInput, {{ passive: true }});
            }}
            return renderFromText(boundTextarea.value || "");
          }};
          try {{
            window.__apSmsCounterIntervals = window.__apSmsCounterIntervals || {{}};
            const prev = window.__apSmsCounterIntervals[COUNTER_ID];
            if (prev) window.clearInterval(prev);
            bindAndRefresh();
            window.setTimeout(bindAndRefresh, 40);
            window.setTimeout(bindAndRefresh, 120);
            window.setTimeout(bindAndRefresh, 260);
            window.__apSmsCounterIntervals[COUNTER_ID] = window.setInterval(bindAndRefresh, 220);
          }} catch (e) {{
            /* no-op */
          }}
        }})();
        </script>
        """,
        height=28,
    )


def _safe_name(ln: str, fn: str) -> str:
    base = _strip_pl_diacritics(f"{(ln or '').strip()}-{(fn or '').strip()}").lower()
    base = re.sub(r"[^a-z0-9\-]+", "", base.replace(" ", "-"))
    return base.strip("-") or "osoba"

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

def _mark_email_subject_edited():
    """Ustaw znacznik, że użytkownik ręcznie zmienił temat."""
    st.session_state._email_dirty = True

def _render_subject(user_subject: Optional[str], fn_gen: str, ln_gen: str) -> str:
    """
    Zwraca finalny temat e-maila w sposób odporny na dublowanie „dla …”.
    Zasady:
    - Jeśli są placeholdery {fn_gen}/{ln_gen} → podstaw i zwróć.
    - W przeciwnym razie utnij wszystko od „ dla …” (jeśli występuje) i dopnij
      aktualne „dla <fn_gen> <ln_gen>”.
    """
    s = (user_subject or "").strip()
    if not s:
        s = "Prośba o wypełnienie ankiety"

    # 1) obsługa placeholderów
    if "{fn_gen}" in s or "{ln_gen}" in s:
        try:
            return s.format(fn_gen=fn_gen, ln_gen=ln_gen)
        except Exception:
            # gdyby format się wysypał, spadamy do normalizacji poniżej
            pass

    # 2) jeśli temat ma już „dla ...” (np. z poprzedniej osoby) → utnij ogon
    s = re.sub(r"\s+dla\s+.*$", "", s, flags=re.IGNORECASE).strip()

    # 3) dołącz bieżące imię+nazwisko (dopełniacz)
    return f"{s} dla {fn_gen} {ln_gen}".strip()


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

    if status == "revoked":
        return "⛔"
    if row.get("rejected_at"):
        return "⛔"
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


def _can_resend_row(row: Dict) -> bool:
    status = str(row.get("status") or "").strip().lower()
    if status == "revoked":
        return False
    if row.get("completed_at") or row.get("rejected_at"):
        return False
    if not str(row.get("token") or "").strip():
        return False
    return True


def _mark_sms_failed(sb, sms_id: str, error_text: str) -> None:
    sb.table("sms_messages").update(
        {"status": "failed", "error_text": str(error_text or "")}
    ).eq("id", sms_id).execute()


def _mark_email_failed(sb, email_id: str, error_text: str) -> None:
    sb.table("email_logs").update(
        {"status": "failed", "error_text": str(error_text or "")}
    ).eq("id", email_id).execute()


def _resend_sms_row(sb, row: Dict, slug: str) -> Tuple[bool, str]:
    sms_id = str(row.get("id") or "").strip()
    phone = str(row.get("phone") or "").strip()
    token = str(row.get("token") or "").strip()
    body = str(row.get("body") or "").strip()
    if not sms_id or not phone or not token:
        return False, "Brak danych rekordu (id/telefon/token)."

    try:
        api_token, sender, base_url = _sms_env()
    except Exception as e:
        return False, str(e)

    if not body:
        fallback_link = _build_link(base_url, slug, token)
        body = f"Link do ankiety: {fallback_link}"
    ok, provider_id, err = send_sms(
        api_token=api_token,
        to_phone=phone,
        text=_strip_pl_diacritics(body),
        sender=sender,
    )
    if ok:
        mark_sms_sent(sb, sms_id=sms_id, provider_message_id=provider_id or "")
        return True, ""
    _mark_sms_failed(sb, sms_id=sms_id, error_text=err or "unknown error")
    return False, str(err or "unknown error")


def _resend_email_row(sb, row: Dict, slug: str, fn_gen: str, ln_gen: str) -> Tuple[bool, str]:
    email_id = str(row.get("id") or "").strip()
    to_email = str(row.get("email") or "").strip()
    token = str(row.get("token") or "").strip()
    subject = str(row.get("subject") or "").strip()
    text = str(row.get("text") or "").strip()
    if not email_id or not to_email or not token:
        return False, "Brak danych rekordu (id/e-mail/token)."

    try:
        host, port, user, pwd, secure, from_email, from_name, base_url = _email_env()
    except Exception as e:
        return False, str(e)

    if not text:
        fallback_link = _build_link(base_url, slug, token)
        text = f"Link do ankiety: {fallback_link}"
    subject = _render_subject(subject or "Prośba o wypełnienie ankiety", fn_gen, ln_gen)
    ok, message_id, err = send_email(
        host=host,
        port=port,
        username=user,
        password=pwd,
        secure=secure,
        from_email=from_email,
        from_name=from_name,
        to_email=to_email,
        subject=subject,
        text=text,
    )
    if ok:
        mark_email_sent(sb, email_id=email_id, provider_message_id=message_id or "")
        return True, ""
    _mark_email_failed(sb, email_id=email_id, error_text=err or "unknown error")
    return False, str(err or "unknown error")


def _revoke_token_access(sb, *, table_name: str, row_id: str, token: str) -> Tuple[bool, str]:
    """
    Unieważnij dostęp dla konkretnego tokenu.
    Priorytet:
    1) rejected_at (gdy kolumna istnieje),
    2) fallback przez RPC mark_token_completed (blokada tokenu w ankiecie),
    3) completed_at (gdy dostępna kolumna).
    """
    rid = str(row_id or "").strip()
    tok = str(token or "").strip()
    if not rid or not tok:
        return False, "Brak danych rekordu (id/token)."

    now_iso = pd.Timestamp.utcnow().isoformat()
    last_err: Optional[Exception] = None

    status_marked = False

    for payload in (
        {"rejected_at": now_iso, "status": "revoked"},
        {"status": "revoked"},
    ):
        try:
            sb.table(table_name).update(payload).eq("id", rid).execute()
            status_marked = True
            break
        except Exception as exc:
            last_err = exc

    try:
        sb.rpc("mark_token_completed", {"p_token": tok}).execute()
        return True, ""
    except Exception as exc:
        last_err = exc

    if status_marked:
        return True, ""

    for payload in (
        {"completed_at": now_iso, "status": "revoked"},
        {"completed_at": now_iso},
    ):
        try:
            sb.table(table_name).update(payload).eq("id", rid).execute()
            return True, ""
        except Exception as exc:
            last_err = exc

    return False, str(last_err or "Nie udało się unieważnić tokenu.")


def _revoke_sms_row(sb, row: Dict) -> Tuple[bool, str]:
    sms_id = str(row.get("id") or "").strip()
    token = str(row.get("token") or "").strip()
    return _revoke_token_access(sb, table_name="sms_messages", row_id=sms_id, token=token)


def _revoke_email_row(sb, row: Dict) -> Tuple[bool, str]:
    email_id = str(row.get("id") or "").strip()
    token = str(row.get("token") or "").strip()
    return _revoke_token_access(sb, table_name="email_logs", row_id=email_id, token=token)


def _logs_dataframe(sb, study_id: str, mode: str, cache_bust: Optional[int] = None) -> pd.DataFrame:
    """
    mode: 'sms' | 'email'
    """
    rows = (list_sms_for_study if mode == "sms" else list_email_for_study)(sb, study_id) or []

    def _is_revoked(row: Dict[str, Any]) -> bool:
        status_txt = str(row.get("status") or "").strip().lower()
        return bool(row.get("rejected_at")) or status_txt == "revoked"

    def _revoked_at(row: Dict[str, Any]) -> str:
        if row.get("rejected_at"):
            return _fmt_dt(row.get("rejected_at"))
        status_txt = str(row.get("status") or "").strip().lower()
        if status_txt != "revoked":
            return ""
        for key in ("updated_at", "status_changed_at", "completed_at", "created_at"):
            txt = _fmt_dt(row.get(key))
            if txt:
                return txt
        return ""

    def _dur_str(click_iso, done_iso) -> str:
        """mm:ss + 🔴 jeśli < 2 min."""
        try:
            c1 = pd.to_datetime(click_iso, utc=True)
            c2 = pd.to_datetime(done_iso,  utc=True)
            if pd.isna(c1) or pd.isna(c2):
                return ""
            sec = int((c2 - c1).total_seconds())
            mm, ss = divmod(max(0, sec), 60)
            return f"{mm:02d}:{ss:02d}" + (" 🔴" if sec < 120 else "")
        except Exception:
            return ""

    out: List[Dict[str, str]] = []
    for r in rows:
        status_txt = str(r.get("status") or "").lower()
        revoked = _is_revoked(r)
        out.append(
            {
                "Data": _fmt_dt(r.get("created_at") or r.get("created_at_pl")),
                ("Telefon" if mode == "sms" else "E-mail"): r.get("phone", "") if mode == "sms" else r.get("email", ""),
                "Status": _status_icon(r),
                "Czas wyp.": _dur_str(r.get("clicked_at"), r.get("completed_at")),
                "Wysłano": "✓" if status_txt in ("sent", "delivered") else "",
                "Kliknięto": _fmt_dt(r.get("clicked_at")),
                "Rozpoczęto": _fmt_dt(r.get("started_at")),
                "Zakończono": "" if revoked else _fmt_dt(r.get("completed_at")),
                "Usunięto": _revoked_at(r) if revoked else "",
                "Błąd": "✖" if status_txt == "failed" else "",
            }
        )
    cols = ["Data", ("Telefon" if mode == "sms" else "E-mail"), "Status", "Czas wyp.", "Wysłano",
            "Kliknięto", "Rozpoczęto", "Zakończono", "Usunięto", "Błąd"]
    return pd.DataFrame(out, columns=cols)



def _df_to_xlsx_bytes(
    df: pd.DataFrame,
    sheet_name: str = "Statusy",
    borders: str = "none"  # "none" = brak ramek (domyślnie), "all" = ramki w całej tabeli (bez nagłówka)
) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as wr:
        # Zapis danych
        df.to_excel(wr, index=False, sheet_name=sheet_name)
        ws = wr.sheets[sheet_name]
        book = wr.book

        # Format nagłówka – BEZ OBRAMOWAŃ
        header_fmt = book.add_format({
            "bold": True,
            "bg_color": "#f3f4f6",
            "font_color": "#111111",
            "align": "left",
            "valign": "vcenter",
            "border": 0
        })

        # Format komórek – zależny od przełącznika
        cell_fmt = book.add_format({
            "border": 1 if str(borders).lower() == "all" else 0
        })

        # Nadpisz nagłówki, aby dostały nasz format (bez ramek)
        for col, title in enumerate(df.columns):
            ws.write(0, col, title, header_fmt)

        # Sformatuj wszystkie komórki danych jednym strzałem
        nrows, ncols = df.shape
        if nrows and ncols:
            # nadaj format zarówno komórkom niepustym, jak i pustym
            ws.conditional_format(1, 0, nrows, ncols - 1, {"type": "no_blanks", "format": cell_fmt})
            ws.conditional_format(1, 0, nrows, ncols - 1, {"type": "blanks", "format": cell_fmt})

        # Szerokości kolumn – jak wcześniej
        for i, col in enumerate(df.columns):
            maxlen = df[col].astype(str).map(len).max()
            try:
                maxlen = int(maxlen) if pd.notna(maxlen) else 0
            except Exception:
                maxlen = 0
            width = max(8, min(36, int(maxlen * 0.9 + 4)))
            ws.set_column(i, i, width)

    return buf.getvalue()


def _df_to_pdf_bytes(df: pd.DataFrame, title: str = "Statusy") -> bytes | None:
    try:
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        font_path = os.path.join("assets", "DejaVuSans.ttf")
        font_bold_path = os.path.join("assets", "DejaVuSans-Bold.ttf")

        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont("DejaVuSans", font_path))
            base_font = "DejaVuSans"

            # jeśli masz plik pogrubienia – użyj go w tytule
            if os.path.exists(font_bold_path):
                pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", font_bold_path))
                title_font = "DejaVuSans-Bold"
            else:
                title_font = base_font
        else:
            # fallback (brak pełnych polskich znaków)
            base_font = "Helvetica"
            title_font = base_font

    except Exception:
        return None

    # Wersja do PDF: status jako tekst (bez emoji), żeby uniknąć „krzaczków”.
    def _status_to_text(s: str) -> str:
        s = (s or "").strip()
        return {
            "📤": "wysłano",
            "📬": "doręczono",
            "🔗": "kliknięto",
            "🏁": "rozpoczęto",
            "✅": "zakończono",
            "⛔": "usunięto",
            "🚫": "nie spełnia warunków",
            "✖": "błąd",
            "⏳": "w kolejce",
            "•":  "inny",
        }.get(s, s)

    df_pdf = df.copy()
    if "Status" in df_pdf.columns:
        df_pdf["Status"] = df_pdf["Status"].map(_status_to_text)
    if "Czas wyp." in df_pdf.columns:
        df_pdf["Czas wyp."] = df_pdf["Czas wyp."].astype(str).str.replace("🔴", "", regex=False)

    data = [list(df_pdf.columns)] + df_pdf.astype(str).values.tolist()

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=24, rightMargin=24, topMargin=24, bottomMargin=24
    )
    styles = getSampleStyleSheet()

    # Tytuł musi używać fontu z polskimi znakami
    from reportlab.lib.styles import ParagraphStyle
    title_style = ParagraphStyle(
        "TitleUnicode",
        parent=styles["Heading3"],
        fontName=("title_font" in locals() and title_font) or base_font  # DejaVuSans-Bold jeśli jest
    )

    table = Table(data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#f3f4f6")),
        ("TEXTCOLOR",  (0,0), (-1,0), colors.HexColor("#111111")),
        ("GRID",       (0,0), (-1,-1), 0.25, colors.HexColor("#d1d5db")),
        ("FONTNAME",   (0,0), (-1,-1), base_font),
        ("FONTSIZE",   (0,0), (-1,-1), 9),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#fafafa")]),
        ("ALIGN", (0,0), (-1,-1), "LEFT"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
    ]))

    story = [Paragraph(title, title_style), Spacer(1, 8), table]
    doc.build(story)
    return buf.getvalue()



def _auto_col_widths(df: pd.DataFrame) -> dict[str, int]:
    """Węższe, bezpieczne szerokości; działa też dla pustych DF."""
    widths: dict[str, int] = {}
    if df is None or df.empty:
        # minimalne szerokości nagłówków
        return {c: 120 for c in (df.columns if df is not None else [])}
    for c in df.columns:
        ser = df[c].astype(str)
        max_in_col = ser.map(len).max()
        try:
            max_in_col = int(max_in_col) if pd.notna(max_in_col) else 0
        except Exception:
            max_in_col = 0
        maxlen = max(len(str(c)), max_in_col)
        widths[c] = max(90, min(360, int(maxlen * 6 + 18)))  # węższy przelicznik
    return widths


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
        st.session_state.setdefault("_e_wrap_w",
                                    int(_e.get("wrap_w", EMAIL_LEFT + EMAIL_WIDTH + 60)))
        st.session_state.setdefault("_e_wrap_h",
                                    int(_e.get("wrap_h", EMAIL_TOP + EMAIL_HEIGHT + 100)))
        st.session_state.setdefault("_e_top", int(_e.get("top", EMAIL_TOP)))
        st.session_state.setdefault("_e_left", int(_e.get("left", EMAIL_LEFT)))
        st.session_state.setdefault("_e_w", int(_e.get("w", EMAIL_WIDTH)))
        st.session_state.setdefault("_e_h", int(_e.get("h", EMAIL_HEIGHT)))
        st.session_state.setdefault("_e_pad", int(_e.get("pad", 18)))
        st.session_state.setdefault("_e_pad_top", int(_e.get("pad_top", 18)))
        # nowość: możliwość korekty marginesu tytułu (może być ujemny)
        st.session_state.setdefault("_e_subj_mt", int(_e.get("subj_mt", 0)))
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

    flash_key = "sendlink_flash_message"
    flash_msg = st.session_state.pop(flash_key, None)
    if flash_msg:
        st.success(str(flash_msg))


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
    recipients_key_prefix = "sendlink_recipients"
    recipients_nonce_key = "sendlink_recipients_widget_nonce"
    clear_recipients_flag_key = "sendlink_clear_recipients_pending"
    if recipients_nonce_key not in st.session_state:
        st.session_state[recipients_nonce_key] = 0
    if st.session_state.pop(clear_recipients_flag_key, False):
        st.session_state[recipients_nonce_key] = int(st.session_state.get(recipients_nonce_key, 0)) + 1
    recipients_widget_key = f"{recipients_key_prefix}_{int(st.session_state.get(recipients_nonce_key, 0))}"
    recipients = st.text_area(
        "Odbiorcy",
        key=recipients_widget_key,
        placeholder=placeholder,
        height=100,
        label_visibility="collapsed",
    )


    # ── Treść (podgląd) ───────────────────────────────────────────────────────
    ln = study.get("last_name_nom") or study.get("last_name") or ""
    fn = study.get("first_name_nom") or study.get("first_name") or ""
    ln_gen = study.get("last_name_gen") or ln
    fn_gen = study.get("first_name_gen") or fn

    # Temat (e-mail) – zawsze wylicz na podstawie bieżącej osoby
    base_tpl = st.secrets.get("EMAIL_SUBJECT", "Prośba o wypełnienie ankiety")
    subject_tpl = _ensure_name_placeholders(base_tpl)
    auto_subject = subject_tpl.format(fn_gen=fn_gen, ln_gen=ln_gen)

    # Inicjalizacja znacznika "czy użytkownik edytował temat ręcznie"
    if "_email_dirty" not in st.session_state:
        st.session_state._email_dirty = False

    # Inicjalizacja pierwszej wartości tematu
    if "email_subject" not in st.session_state:
        st.session_state.email_subject = auto_subject

    # Zapamiętujemy poprzednie wartości, aby wykryć zmiany
    prev_person = st.session_state.get("_email_last_person_label")
    prev_method = st.session_state.get("_email_last_method")

    changed_person = (prev_person is not None and label != prev_person)
    changed_to_email = (method == "E-mail" and prev_method == "SMS")

    # Jeśli użytkownik NIE edytował ręcznie, to aktualizuj temat przy zmianie osoby
    # lub gdy wracamy z SMS do E-mail.
    if (changed_person or changed_to_email) and not st.session_state._email_dirty:
        st.session_state.email_subject = auto_subject

    # Gdy temat z jakiegoś powodu jest pusty – uzupełnij automatem
    if not (st.session_state.email_subject or "").strip():
        st.session_state.email_subject = auto_subject

    # Zapisz aktualny stan do porównań w kolejnych renderach
    st.session_state._email_last_person_label = label
    st.session_state._email_last_method = method

    if method == "E-mail":
        st.text_input(
            "Temat (e-mail)",
            key="email_subject",
            label_visibility="visible",
            on_change=_mark_email_subject_edited  # <- zaznacz, że użytkownik ruszył temat
        )

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

    # ➜ dwa różne domyślne szablony – zależne od "method"
    if method == "E-mail":
        default_body = (
            f"Zwracamy się z prośbą o wypełnienie ankiety w badaniu realizowanym na prośbę {fn_gen} {ln_gen}."
            f"\n\nLink do ankiety: {link_preview}"
            f"\n\nDziękujemy,"
            f"\nZespół badawczy Badania.pro®"
        )
    else:  # SMS
        default_body = (
            f"Zwracamy sie z prosba o wypelnienie ankiety dla {fn_gen} {ln_gen}."
            f"\n\nLink do ankiety: {link_preview}"
            f"\n\nDziekujemy!"
        )

    # Personalizacja/reset gdy zmienisz osobę LUB tryb (SMS/E-mail),
    # ale tylko jeśli użytkownik nie edytował pola ręcznie.
    if "sms_body" not in st.session_state:
        st.session_state.sms_body = default_body
        st.session_state.auto_sms_template = default_body
        st.session_state.last_person_label = label
        st.session_state.last_method = method
    else:
        changed_person = (label != st.session_state.get("last_person_label"))
        changed_method = (method != st.session_state.get("last_method"))
        if changed_person or changed_method:
            if st.session_state.sms_body == st.session_state.get("auto_sms_template"):
                st.session_state.sms_body = default_body
            st.session_state.auto_sms_template = default_body
            st.session_state.last_person_label = label
            st.session_state.last_method = method
        else:
            st.session_state.auto_sms_template = default_body

    cols = st.columns([3, 3], gap="medium")
    with cols[0]:
        st.markdown('<div class="field-label">Treść wiadomości:</div>', unsafe_allow_html=True)
        body_placeholder = "Wpisz treść wiadomości..."
        st.text_area(
            "Treść wiadomości",
            key="sms_body",
            height=240,
            label_visibility="collapsed",
            placeholder=body_placeholder,
        )

        # licznik tylko dla SMS; e-mail nie pokazuje licznika i zachowuje polskie znaki
        if method == "SMS":
            _render_live_sms_counter(
                str(st.session_state.get("sms_body") or ""),
                counter_id="sendlink_sms_counter_live",
                textarea_placeholder=body_placeholder,
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
        msg_preview_html = msg_preview.replace("\n", "<br/>")

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
                      <div class="mock-screen v2">{msg_preview_html}</div>
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
                           {msg_preview_html}
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
                _e_top = st.number_input("Top (px)",
                                         value=int(st.session_state.get("_e_top", EMAIL_TOP)),
                                         step=1)
                _e_left = st.number_input("Left (px)",
                                          value=int(st.session_state.get("_e_left", EMAIL_LEFT)),
                                          step=1)
                _e_w = st.number_input("Szerokość ekranu (px)",
                                       value=int(st.session_state.get("_e_w", EMAIL_WIDTH)), step=1)
                _e_h = st.number_input("Wysokość ekranu (px)",
                                       value=int(st.session_state.get("_e_h", EMAIL_HEIGHT)),
                                       step=1)

                # paddingi + offset tytułu
                _e_pad_top = st.number_input("Padding góra (px)",
                                             value=int(st.session_state.get("_e_pad_top", 18)),
                                             step=1)
                _e_pad = st.number_input("Padding wewnątrz (lewy/prawy/dolny) (px)",
                                         value=int(st.session_state.get("_e_pad", 18)), step=1)
                _e_subj_mt = st.number_input("Offset tytułu (px; może być ujemny)",
                                             value=int(st.session_state.get("_e_subj_mt", 0)),
                                             step=1)

                st.session_state.update(
                    _e_wrap_w=_e_wrap_w, _e_wrap_h=_e_wrap_h,
                    _e_top=_e_top, _e_left=_e_left, _e_w=_e_w, _e_h=_e_h,
                    _e_pad=_e_pad, _e_pad_top=_e_pad_top, _e_subj_mt=_e_subj_mt
                )

                # zapisz / odczytaj
                c1, c2, _ = st.columns([3, 3, 1])
                if c1.button("💾 Zapisz jako domyślne", use_container_width=True):
                    prefs = _load_mockup_prefs()
                    prefs.setdefault("email", {})
                    prefs["email"] = {
                        "wrap_w": int(st.session_state._e_wrap_w),
                        "wrap_h": int(st.session_state._e_wrap_h),
                        "top": int(st.session_state._e_top),
                        "left": int(st.session_state._e_left),
                        "w": int(st.session_state._e_w),
                        "h": int(st.session_state._e_h),
                        "pad": int(st.session_state._e_pad),
                        "pad_top": int(st.session_state._e_pad_top),
                        "subj_mt": int(st.session_state._e_subj_mt),
                    }
                    _save_mockup_prefs(prefs)
                    st.success("Zapisano jako domyślne.")

                if c2.button("↩ Przywróć zapisane", use_container_width=True):
                    prefs = _load_mockup_prefs()
                    e = prefs.get("email", {})
                    if e:
                        st.session_state._e_wrap_w = int(
                            e.get("wrap_w", st.session_state._e_wrap_w))
                        st.session_state._e_wrap_h = int(
                            e.get("wrap_h", st.session_state._e_wrap_h))
                        st.session_state._e_top = int(e.get("top", st.session_state._e_top))
                        st.session_state._e_left = int(e.get("left", st.session_state._e_left))
                        st.session_state._e_w = int(e.get("w", st.session_state._e_w))
                        st.session_state._e_h = int(e.get("h", st.session_state._e_h))
                        st.session_state._e_pad = int(e.get("pad", st.session_state._e_pad))
                        st.session_state._e_pad_top = int(
                            e.get("pad_top", st.session_state._e_pad_top))
                        st.session_state._e_subj_mt = int(
                            e.get("subj_mt", st.session_state._e_subj_mt))
                        st.experimental_rerun()
                    else:
                        st.info("Brak zapisanych ustawień – najpierw użyj „Zapisz jako domyślne”.")

            # temat do podglądu – bez duplikowania imienia/nazwiska
            _subject_preview = _render_subject(st.session_state.get("email_subject") or auto_subject, fn_gen, ln_gen)



            if data_url:
                st.markdown(
                    f"""
                        <div class="mock-wrap">
                          <div class="mock-bg-email"></div>
                          <div class="mock-screen-email">
                            <div class="mock-email-subj">{_subject_preview}</div>
                            <div class="email-body">{msg_preview_html}</div>
                          </div>
                        </div>
                        <style>
                          .mock-wrap{{
                            position:relative;
                            width:{st.session_state._e_wrap_w}px;
                            height:{st.session_state._e_wrap_h}px;
                          }}
                          .mock-bg-email{{
                            position:absolute; inset:0;
                            background-image:url('{data_url}');
                            background-size:contain; background-repeat:no-repeat; background-position:center top;
                          }}
                          .mock-screen-email{{
                            position:absolute;
                            top:{st.session_state._e_top}px; left:{st.session_state._e_left}px;
                            width:{st.session_state._e_w}px; height:{st.session_state._e_h}px;
                            background:#fff; border:1px solid #e5e7eb; border-radius:2px;
                            padding:{st.session_state._e_pad_top}px {st.session_state._e_pad}px {st.session_state._e_pad}px {st.session_state._e_pad}px; overflow:auto;
                            font:13.5px/1.5 system-ui,-apple-system, Segoe UI, Roboto, Arial, sans-serif; color:#111;
                            white-space:pre-wrap; overflow-wrap:break-word; word-break:normal; word-break:break-word; hyphens:auto; line-break:auto;
                            text-indent:0;  /* brak wcięcia pierwszej linii */
                          }}
                          .mock-email-subj{{
                            opacity:.7;
                            margin:{st.session_state._e_subj_mt}px 0 8px 0;  /* sterujesz suwakiem */
                          }}
                          .email-body, .email-body *{{
                            margin-top:0;  /* usuń domyślne górne marginesy pierwszego akapitu */
                            text-indent:0;
                          }}
                        </style>

                    """,
                    unsafe_allow_html=True,
                )
            else:
                # (fallback)
                _subject_preview = _render_subject(st.session_state.get("email_subject") or auto_subject, fn_gen, ln_gen)

                st.markdown(
                    f"""<div style="border:1px solid #e5e7eb;border-radius:8px;padding:18px;background:#fff;box-shadow:0 1px 2px rgb(0 0 0/0.04);font:13.5px/1.5 system-ui;">
                        <div style="opacity:.7;margin-bottom:8px">{_subject_preview}</div>
                        {msg_preview_html}
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
            st.session_state[clear_recipients_flag_key] = True
            st.session_state[flash_key] = f"Wysłano {sent_ok} / {len(phones)}."
            st.rerun()

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
                (st.session_state.get("email_subject") or auto_subject or st.secrets.get(
                    "EMAIL_SUBJECT", "Prośba o wypełnienie ankiety")),
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
            st.session_state[clear_recipients_flag_key] = True
            st.session_state[flash_key] = f"Wysłano {sent_ok} / {len(emails)}."
            st.rerun()

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
    wanted_cols = ["Data", ("Telefon" if mode == "sms" else "E-mail"), "Status", "Czas wyp.",
                   "Wysłano",
                   "Kliknięto", "Rozpoczęto", "Zakończono", "Usunięto", "Błąd"]
    for c in wanted_cols:
        if c not in df_logs.columns:
            df_logs[c] = ""
    df_logs = df_logs[wanted_cols]

    # ikony wg surowych danych
    raw_rows = (list_sms_for_study if mode == "sms" else list_email_for_study)(sb,
                                                                               study["id"]) or []

    def _status_icon_fixed(row: Dict) -> str:
        status = (row.get("status") or "").lower()
        if status == "revoked": return "⛔"
        if row.get("rejected_at"): return "⛔"
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
    can_resend_flags = [_can_resend_row(r) for r in raw_rows]
    if len(can_resend_flags) == len(df_logs):
        df_logs["Ponów"] = ["🔁" if flag else "" for flag in can_resend_flags]
    else:
        df_logs["Ponów"] = ""

    # wąska tabela
    st.markdown(
        """
        <style>.narrow-table { max-width: 1120px; margin: 0 auto; }</style>
        """,
        unsafe_allow_html=True,
    )
    # auto-szerokości na podstawie zawartości
    widths = _auto_col_widths(df_logs)
    col_cfg = {
        col: cc.Column(width=widths.get(col, 100))
        for col in df_logs.columns
    }
    table_height = max(220, min(760, 92 + len(df_logs.index) * 38))

    st.markdown('<div class="narrow-table">', unsafe_allow_html=True)
    st.dataframe(df_logs, hide_index=True, column_config=col_cfg, height=table_height)
    st.markdown('</div>', unsafe_allow_html=True)

    resend_rows = [r for r in raw_rows if _can_resend_row(r)]
    if resend_rows:
        st.caption(
            "🔁 Możesz ponowić wysyłkę dla rekordu (bez tworzenia nowego tokenu i bez zmiany linku) "
            "lub ⛔ unieważnić ten konkretny link."
        )
        label_to_row: Dict[str, Dict] = {}
        for r in resend_rows:
            recipient = str(r.get("phone") or "") if mode == "sms" else str(r.get("email") or "")
            created_at = _fmt_dt(r.get("created_at") or r.get("created_at_pl"))
            token = str(r.get("token") or "")
            status_txt = str(r.get("status") or "").lower()
            short_token = f"...{token[-6:]}" if len(token) > 6 else token
            label_r = f"{recipient} • {created_at} • status: {status_txt} • token: {short_token}"
            label_to_row[label_r] = r
        chosen_resend = st.selectbox(
            "Wybierz rekord do ponownej wysyłki",
            list(label_to_row.keys()),
            key=f"resend_pick_{mode}_{study['id']}",
        )
        c_resend, c_revoke = st.columns([1, 1], gap="small")
        if c_resend.button("🔁 Wyślij ponownie (ten sam link)", key=f"resend_btn_{mode}_{study['id']}"):
            picked = label_to_row.get(chosen_resend) or {}
            if mode == "sms":
                ok, err = _resend_sms_row(sb, picked, slug=slug)
            else:
                ok, err = _resend_email_row(sb, picked, slug=slug, fn_gen=fn_gen, ln_gen=ln_gen)
            if ok:
                st.success("Ponowiono wysyłkę dla wybranego rekordu.")
                st.rerun()
            else:
                st.error(f"Nie udało się ponowić wysyłki: {err}")
        if c_revoke.button("⛔ Usuń dostęp (unieważnij link)", key=f"revoke_btn_{mode}_{study['id']}"):
            picked = label_to_row.get(chosen_resend) or {}
            if mode == "sms":
                ok, err = _revoke_sms_row(sb, picked)
            else:
                ok, err = _revoke_email_row(sb, picked)
            if ok:
                st.success("Dostęp został unieważniony dla wybranego rekordu.")
                st.rerun()
            else:
                st.error(f"Nie udało się unieważnić dostępu: {err}")

    # Eksport
    who = _safe_name(ln, fn)
    prefix = 'sms' if mode == 'sms' else 'email'
    export_df = df_logs.drop(columns=["Ponów"], errors="ignore")
    xlsx_bytes = _df_to_xlsx_bytes(export_df, sheet_name=("SMS" if mode == "sms" else "EMAIL"))
    c1, c2 = st.columns([1, 1])
    c1.download_button(
        "📊 Eksport XLSX",
        data=xlsx_bytes,
        file_name=f"statusy_{prefix}_{who}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )
    pdf_bytes = _df_to_pdf_bytes(export_df, title=f"Statusy – {'SMS' if mode == 'sms' else 'E-mail'} z wysyłki dla {fn_gen} {ln_gen}")
    if pdf_bytes:
        c2.download_button(
            "📄 Eksport PDF",
            data=pdf_bytes,
            file_name=f"statusy_{prefix}_{who}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    else:
        c2.caption("PDF: zainstaluj pakiet `reportlab` na serwerze, aby włączyć eksport.")

    # Legenda
    if mode == "sms":
        legenda = """
          📤 – SMS wysłany<br>
          📬 – SMS doręczony (jeśli provider zwróci potwierdzenie)<br>
          🔗 – Odbiorca kliknął w link<br>
          🏁 – Ankieta rozpoczęta<br>
          ✅ – Ankieta zakończona<br>
          ⛔ – Dostęp usunięty (link unieważniony)<br>
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
          ⛔ – Dostęp usunięty (link unieważniony)<br>
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
