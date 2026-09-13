import type { ParseResult } from "gpu-time";

export const example = "Svaki ponedeljak od 8popodne do 10popodne";

// The code block hardcodes `example`'s output, so the demo carries its own.
export const demoDefault = "zakaži večeru za 2. oktobar u osam popodne";

export type Kind = "date" | "time" | "repeat" | "duration";
export interface Part {
  text: string;
  kind?: Kind;
}

export const kinds: { kind: Kind; label: string }[] = [
  { kind: "date", label: "Dan ili datum" },
  { kind: "time", label: "Vreme na satu" },
  { kind: "repeat", label: "Ponavljanje" },
  { kind: "duration", label: "Trajanje" },
];

export const examples: { use: string; text: string }[] = [
  { use: "Podsetnik", text: "sutra u 9ujutru" },
  {
    use: "Večera, u sred rečenice",
    text: "zakaži večeru za 2. oktobar u osam popodne",
  },
  { use: "Sastanak", text: "svaki radni dan u devet ujutru" },
  { use: "Noćna smena", text: "petak u 10popodne do subota u 2ujutru" },
  { use: "Putovanje", text: "od 4. septembar do 8. septembar" },
  { use: "Plata", text: "poslednji petak meseca" },
  { use: "Dvonedeljni ciklus", text: "svaki drugi petak u podne" },
  { use: "Odbrojavanje", text: "za 20 minuta za pola sata" },
];

const boundary = "(?<![\\p{L}\\d])";
const boundaryEnd = "(?![\\p{L}\\d])";
const hour =
  "jedan|dva|tri|četiri|pet|šest|sedam|osam|devet|deset|jedanaest|dvanaest";
const meridiem = "ujutru|izjutra|popodne|uveče|uvece|noću|nocu";

const patterns: [Kind, RegExp][] = [
  [
    "repeat",
    new RegExp(
      `${boundary}(svaki drugi|svaki|svake|svakog|poslednji|radni dan|radni dani|vikend|vikendi|dnevno|svakodnevno|nedeljno|sedmično|sedmicno|dvonedeljno|petnaestodnevno|mesečno|mesecno|godišnje|godisnje|osim)${boundaryEnd}`,
      "giu",
    ),
  ],
  [
    "duration",
    new RegExp(
      `${boundary}(za|kroz)\\s+(pola|četvrt|jedan|jedna|\\d+(\\.\\d+)?)\\s*(i\\s+po\\s+)?(sati?|sata|minuta?|minut|dana?|dan|nedelj[ae]|sedmic[ae]|mesec[a]?|godin[ae])${boundaryEnd}`,
      "giu",
    ),
  ],
  [
    "time",
    new RegExp(
      `${boundary}(od\\s+)?(\\d{1,2}(:\\d{2})?|${hour})\\s*(${meridiem})?\\s*(-|–|do|pre)\\s*(\\d{1,2}(:\\d{2})?|${hour})\\s*(${meridiem})?${boundaryEnd}`,
      "giu",
    ),
  ],
  [
    "time",
    new RegExp(
      `${boundary}(u\\s+)?(\\d{1,2}(:\\d{2})?|${hour})\\s*(${meridiem})${boundaryEnd}|${boundary}(podne|ponoć|ponoc|jutro|popodne|veče|vece|noć|noc)${boundaryEnd}|${boundary}(pola|četvrt)\\s+(do|pre)\\s+\\S+`,
      "giu",
    ),
  ],
  [
    "date",
    new RegExp(
      `${boundary}(ponedeljak|utorak|sreda|četvrtak|petak|subota|nedelja|pon|uto|sre|čet|pet|sub|ned)${boundaryEnd}`,
      "giu",
    ),
  ],
  [
    "date",
    new RegExp(
      `${boundary}(?:\\d{1,2}\\.\\s*)?(januar|februar|mart|april|maj|jun|jul|avgust|septembar|oktobar|novembar|decembar|jan|feb|mar|apr|avg|sep|okt|nov|dec)[\\p{L}]*\\.?\\s*\\d{0,2}\\.?${boundaryEnd}`,
      "giu",
    ),
  ],
  [
    "date",
    new RegExp(
      `${boundary}(danas|sutra|večeras|veceras|noćas|nocas|juče|jučer|juce|prekosutra|prekjuče|prekjuce)${boundaryEnd}|${boundary}(sledeć[ai]|sledeca|naredn[ai]|prošl[ai]|proslim|prethodn[ai]|ova[j]?|ov[oa])\\s+\\S+|${boundary}\\d{1,2}\\.${boundaryEnd}|${boundary}\\d{1,2}\\/\\d{1,2}(\\/\\d{2,4})?${boundaryEnd}`,
      "giu",
    ),
  ],
];

export function highlight(text: string): Part[] {
  const claims: { start: number; end: number; kind: Kind }[] = [];
  for (const [kind, pattern] of patterns) {
    for (const match of text.matchAll(pattern)) {
      const start = match.index;
      const end = start + match[0].length;
      if (claims.some((claim) => start < claim.end && end > claim.start))
        continue;
      claims.push({ start, end, kind });
    }
  }
  claims.sort((first, second) => first.start - second.start);

  const parts: Part[] = [];
  let at = 0;
  for (const claim of claims) {
    if (claim.start > at) parts.push({ text: text.slice(at, claim.start) });
    parts.push({ text: text.slice(claim.start, claim.end), kind: claim.kind });
    at = claim.end;
  }
  if (at < text.length) parts.push({ text: text.slice(at) });
  return parts;
}

export function format(result: ParseResult, reference: Date, timeZone: string) {
  const dateFormat = new Intl.DateTimeFormat("sr-Latn-RS", {
    timeZone,
    weekday: "short",
    month: "short",
    day: "numeric",
    year: "numeric",
  });
  const timeFormat = new Intl.DateTimeFormat("sr-Latn-RS", {
    timeZone,
    hour: "numeric",
    minute: "2-digit",
  });
  const status = result.diagnostics.length
    ? result.diagnostics.map((diagnostic) => diagnostic.message).join(" ")
    : result.occurrences.length
      ? result.truncated
        ? `Sledeća ${result.occurrences.length} termina`
        : "Rezultat"
      : "Nema pronađenih datuma. Probajte datum ili vremenski period.";

  const rows = result.occurrences.map((occurrence) => {
    const start = new Date(occurrence.start);
    const end = occurrence.end ? new Date(occurrence.end) : start;
    let time: string;
    if (!occurrence.end) {
      time = occurrence.allDay ? "Ceo dan" : timeFormat.format(start);
    } else if (occurrence.allDay) {
      // Date-only ranges have an exclusive end at the next midnight.
      const lastDay = new Date(end.getTime() - 1);
      time =
        dateFormat.format(start) === dateFormat.format(lastDay)
          ? "Ceo dan"
          : `Do ${dateFormat.format(lastDay)} · ceo dan`;
    } else {
      const endDate =
        dateFormat.format(start) === dateFormat.format(end)
          ? ""
          : `${dateFormat.format(end)}, `;
      time = `${timeFormat.format(start)} – ${endDate}${timeFormat.format(end)}`;
    }
    return { date: dateFormat.format(start), time };
  });

  return {
    status,
    rows,
    context: `U odnosu na ${dateFormat.format(reference)} · ${timeZone}`,
  };
}
