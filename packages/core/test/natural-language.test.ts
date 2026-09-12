import { afterAll, beforeAll, expect, it } from "vitest";
import { defineParser } from "../src/index.js";
import { resolve } from "../src/resolve.js";
import { RRule } from "rrule";

const context = {
  reference: "2026-09-09T00:00:00Z",
  timeZone: "UTC",
  limit: 6,
};
let parser: Awaited<ReturnType<typeof defineParser>>;
beforeAll(async () => {
  parser = await defineParser({ backend: "cpu" });
});
afterAll(() => parser.dispose());

it.each([
  ["postavi alarm za osam i petnaest", "2026-09-09T08:15:00+00:00"],
  ["deset i trideset pet popodne", "2026-09-09T22:35:00+00:00"],
  ["sedam", "2026-09-09T07:00:00+00:00"],
  ["sedam i po", "2026-09-09T07:30:00+00:00"],
  ["devet i petnaest", "2026-09-09T09:15:00+00:00"],
  ["četvrt do šest", "2026-09-09T05:45:00+00:00"],
  ["četvrt do dvanaest ujutru", "2026-09-09T23:45:00+00:00"],
  ["osam ujutru", "2026-09-09T08:00:00+00:00"],
  ["šest uveče", "2026-09-09T18:00:00+00:00"],
  ["deset noću", "2026-09-09T22:00:00+00:00"],
  ["dvanaest noću", "2026-09-09T00:00:00+00:00"],
  ["za dva dana i šest sati", "2026-09-11T06:00:00+00:00"],
  ["za pola sata", "2026-09-09T00:30:00+00:00"],
  ["biću ovde 15.", "2026-09-15T00:00:00+00:00"],
  ["zakaži večeru za 2. oktobar u osam popodne", "2026-10-02T20:00:00+00:00"],
  ["prvi petak sledeći mesec", "2026-10-02T00:00:00+00:00"],
  ["21/04/2016", "2016-04-21T00:00:00+00:00"],
  ["04/21/2016", "2016-04-21T00:00:00+00:00"],
])("resolves %s", async (text, start) => {
  const result = await parser.parse(text, context);
  expect(
    result.diagnostics.filter((value) => value.severity === "error"),
  ).toEqual([]);
  expect(result.occurrences).toHaveLength(1);
  expect(result.occurrences[0].start).toBe(start);
});

it.each([
  [
    "za tri sata i trideset minuta",
    "2026-09-09T00:00:00+00:00",
    "2026-09-09T03:30:00+00:00",
  ],
  [
    "za sat i po",
    "2026-09-09T00:00:00+00:00",
    "2026-09-09T01:30:00+00:00",
  ],
  ["za 2.5 sata", "2026-09-09T00:00:00+00:00", "2026-09-09T02:30:00+00:00"],
  [
    "od 4. septembar do 8. septembar",
    "2026-09-04T00:00:00+00:00",
    "2026-09-09T00:00:00+00:00",
  ],
  [
    "petak 11. do utorak 15.",
    "2026-09-11T00:00:00+00:00",
    "2026-09-16T00:00:00+00:00",
  ],
  [
    "petak u 10popodne do subota u 2ujutru",
    "2026-09-11T22:00:00+00:00",
    "2026-09-12T02:00:00+00:00",
  ],
  ["ovaj septembar", "2026-09-01T00:00:00+00:00", "2026-10-01T00:00:00+00:00"],
  ["sledeći mesec", "2026-10-01T00:00:00+00:00", "2026-11-01T00:00:00+00:00"],
  [
    "prva nedelja od oktobar",
    "2026-10-01T00:00:00+00:00",
    "2026-10-08T00:00:00+00:00",
  ],
])("resolves the complete range in %s", async (text, start, end) => {
  const result = await parser.parse(text, context);
  expect(
    result.diagnostics.filter((value) => value.severity === "error"),
  ).toEqual([]);
  expect(result.occurrences).toHaveLength(1);
  expect(result.occurrences[0]).toMatchObject({ start, end });
});

it.each([
  ["svaki drugi petak", ["2026-09-11", "2026-09-25", "2026-10-09"]],
  ["svaki drugi utorak", ["2026-09-15", "2026-09-29", "2026-10-13"]],
  ["poslednji petak meseca", ["2026-09-25", "2026-10-30", "2026-11-27"]],
  [
    "svaki ponedeljak osim prvi ponedeljak meseca",
    ["2026-09-14", "2026-09-21", "2026-09-28", "2026-10-12"],
  ],
])("expands %s", async (text, dates) => {
  const result = await parser.parse(text, context);
  expect(
    result.diagnostics.filter((value) => value.severity === "error"),
  ).toEqual([]);
  expect(
    result.occurrences
      .slice(0, dates.length)
      .map((value) => value.start.slice(0, 10)),
  ).toEqual(dates);
  expect(result.rrules).toHaveLength(1);
});

it("shares a weekday schedule across two clock points", async () => {
  const result = await parser.parse(
    "svaki radni dan u devet ujutru i pet popodne",
    context,
  );
  expect(result.occurrences.slice(0, 4).map((value) => value.start)).toEqual([
    "2026-09-09T09:00:00+00:00",
    "2026-09-09T17:00:00+00:00",
    "2026-09-10T09:00:00+00:00",
    "2026-09-10T17:00:00+00:00",
  ]);
  expect(result.rrules).toHaveLength(2);
});

it("keeps a weekday recurrence's inclusive end bound", async () => {
  const result = await parser.parse("svaki radni dan u devet do 20. decembar", {
    ...context,
    reference: "2026-12-17T00:00:00Z",
  });
  expect(result.occurrences.map((value) => value.start)).toEqual([
    "2026-12-17T09:00:00+00:00",
    "2026-12-18T09:00:00+00:00",
  ]);
});

it("applies calendar days before elapsed hours across DST", () => {
  const result = resolve(
    {
      clauses: [
        {
          shift: {
            amount: 1,
            unit: "day",
            components: [{ amount: 2, unit: "hour" }],
            direction: "after",
          },
        },
      ],
    },
    { reference: "2026-03-07T12:00:00-05:00", timeZone: "America/New_York" },
  );
  expect(result.occurrences[0].start).toBe("2026-03-08T14:00:00-04:00");
});

it("exports repeating monthly exclusions beyond the preview", () => {
  const result = resolve(
    {
      clauses: [
        {
          recurrence: {
            freq: "weekly",
            interval: 1,
            byDay: ["MO"],
            except: [
              {
                kind: "ordinalWeekday",
                ordinal: 1,
                day: "MO",
                of: { kind: "calendar" },
                recurring: true,
              },
            ],
          },
        },
      ],
    },
    context,
  );
  const line = result.rrules[0]
    .split("\n")
    .find((value) => value.startsWith("RRULE:"))!;
  const rule = new RRule({
    ...RRule.parseString(line),
    dtstart: new Date("2026-09-14T00:00:00Z"),
  });
  const dates = rule
    .between(new Date("2026-10-01Z"), new Date("2026-11-01Z"))
    .map((value) => value.toISOString().slice(0, 10));
  expect(dates).toEqual(["2026-10-12", "2026-10-19", "2026-10-26"]);
});

it("uses the caller's date order for ambiguous numeric dates", async () => {
  const dayFirst = await defineParser({ backend: "cpu", dateOrder: "DMY" });
  const monthFirst = await defineParser({ backend: "cpu", dateOrder: "MDY" });
  try {
    const european = await dayFirst.parse("03/04/2027", context);
    const american = await monthFirst.parse("03/04/2027", context);
    expect(european.occurrences[0].start).toBe("2027-04-03T00:00:00+00:00");
    expect(american.occurrences[0].start).toBe("2027-03-04T00:00:00+00:00");
  } finally {
    dayFirst.dispose();
    monthFirst.dispose();
  }
});

it("keeps the original compact multi-day input", async () => {
  const result = await parser.parse(
    "Sub Ned 1popodne-8popodne Pon 10popodne-12ujutru",
    context,
  );
  expect(result.occurrences.map(({ start, end }) => [start, end])).toEqual([
    ["2026-09-12T13:00:00+00:00", "2026-09-12T20:00:00+00:00"],
    ["2026-09-13T13:00:00+00:00", "2026-09-13T20:00:00+00:00"],
    ["2026-09-14T22:00:00+00:00", "2026-09-15T00:00:00+00:00"],
  ]);
});

it("resolves explicit cross-date clocks through a DST change", () => {
  const result = resolve(
    {
      clauses: [
        {
          date: { kind: "calendar", year: 2026, month: 3, day: 7 },
          endDate: { kind: "calendar", year: 2026, month: 3, day: 8 },
          time: { start: { hour: 22, minute: 0 }, end: { hour: 4, minute: 0 } },
        },
      ],
    },
    { ...context, timeZone: "America/New_York" },
  );
  expect(result.occurrences[0]).toMatchObject({
    start: "2026-03-07T22:00:00-05:00",
    end: "2026-03-08T04:00:00-04:00",
  });
});

it.each([
  ["postavi alarm za šest i petnaest popodne", "18:15:00"],
  ["podseti me u jedanaest i trideset pet", "11:35:00"],
  ["zakaži poziv za šest i po popodne", "18:30:00"],
])("understands varied wording: %s", async (text, clock) => {
  const result = await parser.parse(text, context);
  expect(result.occurrences).toHaveLength(1);
  expect(result.occurrences[0].start.slice(11, 19)).toBe(clock);
});

it.each(["-", "do"])(
  "allows equal clocks on different explicit dates (%s)",
  async (separator) => {
    const result = await parser.parse(
      `17. avgust 2013. 2popodne ${separator} 19. avgust 2013. 2popodne`,
      { ...context, timeZone: "Asia/Dhaka" },
    );
    expect(
      result.diagnostics.filter((value) => value.severity === "error"),
    ).toEqual([]);
    expect(result.occurrences).toEqual([
      {
        start: "2013-08-17T14:00:00+06:00",
        end: "2013-08-19T14:00:00+06:00",
        allDay: false,
      },
    ]);
  },
);

it.each([17, 16])(
  "rejects an equal or reversed full datetime range ending August %i",
  async (day) => {
    const result = await parser.parse(
      `17. avgust 2013. 2popodne - ${day}. avgust 2013. 2popodne`,
      context,
    );
    expect(result.occurrences).toEqual([]);
    expect(result.diagnostics.some((value) => value.severity === "error")).toBe(
      true,
    );
  },
);

it("compares complete instants for equal clocks across a DST transition", () => {
  const result = resolve(
    {
      clauses: [
        {
          date: { kind: "calendar", year: 2026, month: 3, day: 7 },
          endDate: { kind: "calendar", year: 2026, month: 3, day: 8 },
          time: {
            start: { hour: 14, minute: 0 },
            end: { hour: 14, minute: 0 },
          },
        },
      ],
    },
    { ...context, timeZone: "America/New_York" },
  );
  const { start, end } = result.occurrences[0];
  expect(start).toBe("2026-03-07T14:00:00-05:00");
  expect(end).toBe("2026-03-08T14:00:00-04:00");
  expect(Date.parse(end!) - Date.parse(start)).toBe(23 * 3600000);
});
