# app.py — panel administratora Archetypów
# WYMAGA: db_utils.py (get_supabase, fetch_studies, insert_study, update_study, check_slug_availability)
#         polish.py (slugify, base_slug, gen_first_name, gen_last_name, loc_person, instr_person)

from __future__ import annotations
from typing import Dict, List, Tuple, Optional
import re
import pandas as pd
import streamlit as st

from db_utils import (
    get_supabase,
    fetch_studies,
    insert_study,
    update_study,
    check_slug_availability,
)
from polish import slugify, base_slug, gen_first_name, gen_last_name, loc_person, instr_person

# -----------------------------------------------------------------------------
# Konfiguracja strony
# -----------------------------------------------------------------------------
st.set_page_config(page_title="Archetypy – panel", layout="wide")

# -----------------------------------------------------------------------------
# STYLE – UI (bez zmian wizualnych poza edytorem przypadków)
# -----------------------------------------------------------------------------
st.markdown(
    """
<style>
:root{ --brand:#178AE6; --brand-hover:#0F6FC0; --line:#E6E9EE; --line-2:#D7DEE8; --muted:#F6F7FB; }
.stApp, .stApp>header{ background:#FAFAFA !important; }
.block-container{ max-width:1160px !important; padding-top:64px !important; }
.page-title{ font-size:36px; font-weight:800; color:#111827; letter-spacing:.2px; margin:6px 0 10px 0; }
.hr-thin{ border:0; border-top:1px solid var(--line); margin:0 0 28px 0; }
.sep{ border:0; border-top:1px solid var(--line); margin:14px 0; }
.tiles{ display:grid; grid-template-columns:repeat(4,1fr); gap:22px; margin:8px 0 18px 0; }
@media(max-width:1100px){ .tiles{ grid-template-columns:repeat(2,1fr);} }
@media(max-width:640px){ .tiles{ grid-template-columns:1fr;} }
.tiles .stButton>button{ width:100%; height:140px; background:#fff!important; border:1px solid var(--line)!important;
  border-radius:16px!important; box-shadow:none!important; transition:transform .12s, border-color .12s, background .12s;
  font-weight:700; font-size:16px; color:#1F2937!important; display:flex; flex-direction:column; align-items:center; justify-content:center; gap:8px; }
.tiles .stButton>button:hover{ transform:translateY(-2px); border-color:#D1D9E4!important; background:#FBFDFF!important; }
.stButton>button[kind="primary"], .stDownloadButton>button[kind="primary"]{ background:var(--brand)!important; color:#fff!important;
  border:1px solid var(--brand)!important; border-radius:12px!important; padding:10px 16px!important; box-shadow:none!important;}
.stButton>button[kind="primary"]:hover{ background:var(--brand-hover)!important; border-color:var(--brand-hover)!important;}
.stButton>button[kind="secondary"]{ background:#fff!important; color:#1F2937!important; border:1px solid var(--line-2)!important; border-radius:12px!important;}
.stButton>button[kind="secondary"]:hover{ background:#F3F6FA!important; border-color:#CBD5E1!important;}
div[data-baseweb="input"]{ border-radius:10px!important; border:1px solid var(--line-2)!important; box-shadow:none!important; }
.stTextInput input, .stTextArea textarea, .stSelectbox>div>div{ background:#FFFFFF!important; }
div[data-baseweb="input"][aria-disabled="true"]{ background:#F3F6FA!important; }
.subhead{ font-size:24px; font-weight:800; margin:12px 0 18px 0; }
.form-label-strong{ font-weight:700; font-size:15px; color:#1F2937; }
.form-label-note{ font-weight:400; color:#748096; margin-left:6px; }
.section-gap{ margin-top:18px; } .section-gap-big{ margin-top:26px; }
.card{ border:1px solid var(--line); background:#fff; border-radius:14px; padding:18px 16px; box-shadow:0 1px 0 rgba(17,24,39,.02);}
.card h3{ margin:4px 0 14px 0; } .card .inner-80{ width:80%; } @media(max-width:1100px){ .card .inner-80{ width:100%; } }
.ghost-killer > div[data-baseweb="input"]{ display:none!important; }
</style>
""",
    unsafe_allow_html=True,
)

# -----------------------------------------------------------------------------
# SHIM compute_all gdy brak w polish.py (GEN/INS/LOC)
# -----------------------------------------------------------------------------
import polish as _pol
if not hasattr(_pol, "compute_all"):
    def _compute_all(first_nom: str, last_nom: str, gender: str) -> Dict[str,str]:
        fn_gen = gen_first_name(first_nom or "", gender) if first_nom else ""
        ln_gen = gen_last_name(last_nom or "", gender) if last_nom else ""
        loc_full = loc_person(first_nom or "", last_nom or "", gender) if (first_nom or last_nom) else ""
        fn_loc, ln_loc = (loc_full.split(" ", 1) if " " in loc_full else (loc_full, ""))
        ins_full = instr_person(first_nom or "", last_nom or "", gender) if (first_nom or last_nom) else ""
        fn_ins, ln_ins = (ins_full.split(" ", 1) if " " in ins_full else (ins_full, ""))
        return {"first_name_gen": fn_gen, "last_name_gen": ln_gen,
                "first_name_loc": fn_loc, "last_name_loc": ln_loc,
                "first_name_ins": fn_ins, "last_name_ins": ln_ins}
    _pol.compute_all = _compute_all  # type: ignore[attr-defined]

# --- fallbacki dla przypadków, gdy nie ma nic w bazie ---
def _acc_name(first_nom: str, gender: str, gen_pre: str="") -> str:
    if gender == "M":
        return gen_pre or first_nom   # M → biernik = dopełniacz (żywotne)
    return (first_nom[:-1] + "ę") if first_nom.endswith("a") else first_nom

def _acc_surname(last_nom: str, gender: str, gen_pre: str="") -> str:
    if gender == "M":
        if last_nom.endswith("ek"): return last_nom[:-2] + "ka"
        if last_nom.endswith("a"):  return last_nom[:-1] + "ę"  # Batyra -> Batyrę
        return gen_pre or last_nom
    # żeńskie
    for a,b in (("ska","ską"),("cka","cką"),("dzka","dzką"),("zka","zką"),("ka","ą"),("a","ą")):
        if last_nom.endswith(a): return last_nom[:-len(a)] + b
    return last_nom

def _dat_name(first_nom: str, gender: str) -> str:
    if first_nom.endswith("a"): return first_nom[:-1] + "ie"
    return first_nom + "owi"

def _dat_surname(last_nom: str, gender: str) -> str:
    if last_nom.endswith("a"): return last_nom[:-1] + "e"
    if last_nom.endswith("o"): return last_nom[:-1] + "u"
    return last_nom + "owi"

def _voc_name(first_nom: str, gender: str) -> str:
    if first_nom.endswith("a"): return first_nom[:-1] + "o"
    if re.search(r"(k|g)$", first_nom): return first_nom + "u"
    return first_nom

def _voc_surname(last_nom: str, gender: str) -> str:
    if last_nom.endswith("a"): return last_nom[:-1] + "o"
    return last_nom

# -----------------------------------------------------------------------------
# Narzędzia
# -----------------------------------------------------------------------------
sb = get_supabase()

def goto(view: str) -> None:
    st.session_state["view"] = view
    st.rerun()

def logged_in() -> bool:
    return bool(st.session_state.get("auth_ok", False))

def require_auth() -> None:
    if not logged_in():
        goto("login")

def header(title: str = "Archetypy – panel administratora") -> None:
    st.markdown(f'<div class="page-title">{title}</div>', unsafe_allow_html=True)
    st.markdown('<hr class="hr-thin">', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# LOGOWANIE
# -----------------------------------------------------------------------------
def login_view() -> None:
    st.markdown('<div class="page-title">Logowanie do panelu</div>', unsafe_allow_html=True)
    st.markdown('<hr class="hr-thin">', unsafe_allow_html=True)
    with st.form("login_form", clear_on_submit=False):
        u = st.text_input("Login", value=st.secrets.get("ADMIN_USER", ""), autocomplete="username")
        p = st.text_input("Hasło", type="password", autocomplete="current-password")
        ok = st.form_submit_button("Zaloguj", type="primary")
    if ok:
        su = st.secrets.get("ADMIN_USER", ""); sp = st.secrets.get("ADMIN_PASS", "")
        if u == su and p == sp and su and sp:
            st.session_state["auth_ok"] = True
            st.toast("Zalogowano ✅"); goto("home")
        else:
            st.error("Błędny login lub hasło.")
    with st.sidebar: st.write("")

# -----------------------------------------------------------------------------
# Prefill z poprzednich rekordów (pamiętanie odmian)
# -----------------------------------------------------------------------------
# Zwraca najnowszy rekord spełniający warunki i tylko potrzebne kolumny
def _pick_cols(rec: Dict) -> Dict[str,str]:
    keys = ["first_name_nom","last_name_nom","first_name_gen","last_name_gen","first_name_dat","last_name_dat",
            "first_name_acc","last_name_acc","first_name_ins","last_name_ins","first_name_loc","last_name_loc",
            "first_name_voc","last_name_voc"]
    return {k:(rec.get(k) or "").strip() for k in keys}

def fetch_prior_exact(first_nom: str, last_nom: str, gender: str) -> Optional[Dict[str,str]]:
    if not first_nom or not last_nom: return None
    try:
        r = sb.table("studies").select(
            "created_at, gender, first_name_nom,last_name_nom, first_name_gen,last_name_gen, "
            "first_name_dat,last_name_dat, first_name_acc,last_name_acc, first_name_ins,last_name_ins, "
            "first_name_loc,last_name_loc, first_name_voc,last_name_voc"
        ).eq("gender", gender).eq("first_name_nom", first_nom).eq("last_name_nom", last_nom)\
         .order("created_at", desc=True).limit(1).execute()
        rows = r.data or []
        if rows: return _pick_cols(rows[0])
    except Exception: pass
    return None

def fetch_prior_first(first_nom: str, gender: str) -> Optional[Dict[str,str]]:
    if not first_nom: return None
    try:
        r = sb.table("studies").select(
            "created_at, gender, first_name_nom, first_name_gen, first_name_dat, first_name_acc, "
            "first_name_ins, first_name_loc, first_name_voc"
        ).eq("gender", gender).eq("first_name_nom", first_nom).order("created_at", desc=True).limit(1).execute()
        rows = r.data or []
        if rows:
            rr = rows[0]; return {
                "first_name_nom": rr.get("first_name_nom",""),
                "first_name_gen": rr.get("first_name_gen",""),
                "first_name_dat": rr.get("first_name_dat",""),
                "first_name_acc": rr.get("first_name_acc",""),
                "first_name_ins": rr.get("first_name_ins",""),
                "first_name_loc": rr.get("first_name_loc",""),
                "first_name_voc": rr.get("first_name_voc",""),
            }
    except Exception: pass
    return None

def fetch_prior_last(last_nom: str, gender: str) -> Optional[Dict[str,str]]:
    if not last_nom: return None
    try:
        r = sb.table("studies").select(
            "created_at, gender, last_name_nom, last_name_gen, last_name_dat, last_name_acc, "
            "last_name_ins, last_name_loc, last_name_voc"
        ).eq("gender", gender).eq("last_name_nom", last_nom).order("created_at", desc=True).limit(1).execute()
        rows = r.data or []
        if rows:
            rr = rows[0]; return {
                "last_name_nom": rr.get("last_name_nom",""),
                "last_name_gen": rr.get("last_name_gen",""),
                "last_name_dat": rr.get("last_name_dat",""),
                "last_name_acc": rr.get("last_name_acc",""),
                "last_name_ins": rr.get("last_name_ins",""),
                "last_name_loc": rr.get("last_name_loc",""),
                "last_name_voc": rr.get("last_name_voc",""),
            }
    except Exception: pass
    return None

# Zbuduj domyślne rozbite formy dla wszystkich przypadków
def make_case_defaults(first_nom: str, last_nom: str, gender: str) -> Dict[str,str]:
    out: Dict[str,str] = {}

    # 1) próba: pełny match
    exact = fetch_prior_exact(first_nom, last_nom, gender) or {}
    out.update({k: v for k,v in exact.items() if v})

    # 2) próba: same imię / samo nazwisko
    if not all(out.get(k) for k in ["first_name_gen","first_name_dat","first_name_acc","first_name_ins","first_name_loc","first_name_voc"]):
        prev_f = fetch_prior_first(first_nom, gender) or {}
        for k,v in prev_f.items():
            if k.startswith("first_name_") and v and not out.get(k): out[k] = v
    if not all(out.get(k) for k in ["last_name_gen","last_name_dat","last_name_acc","last_name_ins","last_name_loc","last_name_voc"]):
        prev_l = fetch_prior_last(last_nom, gender) or {}
        for k,v in prev_l.items():
            if k.startswith("last_name_") and v and not out.get(k): out[k] = v

    # 3) systemowe (GEN/INS/LOC z polish.py)
    forms = _pol.compute_all(first_nom or "", last_nom or "", gender)
    for k in ("first_name_gen","last_name_gen","first_name_ins","last_name_ins","first_name_loc","last_name_loc"):
        if not out.get(k): out[k] = forms.get(k,"")

    # 4) systemowe DAT/VOC + ACC (uwzględnij GEN jako baza)
    if not out.get("first_name_dat"): out["first_name_dat"] = _dat_name(first_nom, gender)
    if not out.get("last_name_dat"):  out["last_name_dat"]  = _dat_surname(last_nom, gender)

    if not out.get("first_name_voc"): out["first_name_voc"] = _voc_name(first_nom, gender)
    if not out.get("last_name_voc"):  out["last_name_voc"]  = _voc_surname(last_nom, gender)

    if not out.get("first_name_acc"):
        out["first_name_acc"] = _acc_name(first_nom, gender, out.get("first_name_gen",""))
    if not out.get("last_name_acc"):
        out["last_name_acc"]  = _acc_surname(last_nom, gender, out.get("last_name_gen",""))

    # 5) nominalne
    out.setdefault("first_name_nom", first_nom or "")
    out.setdefault("last_name_nom",  last_nom or "")
    return out

# Renderer: imię i nazwisko w jednej linii (2 kolumny) dla KAŻDEGO przypadku
def render_cases_editor(prefix: str, defaults: Dict[str,str], existing: Optional[Dict[str,str]] = None) -> Dict[str,str]:
    existing = existing or {}
    rows = [
        ("Mianownik (kto? co?)", "first_name_nom", "last_name_nom"),
        ("Dopełniacz (kogo? czego?)", "first_name_gen", "last_name_gen"),
        ("Celownik (komu? czemu?)", "first_name_dat", "last_name_dat"),
        ("Biernik (kogo? co?)", "first_name_acc", "last_name_acc"),
        ("Narzędnik (z kim? z czym?)", "first_name_ins", "last_name_ins"),
        ("Miejscownik (o kim? o czym?)", "first_name_loc", "last_name_loc"),
        ("Wołacz (o!)", "first_name_voc", "last_name_voc"),
    ]
    out: Dict[str,str] = {}
    for label, fk, lk in rows:
        st.markdown(f'<div class="form-label-strong" style="margin-top:8px;">{label}</div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            fv = existing.get(fk) or defaults.get(fk, "")
            out[fk] = st.text_input(f"{prefix}_{fk}", value=fv, placeholder="Imię…", label_visibility="collapsed").strip()
        with c2:
            lv = existing.get(lk) or defaults.get(lk, "")
            out[lk] = st.text_input(f"{prefix}_{lk}", value=lv, placeholder="Nazwisko…", label_visibility="collapsed").strip()
    return out

# -----------------------------------------------------------------------------
# Wspólne pola osoby
# -----------------------------------------------------------------------------
def person_fields(prefix: str, data: Dict | None = None) -> Tuple[str, str, str, str]:
    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<span class="form-label-strong">Imię</span> <span class="form-label-note">(mianownik)</span>', unsafe_allow_html=True)
        first = st.text_input(f"{prefix}_first", value=(data or {}).get("first_name", ""), placeholder="np. Anna", label_visibility="collapsed")
    with col2:
        st.markdown('<span class="form-label-strong">Nazwisko</span> <span class="form-label-note">(mianownik)</span>', unsafe_allow_html=True)
        last = st.text_input(f"{prefix}_last", value=(data or {}).get("last_name", ""), placeholder="np. Kowalska", label_visibility="collapsed")

    st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)
    st.markdown('<span class="form-label-strong">Nazwa JST</span> <span class="form-label-note">(mianownik)</span>', unsafe_allow_html=True)
    city = st.text_input(f"{prefix}_city", value=(data or {}).get("city", ""), placeholder="np. Kraków", label_visibility="collapsed")

    st.markdown('<div class="section-gap"></div>', unsafe_allow_html=True)
    st.markdown('<span class="form-label-strong">Płeć</span>', unsafe_allow_html=True)
    g_default = (data or {}).get("gender", "M")
    g_index = 0 if g_default == "M" else 1
    g_ui = st.radio(f"{prefix}_gender", ["Mężczyzna", "Kobieta"], index=g_index, horizontal=True, label_visibility="collapsed")
    gender_code = "M" if g_ui == "Mężczyzna" else "F"
    return first, last, city, gender_code

def url_fields(prefix: str, last_name: str, current_slug: str | None = None) -> Tuple[str, bool, str]:
    st.markdown('<div class="section-gap-big"></div>', unsafe_allow_html=True)
    st.markdown('<div class="form-label-strong" style="font-size:18px;">Wybór adresu badania</div>', unsafe_allow_html=True)
    url_base = st.secrets.get("SURVEY_BASE_URL", "https://archetypy.badania.pro")
    base_suggest = slugify(last_name) if last_name else ""
    suffix_value = current_slug if current_slug is not None else base_suggest
    colp, cols = st.columns([0.42, 0.58])
    with colp: st.text_input(f"{prefix}_url_base", value=f"{url_base}/", disabled=True, label_visibility="collapsed")
    with cols:
        allow_key = f"{prefix}_allow_custom"
        allow = st.session_state.get(allow_key, False)
        suffix = st.text_input(f"{prefix}_suffix", value=suffix_value, disabled=(not allow), placeholder="np. kowalska", label_visibility="collapsed")
    allow = st.checkbox("Chcę wpisać własny link", key=allow_key, value=st.session_state.get(allow_key, False))
    chosen = suffix if allow else suffix_value
    free = check_slug_availability(sb, chosen) if chosen else False
    st.caption(f"Wybrany: **/{chosen or '—'}** – {'✅ wolny' if free else ('❌ zajęty' if chosen else '—')}")
    return chosen, free, url_base

# -----------------------------------------------------------------------------
# Statystyki
# -----------------------------------------------------------------------------
def fetch_stats_table() -> Tuple[int, pd.DataFrame]:
    counts: Dict[str, int] = {}
    try:
        r = sb.from_("study_response_count_v").select("slug, resp_count, response_count, v_response_count").execute()
        for row in (r.data or []):
            c = 0
            for k in ("resp_count","response_count","v_response_count"):
                if row.get(k) is not None: c = int(row[k]); break
            if row.get("slug"): counts[row["slug"]] = c
    except Exception: counts = {}
    if not counts:
        try:
            ag = sb.from_("responses").select("study_id, count=study_id.count()").group("study_id").execute()
            studs = sb.table("studies").select("id, slug").execute()
            id2slug = {s["id"]: s["slug"] for s in (studs.data or [])}
            for row in (ag.data or []):
                slug = id2slug.get(row["study_id"])
                if slug: counts[slug] = int(row["count"])
        except Exception: counts = {}
    sres = sb.table("studies").select("first_name_nom,last_name_nom,first_name,last_name,city,slug").order("last_name_nom", desc=False).execute()
    rows: List[Dict[str, object]] = []; total = 0
    for s in (sres.data or []):
        ln = s.get("last_name_nom") or s.get("last_name","")
        fn = s.get("first_name_nom") or s.get("first_name","")
        city = s.get("city",""); c = int(counts.get(s["slug"], 0)); total += c
        rows.append({"Nazwisko i imię": f"{ln} {fn}", "Miasto": city, "Liczba odpowiedzi": c})
    df = pd.DataFrame(rows, columns=["Nazwisko i imię","Miasto","Liczba odpowiedzi"])
    return total, df

def stats_panel() -> None:
    st.markdown('<hr class="sep">', unsafe_allow_html=True)
    st.subheader("Statystyki")
    st.markdown('<div class="ghost-killer">', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    total, df = fetch_stats_table()
    st.markdown('<div class="inner-80">', unsafe_allow_html=True)
    total_all = int(df["Liczba odpowiedzi"].sum()) if not df.empty else total
    st.markdown(f"**Łączna liczba uczestników badań:** {total_all}")
    rows = len(df) + 1; row_h = 36; height = max(rows * row_h, 120)
    st.dataframe(df, use_container_width=True, height=height, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# Widoki
# -----------------------------------------------------------------------------
def home_view() -> None:
    require_auth(); header()
    st.markdown('<div class="tiles">', unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    with c1:
        if st.button("➕\nDodaj badanie archetypu", key="tile_add", type="secondary"): goto("add")
    with c2:
        if st.button("✏️\nEdytuj dane badania", key="tile_edit", type="secondary"): goto("edit")
    with c3:
        if st.button("📨\nWyślij link do ankiety", key="tile_send", type="secondary"): goto("send")
    with c4:
        if st.button("📈\nSprawdź wyniki badania archetypu", key="tile_results", type="secondary"): goto("results")
    st.markdown('</div>', unsafe_allow_html=True)
    stats_panel()

def back_button() -> None:
    if st.button("← Cofnij", type="secondary"): goto("home")

def add_view() -> None:
    require_auth(); header("➕ Dodaj badanie archetypu"); back_button()
    st.markdown('<div class="section-gap-big"></div>', unsafe_allow_html=True)
    first, last, city, gender = person_fields("add")

    with st.expander("Pokaż zaawansowane (odmiana) – opcjonalne"):
        defaults = make_case_defaults(first.strip(), last.strip(), gender)
        case_vals = render_cases_editor("add", defaults)

    chosen_slug, free, url_base = url_fields("add", last)

    st.markdown('<div class="section-gap-big"></div>', unsafe_allow_html=True)
    if st.button("Zapisz badanie", type="primary"):
        if not first or not last or not city:
            st.error("Uzupełnij: imię, nazwisko i nazwę JST."); return
        if not chosen_slug:
            st.error("Wpisz lub wybierz końcówkę linku."); return
        if not free:
            st.error("Ten link jest zajęty – wybierz inny."); return

        payload = {
            "first_name": first.strip(), "last_name": last.strip(), "city": city.strip(),
            "gender": gender, "slug": chosen_slug.strip(), "is_active": True,
            "first_name_nom": case_vals["first_name_nom"] or first.strip(),
            "last_name_nom":  case_vals["last_name_nom"]  or last.strip(),
            "first_name_gen": case_vals["first_name_gen"], "last_name_gen": case_vals["last_name_gen"],
            "first_name_dat": case_vals["first_name_dat"], "last_name_dat": case_vals["last_name_dat"],
            "first_name_acc": case_vals["first_name_acc"], "last_name_acc": case_vals["last_name_acc"],
            "first_name_ins": case_vals["first_name_ins"], "last_name_ins": case_vals["last_name_ins"],
            "first_name_loc": case_vals["first_name_loc"], "last_name_loc": case_vals["last_name_loc"],
            "first_name_voc": case_vals["first_name_voc"], "last_name_voc": case_vals["last_name_voc"],
        }
        try:
            saved = insert_study(sb, payload)
            st.success(f"✅ Dodano: {saved.get('first_name_nom', first)} {saved.get('last_name_nom', last)} – link: {url_base}/{saved['slug']}")
        except Exception as e:
            st.error(f"❌ Błąd zapisu: {e}")

def edit_view() -> None:
    require_auth(); header("✏️ Edytuj dane badania"); back_button()
    st.markdown('<div class="section-gap-big"></div>', unsafe_allow_html=True)

    studies = fetch_studies(sb)
    if not studies: st.info("Brak rekordów w bazie."); return

    st.markdown('<div class="form-label-strong" style="font-size:16px; margin-bottom:8px;">Wybierz rekord</div>', unsafe_allow_html=True)
    options = {f"{s.get('first_name_nom') or s['first_name']} {s.get('last_name_nom') or s['last_name']} ({s['city']}) – /{s['slug']}": s for s in studies}
    choice = st.selectbox("", options=list(options.keys()))
    st.markdown('<hr class="hr-thin">', unsafe_allow_html=True)

    study = options[choice]
    data = {
        "first_name": study.get("first_name_nom") or study["first_name"],
        "last_name":  study.get("last_name_nom")  or study["last_name"],
        "city": study["city"], "gender": study.get("gender","M"),
    }
    first, last, city, gender = person_fields("edit", data)

    existing = {
        "first_name_nom": first.strip(), "last_name_nom": last.strip(),
        "first_name_gen": study.get("first_name_gen",""), "last_name_gen": study.get("last_name_gen",""),
        "first_name_dat": study.get("first_name_dat",""), "last_name_dat": study.get("last_name_dat",""),
        "first_name_acc": study.get("first_name_acc",""), "last_name_acc": study.get("last_name_acc",""),
        "first_name_ins": study.get("first_name_ins",""), "last_name_ins": study.get("last_name_ins",""),
        "first_name_loc": study.get("first_name_loc",""), "last_name_loc": study.get("last_name_loc",""),
        "first_name_voc": study.get("first_name_voc",""), "last_name_voc": study.get("last_name_voc",""),
    }
    defaults = make_case_defaults(first.strip(), last.strip(), gender)
    with st.expander("Pokaż zaawansowane (odmiana) – opcjonalne"):
        case_vals = render_cases_editor("edit", defaults, existing)

    chosen_slug, free, url_base = url_fields("edit", last, current_slug=study["slug"])

    st.markdown('<div class="section-gap-big"></div>', unsafe_allow_html=True)
    if st.button("Zapisz zmiany", type="primary"):
        if chosen_slug != study["slug"] and not free:
            st.error("Nowy link jest zajęty."); return

        payload = {
            "first_name": first.strip(), "last_name": last.strip(), "city": city.strip(),
            "gender": gender, "slug": chosen_slug.strip(),
            "first_name_nom": case_vals["first_name_nom"] or first.strip(),
            "last_name_nom":  case_vals["last_name_nom"]  or last.strip(),
            "first_name_gen": case_vals["first_name_gen"], "last_name_gen": case_vals["last_name_gen"],
            "first_name_dat": case_vals["first_name_dat"], "last_name_dat": case_vals["last_name_dat"],
            "first_name_acc": case_vals["first_name_acc"], "last_name_acc": case_vals["last_name_acc"],
            "first_name_ins": case_vals["first_name_ins"], "last_name_ins": case_vals["last_name_ins"],
            "first_name_loc": case_vals["first_name_loc"], "last_name_loc": case_vals["last_name_loc"],
            "first_name_voc": case_vals["first_name_voc"], "last_name_voc": case_vals["last_name_voc"],
        }
        try:
            upd = update_study(sb, study["id"], payload)
            st.success(f"✅ Zaktualizowano: {upd.get('first_name_nom', first)} {upd.get('last_name_nom', last)} – /{upd['slug']}")
        except Exception as e:
            st.error(f"❌ Błąd zapisu: {e}")

def results_view() -> None:
    require_auth(); header("📊 Sprawdź wyniki badania archetypu"); back_button()
    wide = st.toggle("Szeroki raport", value=st.session_state.get("wide_report", False))
    st.session_state["wide_report"] = wide
    st.markdown(f'<style>.block-container{{max-width:{ "90vw" if wide else "1160px"} !important}}</style>', unsafe_allow_html=True)

    studies = fetch_studies(sb)
    if not studies: st.info("Brak rekordów w bazie."); return
    options = {f"{s.get('first_name_nom') or s['first_name']} {s.get('last_name_nom') or s['last_name']} ({s['city']}) – /{s['slug']}": s for s in studies}
    study = options[st.selectbox("Wybierz osobę/JST", options=list(options.keys()))]

    try:
        import admin_dashboard as AD
        if hasattr(AD, "show_report"): AD.show_report(sb, study, wide=wide)
        else:
            st.warning("Brak show_report w admin_dashboard.py – poniżej dane rekordu.")
            st.json(study)
    except Exception as e:
        st.error(f"Nie udało się wczytać raportu z admin_dashboard.py: {e}")
        st.json(study)

    st.markdown('<div class="section-gap-big"></div>', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.markdown("### Udostępnij raport")
    st.radio("Metoda", ["E-mail","SMS"], horizontal=True, index=0)
    st.text_area("Adresaci", placeholder="Oddziel przecinkami…")
    st.number_input("Ważność (godziny)", min_value=1, max_value=168, value=48, step=1)
    if st.button("Wygeneruj i zapisz linki", type="primary"):
        st.success("Linki zostały wygenerowane i zapisane (placeholder UI).")
    st.markdown("</div>", unsafe_allow_html=True)

def send_link_view() -> None:
    require_auth(); header("📨 Wyślij link do ankiety"); back_button()
    st.markdown('<div class="ghost-killer">', unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.info("Tu wstawisz logikę wysyłki linku do ankiety (e-mail/SMS).")
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# NAWIGACJA + SIDEBAR
# -----------------------------------------------------------------------------
if "view" not in st.session_state: st.session_state["view"] = "login"
with st.sidebar:
    if logged_in():
        if st.button("Wyloguj"): st.session_state.clear(); st.rerun()

view = st.session_state["view"]
if view == "login":   login_view()
elif view == "home":  home_view()
elif view == "add":   add_view()
elif view == "edit":  edit_view()
elif view == "results": results_view()
elif view == "send":  send_link_view()
else: home_view()
