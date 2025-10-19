# email_client.py
from __future__ import annotations
import smtplib
from email.message import EmailMessage
from typing import Tuple, Optional

def send_email(
    host: str,
    port: int,
    username: str,
    password: str,
    secure: str,  # "ssl" | "starttls"
    from_email: str,
    from_name: str,
    to_email: str,
    subject: str,
    text: str,
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Zwraca: (ok, message_id, error)
    """
    msg = EmailMessage()
    msg["From"] = f"{from_name} <{from_email}>" if from_name else from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(text)

    try:
        if (secure or "").lower() == "ssl":
            with smtplib.SMTP_SSL(host, port) as s:
                s.login(username, password)
                s.send_message(msg)
        else:
            with smtplib.SMTP(host, port) as s:
                s.ehlo()
                s.starttls()
                s.login(username, password)
                s.send_message(msg)
        # Message-ID tworzy moduł email automatycznie, ale na wszelki wypadek zwracamy to co jest
        return True, msg.get("Message-Id"), None
    except Exception as e:
        return False, None, str(e)
