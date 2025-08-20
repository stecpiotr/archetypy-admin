// archetypy-admin/src/declensions.ts
// Jedno miejsce z heurystykami odmiany. Użytkownik może je nadpisać w formularzu.
// Zasady są zachowawcze + kilka praktycznych wyjątków.

export type Gender = "M" | "F";

export interface NameCases {
  nom: string;   // mianownik: Kto? Co?  → Janusz / Anna
  gen: string;   // dopełniacz: Kogo? Czego? → Janusza / Anny
  dat: string;   // celownik: Komu? Czemu? → Januszowi / Annie
  acc: string;   // biernik: Kogo? Co? → Janusza / Annę
  instr: string; // narzędnik: Z kim? Z czym? → z Januszem / z Anną
  loc: string;   // miejscownik: O kim? O czym? → o Januszu / o Annie
  voc: string;   // wołacz: O! → Januszu! / Anno!
}

export interface FullCases {
  first: NameCases;
  last: NameCases;
  full: {
    nom: string;
    gen: string;
    dat: string;
    acc: string;
    instr: string;
    loc: string;
    voc: string;
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// PROSTE NARZĘDZIA

const ends = (s: string, suf: string) => s.toLowerCase().endsWith(suf);
const cap = (s: string) => (s ? s[0].toUpperCase() + s.slice(1) : s);

// ─────────────────────────────────────────────────────────────────────────────
// IMIĘ

function declineFirstName(nameNom: string, gender: Gender): NameCases {
  const n = nameNom.trim();

  // Wyjątki: tzw. „żeńskie męskie” – imię żeńskie o formie męskiej „-usz”
  // Tu ważna Twoja uwaga: Janusza (K) → miejscownik: „o Januszy”
  const femaleMasculine = ["Janusza"]; // dopisuj, jeśli pojawią się kolejne przypadki
  const isFemaleMasculine = gender === "F" && femaleMasculine.some(x => x.toLowerCase() === n.toLowerCase());

  if (gender === "F" && !isFemaleMasculine) {
    // typowa żeńska deklinacja
    // nom: Anna
    let gen = n;
    let dat = n;
    let acc = n;
    let instr = n;
    let loc = n;
    let voc = n;

    if (ends(n, "a")) {
      gen = n.slice(0, -1) + "y";     // Anna → Anny
      dat = n.slice(0, -1) + "ie";    // Annie
      acc = n.slice(0, -1) + "ę";     // Annę
      instr = n.slice(0, -1) + "ą";   // Anną
      loc = n.slice(0, -1) + "ie";    // Annie
      voc = n.slice(0, -1) + "o";     // Anno
    } else {
      // żeńskie niekończące się na -a (np. „Eli” – sporadyczne), zostawiamy bezpieczne kopie
      gen = n;
      dat = n;
      acc = n;
      instr = n;
      loc = n;
      voc = n;
    }

    return {
      nom: n, gen: cap(gen), dat: cap(dat), acc: cap(acc),
      instr: cap(instr), loc: cap(loc), voc: cap(voc)
    };
  }

  // męska / lub „żeńskie męskie” (Janusza)
  // Proste reguły, do ręcznego nadpisania w UI jeśli zajdzie potrzeba.
  let gen = n, dat = n, acc = n, instr = n, loc = n, voc = n;

  if (ends(n, "ek")) {
    // Marek → Marka, Markowi, Marka, Markiem, o Marku, Marku!
    const tema = n.slice(0, -2) + "ka";
    gen = tema;
    dat = n.slice(0, -2) + "kowi";
    acc = tema;
    instr = n.slice(0, -2) + "kiem";
    loc = n.slice(0, -1) + "u"; // „o Marku”
    voc = n.slice(0, -1) + "u";
  } else if (ends(n, "a")) {
    // Męskie zakończone na -a (np. Kuba, Michała w gen. itd.)
    gen = n.slice(0, -1) + "y";     // Kuba → Kuby (najczęstszy wzorzec)
    dat = n.slice(0, -1) + "ie";    // Kubie
    acc = n.slice(0, -1) + "ę";     // Kubę
    instr = n.slice(0, -1) + "ą";   // Kubą
    loc = n.slice(0, -1) + "ie";    // Kubie
    voc = n.slice(0, -1) + "o";     // Kubo!
  } else if (ends(n, "usz")) {
    // Janusz (M) → o Januszu / Januszu!
    gen = n + "a";
    dat = n + "owi";
    acc = n + "a";
    instr = n + "em";
    loc = n + "u";
    voc = n + "u";
    // „Janusza” (K) – miejscownik: „o Januszy”
    if (isFemaleMasculine) {
      gen = n;           // tu i tak bierzemy z panelu kobiecego GEN, więc to tylko fallback
      dat = n;
      acc = n;
      instr = n;
      loc = n.slice(0, -1) + "y"; // Januszy
      voc = n;
    }
  } else {
    // Marcin → Marcina, Marcinowi, Marcina, Marcinem, o Marcinie, Marcinie!
    gen = n + "a";
    dat = n + "owi";
    acc = n + "a";
    instr = n + "em";
    loc = n + "ie";
    voc = n + "ie";
  }

  return {
    nom: n, gen: cap(gen), dat: cap(dat), acc: cap(acc),
    instr: cap(instr), loc: cap(loc), voc: cap(voc)
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// NAZWISKO

function declineLastName(sNom: string, gender: Gender): NameCases {
  const s = sNom.trim();

  if (gender === "F") {
    // Kowalska, Nowacka, Stec (nieodmienne żeńskie), etc.
    if (ends(s, "ska")) {
      return {
        nom: s,
        gen: cap(s.slice(0, -3) + "skiej"),
        dat: cap(s.slice(0, -3) + "skiej"),
        acc: cap(s.slice(0, -3) + "ską"),
        instr: cap(s.slice(0, -3) + "ską"),
        loc: cap(s.slice(0, -3) + "skiej"),
        voc: cap(s),
      };
    }
    if (ends(s, "cka")) {
      return {
        nom: s,
        gen: cap(s.slice(0, -3) + "ckiej"),
        dat: cap(s.slice(0, -3) + "ckiej"),
        acc: cap(s.slice(0, -3) + "cką"),
        instr: cap(s.slice(0, -3) + "cką"),
        loc: cap(s.slice(0, -3) + "ckiej"),
        voc: cap(s),
      };
    }
    if (ends(s, "dzka")) {
      return {
        nom: s,
        gen: cap(s.slice(0, -4) + "dzkiej"),
        dat: cap(s.slice(0, -4) + "dzkiej"),
        acc: cap(s.slice(0, -4) + "dzką"),
        instr: cap(s.slice(0, -4) + "dzką"),
        loc: cap(s.slice(0, -4) + "dzkiej"),
        voc: cap(s),
      };
    }
    if (ends(s, "zka")) {
      return {
        nom: s,
        gen: cap(s.slice(0, -3) + "zkiej"),
        dat: cap(s.slice(0, -3) + "zkiej"),
        acc: cap(s.slice(0, -3) + "zką"),
        instr: cap(s.slice(0, -3) + "zką"),
        loc: cap(s.slice(0, -3) + "zkiej"),
        voc: cap(s),
      };
    }
    if (ends(s, "a")) {
      return {
        nom: s,
        gen: cap(s.slice(0, -1) + "y"),
        dat: cap(s.slice(0, -1) + "ie"),
        acc: cap(s.slice(0, -1) + "ę"),
        instr: cap(s.slice(0, -1) + "ą"),
        loc: cap(s.slice(0, -1) + "ie"),
        voc: cap(s),
      };
    }
    // nieodmienne żeńskie (np. Stec) – zachowawczo bez zmian
    return { nom: s, gen: s, dat: s, acc: s, instr: s, loc: s, voc: s };
  }

  // Mężczyźni
  if (ends(s, "ek")) {
    // Gołek → Gołka, Gołkowi, Gołka, Gołkiem, o Gołku, Gołku!
    const tema = s.slice(0, -2) + "ka";
    return {
      nom: s,
      gen: cap(tema),
      dat: cap(s.slice(0, -2) + "kowi"),
      acc: cap(tema),
      instr: cap(s.slice(0, -2) + "kiem"),
      loc: cap(s.slice(0, -1) + "u"),
      voc: cap(s.slice(0, -1) + "u"),
    };
  }
  if (ends(s, "a")) {
    // męskie -a
    return {
      nom: s,
      gen: cap(s.slice(0, -1) + "y"),
      dat: cap(s.slice(0, -1) + "ie"),
      acc: cap(s.slice(0, -1) + "ę"),
      instr: cap(s.slice(0, -1) + "ą"),
      loc: cap(s.slice(0, -1) + "ie"),
      voc: cap(s.slice(0, -1) + "o"),
    };
  }
  // Marcin Kowalski → Marcinem Kowalskim, o Kowalskim
  return {
    nom: s,
    gen: cap(s + "a"),
    dat: cap(s + "owi"),
    acc: cap(s + "a"),
    instr: cap(s + "em"),
    loc: cap(s + "ie"),
    voc: cap(s + "ie"),
  };
}

// ─────────────────────────────────────────────────────────────────────────────

export function buildAllCases(firstNom: string, lastNom: string, gender: Gender): FullCases {
  const first = declineFirstName(firstNom, gender);
  const last = declineLastName(lastNom, gender);

  const full = {
    nom: `${first.nom} ${last.nom}`.trim(),
    gen: `${first.gen} ${last.gen}`.trim(),
    dat: `${first.dat} ${last.dat}`.trim(),
    acc: `${first.acc} ${last.acc}`.trim(),
    instr: `${first.instr} ${last.instr}`.trim(),
    loc: `${first.loc} ${last.loc}`.trim(),
    voc: `${first.voc} ${last.voc}`.trim(),
  };

  return { first, last, full };
}
