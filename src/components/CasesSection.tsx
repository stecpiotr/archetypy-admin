// archetypy-admin/src/components/CasesSection.tsx
// Sekcja formularza: wszystkie przypadki obok siebie (imię + nazwisko w jednym wierszu).
// Automatycznie podpowiada na podstawie mianownika + płci, ale każde pole można nadpisać.

import React from "react";
import { buildAllCases, Gender, NameCases } from "../declensions";

export interface CasesValues {
  first_name_nom: string;
  last_name_nom: string;
  gender: Gender;

  first_name_gen?: string;
  last_name_gen?: string;

  first_name_dat?: string;
  last_name_dat?: string;

  first_name_acc?: string;
  last_name_acc?: string;

  first_name_ins?: string;
  last_name_ins?: string;

  first_name_loc?: string;
  last_name_loc?: string;

  first_name_voc?: string;
  last_name_voc?: string;
}

type Props = {
  value: CasesValues;
  onChange: (next: CasesValues) => void;
};

const Row: React.FC<{
  label: string;
  fKey: keyof NameCases;
  value: CasesValues;
  onChange: (next: CasesValues) => void;
}> = ({ label, fKey, value, onChange }) => {
  const leftKey = (`first_name_${fKey}` as keyof CasesValues);
  const rightKey = (`last_name_${fKey}` as keyof CasesValues);

  return (
    <div style={{ display: "flex", gap: 12, alignItems: "center", marginTop: 10 }}>
      <div style={{ width: 170, fontWeight: 600 }}>{label}</div>
      <input
        style={{ flex: 1, padding: "8px 10px" }}
        value={(value[leftKey] as string) || ""}
        onChange={(e) => onChange({ ...value, [leftKey]: e.target.value })}
        placeholder="Imię w tym przypadku"
      />
      <input
        style={{ flex: 1, padding: "8px 10px" }}
        value={(value[rightKey] as string) || ""}
        onChange={(e) => onChange({ ...value, [rightKey]: e.target.value })}
        placeholder="Nazwisko w tym przypadku"
      />
    </div>
  );
};

const CasesSection: React.FC<Props> = ({ value, onChange }) => {
  const { first_name_nom, last_name_nom, gender } = value;

  const handleAutofill = () => {
    const built = buildAllCases(first_name_nom || "", last_name_nom || "", gender || "M");

    const next: CasesValues = {
      ...value,
      // Imię
      first_name_gen: built.first.gen,
      first_name_dat: built.first.dat,
      first_name_acc: built.first.acc,
      first_name_ins: built.first.instr,
      first_name_loc: built.first.loc,
      first_name_voc: built.first.voc,
      // Nazwisko
      last_name_gen: built.last.gen,
      last_name_dat: built.last.dat,
      last_name_acc: built.last.acc,
      last_name_ins: built.last.instr,
      last_name_loc: built.last.loc,
      last_name_voc: built.last.voc,
    };

    onChange(next);
  };

  return (
    <div style={{ border: "1px solid #e8e8e8", borderRadius: 8, padding: 14, marginTop: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ fontWeight: 700 }}>Odmiana imienia i nazwiska (wszystkie przypadki)</div>
        <button type="button" onClick={handleAutofill} style={{
          background: "#06b09c", color: "#fff", border: "none", borderRadius: 6, padding: "8px 10px",
          cursor: "pointer"
        }}>
          Uzupełnij automatycznie
        </button>
      </div>

      <div style={{ marginTop: 10, color: "#677", fontSize: 13 }}>
        Pola są edytowalne – ręczna zmiana NADPISUJE podpowiedź. W wierszu wprowadzaj imię (lewe) i nazwisko (prawe).
      </div>

      <Row label="Mianownik (kto? co?)" fKey="nom" value={value} onChange={onChange} />
      <Row label="Dopełniacz (kogo? czego?)" fKey="gen" value={value} onChange={onChange} />
      <Row label="Celownik (komu? czemu?)" fKey="dat" value={value} onChange={onChange} />
      <Row label="Biernik (kogo? co?)" fKey="acc" value={value} onChange={onChange} />
      <Row label="Narzędnik (z kim? z czym?)" fKey="instr" value={value} onChange={onChange} />
      <Row label="Miejscownik (o kim? o czym?)" fKey="loc" value={value} onChange={onChange} />
      <Row label="Wołacz" fKey="voc" value={value} onChange={onChange} />
    </div>
  );
};

export default CasesSection;
