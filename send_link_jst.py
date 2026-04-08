from __future__ import annotations

from datetime import datetime
from io import BytesIO
import re
from typing import Dict, List, Optional, Tuple, Callable

import pandas as pd
import streamlit as st

from db_utils import get_supabase
from db_jst_utils import fetch_jst_studies
from db_sms import create_sms_record, mark_sms_sent, list_sms_for_study, DuplicateTokenError as DuplicateSmsTokenError
from db_email import create_email_record, mark_email_sent, list_email_for_study, DuplicateTokenError as DuplicateEmailTokenError
from smsapi_client import send_sms
from email_client import send_email
from utils import make_token


_EMAIL_RE = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.I)


def _normalize_emails(raw: str) -> List[str]:
    if not raw:
        return []
    src = raw.replace("\n", ",").replace(";", ",").replace(" ", ",")
    out: List[str] = []
    seen = set()
    for part in src.split(","):
        val = part.strip().lower()
        if not val or val in seen:
            continue
        if not _EMAIL_RE.match(val):
            continue
        seen.add(val)
        out.append(val)
    return out


def _normalize_phones(raw: str) -> List[str]:
    if not raw:
        return []
    src = raw.replace("\n", ",").replace(";", ",").replace(" ", ",")
    out: List[str] = []
    seen = set()
    for part in src.split(","):
        val = re.sub(r"[^\d+]", "", part.strip())
        if not val or val in seen:
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


def _status_icon(row: Dict) -> str:
    status = str(row.get("status") or "").lower()
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


def _logs_dataframe(sb, study_id: str, mode: str) -> pd.DataFrame:
    rows = (list_sms_for_study if mode == "sms" else list_email_for_study)(sb, study_id) or []

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
                "Wysłano": "✓" if (str(r.get("status") or "").lower() in ("sent", "delivered")) else "",
                "Kliknięto": _fmt_dt(r.get("clicked_at")),
                "Rozpoczęto": _fmt_dt(r.get("started_at")),
                "Zakończono": _fmt_dt(r.get("completed_at")),
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
        "Błąd",
    ]
    return pd.DataFrame(out, columns=cols)


def _default_sms_text(jst_full_gen: str, link_preview: str) -> str:
    return (
        f"Zwracamy sie z prosba o wypelnienie ankiety dla mieszkańców {jst_full_gen}.\n"
        f"Link do ankiety: {link_preview}\n"
        "Dziekujemy!"
    )


def _default_email_text(jst_type: str, jst_full_gen: str, jst_full_nom: str, link_preview: str) -> str:
    type_gen = "miasta" if (jst_type or "").lower() == "miasto" else "gminy"
    verb = "powinno działać" if (jst_type or "").lower() == "miasto" else "powinna działać"
    return (
        "Zwracamy się z prośbą o wypełnienie ankiety w badaniu realizowanym "
        f"wśród mieszkańców {jst_full_gen}. W tym badaniu chcemy przekonać się jakie jest "
        f"Państwa podejście do spraw {type_gen} i oczekiwania dotyczące tego, jak {verb} {jst_full_nom}. \n"
        "Wypełnienie ankiety nie powinno zająć więcej niż 5-7 minut.\n"
        f"Link do ankiety: {link_preview}\n"
        "Dziękujemy,\n"
        "Zespół badawczy Badania.pro®"
    )


def render(back_btn: Callable[[], None]) -> None:
    sb = get_supabase()
    back_btn()

    st.markdown("### Wybierz badanie mieszkańców")
    studies = fetch_jst_studies(sb)
    if not studies:
        st.info("Brak badań JST w bazie.")
        return

    options = {
        f"{(s.get('jst_full_nom') or (str(s.get('jst_type', '')).title() + ' ' + str(s.get('jst_name', '')))).strip()} – /{s.get('slug') or ''}": s
        for s in studies
    }
    label = st.selectbox("Wybierz badanie", options=list(options.keys()), label_visibility="collapsed")
    study = options[label]

    st.markdown("### Metoda wysyłki")
    method = st.radio("Metoda", ["SMS", "E-mail"], horizontal=True, label_visibility="collapsed")

    st.markdown("### Odbiorcy")
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

    base_url = (st.secrets.get("JST_SURVEY_BASE_URL", "https://jst.badania.pro") or "").rstrip("/")
    preview_key = "jst_link_preview"
    preview_study_key = "jst_link_preview_study_id"
    if st.session_state.get(preview_study_key) != str(study.get("id")) or preview_key not in st.session_state:
        st.session_state[preview_key] = _build_link(base_url, slug, make_token(6))
        st.session_state[preview_study_key] = str(study.get("id"))
    link_preview = st.session_state[preview_key]

    default_sms = _default_sms_text(jst_full_gen, link_preview)
    default_email = _default_email_text(jst_type, jst_full_gen, jst_full_nom, link_preview)

    if "jst_msg_method" not in st.session_state:
        st.session_state["jst_msg_method"] = method
    if "jst_msg_body" not in st.session_state:
        st.session_state["jst_msg_body"] = default_sms if method == "SMS" else default_email
    if st.session_state.get("jst_msg_method") != method:
        st.session_state["jst_msg_method"] = method
        st.session_state["jst_msg_body"] = default_sms if method == "SMS" else default_email

    if method == "E-mail":
        st.text_input(
            "Temat wiadomości",
            key="jst_email_subject",
            value=st.session_state.get("jst_email_subject") or "Prośba o wypełnienie ankiety dla mieszkańców",
        )

    st.markdown("### Treść wiadomości")
    st.text_area("Treść", key="jst_msg_body", height=220, label_visibility="collapsed")

    c1, c2 = st.columns([0.3, 0.7], gap="small")
    with c1:
        if st.button("Przywróć domyślną treść", use_container_width=True):
            st.session_state["jst_msg_body"] = default_sms if method == "SMS" else default_email
            st.rerun()
    with c2:
        if st.button("Wyślij", type="primary", use_container_width=True):
            try:
                if method == "SMS":
                    recipients_list = _normalize_phones(recipients)
                    if not recipients_list:
                        st.error("Podaj co najmniej jeden poprawny numer telefonu.")
                        return

                    token_api, sender, base = _sms_env()
                    sent = 0
                    for phone in recipients_list:
                        body_tpl = str(st.session_state.get("jst_msg_body") or "").strip()
                        if not body_tpl:
                            continue
                        for _ in range(4):
                            token = make_token(8)
                            link = _build_link(base, slug, token)
                            body = body_tpl.replace(link_preview, link)
                            try:
                                rec = create_sms_record(sb, str(study["id"]), phone, body, token)
                            except DuplicateSmsTokenError:
                                continue
                            ok, provider_mid, err = send_sms(token_api, phone, body, sender=sender)
                            if ok:
                                mark_sms_sent(sb, rec["id"], provider_mid or "")
                                sent += 1
                            else:
                                sb.table("sms_messages").update({"status": "failed"}).eq("id", rec["id"]).execute()
                                st.warning(f"SMS do {phone} nie został wysłany: {err}")
                            break
                    if sent:
                        st.success(f"Wysłano {sent} wiadomości SMS.")
                    else:
                        st.warning("Nie wysłano żadnej wiadomości SMS.")

                else:
                    recipients_list = _normalize_emails(recipients)
                    if not recipients_list:
                        st.error("Podaj co najmniej jeden poprawny adres e-mail.")
                        return
                    subject = str(st.session_state.get("jst_email_subject") or "").strip() or "Prośba o wypełnienie ankiety"
                    body_tpl = str(st.session_state.get("jst_msg_body") or "").strip()
                    if not body_tpl:
                        st.error("Treść wiadomości jest pusta.")
                        return

                    host, port, user, pwd, secure, from_email, from_name, base = _email_env()
                    sent = 0
                    for email in recipients_list:
                        for _ in range(4):
                            token = make_token(8)
                            link = _build_link(base, slug, token)
                            body = body_tpl.replace(link_preview, link)
                            try:
                                rec = create_email_record(sb, str(study["id"]), email, subject, body, token)
                            except DuplicateEmailTokenError:
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
                                text=body,
                            )
                            if ok:
                                mark_email_sent(sb, rec["id"], provider_mid or "")
                                sent += 1
                            else:
                                sb.table("email_logs").update({"status": "failed"}).eq("id", rec["id"]).execute()
                                st.warning(f"E-mail do {email} nie został wysłany: {err}")
                            break
                    if sent:
                        st.success(f"Wysłano {sent} wiadomości e-mail.")
                    else:
                        st.warning("Nie wysłano żadnej wiadomości e-mail.")
            except Exception as e:
                st.error(f"Błąd wysyłki: {e}")

    st.markdown("---")
    st.markdown("### Statusy wysyłek")
    sms_df = _logs_dataframe(sb, str(study["id"]), "sms")
    email_df = _logs_dataframe(sb, str(study["id"]), "email")

    tab_sms, tab_email = st.tabs(["SMS", "E-mail"])
    with tab_sms:
        if sms_df.empty:
            st.caption("Brak wpisów SMS.")
        else:
            st.dataframe(sms_df, use_container_width=True, hide_index=True)
            st.download_button(
                "Pobierz statusy SMS (xlsx)",
                data=_df_to_xlsx_bytes(sms_df),
                file_name=f"statusy-sms-{slug}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
    with tab_email:
        if email_df.empty:
            st.caption("Brak wpisów e-mail.")
        else:
            st.dataframe(email_df, use_container_width=True, hide_index=True)
            st.download_button(
                "Pobierz statusy e-mail (xlsx)",
                data=_df_to_xlsx_bytes(email_df),
                file_name=f"statusy-email-{slug}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )


def _df_to_xlsx_bytes(df: pd.DataFrame, sheet_name: str = "Statusy") -> bytes:
    out = BytesIO()
    with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
        ws = writer.sheets[sheet_name]
        book = writer.book
        header_fmt = book.add_format({"bold": True, "bg_color": "#f3f4f6", "border": 0})
        for c, title in enumerate(df.columns):
            ws.write(0, c, title, header_fmt)
            col_len = max(10, min(44, int(max(len(str(title)), df.iloc[:, c].astype(str).str.len().max() if len(df) else 0) + 2)))
            ws.set_column(c, c, col_len)
    return out.getvalue()
