# backfill_inflection.py
# Uruchomienie:  python backfill_inflection.py [--force]
# Wymaga ENV: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY lub SUPABASE_ANON_KEY

from __future__ import annotations
import os
import sys
import argparse
import importlib.util
from pathlib import Path
from typing import Any, Dict
from dotenv import load_dotenv
load_dotenv()

from supabase import create_client, Client  # pip install supabase


# ───────────────────────────────────────────────────────────────────────────────
# 1) Ładujemy lokalny plik polish.py NA PEWNO z katalogu projektu
# ───────────────────────────────────────────────────────────────────────────────
HERE = Path(__file__).resolve().parent
POLISH_PATH = HERE / "polish.py"
if not POLISH_PATH.exists():
    raise FileNotFoundError(f"Nie widzę {POLISH_PATH} – upewnij się, że plik istnieje.")

spec = importlib.util.spec_from_file_location("polish_local", str(POLISH_PATH))
polish = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
assert spec and spec.loader
spec.loader.exec_module(polish)  # type: ignore[attr-defined]

print(f"[backfill] Używam polish z: {polish.__file__}")

# Krótki self-test, żebyś od razu widział jakie formy daje aktualna logika
def _selftest() -> None:
    print("[selftest] loc(M, Janusz Palikot):", polish.loc_person("Janusz", "Palikot", "M"))
    print("[selftest] loc(M, Emil Stec):     ", polish.loc_person("Emil", "Stec", "M"))
    print("[selftest] loc(M, Marcin Gołek):  ", polish.loc_person("Marcin", "Gołek", "M"))
    print("[selftest] ins(M, Janusz Kowalski):", polish.instr_person("Janusz", "Kowalski", "M"))
    print("[selftest] ins(F, Anna Kowalska): ", polish.instr_person("Anna", "Kowalska", "F"))

_selftest()


# ───────────────────────────────────────────────────────────────────────────────
# 2) Wyjątki (ostatnia linia obrony). Gdyby heurystyka nie zadziałała,
#    te mapy nadpiszą wynik. Klucze w lower-case.
# ───────────────────────────────────────────────────────────────────────────────
EXCEPT_LOC_SURNAME = {
    "palikot": "Palikocie",   # <— kluczowe dla Twojego przypadku
}
EXCEPT_LOC_FIRST = {
    # dopisz w razie potrzeby
}
EXCEPT_INS_SURNAME = {
    # dopisz w razie potrzeby
}
EXCEPT_INS_FIRST = {
    # dopisz w razie potrzeby
}


# ───────────────────────────────────────────────────────────────────────────────
# 3) Połączenie z Supabase
# ───────────────────────────────────────────────────────────────────────────────
def get_sb() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
           or os.environ.get("SUPABASE_ANON_KEY"))
    if not url or not key:
        raise RuntimeError(
            "Ustaw SUPABASE_URL i klucz (SERVICE_ROLE lub ANON) w zmiennych środowiskowych."
        )
    return create_client(url, key)


# ───────────────────────────────────────────────────────────────────────────────
# 4) Przelicz i zapisz
# ───────────────────────────────────────────────────────────────────────────────
def recalc_row(row: Dict[str, Any]) -> Dict[str, str]:
    fn = (row.get("first_name") or "").strip()
    ln = (row.get("last_name") or "").strip()
    g  = (row.get("gender") or "").strip()  # "M" / "F"

    # genitive
    fn_gen = polish.gen_first_name(fn, g)
    ln_gen = polish.gen_last_name(ln, g)

    # locative
    loc = polish.loc_person(fn, ln, g).strip()
    # rozbijamy – zakładamy format "Imię Nazwisko"
    parts = loc.split()
    if len(parts) >= 2:
        fn_loc, ln_loc = parts[0], " ".join(parts[1:])
    else:
        fn_loc, ln_loc = fn, ln

    # Instrumental
    ins = polish.instr_person(fn, ln, g).strip()
    parts = ins.split()
    if len(parts) >= 2:
        fn_ins, ln_ins = parts[0], " ".join(parts[1:])
    else:
        fn_ins, ln_ins = fn, ln

    # Wyjątki (nadpisują)
    key_ln = ln.lower()
    key_fn = fn.lower()
    if key_ln in EXCEPT_LOC_SURNAME:
        ln_loc = EXCEPT_LOC_SURNAME[key_ln]
    if key_fn in EXCEPT_LOC_FIRST:
        fn_loc = EXCEPT_LOC_FIRST[key_fn]
    if key_ln in EXCEPT_INS_SURNAME:
        ln_ins = EXCEPT_INS_SURNAME[key_ln]
    if key_fn in EXCEPT_INS_FIRST:
        fn_ins = EXCEPT_INS_FIRST[key_fn]

    return {
        "first_name_gen": fn_gen,
        "last_name_gen":  ln_gen,
        "first_name_loc": fn_loc,
        "last_name_loc":  ln_loc,
        "first_name_ins": fn_ins,
        "last_name_ins":  ln_ins,
    }


def main(force: bool = False) -> None:
    sb = get_sb()
    res = sb.table("studies").select("*").execute()
    rows = res.data or []
    print(f"[backfill] Wczytano {len(rows)} rekordów.")

    updated = 0
    skipped = 0

    for r in rows:
        calc = recalc_row(r)

        if not force:
            # Pomijamy rekordy, które już mają komplet wypełnionych pól
            already = all(r.get(k) for k in calc.keys())
            if already:
                skipped += 1
                continue

        # Zapis
        sb.table("studies").update(calc).eq("id", r["id"]).execute()
        print(f"updated: {r.get('slug')} -> {calc}")
        updated += 1

    print(f"\nDone. Updated: {updated}, skipped: {skipped}")


# ───────────────────────────────────────────────────────────────────────────────
# 5) CLI
# ───────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true",
                        help="Nadpisz istniejące odmiany (bez ręcznego czyszczenia kolumn).")
    args = parser.parse_args()
    main(force=args.force)
