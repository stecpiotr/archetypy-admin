# db_utils.py

from __future__ import annotations
from typing import Dict, List, Optional
import os
from datetime import datetime
import streamlit as st
from supabase import create_client, Client

# ────────────────────────────────────────────────────────────────────────────────
# Łagodne importy z polish.py (fallbacki jeśli czegoś brak)
# ────────────────────────────────────────────────────────────────────────────────
try:
    import polish  # type: ignore
except Exception:
    polish = None  # type: ignore


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
# Fallbacki do auto-odmian
# ────────────────────────────────────────────────────────────────────────────────
def _safe(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception:
        return None


def _split_two(s: str) -> tuple[str, str]:
    s = (s or "").strip()
    if not s:
        return "", ""
    if " " in s:
        a, b = s.rsplit(" ", 1)  # ważne: rsplit
        return a.strip(), b.strip()
    return s, ""


def _auto_inflections(first: str, last: str, gender: str) -> Dict[str, str]:
    """Spróbuj policzyć wszystkie odmiany. Priorytet:
    1) polish.compute_all (jeśli jest),
    2) fallbacki: gen_*; ins/loc z pełnych fraz; reszta puste.
    """
    out: Dict[str, str] = {k: "" for k in [
        "first_name_gen","last_name_gen",
        "first_name_dat","last_name_dat",
        "first_name_acc","last_name_acc",
        "first_name_ins","last_name_ins",
        "first_name_loc","last_name_loc",
        "first_name_voc","last_name_voc",
    ]}
    if polish:
        comp = _safe(getattr(polish, "compute_all", None), first, last, gender)
        if isinstance(comp, dict):
            for k, v in comp.items():
                if isinstance(v, str) and k in out:
                    out[k] = v.strip()
        else:
            gen_first = _safe(getattr(polish, "gen_first_name", None), first, gender) or ""
            gen_last  = _safe(getattr(polish, "gen_last_name",  None), last,  gender) or ""
            out["first_name_gen"] = gen_first
            out["last_name_gen"]  = gen_last

            loc_full = (_safe(getattr(polish, "loc_person", None), first, last, gender) or "").strip()
            ins_full = (_safe(getattr(polish, "instr_person", None), first, last, gender) or "").strip()
            fn, ln = _split_two(loc_full)
            out["first_name_loc"], out["last_name_loc"] = fn, ln
            fn, ln = _split_two(ins_full)
            out["first_name_ins"], out["last_name_ins"] = fn, ln
    return out


_CASES = ("gen", "dat", "acc", "ins", "loc", "voc")


def _attach_inflections_for_insert(payload: Dict) -> Dict:
    """Uzupełnia TYLKO BRAKUJĄCE pola podczas INSERT. Sluga nie nadpisuje."""
    first = (payload.get("first_name") or "").strip()
    last  = (payload.get("last_name")  or "").strip()
    gender = ((payload.get("gender") or "M")[:1]).upper()

    payload.setdefault("first_name_nom", first)
    payload.setdefault("last_name_nom",  last)

    auto = _auto_inflections(first, last, gender)
    for case in _CASES:
        fk = f"first_name_{case}"
        lk = f"last_name_{case}"
        if not (payload.get(fk) or "").strip():
            payload[fk] = (auto.get(fk) or "").strip()
        if not (payload.get(lk) or "").strip():
            payload[lk] = (auto.get(lk) or "").strip()

    # slug tylko jeśli pusty  ── obsługa 1-arg i 3-arg base_slug
    if not (payload.get("slug") or "").strip():
        if polish and hasattr(polish, "base_slug"):
            try:
                # Twój polish.py: base_slug(last_name)
                payload["slug"] = polish.base_slug(last)  # type: ignore[arg-type]
            except TypeError:
                # inny wariant (np. 3-arg)
                payload["slug"] = polish.base_slug(first, last, payload.get("city") or "")  # type: ignore[misc]
        else:
            raw = "-".join([x for x in [first, last, payload.get("city", "")] if x]).lower()
            payload["slug"] = "".join(ch if ch.isalnum() or ch == "-" else "-" for ch in raw).strip("-")
    return payload


# ────────────────────────────────────────────────────────────────────────────────
# CRUD (z obsługą soft-delete)
# ────────────────────────────────────────────────────────────────────────────────
def fetch_studies(sb: Client) -> List[Dict]:
    res = (
        sb.table("studies")
        .select("*")
        .or_("is_active.is.true,is_active.is.null")  # tylko aktywne
        .order("created_at", desc=True)
        .execute()
    )
    return res.data or []


def insert_study(sb: Client, payload: Dict) -> Dict:
    """INSERT: uzupełnij brakujące odmiany, ale trzymaj się podanego sluga.
    Jeśli DB zwróci inny slug (np. trigger), spróbuj od razu przestawić na podany."""
    desired_slug = (payload.get("slug") or "").strip()
    payload = _attach_inflections_for_insert(payload.copy())

    ins = sb.table("studies").insert(payload).execute()
    if not ins.data:
        sel = sb.table("studies").select("*").eq("slug", payload["slug"]).limit(1).execute()
        if sel.data:
            return sel.data[0]
        raise RuntimeError("Insert failed (no data returned).")

    row = ins.data[0]
    returned_slug = (row.get("slug") or "").strip()
    if desired_slug and returned_slug and desired_slug != returned_slug:
        # Spróbuj wymusić sluga, jeśli wolny
        try:
            exists = sb.table("studies").select("id").eq("slug", desired_slug).limit(1).execute().data
            if not exists:
                sb.table("studies").update({"slug": desired_slug}).eq("id", row["id"]).execute()
                row = sb.table("studies").select("*").eq("id", row["id"]).limit(1).execute().data[0]
        except Exception:
            pass
    return row


def update_study(sb: Client, study_id: str, payload: Dict) -> Dict:
    """UPDATE: NIE uzupełniamy braków automatem – aktualizujemy tylko to, co przyszło."""
    upd = payload.copy()

    # Jeżeli zmienia się imię/nazwisko – zadbaj o *_nom (spójność)
    if "first_name" in upd:
        upd.setdefault("first_name_nom", (upd.get("first_name") or "").strip())
    if "last_name" in upd:
        upd.setdefault("last_name_nom", (upd.get("last_name") or "").strip())

    # Jeśli slug pusty, nie dotykaj istniejącego w DB
    if not (upd.get("slug") or "").strip():
        upd.pop("slug", None)

    sb.table("studies").update(upd).eq("id", study_id).execute()
    res = sb.table("studies").select("*").eq("id", study_id).limit(1).execute()
    if res.data:
        return res.data[0]
    raise RuntimeError("Update failed (no data returned).")


def soft_delete_study(sb: Client, study_id: str) -> None:
    """Soft-delete: oznacza badanie jako nieaktywne zamiast fizycznego usuwania."""
    sb.table("studies").update({
        "is_active": False,
        "deleted_at": datetime.utcnow().isoformat()
    }).eq("id", study_id).execute()


def check_slug_availability(sb: Client, slug: str) -> bool:
    if not (slug or "").strip():
        return False
    res = sb.table("studies").select("id").eq("slug", slug.strip()).limit(1).execute()
    return len(res.data or []) == 0
