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
from metryczka_config import (
    default_jst_metryczka_config,
    guess_metry_value_emoji,
    guess_metry_variable_emoji,
    metryczka_custom_columns,
    metryczka_questions,
    normalize_jst_metryczka_config,
)


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
M_WIEK_VALUES = ["15-39", "40-59", "60+"]
M_WYKSZT_VALUES = [
    "podst./gim./zaw.",
    "średnie",
    "wyższe",
]
M_ZAWOD_VALUES = [
    "pracownik umysłowy",
    "pracownik fizyczny",
    "własna firma",
    "student/uczeń",
    "bezrobotny",
    "rencista/emeryt",
    "inna",
]
M_MATERIAL_VALUES = [
    "bardzo zła",
    "raczej zła",
    "przeciętna",
    "raczej dobra",
    "bardzo dobra",
    "odmowa",
]
_CUSTOM_METRY_COL_RE = re.compile(r"^M_[A-Z0-9_]{2,40}$")
_AUX_METRY_SUFFIXES: tuple[str, ...] = (
    "_OTHER",
    "_INNE",
    "_OPEN",
    "_TEXT",
    "_TXT",
    "_FREE",
    "_DESC",
    "_COMMENT",
)


def _is_aux_metry_column(col: Any) -> bool:
    key = str(col or "").strip().upper()
    if not key.startswith("M_"):
        return False
    return any(key.endswith(sfx) for sfx in _AUX_METRY_SUFFIXES)


def _metry_open_option_codes_by_column(metryczka_config: Any = None) -> Dict[str, set[str]]:
    out: Dict[str, set[str]] = {}
    for q in metryczka_questions(metryczka_config):
        if not isinstance(q, dict):
            continue
        col = str(q.get("db_column") or q.get("id") or "").strip().upper()
        if not col.startswith("M_"):
            continue
        open_codes: set[str] = set()
        for opt in list(q.get("options") or []):
            if not isinstance(opt, dict):
                continue
            label = str(opt.get("label") or "").strip()
            code = str(opt.get("code") or label).strip()
            is_open = bool(opt.get("is_open") is True) or ("inna (jaka?)" in label.lower())
            if not is_open:
                continue
            if code:
                open_codes.add(_norm(code))
            if label:
                open_codes.add(_norm(label))
        if open_codes:
            out[col] = open_codes
    return out


def _metry_columns_from_config(metryczka_config: Any = None) -> List[str]:
    open_map = _metry_open_option_codes_by_column(metryczka_config)
    cols: List[str] = []
    for q in metryczka_questions(metryczka_config):
        if not isinstance(q, dict):
            continue
        col = str(q.get("db_column") or q.get("id") or "").strip().upper()
        if not col.startswith("M_"):
            continue
        if col not in cols:
            cols.append(col)
        if col in open_map or col in {"M_ZAWOD", "M_PARTIA"}:
            other_col = f"{col}_OTHER"
            if other_col not in cols:
                cols.append(other_col)

    # Fallback bezpieczeństwa dla pól custom (gdyby nie były obecne w pytaniach).
    for col in metryczka_custom_columns(metryczka_config):
        txt = str(col or "").strip().upper()
        if not txt.startswith("M_"):
            continue
        if txt not in cols:
            cols.append(txt)
        if txt in open_map or txt in {"M_ZAWOD", "M_PARTIA"}:
            other_col = f"{txt}_OTHER"
            if other_col not in cols:
                cols.append(other_col)
    return cols


def response_columns(metryczka_config: Any = None) -> List[str]:
    metry_cols = _metry_columns_from_config(metryczka_config)
    if not metry_cols:
        metry_cols = ["M_PLEC", "M_WIEK", "M_WYKSZT", "M_ZAWOD", "M_ZAWOD_OTHER", "M_MATERIAL"]
    cols: List[str] = ["respondent_id", *metry_cols]
    tail_cols: List[str] = [c for c in CANONICAL_COLUMNS if c not in cols]
    cols.extend(tail_cols)
    return cols


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
      study_status TEXT NOT NULL DEFAULT 'active',
      status_changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      started_at TIMESTAMPTZ NULL,
      survey_display_mode TEXT NOT NULL DEFAULT 'matrix',
      survey_show_progress BOOLEAN NOT NULL DEFAULT TRUE,
      survey_allow_back BOOLEAN NOT NULL DEFAULT TRUE,
      survey_randomize_questions BOOLEAN NOT NULL DEFAULT FALSE,
      survey_fast_click_check_enabled BOOLEAN NOT NULL DEFAULT FALSE,
      survey_auto_start_enabled BOOLEAN NOT NULL DEFAULT FALSE,
      survey_auto_start_at TIMESTAMPTZ NULL,
      survey_auto_start_applied_at TIMESTAMPTZ NULL,
      survey_auto_end_enabled BOOLEAN NOT NULL DEFAULT FALSE,
      survey_auto_end_at TIMESTAMPTZ NULL,
      survey_auto_end_applied_at TIMESTAMPTZ NULL,
      survey_notify_on_response BOOLEAN NOT NULL DEFAULT FALSE,
      survey_notify_email TEXT NULL,
      survey_notify_last_count INTEGER NOT NULL DEFAULT 0,
      survey_notify_last_sent_at TIMESTAMPTZ NULL,
      metryczka_config JSONB NULL,
      metryczka_config_version INTEGER NOT NULL DEFAULT 1,
      matching_segments_penalty_strength TEXT NOT NULL DEFAULT 'standard',
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      deleted_at TIMESTAMPTZ NULL
    );

    ALTER TABLE public.jst_studies
      ADD COLUMN IF NOT EXISTS poststrat_targets JSONB NULL;
    ALTER TABLE public.jst_studies
      ADD COLUMN IF NOT EXISTS population_15_plus INTEGER NULL;
    ALTER TABLE public.jst_studies
      ADD COLUMN IF NOT EXISTS study_status TEXT NOT NULL DEFAULT 'active';
    ALTER TABLE public.jst_studies
      ADD COLUMN IF NOT EXISTS status_changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
    ALTER TABLE public.jst_studies
      ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ NULL;
    ALTER TABLE public.jst_studies
      ADD COLUMN IF NOT EXISTS survey_display_mode TEXT NOT NULL DEFAULT 'matrix';
    ALTER TABLE public.jst_studies
      ADD COLUMN IF NOT EXISTS survey_show_progress BOOLEAN NOT NULL DEFAULT TRUE;
    ALTER TABLE public.jst_studies
      ADD COLUMN IF NOT EXISTS survey_allow_back BOOLEAN NOT NULL DEFAULT TRUE;
    ALTER TABLE public.jst_studies
      ADD COLUMN IF NOT EXISTS survey_randomize_questions BOOLEAN NOT NULL DEFAULT FALSE;
    ALTER TABLE public.jst_studies
      ADD COLUMN IF NOT EXISTS survey_fast_click_check_enabled BOOLEAN NOT NULL DEFAULT FALSE;
    ALTER TABLE public.jst_studies
      ADD COLUMN IF NOT EXISTS survey_auto_start_enabled BOOLEAN NOT NULL DEFAULT FALSE;
    ALTER TABLE public.jst_studies
      ADD COLUMN IF NOT EXISTS survey_auto_start_at TIMESTAMPTZ NULL;
    ALTER TABLE public.jst_studies
      ADD COLUMN IF NOT EXISTS survey_auto_start_applied_at TIMESTAMPTZ NULL;
    ALTER TABLE public.jst_studies
      ADD COLUMN IF NOT EXISTS survey_auto_end_enabled BOOLEAN NOT NULL DEFAULT FALSE;
    ALTER TABLE public.jst_studies
      ADD COLUMN IF NOT EXISTS survey_auto_end_at TIMESTAMPTZ NULL;
    ALTER TABLE public.jst_studies
      ADD COLUMN IF NOT EXISTS survey_auto_end_applied_at TIMESTAMPTZ NULL;
    ALTER TABLE public.jst_studies
      ADD COLUMN IF NOT EXISTS survey_notify_on_response BOOLEAN NOT NULL DEFAULT FALSE;
    ALTER TABLE public.jst_studies
      ADD COLUMN IF NOT EXISTS survey_notify_email TEXT NULL;
    ALTER TABLE public.jst_studies
      ADD COLUMN IF NOT EXISTS survey_notify_last_count INTEGER NOT NULL DEFAULT 0;
    ALTER TABLE public.jst_studies
      ADD COLUMN IF NOT EXISTS survey_notify_last_sent_at TIMESTAMPTZ NULL;
    ALTER TABLE public.jst_studies
      ADD COLUMN IF NOT EXISTS metryczka_config JSONB NULL;
    ALTER TABLE public.jst_studies
      ADD COLUMN IF NOT EXISTS metryczka_config_version INTEGER NOT NULL DEFAULT 1;
    ALTER TABLE public.jst_studies
      ADD COLUMN IF NOT EXISTS matching_segments_penalty_strength TEXT NOT NULL DEFAULT 'standard';
    DO $jst_status_chk$
    BEGIN
      IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'jst_studies_status_chk'
      ) THEN
        ALTER TABLE public.jst_studies
          ADD CONSTRAINT jst_studies_status_chk
          CHECK (study_status IN ('active','suspended','closed','deleted'));
      END IF;
    END;
    $jst_status_chk$;

    DO $jst_survey_mode_chk$
    BEGIN
      IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'jst_studies_survey_mode_chk'
      ) THEN
        ALTER TABLE public.jst_studies
          ADD CONSTRAINT jst_studies_survey_mode_chk
          CHECK (survey_display_mode IN ('matrix','single'));
      END IF;
    END;
    $jst_survey_mode_chk$;

    DO $jst_segments_penalty_chk$
    BEGIN
      IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'jst_studies_segments_penalty_chk'
      ) THEN
        ALTER TABLE public.jst_studies
          ADD CONSTRAINT jst_studies_segments_penalty_chk
          CHECK (matching_segments_penalty_strength IN ('łagodna','standard','ostra'));
      END IF;
    END;
    $jst_segments_penalty_chk$;

    UPDATE public.jst_studies
    SET study_status = CASE
      WHEN COALESCE(is_active, true) = false OR deleted_at IS NOT NULL THEN 'deleted'
      ELSE 'active'
    END
    WHERE COALESCE(study_status, '') = '';

    UPDATE public.jst_studies
    SET started_at = COALESCE(started_at, created_at, NOW())
    WHERE started_at IS NULL;

    UPDATE public.jst_studies
    SET matching_segments_penalty_strength = 'standard'
    WHERE COALESCE(matching_segments_penalty_strength, '') = '';

    DO $studies_status$
    BEGIN
      IF EXISTS (
        SELECT 1
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name = 'studies'
      ) THEN
        ALTER TABLE public.studies
          ADD COLUMN IF NOT EXISTS study_status TEXT NOT NULL DEFAULT 'active';
        ALTER TABLE public.studies
          ADD COLUMN IF NOT EXISTS status_changed_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
        ALTER TABLE public.studies
          ADD COLUMN IF NOT EXISTS started_at TIMESTAMPTZ NULL;
        ALTER TABLE public.studies
          ADD COLUMN IF NOT EXISTS survey_display_mode TEXT NOT NULL DEFAULT 'matrix';
        ALTER TABLE public.studies
          ADD COLUMN IF NOT EXISTS survey_show_progress BOOLEAN NOT NULL DEFAULT TRUE;
        ALTER TABLE public.studies
          ADD COLUMN IF NOT EXISTS survey_allow_back BOOLEAN NOT NULL DEFAULT TRUE;
        ALTER TABLE public.studies
          ADD COLUMN IF NOT EXISTS survey_randomize_questions BOOLEAN NOT NULL DEFAULT FALSE;
        ALTER TABLE public.studies
          ADD COLUMN IF NOT EXISTS survey_fast_click_check_enabled BOOLEAN NOT NULL DEFAULT FALSE;
        ALTER TABLE public.studies
          ADD COLUMN IF NOT EXISTS survey_auto_start_enabled BOOLEAN NOT NULL DEFAULT FALSE;
        ALTER TABLE public.studies
          ADD COLUMN IF NOT EXISTS survey_auto_start_at TIMESTAMPTZ NULL;
        ALTER TABLE public.studies
          ADD COLUMN IF NOT EXISTS survey_auto_start_applied_at TIMESTAMPTZ NULL;
        ALTER TABLE public.studies
          ADD COLUMN IF NOT EXISTS survey_auto_end_enabled BOOLEAN NOT NULL DEFAULT FALSE;
        ALTER TABLE public.studies
          ADD COLUMN IF NOT EXISTS survey_auto_end_at TIMESTAMPTZ NULL;
        ALTER TABLE public.studies
          ADD COLUMN IF NOT EXISTS survey_auto_end_applied_at TIMESTAMPTZ NULL;
        ALTER TABLE public.studies
          ADD COLUMN IF NOT EXISTS survey_notify_on_response BOOLEAN NOT NULL DEFAULT FALSE;
        ALTER TABLE public.studies
          ADD COLUMN IF NOT EXISTS survey_notify_email TEXT NULL;
        ALTER TABLE public.studies
          ADD COLUMN IF NOT EXISTS survey_notify_last_count INTEGER NOT NULL DEFAULT 0;
        ALTER TABLE public.studies
          ADD COLUMN IF NOT EXISTS survey_notify_last_sent_at TIMESTAMPTZ NULL;
        ALTER TABLE public.studies
          ADD COLUMN IF NOT EXISTS metryczka_config JSONB NULL;
        ALTER TABLE public.studies
          ADD COLUMN IF NOT EXISTS metryczka_config_version INTEGER NOT NULL DEFAULT 1;

        IF NOT EXISTS (
          SELECT 1
          FROM pg_constraint
          WHERE conname = 'studies_status_chk'
        ) THEN
          ALTER TABLE public.studies
            ADD CONSTRAINT studies_status_chk
            CHECK (study_status IN ('active','suspended','closed','deleted'));
        END IF;

        IF NOT EXISTS (
          SELECT 1
          FROM pg_constraint
          WHERE conname = 'studies_survey_mode_chk'
        ) THEN
          ALTER TABLE public.studies
            ADD CONSTRAINT studies_survey_mode_chk
            CHECK (survey_display_mode IN ('matrix','single'));
        END IF;

        UPDATE public.studies
        SET study_status = CASE
          WHEN COALESCE(is_active, true) = false OR deleted_at IS NOT NULL THEN 'deleted'
          ELSE 'active'
        END
        WHERE COALESCE(study_status, '') = '';

        UPDATE public.studies
        SET started_at = COALESCE(started_at, created_at, NOW())
        WHERE started_at IS NULL;
      END IF;
    END;
    $studies_status$;

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

    CREATE TABLE IF NOT EXISTS public.metryczka_question_templates (
      id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
      kind TEXT NOT NULL DEFAULT 'both',
      name TEXT NOT NULL,
      question JSONB NOT NULL DEFAULT '{}'::jsonb,
      is_active BOOLEAN NOT NULL DEFAULT TRUE,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
      CONSTRAINT metry_q_tpl_kind_chk CHECK (kind IN ('jst','personal','both')),
      CONSTRAINT uq_metry_q_tpl_kind_name UNIQUE (kind, name)
    );

    ALTER TABLE public.metryczka_question_templates
      ADD COLUMN IF NOT EXISTS kind TEXT NOT NULL DEFAULT 'both';
    ALTER TABLE public.metryczka_question_templates
      ADD COLUMN IF NOT EXISTS name TEXT NOT NULL DEFAULT '';
    ALTER TABLE public.metryczka_question_templates
      ADD COLUMN IF NOT EXISTS question JSONB NOT NULL DEFAULT '{}'::jsonb;
    ALTER TABLE public.metryczka_question_templates
      ADD COLUMN IF NOT EXISTS is_active BOOLEAN NOT NULL DEFAULT TRUE;
    ALTER TABLE public.metryczka_question_templates
      ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();
    ALTER TABLE public.metryczka_question_templates
      ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

    CREATE INDEX IF NOT EXISTS idx_metry_q_tpl_kind_active
      ON public.metryczka_question_templates(kind, is_active);

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
          is_active,
          study_status,
          status_changed_at,
          started_at,
          survey_display_mode,
          survey_show_progress,
          survey_allow_back,
          survey_randomize_questions,
          survey_fast_click_check_enabled,
          survey_auto_start_enabled,
          survey_auto_start_at,
          survey_auto_start_applied_at,
          survey_auto_end_enabled,
          survey_auto_end_at,
          survey_auto_end_applied_at,
          survey_notify_on_response,
          survey_notify_email,
          metryczka_config,
          metryczka_config_version
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
      v_study_status text;
      v_auto_start_enabled boolean;
      v_auto_start_at timestamptz;
      v_auto_start_applied_at timestamptz;
      v_auto_end_enabled boolean;
      v_auto_end_at timestamptz;
      v_auto_end_applied_at timestamptz;
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

      SELECT
        id,
        COALESCE(NULLIF(trim(study_status), ''), 'active'),
        COALESCE(survey_auto_start_enabled, false),
        survey_auto_start_at,
        survey_auto_start_applied_at,
        COALESCE(survey_auto_end_enabled, false),
        survey_auto_end_at,
        survey_auto_end_applied_at
      INTO
        v_study_id,
        v_study_status,
        v_auto_start_enabled,
        v_auto_start_at,
        v_auto_start_applied_at,
        v_auto_end_enabled,
        v_auto_end_at,
        v_auto_end_applied_at
      FROM public.jst_studies
      WHERE slug = v_slug
        AND COALESCE(is_active, true)
      LIMIT 1;

      IF v_study_id IS NULL THEN
        RETURN jsonb_build_object('ok', false, 'error', 'study_not_found');
      END IF;

      IF v_auto_start_enabled AND v_auto_start_at IS NOT NULL AND v_auto_start_applied_at IS NULL THEN
        IF NOW() >= v_auto_start_at THEN
          UPDATE public.jst_studies
          SET
            survey_auto_start_applied_at = NOW(),
            study_status = CASE
              WHEN COALESCE(NULLIF(trim(study_status), ''), 'active') = 'suspended' THEN 'active'
              ELSE COALESCE(NULLIF(trim(study_status), ''), 'active')
            END,
            status_changed_at = CASE
              WHEN COALESCE(NULLIF(trim(study_status), ''), 'active') = 'suspended' THEN NOW()
              ELSE status_changed_at
            END
          WHERE id = v_study_id;
          SELECT COALESCE(NULLIF(trim(study_status), ''), 'active'), survey_auto_start_applied_at
          INTO v_study_status, v_auto_start_applied_at
          FROM public.jst_studies
          WHERE id = v_study_id
          LIMIT 1;
        ELSIF v_study_status = 'active' THEN
          UPDATE public.jst_studies
          SET study_status = 'suspended', status_changed_at = NOW()
          WHERE id = v_study_id;
          v_study_status := 'suspended';
        END IF;
      END IF;

      IF v_auto_end_enabled AND v_auto_end_at IS NOT NULL AND v_auto_end_applied_at IS NULL AND NOW() >= v_auto_end_at THEN
        UPDATE public.jst_studies
        SET
          survey_auto_end_applied_at = NOW(),
          study_status = CASE
            WHEN COALESCE(NULLIF(trim(study_status), ''), 'active') = 'active' THEN 'suspended'
            ELSE COALESCE(NULLIF(trim(study_status), ''), 'active')
          END,
          status_changed_at = CASE
            WHEN COALESCE(NULLIF(trim(study_status), ''), 'active') = 'active' THEN NOW()
            ELSE status_changed_at
          END
        WHERE id = v_study_id;
        SELECT COALESCE(NULLIF(trim(study_status), ''), 'active'), survey_auto_end_applied_at
        INTO v_study_status, v_auto_end_applied_at
        FROM public.jst_studies
        WHERE id = v_study_id
        LIMIT 1;
      END IF;

      IF v_study_status <> 'active' THEN
        RETURN jsonb_build_object(
          'ok', false,
          'error', 'study_inactive',
          'study_status', v_study_status
        );
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
              deleted_at = COALESCE(deleted_at, NOW()),
              study_status = 'deleted',
              status_changed_at = NOW()
          WHERE id = r.id;
        EXCEPTION WHEN unique_violation THEN
          UPDATE public.jst_studies
          SET slug = '__deleted__' || left(r.id::text, 8) || '__' || to_char(clock_timestamp(), 'YYYYMMDDHH24MISSMS'),
              updated_at = NOW(),
              deleted_at = COALESCE(deleted_at, NOW()),
              study_status = 'deleted',
              status_changed_at = NOW()
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


_ALLOWED_STUDY_STATUSES = {"active", "suspended", "closed", "deleted"}
_TEMPLATE_KINDS = {"jst", "personal", "both"}
_ALLOWED_SEGMENT_PENALTY_STRENGTHS = {"łagodna", "standard", "ostra"}


def normalize_study_status(raw: Optional[str], *, is_active: Optional[bool] = None, deleted_at: Optional[str] = None) -> str:
    status = str(raw or "").strip().lower()
    if status in _ALLOWED_STUDY_STATUSES:
        return status
    if deleted_at:
        return "deleted"
    if is_active is False:
        return "deleted"
    return "active"


def normalize_matching_segments_penalty_strength(raw: Any) -> str:
    txt = str(raw or "").strip().lower()
    if txt in _ALLOWED_SEGMENT_PENALTY_STRENGTHS:
        return txt
    return "standard"


def _bool_from_any(value: Any, fallback: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    txt = str(value or "").strip().lower()
    if txt in {"1", "true", "t", "yes", "y", "on", "tak", "x"}:
        return True
    if txt in {"0", "false", "f", "no", "n", "off", "nie"}:
        return False
    return bool(fallback)


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


def _is_postgrest_missing_any_column_error(err: Exception, table_name: str) -> bool:
    msg = (getattr(err, "message", "") or str(err) or "").lower()
    return "pgrst204" in msg and str(table_name or "").lower() in msg


def fetch_jst_studies(sb: Client, include_inactive: bool = False) -> List[Dict[str, Any]]:
    q = sb.table("jst_studies").select("*").order("created_at", desc=True)
    if not include_inactive:
        q = q.or_("is_active.is.true,is_active.is.null").is_("deleted_at", "null")
    res = q.execute()
    out: List[Dict[str, Any]] = []
    for row in (res.data or []):
        rec = dict(row)
        cfg = normalize_jst_metryczka_config(rec.get("metryczka_config"))
        rec["metryczka_config"] = cfg
        rec["metryczka_config_version"] = int(cfg.get("version") or 1)
        rec["matching_segments_penalty_strength"] = normalize_matching_segments_penalty_strength(
            rec.get("matching_segments_penalty_strength")
        )
        out.append(rec)
    return out


def fetch_jst_study_by_id(sb: Client, study_id: str) -> Optional[Dict[str, Any]]:
    res = sb.table("jst_studies").select("*").eq("id", str(study_id)).limit(1).execute()
    data = res.data or []
    if not data:
        return None
    rec = dict(data[0])
    cfg = normalize_jst_metryczka_config(rec.get("metryczka_config"))
    rec["metryczka_config"] = cfg
    rec["metryczka_config_version"] = int(cfg.get("version") or 1)
    rec["matching_segments_penalty_strength"] = normalize_matching_segments_penalty_strength(
        rec.get("matching_segments_penalty_strength")
    )
    return rec


def _normalize_template_kind(raw: Any) -> str:
    txt = str(raw or "").strip().lower()
    return txt if txt in _TEMPLATE_KINDS else "both"


def _normalize_template_question_payload(raw: Any) -> Dict[str, Any]:
    src = dict(raw or {}) if isinstance(raw, dict) else {}
    prompt = str(src.get("prompt") or "").strip()
    table_label = str(src.get("table_label") or prompt).strip()
    db_column = str(src.get("db_column") or src.get("id") or "").strip().upper()
    scope = str(src.get("scope") or "custom").strip().lower() or "custom"
    qid = str(src.get("id") or db_column).strip().upper()
    variable_emoji = str(
        src.get("variable_emoji") or guess_metry_variable_emoji(db_column, table_label, prompt)
    ).strip()
    randomize_options = _bool_from_any(src.get("randomize_options"), False)
    legacy_exclude_last = _bool_from_any(src.get("randomize_exclude_last"), False)
    options_out: List[Dict[str, Any]] = []
    seen_codes: set[str] = set()
    has_locked = False
    for opt in list(src.get("options") or []):
        if not isinstance(opt, dict):
            continue
        label = str(opt.get("label") or "").strip()
        code = str(opt.get("code") or label).strip()
        if not label or not code:
            continue
        code_u = code.upper()
        if code_u in seen_codes:
            continue
        seen_codes.add(code_u)
        is_open = _bool_from_any(opt.get("is_open"), False) or ("inna (jaka?)" in label.lower())
        lock_randomization = _bool_from_any(opt.get("lock_randomization"), False)
        if lock_randomization:
            has_locked = True
        options_out.append(
            {
                "label": label,
                "code": code,
                "is_open": bool(is_open),
                "lock_randomization": bool(lock_randomization),
                "value_emoji": (
                    str(opt.get("value_emoji") or "").strip()
                    if "value_emoji" in opt
                    else str(guess_metry_value_emoji(table_label, code, db_column) or "").strip()
                ),
            }
        )
    if randomize_options and legacy_exclude_last and options_out and not has_locked:
        options_out[-1]["lock_randomization"] = True
    return {
        "id": qid or db_column,
        "scope": scope,
        "db_column": db_column,
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


def list_metryczka_question_templates(
    sb: Client,
    *,
    kind: str = "both",
    include_inactive: bool = False,
) -> List[Dict[str, Any]]:
    kind_norm = _normalize_template_kind(kind)
    query = (
        sb.table("metryczka_question_templates")
        .select("*")
        .order("updated_at", desc=True)
        .order("name", desc=False)
    )
    if not include_inactive:
        query = query.eq("is_active", True)
    if kind_norm in {"jst", "personal"}:
        query = query.in_("kind", [kind_norm, "both"])
    try:
        res = query.execute()
    except Exception as e:
        if _is_postgrest_missing_any_column_error(e, "metryczka_question_templates"):
            _notify_postgrest_schema_reload()
            res = query.execute()
        else:
            raise
    out: List[Dict[str, Any]] = []
    for row in (res.data or []):
        rec = dict(row)
        q = _normalize_template_question_payload(rec.get("question"))
        if (
            not str(q.get("prompt") or "").strip()
            or not str(q.get("db_column") or "").strip()
            or len(list(q.get("options") or [])) < 2
        ):
            continue
        rec["kind"] = _normalize_template_kind(rec.get("kind"))
        rec["question"] = q
        out.append(rec)
    return out


def save_metryczka_question_template(
    sb: Client,
    *,
    name: str,
    question: Dict[str, Any],
    kind: str = "both",
) -> Dict[str, Any]:
    name_txt = str(name or "").strip()
    if not name_txt:
        raise ValueError("Podaj nazwę zapisanego pytania.")
    q = _normalize_template_question_payload(question)
    if not str(q.get("prompt") or "").strip():
        raise ValueError("Nie można zapisać pustej treści pytania.")
    if not str(q.get("db_column") or "").strip():
        raise ValueError("Nie można zapisać pytania bez kodowania kolumny.")
    if len(list(q.get("options") or [])) < 2:
        raise ValueError("Pytanie musi zawierać co najmniej 2 odpowiedzi.")

    kind_norm = _normalize_template_kind(kind)
    now_iso = _utc_now_iso()
    payload = {
        "kind": kind_norm,
        "name": name_txt,
        "question": q,
        "is_active": True,
        "updated_at": now_iso,
    }
    try:
        existing = (
            sb.table("metryczka_question_templates")
            .select("id")
            .eq("kind", kind_norm)
            .eq("name", name_txt)
            .limit(1)
            .execute()
            .data
            or []
        )
    except Exception as e:
        if _is_postgrest_missing_any_column_error(e, "metryczka_question_templates"):
            _notify_postgrest_schema_reload()
            existing = (
                sb.table("metryczka_question_templates")
                .select("id")
                .eq("kind", kind_norm)
                .eq("name", name_txt)
                .limit(1)
                .execute()
                .data
                or []
            )
        else:
            raise

    if existing:
        rec_id = str(existing[0].get("id") or "").strip()
        if not rec_id:
            raise RuntimeError("Nie udało się ustalić ID zapisanego pytania.")
        sb.table("metryczka_question_templates").update(payload).eq("id", rec_id).execute()
        refreshed = (
            sb.table("metryczka_question_templates")
            .select("*")
            .eq("id", rec_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        return dict(refreshed[0]) if refreshed else {"id": rec_id, **payload}

    payload["created_at"] = now_iso
    ins = sb.table("metryczka_question_templates").insert(payload).execute()
    if ins.data:
        return dict(ins.data[0])
    raise RuntimeError("Nie udało się zapisać pytania metryczkowego.")


def insert_jst_study(sb: Client, payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload)
    raw_metryczka = data.get("metryczka_config")
    cfg_metryczka = normalize_jst_metryczka_config(raw_metryczka)
    now_iso = _utc_now_iso()
    data.setdefault("id", str(uuid.uuid4()))
    data.setdefault("is_active", True)
    data.setdefault("study_status", "active")
    data.setdefault("status_changed_at", now_iso)
    data.setdefault("started_at", now_iso)
    data.setdefault("survey_display_mode", "matrix")
    data.setdefault("survey_show_progress", True)
    data.setdefault("survey_allow_back", True)
    data.setdefault("survey_randomize_questions", False)
    data.setdefault("survey_fast_click_check_enabled", False)
    data.setdefault("survey_auto_start_enabled", False)
    data.setdefault("survey_auto_end_enabled", False)
    data.setdefault("survey_notify_on_response", False)
    data.setdefault("survey_notify_email", None)
    data.setdefault("survey_notify_last_count", 0)
    data.setdefault("survey_notify_last_sent_at", None)
    data.setdefault("matching_segments_penalty_strength", "standard")
    data["metryczka_config"] = cfg_metryczka if raw_metryczka is not None else default_jst_metryczka_config()
    data.setdefault("metryczka_config_version", int(cfg_metryczka.get("version") or 1))
    data["matching_segments_penalty_strength"] = normalize_matching_segments_penalty_strength(
        data.get("matching_segments_penalty_strength")
    )
    data.setdefault("created_at", now_iso)
    data.setdefault("updated_at", now_iso)
    try:
        ins = sb.table("jst_studies").insert(data).execute()
    except Exception as e:
        if _is_postgrest_missing_any_column_error(e, "jst_studies"):
            _notify_postgrest_schema_reload()
            ins = sb.table("jst_studies").insert(data).execute()
        else:
            raise
    if ins.data:
        return ins.data[0]
    raise RuntimeError("Insert jst_study failed")


def update_jst_study(sb: Client, study_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    data = dict(payload)
    if "metryczka_config" in data:
        cfg = normalize_jst_metryczka_config(data.get("metryczka_config"))
        data["metryczka_config"] = cfg
        data["metryczka_config_version"] = int(cfg.get("version") or 1)
    if "matching_segments_penalty_strength" in data:
        data["matching_segments_penalty_strength"] = normalize_matching_segments_penalty_strength(
            data.get("matching_segments_penalty_strength")
        )
    data["updated_at"] = _utc_now_iso()
    try:
        sb.table("jst_studies").update(data).eq("id", str(study_id)).execute()
    except Exception as e:
        if _is_postgrest_missing_any_column_error(e, "jst_studies"):
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
            "study_status": "deleted",
            "status_changed_at": _utc_now_iso(),
            "slug": archived_slug,
        }
    ).eq("id", sid).execute()


def set_jst_study_status(sb: Client, study_id: str, status: str) -> Dict[str, Any]:
    sid = str(study_id or "").strip()
    target = str(status or "").strip().lower()
    if target not in {"active", "suspended", "closed"}:
        raise ValueError("Nieprawidłowy status badania.")
    row = fetch_jst_study_by_id(sb, sid) or {}
    if not row:
        raise ValueError("Nie znaleziono badania JST.")
    current = normalize_study_status(
        row.get("study_status"),
        is_active=row.get("is_active"),
        deleted_at=row.get("deleted_at"),
    )
    if current == "deleted":
        raise ValueError("Usuniętego badania JST nie można zmienić.")
    if current == "closed" and target != "closed":
        raise ValueError("Badanie zamknięte jest trwałe i nie może zostać ponownie uruchomione.")
    now_iso = _utc_now_iso()
    updates = {
        "study_status": target,
        "status_changed_at": now_iso,
        "updated_at": now_iso,
    }
    sb.table("jst_studies").update(updates).eq("id", sid).execute()
    refreshed = fetch_jst_study_by_id(sb, sid)
    if not refreshed:
        raise RuntimeError("Nie udało się odświeżyć statusu badania JST.")
    return refreshed


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
                    "study_status": "deleted",
                    "status_changed_at": _utc_now_iso(),
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
                        "study_status": "deleted",
                        "status_changed_at": _utc_now_iso(),
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


def delete_jst_responses_by_respondent_ids(
    sb: Client,
    study_id: str,
    respondent_ids: Iterable[str],
) -> int:
    sid = str(study_id or "").strip()
    if not sid:
        return 0

    unique_ids: List[str] = []
    seen: set[str] = set()
    for raw in respondent_ids:
        rid = str(raw or "").strip()
        if not rid or rid in seen:
            continue
        seen.add(rid)
        unique_ids.append(rid)

    if not unique_ids:
        return 0

    chunk_size = 200
    existing_ids: set[str] = set()

    for idx in range(0, len(unique_ids), chunk_size):
        chunk = unique_ids[idx : idx + chunk_size]
        try:
            res = (
                sb.table("jst_responses")
                .select("respondent_id")
                .eq("study_id", sid)
                .in_("respondent_id", chunk)
                .execute()
            )
            for row in (res.data or []):
                rid = str(row.get("respondent_id") or "").strip()
                if rid:
                    existing_ids.add(rid)
        except Exception:
            continue

    if not existing_ids:
        return 0

    ids_to_delete = sorted(existing_ids)
    for idx in range(0, len(ids_to_delete), chunk_size):
        chunk = ids_to_delete[idx : idx + chunk_size]
        (
            sb.table("jst_responses")
            .delete()
            .eq("study_id", sid)
            .in_("respondent_id", chunk)
            .execute()
        )

    return len(ids_to_delete)


def _is_duplicate_conflict_error(exc: Exception) -> bool:
    msg = str(exc or "").lower()
    return bool(
        "duplicate" in msg
        or "unique" in msg
        or "23505" in msg
        or "conflict" in msg
    )


def _build_jst_response_record(
    *,
    study_id: str,
    respondent_id: str,
    payload: Dict[str, Any],
    source: str,
) -> Dict[str, Any]:
    now_iso = _utc_now_iso()
    return {
        "id": str(uuid.uuid4()),
        "study_id": str(study_id),
        "respondent_id": str(respondent_id),
        "payload": dict(payload),
        "source": str(source or "web"),
        "created_at": now_iso,
        "updated_at": now_iso,
    }


def insert_jst_response(
    sb: Client,
    study_id: str,
    respondent_id: str,
    payload: Dict[str, Any],
    source: str = "web",
    skip_if_exists: bool = True,
) -> bool:
    rec = _build_jst_response_record(
        study_id=str(study_id),
        respondent_id=str(respondent_id),
        payload=payload,
        source=source,
    )
    try:
        ins = sb.table("jst_responses").insert(rec).execute()
        return bool(ins.data)
    except Exception as exc:
        if skip_if_exists and _is_duplicate_conflict_error(exc):
            return False
        raise


def insert_jst_response_batch(
    sb: Client,
    *,
    study_id: str,
    rows: Iterable[Dict[str, Any]],
    source: str = "web",
    skip_if_exists: bool = True,
) -> Dict[str, int]:
    sid = str(study_id or "").strip()
    prepared: List[Dict[str, Any]] = []
    skipped = 0
    seen_rids: set[str] = set()

    for raw in rows or []:
        row = dict(raw or {})
        rid = str(row.get("respondent_id") or "").strip()
        payload = row.get("payload")
        if not rid:
            skipped += 1
            continue
        if not isinstance(payload, dict):
            skipped += 1
            continue
        if skip_if_exists and rid in seen_rids:
            skipped += 1
            continue
        seen_rids.add(rid)
        prepared.append(
            _build_jst_response_record(
                study_id=sid,
                respondent_id=rid,
                payload=payload,
                source=source,
            )
        )

    if not prepared:
        return {"inserted": 0, "skipped": skipped, "errors": 0}

    try:
        ins = sb.table("jst_responses").insert(prepared).execute()
        inserted = len(prepared)
        ins_data = getattr(ins, "data", None)
        if isinstance(ins_data, list) and ins_data:
            inserted = min(len(prepared), len(ins_data))
        skipped += max(0, len(prepared) - inserted)
        return {"inserted": inserted, "skipped": skipped, "errors": 0}
    except Exception as exc:
        if not (skip_if_exists and _is_duplicate_conflict_error(exc)):
            raise
        inserted = 0
        errors = 0
        for rec in prepared:
            try:
                ok = insert_jst_response(
                    sb,
                    study_id=sid,
                    respondent_id=str(rec.get("respondent_id") or ""),
                    payload=dict(rec.get("payload") or {}),
                    source=source,
                    skip_if_exists=skip_if_exists,
                )
                if ok:
                    inserted += 1
                else:
                    skipped += 1
            except Exception:
                errors += 1
        return {"inserted": inserted, "skipped": skipped, "errors": errors}


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


def _paired_c_or_d_column(col: Any) -> str:
    txt = str(col or "").strip().upper()
    if not txt:
        return ""
    m = re.fullmatch(r"([CD])([1-9]|1[0-3])", txt)
    if not m:
        return ""
    pref = str(m.group(1))
    num = str(m.group(2))
    return f"{'D' if pref == 'C' else 'C'}{num}"


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


def _choice_to_code(value: Any, options: List[Dict[str, Any]]) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    n = _norm(raw)
    for opt in options:
        if not isinstance(opt, dict):
            continue
        label = str(opt.get("label") or "").strip()
        code = str(opt.get("code") or "").strip()
        if not label and not code:
            continue
        ln = _norm(label)
        cn = _norm(code)
        if n == ln or n == cn:
            return code or label
        if ln and (n in ln or ln in n):
            return code or label
        if cn and (n in cn or cn in n):
            return code or label
    return raw


def _metryczka_questions_by_column(metryczka_config: Any = None) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    for q in metryczka_questions(metryczka_config):
        if not isinstance(q, dict):
            continue
        col = str(q.get("db_column") or "").strip().upper()
        if not col:
            continue
        out[col] = q
    return out


def _validate_open_other_fields(row: Dict[str, Any], metryczka_config: Any = None) -> None:
    open_map = _metry_open_option_codes_by_column(metryczka_config)
    if not open_map:
        return
    labels: Dict[str, str] = {}
    for q in metryczka_questions(metryczka_config):
        if not isinstance(q, dict):
            continue
        col = str(q.get("db_column") or q.get("id") or "").strip().upper()
        if not col.startswith("M_"):
            continue
        label = str(q.get("table_label") or q.get("prompt") or col).strip()
        labels[col] = label or col
    for col, open_codes in open_map.items():
        selected = _norm(str(row.get(col) or "").strip())
        if not selected or selected not in open_codes:
            continue
        other_col = f"{col}_OTHER"
        other_val = str(row.get(other_col) or "").strip()
        if not other_val:
            raise ValueError(
                f"Dla pola '{labels.get(col, col)}' wybrano odpowiedź otwartą; uzupełnij '{other_col}'."
            )


def normalize_response_row(raw: Dict[str, Any], respondent_id_fallback: str = "", metryczka_config: Any = None) -> Dict[str, Any]:
    cols = response_columns(metryczka_config)
    row: Dict[str, Any] = {c: "" for c in cols}
    raw = dict(raw or {})
    q_by_col = _metryczka_questions_by_column(metryczka_config)
    norm_key_map: Dict[str, Any] = {}
    for k, v in raw.items():
        nk = _norm(k)
        if nk and nk not in norm_key_map:
            norm_key_map[nk] = v

    def pick(*keys: Any) -> Any:
        for key in keys:
            txt = str(key or "").strip()
            if not txt:
                continue
            if txt in raw:
                return raw.get(txt)
            nk = _norm(txt)
            if nk and nk in norm_key_map:
                return norm_key_map[nk]
            paired = _paired_c_or_d_column(txt)
            if paired:
                if paired in raw:
                    return raw.get(paired)
                paired_nk = _norm(paired)
                if paired_nk and paired_nk in norm_key_map:
                    return norm_key_map[paired_nk]
        return None

    def q_options(col: str, fallback_values: List[str]) -> List[Dict[str, str]]:
        q = q_by_col.get(col) or {}
        options = q.get("options")
        out: List[Dict[str, str]] = []
        if isinstance(options, list):
            for item in options:
                if not isinstance(item, dict):
                    continue
                label = str(item.get("label") or "").strip()
                code = str(item.get("code") or "").strip()
                if not label or not code:
                    continue
                out.append({"label": label, "code": code})
        if out:
            return out
        return [{"label": v, "code": v} for v in fallback_values]

    rid = str(pick("respondent_id", "Respondent_ID") or "").strip()
    row["respondent_id"] = rid or str(respondent_id_fallback or "")

    row["M_PLEC"] = _choice_to_code(pick("M_PLEC"), q_options("M_PLEC", M_PLEC_VALUES))
    row["M_WIEK"] = _choice_to_code(pick("M_WIEK"), q_options("M_WIEK", M_WIEK_VALUES))
    row["M_WYKSZT"] = _choice_to_code(pick("M_WYKSZT"), q_options("M_WYKSZT", M_WYKSZT_VALUES))
    row["M_ZAWOD"] = _choice_to_code(pick("M_ZAWOD"), q_options("M_ZAWOD", M_ZAWOD_VALUES))
    row["M_MATERIAL"] = _choice_to_code(pick("M_MATERIAL"), q_options("M_MATERIAL", M_MATERIAL_VALUES))

    for col in A_COLUMNS:
        v = _to_int_1_7(pick(col))
        row[col] = int(v) if v is not None else ""

    for arche in ARCHETYPES:
        k = f"B1_{arche}"
        row[k] = int(_to_flag(pick(k)))

    row["B2"] = canonical_archetype(pick("B2"))

    for col in D_COLUMNS:
        row[col] = _to_ab(pick(col, _paired_c_or_d_column(col)))

    row["D13"] = canonical_archetype(pick("D13", "C13"))

    for col in cols:
        if col in CANONICAL_COLUMNS:
            continue
        q = q_by_col.get(col) or {}
        aliases = q.get("aliases") if isinstance(q.get("aliases"), list) else []
        qid = str(q.get("id") or "").strip()
        raw_val = pick(col, qid, *aliases)
        options = q.get("options") if isinstance(q.get("options"), list) else []
        if isinstance(options, list) and options:
            row[col] = _choice_to_code(raw_val, options)
        else:
            row[col] = str(raw_val or "").strip()

    return row


def response_rows_to_dataframe(rows: Iterable[Dict[str, Any]], metryczka_config: Any = None) -> pd.DataFrame:
    cols = response_columns(metryczka_config)
    extra_cols: List[str] = []
    rows_list = list(rows or [])
    for rec in rows_list:
        payload = rec.get("payload") if isinstance(rec, dict) else {}
        if not isinstance(payload, dict):
            continue
        for key in payload.keys():
            key_up = str(key or "").strip().upper()
            if (
                key_up
                and key_up not in cols
                and _CUSTOM_METRY_COL_RE.fullmatch(key_up)
                and not _is_aux_metry_column(key_up)
            ):
                extra_cols.append(key_up)
    cols_all: List[str] = list(cols)
    for col in extra_cols:
        if col not in cols_all:
            cols_all.append(col)
    out_rows: List[Dict[str, Any]] = []
    for idx, rec in enumerate(rows_list, start=1):
        payload = rec.get("payload") or {}
        if not isinstance(payload, dict):
            payload = {}
        merged = dict(payload)
        merged.setdefault("respondent_id", rec.get("respondent_id") or "")
        norm = normalize_response_row(merged, respondent_id_fallback=f"R{idx:04d}", metryczka_config=metryczka_config)
        if not norm.get("respondent_id"):
            norm["respondent_id"] = f"R{idx:04d}"
        if extra_cols:
            norm_key_map: Dict[str, Any] = {}
            for k, v in merged.items():
                nk = _norm(k)
                if nk and nk not in norm_key_map:
                    norm_key_map[nk] = v
            for col in extra_cols:
                raw_val = merged.get(col, norm_key_map.get(_norm(col)))
                norm[col] = str(raw_val or "").strip()
        out_rows.append(norm)

    df = pd.DataFrame(out_rows)
    for c in cols_all:
        if c not in df.columns:
            df[c] = ""
    return df[cols_all].copy()


def make_payload_from_row(row: Dict[str, Any], metryczka_config: Any = None) -> Dict[str, Any]:
    _validate_open_other_fields(row, metryczka_config)
    cols = response_columns(metryczka_config)
    all_cols: List[str] = list(cols)
    for key in list((row or {}).keys()):
        key_up = str(key or "").strip().upper()
        if (
            key_up
            and key_up not in all_cols
            and key_up not in CANONICAL_COLUMNS
            and _CUSTOM_METRY_COL_RE.fullmatch(key_up)
            and not _is_aux_metry_column(key_up)
        ):
            all_cols.append(key_up)
    payload = {k: row.get(k, "") for k in all_cols if k != "respondent_id"}
    return payload


def import_template_dataframe(metryczka_config: Any = None) -> pd.DataFrame:
    return pd.DataFrame(columns=response_columns(metryczka_config))
