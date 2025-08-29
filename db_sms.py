# db_sms.py — operacje na tabeli public.sms_messages (Supabase)

from __future__ import annotations
from typing import Dict, List
from supabase import Client


class DuplicateTokenError(Exception):
    """Unikalny indeks na sms_messages.token zgłosił konflikt (kolizja tokenu)."""
    pass


def _is_unique_violation(err: Exception) -> bool:
    """
    Próba wykrycia błędu unikalności (Postgres 23505 / 409).
    Supabase w Pythonie nie zawsze zwraca kod błędu w tym samym miejscu,
    więc sprawdzamy bezpiecznie treść komunikatu.
    """
    msg = (getattr(err, "message", "") or str(err) or "").lower()
    return (
        "23505" in msg            # kod postgres unique_violation
        or "unique" in msg
        or "duplicate" in msg
        or "conflict" in msg
        or "409" in msg
    )


def create_sms_record(sb: Client, study_id: str, phone: str, text: str, token: str) -> Dict:
    """
    Tworzy rekord w sms_messages i zwraca wstawiony wiersz jako dict.

    WAŻNE:
    - Funkcja NIE generuje nowego tokenu w środku.
      Jeśli wystąpi kolizja (unikalny indeks na `token`), rzuca DuplicateTokenError.
      Dzięki temu warstwa wyżej (send_link.py) może wygenerować NOWY token,
      PODMIENIĆ go w treści SMS i powtórzyć próbę — zachowujemy spójność
      między treścią wysłanego SMS a rekordem w bazie.

    Kolumny w tabeli: id, study_id, phone, body, token, provider_message_id,
                      status, clicked_at, started_at, completed_at, created_at
    """
    try:
        ins = (
            sb.table("sms_messages")
            .insert(
                {
                    "study_id": study_id,
                    "phone": phone,
                    "body": text,
                    "token": token,
                    "status": "queued",
                }
            )
            .execute()
        )
    except Exception as e:
        if _is_unique_violation(e):
            # sygnalizujemy do wyższej warstwy: wygeneruj inny token i spróbuj ponownie
            raise DuplicateTokenError("Token already exists") from e
        raise

    # Supabase zazwyczaj zwraca inserted rows w .data
    if ins.data and len(ins.data) > 0:
        return ins.data[0]

    # Awaryjnie — odczyt ostatniego dopasowania po study_id + phone + body
    sel = (
        sb.table("sms_messages")
        .select("*")
        .eq("study_id", study_id)
        .eq("phone", phone)
        .eq("body", text)
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if sel.data and len(sel.data) > 0:
        return sel.data[0]

    raise RuntimeError("Nie udało się odczytać utworzonego rekordu SMS.")


def mark_sms_sent(sb: Client, sms_id: str, provider_message_id: str) -> None:
    sb.table("sms_messages").update(
        {"status": "sent", "provider_message_id": provider_message_id}
    ).eq("id", sms_id).execute()


def list_sms_for_study(sb: Client, study_id: str) -> List[Dict]:
    """
    Zwraca listę rekordów SMS dla danego badania (najnowsze na górze).
    """
    res = (
        sb.table("sms_messages")
        .select("*")
        .eq("study_id", study_id)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data or []
