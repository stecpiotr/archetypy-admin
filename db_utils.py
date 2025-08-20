# db_utils.py
from __future__ import annotations
from typing import Dict, List, Optional
import os
import streamlit as st
from supabase import create_client, Client
import polish

# ────────────────────────────────────────────────────────────────────────────────
# Supabase client
# ────────────────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_supabase() -> Client:
    def sec(key: str, default: Optional[str] = None) -> Optional[str]:
        try:
            return st.secrets.get(key, default)
        except Exception:
            return default

    url = sec("SUPABASE_URL") or os.getenv("SUPABASE_URL")
    key = (
        sec("SUPABASE_SERVICE_ROLE_KEY")
        or sec("SUPABASE_ANON_KEY")
        or sec("SUPABASE_KEY")
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
        or os.getenv("SUPABASE_KEY")
    )
    if not url or not key:
        raise RuntimeError(
            "Brak SUPABASE_URL / SUPABASE_*KEY. "
            "Uruchom `streamlit run ...` w katalogu z .streamlit/secrets.toml"
        )
    return create_client(url, key)

# ────────────────────────────────────────────────────────────────────────────────
# Helper: dołóż odmiany do payloadu (z poszanowaniem ręcznych nadpisów)
# ────────────────────────────────────────────────────────────────────────────────
def _attach_inflections(payload: Dict) -> Dict:
    first = (payload.get("first_name") or "").strip()
    last  = (payload.get("last_name")  or "").strip()
    gender = (payload.get("gender") or "M").strip()

    auto = polish.compute_all(first, last, gender)

    # jeżeli formularz podał ręcznie – nie nadpisujemy
    for k, v in auto.items():
        if not payload.get(k):
            payload[k] = v

    # slug – jeżeli pusty
    if not payload.get("slug"):
        payload["slug"] = polish.base_slug(first, last, payload.get("city") or "")
    return payload

# ────────────────────────────────────────────────────────────────────────────────
# CRUD
# ────────────────────────────────────────────────────────────────────────────────
def fetch_studies(sb: Client) -> List[Dict]:
    res = sb.table("studies").select("*").order("created_at", desc=True).execute()
    return res.data or []

def insert_study(sb: Client, payload: Dict) -> Dict:
    payload = _attach_inflections(payload)
    ins = sb.table("studies").insert(payload).execute()
    if ins.data:
        return ins.data[0]
    # fallback (gdy REST nie zwraca RETURNING)
    sel = sb.table("studies").select("*").eq("slug", payload["slug"]).limit(1).execute()
    if sel.data:
        return sel.data[0]
    raise RuntimeError("Insert failed (no data returned).")

def update_study(sb: Client, study_id: str, payload: Dict) -> Dict:
    payload = _attach_inflections(payload)
    sb.table("studies").update(payload).eq("id", study_id).execute()
    res = sb.table("studies").select("*").eq("id", study_id).limit(1).execute()
    if res.data:
        return res.data[0]
    raise RuntimeError("Update failed (no data returned).")

def check_slug_availability(sb: Client, slug: str) -> bool:
    res = sb.table("studies").select("id").eq("slug", slug).limit(1).execute()
    return len(res.data or []) == 0
