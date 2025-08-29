// archetypy-admin/src/components/CasesEditor.tsx
import React, { useMemo, useState } from "react";

type Gender = "M" | "F";

export type CasesValue = {
  first_name_gen?: string;  last_name_gen?: string;
  first_name_dat?: string;  last_name_dat?: string;
  first_name_acc?: string;  last_name_acc?: string;
  first_name_ins?: string;  last_name_ins?: string;
  first_name_loc?: string;  last_name_loc?: string;
  first_name_voc?: string;  last_name_voc?: string;
};

export function CasesEditor(props: {
  gender: Gender;
  firstNameNom: string;
  lastNameNom: string;
  value: CasesValue;
  onChange: (v: CasesValue) => void;
}) {
  const { gender, firstNameNom, lastNameNom, value, onChange } = props;

  const [touched, setTouched] = useState<Record<string, boolean>>({});

  const suggest = useMemo(() => suggestPolishCases(firstNameNom, lastNameNom, gender), [
    firstNameNom,
    lastNameNom,
    gender,
  ]);

  function setField(k: keyof CasesValue, val: string) {
    onChange({ ...value, [k]: val });
    setTouched((t) => ({ ...t, [k]: true }));
  }

  function fillSuggestions() {
    const next: CasesValue = { ...value };
    (Object.keys(suggest) as (keyof CasesValue)[]).forEach((k) => {
      if (!touched[k] && !next[k]) next[k] = suggest[k] || "";
    });
    onChange(next);
  }

  const Row = (props: {
    label: string;
    fnKey: keyof CasesValue;
    lnKey: keyof CasesValue;
    fnPh?: string;
    lnPh?: string;
  }) => (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 10 }}>
      <div style={{ gridColumn: "1 / span 2", fontSize: 12, color: "#556", marginBottom: 2 }}>
        {props.label}
      </div>
      <input
        type="text"
        value={value[props.fnKey] || ""}
        placeholder={props.fnPh}
        onChange={(e) => setField(props.fnKey, e.target.value)}
      />
      <input
        type="text"
        value={value[props.lnKey] || ""}
        placeholder={props.lnPh}
        onChange={(e) => setField(props.lnKey, e.target.value)}
      />
    </div>
  );

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "flex-end", marginBottom: 12 }}>
        <button type="button" onClick={fillSuggestions}>
          Generuj odmiany
        </button>
      </div>

      <Row
        label="Dopełniacz (kogo? czego?)"
        fnKey="first_name_gen"
        lnKey="last_name_gen"
        fnPh={suggest.first_name_gen}
        lnPh={suggest.last_name_gen}
      />
      <Row
        label="Celownik (komu? czemu?)"
        fnKey="first_name_dat"
        lnKey="last_name_dat"
        fnPh={suggest.first_name_dat}
        lnPh={suggest.last_name_dat}
      />
      <Row
        label="Biernik (kogo? co?)"
        fnKey="first_name_acc"
        lnKey="last_name_acc"
        fnPh={suggest.first_name_acc}
        lnPh={suggest.last_name_acc}
      />
      <Row
        label="Narzędnik (z kim? z czym?)"
        fnKey="first_name_ins"
        lnKey="last_name_ins"
        fnPh={suggest.first_name_ins}
        lnPh={suggest.last_name_ins}
      />
      <Row
        label="Miejscownik (o kim? o czym?)"
        fnKey="first_name_loc"
        lnKey="last_name_loc"
        fnPh={suggest.first_name_loc}
        lnPh={suggest.last_name_loc}
      />
      <Row
        label="Wołacz"
        fnKey="first_name_voc"
        lnKey="last_name_voc"
        fnPh={suggest.first_name_voc}
        lnPh={suggest.last_name_voc}
      />
    </div>
  );
}

/** Bardzo proste podpowiedzi + wyjątki. NIE zapisujemy automatycznie. */
function suggestPolishCases(first: string, last: string, gender: Gender): CasesValue {
  const fn = first.trim();
  const ln = last.trim();

  const out: CasesValue = {};

  // ——— GEN ———
  out.first_name_gen = genFirst(fn, gender);
  out.last_name_gen  = genLast(ln, gender);

  // ——— DAT (bardzo uproszczony) ———
  out.first_name_dat = datFromGen(out.first_name_gen!);
  out.last_name_dat  = datFromGen(out.last_name_gen!);

  // ——— ACC ———
  out.first_name_acc = accFirst(fn, gender, out.first_name_gen!);
  out.last_name_acc  = accLast(ln, gender, out.last_name_gen!);

  // ——— INS ———
  out.first_name_ins = insFirst(fn, gender);
  out.last_name_ins  = insLast(ln, gender);

  // ——— LOC ———
  out.first_name_loc = locFirst(fn, gender, out.first_name_gen!);
  out.last_name_loc  = locLast(ln, gender, out.last_name_gen!);

  // ——— VOC ———
  out.first_name_voc = vocFirst(fn, gender);
  out.last_name_voc  = vocLast(ln, gender);

  return out;
}

/* ===== Najprostsze reguły + wyjątek „Janusza → Januszy” (F) ===== */

function genFirst(n: string, g: Gender) {
  if (g === "F") {
    if (/a$/i.test(n)) return n.replace(/a$/i, "y"); // Anna->Anny | Janusza->Januszy (DZIAŁA!)
    return n;
  }
  // M
  if (/ek$/i.test(n)) return n.replace(/ek$/i, "ka"); // Marek->Marka
  if (/in$/i.test(n)) return n + "a";                 // Marcin->Marcina
  return n;
}
function genLast(n: string, g: Gender) {
  if (g === "F") {
    if (/ska$/i.test(n)) return n.replace(/ska$/i, "skiej");
    if (/cka$/i.test(n)) return n.replace(/cka$/i, "ckiej");
    return n + ""; // np. „Stec” zostaje „Stec”
  }
  if (/ek$/i.test(n)) return n.replace(/ek$/i, "ka"); // Gołek->Gołka
  return n;
}

function datFromGen(gen: string) {
  // totalny skrót: Anny->Annie, Marcina->Marcinowi, Gołka->Gołkowi
  if (/y$/i.test(gen)) return gen.replace(/y$/i, "ie");
  if (/a$/i.test(gen)) return gen.replace(/a$/i, "owi");
  if (/k$/i.test(gen)) return gen + "owi";
  return gen;
}

function accFirst(nom: string, g: Gender, gen: string) {
  // M: biernik jak dopełniacz, F: „a”->„ę”
  if (g === "M") return gen;
  if (/a$/i.test(nom)) return nom.replace(/a$/i, "ę");
  return nom;
}
function accLast(nom: string, g: Gender, gen: string) {
  if (g === "M") return gen;
  // F: Kowalska->Kowalską, Stec->Stec
  if (/ska$/i.test(nom)) return nom.replace(/ska$/i, "ską");
  if (/cka$/i.test(nom)) return nom.replace(/cka$/i, "cką");
  if (/a$/i.test(nom))   return nom.replace(/a$/i, "ą");
  return nom;
}

function insFirst(n: string, g: Gender) {
  if (g === "M") {
    if (/ek$/i.test(n)) return n.replace(/ek$/i, "kiem"); // Marek->Markiem
    if (/a$/i.test(n))  return n.replace(/a$/i, "ą");
    return n + "em";                                     // Marcin->Marcinem
  }
  if (/a$/i.test(n)) return n.replace(/a$/i, "ą");       // Anna->Anną
  return n;
}
function insLast(n: string, g: Gender) {
  if (g === "M") {
    if (/ek$/i.test(n)) return n.replace(/ek$/i, "kiem"); // Gołek->Gołkiem
    if (!/em$/i.test(n)) return n + "em";
    return n;
  }
  if (/ska$/i.test(n)) return n.replace(/ska$/i, "ską");
  if (/cka$/i.test(n)) return n.replace(/cka$/i, "cką");
  if (/a$/i.test(n))   return n.replace(/a$/i, "ą");
  return n;
}

function locFirst(n: string, g: Gender, gen: string) {
  // wyświetlamy bez „o” — UI ma label „Miejscownik (o kim? o czym?)”
  if (g === "F") {
    if (/a$/i.test(n)) return n.replace(/a$/i, "ie"); // Anna->Annie, Janusza->Januszie (ale patrz wyjątek w GEN->y; tu zachowujemy)
    return n;
  }
  // M
  if (/a$/i.test(gen)) return gen.replace(/a$/i, "ie"); // Marcina->Marcinie
  return gen;
}
function locLast(n: string, g: Gender, gen: string) {
  if (g === "F") {
    if (/ska$/i.test(n)) return n.replace(/ska$/i, "skiej");
    if (/cka$/i.test(n)) return n.replace(/cka$/i, "ckiej");
    if (/a$/i.test(n))   return n.replace(/a$/i, "ie");
    return n;
  }
  if (/a$/i.test(gen)) return gen.replace(/a$/i, "ie"); // Gołka->Gołku
  return gen;
}

function vocFirst(n: string, g: Gender) {
  if (g === "M") {
    if (/in$/i.test(n)) return n.replace(/in$/i, "inie"); // Marcin->Marcinie
    return n;
  }
  if (/a$/i.test(n)) return n.replace(/a$/i, "o");       // Anna->Anno
  return n;
}
function vocLast(n: string, g: Gender) {
  if (g === "M") return n;
  if (/ska$/i.test(n)) return n.replace(/ska$/i, "sko");
  return n;
}
