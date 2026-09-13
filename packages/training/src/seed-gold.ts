import { mkdirSync, writeFileSync } from "node:fs";
import type {
  Clause,
  DateSpec,
  Label,
  Schedule,
  TimeSpec,
} from "../../core/src/types.ts";
import { tokenize } from "../../core/src/tokenizer.ts";

const gold = new URL("../data/gold/", import.meta.url);

const time = (hour: number, end?: number): TimeSpec => ({
  start: { hour, minute: 0 },
  ...(end === undefined ? {} : { end: { hour: end, minute: 0 } }),
});
const noon: TimeSpec = { start: { named: "noon" } };
const weekday = (
  ...days: Extract<DateSpec, { kind: "weekday" }>["days"]
): DateSpec => ({ kind: "weekday", days });
const schedule = (...clauses: Clause[]): Schedule => ({ clauses });

// Expectations are authored from the plans. This file does not call the compiler or resolver.
const adversarial = [
  {
    id: "adversarial-01",
    family: "multi-clause",
    text: "Ponedeljak 10popodne-12ujutru i subota nedelja 1popodne-8popodne",
    schedule: schedule(
      { date: weekday("MO"), time: time(22, 0) },
      { date: weekday("SA", "SU"), time: time(13, 20) },
    ),
  },
  {
    id: "adversarial-02",
    family: "recurrence-bounds",
    text: "svaki drugi utorak do dec",
    schedule: schedule({
      recurrence: {
        freq: "weekly",
        interval: 2,
        byDay: ["TU"],
        until: { kind: "calendar", month: 12 },
      },
    }),
  },
  {
    id: "adversarial-03",
    family: "shared-weekdays",
    text: "utorak i četvrtak u 3popodne",
    schedule: schedule({ date: weekday("TU", "TH"), time: time(15) }),
  },
  {
    id: "adversarial-04",
    family: "anchored-relative",
    text: "3 dana pre Božić",
    schedule: schedule({
      date: { kind: "holiday", name: "christmas" },
      shift: { amount: 3, unit: "day", direction: "before" },
    }),
  },
  {
    id: "adversarial-05",
    family: "relative-quantity",
    text: "1 dan pre",
    schedule: schedule({
      shift: { amount: 1, unit: "day", direction: "before" },
    }),
  },
  {
    id: "adversarial-06",
    family: "frequency-count",
    text: "2 puta na nedelju",
    schedule: schedule({
      recurrence: { freq: "weekly", interval: 1, timesPer: 2 },
    }),
  },
  {
    id: "adversarial-07",
    family: "exceptions",
    text: "svaki dan osim nedelja",
    schedule: schedule({
      recurrence: { freq: "daily", interval: 1, except: [weekday("SU")] },
    }),
  },
  {
    id: "adversarial-08",
    family: "ambiguous-range",
    text: "10popodne-12popodne",
    schedule: schedule({ time: time(22, 12) }),
    diagnostics: ["probable-typo-range"],
  },
  {
    id: "adversarial-09",
    family: "overnight",
    text: "10popodne-12ujutru",
    schedule: schedule({ time: time(22, 0) }),
  },
  {
    id: "adversarial-10",
    family: "weekday-range",
    text: "od 9 do 5 Pon-Pet",
    schedule: schedule({
      time: time(9, 17),
      recurrence: {
        freq: "weekly",
        interval: 1,
        byDay: ["MO", "TU", "WE", "TH", "FR"],
      },
    }),
    diagnostics: ["working-hours"],
  },
  {
    id: "adversarial-11",
    family: "named-clock",
    text: "od 9ujutru do podne",
    schedule: schedule({
      time: { start: { hour: 9, minute: 0 }, end: { named: "noon" } },
    }),
  },
  {
    id: "adversarial-12",
    family: "calendar-range",
    text: "26. jul - 22. avgust",
    schedule: schedule({
      date: {
        kind: "calendarRange",
        from: { month: 7, day: 26 },
        to: { month: 8, day: 22 },
      },
    }),
  },
  {
    id: "adversarial-13",
    family: "relative-window",
    text: "za 5 do 10 minuta",
    schedule: schedule({
      shift: { amount: 5, endAmount: 10, unit: "minute", direction: "after" },
    }),
  },
  {
    id: "adversarial-14",
    family: "day-part",
    text: "nedelja jutro",
    reference: "2026-09-13T12:00:00+06:00",
    schedule: schedule({
      date: weekday("SU"),
      time: { start: { part: "morning" } },
    }),
  },
  {
    id: "adversarial-15",
    family: "duration",
    text: "od sutra za 10 dana",
    schedule: schedule({
      date: { kind: "relativeDay", offset: 1 },
      duration: { amount: 10, unit: "day" },
    }),
  },
  {
    id: "adversarial-16",
    family: "modified-weekday",
    text: "sledeći ponedeljak u 2popodne",
    schedule: schedule({
      date: { kind: "weekday", days: ["MO"], modifier: "next" },
      time: time(14),
    }),
  },
  {
    id: "adversarial-17",
    family: "ordinal-date",
    text: "prvi petak sledeći mesec",
    schedule: schedule({
      date: {
        kind: "ordinalWeekday",
        ordinal: 1,
        day: "FR",
        of: { kind: "relativeUnit", unit: "month", modifier: "next" },
      },
    }),
  },
  {
    id: "adversarial-18",
    family: "relative-period",
    text: "ova nedelja",
    schedule: schedule({
      date: { kind: "relativeUnit", unit: "week", modifier: "this" },
    }),
  },
  {
    id: "adversarial-19",
    family: "weekly",
    text: "svaki ponedeljak u 9ujutru",
    schedule: schedule({
      recurrence: { freq: "weekly", interval: 1, byDay: ["MO"] },
      time: time(9),
    }),
  },
  {
    id: "adversarial-20",
    family: "yearly",
    text: "godišnje 26. mart",
    schedule: schedule({
      recurrence: {
        freq: "yearly",
        interval: 1,
        byMonthDay: [26],
        byMonth: [3],
      },
    }),
  },
  {
    id: "adversarial-21",
    family: "period-bound",
    text: "svaki 3 dana do kraj meseca",
    schedule: schedule({
      recurrence: {
        freq: "daily",
        interval: 3,
        until: {
          kind: "relativeUnit",
          unit: "month",
          modifier: "this",
          edge: "end",
        },
      },
    }),
  },
  {
    id: "adversarial-22",
    family: "start-bound",
    text: "svaki utorak počevši sledeći mesec",
    schedule: schedule({
      recurrence: {
        freq: "weekly",
        interval: 1,
        byDay: ["TU"],
        start: { kind: "relativeUnit", unit: "month", modifier: "next" },
      },
    }),
  },
  {
    id: "adversarial-23",
    family: "calendar-bound",
    text: "svaki ponedeljak, do 31. decembar",
    schedule: schedule({
      recurrence: {
        freq: "weekly",
        interval: 1,
        byDay: ["MO"],
        until: { kind: "calendar", month: 12, day: 31 },
      },
    }),
  },
  {
    id: "adversarial-24",
    family: "monthly-list",
    text: "1. i 15. svaki mesec",
    schedule: schedule({
      recurrence: { freq: "monthly", interval: 1, byMonthDay: [1, 15] },
    }),
  },
  {
    id: "adversarial-25",
    family: "shared-month-range",
    text: "jun 11-16, 2026",
    schedule: schedule({
      date: {
        kind: "calendarRange",
        from: { year: 2026, month: 6, day: 11 },
        to: { year: 2026, month: 6, day: 16 },
      },
    }),
  },
];

const userCases = [
  {
    id: "user-shorthand",
    family: "multi-clause",
    text: "Sub Ned 1popodne-8popodne Pon 10popodne-12ujutru",
    schedule: schedule(
      { date: weekday("SA", "SU"), time: time(13, 20) },
      { date: weekday("MO"), time: time(22, 0) },
    ),
  },
  {
    id: "user-relative",
    family: "relative-quantity",
    text: "jedan dan posle",
    schedule: schedule({
      shift: { amount: 1, unit: "day", direction: "after" },
    }),
  },
  {
    id: "user-long-groups",
    family: "multi-clause",
    text: "Ponedeljak od 8popodne do 10popodne, i zatim subota i nedelja od 1popodne do 10popodne",
    schedule: schedule(
      { date: weekday("MO"), time: time(20, 22) },
      { date: weekday("SA", "SU"), time: time(13, 22) },
    ),
  },
];

const annotations: {
  text: string;
  tags: string;
  clauses?: string[];
  schedule: Schedule;
}[] = [
  {
    text: "1 dan pre",
    tags: "NUM UNIT DIR_BEFORE",
    schedule: adversarial[4].schedule,
  },
  {
    text: "jedan dan posle",
    tags: "NUM UNIT DIR_AFTER",
    schedule: userCases[1].schedule,
  },
  {
    text: "za 90 minuta",
    tags: "DIR_AFTER NUM UNIT",
    schedule: schedule({
      shift: { amount: 90, unit: "minute", direction: "after" },
    }),
  },
  {
    text: "dva sata pre sutra u podne",
    tags: "NUM UNIT DIR_BEFORE REL_DAY O TIME_NAMED",
    schedule: schedule({
      date: { kind: "relativeDay", offset: 1 },
      time: noon,
      shift: { amount: 2, unit: "hour", direction: "before" },
    }),
  },
  {
    text: "Ponedeljak u 2:00 popodne",
    tags: "WEEKDAY O HOUR O MINUTE MERIDIEM",
    schedule: schedule({ date: weekday("MO"), time: time(14) }),
  },
  {
    text: "sledeći petak u podne",
    tags: "DEICTIC WEEKDAY O TIME_NAMED",
    schedule: schedule({
      date: { kind: "weekday", days: ["FR"], modifier: "next" },
      time: noon,
    }),
  },
  {
    text: "svaki drugi utorak do dec",
    tags: "RECUR NUM WEEKDAY BOUND_END MONTH",
    schedule: adversarial[1].schedule,
  },
  {
    text: "taj prvi ponedeljak u svaki mesec",
    tags: "O ORD WEEKDAY O RECUR UNIT",
    schedule: schedule({
      recurrence: {
        freq: "monthly",
        interval: 1,
        byDay: ["MO"],
        bySetPos: [1],
      },
    }),
  },
  {
    text: "poslednji petak u mesecu",
    tags: "ORD WEEKDAY O UNIT",
    schedule: schedule({
      recurrence: {
        freq: "monthly",
        interval: 1,
        byDay: ["FR"],
        bySetPos: [-1],
      },
    }),
  },
  {
    text: "prošli petak",
    tags: "DEICTIC WEEKDAY",
    schedule: schedule({
      date: { kind: "weekday", days: ["FR"], modifier: "last" },
    }),
  },
  {
    text: "svaki radni dan osim petak",
    tags: "RECUR DAYGROUP DAYGROUP EXCEPT WEEKDAY",
    schedule: schedule({
      recurrence: {
        freq: "weekly",
        interval: 1,
        byDay: ["MO", "TU", "WE", "TH", "FR"],
        except: [weekday("FR")],
      },
    }),
  },
  {
    text: "2 puta na nedelju",
    tags: "NUM TIMES O UNIT",
    schedule: adversarial[5].schedule,
  },
  {
    text: "3 puta na dan",
    tags: "NUM TIMES O UNIT",
    schedule: schedule({
      recurrence: { freq: "daily", interval: 1, timesPer: 3 },
    }),
  },
  {
    text: "svaka 2 nedelje na utorak",
    tags: "RECUR NUM UNIT O WEEKDAY",
    schedule: schedule({
      recurrence: { freq: "weekly", interval: 2, byDay: ["TU"] },
    }),
  },
  {
    text: "od 9 do 5 Pon-Pet",
    tags: "RANGE_START HOUR RANGE_END HOUR WEEKDAY RANGE_END WEEKDAY",
    schedule: adversarial[9].schedule,
  },
  {
    text: "između 9ujutru i podne",
    tags: "RANGE_START HOUR MERIDIEM RANGE_END TIME_NAMED",
    schedule: adversarial[10].schedule,
  },
  {
    text: "oktobar 1, 2027 u podne",
    tags: "MONTH DOM O YEAR O TIME_NAMED",
    schedule: schedule({
      date: { kind: "calendar", year: 2027, month: 10, day: 1 },
      time: noon,
    }),
  },
  {
    text: "2026-10-01",
    tags: "YEAR O MONTH O DOM",
    schedule: schedule({
      date: { kind: "calendar", year: 2026, month: 10, day: 1 },
    }),
  },
  {
    text: "jun 11-16, 2026",
    tags: "MONTH DOM RANGE_END DOM O YEAR",
    schedule: adversarial[24].schedule,
  },
  {
    text: "za 2 sata",
    tags: "DUR NUM UNIT",
    schedule: schedule({ duration: { amount: 2, unit: "hour" } }),
  },
  {
    text: "počevši od sutra za narednih 10 dana",
    tags: "BOUND_START O REL_DAY DUR DEICTIC NUM UNIT",
    schedule: adversarial[14].schedule,
  },
  {
    text: "3 dana pre Božić",
    tags: "NUM UNIT DIR_BEFORE HOLIDAY",
    schedule: adversarial[3].schedule,
  },
  {
    text: "9 do 5",
    tags: "HOUR RANGE_END HOUR",
    schedule: schedule({ time: time(9, 17) }),
  },
  {
    text: "svake godine u 26. mart",
    tags: "RECUR UNIT O DOM O MONTH",
    schedule: schedule({
      recurrence: {
        freq: "yearly",
        interval: 1,
        byMonthDay: [26],
        byMonth: [3],
      },
    }),
  },
  {
    text: "1. i 15. svaki mesec",
    tags: "DOM O O DOM O RECUR UNIT",
    schedule: adversarial[23].schedule,
  },
  {
    text: userCases[0].text,
    tags: "WEEKDAY WEEKDAY HOUR MERIDIEM RANGE_END HOUR MERIDIEM WEEKDAY HOUR MERIDIEM RANGE_END HOUR MERIDIEM",
    clauses: ["Pon"],
    schedule: userCases[0].schedule,
  },
];

const labeled = annotations.map((example, index) => {
  const tokens = tokenize(example.text);
  const labels = example.tags.split(" ") as Label[];
  const nonSpace = tokens.filter((token) => token.kind !== 3);
  if (nonSpace.length !== labels.length)
    throw new Error(
      `Annotation ${index + 1}: ${nonSpace.length} tokens but ${labels.length} labels (${example.text})`,
    );
  let labelIndex = 0;
  return {
    id: `oracle-${String(index + 1).padStart(3, "0")}`,
    text: example.text,
    tokens: tokens.map((token) => ({
      start: token.start,
      end: token.end,
      label: token.kind === 3 ? "O" : labels[labelIndex++],
      clauseStart:
        example.clauses?.some(
          (text) => token.start === example.text.indexOf(text),
        ) ?? false,
    })),
    schedule: example.schedule,
  };
});

mkdirSync(gold, { recursive: true });
for (const [name, records] of Object.entries({
  adversarial,
  "user-cases": userCases,
  labels: labeled,
})) {
  writeFileSync(
    new URL(`${name}.jsonl`, gold),
    records.map((record) => JSON.stringify(record)).join("\n") + "\n",
  );
}
console.log(
  `Wrote ${adversarial.length} adversarial cases, ${userCases.length} user cases, and ${labeled.length} hand-labeled oracle cases.`,
);
