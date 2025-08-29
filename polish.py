# polish.py  — heurystyczne odmiany polskich imion i nazwisk
# Używany przez panel admina do podpowiedzi. Możesz edytować ręcznie w UI.

from __future__ import annotations
import re
from typing import Dict, Tuple

# ────────────────────────────── UTIL: slugify ──────────────────────────────
_PL_MAP = str.maketrans(
    "ąćęłńóśżźĄĆĘŁŃÓŚŻŹ",
    "acelnoszzACELNOSZZ",
)

def slugify(text: str) -> str:
    t = (text or "").strip().translate(_PL_MAP)
    t = re.sub(r"[^0-9a-zA-Z]+", "-", t)
    t = re.sub(r"-{2,}", "-", t).strip("-")
    return t.lower()

def base_slug(last_name: str) -> str:
    return slugify(last_name)

# ─────────────────────── Imiona – pomocnicze reguły ───────────────────────

def _title(s: str) -> str:
    return s[:1].upper() + s[1:] if s else s

def _masc_loc_general(name: str) -> str:
    """Miejscownik dla typowych męskich imion zakończonych spółgłoską."""
    low = name.lower()
    # u: końcówki typu -k, -g, -ch, -l, -ł, -r, -sz, -cz, -rz, -z
    if re.search(r"(k|g|ch|l|ł|r|sz|cz|rz|z)$", low):
        # Piotr → Piotrze (wyjątek), Marek → Marku (nie obsługujemy Marek tutaj)
        if low == "piotr":  # wyjątek
            return _title("piotrze")
        if low.endswith("l") or low.endswith("ł"):
            return _title(low + "u")          # Emil → Emilu, Kamil → Kamilu
        if low.endswith(("k", "g", "ch")):
            return _title(low + "u")          # Marek → Marku (zbliżenie)
        if low.endswith(("sz", "cz", "rz", "z", "r")):
            return _title(low + "u")          # Tomasz → Tomaszu
    # domyślnie „-ie”
    return _title(low + "ie")                  # Marcin → Marcinie, Adam → Adamie

def decline_first_m(name: str) -> Dict[str, str]:
    n = (name or "").strip()
    low = n.lower()

    # Specjalne, najczęstsze wyjątki
    if low == "piotr":
        return {
            "gen": "Piotra",
            "dat": "Piotrowi",
            "acc": "Piotra",
            "ins": "Piotrem",
            "loc": "Piotrze",
            "voc": "Piotrze",
        }
    if low == "paweł":
        # Paweł → Pawła / Pawłowi / Pawła / Pawłem / Pawle / Pawle
        return {
            "gen": "Pawła",
            "dat": "Pawłowi",
            "acc": "Pawła",
            "ins": "Pawłem",
            "loc": "Pawle",
            "voc": "Pawle",
        }
    if low == "michał":
        return {
            "gen": "Michała",
            "dat": "Michałowi",
            "acc": "Michała",
            "ins": "Michałem",
            "loc": "Michale",
            "voc": "Michale",
        }

    # NOWE: imiona zakończone na „-ko” (np. Gniewko, Janko)
    if low.endswith("ko"):
        base = n[:-1]  # ucinamy tylko „o”: Gniewk-
        return {
            "gen": _title(base + "a"),     # Gniewka
            "dat": _title(base + "owi"),   # Gniewkowi
            "acc": _title(base + "a"),     # Gniewka
            "ins": _title(base + "iem"),   # Gniewkiem
            "loc": _title(base + "u"),     # Gniewku
            "voc": _title(base + "u"),     # Gniewku
        }

    # Ogólna reguła dla większości męskich imion kończących się spółgłoską
    # (Marcin, Emil, Krzysztof, Jakub, Adam, Rafał, itp.)
    root = n
    gen = _title(root + "a")          # Marcin → Marcina, Emil → Emila
    dat = _title(root + "owi")        # Marcinowi, Emilowi
    acc = gen                         # w męskoosobowych biernik = dopełniacz
    # narzędnik: -em, a po k/g: -iem
    if root.lower().endswith(("k", "g")):
        ins = _title(root + "iem")    # Nowak → Nowakiem (nazwiska), imiona rzadkie na k/g
    else:
        ins = _title(root + "em")     # Marcinem, Emilem, Rafałem (poniżej poprawka)
    # poprawka dla -ał/-eł/-f/-ł → końcówki „-em/-łem”
    if root.lower().endswith("ał") or root.lower().endswith("eł"):
        ins = _title(root[:-1] + "em")   # Michał → Michałem, Paweł → Pawłem (pokryte wyżej)
    if root.lower().endswith("f"):
        ins = _title(root + "em")     # Józef → Józefem
    loc = _masc_loc_general(root)
    # wołacz: zwykle jak miejscownik
    voc = loc

    # Drobne poprawki: Rafał → Rafale, Emil → Emilu itp. zapewnia _masc_loc_general
    return {"gen": gen, "dat": dat, "acc": acc, "ins": ins, "loc": voc, "voc": voc}

def decline_first_f(name: str) -> Dict[str, str]:
    n = (name or "").strip()
    low = n.lower()

    # Bardzo częsty wzorzec „-a”
    if low.endswith("a"):
        base = n[:-1]
        # „-ia” → „-ii”
        if low.endswith("ia"):
            stem = n[:-1]  # ucinamy tylko „a”: Emilia → Emili
            gen = stem + "i"
            dat = stem + "i"
            acc = base + "ę"
            ins = base + "ą"
            loc = stem + "i"
            voc = base + "o"
            return {"gen": gen, "dat": dat, "acc": acc, "ins": ins, "loc": loc, "voc": voc}
        # po k/g zwykle „-i” w dopełniaczu
        gen = base + ("i" if base.lower().endswith(("k", "g")) else "y")
        # dat/loc: najczęściej „-ie”
        dat = base + "ie"
        loc = dat
        acc = base + "ę"
        ins = base + "ą"
        # wołacz bywa „-o”
        voc = base + "o"
        return {"gen": gen, "dat": dat, "acc": acc, "ins": ins, "loc": loc, "voc": voc}

    # Inne żeńskie – zostawiamy bez odmiany (rzadkie przypadki)
    return {"gen": n, "dat": n, "acc": n, "ins": n, "loc": n, "voc": n}

def decline_first_name(name: str, gender: str) -> Dict[str, str]:
    if (gender or "M") == "F":
        return decline_first_f(name)
    # Specjalny wyjątek – „Janusza” (żeńskie imię nietypowe), o które prosiłeś
    if gender == "F" and name.strip().lower().endswith("usza"):
        base = name[:-1]
        return {
            "gen": base + "y",
            "dat": base + "y",
            "acc": name[:-1] + "ę",
            "ins": name[:-1] + "ą",
            "loc": base + "y",
            "voc": base + "o",
        }
    return decline_first_m(name)

# ───────────────────── Nazwiska – pomocnicze reguły ───────────────────────

def decline_surname_m(sur: str) -> Dict[str, str]:
    s = (sur or "").strip()
    low = s.lower()

    # 1) Przymiotnikowe: -ski/-cki/-dzki/-zki
    if re.search(r"(ski|cki|dzki|zki)$", low):
        base = s
        return {
            "gen": base[:-1] + "ego",      # Wiśniewskiego
            "dat": base[:-1] + "emu",      # Wiśniewskiemu
            "acc": base[:-1] + "ego",      # Wiśniewskiego
            "ins": base[:-1] + "im",       # Wiśniewskim
            "loc": base[:-1] + "im",       # Wiśniewskim
            "voc": base,                   # Wołacz jak mianownik
        }

    # NOWE: przymiotnikowe na „-i” (np. Drugi → drugiego/drugiemu/drugim)
    if re.search(r"[bcćdfghjklłmnńprsśtwzźż]i$", low):
        stem = s[:-1]
        return {
            "gen": _title(stem + "iego"),
            "dat": _title(stem + "iemu"),
            "acc": _title(stem + "iego"),
            "ins": _title(stem + "im"),
            "loc": _title(stem + "im"),
            "voc": s,
        }

    # NOWE: przymiotnikowe na „-y” (np. Młody/Nowy → młodego/nowemu/młodym)
    if re.search(r"[bcćdfghjklłmnńprsśtwzźż]y$", low):
        stem = s[:-1]
        return {
            "gen": _title(stem + "ego"),
            "dat": _title(stem + "emu"),
            "acc": _title(stem + "ego"),
            "ins": _title(stem + "ym"),
            "loc": _title(stem + "ym"),
            "voc": s,
        }

    # 2) -ek → Gołek → Gołka / Gołkowi / Gołka / Gołkiem / Gołku / Gołku
    if low.endswith("ek"):
        stem = s[:-2] + "k"
        return {
            "gen": stem + "a",
            "dat": stem + "owi",
            "acc": stem + "a",
            "ins": stem + "iem",
            "loc": stem + "u",
            "voc": stem + "u",
        }

    # 3) -ec → Stec → Steca / Stecowi / Steca / Stecem / Stecu / Stecu
    if low.endswith("ec"):
        return {
            "gen": s + "a",
            "dat": s + "owi",
            "acc": s + "a",
            "ins": s + "em",
            "loc": s + "u",
            "voc": s + "u",
        }

    # 4) Nazwiska męskie na -a (np. Batyra): Batyry, Batyrze, Batyrę, Batyrą, Batyrze, Batyro
    if low.endswith("a"):
        base = s[:-1]  # Batyra → Batyr-
        # dopełniacz: zwykle -y, po k/g → -i
        gen = base + ("i" if base.lower().endswith(("k", "g")) else "y")
        # dat/loc: dla „...ra” bardzo często „...rze”
        if base.lower().endswith("r"):
            dat = base + "ze"   # Batyrze
            loc = dat
        else:
            dat = base + "e"
            loc = dat
        acc = base + "ę"
        ins = base + "ą"
        # Wołacz: często „-o”
        voc = base + "o"
        return {"gen": gen, "dat": dat, "acc": acc, "ins": ins, "loc": loc, "voc": voc}

    # 5) Nazwiska twarde na spółgłoskę (Nowak, Kowal, Mazur, Stec — poza -ec wyżej)
    gen = s + "a"
    dat = s + "owi"
    acc = gen
    if low.endswith(("k", "g")):
        ins = s + "iem"   # Nowakiem
    else:
        ins = s + "em"    # Mazurem
    # miejscownik: zwykle „-u”
    loc = s + "u"
    voc = loc
    return {"gen": gen, "dat": dat, "acc": acc, "ins": ins, "loc": loc, "voc": voc}

def decline_surname_f(sur: str) -> Dict[str, str]:
    s = (sur or "").strip()
    low = s.lower()

    # Przymiotnikowe żeńskie: -ska/-cka/-dzka/-zka
    if re.search(r"(ska|cka|dzka|zka)$", low):
        base = s[:-1]  # „ska” → „sk”
        return {
            "gen": base + "iej",   # Kowalskiej
            "dat": base + "iej",
            "acc": base + "ą",     # Kowalską
            "ins": base + "ą",
            "loc": base + "iej",
            "voc": s,              # wołacz ≈ mianownik
        }

    # -a (żeńskie nie-przymiotnikowe): Anna Nowakowa? – zostaw ogólne
    if low.endswith("a"):
        base = s[:-1]
        gen = base + ("i" if base.lower().endswith(("k", "g")) else "y")
        dat = base + "ie"
        loc = dat
        acc = base + "ę"
        ins = base + "ą"
        voc = base + "o"
        return {"gen": gen, "dat": dat, "acc": acc, "ins": ins, "loc": loc, "voc": voc}

    # Inne żeńskie: bezpieczny fallback – bez odmiany
    return {"gen": s, "dat": s, "acc": s, "ins": s, "loc": s, "voc": s}

def decline_surname(sur: str, gender: str) -> Dict[str, str]:
    return decline_surname_f(sur) if (gender or "M") == "F" else decline_surname_m(sur)

# ─────────────────────── Zbiorcze API używane w panelu ─────────────────────

def compute_all_cases(first_nom: str, last_nom: str, gender: str) -> Dict[str, str]:
    """Zwraca słownik ze WSZYSTKIMI przypadkami osobno dla imienia i nazwiska."""
    f = decline_first_name(first_nom or "", gender or "M")
    l = decline_surname(last_nom or "", gender or "M")
    out = {
        # imię
        "first_name_gen": f["gen"],
        "first_name_dat": f["dat"],
        "first_name_acc": f["acc"],
        "first_name_ins": f["ins"],
        "first_name_loc": f["loc"],
        "first_name_voc": f["voc"],
        # nazwisko
        "last_name_gen": l["gen"],
        "last_name_dat": l["dat"],
        "last_name_acc": l["acc"],
        "last_name_ins": l["ins"],
        "last_name_loc": l["loc"],
        "last_name_voc": l["voc"],
    }
    return out

# ───── wsteczna zgodność – wykorzystywane wcześniej przez panel ─────

def gen_first_name(first_nom: str, gender: str) -> str:
    return compute_all_cases(first_nom, "", gender)["first_name_gen"]

def gen_last_name(last_nom: str, gender: str) -> str:
    return compute_all_cases("", last_nom, gender)["last_name_gen"]

def loc_person(first_nom: str, last_nom: str, gender: str) -> str:
    c = compute_all_cases(first_nom, last_nom, gender)
    fn, ln = c["first_name_loc"], c["last_name_loc"]
    return (fn + " " + ln).strip()

def instr_person(first_nom: str, last_nom: str, gender: str) -> str:
    c = compute_all_cases(first_nom, last_nom, gender)
    fn, ln = c["first_name_ins"], c["last_name_ins"]
    return (fn + " " + ln).strip()

def compute_all(first_nom: str, last_nom: str, gender: str) -> Dict[str, str]:
    """Zachowane dla zgodności: zwraca tylko GEN/LOC/INS — stare UI."""
    c = compute_all_cases(first_nom, last_nom, gender)
    return {
        "first_name_gen": c["first_name_gen"],
        "last_name_gen": c["last_name_gen"],
        "first_name_loc": c["first_name_loc"],
        "last_name_loc": c["last_name_loc"],
        "first_name_ins": c["first_name_ins"],
        "last_name_ins": c["last_name_ins"],
    }
