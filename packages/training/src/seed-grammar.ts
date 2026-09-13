import { writeFileSync } from "node:fs";
import type {
  Clause,
  DateSpec,
  Recurrence,
  Schedule,
  TimeSpec,
  Unit,
  Weekday,
} from "../../core/src/types.ts";

const gold = new URL("../data/gold/", import.meta.url);

const clock = (hour: number, minute = 0): TimeSpec => ({
  start: { hour, minute },
});
const named = (name: "noon" | "midnight"): TimeSpec => ({
  start: { named: name },
});
const window = (start: number, end: number): TimeSpec => ({
  ...clock(start),
  end: { hour: end, minute: 0 },
});
const weekday = (...days: Weekday[]): DateSpec => ({ kind: "weekday", days });
const relative = (offset: number): DateSpec => ({
  kind: "relativeDay",
  offset,
});
const shift = (
  amount: number,
  unit: Unit,
  direction: "before" | "after",
): Clause => ({ shift: { amount, unit, direction } });
const recurrence = (
  freq: Recurrence["freq"],
  extra: Partial<Recurrence> = {},
): Clause => ({ recurrence: { freq, interval: 1, ...extra } });
const calendar = (month: number, day?: number, year?: number): DateSpec => ({
  kind: "calendar",
  month,
  ...(day === undefined ? {} : { day }),
  ...(year === undefined ? {} : { year }),
});
const cases: {
  id: string;
  family: string;
  text: string;
  schedule: Schedule;
}[] = [];
function example(family: string, text: string, ...clauses: Clause[]) {
  cases.push({
    id: `grammar-${String(cases.length + 1).padStart(3, "0")}`,
    family,
    text,
    schedule: { clauses },
  });
}

// Explicit expectations from plan/002, authored without calling any parser.
example("now-relative-day", "sada", { date: { kind: "now" } });
example("now-relative-day", "danas", { date: relative(0) });
example("now-relative-day", "večeras", { date: relative(0) });
example("now-relative-day", "sutra", { date: relative(1) });
example("now-relative-day", "juče", { date: relative(-1) });
example("now-relative-day", "prekosutra", { date: relative(2) });
example("relative-quantity", "1 dan pre", shift(1, "day", "before"));
example("relative-quantity", "10 dana posle", shift(10, "day", "after"));
example("relative-quantity", "kroz 90 minuta", shift(90, "minute", "after"));
example("relative-quantity", "3 nedelje od sada", {
  ...shift(3, "week", "after"),
  date: { kind: "now" },
});
example("relative-quantity", "dva meseca kasnije", shift(2, "month", "after"));
example("relative-quantity", "pre 5 dana", shift(5, "day", "before"));
example("anchored-relative", "2 dana pre petak", {
  ...shift(2, "day", "before"),
  date: weekday("FR"),
});
example("anchored-relative", "dva sata pre sutra u podne", {
  ...shift(2, "hour", "before"),
  date: relative(1),
  time: named("noon"),
});
example("anchored-relative", "3 dana posle 1. oktobar", {
  ...shift(3, "day", "after"),
  date: calendar(10, 1),
});
example("anchored-relative", "jedna nedelja pre Božić", {
  ...shift(1, "week", "before"),
  date: { kind: "holiday", name: "christmas" },
});
example("relative-unit", "prošli mesec", {
  date: { kind: "relativeUnit", unit: "month", modifier: "last" },
});
example("relative-unit", "ovaj vikend", {
  date: { kind: "dayGroup", group: "weekend", modifier: "this" },
});
example("relative-unit", "kroz jedna godina", shift(1, "year", "after"));
example("relative-unit", "kraj sledeći mesec", {
  date: { kind: "relativeUnit", unit: "month", modifier: "next", edge: "end" },
});
example("weekday", "Ponedeljak", { date: weekday("MO") });
example("weekday", "Pon", { date: weekday("MO") });
example("weekday", "sledeći petak", {
  date: { kind: "weekday", days: ["FR"], modifier: "next" },
});
example("weekday", "ovaj ponedeljak", {
  date: { kind: "weekday", days: ["MO"], modifier: "this" },
});
example("weekday", "prošli utorak", {
  date: { kind: "weekday", days: ["TU"], modifier: "last" },
});
example("weekday", "ponedeljak i sreda", { date: weekday("MO", "WE") });
example(
  "day-group",
  "radni dani",
  recurrence("weekly", { byDay: ["MO", "TU", "WE", "TH", "FR"] }),
);
example("day-group", "vikendi", recurrence("weekly", { byDay: ["SA", "SU"] }));
example(
  "day-group",
  "svaki radni dan",
  recurrence("weekly", { byDay: ["MO", "TU", "WE", "TH", "FR"] }),
);
example(
  "day-group",
  "Pon-Pet",
  recurrence("weekly", { byDay: ["MO", "TU", "WE", "TH", "FR"] }),
);
example("clock", "2popodne", { time: clock(14) });
example("clock", "14:00", { time: clock(14) });
example("clock", "2:30popodne", { time: clock(14, 30) });
example("clock", "podne", { time: named("noon") });
example("clock", "ponoć", { time: named("midnight") });
example("day-part", "jutro", { time: { start: { part: "morning" } } });
example("day-part", "popodne", { time: { start: { part: "afternoon" } } });
example("day-part", "veče", { time: { start: { part: "evening" } } });
example("day-part", "noć", { time: { start: { part: "night" } } });
example("day-part", "ponedeljak veče", {
  date: weekday("MO"),
  time: { start: { part: "evening" } },
});
example("day-part", "sutra jutro", {
  date: relative(1),
  time: { start: { part: "morning" } },
});
example("explicit-date", "1. oktobar", { date: calendar(10, 1) });
example("explicit-date", "oktobar 1", { date: calendar(10, 1) });
example("explicit-date", "01/10", { date: calendar(10, 1) });
example("explicit-date", "2026-10-01", { date: calendar(10, 1, 2026) });
example("explicit-date", "1. oktobar 2027 u podne", {
  date: calendar(10, 1, 2027),
  time: named("noon"),
});
example("time-window", "10popodne-12ujutru", { time: window(22, 0) });
example("time-window", "od 8 do 10popodne", { time: window(20, 22) });
example("time-window", "između 9ujutru i podne", {
  time: { start: { hour: 9, minute: 0 }, end: { named: "noon" } },
});
example("time-window", "ponedeljak 1popodne-8popodne", {
  date: weekday("MO"),
  time: window(13, 20),
});
example("time-window", "9 do 5", { time: window(9, 17) });
example("date-range", "jun 11-16", {
  date: {
    kind: "calendarRange",
    from: { month: 6, day: 11 },
    to: { month: 6, day: 16 },
  },
});
example("date-range", "26. jul - 22. avgust", {
  date: {
    kind: "calendarRange",
    from: { month: 7, day: 26 },
    to: { month: 8, day: 22 },
  },
});
example("date-range", "od ponedeljak do sreda", {
  date: { kind: "weekdayRange", from: "MO", to: "WE" },
});
example("duration", "za 2 sata", { duration: { amount: 2, unit: "hour" } });
example("duration", "za 90 minuta", {
  duration: { amount: 90, unit: "minute" },
});
example("duration", "za 10 dana", {
  duration: { amount: 10, unit: "day" },
});
example(
  "multi-clause",
  "ponedeljak 10popodne-12ujutru i subota nedelja 1popodne-8popodne",
  { date: weekday("MO"), time: window(22, 0) },
  { date: weekday("SA", "SU"), time: window(13, 20) },
);
example(
  "multi-clause",
  "pon u 9, sre u 10, pet u 11",
  { date: weekday("MO"), time: clock(9) },
  { date: weekday("WE"), time: clock(10) },
  { date: weekday("FR"), time: clock(11) },
);
example("recurrence", "svaki ponedeljak u 8popodne", {
  ...recurrence("weekly", { byDay: ["MO"] }),
  time: clock(20),
});
example("recurrence", "svaki utorak", recurrence("weekly", { byDay: ["TU"] }));
example("recurrence", "dnevno u podne", {
  ...recurrence("daily"),
  time: named("noon"),
});
example("recurrence", "nedeljno", recurrence("weekly"));
example(
  "recurrence",
  "svaki drugi petak",
  recurrence("weekly", { interval: 2, byDay: ["FR"] }),
);
example("recurrence", "2 puta na nedelju", recurrence("weekly", { timesPer: 2 }));
example("recurrence", "3 puta na dan", recurrence("daily", { timesPer: 3 }));
example(
  "monthly-yearly",
  "svaki mesec 31.",
  recurrence("monthly", { byMonthDay: [31] }),
);
example(
  "monthly-yearly",
  "prvi ponedeljak meseca",
  recurrence("monthly", { byDay: ["MO"], bySetPos: [1] }),
);
example(
  "monthly-yearly",
  "poslednji petak meseca",
  recurrence("monthly", { byDay: ["FR"], bySetPos: [-1] }),
);
example(
  "monthly-yearly",
  "1. i 15. svaki mesec",
  recurrence("monthly", { byMonthDay: [1, 15] }),
);
example(
  "monthly-yearly",
  "godišnje 26. mart",
  recurrence("yearly", { byMonth: [3], byMonthDay: [26] }),
);
example("monthly-yearly", "godišnje", recurrence("yearly"));
example(
  "bounds",
  "svaki ponedeljak počevši od 1. oktobar",
  recurrence("weekly", { byDay: ["MO"], start: calendar(10, 1) }),
);
example(
  "bounds",
  "svaki ponedeljak, do 31. decembar",
  recurrence("weekly", { byDay: ["MO"], until: calendar(12, 31) }),
);
example(
  "bounds",
  "svaki utorak do dec",
  recurrence("weekly", { byDay: ["TU"], until: calendar(12) }),
);
example(
  "bounds",
  "svaki dan do petak",
  recurrence("daily", { until: weekday("FR") }),
);
example(
  "bounds",
  "svaki ponedeljak 6 puta",
  recurrence("weekly", { byDay: ["MO"], count: 6 }),
);
example(
  "bounds",
  "svaki ponedeljak za 10 nedelja",
  recurrence("weekly", { byDay: ["MO"], span: { amount: 10, unit: "week" } }),
);
example(
  "exceptions",
  "svaki radni dan osim petak",
  recurrence("weekly", {
    byDay: ["MO", "TU", "WE", "TH", "FR"],
    except: [weekday("FR")],
  }),
);
example(
  "exceptions",
  "svaki dan osim nedelja",
  recurrence("daily", { except: [weekday("SU")] }),
);
example("prose", "podseti me da nazovem Milana u ponedeljak u 2popodne", {
  date: weekday("MO"),
  time: clock(14),
});
example(
  "prose",
  "sastanak je svaki drugi utorak do dec",
  recurrence("weekly", { byDay: ["TU"], interval: 2, until: calendar(12) }),
);
example("prose", "krajnji rok: 3 dana pre Božić", {
  ...shift(3, "day", "before"),
  date: { kind: "holiday", name: "christmas" },
});
example("holiday", "Božić", {
  date: { kind: "holiday", name: "christmas" },
});
example("holiday", "Badnje veče", {
  date: { kind: "holiday", name: "christmas-eve" },
});
example("holiday", "Nova godina", {
  date: { kind: "holiday", name: "new-year" },
});
example("holiday", "Noć veštica", {
  date: { kind: "holiday", name: "halloween" },
});
example("holiday", "Valentinovo", {
  date: { kind: "holiday", name: "valentines" },
});

example("explicit-date", "šesti oktobar", { date: calendar(10, 6) });
example("explicit-date", "dvanaesti oktobar", { date: calendar(10, 12) });
example("explicit-date", "deveti februar 2028.", {
  date: calendar(2, 9, 2028),
});
example("clock", "dvanaest popodne", { time: clock(12) });
example("clock", "jedanaest ujutru", { time: clock(11) });
example("time-window", "9ujutru do 5", { time: window(9, 17) });
example("time-window", "10 do 2ujutru", { time: window(22, 2) });
example("time-window", "8 do ponoć", {
  time: { start: { hour: 20, minute: 0 }, end: { named: "midnight" } },
});
example(
  "relative-quantity",
  "dvanaest minuta posle",
  shift(12, "minute", "after"),
);
example(
  "monthly-yearly",
  "svaki mesec sedmi",
  recurrence("monthly", { byMonthDay: [7] }),
);
example("holiday", "Badnje veče u podne", {
  date: { kind: "holiday", name: "christmas-eve" },
  time: named("noon"),
});

example("clock-period", "dva popodne", { time: clock(14) });
example("clock-period", "pet ujutru", { time: clock(5) });
example("clock-period", "sedam uveče", { time: clock(19) });
example("clock-period", "dvanaest ujutru", { time: clock(0) });
example("clock-period", "dvanaest popodne", { time: clock(12) });
example("clock-period", "2:30 popodne", { time: clock(14, 30) });
example("clock-period", "sutra u osam ujutru", {
  date: relative(1),
  time: clock(8),
});
example("clock-period", "svaki ponedeljak u šest uveče", {
  ...recurrence("weekly", { byDay: ["MO"] }),
  time: clock(18),
});
example("clock-period", "od 5 do 7 uveče", { time: window(17, 19) });
example("clock-period", "od 9 ujutru do 5 popodne", {
  time: window(9, 17),
});

writeFileSync(
  new URL("grammar.jsonl", gold),
  cases.map((value) => JSON.stringify(value)).join("\n") + "\n",
);
console.log(
  `Authored ${cases.length} core grammar cases across ${new Set(cases.map((value) => value.family)).size} families.`,
);
