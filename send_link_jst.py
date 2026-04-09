from __future__ import annotations

from io import BytesIO
from typing import Any, Callable, Dict, List, Optional, Tuple
import re
import time

import pandas as pd
import streamlit as st
from streamlit import column_config as cc

from db_utils import get_supabase
from db_jst_utils import fetch_jst_studies
from smsapi_client import send_sms
from email_client import send_email
from utils import make_token
from send_link import (
    _auto_col_widths,
    _df_to_xlsx_bytes,
    _df_to_pdf_bytes,
    _load_mockup_prefs,
    _mockup_css_bg,
    _save_mockup_prefs,
    _strip_pl_diacritics,
    EMAIL_HEIGHT,
    EMAIL_LEFT,
    EMAIL_MOCKUP_PATH,
    EMAIL_TOP,
    EMAIL_WIDTH,
    MOCKUP_HEIGHT,
    MOCKUP_LEFT,
    MOCKUP_PATH,
    MOCKUP_TOP,
    MOCKUP_WIDTH,
)


_EMAIL_RE = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.I)

class DuplicateJstTokenError(Exception):
    pass


def _is_unique_violation(err: Exception) -> bool:
    msg = (getattr(err, "message", "") or str(err) or "").lower()
    return (
        "23505" in msg
        or "unique" in msg
        or "duplicate" in msg
        or "conflict" in msg
        or "409" in msg
    )


def _create_jst_sms_record(sb, study_id: str, phone: str, text: str, token: str) -> Dict[str, Any]:
    try:
        ins = (
            sb.table("jst_sms_messages")
            .insert(
                {
                    "study_id": study_id,
                    "phone": phone,
                    "body": text,
                    "token": token,
                    "status": "queued",
                }
            )
            .execute()
        )
    except Exception as e:
        if _is_unique_violation(e):
            raise DuplicateJstTokenError("Token already exists") from e
        raise

    if ins.data:
        return ins.data[0]
    raise RuntimeError("Nie udało się zapisać rekordu jst_sms_messages.")


def _mark_jst_sms_sent(sb, sms_id: str, provider_message_id: str) -> None:
    sb.table("jst_sms_messages").update(
        {"status": "sent", "provider_message_id": provider_message_id, "updated_at": pd.Timestamp.utcnow().isoformat()}
    ).eq("id", sms_id).execute()


def _list_jst_sms_for_study(sb, study_id: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    offset = 0
    page_size = 1000
    sid = str(study_id or "").strip()
    if not sid:
        return out
    while True:
        res = (
            sb.table("jst_sms_messages")
            .select("*")
            .eq("study_id", sid)
            .order("created_at", desc=True)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        chunk = res.data or []
        if not chunk:
            break
        out.extend(chunk)
        if len(chunk) < page_size:
            break
        offset += page_size
    return out


def _create_jst_email_record(sb, study_id: str, email: str, subject: str, text: str, token: str) -> Dict[str, Any]:
    try:
        ins = (
            sb.table("jst_email_logs")
            .insert(
                {
                    "study_id": study_id,
                    "email": email,
                    "subject": subject,
                    "text": text,
                    "token": token,
                    "status": "queued",
                }
            )
            .execute()
        )
    except Exception as e:
        if _is_unique_violation(e):
            raise DuplicateJstTokenError("Token already exists") from e
        raise

    if ins.data:
        return ins.data[0]
    raise RuntimeError("Nie udało się zapisać rekordu jst_email_logs.")


def _mark_jst_email_sent(sb, email_id: str, provider_message_id: str) -> None:
    sb.table("jst_email_logs").update(
        {"status": "sent", "provider_message_id": provider_message_id, "updated_at": pd.Timestamp.utcnow().isoformat()}
    ).eq("id", email_id).execute()


def _list_jst_email_for_study(sb, study_id: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    offset = 0
    page_size = 1000
    sid = str(study_id or "").strip()
    if not sid:
        return out
    while True:
        res = (
            sb.table("jst_email_logs")
            .select("*")
            .eq("study_id", sid)
            .order("created_at", desc=True)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        chunk = res.data or []
        if not chunk:
            break
        out.extend(chunk)
        if len(chunk) < page_size:
            break
        offset += page_size
    return out


def _normalize_recipients(raw: str, mode: str) -> List[str]:
    src = (raw or "").replace("\n", ",").replace(";", ",").replace(" ", ",")
    out: List[str] = []
    seen = set()
    for part in [x.strip() for x in src.split(",") if x.strip()]:
        if mode == "sms":
            val = re.sub(r"[^\d+]", "", part)
            if not val:
                continue
        else:
            val = part.lower()
            if not _EMAIL_RE.match(val):
                continue
        if val in seen:
            continue
        seen.add(val)
        out.append(val)
    return out


def _sms_env() -> Tuple[str, Optional[str], str]:
    token = st.secrets.get("SMSAPI_TOKEN", "")
    sender = st.secrets.get("SMS_SENDER", None)
    base_url = (st.secrets.get("JST_SURVEY_BASE_URL", "https://jst.badania.pro") or "").rstrip("/")
    if not token:
        raise RuntimeError("Brak SMSAPI_TOKEN w st.secrets.")
    if not base_url:
        raise RuntimeError("Brak JST_SURVEY_BASE_URL w st.secrets.")
    return token, sender, base_url


def _email_env() -> Tuple[str, int, str, str, str, str, str, str]:
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
    from_name = st.secrets.get("FROM_NAME", "") or st.secrets.get("SMTP_FROM_NAME", "")
    base_url = (st.secrets.get("JST_SURVEY_BASE_URL", "https://jst.badania.pro") or "").rstrip("/")
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
        missing.append("JST_SURVEY_BASE_URL")
    if missing:
        raise RuntimeError("Brak ustawień SMTP/SURVEY w st.secrets: " + ", ".join(missing))
    return host, port, user, pwd, secure, from_email, from_name, base_url


def _build_link(base_url: str, slug: str, token: str) -> str:
    return f"{(base_url or '').rstrip('/')}/{(slug or '').lstrip('/')}?t={token}"


def _status_icon(row: Dict[str, Any]) -> str:
    status = str(row.get("status") or "").lower()
    if row.get("rejected_at"):
        return "🚫"
    if row.get("completed_at"):
        return "✅"
    if row.get("started_at"):
        return "🏁"
    if row.get("clicked_at"):
        return "🔗"
    if status == "failed":
        return "✖"
    if status == "delivered":
        return "📬"
    if status == "sent":
        return "📤"
    if status == "queued":
        return "⏳"
    return "•"


def _fmt_dt(val: Optional[str]) -> str:
    if not val:
        return ""
    try:
        ts = pd.to_datetime(val, errors="coerce", utc=True)
        if pd.isna(ts):
            return ""
        return ts.tz_convert("Europe/Warsaw").strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(val)


def _logs_dataframe(sb, study_id: str, mode: str) -> pd.DataFrame:
    rows = (_list_jst_sms_for_study if mode == "sms" else _list_jst_email_for_study)(sb, study_id) or []

    def _dur_str(click_iso, done_iso) -> str:
        try:
            c1 = pd.to_datetime(click_iso, utc=True)
            c2 = pd.to_datetime(done_iso, utc=True)
            if pd.isna(c1) or pd.isna(c2):
                return ""
            sec = int((c2 - c1).total_seconds())
            mm, ss = divmod(max(0, sec), 60)
            return f"{mm:02d}:{ss:02d}" + (" 🔴" if sec < 120 else "")
        except Exception:
            return ""

    out: List[Dict[str, str]] = []
    for r in rows:
        out.append(
            {
                "Data": _fmt_dt(r.get("created_at") or r.get("created_at_pl")),
                ("Telefon" if mode == "sms" else "E-mail"): r.get("phone", "") if mode == "sms" else r.get("email", ""),
                "Status": _status_icon(r),
                "Czas wyp.": _dur_str(r.get("clicked_at"), r.get("completed_at")),
                "Wysłano": "✓" if str(r.get("status") or "").lower() in ("sent", "delivered") else "",
                "Kliknięto": _fmt_dt(r.get("clicked_at")),
                "Rozpoczęto": _fmt_dt(r.get("started_at")),
                "Zakończono": _fmt_dt(r.get("completed_at")),
                "Nie spełnia": _fmt_dt(r.get("rejected_at")),
                "Błąd": "✖" if str(r.get("status") or "").lower() == "failed" else "",
            }
        )

    cols = [
        "Data",
        ("Telefon" if mode == "sms" else "E-mail"),
        "Status",
        "Czas wyp.",
        "Wysłano",
        "Kliknięto",
        "Rozpoczęto",
        "Zakończono",
        "Nie spełnia",
        "Błąd",
    ]
    return pd.DataFrame(out, columns=cols)


def _default_sms_text(jst_full_gen: str, link_preview: str) -> str:
    jst_full_gen_ascii = _strip_pl_diacritics(str(jst_full_gen or ""))
    return (
        f"Zwracamy sie z prosba o wypelnienie ankiety dla mieszkancow {jst_full_gen_ascii}.\n\n"
        f"Link do ankiety: {link_preview}\n\n"
        "Dziekujemy!"
    )


def _default_email_text(jst_type: str, jst_full_gen: str, jst_full_nom: str, link_preview: str) -> str:
    type_gen = "miasta" if (jst_type or "").lower() == "miasto" else "gminy"
    verb = "powinno działać" if (jst_type or "").lower() == "miasto" else "powinna działać"
    return (
        "Zwracamy się z prośbą o wypełnienie ankiety w badaniu realizowanym "
        f"wśród mieszkańców {jst_full_gen}. W tym badaniu chcemy przekonać się, jakie jest "
        f"Państwa podejście do spraw {type_gen} i oczekiwania dotyczące tego, jak {verb} {jst_full_nom}.\n\n"
        "Wypełnienie ankiety nie powinno zająć więcej niż 5-7 minut.\n\n"
        f"Link do ankiety: {link_preview}\n\n"
        "Dziękujemy,\n"
        "Zespół badawczy Badania.pro®"
    )


def _fake_phone_mockup(text: str) -> str:
    safe = (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")
    return f"""
    <div style="width:220px;height:430px;border:2px solid #d7dee8;border-radius:30px;background:#f8fafc;position:relative;margin:0 auto;">
      <div style="position:absolute;top:18px;left:50%;transform:translateX(-50%);width:64px;height:8px;border-radius:99px;background:#cbd5e1;"></div>
      <div style="position:absolute;top:48px;left:16px;right:16px;bottom:16px;background:#fff;border:1px solid #e2e8f0;border-radius:6px;padding:14px;overflow:auto;font:13px/1.45 system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;">
        {safe}
      </div>
    </div>
    """


def _fake_email_mockup(subject: str, body: str) -> str:
    subj = (subject or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    safe = (body or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br/>")
    return f"""
    <div style="width:390px;height:250px;border:2px solid #d7dee8;border-radius:10px;background:#111827;position:relative;margin:0 auto;">
      <div style="position:absolute;top:10px;left:10px;right:10px;bottom:10px;background:#fff;border-radius:4px;padding:10px 12px;overflow:auto;font:12.5px/1.45 system-ui,-apple-system,Segoe UI,Roboto,Arial,sans-serif;color:#0f172a;">
        <div style="opacity:.75;margin-bottom:8px;">{subj}</div>
        {safe}
      </div>
    </div>
    """


def render(back_btn: Callable[[], None]) -> None:
    sb = get_supabase()
    back_btn()

    st.markdown(
        """
        <style>
          :root{
            --label-font-size: 16px;
            --label-font-weight: 600;
            --label-margin-top: 16px;
            --label-margin-bottom: 9px;
          }
          .field-label{
            font-weight: var(--label-font-weight);
            font-size: var(--label-font-size);
            margin: var(--label-margin-top) 0 var(--label-margin-bottom) 0;
          }
          .sms-counter{ text-align:right; color:#6b7280; font-size:13px; margin-top:4px; }
          .btn-stack{ margin-top:26px; margin-bottom:24px; }
          .btn-stack .btn-reset{ margin-bottom:10px; }
          .btn-stack .btn-send{ margin-top:14px; margin-bottom:26px; }
          .status-top-tight{ margin-top:0 !important; }
          .status-bottom-gap{ height:60px; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    studies = fetch_jst_studies(sb)
    if not studies:
        st.info("Brak badań JST w bazie.")
        return

    options = {
        f"{(s.get('jst_full_nom') or (str(s.get('jst_type', '')).title() + ' ' + str(s.get('jst_name', '')))).strip()} – /{s.get('slug') or ''}": s
        for s in studies
    }

    st.markdown(
        '<div style="font-size:17.5px; font-weight:675; margin-top:20px; margin-bottom:18px;">Wybierz badanie mieszkańców:</div>',
        unsafe_allow_html=True,
    )
    label = st.selectbox(
        "Wybierz badanie",
        options=list(options.keys()),
        label_visibility="collapsed",
        key="sendlink_jst_study",
    )
    study = options[label]

    st.markdown('<div style="font-size:16px; font-weight:600; margin-top:35px; margin-bottom:5px;">Metoda wysyłki</div>', unsafe_allow_html=True)
    method = st.radio("Metoda wysyłki", ["SMS", "E-mail"], horizontal=True, index=0, label_visibility="collapsed")

    st.markdown('<div class="field-label">Odbiorcy</div>', unsafe_allow_html=True)
    recipients = st.text_area(
        "Odbiorcy",
        placeholder=("48500123456, 48600111222" if method == "SMS" else "jan@firma.pl, ola@urzad.gov.pl"),
        height=100,
        label_visibility="collapsed",
    )

    slug = str(study.get("slug") or "").strip()
    jst_type = str(study.get("jst_type") or "miasto").strip().lower()
    jst_full_gen = str(study.get("jst_full_gen") or "").strip()
    jst_full_nom = str(study.get("jst_full_nom") or "").strip()

    preview_key = "jst_send_preview_link"
    preview_study_key = "jst_send_preview_study"
    base_url_preview = (st.secrets.get("JST_SURVEY_BASE_URL", "https://jst.badania.pro") or "").rstrip("/")
    if st.session_state.get(preview_study_key) != str(study.get("id")) or preview_key not in st.session_state:
        st.session_state[preview_key] = _build_link(base_url_preview, slug, make_token(6))
        st.session_state[preview_study_key] = str(study.get("id"))
    link_preview = st.session_state[preview_key]

    default_sms = _default_sms_text(jst_full_gen, link_preview)
    default_email = _default_email_text(jst_type, jst_full_gen, jst_full_nom, link_preview)
    study_id = str(study.get("id") or "")
    default_body = default_sms if method == "SMS" else default_email
    if "jst_send_body" not in st.session_state:
        st.session_state["jst_send_body"] = default_body
        st.session_state["jst_send_method"] = method
        st.session_state["jst_send_last_study"] = study_id
        st.session_state["jst_send_auto_template"] = default_body
    else:
        changed_study = st.session_state.get("jst_send_last_study") != study_id
        changed_method = st.session_state.get("jst_send_method") != method
        if changed_study or changed_method:
            st.session_state["jst_send_body"] = default_body
        st.session_state["jst_send_method"] = method
        st.session_state["jst_send_last_study"] = study_id
        st.session_state["jst_send_auto_template"] = default_body
    reset_to_key = "jst_send_body_reset_to"
    if reset_to_key in st.session_state:
        st.session_state["jst_send_body"] = st.session_state.pop(reset_to_key)

    if method == "E-mail":
        subj_key = "jst_send_subject"
        subj_study_key = "jst_send_subject_study"
        if subj_key not in st.session_state or st.session_state.get(subj_study_key) != str(study.get("id")):
            st.session_state[subj_key] = f"Prośba o wypełnienie ankiety dla mieszkańców {jst_full_gen}"
            st.session_state[subj_study_key] = str(study.get("id"))
        st.text_input("Temat (e-mail)", key=subj_key)

    cols = st.columns([3, 3], gap="medium")
    with cols[0]:
        st.markdown('<div class="field-label">Treść wiadomości:</div>', unsafe_allow_html=True)
        st.text_area("Treść wiadomości", key="jst_send_body", height=240, label_visibility="collapsed")

        if method == "SMS":
            msg_len = len(str(st.session_state.get("jst_send_body") or ""))
            seg_len = 160
            segments = (msg_len + seg_len - 1) // seg_len
            remain = seg_len - (msg_len % seg_len or seg_len)
            st.markdown(
                f'<div class="sms-counter">Długość: {msg_len} znaków • Segmenty: {segments} • Pozostało w bieżącym: {remain}</div>',
                unsafe_allow_html=True,
            )

        st.markdown('<div class="btn-stack">', unsafe_allow_html=True)
        st.markdown('<div class="btn-reset">', unsafe_allow_html=True)
        if st.button("Przywróć domyślną treść", key="jst_send_reset"):
            st.session_state[reset_to_key] = default_sms if method == "SMS" else default_email
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown('<div class="btn-send">', unsafe_allow_html=True)
        send_btn = st.button("Wyślij", key="jst_send_btn", type="primary")
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with cols[1]:
        body_preview = str(st.session_state.get("jst_send_body") or "")
        if method == "SMS":
            msg_preview = _strip_pl_diacritics(body_preview)
            msg_preview_html = msg_preview.replace("\n", "<br/>")
            data_url = _mockup_css_bg(MOCKUP_PATH)
            prefs = _load_mockup_prefs().get("sms", {})

            with st.expander("Dopasuj mockup SMS (ręcznie)", expanded=False):
                _sms_top = st.number_input(
                    "Top (px)",
                    value=int(st.session_state.get("_jst_sms_top", prefs.get("top", MOCKUP_TOP))),
                    step=1,
                    key="_jst_sms_top_input",
                )
                _sms_left = st.number_input(
                    "Left (px)",
                    value=int(st.session_state.get("_jst_sms_left", prefs.get("left", MOCKUP_LEFT))),
                    step=1,
                    key="_jst_sms_left_input",
                )
                _sms_w = st.number_input(
                    "Szerokość (px)",
                    value=int(st.session_state.get("_jst_sms_w", prefs.get("w", MOCKUP_WIDTH))),
                    step=1,
                    key="_jst_sms_w_input",
                )
                _sms_h = st.number_input(
                    "Wysokość (px)",
                    value=int(st.session_state.get("_jst_sms_h", prefs.get("h", MOCKUP_HEIGHT))),
                    step=1,
                    key="_jst_sms_h_input",
                )
                _sms_pad = st.number_input(
                    "Padding wewnątrz (px)",
                    value=int(st.session_state.get("_jst_sms_pad", prefs.get("pad", 50))),
                    step=1,
                    key="_jst_sms_pad_input",
                )

                st.session_state.update(
                    _jst_sms_top=int(_sms_top),
                    _jst_sms_left=int(_sms_left),
                    _jst_sms_w=int(_sms_w),
                    _jst_sms_h=int(_sms_h),
                    _jst_sms_pad=int(_sms_pad),
                )

                c_save, c_restore, _ = st.columns([3, 3, 1])
                if c_save.button("💾 Zapisz jako domyślne", key="jst_sms_mockup_save", use_container_width=True):
                    prefs_all = _load_mockup_prefs()
                    prefs_all.setdefault("sms", {})
                    prefs_all["sms"] = {
                        "top": int(st.session_state.get("_jst_sms_top", MOCKUP_TOP)),
                        "left": int(st.session_state.get("_jst_sms_left", MOCKUP_LEFT)),
                        "w": int(st.session_state.get("_jst_sms_w", MOCKUP_WIDTH)),
                        "h": int(st.session_state.get("_jst_sms_h", MOCKUP_HEIGHT)),
                        "pad": int(st.session_state.get("_jst_sms_pad", 50)),
                    }
                    _save_mockup_prefs(prefs_all)
                    st.success("Zapisano jako domyślne.")
                if c_restore.button("↩ Przywróć zapisane", key="jst_sms_mockup_restore", use_container_width=True):
                    p = _load_mockup_prefs().get("sms", {})
                    if p:
                        st.session_state["_jst_sms_top"] = int(p.get("top", MOCKUP_TOP))
                        st.session_state["_jst_sms_left"] = int(p.get("left", MOCKUP_LEFT))
                        st.session_state["_jst_sms_w"] = int(p.get("w", MOCKUP_WIDTH))
                        st.session_state["_jst_sms_h"] = int(p.get("h", MOCKUP_HEIGHT))
                        st.session_state["_jst_sms_pad"] = int(p.get("pad", 50))
                        st.rerun()
                    else:
                        st.info("Brak zapisanych ustawień – najpierw użyj „Zapisz jako domyślne”.")

            if data_url:
                st.markdown(
                    f"""
                    <div class="mock-wrap">
                      <div class="mock-bg"></div>
                      <div class="mock-screen v2">{msg_preview_html}</div>
                    </div>
                    <style>
                      .mock-wrap {{
                        position:relative; width:{int(st.session_state.get("_jst_sms_left", MOCKUP_LEFT)) + int(st.session_state.get("_jst_sms_w", MOCKUP_WIDTH)) + 40}px;
                        height:{int(st.session_state.get("_jst_sms_top", MOCKUP_TOP)) + int(st.session_state.get("_jst_sms_h", MOCKUP_HEIGHT)) + 80}px;
                      }}
                      .mock-bg {{
                        position:absolute; inset:0;
                        background-image:url('{data_url}');
                        background-size:contain; background-repeat:no-repeat; background-position:center top;
                      }}
                      .mock-screen.v2 {{
                        position:absolute;
                        top:{int(st.session_state.get("_jst_sms_top", MOCKUP_TOP))}px; left:{int(st.session_state.get("_jst_sms_left", MOCKUP_LEFT))}px;
                        width:{int(st.session_state.get("_jst_sms_w", MOCKUP_WIDTH))}px; height:{int(st.session_state.get("_jst_sms_h", MOCKUP_HEIGHT))}px;
                        background:transparent; border:none;
                        padding:{int(st.session_state.get("_jst_sms_pad", 50))}px 25px; overflow:auto;
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
            subj = str(st.session_state.get("jst_send_subject") or "")
            body_preview_html = body_preview.replace("\n", "<br/>")
            data_url = _mockup_css_bg(EMAIL_MOCKUP_PATH)
            prefs = _load_mockup_prefs().get("email", {})

            with st.expander("Dopasuj mockup E-mail (ręcznie)", expanded=False):
                _e_wrap_w = st.number_input(
                    "Szerokość mockupu (px)",
                    value=int(st.session_state.get("_jst_e_wrap_w", prefs.get("wrap_w", EMAIL_LEFT + EMAIL_WIDTH + 60))),
                    step=10,
                    key="_jst_e_wrap_w_input",
                )
                _e_wrap_h = st.number_input(
                    "Wysokość mockupu (px)",
                    value=int(st.session_state.get("_jst_e_wrap_h", prefs.get("wrap_h", EMAIL_TOP + EMAIL_HEIGHT + 100))),
                    step=10,
                    key="_jst_e_wrap_h_input",
                )
                _e_top = st.number_input(
                    "Top (px)",
                    value=int(st.session_state.get("_jst_e_top", prefs.get("top", EMAIL_TOP))),
                    step=1,
                    key="_jst_e_top_input",
                )
                _e_left = st.number_input(
                    "Left (px)",
                    value=int(st.session_state.get("_jst_e_left", prefs.get("left", EMAIL_LEFT))),
                    step=1,
                    key="_jst_e_left_input",
                )
                _e_w = st.number_input(
                    "Szerokość ekranu (px)",
                    value=int(st.session_state.get("_jst_e_w", prefs.get("w", EMAIL_WIDTH))),
                    step=1,
                    key="_jst_e_w_input",
                )
                _e_h = st.number_input(
                    "Wysokość ekranu (px)",
                    value=int(st.session_state.get("_jst_e_h", prefs.get("h", EMAIL_HEIGHT))),
                    step=1,
                    key="_jst_e_h_input",
                )
                _e_pad_top = st.number_input(
                    "Padding góra (px)",
                    value=int(st.session_state.get("_jst_e_pad_top", prefs.get("pad_top", 18))),
                    step=1,
                    key="_jst_e_pad_top_input",
                )
                _e_pad = st.number_input(
                    "Padding wewnątrz (lewy/prawy/dolny) (px)",
                    value=int(st.session_state.get("_jst_e_pad", prefs.get("pad", 18))),
                    step=1,
                    key="_jst_e_pad_input",
                )
                _e_subj_mt = st.number_input(
                    "Offset tytułu (px; może być ujemny)",
                    value=int(st.session_state.get("_jst_e_subj_mt", prefs.get("subj_mt", 0))),
                    step=1,
                    key="_jst_e_subj_mt_input",
                )

                st.session_state.update(
                    _jst_e_wrap_w=int(_e_wrap_w),
                    _jst_e_wrap_h=int(_e_wrap_h),
                    _jst_e_top=int(_e_top),
                    _jst_e_left=int(_e_left),
                    _jst_e_w=int(_e_w),
                    _jst_e_h=int(_e_h),
                    _jst_e_pad=int(_e_pad),
                    _jst_e_pad_top=int(_e_pad_top),
                    _jst_e_subj_mt=int(_e_subj_mt),
                )

                c_save, c_restore, _ = st.columns([3, 3, 1])
                if c_save.button("💾 Zapisz jako domyślne", key="jst_email_mockup_save", use_container_width=True):
                    prefs_all = _load_mockup_prefs()
                    prefs_all.setdefault("email", {})
                    prefs_all["email"] = {
                        "wrap_w": int(st.session_state.get("_jst_e_wrap_w", EMAIL_LEFT + EMAIL_WIDTH + 60)),
                        "wrap_h": int(st.session_state.get("_jst_e_wrap_h", EMAIL_TOP + EMAIL_HEIGHT + 100)),
                        "top": int(st.session_state.get("_jst_e_top", EMAIL_TOP)),
                        "left": int(st.session_state.get("_jst_e_left", EMAIL_LEFT)),
                        "w": int(st.session_state.get("_jst_e_w", EMAIL_WIDTH)),
                        "h": int(st.session_state.get("_jst_e_h", EMAIL_HEIGHT)),
                        "pad": int(st.session_state.get("_jst_e_pad", 18)),
                        "pad_top": int(st.session_state.get("_jst_e_pad_top", 18)),
                        "subj_mt": int(st.session_state.get("_jst_e_subj_mt", 0)),
                    }
                    _save_mockup_prefs(prefs_all)
                    st.success("Zapisano jako domyślne.")
                if c_restore.button("↩ Przywróć zapisane", key="jst_email_mockup_restore", use_container_width=True):
                    p = _load_mockup_prefs().get("email", {})
                    if p:
                        st.session_state["_jst_e_wrap_w"] = int(p.get("wrap_w", EMAIL_LEFT + EMAIL_WIDTH + 60))
                        st.session_state["_jst_e_wrap_h"] = int(p.get("wrap_h", EMAIL_TOP + EMAIL_HEIGHT + 100))
                        st.session_state["_jst_e_top"] = int(p.get("top", EMAIL_TOP))
                        st.session_state["_jst_e_left"] = int(p.get("left", EMAIL_LEFT))
                        st.session_state["_jst_e_w"] = int(p.get("w", EMAIL_WIDTH))
                        st.session_state["_jst_e_h"] = int(p.get("h", EMAIL_HEIGHT))
                        st.session_state["_jst_e_pad"] = int(p.get("pad", 18))
                        st.session_state["_jst_e_pad_top"] = int(p.get("pad_top", 18))
                        st.session_state["_jst_e_subj_mt"] = int(p.get("subj_mt", 0))
                        st.rerun()
                    else:
                        st.info("Brak zapisanych ustawień – najpierw użyj „Zapisz jako domyślne”.")

            if data_url:
                st.markdown(
                    f"""
                    <div class="mock-wrap">
                      <div class="mock-bg-email"></div>
                      <div class="mock-screen-email">
                        <div class="mock-email-subj">{subj}</div>
                        <div class="email-body">{body_preview_html}</div>
                      </div>
                    </div>
                    <style>
                      .mock-wrap{{
                        position:relative;
                        width:{int(st.session_state.get("_jst_e_wrap_w", EMAIL_LEFT + EMAIL_WIDTH + 60))}px;
                        height:{int(st.session_state.get("_jst_e_wrap_h", EMAIL_TOP + EMAIL_HEIGHT + 100))}px;
                      }}
                      .mock-bg-email{{
                        position:absolute; inset:0;
                        background-image:url('{data_url}');
                        background-size:contain; background-repeat:no-repeat; background-position:center top;
                      }}
                      .mock-screen-email{{
                        position:absolute;
                        top:{int(st.session_state.get("_jst_e_top", EMAIL_TOP))}px; left:{int(st.session_state.get("_jst_e_left", EMAIL_LEFT))}px;
                        width:{int(st.session_state.get("_jst_e_w", EMAIL_WIDTH))}px; height:{int(st.session_state.get("_jst_e_h", EMAIL_HEIGHT))}px;
                        background:#fff; border:1px solid #e5e7eb; border-radius:2px;
                        padding:{int(st.session_state.get("_jst_e_pad_top", 18))}px {int(st.session_state.get("_jst_e_pad", 18))}px {int(st.session_state.get("_jst_e_pad", 18))}px {int(st.session_state.get("_jst_e_pad", 18))}px; overflow:auto;
                        font:13.5px/1.5 system-ui,-apple-system, Segoe UI, Roboto, Arial, sans-serif; color:#111;
                        white-space:pre-wrap; overflow-wrap:break-word; word-break:normal; word-break:break-word; hyphens:auto; line-break:auto;
                        text-indent:0;
                      }}
                      .mock-email-subj{{
                        opacity:.7;
                        margin-top:{int(st.session_state.get("_jst_e_subj_mt", 0))}px;
                        margin-bottom:8px;
                      }}
                      .email-body{{text-indent:0;}}
                    </style>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"""<div style="border:1px solid #e5e7eb;border-radius:8px;padding:18px;font:13px/1.5 system-ui;">
                           <div style="opacity:.75;margin-bottom:8px;">{subj}</div>
                           {body_preview_html}
                        </div>""",
                    unsafe_allow_html=True,
                )

    if send_btn:
        mode = "sms" if method == "SMS" else "email"
        recipients_list = _normalize_recipients(recipients, mode=mode)
        if not recipients_list:
            st.warning("Podaj co najmniej jednego poprawnego odbiorcę.")
            st.stop()

        body_tpl = str(st.session_state.get("jst_send_body") or "").strip()
        if not body_tpl:
            st.warning("Treść wiadomości jest pusta.")
            st.stop()

        if mode == "sms":
            api_token, sender, base = _sms_env()
            sent_ok = 0
            for phone in recipients_list:
                token = make_token(8)
                final_link = _build_link(base, slug, token)
                msg = body_tpl.replace(link_preview, final_link)
                for _ in range(5):
                    try:
                        rec = _create_jst_sms_record(sb, study_id=study["id"], phone=phone, text=msg, token=token)
                        break
                    except DuplicateJstTokenError:
                        token = make_token(8)
                        final_link = _build_link(base, slug, token)
                        msg = body_tpl.replace(link_preview, final_link)
                else:
                    st.error(f"Nie udało się wygenerować unikalnego tokena dla {phone}.")
                    continue
                ok, provider_id, err = send_sms(api_token=api_token, to_phone=phone, text=msg, sender=sender)
                if ok:
                    _mark_jst_sms_sent(sb, sms_id=rec["id"], provider_message_id=provider_id or "")
                    sent_ok += 1
                else:
                    st.error(f"Nie wysłano SMS do {phone}: {err or 'unknown error'}")
            st.success(f"Wysłano {sent_ok} / {len(recipients_list)}.")
        else:
            host, port, user, pwd, secure, from_email, from_name, base = _email_env()
            subject = str(st.session_state.get("jst_send_subject") or "").strip() or "Prośba o wypełnienie ankiety"
            sent_ok = 0
            for email in recipients_list:
                token = make_token(8)
                final_link = _build_link(base, slug, token)
                msg = body_tpl.replace(link_preview, final_link)
                for _ in range(5):
                    try:
                        rec = _create_jst_email_record(
                            sb,
                            study_id=study["id"],
                            email=email,
                            subject=subject,
                            text=msg,
                            token=token,
                        )
                        break
                    except DuplicateJstTokenError:
                        token = make_token(8)
                        final_link = _build_link(base, slug, token)
                        msg = body_tpl.replace(link_preview, final_link)
                else:
                    st.error(f"Nie udało się wygenerować unikalnego tokena dla {email}.")
                    continue
                ok, provider_mid, err = send_email(
                    host=host,
                    port=port,
                    username=user,
                    password=pwd,
                    secure=secure,
                    from_email=from_email,
                    from_name=from_name,
                    to_email=email,
                    subject=subject,
                    text=msg,
                )
                if ok:
                    _mark_jst_email_sent(sb, email_id=rec["id"], provider_message_id=provider_mid or "")
                    sent_ok += 1
                else:
                    st.error(f"Nie wysłano e-maila do {email}: {err or 'unknown error'}")
            st.success(f"Wysłano {sent_ok} / {len(recipients_list)}.")

    st.markdown('<hr class="hr-thin status-top-tight">', unsafe_allow_html=True)
    mode = "sms" if method == "SMS" else "email"
    status_label = "Statusy SMS" if mode == "sms" else "Statusy e-mail"
    st.markdown(f'<div class="form-label-strong" style="font-size:18px;margin-bottom:16px;">{status_label}</div>', unsafe_allow_html=True)

    c1, c2 = st.columns([1, 5])
    with c1:
        if st.button("⟳ Odśwież statusy", key=f"jst_refresh_{mode}"):
            st.rerun()
    with c2:
        auto_key = f"jst_auto_refresh_{mode}"
        auto_refresh = st.checkbox("Auto-odśwież co 15 sekund", value=st.session_state.get(auto_key, False), key=auto_key)

    df_logs = _logs_dataframe(sb, study_id=study["id"], mode=mode)
    if df_logs.empty:
        st.caption("Brak statusów do wyświetlenia.")
    else:
        wanted_cols = [
            "Data",
            ("Telefon" if mode == "sms" else "E-mail"),
            "Status",
            "Czas wyp.",
            "Wysłano",
            "Kliknięto",
            "Rozpoczęto",
            "Zakończono",
            "Nie spełnia",
            "Błąd",
        ]
        for col in wanted_cols:
            if col not in df_logs.columns:
                df_logs[col] = ""
        df_logs = df_logs[wanted_cols].copy()

        raw_rows = (_list_jst_sms_for_study if mode == "sms" else _list_jst_email_for_study)(sb, study["id"]) or []

        def _status_icon_fixed(row: Dict[str, Any]) -> str:
            status = str(row.get("status") or "").lower()
            if row.get("rejected_at"):
                return "🚫"
            if status == "failed":
                return "✖"
            if row.get("completed_at"):
                return "✅"
            if row.get("started_at"):
                return "🏁"
            if row.get("clicked_at"):
                return "🔗"
            if status == "delivered":
                return "📬"
            if status == "sent":
                return "📤"
            if status == "queued":
                return "⏳"
            return "•"

        icons = [_status_icon_fixed(r) for r in raw_rows]
        if len(icons) == len(df_logs.index):
            df_logs["Status"] = icons

        st.markdown(
            """
            <style>.narrow-table { max-width: 1120px; margin: 0 auto; }</style>
            """,
            unsafe_allow_html=True,
        )
        widths = _auto_col_widths(df_logs)
        col_cfg = {col: cc.Column(width=widths.get(col, 100)) for col in df_logs.columns}
        st.markdown('<div class="narrow-table">', unsafe_allow_html=True)
        st.dataframe(df_logs, hide_index=True, column_config=col_cfg)
        st.markdown("</div>", unsafe_allow_html=True)

        out_name = slug or "jst"
        xlsx_bytes = _df_to_xlsx_bytes(df_logs, sheet_name=("SMS" if mode == "sms" else "EMAIL"), borders="none")
        cxl, cpdf = st.columns(2)
        with cxl:
            st.download_button(
                "📊 Eksport XLSX",
                data=xlsx_bytes,
                file_name=f"statusy-{mode}-{out_name}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        with cpdf:
            pdf_bytes = _df_to_pdf_bytes(df_logs, title=f"Statusy {mode.upper()} – {jst_full_nom}")
            if pdf_bytes:
                st.download_button(
                    "📄 Eksport PDF",
                    data=pdf_bytes,
                    file_name=f"statusy-{mode}-{out_name}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            else:
                st.caption("PDF: zainstaluj pakiet `reportlab` na serwerze, aby włączyć eksport.")

    legend = """
      📤 – wiadomość wysłana<br>
      📬 – wiadomość doręczona (jeśli provider zwróci potwierdzenie)<br>
      🔗 – odbiorca kliknął w link<br>
      🏁 – ankieta rozpoczęta<br>
      ✅ – ankieta zakończona<br>
      🚫 – odbiorca nie spełnia warunków udziału<br>
      ✖ – błąd wysyłki<br>
      ⏳ – oczekuje w kolejce<br>
      • – inny / nieznany status
    """
    st.markdown(
        f"""<div style="margin-top:18px;font-size:14px;line-height:1.6;"><b>Legenda statusów:</b><br>{legend}</div><div style="margin-bottom:60px"></div>""",
        unsafe_allow_html=True,
    )

    if auto_refresh:
        st.caption("Auto-odświeżanie aktywne (co 15 s)")
        time.sleep(15)
        st.rerun()
