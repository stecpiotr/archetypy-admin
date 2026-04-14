# db_utils.py

from __future__ import annotations
from typing import Dict, List, Optional, Any
import ast
import json
import os
from datetime import datetime
import streamlit as st
from supabase import create_client, Client
from metryczka_config import default_personal_metryczka_config, normalize_personal_metryczka_config

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
_ALLOWED_STUDY_STATUSES = {"active", "suspended", "closed", "deleted"}


def _utc_now_iso() -> str:
    return datetime.utcnow().isoformat()


def normalize_study_status(raw: Optional[str], *, is_active: Optional[bool] = None, deleted_at: Optional[str] = None) -> str:
    status = str(raw or "").strip().lower()
    if status in _ALLOWED_STUDY_STATUSES:
        return status
    if deleted_at:
        return "deleted"
    if is_active is False:
        return "deleted"
    return "active"


def fetch_studies(sb: Client) -> List[Dict]:
    res = (
        sb.table("studies")
        .select("*")
        .or_("is_active.is.true,is_active.is.null")  # tylko aktywne
        .order("created_at", desc=True)
        .execute()
    )
    out: List[Dict[str, Any]] = []
    for row in (res.data or []):
        rec = dict(row)
        cfg = normalize_personal_metryczka_config(rec.get("metryczka_config"))
        rec["metryczka_config"] = cfg
        rec["metryczka_config_version"] = int(cfg.get("version") or 1)
        out.append(rec)
    return out


def insert_study(sb: Client, payload: Dict) -> Dict:
    """INSERT: uzupełnij brakujące odmiany, ale trzymaj się podanego sluga.
    Jeśli DB zwróci inny slug (np. trigger), spróbuj od razu przestawić na podany."""
    desired_slug = (payload.get("slug") or "").strip()
    payload = _attach_inflections_for_insert(payload.copy())
    raw_metryczka = payload.get("metryczka_config")
    cfg_metryczka = normalize_personal_metryczka_config(raw_metryczka)
    now_iso = _utc_now_iso()
    payload.setdefault("study_status", "active")
    payload.setdefault("status_changed_at", now_iso)
    payload.setdefault("started_at", now_iso)
    payload.setdefault("survey_notify_on_response", False)
    payload.setdefault("survey_notify_email", None)
    payload.setdefault("survey_notify_last_count", 0)
    payload.setdefault("survey_notify_last_sent_at", None)
    payload["metryczka_config"] = cfg_metryczka if raw_metryczka is not None else default_personal_metryczka_config()
    payload.setdefault("metryczka_config_version", int(cfg_metryczka.get("version") or 1))

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

    if "metryczka_config" in upd:
        cfg = normalize_personal_metryczka_config(upd.get("metryczka_config"))
        upd["metryczka_config"] = cfg
        upd["metryczka_config_version"] = int(cfg.get("version") or 1)

    sb.table("studies").update(upd).eq("id", study_id).execute()
    res = sb.table("studies").select("*").eq("id", study_id).limit(1).execute()
    if res.data:
        rec = dict(res.data[0])
        cfg = normalize_personal_metryczka_config(rec.get("metryczka_config"))
        rec["metryczka_config"] = cfg
        rec["metryczka_config_version"] = int(cfg.get("version") or 1)
        return rec
    raise RuntimeError("Update failed (no data returned).")


def soft_delete_study(sb: Client, study_id: str) -> None:
    """Soft-delete: oznacza badanie jako nieaktywne zamiast fizycznego usuwania."""
    sb.table("studies").update({
        "is_active": False,
        "deleted_at": _utc_now_iso(),
        "study_status": "deleted",
        "status_changed_at": _utc_now_iso(),
    }).eq("id", study_id).execute()


def set_study_status(sb: Client, study_id: str, status: str) -> Dict:
    sid = str(study_id or "").strip()
    target = str(status or "").strip().lower()
    if target not in {"active", "suspended", "closed"}:
        raise ValueError("Nieprawidłowy status badania.")
    row_res = sb.table("studies").select("*").eq("id", sid).limit(1).execute()
    row = (row_res.data or [None])[0]
    if not row:
        raise ValueError("Nie znaleziono badania.")
    current = normalize_study_status(
        row.get("study_status"),
        is_active=row.get("is_active"),
        deleted_at=row.get("deleted_at"),
    )
    if current == "deleted":
        raise ValueError("Usuniętego badania nie można zmienić.")
    if current == "closed" and target != "closed":
        raise ValueError("Badanie zamknięte jest trwałe i nie może zostać ponownie uruchomione.")
    now_iso = _utc_now_iso()
    updates = {
        "study_status": target,
        "status_changed_at": now_iso,
    }
    sb.table("studies").update(updates).eq("id", sid).execute()
    fresh_res = sb.table("studies").select("*").eq("id", sid).limit(1).execute()
    fresh = (fresh_res.data or [None])[0]
    if not fresh:
        raise RuntimeError("Nie udało się odświeżyć statusu badania.")
    return fresh


def _normalize_answers_for_merge(raw: Any) -> Optional[List[int]]:
    if isinstance(raw, list):
        out: List[int] = []
        for item in raw:
            try:
                out.append(int(item))
            except Exception:
                return None
        return out
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None
        for parser in (json.loads, ast.literal_eval):
            try:
                parsed = parser(text)
            except Exception:
                continue
            if isinstance(parsed, list):
                out2: List[int] = []
                ok = True
                for item in parsed:
                    try:
                        out2.append(int(item))
                    except Exception:
                        ok = False
                        break
                if ok:
                    return out2
        return None
    return None


def fetch_personal_response_count(sb: Client, study_id: str) -> int:
    sid = str(study_id or "").strip()
    if not sid:
        return 0
    res = sb.table("responses").select("id", count="exact", head=True).eq("study_id", sid).execute()
    return int(getattr(res, "count", 0) or 0)


def merge_personal_study_responses(
    sb: Client,
    target_study_id: str,
    source_study_ids: List[str],
    *,
    fetch_batch_size: int = 500,
    insert_batch_size: int = 200,
) -> Dict[str, Any]:
    target_id = str(target_study_id or "").strip()
    if not target_id:
        raise ValueError("Brak badania docelowego.")
    source_ids = []
    for raw in (source_study_ids or []):
        sid = str(raw or "").strip()
        if sid and sid != target_id and sid not in source_ids:
            source_ids.append(sid)
    if not source_ids:
        raise ValueError("Wybierz co najmniej jedno badanie źródłowe.")

    total_inserted = 0
    total_skipped = 0
    details: List[Dict[str, Any]] = []

    for source_id in source_ids:
        inserted = 0
        skipped = 0
        offset = 0
        while True:
            rows_res = (
                sb.table("responses")
                .select("answers,scores,raw_total")
                .eq("study_id", source_id)
                .range(offset, offset + fetch_batch_size - 1)
                .execute()
            )
            rows = rows_res.data or []
            if not rows:
                break

            payload_batch: List[Dict[str, Any]] = []
            for row in rows:
                answers = _normalize_answers_for_merge(row.get("answers"))
                if not answers:
                    skipped += 1
                    continue
                payload_batch.append(
                    {
                        "study_id": target_id,
                        "answers": answers,
                        "scores": row.get("scores"),
                        "raw_total": row.get("raw_total"),
                    }
                )

            for b_start in range(0, len(payload_batch), insert_batch_size):
                chunk = payload_batch[b_start : b_start + insert_batch_size]
                if not chunk:
                    continue
                sb.table("responses").insert(chunk).execute()
                inserted += len(chunk)

            if len(rows) < fetch_batch_size:
                break
            offset += fetch_batch_size

        total_inserted += inserted
        total_skipped += skipped
        details.append(
            {
                "source_study_id": source_id,
                "inserted": inserted,
                "skipped": skipped,
            }
        )

    return {
        "target_study_id": target_id,
        "source_study_ids": source_ids,
        "inserted_total": total_inserted,
        "skipped_total": total_skipped,
        "details": details,
    }


def check_slug_availability(sb: Client, slug: str) -> bool:
    if not (slug or "").strip():
        return False
    res = sb.table("studies").select("id").eq("slug", slug.strip()).limit(1).execute()
    return len(res.data or []) == 0
