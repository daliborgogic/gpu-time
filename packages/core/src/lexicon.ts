import type { DateSpec, Unit, Weekday } from "./types.js";

export const weekdays: Weekday[] = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"];

export const dayNames = [
  "ponedeljak",
  "utorak",
  "sreda",
  "četvrtak",
  "petak",
  "subota",
  "nedelja",
];

// Genitive forms ("od ponedeljka do srede" = "from Monday to Wednesday") —
// the case a weekday takes after "od"/"do", not just the nominative.
const dayGenitive = [
  "ponedeljka",
  "utorka",
  "srede",
  "četvrtka",
  "petka",
  "subote",
  "nedelje",
];

export const monthNames = [
  "januar",
  "februar",
  "mart",
  "april",
  "maj",
  "jun",
  "jul",
  "avgust",
  "septembar",
  "oktobar",
  "novembar",
  "decembar",
];

// Genitive forms ("prva nedelja oktobra" = "first week of October") — the
// case Serbian normally uses after another noun, not just the nominative.
const monthGenitive = [
  "januara",
  "februara",
  "marta",
  "aprila",
  "maja",
  "juna",
  "jula",
  "avgusta",
  "septembra",
  "oktobra",
  "novembra",
  "decembra",
];

export const quantities: Record<string, number> = {
  nula: 0,
  jedan: 1,
  jedna: 1,
  jedno: 1,
  dva: 2,
  dve: 2,
  tri: 3,
  četiri: 4,
  pet: 5,
  šest: 6,
  sedam: 7,
  osam: 8,
  devet: 9,
  deset: 10,
  jedanaest: 11,
  dvanaest: 12,
  trinaest: 13,
  četrnaest: 14,
  petnaest: 15,
  šesnaest: 16,
  sedamnaest: 17,
  osamnaest: 18,
  devetnaest: 19,
  dvadeset: 20,
  trideset: 30,
  četrdeset: 40,
  pedeset: 50,
  šezdeset: 60,
  sedamdeset: 70,
  osamdeset: 80,
  devedeset: 90,
  po: 0.5,
  pola: 0.5,
  četvrt: 0.25,
  par: 2,
  nekoliko: 3,
  jednom: 1,
  dvaput: 2,
  triput: 3,
  prvi: 1,
  prva: 1,
  prvo: 1,
  drugi: 2,
  druga: 2,
  drugo: 2,
  treći: 3,
  treća: 3,
  treće: 3,
  četvrti: 4,
  četvrta: 4,
  četvrto: 4,
  peti: 5,
  peta: 5,
  peto: 5,
  šesti: 6,
  sedmi: 7,
  osmi: 8,
  deveti: 9,
  deseti: 10,
  jedanaesti: 11,
  dvanaesti: 12,
  trinaesti: 13,
  četrnaesti: 14,
  petnaesti: 15,
  šesnaesti: 16,
  sedamnaesti: 17,
  osamnaesti: 18,
  devetnaesti: 19,
  dvadeseti: 20,
  trideseti: 30,
  poslednji: -1,
  poslednja: -1,
  poslednje: -1,
};

// "dvadeset prvi" (twenty-first) reaches the compiler as two tokens, so the
// tens word and the ones ordinal are combined rather than listed as thirty
// more entries.
const tensWords: Record<string, number> = {
  dvadeset: 20,
  trideset: 30,
  četrdeset: 40,
  pedeset: 50,
  šezdeset: 60,
  sedamdeset: 70,
  osamdeset: 80,
  devedeset: 90,
};

export function compoundOrdinal(tens: string, ones: string): number {
  const base = tensWords[tens.toLowerCase()];
  const unit = quantities[ones.toLowerCase()];
  if (base === undefined || unit === undefined || unit < 1 || unit > 9)
    return NaN;
  return base + unit;
}

const unitWords: Record<string, Unit> = {
  minut: "minute",
  minuta: "minute",
  minute: "minute",
  minutu: "minute",
  minuti: "minute",
  minutima: "minute",
  min: "minute",
  m: "minute",
  sat: "hour",
  sata: "hour",
  satu: "hour",
  sati: "hour",
  satima: "hour",
  h: "hour",
  dan: "day",
  dana: "day",
  danu: "day",
  dani: "day",
  danima: "day",
  d: "day",
  nedelja: "week",
  nedelje: "week",
  nedelji: "week",
  nedelju: "week",
  sedmica: "week",
  sedmice: "week",
  sedmici: "week",
  sedmicu: "week",
  sedmicama: "week",
  ned: "week",
  sed: "week",
  mesec: "month",
  meseca: "month",
  mesecu: "month",
  meseci: "month",
  mesecima: "month",
  mes: "month",
  mo: "month",
  godina: "year",
  godine: "year",
  godini: "year",
  godinu: "year",
  godinama: "year",
  god: "year",
  g: "year",
};

export function number(text: string): number {
  const word = text.toLowerCase();
  const spelledOut = Object.hasOwn(quantities, word)
    ? quantities[word]
    : undefined;
  if (spelledOut !== undefined) return spelledOut;
  return /^-?\d+$/.test(text) ? Number(text) : NaN;
}

export function weekday(text: string): Weekday | undefined {
  const word = text.toLowerCase().replace(/\.$/, "");
  const index = dayNames.findIndex(
    (name, position) =>
      name === word || name.slice(0, 3) === word || dayGenitive[position] === word,
  );

  return weekdays[index];
}

export function month(text: string): number | undefined {
  const word = text.toLowerCase().replace(/\.$/, "");
  const index = monthNames.findIndex(
    (name, position) =>
      name === word ||
      name.slice(0, 3) === word ||
      monthGenitive[position] === word,
  );

  return index < 0 ? undefined : index + 1;
}

export function unit(text: string): Unit | undefined {
  const word = text.toLowerCase();
  return Object.hasOwn(unitWords, word) ? unitWords[word] : undefined;
}

export const holidayNames: Record<
  string,
  Extract<DateSpec, { kind: "holiday" }>["name"]
> = {
  božić: "christmas",
  badnjidan: "christmas-eve",
  badnjeveče: "christmas-eve",
  novagodina: "new-year",
  novogodišnjidan: "new-year",
  silvestrovo: "new-years-eve",
  novogodišnjanoć: "new-years-eve",
  noćveštica: "halloween",
  helovin: "halloween",
  haloween: "halloween",
  valentinovo: "valentines",
  danzaljubljenih: "valentines",
};
