# msapi_client.py

from __future__ import annotations
from typing import Optional, Tuple
import requests

SMSAPI_BASE = "https://api.smsapi.pl/sms.do"   # format=json

def send_sms(api_token: str, to_phone: str, text: str, sender: Optional[str] = None, timeout: int = 20
             ) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Zwraca (ok, provider_message_id, error).
    """
    headers = {"Authorization": f"Bearer {api_token}"}
    data = {"to": to_phone, "message": text, "format": "json"}
    if sender:
        data["from"] = sender
    try:
        resp = requests.post(SMSAPI_BASE, headers=headers, data=data, timeout=timeout)
        resp.raise_for_status()
        js = resp.json()
        mid = None
        if isinstance(js, dict) and "list" in js and js["list"]:
            mid = js["list"][0].get("id")
        if mid:
            return True, mid, None
        return False, None, f"Brak ID w odpowiedzi SMSAPI: {js}"
    except Exception as e:
        return False, None, str(e)
