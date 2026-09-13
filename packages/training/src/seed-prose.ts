import { writeFileSync } from "node:fs";
import type { Clause } from "../../core/src/types.ts";

const gold = new URL("../data/gold/", import.meta.url);

const at = (hour: number): Clause => ({ time: { start: { hour, minute: 0 } } });
const window = (start: number, end: number): Clause => ({
  time: { start: { hour: start, minute: 0 }, end: { hour: end, minute: 0 } },
});
const cases: [string, Clause | null][] = [
  ["biću odsutan između 5 i 6popodne", window(17, 18)],
  ["biću odsutan od 1ujutru do 5popodne", window(1, 17)],
  ["bićemo dostupni od 9ujutru do 5popodne", window(9, 17)],
  [
    "biblioteka je otvorena od 10ujutru do podne",
    { time: { start: { hour: 10, minute: 0 }, end: { named: "noon" } } },
  ],
  [
    "kancelarija je zatvorena od 10popodne do ponoć",
    { time: { start: { hour: 22, minute: 0 }, end: { named: "midnight" } } },
  ],
  ["možeš li postaviti alarm za 8ujutru", at(8)],
  [
    "molim te postavi alarm za 7:30ujutru",
    { time: { start: { hour: 7, minute: 30 } } },
  ],
  [
    "možeš li rezervisati sobu 24 za sutra u 3popodne",
    { date: { kind: "relativeDay", offset: 1 }, ...at(15) },
  ],
  [
    "sastanak je zakazan za petak u podne",
    {
      date: { kind: "weekday", days: ["FR"] },
      time: { start: { named: "noon" } },
    },
  ],
  [
    "intervju počinje ponedeljak u 2popodne",
    { date: { kind: "weekday", days: ["MO"] }, ...at(14) },
  ],
  [
    "naša klinika se otvara svaki radni dan u 8ujutru",
    {
      recurrence: {
        freq: "weekly",
        interval: 1,
        byDay: ["MO", "TU", "WE", "TH", "FR"],
      },
      ...at(8),
    },
  ],
  [
    "molim te zakaži poziv za svaki drugi utorak u 11ujutru",
    { recurrence: { freq: "weekly", interval: 2, byDay: ["TU"] }, ...at(11) },
  ],
  [
    "čas je zakazan za jun 12",
    { date: { kind: "calendar", month: 6, day: 12 } },
  ],
  [
    "vratiću se kroz dva sata",
    { shift: { amount: 2, unit: "hour", direction: "after" } },
  ],
  [
    "hteo bih da zakažem sastanak za sutra",
    { date: { kind: "relativeDay", offset: 1 } },
  ],
  [
    "molim te podseti me na Božić",
    { date: { kind: "holiday", name: "christmas" } },
  ],
  [
    "sastanak je zakazan za sledeći mesec",
    { date: { kind: "relativeUnit", unit: "month", modifier: "next" } },
  ],
  [
    "molim te rezerviši sobu 17 od ponedeljak do sreda",
    { date: { kind: "weekdayRange", from: "MO", to: "WE" } },
  ],
  ["biblioteka je zatvorena zbog popravke.", null],
  ["molim te postavi alarm za eksperiment.", null],
  ["možeš li rezervisati sobu 24 za tim?", null],
  ["intervju je o našem drugom proizvodu.", null],
  ["biću odsutan iz kancelarije zbog privatnih razloga.", null],
  ["naša klinika je otvorena za pitanja.", null],
];

writeFileSync(
  new URL("prose.jsonl", gold),
  cases
    .flatMap(([text, clause], index) => {
      const variants = {
        authored: text,
        lowercase: text.toLowerCase(),
        uppercase: text.toUpperCase(),
      };
      return Object.entries(variants).map(([variant, text]) =>
        JSON.stringify({
          id: `prose-${String(index + 1).padStart(3, "0")}-${variant}`,
          family: clause ? "prose-carrier" : "prose-negative",
          variant,
          text,
          schedule: clause ? { clauses: [clause] } : null,
        }),
      );
    })
    .join("\n") + "\n",
);
console.log(
  `Authored ${cases.length} prose checks with ${cases.length * 2} derived casing variants.`,
);
