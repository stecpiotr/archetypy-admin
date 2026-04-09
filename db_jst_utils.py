from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable, List, Optional
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
      population_15_plus INTEGER NULL,
      is_active BOOLEAN NOT NULL DEFAULT TRUE,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      deleted_at TIMESTAMPTZ NULL
    );

    ALTER TABLE public.jst_studies
      ADD COLUMN IF NOT EXISTS poststrat_targets JSONB NULL;
    ALTER TABLE public.jst_studies
      ADD COLUMN IF NOT EXISTS population_15_plus INTEGER NULL;

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

    CREATE OR REPLACE VIEW public.jst_response_count_v
      WITH (security_invoker = on) AS
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
          population_15_plus,
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

    CREATE TABLE IF NOT EXISTS public.jst_sms_messages (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      study_id TEXT NOT NULL REFERENCES public.jst_studies(id) ON DELETE CASCADE,
      phone TEXT NOT NULL,
      body TEXT NOT NULL,
      token TEXT NOT NULL UNIQUE,
      status TEXT NOT NULL DEFAULT 'queued',
      provider_message_id TEXT NULL,
      error_text TEXT NULL,
      clicked_at TIMESTAMPTZ NULL,
      started_at TIMESTAMPTZ NULL,
      completed_at TIMESTAMPTZ NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    ALTER TABLE public.jst_sms_messages ADD COLUMN IF NOT EXISTS clicked_at TIMESTAMPTZ NULL;
    ALTER TABLE public.jst_sms_messages ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ NULL;
    ALTER TABLE public.jst_sms_messages ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ NULL;
    ALTER TABLE public.jst_sms_messages ADD COLUMN IF NOT EXISTS rejected_at TIMESTAMPTZ NULL;
    ALTER TABLE public.jst_sms_messages ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

    CREATE INDEX IF NOT EXISTS idx_jst_sms_messages_study ON public.jst_sms_messages(study_id);
    CREATE INDEX IF NOT EXISTS idx_jst_sms_messages_created ON public.jst_sms_messages(created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_jst_sms_messages_token ON public.jst_sms_messages(token);

    CREATE TABLE IF NOT EXISTS public.jst_email_logs (
      id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      study_id TEXT NOT NULL REFERENCES public.jst_studies(id) ON DELETE CASCADE,
      email TEXT NOT NULL,
      subject TEXT NOT NULL,
      text TEXT NOT NULL,
      token TEXT NOT NULL UNIQUE,
      status TEXT NOT NULL DEFAULT 'queued',
      provider_message_id TEXT NULL,
      error_text TEXT NULL,
      clicked_at TIMESTAMPTZ NULL,
      started_at TIMESTAMPTZ NULL,
      completed_at TIMESTAMPTZ NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    ALTER TABLE public.jst_email_logs ADD COLUMN IF NOT EXISTS clicked_at TIMESTAMPTZ NULL;
    ALTER TABLE public.jst_email_logs ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ NULL;
    ALTER TABLE public.jst_email_logs ADD COLUMN IF NOT EXISTS completed_at TIMESTAMPTZ NULL;
    ALTER TABLE public.jst_email_logs ADD COLUMN IF NOT EXISTS rejected_at TIMESTAMPTZ NULL;
    ALTER TABLE public.jst_email_logs ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

    CREATE INDEX IF NOT EXISTS idx_jst_email_logs_study ON public.jst_email_logs(study_id);
    CREATE INDEX IF NOT EXISTS idx_jst_email_logs_created ON public.jst_email_logs(created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_jst_email_logs_token ON public.jst_email_logs(token);

    CREATE OR REPLACE FUNCTION public.mark_jst_sms_clicked(p_token text)
    RETURNS void
    LANGUAGE plpgsql
    SECURITY DEFINER
    SET search_path = public
    AS $func$
    BEGIN
      IF trim(coalesce(p_token, '')) = '' THEN
        RETURN;
      END IF;
      UPDATE public.jst_sms_messages
      SET clicked_at = COALESCE(clicked_at, NOW()),
          updated_at = NOW()
      WHERE token = trim(p_token);
    END;
    $func$;

    CREATE OR REPLACE FUNCTION public.mark_jst_sms_started(p_token text)
    RETURNS void
    LANGUAGE plpgsql
    SECURITY DEFINER
    SET search_path = public
    AS $func$
    BEGIN
      IF trim(coalesce(p_token, '')) = '' THEN
        RETURN;
      END IF;
      UPDATE public.jst_sms_messages
      SET started_at = COALESCE(started_at, NOW()),
          updated_at = NOW()
      WHERE token = trim(p_token);
    END;
    $func$;

    CREATE OR REPLACE FUNCTION public.mark_jst_sms_completed(p_token text)
    RETURNS void
    LANGUAGE plpgsql
    SECURITY DEFINER
    SET search_path = public
    AS $func$
    BEGIN
      IF trim(coalesce(p_token, '')) = '' THEN
        RETURN;
      END IF;
      UPDATE public.jst_sms_messages
      SET completed_at = COALESCE(completed_at, NOW()),
          updated_at = NOW()
      WHERE token = trim(p_token);
    END;
    $func$;

    CREATE OR REPLACE FUNCTION public.mark_jst_sms_rejected(p_token text)
    RETURNS void
    LANGUAGE plpgsql
    SECURITY DEFINER
    SET search_path = public
    AS $func$
    BEGIN
      IF trim(coalesce(p_token, '')) = '' THEN
        RETURN;
      END IF;
      UPDATE public.jst_sms_messages
      SET rejected_at = COALESCE(rejected_at, NOW()),
          updated_at = NOW()
      WHERE token = trim(p_token);
    END;
    $func$;

    CREATE OR REPLACE FUNCTION public.mark_jst_email_clicked(p_token text)
    RETURNS void
    LANGUAGE plpgsql
    SECURITY DEFINER
    SET search_path = public
    AS $func$
    BEGIN
      IF trim(coalesce(p_token, '')) = '' THEN
        RETURN;
      END IF;
      UPDATE public.jst_email_logs
      SET clicked_at = COALESCE(clicked_at, NOW()),
          updated_at = NOW()
      WHERE token = trim(p_token);
    END;
    $func$;

    CREATE OR REPLACE FUNCTION public.mark_jst_email_started(p_token text)
    RETURNS void
    LANGUAGE plpgsql
    SECURITY DEFINER
    SET search_path = public
    AS $func$
    BEGIN
      IF trim(coalesce(p_token, '')) = '' THEN
        RETURN;
      END IF;
      UPDATE public.jst_email_logs
      SET started_at = COALESCE(started_at, NOW()),
          updated_at = NOW()
      WHERE token = trim(p_token);
    END;
    $func$;

    CREATE OR REPLACE FUNCTION public.mark_jst_email_completed(p_token text)
    RETURNS void
    LANGUAGE plpgsql
    SECURITY DEFINER
    SET search_path = public
    AS $func$
    BEGIN
      IF trim(coalesce(p_token, '')) = '' THEN
        RETURN;
      END IF;
      UPDATE public.jst_email_logs
      SET completed_at = COALESCE(completed_at, NOW()),
          updated_at = NOW()
      WHERE token = trim(p_token);
    END;
    $func$;

    CREATE OR REPLACE FUNCTION public.mark_jst_email_rejected(p_token text)
    RETURNS void
    LANGUAGE plpgsql
    SECURITY DEFINER
    SET search_path = public
    AS $func$
    BEGIN
      IF trim(coalesce(p_token, '')) = '' THEN
        RETURN;
      END IF;
      UPDATE public.jst_email_logs
      SET rejected_at = COALESCE(rejected_at, NOW()),
          updated_at = NOW()
      WHERE token = trim(p_token);
    END;
    $func$;

    CREATE OR REPLACE FUNCTION public.mark_jst_token_started(p_token text)
    RETURNS void
    LANGUAGE plpgsql
    SECURITY DEFINER
    SET search_path = public
    AS $func$
    BEGIN
      IF trim(coalesce(p_token, '')) = '' THEN
        RETURN;
      END IF;
      PERFORM public.mark_jst_sms_started(p_token);
      PERFORM public.mark_jst_email_started(p_token);
    END;
    $func$;

    CREATE OR REPLACE FUNCTION public.mark_jst_token_completed(p_token text)
    RETURNS void
    LANGUAGE plpgsql
    SECURITY DEFINER
    SET search_path = public
    AS $func$
    BEGIN
      IF trim(coalesce(p_token, '')) = '' THEN
        RETURN;
      END IF;
      PERFORM public.mark_jst_sms_completed(p_token);
      PERFORM public.mark_jst_email_completed(p_token);
    END;
    $func$;

    CREATE OR REPLACE FUNCTION public.mark_jst_token_rejected(p_token text)
    RETURNS void
    LANGUAGE plpgsql
    SECURITY DEFINER
    SET search_path = public
    AS $func$
    BEGIN
      IF trim(coalesce(p_token, '')) = '' THEN
        RETURN;
      END IF;
      PERFORM public.mark_jst_sms_rejected(p_token);
      PERFORM public.mark_jst_email_rejected(p_token);
    END;
    $func$;

    CREATE OR REPLACE FUNCTION public.get_jst_token_meta(p_token text)
    RETURNS jsonb
    LANGUAGE plpgsql
    SECURITY DEFINER
    SET search_path = public
    AS $func$
    DECLARE
      v_token text := trim(coalesce(p_token, ''));
      v_channel text;
      v_contact text;
      v_study_id text;
      v_study_slug text;
      v_completed_at timestamptz;
      v_rejected_at timestamptz;
    BEGIN
      IF v_token = '' THEN
        RETURN jsonb_build_object(
          'found', false,
          'completed', false,
          'rejected', false
        );
      END IF;

      SELECT x.channel, x.contact, x.study_id, x.study_slug, x.completed_at, x.rejected_at
      INTO v_channel, v_contact, v_study_id, v_study_slug, v_completed_at, v_rejected_at
      FROM (
        SELECT
          'sms'::text AS channel,
          m.phone::text AS contact,
          m.study_id::text AS study_id,
          s.slug::text AS study_slug,
          m.completed_at,
          m.rejected_at,
          m.created_at
        FROM public.jst_sms_messages m
        LEFT JOIN public.jst_studies s ON s.id = m.study_id
        WHERE m.token = v_token

        UNION ALL

        SELECT
          'email'::text AS channel,
          e.email::text AS contact,
          e.study_id::text AS study_id,
          s.slug::text AS study_slug,
          e.completed_at,
          e.rejected_at,
          e.created_at
        FROM public.jst_email_logs e
        LEFT JOIN public.jst_studies s ON s.id = e.study_id
        WHERE e.token = v_token
      ) x
      ORDER BY
        CASE WHEN x.completed_at IS NOT NULL THEN 0 ELSE 1 END,
        x.created_at DESC
      LIMIT 1;

      IF v_channel IS NULL THEN
        RETURN jsonb_build_object(
          'found', false,
          'completed', false,
          'rejected', false
        );
      END IF;

      RETURN jsonb_build_object(
        'found', true,
        'channel', v_channel,
        'contact', coalesce(v_contact, ''),
        'study_id', coalesce(v_study_id, ''),
        'study_slug', coalesce(v_study_slug, ''),
        'completed', (v_completed_at IS NOT NULL),
        'rejected', (v_rejected_at IS NOT NULL),
        'completed_at', v_completed_at,
        'rejected_at', v_rejected_at
      );
    END;
    $func$;

    CREATE OR REPLACE FUNCTION public.is_jst_token_completed(p_token text)
    RETURNS boolean
    LANGUAGE plpgsql
    SECURITY DEFINER
    SET search_path = public
    AS $func$
    DECLARE
      v_token text := trim(coalesce(p_token, ''));
      v_done boolean := false;
    BEGIN
      IF v_token = '' THEN
        RETURN false;
      END IF;

      SELECT
        EXISTS(
          SELECT 1
          FROM public.jst_sms_messages
          WHERE token = v_token AND (completed_at IS NOT NULL OR rejected_at IS NOT NULL)
        )
        OR
        EXISTS(
          SELECT 1
          FROM public.jst_email_logs
          WHERE token = v_token AND (completed_at IS NOT NULL OR rejected_at IS NOT NULL)
        )
      INTO v_done;

      RETURN COALESCE(v_done, false);
    END;
    $func$;

    GRANT EXECUTE ON FUNCTION public.get_jst_study_public(text) TO anon, authenticated;
    GRANT EXECUTE ON FUNCTION public.add_jst_response_by_slug(text, jsonb, text) TO anon, authenticated;
    GRANT EXECUTE ON FUNCTION public.mark_jst_sms_clicked(text) TO anon, authenticated;
    GRANT EXECUTE ON FUNCTION public.mark_jst_sms_started(text) TO anon, authenticated;
    GRANT EXECUTE ON FUNCTION public.mark_jst_sms_completed(text) TO anon, authenticated;
    GRANT EXECUTE ON FUNCTION public.mark_jst_sms_rejected(text) TO anon, authenticated;
    GRANT EXECUTE ON FUNCTION public.mark_jst_email_clicked(text) TO anon, authenticated;
    GRANT EXECUTE ON FUNCTION public.mark_jst_email_started(text) TO anon, authenticated;
    GRANT EXECUTE ON FUNCTION public.mark_jst_email_completed(text) TO anon, authenticated;
    GRANT EXECUTE ON FUNCTION public.mark_jst_email_rejected(text) TO anon, authenticated;
    GRANT EXECUTE ON FUNCTION public.mark_jst_token_started(text) TO anon, authenticated;
    GRANT EXECUTE ON FUNCTION public.mark_jst_token_completed(text) TO anon, authenticated;
    GRANT EXECUTE ON FUNCTION public.mark_jst_token_rejected(text) TO anon, authenticated;
    GRANT EXECUTE ON FUNCTION public.get_jst_token_meta(text) TO anon, authenticated;
    GRANT EXECUTE ON FUNCTION public.is_jst_token_completed(text) TO anon, authenticated;

    DO $cleanup$
    DECLARE
      r record;
      v_new_slug text;
    BEGIN
      FOR r IN
        SELECT id, slug
        FROM public.jst_studies
        WHERE COALESCE(is_active, false) = false
          AND COALESCE(slug, '') <> ''
          AND POSITION('--deleted--' IN slug) = 0
      LOOP
        v_new_slug := r.slug || '--deleted--' || left(r.id::text, 8) || '--' || to_char(clock_timestamp(), 'YYYYMMDDHH24MISSMS');
        BEGIN
          UPDATE public.jst_studies
          SET slug = v_new_slug,
              updated_at = NOW(),
              deleted_at = COALESCE(deleted_at, NOW())
          WHERE id = r.id;
        EXCEPTION WHEN unique_violation THEN
          UPDATE public.jst_studies
          SET slug = '__deleted__' || left(r.id::text, 8) || '__' || to_char(clock_timestamp(), 'YYYYMMDDHH24MISSMS'),
              updated_at = NOW(),
              deleted_at = COALESCE(deleted_at, NOW())
          WHERE id = r.id;
        END;
      END LOOP;
    END;
    $cleanup$;
    """
    with _db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
        conn.commit()
    _notify_postgrest_schema_reload()


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _notify_postgrest_schema_reload() -> None:
    try:
        with _db_connect() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT pg_notify('pgrst', 'reload schema');")
            conn.commit()
    except Exception:
        # Brak uprawnień do notify nie powinien zatrzymywać działania panelu.
        pass


def _is_postgrest_missing_column_error(err: Exception, table_name: str, column_name: str) -> bool:
    msg = (getattr(err, "message", "") or str(err) or "").lower()
    return (
        "pgrst204" in msg
        and str(table_name or "").lower() in msg
        and str(column_name or "").lower() in msg
    )


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
    try:
        ins = sb.table("jst_studies").insert(data).execute()
    except Exception as e:
        if "population_15_plus" in data and _is_postgrest_missing_column_error(e, "jst_studies", "population_15_plus"):
            _notify_postgrest_schema_reload()
            ins = sb.table("jst_studies").insert(data).execute()
        else:
            raise
    if ins.data:
        return ins.data[0]
    raise RuntimeError("Insert jst_study failed")


def update_jst_study(sb: Client, study_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload)
    data["updated_at"] = _utc_now_iso()
    try:
        sb.table("jst_studies").update(data).eq("id", str(study_id)).execute()
    except Exception as e:
        if "population_15_plus" in data and _is_postgrest_missing_column_error(e, "jst_studies", "population_15_plus"):
            _notify_postgrest_schema_reload()
            sb.table("jst_studies").update(data).eq("id", str(study_id)).execute()
        else:
            raise
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


def _release_inactive_slug_conflicts(sb: Client, slug: str, exclude_id: Optional[str] = None) -> None:
    s = (slug or "").strip()
    if not s:
        return
    try:
        rows = sb.table("jst_studies").select("id,slug,is_active,deleted_at").eq("slug", s).execute().data or []
    except Exception:
        return

    now_tag = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    for row in rows:
        rid = str(row.get("id") or "").strip()
        if not rid:
            continue
        if exclude_id and rid == str(exclude_id):
            continue
        is_active = bool(row.get("is_active") is True and not row.get("deleted_at"))
        if is_active:
            continue

        archived_slug = f"{s}--deleted--{rid[:8]}--{now_tag}"
        try:
            sb.table("jst_studies").update(
                {
                    "slug": archived_slug,
                    "deleted_at": row.get("deleted_at") or _utc_now_iso(),
                    "updated_at": _utc_now_iso(),
                }
            ).eq("id", rid).execute()
        except Exception:
            # Fallback jeśli suffix wygenerował konflikt unikalności.
            try:
                sb.table("jst_studies").update(
                    {
                        "slug": f"__deleted__{rid[:8]}__{now_tag}",
                        "deleted_at": row.get("deleted_at") or _utc_now_iso(),
                        "updated_at": _utc_now_iso(),
                    }
                ).eq("id", rid).execute()
            except Exception:
                # Nie blokujemy działania formularza.
                pass


def check_jst_slug_availability(sb: Client, slug: str, exclude_id: Optional[str] = None) -> bool:
    s = (slug or "").strip()
    if not s:
        return False
    _release_inactive_slug_conflicts(sb, s, exclude_id=exclude_id)
    q = sb.table("jst_studies").select("id").eq("slug", s).eq("is_active", True).limit(1)
    if exclude_id:
        q = q.neq("id", str(exclude_id))
    res = q.execute()
    return len(res.data or []) == 0


def _fetch_all_pages(
    fetch_page: Callable[[int, int], List[Dict[str, Any]]],
    page_size: int = 1000,
) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    offset = 0
    limit = max(100, int(page_size))
    while True:
        chunk = fetch_page(offset, offset + limit - 1) or []
        if not chunk:
            break
        out.extend(chunk)
        if len(chunk) < limit:
            break
        offset += limit
    return out


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
        rows = _fetch_all_pages(
            lambda frm, to: (
                sb.table("jst_responses")
                .select("study_id")
                .order("study_id", desc=False)
                .range(frm, to)
                .execute()
                .data
                or []
            )
        )
        for r in rows:
            sid = str(r.get("study_id") or "").strip()
            if sid:
                out[sid] = int(out.get(sid, 0)) + 1
    except Exception:
        pass
    return out


def list_jst_responses(sb: Client, study_id: str) -> List[Dict[str, Any]]:
    sid = str(study_id or "").strip()
    if not sid:
        return []
    return _fetch_all_pages(
        lambda frm, to: (
            sb.table("jst_responses")
            .select("*")
            .eq("study_id", sid)
            .order("created_at", desc=False)
            .order("id", desc=False)
            .range(frm, to)
            .execute()
            .data
            or []
        )
    )


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
