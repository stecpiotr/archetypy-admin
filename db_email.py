# db_email.py
from __future__ import annotations
from typing import Dict, Any, List, Optional

class DuplicateTokenError(Exception):
    pass

TABLE = "email_logs"

def create_email_record(sb, study_id: str, email: str, subject: str, text: str, token: str) -> Dict[str, Any]:
    data = {
        "study_id": study_id,
        "email": email,
        "subject": subject,
        "text": text,
        "token": token,
        "status": "queued",
    }
    res = sb.table(TABLE).insert(data).execute()
    if getattr(res, "data", None):
        return res.data[0]
    # sprawdź unikalność tokenu
    chk = sb.table(TABLE).select("id").eq("token", token).execute()
    if getattr(chk, "data", None):
        raise DuplicateTokenError("token taken")
    # inny błąd
    raise RuntimeError(str(getattr(res, "error", "email insert error")))

def mark_email_sent(sb, email_id: str, provider_message_id: str = "") -> None:
    sb.table(TABLE).update({"status": "sent", "provider_message_id": provider_message_id}).eq("id", email_id).execute()

def list_email_for_study(sb, study_id: str) -> List[Dict[str, Any]]:
    res = sb.table(TABLE).select("*").eq("study_id", study_id).order("created_at", desc=True).execute()
    return getattr(res, "data", []) or []
