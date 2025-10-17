# utils.py

from __future__ import annotations
import secrets
import string

def make_token(n: int = 40) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(n))
