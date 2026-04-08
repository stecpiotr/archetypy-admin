from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional
import re
import unicodedata
import uuid

import pandas as pd
import psycopg2
import streamlit as st
from supabase import Client


ARCHETYPES: List[str] = [
    "Władca", "Bohater", "Mędrzec", "Opiekun", "Kochanek", "Błazen",
    "Twórca", "Odkrywca", "Czarodziej", "Towarzysz", "Niewinny", "Buntownik",
]

B1_COLUMNS: List[str] = [f"B1_{a}" for a in ARCHETYPES]
A_COLUMNS: List[str] = [f"A{i}" for i in range(1, 19)]
D_COLUMNS: List[str] = [f"D{i}" for i in range(1, 13)]

CANONICAL_COLUMNS: List[str] = [
    "respondent_id",
    "M_PLEC",
    "M_WIEK",
    "M_WYKSZT",
    "M_ZAWOD",
    "M_MATERIAL",
    *A_COLUMNS,
    *B1_COLUMNS,
    "B2",
    *D_COLUMNS,
    "D13",
]

# Kolejność i dokładne etykiety wymagane przez analizator JST
M_PLEC_VALUES = ["kobieta", "mężczyzna"]
M_WIEK_VALUES = ["15-39", "40-59", "60 i więcej"]
M_WYKSZT_VALUES = [
    "podstawowe, gimnazjalne, zasadnicze zawodowe",
    "średnie",
    "wyższe",
]
M_ZAWOD_VALUES = [
    "pracownik umysłowy",
    "pracownik fizyczny",
    "prowadzę własną firmę",
    "student/uczeń",
    "bezrobotny",
    "rencista/emeryt",
    "inna (jaka?)",
]
M_MATERIAL_VALUES = [
    "powodzi mi się bardzo źle, jestem w ciężkiej sytuacji materialnej",
    "powodzi mi się raczej źle",
    "powodzi mi się przeciętnie, średnio",
    "powodzi mi się raczej dobrze",
    "powodzi mi się bardzo dobrze",
    "odmawiam udzielenia odpowiedzi",
]


def _db_connect():
    return psycopg2.connect(
        host=st.secrets["db_host"],
        dbname=st.secrets["db_name"],
        user=st.secrets["db_user"],
        password=st.secrets["db_pass"],
        port=int(st.secrets.get("db_port", 5432)),
        sslmode="require",
        connect_timeout=int(st.secrets.get("db_connect_timeout", 5)),
    )


def ensure_jst_schema() -> None:
    ddl = """
    CREATE EXTENSION IF NOT EXISTS pgcrypto;

    CREATE TABLE IF NOT EXISTS public.jst_studies (
      id TEXT PRIMARY KEY,
      jst_type TEXT NOT NULL CHECK (jst_type IN ('miasto','gmina')),
      jst_name TEXT NOT NULL,

      jst_name_nom TEXT NOT NULL,
      jst_name_gen TEXT NOT NULL,
      jst_name_dat TEXT NOT NULL,
      jst_name_acc TEXT NOT NULL,
      jst_name_ins TEXT NOT NULL,
      jst_name_loc TEXT NOT NULL,
      jst_name_voc TEXT NOT NULL,

      jst_full_nom TEXT NOT NULL,
      jst_full_gen TEXT NOT NULL,
      jst_full_dat TEXT NOT NULL,
      jst_full_acc TEXT NOT NULL,
      jst_full_ins TEXT NOT NULL,
      jst_full_loc TEXT NOT NULL,
      jst_full_voc TEXT NOT NULL,

      slug TEXT NOT NULL UNIQUE,
      poststrat_targets JSONB NULL,
      is_active BOOLEAN NOT NULL DEFAULT TRUE,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      deleted_at TIMESTAMPTZ NULL
    );

    ALTER TABLE public.jst_studies
      ADD COLUMN IF NOT EXISTS poststrat_targets JSONB NULL;

    CREATE INDEX IF NOT EXISTS idx_jst_studies_active ON public.jst_studies(is_active);
    CREATE INDEX IF NOT EXISTS idx_jst_studies_slug ON public.jst_studies(slug);

    CREATE TABLE IF NOT EXISTS public.jst_responses (
      id TEXT PRIMARY KEY,
      study_id TEXT NOT NULL,
      respondent_id TEXT NOT NULL,
      payload JSONB NOT NULL DEFAULT '{}'::jsonb,
      source TEXT NOT NULL DEFAULT 'web',
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      CONSTRAINT uq_jst_responses_study_respondent UNIQUE (study_id, respondent_id)
    );

    CREATE INDEX IF NOT EXISTS idx_jst_responses_study ON public.jst_responses(study_id);
    CREATE INDEX IF NOT EXISTS idx_jst_responses_created ON public.jst_responses(created_at);

    CREATE OR REPLACE VIEW public.jst_response_count_v AS
      SELECT study_id, COUNT(*)::INT AS responses
      FROM public.jst_responses
      GROUP BY study_id;

    ALTER TABLE public.jst_studies ENABLE ROW LEVEL SECURITY;
    ALTER TABLE public.jst_responses ENABLE ROW LEVEL SECURITY;

    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1
        FROM pg_policies
        WHERE schemaname = 'public'
          AND tablename = 'jst_studies'
          AND policyname = 'jst_studies_active_read'
      ) THEN
        CREATE POLICY jst_studies_active_read
          ON public.jst_studies
          FOR SELECT
          TO anon, authenticated
          USING (COALESCE(is_active, true));
      END IF;
    END$$;

    CREATE OR REPLACE FUNCTION public.get_jst_study_public(p_slug text)
    RETURNS jsonb
    LANGUAGE plpgsql
    SECURITY DEFINER
    SET search_path = public
    AS $func$
    DECLARE
      rec jsonb;
    BEGIN
      SELECT to_jsonb(s) INTO rec
      FROM (
        SELECT
          id,
          slug,
          jst_type,
          jst_name,
          jst_name_nom,
          jst_name_gen,
          jst_name_dat,
          jst_name_acc,
          jst_name_ins,
          jst_name_loc,
          jst_name_voc,
          jst_full_nom,
          jst_full_gen,
          jst_full_dat,
          jst_full_acc,
          jst_full_ins,
          jst_full_loc,
          jst_full_voc,
          is_active
        FROM public.jst_studies
        WHERE slug = trim(coalesce(p_slug, ''))
          AND COALESCE(is_active, true)
        LIMIT 1
      ) s;
      RETURN rec;
    END;
    $func$;

    CREATE OR REPLACE FUNCTION public.add_jst_response_by_slug(
      p_slug text,
      p_payload jsonb,
      p_respondent_id text DEFAULT NULL
    )
    RETURNS jsonb
    LANGUAGE plpgsql
    SECURITY DEFINER
    SET search_path = public
    AS $func$
    DECLARE
      v_study_id text;
      v_slug text;
      v_payload jsonb;
      v_resp_id text;
      v_n int;
      v_inserted text;
      v_try int := 0;
    BEGIN
      v_slug := trim(coalesce(p_slug, ''));
      IF v_slug = '' THEN
        RETURN jsonb_build_object('ok', false, 'error', 'missing_slug');
      END IF;

      SELECT id INTO v_study_id
      FROM public.jst_studies
      WHERE slug = v_slug
        AND COALESCE(is_active, true)
      LIMIT 1;

      IF v_study_id IS NULL THEN
        RETURN jsonb_build_object('ok', false, 'error', 'study_not_found');
      END IF;

      v_payload := COALESCE(p_payload, '{}'::jsonb);
      v_resp_id := trim(coalesce(p_respondent_id, ''));

      IF v_resp_id = '' THEN
        SELECT COALESCE(MAX((regexp_match(respondent_id, '^R(\\d+)$'))[1]::int), 0) + 1
          INTO v_n
        FROM public.jst_responses
        WHERE study_id = v_study_id
          AND respondent_id ~ '^R\\d+$';
        v_resp_id := 'R' || lpad(v_n::text, 4, '0');
      END IF;

      LOOP
        v_try := v_try + 1;

        INSERT INTO public.jst_responses (id, study_id, respondent_id, payload, source)
        VALUES (gen_random_uuid()::text, v_study_id, v_resp_id, v_payload, 'web')
        ON CONFLICT (study_id, respondent_id) DO NOTHING
        RETURNING id INTO v_inserted;

        IF v_inserted IS NOT NULL THEN
          RETURN jsonb_build_object(
            'ok', true,
            'id', v_inserted,
            'study_id', v_study_id,
            'respondent_id', v_resp_id
          );
        END IF;

        IF p_respondent_id IS NOT NULL AND trim(p_respondent_id) <> '' THEN
          RETURN jsonb_build_object(
            'ok', false,
            'error', 'duplicate_respondent_id',
            'respondent_id', v_resp_id
          );
        END IF;

        IF v_try >= 8 THEN
          RETURN jsonb_build_object(
            'ok', false,
            'error', 'cannot_generate_respondent_id'
          );
        END IF;

        SELECT COALESCE(MAX((regexp_match(respondent_id, '^R(\\d+)$'))[1]::int), 0) + 1
          INTO v_n
        FROM public.jst_responses
        WHERE study_id = v_study_id
          AND respondent_id ~ '^R\\d+$';
        v_resp_id := 'R' || lpad(v_n::text, 4, '0');
      END LOOP;
    END;
    $func$;

    GRANT EXECUTE ON FUNCTION public.get_jst_study_public(text) TO anon, authenticated;
    GRANT EXECUTE ON FUNCTION public.add_jst_response_by_slug(text, jsonb, text) TO anon, authenticated;
    """
    with _db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
        conn.commit()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def fetch_jst_studies(sb: Client, include_inactive: bool = False) -> List[Dict[str, Any]]:
    q = sb.table("jst_studies").select("*").order("created_at", desc=True)
    if not include_inactive:
        q = q.or_("is_active.is.true,is_active.is.null").is_("deleted_at", "null")
    res = q.execute()
    return res.data or []


def fetch_jst_study_by_id(sb: Client, study_id: str) -> Optional[Dict[str, Any]]:
    res = sb.table("jst_studies").select("*").eq("id", str(study_id)).limit(1).execute()
    data = res.data or []
    return data[0] if data else None


def insert_jst_study(sb: Client, payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload)
    data.setdefault("id", str(uuid.uuid4()))
    data.setdefault("is_active", True)
    data.setdefault("created_at", _utc_now_iso())
    data.setdefault("updated_at", _utc_now_iso())
    ins = sb.table("jst_studies").insert(data).execute()
    if ins.data:
        return ins.data[0]
    raise RuntimeError("Insert jst_study failed")


def update_jst_study(sb: Client, study_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload)
    data["updated_at"] = _utc_now_iso()
    sb.table("jst_studies").update(data).eq("id", str(study_id)).execute()
    rec = fetch_jst_study_by_id(sb, study_id)
    if rec:
        return rec
    raise RuntimeError("Update jst_study failed")


def soft_delete_jst_study(sb: Client, study_id: str) -> None:
    sid = str(study_id or "").strip()
    if not sid:
        return
    rec = fetch_jst_study_by_id(sb, sid) or {}
    old_slug = str(rec.get("slug") or "").strip()
    suffix = re.sub(r"[^0-9]", "", _utc_now_iso())
    archived_slug = f"__deleted__{sid[:8]}__{suffix}"
    if old_slug:
        archived_slug = f"{old_slug}--deleted--{sid[:8]}--{suffix}"
    sb.table("jst_studies").update(
        {
            "is_active": False,
            "deleted_at": _utc_now_iso(),
            "updated_at": _utc_now_iso(),
            "slug": archived_slug,
        }
    ).eq("id", sid).execute()


def check_jst_slug_availability(sb: Client, slug: str, exclude_id: Optional[str] = None) -> bool:
    s = (slug or "").strip()
    if not s:
        return False
    q = (
        sb.table("jst_studies")
        .select("id")
        .eq("slug", s)
        .or_("is_active.is.true,is_active.is.null")
        .is_("deleted_at", "null")
        .limit(1)
    )
    if exclude_id:
        q = q.neq("id", str(exclude_id))
    res = q.execute()
    return len(res.data or []) == 0


def fetch_jst_response_counts(sb: Client) -> Dict[str, int]:
    out: Dict[str, int] = {}
    try:
        res = sb.table("jst_response_count_v").select("study_id,responses").execute()
        for row in (res.data or []):
            sid = str(row.get("study_id") or "").strip()
            if sid:
                out[sid] = int(row.get("responses") or 0)
        return out
    except Exception:
        pass

    # fallback bez widoku
    try:
        rows = sb.table("jst_responses").select("study_id").execute().data or []
        for r in rows:
            sid = str(r.get("study_id") or "").strip()
            if sid:
                out[sid] = int(out.get(sid, 0)) + 1
    except Exception:
        pass
    return out


def list_jst_responses(sb: Client, study_id: str) -> List[Dict[str, Any]]:
    res = (
        sb.table("jst_responses")
        .select("*")
        .eq("study_id", str(study_id))
        .order("created_at", desc=False)
        .execute()
    )
    return res.data or []


def insert_jst_response(
    sb: Client,
    study_id: str,
    respondent_id: str,
    payload: Dict[str, Any],
    source: str = "web",
    skip_if_exists: bool = True,
) -> bool:
    rec = {
        "id": str(uuid.uuid4()),
        "study_id": str(study_id),
        "respondent_id": str(respondent_id),
        "payload": dict(payload),
        "source": str(source or "web"),
        "created_at": _utc_now_iso(),
        "updated_at": _utc_now_iso(),
    }
    try:
        ins = sb.table("jst_responses").insert(rec).execute()
        return bool(ins.data)
    except Exception as exc:
        msg = str(exc).lower()
        if skip_if_exists and ("duplicate" in msg or "unique" in msg or "23505" in msg or "conflict" in msg):
            return False
        raise


def _strip_accents(s: str) -> str:
    norm = unicodedata.normalize("NFKD", s or "")
    return "".join(ch for ch in norm if not unicodedata.combining(ch))


def _norm(s: Any) -> str:
    txt = str(s or "").strip().lower()
    txt = _strip_accents(txt)
    txt = re.sub(r"\s+", " ", txt)
    return txt


_ARCHETYPE_BY_NORM = {_norm(a): a for a in ARCHETYPES}


def canonical_archetype(value: Any) -> str:
    if value is None:
        return ""
    raw = str(value).strip()
    if not raw:
        return ""

    n = _norm(raw)
    if n in _ARCHETYPE_BY_NORM:
        return _ARCHETYPE_BY_NORM[n]

    # Obsługa numerów 1..12
    if n.isdigit():
        idx = int(n)
        if 1 <= idx <= len(ARCHETYPES):
            return ARCHETYPES[idx - 1]

    for a in ARCHETYPES:
        an = _norm(a)
        if n == an or n.startswith(an) or an.startswith(n):
            return a
    return raw


def _to_int_1_7(value: Any) -> Optional[int]:
    if value is None:
        return None
    txt = str(value).strip().replace(",", ".")
    if not txt:
        return None
    try:
        iv = int(float(txt))
    except Exception:
        return None
    return iv if 1 <= iv <= 7 else None


def _to_ab(value: Any) -> str:
    v = _norm(value)
    if v in {"a", "1", "+", "plus", "tak"}:
        return "A"
    if v in {"b", "2", "-", "minus", "nie"}:
        return "B"
    return ""


def _to_flag(value: Any) -> int:
    v = _norm(value)
    if v in {"1", "true", "t", "tak", "yes", "y", "on", "x"}:
        return 1
    return 0


def _norm_choice(value: Any, allowed: List[str]) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    n = _norm(raw)
    for opt in allowed:
        on = _norm(opt)
        if n == on or n in on or on in n:
            return opt
    return raw


def normalize_response_row(raw: Dict[str, Any], respondent_id_fallback: str = "") -> Dict[str, Any]:
    row: Dict[str, Any] = {c: "" for c in CANONICAL_COLUMNS}

    rid = str(raw.get("respondent_id") or raw.get("Respondent_ID") or "").strip()
    row["respondent_id"] = rid or str(respondent_id_fallback or "")

    row["M_PLEC"] = _norm_choice(raw.get("M_PLEC"), M_PLEC_VALUES)
    row["M_WIEK"] = _norm_choice(raw.get("M_WIEK"), M_WIEK_VALUES)
    row["M_WYKSZT"] = _norm_choice(raw.get("M_WYKSZT"), M_WYKSZT_VALUES)
    row["M_ZAWOD"] = _norm_choice(raw.get("M_ZAWOD"), M_ZAWOD_VALUES)
    row["M_MATERIAL"] = _norm_choice(raw.get("M_MATERIAL"), M_MATERIAL_VALUES)

    for col in A_COLUMNS:
        v = _to_int_1_7(raw.get(col))
        row[col] = int(v) if v is not None else ""

    for arche in ARCHETYPES:
        k = f"B1_{arche}"
        row[k] = int(_to_flag(raw.get(k)))

    row["B2"] = canonical_archetype(raw.get("B2"))

    for col in D_COLUMNS:
        row[col] = _to_ab(raw.get(col))

    row["D13"] = canonical_archetype(raw.get("D13"))

    return row


def response_rows_to_dataframe(rows: Iterable[Dict[str, Any]]) -> pd.DataFrame:
    out_rows: List[Dict[str, Any]] = []
    for idx, rec in enumerate(rows, start=1):
        payload = rec.get("payload") or {}
        if not isinstance(payload, dict):
            payload = {}
        merged = dict(payload)
        merged.setdefault("respondent_id", rec.get("respondent_id") or "")
        norm = normalize_response_row(merged, respondent_id_fallback=f"R{idx:04d}")
        if not norm.get("respondent_id"):
            norm["respondent_id"] = f"R{idx:04d}"
        out_rows.append(norm)

    df = pd.DataFrame(out_rows)
    for c in CANONICAL_COLUMNS:
        if c not in df.columns:
            df[c] = ""
    return df[CANONICAL_COLUMNS].copy()


def make_payload_from_row(row: Dict[str, Any]) -> Dict[str, Any]:
    payload = {k: row.get(k, "") for k in CANONICAL_COLUMNS if k != "respondent_id"}
    return payload
