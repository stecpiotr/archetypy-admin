from __future__ import annotations
from typing import Any, Dict, List, Tuple, Optional
import contextlib
from datetime import datetime, timedelta, timezone
import warnings
import re
import html
import math
import json
import subprocess
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse, quote
import shutil
import urllib.request
import urllib.error
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from zoneinfo import ZoneInfo

from db_utils import (
    get_supabase,
    fetch_studies,
    insert_study,
    update_study,
    check_slug_availability,
)
from db_jst_utils import (
    ARCHETYPES as JST_ARCHETYPES,
    CANONICAL_COLUMNS as JST_CANONICAL_COLUMNS,
    check_jst_slug_availability,
    ensure_jst_schema,
    fetch_jst_response_counts,
    fetch_jst_studies,
    insert_jst_response,
    insert_jst_study,
    list_jst_responses,
    make_payload_from_row as jst_make_payload_from_row,
    normalize_response_row as jst_normalize_response_row,
    response_rows_to_dataframe as jst_response_rows_to_dataframe,
    soft_delete_jst_study,
    update_jst_study,
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
from send_link_jst import render as render_send_link_jst
from jst_analysis import generate_jst_report, inline_local_assets, bundle_report_dir_zip
from streamlit.components.v1 import html as html_component
from email_client import send_email
from report_share import (
    ensure_schema as ensure_report_share_schema,
    create_access as create_report_access,
    list_accesses as list_report_accesses,
    set_status as set_report_access_status,
    delete_access as delete_report_access,
    regrant_access as regrant_report_access,
    set_password as set_report_access_password,
    verify_token_credentials as verify_report_token_credentials,
    get_access_by_token as get_report_access_by_token,
    mark_sent as mark_report_access_sent,
)

warnings.filterwarnings(
    "ignore",
    message="pkg_resources is deprecated as an API",
    category=UserWarning,
    module="docxcompose.properties",
)

st.set_page_config(
    page_title="Archetypy – panel",
    layout="wide",
    initial_sidebar_state="collapsed"   # ← domyślnie zwinięty sidebar
)

# ▼ dodaj po importach, PRZED pierwszym użyciem Plotly/kaleido
import os
for _chrome_candidate in (
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/usr/bin/google-chrome",
    "/usr/local/bin/google-chrome-headless",
):
    if os.path.exists(_chrome_candidate):
        os.environ.setdefault("PLOTLY_CHROME_PATH", _chrome_candidate)
        break


def _first_nonempty(*values: Any) -> str:
    for value in values:
        txt = str(value or "").strip()
        if txt:
            return txt
    return ""


def _secret_get(name: str) -> str:
    try:
        return str(st.secrets.get(name) or "").strip()
    except Exception:
        return ""


def _to_warsaw_time(raw: str) -> str:
    txt = str(raw or "").strip()
    if not txt:
        return ""
    dt_obj: Optional[datetime] = None
    try:
        dt_obj = datetime.fromisoformat(txt.replace("Z", "+00:00"))
    except Exception:
        dt_obj = None
    if dt_obj is None:
        try:
            dt_obj = datetime.fromtimestamp(float(txt), tz=timezone.utc)
        except Exception:
            return ""
    if dt_obj.tzinfo is None:
        dt_obj = dt_obj.replace(tzinfo=timezone.utc)
    try:
        return dt_obj.astimezone(ZoneInfo("Europe/Warsaw")).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ""


@st.cache_data(ttl=600, show_spinner=False)
def _fetch_github_head_commit(repo: str, branch: str, token: str = "") -> Tuple[str, str]:
    repo_slug = str(repo or "").strip().strip("/")
    branch_name = str(branch or "").strip() or "main"
    if not repo_slug:
        return "", ""
    url = f"https://api.github.com/repos/{repo_slug}/commits/{quote(branch_name, safe='')}"
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "archetypy-admin-panel",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=4.5) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
    except Exception:
        return "", ""
    try:
        data = json.loads(raw)
    except Exception:
        return "", ""
    sha = str(data.get("sha") or "").strip()
    commit = data.get("commit") or {}
    committer = commit.get("committer") or {}
    committed_at = str(committer.get("date") or "").strip()
    return sha, committed_at


def _app_build_signature() -> str:
    """Krótki znacznik buildu do szybkiej weryfikacji, czy działa nowy deploy."""
    repo_root = str(Path(__file__).resolve().parent)
    git_bin = shutil.which("git") or "git"

    commit = _first_nonempty(
        os.getenv("STREAMLIT_GIT_COMMIT_SHA"),
        os.getenv("GITHUB_SHA"),
        os.getenv("COMMIT_SHA"),
        os.getenv("VERCEL_GIT_COMMIT_SHA"),
        _secret_get("STREAMLIT_GIT_COMMIT_SHA"),
        _secret_get("GITHUB_SHA"),
        _secret_get("COMMIT_SHA"),
    )
    raw_commit_time = _first_nonempty(
        os.getenv("STREAMLIT_GIT_COMMIT_TIME"),
        os.getenv("GITHUB_COMMIT_TIME"),
        os.getenv("COMMIT_TIME"),
        os.getenv("VERCEL_GIT_COMMIT_TIMESTAMP"),
        os.getenv("SOURCE_COMMIT_TIMESTAMP"),
        _secret_get("STREAMLIT_GIT_COMMIT_TIME"),
        _secret_get("GITHUB_COMMIT_TIME"),
        _secret_get("COMMIT_TIME"),
    )

    if not commit:
        deployed_sha = _first_nonempty(
            _secret_get("DEPLOYED_SHA"),
        )
        if deployed_sha:
            commit = deployed_sha
    if not commit:
        deployed_sha_path = Path(repo_root) / ".deployed_sha"
        if deployed_sha_path.exists():
            try:
                commit = str(deployed_sha_path.read_text(encoding="utf-8", errors="ignore")).strip()
            except Exception:
                commit = ""

    if not commit or not raw_commit_time:
        try:
            if not commit:
                commit = subprocess.run(
                    [git_bin, "-C", repo_root, "rev-parse", "HEAD"],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=5.0,
                ).stdout.strip()
            if not raw_commit_time:
                raw_commit_time = subprocess.run(
                    [git_bin, "-C", repo_root, "show", "-s", "--format=%cI", "HEAD"],
                    capture_output=True,
                    text=True,
                    check=True,
                    timeout=5.0,
                ).stdout.strip()
        except Exception:
            pass

    if not commit or not raw_commit_time:
        gh_repo = _first_nonempty(
            os.getenv("GITHUB_REPOSITORY"),
            _secret_get("GITHUB_REPOSITORY"),
            "stecpiotr/archetypy-admin",
        )
        gh_branch = _first_nonempty(
            os.getenv("GITHUB_REF_NAME"),
            _secret_get("GITHUB_REF_NAME"),
            "main",
        )
        gh_token = _first_nonempty(
            os.getenv("GITHUB_TOKEN"),
            os.getenv("GH_TOKEN"),
            _secret_get("GITHUB_TOKEN"),
            _secret_get("GH_TOKEN"),
        )
        gh_commit, gh_committed_at = _fetch_github_head_commit(gh_repo, gh_branch, gh_token)
        if not commit and gh_commit:
            commit = gh_commit
        if not raw_commit_time and gh_committed_at:
            raw_commit_time = gh_committed_at

    build_time = _to_warsaw_time(raw_commit_time)

    commit_short = commit[:8] if commit else "unknown"

    if build_time:
        return f"build: {build_time} | commit: {commit_short}"
    return f"build: unknown-time | commit: {commit_short}"


def render_build_badge() -> None:
    sig = html.escape(_app_build_signature())
    st.markdown(
        f"""
        <style>
        #ap-build-signature {{
          position: fixed;
          right: 12px;
          bottom: 10px;
          z-index: 99999;
          padding: 5px 10px;
          border-radius: 10px;
          background: rgba(15, 23, 42, 0.80);
          color: #e2e8f0;
          font: 600 12px/1.2 "Segoe UI", Arial, sans-serif;
          letter-spacing: .01em;
          border: 1px solid rgba(255,255,255,.16);
          backdrop-filter: blur(2px);
          box-shadow: 0 4px 16px rgba(0,0,0,.18);
          pointer-events: none;
        }}
        @media (max-width: 900px) {{
          #ap-build-signature {{
            display: none !important;
          }}
        }}
        </style>
        <div id="ap-build-signature">{sig}</div>
        """,
        unsafe_allow_html=True,
    )

# globalna kotwica na samym szczycie aplikacji
st.markdown('<a id="__top__"></a>', unsafe_allow_html=True)

ENABLE_TITLEBAR = False  # ukryj teraz pasek breadcrumbs; ustaw True gdy zechcesz pokazać

def inject_scroll_to_top() -> None:
    st.markdown(
        """
        <style>
          #toTopWrapper{
            position: fixed;
            z-index: 2147483647;
            top: calc(70px + env(safe-area-inset-top, 0px));
            left: 15px;
            width: 0; height: 0;
            pointer-events: none;
          }
          #toTopBtn{
            pointer-events: auto;
            width: 40px; height: 40px;
            border-radius: 999px;
            display: inline-flex; align-items:center; justify-content:center;
            border: 1px solid #D7DEE8;
            background:#FFFFFF;
            color:#8898AC;
            line-height:0;
            box-shadow: 0 1px 2px rgba(0,0,0,.05);
            cursor: pointer;
            transition: transform .08s ease, background .15s ease, border-color .15s ease;
            text-decoration: none; color: inherit;
          }
          #toTopBtn:hover{ background:#F3F6FA; border-color:#CBD5E1; }
          #toTopBtn:active{ transform: translateY(1px) scale(0.98); }
          #toTopBtn svg{ width:18px; height:18px; opacity:.9; }
          @media (prefers-color-scheme: dark){
            #toTopBtn{
              background:#182436;
              border-color:#334155;
              color:#D7DEE8;
            }
            #toTopBtn:hover{
              background:#213145;
              border-color:#475569;
            }
          }
        </style>

        <div id="toTopWrapper" aria-hidden="true">
          <!-- KLUCZ: to jest <a> z href do kotwicy; zadziała nawet bez JS -->
          <a id="toTopBtn" href="#__top__" aria-label="Do góry" title="Do góry">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                 stroke-linecap="round" stroke-linejoin="round">
              <polyline points="18 15 12 9 6 15"></polyline>
            </svg>
          </a>
        </div>

        <script>
        (function(){
          const doc = window.document;

          // usuń duplikaty wrappera i przenieś do <body>
          const olds = Array.from(doc.querySelectorAll('#toTopWrapper'));
          if (olds.length > 1) olds.slice(0, -1).forEach(n => n.remove());
          const wrap = doc.getElementById('toTopWrapper');
          if (wrap && wrap.parentElement !== doc.body) doc.body.appendChild(wrap);

          const btn = doc.getElementById('toTopBtn');
          if (!btn || btn.dataset.bound) return;
          btn.dataset.bound = '1';

          // gdy JS jest dostępny – smooth scroll + dobijanie
          function scrollAllTop(){
            const targets = new Set([
              window,
              doc, doc.documentElement, doc.body, doc.scrollingElement,
              doc.querySelector('section.main'),
              doc.querySelector('[data-testid="stAppViewContainer"]'),
              doc.querySelector('.block-container')?.parentElement
            ].filter(Boolean));

            // dorzuć wszystkie realnie przewijalne
            doc.querySelectorAll('*').forEach(el=>{
              try{
                const s = getComputedStyle(el);
                const can = /(auto|scroll)/.test(s.overflow + s.overflowY + s.overflowX);
                if (can && el.scrollHeight > el.clientHeight + 1) targets.add(el);
              }catch(e){}
            });

            targets.forEach(el=>{
              try{
                if (typeof el.scrollTo === 'function') el.scrollTo({top:0, behavior:'smooth'});
                else if (typeof el.scrollTop === 'number') el.scrollTop = 0;
              }catch(e){}
            });

            // dociśnij w kilku klatkach
            let i=0;
            const nudge=()=> {
              i++;
              targets.forEach(el=>{
                try{ (el===window)? window.scrollTo(0,0) : (el.scrollTop=0); }catch(e){}
              });
              if(i<8) requestAnimationFrame(nudge);
            };
            requestAnimationFrame(nudge);
          }

          // nadpisujemy domyślne przewinięcie #hash tylko po to, by dodać smooth
          btn.addEventListener('click', function(e){
            // pozwól działać hash-jumpowi, ale dodatkowo uruchom „smooth + nudge”
            setTimeout(scrollAllTop, 0);
          }, {passive:true});
        })();
        </script>
        """,
        unsafe_allow_html=True,
    )

# ───────────────────────── styles (bez zmian poza danger button) ────────────────────────
st.markdown(
    """
<style>
:root{ --brand:#178AE6; --brand-hover:#0F6FC0; --line:#E6E9EE; --line-2:#D7DEE8; }
.stApp, .stApp > header { background:#FAFAFA !important; }
.block-container{ max-width:1160px !important; padding-top:72px !important; }
.page-title{ font-size:36px; font-weight:800; color:#111827; letter-spacing:.2px; margin:15px 0 45px 0; padding-bottom:12px; border-bottom:1px solid var(--line); }
.hr-thin{ border:0; border-top:1px solid var(--line); margin:16px 0 22px 0; }
/* Kafelki panelu startowego (3 kolumny) */
body[data-ap-view="home_root"] div[data-testid="stButton"] > button[kind="secondary"]{
  width:100%;
  min-height:156px !important;
  background:#fff !important;
  color:#1F2937 !important;
  border:1px solid var(--line) !important;
  border-radius:16px !important;
  padding:20px 18px !important;
  display:flex;
  align-items:flex-start;
  justify-content:flex-start;
  text-align:left;
  white-space:pre-line;
  line-height:1.32 !important;
  font-size:1.08rem !important;
  font-weight:650 !important;
  transition:transform .12s ease, box-shadow .16s ease, border-color .16s ease;
}
body[data-ap-view="home_root"] div[data-testid="stButton"] > button[kind="secondary"]:hover{
  border-color:#D1D9E4 !important;
  transform:translateY(-2px);
  box-shadow:0 8px 20px rgba(15,23,42,.08);
}
/* Kafelki paneli "Badania personalne" i "Badania mieszkańców" */
body[data-ap-view="home_personal"] div[data-testid="stButton"] > button[kind="secondary"],
body[data-ap-view="home_jst"] div[data-testid="stButton"] > button[kind="secondary"]{
  width:100%;
  min-height:132px !important;
  background:#fff !important;
  color:#0f2847 !important;
  border:1px solid #cfd8e6 !important;
  border-radius:16px !important;
  padding:14px 12px !important;
  display:flex;
  align-items:center;
  justify-content:center;
  text-align:center;
  white-space:pre-line;
  line-height:1.34 !important;
  font-size:1.05rem !important;
  font-weight:600 !important;
  transition:transform .12s ease, box-shadow .16s ease, border-color .16s ease;
}
body[data-ap-view="home_personal"] div[data-testid="stButton"] > button[kind="secondary"]:hover,
body[data-ap-view="home_jst"] div[data-testid="stButton"] > button[kind="secondary"]:hover{
  border-color:#c3d1e6 !important;
  background:#f9fbff !important;
  transform:translateY(-2px);
  box-shadow:0 8px 18px rgba(15,23,42,.06);
}
.top-back-wrap{ margin:0 0 8px 0; }
.top-back-wrap .stButton>button{
  border-radius:12px !important;
  min-height:auto !important;
  height:auto !important;
  padding:7px 12px !important;
  font-weight:600 !important;
  font-size:0.95rem !important;
  text-align:center !important;
  justify-content:center !important;
  align-items:center !important;
}
body[data-ap-view="home_personal"] .top-back-wrap div[data-testid="stButton"] > button[kind="secondary"],
body[data-ap-view="home_jst"] .top-back-wrap div[data-testid="stButton"] > button[kind="secondary"]{
  min-height:auto !important;
  height:auto !important;
  padding:7px 12px !important;
  font-size:0.95rem !important;
  line-height:1.2 !important;
}
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
/* cienka szara linia, używana przed "Udostępnij raport" */
.soft-hr{
  border:0;
  border-top:1px solid var(--line);
  margin:28px 0 10px 0;
}

/* nagłówki sekcji — warianty z dedykowanymi marginesami/czcionką */
.section-title.choose-title{
  font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", "Liberation Sans", sans-serif;
  font-weight: 700;
  font-size: 18px;
  color:#195299;
  margin-top: 18px;
  margin-bottom: 10px;
}
.section-title.share-title{
  font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", "Liberation Sans", sans-serif;
  font-weight: 700;
  font-size: 18px;
  color:#1F2937;
  margin-top: 8px;
  margin-bottom: 14px;
}

/* niebieskie stylowanie selectboxa — tylko w obrębie kontenera #blue-select-scope */
#blue-select-scope .stSelectbox>div>div{
  border:2px solid var(--brand) !important;
  border-radius:10px !important;
  background:#F8FBFF !important;
}
#blue-select-scope .stSelectbox label{
  display:none !important; /* chowamy label, dajemy własny nagłówek */
}

/* przyciski nawigacyjne (Opisy archetypów / Raport / Tabela / Udostępnij) */
.quick-nav{
  display:flex; flex-wrap:wrap; gap:10px; margin:10px 0 14px 0;
}
.quick-nav button{
  cursor:pointer;
  border:1px solid var(--line-2);
  background:#FFFFFF;
  border-radius:10px;
  padding:8px 12px;
  font-weight:600;
}
.quick-nav button:hover{ background:#F3F6FA; border-color:#CBD5E1; }
/* ───── wyniki/raport: szybka nawigacja i drobne poprawki ───── */
.soft-hr{border:0;border-top:1px solid var(--line);margin:28px 0 18px 0;}
.section-label{font-weight:700;font-size:16px;margin:18px 0 8px 0;color:#1F2937;}
.quicknav{display:flex;gap:10px;align-items:center;justify-content:flex-end;flex-wrap:wrap;margin:4px 0 8px;}
.quicknav b.sep{opacity:.6;margin:0 6px;}
.quicknav a{
  display:inline-block;padding:6px 10px;border:1px solid var(--line-2);
  border-radius:10px;text-decoration:none;color:#1F2937;font-weight:600;font-size:13px;
  background:#fff;
}
.quicknav a:hover{border-color:#CBD5E1;background:#F3F6FA}

/* “Wybierz osobę/JST” – niebieska obwódka jak w “Wyślij link…” */
.stSelectbox div[data-baseweb="select"]>div{
  border:1px solid var(--brand) !important;
  box-shadow:0 0 0 1px var(--brand) inset !important;
  border-radius:10px !important;
}

/* ── results: lokalne marginesy dla etykiety i selectboxa ── */
#results-choose .section-label{
  /* TYPOGRAFIA */
  font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", "Liberation Sans", sans-serif;
  font-weight: 630;      /* zmień jeśli chcesz cieńszą: 600/500 */
  font-size: 19px;       /* rozmiar etykiety */
  line-height: 1.25;
  color: #1F2937;

  /* ODSTĘPY: góra | prawo | dół | lewo */
  margin: 6px 0 12px 0;  /* ← edytuj tutaj */
}
#results-choose .stSelectbox{
  margin-bottom: 10px;   /* przerwa pod selectem – edytuj */
}

.share-manage-title{
  font-weight:700;
  font-size:16px;
  margin:0 0 8px 0;
  color:#1f2937;
}
.share-manage-meta{
  display:flex;
  gap:10px;
  flex-wrap:wrap;
  align-items:center;
  margin:0 0 8px 0;
}
.share-chip{
  display:inline-flex;
  align-items:center;
  border-radius:999px;
  padding:4px 10px;
  font-size:12px;
  font-weight:600;
  border:1px solid #cbd5e1;
  background:#f8fafc;
  color:#334155;
}
.share-chip.active{
  background:#ecfdf3;
  border-color:#86efac;
  color:#166534;
}
.share-chip.suspended{
  background:#fff7ed;
  border-color:#fed7aa;
  color:#9a3412;
}
.share-chip.expired{
  background:#f8fafc;
  border-color:#cbd5e1;
  color:#475569;
}
.share-chip.revoked{
  background:#fef2f2;
  border-color:#fecaca;
  color:#991b1b;
}
.share-chip.deleted{
  background:#fef2f2;
  border-color:#fecaca;
  color:#991b1b;
}

/* "Przyznaj ponownie" – spokojniejszy kolor niż domyślny primary */
#regrant-anchor + div button{
  background:#f4f6fb !important;
  color:#1f2937 !important;
  border:1px solid #cfd8e3 !important;
  border-radius:10px !important;
}
#regrant-anchor + div button:hover{
  background:#e9eef6 !important;
  border-color:#b8c4d6 !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# ← TU, już po zamknięciu st.markdown, wywołaj strzałkę:
inject_scroll_to_top()

sb = get_supabase()
JST_SCHEMA_READY = False
JST_SCHEMA_INIT_ATTEMPTED = False
JST_SCHEMA_ERROR: Optional[str] = None


def _ensure_jst_schema_initialized(force_retry: bool = False) -> bool:
    global JST_SCHEMA_READY, JST_SCHEMA_INIT_ATTEMPTED, JST_SCHEMA_ERROR
    if JST_SCHEMA_READY:
        return True
    if JST_SCHEMA_INIT_ATTEMPTED and not force_retry:
        return False
    JST_SCHEMA_INIT_ATTEMPTED = True
    try:
        ensure_jst_schema()
        JST_SCHEMA_READY = True
        JST_SCHEMA_ERROR = None
        return True
    except Exception as exc:
        JST_SCHEMA_READY = False
        JST_SCHEMA_ERROR = str(exc)
        return False

def render_titlebar(crumbs: List[str]) -> None:
    """
    Pasek breadcrumbs – renderuj tylko, gdy ENABLE_TITLEBAR = True.
    (Strzałka '↑' jest wstrzykiwana globalnie przez inject_scroll_to_top().)
    """
    if not ENABLE_TITLEBAR:
        return

    crumbs_html = ' <span class="sep">›</span> '.join(
        [f'<span class="crumb">{c}</span>' for c in crumbs]
    )
    page_title = " / ".join(crumbs)

    st.markdown(
        f"""
        <style>
          #titlebar {{
            position: sticky; top: 0; z-index: 9998;
            background: #FAFAFA;  /* tło jak strona */
            border-bottom:1px solid var(--line);
            padding: 10px 12px; margin: -8px 0 10px 0;
            display:flex; align-items:center; gap:10px;
          }}
          #titlebar .sep   {{ opacity:.55; margin: 0 6px; }}
          #titlebar .crumb {{ font-size:13px; color:#64748B; }}
          #titlebar .crumb:last-child {{ color:#0F172A; font-weight:700; }}
        </style>
        <div id="titlebar">
          <div class="crumbs">{crumbs_html}</div>
        </div>
        <script>
          try {{ document.title = "Archetypy – {page_title}"; }} catch(e) {{}}
        </script>
        """,
        unsafe_allow_html=True,
    )


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


EMAIL_RE = re.compile(r"^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$", re.I)


def _normalize_emails(raw: str) -> List[str]:
    src = (raw or "").replace("\n", ",").replace(";", ",")
    seen = set()
    out: List[str] = []
    for chunk in src.split(","):
        email = chunk.strip().lower()
        if not email:
            continue
        if not EMAIL_RE.match(email):
            continue
        if email in seen:
            continue
        seen.add(email)
        out.append(email)
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
    from_name = st.secrets.get("FROM_NAME", "") or st.secrets.get("SMTP_FROM_NAME", "")

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
    if missing:
        raise RuntimeError("Brak konfiguracji SMTP w secrets.toml: " + ", ".join(missing))
    return host, port, user, pwd, secure, from_email, from_name


def _fmt_local_ts(ts) -> str:
    if not ts:
        return ""
    try:
        val = pd.to_datetime(ts, utc=True, errors="coerce")
        if pd.isna(val):
            return ""
        return val.tz_convert("Europe/Warsaw").strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(ts)


def _sanitize_base_url(raw: str) -> str:
    txt = (raw or "").strip()
    if not txt:
        return ""
    if not txt.startswith(("http://", "https://")):
        txt = "https://" + txt.lstrip("/")
    try:
        parsed = urlparse(txt)
    except Exception:
        return ""
    host = (parsed.netloc or "").strip()
    if not host:
        return ""
    scheme = parsed.scheme or "https"
    return f"{scheme}://{host}".rstrip("/")


def _build_report_link(token: str) -> str:
    base_public = _sanitize_base_url(st.secrets.get("REPORT_PUBLIC_BASE_URL", ""))
    base_secret = _sanitize_base_url(st.secrets.get("REPORT_BASE_URL", ""))

    base = base_public
    if not base and base_secret:
        host = (urlparse(base_secret).netloc or "").lower()
        # Bierz REPORT_BASE_URL tylko jeśli faktycznie wskazuje domenę raportową/lokalną.
        if ("raport." in host or host.startswith("localhost") or host.startswith("127.0.0.1")) and "streamlit.app" not in host:
            base = base_secret

    if not base:
        base = "https://raport.archetypy.badania.pro"

    return f"{base}?token={token}"


def _access_validity_text(row: Dict, hours_value: Optional[int] = None, indefinite: Optional[bool] = None) -> str:
    if indefinite is None:
        indefinite = bool(row.get("indefinite"))
    if indefinite:
        return "do odwołania"

    if hours_value:
        return f"{int(hours_value)} godzin"

    expires = _fmt_local_ts(row.get("expires_at"))
    if expires:
        return f"do {expires}"
    return "czasowo"


_ACCESS_STATUS_LABELS = {
    "active": "aktywne",
    "expired": "wygasłe",
    "suspended": "zawieszone",
    "revoked": "usunięte",
    "deleted": "usunięte",
}

_ACCESS_STATUS_ICONS = {
    "active": "🟢",
    "expired": "⌛",
    "suspended": "⏸️",
    "revoked": "🗑️",
    "deleted": "🗑️",
}


def _is_access_expired(row: Dict, now_utc: Optional[datetime] = None) -> bool:
    if bool(row.get("indefinite")):
        return False
    expires_at = row.get("expires_at")
    if not expires_at:
        return False
    try:
        exp_utc = pd.to_datetime(expires_at, utc=True, errors="coerce")
        if pd.isna(exp_utc):
            return False
        current_utc = now_utc if now_utc is not None else datetime.now(timezone.utc)
        return current_utc > exp_utc.to_pydatetime()
    except Exception:
        return False


def _effective_access_status(row: Dict, now_utc: Optional[datetime] = None) -> str:
    raw_status = str(row.get("status") or "").strip().lower()
    if raw_status in {"revoked", "deleted", "suspended"}:
        return raw_status
    if raw_status == "active" and _is_access_expired(row, now_utc=now_utc):
        return "expired"
    return raw_status or "unknown"


def _access_status_label(status_key: str, with_icon: bool = False) -> str:
    normalized = str(status_key or "").strip().lower()
    label = _ACCESS_STATUS_LABELS.get(normalized, normalized or "—")
    if not with_icon:
        return label
    icon = _ACCESS_STATUS_ICONS.get(normalized, "•")
    return f"{icon} {label}".strip()


def _person_genitive(study: Dict) -> str:
    first = (study.get("first_name_gen") or study.get("first_name_nom") or study.get("first_name") or "").strip()
    last = (study.get("last_name_gen") or study.get("last_name_nom") or study.get("last_name") or "").strip()
    full = f"{first} {last}".strip()
    return full or "tej osoby"


def _fetch_study_by_id(study_id: str) -> Optional[Dict]:
    try:
        res = sb.table("studies").select("*").eq("id", study_id).limit(1).execute()
        data = getattr(res, "data", None) or []
        return data[0] if data else None
    except Exception:
        return None


def _get_query_token() -> str:
    try:
        token = st.query_params.get("token", "")
        if isinstance(token, list):
            token = token[0] if token else ""
        return str(token or "").strip()
    except Exception:
        try:
            qp = st.experimental_get_query_params()
            return str((qp.get("token") or [""])[0]).strip()
        except Exception:
            return ""


def _inject_report_dark_fix_css() -> None:
    st.markdown(
        """
        <style>
        @media (prefers-color-scheme: dark){
          .img,
          .img-profile-sm,
          .ap-ext-zestawy-card,
          .ap-ext-card-modal-img,
          .cluster-figure-wrap img,
          img[src$=".png"],
          img[src$=".jpg"],
          img[src$=".jpeg"]{
            background:#0f172a !important;
          }
          .ap-ext-card-modal-content{
            background:rgba(9,16,27,.75) !important;
            border-color:rgba(148,163,184,.45) !important;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _require_jst_ready() -> bool:
    if _ensure_jst_schema_initialized():
        return True
    if JST_SCHEMA_ERROR:
        st.error(
            "Moduł JST nie został zainicjalizowany poprawnie. "
            "Sprawdź konfigurację bazy i uprawnienia PostgreSQL.\n\n"
            f"Szczegóły: {JST_SCHEMA_ERROR}"
        )
        if st.button("Spróbuj ponownie połączenie JST", type="secondary"):
            _ensure_jst_schema_initialized(force_retry=True)
            st.rerun()
    return False

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


JST_CASES = ["nom", "gen", "dat", "acc", "ins", "loc", "voc"]
POSTSTRAT_GENDER = [(1, "kobieta"), (2, "mężczyzna")]
POSTSTRAT_AGE = [(1, "15-39"), (2, "40-59"), (3, "60 i więcej")]


def _jst_type_forms(jst_type: str) -> Dict[str, str]:
    jt = (jst_type or "miasto").strip().lower()
    if jt == "gmina":
        return {
            "nom": "Gmina",
            "gen": "Gminy",
            "dat": "Gminie",
            "acc": "Gminę",
            "ins": "Gminą",
            "loc": "Gminie",
            "voc": "Gmino",
        }
    return {
        "nom": "Miasto",
        "gen": "Miasta",
        "dat": "Miastu",
        "acc": "Miasto",
        "ins": "Miastem",
        "loc": "Mieście",
        "voc": "Miasto",
    }


def _guess_word_cases(word: str, is_secondary: bool) -> Dict[str, str]:
    w = (word or "").strip()
    if not w:
        return {c: "" for c in JST_CASES}

    low = w.lower()

    # Częsty przymiotnik w drugim członie (np. Biała Podlaska, Niedrzwica Duża)
    if is_secondary and low.endswith(
        (
            "ska", "cka", "dzka", "zka", "na", "ta", "ra", "wa", "la", "ma", "ga",
            "da", "ża", "ła",
        )
    ):
        base = w[:-1]
        return {
            "nom": w,
            "gen": base + "ej",
            "dat": base + "ej",
            "acc": base + "ą",
            "ins": base + "ą",
            "loc": base + "ej",
            "voc": w,
        }

    if low.endswith("a"):
        base = w[:-1]
        gen_end = "i" if base.lower().endswith(("k", "g")) else "y"
        return {
            "nom": w,
            "gen": base + gen_end,
            "dat": base + "ie",
            "acc": base + "ę",
            "ins": base + "ą",
            "loc": base + "ie",
            "voc": w,
        }

    # częste nazwy typu „Poznań”: Poznania, Poznaniowi, Poznaniem, Poznaniu
    if low.endswith("ń"):
        base = w[:-1]
        return {
            "nom": w,
            "gen": base + "nia",
            "dat": base + "niowi",
            "acc": w,
            "ins": base + "niem",
            "loc": base + "niu",
            "voc": base + "niu",
        }

    # uproszczone reguły dla nazw nieżywotnych (miast/gmin) kończących się spółgłoską
    ins_end = "iem" if low.endswith(("k", "g")) else "em"
    loc_end = "u" if low.endswith(("k", "g", "ch", "sz", "cz", "rz", "ż", "ź", "ś")) else "ie"
    return {
        "nom": w,
        "gen": w + "a",
        "dat": w + "owi",
        "acc": w,
        "ins": w + ins_end,
        "loc": w + loc_end,
        "voc": w + loc_end,
    }


def _guess_phrase_cases(phrase: str) -> Dict[str, str]:
    words = [w for w in (phrase or "").split() if w.strip()]
    if not words:
        return {c: "" for c in JST_CASES}

    word_cases = [_guess_word_cases(w, is_secondary=(i > 0)) for i, w in enumerate(words)]
    out: Dict[str, str] = {}
    for c in JST_CASES:
        out[c] = " ".join(x[c] for x in word_cases if x.get(c)).strip()
    return out


def _make_jst_defaults(jst_type: str, jst_name: str) -> Dict[str, str]:
    type_forms = _jst_type_forms(jst_type)
    base_cases = _guess_phrase_cases(jst_name)

    out: Dict[str, str] = {
        "jst_type": (jst_type or "miasto").strip().lower(),
        "jst_name": (jst_name or "").strip(),
    }

    for c in JST_CASES:
        out[f"jst_name_{c}"] = (base_cases.get(c) or "").strip()
        type_piece = type_forms.get(c, "").strip()
        name_piece = out[f"jst_name_{c}"]
        out[f"jst_full_{c}"] = f"{type_piece} {name_piece}".strip()

    return out


def _suggest_jst_slug(jst_type: str, jst_name: str) -> str:
    base = slugify((jst_name or "").strip())
    if not base:
        return ""
    jt = (jst_type or "").strip().lower()
    return f"gmina-{base}" if jt == "gmina" else base


def _jst_option_label(s: Dict[str, Any]) -> str:
    full_nom = (s.get("jst_full_nom") or "").strip()
    if not full_nom:
        full_nom = f"{(s.get('jst_type') or '').title()} {(s.get('jst_name') or '')}".strip()
    slug = (s.get("slug") or "").strip()
    return f"{full_nom} – /{slug}"


def _next_jst_respondent_id(existing: set[str]) -> str:
    max_n = 0
    for rid in existing:
        txt = str(rid or "")
        m = re.fullmatch(r"R(\d{4,})", txt)
        if m:
            max_n = max(max_n, int(m.group(1)))
    n = max_n + 1
    while True:
        cand = f"R{n:04d}"
        if cand not in existing:
            return cand
        n += 1

# ───────────────────────── wspólne UI ─────────────────────────
def back_button(dest: str = "home_personal", label: str = "← Cofnij") -> None:
    st.markdown('<div class="top-back-wrap">', unsafe_allow_html=True)
    if st.button(label, type="secondary"):
        goto(dest)
    st.markdown("</div>", unsafe_allow_html=True)


def _set_view_scope(view_name: str) -> None:
    safe = re.sub(r"[^a-z0-9_-]", "", str(view_name or "").lower())
    if not safe:
        return
    st.markdown(
        f"""
        <script>
        (function(){{
          try {{
            const body = window.parent?.document?.body || document.body;
            if (body) body.setAttribute("data-ap-view", "{safe}");
          }} catch(e) {{}}
        }})();
        </script>
        """,
        unsafe_allow_html=True,
    )

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
            st.session_state["auth_ok"] = True; st.toast("Zalogowano ✅"); goto("home_root")
        else:
            st.error("Błędny login lub hasło.")

def home_personal_view() -> None:
    require_auth()
    _set_view_scope("home_personal")
    back_button("home_root", "← Powrót do wyboru modułu")
    header("Badania personalne - panel")
    render_titlebar(["Panel", "Badania personalne"])

    c1, c2, c3, c4 = st.columns(4, gap="medium")
    with c1:
        if st.button("➕\n\nDodaj badanie archetypu", key="tile_home_personal_add", type="secondary", use_container_width=True):
            goto("add")
    with c2:
        if st.button("✏️\n\nEdytuj dane badania", key="tile_home_personal_edit", type="secondary", use_container_width=True):
            goto("edit")
    with c3:
        if st.button("✉️\n\nWyślij link do ankiety", key="tile_home_personal_send", type="secondary", use_container_width=True):
            goto("send")
    with c4:
        if st.button("📊\n\nSprawdź wyniki badania archetypu", key="tile_home_personal_results", type="secondary", use_container_width=True):
            goto("results")

    # 🔽 linia oddzielająca kafle od statystyk
    st.markdown(
        "<hr style='border:0; border-top:1px solid #E6E9EE; margin:20px 0;'>",
        unsafe_allow_html=True)

    # panel statystyk
    stats_panel()


def home_root_view() -> None:
    require_auth()
    _set_view_scope("home_root")
    header("Archetypy – panel administratora")
    render_titlebar(["Panel", "Start"])

    c1, c2, c3 = st.columns(3, gap="large")
    with c1:
        if st.button("🧑‍💼\nBadania personalne", key="tile_home_root_personal", type="secondary", use_container_width=True):
            goto("home_personal")
    with c2:
        if st.button("🏘️\nBadania mieszkańców", key="tile_home_root_jst", type="secondary", use_container_width=True):
            goto("home_jst")
    with c3:
        if st.button("🧭\nMatching - dopadowywanie profili", key="tile_home_root_matching", type="secondary", use_container_width=True):
            goto("matching")


def home_jst_view() -> None:
    require_auth()
    if not _require_jst_ready():
        return
    _set_view_scope("home_jst")
    back_button("home_root", "← Powrót do wyboru modułu")
    header("Badania mieszkańców - panel")
    render_titlebar(["Panel", "Badania mieszkańców"])

    c1, c2, c3, c4, c5 = st.columns(5, gap="small")
    with c1:
        if st.button("➕\n\nDodaj badanie\nmieszkańców", key="tile_home_jst_add", type="secondary", use_container_width=True):
            goto("jst_add")
    with c2:
        if st.button("✏️\n\nEdytuj dane\nbadania", key="tile_home_jst_edit", type="secondary", use_container_width=True):
            goto("jst_edit")
    with c3:
        if st.button("✉️\n\nWyślij link\ndo ankiety", key="tile_home_jst_send", type="secondary", use_container_width=True):
            goto("jst_send")
    with c4:
        if st.button("💾\n\nImport i eksport\nbaz danych", key="tile_home_jst_io", type="secondary", use_container_width=True):
            goto("jst_io")
    with c5:
        if st.button("📊\n\nAnaliza\nbadania", key="tile_home_jst_analysis", type="secondary", use_container_width=True):
            goto("jst_analysis")

    studies = fetch_jst_studies(sb)
    counts = fetch_jst_response_counts(sb)
    total_resp = int(sum(counts.values()))
    rows = []
    for s in studies:
        sid = str(s.get("id") or "")
        rows.append(
            {
                "JST": (s.get("jst_full_nom") or f"{str(s.get('jst_type') or '').title()} {s.get('jst_name') or ''}").strip(),
                "Link": f"/{s.get('slug') or ''}",
                "Liczba odpowiedzi": int(counts.get(sid, 0)),
                "Data utworzenia": _fmt_local_ts(s.get("created_at")),
            }
        )
    jst_stats_panel(studies, rows, total_resp)


_JST_CASE_LABELS = {
    "nom": "Mianownik (kto? co?)",
    "gen": "Dopełniacz (kogo? czego?)",
    "dat": "Celownik (komu? czemu?)",
    "acc": "Biernik (kogo? co?)",
    "ins": "Narzędnik (z kim? z czym?)",
    "loc": "Miejscownik (o kim? o czym?)",
    "voc": "Wołacz (o!)",
}


def _next_free_jst_slug(base: str, exclude_id: Optional[str] = None) -> str:
    stem = (base or "").strip()
    if not stem:
        return ""
    if check_jst_slug_availability(sb, stem, exclude_id=exclude_id):
        return stem
    n = 2
    while n < 200:
        cand = f"{stem}-{n}"
        if check_jst_slug_availability(sb, cand, exclude_id=exclude_id):
            return cand
        n += 1
    return stem


def _jst_cases_editor(prefix: str, defaults: Dict[str, str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for c in JST_CASES:
        c1, c2 = st.columns([0.32, 0.68])
        with c1:
            st.markdown(f"<div class='form-label-strong'>{_JST_CASE_LABELS[c]}</div>", unsafe_allow_html=True)
        key = f"{prefix}_case_{c}"
        if key not in st.session_state:
            st.session_state[key] = defaults.get(c, "")
        with c2:
            out[c] = st.text_input(
                key,
                value=st.session_state.get(key, defaults.get(c, "")),
                label_visibility="collapsed",
                placeholder=f"Wpisz odmianę ({c})",
            ).strip()
    return out


def _jst_url_editor(prefix: str, jst_type: str, jst_name: str, study_id: Optional[str] = None, current_slug: str = "") -> Tuple[str, bool]:
    base_url = (st.secrets.get("JST_SURVEY_BASE_URL", "https://jst.badania.pro") or "").rstrip("/")
    st.markdown('<div class="section-gap-big"></div>', unsafe_allow_html=True)
    st.markdown(
        "<div style='font-size:18px;font-weight:600;margin-top:10px;margin-bottom:10px;border-top:1px solid #ccc;padding-top:30px;'>Wybór adresu badania</div>",
        unsafe_allow_html=True,
    )

    allow_key = f"{prefix}_allow_custom_slug"
    if allow_key not in st.session_state:
        st.session_state[allow_key] = False
    allow_custom = st.checkbox("Chcę wpisać własny link", key=allow_key)

    suggested = _next_free_jst_slug(_suggest_jst_slug(jst_type, jst_name), exclude_id=study_id)
    if current_slug and not allow_custom:
        suggested = current_slug

    slug_key = f"{prefix}_slug"
    if slug_key not in st.session_state:
        st.session_state[slug_key] = current_slug or suggested
    if not allow_custom:
        st.session_state[slug_key] = current_slug or suggested

    col_l, col_r = st.columns([0.42, 0.58])
    with col_l:
        st.text_input(f"{prefix}_url_base", value=f"{base_url}/", disabled=True, label_visibility="collapsed")
    with col_r:
        slug_val = st.text_input(slug_key, value=st.session_state.get(slug_key, ""), disabled=(not allow_custom), placeholder="np. lublin", label_visibility="collapsed").strip()
    chosen = slug_val if allow_custom else (current_slug or suggested)
    free = check_jst_slug_availability(sb, chosen, exclude_id=study_id) if chosen else False
    st.caption(f"Wybrany: **/{chosen or '—'}** – {'✅ wolny' if free else ('❌ zajęty' if chosen else '—')}")
    return chosen, free


def _jst_payload_from_form(jst_type: str, jst_name: str, forms: Dict[str, str], slug: str) -> Dict[str, Any]:
    f = _jst_type_forms(jst_type)
    payload: Dict[str, Any] = {
        "jst_type": (jst_type or "miasto").strip().lower(),
        "jst_name": (jst_name or "").strip(),
        "slug": (slug or "").strip(),
        "is_active": True,
    }
    for c in JST_CASES:
        name_case = (forms.get(c) or "").strip()
        payload[f"jst_name_{c}"] = name_case
        payload[f"jst_full_{c}"] = f"{f.get(c, '').strip()} {name_case}".strip()
    return payload


def _load_poststrat_targets(study: Dict[str, Any]) -> Dict[str, float]:
    raw = study.get("poststrat_targets")
    if not isinstance(raw, dict):
        return {}
    out: Dict[str, float] = {}
    for g, _ in POSTSTRAT_GENDER:
        for a, _ in POSTSTRAT_AGE:
            key = f"{g}_{a}"
            try:
                v = float(raw.get(key) or 0.0)
            except Exception:
                v = 0.0
            out[key] = max(0.0, v)
    return out


def _normalize_population_15_plus(value: Any) -> Optional[int]:
    txt = str(value or "").strip().replace(" ", "").replace(",", ".")
    if not txt:
        return None
    try:
        num = int(float(txt))
    except Exception:
        return None
    return num if num > 0 else None


def _render_poststrat_editor(prefix: str, current: Dict[str, float]) -> Dict[str, float]:
    st.markdown("### Wagi poststratyfikacyjne (płeć × wiek) – opcjonalne")
    st.caption("Podaj udziały docelowe (%) dla 6 komórek. System automatycznie znormalizuje sumę do 100%.")
    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    hdr = st.columns([1.2, 1, 1, 1], gap="small")
    with hdr[0]:
        st.markdown("**Płeć \\ Wiek**")
    for i, (_, age_lbl) in enumerate(POSTSTRAT_AGE):
        with hdr[i + 1]:
            st.markdown(f"**{age_lbl}**")

    out: Dict[str, float] = {}
    for g, g_lbl in POSTSTRAT_GENDER:
        row = st.columns([1.2, 1, 1, 1], gap="small")
        with row[0]:
            st.markdown(f"**{g_lbl}**")
        for i, (a, _) in enumerate(POSTSTRAT_AGE):
            key = f"{prefix}_post_{g}_{a}"
            if key not in st.session_state:
                st.session_state[key] = float(current.get(f"{g}_{a}", 0.0))
            with row[i + 1]:
                out[f"{g}_{a}"] = float(
                    st.number_input(
                        f"{g_lbl}-{a}",
                        min_value=0.0,
                        max_value=100.0,
                        step=0.1,
                        key=key,
                        label_visibility="collapsed",
                    )
                )

    total = float(sum(out.values()))
    if total > 0:
        st.caption(f"Suma wprowadzonych udziałów: {total:.1f}% (zostanie znormalizowana do 100%).")
    else:
        st.caption("Brak wartości > 0: użyjemy domyślnych proporcji z narzędzia analitycznego.")
    return out


def _xlsx_bytes_from_df(df: pd.DataFrame, sheet_name: str = "Dane") -> bytes:
    out = BytesIO()
    with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
        ws = writer.sheets[sheet_name]
        for i, col in enumerate(df.columns):
            max_len = int(max(len(str(col)), df[col].astype(str).str.len().max() if len(df) else 0))
            ws.set_column(i, i, min(52, max(12, max_len + 2)))
    return out.getvalue()


def jst_add_view() -> None:
    require_auth()
    if not _require_jst_ready():
        return
    header("➕ Dodaj badanie mieszkańców")
    render_titlebar(["Panel", "Badania mieszkańców", "Dodaj badanie"])
    back_button("home_jst")

    c1, c2, c3 = st.columns([1.0, 1.35, 1.0], gap="small")
    with c1:
        jst_type_ui = st.radio("Typ JST", ["Miasto", "Gmina"], horizontal=True)
    with c2:
        st.markdown('<span class="form-label-strong">Nazwa JST (bez członu typu)</span>', unsafe_allow_html=True)
        jst_name = st.text_input("Nazwa JST", placeholder="np. Poznań, Lublin, Biała Podlaska", label_visibility="collapsed").strip()
    with c3:
        st.markdown('<span class="form-label-strong">Podaj liczbę mieszkańców 15+ dla JST:</span>', unsafe_allow_html=True)
        population_15_plus_ui = st.number_input(
            "Liczba mieszkańców 15+",
            min_value=0,
            value=0,
            step=1,
            format="%d",
            label_visibility="collapsed",
            help="Opcjonalnie. Przykład dla Poznania: 466292.",
        )
    jst_type = "miasto" if jst_type_ui == "Miasto" else "gmina"
    population_15_plus = _normalize_population_15_plus(population_15_plus_ui)

    defaults = _make_jst_defaults(jst_type, jst_name)
    if st.button("Uzupełnij odmiany automatycznie", type="secondary"):
        for c in JST_CASES:
            st.session_state[f"jst_add_case_{c}"] = defaults.get(f"jst_name_{c}", "")
        st.rerun()

    with st.expander("Pokaż zaawansowane (odmiana) – opcjonalne", expanded=True):
        forms = _jst_cases_editor(
            "jst_add",
            {c: defaults.get(f"jst_name_{c}", "") for c in JST_CASES},
        )

    slug, slug_free = _jst_url_editor("jst_add", jst_type, jst_name, study_id=None, current_slug="")

    st.markdown('<div class="section-gap-big"></div>', unsafe_allow_html=True)
    if st.button("Zapisz badanie", type="primary"):
        if not jst_name:
            st.error("Uzupełnij nazwę JST.")
            return
        if not slug:
            st.error("Uzupełnij końcówkę linku.")
            return
        if not slug_free:
            st.error("Wybrany link jest zajęty.")
            return
        if any(not (forms.get(c) or "").strip() for c in JST_CASES):
            st.error("Uzupełnij odmiany nazwy JST (mianownik–wołacz).")
            return
        payload = _jst_payload_from_form(jst_type, jst_name, forms, slug)
        payload["population_15_plus"] = population_15_plus
        try:
            saved = insert_jst_study(sb, payload)
            base = (st.secrets.get("JST_SURVEY_BASE_URL", "https://jst.badania.pro") or "").rstrip("/")
            st.success(f"✅ Dodano badanie: {saved.get('jst_full_nom')} – {base}/{saved.get('slug')}")
            for c in JST_CASES:
                st.session_state.pop(f"jst_add_case_{c}", None)
            st.session_state.pop("jst_add_slug", None)
            st.session_state.pop("jst_add_allow_custom_slug", None)
        except Exception as e:
            st.error(f"Błąd zapisu: {e}")


def jst_edit_view() -> None:
    require_auth()
    if not _require_jst_ready():
        return
    header("✏️ Edytuj dane badania mieszkańców")
    render_titlebar(["Panel", "Badania mieszkańców", "Edycja"])
    back_button("home_jst")

    studies = fetch_jst_studies(sb)
    if not studies:
        st.info("Brak badań JST w bazie.")
        return
    options = {_jst_option_label(s): s for s in studies}
    choice = st.selectbox("Wybierz rekord", list(options.keys()), label_visibility="visible")
    study = options[choice]
    active_id = str(study.get("id") or "")
    if st.session_state.get("jst_edit_loaded_id") != active_id:
        st.session_state["jst_edit_loaded_id"] = active_id
        for c in JST_CASES:
            st.session_state[f"jst_edit_case_{c}"] = str(study.get(f"jst_name_{c}") or "")
        st.session_state["jst_edit_slug"] = str(study.get("slug") or "")
        st.session_state["jst_edit_allow_custom_slug"] = False
        ps = _load_poststrat_targets(study)
        for g, _ in POSTSTRAT_GENDER:
            for a, _ in POSTSTRAT_AGE:
                st.session_state[f"jst_edit_post_{g}_{a}"] = float(ps.get(f"{g}_{a}", 0.0))

    type_idx = 0 if str(study.get("jst_type") or "miasto").lower() == "miasto" else 1
    c1, c2, c3 = st.columns([1.0, 1.35, 1.0], gap="small")
    with c1:
        jst_type_ui = st.radio("Typ JST", ["Miasto", "Gmina"], index=type_idx, horizontal=True)
    with c2:
        jst_name = st.text_input("Nazwa JST", value=str(study.get("jst_name") or ""), label_visibility="visible").strip()
    with c3:
        pop_default = int(_normalize_population_15_plus(study.get("population_15_plus")) or 0)
        population_15_plus_ui = st.number_input(
            "Podaj liczbę mieszkańców 15+ dla JST:",
            min_value=0,
            value=pop_default,
            step=1,
            format="%d",
            help="Opcjonalnie. Przykład dla Poznania: 466292.",
        )
    jst_type = "miasto" if jst_type_ui == "Miasto" else "gmina"
    population_15_plus = _normalize_population_15_plus(population_15_plus_ui)

    defaults = {
        c: str(study.get(f"jst_name_{c}") or "")
        for c in JST_CASES
    }
    if st.button("Uzupełnij odmiany automatycznie", type="secondary"):
        auto = _make_jst_defaults(jst_type, jst_name)
        for c in JST_CASES:
            st.session_state[f"jst_edit_case_{c}"] = auto.get(f"jst_name_{c}", "")
        st.rerun()

    with st.expander("Odmiana nazwy JST", expanded=True):
        forms = _jst_cases_editor("jst_edit", defaults)

    poststrat_current = _load_poststrat_targets(study)
    poststrat_targets = _render_poststrat_editor("jst_edit", poststrat_current)

    slug, slug_free = _jst_url_editor(
        "jst_edit",
        jst_type=jst_type,
        jst_name=jst_name,
        study_id=str(study.get("id")),
        current_slug=str(study.get("slug") or ""),
    )

    left, right = st.columns(2)
    with left:
        if st.button("Zapisz zmiany", type="primary"):
            if not jst_name:
                st.error("Uzupełnij nazwę JST.")
                return
            if not slug:
                st.error("Uzupełnij końcówkę linku.")
                return
            if not slug_free and slug != str(study.get("slug") or ""):
                st.error("Wybrany link jest zajęty.")
                return
            if any(not (forms.get(c) or "").strip() for c in JST_CASES):
                st.error("Uzupełnij odmiany nazwy JST (mianownik–wołacz).")
                return
            payload = _jst_payload_from_form(jst_type, jst_name, forms, slug)
            payload["population_15_plus"] = population_15_plus
            if any(float(v or 0.0) > 0 for v in poststrat_targets.values()):
                payload["poststrat_targets"] = {k: float(v) for k, v in poststrat_targets.items() if float(v or 0.0) > 0}
            else:
                payload["poststrat_targets"] = None
            try:
                update_jst_study(sb, str(study["id"]), payload)
                st.success("✅ Zapisano zmiany.")
            except Exception as e:
                st.error(f"Błąd zapisu: {e}")
    with right:
        if st.button("🗑️ Usuń badanie", type="secondary"):
            st.session_state["jst_delete_confirm_id"] = str(study["id"])

    if st.session_state.get("jst_delete_confirm_id") == str(study["id"]):
        with modal("Czy na pewno usunąć to badanie?"):
            st.warning("Tej operacji nie można cofnąć.")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Tak, usuń", type="primary"):
                    try:
                        soft_delete_jst_study(sb, str(study["id"]))
                        st.session_state.pop("jst_delete_confirm_id", None)
                        st.success("Badanie zostało usunięte.")
                        goto("home_jst")
                    except Exception as e:
                        st.error(f"Błąd usuwania: {e}")
            with c2:
                if st.button("Anuluj", type="secondary"):
                    st.session_state.pop("jst_delete_confirm_id", None)
                    st.rerun()


def jst_send_view() -> None:
    require_auth()
    if not _require_jst_ready():
        return
    header("✉️ Wyślij link do ankiety")
    render_titlebar(["Panel", "Badania mieszkańców", "Wyślij link"])
    render_send_link_jst(lambda: back_button("home_jst"))


def jst_io_view() -> None:
    require_auth()
    if not _require_jst_ready():
        return
    header("💾 Import i eksport baz danych")
    render_titlebar(["Panel", "Badania mieszkańców", "Import / eksport"])
    back_button("home_jst")

    studies = fetch_jst_studies(sb)
    if not studies:
        st.info("Brak badań JST w bazie.")
        return

    options = {_jst_option_label(s): s for s in studies}
    chosen = st.selectbox("Wybierz badanie", list(options.keys()))
    study = options[chosen]
    study_id = str(study["id"])

    st.markdown("### Import odpowiedzi (CSV / XLSX)")
    uploaded = st.file_uploader("Wybierz plik", type=["csv", "xlsx"])
    if st.button("Importuj dane", type="primary"):
        if uploaded is None:
            st.error("Wybierz plik do importu.")
        else:
            try:
                with st.spinner("Import trwa. Prosimy o chwilę cierpliwości..."):
                    if uploaded.name.lower().endswith(".xlsx"):
                        src_df = pd.read_excel(uploaded)
                    else:
                        src_df = pd.read_csv(uploaded, encoding="utf-8-sig")
                    if src_df.empty:
                        st.warning("Plik nie zawiera rekordów.")
                        return

                    total_rows = int(len(src_df.index))
                    progress = st.progress(0.0, text=f"Przygotowanie importu ({total_rows} wierszy)...")

                    existing_rows = list_jst_responses(sb, study_id)
                    existing_ids = {str(r.get("respondent_id") or "").strip() for r in existing_rows if str(r.get("respondent_id") or "").strip()}
                    next_id = _next_jst_respondent_id(existing_ids)
                    next_n = int(next_id[1:]) if len(next_id) > 1 and next_id[1:].isdigit() else (len(existing_ids) + 1)

                    inserted = 0
                    skipped = 0
                    progress_every = max(1, total_rows // 120)
                    for idx, (_, row) in enumerate(src_df.iterrows(), start=1):
                        raw = {k: row.get(k) for k in src_df.columns}
                        rid = str(raw.get("respondent_id") or "").strip()
                        if not rid:
                            rid = f"R{next_n:04d}"
                            next_n += 1
                        norm = jst_normalize_response_row(raw, respondent_id_fallback=rid)
                        if not norm.get("respondent_id"):
                            norm["respondent_id"] = rid

                        if norm["respondent_id"] in existing_ids:
                            skipped += 1
                        else:
                            ok = insert_jst_response(
                                sb,
                                study_id=study_id,
                                respondent_id=str(norm["respondent_id"]),
                                payload=jst_make_payload_from_row(norm),
                                source="import",
                                skip_if_exists=True,
                            )
                            if ok:
                                inserted += 1
                                existing_ids.add(str(norm["respondent_id"]))
                            else:
                                skipped += 1

                        if idx == 1 or idx % progress_every == 0 or idx == total_rows:
                            progress.progress(
                                min(1.0, idx / max(total_rows, 1)),
                                text=f"Importowanie rekordów: {idx}/{total_rows}",
                            )

                    progress.progress(1.0, text="Finalizacja importu...")
                    progress.empty()

                st.success(f"Import zakończony. Dodano: {inserted}, pominięto: {skipped}.")
            except Exception as e:
                st.error(f"Błąd importu: {e}")

    st.markdown("---")
    st.markdown("### Eksport odpowiedzi")
    rows = list_jst_responses(sb, study_id)
    if not rows:
        st.info("Brak odpowiedzi do eksportu.")
        return
    out_df = jst_response_rows_to_dataframe(rows)
    slug = str(study.get("slug") or "jst")
    safe_name = slugify(str(study.get("jst_full_nom") or slug)) or slug

    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "Pobierz CSV",
            data=out_df.to_csv(index=False, encoding="utf-8-sig"),
            file_name=f"baza-odpowiedzi-{safe_name}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with c2:
        st.download_button(
            "Pobierz XLSX",
            data=_xlsx_bytes_from_df(out_df, sheet_name="Odpowiedzi"),
            file_name=f"baza-odpowiedzi-{safe_name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    st.dataframe(out_df, use_container_width=True, hide_index=True, height=420)


def _estimate_report_iframe_height(html_text: str, wide_mode: bool) -> int:
    img_count = (html_text or "").lower().count("<img")
    base = 2200 if wide_mode else 1800
    # Duże raporty mają bardzo dużo sekcji i wykresów, więc dajemy zapas wysokości,
    # aby uniknąć dodatkowego scrolla wewnątrz iframe.
    estimated = base + img_count * 320 + int(len(html_text or "") / 3500)
    return max(2200, min(52000, estimated))


def _prepare_report_html_for_iframe(html_text: str) -> str:
    if not html_text:
        return ""
    iframe_fix_css = """
<style>
html, body {
  overflow: visible !important;
  height: auto !important;
}
</style>
"""
    if re.search(r"</head\s*>", html_text, flags=re.IGNORECASE):
        html_text = re.sub(r"</head\s*>", iframe_fix_css + "</head>", html_text, flags=re.IGNORECASE, count=1)
    else:
        html_text = iframe_fix_css + html_text
    autosize_js = """
<script>
(function(){
  function resizeNow(){
    try{
      const h = Math.max(
        document.body ? document.body.scrollHeight : 0,
        document.documentElement ? document.documentElement.scrollHeight : 0
      );
      if (window.frameElement && h > 0){
        window.frameElement.style.height = (h + 32) + 'px';
      }
    }catch(e){}
  }
  window.addEventListener('load', function(){
    resizeNow();
    setTimeout(resizeNow, 120);
    setTimeout(resizeNow, 450);
  });
  if (typeof ResizeObserver !== 'undefined' && document.body){
    try{
      const ro = new ResizeObserver(function(){ resizeNow(); });
      ro.observe(document.body);
    }catch(e){}
  }
  setTimeout(resizeNow, 30);
})();
</script>
"""
    if re.search(r"</body\s*>", html_text, flags=re.IGNORECASE):
        return re.sub(r"</body\s*>", autosize_js + "</body>", html_text, flags=re.IGNORECASE, count=1)
    return html_text + autosize_js


_SEGMENT_HIT_THRESHOLD_DEFAULTS: Dict[str, float] = {
    "2 z 2 · #1": 3.94,
    "4 z 4 · #1": 3.0,
    "3 z 4 · #2": 2.1,
    "1 z 4 · #4": 2.1,
    "1 z 4 · #3": 2.1,
}


def _normalize_segment_threshold_overrides(raw: Any) -> Dict[str, float]:
    out: Dict[str, float] = {}
    if not isinstance(raw, dict):
        return out
    for k, v in raw.items():
        key = str(k or "").strip()
        if not key:
            continue
        try:
            val = float(str(v).replace(",", ".").strip())
        except Exception:
            continue
        out[key] = val
    return out


def _load_segment_threshold_overrides(
    template_root: Path,
    run_base: Path,
    study_id: str,
    study: Dict[str, Any],
) -> Dict[str, float]:
    merged: Dict[str, float] = dict(_SEGMENT_HIT_THRESHOLD_DEFAULTS)
    template_settings = template_root / "settings.json"
    if template_settings.exists():
        try:
            raw_template = json.loads(template_settings.read_text(encoding="utf-8"))
            merged.update(_normalize_segment_threshold_overrides(raw_template.get("segment_hit_threshold_overrides")))
        except Exception:
            pass
    merged.update(_normalize_segment_threshold_overrides(study.get("segment_hit_threshold_overrides")))

    if study_id:
        override_path = run_base / study_id / "segment_hit_threshold_overrides.json"
        if override_path.exists():
            try:
                raw_override = json.loads(override_path.read_text(encoding="utf-8"))
                merged.update(_normalize_segment_threshold_overrides(raw_override))
            except Exception:
                pass
    return merged


def _save_segment_threshold_overrides(run_base: Path, study_id: str, overrides: Dict[str, float]) -> None:
    if not study_id:
        return
    target = run_base / study_id / "segment_hit_threshold_overrides.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(overrides, ensure_ascii=False, indent=2), encoding="utf-8")


def _parse_segment_threshold_overrides_text(text: str) -> Dict[str, float]:
    src = (text or "").strip() or "{}"
    raw = json.loads(src)
    if not isinstance(raw, dict):
        raise ValueError("Wpisz poprawny JSON obiektowy (np. {\"2 z 2 · #1\": 3.94}).")
    return _normalize_segment_threshold_overrides(raw)


def jst_analysis_view() -> None:
    require_auth()
    if not _require_jst_ready():
        return
    header("📊 Analiza badania mieszkańców")
    render_titlebar(["Panel", "Badania mieszkańców", "Analiza"])
    back_button("home_jst")
    if "wide_jst_report" not in st.session_state:
        st.session_state["wide_jst_report"] = True
    wide_jst = st.toggle("🔎 Szeroki raport", key="wide_jst_report")
    if wide_jst:
        st.markdown(
            "<style>.block-container{max-width:100vw !important; padding-left:3vw !important; padding-right:3vw !important;}</style>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<style>.block-container{max-width:1160px !important; padding-left:1rem !important; padding-right:1rem !important;}</style>",
            unsafe_allow_html=True,
        )

    studies = fetch_jst_studies(sb)
    if not studies:
        st.info("Brak badań JST w bazie.")
        return
    options: Dict[str, Optional[Dict[str, Any]]] = {"-": None}
    options.update({_jst_option_label(s): s for s in studies})
    chosen = st.selectbox("Wybierz badanie", list(options.keys()))
    study = options.get(chosen)
    has_study = isinstance(study, dict)

    sid = str((study or {}).get("id") or "")
    template_root = Path(__file__).resolve().parent / "JST_Archetypy_Analiza"
    run_base = template_root / "_runs"
    cache_key = f"jst_report_html_v2_{sid}"
    cache_meta_key = f"jst_report_meta_v2_{sid}"
    inline_limit = int(st.secrets.get("JST_REPORT_INLINE_LIMIT_BYTES", 45_000_000) or 45_000_000)
    inline_source_limit = int(st.secrets.get("JST_REPORT_INLINE_SOURCE_LIMIT_BYTES", 70_000_000) or 70_000_000)
    safe_message_limit = int(st.secrets.get("JST_REPORT_SAFE_MESSAGE_LIMIT_BYTES", 185_000_000) or 185_000_000)

    c1, c2 = st.columns([0.35, 0.65], gap="small")
    with c1:
        generate_now = st.button(
            "Generuj raport",
            type="primary",
            use_container_width=True,
            disabled=not has_study,
        )
    with c2:
        regenerate_now = st.button(
            "Przelicz od nowa",
            type="secondary",
            use_container_width=True,
            disabled=not has_study,
        )

    if not has_study:
        st.info("Wybierz badanie z listy i kliknij „Generuj raport”.")
        return

    overrides_editor_key = f"jst_segment_threshold_editor_{sid}"
    saved_overrides = _load_segment_threshold_overrides(template_root, run_base, sid, study or {})
    if overrides_editor_key not in st.session_state:
        st.session_state[overrides_editor_key] = json.dumps(saved_overrides, ensure_ascii=False, indent=2)

    with st.expander("⚙️ segment_hit_threshold_overrides", expanded=False):
        st.caption(
            "Możesz tutaj zmieniać i dodawać progi segmentów. "
            "Zmiana zostanie uwzględniona przy generowaniu nowego raportu."
        )
        st.text_area(
            "segment_hit_threshold_overrides (JSON)",
            key=overrides_editor_key,
            height=220,
            label_visibility="collapsed",
        )
        cset1, cset2 = st.columns(2)
        with cset1:
            if st.button("💾 Zapisz progi segmentów", key=f"save_segment_overrides_{sid}", use_container_width=True):
                try:
                    parsed = _parse_segment_threshold_overrides_text(str(st.session_state.get(overrides_editor_key) or "{}"))
                    _save_segment_threshold_overrides(run_base, sid, parsed)
                    st.success("Zapisano progi segmentów dla tego badania.")
                except Exception as e:
                    st.error(f"Niepoprawny JSON progów: {e}")
        with cset2:
            if st.button("↩ Przywróć domyślne", key=f"reset_segment_overrides_{sid}", use_container_width=True):
                st.session_state[overrides_editor_key] = json.dumps(_SEGMENT_HIT_THRESHOLD_DEFAULTS, ensure_ascii=False, indent=2)
                _save_segment_threshold_overrides(run_base, sid, dict(_SEGMENT_HIT_THRESHOLD_DEFAULTS))
                st.success("Przywrócono domyślne progi segmentów.")

    if generate_now or regenerate_now:
        try:
            active_overrides = _parse_segment_threshold_overrides_text(str(st.session_state.get(overrides_editor_key) or "{}"))
        except Exception as e:
            st.error(f"Nie można wygenerować raportu: niepoprawny JSON progów segmentów ({e}).")
            return
        rows = list_jst_responses(sb, sid)
        if not rows:
            st.warning("To badanie nie ma jeszcze żadnych odpowiedzi.")
            return
        out_df = jst_response_rows_to_dataframe(rows)
        study_for_report = dict(study or {})
        study_for_report["segment_hit_threshold_overrides"] = active_overrides
        with st.spinner("Generujemy raport dla tego badania. Prosimy o chwilę cierpliwości."):
            try:
                report_path = generate_jst_report(
                    template_root=template_root,
                    run_base_dir=run_base,
                    study=study_for_report,
                    data_df=out_df[JST_CANONICAL_COLUMNS].copy(),
                    force=bool(regenerate_now),
                )
                raw_html = report_path.read_text(encoding="utf-8", errors="ignore")
                raw_bytes = len(raw_html.encode("utf-8", errors="ignore"))
                inlined = ""
                inlined_bytes = 0
                inline_error = ""
                if raw_bytes <= inline_source_limit:
                    try:
                        inlined = inline_local_assets(raw_html, report_path.parent)
                        inlined_bytes = len(inlined.encode("utf-8", errors="ignore"))
                    except Exception as ex:
                        inline_error = str(ex)
                        inlined = ""
                        inlined_bytes = 0
                inlined_used = bool(inlined and inlined_bytes <= safe_message_limit and inlined_bytes <= inline_limit)
                if inlined_used:
                    st.session_state[cache_key] = inlined
                elif raw_bytes <= safe_message_limit:
                    st.session_state[cache_key] = raw_html
                else:
                    st.session_state[cache_key] = "__report_path_only__"
                st.session_state[cache_meta_key] = {
                    "report_path": str(report_path),
                    "raw_bytes": raw_bytes,
                    "inlined_bytes": inlined_bytes,
                    "inlined_used": inlined_used,
                    "inline_error": inline_error,
                    "inline_limit": inline_limit,
                    "inline_source_limit": inline_source_limit,
                    "safe_message_limit": safe_message_limit,
                }
                st.success("Raport gotowy.")
            except Exception as e:
                st.error(f"Nie udało się wygenerować raportu: {e}")
                return

    rendered = st.session_state.get(cache_key)
    meta = st.session_state.get(cache_meta_key) or {}
    if not rendered:
        rows = list_jst_responses(sb, sid)
        if not rows:
            st.warning("To badanie nie ma jeszcze żadnych odpowiedzi.")
        else:
            st.caption("Kliknij „Generuj raport”, aby wyświetlić raport.")
        return

    report_path_str = str(meta.get("report_path") or "")
    report_path = Path(report_path_str) if report_path_str else None
    raw_bytes = int(meta.get("raw_bytes") or 0)
    inlined_bytes = int(meta.get("inlined_bytes") or 0)
    inlined_used = bool(meta.get("inlined_used"))
    safe_limit = int(meta.get("safe_message_limit") or safe_message_limit)

    if report_path and report_path.exists():
        report_slug = slugify(str((study or {}).get("jst_full_nom") or (study or {}).get("slug") or "raport-jst")) or "raport-jst"
        raw_report = report_path.read_text(encoding="utf-8", errors="ignore")
        full_report = raw_report
        try:
            full_report = inline_local_assets(raw_report, report_path.parent)
        except Exception:
            full_report = raw_report
        report_zip = bundle_report_dir_zip(report_path.parent)
        d1, d2 = st.columns(2)
        with d1:
            st.download_button(
                "📥 Pobierz raport HTML (pełny)",
                data=full_report,
                file_name=f"{report_slug}.html",
                mime="text/html",
                use_container_width=True,
            )
        with d2:
            if report_zip:
                st.download_button(
                    "🧳 Pobierz raport ZIP (WYNIKI)",
                    data=report_zip,
                    file_name=f"{report_slug}-WYNIKI.zip",
                    mime="application/zip",
                    use_container_width=True,
                )
            else:
                st.caption("Nie udało się przygotować paczki ZIP raportu.")

    preview_enabled = st.toggle(
        "Podgląd raportu online w panelu",
        value=False,
        key=f"jst_preview_online_{sid}",
    )
    if not preview_enabled:
        st.info(
            "Podgląd online jest wyłączony. To tryb stabilny dla dużych raportów. "
            "Pobierz raport HTML (pełny) albo paczkę ZIP i otwórz lokalnie."
        )
        return

    if inlined_bytes > int(meta.get("inline_limit") or inline_limit):
        st.warning(
            "Raport jest duży. Domyślnie zalecamy tryb lekki, a pełny podgląd może wolniej działać na słabszych urządzeniach."
        )
    if meta.get("inline_error"):
        st.caption("Uwaga techniczna: nie udało się osadzić części zasobów raportu, dlatego użyty został tryb bezpieczniejszy.")

    auto_light = (not inlined_used) or (inlined_bytes > safe_limit and raw_bytes <= safe_limit)
    light_mode = st.toggle(
        "Tryb lekki renderowania (szybciej, bez osadzonych wykresów)",
        value=auto_light,
        key=f"jst_light_mode_{sid}",
    )
    if rendered:
        to_render = rendered
        if to_render == "__report_path_only__":
            if report_path and report_path.exists():
                to_render = report_path.read_text(encoding="utf-8", errors="ignore")
            else:
                st.error("Nie udało się odnaleźć pliku raportu do podglądu.")
                return
        if light_mode and report_path and report_path.exists():
            to_render = report_path.read_text(encoding="utf-8", errors="ignore")
            st.info("Tryb lekki jest włączony. Raport renderuje się szybciej i stabilniej przy dużych danych.")
        elif (not light_mode) and (not inlined_used) and report_path and report_path.exists():
            to_render = report_path.read_text(encoding="utf-8", errors="ignore")

        render_size = len(to_render.encode("utf-8", errors="ignore"))
        if render_size > safe_limit:
            st.error(
                "Podgląd raportu w panelu został wyłączony, bo przekracza bezpieczny limit przesyłania danych do przeglądarki."
            )
            st.info("Użyj przycisku „📥 Pobierz raport HTML (pełny)” lub „🧳 Pobierz raport ZIP (WYNIKI)” i otwórz lokalnie.")
            return

        prepared = _prepare_report_html_for_iframe(to_render)
        html_component(
            prepared,
            height=_estimate_report_iframe_height(prepared, wide_mode=wide_jst),
            scrolling=False,
        )


def _load_personal_profile_pct(study_id: str) -> Tuple[Dict[str, float], int]:
    try:
        import admin_dashboard as AD
    except Exception:
        return {}, 0

    try:
        df = AD.load(study_id=study_id)
    except Exception:
        return {}, 0
    if df is None or len(df) == 0:
        return {}, 0

    sums = {a: 0.0 for a in JST_ARCHETYPES}
    n = 0
    for ans in df.get("answers", []):
        scores = AD.archetype_scores(ans)
        if not isinstance(scores, dict):
            continue
        n += 1
        for a in JST_ARCHETYPES:
            val = scores.get(a)
            if val is None:
                continue
            sums[a] += float(val)
    if n <= 0:
        return {}, 0
    pct = {a: round((sums[a] / n) / 20.0 * 100.0, 2) for a in JST_ARCHETYPES}
    return pct, n


JST_A_PAIRS: List[Tuple[str, str, str]] = [
    ("A1", "Opiekun", "Odkrywca"),
    ("A2", "Towarzysz", "Władca"),
    ("A3", "Opiekun", "Twórca"),
    ("A4", "Mędrzec", "Bohater"),
    ("A5", "Władca", "Buntownik"),
    ("A6", "Niewinny", "Odkrywca"),
    ("A7", "Buntownik", "Kochanek"),
    ("A8", "Opiekun", "Bohater"),
    ("A9", "Towarzysz", "Czarodziej"),
    ("A10", "Kochanek", "Bohater"),
    ("A11", "Władca", "Błazen"),
    ("A12", "Niewinny", "Czarodziej"),
    ("A13", "Czarodziej", "Mędrzec"),
    ("A14", "Towarzysz", "Twórca"),
    ("A15", "Błazen", "Niewinny"),
    ("A16", "Odkrywca", "Mędrzec"),
    ("A17", "Kochanek", "Buntownik"),
    ("A18", "Błazen", "Twórca"),
]
JST_A_PAIR_COUNTS: Dict[str, int] = {
    a: sum(1 for _, left, right in JST_A_PAIRS if left == a or right == a) for a in JST_ARCHETYPES
}


def _calc_jst_target_profile(rows: List[Dict[str, Any]]) -> Tuple[Dict[str, float], List[Dict[str, Any]], Dict[str, Any]]:
    if not rows:
        return {}, [], {}
    totals = {a: 0.0 for a in JST_ARCHETYPES}
    respondent_vectors: List[Dict[str, Any]] = []
    component_sums: Dict[str, Dict[str, float]] = {
        a: {"A": 0.0, "B1": 0.0, "B2": 0.0, "D13": 0.0, "TOTAL": 0.0} for a in JST_ARCHETYPES
    }
    a_valid_total = 0
    a_expected_total = len(rows) * len(JST_A_PAIRS)
    a_valid_by_q = {qid: 0 for qid, _, _ in JST_A_PAIRS}
    b1_selected_total = 0
    b2_valid_total = 0
    d13_valid_total = 0

    def _parse_a_value(raw: Any) -> Optional[int]:
        try:
            val = int(float(str(raw).strip().replace(",", ".")))
        except Exception:
            return None
        return val if 1 <= val <= 7 else None

    for rec in rows:
        payload = rec.get("payload") or {}
        if not isinstance(payload, dict):
            payload = {}

        # Oczekiwania mieszkańców z komponentem A:
        # A = 40% (średnia preferencja z par A1..A18),
        # B1 = 20% (czy archetyp jest w TOP3),
        # B2 = 25% (czy archetyp jest TOP1),
        # D13 = 15% (archetyp preferowany w pytaniu D13).
        # Każdy archetyp kończy ze skalą 0..100 i nie jest sztucznie
        # normalizowany do sumy 100%.
        a_acc = {a: 0.0 for a in JST_ARCHETYPES}
        for qid, left_arch, right_arch in JST_A_PAIRS:
            val = _parse_a_value(payload.get(qid))
            if val is None:
                continue
            a_valid_total += 1
            a_valid_by_q[qid] = int(a_valid_by_q.get(qid, 0)) + 1
            p_right = float(val - 1) / 6.0
            p_left = 1.0 - p_right
            if left_arch in a_acc:
                a_acc[left_arch] += p_left
            if right_arch in a_acc:
                a_acc[right_arch] += p_right

        selected_b1 = {
            a
            for a in JST_ARCHETYPES
            if str(payload.get(f"B1_{a}") or "").strip().lower() in {"1", "1.0", "true", "t", "tak", "yes", "y"}
        }
        arch_by_lower = {a.casefold(): a for a in JST_ARCHETYPES}
        b2_raw = str(payload.get("B2") or "").strip()
        d13_raw = str(payload.get("D13") or "").strip()
        b2 = arch_by_lower.get(b2_raw.casefold(), b2_raw)
        d13 = arch_by_lower.get(d13_raw.casefold(), d13_raw)
        b1_selected_total += int(len(selected_b1))
        if b2 in JST_ARCHETYPES:
            b2_valid_total += 1
        if d13 in JST_ARCHETYPES:
            d13_valid_total += 1

        vec: Dict[str, float] = {}
        for a in JST_ARCHETYPES:
            denom = float(JST_A_PAIR_COUNTS.get(a, 1) or 1)
            a_norm = float(a_acc.get(a, 0.0)) / denom
            b1_hit = 1.0 if a in selected_b1 else 0.0
            b2_hit = 1.0 if b2 == a else 0.0
            d13_hit = 1.0 if d13 == a else 0.0
            a_component = 0.40 * a_norm * 100.0
            b1_component = 0.20 * b1_hit * 100.0
            b2_component = 0.25 * b2_hit * 100.0
            d13_component = 0.15 * d13_hit * 100.0
            score = a_component + b1_component + b2_component + d13_component
            vec[a] = score
            component_sums[a]["A"] += a_component
            component_sums[a]["B1"] += b1_component
            component_sums[a]["B2"] += b2_component
            component_sums[a]["D13"] += d13_component
            component_sums[a]["TOTAL"] += score

        for a in JST_ARCHETYPES:
            totals[a] += vec[a]
        respondent_vectors.append({"payload": payload, "vec": vec})

    n = float(len(rows))
    profile = {a: round((totals[a] / n), 2) for a in JST_ARCHETYPES}
    rows_n = int(len(rows))
    component_means = {
        a: {
            "A": round(component_sums[a]["A"] / max(1, rows_n), 2),
            "B1": round(component_sums[a]["B1"] / max(1, rows_n), 2),
            "B2": round(component_sums[a]["B2"] / max(1, rows_n), 2),
            "D13": round(component_sums[a]["D13"] / max(1, rows_n), 2),
            "TOTAL": round(component_sums[a]["TOTAL"] / max(1, rows_n), 2),
        }
        for a in JST_ARCHETYPES
    }
    audit: Dict[str, Any] = {
        "rows_n": rows_n,
        "a_valid_rate_pct": round((100.0 * a_valid_total / a_expected_total), 1) if a_expected_total > 0 else 0.0,
        "a_valid_by_q_rate_pct": {
            qid: round((100.0 * int(cnt) / max(1, rows_n)), 1) for qid, cnt in a_valid_by_q.items()
        },
        "b1_mean_selected": round(float(b1_selected_total) / max(1, rows_n), 2),
        "b2_valid_rate_pct": round((100.0 * b2_valid_total / max(1, rows_n)), 1),
        "d13_valid_rate_pct": round((100.0 * d13_valid_total / max(1, rows_n)), 1),
        "component_means_by_archetype": component_means,
    }
    return profile, respondent_vectors, audit


def _dot(a: Dict[str, float], b: Dict[str, float]) -> float:
    return float(sum(float(a.get(k, 0.0)) * float(b.get(k, 0.0)) for k in JST_ARCHETYPES))


def _norm(a: Dict[str, float]) -> float:
    return float(sum(float(a.get(k, 0.0)) ** 2 for k in JST_ARCHETYPES)) ** 0.5


def matching_view() -> None:
    require_auth()
    if not _require_jst_ready():
        return
    back_button("home_root", "← Powrót do wyboru modułu")
    header("🧭 Matching")
    render_titlebar(["Panel", "Matching"])

    personal_studies = fetch_studies(sb)
    jst_studies = fetch_jst_studies(sb)
    if not personal_studies:
        st.info("Brak badań personalnych.")
        return
    if not jst_studies:
        st.info("Brak badań mieszkańców.")
        return

    p_options = {
        f"{(s.get('last_name_nom') or s.get('last_name') or '')} {(s.get('first_name_nom') or s.get('first_name') or '')} ({s.get('city') or ''}) – /{s.get('slug') or ''}": s
        for s in personal_studies
    }
    j_options = {_jst_option_label(s): s for s in jst_studies}

    tab_pick, tab_summary, tab_demo, tab_strategy = st.tabs(["Wybierz badania", "Podsumowanie", "Demografia", "Strategia komunikacji"])

    with tab_pick:
        pick_personal = st.selectbox("Badanie personalne", list(p_options.keys()))
        pick_jst = st.selectbox("Badanie mieszkańców", list(j_options.keys()))
        if st.button("Połącz i policz matching", type="primary"):
            person = p_options[pick_personal]
            jst_study = j_options[pick_jst]

            p_profile, p_n = _load_personal_profile_pct(str(person.get("id")))
            j_rows = list_jst_responses(sb, str(jst_study.get("id")))
            j_profile, respondent_vectors, target_audit = _calc_jst_target_profile(j_rows)

            if not p_profile:
                st.error("Nie udało się policzyć profilu personalnego (brak odpowiedzi).")
                return
            if not j_profile:
                st.error("Nie udało się policzyć profilu mieszkańców (brak odpowiedzi).")
                return

            diffs = {a: abs(float(p_profile.get(a, 0.0)) - float(j_profile.get(a, 0.0))) for a in JST_ARCHETYPES}
            diff_vals = [float(v) for v in diffs.values()]
            mae = float(sum(diff_vals) / max(1, len(diff_vals)))
            rmse = math.sqrt(float(sum(v * v for v in diff_vals) / max(1, len(diff_vals))))
            sorted_gaps_desc = sorted(diff_vals, reverse=True)
            top3_gap_mae = float(sum(sorted_gaps_desc[:3]) / max(1, min(3, len(sorted_gaps_desc))))

            score_mae = max(0.0, min(100.0, 100.0 - mae))
            score_rmse = max(0.0, min(100.0, 100.0 - rmse))
            score_top3 = max(0.0, min(100.0, 100.0 - top3_gap_mae))
            # Metryka mieszana: średni błąd + kara za duże odchylenia i największe luki.
            match_score = max(0.0, min(100.0, 0.40 * score_mae + 0.25 * score_rmse + 0.35 * score_top3))

            strengths = sorted(JST_ARCHETYPES, key=lambda a: diffs[a])[:3]
            gaps = sorted(JST_ARCHETYPES, key=lambda a: diffs[a], reverse=True)[:3]
            strengths_rows = [{"archetyp": a, "diff": round(float(diffs[a]), 1)} for a in strengths]
            gaps_rows = [{"archetyp": a, "diff": round(float(diffs[a]), 1)} for a in gaps]

            if match_score >= 80:
                match_band = ("Bardzo wysokie", "Różnice są niskie i stabilne także na największych lukach.")
            elif match_score >= 65:
                match_band = ("Umiarkowanie wysokie", "Profil jest częściowo zgodny, ale wymaga korekty na największych lukach.")
            elif match_score >= 50:
                match_band = ("Umiarkowane", "Widać istotne rozjazdy między profilem polityka i oczekiwaniami mieszkańców.")
            else:
                match_band = ("Niskie", "Duże luki dominują - warto przebudować komunikację i priorytety.")

            unit_person = {a: float(p_profile.get(a, 0.0)) for a in JST_ARCHETYPES}
            top_sim_rows = []
            base_norm = _norm(unit_person) or 1.0
            for rec in respondent_vectors:
                vec = {a: float(rec["vec"].get(a, 0.0)) for a in JST_ARCHETYPES}
                sim = _dot(unit_person, vec) / (base_norm * (_norm(vec) or 1.0))
                top_sim_rows.append({"sim": sim, "payload": rec.get("payload") or {}})
            top_sim_rows.sort(key=lambda x: x["sim"], reverse=True)
            take_n = max(1, int(len(top_sim_rows) * 0.25))
            subset = top_sim_rows[:take_n]

            all_payloads = [r.get("payload") or {} for r in top_sim_rows]
            subset_payloads = [r.get("payload") or {} for r in subset]
            jst_name_nom = str(jst_study.get("jst_full_nom") or "").strip() or str(jst_study.get("jst_name") or "").strip() or str(pick_jst)

            dim_specs = [
                {
                    "label": "Płeć",
                    "field": "M_PLEC",
                    "order": ["kobieta", "mężczyzna"],
                    "emoji": {"kobieta": "👩", "mężczyzna": "👨"},
                },
                {
                    "label": "Wiek",
                    "field": "M_WIEK",
                    "order": ["15-39", "40-59", "60+"],
                    "emoji": {"15-39": "🧑", "40-59": "🧑‍💼", "60+": "🧓"},
                },
                {
                    "label": "Wykształcenie",
                    "field": "M_WYKSZT",
                    "order": ["podst./gim./zaw.", "średnie", "wyższe"],
                    "emoji": {"podst./gim./zaw.": "🛠️", "średnie": "📘", "wyższe": "🎓"},
                },
                {
                    "label": "Status zawodowy",
                    "field": "M_ZAWOD",
                    "order": ["prac. umysłowy", "prac. fizyczny", "własna firma", "student/uczeń", "bezrobotny", "rencista/emeryt", "inna"],
                    "emoji": {
                        "prac. umysłowy": "🧠",
                        "prac. fizyczny": "🛠️",
                        "własna firma": "🏢",
                        "student/uczeń": "🧑‍🎓",
                        "bezrobotny": "🔎",
                        "rencista/emeryt": "🌿",
                        "inna": "🧩",
                    },
                },
                {
                    "label": "Sytuacja materialna",
                    "field": "M_MATERIAL",
                    "order": ["bardzo dobra", "raczej dobra", "przeciętna", "raczej zła", "bardzo zła", "odmowa"],
                    "emoji": {
                        "bardzo dobra": "😄",
                        "raczej dobra": "🙂",
                        "przeciętna": "😐",
                        "raczej zła": "🙁",
                        "bardzo zła": "😟",
                        "odmowa": "🤐",
                    },
                },
            ]

            def _norm_demo(value: Any) -> str:
                txt = str(value or "").strip().lower()
                for src, dst in (("ą", "a"), ("ć", "c"), ("ę", "e"), ("ł", "l"), ("ń", "n"), ("ó", "o"), ("ś", "s"), ("ż", "z"), ("ź", "z")):
                    txt = txt.replace(src, dst)
                return re.sub(r"\s+", " ", txt)

            def _canon_demo(field: str, value: Any) -> str:
                raw = str(value or "").strip()
                n = _norm_demo(value)
                if not n:
                    return "brak danych"
                if field == "M_PLEC":
                    if n in {"1", "k", "kobieta"} or "kobiet" in n:
                        return "kobieta"
                    if n in {"2", "m", "mezczyzna"} or "mezczyzn" in n:
                        return "mężczyzna"
                elif field == "M_WIEK":
                    if re.search(r"15\D*39", n):
                        return "15-39"
                    if re.search(r"40\D*59", n):
                        return "40-59"
                    if "60" in n:
                        return "60+"
                elif field == "M_WYKSZT":
                    if "wyzsze" in n:
                        return "wyższe"
                    if "srednie" in n:
                        return "średnie"
                    if any(k in n for k in ("podstaw", "gimnaz", "zawod")):
                        return "podst./gim./zaw."
                elif field == "M_ZAWOD":
                    if "umysl" in n:
                        return "prac. umysłowy"
                    if "fizycz" in n:
                        return "prac. fizyczny"
                    if "wlasn" in n and "firm" in n:
                        return "własna firma"
                    if "student" in n or "uczen" in n:
                        return "student/uczeń"
                    if "bezrobot" in n:
                        return "bezrobotny"
                    if "renc" in n or "emery" in n:
                        return "rencista/emeryt"
                    if "inna" in n or "jaka" in n:
                        return "inna"
                elif field == "M_MATERIAL":
                    if "odmaw" in n:
                        return "odmowa"
                    if "bardzo dobrze" in n or "bardzo dobra" in n:
                        return "bardzo dobra"
                    if "raczej dobrze" in n or "raczej dobra" in n:
                        return "raczej dobra"
                    if "przeciet" in n or "srednio" in n:
                        return "przeciętna"
                    if "raczej zle" in n or "raczej zla" in n:
                        return "raczej zła"
                    if "bardzo zle" in n or "bardzo zla" in n or "ciezk" in n:
                        return "bardzo zła"
                return raw or "brak danych"

            def _poststrat_cell(payload: Dict[str, Any]) -> Optional[str]:
                g = _canon_demo("M_PLEC", payload.get("M_PLEC"))
                a = _canon_demo("M_WIEK", payload.get("M_WIEK"))
                if g == "kobieta":
                    g_id = 1
                elif g == "mężczyzna":
                    g_id = 2
                else:
                    return None
                if a == "15-39":
                    a_id = 1
                elif a == "40-59":
                    a_id = 2
                elif a == "60+":
                    a_id = 3
                else:
                    return None
                return f"{g_id}_{a_id}"

            def _calc_poststrat_weights(payloads: List[Dict[str, Any]], study: Dict[str, Any]) -> Tuple[List[float], bool]:
                if not payloads:
                    return [], False
                targets = _load_poststrat_targets(study)
                target_sum = float(sum(float(v or 0.0) for v in targets.values()))
                if target_sum <= 0:
                    return [1.0] * len(payloads), False

                sample_counts: Dict[str, int] = {}
                for p in payloads:
                    cell = _poststrat_cell(p)
                    if cell:
                        sample_counts[cell] = int(sample_counts.get(cell, 0)) + 1
                present_cells = [k for k, v in sample_counts.items() if int(v) > 0]
                if not present_cells:
                    return [1.0] * len(payloads), False

                present_target_sum = float(sum(float(targets.get(k, 0.0) or 0.0) for k in present_cells))
                if present_target_sum <= 0:
                    return [1.0] * len(payloads), False

                sample_total = float(sum(sample_counts.values()))
                if sample_total <= 0:
                    return [1.0] * len(payloads), False

                cell_weights: Dict[str, float] = {}
                for k in present_cells:
                    target_share = float(targets.get(k, 0.0) or 0.0) / present_target_sum
                    sample_share = float(sample_counts.get(k, 0)) / sample_total
                    if sample_share > 0:
                        cell_weights[k] = target_share / sample_share

                if not cell_weights:
                    return [1.0] * len(payloads), False

                weights = [float(cell_weights.get(_poststrat_cell(p) or "", 1.0)) for p in payloads]
                mean_w = float(sum(weights) / max(1, len(weights)))
                if mean_w > 0:
                    weights = [float(max(0.0, w / mean_w)) for w in weights]
                return weights, True

            all_weights, weights_used = _calc_poststrat_weights(all_payloads, jst_study)
            subset_weights = all_weights[:take_n] if all_weights else [1.0] * len(subset_payloads)

            def _weighted_count(payloads: List[Dict[str, Any]], weights: List[float], field: str) -> Dict[str, float]:
                out: Dict[str, float] = {}
                for idx, p in enumerate(payloads):
                    w = float(weights[idx]) if idx < len(weights) else 1.0
                    if w <= 0:
                        continue
                    val = _canon_demo(field, p.get(field))
                    out[val] = float(out.get(val, 0.0)) + w
                return out

            demo_rows: List[Dict[str, Any]] = []
            demo_cards: List[Dict[str, Any]] = []
            for spec in dim_specs:
                dim_label = str(spec["label"])
                field = str(spec["field"])
                dist_sub = _weighted_count(subset_payloads, subset_weights, field)
                dist_all = _weighted_count(all_payloads, all_weights, field)
                sum_sub = float(sum(float(v) for v in dist_sub.values()))
                sum_all = float(sum(float(v) for v in dist_all.values()))
                known_order = list(spec.get("order") or [])
                unknown = sorted((set(dist_sub.keys()) | set(dist_all.keys())) - set(known_order))
                cats = known_order + unknown

                top_cat = None
                top_pct = -1.0
                top_all_pct = 0.0
                for cat in cats:
                    c_sub = float(dist_sub.get(cat, 0.0))
                    c_all = float(dist_all.get(cat, 0.0))
                    pct_sub = (100.0 * c_sub / sum_sub) if sum_sub > 0 else 0.0
                    pct_all = (100.0 * c_all / sum_all) if sum_all > 0 else 0.0
                    if pct_sub > top_pct:
                        top_pct = pct_sub
                        top_cat = cat
                        top_all_pct = pct_all
                    demo_rows.append(
                        {
                            "Zmienna": dim_label,
                            "Kategoria": cat,
                            "% grupa dopasowana": round(pct_sub, 1),
                            "% ogół mieszkańców (ważony)": round(pct_all, 1),
                            "Róznica (w pp.)": round(pct_sub - pct_all, 1),
                        }
                    )
                if top_cat is not None:
                    demo_cards.append(
                        {
                            "label": dim_label,
                            "top": str(top_cat),
                            "pct": round(max(top_pct, 0.0), 1),
                            "diff_pp": round(top_pct - top_all_pct, 1),
                            "emoji": str((spec.get("emoji") or {}).get(str(top_cat), "•")),
                        }
                    )

            st.session_state["matching_result"] = {
                "person_label": pick_personal,
                "jst_label": pick_jst,
                "person_study_id": str(person.get("id") or ""),
                "jst_study_id": str(jst_study.get("id") or ""),
                "person_name_nom": f"{(person.get('first_name_nom') or person.get('first_name') or '').strip()} {(person.get('last_name_nom') or person.get('last_name') or '').strip()}".strip(),
                "jst_name_nom": jst_name_nom,
                "match_score": round(match_score, 1),
                "personal_n": p_n,
                "jst_n": len(j_rows),
                "personal_profile": p_profile,
                "jst_profile": j_profile,
                "strengths": strengths,
                "gaps": gaps,
                "strengths_rows": strengths_rows,
                "gaps_rows": gaps_rows,
                "match_metrics": {
                    "mae": round(mae, 1),
                    "rmse": round(rmse, 1),
                    "top3_gap_mae": round(top3_gap_mae, 1),
                    "score_mae": round(score_mae, 1),
                    "score_rmse": round(score_rmse, 1),
                    "score_top3": round(score_top3, 1),
                    "band_label": str(match_band[0]),
                    "band_desc": str(match_band[1]),
                },
                "demo_cards": demo_cards,
                "demo_rows": demo_rows,
                "demo_jst_weighted_header": f"{jst_name_nom} / (po wagowaniu)",
                "demo_weights_used": bool(weights_used),
                "target_audit": target_audit,
                "match_formula": (
                    "match = clamp(0,100, 0.40*(100 - MAE) + 0.25*(100 - RMSE) + 0.35*(100 - TOP3_MAE)); "
                    "gdzie MAE = średnia |Δ| dla 12 archetypów, RMSE = pierwiastek ze średniej kwadratów |Δ|, "
                    "TOP3_MAE = średnia z 3 największych |Δ|."
                ),
            }
            st.success("Wynik dopasowania został obliczony.")

    result = st.session_state.get("matching_result")
    if not result:
        with tab_summary:
            st.info("Najpierw wybierz badania w zakładce „Wybierz badania”.")
        with tab_demo:
            st.info("Najpierw wybierz badania w zakładce „Wybierz badania”.")
        with tab_strategy:
            st.info("Najpierw wybierz badania w zakładce „Wybierz badania”.")
        return

    with tab_summary:
        st.markdown(f"**Badanie personalne:** {result['person_label']}")
        st.markdown(f"**Badanie mieszkańców:** {result['jst_label']}")
        metrics = result.get("match_metrics") or {}
        st.progress(min(100, max(0, int(round(result["match_score"])))))
        st.metric("Poziom dopasowania", f"{result['match_score']}%")
        if metrics:
            st.caption(f"Ocena: {str(metrics.get('band_label') or '')} · {str(metrics.get('band_desc') or '')}")
            mcol1, mcol2, mcol3 = st.columns(3)
            mcol1.metric("Średnia różnica (MAE)", f"{float(metrics.get('mae', 0.0)):.1f} pp")
            mcol2.metric("Różnica z karą za odchylenia (RMSE)", f"{float(metrics.get('rmse', 0.0)):.1f} pp")
            mcol3.metric("Średnia TOP3 luk", f"{float(metrics.get('top3_gap_mae', 0.0)):.1f} pp")
        st.caption(f"Próba personalna: {result['personal_n']} odpowiedzi · Próba mieszkańców: {result['jst_n']} odpowiedzi")

        cmp_rows = []
        for a in JST_ARCHETYPES:
            pol = float(result["personal_profile"].get(a, 0.0))
            ocz = float(result["jst_profile"].get(a, 0.0))
            diff = abs(pol - ocz)
            cmp_rows.append(
                {
                    "Archetyp": a,
                    "Profil polityka (%)": f"{pol:.1f}",
                    "Oczekiwania mieszkańców (%)": f"{ocz:.1f}",
                    "Różnica |Δ|": f"{diff:.1f}",
                    "__sort_diff": diff,
                }
            )
        df_cmp = pd.DataFrame(cmp_rows).sort_values("__sort_diff", ascending=True).drop(columns="__sort_diff")
        cmp_rows_n = len(df_cmp.index)
        cmp_height = max(92, min(760, 40 + cmp_rows_n * 35))
        st.dataframe(
            df_cmp,
            use_container_width=True,
            hide_index=True,
            height=cmp_height,
        )
        st.caption(
            "„Oczekiwania mieszkańców (%)” liczymy łącząc komponent A (40%), B1 (20%), B2 (25%) i D13 (15%) "
            "dla każdego archetypu. Skala nie jest sztucznie zamykana do 100% sumarycznie."
        )
        with st.expander("Jak liczony jest poziom dopasowania?", expanded=False):
            st.markdown(result.get("match_formula", ""))
            st.markdown(
                "Metryka celowo bardziej karze duże luki archetypowe: oprócz średniej różnicy uwzględnia "
                "także RMSE (wrażliwy na skrajne odchylenia) i średnią z 3 największych luk."
            )
            if metrics:
                st.markdown(
                    f"**Składowe dla tego porównania:** "
                    f"MAE `{float(metrics.get('mae', 0.0)):.1f} pp`, "
                    f"RMSE `{float(metrics.get('rmse', 0.0)):.1f} pp`, "
                    f"TOP3_MAE `{float(metrics.get('top3_gap_mae', 0.0)):.1f} pp`."
                )
            st.markdown("**Jak dokładnie liczony jest komponent `A` (40%)?**")
            st.markdown(
                "- Dla każdej pary `A1..A18` odpowiedź 1–7 jest przeliczana liniowo na udział lewego/prawego archetypu.\n"
                "- Wzór dla pary: `p_prawy = (wartość_A - 1) / 6`, `p_lewy = 1 - p_prawy`.\n"
                "- Dla archetypu sumujemy wkłady z jego par i dzielimy przez liczbę par, w których występuje (`A_norm` 0–1).\n"
                "- Składanie wyniku archetypu: `score = 100 * (0.40*A_norm + 0.20*B1_hit + 0.25*B2_hit + 0.15*D13_hit)`."
            )
            audit = result.get("target_audit") or {}
            if audit:
                st.markdown(
                    f"**Audyt danych wejściowych:** A valid `{float(audit.get('a_valid_rate_pct', 0.0)):.1f}%`, "
                    f"B2 valid `{float(audit.get('b2_valid_rate_pct', 0.0)):.1f}%`, "
                    f"D13 valid `{float(audit.get('d13_valid_rate_pct', 0.0)):.1f}%`, "
                    f"średnia liczba wskazań B1: `{float(audit.get('b1_mean_selected', 0.0)):.2f}`."
                )
                comp = audit.get("component_means_by_archetype") or {}
                if isinstance(comp, dict) and comp:
                    comp_rows: List[Dict[str, str]] = []
                    for a in JST_ARCHETYPES:
                        row = comp.get(a) or {}
                        comp_rows.append(
                            {
                                "Archetyp": a,
                                "A (40%)": f"{float(row.get('A', 0.0)):.1f}",
                                "B1 (20%)": f"{float(row.get('B1', 0.0)):.1f}",
                                "B2 (25%)": f"{float(row.get('B2', 0.0)):.1f}",
                                "D13 (15%)": f"{float(row.get('D13', 0.0)):.1f}",
                                "Suma": f"{float(row.get('TOTAL', 0.0)):.1f}",
                            }
                        )
                    st.dataframe(
                        pd.DataFrame(comp_rows),
                        use_container_width=True,
                        hide_index=True,
                        height=max(92, min(520, 40 + len(comp_rows) * 35)),
                    )
        strengths_rows = result.get("strengths_rows") or []
        gaps_rows = result.get("gaps_rows") or []
        strength_items_html = "".join(
            [
                f"<span class='match-chip good'>{html.escape(str(r.get('archetyp') or ''))} "
                f"<small>|Δ| {float(r.get('diff', 0.0)):.1f} pp</small></span>"
                for r in strengths_rows
            ]
        )
        gap_items_html = "".join(
            [
                f"<span class='match-chip gap'>{html.escape(str(r.get('archetyp') or ''))} "
                f"<small>|Δ| {float(r.get('diff', 0.0)):.1f} pp</small></span>"
                for r in gaps_rows
            ]
        )
        st.markdown(
            f"""
            <style>
              .match-insight-grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:8px;}}
              .match-insight-box{{border:1px solid #d9e2ef;border-radius:12px;background:#fff;padding:12px 14px;}}
              .match-insight-title{{font-size:14px;font-weight:900;color:#1f2f44;margin:0 0 8px 0;}}
              .match-chip{{display:inline-flex;align-items:center;gap:6px;margin:4px 6px 4px 0;padding:6px 10px;border-radius:999px;font-size:13px;font-weight:700;}}
              .match-chip small{{font-size:12px;font-weight:700;opacity:.9;}}
              .match-chip.good{{background:#ecfdf3;border:1px solid #b7efcc;color:#11663a;}}
              .match-chip.gap{{background:#fff1f2;border:1px solid #fecdd3;color:#9f1239;}}
              @media (max-width: 900px){{.match-insight-grid{{grid-template-columns:1fr;}}}}
            </style>
            <div class="match-insight-grid">
              <div class="match-insight-box">
                <div class="match-insight-title">Najlepsze dopasowania</div>
                {strength_items_html or "<span class='match-chip good'>Brak danych</span>"}
              </div>
              <div class="match-insight-box">
                <div class="match-insight-title">Największe luki</div>
                {gap_items_html or "<span class='match-chip gap'>Brak danych</span>"}
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:18px;'></div>", unsafe_allow_html=True)
        st.markdown("### Porównanie profili archetypowych")

        person_name = str(result.get("person_name_nom") or result.get("person_label") or "Polityk")
        jst_name = str(result.get("jst_name_nom") or result.get("jst_label") or "JST")
        person_sid = str(result.get("person_study_id") or "")
        jst_sid = str(result.get("jst_study_id") or "")

        person_profile_100 = {a: float(result["personal_profile"].get(a, 0.0)) for a in JST_ARCHETYPES}
        jst_profile_100 = {a: float(result["jst_profile"].get(a, 0.0)) for a in JST_ARCHETYPES}

        radar_order: List[str] = [
            "Buntownik", "Błazen", "Kochanek", "Opiekun", "Towarzysz", "Niewinny",
            "Władca", "Mędrzec", "Czarodziej", "Bohater", "Twórca", "Odkrywca",
        ]
        person_profile_20 = {a: float(person_profile_100.get(a, 0.0)) / 5.0 for a in radar_order}
        jst_profile_20 = {a: float(jst_profile_100.get(a, 0.0)) / 5.0 for a in radar_order}

        def _top3(profile: Dict[str, float], order: List[str]) -> List[str]:
            return sorted(order, key=lambda a: (-float(profile.get(a, 0.0)), order.index(a)))[:3]

        p_top = _top3(person_profile_20, radar_order)
        j_top = _top3(jst_profile_20, radar_order)

        person_top_colors = {"main": "#ef4444", "aux": "#facc15", "supp": "#22c55e"}
        jst_top_colors = {"main": "#2563eb", "aux": "#a855f7", "supp": "#f97316"}

        def _marker_series(profile: Dict[str, float], top3: List[str], palette: Dict[str, str]) -> Tuple[List[Optional[float]], List[str]]:
            r_vals: List[Optional[float]] = []
            colors: List[str] = []
            mapping = {
                top3[0]: palette["main"] if len(top3) > 0 else "rgba(0,0,0,0)",
                top3[1]: palette["aux"] if len(top3) > 1 else "rgba(0,0,0,0)",
                top3[2]: palette["supp"] if len(top3) > 2 else "rgba(0,0,0,0)",
            }
            for arche in radar_order:
                if arche in mapping:
                    r_vals.append(float(profile.get(arche, 0.0)))
                    colors.append(str(mapping[arche]))
                else:
                    r_vals.append(None)
                    colors.append("rgba(0,0,0,0)")
            return r_vals, colors

        p_marker_r, p_marker_c = _marker_series(person_profile_20, p_top, person_top_colors)
        j_marker_r, j_marker_c = _marker_series(jst_profile_20, j_top, jst_top_colors)
        person_vals = [float(person_profile_20.get(a, 0.0)) for a in radar_order]
        jst_vals = [float(jst_profile_20.get(a, 0.0)) for a in radar_order]

        fig_cmp = go.Figure(
            data=[
                go.Scatterpolar(
                    r=person_vals + [person_vals[0]],
                    theta=radar_order + [radar_order[0]],
                    fill="toself",
                    fillcolor="rgba(37,99,235,0.18)",
                    line=dict(color="#2563eb", width=3),
                    marker=dict(size=5),
                    name=f"Profil polityka: {person_name}",
                    showlegend=False,
                    hovertemplate="<b>%{theta}</b><br>Polityk: %{r:.2f}<extra></extra>",
                ),
                go.Scatterpolar(
                    r=jst_vals + [jst_vals[0]],
                    theta=radar_order + [radar_order[0]],
                    fill="toself",
                    fillcolor="rgba(15,118,110,0.16)",
                    line=dict(color="#0f766e", width=3, dash="dot"),
                    marker=dict(size=5),
                    name=f"Mieszkańcy: {jst_name} (N={int(result.get('jst_n') or 0)})",
                    showlegend=False,
                    hovertemplate="<b>%{theta}</b><br>Mieszkańcy: %{r:.2f}<extra></extra>",
                ),
                go.Scatterpolar(
                    r=p_marker_r,
                    theta=radar_order,
                    mode="markers",
                    marker=dict(size=16, color=p_marker_c, opacity=0.92, line=dict(color="black", width=2.6)),
                    name="TOP3 polityka",
                    showlegend=False,
                    hovertemplate="<b>%{theta}</b><br>TOP3 polityka: %{r:.2f}<extra></extra>",
                ),
                go.Scatterpolar(
                    r=j_marker_r,
                    theta=radar_order,
                    mode="markers",
                    marker=dict(size=14, color=j_marker_c, opacity=0.94, line=dict(color="#0f172a", width=2.0)),
                    name="TOP3 mieszkańców",
                    showlegend=False,
                    hovertemplate="<b>%{theta}</b><br>TOP3 mieszkańców: %{r:.2f}<extra></extra>",
                ),
            ]
        )
        fig_cmp.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            height=560,
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(visible=True, range=[0, 20]),
                angularaxis=dict(
                    tickfont=dict(size=14),
                    tickvals=radar_order,
                    ticktext=radar_order,
                    rotation=90,
                    direction="clockwise",
                ),
            ),
            margin=dict(l=20, r=20, t=26, b=20),
            showlegend=False,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.03,
                xanchor="center",
                x=0.5,
                font=dict(size=12),
            ),
        )
        st.plotly_chart(
            fig_cmp,
            use_container_width=True,
            config={"displaylogo": False, "displayModeBar": False, "responsive": True},
            key=f"matching-radar-compare-{person_sid}-{jst_sid}",
        )
        st.caption(
            f"Niebieska linia: profil polityka ({person_name}) • "
            f"Turkusowa linia przerywana: profil mieszkańców ({jst_name}, N={int(result.get('jst_n') or 0)})."
        )
        lg1, lg2 = st.columns(2, gap="large")
        with lg1:
            st.markdown(
                f"**TOP3 polityka:** "
                f"<span style='color:{person_top_colors['main']};font-weight:800;'>●</span> główny, "
                f"<span style='color:{person_top_colors['aux']};font-weight:800;'>●</span> wspierający, "
                f"<span style='color:{person_top_colors['supp']};font-weight:800;'>●</span> poboczny",
                unsafe_allow_html=True,
            )
        with lg2:
            st.markdown(
                f"**TOP3 mieszkańców:** "
                f"<span style='color:{jst_top_colors['main']};font-weight:800;'>●</span> główny, "
                f"<span style='color:{jst_top_colors['aux']};font-weight:800;'>●</span> wspierający, "
                f"<span style='color:{jst_top_colors['supp']};font-weight:800;'>●</span> poboczny",
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height:12px;'></div>", unsafe_allow_html=True)
        st.markdown("#### Profile archetypowe 0-100")
        left_profile_col, right_profile_col = st.columns(2, gap="large")
        try:
            import admin_dashboard as AD
            p_key = re.sub(r"[^a-zA-Z0-9_-]+", "_", person_sid or "person")
            j_key = re.sub(r"[^a-zA-Z0-9_-]+", "_", jst_sid or "jst")
            person_profile_img = AD.make_segment_profile_wheel_png(
                mean_scores=person_profile_100,
                out_path=f"matching_profile_person_{p_key}_{j_key}.png",
            )
            jst_profile_img = AD.make_segment_profile_wheel_png(
                mean_scores=jst_profile_100,
                out_path=f"matching_profile_jst_{j_key}_{p_key}.png",
            )

            def _show_image_compat(img_path: str, max_width_px: int = 520) -> None:
                try:
                    st.image(img_path, width=max_width_px)
                except TypeError:
                    try:
                        st.image(img_path, use_column_width=True)
                    except Exception:
                        st.image(img_path)

            with left_profile_col:
                st.markdown(f"**Profil archetypowy {person_name} (siła archetypu, skala: 0-100)**")
                _show_image_compat(person_profile_img, max_width_px=520)
            with right_profile_col:
                st.markdown(f"**Profil archetypowy mieszkańców {jst_name} (siła archetypu, skala: 0-100)**")
                _show_image_compat(jst_profile_img, max_width_px=520)
        except Exception as e:
            st.info(f"Nie udało się wygenerować porównania kół 0-100: {e}")

    with tab_demo:
        st.markdown("Demografia grupy mieszkańców najbardziej dopasowanej do profilu polityka (top 25% podobieństwa).")
        st.markdown(
            """
            <style>
              .match-demo-box{border:1px solid #dbe4ef;border-radius:12px;background:#fff;padding:10px 12px;margin:0 0 10px 0;}
              .match-demo-box-label{font-size:15px;font-weight:900;text-transform:uppercase;letter-spacing:.02em;color:#334155;display:flex;align-items:center;gap:6px;}
              .match-demo-box-note{color:#5f6b7a;font-size:12px;margin:2px 0 6px 0;}
              .match-demo-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(175px,1fr));gap:8px;margin:10px 0 12px 0;}
              .match-demo-stat{border:1px solid #dbe4ef;border-radius:10px;background:#fff;padding:8px 10px;}
              .match-demo-stat-label{font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.03em;color:#5f6b7a;}
              .match-demo-stat-main{margin-top:2px;font-size:14px;font-weight:900;color:#111827;line-height:1.2;}
              .match-demo-stat-sub{margin-top:2px;font-size:12.5px;color:#3f4954;}
              .match-demo-table-wrap{overflow-x:auto;max-width:940px;}
              .match-demo-table{margin-top:0;width:100%;min-width:720px;max-width:940px;border-collapse:collapse;border:3px solid #b8c2cc;background:#fff;font-size:13.5px;color:#334155;}
              .match-demo-table th,.match-demo-table td{padding:8px 10px;border:1px solid #dfe4ea;text-align:left;vertical-align:middle;}
              .match-demo-table th{background:#f2f6fb;color:#1f2f44;font-weight:800;font-size:13.5px;}
            </style>
            """,
            unsafe_allow_html=True,
        )
        variable_emoji = {
            "Płeć": "👫",
            "Wiek": "🧭",
            "Wykształcenie": "🎓",
            "Status zawodowy": "💼",
            "Sytuacja materialna": "💰",
        }
        cards = result.get("demo_cards") or []
        if cards:
            cards_html = "".join(
                f"""
                <div class="match-demo-stat">
                  <div class="match-demo-stat-label">{html.escape(str(variable_emoji.get(str(c.get("label") or ""), "📌")))} {html.escape(str(c.get("label") or "").upper())}</div>
                  <div class="match-demo-stat-main">{html.escape(str(c.get("emoji") or ""))} {html.escape(str(c.get("top") or ""))}</div>
                  <div class="match-demo-stat-sub">{float(c.get("pct") or 0.0):.1f}% • {float(c.get("diff_pp") or 0.0):+,.1f} pp</div>
                </div>
                """
                for c in cards
            )
            st.markdown(
                f"""
                <div class="match-demo-box">
                  <div class="match-demo-box-label">📌 STATYSTYCZNY PROFIL DEMOGRAFICZNY</div>
                  <div class="match-demo-cards">{cards_html}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        ddf = pd.DataFrame(result.get("demo_rows") or [])
        if ddf.empty:
            st.caption("Brak danych demograficznych.")
        else:
            jst_weighted_header = str(result.get("demo_jst_weighted_header") or "JST / (po wagowaniu)")
            ddf = ddf.copy()
            ddf["% grupa dopasowana"] = pd.to_numeric(ddf["% grupa dopasowana"], errors="coerce").fillna(0.0).round(1)
            ddf["% ogół mieszkańców (ważony)"] = pd.to_numeric(ddf["% ogół mieszkańców (ważony)"], errors="coerce").fillna(0.0).round(1)
            ddf["Róznica (w pp.)"] = pd.to_numeric(ddf["Róznica (w pp.)"], errors="coerce").fillna(0.0).round(1)

            variable_order = ["Płeć", "Wiek", "Wykształcenie", "Status zawodowy", "Sytuacja materialna"]
            category_order = {
                "Płeć": ["kobieta", "mężczyzna"],
                "Wiek": ["15-39", "40-59", "60+"],
                "Wykształcenie": ["podst./gim./zaw.", "średnie", "wyższe"],
                "Status zawodowy": ["prac. umysłowy", "prac. fizyczny", "własna firma", "student/uczeń", "bezrobotny", "rencista/emeryt", "inna"],
                "Sytuacja materialna": ["bardzo dobra", "raczej dobra", "przeciętna", "raczej zła", "bardzo zła", "odmowa"],
            }
            category_emoji = {
                "kobieta": "👩",
                "mężczyzna": "👨",
                "15-39": "🧑",
                "40-59": "🧑‍💼",
                "60+": "🧓",
                "podst./gim./zaw.": "🛠️",
                "średnie": "📘",
                "wyższe": "🎓",
                "prac. umysłowy": "🧠",
                "prac. fizyczny": "🛠️",
                "własna firma": "🏢",
                "student/uczeń": "🧑‍🎓",
                "bezrobotny": "🔎",
                "rencista/emeryt": "🌿",
                "inna": "🧩",
                "bardzo dobra": "😄",
                "raczej dobra": "🙂",
                "przeciętna": "😐",
                "raczej zła": "🙁",
                "bardzo zła": "😟",
                "odmowa": "🤐",
                "brak danych": "❔",
            }

            ddf["__var_order"] = ddf["Zmienna"].map(lambda v: variable_order.index(v) if v in variable_order else 999)
            ddf["__cat_order"] = ddf.apply(
                lambda row: (
                    category_order.get(str(row["Zmienna"]), []).index(str(row["Kategoria"]))
                    if str(row["Kategoria"]) in category_order.get(str(row["Zmienna"]), [])
                    else 999
                ),
                axis=1,
            )
            ddf = ddf.sort_values(["__var_order", "__cat_order", "Kategoria"], ascending=[True, True, True])

            table_rows: List[str] = []
            for var_name in variable_order:
                part = ddf[ddf["Zmienna"] == var_name].copy()
                if part.empty:
                    continue
                top_idx = part["% grupa dopasowana"].idxmax()
                rowspan = len(part.index)
                for idx, (_, row) in enumerate(part.iterrows()):
                    cat = str(row["Kategoria"])
                    pct_sub = float(row["% grupa dopasowana"])
                    pct_all = float(row["% ogół mieszkańców (ważony)"])
                    diff = float(row["Róznica (w pp.)"])
                    is_top = bool(row.name == top_idx)
                    bar_w = max(0.0, min(100.0, pct_sub))
                    var_icon = variable_emoji.get(var_name, "📌")
                    fill_color = "#8ecae6" if is_top else "#d8e5f1"
                    top_border = "border-top:3px solid #b8c2cc;"
                    diff_color = "#0f766e" if diff >= 0 else "#9a3412"
                    diff_text = f"{diff:+.1f} pp"
                    cat_weight = "800" if is_top else "500"
                    pct_weight = "900" if is_top else "600"
                    first_col = (
                        "<td "
                        f"rowspan='{rowspan}' "
                        f"style=\"font-weight:800; text-transform:uppercase; vertical-align:middle; background:#fafafa; border-left:3px solid #b8c2cc; {top_border}\">"
                        "<span style='display:inline-flex; align-items:center; gap:6px;'>"
                        f"<span>{html.escape(var_icon)}</span>"
                        f"<span>{html.escape(var_name)}</span>"
                        "</span>"
                        "</td>"
                        if idx == 0
                        else ""
                    )
                    table_rows.append(
                        "<tr>"
                        f"{first_col}"
                        f"<td style=\"font-size:13.5px; font-weight:{cat_weight}; {top_border if idx == 0 else ''}\">"
                        "<span style='display:inline-flex; align-items:center; gap:6px;'>"
                        f"<span>{html.escape(category_emoji.get(cat, '📌'))}</span>"
                        f"<span>{html.escape(cat)}</span>"
                        "</span>"
                        "</td>"
                        f"<td style=\"padding:0; min-width:176px; border:1px solid #dfe4ea; {top_border if idx == 0 else ''}\">"
                        "<div style=\"position:relative; height:34px; background:#fff;\">"
                        f"<div style=\"position:absolute; left:0; top:0; bottom:0; width:{bar_w:.1f}%; background:{fill_color}; opacity:0.96;\"></div>"
                        f"<span style=\"position:absolute; right:6px; top:7px; z-index:2; background:rgba(255,255,255,0.88); padding:1px 5px; border-radius:4px; font-size:12px; font-weight:{pct_weight}; color:#111;\">{pct_sub:.1f}%</span>"
                        "</div>"
                        "</td>"
                        f"<td style=\"font-size:13.5px; text-align:right; {top_border if idx == 0 else ''}\">{pct_all:.1f}%</td>"
                        f"<td style=\"font-size:13.5px; text-align:right; color:{diff_color}; font-weight:400; border-right:3px solid #b8c2cc; {top_border if idx == 0 else ''}\">{diff_text}</td>"
                        "</tr>"
                    )

            jst_weighted_header_html = html.escape(jst_weighted_header).replace(" / ", " /<br>")
            table_html = (
                "<div class='match-demo-table-wrap'>"
                "<table class='match-demo-table'>"
                "<thead><tr>"
                "<th style='min-width:150px; font-size:13.5px; border-top:3px solid #b8c2cc; border-left:3px solid #b8c2cc;'>Zmienna</th>"
                "<th style='min-width:220px; font-size:13.5px; border-top:3px solid #b8c2cc;'>Kategoria</th>"
                "<th style='min-width:176px; text-align:center; border-top:3px solid #b8c2cc;'>% grupa dopasowana</th>"
                f"<th style='min-width:130px; text-align:center; border-top:3px solid #b8c2cc;'>{jst_weighted_header_html}</th>"
                "<th style='min-width:120px; text-align:center; border-top:3px solid #b8c2cc; border-right:3px solid #b8c2cc;'>Róznica (w pp.)</th>"
                "</tr></thead><tbody>"
                + "".join(table_rows)
                + "</tbody></table></div>"
            )
            weights_note = (
                "Wartości w kolumnie referencyjnej i grupie dopasowanej liczone po wagowaniu (płeć × wiek)."
                if bool(result.get("demo_weights_used"))
                else "Brak zdefiniowanych wag poststratyfikacyjnych dla tego badania — pokazujemy rozkład surowy."
            )
            st.markdown(
                f"""
                <div class="match-demo-box">
                  <div class="match-demo-box-label">👥 PROFIL DEMOGRAFICZNY</div>
                  <div class="match-demo-box-note">W tabeli pogrubiona najwyższa kategoria w każdej zmiennej.</div>
                  <div class="match-demo-box-note">{html.escape(weights_note)}</div>
                  {table_html}
                </div>
                """,
                unsafe_allow_html=True,
            )

    with tab_strategy:
        st.markdown("**Rekomendacje komunikacyjne (automatyczne):**")
        strengths = result["strengths"]
        gaps = result["gaps"]
        st.markdown(f"1. W komunikacji wzmacniaj osie: **{strengths[0]}**, **{strengths[1]}**, **{strengths[2]}** – to naturalne pola dopasowania.")
        st.markdown(f"2. Opracuj osobne narracje dla luk: **{gaps[0]}**, **{gaps[1]}**, **{gaps[2]}** (krótkie, konkretne obietnice + dowód wykonania).")
        st.markdown("3. Dla grup najlepiej dopasowanych demograficznie przygotuj dedykowane komunikaty i testuj je w kampaniach SMS/e-mail.")

def add_view() -> None:
    require_auth()
    header("➕ Dodaj badanie archetypu")
    render_titlebar(["Panel", "Dodaj badanie"])
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
    render_titlebar(["Panel", "Edytuj badanie"])

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
                        goto("home_personal")
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
    L, C, R = st.columns([1, 8, 1], gap="small")  # szerokość ramki ~ środkowa kolumna
    with C:
        with st.container(border=True):
            st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)

            # tytuł
            st.markdown(
                "<div style='font-weight:700; font-size:25px; "
                "margin:5px 0 40px 0; padding-bottom:8px; "
                "border-bottom:1px solid #E6E9EE;'>Statystyki</div>",
                unsafe_allow_html=True
            )

            # dane + metryki
            total, df = fetch_stats_table()
            c1, c2 = st.columns(2)  # ← JEDEN poziom zagnieżdżenia OK
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


def jst_stats_panel(studies: List[Dict[str, Any]], rows: List[Dict[str, Any]], total_resp: int) -> None:
    st.markdown("<hr class='hr-thin'>", unsafe_allow_html=True)
    st.markdown("<div style='height:24px;'></div>", unsafe_allow_html=True)
    L, C, R = st.columns([1, 8, 1], gap="small")
    with C:
        with st.container(border=True):
            st.markdown("<div style='height:20px;'></div>", unsafe_allow_html=True)
            st.markdown(
                "<div style='font-weight:700; font-size:25px; margin:5px 0 40px 0; "
                "padding-bottom:8px; border-bottom:1px solid #E6E9EE;'>Statystyki</div>",
                unsafe_allow_html=True,
            )
            c1, c2 = st.columns(2)
            with c1:
                st.metric("Łączna liczba uczestników badań", int(total_resp))
            with c2:
                st.metric("Liczba badań w bazie", len(studies))

            if rows:
                df = pd.DataFrame(rows, columns=["JST", "Link", "Data utworzenia", "Liczba odpowiedzi"])
                sort_idx = pd.to_datetime(df["Data utworzenia"], errors="coerce", format="%Y-%m-%d %H:%M")
                df = df.assign(_sort=sort_idx).sort_values("_sort", ascending=False).drop(columns="_sort")
                rows_count = len(df)
                jst_height = max(96, min(640, 42 + rows_count * 35))
                st.dataframe(
                    df,
                    use_container_width=True,
                    hide_index=True,
                    height=jst_height,
                )
            else:
                st.caption("Brak badań JST.")

            st.markdown("<div style='height:16px;'></div>", unsafe_allow_html=True)





def _render_public_gate(token: str) -> bool:
    if bool(st.session_state.get(f"public_ok_{token}", False)):
        return True

    st.markdown(
        """
        <style>
        /* Wyłączenie starych warstw (legacy CSS) */
        .public-lock-overlay,
        .public-lock-card,
        .public-form-wrap,
        [class*="public-lock-overlay"],
        [class*="public-lock-card"],
        [class*="public-form-wrap"]{
          display:none !important;
          visibility:hidden !important;
          height:0 !important;
          overflow:hidden !important;
        }
        .public-unlock-note{
          color:#334155;
          margin:0 0 10px 0;
          line-height:1.45;
          font-size:0.98rem;
        }
        /* mobile-only: poprawa czytelności formularza odblokowania na iPhone */
        @media (max-width: 900px){
          .public-unlock-note{
            font-size:1.04rem;
            color:#334155;
          }
          div[data-testid="stForm"]{
            background: transparent !important;
          }
          div[data-testid="stForm"] label{
            color:#334155 !important;
            font-weight:600 !important;
          }
          div[data-testid="stForm"] [data-baseweb="input"]{
            background:#ffffff !important;
            border:1px solid #cbd5e1 !important;
          }
          div[data-testid="stForm"] input{
            background:#ffffff !important;
            color:#0f172a !important;
            -webkit-text-fill-color:#0f172a !important;
            caret-color:#0f172a !important;
            font-size:16px !important; /* zapobiega dziwnemu zoomowi iOS */
          }
          div[data-testid="stForm"] input::placeholder{
            color:#64748b !important;
            opacity:1 !important;
          }
        }
        @media (prefers-color-scheme: dark){
          .public-unlock-note{
            color:#d9e4f0 !important;
          }
          div[data-testid="stForm"] label{
            color:#d9e4f0 !important;
          }
          div[data-testid="stForm"] [data-baseweb="input"]{
            background:#111b2a !important;
            border:1px solid #334155 !important;
          }
          div[data-testid="stForm"] input{
            background:#111b2a !important;
            color:#e2e8f0 !important;
            -webkit-text-fill-color:#e2e8f0 !important;
            caret-color:#e2e8f0 !important;
          }
          div[data-testid="stForm"] input::placeholder{
            color:#9fb0c4 !important;
          }
        }
        div[data-testid="stForm"] button[kind="primaryFormSubmit"]{
          background:#ff4d5b !important;
          color:#ffffff !important;
          border:1px solid #ff4d5b !important;
          font-weight:700 !important;
        }
        div[data-testid="stForm"] button[kind="primaryFormSubmit"]:hover{
          background:#ff3b4c !important;
          border-color:#ff3b4c !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    lock_l, lock_c, lock_r = st.columns([0.08, 0.84, 0.08], gap="small")
    with lock_c:
        st.markdown("<div style='height:10vh;'></div>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("### Podgląd raportu jest zabezpieczony")
            st.markdown(
                "<p class='public-unlock-note'>Podaj e-mail, na który wysłano link, oraz hasło dostępu.</p>",
                unsafe_allow_html=True,
            )
            with st.form(f"public_unlock_{token}", clear_on_submit=False):
                email = st.text_input("E-mail", key=f"public_email_{token}", autocomplete="off")
                password = st.text_input("Hasło dostępu", type="password", key=f"public_pwd_{token}", autocomplete="new-password")
                unlock = st.form_submit_button("Odblokuj raport", type="primary")

    if unlock:
        res = verify_report_token_credentials(token, email, password)
        if res.ok:
            st.session_state[f"public_ok_{token}"] = True
            st.rerun()
        st.error(res.message or "Brak dostępu.")
    return bool(st.session_state.get(f"public_ok_{token}", False))


def public_report_view(token: str) -> None:
    ensure_report_share_schema()
    grant = get_report_access_by_token(token)
    if not grant:
        st.error("Nieprawidłowy lub nieaktywny link podglądu raportu.")
        st.stop()

    status = str(grant.get("status") or "").lower()
    if status != "active":
        st.error("Dostęp do tego raportu jest obecnie nieaktywny.")
        st.stop()
    if (not bool(grant.get("indefinite"))) and grant.get("expires_at"):
        try:
            if datetime.now().astimezone().tzinfo is None:
                now_utc = datetime.utcnow()
            else:
                now_utc = datetime.now(timezone.utc)
            exp_utc = pd.to_datetime(grant.get("expires_at"), utc=True, errors="coerce")
            if pd.notna(exp_utc) and now_utc > exp_utc.to_pydatetime():
                st.error("Ten link wygasł.")
                st.stop()
        except Exception:
            pass

    if not _render_public_gate(token):
        st.stop()

    study = _fetch_study_by_id(str(grant.get("study_id") or ""))
    if not study:
        st.error("Nie udało się odnaleźć badania przypisanego do tego linku.")
        st.stop()

    st.markdown(
        "<style>.block-container{max-width:98vw !important;padding-left:1.2rem !important;padding-right:1.2rem !important;}</style>",
        unsafe_allow_html=True,
    )
    _inject_report_dark_fix_css()
    st.markdown("<div style='height:6px;'></div>", unsafe_allow_html=True)
    try:
        import admin_dashboard as AD
        if hasattr(AD, "show_report"):
            try:
                AD.show_report(sb, study, wide=True, public_view=True)
            except TypeError:
                AD.show_report(sb, study, wide=True)
        else:
            st.error("Brak funkcji renderującej raport.")
    except Exception as e:
        st.error(f"Nie udało się wyrenderować podglądu raportu: {e}")
    st.stop()


def results_view() -> None:
    require_auth()
    header("📊 Sprawdź wyniki badania archetypu")
    render_titlebar(["Panel", "Wyniki"])
    back_button()

    # ⬇️ Ukryj siatkę kafli z home_view na czas renderu wyników (eliminuje migotanie)
    st.markdown("<style>.tiles{display:none!important}</style>", unsafe_allow_html=True)

    studies = fetch_studies(sb)
    if not studies:
        st.info("Brak rekordów w bazie."); return

    # ── GÓRNY RZĄD: 1) przełącznik szerokości + 2) szybka nawigacja
    if "wide_report" not in st.session_state:
        st.session_state["wide_report"] = True

    topL, topR = st.columns([0.42, 0.58])
    with topL:
        # ⬅️ JEDEN toggle z unikalnym key
        wide = st.toggle("🔎 Szeroki raport", key="wide_report")
        st.markdown(
            f"<style>.block-container{{max-width:{'100vw' if wide else '1160px'} !important}}</style>",
            unsafe_allow_html=True
        )
    with topR:
        st.markdown("""
        <div class="quicknav">
          <b class="sep">|</b>
          <a href="#opisy">Opisy archetypów</a>
          <a href="#raport">Raport</a>
          <a href="#tabela">Tabela</a>
          <a href="#udostepnij">Udostępnij</a>
        </div>
        <script>
          const root = window.document;
          root.querySelectorAll('.quicknav a').forEach(a=>{
            a.addEventListener('click', (e)=>{
              e.preventDefault();
              const id = a.getAttribute('href');
              const el = root.querySelector(id);
              if(el){ el.scrollIntoView({behavior:'smooth', block:'start'}); }
            });
          });
        </script>
        """, unsafe_allow_html=True)

    # lokalny wrapper, żeby CSS działał tylko tutaj
    st.markdown('<div id="results-choose"><div class="section-label">Wybierz osobę:</div>', unsafe_allow_html=True)
    st.markdown(
        """
        <div id="ff-autofill-trap" aria-hidden="true" style="position:fixed;left:-9999px;top:-9999px;opacity:0;pointer-events:none;width:1px;height:1px;overflow:hidden;">
          <input type="text" name="username" autocomplete="username" tabindex="-1" />
          <input type="password" name="current-password" autocomplete="current-password" tabindex="-1" />
        </div>
        """,
        unsafe_allow_html=True,
    )

    options = {
        f"{s.get('last_name_nom') or s['last_name']} {s.get('first_name_nom') or s['first_name']} ({s['city']}) – /{s['slug']}"
        : s for s in studies
    }
    choice = st.selectbox("Wybierz widok", options=list(options.keys()), label_visibility="collapsed")
    st.markdown(
        """
        <script>
        (function(){
          const scope = document.getElementById('results-choose');
          if(!scope) return;

          const harden = () => {
            let idx = 0;
            const direct = scope.querySelectorAll('input,[role="combobox"],[contenteditable="true"]');
            const globalCombobox = document.querySelectorAll('input[role="combobox"], [data-baseweb="select"] input, [data-baseweb="select"] [contenteditable="true"]');
            const all = [...direct, ...globalCombobox];
            all.forEach((el) => {
              try{
                el.setAttribute('autocomplete','new-password');
                el.setAttribute('autocorrect','off');
                el.setAttribute('autocapitalize','off');
                el.setAttribute('spellcheck','false');
                el.setAttribute('data-lpignore','true');
                el.setAttribute('data-1p-ignore','true');
                el.setAttribute('name','results_selector_' + (idx++));
                if (el.matches('input[role="combobox"]')) {
                  el.readOnly = true;
                }
              }catch(_e){}
            });
          };

          harden();
          setTimeout(harden, 120);
          setTimeout(harden, 600);
          setTimeout(harden, 1200);

          const mo = new MutationObserver(() => harden());
          mo.observe(document.body, { childList:true, subtree:true, attributes:true });
          setTimeout(() => { try { mo.disconnect(); } catch(_e){} }, 12000);
        })();
        </script>
        """,
        unsafe_allow_html=True,
    )
    study = options[choice]
    render_titlebar([
        "Panel", "Wyniki",
        f"{(study.get('last_name_nom') or study['last_name'])} "
        f"{(study.get('first_name_nom') or study['first_name'])} "
        f"({study.get('city', '')})"
    ])

    st.markdown('</div>', unsafe_allow_html=True)

    # ⬇️ PRZENIESIONA LINIA — TERAZ POD SELECTEM
    st.markdown('<hr class="hr-thin">', unsafe_allow_html=True)
    _inject_report_dark_fix_css()

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

    # Sprzątanie: jeżeli jakiś komponent dodał swój #titlebar niżej – usuń go
    st.markdown("""
    <script>
      (function(){
        const bars = Array.from(document.querySelectorAll('#titlebar'));
        // zostaw tylko pierwszy (ten u góry)
        if (bars.length > 1) {
          bars.slice(1).forEach(el => el.remove());
        }
      })();
    </script>
    """, unsafe_allow_html=True)


    # szara linia + kotwica + nagłówek
    st.markdown("<hr class='soft-hr' /><div id='udostepnij'></div>", unsafe_allow_html=True)
    st.markdown('<div class="section-title share-title">Udostępnij raport</div>', unsafe_allow_html=True)
    ensure_report_share_schema()

    with st.form(f"share_form_{study['id']}"):
        recipients_raw = st.text_area(
            "Adresy e-mail",
            placeholder="Oddziel przecinkami: np. jan@firma.pl, ola@urzad.gov.pl",
        )
        password = st.text_input(
            "Hasło dostępu",
            type="password",
            autocomplete="new-password",
            help="To hasło będzie wymagane przy otwieraniu linku do raportu.",
        )
        validity_mode = st.radio(
            "Ważność linku",
            ["Ważny przez liczbę godzin", "Ważny do odwołania"],
            horizontal=True,
            index=0,
        )
        hours = None
        if validity_mode == "Ważny przez liczbę godzin":
            hours = st.number_input("Liczba godzin", min_value=1, max_value=7200, value=48)
        submit_share = st.form_submit_button("Przyznaj dostęp i wyślij e-mail", type="primary")

    if submit_share:
        emails = _normalize_emails(recipients_raw)
        if not emails:
            st.error("Podaj co najmniej jeden poprawny adres e-mail.")
        elif len((password or "").strip()) < 4:
            st.error("Hasło musi mieć co najmniej 4 znaki.")
        else:
            try:
                host, port, user, pwd, secure, from_email, from_name = _email_env()
                person_gen = _person_genitive(study)
                sent_links: List[Tuple[str, str]] = []
                indefinite = validity_mode == "Ważny do odwołania"
                for email in emails:
                    rec = create_report_access(
                        str(study["id"]),
                        email,
                        password.strip(),
                        hours_valid=(None if indefinite else int(hours or 48)),
                        indefinite=indefinite,
                        token=make_token(40),
                    )
                    link = _build_report_link(rec["token"])
                    validity_text = _access_validity_text(rec, hours_value=(None if indefinite else int(hours or 48)), indefinite=indefinite)

                    msg = (
                        f"Została udostępniona Ci możliwość podglądu raportu z badania archetypu {person_gen}.\n\n"
                        f"Aby zobaczyć raport kliknij w link: {link}.\n\n"
                        f"Link jest ważny: {validity_text}.\n\n"
                        f"Hasło dostępowe umożliwiające dostęp do raportu: {password.strip()}. "
                        f"Pamiętaj, aby nie udostępniać nikomu hasła!\n\n"
                        "W przypadku pytań lub wątpliwości skontaktuj się z:\n"
                        "Piotr Stec\n"
                        "Badania.pro®\n"
                        "e-mail: piotr.stec@badania.pro"
                    )
                    subject = f"Dostęp do raportu archetypu {person_gen}"
                    ok, provider_id, err = send_email(
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
                        mark_report_access_sent(rec["id"])
                        sent_links.append((email, link))
                    else:
                        st.error(f"Nie udało się wysłać e-maila do {email}: {err}")

                if sent_links:
                    st.success("Dostęp został przyznany i wiadomości e-mail zostały wysłane.")
                    for email, link in sent_links:
                        st.markdown(f"**{email}**")
                        st.code(link)
            except Exception as e:
                st.error(f"Nie udało się utworzyć udostępnień: {e}")

    access_rows = list_report_accesses(str(study["id"]))
    if access_rows:
        st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)
        st.markdown("**Aktywne i historyczne dostępy (e-mail):**")
        now_utc = datetime.now(timezone.utc)
        table_rows = []
        for row in access_rows:
            effective_status = _effective_access_status(row, now_utc=now_utc)
            expiry = "do odwołania" if row.get("indefinite") else (_fmt_local_ts(row.get("expires_at")) or "—")
            table_rows.append(
                {
                    "E-mail": row.get("email", ""),
                    "Status": _access_status_label(effective_status, with_icon=True),
                    "Ważny do": expiry,
                    "Utworzono": _fmt_local_ts(row.get("created_at")),
                    "Ostatnia wysyłka": _fmt_local_ts(row.get("last_sent_at")),
                }
            )
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

        with st.container(border=True):
            st.markdown("<div class='share-manage-title'>Wybierz dostęp do zarządzania</div>", unsafe_allow_html=True)
            manage_options = {
                f"{r.get('email','')} | {_access_status_label(_effective_access_status(r, now_utc=now_utc), with_icon=True)} | {_fmt_local_ts(r.get('created_at'))}": r
                for r in access_rows
            }
            selected_key = st.selectbox(
                "Wybierz dostęp do zarządzania",
                options=list(manage_options.keys()),
                key=f"share_manage_{study['id']}",
                label_visibility="collapsed",
            )
            selected = manage_options[selected_key]
            selected_status_db = str(selected.get("status") or "").lower()
            selected_status_effective = _effective_access_status(selected, now_utc=now_utc)
            selected_status_chip_class = "revoked" if selected_status_effective in {"revoked", "deleted"} else selected_status_effective
            selected_expiry = "do odwołania" if selected.get("indefinite") else (_fmt_local_ts(selected.get("expires_at")) or "—")

            st.markdown(
                "<div class='share-manage-meta'>"
                f"<span class='share-chip {selected_status_chip_class}'>status: {_access_status_label(selected_status_effective, with_icon=True)}</span>"
                f"<span class='share-chip'>e-mail: {selected.get('email','')}</span>"
                f"<span class='share-chip'>ważny do: {selected_expiry}</span>"
                "</div>",
                unsafe_allow_html=True,
            )

            b1, b2, b3, b4, _btn_spacer = st.columns([0.14, 0.14, 0.14, 0.14, 0.44], gap="small")
            with b1:
                if st.button("⏸️ Zawieś", key=f"suspend_{selected['id']}", use_container_width=True, disabled=selected_status_db != "active"):
                    set_report_access_status(selected["id"], "suspended")
                    st.rerun()
            with b2:
                if st.button("▶️ Odwieś", key=f"unsuspend_{selected['id']}", use_container_width=True, disabled=selected_status_db != "suspended"):
                    set_report_access_status(selected["id"], "active")
                    st.rerun()
            with b3:
                if st.button("🛑 Odwołaj", key=f"revoke_{selected['id']}", use_container_width=True, disabled=selected_status_db in {"revoked", "deleted"}):
                    set_report_access_status(selected["id"], "revoked")
                    st.rerun()
            with b4:
                if st.button("🗑️ Usuń", key=f"delete_{selected['id']}", use_container_width=True):
                    st.session_state[f"share_delete_confirm_{selected['id']}"] = True
                    st.rerun()

            if st.session_state.get(f"share_delete_confirm_{selected['id']}", False):
                st.warning("Czy na pewno trwale usunąć dostęp? Tej operacji nie można cofnąć.")
                d1, d2, _dsp = st.columns([0.20, 0.16, 0.64], gap="small")
                with d1:
                    if st.button("✅ Tak, usuń trwale", key=f"delete_confirm_yes_{selected['id']}", use_container_width=True):
                        ok = delete_report_access(selected["id"])
                        st.session_state.pop(f"share_delete_confirm_{selected['id']}", None)
                        if ok:
                            st.success("Dostęp został trwale usunięty.")
                            st.rerun()
                        st.error("Nie udało się usunąć dostępu.")
                with d2:
                    if st.button("↩️ Anuluj", key=f"delete_confirm_no_{selected['id']}", use_container_width=True):
                        st.session_state.pop(f"share_delete_confirm_{selected['id']}", None)
                        st.rerun()

            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)
            regrant_mode = st.radio(
                "Przyznaj ponownie — ważność",
                ["Ważny przez liczbę godzin", "Ważny do odwołania"],
                horizontal=True,
                key=f"regrant_mode_{study['id']}",
            )
            regrant_hours = None
            if regrant_mode == "Ważny przez liczbę godzin":
                regrant_hours = st.number_input(
                    "Liczba godzin (przyznaj ponownie)",
                    min_value=1,
                    max_value=7200,
                    value=48,
                    key=f"regrant_hours_{study['id']}",
                )
            pw_col, _pw_spacer = st.columns([0.34, 0.66], gap="small")
            with pw_col:
                regrant_password = st.text_input(
                    "Hasło przy przyznaniu ponownie",
                    type="password",
                    autocomplete="new-password",
                    key=f"regrant_password_{study['id']}",
                    help="To hasło zostanie wysłane ponownie e-mailem razem z nowym linkiem.",
                )
            rg_l, rg_r = st.columns([0.82, 0.18], gap="small")
            with rg_r:
                st.markdown("<div id='regrant-anchor'></div>", unsafe_allow_html=True)
                do_regrant = st.button(
                    "🔁 Przyznaj ponownie",
                    key=f"regrant_btn_{selected['id']}",
                    use_container_width=True,
                    type="secondary",
                )
            if do_regrant:
                if len((regrant_password or "").strip()) < 4:
                    st.error("Przy przyznaniu ponownie podaj hasło (min. 4 znaki).")
                else:
                    indefinite = regrant_mode == "Ważny do odwołania"
                    rec = regrant_report_access(
                        selected["id"],
                        hours_valid=(None if indefinite else int(regrant_hours or 48)),
                        indefinite=indefinite,
                    )
                    if not rec:
                        st.error("Nie udało się przyznać dostępu ponownie.")
                    else:
                        set_report_access_password(rec["id"], regrant_password.strip())
                        link = _build_report_link(rec["token"])
                        person_gen = _person_genitive(study)
                        validity_text = _access_validity_text(rec, hours_value=(None if indefinite else int(regrant_hours or 48)), indefinite=indefinite)
                        msg = (
                            f"Została udostępniona Ci możliwość podglądu raportu z badania archetypu {person_gen}.\n\n"
                            f"Aby zobaczyć raport kliknij w link: {link}.\n\n"
                            f"Link jest ważny: {validity_text}.\n\n"
                            f"Hasło dostępowe umożliwiające dostęp do raportu: {regrant_password.strip()}. "
                            f"Pamiętaj, aby nie udostępniać nikomu hasła!\n\n"
                            "W przypadku pytań lub wątpliwości skontaktuj się z:\n"
                            "Piotr Stec\n"
                            "Badania.pro®\n"
                            "e-mail: piotr.stec@badania.pro"
                        )
                        try:
                            host, port, user, pwd, secure, from_email, from_name = _email_env()
                            ok, _provider_id, err = send_email(
                                host=host,
                                port=port,
                                username=user,
                                password=pwd,
                                secure=secure,
                                from_email=from_email,
                                from_name=from_name,
                                to_email=rec["email"],
                                subject=f"Dostęp do raportu archetypu {person_gen}",
                                text=msg,
                            )
                            if ok:
                                mark_report_access_sent(rec["id"])
                                st.success("Dostęp przyznano ponownie i wysłano nowy link.")
                                st.code(link)
                                st.rerun()
                            else:
                                st.error(f"Dostęp przyznano, ale nie udało się wysłać e-maila: {err}")
                        except Exception as e:
                            st.error(f"Dostęp przyznano, ale wysyłka e-maila nie powiodła się: {e}")

def send_link_view() -> None:
    require_auth()
    header("✉️ Wyślij link do ankiety")
    render_titlebar(["Panel", "Wyślij link do ankiety"])
    render_send_link(back_button)

# ───────────────────────── routing ─────────────────────────
if "view" not in st.session_state:
    st.session_state["view"] = "login"
render_build_badge()
with st.sidebar:
    if logged_in():
        if st.button("Wyloguj"): st.session_state.clear(); st.rerun()

public_token = _get_query_token()
if public_token:
    public_report_view(public_token)
else:
    view = st.session_state["view"]
    _set_view_scope(view)
    if view == "login":
        login_view()
    elif view == "home_root":
        home_root_view()
    elif view == "home_personal":
        home_personal_view()
    elif view == "home_jst":
        home_jst_view()
    elif view == "matching":
        matching_view()
    elif view == "add":
        add_view()
    elif view == "edit":
        edit_view()
    elif view == "results":
        results_view()
    elif view == "send":
        send_link_view()
    elif view == "jst_add":
        jst_add_view()
    elif view == "jst_edit":
        jst_edit_view()
    elif view == "jst_send":
        jst_send_view()
    elif view == "jst_io":
        jst_io_view()
    elif view == "jst_analysis":
        jst_analysis_view()
    else:
        home_root_view()
