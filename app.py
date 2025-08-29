# app.py — panel administratora Archetypów (Streamlit)

from __future__ import annotations
from typing import Dict, List, Tuple, Optional
import contextlib
from datetime import datetime, timedelta
import pandas as pd
import streamlit as st

from db_utils import (
    get_supabase,
    fetch_studies,
    insert_study,
    update_study,
    check_slug_availability,
)
from polish import (
    slugify,
    base_slug,
    gen_first_name,
    gen_last_name,
    loc_person,
    instr_person,
)
try:
    from polish import compute_all_cases as _compute_all_cases  # type: ignore
except Exception:
    _compute_all_cases = None

from utils import make_token
from send_link import render as render_send_link

st.set_page_config(page_title="Archetypy – panel", layout="wide")

# ───────────────────────── styles (bez zmian poza danger button) ────────────────────────
st.markdown(
    """
<style>
:root{ --brand:#178AE6; --brand-hover:#0F6FC0; --line:#E6E9EE; --line-2:#D7DEE8; }
.stApp, .stApp > header { background:#FAFAFA !important; }
.block-container{ max-width:1160px !important; padding-top:72px !important; }
.page-title{ font-size:36px; font-weight:800; color:#111827; letter-spacing:.2px; margin:15px 0 45px 0; padding-bottom:12px; border-bottom:1px solid var(--line); }
.hr-thin{ border:0; border-top:1px solid var(--line); margin:16px 0 22px 0; }
.tiles{ display:grid; grid-template-columns:repeat(4,1fr); gap:22px; margin:8px 0 18px 0; }
@media (max-width:1100px){ .tiles{ grid-template-columns:repeat(2,1fr); } }
@media (max-width:640px){ .tiles{ grid-template-columns:1fr; } }
.tiles .stButton>button{ width:100%; height:140px; background:#fff !important; color:#1F2937 !important; font-weight:700 !important; border:1px solid var(--line) !important; border-radius:16px !important; padding:14px 16px !important; display:flex; align-items:center; justify-content:center; text-align:center; white-space:pre-line; }
.tiles .stButton>button:hover{ border-color:#D1D9E4 !important; }
.stButton>button[kind="primary"]{ background:var(--brand) !important; color:#fff !important; border:1px solid var(--brand) !important; border-radius:12px !important; }
.stButton>button[kind="primary"]:hover{ background:var(--brand-hover) !important; border-color:var(--brand-hover) !important; }
.stButton>button[kind="secondary"]{ background:#fff !important; color:#1F2937 !important; border:1px solid var(--line-2) !important; border-radius:12px !important; }
.stButton>button[kind="secondary"]:hover{ background:#F3F6FA !important; border-color:#CBD5E1 !important; }
div[data-baseweb="input"]{ border-radius:10px !important; border:1px solid var(--line-2) !important; box-shadow:none !important; }
.stTextInput input, .stTextArea textarea, .stSelectbox>div>div{ background:#FFFFFF !important; }
input:-webkit-autofill, input:-webkit-autofill:hover, input:-webkit-autofill:focus{ -webkit-box-shadow:0 0 0px 1000px #FFFFFF inset !important; box-shadow:0 0 0px 1000px #FFFFFF inset !important; -webkit-text-fill-color:#0F172A !important; }
.form-label-strong{ font-weight:700; font-size:15px; color:#1F2937; }
.form-label-note{ font-weight:400; color:#748096; margin-left:6px; }
.section-gap{ margin-top:18px; } .section-gap-big{ margin-top:26px; }
.card{ border:1px solid var(--line); background:#fff; border-radius:14px; padding:18px 16px; }
.section-title{ font-weight:700; font-size:18px; margin-bottom:12px; }

/* Danger button tylko dla przycisku z kotwicą #danger-del-anchor */
#danger-del-anchor + div button{
  background:#EF4444 !important; color:#fff !important;
  border-color:#EF4444 !important; border-radius:12px !important;
}
#danger-del-anchor + div button:hover{
  background:#DC2626 !important; border-color:#DC2626 !important;
}
</style>
""",
    unsafe_allow_html=True,
)

sb = get_supabase()

def goto(view: str) -> None:
    st.session_state["view"] = view
    st.rerun()

def logged_in() -> bool:
    return bool(st.session_state.get("auth_ok", False))

def require_auth() -> None:
    if not logged_in():
        goto("login")

def header(title: str) -> None:
    st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)

def modal(title: str):
    if hasattr(st, "modal"):
        return st.modal(title)
    @contextlib.contextmanager
    def _fake_modal():
        st.warning(title); yield
    return _fake_modal()

CASES = ["nom", "gen", "dat", "acc", "ins", "loc", "voc"]

def _split_two(s: str) -> Tuple[str, str]:
    s = (s or "").strip()
    if not s: return "", ""
    if " " in s:
        a, b = s.split(" ", 1)
        return a.strip(), b.strip()
    return s, ""

def _acc_name(first: str, gender: str) -> str: return (first or "").strip()
def _acc_surname(last: str, gender: str) -> str: return (last or "").strip()
def _dat_name(first: str, gender: str) -> str: return (first or "").strip()
def _dat_surname(last: str, gender: str) -> str: return (last or "").strip()
def _voc_name(first: str, gender: str) -> str: return (first or "").strip()
def _voc_surname(last: str, gender: str) -> str: return (last or "").strip()

def _make_name_defaults(first_nom: str, last_nom: str, gender: str) -> Dict[str, str]:
    first_nom = (first_nom or "").strip()
    last_nom  = (last_nom or "").strip()
    gender    = (gender or "M").strip()[:1].upper()

    out: Dict[str, str] = {f"first_name_{c}": "" for c in CASES}
    out.update({f"last_name_{c}": "" for c in CASES})

    if _compute_all_cases and (first_nom or last_nom):
        try:
            base = _compute_all_cases(first_nom, last_nom, gender) or {}
            for c in CASES:
                fk, lk = f"first_name_{c}", f"last_name_{c}"
                if base.get(fk): out[fk] = base[fk].strip()
                if base.get(lk): out[lk] = base[lk].strip()
        except Exception:
            pass

    # poprzednie korekty ze studies
    def _prev_first():
        if not first_nom: return {}
        r = (sb.from_("studies")
             .select(",".join([f"first_name_{c}" for c in CASES]) + ",gender,created_at")
             .eq("first_name_nom", first_nom).eq("gender", gender)
             .order("created_at", desc=True).limit(1).execute())
        return (r.data or [{}])[0]
    def _prev_last():
        if not last_nom: return {}
        r = (sb.from_("studies")
             .select(",".join([f"last_name_{c}" for c in CASES]) + ",gender,created_at")
             .eq("last_name_nom", last_nom).eq("gender", gender)
             .order("created_at", desc=True).limit(1).execute())
        return (r.data or [{}])[0]

    pf, pl = _prev_first(), _prev_last()
    for c in CASES:
        fk, lk = f"first_name_{c}", f"last_name_{c}"
        if pf.get(fk): out[fk] = pf[fk] or out[fk]
        if pl.get(lk): out[lk] = pl[lk] or out[lk]

    # fallbacki
    if first_nom and not out["first_name_gen"]:
        out["first_name_gen"] = gen_first_name(first_nom, gender) or ""
    if last_nom and not out["last_name_gen"]:
        out["last_name_gen"] = gen_last_name(last_nom, gender) or ""

    if (first_nom or last_nom) and (not out["first_name_loc"] or not out["last_name_loc"]):
        a,b = _split_two((loc_person(first_nom, last_nom, gender) or "").strip())
        out["first_name_loc"] = out["first_name_loc"] or a
        out["last_name_loc"]  = out["last_name_loc"]  or b

    if (first_nom or last_nom) and (not out["first_name_ins"] or not out["last_name_ins"]):
        a,b = _split_two((instr_person(first_nom, last_nom, gender) or "").strip())
        out["first_name_ins"] = out["first_name_ins"] or a
        out["last_name_ins"]  = out["last_name_ins"]  or b

    if not out["first_name_dat"]: out["first_name_dat"] = _dat_name(first_nom, gender)
    if not out["last_name_dat"]:  out["last_name_dat"]  = _dat_surname(last_nom, gender)
    if not out["first_name_acc"]: out["first_name_acc"] = _acc_name(first_nom, gender)
    if not out["last_name_acc"]:  out["last_name_acc"]  = _acc_surname(last_nom, gender)
    if not out["first_name_voc"]: out["first_name_voc"] = _voc_name(first_nom, gender)
    if not out["last_name_voc"]:  out["last_name_voc"]  = _voc_surname(last_nom, gender)

    out["first_name_nom"] = first_nom
    out["last_name_nom"]  = last_nom

    # nie podpowiadamy po pustej stronie
    if not first_nom:
        for c in CASES: out[f"first_name_{c}"] = ""
    if not last_nom:
        for c in CASES: out[f"last_name_{c}"] = ""
    return out

def _cases_editor(prefix: str, values: Dict[str, str], base_first: str, base_last: str) -> Dict[str, str]:
    labels = {
        "nom":"Mianownik (kto? co?)","gen":"Dopełniacz (kogo? czego?)","dat":"Celownik (komu? czemu?)",
        "acc":"Biernik (kogo? co?)","ins":"Narzędnik (z kim? z czym?)","loc":"Miejscownik (o kim? o czym?)","voc":"Wołacz (o!)",
    }
    out = dict(values)
    for c in CASES:
        c1,c2,c3 = st.columns([0.32,0.34,0.34])
        with c1: st.markdown(f"<div class='form-label-strong'>{labels[c]}</div>", unsafe_allow_html=True)
        fk, lk = f"first_name_{c}", f"last_name_{c}"
        f_def = values.get(fk, "") if base_first else ""
        l_def = values.get(lk, "") if base_last  else ""
        with c2: out[fk] = st.text_input(f"{prefix}_{fk}", value=f_def, placeholder="(imię)", label_visibility="collapsed")
        with c3: out[lk] = st.text_input(f"{prefix}_{lk}", value=l_def, placeholder="(nazwisko)", label_visibility="collapsed")
    return out

def _payload_from_cases(first: str, last: str, city: str, gender: str, slug: str, cases: Dict[str, str], is_new: bool=False) -> Dict[str, str]:
    payload = {
        "first_name": first.strip(), "last_name": last.strip(), "city": city.strip(),
        "gender": gender, "slug": slug.strip(), "is_active": True if is_new else None,
    }
    for c in CASES:
        payload[f"first_name_{c}"] = (cases.get(f"first_name_{c}") or "").strip()
        payload[f"last_name_{c}"]  = (cases.get(f"last_name_{c}")  or "").strip()
    return {k:v for k,v in payload.items() if v is not None}

def _payload_only_changes(study: Dict, full_payload: Dict) -> Dict:
    """Zwraca TYLKO faktyczne zmiany (łącznie z base polami)."""
    out: Dict[str,str] = {}
    base_keys = ("first_name","last_name","city","gender","slug")
    for k in base_keys:
        if k in full_payload and (full_payload[k] or "") != (study.get(k) or ""):
            out[k] = full_payload[k]
    for c in CASES:
        fk,lk = f"first_name_{c}", f"last_name_{c}"
        if (full_payload.get(fk) or "") != (study.get(fk) or ""): out[fk] = full_payload.get(fk,"")
        if (full_payload.get(lk) or "") != (study.get(lk) or ""): out[lk] = full_payload.get(lk,"")
    return out

# ───────────────────────── wspólne UI ─────────────────────────
def back_button() -> None:
    if st.button("← Cofnij", type="secondary"): goto("home")

def person_fields(prefix: str, data: Optional[Dict] = None) -> Tuple[str, str, str, str]:
    c1,c2 = st.columns(2)
    with c1:
        st.markdown('<span class="form-label-strong">Imię</span> <span class="form-label-note">(mianownik)</span>', unsafe_allow_html=True)
        first = st.text_input(f"{prefix}_first", value=(data or {}).get("first_name",""), placeholder="np. Anna", label_visibility="collapsed")
    with c2:
        st.markdown('<span class="form-label-strong">Nazwisko</span> <span class="form-label-note">(mianownik)</span>', unsafe_allow_html=True)
        last = st.text_input(f"{prefix}_last", value=(data or {}).get("last_name",""), placeholder="np. Kowalska", label_visibility="collapsed")
    st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)
    st.markdown('<span class="form-label-strong">Nazwa JST</span> <span class="form-label-note">(mianownik)</span>', unsafe_allow_html=True)
    city = st.text_input(f"{prefix}_city", value=(data or {}).get("city",""), placeholder="np. Kraków", label_visibility="collapsed")
    st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)
    st.markdown('<span class="form-label-strong">Płeć</span>', unsafe_allow_html=True)
    g_default = (data or {}).get("gender","M"); g_index = 0 if g_default=="M" else 1
    g_ui = st.radio(f"{prefix}_gender", ["Mężczyzna","Kobieta"], index=g_index, horizontal=True, label_visibility="collapsed")
    return first, last, city, ("M" if g_ui=="Mężczyzna" else "F")

def url_fields(prefix: str, last_name: str, current_slug: Optional[str] = None) -> Tuple[str, bool, str]:
    """UI: w jednej linii prefix i slug; **checkbox pod polem prefix** (po lewej)."""
    st.markdown('<div class="section-gap-big"></div>', unsafe_allow_html=True)
    st.markdown("""
    <div style="
        font-size:18px;
        font-weight:600;
        margin-top:10px;
        margin-bottom:10px;
        border-top:1px solid #ccc;
        padding-top:30px;
    ">
        Wybór adresu badania
    </div>
    """, unsafe_allow_html=True)

    url_base = st.secrets.get("SURVEY_BASE_URL", "https://archetypy.badania.pro")
    base_suggest = slugify(last_name) if last_name else ""
    suffix_value = current_slug if current_slug is not None else base_suggest

    c_left, c_right = st.columns([0.42, 0.58])

    # lewa kolumna: prefix + checkbox
    with c_left:
        st.text_input(f"{prefix}_url_base", value=f"{url_base}/", disabled=True, label_visibility="collapsed")
        allow_key = f"{prefix}_allow_custom"
        allow = st.checkbox("Chcę wpisać własny link", key=allow_key, value=st.session_state.get(allow_key, False))

    # prawa kolumna: slug zależny od checkboxa
    with c_right:
        suffix = st.text_input(
            f"{prefix}_suffix",
            value=suffix_value,
            disabled=(not allow),
            placeholder="np. kowalska",
            label_visibility="collapsed",
        )

    chosen = (suffix or "").strip() if allow else (suffix_value or "").strip()
    free = check_slug_availability(sb, chosen) if chosen else False
    st.caption(f"Wybrany: **/{chosen or '—'}** – {'✅ wolny' if free else ('❌ zajęty' if chosen else '—')}")
    return chosen, free, url_base

# ───────────────────────── widoki ─────────────────────────
def login_view() -> None:
    header("Logowanie do panelu")
    st.markdown('<hr class="hr-thin">', unsafe_allow_html=True)
    with st.form("login_form", clear_on_submit=False):
        u = st.text_input("Login", value=st.secrets.get("ADMIN_USER",""), autocomplete="username")
        p = st.text_input("Hasło", type="password", autocomplete="current-password")
        ok = st.form_submit_button("Zaloguj", type="secondary")
    if ok:
        su = st.secrets.get("ADMIN_USER",""); sp = st.secrets.get("ADMIN_PASS","")
        if u==su and p==sp and su and sp:
            st.session_state["auth_ok"] = True; st.toast("Zalogowano ✅"); goto("home")
        else:
            st.error("Błędny login lub hasło.")

def home_view() -> None:
    require_auth()
    header("Archetypy – panel administratora")

    # kafle
    st.markdown('<div class="tiles">', unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    with c1:
        if st.button("➕\nDodaj badanie archetypu", type="secondary"): goto("add")
    with c2:
        if st.button("✏️\nEdytuj dane badania", type="secondary"): goto("edit")
    with c3:
        if st.button("✉️\nWyślij link do ankiety", type="secondary"): goto("send")
    with c4:
        if st.button("📊\nSprawdź wyniki badania archetypu", type="secondary"): goto("results")
    st.markdown('</div>', unsafe_allow_html=True)

    # 🔽 linia oddzielająca kafle od statystyk
    st.markdown(
        "<hr style='border:0; border-top:1px solid #E6E9EE; margin:40px 0;'>",
        unsafe_allow_html=True)

    # panel statystyk
    stats_panel()

def add_view() -> None:
    require_auth()
    header("➕ Dodaj badanie archetypu")
    back_button()
    st.markdown('<div class="section-gap-big"></div>', unsafe_allow_html=True)

    first, last, city, gender = person_fields("add")
    defaults = _make_name_defaults(first, last, gender)

    with st.expander("Pokaż zaawansowane (odmiana) – opcjonalne"):
        cases_vals = _cases_editor("add", defaults, base_first=first.strip(), base_last=last.strip())

    chosen_slug, free, url_base = url_fields("add", last)

    st.markdown('<div class="section-gap-big"></div>', unsafe_allow_html=True)
    if st.button("Zapisz badanie", type="primary"):
        if not first or not last or not city:
            st.error("Uzupełnij: imię, nazwisko i nazwę JST."); return
        if not chosen_slug:
            st.error("Wpisz lub wybierz końcówkę linku."); return
        if not free:
            st.error("Ten link jest zajęty – wybierz inny."); return

        payload = _payload_from_cases(first, last, city, gender, chosen_slug, cases_vals, is_new=True)
        try:
            saved = insert_study(sb, payload)
            st.success(f"✅ Dodano: {saved.get('first_name_nom', first)} {saved.get('last_name_nom', last)} – link: {url_base}/{saved['slug']}")
        except Exception as e:
            st.error(f"❌ Błąd zapisu: {e}")

def edit_view() -> None:
    require_auth()
    header("✏️ Edytuj dane badania")
    back_button()
    st.markdown('<div class="section-gap-big"></div>', unsafe_allow_html=True)

    studies = fetch_studies(sb)
    if not studies:
        st.info("Brak rekordów w bazie."); return

    st.markdown('<div class="form-label-strong" style="font-size:16px; margin-bottom:8px;">Wybierz rekord</div>', unsafe_allow_html=True)
    options = { f"{s.get('first_name_nom') or s['first_name']} {s.get('last_name_nom') or s['last_name']} ({s['city']}) – /{s['slug']}": s for s in studies }
    choice = st.selectbox("", options=list(options.keys()))
    st.markdown('<hr class="hr-thin">', unsafe_allow_html=True)

    study = options[choice]
    data = {
        "first_name": study.get("first_name_nom") or study["first_name"],
        "last_name":  study.get("last_name_nom")  or study["last_name"],
        "city": study["city"], "gender": study.get("gender","M"),
    }
    first, last, city, gender = person_fields("edit", data)

    defaults = _make_name_defaults(first, last, gender)
    for c in CASES:
        fk,lk = f"first_name_{c}", f"last_name_{c}"
        if study.get(fk): defaults[fk] = study.get(fk)
        if study.get(lk): defaults[lk] = study.get(lk)

    with st.expander("Pokaż zaawansowane (odmiana) – opcjonalne"):
        cases_vals = _cases_editor("edit", defaults, base_first=first.strip(), base_last=last.strip())

    chosen_slug, free, url_base = url_fields("edit", last, current_slug=study["slug"])

    st.markdown('<div class="section-gap-big"></div>', unsafe_allow_html=True)
    cols = st.columns([1,1])
    with cols[0]:
        if st.button("Zapisz zmiany", type="primary"):
            if chosen_slug != study["slug"] and not free:
                st.error("Nowy link jest zajęty."); return
            full_payload = _payload_from_cases(first, last, city, gender, chosen_slug, cases_vals, is_new=False)
            payload = _payload_only_changes(study, full_payload)
            if not payload:
                st.info("Brak zmian do zapisania."); return
            try:
                upd = update_study(sb, study["id"], payload)
                st.success(f"✅ Zaktualizowano: {upd.get('first_name_nom', first)} {upd.get('last_name_nom', last)} – /{upd['slug']}")
            except Exception as e:
                st.error(f"❌ Błąd zapisu: {e}")

    with cols[1]:
        st.markdown('<div id="danger-del-anchor"></div>', unsafe_allow_html=True)
        if st.button("🗑️ Usuń badanie", key="del_btn", type="secondary"):
            st.session_state["show_del_modal"] = True

    if st.session_state.get("show_del_modal"):
        with modal("Czy na pewno usunąć to badanie?"):
            st.warning("Tej operacji nie można cofnąć.")
            c = st.columns(2)
            with c[0]:
                if st.button("Tak, usuń", type="primary"):
                    try:
                        sb.table("studies").update({
                            "is_active": False,
                            "deleted_at": datetime.utcnow().isoformat()  # kolumna timestamp w studies
                        }).eq("id", study["id"]).execute()
                        st.session_state["show_del_modal"] = False
                        st.success("Badanie oznaczone jako usunięte.");
                        goto("home")
                    except Exception as e:
                        st.error(f"Nie udało się usunąć: {e}")
            with c[1]:
                if st.button("Anuluj", type="secondary"):
                    st.session_state["show_del_modal"] = False; st.rerun()

def fetch_stats_table() -> Tuple[int, pd.DataFrame]:
    counts: Dict[str,int] = {}
    try:
        r = sb.from_("study_response_count_v").select("slug, responses").execute()
        for row in (r.data or []):
            slug = row.get("slug"); cnt = int(row.get("responses") or 0)
            if slug: counts[slug] = cnt
    except Exception:
        counts = {}

    sres = (
        sb.table("studies")
        .select("first_name_nom,last_name_nom,first_name,last_name,city,slug,created_at")
        .or_("is_active.is.true,is_active.is.null")
        .order("last_name_nom", desc=False)
        .execute()
    )

    rows: List[Dict[str,object]] = []; total = 0
    for s in (sres.data or []):
        ln = s.get("last_name_nom") or s.get("last_name","")
        fn = s.get("first_name_nom") or s.get("first_name","")
        city = s.get("city","")
        cnt = int(counts.get(s.get("slug"),0)); total += cnt

        # Data startu badania → RRRR-MM-DD HH:MM (Europa/Warszawa)
        dt_raw = s.get("created_at")
        dt_str = ""
        try:
            ts = pd.to_datetime(dt_raw, utc=True, errors="coerce")
            if pd.isna(ts):
                ts = pd.to_datetime(dt_raw, errors="coerce")
            if not pd.isna(ts):
                if ts.tzinfo is None:
                    ts = ts.tz_localize("UTC")
                dt_str = ts.tz_convert("Europe/Warsaw").strftime("%Y-%m-%d %H:%M")
        except Exception:
            dt_str = ""

        rows.append({
            "Nazwisko i imię": f"{ln} {fn}",
            "Miasto": city,
            "Data": dt_str,                   # <-- NOWA KOLUMNA
            "Liczba odpowiedzi": cnt,
        })

    df = pd.DataFrame(rows, columns=["Nazwisko i imię","Miasto","Data","Liczba odpowiedzi"])
    df = df[df.notna().any(axis=1)]

    # domyślne sortowanie: najnowsze na górze
    if not df.empty:
        _sort = pd.to_datetime(df["Data"], format="%Y-%m-%d %H:%M", errors="coerce")
        df = df.assign(_sort=_sort).sort_values("_sort", ascending=False).drop(columns="_sort").reset_index(drop=True)

    return total, df


def stats_panel() -> None:
    # odstęp nad ramką
    st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)

    # ⬅️➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➤➡️
    # Tu sterujesz SZEROKOŚCIĄ całej ramki:
    # [1, 6, 1] ≈ 75% szerokości kontenera strony
    # np. [1, 5, 1] węższa, [1, 8, 1] szersza
    L, C, R = st.columns([1, 28, 1], gap="large")
    # ⬅️➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➖➤➡️

    with C:
        card = st.container(border=True)
        with card:
            # pionowe paddingi wewnątrz ramki
            st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)

            # (opcjonalnie) minimalny „gutter” lewo/prawo dla treści
            gL, body, gR = st.columns([1, 20, 1], gap="small")
            with body:
                # tytuł
                st.markdown(
                    "<div style='font-weight:700; font-size:25px; "
                    "margin:25px 0 60px 0; padding-bottom:8px; "
                    "border-bottom:1px solid #E6E9EE;'>Statystyki</div>",
                    unsafe_allow_html=True
                )

                # dane + metryki
                total, df = fetch_stats_table()
                c1, c2 = st.columns(2)
                with c1:
                    st.metric('Łączna liczba uczestników badań', int(total))
                with c2:
                    st.metric('Liczba badań w bazie', len(df))

                # tabela
                rows = len(df)
                st.dataframe(
                    df,
                    use_container_width=True,
                    height=max(rows * 36 + 15, 120),
                    hide_index=True
                )

            st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)



def results_view() -> None:
    require_auth()
    header("📊 Sprawdź wyniki badania archetypu")
    back_button()
    st.markdown('<hr class="hr-thin">', unsafe_allow_html=True)

    studies = fetch_studies(sb)
    if not studies:
        st.info("Brak rekordów w bazie."); return

    options = { f"{s.get('first_name_nom') or s['first_name']} {s.get('last_name_nom') or s['last_name']} ({s['city']}) – /{s['slug']}": s for s in studies }
    choice = st.selectbox("Wybierz osobę/JST", options=list(options.keys()))
    study = options[choice]

    if "wide_report" not in st.session_state: st.session_state["wide_report"] = True
    wide = st.toggle("Szeroki raport", key="wide_report")
    st.markdown(f"<style>.block-container{{max-width:{'90vw' if wide else '1160px'} !important}}</style>", unsafe_allow_html=True)

    try:
        import admin_dashboard as AD
        if hasattr(AD, "show_report"):
            try: AD.show_report(sb, study, wide=wide)
            except TypeError: AD.show_report(sb, study)
        else:
            st.warning("Brak show_report(sb, study, wide) – poniżej dane rekordu.")
            st.json(study)
    except Exception as e:
        st.error(f"Nie udało się wczytać raportu: {e}"); st.json(study)

    st.markdown('<div class="section-title">Udostępnij raport</div>', unsafe_allow_html=True)
    with st.form("share_form"):
        method = st.radio("Metoda", ["E-mail","SMS"], horizontal=True, index=0)
        recipients_raw = st.text_area("Adresaci", placeholder="Oddziel przecinkami: np. jan@firma.pl, ola@urzad.gov.pl (lub numery telefonów dla SMS)")
        hours = st.number_input("Ważność (godziny)", min_value=1, max_value=720, value=48)
        submit_share = st.form_submit_button("Wygeneruj i zapisz linki", type="primary")
    if submit_share:
        recips = [x.strip() for x in recipients_raw.split(",") if x.strip()]
        if not recips:
            st.error("Podaj co najmniej jednego adresata.")
        else:
            exp = datetime.utcnow() + timedelta(hours=hours)
            saved_links: List[str] = []
            for r in recips:
                token = make_token(40)
                try:
                    rc = sb.table("share_recipients").insert({"contact": r}).select("id").single().execute().data
                    rid = rc["id"]
                    sb.table("share_tokens").insert({"token": token, "study_id": study["id"], "recipient_id": rid, "method": "email" if method=="E-mail" else "sms", "expires_at": exp.isoformat()}).execute()
                    saved_links.append(f"/public/report?token={token}")
                except Exception as e:
                    st.error(f"Nie udało się zapisać udostępnienia dla „{r}”: {e}")
            if saved_links:
                st.success("Utworzono udostępnienia:")
                for L in saved_links: st.code(L)

def send_link_view() -> None:
    require_auth(); header("✉️ Wyślij link do ankiety"); render_send_link(back_button)

# ───────────────────────── routing ─────────────────────────
if "view" not in st.session_state: st.session_state["view"] = "login"
with st.sidebar:
    if logged_in():
        if st.button("Wyloguj"): st.session_state.clear(); st.rerun()

view = st.session_state["view"]
if view=="login": login_view()
elif view=="home": home_view()
elif view=="add": add_view()
elif view=="edit": edit_view()
elif view=="results": results_view()
elif view=="send": send_link_view()
else: home_view()
