from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import os
import secrets
import uuid
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor
import streamlit as st


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _db_connect():
    return psycopg2.connect(
        host=st.secrets["db_host"],
        dbname=st.secrets["db_name"],
        user=st.secrets["db_user"],
        password=st.secrets["db_pass"],
        port=int(st.secrets.get("db_port", 5432)),
        sslmode="require",
    )


def ensure_schema() -> None:
    ddl = """
    CREATE TABLE IF NOT EXISTS public.report_share_links (
        id TEXT PRIMARY KEY,
        token TEXT UNIQUE NOT NULL,
        study_id TEXT NOT NULL,
        email TEXT NOT NULL,
        password_salt TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        expires_at TIMESTAMPTZ NULL,
        indefinite BOOLEAN NOT NULL DEFAULT FALSE,
        status TEXT NOT NULL DEFAULT 'active',
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        suspended_at TIMESTAMPTZ NULL,
        revoked_at TIMESTAMPTZ NULL,
        last_sent_at TIMESTAMPTZ NULL
    );
    CREATE INDEX IF NOT EXISTS idx_report_share_links_study ON public.report_share_links(study_id);
    CREATE INDEX IF NOT EXISTS idx_report_share_links_email ON public.report_share_links(email);
    """
    with _db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
        conn.commit()


def _hash_password(password: str, salt_hex: str | None = None) -> tuple[str, str]:
    if salt_hex:
        salt = bytes.fromhex(salt_hex)
    else:
        salt = os.urandom(16)
        salt_hex = salt.hex()
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 210_000).hex()
    return salt_hex, digest


def create_access(
    study_id: str,
    email: str,
    password: str,
    *,
    hours_valid: int | None,
    indefinite: bool,
    token: str | None = None,
) -> dict[str, Any]:
    ensure_schema()
    token = token or secrets.token_urlsafe(32)
    row_id = str(uuid.uuid4())
    email_norm = (email or "").strip().lower()
    salt_hex, password_hash = _hash_password(password)
    expires_at = None if indefinite else (_utc_now() + timedelta(hours=max(int(hours_valid or 1), 1)))

    sql = """
    INSERT INTO public.report_share_links (
        id, token, study_id, email, password_salt, password_hash, expires_at, indefinite, status, created_at, updated_at
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'active', NOW(), NOW())
    RETURNING *;
    """
    with _db_connect() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                sql,
                (
                    row_id,
                    token,
                    str(study_id),
                    email_norm,
                    salt_hex,
                    password_hash,
                    expires_at,
                    bool(indefinite),
                ),
            )
            rec = dict(cur.fetchone())
        conn.commit()
    return rec


def list_accesses(study_id: str) -> list[dict[str, Any]]:
    ensure_schema()
    sql = """
    SELECT id, email, status, token, expires_at, indefinite, created_at, updated_at, suspended_at, revoked_at, last_sent_at
    FROM public.report_share_links
    WHERE study_id = %s
    ORDER BY created_at DESC;
    """
    with _db_connect() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (str(study_id),))
            rows = [dict(r) for r in (cur.fetchall() or [])]
    return rows


def get_access_by_token(token: str) -> dict[str, Any] | None:
    ensure_schema()
    sql = """
    SELECT *
    FROM public.report_share_links
    WHERE token = %s
    LIMIT 1;
    """
    with _db_connect() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, ((token or "").strip(),))
            row = cur.fetchone()
    return dict(row) if row else None


@dataclass
class VerifyResult:
    ok: bool
    message: str
    row: dict[str, Any] | None = None


def verify_token_credentials(token: str, email: str, password: str) -> VerifyResult:
    row = get_access_by_token(token)
    if not row:
        return VerifyResult(False, "Link jest nieprawidłowy lub został usunięty.")

    if (row.get("email") or "").strip().lower() != (email or "").strip().lower():
        return VerifyResult(False, "Nieprawidłowy e-mail lub hasło.")

    status = str(row.get("status") or "").lower()
    if status == "suspended":
        return VerifyResult(False, "Dostęp został zawieszony.")
    if status == "revoked":
        return VerifyResult(False, "Dostęp został odwołany.")
    if status != "active":
        return VerifyResult(False, "Dostęp jest nieaktywny.")

    if not bool(row.get("indefinite")):
        expires_at = row.get("expires_at")
        if expires_at and _utc_now() > expires_at:
            return VerifyResult(False, "Link wygasł.")

    _, digest = _hash_password(password or "", row.get("password_salt") or "")
    if digest != (row.get("password_hash") or ""):
        return VerifyResult(False, "Nieprawidłowy e-mail lub hasło.")

    return VerifyResult(True, "OK", row=row)


def set_status(link_id: str, status: str) -> dict[str, Any] | None:
    status = (status or "").strip().lower()
    if status not in {"active", "suspended", "revoked"}:
        raise ValueError("Nieprawidłowy status")

    updates = ["status = %s", "updated_at = NOW()"]
    params: list[Any] = [status]
    if status == "suspended":
        updates.append("suspended_at = NOW()")
    elif status == "active":
        updates.append("suspended_at = NULL")
        updates.append("revoked_at = NULL")
    elif status == "revoked":
        updates.append("revoked_at = NOW()")

    sql = f"""
    UPDATE public.report_share_links
    SET {", ".join(updates)}
    WHERE id = %s
    RETURNING *;
    """
    params.append(link_id)
    with _db_connect() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, tuple(params))
            row = cur.fetchone()
        conn.commit()
    return dict(row) if row else None


def set_password(link_id: str, password: str) -> dict[str, Any] | None:
    salt_hex, password_hash = _hash_password(password)
    sql = """
    UPDATE public.report_share_links
    SET password_salt = %s, password_hash = %s, updated_at = NOW()
    WHERE id = %s
    RETURNING *;
    """
    with _db_connect() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (salt_hex, password_hash, link_id))
            row = cur.fetchone()
        conn.commit()
    return dict(row) if row else None


def regrant_access(link_id: str, *, hours_valid: int | None, indefinite: bool) -> dict[str, Any] | None:
    new_token = secrets.token_urlsafe(32)
    expires_at = None if indefinite else (_utc_now() + timedelta(hours=max(int(hours_valid or 1), 1)))
    sql = """
    UPDATE public.report_share_links
    SET
        token = %s,
        status = 'active',
        indefinite = %s,
        expires_at = %s,
        suspended_at = NULL,
        revoked_at = NULL,
        updated_at = NOW()
    WHERE id = %s
    RETURNING *;
    """
    with _db_connect() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(sql, (new_token, bool(indefinite), expires_at, link_id))
            row = cur.fetchone()
        conn.commit()
    return dict(row) if row else None


def delete_access(link_id: str) -> bool:
    sql = """
    DELETE FROM public.report_share_links
    WHERE id = %s;
    """
    with _db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (link_id,))
            deleted = cur.rowcount > 0
        conn.commit()
    return bool(deleted)


def mark_sent(link_id: str) -> None:
    sql = """
    UPDATE public.report_share_links
    SET last_sent_at = NOW(), updated_at = NOW()
    WHERE id = %s;
    """
    with _db_connect() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (link_id,))
        conn.commit()
