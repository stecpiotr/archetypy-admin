from __future__ import annotations
from typing import Any, Callable, Dict, List, Tuple, Optional
from copy import deepcopy
import contextlib
from datetime import datetime, timedelta, timezone
import threading
import time
import warnings
import re
import html
import math
import json
import inspect
import base64
import subprocess
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse, quote
import shutil
import urllib.request
import urllib.error
import pandas as pd
import streamlit as st
from streamlit import config as st_config
import plotly.graph_objects as go
from zoneinfo import ZoneInfo

from db_utils import (
    get_supabase,
    fetch_studies,
    fetch_personal_response_count,
    insert_study,
    merge_personal_study_responses,
    update_study,
    check_slug_availability,
    soft_delete_study,
    set_study_status,
    normalize_study_status as normalize_personal_study_status,
)
from db_jst_utils import (
    ARCHETYPES as JST_ARCHETYPES,
    check_jst_slug_availability,
    delete_jst_responses_by_respondent_ids,
    ensure_jst_schema,
    fetch_jst_response_counts,
    fetch_jst_study_by_id,
    fetch_jst_studies,
    insert_jst_response,
    insert_jst_study,
    list_jst_responses,
    make_payload_from_row as jst_make_payload_from_row,
    normalize_response_row as jst_normalize_response_row,
    response_rows_to_dataframe as jst_response_rows_to_dataframe,
    save_metryczka_question_template,
    soft_delete_jst_study,
    set_jst_study_status,
    list_metryczka_question_templates,
    normalize_matching_segments_penalty_strength,
    normalize_study_status as normalize_jst_study_status,
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
from metryczka_config import (
    guess_metry_value_emoji,
    guess_metry_variable_emoji,
    normalize_jst_metryczka_config,
    normalize_personal_metryczka_config,
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


@st.cache_data(ttl=60, show_spinner=False)
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

    # Priorytet: ostatni commit z HEAD gałęzi (GitHub) - zgodnie z oczekiwaniem UI.
    commit = ""
    raw_commit_time = ""
    gh_head_commit, gh_head_committed_at = _fetch_github_head_commit(gh_repo, gh_branch, gh_token)
    if gh_head_commit and gh_head_committed_at:
        commit = gh_head_commit
        raw_commit_time = gh_head_committed_at

    # Fallback 1: lokalny git HEAD.
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

    # Fallback 2: env/secrets/.deployed_sha.
    if not commit:
        commit = _first_nonempty(
            os.getenv("STREAMLIT_GIT_COMMIT_SHA"),
            os.getenv("GITHUB_SHA"),
            os.getenv("COMMIT_SHA"),
            os.getenv("VERCEL_GIT_COMMIT_SHA"),
            os.getenv("SOURCE_VERSION"),
            os.getenv("RENDER_GIT_COMMIT"),
            os.getenv("RAILWAY_GIT_COMMIT_SHA"),
            os.getenv("CI_COMMIT_SHA"),
            os.getenv("HEROKU_SLUG_COMMIT"),
            os.getenv("CF_PAGES_COMMIT_SHA"),
            _secret_get("STREAMLIT_GIT_COMMIT_SHA"),
            _secret_get("GITHUB_SHA"),
            _secret_get("COMMIT_SHA"),
            _secret_get("DEPLOYED_SHA"),
        )
    if not raw_commit_time:
        raw_commit_time = _first_nonempty(
            os.getenv("STREAMLIT_GIT_COMMIT_TIME"),
            os.getenv("GITHUB_COMMIT_TIME"),
            os.getenv("COMMIT_TIME"),
            os.getenv("VERCEL_GIT_COMMIT_TIMESTAMP"),
            os.getenv("SOURCE_COMMIT_TIMESTAMP"),
            os.getenv("RAILWAY_GIT_COMMIT_TIME"),
            os.getenv("CI_COMMIT_TIMESTAMP"),
            os.getenv("BUILD_TIMESTAMP"),
            _secret_get("STREAMLIT_GIT_COMMIT_TIME"),
            _secret_get("GITHUB_COMMIT_TIME"),
            _secret_get("COMMIT_TIME"),
        )
    if not commit:
        deployed_sha_path = Path(repo_root) / ".deployed_sha"
        if deployed_sha_path.exists():
            try:
                commit = str(deployed_sha_path.read_text(encoding="utf-8", errors="ignore")).strip()
            except Exception:
                commit = ""

    # Fallback 3: gdy mamy SHA, ale brak czasu - pobierz metadane tego konkretnego SHA z GitHub.
    if commit and not raw_commit_time:
        _sha_commit, sha_committed_at = _fetch_github_head_commit(gh_repo, commit, gh_token)
        if sha_committed_at:
            raw_commit_time = sha_committed_at

    # Ostatni fallback czasu: mtime pliku app.py (lepsze niż unknown-time).
    if not raw_commit_time:
        try:
            raw_commit_time = str(Path(__file__).resolve().stat().st_mtime)
        except Exception:
            raw_commit_time = ""

    build_time = _to_warsaw_time(raw_commit_time)

    commit_short = commit[:8] if commit else "local"

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
.block-container{ max-width:1160px !important; padding-top:3px !important; }
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

/* Metryczka: pole "Pytanie" startuje wyżej i daje się ręcznie rozszerzać w dół */
textarea[aria-label="Pytanie"]{
  min-height: 56px !important;
  height: auto !important;
  max-height: none !important;
  line-height: 1.3 !important;
  resize: vertical !important;
}
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
.share-chip.closed{
  background:#f1f5f9;
  border-color:#cbd5e1;
  color:#1f2937;
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


def _bool_from_any(raw: Any, default: bool = False) -> bool:
    if raw is None:
        return bool(default)
    if isinstance(raw, bool):
        return raw
    txt = str(raw).strip().lower()
    if txt in {"1", "true", "t", "yes", "y", "on"}:
        return True
    if txt in {"0", "false", "f", "no", "n", "off", ""}:
        return False
    return bool(default)


def _parse_utc_dt(raw: Any) -> Optional[datetime]:
    if raw in (None, ""):
        return None
    try:
        ts = pd.to_datetime(raw, utc=True, errors="coerce")
    except Exception:
        return None
    if pd.isna(ts):
        return None
    try:
        return ts.to_pydatetime()
    except Exception:
        return None


def _utc_to_warsaw_input_defaults(raw: Any, *, fallback_hour: int, fallback_minute: int) -> Tuple[Any, Any]:
    local_now = datetime.now(ZoneInfo("Europe/Warsaw"))
    local_default_dt = local_now.replace(hour=fallback_hour, minute=fallback_minute, second=0, microsecond=0)
    dt_utc = _parse_utc_dt(raw)
    if dt_utc is None:
        return local_default_dt.date(), local_default_dt.time()
    local_dt = dt_utc.astimezone(ZoneInfo("Europe/Warsaw"))
    local_dt = local_dt.replace(second=0, microsecond=0)
    return local_dt.date(), local_dt.time()


def _local_date_time_to_utc_iso(day_value: Any, time_value: Any) -> Optional[str]:
    if not day_value or time_value is None:
        return None
    try:
        local_dt = datetime.combine(day_value, time_value)
    except Exception:
        return None
    if local_dt.tzinfo is None:
        local_dt = local_dt.replace(tzinfo=ZoneInfo("Europe/Warsaw"))
    return local_dt.astimezone(timezone.utc).isoformat()


def _normalize_survey_display_mode(raw: Any, *, allow_single: bool) -> str:
    mode = str(raw or "").strip().lower()
    if allow_single and mode == "single":
        return "single"
    return "matrix"


def _extract_survey_settings(study: Dict[str, Any], *, allow_single: bool) -> Dict[str, Any]:
    notify_raw = study.get("survey_notify_last_count")
    notify_last_count = 0
    try:
        notify_last_count = max(0, int(notify_raw or 0))
    except Exception:
        notify_last_count = 0
    return {
        "display_mode": _normalize_survey_display_mode(study.get("survey_display_mode"), allow_single=allow_single),
        "show_progress": _bool_from_any(study.get("survey_show_progress"), True),
        "allow_back": _bool_from_any(study.get("survey_allow_back"), True),
        "randomize_questions": _bool_from_any(study.get("survey_randomize_questions"), False),
        "auto_start_enabled": _bool_from_any(study.get("survey_auto_start_enabled"), False),
        "auto_start_at": study.get("survey_auto_start_at"),
        "auto_start_applied_at": study.get("survey_auto_start_applied_at"),
        "auto_end_enabled": _bool_from_any(study.get("survey_auto_end_enabled"), False),
        "auto_end_at": study.get("survey_auto_end_at"),
        "auto_end_applied_at": study.get("survey_auto_end_applied_at"),
        "notify_on_response": _bool_from_any(study.get("survey_notify_on_response"), False),
        "notify_email": str(study.get("survey_notify_email") or "").strip(),
        "notify_last_count": notify_last_count,
        "notify_last_sent_at": study.get("survey_notify_last_sent_at"),
    }


def _normalize_notify_email(raw: Any) -> str:
    email = str(raw or "").strip().lower()
    if not email:
        return ""
    if not EMAIL_RE.match(email):
        return ""
    return email


def _survey_notify_descriptor(study: Dict[str, Any], *, kind: str) -> str:
    if kind == "jst":
        full_gen = str(study.get("jst_full_gen") or "").strip()
        if not full_gen:
            full_gen = str(study.get("jst_full_nom") or "").strip()
        if not full_gen:
            full_gen = f"{str(study.get('jst_type') or '').title()} {str(study.get('jst_name') or '').strip()}".strip()
        return f"mieszkańców {full_gen}".strip() if full_gen else "mieszkańców tego badania"

    first_gen = str(study.get("first_name_gen") or study.get("first_name_nom") or study.get("first_name") or "").strip()
    last_gen = str(study.get("last_name_gen") or study.get("last_name_nom") or study.get("last_name") or "").strip()
    city = str(study.get("city") or "").strip()
    person = f"{first_gen} {last_gen}".strip()
    if person and city:
        person = f"{person} ({city})"
    if not person:
        slug = str(study.get("slug") or "").strip()
        person = f"/{slug}" if slug else "tej osoby"
    return f"archetypu {person}".strip()


def _survey_public_url(slug: str, *, kind: str) -> str:
    clean_slug = str(slug or "").strip().lstrip("/")
    if kind == "jst":
        base = str(st.secrets.get("JST_SURVEY_BASE_URL", "https://jst.badania.pro") or "").rstrip("/")
    else:
        base = str(st.secrets.get("SURVEY_BASE_URL", "https://archetypy.badania.pro") or "").rstrip("/")
    return f"{base}/{clean_slug}" if clean_slug else base


def _survey_notify_body(study_descriptor: str, survey_url: str, total_count: int) -> str:
    safe_count = max(0, int(total_count or 0))
    return (
        f"Została udzielona odpowiedź w badaniu {study_descriptor}, dostępnym pod adresem {survey_url}.\n\n"
        f"Łączna liczba wypełnionych ankiet dla tego badania to: {safe_count}."
    )


def _send_response_notify_email(*, to_email: str, study_descriptor: str, survey_url: str, total_count: int) -> Tuple[bool, str]:
    try:
        host, port, user, pwd, secure, from_email, from_name = _email_env()
    except Exception as exc:
        return False, str(exc)
    ok, _provider_id, err = send_email(
        host=host,
        port=port,
        username=user,
        password=pwd,
        secure=secure,
        from_email=from_email,
        from_name=from_name,
        to_email=to_email,
        subject=f"Nowa odpowiedź w badaniu {study_descriptor}",
        text=_survey_notify_body(study_descriptor, survey_url, total_count),
    )
    return bool(ok), str(err or "")


def _fetch_personal_counts_by_slug() -> Dict[str, int]:
    out: Dict[str, int] = {}
    try:
        res = sb.from_("study_response_count_v").select("slug,responses").execute()
    except Exception:
        return out
    for row in (res.data or []):
        slug = str(row.get("slug") or "").strip()
        if not slug:
            continue
        try:
            out[slug] = max(0, int(row.get("responses") or 0))
        except Exception:
            out[slug] = 0
    return out


def _dispatch_personal_response_notifications() -> None:
    studies = fetch_studies(sb)
    if not studies:
        return
    counts_by_slug = _fetch_personal_counts_by_slug()
    now_iso = datetime.now(timezone.utc).isoformat()
    for study in studies:
        sid = str(study.get("id") or "").strip()
        slug = str(study.get("slug") or "").strip()
        if not sid or not slug:
            continue
        cfg = _extract_survey_settings(study, allow_single=True)
        if not bool(cfg.get("notify_on_response")):
            continue
        notify_email = _normalize_notify_email(cfg.get("notify_email"))
        if not notify_email:
            continue
        current_count = max(0, int(counts_by_slug.get(slug, 0)))
        last_count = max(0, int(cfg.get("notify_last_count") or 0))
        if current_count <= last_count:
            if current_count < last_count:
                try:
                    sb.table("studies").update({"survey_notify_last_count": current_count}).eq("id", sid).execute()
                except Exception:
                    pass
            continue
        study_descriptor = _survey_notify_descriptor(study, kind="personal")
        survey_url = _survey_public_url(slug, kind="personal")
        ok, _err = _send_response_notify_email(
            to_email=notify_email,
            study_descriptor=study_descriptor,
            survey_url=survey_url,
            total_count=current_count,
        )
        if ok:
            try:
                sb.table("studies").update(
                    {
                        "survey_notify_last_count": current_count,
                        "survey_notify_last_sent_at": now_iso,
                    }
                ).eq("id", sid).execute()
            except Exception:
                pass


def _dispatch_jst_response_notifications() -> None:
    studies = fetch_jst_studies(sb)
    if not studies:
        return
    counts_by_id = fetch_jst_response_counts(sb)
    now_iso = datetime.now(timezone.utc).isoformat()
    for study in studies:
        sid = str(study.get("id") or "").strip()
        slug = str(study.get("slug") or "").strip()
        if not sid or not slug:
            continue
        cfg = _extract_survey_settings(study, allow_single=False)
        if not bool(cfg.get("notify_on_response")):
            continue
        notify_email = _normalize_notify_email(cfg.get("notify_email"))
        if not notify_email:
            continue
        current_count = max(0, int(counts_by_id.get(sid, 0)))
        last_count = max(0, int(cfg.get("notify_last_count") or 0))
        if current_count <= last_count:
            if current_count < last_count:
                try:
                    sb.table("jst_studies").update({"survey_notify_last_count": current_count}).eq("id", sid).execute()
                except Exception:
                    pass
            continue
        study_descriptor = _survey_notify_descriptor(study, kind="jst")
        survey_url = _survey_public_url(slug, kind="jst")
        ok, _err = _send_response_notify_email(
            to_email=notify_email,
            study_descriptor=study_descriptor,
            survey_url=survey_url,
            total_count=current_count,
        )
        if ok:
            try:
                sb.table("jst_studies").update(
                    {
                        "survey_notify_last_count": current_count,
                        "survey_notify_last_sent_at": now_iso,
                    }
                ).eq("id", sid).execute()
            except Exception:
                pass


def _run_response_notifications_dispatcher() -> None:
    now_utc = datetime.now(timezone.utc)
    last_run = st.session_state.get("_notify_dispatch_last_run_utc")
    if isinstance(last_run, datetime):
        if (now_utc - last_run).total_seconds() < 30:
            return
    st.session_state["_notify_dispatch_last_run_utc"] = now_utc
    if not _ensure_jst_schema_initialized():
        return
    try:
        _dispatch_personal_response_notifications()
        _dispatch_jst_response_notifications()
    except Exception:
        # Dispatcher nie może blokować panelu.
        pass


def _notification_dispatcher_loop(poll_seconds: int) -> None:
    interval = max(5, int(poll_seconds or 5))
    while True:
        try:
            if _ensure_jst_schema_initialized():
                _dispatch_personal_response_notifications()
                _dispatch_jst_response_notifications()
        except Exception:
            # Pętla nie może się wywrócić przez chwilową niedostępność DB/SMTP.
            pass
        time.sleep(interval)


@st.cache_resource
def _start_notification_dispatcher_background() -> Dict[str, Any]:
    enabled_raw = st.secrets.get("SURVEY_NOTIFY_BACKGROUND_ENABLED", True)
    enabled = _bool_from_any(enabled_raw, True)
    poll_raw = st.secrets.get("SURVEY_NOTIFY_POLL_SECONDS", 5)
    try:
        poll_seconds = max(5, int(poll_raw or 5))
    except Exception:
        poll_seconds = 5
    if not enabled:
        return {"enabled": False, "poll_seconds": poll_seconds}

    worker = threading.Thread(
        target=_notification_dispatcher_loop,
        args=(poll_seconds,),
        daemon=True,
        name="survey-notify-dispatcher",
    )
    worker.start()
    return {"enabled": True, "poll_seconds": poll_seconds}


def _scheduled_survey_transition_updates(study: Dict[str, Any], *, kind: str, now_utc: Optional[datetime] = None) -> Dict[str, Any]:
    cfg = _extract_survey_settings(study, allow_single=(kind == "personal"))
    if kind == "jst":
        status = normalize_jst_study_status(
            study.get("study_status"),
            is_active=study.get("is_active"),
            deleted_at=study.get("deleted_at"),
        )
    else:
        status = normalize_personal_study_status(
            study.get("study_status"),
            is_active=study.get("is_active"),
            deleted_at=study.get("deleted_at"),
        )
    if status in {"closed", "deleted"}:
        return {}

    now_val = now_utc or datetime.now(timezone.utc)
    now_iso = now_val.isoformat()
    updates: Dict[str, Any] = {}
    next_status = status

    start_at = _parse_utc_dt(cfg.get("auto_start_at"))
    start_applied_at = _parse_utc_dt(cfg.get("auto_start_applied_at"))
    end_at = _parse_utc_dt(cfg.get("auto_end_at"))
    end_applied_at = _parse_utc_dt(cfg.get("auto_end_applied_at"))

    if cfg.get("auto_start_enabled") and start_at and start_applied_at is None:
        if now_val >= start_at:
            updates["survey_auto_start_applied_at"] = now_iso
            if next_status == "suspended":
                next_status = "active"
        else:
            if next_status == "active":
                next_status = "suspended"

    if cfg.get("auto_end_enabled") and end_at and end_applied_at is None and now_val >= end_at:
        updates["survey_auto_end_applied_at"] = now_iso
        if next_status == "active":
            next_status = "suspended"

    if next_status != status:
        updates["study_status"] = next_status
        updates["status_changed_at"] = now_iso

    return updates


def _apply_scheduled_survey_transitions(study: Dict[str, Any], *, kind: str) -> Dict[str, Any]:
    sid = str(study.get("id") or "").strip()
    if not sid:
        return study
    updates = _scheduled_survey_transition_updates(study, kind=kind)
    if not updates:
        return study
    try:
        if kind == "jst":
            update_jst_study(sb, sid, updates)
            fresh = fetch_jst_study_by_id(sb, sid)
            return fresh or study
        update_study(sb, sid, updates)
        fresh_res = sb.table("studies").select("*").eq("id", sid).limit(1).execute()
        return (fresh_res.data or [study])[0]
    except Exception:
        return study


def _download_button_supports_ignore() -> bool:
    try:
        sig = inspect.signature(st.download_button)
        param = sig.parameters.get("on_click")
        if not param:
            return False
        ann = str(param.annotation or "")
        default = str(param.default or "")
        joined = (ann + " " + default).lower()
        return ("ignore" in joined) and ("rerun" in joined)
    except Exception:
        return False


def _download_button_compat(*args, **kwargs):
    # Starsze wersje Streamlit nie wspierają on_click="ignore" i traktują string jak callback,
    # co kończy się błędem "str object is not callable" podczas rerunu.
    if _download_button_supports_ignore():
        kwargs.setdefault("on_click", "ignore")
    else:
        kwargs.pop("on_click", None)
    return st.download_button(*args, **kwargs)


def _toast_success_compat(message: str) -> None:
    toast_fn = getattr(st, "toast", None)
    if callable(toast_fn):
        try:
            toast_fn(message, icon="✅")
            return
        except TypeError:
            try:
                toast_fn(message)
                return
            except Exception:
                pass
        except Exception:
            pass
    st.success(message)


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


def _study_status_label(status: str, with_icon: bool = False) -> str:
    s = str(status or "").strip().lower()
    if s == "suspended":
        return "🟠 zawieszone" if with_icon else "zawieszone"
    if s == "closed":
        return "⚫ zamknięte" if with_icon else "zamknięte"
    if s == "deleted":
        return "🔴 usunięte" if with_icon else "usunięte"
    return "🟢 aktywne" if with_icon else "aktywne"


def _study_status_meta(study: Dict[str, Any], *, kind: str) -> Dict[str, str]:
    if kind == "jst":
        status = normalize_jst_study_status(
            study.get("study_status"),
            is_active=study.get("is_active"),
            deleted_at=study.get("deleted_at"),
        )
    else:
        status = normalize_personal_study_status(
            study.get("study_status"),
            is_active=study.get("is_active"),
            deleted_at=study.get("deleted_at"),
        )
    started_at = _fmt_local_ts(study.get("started_at")) or _fmt_local_ts(study.get("created_at")) or "—"
    status_changed = (
        _fmt_local_ts(study.get("status_changed_at"))
        or _fmt_local_ts(study.get("updated_at"))
        or _fmt_local_ts(study.get("created_at"))
        or "—"
    )
    return {
        "status": status,
        "status_label": _study_status_label(status, with_icon=True),
        "started_at": started_at,
        "status_changed_at": status_changed,
    }


def _render_study_status_panel(
    *,
    kind: str,
    study: Dict[str, Any],
    on_suspend: Callable[[], None],
    on_unsuspend: Callable[[], None],
    on_close: Callable[[], None],
    on_delete: Callable[[], None],
    close_confirm_key: str,
    delete_confirm_key: str,
) -> None:
    meta = _study_status_meta(study, kind=kind)
    status = meta["status"]
    st.markdown('<div class="section-gap-big"></div>', unsafe_allow_html=True)
    st.markdown("### Status badania")
    status_df = pd.DataFrame(
        [
            {
                "Status": meta["status_label"],
                "Data uruchomienia badania": meta["started_at"],
                "Data ostatniego statusu": meta["status_changed_at"],
            }
        ]
    )
    st.dataframe(status_df, use_container_width=True, hide_index=True)
    st.markdown(
        "<div class='share-manage-meta'>"
        f"<span class='share-chip {status}'>status: {meta['status_label']}</span>"
        f"<span class='share-chip'>start: {meta['started_at']}</span>"
        f"<span class='share-chip'>ostatnia zmiana: {meta['status_changed_at']}</span>"
        "</div>",
        unsafe_allow_html=True,
    )

    b1, b2, b3, b4, _sp = st.columns([0.17, 0.17, 0.20, 0.17, 0.29], gap="small")
    with b1:
        if st.button("⏸️ Zawieś", key=f"{kind}_suspend_{study.get('id')}", use_container_width=True, disabled=status != "active"):
            on_suspend()
    with b2:
        if st.button("▶️ Odwieś", key=f"{kind}_unsuspend_{study.get('id')}", use_container_width=True, disabled=status != "suspended"):
            on_unsuspend()
    with b3:
        close_disabled = status in {"closed", "deleted"}
        if st.button("🔒 Zamknij badanie", key=f"{kind}_close_{study.get('id')}", use_container_width=True, disabled=close_disabled):
            st.session_state[close_confirm_key] = True
            st.rerun()
    with b4:
        if st.button("🗑️ Usuń badanie", key=f"{kind}_delete_{study.get('id')}", use_container_width=True):
            st.session_state[delete_confirm_key] = True
            st.rerun()

    if status == "closed":
        st.info("Badanie jest zamknięte na stałe. Nie można go ponownie uruchomić ani zbierać nowych głosów.")

    if st.session_state.get(close_confirm_key, False):
        st.warning("Po zamknięciu badania nie będzie można już przyjmować odpowiedzi ani ponownie uruchomić badania.")
        c1, c2, _csp = st.columns([0.24, 0.16, 0.60], gap="small")
        with c1:
            if st.button("✅ Tak, zamknij", key=f"{kind}_close_yes_{study.get('id')}", use_container_width=True):
                st.session_state.pop(close_confirm_key, None)
                on_close()
        with c2:
            if st.button("↩️ Anuluj", key=f"{kind}_close_no_{study.get('id')}", use_container_width=True):
                st.session_state.pop(close_confirm_key, None)
                st.rerun()

    if st.session_state.get(delete_confirm_key, False):
        st.warning("Czy na pewno usunąć badanie? Tej operacji nie można cofnąć.")
        d1, d2, _dsp = st.columns([0.22, 0.16, 0.62], gap="small")
        with d1:
            if st.button("✅ Tak, usuń", key=f"{kind}_delete_yes_{study.get('id')}", use_container_width=True):
                st.session_state.pop(delete_confirm_key, None)
                on_delete()
        with d2:
            if st.button("↩️ Anuluj", key=f"{kind}_delete_no_{study.get('id')}", use_container_width=True):
                st.session_state.pop(delete_confirm_key, None)
                st.rerun()

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

# Wyjątki dla nieregularnych nazw JST (łatwe do dalszego rozszerzania).
JST_WORD_CASE_OVERRIDES: Dict[str, Dict[str, str]] = {
    "ełk": {
        "nom": "Ełk",
        "gen": "Ełku",
        "dat": "Ełkowi",
        "acc": "Ełk",
        "ins": "Ełkiem",
        "loc": "Ełku",
        "voc": "Ełku",
    },
    "sopot": {
        "nom": "Sopot",
        "gen": "Sopotu",
        "dat": "Sopotowi",
        "acc": "Sopot",
        "ins": "Sopotem",
        "loc": "Sopocie",
        "voc": "Sopocie",
    },
    "kielce": {
        "nom": "Kielce",
        "gen": "Kielc",
        "dat": "Kielcom",
        "acc": "Kielce",
        "ins": "Kielcami",
        "loc": "Kielcach",
        "voc": "Kielce",
    },
    "katowice": {
        "nom": "Katowice",
        "gen": "Katowic",
        "dat": "Katowicom",
        "acc": "Katowice",
        "ins": "Katowicami",
        "loc": "Katowicach",
        "voc": "Katowice",
    },
    "suwałki": {
        "nom": "Suwałki",
        "gen": "Suwałk",
        "dat": "Suwałkom",
        "acc": "Suwałki",
        "ins": "Suwałkami",
        "loc": "Suwałkach",
        "voc": "Suwałki",
    },
    "tychy": {
        "nom": "Tychy",
        "gen": "Tychów",
        "dat": "Tychom",
        "acc": "Tychy",
        "ins": "Tychami",
        "loc": "Tychach",
        "voc": "Tychy",
    },
    "zakopane": {
        "nom": "Zakopane",
        "gen": "Zakopanego",
        "dat": "Zakopanemu",
        "acc": "Zakopane",
        "ins": "Zakopanem",
        "loc": "Zakopanem",
        "voc": "Zakopane",
    },
}

JST_PHRASE_CASE_OVERRIDES: Dict[str, Dict[str, str]] = {
    "zielona góra": {
        "nom": "Zielona Góra",
        "gen": "Zielonej Góry",
        "dat": "Zielonej Górze",
        "acc": "Zieloną Górę",
        "ins": "Zieloną Górą",
        "loc": "Zielonej Górze",
        "voc": "Zielona Góra",
    },
    "nowy sącz": {
        "nom": "Nowy Sącz",
        "gen": "Nowego Sącza",
        "dat": "Nowemu Sączowi",
        "acc": "Nowy Sącz",
        "ins": "Nowym Sączem",
        "loc": "Nowym Sączu",
        "voc": "Nowy Sączu",
    },
}


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

    override = JST_WORD_CASE_OVERRIDES.get(low)
    if override:
        return {c: (override.get(c) or "") for c in JST_CASES}

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

    # Częste nazwy miejscowe nijakie zakończone na -o (np. Testowo, Braniewo, Gniezno)
    if low.endswith("o") and len(w) > 1:
        base = w[:-1]
        return {
            "nom": w,
            "gen": base + "a",
            "dat": base + "u",
            "acc": w,
            "ins": base + "em",
            "loc": base + "ie",
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
    phrase_clean = re.sub(r"\s+", " ", (phrase or "").strip())
    phrase_override = JST_PHRASE_CASE_OVERRIDES.get(phrase_clean.lower())
    if phrase_override:
        return {c: (phrase_override.get(c) or phrase_clean) for c in JST_CASES}

    words = [w for w in phrase_clean.split() if w.strip()]
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

    c1, c2, c3, c4, c5, c6, c7 = st.columns(7, gap="small")
    with c1:
        if st.button("➕\n\nDodaj badanie archetypu", key="tile_home_personal_add", type="secondary", use_container_width=True):
            goto("add")
    with c2:
        if st.button("✏️\n\nEdytuj dane badania", key="tile_home_personal_edit", type="secondary", use_container_width=True):
            goto("edit")
    with c3:
        if st.button("⚙️\n\nUstawienia ankiety", key="tile_home_personal_settings", type="secondary", use_container_width=True):
            goto("personal_settings")
    with c4:
        if st.button("🧾\n\nMetryczka", key="tile_home_personal_metryczka", type="secondary", use_container_width=True):
            goto("personal_metryczka")
    with c5:
        if st.button("✉️\n\nWyślij link do ankiety", key="tile_home_personal_send", type="secondary", use_container_width=True):
            goto("send")
    with c6:
        if st.button("🔗\n\nPołącz badania", key="tile_home_personal_merge", type="secondary", use_container_width=True):
            goto("personal_merge")
    with c7:
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

    c1, c2, c3, c4, c5, c6, c7 = st.columns(7, gap="small")
    with c1:
        if st.button("➕\n\nDodaj badanie\nmieszkańców", key="tile_home_jst_add", type="secondary", use_container_width=True):
            goto("jst_add")
    with c2:
        if st.button("✏️\n\nEdytuj dane\nbadania", key="tile_home_jst_edit", type="secondary", use_container_width=True):
            goto("jst_edit")
    with c3:
        if st.button("⚙️\n\nUstawienia\nankiety", key="tile_home_jst_settings", type="secondary", use_container_width=True):
            goto("jst_settings")
    with c4:
        if st.button("🧾\n\nMetryczka", key="tile_home_jst_metryczka", type="secondary", use_container_width=True):
            goto("jst_metryczka")
    with c5:
        if st.button("✉️\n\nWyślij link\ndo ankiety", key="tile_home_jst_send", type="secondary", use_container_width=True):
            goto("jst_send")
    with c6:
        if st.button("💾\n\nImport i eksport\nbaz danych", key="tile_home_jst_io", type="secondary", use_container_width=True):
            goto("jst_io")
    with c7:
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
            st.rerun()
        except Exception as e:
            st.error(f"Błąd zapisu: {e}")

_METRY_CORE_IDS: Tuple[str, ...] = ("M_PLEC", "M_WIEK", "M_WYKSZT", "M_ZAWOD", "M_MATERIAL")
_METRY_CUSTOM_CODE_RE = re.compile(r"^M_[A-Z0-9_]{2,40}$")
_METRY_PASTE_OPTION_PREFIX_RE = re.compile(r"^\s*(?:[-–—*•]+|\(?\d{1,3}[\)\].:-]|[A-Za-z][\)\].:-])\s+")
_METRY_ICON_LIBRARY: List[Tuple[str, str]] = [
    ("", "(brak ikony)"),
    ("📌", "uniwersalna"),
    ("👫", "płeć"),
    ("👩", "kobieta"),
    ("👨", "mężczyzna"),
    ("⌛", "wiek"),
    ("🧭", "orientacja / poglądy"),
    ("🧑", "wiek 15-39"),
    ("🧑‍💼", "wiek 40-59"),
    ("🧓", "wiek 60+"),
    ("🎓", "wykształcenie"),
    ("🛠️", "podst./gim./zaw."),
    ("📘", "średnie"),
    ("💼", "status zawodowy"),
    ("🧠", "prac. umysłowy"),
    ("🏢", "własna firma"),
    ("🧑‍🎓", "student/uczeń"),
    ("🔎", "bezrobotny"),
    ("🌿", "rencista/emeryt"),
    ("🧩", "inna"),
    ("💰", "sytuacja materialna"),
    ("😄", "bardzo dobra"),
    ("🙂", "raczej dobra"),
    ("😐", "przeciętna"),
    ("🙁", "raczej zła"),
    ("😟", "bardzo zła"),
    ("🤐", "odmowa"),
    ("📍", "miejsce / obszar"),
    ("🏙️", "miasto"),
    ("🌾", "wieś"),
    ("🗳️", "preferencje polityczne"),
    ("➡️", "prawicowe"),
    ("↗️", "centro-prawicowe"),
    ("⚖️", "centrowe"),
    ("↖️", "centro-lewicowe"),
    ("⬅️", "lewicowe"),
    ("❓", "nie wiem"),
    ("✅", "tak"),
    ("❌", "nie"),
]
_METRY_ICON_CUSTOM_LABEL = "✍️ Własna ikona…"
_METRY_ICON_LABEL_TO_VALUE: Dict[str, str] = {
    (f"{icon} {name}".strip() if icon else name): icon for icon, name in _METRY_ICON_LIBRARY
}
_METRY_ICON_VALUE_TO_LABEL: Dict[str, str] = {
    icon: (f"{icon} {name}".strip() if icon else name) for icon, name in _METRY_ICON_LIBRARY
}
_METRY_ICON_PICK_VALUES: List[str] = [icon for icon, _ in _METRY_ICON_LIBRARY]


def _metry_icon_picker(
    *,
    label: str,
    key_prefix: str,
    value: Any,
    help_text: str = "",
) -> str:
    current = str(value or "").strip()
    pick_key = f"{key_prefix}_pick"
    custom_key = f"{key_prefix}_custom"
    select_options = list(_METRY_ICON_LABEL_TO_VALUE.keys()) + [_METRY_ICON_CUSTOM_LABEL]
    if pick_key not in st.session_state:
        st.session_state[pick_key] = _METRY_ICON_VALUE_TO_LABEL.get(current, _METRY_ICON_CUSTOM_LABEL)
    if custom_key not in st.session_state:
        st.session_state[custom_key] = current if current not in _METRY_ICON_VALUE_TO_LABEL else ""
    picked = st.selectbox(
        label,
        select_options,
        key=pick_key,
        help=help_text or None,
    )
    if picked == _METRY_ICON_CUSTOM_LABEL:
        custom_val = st.text_input(
            "Wgraj/wklej własną ikonkę",
            key=custom_key,
            placeholder="np. 🛰️",
        )
        return str(custom_val or "").strip()
    st.session_state[custom_key] = ""
    return str(_METRY_ICON_LABEL_TO_VALUE.get(picked) or "").strip()


def _metryczka_normalize_config(kind: str, raw: Any) -> Dict[str, Any]:
    return normalize_jst_metryczka_config(raw) if kind == "jst" else normalize_personal_metryczka_config(raw)


def _metryczka_editor_state_key(kind: str, study_key: str) -> str:
    return f"{kind}_metryczka_editor_cfg_{study_key}"


def _metryczka_editor_nonce_key(kind: str, study_key: str) -> str:
    return f"{kind}_metryczka_editor_nonce_{study_key}"


def _metryczka_editor_widget_prefix(kind: str, study_key: str) -> str:
    nonce_key = _metryczka_editor_nonce_key(kind, study_key)
    try:
        nonce = int(st.session_state.get(nonce_key, 0) or 0)
    except Exception:
        nonce = 0
    return f"{kind}_metryczka_editor_widget_{study_key}_{nonce}_"


def _bump_metryczka_editor_nonce(kind: str, study_key: str) -> None:
    nonce_key = _metryczka_editor_nonce_key(kind, study_key)
    try:
        current = int(st.session_state.get(nonce_key, 0) or 0)
    except Exception:
        current = 0
    st.session_state[nonce_key] = current + 1


def _metryczka_scroll_target_key(kind: str, study_key: str) -> str:
    return f"{kind}_metryczka_editor_scroll_target_{study_key}"


def _metryczka_scroll_nonce_key(kind: str, study_key: str) -> str:
    return f"{kind}_metryczka_editor_scroll_nonce_{study_key}"



def _metryczka_anchor_id(kind: str, study_key: str, ui_key: str) -> str:
    raw = f"metryczka-{kind}-{study_key}-{ui_key}"
    safe = re.sub(r"[^A-Za-z0-9_-]+", "-", raw).strip("-")
    return safe or f"metryczka-{kind}"


def _option_value_emoji_or_guess(opt: Dict[str, Any], *, table_label: str, code: str, db_column: str) -> str:
    if isinstance(opt, dict) and "value_emoji" in opt:
        return str(opt.get("value_emoji") or "").strip()
    return str(guess_metry_value_emoji(table_label, code, db_column) or "").strip()


def _metryczka_options_to_df(
    options: Any,
    *,
    randomize_options: bool = False,
    legacy_exclude_last: bool = False,
    table_label: str = "",
    db_column: str = "",
) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    has_locked = False
    if isinstance(options, list):
        for opt in options:
            if not isinstance(opt, dict):
                continue
            lock_randomization = bool(opt.get("lock_randomization") is True)
            if lock_randomization:
                has_locked = True
            rows.append(
                {
                    "Odpowiedź": str(opt.get("label") or "").strip(),
                    "Kodowanie": str(opt.get("code") or "").strip(),
                    "Otwarta": bool(opt.get("is_open") is True),
                    "Blokuj losowanie": lock_randomization,
                    "Ikona": _option_value_emoji_or_guess(
                        opt,
                        table_label=table_label,
                        code=str(opt.get("code") or opt.get("label") or "").strip(),
                        db_column=db_column,
                    ),
                }
            )
    if randomize_options and legacy_exclude_last and rows and not has_locked:
        rows[-1]["Blokuj losowanie"] = True
    if not rows:
        rows = [{"Odpowiedź": "", "Kodowanie": "", "Otwarta": False, "Blokuj losowanie": False, "Ikona": ""}]
    return pd.DataFrame(rows)


def _metryczka_data_editor_height(df: Any, *, min_rows: int = 1, max_rows: int = 60) -> int:
    row_count = int(len(df.index)) if isinstance(df, pd.DataFrame) else 0
    visible_rows = min(max(row_count, int(min_rows)), int(max_rows))
    # Nagłówek + wiersze danych; bez sztucznego "dopompowania" pustych rzędów.
    return int(70 + visible_rows * 35)


def _metryczka_editor_df_clean(df: Any) -> pd.DataFrame:
    cols = ["Odpowiedź", "Kodowanie", "Otwarta", "Blokuj losowanie", "Ikona"]
    if not isinstance(df, pd.DataFrame):
        return pd.DataFrame(columns=cols)
    out = df.copy()
    for col in cols:
        if col not in out.columns:
            out[col] = "" if col not in {"Otwarta", "Blokuj losowanie"} else False
    def _is_blank_row(row: pd.Series) -> bool:
        ans = str(row.get("Odpowiedź") or "").strip()
        code = str(row.get("Kodowanie") or "").strip()
        icon = str(row.get("Ikona") or "").strip()
        is_open = bool(row.get("Otwarta") is True)
        lock = bool(row.get("Blokuj losowanie") is True)
        return (not ans) and (not code) and (not icon) and (not is_open) and (not lock)
    if not out.empty:
        mask = out.apply(_is_blank_row, axis=1)
        nonblank_count = int((~mask).sum())
        if nonblank_count > 0:
            out = out.loc[~mask].copy()
        else:
            out = out.iloc[:1].copy()
    if out.empty:
        return pd.DataFrame(columns=cols)
    return out[cols].reset_index(drop=True)


def _metryczka_reorder_df(df: pd.DataFrame, index: int, delta: int) -> pd.DataFrame:
    out = _metryczka_editor_df_clean(df)
    if out.empty:
        return out
    i = int(index)
    j = i + int(delta)
    if i < 0 or i >= len(out.index) or j < 0 or j >= len(out.index):
        return out
    rows = out.to_dict("records")
    rows[i], rows[j] = rows[j], rows[i]
    return pd.DataFrame(rows, columns=list(out.columns))


def _metryczka_append_empty_row(df: Any) -> pd.DataFrame:
    out = _metryczka_editor_df_clean(df)
    if not out.empty:
        only_blank = True
        for _, row in out.iterrows():
            if str(row.get("Odpowiedź") or "").strip() or str(row.get("Kodowanie") or "").strip() or str(row.get("Ikona") or "").strip() or bool(row.get("Otwarta") is True) or bool(row.get("Blokuj losowanie") is True):
                only_blank = False
                break
        if only_blank:
            return out
    empty_row = {
        "Odpowiedź": "",
        "Kodowanie": "",
        "Otwarta": False,
        "Blokuj losowanie": False,
        "Ikona": "",
    }
    out = pd.concat([out, pd.DataFrame([empty_row])], ignore_index=True)
    return out


def _metryczka_attach_move_marker(df: Any, selected_index: int, marker_col: str = "Przesuń") -> pd.DataFrame:
    base = _metryczka_editor_df_clean(df)
    out = base.copy()
    if marker_col in out.columns:
        out = out.drop(columns=[marker_col], errors="ignore")
    sel = int(selected_index) if isinstance(selected_index, int) else -1
    out.insert(0, marker_col, [i == sel for i in range(len(out.index))])
    return out


def _metryczka_extract_move_marker(df: Any, marker_col: str = "Przesuń") -> Tuple[pd.DataFrame, int]:
    if not isinstance(df, pd.DataFrame):
        return _metryczka_editor_df_clean(df), -1
    out = df.copy()
    selected_idx = -1
    if marker_col in out.columns:
        picked = [i for i, v in enumerate(list(out[marker_col])) if bool(v)]
        if picked:
            selected_idx = int(picked[-1])
            out[marker_col] = [i == selected_idx for i in range(len(out.index))]
        out = out.drop(columns=[marker_col], errors="ignore")
    out = _metryczka_editor_df_clean(out)
    if selected_idx >= len(out.index):
        selected_idx = -1
    return out, selected_idx


def _metryczka_options_from_df(df: Any) -> List[Dict[str, Any]]:
    if not isinstance(df, pd.DataFrame):
        return []
    df = _metryczka_editor_df_clean(df)
    out: List[Dict[str, Any]] = []
    seen_codes: set[str] = set()
    for _, row in df.iterrows():
        label = str(row.get("Odpowiedź") or "").strip()
        code = str(row.get("Kodowanie") or "").strip()
        is_open = bool(row.get("Otwarta") is True)
        lock_randomization = bool(row.get("Blokuj losowanie") is True)
        value_emoji = str(row.get("Ikona") or "").strip()
        if not label:
            continue
        # Zachowujemy wiersze nawet z pustym kodowaniem, aby nie gubić odpowiedzi w UI.
        # Duplikaty filtrujemy tylko dla niepustych kodów.
        if code:
            code_norm = code.lower()
            if code_norm in seen_codes:
                continue
            seen_codes.add(code_norm)
        out.append(
            {
                "label": label,
                "code": code,
                "is_open": is_open,
                "lock_randomization": lock_randomization,
                "value_emoji": value_emoji,
            }
        )
    return out


def _metry_icon_options_for_df(df: Any) -> List[str]:
    out = list(_METRY_ICON_PICK_VALUES)
    if isinstance(df, pd.DataFrame) and "Ikona" in df.columns:
        for raw in list(df["Ikona"].tolist()):
            icon = str(raw or "").strip()
            if not icon or icon in out:
                continue
            out.append(icon)
    return out


def _metryczka_apply_legacy_exclude_last_lock(
    options: List[Dict[str, Any]],
    *,
    randomize_options: bool,
    legacy_exclude_last: bool,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    has_locked = False
    for opt in options:
        if not isinstance(opt, dict):
            continue
        cloned = dict(opt)
        locked = bool(cloned.get("lock_randomization") is True)
        if locked:
            has_locked = True
        cloned["lock_randomization"] = locked
        out.append(cloned)
    if randomize_options and legacy_exclude_last and out and not has_locked:
        out[-1]["lock_randomization"] = True
    return out


def _paste_line_normalize(raw_line: Any) -> str:
    txt = str(raw_line or "").replace("\t", " ").strip()
    txt = re.sub(r"\s+", " ", txt)
    return txt


def _paste_line_as_option(raw_line: Any) -> str:
    txt = _paste_line_normalize(raw_line)
    txt = _METRY_PASTE_OPTION_PREFIX_RE.sub("", txt).strip()
    return txt


def _paste_is_option_like(raw_line: Any) -> bool:
    raw = str(raw_line or "").strip()
    if not raw:
        return False
    if _METRY_PASTE_OPTION_PREFIX_RE.match(raw):
        return True
    txt = _paste_line_as_option(raw_line)
    if not txt:
        return False
    if len(txt) > 90:
        return False
    if txt.endswith("?"):
        return False
    return True


def _parse_pasted_question_and_answers(raw_text: Any, fallback_prompt: str = "") -> Tuple[str, List[str]]:
    lines_raw = [str(x) for x in str(raw_text or "").splitlines()]
    lines: List[str] = []
    for ln in lines_raw:
        txt = _paste_line_normalize(ln)
        if not txt:
            continue
        low = txt.lower().rstrip(":")
        if low in {"treść pytania", "tresc pytania", "pytanie", "odpowiedzi", "odpowiedź", "odpowiedz"}:
            continue
        txt = re.sub(r"^(?:treść pytania|tresc pytania)\s*:\s*", "", txt, flags=re.IGNORECASE).strip()
        txt = re.sub(r"^(?:pytanie)\s*:\s*", "", txt, flags=re.IGNORECASE).strip()
        txt = re.sub(r"^(?:odpowiedzi|odpowiedź|odpowiedz)\s*:\s*", "", txt, flags=re.IGNORECASE).strip()
        if txt:
            lines.append(txt)

    if not lines:
        return "", []

    if len(lines) >= 2 and fallback_prompt and _paste_is_option_like(lines[0]) and _paste_is_option_like(lines[1]):
        answers_only = [_paste_line_as_option(x) for x in lines if _paste_line_as_option(x)]
        return str(fallback_prompt or "").strip(), answers_only

    split_idx: Optional[int] = None
    for i in range(1, len(lines) - 1):
        if _paste_is_option_like(lines[i]) and _paste_is_option_like(lines[i + 1]):
            split_idx = i
            break

    if split_idx is None:
        if len(lines) >= 2 and lines[0].rstrip().endswith("?"):
            split_idx = 1
        elif len(lines) >= 3:
            split_idx = 2
        else:
            split_idx = 1 if len(lines) > 1 else len(lines)

    question_lines = lines[:split_idx]
    answer_lines = lines[split_idx:]
    question = " ".join(question_lines).strip()
    if not question:
        question = str(fallback_prompt or "").strip()

    answers: List[str] = []
    seen: set[str] = set()
    for ln in answer_lines:
        opt = _paste_line_as_option(ln)
        key = opt.lower()
        if not opt or key in seen:
            continue
        seen.add(key)
        answers.append(opt)

    return question, answers


def _next_custom_metryczka_code(questions: List[Dict[str, Any]]) -> str:
    used: set[str] = set()
    for q in questions:
        if not isinstance(q, dict):
            continue
        used.add(str(q.get("db_column") or "").strip().upper())
        used.add(str(q.get("id") or "").strip().upper())
    i = 1
    while i < 1000:
        cand = f"M_CUSTOM_{i}"
        if cand not in used:
            return cand
        i += 1
    return f"M_CUSTOM_{int(time.time())}"


def _new_custom_metryczka_question(questions: List[Dict[str, Any]]) -> Dict[str, Any]:
    code = _next_custom_metryczka_code(questions)
    return {
        "id": code,
        "scope": "custom",
        "db_column": code,
        "_ui_key": f"q_{int(time.time() * 1_000_000)}",
        "prompt": "",
        "table_label": "",
        "variable_emoji": "📌",
        "required": True,
        "multiple": False,
        "randomize_options": False,
        "randomize_exclude_last": False,
        "aliases": [],
        "options": [
            {"label": "", "code": "1", "is_open": False, "lock_randomization": False, "value_emoji": ""},
            {"label": "", "code": "2", "is_open": False, "lock_randomization": False, "value_emoji": ""},
        ],
    }


def _unique_custom_metryczka_code(preferred: str, questions: List[Dict[str, Any]]) -> str:
    used: set[str] = set()
    for q in questions:
        if not isinstance(q, dict):
            continue
        used.add(str(q.get("db_column") or "").strip().upper())
        used.add(str(q.get("id") or "").strip().upper())
    pref = str(preferred or "").strip().upper()
    if _METRY_CUSTOM_CODE_RE.fullmatch(pref) and pref not in used:
        return pref
    if _METRY_CUSTOM_CODE_RE.fullmatch(pref):
        base = re.sub(r"_\d+$", "", pref)
        for i in range(2, 500):
            cand = f"{base}_{i}"
            if _METRY_CUSTOM_CODE_RE.fullmatch(cand) and cand not in used:
                return cand
    return _next_custom_metryczka_code(questions)


def _question_from_template_payload(template_q: Dict[str, Any], questions: List[Dict[str, Any]]) -> Dict[str, Any]:
    q_src = dict(template_q or {})
    desired_code = str(q_src.get("db_column") or q_src.get("id") or "").strip().upper()
    code = _unique_custom_metryczka_code(desired_code, questions)
    prompt = str(q_src.get("prompt") or "").strip()
    table_label = str(q_src.get("table_label") or prompt).strip()
    variable_emoji = str(q_src.get("variable_emoji") or guess_metry_variable_emoji(code, table_label, prompt)).strip()
    randomize_options = bool(q_src.get("randomize_options") is True)
    legacy_exclude_last = bool(q_src.get("randomize_exclude_last") is True)
    options_out: List[Dict[str, Any]] = []
    seen_codes: set[str] = set()
    for opt in list(q_src.get("options") or []):
        if not isinstance(opt, dict):
            continue
        label = str(opt.get("label") or "").strip()
        code_opt = str(opt.get("code") or label).strip()
        if not label or not code_opt:
            continue
        code_key = code_opt.upper()
        if code_key in seen_codes:
            continue
        seen_codes.add(code_key)
        options_out.append(
            {
                "label": label,
                "code": code_opt,
                "is_open": bool(opt.get("is_open") is True),
                "lock_randomization": bool(opt.get("lock_randomization") is True),
                "value_emoji": _option_value_emoji_or_guess(
                    opt,
                    table_label=table_label,
                    code=code_opt,
                    db_column=code,
                ),
            }
        )
    if len(options_out) < 2:
        options_out = [
            {"label": "", "code": "", "is_open": False, "lock_randomization": False, "value_emoji": ""},
            {"label": "", "code": "", "is_open": False, "lock_randomization": False, "value_emoji": ""},
        ]
    options_out = _metryczka_apply_legacy_exclude_last_lock(
        options_out,
        randomize_options=randomize_options,
        legacy_exclude_last=legacy_exclude_last,
    )
    return {
        "id": code,
        "scope": "custom",
        "db_column": code,
        "_ui_key": f"q_{int(time.time() * 1_000_000)}",
        "prompt": prompt,
        "table_label": table_label,
        "variable_emoji": variable_emoji,
        "required": True,
        "multiple": False,
        "randomize_options": randomize_options,
        "randomize_exclude_last": False,
        "aliases": [],
        "options": options_out,
    }


def _validate_metryczka_before_save(raw_cfg: Dict[str, Any]) -> Tuple[bool, str]:
    questions = raw_cfg.get("questions")
    if not isinstance(questions, list) or not questions:
        return False, "Metryczka nie zawiera pytań."

    seen_columns: set[str] = set()
    for idx, q in enumerate(questions, start=1):
        if not isinstance(q, dict):
            return False, f"Pytanie #{idx} ma nieprawidłowy format."

        scope = str(q.get("scope") or "").strip().lower()
        prompt = str(q.get("prompt") or "").strip()
        db_column = str(q.get("db_column") or "").strip().upper()
        options = q.get("options")

        if not prompt:
            return False, f"Pytanie #{idx}: uzupełnij treść pytania."
        if not db_column:
            return False, f"Pytanie #{idx}: uzupełnij pole 'Kodowanie'."
        if db_column in seen_columns:
            return False, f"Pole 'Kodowanie' musi być unikalne. Duplikat: {db_column}."
        seen_columns.add(db_column)

        if scope == "custom" and not _METRY_CUSTOM_CODE_RE.fullmatch(db_column):
            return False, (
                f"Pytanie #{idx}: kodowanie '{db_column}' ma zły format. "
                "Użyj np. M_POWIAT (duże litery, cyfry i podkreślenie)."
            )

        if not isinstance(options, list) or len(options) < 2:
            return False, f"Pytanie #{idx}: dodaj co najmniej 2 odpowiedzi."

        seen_option_codes: set[str] = set()
        for opt_idx, opt in enumerate(options, start=1):
            if not isinstance(opt, dict):
                return False, f"Pytanie #{idx}: odpowiedź #{opt_idx} ma nieprawidłowy format."
            label = str(opt.get("label") or "").strip()
            code = str(opt.get("code") or "").strip().upper()
            if not label:
                return False, f"Pytanie #{idx}: odpowiedź #{opt_idx} nie ma treści."
            if not code:
                return False, f"Pytanie #{idx}: odpowiedź #{opt_idx} nie ma kodowania."
            if code in seen_option_codes:
                return False, f"Pytanie #{idx}: zduplikowane kodowanie odpowiedzi '{code}'."
            seen_option_codes.add(code)

    return True, ""


def _metryczka_merge_question_from_template(
    *,
    kind: str,
    existing_question: Dict[str, Any],
    template_question: Dict[str, Any],
) -> Dict[str, Any]:
    q_existing = dict(existing_question or {})
    q_tpl = dict(template_question or {})
    db_column = str(q_existing.get("db_column") or q_existing.get("id") or "").strip().upper()
    prompt = str(q_tpl.get("prompt") or q_existing.get("prompt") or "").strip()
    table_label = str(q_tpl.get("table_label") or prompt or q_existing.get("table_label") or db_column).strip()
    variable_emoji = str(
        q_tpl.get("variable_emoji")
        or q_existing.get("variable_emoji")
        or guess_metry_variable_emoji(db_column, table_label, prompt)
    ).strip()
    randomize_options = bool(q_tpl.get("randomize_options") is True)
    options_new: List[Dict[str, Any]] = []
    seen_codes: set[str] = set()
    for opt in list(q_tpl.get("options") or []):
        if not isinstance(opt, dict):
            continue
        label = str(opt.get("label") or "").strip()
        code = str(opt.get("code") or label).strip()
        if not label:
            continue
        if not code:
            continue
        code_key = code.lower()
        if code_key in seen_codes:
            continue
        seen_codes.add(code_key)
        options_new.append(
            {
                "label": label,
                "code": code,
                "is_open": bool(opt.get("is_open") is True),
                "lock_randomization": bool(opt.get("lock_randomization") is True),
                "value_emoji": _option_value_emoji_or_guess(
                    opt,
                    table_label=table_label,
                    code=code,
                    db_column=db_column,
                ),
            }
        )
    if len(options_new) < 2:
        options_new = list(q_existing.get("options") or [])
    merged = dict(q_existing)
    merged["prompt"] = prompt
    merged["table_label"] = table_label
    merged["variable_emoji"] = variable_emoji
    merged["randomize_options"] = randomize_options
    merged["randomize_exclude_last"] = False
    merged["options"] = options_new
    return merged


def _apply_template_question_to_config(
    *,
    kind: str,
    config: Any,
    template_question: Dict[str, Any],
) -> Tuple[Dict[str, Any], int]:
    cfg = _metryczka_normalize_config(kind, config)
    target_code = str(template_question.get("db_column") or template_question.get("id") or "").strip().upper()
    if not target_code:
        return cfg, 0
    changed = 0
    new_questions: List[Dict[str, Any]] = []
    for q in list(cfg.get("questions") or []):
        if not isinstance(q, dict):
            continue
        q_code = str(q.get("db_column") or q.get("id") or "").strip().upper()
        if q_code != target_code:
            new_questions.append(q)
            continue
        merged = _metryczka_merge_question_from_template(
            kind=kind,
            existing_question=q,
            template_question=template_question,
        )
        if merged != q:
            changed += 1
        new_questions.append(merged)
    if changed <= 0:
        return cfg, 0
    out_cfg = {"version": int(cfg.get("version") or 1), "questions": new_questions}
    return _metryczka_normalize_config(kind, out_cfg), changed


def _propagate_template_question_globally(
    *,
    template_question: Dict[str, Any],
    kind_scope: str,
) -> Dict[str, int]:
    scope = str(kind_scope or "both").strip().lower()
    apply_jst = scope in {"jst", "both"}
    apply_personal = scope in {"personal", "both"}
    stats = {
        "jst_updated": 0,
        "jst_questions_updated": 0,
        "personal_updated": 0,
        "personal_questions_updated": 0,
        "errors": 0,
    }
    if apply_jst:
        try:
            jst_rows = fetch_jst_studies(sb, include_inactive=True)
        except Exception:
            jst_rows = fetch_jst_studies(sb)
        for row in jst_rows:
            sid = str(row.get("id") or "").strip()
            if not sid:
                continue
            try:
                cfg_new, changed_q = _apply_template_question_to_config(
                    kind="jst",
                    config=row.get("metryczka_config"),
                    template_question=template_question,
                )
                if changed_q <= 0:
                    continue
                update_jst_study(
                    sb,
                    sid,
                    {
                        "metryczka_config": cfg_new,
                        "metryczka_config_version": int(cfg_new.get("version") or 1),
                    },
                )
                stats["jst_updated"] += 1
                stats["jst_questions_updated"] += int(changed_q)
            except Exception:
                stats["errors"] += 1
    if apply_personal:
        try:
            personal_rows = (
                sb.table("studies")
                .select("*")
                .or_("is_active.is.true,is_active.is.false,is_active.is.null")
                .execute()
                .data
                or []
            )
        except Exception:
            personal_rows = fetch_studies(sb)
        for row in personal_rows:
            sid = str(row.get("id") or "").strip()
            if not sid:
                continue
            try:
                cfg_new, changed_q = _apply_template_question_to_config(
                    kind="personal",
                    config=row.get("metryczka_config"),
                    template_question=template_question,
                )
                if changed_q <= 0:
                    continue
                update_study(
                    sb,
                    sid,
                    {
                        "metryczka_config": cfg_new,
                        "metryczka_config_version": int(cfg_new.get("version") or 1),
                    },
                )
                stats["personal_updated"] += 1
                stats["personal_questions_updated"] += int(changed_q)
            except Exception:
                stats["errors"] += 1
    return stats


def _stable_json_repr(value: Any) -> str:
    try:
        return json.dumps(value if value is not None else {}, ensure_ascii=False, sort_keys=True)
    except Exception:
        return str(value)


def _fetch_rows_paged_raw(table_name: str, columns: str, *, batch_size: int = 500) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    start = 0
    while True:
        end = start + max(1, int(batch_size)) - 1
        res = sb.table(table_name).select(columns).range(start, end).execute()
        chunk = list(res.data or [])
        if not chunk:
            break
        out.extend([dict(r) for r in chunk if isinstance(r, dict)])
        if len(chunk) < batch_size:
            break
        start += batch_size
    return out


def _run_metryczka_backfill_once() -> None:
    done_key = "_metryczka_backfill_done_v2"
    if bool(st.session_state.get(done_key)):
        return
    stats = {"jst_updated": 0, "personal_updated": 0, "errors": 0}
    try:
        jst_rows = _fetch_rows_paged_raw("jst_studies", "id,metryczka_config")
        for row in jst_rows:
            sid = str(row.get("id") or "").strip()
            if not sid:
                continue
            raw_cfg = row.get("metryczka_config")
            norm_cfg = normalize_jst_metryczka_config(raw_cfg)
            if _stable_json_repr(raw_cfg) == _stable_json_repr(norm_cfg):
                continue
            try:
                update_jst_study(sb, sid, {"metryczka_config": norm_cfg})
                stats["jst_updated"] += 1
            except Exception:
                stats["errors"] += 1

        personal_rows = _fetch_rows_paged_raw("studies", "id,metryczka_config")
        for row in personal_rows:
            sid = str(row.get("id") or "").strip()
            if not sid:
                continue
            raw_cfg = row.get("metryczka_config")
            norm_cfg = normalize_personal_metryczka_config(raw_cfg)
            if _stable_json_repr(raw_cfg) == _stable_json_repr(norm_cfg):
                continue
            try:
                update_study(sb, sid, {"metryczka_config": norm_cfg})
                stats["personal_updated"] += 1
            except Exception:
                stats["errors"] += 1
    except Exception:
        stats["errors"] += 1
    st.session_state[done_key] = True
    st.session_state["_metryczka_backfill_stats_v2"] = stats


def _render_metryczka_editor(kind: str, study_key: str, current_cfg: Dict[str, Any]) -> Dict[str, Any]:
    state_key = _metryczka_editor_state_key(kind, study_key)
    scroll_target_key = _metryczka_scroll_target_key(kind, study_key)
    scroll_nonce_key = _metryczka_scroll_nonce_key(kind, study_key)
    widget_prefix = _metryczka_editor_widget_prefix(kind, study_key)
    normalized_cfg = _metryczka_normalize_config(kind, current_cfg)
    tpl_panel_key = f"{widget_prefix}tpl_panel_open"

    if state_key not in st.session_state:
        st.session_state[state_key] = deepcopy(normalized_cfg)

    r1, r2, r3 = st.columns([0.28, 0.28, 0.44], gap="small")
    with r1:
        if st.button("↩️ Odrzuć niezapisane zmiany", key=f"{widget_prefix}reset", use_container_width=True):
            st.session_state[state_key] = deepcopy(normalized_cfg)
            _bump_metryczka_editor_nonce(kind, study_key)
            st.rerun()
    with r2:
        if st.button("📚 Predefiniowane metryczki", key=f"{widget_prefix}open_tpl_panel_top", type="secondary", use_container_width=True):
            st.session_state[tpl_panel_key] = not bool(st.session_state.get(tpl_panel_key, False))
    with r3:
        st.caption(
            "Pierwsze 5 pytań to rdzeń metryczki (stałe kodowanie kolumn). "
            "Możesz edytować treść pytań i odpowiedzi oraz dodawać pytania dodatkowe."
        )

    cfg_state = st.session_state.get(state_key) or deepcopy(normalized_cfg)
    if bool(st.session_state.get(tpl_panel_key, False)):
        templates = list_metryczka_question_templates(sb, kind=kind)
        with st.container(border=True):
            st.markdown("**Predefiniowane metryczki (zapisane pytania)**")
            st.caption(
                "Zmiany zapisane tutaj są globalne: aktualizują wszystkie ankiety, które mają pytanie o tym samym kodowaniu."
            )
            if not templates:
                st.caption("Brak zapisanych pytań metryczkowych. Zapisz pierwsze pytanie przyciskiem „💾 Zapisz do zapisanych”.")
            else:
                tpl_options: Dict[str, Dict[str, Any]] = {}
                for tpl in templates:
                    name = str(tpl.get("name") or "").strip() or "bez nazwy"
                    kind_lbl = str(tpl.get("kind") or "").strip().lower()
                    if kind_lbl == "both":
                        kind_lbl = "jst + personal"
                    q_tpl = tpl.get("question") if isinstance(tpl.get("question"), dict) else {}
                    code = str(q_tpl.get("db_column") or "").strip().upper()
                    prompt = str(q_tpl.get("prompt") or "").strip()
                    answers_n = len(list(q_tpl.get("options") or []))
                    label = f"{name} ({code}, odp.: {answers_n}, zakres: {kind_lbl})"
                    if prompt:
                        label = f"{label} — {prompt[:80]}"
                    tpl_options[label] = tpl

                picked_label = st.selectbox(
                    "Zapisane pytanie",
                    list(tpl_options.keys()),
                    key=f"{widget_prefix}tpl_pick_top",
                    label_visibility="collapsed",
                )
                picked_tpl = tpl_options[picked_label]
                picked_kind = str(picked_tpl.get("kind") or "both").strip().lower() or "both"
                picked_q = picked_tpl.get("question") if isinstance(picked_tpl.get("question"), dict) else {}
                edit_name_key = f"{widget_prefix}tpl_edit_name_top"
                edit_prompt_key = f"{widget_prefix}tpl_edit_prompt_top"
                edit_table_label_key = f"{widget_prefix}tpl_edit_table_label_top"
                edit_code_key = f"{widget_prefix}tpl_edit_code_top"
                edit_var_icon_key = f"{widget_prefix}tpl_edit_var_icon_top"
                edit_rand_key = f"{widget_prefix}tpl_edit_rand_top"
                edit_loaded_key = f"{widget_prefix}tpl_edit_loaded_top"
                edit_opts_key = f"{widget_prefix}tpl_edit_opts_top"
                tpl_insert_pending_key = f"{widget_prefix}tpl_insert_pending_top"
                tpl_insert_conflict_code_key = f"{widget_prefix}tpl_insert_conflict_code_top"
                picked_id = str(picked_tpl.get("id") or "").strip()
                if st.session_state.get(edit_loaded_key) != picked_id:
                    st.session_state[edit_loaded_key] = picked_id
                    st.session_state[edit_name_key] = str(picked_tpl.get("name") or "").strip()
                    st.session_state[edit_prompt_key] = str(picked_q.get("prompt") or "").strip()
                    st.session_state[edit_table_label_key] = str(
                        picked_q.get("table_label") or picked_q.get("prompt") or ""
                    ).strip()
                    st.session_state[edit_code_key] = str(picked_q.get("db_column") or picked_q.get("id") or "").strip().upper()
                    st.session_state[edit_var_icon_key] = str(
                        picked_q.get("variable_emoji")
                        or guess_metry_variable_emoji(
                            st.session_state.get(edit_code_key),
                            st.session_state.get(edit_table_label_key),
                            st.session_state.get(edit_prompt_key),
                        )
                    ).strip()
                    st.session_state[edit_rand_key] = bool(picked_q.get("randomize_options") is True)
                    st.session_state[edit_opts_key] = _metryczka_options_to_df(
                        picked_q.get("options"),
                        randomize_options=bool(picked_q.get("randomize_options") is True),
                        legacy_exclude_last=bool(picked_q.get("randomize_exclude_last") is True),
                        table_label=str(st.session_state.get(edit_table_label_key) or ""),
                        db_column=str(st.session_state.get(edit_code_key) or ""),
                    )
                    st.session_state.pop(tpl_insert_pending_key, None)
                    st.session_state.pop(tpl_insert_conflict_code_key, None)

                st.text_input("Nazwa zapisanego pytania", key=edit_name_key, placeholder="np. M_OBSZAR")
                e1, e2 = st.columns([0.68, 0.32], gap="small")
                with e1:
                    st.text_area(
                        "Treść pytania",
                        key=edit_prompt_key,
                        height=74,
                        placeholder="Treść pytania widoczna dla respondenta",
                    )
                    st.text_input(
                        "Kodowanie do tabel",
                        key=edit_table_label_key,
                        placeholder="Krótka etykieta zmiennej do tabel demograficznych",
                    )
                with e2:
                    st.text_input("Kodowanie", key=edit_code_key, placeholder="np. M_POWIAT")
                    picked_var_icon = _metry_icon_picker(
                        label="Ikona zmiennej (z bazy)",
                        key_prefix=f"{widget_prefix}tpl_var_icon_top_{picked_id}",
                        value=st.session_state.get(edit_var_icon_key),
                        help_text="Ikona pokazywana przy nazwie zmiennej w tabelach demograficznych.",
                    )
                    st.session_state[edit_var_icon_key] = picked_var_icon
                    st.checkbox(
                        "Losowa kolejność odpowiedzi",
                        key=edit_rand_key,
                    )

                tpl_opts_df = st.session_state.get(edit_opts_key)
                if not isinstance(tpl_opts_df, pd.DataFrame):
                    tpl_opts_df = _metryczka_options_to_df(
                        [],
                        table_label=str(st.session_state.get(edit_table_label_key) or ""),
                        db_column=str(st.session_state.get(edit_code_key) or ""),
                    )
                tpl_opts_df = _metryczka_editor_df_clean(tpl_opts_df)
                move_key = f"{widget_prefix}tpl_move_idx_{picked_id}"
                move_idx = int(st.session_state.get(move_key, -1) or -1)
                tpl_editor_df = _metryczka_attach_move_marker(tpl_opts_df, move_idx)
                tpl_editor_widget_key = f"{edit_opts_key}_editor_{picked_id}"
                tpl_editor_df = st.data_editor(
                    tpl_editor_df,
                    height=_metryczka_data_editor_height(tpl_opts_df),
                    use_container_width=True,
                    hide_index=True,
                    num_rows="dynamic",
                    key=tpl_editor_widget_key,
                    column_config={
                        "Przesuń": st.column_config.CheckboxColumn(
                            "Przesuń",
                            help="Zaznacz jeden wiersz, aby przesunąć go w górę lub w dół.",
                            default=False,
                            width="small",
                        ),
                        "Odpowiedź": st.column_config.TextColumn(
                            "Odpowiedź",
                            help="Tekst widoczny dla respondenta.",
                            width="large",
                        ),
                        "Kodowanie": st.column_config.TextColumn(
                            "Kodowanie",
                            help="Kod zapisywany dla tej odpowiedzi.",
                            width="medium",
                        ),
                        "Otwarta": st.column_config.CheckboxColumn(
                            "Otwarta",
                            help="Po wyborze tej odpowiedzi respondent musi wpisać własną treść.",
                            default=False,
                            width="small",
                        ),
                        "Blokuj losowanie": st.column_config.CheckboxColumn(
                            "Blokuj losowanie",
                            help="Po zaznaczeniu odpowiedź zachowuje stałą pozycję przy randomizacji.",
                            default=False,
                            width="small",
                        ),
                        "Ikona": st.column_config.TextColumn(
                            "Ikona",
                            help="Wklej emoji (np. 🗳️) lub pozostaw puste, aby użyć automatycznej ikonki.",
                            width="small",
                        ),
                    },
                )
                # W praktyce st.data_editor bywa "o 1 rerun do tyłu" na wartości zwracanej.
                # Źródłem prawdy jest stan widgetu pod jego kluczem.
                tpl_editor_live = st.session_state.get(tpl_editor_widget_key, tpl_editor_df)
                tpl_opts_df, move_idx = _metryczka_extract_move_marker(tpl_editor_live)
                st.session_state[edit_opts_key] = tpl_opts_df
                st.session_state[move_key] = move_idx
                row_count = int(len(tpl_opts_df.index))
                if row_count > 0:
                    r1, r2 = st.columns([0.16, 0.16], gap="small")
                    with r1:
                        if st.button("↑ Do góry", key=f"{widget_prefix}tpl_move_up_{picked_id}", use_container_width=True):
                            idx_move = int(st.session_state.get(move_key, -1) or -1)
                            if idx_move > 0:
                                st.session_state[edit_opts_key] = _metryczka_reorder_df(tpl_opts_df, idx_move, -1)
                                st.session_state[move_key] = idx_move - 1
                                st.rerun()
                    with r2:
                        if st.button("↓ W dół", key=f"{widget_prefix}tpl_move_down_{picked_id}", use_container_width=True):
                            idx_move = int(st.session_state.get(move_key, -1) or -1)
                            if idx_move < row_count - 1:
                                st.session_state[edit_opts_key] = _metryczka_reorder_df(tpl_opts_df, idx_move, +1)
                                st.session_state[move_key] = idx_move + 1
                                st.rerun()
                    st.caption("Dodawanie/usuwanie odpowiedzi: bezpośrednio w tabeli. Przesuwanie: zaznacz checkbox „Przesuń”.")

                live_tpl_question = {
                    "id": str(st.session_state.get(edit_code_key) or "").strip().upper(),
                    "scope": "custom",
                    "db_column": str(st.session_state.get(edit_code_key) or "").strip().upper(),
                    "prompt": str(st.session_state.get(edit_prompt_key) or "").strip(),
                    "table_label": str(st.session_state.get(edit_table_label_key) or "").strip(),
                    "variable_emoji": str(st.session_state.get(edit_var_icon_key) or "").strip(),
                    "randomize_options": bool(st.session_state.get(edit_rand_key)),
                    "randomize_exclude_last": False,
                    "options": [
                        {
                            **opt,
                            "value_emoji": _option_value_emoji_or_guess(
                                opt,
                                table_label=str(st.session_state.get(edit_table_label_key) or ""),
                                code=str(opt.get("code") or opt.get("label") or ""),
                                db_column=str(st.session_state.get(edit_code_key) or ""),
                            ),
                        }
                        for opt in _metryczka_options_from_df(tpl_opts_df)
                    ],
                }
                st.caption(
                    f"Kodowanie pytania: {str(live_tpl_question.get('db_column') or '').strip().upper()} • "
                    f"Odpowiedzi: {len(list(live_tpl_question.get('options') or []))}"
                )
                t1, t2, t3 = st.columns([0.24, 0.24, 0.24], gap="small")
                with t1:
                    if st.button("💾 Zapisz zmiany", key=f"{widget_prefix}tpl_save_top", type="secondary", use_container_width=True):
                        try:
                            saved_tpl = save_metryczka_question_template(
                                sb,
                                name=str(st.session_state.get(edit_name_key) or "").strip(),
                                question=live_tpl_question,
                                kind=picked_kind if picked_kind in {"jst", "personal", "both"} else "both",
                            )
                            saved_tpl_question = (
                                saved_tpl.get("question")
                                if isinstance(saved_tpl, dict) and isinstance(saved_tpl.get("question"), dict)
                                else live_tpl_question
                            )
                            apply_kind = str(saved_tpl.get("kind") or picked_kind or "both").strip().lower()
                            apply_stats = _propagate_template_question_globally(
                                template_question=dict(saved_tpl_question or {}),
                                kind_scope=apply_kind,
                            )
                            # Natychmiast aktualizujemy też bieżący widok metryczki w tej sesji.
                            cfg_local_after, changed_local = _apply_template_question_to_config(
                                kind=kind,
                                config=st.session_state.get(state_key) or cfg_state,
                                template_question=dict(saved_tpl_question or {}),
                            )
                            if changed_local > 0:
                                st.session_state[state_key] = deepcopy(cfg_local_after)
                                _bump_metryczka_editor_nonce(kind, study_key)
                            st.session_state[edit_loaded_key] = str(saved_tpl.get("id") or "").strip()
                            st.success(
                                "Zapisano zmiany predefiniowanego pytania i zastosowano globalnie "
                                f"(JST: {int(apply_stats.get('jst_updated', 0))}, "
                                f"personalne: {int(apply_stats.get('personal_updated', 0))})."
                            )
                            if int(apply_stats.get("errors", 0)) > 0:
                                st.warning(
                                    f"Nie udało się zaktualizować części badań: {int(apply_stats.get('errors', 0))}."
                                )
                            st.rerun()
                        except Exception as e:
                            st.error(f"Nie udało się zapisać zmian: {e}")
                with t2:
                    if st.button("Wstaw pytanie", key=f"{widget_prefix}tpl_insert_top", type="primary", use_container_width=True):
                        working = deepcopy(st.session_state.get(state_key) or cfg_state)
                        q_list = list(working.get("questions") or [])
                        desired_code = str(
                            live_tpl_question.get("db_column") or live_tpl_question.get("id") or ""
                        ).strip().upper()
                        existing_codes: set[str] = set()
                        for q in q_list:
                            if not isinstance(q, dict):
                                continue
                            existing_codes.add(str(q.get("db_column") or "").strip().upper())
                            existing_codes.add(str(q.get("id") or "").strip().upper())
                        if desired_code and desired_code in existing_codes:
                            st.session_state[tpl_insert_pending_key] = deepcopy(live_tpl_question)
                            st.session_state[tpl_insert_conflict_code_key] = desired_code
                            st.rerun()
                        st.session_state.pop(tpl_insert_pending_key, None)
                        st.session_state.pop(tpl_insert_conflict_code_key, None)
                        new_q = _question_from_template_payload(live_tpl_question, q_list)
                        q_list.append(new_q)
                        working["questions"] = q_list
                        st.session_state[state_key] = working
                        st.session_state[scroll_target_key] = _metryczka_anchor_id(
                            kind, study_key, str(new_q.get("_ui_key") or "")
                        )
                        st.session_state[scroll_nonce_key] = int(time.time() * 1_000_000)
                        st.rerun()
                with t3:
                    if st.button("Zamknij", key=f"{widget_prefix}tpl_close_top", type="secondary", use_container_width=True):
                        st.session_state[tpl_panel_key] = False
                        st.session_state.pop(tpl_insert_pending_key, None)
                        st.session_state.pop(tpl_insert_conflict_code_key, None)
                        st.rerun()

                pending_tpl_insert = st.session_state.get(tpl_insert_pending_key)
                if isinstance(pending_tpl_insert, dict):
                    conflict_code = str(st.session_state.get(tpl_insert_conflict_code_key) or "").strip().upper()
                    st.warning("Masz już to pytanie w metryczce. Czy chcesz na pewno je wstawić?")
                    if conflict_code:
                        st.caption(f"Wykryte kodowanie: {conflict_code}")
                    c_yes, c_no = st.columns([0.14, 0.14], gap="small")
                    with c_yes:
                        if st.button("Tak", key=f"{widget_prefix}tpl_insert_confirm_yes_top", type="primary", use_container_width=True):
                            working = deepcopy(st.session_state.get(state_key) or cfg_state)
                            q_list = list(working.get("questions") or [])
                            new_q = _question_from_template_payload(pending_tpl_insert, q_list)
                            q_list.append(new_q)
                            working["questions"] = q_list
                            st.session_state[state_key] = working
                            st.session_state.pop(tpl_insert_pending_key, None)
                            st.session_state.pop(tpl_insert_conflict_code_key, None)
                            st.session_state[scroll_target_key] = _metryczka_anchor_id(
                                kind, study_key, str(new_q.get("_ui_key") or "")
                            )
                            st.session_state[scroll_nonce_key] = int(time.time() * 1_000_000)
                            st.rerun()
                    with c_no:
                        if st.button("Nie", key=f"{widget_prefix}tpl_insert_confirm_no_top", type="secondary", use_container_width=True):
                            st.session_state.pop(tpl_insert_pending_key, None)
                            st.session_state.pop(tpl_insert_conflict_code_key, None)
                            st.rerun()

    questions = list((cfg_state.get("questions") or []))
    rebuilt_questions: List[Dict[str, Any]] = []
    remove_idx: Optional[int] = None

    for idx, q in enumerate(questions, start=1):
        q_dict = dict(q or {})
        scope = str(q_dict.get("scope") or "custom").strip().lower()
        is_core = scope == "core"
        ui_key = str(q_dict.get("_ui_key") or f"q_{idx}_{str(q_dict.get('id') or '')}".strip())
        anchor_id = _metryczka_anchor_id(kind, study_key, ui_key)
        db_column = str(q_dict.get("db_column") or q_dict.get("id") or "").strip().upper()
        if is_core and db_column in _METRY_CORE_IDS:
            qid = db_column
        else:
            qid = str(q_dict.get("id") or db_column or f"M_CUSTOM_{idx}").strip().upper()
        prompt_default = str(q_dict.get("prompt") or "").strip()
        table_label_default = str(q_dict.get("table_label") or prompt_default).strip()
        variable_emoji_default = str(
            q_dict.get("variable_emoji")
            or guess_metry_variable_emoji(db_column, table_label_default, prompt_default)
        ).strip()
        options_default = q_dict.get("options") or []

        st.markdown(f"<div id='{anchor_id}'></div>", unsafe_allow_html=True)
        st.markdown("---")
        h1, h2 = st.columns([0.72, 0.28], gap="small")
        with h1:
            role_txt = "rdzeń" if is_core else "pytanie dodatkowe"
            st.markdown(f"**{idx}. {qid}**")
            st.caption(f"Typ: {role_txt}")
        with h2:
            if not is_core:
                if st.button("🗑️ Usuń pytanie", key=f"{widget_prefix}rm_q_{ui_key}", use_container_width=True):
                    remove_idx = idx - 1

        p_col, c_col = st.columns([0.72, 0.28], gap="small")
        with p_col:
            prompt = st.text_area(
                "Pytanie",
                value=prompt_default,
                key=f"{widget_prefix}prompt_{ui_key}",
                height=56,
                placeholder="Treść pytania widoczna dla respondenta",
            )
            table_label = st.text_input(
                "Kodowanie do tabel",
                value=table_label_default,
                key=f"{widget_prefix}table_label_{ui_key}",
                placeholder="Krótka etykieta zmiennej do tabel demograficznych",
            )
        with c_col:
            code_value = st.text_input(
                "Kodowanie",
                value=db_column,
                key=f"{widget_prefix}code_{ui_key}",
                disabled=is_core,
                placeholder="np. M_POWIAT",
            )
            variable_emoji = _metry_icon_picker(
                label="Ikona zmiennej (z bazy)",
                key_prefix=f"{widget_prefix}var_icon_{ui_key}",
                value=variable_emoji_default,
                help_text="Ikona pokazywana przy tej zmiennej w tabelach demograficznych.",
            )
            randomize_options_val = st.checkbox(
                "Losowa kolejność odpowiedzi",
                value=bool(q_dict.get("randomize_options") is True),
                key=f"{widget_prefix}randomize_{ui_key}",
            )
            if is_core:
                st.caption("Kodowanie rdzenia jest zgodne z historyczną bazą (tekst odpowiedzi).")

        st.markdown("**Odpowiedzi**")
        options_df_seed = _metryczka_options_to_df(
            options_default,
            randomize_options=bool(q_dict.get("randomize_options") is True),
            legacy_exclude_last=bool(q_dict.get("randomize_exclude_last") is True),
            table_label=table_label_default,
            db_column=db_column,
        )
        options_df_state_key = f"{widget_prefix}opts_df_state_{ui_key}"
        if options_df_state_key not in st.session_state:
            st.session_state[options_df_state_key] = _metryczka_editor_df_clean(options_df_seed)
        options_df = _metryczka_editor_df_clean(st.session_state.get(options_df_state_key))
        move_key = f"{widget_prefix}opts_move_idx_{ui_key}"
        move_idx = int(st.session_state.get(move_key, -1) or -1)
        options_editor_df = _metryczka_attach_move_marker(options_df, move_idx)
        options_editor_widget_key = f"{widget_prefix}opts_{ui_key}"
        options_editor_df = st.data_editor(
            options_editor_df,
            height=_metryczka_data_editor_height(options_df),
            use_container_width=True,
            hide_index=True,
            num_rows="dynamic",
            key=options_editor_widget_key,
            column_config={
                "Przesuń": st.column_config.CheckboxColumn(
                    "Przesuń",
                    help="Zaznacz jeden wiersz, aby przesunąć go w górę lub w dół.",
                    default=False,
                    width="small",
                ),
                "Odpowiedź": st.column_config.TextColumn(
                    "Odpowiedź",
                    help="Tekst widoczny dla respondenta.",
                    width="large",
                ),
                "Kodowanie": st.column_config.TextColumn(
                    "Kodowanie",
                    help="Kod zapisywany dla tej odpowiedzi.",
                    width="medium",
                ),
                "Otwarta": st.column_config.CheckboxColumn(
                    "Otwarta",
                    help="Po wyborze tej odpowiedzi respondent musi wpisać własną treść.",
                    default=False,
                    width="small",
                ),
                "Blokuj losowanie": st.column_config.CheckboxColumn(
                    "Blokuj losowanie",
                    help="Po zaznaczeniu odpowiedź zachowuje stałą pozycję przy randomizacji.",
                    default=False,
                    width="small",
                ),
                "Ikona": st.column_config.TextColumn(
                    "Ikona",
                    help="Wklej emoji (np. 🗳️) lub pozostaw puste, aby użyć automatycznej ikonki.",
                    width="small",
                ),
            },
        )
        # Odczytujemy "live" dane z session_state, żeby nie gubić pierwszej edycji komórki.
        options_editor_live = st.session_state.get(options_editor_widget_key, options_editor_df)
        edited_options_df, move_idx = _metryczka_extract_move_marker(options_editor_live)
        st.session_state[options_df_state_key] = edited_options_df
        st.session_state[move_key] = move_idx
        row_count = int(len(edited_options_df.index))
        if row_count > 0:
            r1, r2 = st.columns([0.16, 0.16], gap="small")
            with r1:
                if st.button("↑ Do góry", key=f"{widget_prefix}opts_move_up_{ui_key}", use_container_width=True):
                    idx_move = int(st.session_state.get(move_key, -1) or -1)
                    if idx_move > 0:
                        st.session_state[options_df_state_key] = _metryczka_reorder_df(edited_options_df, idx_move, -1)
                        st.session_state[move_key] = idx_move - 1
                        st.session_state[scroll_target_key] = anchor_id
                        st.session_state[scroll_nonce_key] = int(time.time() * 1_000_000)
                        st.rerun()
            with r2:
                if st.button("↓ W dół", key=f"{widget_prefix}opts_move_down_{ui_key}", use_container_width=True):
                    idx_move = int(st.session_state.get(move_key, -1) or -1)
                    if idx_move < row_count - 1:
                        st.session_state[options_df_state_key] = _metryczka_reorder_df(edited_options_df, idx_move, +1)
                        st.session_state[move_key] = idx_move + 1
                        st.session_state[scroll_target_key] = anchor_id
                        st.session_state[scroll_nonce_key] = int(time.time() * 1_000_000)
                        st.rerun()
            st.caption("Dodawanie/usuwanie odpowiedzi: bezpośrednio w tabeli. Przesuwanie: zaznacz checkbox „Przesuń”.")

        options = _metryczka_options_from_df(st.session_state.get(options_df_state_key))

        paste_toggle_key = f"{widget_prefix}paste_open_{ui_key}"
        paste_text_key = f"{widget_prefix}paste_text_{ui_key}"
        paste_clear_key = f"{widget_prefix}paste_clear_{ui_key}"
        existing_prompt = str(prompt or "").strip()
        existing_answers = [
            str(opt.get("label") or "").strip()
            for opt in options
            if str(opt.get("label") or "").strip()
        ]
        if bool(st.session_state.get(paste_clear_key, False)):
            st.session_state.pop(paste_text_key, None)
            st.session_state[paste_clear_key] = False
        if st.button(
            "📋 Wklej pytanie i odpowiedzi",
            key=f"{widget_prefix}paste_btn_{ui_key}",
            type="secondary",
        ):
            is_open = bool(st.session_state.get(paste_toggle_key, False))
            st.session_state[paste_toggle_key] = not is_open
            if is_open:
                st.session_state[paste_clear_key] = True
            else:
                seed_lines: List[str] = []
                if existing_prompt:
                    seed_lines.append(f"Pytanie: {existing_prompt}")
                if existing_answers:
                    seed_lines.append("Odpowiedzi:")
                    seed_lines.extend(existing_answers)
                st.session_state[paste_text_key] = "\n".join(seed_lines).strip()

        if bool(st.session_state.get(paste_toggle_key, False)):
            with st.container(border=True):
                st.markdown("**Wklej pytanie i odpowiedzi z innego źródła (np. Word/Excel)**")
                st.caption(
                    "Wklej treść, gdzie pierwsza część to pytanie, a kolejne linie to odpowiedzi. "
                    "Parser usuwa automatycznie numerację/bulety (np. 1., -, •)."
                )
                col_input, col_preview = st.columns([0.5, 0.5], gap="small")
                with col_input:
                    pasted_text = st.text_area(
                        "Wklej treść",
                        key=paste_text_key,
                        height=260,
                        placeholder=(
                            "Pytanie: Treść pytania...\n"
                            "Odpowiedzi:\n"
                            "Odpowiedź 1\n"
                            "Odpowiedź 2\n"
                            "Odpowiedź 3"
                        ),
                        label_visibility="collapsed",
                    )
                parsed_question, parsed_answers = _parse_pasted_question_and_answers(
                    pasted_text,
                    fallback_prompt=existing_prompt,
                )
                preview_question = parsed_question or existing_prompt
                preview_answers = parsed_answers if parsed_answers else existing_answers
                with col_preview:
                    st.markdown("**Podgląd**")
                    if preview_question:
                        st.markdown(f"**Treść pytania:** {preview_question}")
                    else:
                        st.markdown("**Treść pytania:** _(brak)_")
                    if preview_answers:
                        st.markdown("**Odpowiedzi:**")
                        answers_html = "".join(
                            f"<li style='margin:0.08rem 0;'>{html.escape(str(ans))}</li>"
                            for ans in preview_answers
                        )
                        st.markdown(
                            (
                                "<ul style='margin:0.12rem 0 0.04rem 1rem; padding-left:0.75rem; "
                                "line-height:1.14; list-style-position:outside; display:block;'>"
                                f"{answers_html}</ul>"
                            ),
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown("**Odpowiedzi:** _(brak)_")

                b1, b2 = st.columns([0.22, 0.22], gap="small")
                with b1:
                    if st.button(
                        "Wstaw",
                        key=f"{widget_prefix}paste_insert_{ui_key}",
                        disabled=len(parsed_answers) < 2,
                        type="primary",
                    ):
                        working = deepcopy(st.session_state.get(state_key) or cfg_state)
                        q_list = list(working.get("questions") or [])
                        for q_item in q_list:
                            if str(q_item.get("_ui_key") or "").strip() != ui_key:
                                continue
                            if parsed_question:
                                q_item["prompt"] = parsed_question
                            q_scope = str(q_item.get("scope") or "").strip().lower()
                            # Bazujemy na aktualnym stanie tabeli odpowiedzi z bieżącego przebiegu
                            # (a nie na historycznym q_item), aby nie gubić świeżo edytowanego kodowania.
                            existing_opts: List[Dict[str, str]] = []
                            for it in options:
                                if not isinstance(it, dict):
                                    continue
                                existing_opts.append(
                                    {
                                        "label": str(it.get("label") or "").strip(),
                                        "code": str(it.get("code") or "").strip(),
                                        "is_open": bool(it.get("is_open") is True),
                                        "lock_randomization": bool(it.get("lock_randomization") is True),
                                        "value_emoji": str(it.get("value_emoji") or "").strip(),
                                    }
                                )
                            if not existing_opts:
                                existing_opts_raw = q_item.get("options")
                                if isinstance(existing_opts_raw, list):
                                    for it in existing_opts_raw:
                                        if not isinstance(it, dict):
                                            continue
                                        existing_opts.append(
                                            {
                                                "label": str(it.get("label") or "").strip(),
                                                "code": str(it.get("code") or "").strip(),
                                                "is_open": bool(it.get("is_open") is True),
                                                "lock_randomization": bool(it.get("lock_randomization") is True),
                                                "value_emoji": str(it.get("value_emoji") or "").strip(),
                                            }
                                        )

                            old_codes_by_label: Dict[str, str] = {}
                            old_open_by_label: Dict[str, bool] = {}
                            old_lock_by_label: Dict[str, bool] = {}
                            old_icon_by_label: Dict[str, str] = {}
                            old_icon_has_by_label: Dict[str, bool] = {}
                            for opt in existing_opts:
                                old_label = str(opt.get("label") or "").strip().lower()
                                old_code = str(opt.get("code") or "").strip()
                                if old_label and old_code and old_label not in old_codes_by_label:
                                    old_codes_by_label[old_label] = old_code
                                if old_label and old_label not in old_open_by_label:
                                    old_open_by_label[old_label] = bool(opt.get("is_open") is True)
                                if old_label and old_label not in old_lock_by_label:
                                    old_lock_by_label[old_label] = bool(opt.get("lock_randomization") is True)
                                if old_label and old_label not in old_icon_by_label:
                                    old_icon_by_label[old_label] = str(opt.get("value_emoji") or "").strip()
                                    old_icon_has_by_label[old_label] = ("value_emoji" in opt)

                            new_options: List[Dict[str, Any]] = []
                            for i, ans in enumerate(parsed_answers):
                                if q_scope == "core":
                                    ans_key = str(ans).strip().lower()
                                    code_core = str(old_codes_by_label.get(ans_key) or "").strip() or ans
                                    has_icon_core = bool(old_icon_has_by_label.get(ans_key, False))
                                    icon_core = str(old_icon_by_label.get(ans_key, "") or "").strip()
                                    if not has_icon_core:
                                        icon_core = guess_metry_value_emoji(
                                            str(q_item.get("table_label") or q_item.get("prompt") or ""),
                                            code_core,
                                            str(q_item.get("db_column") or ""),
                                        )
                                    new_options.append(
                                        {
                                            "label": ans,
                                            "code": code_core,
                                            "is_open": bool(old_open_by_label.get(ans_key, False)),
                                            "lock_randomization": bool(old_lock_by_label.get(ans_key, False)),
                                            "value_emoji": str(icon_core or "").strip(),
                                        }
                                    )
                                    continue
                                code_existing = old_codes_by_label.get(str(ans).strip().lower(), "")
                                open_existing = bool(old_open_by_label.get(str(ans).strip().lower(), False))
                                lock_existing = bool(old_lock_by_label.get(str(ans).strip().lower(), False))
                                icon_existing = str(old_icon_by_label.get(str(ans).strip().lower(), "") or "").strip()
                                has_icon_existing = bool(old_icon_has_by_label.get(str(ans).strip().lower(), False))
                                if (not code_existing) and i < len(existing_opts):
                                    idx_code = str(existing_opts[i].get("code") or "").strip()
                                    idx_label = str(existing_opts[i].get("label") or "").strip().lower()
                                    if idx_code and idx_label and idx_label == str(ans).strip().lower():
                                        code_existing = idx_code
                                        open_existing = bool(existing_opts[i].get("is_open") is True)
                                        lock_existing = bool(existing_opts[i].get("lock_randomization") is True)
                                        icon_existing = str(existing_opts[i].get("value_emoji") or "").strip()
                                        has_icon_existing = ("value_emoji" in existing_opts[i])
                                # Wklejka ma aktualizować treść pytania/odpowiedzi, nie narzucać nowych kodowań.
                                if not code_existing:
                                    # Propozycja domyślna: kodowanie = treść odpowiedzi (edytowalne przez użytkownika).
                                    code_existing = ans
                                if not has_icon_existing:
                                    icon_existing = guess_metry_value_emoji(
                                        str(q_item.get("table_label") or q_item.get("prompt") or ""),
                                        code_existing,
                                        str(q_item.get("db_column") or ""),
                                    )
                                new_options.append(
                                    {
                                        "label": ans,
                                        "code": code_existing,
                                        "is_open": open_existing,
                                        "lock_randomization": lock_existing,
                                        "value_emoji": icon_existing,
                                    }
                                )
                            q_item["options"] = new_options
                            st.session_state[options_df_state_key] = _metryczka_editor_df_clean(
                                _metryczka_options_to_df(
                                    new_options,
                                    randomize_options=bool(q_item.get("randomize_options") is True),
                                    legacy_exclude_last=bool(q_item.get("randomize_exclude_last") is True),
                                    table_label=str(q_item.get("table_label") or q_item.get("prompt") or ""),
                                    db_column=str(q_item.get("db_column") or ""),
                                )
                            )
                            break
                        working["questions"] = q_list
                        st.session_state[state_key] = working
                        st.session_state[paste_toggle_key] = False
                        st.session_state[paste_clear_key] = True
                        st.session_state[scroll_target_key] = anchor_id
                        st.session_state[scroll_nonce_key] = int(time.time() * 1_000_000)
                        st.rerun()
                with b2:
                    if st.button(
                        "Anuluj",
                        key=f"{widget_prefix}paste_cancel_{ui_key}",
                        type="secondary",
                    ):
                        st.session_state[paste_toggle_key] = False
                        st.session_state[paste_clear_key] = True
                        st.session_state[scroll_target_key] = anchor_id
                        st.session_state[scroll_nonce_key] = int(time.time() * 1_000_000)
                        st.rerun()

        if not is_core:
            template_name_key = f"{widget_prefix}tpl_name_{ui_key}"
            if template_name_key not in st.session_state:
                st.session_state[template_name_key] = str(db_column or qid or "").strip().upper()
            tcol1, tcol2 = st.columns([0.64, 0.36], gap="small")
            with tcol1:
                tpl_name = st.text_input(
                    "Nazwa zapisanego pytania",
                    key=template_name_key,
                    placeholder="np. M_OBSZAR",
                )
            with tcol2:
                st.markdown("<div style='height:1.6rem;'></div>", unsafe_allow_html=True)
                if st.button("💾 Zapisz do zapisanych", key=f"{widget_prefix}save_tpl_{ui_key}", use_container_width=True):
                    try:
                        code_for_template = str(code_value or "").strip().upper()
                        template_question = {
                            "id": code_for_template,
                            "scope": "custom",
                            "db_column": code_for_template,
                            "prompt": str(prompt or "").strip(),
                            "table_label": str(table_label or prompt or "").strip(),
                            "variable_emoji": str(variable_emoji or "").strip(),
                            "randomize_options": bool(randomize_options_val),
                            "randomize_exclude_last": False,
                            "options": [
                                {
                                    "label": str(opt.get("label") or "").strip(),
                                    "code": str(opt.get("code") or "").strip(),
                                    "is_open": bool(opt.get("is_open") is True),
                                    "lock_randomization": bool(opt.get("lock_randomization") is True),
                                    "value_emoji": _option_value_emoji_or_guess(
                                        opt,
                                        table_label=str(table_label or prompt or ""),
                                        code=str(opt.get("code") or opt.get("label") or ""),
                                        db_column=code_for_template,
                                    ),
                                }
                                for opt in options
                                if isinstance(opt, dict)
                            ],
                        }
                        saved_tpl = save_metryczka_question_template(
                            sb,
                            name=str(tpl_name or code_for_template).strip(),
                            question=template_question,
                            kind="both",
                        )
                        saved_name = str(saved_tpl.get("name") or tpl_name or code_for_template).strip()
                        st.success(f"Zapisano pytanie w bibliotece: {saved_name}")
                    except Exception as e:
                        st.error(f"Nie udało się zapisać pytania w bibliotece: {e}")
                st.caption("Zapis lokalnych zmian w metryczce następuje dopiero po kliknięciu „💾 Zapisz metryczkę”.")

        final_code = str(code_value or "").strip().upper()
        if is_core:
            final_code = db_column
        final_id = final_code if not is_core else qid
        rebuilt_questions.append(
            {
                "id": final_id,
                "scope": "core" if is_core else "custom",
                "db_column": final_code,
                "_ui_key": ui_key,
                "prompt": str(prompt or "").strip(),
                "table_label": str(table_label or prompt or "").strip(),
                "variable_emoji": str(
                    variable_emoji or guess_metry_variable_emoji(final_code, str(table_label or prompt or ""), str(prompt or ""))
                ).strip(),
                "required": True,
                "multiple": False,
                "randomize_options": bool(randomize_options_val),
                "randomize_exclude_last": False,
                "aliases": list(q_dict.get("aliases") or []),
                "options": [
                    {
                        **dict(opt),
                        "value_emoji": _option_value_emoji_or_guess(
                            dict(opt),
                            table_label=str(table_label or prompt or ""),
                            code=str(opt.get("code") or opt.get("label") or ""),
                            db_column=final_code,
                        ),
                    }
                    for opt in options
                    if isinstance(opt, dict)
                ],
            }
        )

    cfg_out = {
        "version": int(cfg_state.get("version") or 1),
        "questions": rebuilt_questions,
    }
    st.session_state[state_key] = deepcopy(cfg_out)

    if remove_idx is not None:
        working = deepcopy(st.session_state[state_key])
        q_list = list(working.get("questions") or [])
        if 0 <= remove_idx < len(q_list):
            q_list.pop(remove_idx)
            working["questions"] = q_list
            st.session_state[state_key] = working
            st.rerun()

    st.markdown("<div style='height:0.55rem;'></div>", unsafe_allow_html=True)
    controls_col1, controls_col2 = st.columns([0.25, 0.75], gap="small")
    with controls_col1:
        if st.button("➕ Dodaj puste pytanie", key=f"{widget_prefix}add_q", type="secondary", use_container_width=True):
            working = deepcopy(st.session_state.get(state_key) or cfg_out)
            q_list = list(working.get("questions") or [])
            new_q = _new_custom_metryczka_question(q_list)
            q_list.append(new_q)
            working["questions"] = q_list
            st.session_state[state_key] = working
            st.session_state[scroll_target_key] = _metryczka_anchor_id(
                kind, study_key, str(new_q.get("_ui_key") or "")
            )
            st.session_state[scroll_nonce_key] = int(time.time() * 1_000_000)
            st.rerun()
    with controls_col2:
        quick_tpls = list_metryczka_question_templates(sb, kind=kind)
        if quick_tpls:
            tpl_map: Dict[str, Dict[str, Any]] = {}
            for tpl in quick_tpls:
                q_tpl = tpl.get("question") if isinstance(tpl.get("question"), dict) else {}
                name = str(tpl.get("name") or "").strip() or "bez nazwy"
                code = str(q_tpl.get("db_column") or "").strip().upper()
                prompt = str(q_tpl.get("prompt") or "").strip()
                label = f"{name} ({code})"
                if prompt:
                    label = f"{label} — {prompt[:72]}"
                tpl_map[label] = tpl
            ins_key = f"{widget_prefix}quick_tpl_pick"
            c2a, c2b = st.columns([0.72, 0.28], gap="small")
            with c2a:
                picked_lbl = st.selectbox(
                    "Wstaw z zapisanych",
                    options=list(tpl_map.keys()),
                    key=ins_key,
                    label_visibility="collapsed",
                )
            with c2b:
                if st.button("📥 Wstaw z zapisanych", key=f"{widget_prefix}quick_tpl_insert", use_container_width=True):
                    tpl_rec = tpl_map.get(str(picked_lbl or ""))
                    tpl_q = tpl_rec.get("question") if isinstance(tpl_rec, dict) and isinstance(tpl_rec.get("question"), dict) else {}
                    if tpl_q:
                        working = deepcopy(st.session_state.get(state_key) or cfg_out)
                        q_list = list(working.get("questions") or [])
                        new_q = _question_from_template_payload(tpl_q, q_list)
                        q_list.append(new_q)
                        working["questions"] = q_list
                        st.session_state[state_key] = working
                        st.session_state[scroll_target_key] = _metryczka_anchor_id(
                            kind, study_key, str(new_q.get("_ui_key") or "")
                        )
                        st.session_state[scroll_nonce_key] = int(time.time() * 1_000_000)
                        st.rerun()
        else:
            st.caption("Brak zapisanych pytań do szybkiego wstawienia.")

    q_list_live = list((st.session_state.get(state_key) or cfg_out).get("questions") or [])
    custom_positions = [
        i for i, q in enumerate(q_list_live)
        if isinstance(q, dict) and str(q.get("scope") or "").strip().lower() != "core"
    ]
    if len(custom_positions) >= 2:
        with st.expander("↕️ Zmień kolejność pytań metryczkowych", expanded=False):
            ord_key = f"{widget_prefix}q_order_pick"
            labels = [
                f"{int(pos)+1}. {str(q_list_live[pos].get('db_column') or q_list_live[pos].get('id') or '').strip()}"
                for pos in custom_positions
            ]
            chosen_ord = st.selectbox(
                "Wybierz pytanie do przesunięcia",
                options=list(range(len(custom_positions))),
                key=ord_key,
                format_func=lambda i: labels[int(i)],
            )
            o1, o2 = st.columns([0.16, 0.16], gap="small")
            with o1:
                if st.button("↑ Do góry", key=f"{widget_prefix}q_order_up", use_container_width=True):
                    sel = int(chosen_ord or 0)
                    if sel > 0:
                        src_idx = custom_positions[sel]
                        dst_idx = custom_positions[sel - 1]
                        q_work = list(q_list_live)
                        q_work[src_idx], q_work[dst_idx] = q_work[dst_idx], q_work[src_idx]
                        st.session_state[state_key] = {
                            "version": int((st.session_state.get(state_key) or cfg_out).get("version") or 1),
                            "questions": q_work,
                        }
                        moved_ui = str(q_work[dst_idx].get("_ui_key") or "")
                        if moved_ui:
                            st.session_state[scroll_target_key] = _metryczka_anchor_id(kind, study_key, moved_ui)
                            st.session_state[scroll_nonce_key] = int(time.time() * 1_000_000)
                        st.rerun()
            with o2:
                if st.button("↓ W dół", key=f"{widget_prefix}q_order_down", use_container_width=True):
                    sel = int(chosen_ord or 0)
                    if sel < len(custom_positions) - 1:
                        src_idx = custom_positions[sel]
                        dst_idx = custom_positions[sel + 1]
                        q_work = list(q_list_live)
                        q_work[src_idx], q_work[dst_idx] = q_work[dst_idx], q_work[src_idx]
                        st.session_state[state_key] = {
                            "version": int((st.session_state.get(state_key) or cfg_out).get("version") or 1),
                            "questions": q_work,
                        }
                        moved_ui = str(q_work[dst_idx].get("_ui_key") or "")
                        if moved_ui:
                            st.session_state[scroll_target_key] = _metryczka_anchor_id(kind, study_key, moved_ui)
                            st.session_state[scroll_nonce_key] = int(time.time() * 1_000_000)
                        st.rerun()

    scroll_target = str(st.session_state.pop(scroll_target_key, "") or "").strip()
    scroll_nonce = int(st.session_state.pop(scroll_nonce_key, 0) or 0)
    if scroll_target:
        if scroll_nonce <= 0:
            scroll_nonce = int(time.time() * 1_000_000)
        html_component(
            f"""
            <script>
            (function(){{
              const id = {json.dumps(scroll_target)};
              const runId = {json.dumps(str(scroll_nonce))};
              if (!runId) return;

              const findTarget = () => {{
                let win = window;
                let hops = 0;
                while (win && hops < 6) {{
                  try {{
                    const doc = win.document;
                    const el = doc ? doc.getElementById(id) : null;
                    if (el) return {{ win, el }};
                  }} catch (e) {{}}
                  try {{
                    if (!win.parent || win.parent === win) break;
                    win = win.parent;
                    hops += 1;
                  }} catch (e) {{
                    break;
                  }}
                }}
                return null;
              }};

              const scrollToTarget = () => {{
                const found = findTarget();
                if (!found) return false;
                const hostWin = found.win;
                const el = found.el;
                const doc = hostWin.document;
                const scrollingTargets = [
                  doc.scrollingElement,
                  doc.documentElement,
                  doc.body,
                  doc.querySelector('section.main'),
                  doc.querySelector('[data-testid="stAppViewContainer"]'),
                  doc.querySelector('.block-container')?.parentElement
                ].filter(Boolean);
                try {{
                  const rect = el.getBoundingClientRect();
                  const top = Math.max(0, rect.top + hostWin.pageYOffset - Math.round(hostWin.innerHeight * 0.22));
                  hostWin.scrollTo({{ top, behavior: 'auto' }});
                  for (const tgt of scrollingTargets) {{
                    try {{
                      if (tgt === doc.body || tgt === doc.documentElement || tgt === doc.scrollingElement) {{
                        continue;
                      }}
                      const tRect = tgt.getBoundingClientRect();
                      const relTop = (rect.top - tRect.top) + (tgt.scrollTop || 0) - 24;
                      if (typeof tgt.scrollTo === 'function') tgt.scrollTo({{ top: Math.max(0, relTop), behavior: 'auto' }});
                      else tgt.scrollTop = Math.max(0, relTop);
                    }} catch (e) {{}}
                  }}
                }} catch (e) {{
                  try {{ el.scrollIntoView({{ behavior: 'auto', block: 'center' }}); }} catch (e2) {{}}
                }}
                try {{
                  const hashTarget = `#${{id}}`;
                  if (hostWin.location.hash === hashTarget) {{
                    hostWin.location.hash = '';
                  }}
                  hostWin.location.hash = hashTarget;
                }} catch (e) {{}}
                return true;
              }};

              let tries = 0;
              const timer = setInterval(() => {{
                tries += 1;
                if (scrollToTarget() || tries > 40) {{
                  clearInterval(timer);
                }}
              }}, 75);
            }})();
            </script>
            """,
            height=1,
        )
        st.markdown(
            f"""
            <script>
            (function(){{
              const id = {json.dumps(scroll_target)};
              const runId = {json.dumps(str(scroll_nonce))};
              if (!runId) return;

              const scrollLocal = () => {{
                const el = document.getElementById(id);
                if (!el) return false;
                try {{
                  const rect = el.getBoundingClientRect();
                  const top = Math.max(0, rect.top + window.pageYOffset - Math.round(window.innerHeight * 0.22));
                  window.scrollTo({{ top, behavior: 'auto' }});
                  const extra = [
                    document.querySelector('section.main'),
                    document.querySelector('[data-testid="stAppViewContainer"]'),
                    document.querySelector('.block-container')?.parentElement
                  ].filter(Boolean);
                  for (const tgt of extra) {{
                    try {{
                      const tRect = tgt.getBoundingClientRect();
                      const relTop = (rect.top - tRect.top) + (tgt.scrollTop || 0) - 24;
                      if (typeof tgt.scrollTo === 'function') tgt.scrollTo({{ top: Math.max(0, relTop), behavior: 'auto' }});
                      else tgt.scrollTop = Math.max(0, relTop);
                    }} catch (e) {{}}
                  }}
                }} catch (e) {{
                  try {{ el.scrollIntoView({{ behavior: 'auto', block: 'center' }}); }} catch (e2) {{}}
                }}
                try {{
                  const hashTarget = `#${{id}}`;
                  if (window.location.hash === hashTarget) window.location.hash = '';
                  window.location.hash = hashTarget;
                }} catch (e) {{}}
                return true;
              }};

              let tries = 0;
              const timer = setInterval(() => {{
                tries += 1;
                if (scrollLocal() || tries > 40) clearInterval(timer);
              }}, 75);
            }})();
            </script>
            """,
            unsafe_allow_html=True,
        )

    return deepcopy(st.session_state.get(state_key) or cfg_out)


def jst_metryczka_view() -> None:
    require_auth()
    if not _require_jst_ready():
        return
    header("🧾 Metryczka ankiety")
    render_titlebar(["Panel", "Badania mieszkańców", "Metryczka"])
    back_button("home_jst", "← Powrót do panelu mieszkańców")
    st.markdown('<div class="section-gap-big"></div>', unsafe_allow_html=True)

    studies = fetch_jst_studies(sb)
    if not studies:
        st.info("Brak badań JST w bazie.")
        return

    counts_by_id = fetch_jst_response_counts(sb)
    options: Dict[str, Dict[str, Any]] = {}
    for s in studies:
        sid = str(s.get("id") or "").strip()
        if not sid:
            continue
        options[f"{_jst_option_label(s)} • {int(counts_by_id.get(sid, 0))} odp."] = s

    st.markdown(
        "<div style='font-size:17px;font-weight:800;margin-bottom:6px;'>Wybierz badanie</div>",
        unsafe_allow_html=True,
    )
    choice = st.selectbox(
        "Wybierz badanie JST",
        list(options.keys()),
        key="jst_metryczka_pick",
        label_visibility="collapsed",
    )
    study = options[choice]
    sid = str(study.get("id") or "").strip()
    study_row = fetch_jst_study_by_id(sb, sid) or study
    study_row = _apply_scheduled_survey_transitions(study_row, kind="jst")
    status_meta = _study_status_meta(study_row, kind="jst")
    slug = str(study_row.get("slug") or "").strip()
    survey_base = str(st.secrets.get("JST_SURVEY_BASE_URL", "https://jst.badania.pro") or "").rstrip("/")
    survey_url = f"{survey_base}/{slug}" if slug else "—"

    info_df = pd.DataFrame(
        [
            {
                "Status": status_meta["status_label"],
                "Liczba odpowiedzi": int(counts_by_id.get(sid, 0)),
                "Link ankiety": survey_url,
            }
        ]
    )
    st.dataframe(info_df, use_container_width=True, hide_index=True)

    st.markdown('<div class="section-gap-big"></div>', unsafe_allow_html=True)
    st.markdown("### Konfiguracja metryczki")
    edited_cfg = _render_metryczka_editor(
        "jst",
        sid,
        normalize_jst_metryczka_config(study_row.get("metryczka_config")),
    )

    _, save_col = st.columns([0.66, 0.34], gap="small")
    with save_col:
        save_clicked = st.button(
            "💾 Zapisz metryczkę",
            type="primary",
            key=f"jst_metryczka_save_{sid}",
            use_container_width=True,
        )
    if save_clicked:
        valid, msg = _validate_metryczka_before_save(edited_cfg)
        if not valid:
            st.error(msg)
        else:
            cfg_norm = normalize_jst_metryczka_config(edited_cfg)
            try:
                update_jst_study(
                    sb,
                    sid,
                    {
                        "metryczka_config": cfg_norm,
                        "metryczka_config_version": int(cfg_norm.get("version") or 1),
                    },
                )
                st.session_state[_metryczka_editor_state_key("jst", sid)] = deepcopy(cfg_norm)
                st.success("Zapisano konfigurację metryczki.")
                st.rerun()
            except Exception as exc:
                st.error(f"Nie udało się zapisać metryczki: {exc}")


def jst_settings_view() -> None:
    require_auth()
    if not _require_jst_ready():
        return
    header("⚙️ Ustawienia ankiety")
    render_titlebar(["Panel", "Badania mieszkańców", "Ustawienia ankiety"])
    back_button("home_jst", "← Powrót do panelu mieszkańców")
    st.markdown('<div class="section-gap-big"></div>', unsafe_allow_html=True)

    studies = fetch_jst_studies(sb)
    if not studies:
        st.info("Brak badań JST w bazie.")
        return

    counts_by_id = fetch_jst_response_counts(sb)
    options: Dict[str, Dict[str, Any]] = {}
    for s in studies:
        sid = str(s.get("id") or "").strip()
        if not sid:
            continue
        jst_label = _jst_option_label(s)
        count = int(counts_by_id.get(sid, 0))
        options[f"{jst_label} • {count} odp."] = s

    st.markdown("<div style='font-size:17px;font-weight:800;margin-bottom:6px;'>Wybierz badanie</div>", unsafe_allow_html=True)
    choice = st.selectbox(
        "Wybierz badanie",
        list(options.keys()),
        key="jst_settings_pick",
        label_visibility="collapsed",
    )
    study = options[choice]
    sid = str(study.get("id") or "").strip()
    study_row = fetch_jst_study_by_id(sb, sid) or study
    study_row = _apply_scheduled_survey_transitions(study_row, kind="jst")
    status_meta = _study_status_meta(study_row, kind="jst")
    slug = str(study_row.get("slug") or "").strip()
    survey_base = str(st.secrets.get("JST_SURVEY_BASE_URL", "https://jst.badania.pro") or "").rstrip("/")
    survey_url = f"{survey_base}/{slug}" if slug else "—"
    save_flash_key = f"jst_settings_saved_flash_{sid}"
    flash_msg = st.session_state.pop(save_flash_key, None)
    if flash_msg:
        _toast_success_compat(str(flash_msg))

    info_rows = pd.DataFrame(
        [
            {
                "Status": status_meta["status_label"],
                "Liczba odpowiedzi": int(counts_by_id.get(sid, 0)),
                "Data uruchomienia": status_meta["started_at"],
                "Ostatnia zmiana statusu": status_meta["status_changed_at"],
                "Link ankiety": survey_url,
            }
        ]
    )
    st.dataframe(info_rows, use_container_width=True, hide_index=True)

    st.markdown('<div class="section-gap-big"></div>', unsafe_allow_html=True)
    st.markdown("### Parametry ankiety")
    cfg = _extract_survey_settings(study_row, allow_single=False)

    st.markdown("#### Nawigacja ankiety")
    show_progress = st.checkbox(
        "Pokaż pasek postępu",
        value=bool(cfg.get("show_progress")),
        key=f"jst_settings_progress_{sid}",
    )
    allow_back = st.checkbox(
        "Wyświetlaj przycisk Wstecz",
        value=bool(cfg.get("allow_back")),
        key=f"jst_settings_back_{sid}",
    )

    st.markdown("#### Powiadomienia")
    notify_on_response = st.checkbox(
        "Wysyłaj powiadomienie po uzyskaniu odpowiedzi",
        value=bool(cfg.get("notify_on_response")),
        key=f"jst_settings_notify_enabled_{sid}",
    )
    notify_email = st.text_input(
        "Adres e-mail do powiadomień",
        value=str(cfg.get("notify_email") or ""),
        key=f"jst_settings_notify_email_{sid}",
        disabled=not notify_on_response,
        placeholder="np. imie.nazwisko@domena.pl",
    )

    st.markdown("#### Automatyczny start i zakończenie badania")
    start_def_date, start_def_time = _utc_to_warsaw_input_defaults(
        cfg.get("auto_start_at"), fallback_hour=0, fallback_minute=0
    )
    end_def_date, end_def_time = _utc_to_warsaw_input_defaults(
        cfg.get("auto_end_at"), fallback_hour=23, fallback_minute=59
    )

    start_enabled = st.checkbox(
        "Aktywuj ankietę wybranego dnia",
        value=bool(cfg.get("auto_start_enabled")),
        key=f"jst_settings_auto_start_enabled_{sid}",
    )
    jst_scol1, jst_scol2 = st.columns([1, 1], gap="small")
    with jst_scol1:
        start_date = st.date_input(
            "Data startu JST",
            value=start_def_date,
            key=f"jst_settings_auto_start_date_{sid}",
            disabled=not start_enabled,
            label_visibility="collapsed",
        )
    with jst_scol2:
        start_time = st.time_input(
            "Godzina startu JST",
            value=start_def_time,
            key=f"jst_settings_auto_start_time_{sid}",
            disabled=not start_enabled,
            label_visibility="collapsed",
        )

    end_enabled = st.checkbox(
        "Zakończ ankietę wybranego dnia",
        value=bool(cfg.get("auto_end_enabled")),
        key=f"jst_settings_auto_end_enabled_{sid}",
    )
    jst_ecol1, jst_ecol2 = st.columns([1, 1], gap="small")
    with jst_ecol1:
        end_date = st.date_input(
            "Data zakończenia JST",
            value=end_def_date,
            key=f"jst_settings_auto_end_date_{sid}",
            disabled=not end_enabled,
            label_visibility="collapsed",
        )
    with jst_ecol2:
        end_time = st.time_input(
            "Godzina zakończenia JST",
            value=end_def_time,
            key=f"jst_settings_auto_end_time_{sid}",
            disabled=not end_enabled,
            label_visibility="collapsed",
        )

    if st.button("💾 Zapisz parametry ankiety", type="primary", key=f"jst_settings_save_params_{sid}"):
        notify_email_clean = str(notify_email or "").strip().lower()
        notify_email_valid = _normalize_notify_email(notify_email_clean)
        if notify_on_response and not notify_email_valid:
            st.error("Podaj poprawny adres e-mail do powiadomień.")
            return

        start_iso = _local_date_time_to_utc_iso(start_date, start_time) if start_enabled else None
        end_iso = _local_date_time_to_utc_iso(end_date, end_time) if end_enabled else None
        if start_enabled and not start_iso:
            st.error("Nie udało się odczytać daty/godziny startu ankiety.")
            return
        if end_enabled and not end_iso:
            st.error("Nie udało się odczytać daty/godziny zakończenia ankiety.")
            return
        start_dt = _parse_utc_dt(start_iso)
        end_dt = _parse_utc_dt(end_iso)
        if start_enabled and end_enabled and start_dt and end_dt and start_dt >= end_dt:
            st.error("Data i godzina zakończenia muszą być późniejsze niż data i godzina startu.")
            return

        updates: Dict[str, Any] = {
            "survey_show_progress": bool(show_progress),
            "survey_allow_back": bool(allow_back),
            "survey_auto_start_enabled": bool(start_enabled),
            "survey_auto_start_at": start_iso if start_enabled else None,
            "survey_auto_end_enabled": bool(end_enabled),
            "survey_auto_end_at": end_iso if end_enabled else None,
            "survey_notify_on_response": bool(notify_on_response),
            "survey_notify_email": notify_email_clean or None,
        }
        previous_notify_enabled = bool(cfg.get("notify_on_response"))
        previous_notify_email = _normalize_notify_email(cfg.get("notify_email"))
        current_count = int(counts_by_id.get(sid, 0))
        if not notify_on_response:
            updates["survey_notify_last_count"] = current_count
        elif (not previous_notify_enabled) or (notify_email_valid != previous_notify_email):
            updates["survey_notify_last_count"] = current_count
            updates["survey_notify_last_sent_at"] = None

        if (bool(start_enabled) != bool(cfg.get("auto_start_enabled"))) or (
            bool(start_enabled) and str(start_iso or "") != str(cfg.get("auto_start_at") or "")
        ):
            updates["survey_auto_start_applied_at"] = None
        if not start_enabled:
            updates["survey_auto_start_applied_at"] = None
        if (bool(end_enabled) != bool(cfg.get("auto_end_enabled"))) or (
            bool(end_enabled) and str(end_iso or "") != str(cfg.get("auto_end_at") or "")
        ):
            updates["survey_auto_end_applied_at"] = None
        if not end_enabled:
            updates["survey_auto_end_applied_at"] = None

        preview_study = dict(study_row)
        preview_study.update(updates)
        updates.update(_scheduled_survey_transition_updates(preview_study, kind="jst"))
        try:
            update_jst_study(sb, sid, updates)
            st.session_state[save_flash_key] = "Zapisano parametry ankiety."
            st.rerun()
        except Exception as exc:
            st.error(f"Nie udało się zapisać parametrów ankiety: {exc}")

    def _do_suspend_jst() -> None:
        try:
            set_jst_study_status(sb, sid, "suspended")
            st.success("Badanie zostało zawieszone.")
            st.rerun()
        except Exception as exc:
            st.error(f"Nie udało się zawiesić badania: {exc}")

    def _do_unsuspend_jst() -> None:
        try:
            set_jst_study_status(sb, sid, "active")
            st.success("Badanie zostało odwieszone.")
            st.rerun()
        except Exception as exc:
            st.error(f"Nie udało się odwiesić badania: {exc}")

    def _do_close_jst() -> None:
        try:
            set_jst_study_status(sb, sid, "closed")
            st.success("Badanie zostało zamknięte na stałe.")
            st.rerun()
        except Exception as exc:
            st.error(f"Nie udało się zamknąć badania: {exc}")

    def _do_delete_jst() -> None:
        try:
            soft_delete_jst_study(sb, sid)
            st.success("Badanie zostało usunięte.")
            goto("home_jst")
        except Exception as exc:
            st.error(f"Błąd usuwania: {exc}")

    _render_study_status_panel(
        kind="jst",
        study=study_row,
        on_suspend=_do_suspend_jst,
        on_unsuspend=_do_unsuspend_jst,
        on_close=_do_close_jst,
        on_delete=_do_delete_jst,
        close_confirm_key=f"jst_settings_close_confirm_{sid}",
        delete_confirm_key=f"jst_settings_delete_confirm_{sid}",
    )


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
                        norm = jst_normalize_response_row(
                            raw,
                            respondent_id_fallback=rid,
                            metryczka_config=study.get("metryczka_config"),
                        )
                        if not norm.get("respondent_id"):
                            norm["respondent_id"] = rid

                        if norm["respondent_id"] in existing_ids:
                            skipped += 1
                        else:
                            ok = insert_jst_response(
                                sb,
                                study_id=study_id,
                                respondent_id=str(norm["respondent_id"]),
                                payload=jst_make_payload_from_row(norm, metryczka_config=study.get("metryczka_config")),
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
    out_df = jst_response_rows_to_dataframe(rows, metryczka_config=study.get("metryczka_config"))
    slug = str(study.get("slug") or "jst")
    safe_name = slugify(str(study.get("jst_full_nom") or slug)) or slug

    c1, c2 = st.columns(2)
    with c1:
        _download_button_compat(
            "Pobierz CSV",
            data=out_df.to_csv(index=False, encoding="utf-8-sig"),
            file_name=f"baza-odpowiedzi-{safe_name}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with c2:
        _download_button_compat(
            "Pobierz XLSX",
            data=_xlsx_bytes_from_df(out_df, sheet_name="Odpowiedzi"),
            file_name=f"baza-odpowiedzi-{safe_name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

    st.markdown("#### Podgląd odpowiedzi")
    preview_df = out_df.copy()
    if "respondent_id" not in preview_df.columns:
        fallback_ids = [str(r.get("respondent_id") or "").strip() for r in rows]
        if len(fallback_ids) != len(preview_df.index):
            fallback_ids = [f"R{idx:04d}" for idx in range(1, len(preview_df.index) + 1)]
        preview_df.insert(0, "respondent_id", fallback_ids)
    preview_df.insert(0, "Usuń", False)

    selected_ids: List[str] = []
    editor_key = f"jst_io_editor_{study_id}"
    try:
        edited_df = st.data_editor(
            preview_df,
            use_container_width=True,
            hide_index=True,
            height=420,
            key=editor_key,
            disabled=[col for col in preview_df.columns if col != "Usuń"],
            column_config={
                "Usuń": st.column_config.CheckboxColumn(
                    "Usuń",
                    help="Zaznacz rekordy do usunięcia z bazy.",
                    default=False,
                )
            },
        )
        if isinstance(edited_df, pd.DataFrame):
            sel_series = edited_df.loc[edited_df["Usuń"] == True, "respondent_id"]  # noqa: E712
            selected_ids = [str(v).strip() for v in sel_series.tolist() if str(v).strip()]
    except Exception:
        st.dataframe(out_df, use_container_width=True, hide_index=True, height=420)
        options = [str(v).strip() for v in out_df.get("respondent_id", pd.Series(dtype=str)).tolist() if str(v).strip()]
        selected_ids = st.multiselect(
            "Wybierz respondentów do usunięcia",
            options=options,
            key=f"jst_io_delete_multiselect_{study_id}",
        )

    selected_unique = sorted(set(selected_ids))
    delete_confirm_key = f"jst_io_delete_confirm_{study_id}"
    delete_ids_key = f"jst_io_delete_ids_{study_id}"

    a1, a2, _sp = st.columns([0.28, 0.20, 0.52], gap="small")
    with a1:
        if st.button(
            "🗑️ Usuń zaznaczone",
            key=f"jst_io_delete_btn_{study_id}",
            use_container_width=True,
        ):
            if not selected_unique:
                st.warning("Zaznacz co najmniej jeden rekord do usunięcia.")
            else:
                st.session_state[delete_ids_key] = selected_unique
                st.session_state[delete_confirm_key] = True
                st.rerun()
    with a2:
        st.caption(f"Zaznaczone: {len(selected_unique)}")

    pending_delete_ids = [str(v).strip() for v in st.session_state.get(delete_ids_key, []) if str(v).strip()]
    if st.session_state.get(delete_confirm_key, False):
        if not pending_delete_ids:
            st.session_state.pop(delete_confirm_key, None)
            st.session_state.pop(delete_ids_key, None)
        else:
            st.warning(
                f"Czy na pewno usunąć zaznaczone rekordy? ({len(pending_delete_ids)}). "
                "Tej operacji nie można cofnąć."
            )
            d1, d2, _dsp = st.columns([0.26, 0.16, 0.58], gap="small")
            with d1:
                if st.button(
                    "✅ Tak, usuń zaznaczone",
                    key=f"jst_io_delete_yes_{study_id}",
                    use_container_width=True,
                ):
                    try:
                        removed = delete_jst_responses_by_respondent_ids(sb, study_id, pending_delete_ids)
                        st.session_state.pop(delete_confirm_key, None)
                        st.session_state.pop(delete_ids_key, None)
                        st.success(f"Usunięto {removed} rekordów.")
                        st.rerun()
                    except Exception as exc:
                        st.session_state.pop(delete_confirm_key, None)
                        st.session_state.pop(delete_ids_key, None)
                        st.error(f"Nie udało się usunąć zaznaczonych rekordów: {exc}")
            with d2:
                if st.button(
                    "↩️ Anuluj",
                    key=f"jst_io_delete_no_{study_id}",
                    use_container_width=True,
                ):
                    st.session_state.pop(delete_confirm_key, None)
                    st.session_state.pop(delete_ids_key, None)
                    st.rerun()


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


def _normalize_archetype_label_mode(raw: Any) -> str:
    txt = str(raw or "").strip().lower()
    if txt.startswith("wart"):
        return "values"
    if "żeń" in txt or "fem" in txt:
        return "female"
    return "male"


def _apply_archetype_label_mode_to_html(html_text: str, mode_choice: Any) -> str:
    source = str(html_text or "")
    if not source:
        return source
    mode = _normalize_archetype_label_mode(mode_choice)
    if mode == "male":
        return source

    if mode == "female":
        base_map: Dict[str, str] = dict(_MATCHING_FEMININE_MAP)
    else:
        base_map = {str(k): str(v) for k, v in JST_VALUE_BY_ARCH.items()}
    if not base_map:
        return source

    variant_map: Dict[str, str] = {}
    for src, dst in base_map.items():
        s = str(src)
        d = str(dst)
        variant_map[s] = d
        variant_map[s.upper()] = d.upper()
        variant_map[s.lower()] = d.lower()

    keys = sorted(variant_map.keys(), key=len, reverse=True)
    boundary = r"(?<![\wĄąĆćĘęŁłŃńÓóŚśŹźŻż])({})(?![\wĄąĆćĘęŁłŃńÓóŚśŹźŻż])"
    pattern = re.compile(boundary.format("|".join(re.escape(k) for k in keys)))
    return pattern.sub(lambda m: variant_map.get(m.group(1), m.group(1)), source)


def _fmt_bytes_compact(size_bytes: int) -> str:
    n = max(0, int(size_bytes or 0))
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024.0:.1f} KB"
    return f"{n / (1024.0 * 1024.0):.1f} MB"


_SEGMENT_HIT_THRESHOLD_DEFAULTS: Dict[str, float] = {
    "0 z 2 · #2": 4.0,
    "0 z 2 · #3": 4.0,
    "1 z 1 · #1": 3.0,
    "1 z 2 · #2": 3.0,
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
    src = (text or "").strip()
    if not src:
        return {}

    # Użytkownicy często wklejają „smart quotes” albo format listy `klucz: wartość`.
    normalized = (
        src.replace("\u201e", '"')
        .replace("\u201d", '"')
        .replace("\u201c", '"')
        .replace("\u2019", "'")
        .replace("\xa0", " ")
    )

    try:
        raw = json.loads(normalized)
        if not isinstance(raw, dict):
            raise ValueError("Wpisz poprawny JSON obiektowy (np. {\"2 z 2 · #1\": 3.94}).")
        return _normalize_segment_threshold_overrides(raw)
    except Exception:
        pass

    # Fallback: format linia-po-linii:
    # 0 z 2 · #2: 4.0
    # "0 z 2 · #3": 4.0,
    # 1 z 4 · #4 = 2.1
    parsed: Dict[str, float] = {}
    bad_lines: List[str] = []
    for raw_line in normalized.splitlines():
        line = (raw_line or "").strip().rstrip(",")
        if not line or line in {"{", "}"}:
            continue
        m = re.match(r'^\s*"?([^"]+?)"?\s*[:=]\s*([-+]?\d+(?:[.,]\d+)?)\s*$', line)
        if not m:
            bad_lines.append(line)
            continue
        key = str(m.group(1) or "").strip()
        if not key:
            bad_lines.append(line)
            continue
        try:
            value = float(str(m.group(2) or "").replace(",", "."))
        except Exception:
            bad_lines.append(line)
            continue
        parsed[key] = value

    if bad_lines:
        example = bad_lines[0]
        raise ValueError(
            "Nie udało się odczytać części linii. Użyj formatu `\"segment\": liczba` lub `segment: liczba`. "
            f"Przykładowa problematyczna linia: {example}"
        )
    if not parsed:
        raise ValueError("Nie wykryto żadnych progów. Wklej JSON lub listę linii `segment: wartość`.")

    return _normalize_segment_threshold_overrides(parsed)


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
    preview_inline_key = f"jst_report_inline_preview_v1_{sid}"
    preview_inline_meta_key = f"jst_report_inline_preview_meta_v1_{sid}"
    inline_limit = int(st.secrets.get("JST_REPORT_INLINE_LIMIT_BYTES", 45_000_000) or 45_000_000)
    inline_source_limit = int(st.secrets.get("JST_REPORT_INLINE_SOURCE_LIMIT_BYTES", 70_000_000) or 70_000_000)
    try:
        max_message_mb = float(st_config.get_option("server.maxMessageSize") or 200.0)
    except Exception:
        max_message_mb = 200.0
    max_message_bytes = int(max(1.0, max_message_mb) * 1024 * 1024)
    safe_limit_default = int(max(64_000_000, max_message_bytes * 0.88))
    safe_message_limit = int(st.secrets.get("JST_REPORT_SAFE_MESSAGE_LIMIT_BYTES", safe_limit_default) or safe_limit_default)
    safe_message_limit = int(min(safe_message_limit, max(32_000_000, int(max_message_bytes * 0.94))))
    hard_limit_cfg = int(st.secrets.get("JST_REPORT_PANEL_HARD_LIMIT_BYTES", 0) or 0)
    panel_hard_limit = int(min(max(40_000_000, int(max_message_bytes * 0.98)), max(hard_limit_cfg, safe_message_limit)))
    standalone_html_limit = int(
        st.secrets.get("JST_REPORT_STANDALONE_HTML_LIMIT_BYTES", 85_000_000) or 85_000_000
    )

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

    label_mode_choice = st.radio(
        "Wybierz formę archetypów",
        ["Archetypy męskie", "Archetypy żeńskie", "Wartości"],
        horizontal=True,
        key=f"jst_report_label_mode_{sid}",
    )

    overrides_editor_key = f"jst_segment_threshold_editor_{sid}"
    overrides_editor_pending_key = f"{overrides_editor_key}__pending_value"
    overrides_editor_notice_key = f"{overrides_editor_key}__notice"
    saved_overrides = _load_segment_threshold_overrides(template_root, run_base, sid, study or {})
    if overrides_editor_pending_key in st.session_state:
        st.session_state[overrides_editor_key] = str(st.session_state.pop(overrides_editor_pending_key) or "{}")
    if overrides_editor_key not in st.session_state:
        st.session_state[overrides_editor_key] = json.dumps(saved_overrides, ensure_ascii=False, indent=2)

    with st.expander("⚙️ segment_hit_threshold_overrides", expanded=False):
        notice = st.session_state.pop(overrides_editor_notice_key, "")
        if notice == "saved":
            st.success("Zapisano progi segmentów dla tego badania.")
        elif notice == "reset":
            st.success("Przywrócono domyślne progi segmentów.")
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
                    st.session_state[overrides_editor_pending_key] = json.dumps(parsed, ensure_ascii=False, indent=2)
                    st.session_state[overrides_editor_notice_key] = "saved"
                    st.rerun()
                except Exception as e:
                    st.error(f"Niepoprawny JSON progów: {e}")
        with cset2:
            if st.button("↩ Przywróć domyślne", key=f"reset_segment_overrides_{sid}", use_container_width=True):
                reset_text = json.dumps(_SEGMENT_HIT_THRESHOLD_DEFAULTS, ensure_ascii=False, indent=2)
                st.session_state[overrides_editor_pending_key] = reset_text
                _save_segment_threshold_overrides(run_base, sid, dict(_SEGMENT_HIT_THRESHOLD_DEFAULTS))
                st.session_state[overrides_editor_notice_key] = "reset"
                st.rerun()

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
        out_df = jst_response_rows_to_dataframe(rows, metryczka_config=(study or {}).get("metryczka_config"))
        study_for_report = dict(study or {})
        study_for_report["segment_hit_threshold_overrides"] = active_overrides
        with st.spinner("Generujemy raport dla tego badania. Prosimy o chwilę cierpliwości."):
            try:
                report_path = generate_jst_report(
                    template_root=template_root,
                    run_base_dir=run_base,
                    study=study_for_report,
                    data_df=out_df.copy(),
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
                    "panel_hard_limit": panel_hard_limit,
                    "standalone_html_limit": standalone_html_limit,
                }
                st.session_state.pop(preview_inline_key, None)
                st.session_state.pop(preview_inline_meta_key, None)
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
    if not (report_path and report_path.exists()):
        fallback_candidates = [
            run_base / sid / "WYNIKI" / "raport.html",
            template_root / "WYNIKI" / "raport.html",
        ]
        for cand in fallback_candidates:
            if cand.exists():
                report_path = cand
                break
    raw_bytes = int(meta.get("raw_bytes") or 0)
    inlined_bytes = int(meta.get("inlined_bytes") or 0)
    inlined_used = bool(meta.get("inlined_used"))
    safe_limit = int(meta.get("safe_message_limit") or safe_message_limit)
    hard_limit = int(meta.get("panel_hard_limit") or panel_hard_limit)
    standalone_limit = int(meta.get("standalone_html_limit") or standalone_html_limit)
    raw_report_for_preview = ""

    if report_path and report_path.exists():
        report_slug = slugify(str((study or {}).get("jst_full_nom") or (study or {}).get("slug") or "raport-jst")) or "raport-jst"
        raw_report = _apply_archetype_label_mode_to_html(
            report_path.read_text(encoding="utf-8", errors="ignore"),
            label_mode_choice,
        )
        raw_report_for_preview = raw_report
        full_report = ""
        full_report_bytes = 0
        full_report_error = ""
        full_report_available = False
        # Nie osadzamy ponownie całego raportu przy każdym rerunie: to potrafi mocno wydłużyć UI.
        if rendered and rendered != "__report_path_only__" and inlined_used:
            full_report = _apply_archetype_label_mode_to_html(str(rendered), label_mode_choice)
            full_report_bytes = len(full_report.encode("utf-8", errors="ignore"))
            full_report_available = bool(full_report and full_report_bytes <= standalone_limit)
            if not full_report_available:
                full_report_error = (
                    "Samodzielny HTML byłby zbyt ciężki "
                    f"({_fmt_bytes_compact(full_report_bytes)} > {_fmt_bytes_compact(standalone_limit)})."
                )
        else:
            src_bytes = len(raw_report.encode("utf-8", errors="ignore"))
            if src_bytes > int(meta.get("inline_source_limit") or inline_source_limit):
                full_report_error = (
                    "Raport źródłowy jest zbyt duży, aby bezpiecznie przygotować samodzielny plik HTML."
                )
            else:
                full_report_error = (
                    "Pełny HTML nie jest aktualnie zcache’owany w panelu. "
                    "Użyj ZIP (WYNIKI) albo wygeneruj raport ponownie i pobierz od razu."
                )
        report_zip = bundle_report_dir_zip(report_path.parent)
        d1, d2 = st.columns(2)
        with d1:
            _download_button_compat(
                "📥 Pobierz raport HTML (pełny)",
                data=(full_report or ""),
                file_name=f"{report_slug}.html",
                mime="text/html",
                use_container_width=True,
                disabled=not full_report_available,
                help=(
                    "Jednoplikowy HTML z osadzonymi zasobami (działa samodzielnie offline)."
                    if full_report_available
                    else "Dla tego raportu zalecana jest paczka ZIP (stabilniejsza i lżejsza)."
                ),
            )
        with d2:
            if report_zip:
                _download_button_compat(
                    "🧳 Pobierz raport ZIP (WYNIKI)",
                    data=report_zip,
                    file_name=f"{report_slug}-WYNIKI.zip",
                    mime="application/zip",
                    use_container_width=True,
                )
            else:
                st.caption("Nie udało się przygotować paczki ZIP raportu.")
        if full_report_available:
            st.caption(
                "HTML (pełny) jest samowystarczalny: wszystkie obrazy, style i skrypty są osadzone w jednym pliku."
            )
        elif full_report_error:
            st.info(
                f"To nie jest błąd generowania raportu. {full_report_error} "
                "Pobierz paczkę ZIP (WYNIKI) i otwórz lokalnie plik `raport.html` z tego folderu."
            )
    else:
        report_slug = slugify(str((study or {}).get("jst_full_nom") or (study or {}).get("slug") or "raport-jst")) or "raport-jst"
        cached_html = ""
        if isinstance(rendered, str) and rendered not in {"", "__report_path_only__", "__inline_error__"}:
            cached_html = _apply_archetype_label_mode_to_html(rendered, label_mode_choice)
        st.warning(
            "Raport został policzony, ale panel nie odnalazł pliku `raport.html` w katalogu runa. "
            "Najczęściej pomaga kliknięcie „Przelicz od nowa”."
        )
        if cached_html:
            _download_button_compat(
                "📥 Pobierz raport HTML (z cache panelu)",
                data=cached_html,
                file_name=f"{report_slug}.html",
                mime="text/html",
                use_container_width=True,
            )
            st.caption("Ten plik HTML pochodzi z cache panelu; paczka ZIP wymaga poprawnego pliku runa.")
        else:
            st.info("Brak cache HTML do pobrania. Kliknij „Przelicz od nowa”.")

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
    force_heavy_preview = False
    to_render = ""
    if light_mode:
        if report_path and report_path.exists():
            to_render = raw_report_for_preview or report_path.read_text(encoding="utf-8", errors="ignore")
            st.info("Tryb lekki jest włączony. Raport renderuje się szybciej i stabilniej przy dużych danych.")
        elif rendered and rendered != "__report_path_only__":
            to_render = str(rendered)
        else:
            st.error("Nie udało się odnaleźć pliku raportu do podglądu.")
            return
    else:
        if rendered and rendered != "__report_path_only__" and inlined_used:
            to_render = str(rendered)
        else:
            cached_inline = st.session_state.get(preview_inline_key)
            cached_meta = st.session_state.get(preview_inline_meta_key) or {}
            if cached_inline is None:
                if not (report_path and report_path.exists()):
                    st.error("Nie udało się odnaleźć pliku raportu do podglądu.")
                    return
                source_html = raw_report_for_preview or report_path.read_text(encoding="utf-8", errors="ignore")
                with st.spinner("Przygotowujemy pełny podgląd (osadzanie obrazów i zasobów)..."):
                    try:
                        inlined_preview = inline_local_assets(source_html, report_path.parent)
                        inlined_preview_bytes = len(inlined_preview.encode("utf-8", errors="ignore"))
                        if inlined_preview_bytes <= safe_limit:
                            st.session_state[preview_inline_key] = inlined_preview
                            st.session_state[preview_inline_meta_key] = {
                                "status": "ok",
                                "bytes": inlined_preview_bytes,
                                "error": "",
                            }
                        else:
                            st.session_state[preview_inline_key] = inlined_preview
                            st.session_state[preview_inline_meta_key] = {
                                "status": "too_large",
                                "bytes": inlined_preview_bytes,
                                "error": "",
                            }
                    except Exception as ex:
                        st.session_state[preview_inline_key] = "__inline_error__"
                        st.session_state[preview_inline_meta_key] = {
                            "status": "error",
                            "bytes": 0,
                            "error": str(ex),
                        }
                cached_inline = st.session_state.get(preview_inline_key)
                cached_meta = st.session_state.get(preview_inline_meta_key) or {}

            status = str(cached_meta.get("status") or "")
            if isinstance(cached_inline, str) and status == "ok" and cached_inline not in {"__too_large__", "__inline_error__"}:
                to_render = cached_inline
            elif status == "too_large":
                sz = _fmt_bytes_compact(int(cached_meta.get("bytes") or 0))
                lim = _fmt_bytes_compact(safe_limit)
                hlim = _fmt_bytes_compact(hard_limit)
                if int(cached_meta.get("bytes") or 0) > hard_limit:
                    st.error(
                        "Pełny podgląd przekracza techniczny limit panelu: "
                        f"{sz} > {hlim}."
                    )
                    st.info("Włącz „Tryb lekki renderowania” albo pobierz raport ZIP (WYNIKI) i otwórz lokalnie.")
                    return
                st.warning(
                    "Pełny podgląd jest duży dla panelu, ale możesz go uruchomić: "
                    f"{sz} (zalecany bezpieczny limit: {lim})."
                )
                force_heavy_preview = st.toggle(
                    "Pokaż pełny podgląd mimo dużego rozmiaru",
                    value=True,
                    key=f"jst_force_heavy_preview_{sid}",
                )
                if force_heavy_preview and isinstance(cached_inline, str) and cached_inline:
                    to_render = cached_inline
                    st.info("Uruchomiono pełny podgląd. Jeśli panel zwolni, przełącz na tryb lekki.")
                else:
                    st.info("Włącz „Tryb lekki renderowania” albo pobierz raport ZIP (WYNIKI) i otwórz lokalnie.")
                    return
            else:
                err = str(cached_meta.get("error") or "").strip()
                st.error("Nie udało się osadzić zasobów pełnego podglądu w panelu.")
                if err:
                    st.caption(f"Szczegóły techniczne: {err}")
                st.info("Włącz „Tryb lekki renderowania” albo pobierz raport ZIP (WYNIKI) i otwórz lokalnie.")
                return

    to_render = _apply_archetype_label_mode_to_html(to_render, label_mode_choice)
    render_size = len(to_render.encode("utf-8", errors="ignore"))
    if render_size > hard_limit:
        st.error(
            f"Podgląd raportu przekracza techniczny limit panelu ({_fmt_bytes_compact(render_size)} > {_fmt_bytes_compact(hard_limit)})."
        )
        st.info("Użyj trybu lekkiego albo pobierz raport ZIP (WYNIKI) i otwórz lokalnie.")
        return
    if render_size > safe_limit and not force_heavy_preview:
        st.error(
            "Podgląd raportu w panelu został wyłączony, bo przekracza bezpieczny limit przesyłania danych do przeglądarki."
        )
        st.info("Włącz tryb lekki albo użyj trybu wymuszonego przy pełnym podglądzie.")
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
JST_D_ITEMS: List[Tuple[str, str]] = [
    ("D1", "Władca"),
    ("D2", "Bohater"),
    ("D3", "Mędrzec"),
    ("D4", "Opiekun"),
    ("D5", "Kochanek"),
    ("D6", "Błazen"),
    ("D7", "Twórca"),
    ("D8", "Odkrywca"),
    ("D9", "Czarodziej"),
    ("D10", "Towarzysz"),
    ("D11", "Niewinny"),
    ("D12", "Buntownik"),
]
JST_D_BY_ARCH: Dict[str, str] = {arch: qid for qid, arch in JST_D_ITEMS}
JST_VALUE_BY_ARCH: Dict[str, str] = {
    "Buntownik": "Odnowa",
    "Błazen": "Otwartość",
    "Kochanek": "Relacje",
    "Opiekun": "Troska",
    "Towarzysz": "Współpraca",
    "Niewinny": "Przejrzystość",
    "Władca": "Skuteczność",
    "Mędrzec": "Racjonalność",
    "Czarodziej": "Wizja",
    "Bohater": "Odwaga",
    "Twórca": "Rozwój",
    "Odkrywca": "Wolność",
}
JST_ARCH_BY_KEY: Dict[str, str] = {}
for _idx, _arch in enumerate(JST_ARCHETYPES):
    _k = str(_arch or "").strip()
    if _k:
        JST_ARCH_BY_KEY[_k.casefold()] = _arch
    JST_ARCH_BY_KEY[str(_idx + 1)] = _arch
    JST_ARCH_BY_KEY[str(_idx)] = _arch
del _idx
del _arch
del _k


def compute_top3_share(hit_weight_by_archetype: Dict[str, float], answered_weight: float) -> Dict[str, float]:
    return {
        a: (100.0 * float(hit_weight_by_archetype.get(a, 0.0)) / float(answered_weight)) if float(answered_weight) > 0 else float("nan")
        for a in JST_ARCHETYPES
    }


def compute_top1_share(hit_weight_by_archetype: Dict[str, float], answered_weight: float) -> Dict[str, float]:
    return {
        a: (100.0 * float(hit_weight_by_archetype.get(a, 0.0)) / float(answered_weight)) if float(answered_weight) > 0 else float("nan")
        for a in JST_ARCHETYPES
    }


def compute_negative_experience_share(neg_weight_by_archetype: Dict[str, float], answered_weight_by_archetype: Dict[str, float]) -> Dict[str, float]:
    return {
        a: (
            100.0 * float(neg_weight_by_archetype.get(a, 0.0)) / float(answered_weight_by_archetype.get(a, 0.0))
            if float(answered_weight_by_archetype.get(a, 0.0)) > 0
            else float("nan")
        )
        for a in JST_ARCHETYPES
    }


def compute_most_important_experience_balance(
    negative_weight_by_archetype: Dict[str, float],
    positive_weight_by_archetype: Dict[str, float],
    answered_weight: float,
) -> Tuple[Dict[str, float], Dict[str, float], Dict[str, float]]:
    mneg = {
        a: (100.0 * float(negative_weight_by_archetype.get(a, 0.0)) / float(answered_weight)) if float(answered_weight) > 0 else float("nan")
        for a in JST_ARCHETYPES
    }
    mpos = {
        a: (100.0 * float(positive_weight_by_archetype.get(a, 0.0)) / float(answered_weight)) if float(answered_weight) > 0 else float("nan")
        for a in JST_ARCHETYPES
    }
    mbal = {
        a: (
            float(mneg.get(a, float("nan"))) - float(mpos.get(a, float("nan")))
            if math.isfinite(float(mneg.get(a, float("nan")))) and math.isfinite(float(mpos.get(a, float("nan"))))
            else float("nan")
        )
        for a in JST_ARCHETYPES
    }
    return mbal, mneg, mpos


def _matching_mode_labels(mode_choice: str) -> Tuple[str, str, str]:
    pick = str(mode_choice or "").strip().lower()
    if pick.startswith("wart"):
        return (
            "ISOW",
            "Indeks Społecznego Oczekiwania Wartości (ISOW)",
            "Wartość",
        )
    return (
        "ISOA",
        "Indeks Społecznego Oczekiwania Archetypu (ISOA)",
        "Archetyp",
    )


_MATCHING_FEMININE_MAP: Dict[str, str] = {
    "Władca": "Władczyni",
    "Bohater": "Bohaterka",
    "Mędrzec": "Mędrczyni",
    "Opiekun": "Opiekunka",
    "Kochanek": "Kochanka",
    "Błazen": "Komiczka",
    "Twórca": "Twórczyni",
    "Odkrywca": "Odkrywczyni",
    "Czarodziej": "Czarodziejka",
    "Towarzysz": "Towarzyszka",
    "Niewinny": "Niewinna",
    "Buntownik": "Buntowniczka",
}
_MATCHING_MASC_FROM_FEM: Dict[str, str] = {v: k for k, v in _MATCHING_FEMININE_MAP.items()}


def _normalize_matching_gender_code(raw: Any) -> str:
    txt = str(raw or "").strip().lower()
    if txt in {"k", "kobieta", "kob", "female", "f"}:
        return "K"
    return "M"


def _matching_entity_name(entity: str, axis_label: str, gender_code: str = "M") -> str:
    if str(axis_label) == "Wartość":
        return str(JST_VALUE_BY_ARCH.get(str(entity), str(entity)))
    base = str(_MATCHING_MASC_FROM_FEM.get(str(entity), str(entity)))
    if _normalize_matching_gender_code(gender_code) == "K":
        return str(_MATCHING_FEMININE_MAP.get(base, base))
    return base


_JST_ARCH_BY_VALUE: Dict[str, str] = {str(v): str(k) for k, v in JST_VALUE_BY_ARCH.items()}
_MATCHING_ICON_BY_ARCH: Dict[str, str] = {
    "Władca": "♕",
    "Bohater": "🛡",
    "Mędrzec": "📖",
    "Opiekun": "👐",
    "Kochanek": "♡",
    "Błazen": "❦",
    "Twórca": "⚒",
    "Odkrywca": "🧭",
    "Czarodziej": "✣",
    "Buntownik": "✊",
    "Niewinny": "🕊",
    "Towarzysz": "🍻",
}
_MATCHING_ICON_FILE_BY_ARCH: Dict[str, str] = {
    "Buntownik": "buntownik.png",
    "Błazen": "blazen.png",
    "Kochanek": "kochanek.png",
    "Opiekun": "opiekun.png",
    "Towarzysz": "towarzysz.png",
    "Niewinny": "niewinny.png",
    "Władca": "wladca.png",
    "Mędrzec": "medrzec.png",
    "Czarodziej": "czarodziej.png",
    "Bohater": "bohater.png",
    "Twórca": "tworca.png",
    "Odkrywca": "odkrywca.png",
}
_MATCHING_ICON_DATA_URI_CACHE: Dict[str, str] = {}


def _matching_entity_icon(entity: str, axis_label: str) -> str:
    ent = str(entity)
    if str(axis_label) == "Wartość":
        ent = str(_JST_ARCH_BY_VALUE.get(ent, ent))
    ent = str(_MATCHING_MASC_FROM_FEM.get(ent, ent))
    return str(_MATCHING_ICON_BY_ARCH.get(ent, "•"))


def _matching_entity_icon_html(entity: str, axis_label: str) -> str:
    ent = str(entity)
    if str(axis_label) == "Wartość":
        ent = str(_JST_ARCH_BY_VALUE.get(ent, ent))
    ent = str(_MATCHING_MASC_FROM_FEM.get(ent, ent))
    icon_file = str(_MATCHING_ICON_FILE_BY_ARCH.get(ent, "")).strip()
    if icon_file:
        icon_path = Path(__file__).with_name("ikony") / icon_file
        if icon_path.exists():
            cached = _MATCHING_ICON_DATA_URI_CACHE.get(icon_file)
            if not cached:
                try:
                    encoded = base64.b64encode(icon_path.read_bytes()).decode("ascii")
                    cached = f"data:image/png;base64,{encoded}"
                    _MATCHING_ICON_DATA_URI_CACHE[icon_file] = cached
                except Exception:
                    cached = ""
            if cached:
                return (
                    f"<img src='{cached}' alt='{html.escape(ent)}' class='match-top3-icon-img'/>"
                )
    return html.escape(str(_MATCHING_ICON_BY_ARCH.get(ent, "•")))


def _parse_a_value(raw: Any) -> Optional[int]:
    try:
        val = int(float(str(raw).strip().replace(",", ".")))
    except Exception:
        return None
    return val if 1 <= val <= 7 else None


def _parse_binary_mark(raw: Any) -> Optional[bool]:
    if raw is None:
        return None
    txt = str(raw).strip().lower()
    if not txt:
        return None
    if txt in {"1", "1.0", "true", "t", "tak", "yes", "y", "x", "on"}:
        return True
    if txt in {"0", "0.0", "false", "f", "nie", "no", "n", "off"}:
        return False
    try:
        return float(txt.replace(",", ".")) > 0.0
    except Exception:
        return None


def _parse_archetype_choice(raw: Any) -> Optional[str]:
    txt = str(raw or "").strip()
    if not txt:
        return None
    key = txt.casefold()
    if key in JST_ARCH_BY_KEY:
        return JST_ARCH_BY_KEY[key]
    m = re.search(r"(\d+)", txt)
    if m:
        key_num = str(int(m.group(1)))
        if key_num in JST_ARCH_BY_KEY:
            return JST_ARCH_BY_KEY[key_num]
    return None


def _parse_ab_choice(raw: Any) -> Optional[str]:
    txt = str(raw or "").strip()
    if not txt:
        return None
    up = txt.upper()
    if up in {"A", "B"}:
        return up
    if txt in {"1", "2"}:
        return "A" if txt == "1" else "B"
    if up.startswith("A"):
        return "A"
    if up.startswith("B"):
        return "B"
    return None


def safe_zscore_by_archetype(values: Dict[str, float]) -> Tuple[Dict[str, float], Dict[str, float]]:
    vals = [float(values.get(a, float("nan"))) for a in JST_ARCHETYPES]
    finite_vals = [v for v in vals if math.isfinite(v)]
    if len(finite_vals) < 2:
        return {a: 0.0 for a in JST_ARCHETYPES}, {"mean": float("nan"), "std": 0.0}
    mean_val = float(sum(finite_vals) / len(finite_vals))
    variance = float(sum((v - mean_val) ** 2 for v in finite_vals) / len(finite_vals))
    std_val = math.sqrt(max(0.0, variance))
    if not math.isfinite(std_val) or std_val <= 1e-12:
        return {a: 0.0 for a in JST_ARCHETYPES}, {"mean": mean_val, "std": 0.0}
    out: Dict[str, float] = {}
    for a in JST_ARCHETYPES:
        v = float(values.get(a, float("nan")))
        out[a] = float((v - mean_val) / std_val) if math.isfinite(v) else 0.0
    return out, {"mean": mean_val, "std": std_val}


def compute_variant_b_correction(
    b1_pct: Dict[str, float],
    b2_pct: Dict[str, float],
    n_pct: Dict[str, float],
    mbal_pp: Dict[str, float],
) -> Tuple[
    Dict[str, float],
    Dict[str, float],
    Dict[str, float],
    Dict[str, float],
]:
    delta_b1: Dict[str, float] = {}
    delta_b2: Dict[str, float] = {}
    delta_n: Dict[str, float] = {}
    k_b: Dict[str, float] = {}
    b2_neutral = 8.3333333333
    for a in JST_ARCHETYPES:
        b1 = float(b1_pct.get(a, float("nan")))
        b2 = float(b2_pct.get(a, float("nan")))
        n = float(n_pct.get(a, float("nan")))
        mbal = float(mbal_pp.get(a, float("nan")))
        d_b1 = (b1 - 25.0) if math.isfinite(b1) else 0.0
        d_b2 = (b2 - b2_neutral) if math.isfinite(b2) else 0.0
        d_n = (n - 50.0) if math.isfinite(n) else 0.0
        mbal_safe = mbal if math.isfinite(mbal) else 0.0
        corr = float(0.35 * d_b1 + 0.90 * d_b2 + 0.08 * d_n + 0.20 * mbal_safe)
        delta_b1[a] = float(d_b1)
        delta_b2[a] = float(d_b2)
        delta_n[a] = float(d_n)
        k_b[a] = corr
    return delta_b1, delta_b2, delta_n, k_b


def compute_social_expectation_variant_b(
    a_pct: Dict[str, float],
    k_b: Dict[str, float],
) -> Tuple[Dict[str, float], Dict[str, float]]:
    raw = {
        a: (
            float(a_pct.get(a, float("nan"))) + float(k_b.get(a, 0.0))
            if math.isfinite(float(a_pct.get(a, float("nan"))))
            else float("nan")
        )
        for a in JST_ARCHETYPES
    }
    scaled = {
        a: float(max(0.0, min(100.0, float(raw[a])))) if math.isfinite(float(raw[a])) else float("nan")
        for a in JST_ARCHETYPES
    }
    return raw, scaled


def update_matching_summary_description(sei_short: str, sei_full: str, data_basis: str) -> str:
    return (
        f"Kolumna `Oczekiwania mieszkańców ({sei_short})` pokazuje `{sei_full}` w skali 0–100 "
        f"(to indeks syntetyczny, nie procent mieszkańców). "
        "Wskaźnik jest zakotwiczony w `% oczekujących` z pytania A. "
        "B1 i B2 wzmacniają lub osłabiają wynik względem poziomu neutralnego, a C13/D13 działa jako umiarkowana korekta doświadczeniowa. "
        f"Podstawa danych: {data_basis}."
    )


def _calc_jst_target_profile(
    rows: List[Dict[str, Any]],
    row_weights: Optional[List[float]] = None,
) -> Tuple[Dict[str, float], List[Dict[str, Any]], Dict[str, Any]]:
    if not rows:
        return {}, [], {}

    rows_n = int(len(rows))
    if row_weights and len(row_weights) == rows_n:
        weights = [float(w) if math.isfinite(float(w)) and float(w) > 0 else 1.0 for w in row_weights]
    else:
        weights = [1.0] * rows_n
    mean_w = float(sum(weights) / max(1, len(weights)))
    if mean_w > 0:
        weights = [float(max(0.0, w / mean_w)) for w in weights]
    total_w = float(sum(weights)) or float(rows_n) or 1.0

    a_num = {a: 0.0 for a in JST_ARCHETYPES}
    a_den = {a: 0.0 for a in JST_ARCHETYPES}
    a_valid_by_q_w = {qid: 0.0 for qid, _, _ in JST_A_PAIRS}
    b1_num = {a: 0.0 for a in JST_ARCHETYPES}
    b1_den = 0.0
    b2_num = {a: 0.0 for a in JST_ARCHETYPES}
    b2_den = 0.0
    n_neg_num = {a: 0.0 for a in JST_ARCHETYPES}
    n_den = {a: 0.0 for a in JST_ARCHETYPES}
    mbal_neg_num = {a: 0.0 for a in JST_ARCHETYPES}
    mbal_pos_num = {a: 0.0 for a in JST_ARCHETYPES}
    d13_den = 0.0

    respondent_vectors: List[Dict[str, Any]] = []
    b1_selected_total = 0.0
    b2_valid_total_w = 0.0
    d13_valid_total_w = 0.0

    for idx, rec in enumerate(rows):
        payload = rec.get("payload") or {}
        if not isinstance(payload, dict):
            payload = {}
        w = float(weights[idx]) if idx < len(weights) else 1.0
        if w <= 0:
            continue

        a_score_sum = {a: 0.0 for a in JST_ARCHETYPES}
        a_score_cnt = {a: 0 for a in JST_ARCHETYPES}
        for qid, left_arch, right_arch in JST_A_PAIRS:
            val = _parse_a_value(payload.get(qid))
            if val is None:
                continue
            a_valid_by_q_w[qid] = float(a_valid_by_q_w.get(qid, 0.0)) + w
            points_left = float(4 - val)
            points_right = float(val - 4)
            a_score_sum[left_arch] += points_left
            a_score_cnt[left_arch] = int(a_score_cnt.get(left_arch, 0)) + 1
            a_score_sum[right_arch] += points_right
            a_score_cnt[right_arch] = int(a_score_cnt.get(right_arch, 0)) + 1

        b1_selected: set[str] = set()
        b1_answered = False
        for a in JST_ARCHETYPES:
            mark = _parse_binary_mark(payload.get(f"B1_{a}"))
            if mark is None:
                continue
            b1_answered = True
            if mark:
                b1_selected.add(a)
        if b1_answered:
            b1_den += w
            b1_selected_total += float(len(b1_selected)) * w
            for a in b1_selected:
                b1_num[a] += w

        b2 = _parse_archetype_choice(payload.get("B2"))
        if b2 in JST_ARCHETYPES:
            b2_den += w
            b2_num[b2] += w
            b2_valid_total_w += w

        d12_choice_by_arch: Dict[str, Optional[str]] = {}
        for qid, a in JST_D_ITEMS:
            choice = _parse_ab_choice(payload.get(qid))
            d12_choice_by_arch[a] = choice
            if choice is None:
                continue
            n_den[a] += w
            if choice == "B":
                n_neg_num[a] += w

        d13 = _parse_archetype_choice(payload.get("D13"))
        if d13 in JST_ARCHETYPES:
            d13_den += w
            d13_valid_total_w += w
            selected_d_choice = d12_choice_by_arch.get(d13)
            if selected_d_choice == "B":
                mbal_neg_num[d13] += w
            elif selected_d_choice == "A":
                mbal_pos_num[d13] += w

        vec: Dict[str, float] = {}
        for a in JST_ARCHETYPES:
            cnt = int(a_score_cnt.get(a, 0))
            if cnt > 0:
                score_mean = float(a_score_sum.get(a, 0.0)) / float(cnt)
                a_strength = max(0.0, min(100.0, ((score_mean + 3.0) / 6.0) * 100.0))
                a_den[a] += w
                if score_mean > 0:
                    a_num[a] += w
            else:
                a_strength = 50.0
            b1_hit = 100.0 if a in b1_selected else 0.0
            b2_hit = 100.0 if b2 == a else 0.0
            d13_hit = 100.0 if d13 == a else 0.0
            vec[a] = float((a_strength + b1_hit + b2_hit + d13_hit) / 4.0)

        respondent_vectors.append(
            {
                "respondent_id": str(rec.get("respondent_id") or "").strip(),
                "payload": payload,
                "vec": vec,
                "weight": w,
            }
        )

    comp_A = {
        a: (100.0 * float(a_num[a]) / float(a_den[a])) if float(a_den[a]) > 0 else float("nan")
        for a in JST_ARCHETYPES
    }
    comp_B1 = compute_top3_share(b1_num, b1_den)
    comp_B2 = compute_top1_share(b2_num, b2_den)
    comp_N = compute_negative_experience_share(n_neg_num, n_den)
    comp_MBAL, comp_MNEG, comp_MPOS = compute_most_important_experience_balance(
        negative_weight_by_archetype=mbal_neg_num,
        positive_weight_by_archetype=mbal_pos_num,
        answered_weight=d13_den,
    )
    expected_arches = set(JST_ARCHETYPES)
    components_aligned = all(
        set(comp.keys()) == expected_arches
        for comp in (comp_A, comp_B1, comp_B2, comp_N, comp_MBAL)
    )

    delta_b1, delta_b2, delta_n, corr_b = compute_variant_b_correction(
        b1_pct=comp_B1,
        b2_pct=comp_B2,
        n_pct=comp_N,
        mbal_pp=comp_MBAL,
    )
    sei_raw, sei_100 = compute_social_expectation_variant_b(comp_A, corr_b)

    profile = {
        a: (round(float(sei_100[a]), 2) if math.isfinite(float(sei_100.get(a, float("nan")))) else float("nan"))
        for a in JST_ARCHETYPES
    }
    component_rows = {
        a: {
            "A": round(float(comp_A.get(a, float("nan"))), 3) if math.isfinite(float(comp_A.get(a, float("nan")))) else float("nan"),
            "B1": round(float(comp_B1.get(a, float("nan"))), 3) if math.isfinite(float(comp_B1.get(a, float("nan")))) else float("nan"),
            "B2": round(float(comp_B2.get(a, float("nan"))), 3) if math.isfinite(float(comp_B2.get(a, float("nan")))) else float("nan"),
            "N": round(float(comp_N.get(a, float("nan"))), 3) if math.isfinite(float(comp_N.get(a, float("nan")))) else float("nan"),
            "Mneg": round(float(comp_MNEG.get(a, float("nan"))), 3) if math.isfinite(float(comp_MNEG.get(a, float("nan")))) else float("nan"),
            "Mpos": round(float(comp_MPOS.get(a, float("nan"))), 3) if math.isfinite(float(comp_MPOS.get(a, float("nan")))) else float("nan"),
            "MBAL": round(float(comp_MBAL.get(a, float("nan"))), 3) if math.isfinite(float(comp_MBAL.get(a, float("nan")))) else float("nan"),
            "delta_B1": round(float(delta_b1.get(a, 0.0)), 4),
            "delta_B2": round(float(delta_b2.get(a, 0.0)), 4),
            "delta_N": round(float(delta_n.get(a, 0.0)), 4),
            "K_B": round(float(corr_b.get(a, 0.0)), 4),
            "SEI_raw": round(float(sei_raw.get(a, 0.0)), 4),
            "SEI_100": (
                round(float(sei_100.get(a, float("nan"))), 3)
                if math.isfinite(float(sei_100.get(a, float("nan"))))
                else float("nan")
            ),
        }
        for a in JST_ARCHETYPES
    }
    component_missing_counts = {
        "A": int(sum(0 if math.isfinite(float(comp_A.get(a, float("nan")))) else 1 for a in JST_ARCHETYPES)),
        "B1": int(sum(0 if math.isfinite(float(comp_B1.get(a, float("nan")))) else 1 for a in JST_ARCHETYPES)),
        "B2": int(sum(0 if math.isfinite(float(comp_B2.get(a, float("nan")))) else 1 for a in JST_ARCHETYPES)),
        "N": int(sum(0 if math.isfinite(float(comp_N.get(a, float("nan")))) else 1 for a in JST_ARCHETYPES)),
        "MBAL": int(sum(0 if math.isfinite(float(comp_MBAL.get(a, float("nan")))) else 1 for a in JST_ARCHETYPES)),
    }

    audit: Dict[str, Any] = {
        "rows_n": rows_n,
        "weights_applied": bool(row_weights and len(row_weights) == rows_n),
        "a_valid_rate_pct": round((100.0 * sum(float(v) for v in a_valid_by_q_w.values()) / max(1.0, total_w * len(JST_A_PAIRS))), 1),
        "a_valid_by_q_rate_pct": {
            qid: round((100.0 * float(a_valid_by_q_w.get(qid, 0.0)) / max(1.0, total_w)), 1)
            for qid, _, _ in JST_A_PAIRS
        },
        "b1_valid_rate_pct": round((100.0 * float(b1_den) / max(1.0, total_w)), 1),
        "b2_valid_rate_pct": round((100.0 * float(b2_valid_total_w) / max(1.0, total_w)), 1),
        "d13_valid_rate_pct": round((100.0 * float(d13_valid_total_w) / max(1.0, total_w)), 1),
        "b1_mean_selected": round((float(b1_selected_total) / max(1.0, float(b1_den))) if b1_den > 0 else 0.0, 2),
        "component_means_by_archetype": component_rows,
        "component_a_pct": comp_A,
        "component_b1_pct": comp_B1,
        "component_b2_pct": comp_B2,
        "component_negative_pct": comp_N,
        "component_mneg_pct": comp_MNEG,
        "component_mpos_pct": comp_MPOS,
        "component_mbal_pp": comp_MBAL,
        "components_aligned": bool(components_aligned),
        "component_missing_counts": component_missing_counts,
        "methodology": {
            "anchor_formula": "A_base = % oczekujących z pytania A",
            "delta_formula": "delta_B1=B1-25.0; delta_B2=B2-8.3333333333; delta_N=N-50.0; MBAL=Mneg-Mpos",
            "corr_formula": "K_B = 0.35*delta_B1 + 0.90*delta_B2 + 0.08*delta_N + 0.20*MBAL",
            "raw_formula": "SEI_B = A_base + K_B",
            "scale_formula": "SEI_B_100 = clamp(SEI_B, 0..100)",
        },
    }
    return profile, respondent_vectors, audit


def _norm_demo_token(value: Any) -> str:
    txt = str(value or "").strip().lower()
    repl = (
        ("ą", "a"),
        ("ć", "c"),
        ("ę", "e"),
        ("ł", "l"),
        ("ń", "n"),
        ("ó", "o"),
        ("ś", "s"),
        ("ż", "z"),
        ("ź", "z"),
    )
    for a, b in repl:
        txt = txt.replace(a, b)
    return re.sub(r"\s+", " ", txt).strip()


def _matching_guess_variable_emoji(field: str, label: str) -> str:
    key = _norm_demo_token(f"{field} {label}")
    if "wiek" in key:
        return "⌛"
    if any(k in key for k in ("obszar", "miejsce", "zamiesz", "lokaliz", "wies", "miasto")):
        return "🏘️"
    if any(k in key for k in ("preferencj", "komitet", "wybor", "glos", "parti", "sejm")):
        return "🗳️"
    if any(k in key for k in ("orientac", "poglad", "politycz", "ideolog")):
        return "🧭"
    return "📌"


def _matching_guess_value_emoji(var_label: str, code: str) -> str:
    nk_var = _norm_demo_token(var_label)
    nk = _norm_demo_token(code)
    nk_sp = nk.replace("-", " ")
    if not nk:
        return "❔"
    if any(k in nk_var for k in ("obszar", "miejsce", "zamiesz", "lokaliz", "wies", "miasto")):
        if "miasto" in nk:
            return "🏙️"
        if "wies" in nk:
            return "🌾"
    if any(k in nk_var for k in ("preferencj", "komitet", "wybor", "glos", "parti", "sejm")):
        if "odmow" in nk:
            return "🤐"
        if "nie wiem" in nk or "niezdecyd" in nk or "trudno" in nk:
            return "❓"
        return "🗳️"
    if any(k in nk_var for k in ("orientac", "poglad", "politycz", "ideolog")):
        if "centro prawic" in nk_sp:
            return "↗️"
        if "prawic" in nk:
            return "➡️"
        if "centro lewic" in nk_sp:
            return "↖️"
        if "lewic" in nk:
            return "⬅️"
        if "centr" in nk:
            return "⚖️"
        if "odmow" in nk:
            return "🤐"
        if "nie wiem" in nk or "trudno" in nk:
            return "❓"
        return "🧭"
    return "📌"


def _canon_demo_value(field: str, value: Any) -> str:
    raw = str(value or "").strip()
    n = _norm_demo_token(value)
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


_MATCHING_CORE_DEMO_META: Dict[str, Dict[str, Any]] = {
    "M_PLEC": {
        "label": "Płeć",
        "order": ["kobieta", "mężczyzna"],
        "variable_emoji": "👫",
        "value_emoji": {"kobieta": "👩", "mężczyzna": "👨"},
    },
    "M_WIEK": {
        "label": "Wiek",
        "order": ["15-39", "40-59", "60+"],
        "variable_emoji": "⌛",
        "value_emoji": {"15-39": "🧑", "40-59": "🧑‍💼", "60+": "🧓"},
    },
    "M_WYKSZT": {
        "label": "Wykształcenie",
        "order": ["podst./gim./zaw.", "średnie", "wyższe"],
        "variable_emoji": "🎓",
        "value_emoji": {"podst./gim./zaw.": "🛠️", "średnie": "📘", "wyższe": "🎓"},
    },
    "M_ZAWOD": {
        "label": "Status zawodowy",
        "order": ["prac. umysłowy", "prac. fizyczny", "własna firma", "student/uczeń", "bezrobotny", "rencista/emeryt", "inna"],
        "variable_emoji": "💼",
        "value_emoji": {
            "prac. umysłowy": "🧠",
            "prac. fizyczny": "🛠️",
            "własna firma": "🏢",
            "student/uczeń": "🧑‍🎓",
            "bezrobotny": "🔎",
            "rencista/emeryt": "🌿",
            "inna": "🧩",
        },
    },
    "M_MATERIAL": {
        "label": "Sytuacja materialna",
        "order": ["bardzo dobra", "raczej dobra", "przeciętna", "raczej zła", "bardzo zła", "odmowa"],
        "variable_emoji": "💰",
        "value_emoji": {
            "bardzo dobra": "😄",
            "raczej dobra": "🙂",
            "przeciętna": "😐",
            "raczej zła": "🙁",
            "bardzo zła": "😟",
            "odmowa": "🤐",
        },
    },
}


def _matching_demo_options(question: Dict[str, Any]) -> List[Dict[str, str]]:
    out: List[Dict[str, Any]] = []
    seen: set[str] = set()
    for opt in list(question.get("options") or []):
        if not isinstance(opt, dict):
            continue
        label = str(opt.get("label") or "").strip()
        code = str(opt.get("code") or label).strip()
        if not label or not code:
            continue
        code_u = code.upper()
        if code_u in seen:
            continue
        seen.add(code_u)
        out.append(
            {
                "code": code,
                "label": label,
                "value_emoji": str(opt.get("value_emoji") or "").strip(),
                "has_value_emoji": ("value_emoji" in opt),
            }
        )
    return out


def _matching_demo_build_specs(metryczka_config: Any) -> List[Dict[str, Any]]:
    cfg = normalize_jst_metryczka_config(metryczka_config)
    specs: List[Dict[str, Any]] = []
    seen_fields: set[str] = set()
    for q in list(cfg.get("questions") or []):
        if not isinstance(q, dict):
            continue
        field = str(q.get("db_column") or q.get("id") or "").strip().upper()
        if not field or field in seen_fields:
            continue
        seen_fields.add(field)
        opts = _matching_demo_options(q)
        core_meta = _MATCHING_CORE_DEMO_META.get(field)
        display_labels: Dict[str, str] = {}
        if core_meta:
            core_label = str(q.get("table_label") or core_meta.get("label") or field).strip() or field
            for cat in list(core_meta.get("order") or []):
                display_labels[str(cat)] = str(cat)
            value_emoji_map = dict(core_meta.get("value_emoji") or {})
            for opt in opts:
                if not isinstance(opt, dict):
                    continue
                code = str(opt.get("code") or "").strip()
                icon = str(opt.get("value_emoji") or "").strip()
                has_icon = bool(opt.get("has_value_emoji"))
                if not code:
                    continue
                canon_code = _canon_demo_value(field, code)
                if canon_code and canon_code != "brak danych":
                    if has_icon:
                        value_emoji_map[str(canon_code)] = icon
            specs.append(
                {
                    "field": field,
                    "label": core_label,
                    "order_codes": list(core_meta.get("order") or []),
                    "display_labels": display_labels,
                    "options": opts,
                    "variable_emoji": str(
                        q.get("variable_emoji")
                        or core_meta.get("variable_emoji")
                        or guess_metry_variable_emoji(field, core_label, q.get("prompt"))
                    ).strip() or "📌",
                    "value_emoji": value_emoji_map,
                    "is_core": True,
                }
            )
            continue

        order_codes = [str(opt.get("code") or "").strip() for opt in opts if str(opt.get("code") or "").strip()]
        # W tabelach demograficznych dla pytań custom pokazujemy kodowania odpowiedzi
        # (nie pełne etykiety dla respondentów), aby zachować spójność analityczną.
        display_labels = {
            str(opt.get("code") or "").strip(): str(opt.get("code") or "").strip()
            for opt in opts
            if str(opt.get("code") or "").strip()
        }
        label = str(q.get("table_label") or q.get("prompt") or field).strip() or field
        var_emoji = str(
            q.get("variable_emoji")
            or guess_metry_variable_emoji(field, label, q.get("prompt"))
            or _matching_guess_variable_emoji(field, label)
        ).strip() or "📌"
        value_emoji: Dict[str, str] = {}
        for code in order_codes:
            opt = next((o for o in opts if str(o.get("code") or "").strip() == code), {})
            has_icon = bool(isinstance(opt, dict) and opt.get("has_value_emoji"))
            if has_icon:
                value_emoji[str(code)] = str(opt.get("value_emoji") or "").strip()
            else:
                value_emoji[str(code)] = str(
                    guess_metry_value_emoji(label, code, field) or _matching_guess_value_emoji(label, code)
                ).strip()
        specs.append(
            {
                "field": field,
                "label": label,
                "order_codes": order_codes,
                "display_labels": display_labels,
                "options": opts,
                "variable_emoji": var_emoji,
                "value_emoji": value_emoji,
                "is_core": False,
            }
        )
    return specs


def _matching_demo_value_for_spec(spec: Dict[str, Any], value: Any) -> str:
    field = str(spec.get("field") or "").strip().upper()
    if str(spec.get("is_core") or "").lower() == "true" or bool(spec.get("is_core")):
        return _canon_demo_value(field, value)
    raw = str(value or "").strip()
    if not raw:
        return "brak danych"
    n_raw = _norm_demo_token(raw)
    for opt in list(spec.get("options") or []):
        if not isinstance(opt, dict):
            continue
        code = str(opt.get("code") or "").strip()
        label = str(opt.get("label") or "").strip()
        if not code:
            continue
        if n_raw in {_norm_demo_token(code), _norm_demo_token(label)}:
            return code
    return raw


def _matching_demo_label_for_code(spec: Dict[str, Any], code: str) -> str:
    txt = str(code or "").strip()
    if not txt:
        return "brak danych"
    if txt == "brak danych":
        return "brak danych"
    labels = spec.get("display_labels") if isinstance(spec.get("display_labels"), dict) else {}
    return str(labels.get(txt) or txt)


def _matching_demo_build_rows(
    subset_records: List[Dict[str, Any]],
    all_records: List[Dict[str, Any]],
    specs: List[Dict[str, Any]],
    subset_col_name: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    def _weighted_count_records(records: List[Dict[str, Any]], spec: Dict[str, Any]) -> Dict[str, float]:
        out: Dict[str, float] = {}
        field = str(spec.get("field") or "").strip().upper()
        for rec in records:
            payload = rec.get("payload") if isinstance(rec.get("payload"), dict) else {}
            w = float(rec.get("weight") or 1.0)
            if not math.isfinite(w) or w <= 0:
                continue
            val = _matching_demo_value_for_spec(spec, payload.get(field))
            out[val] = float(out.get(val, 0.0)) + w
        return out

    demo_rows: List[Dict[str, Any]] = []
    demo_cards: List[Dict[str, Any]] = []
    for spec in specs:
        dim_label = str(spec.get("label") or spec.get("field") or "").strip()
        if not dim_label:
            continue
        dist_sub = _weighted_count_records(subset_records, spec)
        dist_all = _weighted_count_records(all_records, spec)
        sum_sub = float(sum(float(v) for v in dist_sub.values()))
        sum_all = float(sum(float(v) for v in dist_all.values()))
        known_order = [str(x) for x in list(spec.get("order_codes") or []) if str(x).strip()]
        unknown = sorted((set(dist_sub.keys()) | set(dist_all.keys())) - set(known_order))
        cats = known_order + list(unknown)
        if not cats:
            continue

        top_cat: Optional[str] = None
        top_pct = -1.0
        top_all_pct = 0.0
        for cat in cats:
            c_sub = float(dist_sub.get(cat, 0.0))
            c_all = float(dist_all.get(cat, 0.0))
            pct_sub = (100.0 * c_sub / sum_sub) if sum_sub > 0 else 0.0
            pct_all = (100.0 * c_all / sum_all) if sum_all > 0 else 0.0
            if pct_sub > top_pct:
                top_pct = pct_sub
                top_cat = str(cat)
                top_all_pct = pct_all
            demo_rows.append(
                {
                    "Zmienna": dim_label,
                    "Pole": str(spec.get("field") or "").strip().upper(),
                    "KategoriaKod": str(cat),
                    "Kategoria": _matching_demo_label_for_code(spec, str(cat)),
                    subset_col_name: round(pct_sub, 1),
                    "% ogół mieszkańców (ważony)": round(pct_all, 1),
                    "Róznica (w pp.)": round(pct_sub - pct_all, 1),
                }
            )
        if top_cat is not None:
            value_emoji = spec.get("value_emoji") if isinstance(spec.get("value_emoji"), dict) else {}
            demo_cards.append(
                {
                    "field": str(spec.get("field") or "").strip().upper(),
                    "label": dim_label,
                    "top_code": str(top_cat),
                    "top": _matching_demo_label_for_code(spec, str(top_cat)),
                    "pct": round(max(top_pct, 0.0), 1),
                    "diff_pp": round(top_pct - top_all_pct, 1),
                    "emoji": str(value_emoji.get(str(top_cat), "•")),
                    "variable_emoji": str(spec.get("variable_emoji") or "📌"),
                }
            )
    return demo_rows, demo_cards


def _poststrat_cell_from_payload(payload: Dict[str, Any]) -> Optional[str]:
    g = _canon_demo_value("M_PLEC", payload.get("M_PLEC"))
    a = _canon_demo_value("M_WIEK", payload.get("M_WIEK"))
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


def _calc_poststrat_weights_for_payloads(payloads: List[Dict[str, Any]], study: Dict[str, Any]) -> Tuple[List[float], bool]:
    if not payloads:
        return [], False
    targets = _load_poststrat_targets(study)
    target_sum = float(sum(float(v or 0.0) for v in targets.values()))
    if target_sum <= 0:
        return [1.0] * len(payloads), False

    sample_counts: Dict[str, int] = {}
    for payload in payloads:
        cell = _poststrat_cell_from_payload(payload)
        if cell:
            sample_counts[cell] = int(sample_counts.get(cell, 0)) + 1
    present_cells = [k for k, v in sample_counts.items() if int(v) > 0]
    if not present_cells:
        return [1.0] * len(payloads), False

    present_target_sum = float(sum(float(targets.get(k, 0.0) or 0.0) for k in present_cells))
    sample_total = float(sum(sample_counts.values()))
    if present_target_sum <= 0 or sample_total <= 0:
        return [1.0] * len(payloads), False

    cell_weights: Dict[str, float] = {}
    for cell in present_cells:
        target_share = float(targets.get(cell, 0.0) or 0.0) / present_target_sum
        sample_share = float(sample_counts.get(cell, 0)) / sample_total
        if sample_share > 0:
            cell_weights[cell] = target_share / sample_share

    if not cell_weights:
        return [1.0] * len(payloads), False

    weights = [float(cell_weights.get(_poststrat_cell_from_payload(p) or "", 1.0)) for p in payloads]
    mean_w = float(sum(weights) / max(1, len(weights)))
    if mean_w > 0:
        weights = [float(max(0.0, w / mean_w)) for w in weights]
    return weights, True


def _dot(a: Dict[str, float], b: Dict[str, float]) -> float:
    return float(sum(float(a.get(k, 0.0)) * float(b.get(k, 0.0)) for k in JST_ARCHETYPES))


def _norm(a: Dict[str, float]) -> float:
    return float(sum(float(a.get(k, 0.0)) ** 2 for k in JST_ARCHETYPES)) ** 0.5


def _norm_arch_key(value: Any) -> str:
    txt = str(value or "").strip().lower()
    repl = (
        ("ą", "a"),
        ("ć", "c"),
        ("ę", "e"),
        ("ł", "l"),
        ("ń", "n"),
        ("ó", "o"),
        ("ś", "s"),
        ("ż", "z"),
        ("ź", "z"),
    )
    for a, b in repl:
        txt = txt.replace(a, b)
    txt = re.sub(r"\s+", "", txt)
    return txt


def _safe_float_num(raw: Any, default: float = 0.0) -> float:
    try:
        v = float(raw)
    except Exception:
        return float(default)
    return v if math.isfinite(v) else float(default)


def _load_matching_segment_profiles(jst_study_id: str) -> Tuple[List[Dict[str, Any]], str, str]:
    sid = str(jst_study_id or "").strip()
    if not sid:
        return [], "", "Brak ID badania JST."

    template_root = Path(__file__).resolve().parent / "JST_Archetypy_Analiza"
    csv_path = template_root / "_runs" / sid / "WYNIKI" / "SEGMENTY_ULTRA_PREMIUM_profile.csv"
    if not csv_path.exists():
        return [], str(csv_path), "Brak profili segmentów dla tego badania. Najpierw wygeneruj raport JST."

    try:
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
    except Exception as e:
        return [], str(csv_path), f"Nie udało się odczytać pliku segmentów: {e}"
    if df is None or df.empty:
        return [], str(csv_path), "Plik segmentów jest pusty."

    pm_col_by_arch: Dict[str, str] = {}
    for col in [str(c) for c in df.columns]:
        if not col.startswith("pm_share_"):
            continue
        arch_key = _norm_arch_key(col.replace("pm_share_", "", 1))
        if arch_key and arch_key not in pm_col_by_arch:
            pm_col_by_arch[arch_key] = col

    out: List[Dict[str, Any]] = []
    for idx, row in df.iterrows():
        segment_profile: Dict[str, float] = {}
        for arch in JST_ARCHETYPES:
            col_name = f"pm_share_{arch}"
            if col_name not in df.columns:
                col_name = pm_col_by_arch.get(_norm_arch_key(arch), "")
            val = _safe_float_num(row.get(col_name), 0.0)
            segment_profile[arch] = float(max(0.0, min(100.0, val)))

        seg_label = str(row.get("segment") or f"Seg_{idx + 1}").strip() or f"Seg_{idx + 1}"
        out.append(
            {
                "segment": seg_label,
                "segment_id": int(round(_safe_float_num(row.get("segment_id"), idx))),
                "name_arche": str(row.get("name_marketing_arche") or "").strip(),
                "name_values": str(row.get("name_marketing_values") or "").strip(),
                "n": int(round(_safe_float_num(row.get("n"), 0.0))),
                "share_pct": _safe_float_num(row.get("share_pct"), 0.0),
                "profile": segment_profile,
            }
        )

    out.sort(key=lambda x: (int(x.get("segment_id", 9999)), -float(x.get("share_pct", 0.0))))
    return out, str(csv_path), ""


def _load_matching_segment_membership(jst_study_id: str) -> Tuple[pd.DataFrame, str, str]:
    sid = str(jst_study_id or "").strip()
    if not sid:
        return pd.DataFrame(), "", "Brak ID badania JST."

    template_root = Path(__file__).resolve().parent / "JST_Archetypy_Analiza"
    csv_path = template_root / "_runs" / sid / "WYNIKI" / "respondenci_segmenty_ultra_premium.csv"
    if not csv_path.exists():
        return pd.DataFrame(), str(csv_path), "Brak przypisań respondentów do segmentów (CSV)."

    try:
        df = pd.read_csv(csv_path, encoding="utf-8-sig")
    except Exception as e:
        return pd.DataFrame(), str(csv_path), f"Nie udało się odczytać pliku przypisań segmentów: {e}"
    if df is None or df.empty:
        return pd.DataFrame(), str(csv_path), "Plik przypisań segmentów jest pusty."
    for col in ("respondent_id", "segment"):
        if col not in df.columns:
            return pd.DataFrame(), str(csv_path), f"Brak wymaganej kolumny `{col}` w pliku przypisań segmentów."
    return df, str(csv_path), ""


def matching_view() -> None:
    require_auth()
    if not _require_jst_ready():
        return
    _set_view_scope("matching")
    back_button("home_root", "← Powrót do wyboru modułu")
    header("🧭 Matching")
    render_titlebar(["Panel", "Matching"])
    st.markdown(
        """
        <style>
          div[data-testid="stTabs"] [data-baseweb="tab-list"],
          div[data-testid="stTabs"] [role="tablist"]{
            gap:10px;
            border:1px solid #c4cedc !important;
            border-bottom:1px solid #bcc7d7 !important;
            padding:10px 12px 12px 12px !important;
            background:#edf2f8 !important;
            border-radius:14px 14px 0 0 !important;
            flex-wrap:wrap;
            box-shadow:inset 0 1px 0 rgba(255,255,255,.75);
          }
          div[data-testid="stTabs"] [data-baseweb="tab"],
          div[data-testid="stTabs"] [role="tab"]{
            background:#ffffff !important;
            border:1px solid #b9c6d8 !important;
            border-radius:12px !important;
            padding:9px 16px !important;
            font-weight:800 !important;
            color:#2d3f57 !important;
            font-size:15px !important;
            letter-spacing:.01em;
            box-shadow:0 1px 3px rgba(15,58,116,.06);
            transition:all .15s ease;
            cursor:pointer !important;
            min-height:40px !important;
          }
          div[data-testid="stTabs"] [data-baseweb="tab"]:hover,
          div[data-testid="stTabs"] [role="tab"]:hover{
            border-color:#7fa6da !important;
            box-shadow:0 5px 14px rgba(37,99,235,.18) !important;
            background:#f3f8ff !important;
          }
          div[data-testid="stTabs"] [aria-selected="true"]{
            background:linear-gradient(180deg,#2f7fd8 0%, #2b70c2 100%) !important;
            border-color:#255fa6 !important;
            color:#ffffff !important;
            box-shadow:0 7px 16px rgba(37,99,235,.30) !important;
            transform:translateY(-1px);
            opacity:1 !important;
          }
          div[data-testid="stTabs"] [aria-selected="true"]:hover{
            background:linear-gradient(180deg,#2f7fd8 0%, #2b70c2 100%) !important;
            border-color:#1d4f8c !important;
            color:#ffffff !important;
            box-shadow:0 8px 18px rgba(37,99,235,.34) !important;
            opacity:1 !important;
          }
          div[data-testid="stTabs"] [aria-selected="true"] *{
            color:#ffffff !important;
          }
          div[data-testid="stTabs"] [aria-selected="true"]:hover *{
            color:#ffffff !important;
          }
          div[data-testid="stTabs"] [data-baseweb="tab-highlight"]{
            display:none;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )
    mode_pick = st.radio(
        "Tryb etykiet wskaźnika społecznego oczekiwania",
        ["Archetypy", "Wartości"],
        horizontal=True,
        key="matching_label_mode",
    )
    current_sei_short, current_sei_full, current_axis_label = _matching_mode_labels(mode_pick)

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

    tab_pick, tab_summary, tab_demo, tab_segments, tab_strategy = st.tabs(
        ["Wybierz badania", "Podsumowanie", "Demografia", "Segmenty", "Strategia komunikacji"]
    )

    with tab_pick:
        def _invalidate_matching_result() -> None:
            st.session_state.pop("matching_result", None)
            st.session_state.pop("matching_result_notice", None)

        personal_choices = list(p_options.keys())
        jst_choices = list(j_options.keys())
        if st.session_state.get("matching_pick_personal") not in personal_choices:
            st.session_state["matching_pick_personal"] = personal_choices[0]
        if st.session_state.get("matching_pick_jst") not in jst_choices:
            st.session_state["matching_pick_jst"] = jst_choices[0]

        pick_personal = st.selectbox(
            "Badanie personalne",
            personal_choices,
            key="matching_pick_personal",
            on_change=_invalidate_matching_result,
        )
        pick_jst = st.selectbox(
            "Badanie mieszkańców",
            jst_choices,
            key="matching_pick_jst",
            on_change=_invalidate_matching_result,
        )
        existing_result = st.session_state.get("matching_result")
        if isinstance(existing_result, dict):
            if (
                str(existing_result.get("person_label") or "") != str(pick_personal)
                or str(existing_result.get("jst_label") or "") != str(pick_jst)
            ):
                _invalidate_matching_result()

        if st.button("Połącz i policz matching", type="primary"):
            person = p_options[pick_personal]
            jst_study = j_options[pick_jst]
            person_gender_code = _normalize_matching_gender_code(person.get("gender"))
            person_role_gen_calc = "polityczki" if person_gender_code == "K" else "polityka"

            p_profile, p_n = _load_personal_profile_pct(str(person.get("id")))
            j_rows = list_jst_responses(sb, str(jst_study.get("id")))
            source_payloads = [
                (r.get("payload") if isinstance(r.get("payload"), dict) else {}) for r in j_rows
            ]
            profile_weights, profile_weights_used = _calc_poststrat_weights_for_payloads(source_payloads, jst_study)
            j_profile, respondent_vectors, target_audit = _calc_jst_target_profile(
                j_rows,
                row_weights=profile_weights if profile_weights_used else None,
            )

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

            arch_order = list(JST_ARCHETYPES)

            def _key_priority_pool(profile: Dict[str, float]) -> List[str]:
                ordered = sorted(
                    arch_order,
                    key=lambda a: (-float(profile.get(a, 0.0)), arch_order.index(a)),
                )
                top3 = ordered[:3]
                if len(top3) >= 3 and float(profile.get(top3[2], 0.0)) < 70.0:
                    return top3[:2]
                return top3

            person_top3 = _key_priority_pool(p_profile)
            jst_top3 = _key_priority_pool(j_profile)
            key_archetypes: List[str] = []
            for arche in person_top3 + jst_top3:
                if arche not in key_archetypes:
                    key_archetypes.append(arche)
            key_gap_vals = [float(diffs.get(a, 0.0)) for a in key_archetypes]
            key_gap_mae = float(sum(key_gap_vals) / max(1, len(key_gap_vals)))
            key_gap_max = float(max(key_gap_vals)) if key_gap_vals else 0.0
            shared_priority_count = len(set(person_top3).intersection(set(jst_top3)))
            main_priority_mismatch_penalty = (
                2.5 if (person_top3 and jst_top3 and person_top3[0] != jst_top3[0]) else 0.0
            )
            shared_priority_penalty = (
                5.5 if shared_priority_count == 0 else (2.0 if shared_priority_count == 1 else 0.0)
            )

            score_mae = max(0.0, min(100.0, 100.0 - mae))
            score_rmse = max(0.0, min(100.0, 100.0 - rmse))
            score_top3 = max(0.0, min(100.0, 100.0 - top3_gap_mae))
            score_key = max(0.0, min(100.0, 100.0 - key_gap_mae))
            base_score = 0.40 * score_mae + 0.20 * score_rmse + 0.20 * score_top3 + 0.20 * score_key
            # Kara kluczowa: mocniej dociąża duże luki na priorytetach oraz brak wspólnego TOP.
            key_penalty = (
                0.56 * key_gap_mae
                + 0.26 * max(0.0, key_gap_max - 10.0)
                + shared_priority_penalty
                + main_priority_mismatch_penalty
            )
            # Metryka mieszana z dodatkową karą za luki na archetypach kluczowych
            # (TOP3 polityka + TOP3 mieszkańców), żeby nie zawyżać wyniku przy strategicznych rozjazdach.
            match_score = max(0.0, min(100.0, base_score - key_penalty))

            strengths = sorted(JST_ARCHETYPES, key=lambda a: diffs[a])[:3]
            gaps = sorted(JST_ARCHETYPES, key=lambda a: diffs[a], reverse=True)[:3]
            strengths_rows = [{"archetyp": a, "diff": round(float(diffs[a]), 1)} for a in strengths]
            gaps_rows = [{"archetyp": a, "diff": round(float(diffs[a]), 1)} for a in gaps]

            if match_score >= 90:
                score_band_idx = 7
            elif match_score >= 80:
                score_band_idx = 6
            elif match_score >= 70:
                score_band_idx = 5
            elif match_score >= 60:
                score_band_idx = 4
            elif match_score >= 50:
                score_band_idx = 3
            elif match_score >= 40:
                score_band_idx = 2
            elif match_score >= 30:
                score_band_idx = 1
            else:
                score_band_idx = 0
            # Korekta opisu: przy bardzo dużych lukach kluczowych dopinamy ostrzeżenie,
            # ale nie nadpisujemy podstawowego progu liczbowego (żeby zakresy 0-100 były czytelne).
            key_guard_idx = score_band_idx
            guard_note = ""
            if key_gap_max >= 35.0 or key_gap_mae >= 24.0:
                guard_note = "Duże luki kluczowe oznaczają wysokie ryzyko rozjazdu strategicznego."
            elif key_gap_max >= 28.0 or key_gap_mae >= 19.0:
                guard_note = "Luki kluczowe pozostają wysokie i wymagają korekty przekazu."
            elif key_gap_max >= 22.0 or key_gap_mae >= 15.0:
                guard_note = "W obszarze kluczowych archetypów nadal widoczne są istotne rozjazdy."
            elif key_gap_max >= 18.0 or key_gap_mae >= 12.0:
                guard_note = "Drobne rozjazdy kluczowe ograniczają ocenę do poziomu wysokiego."
            final_band_idx = min(score_band_idx, key_guard_idx)
            match_bands: List[Tuple[str, str]] = [
                ("Marginalne dopasowanie", "Profile są w dużej mierze rozbieżne; potrzebna gruntowna korekta przekazu i priorytetów."),
                ("Bardzo niskie dopasowanie", "Dopasowanie jest słabe i niestabilne; dominują rozjazdy strategiczne."),
                ("Niskie dopasowanie", "Widać pojedyncze punkty wspólne, ale profil nadal wyraźnie się rozjeżdża."),
                ("Umiarkowane dopasowanie", "Istnieje wspólny rdzeń, ale kluczowe luki nadal wymagają korekty."),
                ("Znaczące dopasowanie", "Dopasowanie jest zauważalne, choć nadal potrzebne są poprawki na kluczowych pozycjach."),
                ("Wysokie dopasowanie", "Profil jest w dużej części zgodny; pozostają pojedyncze luki do domknięcia."),
                ("Bardzo wysokie dopasowanie", "Różnice są niewielkie i dotyczą głównie lokalnych odchyleń."),
                ("Ekstremalnie wysokie dopasowanie", "Profile są niemal zbieżne także na kluczowych archetypach."),
            ]
            band_label, band_desc = match_bands[final_band_idx]
            if guard_note and final_band_idx < score_band_idx:
                band_desc = f"{band_desc} {guard_note}"
            match_band = (band_label, band_desc)

            unit_person = {a: float(p_profile.get(a, 0.0)) for a in JST_ARCHETYPES}
            top_sim_rows = []
            base_norm = _norm(unit_person) or 1.0
            for rec in respondent_vectors:
                vec = {a: float(rec["vec"].get(a, 0.0)) for a in JST_ARCHETYPES}
                sim = _dot(unit_person, vec) / (base_norm * (_norm(vec) or 1.0))
                top_sim_rows.append(
                    {
                        "sim": sim,
                        "payload": rec.get("payload") or {},
                        "weight": float(rec.get("weight") or 1.0),
                    }
                )
            top_sim_rows.sort(key=lambda x: x["sim"], reverse=True)
            take_n = max(1, int(len(top_sim_rows) * 0.25))
            subset = top_sim_rows[:take_n]

            all_payloads = [r.get("payload") or {} for r in top_sim_rows]
            subset_payloads = [r.get("payload") or {} for r in subset]
            all_weights = [
                float(r.get("weight") or 1.0) if math.isfinite(float(r.get("weight") or 1.0)) else 1.0
                for r in top_sim_rows
            ]
            subset_weights = [
                float(r.get("weight") or 1.0) if math.isfinite(float(r.get("weight") or 1.0)) else 1.0
                for r in subset
            ]
            weights_used = bool(profile_weights_used)
            jst_name_nom = str(jst_study.get("jst_full_nom") or "").strip() or str(jst_study.get("jst_name") or "").strip() or str(pick_jst)
            person_name_gen = _person_genitive(person)
            jst_name_gen = str(jst_study.get("jst_full_gen") or "").strip()
            if not jst_name_gen:
                try:
                    auto_jst = _make_jst_defaults(
                        str(jst_study.get("jst_type") or "miasto"),
                        str(jst_study.get("jst_name") or ""),
                    )
                    jst_name_gen = str(auto_jst.get("jst_full_gen") or "").strip()
                except Exception:
                    jst_name_gen = ""
            if not jst_name_gen:
                jst_name_gen = jst_name_nom

            if not subset_weights:
                subset_weights = [1.0] * len(subset_payloads)
            if not all_weights:
                all_weights = [1.0] * len(all_payloads)

            demo_specs = _matching_demo_build_specs(jst_study.get("metryczka_config"))
            if not demo_specs:
                demo_specs = _matching_demo_build_specs(None)
            all_demo_records = [
                {
                    "payload": p,
                    "weight": float(all_weights[idx]) if idx < len(all_weights) and math.isfinite(float(all_weights[idx])) else 1.0,
                }
                for idx, p in enumerate(all_payloads)
            ]
            subset_demo_records = [
                {
                    "payload": p,
                    "weight": float(subset_weights[idx]) if idx < len(subset_weights) and math.isfinite(float(subset_weights[idx])) else 1.0,
                }
                for idx, p in enumerate(subset_payloads)
            ]
            demo_rows, demo_cards = _matching_demo_build_rows(
                subset_demo_records,
                all_demo_records,
                demo_specs,
                "% grupa dopasowana",
            )

            st.session_state["matching_result"] = {
                "person_label": pick_personal,
                "jst_label": pick_jst,
                "person_study_id": str(person.get("id") or ""),
                "jst_study_id": str(jst_study.get("id") or ""),
                "person_name_nom": f"{(person.get('first_name_nom') or person.get('first_name') or '').strip()} {(person.get('last_name_nom') or person.get('last_name') or '').strip()}".strip(),
                "person_name_gen": person_name_gen,
                "person_gender_code": person_gender_code,
                "jst_name_nom": jst_name_nom,
                "jst_name_gen": jst_name_gen,
                "match_score": round(match_score, 1),
                "personal_n": p_n,
                "jst_n": len(j_rows),
                "personal_profile": p_profile,
                "jst_profile": j_profile,
                "mode_choice": mode_pick,
                "sei_short": current_sei_short,
                "sei_full": current_sei_full,
                "sei_data_basis": (
                    "dane ważone poststratyfikacyjnie"
                    if bool(target_audit.get("weights_applied"))
                    else "dane surowe"
                ),
                "strengths": strengths,
                "gaps": gaps,
                "strengths_rows": strengths_rows,
                "gaps_rows": gaps_rows,
                "match_metrics": {
                    "mae": round(mae, 1),
                    "rmse": round(rmse, 1),
                    "top3_gap_mae": round(top3_gap_mae, 1),
                    "key_gap_mae": round(key_gap_mae, 1),
                    "key_gap_max": round(key_gap_max, 1),
                    "key_penalty": round(key_penalty, 1),
                    "score_mae": round(score_mae, 1),
                    "score_rmse": round(score_rmse, 1),
                    "score_top3": round(score_top3, 1),
                    "score_key": round(score_key, 1),
                    "key_archetypes": list(key_archetypes),
                    "shared_priority_count": int(shared_priority_count),
                    "shared_priority_penalty": round(shared_priority_penalty, 1),
                    "main_priority_mismatch_penalty": round(main_priority_mismatch_penalty, 1),
                    "band_label": str(match_band[0]),
                    "band_desc": str(match_band[1]),
                },
                "demo_cards": demo_cards,
                "demo_rows": demo_rows,
                "demo_specs": demo_specs,
                "demo_jst_weighted_header": f"{jst_name_nom} / (po wagowaniu)",
                "demo_weights_used": bool(weights_used),
                "target_audit": target_audit,
                "jst_demo_vectors": [
                    {
                        "respondent_id": str(rec.get("respondent_id") or "").strip(),
                        "payload": (rec.get("payload") if isinstance(rec.get("payload"), dict) else {}),
                        "weight": float(rec.get("weight") or 1.0),
                    }
                    for rec in respondent_vectors
                ],
                "match_formula": (
                    "base = 0.40*(100 - MAE) + 0.20*(100 - RMSE) + 0.20*(100 - TOP3_MAE) + 0.20*(100 - KEY_MAE); "
                    "kara_kluczowa = 0.56*KEY_MAE + 0.26*max(0, KEY_MAX - 10) + kara_wspolnych_priorytetow + kara_roznicy_priorytetu_glownego; "
                    "match = clamp(0,100, base - kara_kluczowa); "
                    "gdzie MAE = średnia |Δ| dla 12 archetypów, RMSE = pierwiastek ze średniej kwadratów |Δ|, "
                    f"TOP3_MAE = średnia z 3 największych |Δ|, KEY_MAE = średnia |Δ| dla unii priorytetów {person_role_gen_calc} i mieszkańców "
                    "(TOP3, ale jeśli 3. pozycja ma <70, do puli kluczowej wchodzi tylko TOP2), "
                    "KEY_MAX = największa |Δ| w tej samej puli kluczowej; "
                    "kara_wspolnych_priorytetow = 5.5 gdy brak części wspólnej TOP, 2.0 gdy wspólna jest tylko 1 pozycja, inaczej 0; "
                    f"kara_roznicy_priorytetu_glownego = 2.5 gdy TOP1 {person_role_gen_calc} i mieszkańców są różne. "
                    "To równanie dotyczy wyłącznie wskaźnika Poziom dopasowania. "
                    "Model nie dodaje osobnej premii dodatniej za zgodność - niższa luka poprawia wynik tylko przez mniejszą karę."
                ),
            }
            st.session_state["matching_result_notice"] = True

        if st.session_state.get("matching_result_notice") and st.session_state.get("matching_result"):
            st.success("Wynik dopasowania został obliczony.")

    result = st.session_state.get("matching_result")
    if not result:
        with tab_summary:
            st.info("Najpierw wybierz badania w zakładce „Wybierz badania”.")
        with tab_demo:
            st.info("Najpierw wybierz badania w zakładce „Wybierz badania”.")
        with tab_segments:
            st.info("Najpierw wybierz badania w zakładce „Wybierz badania”.")
        with tab_strategy:
            st.info("Najpierw wybierz badania w zakładce „Wybierz badania”.")
        return

    person_gender_code = _normalize_matching_gender_code(result.get("person_gender_code"))
    person_role_nom = "polityczka" if person_gender_code == "K" else "polityk"
    person_role_gen = "polityczki" if person_gender_code == "K" else "polityka"
    person_role_nom_cap = "Polityczka" if person_gender_code == "K" else "Polityk"

    with tab_summary:
        st.markdown(
            f"""
            <style>
              .match-target-card{{border:1px solid #d5dfec;border-radius:14px;background:linear-gradient(180deg,#ffffff 0%,#f6f9ff 100%);padding:10px 12px;margin:0 0 10px 0;}}
              .match-target-title{{font-size:13px;font-weight:900;color:#334155;margin:0 0 8px 0;text-transform:uppercase;letter-spacing:.03em;}}
              .match-target-grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px;}}
              .match-target-item{{border:1px solid #dbe4ef;border-radius:12px;background:#fff;padding:8px 10px;}}
              .match-target-item .k{{font-size:12px;font-weight:800;color:#64748b;margin:0 0 2px 0;}}
              .match-target-item .v{{font-size:16px;font-weight:900;color:#1f2f44;line-height:1.28;}}
              @media (max-width:900px){{ .match-target-grid{{grid-template-columns:1fr;}} }}
            </style>
            <div class="match-target-card">
              <div class="match-target-title">Dla kogo liczony jest matching</div>
              <div class="match-target-grid">
                <div class="match-target-item">
                  <div class="k">👤 Badanie personalne</div>
                  <div class="v">{html.escape(str(result['person_label']))}</div>
                </div>
                <div class="match-target-item">
                  <div class="k">🏙️ Badanie mieszkańców</div>
                  <div class="v">{html.escape(str(result['jst_label']))}</div>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        metrics = result.get("match_metrics") or {}
        score_pct = float(result.get("match_score") or 0.0)
        score_pct = max(0.0, min(100.0, score_pct))
        band_label = str(metrics.get("band_label") or "")
        band_desc = str(metrics.get("band_desc") or "")
        if score_pct >= 90:
            score_color = "#0f766e"
            score_bg = "#ecfeff"
        elif score_pct >= 80:
            score_color = "#0e7490"
            score_bg = "#ecfeff"
        elif score_pct >= 70:
            score_color = "#6d28d9"
            score_bg = "#f5f3ff"
        elif score_pct >= 60:
            score_color = "#1d4ed8"
            score_bg = "#eff6ff"
        elif score_pct >= 50:
            score_color = "#b45309"
            score_bg = "#fffbeb"
        elif score_pct >= 40:
            score_color = "#c2410c"
            score_bg = "#fff7ed"
        elif score_pct >= 30:
            score_color = "#be123c"
            score_bg = "#fff1f2"
        else:
            score_color = "#7f1d1d"
            score_bg = "#fef2f2"
        st.markdown(
            f"""
            <style>
              .match-score-card{{border:1px solid #d5dfec;border-radius:12px;background:#ffffff;padding:12px 14px;margin:8px 0 10px 0;}}
              .match-score-title{{font-size:15px;font-weight:800;color:#334155;margin:0 0 4px 0;}}
              .match-score-value{{font-size:46px;line-height:1;font-weight:900;color:#0f172a;margin:0 0 8px 0;}}
              .match-score-badge{{display:inline-block;padding:5px 10px;border-radius:999px;border:1px solid {score_color};background:{score_bg};color:{score_color};font-weight:900;font-size:15px;}}
              .match-score-desc{{margin:8px 0 10px 0;color:#475569;font-size:14px;font-weight:600;}}
              .match-score-track{{height:14px;border-radius:999px;background:#d5dde8;border:1px solid #aebfd3;overflow:hidden;}}
              .match-score-fill{{height:100%;border-radius:999px;background:linear-gradient(90deg,#2563eb 0%,#22c55e 100%);width:{score_pct:.1f}%;}}
              .match-score-scale{{display:flex;justify-content:space-between;color:#64748b;font-size:11px;margin-top:6px;font-weight:700;}}
            </style>
            <div class="match-score-card">
              <div class="match-score-title">Poziom dopasowania</div>
              <div class="match-score-value">{score_pct:.1f}%</div>
              <div class="match-score-badge">Ocena: {html.escape(band_label)}</div>
              <div class="match-score-desc">{html.escape(band_desc)}</div>
              <div class="match-score-track"><div class="match-score-fill"></div></div>
              <div class="match-score-scale"><span>0%</span><span>100%</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if metrics:
            mcol1, mcol2, mcol3, mcol4, mcol5 = st.columns(5)
            mcol1.metric("Średnia różnica (MAE)", f"{float(metrics.get('mae', 0.0)):.1f} pp")
            mcol2.metric("RMSE (kara odchyleń)", f"{float(metrics.get('rmse', 0.0)):.1f} pp")
            mcol3.metric("Średnia TOP3 luk", f"{float(metrics.get('top3_gap_mae', 0.0)):.1f} pp")
            mcol4.metric("Luki kluczowe (TOP P+JST)", f"{float(metrics.get('key_gap_mae', 0.0)):.1f} pp")
            mcol5.metric("Maks. luka kluczowa", f"{float(metrics.get('key_gap_max', 0.0)):.1f} pp")
        st.caption(f"Próba personalna: {result['personal_n']} odpowiedzi · Próba mieszkańców: {result['jst_n']} odpowiedzi")
        sei_short = str(current_sei_short)
        sei_full = str(current_sei_full)
        sei_basis = str(result.get("sei_data_basis") or "dane surowe")

        cmp_rows = []
        for a in JST_ARCHETYPES:
            pol = float(result["personal_profile"].get(a, 0.0))
            ocz = float(result["jst_profile"].get(a, 0.0))
            diff = abs(pol - ocz)
            cmp_rows.append(
                {
                    current_axis_label: _matching_entity_name(a, current_axis_label, person_gender_code),
                    f"Profil {person_role_gen}": round(pol, 1),
                    f"Oczekiwania mieszkańców ({sei_short})": round(ocz, 1),
                    "Różnica |Δ|": round(diff, 1),
                    "__sort_diff": diff,
                }
            )
        df_cmp = pd.DataFrame(cmp_rows).sort_values("__sort_diff", ascending=True).drop(columns="__sort_diff")
        cmp_rows_n = len(df_cmp.index)
        cmp_height = max(92, min(760, 40 + cmp_rows_n * 35))
        ocz_col = f"Oczekiwania mieszkańców ({sei_short})"
        person_profile_col = f"Profil {person_role_gen}"
        cmp_col_config = {
            person_profile_col: st.column_config.NumberColumn(person_profile_col, format="%.1f"),
            ocz_col: st.column_config.NumberColumn(ocz_col, format="%.1f"),
            "Różnica |Δ|": st.column_config.NumberColumn("Różnica |Δ|", format="%.1f"),
        }
        try:
            st.dataframe(
                df_cmp,
                use_container_width=True,
                hide_index=True,
                height=cmp_height,
                column_config=cmp_col_config,
            )
        except TypeError:
            st.dataframe(
                df_cmp,
                use_container_width=True,
                hide_index=True,
                height=cmp_height,
            )
        st.caption(update_matching_summary_description(sei_short, sei_full, sei_basis))
        with st.expander("Jak liczony jest poziom dopasowania?", expanded=False):
            st.markdown(result.get("match_formula", ""))
            st.info(
                "To równanie dotyczy wyłącznie wskaźnika `Poziom dopasowania` i NIE służy do liczenia "
                f"kolumny `Oczekiwania mieszkańców ({sei_short})`."
            )
            st.markdown(
                "Metryka celowo mocniej karze strategiczne rozjazdy: oprócz MAE, RMSE i średniej 3 największych luk "
                f"uwzględnia też luki na archetypach kluczowych (unia priorytetów {person_role_gen} i mieszkańców) "
                "oraz dodatkowe kary za skrajny rozjazd w tej puli, brak wspólnych priorytetów i różny priorytet główny."
            )
            st.markdown(
                "**Progi oceny (wynik bazowy):** "
                "`0–29` marginalne dopasowanie, `30–39` bardzo niskie, `40–49` niskie, `50–59` umiarkowane, "
                "`60–69` znaczące, `70–79` wysokie, `80–89` bardzo wysokie, `90–100` ekstremalnie wysokie. "
                "Duże luki kluczowe (`KEY_MAE`/`KEY_MAX`) są dodatkowo sygnalizowane w opisie jakościowym."
            )
            st.caption(
                "W modelu nie ma osobnej premii dodatniej za zgodność. Lepszy wynik wynika wyłącznie z niższych luk i mniejszej kary kluczowej."
            )
            if metrics:
                key_list = metrics.get("key_archetypes") or []
                key_list_txt = ", ".join(
                    [_matching_entity_name(str(a), current_axis_label, person_gender_code) for a in key_list]
                ) if isinstance(key_list, list) and key_list else "brak"
                st.markdown(
                    f"**Składowe dla tego porównania:** "
                    f"MAE `{float(metrics.get('mae', 0.0)):.1f} pp`, "
                    f"RMSE `{float(metrics.get('rmse', 0.0)):.1f} pp`, "
                    f"TOP3_MAE `{float(metrics.get('top3_gap_mae', 0.0)):.1f} pp`, "
                    f"KEY_MAE `{float(metrics.get('key_gap_mae', 0.0)):.1f} pp`, "
                    f"KEY_MAX `{float(metrics.get('key_gap_max', 0.0)):.1f} pp`, "
                    f"kara kluczowa `{float(metrics.get('key_penalty', 0.0)):.1f}`."
                )
                st.markdown(
                    "**Archetypy kluczowe (TOP3, ale gdy 3. pozycja <70 -> TOP2):** "
                    f"{key_list_txt}."
                )
            axis_entity_gen = "wartości" if current_axis_label == "Wartość" else "archetypu"
            st.markdown(f"**Jak liczony jest `{sei_full}`?**")
            st.markdown(
                f"- `A`: odsetek respondentów z dodatnim bilansem oczekiwania dla {axis_entity_gen} (`score_mean > 0`) w versusach A.\n"
                f"- `B1`: odsetek osób, które wskazały {axis_entity_gen} w TOP3.\n"
                f"- `B2`: odsetek osób, które wskazały {axis_entity_gen} jako TOP1.\n"
                f"- `N`: odsetek negatywnych doświadczeń dla {axis_entity_gen} (C13/D13).\n"
                "- `MBAL`: bilans najważniejszego doświadczenia (C13/D13), liczony jako `Mneg - Mpos`.\n"
                "- Odchylenia od poziomów neutralnych: `delta_B1 = B1 - 25.0`, `delta_B2 = B2 - 8.3333333333`, `delta_N = N - 50.0`.\n"
                "- Korekta wariantu B: `K_B = 0.35*delta_B1 + 0.90*delta_B2 + 0.08*delta_N + 0.20*MBAL`.\n"
                "- Wynik końcowy: `SEI_B = A + K_B`.\n"
                "- Skala końcowa: `SEI_B_100 = clamp(SEI_B, 0..100)` (bez min-max)."
            )
            audit = result.get("target_audit") or {}
            if audit:
                if not bool(audit.get("components_aligned", True)):
                    st.warning(
                        "Komponenty A/B1/B2/C13-D13 nie zostały zmapowane do identycznego zestawu 12 pozycji. "
                        "Sprawdź kompletność danych wejściowych."
                    )
                st.markdown(
                    f"**Audyt danych wejściowych:** A valid `{float(audit.get('a_valid_rate_pct', 0.0)):.1f}%`, "
                    f"B1 valid `{float(audit.get('b1_valid_rate_pct', 0.0)):.1f}%`, "
                    f"B2 valid `{float(audit.get('b2_valid_rate_pct', 0.0)):.1f}%`, "
                    f"D13 valid `{float(audit.get('d13_valid_rate_pct', 0.0)):.1f}%`, "
                    f"średnia liczba wskazań B1: `{float(audit.get('b1_mean_selected', 0.0)):.2f}`."
                )
                comp = audit.get("component_means_by_archetype") or {}
                if isinstance(comp, dict) and comp:
                    comp_rows: List[Dict[str, str]] = []
                    def _fmt_cell(val: Any, digits: int) -> str:
                        try:
                            fval = float(val)
                        except Exception:
                            return "—"
                        if not math.isfinite(fval):
                            return "—"
                        return f"{fval:.{digits}f}"
                    for a in JST_ARCHETYPES:
                        row = comp.get(a) or {}
                        comp_rows.append(
                            {
                                current_axis_label: _matching_entity_name(a, current_axis_label, person_gender_code),
                                "A (% oczekujących)": _fmt_cell(row.get("A"), 1),
                                "B1: TOP3 (%)": _fmt_cell(row.get("B1"), 1),
                                "B2: TOP1 (%)": _fmt_cell(row.get("B2"), 1),
                                "C13/D13: negatywne doświadczenie (%)": _fmt_cell(row.get("N"), 1),
                                "C13/D13: Mneg (%)": _fmt_cell(row.get("Mneg"), 1),
                                "C13/D13: Mpos (%)": _fmt_cell(row.get("Mpos"), 1),
                                "C13/D13: bilans najważniejszego doświadczenia": _fmt_cell(row.get("MBAL"), 1),
                                "delta_B1": _fmt_cell(row.get("delta_B1"), 2),
                                "delta_B2": _fmt_cell(row.get("delta_B2"), 2),
                                "delta_N": _fmt_cell(row.get("delta_N"), 2),
                                "Korekta wariantu B": _fmt_cell(row.get("K_B"), 2),
                                "SEI_B": _fmt_cell(row.get("SEI_raw"), 2),
                                f"{sei_short} 0-100": _fmt_cell(row.get("SEI_100"), 1),
                            }
                        )
                    st.dataframe(
                        pd.DataFrame(comp_rows),
                        use_container_width=True,
                        hide_index=True,
                        height=max(92, min(520, 40 + len(comp_rows) * 35)),
                    )
                    missing_counts = audit.get("component_missing_counts") or {}
                    if isinstance(missing_counts, dict):
                        missing_bits = [
                            f"{k}: {int(v)}"
                            for k, v in missing_counts.items()
                            if int(v or 0) > 0
                        ]
                        if missing_bits:
                            st.warning(
                                "Część komponentów ma braki danych dla wybranych archetypów/wartości "
                                f"({', '.join(missing_bits)}). "
                                "Indeks jest liczony dalej: brakujące komponenty działają jako neutralna korekta."
                            )
        strengths_rows = result.get("strengths_rows") or []
        gaps_rows = result.get("gaps_rows") or []
        strength_items_html = "".join(
            [
                f"<span class='match-chip good'>{html.escape(_matching_entity_name(str(r.get('archetyp') or ''), current_axis_label, person_gender_code))} "
                f"<small>|Δ| {float(r.get('diff', 0.0)):.1f} pp</small></span>"
                for r in strengths_rows
            ]
        )
        gap_items_html = "".join(
            [
                f"<span class='match-chip gap'>{html.escape(_matching_entity_name(str(r.get('archetyp') or ''), current_axis_label, person_gender_code))} "
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

        st.markdown(
            """
            <style>
              .match-section-header{
                border:none;
                border-top:1px solid #d9e2ef;
                border-radius:0;
                background:transparent;
                padding:12px 0 0 0;
                margin:18px 0 10px 0;
              }
              .match-section-header.match-compare-header{
                margin:8px 0 0 0;
              }
              .match-section-header.match-profile-header{
                margin-top:30px;
              }
              .match-section-header h3{
                margin:0;
                font-size:21px;
                font-weight:800;
                color:#1f2f44;
              }
              .match-profile-title{
                text-align:center;
                font-weight:800;
                font-size:16px;
                line-height:1.2;
                color:#1f2f44;
                margin:2px 0 8px 0;
              }
              .match-top3-compare{
                display:grid;
                grid-template-columns:1fr 1fr;
                gap:12px;
                margin:14px 0 10px 0;
              }
              .match-top3-card{
                border:1px solid #d9e2ef;
                border-radius:14px;
                background:#ffffff;
                padding:12px 12px 10px 12px;
                box-shadow:0 2px 6px rgba(15,23,42,.06);
              }
              .match-top3-card h4{
                margin:0 0 8px 0;
                font-size:14px;
                color:#1f2f44;
                font-weight:900;
              }
              .match-top3-row{
                display:grid;
                grid-template-columns:118px 1fr;
                gap:8px;
                align-items:center;
                margin:7px 0;
              }
              .match-top3-rank{
                width:118px;
                text-align:center;
                font-size:11px;
                font-weight:900;
                letter-spacing:.02em;
                border-radius:999px;
                padding:6px 8px;
                border:1px solid transparent;
              }
              .match-r-main{background:#fff1f0;color:#d7263d;border-color:#f6c1c0;}
              .match-r-aux{background:#fff9df;color:#8a6a00;border-color:#f4e5a0;}
              .match-r-supp{background:#eefbea;color:#1b7f3c;border-color:#b8e6c9;}
              .match-top3-name{
                flex:1;
                font-weight:800;
                font-size:14px;
                border:1px solid #dbe4ef;
                border-radius:999px;
                padding:6px 12px;
                background:#f8fbff;
                display:inline-flex;
                align-items:center;
                gap:8px;
              }
              .match-top3-name.match-r-main{color:#d7263d;}
              .match-top3-name.match-r-aux{color:#8a6a00;}
              .match-top3-name.match-r-supp{color:#1b7f3c;}
              .match-top3-icon{
                display:inline-flex;
                align-items:center;
                justify-content:center;
                width:18px;
                min-width:18px;
                height:18px;
                line-height:1;
              }
              .match-top3-icon-img{
                width:18px;
                height:18px;
                object-fit:contain;
                display:block;
              }
              .match-radar-legend{
                display:flex;
                justify-content:center;
                gap:12px;
                flex-wrap:wrap;
                margin:2px 0 2px 0;
              }
              .match-radar-pill{
                display:inline-flex;
                align-items:center;
                gap:8px;
                border:1px solid #dbe4ef;
                background:#fff;
                border-radius:999px;
                padding:8px 16px;
                font-size:13px;
                font-weight:700;
                color:#1f2f44;
              }
              .match-radar-line{
                width:30px;
                height:0;
                border-top:3px solid #2563eb;
                display:inline-block;
              }
              .match-radar-line.dashed{
                border-top:3px dashed #0f766e;
              }
              .match-top3-style-grid{
                display:grid;
                grid-template-columns:1fr 1fr;
                gap:12px;
                margin:-18px 0 4px 0;
              }
              .match-top3-style-card{
                border:1px solid #dbe4ef;
                border-radius:12px;
                background:#fff;
                padding:10px 12px;
                text-align:center;
              }
              .match-top3-style-card .title{
                font-size:13px;
                font-weight:500;
                color:#1f2f44;
                margin-bottom:4px;
              }
              .match-top3-style-card .line2{
                display:flex;
                align-items:center;
                justify-content:center;
                gap:18px;
                flex-wrap:wrap;
                font-size:14px;
                font-weight:700;
                line-height:1.35;
              }
              .match-top3-style-card .line2 span{
                white-space:nowrap;
              }
              .js-plotly-plot .legend rect.bg{
                rx:10px !important;
                ry:10px !important;
              }
              .match-wheel-legend-wrap{
                margin-top:6px;
                display:flex;
                justify-content:center;
              }
              .match-wheel-legend{
                display:flex;
                justify-content:center;
                gap:20px;
                flex-wrap:wrap;
                align-items:center;
                border:1px solid #dbe4ef;
                border-radius:12px;
                background:#fff;
                padding:8px 14px;
              }
              .match-wheel-legend span{
                display:inline-flex;
                align-items:center;
                gap:7px;
                font-size:13px;
                color:#334155;
                font-weight:700;
              }
              .match-wheel-legend i{
                width:10px;
                height:10px;
                border-radius:2px;
                display:inline-block;
              }
              @media (max-width: 900px){
                .match-top3-compare{grid-template-columns:1fr;}
                .match-top3-style-grid{grid-template-columns:1fr;}
              }
            </style>
            """,
            unsafe_allow_html=True,
        )
        person_name = str(result.get("person_name_nom") or result.get("person_label") or person_role_nom_cap)
        jst_name = str(result.get("jst_name_nom") or result.get("jst_label") or "JST")
        person_name_gen = str(result.get("person_name_gen") or "").strip() or person_name
        jst_name_gen = str(result.get("jst_name_gen") or "").strip() or jst_name
        person_sid = str(result.get("person_study_id") or "")
        jst_sid = str(result.get("jst_study_id") or "")

        person_profile_100 = {a: float(result["personal_profile"].get(a, 0.0)) for a in JST_ARCHETYPES}
        jst_profile_100 = {a: float(result["jst_profile"].get(a, 0.0)) for a in JST_ARCHETYPES}

        radar_order: List[str] = [
            "Buntownik", "Błazen", "Kochanek", "Opiekun", "Towarzysz", "Niewinny",
            "Władca", "Mędrzec", "Czarodziej", "Bohater", "Twórca", "Odkrywca",
        ]
        radar_tick_labels: List[str] = [_matching_entity_name(a, current_axis_label, person_gender_code) for a in radar_order]
        person_profile_20 = {a: float(person_profile_100.get(a, 0.0)) / 5.0 for a in radar_order}
        jst_profile_20 = {a: float(jst_profile_100.get(a, 0.0)) / 5.0 for a in radar_order}

        def _priority_top_for_ui(profile_100: Dict[str, float], order: List[str]) -> List[str]:
            ordered = sorted(order, key=lambda a: (-float(profile_100.get(a, 0.0)), order.index(a)))
            top3 = ordered[:3]
            if len(top3) >= 3 and float(profile_100.get(top3[2], 0.0)) < 70.0:
                return top3[:2]
            return top3

        p_top = _priority_top_for_ui(person_profile_100, radar_order)
        j_top = _priority_top_for_ui(jst_profile_100, radar_order)
        radar_top_union = set(p_top + j_top)
        radar_tick_text: List[str] = []
        for arche, lbl in zip(radar_order, radar_tick_labels):
            safe_lbl = html.escape(str(lbl))
            radar_tick_text.append(f"<b>{safe_lbl}</b>" if arche in radar_top_union else safe_lbl)
        entity_gen = "archetypów" if current_axis_label == "Archetyp" else "wartości"
        rank_names = ["Główny", "Wspierający", "Poboczny"]
        p_top_label = f"TOP{max(1, len(p_top))} {person_role_gen}"
        j_top_label = f"TOP{max(1, len(j_top))} mieszkańców"
        person_top_colors = {"main": "#ef4444", "aux": "#facc15", "supp": "#22c55e"}
        jst_top_colors = {"main": "#2563eb", "aux": "#a855f7", "supp": "#f97316"}

        def _role_legend_html(palette: Dict[str, str], marker: str, count: int) -> str:
            role_defs = [("główny", "main"), ("wspierający", "aux"), ("poboczny", "supp")]
            items: List[str] = []
            for idx, (label, role_key) in enumerate(role_defs):
                if idx >= max(0, int(count)):
                    break
                items.append(
                    f"<span><span style=\"color:{palette[role_key]};\">{marker}</span> {label}</span>"
                )
            return "".join(items)

        p_role_legend = _role_legend_html(person_top_colors, "●", len(p_top))
        j_role_legend = _role_legend_html(jst_top_colors, "■", len(j_top))

        def _top3_compare_card(title: str, items: List[str]) -> str:
            rows: List[str] = []
            for idx, item in enumerate(items[:3]):
                item_label = _matching_entity_name(str(item), current_axis_label, person_gender_code)
                item_icon_html = _matching_entity_icon_html(str(item), current_axis_label)
                rank_class = "match-r-main" if idx == 0 else ("match-r-aux" if idx == 1 else "match-r-supp")
                rows.append(
                    "<div class='match-top3-row'>"
                    f"<span class='match-top3-rank {rank_class}'>{html.escape(rank_names[idx])}</span>"
                    f"<span class='match-top3-name {rank_class}'><span class='match-top3-icon'>{item_icon_html}</span>{html.escape(item_label)}</span>"
                    "</div>"
                )
            if not rows:
                rows.append("<div class='match-top3-row'><span class='match-top3-name'>Brak danych</span></div>")
            return (
                "<div class='match-top3-card'>"
                f"<h4>{html.escape(title)}</h4>"
                + "".join(rows)
                + "</div>"
            )

        st.markdown(
            "<div class='match-top3-compare'>"
            + _top3_compare_card(
                f"TOP{max(1, len(p_top))} {entity_gen} dla {person_name_gen}",
                p_top,
            )
            + _top3_compare_card(
                f"TOP{max(1, len(j_top))} {entity_gen} dla {jst_name_gen}",
                j_top,
            )
            + "</div>",
            unsafe_allow_html=True,
        )
        diff_by_entity: Dict[str, float] = {
            a: abs(float(person_profile_100.get(a, 0.0)) - float(jst_profile_100.get(a, 0.0)))
            for a in JST_ARCHETYPES
        }
        key_union: List[str] = []
        for arche in p_top + j_top:
            if arche not in key_union:
                key_union.append(arche)
        key_gap_vals_live = [float(diff_by_entity.get(a, 0.0)) for a in key_union]
        key_gap_mae_live = float(sum(key_gap_vals_live) / max(1, len(key_gap_vals_live)))
        key_max_entity = max(
            key_union or list(diff_by_entity.keys()),
            key=lambda a: float(diff_by_entity.get(a, 0.0)),
        )
        key_max_gap_live = float(diff_by_entity.get(key_max_entity, 0.0))
        best_entity = min(diff_by_entity.keys(), key=lambda a: float(diff_by_entity.get(a, 0.0)))
        best_gap_live = float(diff_by_entity.get(best_entity, 0.0))
        strongest_fit_entities = sorted(diff_by_entity.keys(), key=lambda a: float(diff_by_entity.get(a, 0.0)))[:3]
        largest_gap_entities = sorted(diff_by_entity.keys(), key=lambda a: float(diff_by_entity.get(a, 0.0)), reverse=True)[:3]
        # Priorytetowo bierzemy dokładnie te same listy, które są pokazane w chipach
        # "Najlepsze dopasowania" i "Największe luki", żeby nie było rozjazdu narracji.
        strengths_src = strengths_rows if isinstance(strengths_rows, list) else []
        gaps_src = gaps_rows if isinstance(gaps_rows, list) else []

        def _safe_src_names(rows: List[Any]) -> List[str]:
            names: List[str] = []
            for row in rows:
                raw = ""
                if isinstance(row, dict):
                    raw = str(row.get("archetyp") or row.get("entity") or row.get("name") or "").strip()
                else:
                    raw = str(row or "").strip()
                if raw:
                    names.append(raw)
            return names

        src_best_names = _safe_src_names(strengths_src) if strengths_src else []
        src_gap_names = _safe_src_names(gaps_src) if gaps_src else []
        if not src_best_names:
            src_best_names = strongest_fit_entities
        if not src_gap_names:
            src_gap_names = largest_gap_entities
        overlap_top = [a for a in p_top if a in j_top]

        advantages: List[str] = []
        problems: List[str] = []
        axis_gen = "archetypach" if current_axis_label == "Archetyp" else "wartościach"

        if p_top and j_top and p_top[0] == j_top[0]:
            main_name = _matching_entity_name(p_top[0], current_axis_label, person_gender_code)
            advantages.append(f"Zgodny priorytet główny: {main_name}.")
        elif p_top and j_top:
            p_main = _matching_entity_name(p_top[0], current_axis_label, person_gender_code)
            j_main = _matching_entity_name(j_top[0], current_axis_label, person_gender_code)
            problems.append(f"Różny priorytet główny: {person_role_nom} stawia na {p_main}, mieszkańcy na {j_main}.")

        if overlap_top:
            overlap_txt = ", ".join(_matching_entity_name(a, current_axis_label, person_gender_code) for a in overlap_top)
            overlap_total = max(1, min(len(p_top), len(j_top)))
            advantages.append(f"Wspólne priorytety ({len(overlap_top)}/{overlap_total}): {overlap_txt}.")
        else:
            problems.append(f"Brak wspólnych pozycji w priorytetach {person_role_gen} i mieszkańców.")

        # Jeśli priorytety (TOP2/TOP3) pokrywają się z najlepszymi / największymi lukami,
        # pokazujemy to jawnie w sekcji zalet/problemów.
        def _canon_name(name: str) -> str:
            raw_name = str(name or "").strip()
            if str(current_axis_label) == "Wartość":
                raw_name = str(_JST_ARCH_BY_VALUE.get(raw_name, raw_name))
            raw_name = str(_MATCHING_MASC_FROM_FEM.get(raw_name, raw_name))
            return slugify(raw_name).lower()

        priority_for_checks: List[str] = []
        for arche in p_top + j_top:
            if arche not in priority_for_checks:
                priority_for_checks.append(arche)
        # Łączymy nazwy z aktualnie wyrenderowanych chipów oraz z list live
        # wyliczonych z bieżącej tabeli różnic. Dzięki temu overlap TOP<->luki/
        # TOP<->najlepsze dopasowania nie zależy od formatu źródłowych nazw.
        best_names_for_check = list(src_best_names) + list(strongest_fit_entities)
        gaps_names_for_check = list(src_gap_names) + list(largest_gap_entities)
        best_canon = {_canon_name(a) for a in best_names_for_check if str(a or "").strip()}
        gaps_canon = {_canon_name(a) for a in gaps_names_for_check if str(a or "").strip()}
        priority_in_best = [a for a in priority_for_checks if _canon_name(a) in best_canon]
        priority_in_gaps = [a for a in priority_for_checks if _canon_name(a) in gaps_canon]
        _delta_nbsp = lambda diff: f"(|Δ| {float(diff):.1f} pp)"
        _delta_re = re.compile(r"\(\|Δ\|[\s\u00a0]*([-+]?\d+(?:[.,]\d+)?)\s*pp\)")

        def _render_eval_line_html(raw_text: str) -> str:
            safe = html.escape(str(raw_text or ""))
            return _delta_re.sub(
                lambda m: f"<span class='match-delta-nowrap'>(|Δ| {m.group(1)} pp)</span>",
                safe,
            )

        if priority_in_best:
            best_priority_txt = ", ".join(
                f"{_matching_entity_name(a, current_axis_label, person_gender_code)} {_delta_nbsp(diff_by_entity.get(a, 0.0))}"
                for a in priority_in_best
            )
            advantages.insert(0, f"Priorytetowe pozycje są też wśród najlepszych dopasowań: {best_priority_txt}.")

        if priority_in_gaps:
            gap_priority_txt = ", ".join(
                f"{_matching_entity_name(a, current_axis_label, person_gender_code)} {_delta_nbsp(diff_by_entity.get(a, 0.0))}"
                for a in priority_in_gaps
            )
            problems.insert(0, f"Priorytetowe pozycje są też wśród największych luk: {gap_priority_txt}.")

        if key_gap_mae_live <= 10.0:
            advantages.append(f"Średnia luka na kluczowych {axis_gen} jest niska ({key_gap_mae_live:.1f} pp).")
        elif key_gap_mae_live >= 16.0:
            problems.append(f"Średnia luka na kluczowych {axis_gen} jest wysoka ({key_gap_mae_live:.1f} pp).")

        if key_max_gap_live >= 20.0:
            key_max_name = _matching_entity_name(key_max_entity, current_axis_label, person_gender_code)
            problems.append(f"Największa luka kluczowa: {key_max_name} {_delta_nbsp(key_max_gap_live)}.")

        best_name = _matching_entity_name(best_entity, current_axis_label, person_gender_code)
        advantages.append(f"Najlepsza zgodność dotyczy pozycji {best_name} {_delta_nbsp(best_gap_live)}.")

        if not advantages:
            advantages = ["Brak wyraźnych przewag w tym porównaniu — potrzebna dalsza kalibracja przekazu."]
        if not problems:
            problems = ["Brak krytycznych rozjazdów na kluczowych pozycjach."]

        adv_items_html = "".join(
            [f"<li><span class='badge'>✓</span><span>{_render_eval_line_html(txt)}</span></li>" for txt in advantages[:4]]
        )
        prob_items_html = "".join(
            [f"<li><span class='badge'>!</span><span>{_render_eval_line_html(txt)}</span></li>" for txt in problems[:4]]
        )
        st.markdown(
            f"""
            <style>
              .match-eval-grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:10px 0 8px 0;}}
              .match-eval-card{{border:1px solid #d9e2ef;border-radius:14px;background:#fff;padding:12px 14px;}}
              .match-eval-card.good{{box-shadow:inset 0 3px 0 #10b981;}}
              .match-eval-card.warn{{box-shadow:inset 0 3px 0 #ef4444;}}
              .match-eval-title{{margin:0 0 8px 0;font-size:14px;font-weight:900;color:#1f2f44;}}
              .match-eval-list{{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:7px;}}
              .match-eval-list li{{display:grid;grid-template-columns:22px 1fr;gap:8px;align-items:start;color:#334155;font-size:13px;font-weight:700;line-height:1.35;}}
              .match-eval-list .badge{{display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;border-radius:999px;font-size:12px;font-weight:900;}}
              .match-delta-nowrap{{white-space:nowrap;display:inline-block;}}
              .match-eval-card.good .badge{{background:#e8fbf1;color:#0f7a48;border:1px solid #b9eed3;}}
              .match-eval-card.warn .badge{{background:#fff1f2;color:#b91c1c;border:1px solid #fecdd3;}}
              @media (max-width:900px){{.match-eval-grid{{grid-template-columns:1fr;}}}}
            </style>
            <div class="match-eval-grid">
              <div class="match-eval-card good">
                <div class="match-eval-title">Główne zalety</div>
                <ul class="match-eval-list">{adv_items_html}</ul>
              </div>
              <div class="match-eval-card warn">
                <div class="match-eval-title">Główne problemy</div>
                <ul class="match-eval-list">{prob_items_html}</ul>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        compare_title = "Porównanie profili archetypowych" if current_axis_label == "Archetyp" else "Porównanie profili wartości"
        st.markdown(f"<div class='match-section-header match-compare-header'><h3>{html.escape(compare_title)}</h3></div>", unsafe_allow_html=True)

        def _marker_series(profile: Dict[str, float], top3: List[str], palette: Dict[str, str]) -> Tuple[List[Optional[float]], List[str]]:
            r_vals: List[Optional[float]] = []
            colors: List[str] = []
            mapping: Dict[str, str] = {}
            if len(top3) > 0:
                mapping[top3[0]] = palette["main"]
            if len(top3) > 1:
                mapping[top3[1]] = palette["aux"]
            if len(top3) > 2:
                mapping[top3[2]] = palette["supp"]
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
        legend_person_label = f"\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0profil {person_role_gen} ({person_name})\u00a0\u00a0\u00a0"
        legend_jst_label = f"\u00a0\u00a0\u00a0\u00a0\u00a0\u00a0profil mieszkańców ({jst_name})\u00a0\u00a0\u00a0"

        fig_cmp = go.Figure(
            data=[
                go.Scatterpolar(
                    r=person_vals + [person_vals[0]],
                    theta=radar_tick_labels + [radar_tick_labels[0]],
                    fill="toself",
                    fillcolor="rgba(37,99,235,0.18)",
                    line=dict(color="#2563eb", width=3),
                    marker=dict(size=5, symbol="circle"),
                    name=legend_person_label,
                    showlegend=True,
                    hovertemplate=f"<b>%{{theta}}</b><br>{person_role_nom_cap}: %{{r:.2f}}<extra></extra>",
                ),
                go.Scatterpolar(
                    r=jst_vals + [jst_vals[0]],
                    theta=radar_tick_labels + [radar_tick_labels[0]],
                    fill="toself",
                    fillcolor="rgba(15,118,110,0.16)",
                    line=dict(color="#0f766e", width=3, dash="dot"),
                    marker=dict(size=6, symbol="square"),
                    name=legend_jst_label,
                    showlegend=True,
                    hovertemplate="<b>%{theta}</b><br>Mieszkańcy: %{r:.2f}<extra></extra>",
                ),
                go.Scatterpolar(
                    r=p_marker_r,
                    theta=radar_tick_labels,
                    mode="markers",
                    marker=dict(size=16, symbol="circle", color=p_marker_c, opacity=0.92, line=dict(color="black", width=2.6)),
                    name=p_top_label,
                    showlegend=False,
                    hovertemplate=f"<b>%{{theta}}</b><br>{p_top_label}: %{{r:.2f}}<extra></extra>",
                ),
                go.Scatterpolar(
                    r=j_marker_r,
                    theta=radar_tick_labels,
                    mode="markers",
                    marker=dict(size=14, symbol="square", color=j_marker_c, opacity=0.94, line=dict(color="#0f172a", width=2.0)),
                    name=j_top_label,
                    showlegend=False,
                    hovertemplate=f"<b>%{{theta}}</b><br>{j_top_label}: %{{r:.2f}}<extra></extra>",
                ),
            ]
        )
        fig_cmp.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            height=640,
            polar=dict(
                bgcolor="rgba(0,0,0,0)",
                radialaxis=dict(visible=True, range=[0, 20]),
                angularaxis=dict(
                    tickfont=dict(size=16),
                    tickvals=radar_tick_labels,
                    ticktext=radar_tick_text,
                    rotation=90,
                    direction="clockwise",
                ),
            ),
            margin=dict(l=24, r=24, t=66, b=90),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.16,
                xanchor="center",
                x=0.5,
                font=dict(size=13.5),
                bgcolor="rgba(255,255,255,0.94)",
                bordercolor="#cfd9e8",
                borderwidth=1,
                entrywidthmode="pixels",
                entrywidth=232,
                tracegroupgap=28,
                itemclick="toggle",
                itemdoubleclick="toggleothers",
            ),
        )
        st.plotly_chart(
            fig_cmp,
            use_container_width=True,
            config={"displaylogo": False, "displayModeBar": False, "responsive": True},
            key=f"matching-radar-compare-{person_sid}-{jst_sid}",
        )
        st.markdown(
            f"""
            <div class="match-top3-style-grid">
              <div class="match-top3-style-card">
                <div class="title">{html.escape(p_top_label)}</div>
                <div class="line2">{p_role_legend}</div>
              </div>
              <div class="match-top3-style-card">
                <div class="title">{html.escape(j_top_label)}</div>
                <div class="line2">{j_role_legend}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        profile_title = (
            "Profile archetypowe 0-100 (siła archetypu, skala: 0-100)"
            if current_axis_label == "Archetyp"
            else "Profile wartości 0-100 (siła wartości, skala: 0-100)"
        )
        st.markdown(f"<div class='match-section-header match-profile-header'><h3>{html.escape(profile_title)}</h3></div>", unsafe_allow_html=True)
        left_profile_col, right_profile_col = st.columns(2, gap="large")
        try:
            import admin_dashboard as AD
            p_key = re.sub(r"[^a-zA-Z0-9_-]+", "_", person_sid or "person")
            j_key = re.sub(r"[^a-zA-Z0-9_-]+", "_", jst_sid or "jst")
            person_profile_img = AD.make_segment_profile_wheel_png(
                mean_scores=person_profile_100,
                out_path=f"matching_profile_person_{p_key}_{j_key}.png",
                label_mode=("values" if current_axis_label == "Wartość" else "arche"),
                gender_code=person_gender_code,
            )
            jst_profile_img = AD.make_segment_profile_wheel_png(
                mean_scores=jst_profile_100,
                out_path=f"matching_profile_jst_{j_key}_{p_key}.png",
                label_mode=("values" if current_axis_label == "Wartość" else "arche"),
                gender_code=person_gender_code,
            )

            def _show_image_compat(img_path: str, max_width_px: int = 560) -> None:
                try:
                    st.image(img_path, width=max_width_px)
                except TypeError:
                    st.image(img_path, use_column_width=True)

            with left_profile_col:
                st.markdown(
                    f"<div class='match-profile-title'>"
                    f"{'Profil archetypowy' if current_axis_label == 'Archetyp' else 'Profil wartości'} {html.escape(str(person_name_gen or ''))}"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                _show_image_compat(person_profile_img, max_width_px=520)
            with right_profile_col:
                st.markdown(
                    f"<div class='match-profile-title'>"
                    f"{'Profil archetypowy mieszkańców' if current_axis_label == 'Archetyp' else 'Profil wartości mieszkańców'} {html.escape(str(jst_name_gen or ''))}"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                _show_image_compat(jst_profile_img, max_width_px=520)
            st.markdown(
                """
                <div class="match-wheel-legend-wrap">
                  <div class="match-wheel-legend">
                    <span><i style="background:#e53935"></i>Zmiana</span>
                    <span><i style="background:#1e88e5"></i>Ludzie</span>
                    <span><i style="background:#2e7d32"></i>Porządek</span>
                    <span><i style="background:#7e57c2"></i>Niezależność</span>
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        except Exception as e:
            st.info(f"Nie udało się wygenerować porównania kół 0-100: {e}")

    with tab_demo:
        demo_person_name = str(result.get("person_name_nom") or result.get("person_label") or "").strip()
        demo_jst_name = str(result.get("jst_name_nom") or result.get("jst_label") or "").strip()
        if demo_person_name or demo_jst_name:
            st.markdown(
                """
                <style>
                  .match-demo-context{
                    display:inline-flex;
                    align-items:center;
                    gap:8px;
                    flex-wrap:wrap;
                    padding:7px 12px;
                    border:1px solid #dbe4ef;
                    border-radius:999px;
                    background:#f8fbff;
                    margin:0 0 8px 0;
                  }
                  .match-demo-context-label{
                    font-size:12.5px;
                    font-weight:800;
                    color:#64748b;
                    letter-spacing:.02em;
                    text-transform:uppercase;
                  }
                  .match-demo-context-item{
                    font-size:14px;
                    font-weight:700;
                    color:#1f2f44;
                  }
                  .match-demo-context-sep{
                    font-size:13px;
                    font-weight:700;
                    color:#94a3b8;
                    margin:0 2px;
                  }
                </style>
                """,
                unsafe_allow_html=True,
            )
            st.markdown(
                f"""
                <div class="match-demo-context">
                  <span class="match-demo-context-label">Kontekst</span>
                  <span class="match-demo-context-item">{person_role_nom_cap}: {html.escape(demo_person_name or "—")}</span>
                  <span class="match-demo-context-sep">•</span>
                  <span class="match-demo-context-item">JST: {html.escape(demo_jst_name or "—")}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        st.markdown(f"Demografia grupy mieszkańców najbardziej dopasowanej do profilu {person_role_gen} (top 25% podobieństwa).")
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
              .match-demo-box.match-demo-profile-box{padding-top:15px;padding-left:25px;}
              .match-demo-table{margin-top:0;width:100%;min-width:720px;max-width:940px;border-collapse:collapse;border:3px solid #b8c2cc;background:#fff;font-size:13.5px;color:#334155;}
              .match-demo-table th,.match-demo-table td{padding:8px 10px;border:1px solid #dfe4ea;text-align:left;vertical-align:middle;}
              .match-demo-table th{background:#f2f6fb;color:#1f2f44;font-weight:800;font-size:13.5px;}
              @media (max-width:900px){ .match-demo-box.match-demo-profile-box{padding:12px 12px 10px 12px;} }
            </style>
            """,
            unsafe_allow_html=True,
        )
        demo_specs = [dict(x) for x in list(result.get("demo_specs") or []) if isinstance(x, dict)]
        if not demo_specs:
            demo_specs = _matching_demo_build_specs(None)
        spec_by_label = {
            str(spec.get("label") or "").strip(): spec
            for spec in demo_specs
            if str(spec.get("label") or "").strip()
        }
        variable_emoji = {
            str(spec.get("label") or "").strip(): str(spec.get("variable_emoji") or "📌")
            for spec in demo_specs
            if str(spec.get("label") or "").strip()
        }
        cards = result.get("demo_cards") or []
        if cards:
            cards_html = "".join(
                f"""
                <div class="match-demo-stat">
                  <div class="match-demo-stat-label">{html.escape(str(c.get("variable_emoji") or variable_emoji.get(str(c.get("label") or ""), "📌")))} {html.escape(str(c.get("label") or "").upper())}</div>
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
            if "KategoriaKod" not in ddf.columns:
                ddf["KategoriaKod"] = ddf["Kategoria"].astype(str)
            ddf["% grupa dopasowana"] = pd.to_numeric(ddf["% grupa dopasowana"], errors="coerce").fillna(0.0).round(1)
            ddf["% ogół mieszkańców (ważony)"] = pd.to_numeric(ddf["% ogół mieszkańców (ważony)"], errors="coerce").fillna(0.0).round(1)
            ddf["Róznica (w pp.)"] = pd.to_numeric(ddf["Róznica (w pp.)"], errors="coerce").fillna(0.0).round(1)

            variable_order = [str(spec.get("label") or "").strip() for spec in demo_specs if str(spec.get("label") or "").strip()]
            for extra_label in [str(v) for v in list(ddf["Zmienna"].astype(str).unique())]:
                if extra_label not in variable_order:
                    variable_order.append(extra_label)
            variable_pos = {label: idx for idx, label in enumerate(variable_order)}
            ddf["__var_order"] = ddf["Zmienna"].map(lambda v: int(variable_pos.get(str(v), 999)))
            ddf["__cat_order"] = ddf.apply(
                lambda row: (
                    list((spec_by_label.get(str(row["Zmienna"])) or {}).get("order_codes") or []).index(str(row.get("KategoriaKod") or ""))
                    if str(row.get("KategoriaKod") or "") in list((spec_by_label.get(str(row["Zmienna"])) or {}).get("order_codes") or [])
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
                spec = spec_by_label.get(var_name) or {}
                value_emoji_map = (
                    dict(spec.get("value_emoji") or {})
                    if isinstance(spec.get("value_emoji"), dict)
                    else {}
                )
                top_idx = part["% grupa dopasowana"].idxmax()
                rowspan = len(part.index)
                for idx, (_, row) in enumerate(part.iterrows()):
                    cat = str(row["Kategoria"])
                    cat_code = str(row.get("KategoriaKod") or cat)
                    pct_sub = float(row["% grupa dopasowana"])
                    pct_all = float(row["% ogół mieszkańców (ważony)"])
                    diff = float(row["Róznica (w pp.)"])
                    is_top = bool(row.name == top_idx)
                    bar_w = max(0.0, min(100.0, pct_sub))
                    var_icon = variable_emoji.get(var_name, "📌")
                    cat_icon = value_emoji_map.get(cat_code, "❔" if cat == "brak danych" else "📌")
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
                        f"<span>{html.escape(cat_icon)}</span>"
                        f"<span>{html.escape(cat)}</span>"
                        "</span>"
                        "</td>"
                        f"<td style=\"padding:0; min-width:176px; border:1px solid #dfe4ea; {top_border if idx == 0 else ''}\">"
                        "<div style=\"position:relative; height:34px; background:#fff;\">"
                        f"<div style=\"position:absolute; left:0; top:0; bottom:0; width:{bar_w:.1f}%; background:{fill_color}; opacity:0.96;\"></div>"
                        f"<span style=\"position:absolute; right:6px; top:6px; z-index:2; background:rgba(255,255,255,0.88); padding:1px 5px; border-radius:4px; font-size:13.5px; font-weight:{pct_weight}; color:#111;\">{pct_sub:.1f}%</span>"
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
                "<th style='min-width:176px; text-align:center; font-size:13.5px; border-top:3px solid #b8c2cc;'>% grupa dopasowana</th>"
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
                <div class="match-demo-box match-demo-profile-box">
                  <div class="match-demo-box-label">👥 PROFIL DEMOGRAFICZNY</div>
                  <div class="match-demo-box-note">W tabeli pogrubiona najwyższa kategoria w każdej zmiennej.</div>
                  <div class="match-demo-box-note">{html.escape(weights_note)}</div>
                  {table_html}
                </div>
                """,
                unsafe_allow_html=True,
            )

    with tab_segments:
        person_profile_match = {
            a: float((result.get("personal_profile") or {}).get(a, 0.0) or 0.0)
            for a in JST_ARCHETYPES
        }
        jst_sid = str(result.get("jst_study_id") or "").strip()
        person_sid = str(result.get("person_study_id") or "").strip()
        segment_profiles, segment_source, segment_err = _load_matching_segment_profiles(jst_sid)
        segment_membership_df, segment_membership_source, segment_membership_err = _load_matching_segment_membership(jst_sid)

        st.markdown(
            "Porównanie działa wyłącznie na wspólnej skali 12 archetypów (0-100): "
            "dla każdego segmentu liczona jest zgodność strategiczna z naciskiem na kluczowe archetypy "
            f"(TOP6 {person_role_gen} + TOP6 segmentu, 100% bazy wyniku z puli kluczowej; analiza TOP3/TOP2, luki i kary za rozjazdy priorytetów)."
        )
        if segment_err:
            st.warning(segment_err)
            if segment_source:
                st.caption(f"Oczekiwany plik segmentów: `{segment_source}`")
        if not segment_profiles:
            st.info("Brak danych segmentów do porównania w tym badaniu JST.")
        else:
            jst_row_live: Dict[str, Any] = {}
            if jst_sid:
                with contextlib.suppress(Exception):
                    jst_row_live = fetch_jst_study_by_id(sb, jst_sid) or {}
            stored_penalty_strength = normalize_matching_segments_penalty_strength(
                (jst_row_live or {}).get("matching_segments_penalty_strength")
            )
            penalty_strength_widget_key = f"matching_segments_penalty_strength_{jst_sid}"
            if penalty_strength_widget_key not in st.session_state:
                st.session_state[penalty_strength_widget_key] = stored_penalty_strength

            jst_n = int(result.get("jst_n") or 0)
            default_min_seg_n = max(30, int(round(jst_n * 0.06))) if jst_n > 0 else 60
            ctrl_a, ctrl_b, ctrl_c = st.columns([0.42, 0.30, 0.28], gap="large")
            with ctrl_a:
                min_seg_n = int(
                    st.number_input(
                        "Minimalna liczebność segmentu (N) dla wiarygodnego porównania",
                        min_value=10,
                        max_value=5000,
                        value=int(default_min_seg_n),
                        step=5,
                        key=f"matching_segments_min_n_{person_sid}_{jst_sid}",
                    )
                )
            with ctrl_b:
                show_uncertain = bool(
                    st.toggle(
                        "Pokaż segmenty poniżej progu (niepewne)",
                        value=True,
                        key=f"matching_segments_show_uncertain_{person_sid}_{jst_sid}",
                    )
                )
            with ctrl_c:
                penalty_strength = normalize_matching_segments_penalty_strength(
                    st.select_slider(
                        "Siła kar segmentowych",
                        options=["łagodna", "standard", "ostra"],
                        key=penalty_strength_widget_key,
                    )
                )
            if jst_sid and penalty_strength != stored_penalty_strength:
                with contextlib.suppress(Exception):
                    updated_jst = update_jst_study(
                        sb,
                        jst_sid,
                        {"matching_segments_penalty_strength": penalty_strength},
                    )
                    jst_row_live = dict(updated_jst or {})
                if isinstance(jst_row_live, dict):
                    jst_row_live["matching_segments_penalty_strength"] = penalty_strength
                result["matching_segments_penalty_strength"] = penalty_strength

            arch_order = list(JST_ARCHETYPES)
            penalty_profiles: Dict[str, Dict[str, float]] = {
                "łagodna": {
                    "kgap_mul": 0.40,
                    "kmax_mul": 0.12,
                    "kmax_floor": 12.0,
                    "shared_zero": 2.8,
                    "shared_one": 1.0,
                    "top1_mismatch": 1.2,
                },
                "standard": {
                    "kgap_mul": 0.50,
                    "kmax_mul": 0.18,
                    "kmax_floor": 12.0,
                    "shared_zero": 4.0,
                    "shared_one": 1.5,
                    "top1_mismatch": 1.8,
                },
                "ostra": {
                    "kgap_mul": 0.62,
                    "kmax_mul": 0.24,
                    "kmax_floor": 10.0,
                    "shared_zero": 5.6,
                    "shared_one": 2.3,
                    "top1_mismatch": 2.6,
                },
            }
            penalty_cfg = penalty_profiles.get(penalty_strength, penalty_profiles["standard"])

            def _segment_priority_pool(profile_100: Dict[str, float]) -> List[str]:
                ordered = sorted(
                    arch_order,
                    key=lambda a: (-float(profile_100.get(a, 0.0)), arch_order.index(a)),
                )
                top3 = ordered[:3]
                if len(top3) >= 3 and float(profile_100.get(top3[2], 0.0)) < 70.0:
                    return top3[:2]
                return top3

            def _segment_top_n(profile_100: Dict[str, float], n: int = 6) -> List[str]:
                ordered = sorted(
                    arch_order,
                    key=lambda a: (-float(profile_100.get(a, 0.0)), arch_order.index(a)),
                )
                return ordered[: max(1, int(n))]

            def _segment_strategic_score(person_profile_100: Dict[str, float], seg_profile_100: Dict[str, float]) -> Dict[str, float]:
                diffs = {
                    a: abs(float(person_profile_100.get(a, 0.0)) - float(seg_profile_100.get(a, 0.0)))
                    for a in arch_order
                }
                diff_vals_all = [float(v) for v in diffs.values()]
                mae_all = float(sum(diff_vals_all) / max(1, len(diff_vals_all)))
                rmse_all = math.sqrt(float(sum(v * v for v in diff_vals_all) / max(1, len(diff_vals_all))))
                top3_gap_mae_all = float(sum(sorted(diff_vals_all, reverse=True)[:3]) / max(1, min(3, len(diff_vals_all))))

                key_pool: List[str] = []
                for a in _segment_top_n(person_profile_100, 6) + _segment_top_n(seg_profile_100, 6):
                    if a not in key_pool:
                        key_pool.append(a)
                if not key_pool:
                    key_pool = arch_order[:6]
                diff_vals_key = [float(diffs.get(a, 0.0)) for a in key_pool]
                mae_key = float(sum(diff_vals_key) / max(1, len(diff_vals_key)))
                rmse_key = math.sqrt(float(sum(v * v for v in diff_vals_key) / max(1, len(diff_vals_key))))
                top3_gap_mae_key = float(sum(sorted(diff_vals_key, reverse=True)[:3]) / max(1, min(3, len(diff_vals_key))))

                person_top = _segment_priority_pool(person_profile_100)
                seg_top = _segment_priority_pool(seg_profile_100)
                key_archetypes: List[str] = []
                for arche in person_top + seg_top:
                    if arche not in key_archetypes:
                        key_archetypes.append(arche)
                key_gap_vals = [float(diffs.get(a, 0.0)) for a in key_archetypes]
                key_gap_mae = float(sum(key_gap_vals) / max(1, len(key_gap_vals)))
                key_gap_max = float(max(key_gap_vals)) if key_gap_vals else 0.0
                shared_priority_count = len(set(person_top).intersection(set(seg_top)))
                main_priority_mismatch_penalty = (
                    float(penalty_cfg.get("top1_mismatch", 1.8))
                    if (person_top and seg_top and person_top[0] != seg_top[0])
                    else 0.0
                )
                shared_priority_penalty = (
                    float(penalty_cfg.get("shared_zero", 4.0))
                    if shared_priority_count == 0
                    else (
                        float(penalty_cfg.get("shared_one", 1.5))
                        if shared_priority_count == 1
                        else 0.0
                    )
                )

                score_mae_all = max(0.0, min(100.0, 100.0 - mae_all))
                score_rmse_all = max(0.0, min(100.0, 100.0 - rmse_all))
                score_top3_all = max(0.0, min(100.0, 100.0 - top3_gap_mae_all))
                score_mae_key = max(0.0, min(100.0, 100.0 - mae_key))
                score_rmse_key = max(0.0, min(100.0, 100.0 - rmse_key))
                score_top3_key = max(0.0, min(100.0, 100.0 - top3_gap_mae_key))
                base_global = 0.50 * score_mae_all + 0.20 * score_rmse_all + 0.30 * score_top3_all
                base_key = 0.45 * score_mae_key + 0.25 * score_rmse_key + 0.30 * score_top3_key
                base_score = base_key
                key_penalty = (
                    float(penalty_cfg.get("kgap_mul", 0.50)) * key_gap_mae
                    + float(penalty_cfg.get("kmax_mul", 0.18))
                    * max(0.0, key_gap_max - float(penalty_cfg.get("kmax_floor", 12.0)))
                    + shared_priority_penalty
                    + main_priority_mismatch_penalty
                )
                match_score = max(0.0, min(100.0, base_score - key_penalty))
                return {
                    "mae_key": float(mae_key),
                    "mae_all": float(mae_all),
                    "match_pct": float(match_score),
                    "key_gap_mae": float(key_gap_mae),
                    "key_penalty": float(key_penalty),
                    "key_pool_n": float(len(key_pool)),
                    "penalty_strength": str(penalty_strength),
                }

            seg_rows: List[Dict[str, Any]] = []
            for seg in segment_profiles:
                seg_profile = {
                    a: float((seg.get("profile") or {}).get(a, 0.0) or 0.0)
                    for a in JST_ARCHETYPES
                }
                seg_metrics = _segment_strategic_score(person_profile_match, seg_profile)
                mae = float(seg_metrics.get("mae_key", 0.0))
                match_pct = float(seg_metrics.get("match_pct", 0.0))
                seg_n = int(seg.get("n") or 0)
                reliable = bool(seg_n >= min_seg_n)
                seg_name = (
                    str(seg.get("name_values") or "").strip()
                    if str(current_axis_label) == "Wartość"
                    else str(seg.get("name_arche") or "").strip()
                )
                if not seg_name:
                    seg_name = str(seg.get("name_arche") or seg.get("name_values") or seg.get("segment") or "").strip()
                seg_rows.append(
                    {
                        "segment": str(seg.get("segment") or "").strip(),
                        "segment_id": int(seg.get("segment_id") or 0),
                        "segment_name": seg_name,
                        "n": seg_n,
                        "share_pct": float(seg.get("share_pct") or 0.0),
                        "mae": mae,
                        "mae_all": float(seg_metrics.get("mae_all", 0.0)),
                        "match_pct": match_pct,
                        "key_gap_mae": float(seg_metrics.get("key_gap_mae", 0.0)),
                        "key_penalty": float(seg_metrics.get("key_penalty", 0.0)),
                        "key_pool_n": int(seg_metrics.get("key_pool_n", 0.0)),
                        "reliable": reliable,
                        "profile": seg_profile,
                    }
                )

            seg_rows.sort(
                key=lambda r: (
                    0 if bool(r.get("reliable")) else 1,
                    -float(r.get("match_pct") or 0.0),
                    float(r.get("mae") or 0.0),
                )
            )
            visible_rows = list(seg_rows) if show_uncertain else [r for r in seg_rows if bool(r.get("reliable"))]
            if not visible_rows:
                st.warning("Po zastosowaniu progu wiarygodności nie ma segmentów do pokazania.")
            else:
                def _fmt1_pl(v: Any) -> str:
                    try:
                        return f"{float(v):.1f}".replace(".", ",")
                    except Exception:
                        return "0,0"

                opt_map: Dict[str, Dict[str, Any]] = {}
                for r in visible_rows:
                    status_suffix = " • niepewne" if not bool(r.get("reliable")) else ""
                    label = (
                        f"{r['segment']} — {r['segment_name']} "
                        f"(N={int(r['n'])}, zgodność={_fmt1_pl(r['match_pct'])}%){status_suffix}"
                    )
                    opt_map[label] = r

                selected_label = st.selectbox(
                    "Wybrany segment do podsumowania",
                    list(opt_map.keys()),
                    key=f"matching_segments_pick_{person_sid}_{jst_sid}",
                )
                selected_seg = opt_map[selected_label]
                selected_score = float(selected_seg.get("match_pct") or 0.0)
                selected_score = max(0.0, min(100.0, selected_score))

                if selected_score >= 90:
                    seg_band_label = "Ekstremalnie wysokie dopasowanie"
                    seg_band_desc = f"Profil segmentu i profil {person_role_gen} są niemal zbieżne także na osiach kluczowych."
                    score_color = "#0f766e"
                    score_bg = "#ecfeff"
                elif selected_score >= 80:
                    seg_band_label = "Bardzo wysokie dopasowanie"
                    seg_band_desc = "Różnice są niewielkie i dotyczą głównie lokalnych odchyleń."
                    score_color = "#0e7490"
                    score_bg = "#ecfeff"
                elif selected_score >= 70:
                    seg_band_label = "Wysokie dopasowanie"
                    seg_band_desc = "Segment jest dobrze dopasowany, ale są jeszcze punktowe luki priorytetowe."
                    score_color = "#6d28d9"
                    score_bg = "#f5f3ff"
                elif selected_score >= 60:
                    seg_band_label = "Znaczące dopasowanie"
                    seg_band_desc = "Wspólny rdzeń jest wyraźny, jednak część kluczowych osi wymaga domknięcia."
                    score_color = "#1d4ed8"
                    score_bg = "#eff6ff"
                elif selected_score >= 50:
                    seg_band_label = "Umiarkowane dopasowanie"
                    seg_band_desc = "Są elementy wspólne, ale strategiczne luki pozostają widoczne."
                    score_color = "#b45309"
                    score_bg = "#fffbeb"
                elif selected_score >= 40:
                    seg_band_label = "Niskie dopasowanie"
                    seg_band_desc = "Dopasowanie segmentu jest słabe; profil wymaga istotnej korekty pod ten segment."
                    score_color = "#c2410c"
                    score_bg = "#fff7ed"
                elif selected_score >= 30:
                    seg_band_label = "Bardzo niskie dopasowanie"
                    seg_band_desc = f"Dominują rozjazdy strategiczne między {person_role_nom} a segmentem."
                    score_color = "#be123c"
                    score_bg = "#fff1f2"
                else:
                    seg_band_label = "Marginalne dopasowanie"
                    seg_band_desc = f"Segment i {person_role_nom} są silnie rozbieżni na osiach kluczowych."
                    score_color = "#7f1d1d"
                    score_bg = "#fef2f2"

                st.markdown(
                    f"""
                    <style>
                      .match-seg-target-card{{border:1px solid #d5dfec;border-radius:14px;background:linear-gradient(180deg,#ffffff 0%,#f6f9ff 100%);padding:10px 12px;margin:10px 0 10px 0;}}
                      .match-seg-target-title{{font-size:13px;font-weight:900;color:#334155;margin:0 0 8px 0;text-transform:uppercase;letter-spacing:.03em;}}
                      .match-seg-target-grid{{display:grid;grid-template-columns:1fr 1fr;gap:10px;}}
                      .match-seg-target-item{{border:1px solid #dbe4ef;border-radius:12px;background:#fff;padding:8px 10px;}}
                      .match-seg-target-item .k{{font-size:12px;font-weight:800;color:#64748b;margin:0 0 2px 0;}}
                      .match-seg-target-item .v{{font-size:16px;font-weight:900;color:#1f2f44;line-height:1.28;}}
                      .match-seg-score-card{{border:1px solid #d5dfec;border-radius:12px;background:#ffffff;padding:12px 14px;margin:8px 0 10px 0;}}
                      .match-seg-score-title{{font-size:15px;font-weight:800;color:#334155;margin:0 0 4px 0;}}
                      .match-seg-score-value{{font-size:42px;line-height:1;font-weight:900;color:#0f172a;margin:0 0 8px 0;}}
                      .match-seg-score-badge{{display:inline-block;padding:5px 10px;border-radius:999px;border:1px solid {score_color};background:{score_bg};color:{score_color};font-weight:900;font-size:15px;}}
                      .match-seg-score-desc{{margin:8px 0 10px 0;color:#475569;font-size:14px;font-weight:600;}}
                      .match-seg-score-track{{height:14px;border-radius:999px;background:#d5dde8;border:1px solid #aebfd3;overflow:hidden;}}
                      .match-seg-score-fill{{height:100%;border-radius:999px;background:linear-gradient(90deg,#2563eb 0%,#22c55e 100%);width:{selected_score:.1f}%;}}
                      .match-seg-score-scale{{display:flex;justify-content:space-between;color:#64748b;font-size:11px;margin-top:6px;font-weight:700;}}
                      @media (max-width:900px){{ .match-seg-target-grid{{grid-template-columns:1fr;}} }}
                    </style>
                    <div class="match-seg-target-card">
                      <div class="match-seg-target-title">Dla kogo liczona jest segmentacja</div>
                      <div class="match-seg-target-grid">
                        <div class="match-seg-target-item">
                          <div class="k">👤 Badanie personalne</div>
                          <div class="v">{html.escape(str(result.get('person_label') or ''))}</div>
                        </div>
                        <div class="match-seg-target-item">
                          <div class="k">🏙️ Badanie mieszkańców</div>
                          <div class="v">{html.escape(str(result.get('jst_label') or ''))}</div>
                        </div>
                      </div>
                    </div>
                    <div class="match-seg-score-card">
                      <div class="match-seg-score-title">Poziom zgodności wybranego segmentu</div>
                      <div class="match-seg-score-value">{_fmt1_pl(selected_score)}%</div>
                      <div class="match-seg-score-badge">Ocena: {html.escape(seg_band_label)}</div>
                      <div class="match-seg-score-desc">
                        {html.escape(seg_band_desc)} Wybrany segment: {html.escape(str(selected_seg.get('segment') or ''))} — {html.escape(str(selected_seg.get('segment_name') or ''))}
                        (N={int(selected_seg.get('n') or 0)}, udział={_fmt1_pl(selected_seg.get('share_pct') or 0.0)}%, luka kluczowa={_fmt1_pl(selected_seg.get('mae') or 0.0)} pp).
                      </div>
                      <div class="match-seg-score-track"><div class="match-seg-score-fill"></div></div>
                      <div class="match-seg-score-scale"><span>0%</span><span>100%</span></div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                table_df = pd.DataFrame(
                    [
                        {
                            "Segment": str(r["segment"]),
                            "Nazwa segmentu": str(r["segment_name"]),
                            "N": int(r["n"]),
                            "Udział (%)": _fmt1_pl(r["share_pct"]),
                            "Śr. luka kluczowa |Δ| (pp)": _fmt1_pl(r["mae"]),
                            "Zgodność (%)": _fmt1_pl(r["match_pct"]),
                            "Wiarygodność": ("OK" if bool(r["reliable"]) else f"Niepewne (N<{min_seg_n})"),
                        }
                        for r in visible_rows
                    ]
                )
                seg_height = min(560, 56 + 38 * len(table_df))
                st.dataframe(table_df, use_container_width=True, hide_index=True, height=seg_height)

                uncertain_count = int(sum(1 for r in visible_rows if not bool(r.get("reliable"))))
                if uncertain_count > 0:
                    st.warning(
                        f"{uncertain_count} segment(ów) jest poniżej progu N={min_seg_n}. "
                        "Wyniki traktuj orientacyjnie (wysoka niepewność estymacji)."
                    )

                reliable_rows = [r for r in visible_rows if bool(r.get("reliable"))]
                if reliable_rows:
                    best = reliable_rows[0]
                    st.success(
                        f"Najwyższa zgodność strategiczna (segment wiarygodny): {best['segment']} — {best['segment_name']} "
                        f"(zgodność {_fmt1_pl(best['match_pct'])}%, N={best['n']})."
                    )
                else:
                    st.info("Brak segmentów spełniających próg wiarygodności. Obniż próg N lub traktuj wynik jako eksploracyjny.")

                st.markdown(
                    """
                    <style>
                      .match-seg-radar-label{
                        margin:22px 0 10px 0;
                        font-size:24px;
                        font-weight:900;
                        color:#1f2f44;
                        line-height:1.2;
                      }
                      .match-seg-top3-style-grid{
                        display:grid;
                        grid-template-columns:1fr 1fr;
                        gap:12px;
                        margin:-18px 0 4px 0;
                      }
                      .match-seg-top3-style-card{
                        border:1px solid #dbe4ef;
                        border-radius:12px;
                        background:#fff;
                        padding:10px 12px;
                        text-align:center;
                      }
                      .match-seg-top3-style-card .title{
                        font-size:13px;
                        font-weight:500;
                        color:#1f2f44;
                        margin-bottom:4px;
                      }
                      .match-seg-top3-style-card .line2{
                        display:flex;
                        align-items:center;
                        justify-content:center;
                        gap:18px;
                        flex-wrap:wrap;
                        font-size:14px;
                        font-weight:700;
                        line-height:1.35;
                      }
                      .match-seg-top3-style-card .line2 span{white-space:nowrap;}
                      @media (max-width: 900px){
                        .match-seg-top3-style-grid{grid-template-columns:1fr;}
                      }
                      .match-seg-radar-legend{
                        margin:4px auto 10px auto;
                        max-width:1140px;
                        width:100%;
                        display:flex;
                        justify-content:center;
                        gap:12px;
                        flex-wrap:wrap;
                      }
                      .match-seg-radar-pill{
                        display:inline-flex;
                        align-items:center;
                        gap:8px;
                        border:1px solid #dbe4ef;
                        background:#fff;
                        border-radius:999px;
                        padding:7px 14px;
                        font-size:13px;
                        font-weight:700;
                        color:#1f2f44;
                        min-width:340px;
                        justify-content:center;
                      }
                      .match-seg-radar-line{
                        width:30px;
                        height:0;
                        border-top:3px solid #2563eb;
                        display:inline-block;
                      }
                      .match-seg-radar-line.dashed{
                        border-top:3px dashed #0f766e;
                      }
                    </style>
                    """,
                    unsafe_allow_html=True,
                )
                st.markdown("<div class='match-seg-radar-label'>Podgląd radarowy segmentu</div>", unsafe_allow_html=True)
                if not bool(selected_seg.get("reliable")):
                    st.warning(
                        f"Wybrany segment ma N={int(selected_seg.get('n') or 0)} (<{min_seg_n}) — interpretuj radar ostrożnie."
                    )

                radar_order: List[str] = [
                    "Buntownik", "Błazen", "Kochanek", "Opiekun", "Towarzysz", "Niewinny",
                    "Władca", "Mędrzec", "Czarodziej", "Bohater", "Twórca", "Odkrywca",
                ]
                radar_tick_labels = [_matching_entity_name(a, current_axis_label, person_gender_code) for a in radar_order]
                seg_profile = {a: float((selected_seg.get("profile") or {}).get(a, 0.0)) for a in radar_order}
                person_profile_20 = {a: float(person_profile_match.get(a, 0.0)) / 5.0 for a in radar_order}
                seg_profile_20 = {a: float(seg_profile.get(a, 0.0)) / 5.0 for a in radar_order}

                def _priority_top_for_ui_seg(profile_100: Dict[str, float], order: List[str]) -> List[str]:
                    ordered = sorted(order, key=lambda a: (-float(profile_100.get(a, 0.0)), order.index(a)))
                    top3 = ordered[:3]
                    if len(top3) >= 3 and float(profile_100.get(top3[2], 0.0)) < 70.0:
                        return top3[:2]
                    return top3

                p_top = _priority_top_for_ui_seg(person_profile_match, radar_order)
                seg_top = _priority_top_for_ui_seg(seg_profile, radar_order)
                radar_top_union = set(p_top + seg_top)
                radar_tick_text: List[str] = []
                for arche, lbl in zip(radar_order, radar_tick_labels):
                    safe_lbl = html.escape(str(lbl))
                    radar_tick_text.append(f"<b>{safe_lbl}</b>" if arche in radar_top_union else safe_lbl)

                person_top_colors = {"main": "#ef4444", "aux": "#facc15", "supp": "#22c55e"}
                seg_top_colors = {"main": "#2563eb", "aux": "#a855f7", "supp": "#f97316"}
                p_top_label = f"TOP{max(1, len(p_top))} {person_role_gen}"
                seg_top_label = f"TOP{max(1, len(seg_top))} segmentu"

                def _marker_series_seg(profile: Dict[str, float], top3: List[str], palette: Dict[str, str]) -> Tuple[List[Optional[float]], List[str]]:
                    r_vals: List[Optional[float]] = []
                    colors: List[str] = []
                    mapping: Dict[str, str] = {}
                    if len(top3) > 0:
                        mapping[top3[0]] = palette["main"]
                    if len(top3) > 1:
                        mapping[top3[1]] = palette["aux"]
                    if len(top3) > 2:
                        mapping[top3[2]] = palette["supp"]
                    for arche in radar_order:
                        if arche in mapping:
                            r_vals.append(float(profile.get(arche, 0.0)))
                            colors.append(str(mapping[arche]))
                        else:
                            r_vals.append(None)
                            colors.append("rgba(0,0,0,0)")
                    return r_vals, colors

                def _role_legend_html_seg(palette: Dict[str, str], marker: str, count: int) -> str:
                    role_defs = [("główny", "main"), ("wspierający", "aux"), ("poboczny", "supp")]
                    items: List[str] = []
                    for idx, (label, role_key) in enumerate(role_defs):
                        if idx >= max(0, int(count)):
                            break
                        items.append(
                            f"<span><span style=\"color:{palette[role_key]};\">{marker}</span> {label}</span>"
                        )
                    return "".join(items)

                p_role_legend = _role_legend_html_seg(person_top_colors, "●", len(p_top))
                seg_role_legend = _role_legend_html_seg(seg_top_colors, "■", len(seg_top))

                p_marker_r, p_marker_c = _marker_series_seg(person_profile_20, p_top, person_top_colors)
                seg_marker_r, seg_marker_c = _marker_series_seg(seg_profile_20, seg_top, seg_top_colors)
                person_vals_20 = [float(person_profile_20.get(a, 0.0)) for a in radar_order]
                seg_vals_20 = [float(seg_profile_20.get(a, 0.0)) for a in radar_order]
                person_name_seg = str(result.get("person_name_nom") or result.get("person_label") or person_role_nom_cap)
                segment_name_seg = str(selected_seg.get("segment_name") or selected_seg.get("segment") or "segment")
                legend_person_label = f"profil {person_role_gen} ({person_name_seg})"
                legend_segment_label = f"profil segmentu ({segment_name_seg})"
                st.markdown(
                    f"""
                    <div class="match-seg-radar-legend">
                      <span class="match-seg-radar-pill"><span class="match-seg-radar-line"></span>{html.escape(legend_person_label)}</span>
                      <span class="match-seg-radar-pill"><span class="match-seg-radar-line dashed"></span>{html.escape(legend_segment_label)}</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                fig_seg = go.Figure(
                    data=[
                        go.Scatterpolar(
                            r=person_vals_20 + [person_vals_20[0]],
                            theta=radar_tick_labels + [radar_tick_labels[0]],
                            fill="toself",
                            fillcolor="rgba(37,99,235,0.18)",
                            line=dict(color="#2563eb", width=3),
                            marker=dict(size=5, symbol="circle"),
                            name=legend_person_label,
                            showlegend=False,
                            hovertemplate=f"<b>%{{theta}}</b><br>{person_role_nom_cap}: %{{r:.2f}}<extra></extra>",
                        ),
                        go.Scatterpolar(
                            r=seg_vals_20 + [seg_vals_20[0]],
                            theta=radar_tick_labels + [radar_tick_labels[0]],
                            fill="toself",
                            fillcolor="rgba(15,118,110,0.16)",
                            line=dict(color="#0f766e", width=3, dash="dot"),
                            marker=dict(size=6, symbol="square"),
                            name=legend_segment_label,
                            showlegend=False,
                            hovertemplate="<b>%{theta}</b><br>Segment: %{r:.2f}<extra></extra>",
                        ),
                        go.Scatterpolar(
                            r=p_marker_r,
                            theta=radar_tick_labels,
                            mode="markers",
                            marker=dict(size=16, symbol="circle", color=p_marker_c, opacity=0.92, line=dict(color="black", width=2.6)),
                            name=p_top_label,
                            showlegend=False,
                            hovertemplate=f"<b>%{{theta}}</b><br>{p_top_label}: %{{r:.2f}}<extra></extra>",
                        ),
                        go.Scatterpolar(
                            r=seg_marker_r,
                            theta=radar_tick_labels,
                            mode="markers",
                            marker=dict(size=14, symbol="square", color=seg_marker_c, opacity=0.94, line=dict(color="#0f172a", width=2.0)),
                            name=seg_top_label,
                            showlegend=False,
                            hovertemplate=f"<b>%{{theta}}</b><br>{seg_top_label}: %{{r:.2f}}<extra></extra>",
                        ),
                    ]
                )
                fig_seg.update_layout(
                    paper_bgcolor="rgba(0,0,0,0)",
                    height=640,
                    polar=dict(
                        bgcolor="rgba(0,0,0,0)",
                        radialaxis=dict(visible=True, range=[0, 20]),
                        angularaxis=dict(
                            tickfont=dict(size=16),
                            tickvals=radar_tick_labels,
                            ticktext=radar_tick_text,
                            rotation=90,
                            direction="clockwise",
                        ),
                    ),
                    margin=dict(l=24, r=24, t=66, b=90),
                    showlegend=False,
                )
                seg_key_safe = re.sub(
                    r"[^a-zA-Z0-9_-]+",
                    "_",
                    str(selected_seg.get("segment") or selected_seg.get("segment_name") or "segment"),
                )
                st.plotly_chart(
                    fig_seg,
                    use_container_width=True,
                    config={"displaylogo": False, "displayModeBar": False, "responsive": True},
                    key=f"matching-segment-radar-{person_sid}-{jst_sid}-{seg_key_safe}",
                )
                st.markdown(
                    f"""
                    <div class="match-seg-top3-style-grid">
                      <div class="match-seg-top3-style-card">
                        <div class="title">{html.escape(p_top_label)}</div>
                        <div class="line2">{p_role_legend}</div>
                      </div>
                      <div class="match-seg-top3-style-card">
                        <div class="title">{html.escape(seg_top_label)}</div>
                        <div class="line2">{seg_role_legend}</div>
                      </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.caption(
                    f"Metoda porównania strategicznego (key-focused): 100% bazy wyniku liczone jest z puli kluczowej "
                    f"(TOP6 {person_role_gen} + TOP6 segmentu); dodatkowo działa kara za luki priorytetów TOP3/TOP2. "
                    f"Aktualna siła kar: {penalty_strength}."
                )

                profile_title = (
                    "Profile archetypowe 0-100 (siła archetypu, skala: 0-100)"
                    if current_axis_label == "Archetyp"
                    else "Profile wartości 0-100 (siła wartości, skala: 0-100)"
                )
                st.markdown(
                    f"<div class='match-section-header match-profile-header'><h3>{html.escape(profile_title)}</h3></div>",
                    unsafe_allow_html=True,
                )
                seg_left_profile_col, seg_right_profile_col = st.columns(2, gap="large")
                try:
                    import admin_dashboard as AD

                    p_key = re.sub(r"[^a-zA-Z0-9_-]+", "_", person_sid or "person")
                    s_key = re.sub(r"[^a-zA-Z0-9_-]+", "_", seg_key_safe or "segment")
                    person_profile_img = AD.make_segment_profile_wheel_png(
                        mean_scores=person_profile_match,
                        out_path=f"matching_segment_profile_person_{p_key}_{s_key}.png",
                        label_mode=("values" if current_axis_label == "Wartość" else "arche"),
                        gender_code=person_gender_code,
                    )
                    segment_profile_img = AD.make_segment_profile_wheel_png(
                        mean_scores=seg_profile,
                        out_path=f"matching_segment_profile_segment_{s_key}_{p_key}.png",
                        label_mode=("values" if current_axis_label == "Wartość" else "arche"),
                        gender_code=person_gender_code,
                    )

                    def _show_image_compat_segment(img_path: str, max_width_px: int = 560) -> None:
                        try:
                            st.image(img_path, width=max_width_px)
                        except TypeError:
                            st.image(img_path, use_column_width=True)

                    with seg_left_profile_col:
                        st.markdown(
                            f"<div class='match-profile-title'>"
                            f"{'Profil archetypowy' if current_axis_label == 'Archetyp' else 'Profil wartości'} {html.escape(str(person_name_seg or ''))}"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                        _show_image_compat_segment(person_profile_img, max_width_px=520)
                    with seg_right_profile_col:
                        st.markdown(
                            f"<div class='match-profile-title'>"
                            f"{'Profil archetypowy segmentu' if current_axis_label == 'Archetyp' else 'Profil wartości segmentu'} {html.escape(str(segment_name_seg or ''))}"
                            f"</div>",
                            unsafe_allow_html=True,
                        )
                        _show_image_compat_segment(segment_profile_img, max_width_px=520)
                    st.markdown(
                        """
                        <div class="match-wheel-legend-wrap">
                          <div class="match-wheel-legend">
                            <span><i style="background:#e53935"></i>Zmiana</span>
                            <span><i style="background:#1e88e5"></i>Ludzie</span>
                            <span><i style="background:#2e7d32"></i>Porządek</span>
                            <span><i style="background:#7e57c2"></i>Niezależność</span>
                          </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                except Exception as e:
                    st.info(f"Nie udało się wygenerować porównania kół 0-100 dla segmentu: {e}")

                st.markdown(
                    """
                    <style>
                      .match-seg-demo-box{border:1px solid #dbe4ef;border-radius:12px;background:#fff;padding:10px 12px;margin:10px 0 10px 0;}
                      .match-seg-demo-box-label{font-size:15px;font-weight:900;text-transform:uppercase;letter-spacing:.02em;color:#334155;display:flex;align-items:center;gap:6px;}
                      .match-seg-demo-box-note{color:#5f6b7a;font-size:12px;margin:2px 0 6px 0;}
                      .match-seg-demo-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(175px,1fr));gap:8px;margin:10px 0 8px 0;}
                      .match-seg-demo-stat{border:1px solid #dbe4ef;border-radius:10px;background:#fff;padding:8px 10px;}
                      .match-seg-demo-stat-label{font-size:12px;font-weight:800;text-transform:uppercase;letter-spacing:.03em;color:#5f6b7a;}
                      .match-seg-demo-stat-main{margin-top:2px;font-size:14px;font-weight:900;color:#111827;line-height:1.2;}
                      .match-seg-demo-stat-sub{margin-top:2px;font-size:12.5px;color:#3f4954;}
                      .match-seg-demo-table-wrap{overflow-x:auto;max-width:940px;}
                      .match-seg-demo-table{margin-top:0;width:100%;min-width:720px;max-width:940px;border-collapse:collapse;border:3px solid #b8c2cc;background:#fff;font-size:13.5px;color:#334155;}
                      .match-seg-demo-table th,.match-seg-demo-table td{padding:8px 10px;border:1px solid #dfe4ea;text-align:left;vertical-align:middle;}
                      .match-seg-demo-table th{background:#f2f6fb;color:#1f2f44;font-weight:800;font-size:13.5px;}
                    </style>
                    """,
                    unsafe_allow_html=True,
                )

                if segment_membership_err:
                    st.warning(segment_membership_err)
                    if segment_membership_source:
                        st.caption(f"Oczekiwany plik przypisań segmentów: `{segment_membership_source}`")
                else:
                    jst_demo_vectors_raw = result.get("jst_demo_vectors") or []
                    jst_demo_vectors: List[Dict[str, Any]] = []
                    for rec in jst_demo_vectors_raw if isinstance(jst_demo_vectors_raw, list) else []:
                        if not isinstance(rec, dict):
                            continue
                        payload = rec.get("payload") if isinstance(rec.get("payload"), dict) else {}
                        rid = str(rec.get("respondent_id") or "").strip()
                        w = float(rec.get("weight") or 1.0) if math.isfinite(float(rec.get("weight") or 1.0)) else 1.0
                        if not payload:
                            continue
                        jst_demo_vectors.append({"respondent_id": rid, "payload": payload, "weight": w})

                    seg_demo_weights_used = bool(result.get("demo_weights_used"))
                    if not jst_demo_vectors:
                        try:
                            jst_study_live = fetch_jst_study_by_id(sb, jst_sid) or {}
                            j_rows_live = list_jst_responses(sb, jst_sid)
                            payloads_live = [
                                (r.get("payload") if isinstance(r.get("payload"), dict) else {})
                                for r in j_rows_live
                            ]
                            weights_live, weights_used_live = _calc_poststrat_weights_for_payloads(payloads_live, jst_study_live)
                            seg_demo_weights_used = bool(weights_used_live)
                            for idx, row_live in enumerate(j_rows_live):
                                payload_live = row_live.get("payload") if isinstance(row_live.get("payload"), dict) else {}
                                if not payload_live:
                                    continue
                                rid_live = str(row_live.get("respondent_id") or "").strip()
                                w_live = float(weights_live[idx]) if idx < len(weights_live) else 1.0
                                if not math.isfinite(w_live) or w_live <= 0:
                                    w_live = 1.0
                                jst_demo_vectors.append({"respondent_id": rid_live, "payload": payload_live, "weight": w_live})
                        except Exception as e:
                            st.info(f"Nie udało się pobrać danych demograficznych segmentu: {e}")

                    if not jst_demo_vectors:
                        st.caption("Brak danych do wyliczenia statystycznego profilu demograficznego segmentu.")
                    else:
                        seg_assign_by_rid: Dict[str, Dict[str, Any]] = {}
                        for _, seg_row in segment_membership_df.iterrows():
                            rid = str(seg_row.get("respondent_id") or "").strip()
                            if not rid:
                                continue
                            seg_label_row = str(seg_row.get("segment") or "").strip()
                            seg_id_row = int(round(_safe_float_num(seg_row.get("segment_id"), -1)))
                            seg_assign_by_rid[rid] = {
                                "segment": seg_label_row,
                                "segment_id": seg_id_row,
                            }

                        def _seg_norm(v: Any) -> str:
                            return re.sub(r"\s+", "", str(v or "").strip().lower())

                        selected_segment_norm = _seg_norm(selected_seg.get("segment"))
                        selected_segment_id = int(selected_seg.get("segment_id") or -1)
                        all_records: List[Dict[str, Any]] = []
                        subset_records: List[Dict[str, Any]] = []
                        for rec in jst_demo_vectors:
                            rid = str(rec.get("respondent_id") or "").strip()
                            if not rid:
                                continue
                            seg_meta = seg_assign_by_rid.get(rid)
                            if not isinstance(seg_meta, dict):
                                continue
                            payload = rec.get("payload") if isinstance(rec.get("payload"), dict) else {}
                            if not payload:
                                continue
                            w = float(rec.get("weight") or 1.0)
                            if not math.isfinite(w) or w <= 0:
                                w = 1.0
                            entry = {
                                "payload": payload,
                                "weight": w,
                                "segment": str(seg_meta.get("segment") or "").strip(),
                                "segment_id": int(seg_meta.get("segment_id") or -1),
                            }
                            all_records.append(entry)
                            same_by_id = selected_segment_id >= 0 and int(entry["segment_id"]) == selected_segment_id
                            same_by_label = _seg_norm(entry["segment"]) == selected_segment_norm
                            if same_by_id or same_by_label:
                                subset_records.append(entry)

                        if not all_records:
                            st.caption("Brak wspólnych rekordów respondentów między odpowiedziami JST a plikiem przypisań segmentów.")
                        elif not subset_records:
                            st.caption("Brak danych respondentów dla wybranego segmentu.")
                        else:
                            seg_demo_specs = [dict(x) for x in list(result.get("demo_specs") or []) if isinstance(x, dict)]
                            if not seg_demo_specs:
                                seg_demo_specs = _matching_demo_build_specs((fetch_jst_study_by_id(sb, jst_sid) or {}).get("metryczka_config"))
                            if not seg_demo_specs:
                                seg_demo_specs = _matching_demo_build_specs(None)
                            seg_spec_by_label = {
                                str(spec.get("label") or "").strip(): spec
                                for spec in seg_demo_specs
                                if str(spec.get("label") or "").strip()
                            }
                            seg_variable_emoji = {
                                str(spec.get("label") or "").strip(): str(spec.get("variable_emoji") or "📌")
                                for spec in seg_demo_specs
                                if str(spec.get("label") or "").strip()
                            }
                            seg_demo_rows, seg_demo_cards = _matching_demo_build_rows(
                                subset_records,
                                all_records,
                                seg_demo_specs,
                                "% segment",
                            )

                            cards_html = "".join(
                                f"""
                                <div class="match-seg-demo-stat">
                                  <div class="match-seg-demo-stat-label">{html.escape(str(c.get("variable_emoji") or seg_variable_emoji.get(str(c.get("label") or ""), "📌")))} {html.escape(str(c.get("label") or "").upper())}</div>
                                  <div class="match-seg-demo-stat-main">{html.escape(str(c.get("emoji") or ""))} {html.escape(str(c.get("top") or ""))}</div>
                                  <div class="match-seg-demo-stat-sub">{float(c.get("pct") or 0.0):.1f}% • {float(c.get("diff_pp") or 0.0):+,.1f} pp</div>
                                </div>
                                """
                                for c in seg_demo_cards
                            )
                            strongest = None
                            if seg_demo_cards:
                                strongest = max(seg_demo_cards, key=lambda x: float(x.get("diff_pp") or 0.0))
                            strongest_note = ""
                            if strongest is not None:
                                strongest_note = (
                                    f"Najmocniejsza nadreprezentacja: {str(strongest.get('label') or '')} – "
                                    f"{str(strongest.get('top') or '')} ({float(strongest.get('diff_pp') or 0.0):+,.1f} pp)."
                                )
                            st.markdown(
                                f"""
                                <div class="match-seg-demo-box">
                                  <div class="match-seg-demo-box-label">📌 STATYSTYCZNY PROFIL DEMOGRAFICZNY SEGMENTU</div>
                                  <div class="match-seg-demo-cards">{cards_html}</div>
                                  {"<div class='match-seg-demo-box-note'>" + html.escape(strongest_note) + "</div>" if strongest_note else ""}
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )

                            ddf = pd.DataFrame(seg_demo_rows)
                            if ddf.empty:
                                st.caption("Brak danych demograficznych dla wybranego segmentu.")
                            else:
                                if "KategoriaKod" not in ddf.columns:
                                    ddf["KategoriaKod"] = ddf["Kategoria"].astype(str)
                                ddf["% segment"] = pd.to_numeric(ddf["% segment"], errors="coerce").fillna(0.0).round(1)
                                ddf["% ogół mieszkańców (ważony)"] = pd.to_numeric(ddf["% ogół mieszkańców (ważony)"], errors="coerce").fillna(0.0).round(1)
                                ddf["Róznica (w pp.)"] = pd.to_numeric(ddf["Róznica (w pp.)"], errors="coerce").fillna(0.0).round(1)
                                variable_order = [str(spec.get("label") or "").strip() for spec in seg_demo_specs if str(spec.get("label") or "").strip()]
                                for extra_label in [str(v) for v in list(ddf["Zmienna"].astype(str).unique())]:
                                    if extra_label not in variable_order:
                                        variable_order.append(extra_label)
                                variable_pos = {label: idx for idx, label in enumerate(variable_order)}
                                ddf["__var_order"] = ddf["Zmienna"].map(lambda v: int(variable_pos.get(str(v), 999)))
                                ddf["__cat_order"] = ddf.apply(
                                    lambda row: (
                                        list((seg_spec_by_label.get(str(row["Zmienna"])) or {}).get("order_codes") or []).index(str(row.get("KategoriaKod") or ""))
                                        if str(row.get("KategoriaKod") or "") in list((seg_spec_by_label.get(str(row["Zmienna"])) or {}).get("order_codes") or [])
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
                                    spec = seg_spec_by_label.get(var_name) or {}
                                    value_emoji_map = (
                                        dict(spec.get("value_emoji") or {})
                                        if isinstance(spec.get("value_emoji"), dict)
                                        else {}
                                    )
                                    top_idx = part["% segment"].idxmax()
                                    rowspan = len(part.index)
                                    for idx, (_, row) in enumerate(part.iterrows()):
                                        cat = str(row["Kategoria"])
                                        cat_code = str(row.get("KategoriaKod") or cat)
                                        pct_sub = float(row["% segment"])
                                        pct_all = float(row["% ogół mieszkańców (ważony)"])
                                        diff = float(row["Róznica (w pp.)"])
                                        is_top = bool(row.name == top_idx)
                                        bar_w = max(0.0, min(100.0, pct_sub))
                                        var_icon = seg_variable_emoji.get(var_name, "📌")
                                        cat_icon = value_emoji_map.get(cat_code, "❔" if cat == "brak danych" else "📌")
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
                                            f"<span>{html.escape(cat_icon)}</span>"
                                            f"<span>{html.escape(cat)}</span>"
                                            "</span>"
                                            "</td>"
                                            f"<td style=\"padding:0; min-width:176px; border:1px solid #dfe4ea; {top_border if idx == 0 else ''}\">"
                                            "<div style=\"position:relative; height:34px; background:#fff;\">"
                                            f"<div style=\"position:absolute; left:0; top:0; bottom:0; width:{bar_w:.1f}%; background:{fill_color}; opacity:0.96;\"></div>"
                                            f"<span style=\"position:absolute; right:6px; top:6px; z-index:2; background:rgba(255,255,255,0.88); padding:1px 5px; border-radius:4px; font-size:13.5px; font-weight:{pct_weight}; color:#111;\">{pct_sub:.1f}%</span>"
                                            "</div>"
                                            "</td>"
                                            f"<td style=\"font-size:13.5px; text-align:right; {top_border if idx == 0 else ''}\">{pct_all:.1f}%</td>"
                                            f"<td style=\"font-size:13.5px; text-align:right; color:{diff_color}; font-weight:400; border-right:3px solid #b8c2cc; {top_border if idx == 0 else ''}\">{diff_text}</td>"
                                            "</tr>"
                                        )

                                jst_weighted_header = str(result.get("demo_jst_weighted_header") or "JST / (po wagowaniu)")
                                jst_weighted_header_html = html.escape(jst_weighted_header).replace(" / ", " /<br>")
                                table_html = (
                                    "<div class='match-seg-demo-table-wrap'>"
                                    "<table class='match-seg-demo-table'>"
                                    "<thead><tr>"
                                    "<th style='min-width:150px; font-size:13.5px; border-top:3px solid #b8c2cc; border-left:3px solid #b8c2cc;'>Zmienna</th>"
                                    "<th style='min-width:220px; font-size:13.5px; border-top:3px solid #b8c2cc;'>Kategoria</th>"
                                    "<th style='min-width:176px; text-align:center; font-size:13.5px; border-top:3px solid #b8c2cc;'>% segment</th>"
                                    f"<th style='min-width:130px; text-align:center; border-top:3px solid #b8c2cc;'>{jst_weighted_header_html}</th>"
                                    "<th style='min-width:120px; text-align:center; border-top:3px solid #b8c2cc; border-right:3px solid #b8c2cc;'>Róznica (w pp.)</th>"
                                    "</tr></thead><tbody>"
                                    + "".join(table_rows)
                                    + "</tbody></table></div>"
                                )
                                weights_note = (
                                    "Wartości w kolumnie referencyjnej i segmencie liczone po wagowaniu (płeć × wiek)."
                                    if seg_demo_weights_used
                                    else "Brak zdefiniowanych wag poststratyfikacyjnych dla tego badania — pokazujemy rozkład surowy."
                                )
                                coverage_pct = 100.0 * float(len(all_records)) / max(1.0, float(len(jst_demo_vectors)))
                                st.markdown(
                                    f"""
                                    <div class="match-seg-demo-box">
                                      <div class="match-seg-demo-box-label">👥 PROFIL DEMOGRAFICZNY SEGMENTU</div>
                                      <div class="match-seg-demo-box-note">W tabeli pogrubiona najwyższa kategoria w każdej zmiennej.</div>
                                      <div class="match-seg-demo-box-note">{html.escape(weights_note)}</div>
                                      <div class="match-seg-demo-box-note">Pokrycie mapowania segmentów: {coverage_pct:.1f}% respondentów z bieżącej próby JST.</div>
                                      {table_html}
                                    </div>
                                    """,
                                    unsafe_allow_html=True,
                                )

    with tab_strategy:
        strengths = [str(_matching_entity_name(x, current_axis_label, person_gender_code)) for x in (result.get("strengths") or [])[:3]]
        gaps = [str(_matching_entity_name(x, current_axis_label, person_gender_code)) for x in (result.get("gaps") or [])[:3]]
        demo_cards = list(result.get("demo_cards") or [])
        target_cards = demo_cards[:2]
        target_group_txt = ", ".join([str(c.get("top") or "").strip() for c in target_cards if str(c.get("top") or "").strip()]) or "najmocniej dopasowane segmenty demograficzne"
        strengths_txt = ", ".join(strengths) if strengths else "brak wyraźnych osi"
        gaps_txt = ", ".join(gaps) if gaps else "brak wyraźnych luk"
        st.markdown(
            """
            <style>
              .match-strategy-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:8px;}
              .match-strategy-card{
                border:1px solid #dbe4ef;
                border-radius:14px;
                background:linear-gradient(180deg,#ffffff 0%,#f7fbff 100%);
                padding:12px 14px;
              }
              .match-strategy-card h4{
                margin:0 0 8px 0;
                font-size:15px;
                font-weight:900;
                color:#1f2f44;
              }
              .match-strategy-list{margin:0;padding-left:18px;}
              .match-strategy-list li{margin:6px 0;font-size:14px;line-height:1.35;color:#1e293b;}
              .match-strategy-badge{
                display:inline-flex;
                align-items:center;
                gap:6px;
                font-size:12px;
                font-weight:800;
                color:#1d4ed8;
                background:#e8f0ff;
                border:1px solid #bfdbfe;
                border-radius:999px;
                padding:4px 9px;
                margin-bottom:8px;
              }
              @media (max-width: 960px){.match-strategy-grid{grid-template-columns:1fr;}}
            </style>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div class="match-strategy-grid">
              <div class="match-strategy-card">
                <div class="match-strategy-badge">🎯 Oś przekazu</div>
                <h4>Co wzmacniać w komunikacji</h4>
                <ul class="match-strategy-list">
                  <li>Buduj główną narrację wokół: <b>{html.escape(strengths_txt)}</b>.</li>
                  <li>W kampanii używaj prostych dowodów wykonania: „co zrobiono”, „co to zmienia dla mieszkańca”, „kiedy będzie efekt”.</li>
                  <li>Każdy materiał kończ jednym CTA dopasowanym do kanału (offline / social / SMS).</li>
                </ul>
              </div>
              <div class="match-strategy-card">
                <div class="match-strategy-badge">🧩 Luki komunikacyjne</div>
                <h4>Co domykać priorytetowo</h4>
                <ul class="match-strategy-list">
                  <li>Luki wymagające osobnych mini-narracji: <b>{html.escape(gaps_txt)}</b>.</li>
                  <li>Dla każdej luki przygotuj pakiet: problem → konkretna decyzja → mierzalny efekt.</li>
                  <li>W debacie porównawczej używaj kontr-przekazu opartego o fakty i harmonogram realizacji.</li>
                </ul>
              </div>
              <div class="match-strategy-card">
                <div class="match-strategy-badge">👥 Segment docelowy</div>
                <h4>Do kogo mówić najpierw</h4>
                <ul class="match-strategy-list">
                  <li>Pierwszy rzut komunikacji kieruj do: <b>{html.escape(target_group_txt)}</b>.</li>
                  <li>Przygotuj 2 wersje kreacji: korzyść praktyczna oraz korzyść wartościowa (bardziej emocjonalna).</li>
                  <li>W kanałach bezpośrednich (SMS/e-mail) stosuj krótkie, jednowątkowe komunikaty.</li>
                </ul>
              </div>
              <div class="match-strategy-card">
                <div class="match-strategy-badge">🧪 Plan testów</div>
                <h4>Plan 14-dniowy (szybkie iteracje)</h4>
                <ul class="match-strategy-list">
                  <li>Dni 1-4: test 2 nagłówków dla osi „dopasowania” i 2 nagłówków dla osi „luki”.</li>
                  <li>Dni 5-9: utrzymaj lepszy wariant, zmieniaj tylko CTA i format (grafika / krótki tekst / wideo).</li>
                  <li>Dni 10-14: podsumuj reakcje i zamknij finalny zestaw przekazów dla najbliższej kampanii.</li>
                </ul>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

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


def personal_metryczka_view() -> None:
    require_auth()
    if not _ensure_jst_schema_initialized():
        st.warning("Nie udało się potwierdzić schematu metryczki. Spróbuj ponownie za chwilę.")
        return
    header("🧾 Metryczka ankiety")
    render_titlebar(["Panel", "Badania personalne", "Metryczka"])
    back_button("home_personal", "← Powrót do panelu personalnego")
    st.markdown('<div class="section-gap-big"></div>', unsafe_allow_html=True)

    studies = fetch_studies(sb)
    if not studies:
        st.info("Brak badań personalnych.")
        return

    counts_by_slug: Dict[str, int] = {}
    try:
        c_res = sb.from_("study_response_count_v").select("slug,responses").execute()
        for row in (c_res.data or []):
            slug = str(row.get("slug") or "").strip()
            if slug:
                counts_by_slug[slug] = int(row.get("responses") or 0)
    except Exception:
        counts_by_slug = {}

    options: Dict[str, Dict[str, Any]] = {}
    for s in studies:
        fn = str(s.get("first_name_nom") or s.get("first_name") or "").strip()
        ln = str(s.get("last_name_nom") or s.get("last_name") or "").strip()
        city = str(s.get("city") or "").strip()
        slug = str(s.get("slug") or "").strip()
        count = int(counts_by_slug.get(slug, 0))
        label = f"{ln} {fn} ({city}) – /{slug} • {count} odp."
        options[label] = s

    st.markdown(
        "<div style='font-size:17px;font-weight:800;margin-bottom:6px;'>Wybierz badanie</div>",
        unsafe_allow_html=True,
    )
    pick = st.selectbox(
        "Wybierz badanie",
        list(options.keys()),
        key="personal_metryczka_pick",
        label_visibility="collapsed",
    )
    study = options[pick]
    study_id = str(study.get("id") or "").strip()
    if study_id:
        try:
            fresh_res = sb.table("studies").select("*").eq("id", study_id).limit(1).execute()
            fresh_row = (fresh_res.data or [None])[0]
            if isinstance(fresh_row, dict):
                study = dict(fresh_row)
        except Exception:
            pass

    study = _apply_scheduled_survey_transitions(study, kind="personal")
    status_meta = _study_status_meta(study, kind="personal")
    slug = str(study.get("slug") or "").strip()
    survey_base = str(st.secrets.get("SURVEY_BASE_URL", "https://archetypy.badania.pro") or "").rstrip("/")
    survey_url = f"{survey_base}/{slug}" if slug else "—"

    info_rows = pd.DataFrame(
        [
            {
                "Status": status_meta["status_label"],
                "Liczba odpowiedzi": int(counts_by_slug.get(slug, 0)),
                "Link ankiety": survey_url,
            }
        ]
    )
    st.dataframe(info_rows, use_container_width=True, hide_index=True)
    st.caption("W ankiecie personalnej metryczka będzie częścią flow po ekranie powitalnym.")

    st.markdown('<div class="section-gap-big"></div>', unsafe_allow_html=True)
    st.markdown("### Konfiguracja metryczki")
    edited_cfg = _render_metryczka_editor(
        "personal",
        study_id or slug,
        _metryczka_normalize_config("personal", study.get("metryczka_config")),
    )

    _, save_col = st.columns([0.66, 0.34], gap="small")
    with save_col:
        save_clicked = st.button(
            "💾 Zapisz metryczkę",
            type="primary",
            key=f"personal_metryczka_save_{study_id or slug}",
            use_container_width=True,
        )
    if save_clicked:
        if not study_id:
            st.error("Brak identyfikatora badania.")
        else:
            valid, msg = _validate_metryczka_before_save(edited_cfg)
            if not valid:
                st.error(msg)
            else:
                cfg_norm = normalize_personal_metryczka_config(edited_cfg)
                try:
                    update_study(
                        sb,
                        study_id,
                        {
                            "metryczka_config": cfg_norm,
                            "metryczka_config_version": int(cfg_norm.get("version") or 1),
                        },
                    )
                    st.session_state[_metryczka_editor_state_key("personal", study_id or slug)] = deepcopy(cfg_norm)
                    st.success("Zapisano konfigurację metryczki.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Nie udało się zapisać metryczki: {exc}")


def personal_settings_view() -> None:
    require_auth()
    if not _ensure_jst_schema_initialized():
        st.warning("Nie udało się potwierdzić schematu parametrów ankiety. Część ustawień może być chwilowo niedostępna.")
    header("⚙️ Ustawienia ankiety")
    render_titlebar(["Panel", "Badania personalne", "Ustawienia ankiety"])
    back_button("home_personal", "← Powrót do panelu personalnego")
    st.markdown('<div class="section-gap-big"></div>', unsafe_allow_html=True)

    studies = fetch_studies(sb)
    if not studies:
        st.info("Brak badań personalnych.")
        return

    counts_by_slug: Dict[str, int] = {}
    try:
        c_res = sb.from_("study_response_count_v").select("slug,responses").execute()
        for row in (c_res.data or []):
            slug = str(row.get("slug") or "").strip()
            if slug:
                counts_by_slug[slug] = int(row.get("responses") or 0)
    except Exception:
        counts_by_slug = {}

    options: Dict[str, Dict[str, Any]] = {}
    for s in studies:
        fn = str(s.get("first_name_nom") or s.get("first_name") or "").strip()
        ln = str(s.get("last_name_nom") or s.get("last_name") or "").strip()
        city = str(s.get("city") or "").strip()
        slug = str(s.get("slug") or "").strip()
        count = int(counts_by_slug.get(slug, 0))
        label = f"{ln} {fn} ({city}) – /{slug} • {count} odp."
        options[label] = s

    st.markdown("<div style='font-size:17px;font-weight:800;margin-bottom:6px;'>Wybierz badanie</div>", unsafe_allow_html=True)
    pick = st.selectbox(
        "Wybierz badanie",
        list(options.keys()),
        key="personal_settings_pick",
        label_visibility="collapsed",
    )
    study = options[pick]
    study_id = str(study.get("id") or "").strip()
    if study_id:
        try:
            fresh_res = sb.table("studies").select("*").eq("id", study_id).limit(1).execute()
            fresh_row = (fresh_res.data or [None])[0]
            if isinstance(fresh_row, dict):
                study = fresh_row
        except Exception:
            pass
    study = _apply_scheduled_survey_transitions(study, kind="personal")
    status_meta = _study_status_meta(study, kind="personal")
    slug = str(study.get("slug") or "").strip()
    survey_base = str(st.secrets.get("SURVEY_BASE_URL", "https://archetypy.badania.pro") or "").rstrip("/")
    survey_url = f"{survey_base}/{slug}" if slug else "—"
    save_flash_key = f"personal_settings_saved_flash_{study_id or slug}"
    flash_msg = st.session_state.pop(save_flash_key, None)
    if flash_msg:
        _toast_success_compat(str(flash_msg))

    info_rows = pd.DataFrame(
        [
            {
                "Status": status_meta["status_label"],
                "Liczba odpowiedzi": int(counts_by_slug.get(slug, 0)),
                "Data uruchomienia": status_meta["started_at"],
                "Ostatnia zmiana statusu": status_meta["status_changed_at"],
                "Link ankiety": survey_url,
            }
        ]
    )
    st.dataframe(info_rows, use_container_width=True, hide_index=True)

    st.markdown('<div class="section-gap-big"></div>', unsafe_allow_html=True)
    st.markdown("### Parametry ankiety")
    cfg = _extract_survey_settings(study, allow_single=True)

    st.markdown("#### Wyświetlanie ankiety")
    mode_ui = st.radio(
        "Tryb wyświetlania pytań",
        ["Macierz", "Pojedyncze ekrany"],
        horizontal=True,
        key=f"personal_settings_mode_{study_id or slug}",
        index=1 if str(cfg.get("display_mode")) == "single" else 0,
    )
    randomize_questions = st.checkbox(
        "Losuj kolejność pytań",
        value=bool(cfg.get("randomize_questions")),
        key=f"personal_settings_randomize_{study_id or slug}",
        help="Działa zarówno dla widoku macierzowego (losowa kolejność wierszy), jak i pojedynczych ekranów.",
    )

    st.markdown("#### Nawigacja ankiety")
    show_progress = st.checkbox(
        "Pokaż pasek postępu",
        value=bool(cfg.get("show_progress")),
        key=f"personal_settings_progress_{study_id or slug}",
    )
    allow_back = st.checkbox(
        "Wyświetlaj przycisk Wstecz",
        value=bool(cfg.get("allow_back")),
        key=f"personal_settings_back_{study_id or slug}",
    )

    st.markdown("#### Powiadomienia")
    notify_on_response = st.checkbox(
        "Wysyłaj powiadomienie po uzyskaniu odpowiedzi",
        value=bool(cfg.get("notify_on_response")),
        key=f"personal_settings_notify_enabled_{study_id or slug}",
    )
    notify_email = st.text_input(
        "Adres e-mail do powiadomień",
        value=str(cfg.get("notify_email") or ""),
        key=f"personal_settings_notify_email_{study_id or slug}",
        disabled=not notify_on_response,
        placeholder="np. imie.nazwisko@domena.pl",
    )

    st.markdown("#### Automatyczny start i zakończenie badania")
    start_def_date, start_def_time = _utc_to_warsaw_input_defaults(
        cfg.get("auto_start_at"), fallback_hour=0, fallback_minute=0
    )
    end_def_date, end_def_time = _utc_to_warsaw_input_defaults(
        cfg.get("auto_end_at"), fallback_hour=23, fallback_minute=59
    )

    start_enabled = st.checkbox(
        "Aktywuj ankietę wybranego dnia",
        value=bool(cfg.get("auto_start_enabled")),
        key=f"personal_settings_auto_start_enabled_{study_id or slug}",
    )
    s_col1, s_col2 = st.columns([1, 1], gap="small")
    with s_col1:
        start_date = st.date_input(
            "Data startu",
            value=start_def_date,
            key=f"personal_settings_auto_start_date_{study_id or slug}",
            disabled=not start_enabled,
            label_visibility="collapsed",
        )
    with s_col2:
        start_time = st.time_input(
            "Godzina startu",
            value=start_def_time,
            key=f"personal_settings_auto_start_time_{study_id or slug}",
            disabled=not start_enabled,
            label_visibility="collapsed",
        )

    end_enabled = st.checkbox(
        "Zakończ ankietę wybranego dnia",
        value=bool(cfg.get("auto_end_enabled")),
        key=f"personal_settings_auto_end_enabled_{study_id or slug}",
    )
    e_col1, e_col2 = st.columns([1, 1], gap="small")
    with e_col1:
        end_date = st.date_input(
            "Data zakończenia",
            value=end_def_date,
            key=f"personal_settings_auto_end_date_{study_id or slug}",
            disabled=not end_enabled,
            label_visibility="collapsed",
        )
    with e_col2:
        end_time = st.time_input(
            "Godzina zakończenia",
            value=end_def_time,
            key=f"personal_settings_auto_end_time_{study_id or slug}",
            disabled=not end_enabled,
            label_visibility="collapsed",
        )

    if st.button(
        "💾 Zapisz parametry ankiety",
        type="primary",
        key=f"personal_settings_save_params_{study_id or slug}",
    ):
        notify_email_clean = str(notify_email or "").strip().lower()
        notify_email_valid = _normalize_notify_email(notify_email_clean)
        if notify_on_response and not notify_email_valid:
            st.error("Podaj poprawny adres e-mail do powiadomień.")
            return

        start_iso = _local_date_time_to_utc_iso(start_date, start_time) if start_enabled else None
        end_iso = _local_date_time_to_utc_iso(end_date, end_time) if end_enabled else None
        if start_enabled and not start_iso:
            st.error("Nie udało się odczytać daty/godziny startu ankiety.")
            return
        if end_enabled and not end_iso:
            st.error("Nie udało się odczytać daty/godziny zakończenia ankiety.")
            return
        start_dt = _parse_utc_dt(start_iso)
        end_dt = _parse_utc_dt(end_iso)
        if start_enabled and end_enabled and start_dt and end_dt and start_dt >= end_dt:
            st.error("Data i godzina zakończenia muszą być późniejsze niż data i godzina startu.")
            return

        mode_value = "single" if mode_ui == "Pojedyncze ekrany" else "matrix"
        updates: Dict[str, Any] = {
            "survey_display_mode": mode_value,
            "survey_show_progress": bool(show_progress),
            "survey_allow_back": bool(allow_back),
            "survey_randomize_questions": bool(randomize_questions),
            "survey_auto_start_enabled": bool(start_enabled),
            "survey_auto_start_at": start_iso if start_enabled else None,
            "survey_auto_end_enabled": bool(end_enabled),
            "survey_auto_end_at": end_iso if end_enabled else None,
            "survey_notify_on_response": bool(notify_on_response),
            "survey_notify_email": notify_email_clean or None,
        }
        previous_notify_enabled = bool(cfg.get("notify_on_response"))
        previous_notify_email = _normalize_notify_email(cfg.get("notify_email"))
        current_count = int(counts_by_slug.get(slug, 0))
        if not notify_on_response:
            updates["survey_notify_last_count"] = current_count
        elif (not previous_notify_enabled) or (notify_email_valid != previous_notify_email):
            updates["survey_notify_last_count"] = current_count
            updates["survey_notify_last_sent_at"] = None

        if (bool(start_enabled) != bool(cfg.get("auto_start_enabled"))) or (
            bool(start_enabled) and str(start_iso or "") != str(cfg.get("auto_start_at") or "")
        ):
            updates["survey_auto_start_applied_at"] = None
        if not start_enabled:
            updates["survey_auto_start_applied_at"] = None
        if (bool(end_enabled) != bool(cfg.get("auto_end_enabled"))) or (
            bool(end_enabled) and str(end_iso or "") != str(cfg.get("auto_end_at") or "")
        ):
            updates["survey_auto_end_applied_at"] = None
        if not end_enabled:
            updates["survey_auto_end_applied_at"] = None

        preview_study = dict(study)
        preview_study.update(updates)
        updates.update(_scheduled_survey_transition_updates(preview_study, kind="personal"))
        try:
            update_study(sb, study_id, updates)
            st.session_state[save_flash_key] = "Zapisano parametry ankiety."
            st.rerun()
        except Exception as exc:
            st.error(f"Nie udało się zapisać parametrów ankiety: {exc}")

    def _do_suspend_personal() -> None:
        try:
            set_study_status(sb, str(study["id"]), "suspended")
            st.success("Badanie zostało zawieszone.")
            st.rerun()
        except Exception as exc:
            st.error(f"Nie udało się zawiesić badania: {exc}")

    def _do_unsuspend_personal() -> None:
        try:
            set_study_status(sb, str(study["id"]), "active")
            st.success("Badanie zostało odwieszone.")
            st.rerun()
        except Exception as exc:
            st.error(f"Nie udało się odwiesić badania: {exc}")

    def _do_close_personal() -> None:
        try:
            set_study_status(sb, str(study["id"]), "closed")
            st.success("Badanie zostało zamknięte na stałe.")
            st.rerun()
        except Exception as exc:
            st.error(f"Nie udało się zamknąć badania: {exc}")

    def _do_delete_personal() -> None:
        try:
            soft_delete_study(sb, str(study["id"]))
            st.success("Badanie oznaczone jako usunięte.")
            goto("home_personal")
        except Exception as exc:
            st.error(f"Nie udało się usunąć badania: {exc}")

    _render_study_status_panel(
        kind="personal",
        study=study,
        on_suspend=_do_suspend_personal,
        on_unsuspend=_do_unsuspend_personal,
        on_close=_do_close_personal,
        on_delete=_do_delete_personal,
        close_confirm_key=f"personal_settings_close_confirm_{study.get('id')}",
        delete_confirm_key=f"personal_settings_delete_confirm_{study.get('id')}",
    )


def personal_merge_view() -> None:
    require_auth()
    header("🔗 Połącz badania")
    render_titlebar(["Panel", "Badania personalne", "Połącz badania"])
    back_button("home_personal", "← Powrót do panelu personalnego")
    st.markdown('<div class="section-gap-big"></div>', unsafe_allow_html=True)

    studies = fetch_studies(sb)
    if len(studies) < 2:
        st.info("Do łączenia potrzebne są co najmniej 2 aktywne badania personalne.")
        return

    counts_by_slug: Dict[str, int] = {}
    try:
        c_res = sb.from_("study_response_count_v").select("slug,responses").execute()
        for row in (c_res.data or []):
            slug = str(row.get("slug") or "").strip()
            if slug:
                counts_by_slug[slug] = int(row.get("responses") or 0)
    except Exception:
        counts_by_slug = {}

    study_by_id: Dict[str, Dict[str, Any]] = {}
    labels_by_id: Dict[str, str] = {}
    for s in studies:
        sid = str(s.get("id") or "").strip()
        if not sid:
            continue
        fn = str(s.get("first_name_nom") or s.get("first_name") or "").strip()
        ln = str(s.get("last_name_nom") or s.get("last_name") or "").strip()
        city = str(s.get("city") or "").strip()
        slug = str(s.get("slug") or "").strip()
        cnt = int(counts_by_slug.get(slug, 0))
        study_by_id[sid] = s
        labels_by_id[sid] = f"{ln} {fn} ({city}) – /{slug} • {cnt} odp."

    target_ids = list(study_by_id.keys())
    target_id = st.selectbox(
        "Badanie główne (do tego badania dodamy wyniki z innych):",
        target_ids,
        key="personal_merge_target_id",
        format_func=lambda sid: labels_by_id.get(str(sid), str(sid)),
    )
    target_label = labels_by_id.get(target_id, target_id)
    st.caption(
        "Dodanie wyników nie usuwa odpowiedzi ze źródłowych badań. "
        "Operacja tworzy kopie odpowiedzi w badaniu głównym."
    )

    slots = st.session_state.get("personal_merge_source_slots")
    if not isinstance(slots, list) or not slots:
        slots = [""]
    slots = [str(x or "") for x in slots]
    st.session_state["personal_merge_source_slots"] = slots

    selected_ids: List[str] = []
    all_source_ids = [sid for sid in study_by_id.keys() if sid != target_id]

    for idx in range(len(slots)):
        key = f"personal_merge_source_pick_{idx}"
        current = slots[idx] if slots[idx] in all_source_ids else ""
        available = [sid for sid in all_source_ids if sid == current or sid not in selected_ids]
        choices = [""] + available
        if st.session_state.get(key) not in choices:
            st.session_state[key] = current if current in choices else ""
        picked = st.selectbox(
            f"Badanie źródłowe #{idx + 1}",
            choices,
            key=key,
            format_func=lambda sid: "— wybierz badanie —" if not sid else labels_by_id.get(str(sid), str(sid)),
        )
        slots[idx] = str(picked or "")
        if slots[idx]:
            selected_ids.append(slots[idx])

    st.session_state["personal_merge_source_slots"] = slots
    selected_unique = [sid for sid in selected_ids if sid and sid != target_id]

    a1, a2 = st.columns([1, 1])
    with a1:
        if st.button("➕ Dodaj badanie", key="personal_merge_add_slot", type="secondary", use_container_width=True):
            st.session_state["personal_merge_source_slots"] = slots + [""]
            st.rerun()
    with a2:
        if st.button(
            "➖ Usuń ostatnie",
            key="personal_merge_remove_slot",
            type="secondary",
            use_container_width=True,
            disabled=len(slots) <= 1,
        ):
            st.session_state["personal_merge_source_slots"] = slots[:-1] if len(slots) > 1 else [""]
            st.rerun()

    st.markdown('<div class="section-gap-big"></div>', unsafe_allow_html=True)
    if selected_unique:
        plan_df = pd.DataFrame(
            [
                {
                    "Badanie główne": target_label,
                    "Badanie źródłowe": labels_by_id.get(sid, sid),
                }
                for sid in selected_unique
            ]
        )
        st.dataframe(plan_df, use_container_width=True, hide_index=True)
    else:
        st.info("Dodaj co najmniej jedno badanie źródłowe.")

    if st.button("Dodaj", type="primary", disabled=not bool(selected_unique)):
        with st.spinner("Trwa łączenie wyników badań..."):
            before_count = fetch_personal_response_count(sb, target_id)
            merge_result = merge_personal_study_responses(sb, target_id, selected_unique)
            after_count = fetch_personal_response_count(sb, target_id)
        st.success(
            f"Dodano odpowiedzi: {int(merge_result.get('inserted_total') or 0)} "
            f"(pominięto: {int(merge_result.get('skipped_total') or 0)}). "
            f"Badanie główne: {before_count} → {after_count} odpowiedzi."
        )
        details = merge_result.get("details") or []
        if details:
            details_df = pd.DataFrame(details)
            details_df["source_study_id"] = details_df["source_study_id"].map(lambda sid: labels_by_id.get(str(sid), str(sid)))
            details_df = details_df.rename(
                columns={
                    "source_study_id": "Badanie źródłowe",
                    "inserted": "Dodane odpowiedzi",
                    "skipped": "Pominięte rekordy",
                }
            )
            st.dataframe(details_df, use_container_width=True, hide_index=True)


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
            st.rerun()
        except Exception as e:
            st.error(f"❌ Błąd zapisu: {e}")

    st.info("Status badania i działania administracyjne znajdziesz teraz w module „⚙️ Ustawienia ankiety”.")

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
        """
        <style>
          .block-container{
            max-width:98vw !important;
            padding-left:1.2rem !important;
            padding-right:1.2rem !important;
          }
        </style>
        """,
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
    options = {
        f"{s.get('last_name_nom') or s['last_name']} {s.get('first_name_nom') or s['first_name']} ({s['city']}) – /{s['slug']}"
        : s for s in studies
    }
    option_labels = list(options.keys())
    choice_key = "results_view_choice"
    if (choice_key not in st.session_state) or (st.session_state.get(choice_key) not in options):
        st.session_state[choice_key] = option_labels[0]
    open_demo_requested = False

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
        nav_btn_col, nav_links_col = st.columns([0.36, 0.64], gap="small")
        with nav_btn_col:
            open_demo_requested = st.button(
                "👥 Raport demograficzny",
                key="open_personal_demography_from_results_top",
                use_container_width=True,
            )
        with nav_links_col:
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

    choice = st.selectbox(
        "Wybierz widok",
        options=option_labels,
        label_visibility="collapsed",
        key=choice_key,
    )
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
    if open_demo_requested:
        st.session_state[f"personal_demo_page_{study['id']}"] = True
        st.rerun()
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
_notify_bg_meta = _start_notification_dispatcher_background()
if not bool((_notify_bg_meta or {}).get("enabled")):
    _run_response_notifications_dispatcher()
render_build_badge()
with st.sidebar:
    if logged_in():
        if st.button("Wyloguj"): st.session_state.clear(); st.rerun()

public_token = _get_query_token()
if public_token:
    public_report_view(public_token)
else:
    if logged_in():
        _run_metryczka_backfill_once()
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
    elif view == "personal_settings":
        personal_settings_view()
    elif view == "personal_metryczka":
        personal_metryczka_view()
    elif view == "personal_merge":
        personal_merge_view()
    elif view == "results":
        results_view()
    elif view == "send":
        send_link_view()
    elif view == "jst_add":
        jst_add_view()
    elif view == "jst_edit":
        jst_edit_view()
    elif view == "jst_settings":
        jst_settings_view()
    elif view == "jst_metryczka":
        jst_metryczka_view()
    elif view == "jst_send":
        jst_send_view()
    elif view == "jst_io":
        jst_io_view()
    elif view == "jst_analysis":
        jst_analysis_view()
    else:
        home_root_view()
