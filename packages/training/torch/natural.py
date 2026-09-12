"""Natural phrasing with independently constructed schedules and role supervision.

Reference dates and timezones never enter these examples. Reserved wording uses
separate sentence frames; quantities, dates and combinations vary within frames.
"""

from __future__ import annotations
import random
from copy import deepcopy
import background
from semantic import (
    DAYS,
    DAY_CODES,
    MONTHS,
    Specification,
    unit_form,
    unit_gender,
    modifier_word,
    weekday_gender,
    ordinal_feminine,
)

ONES = (
    "nula jedan dva tri četiri pet šest sedam osam devet deset jedanaest "
    "dvanaest trinaest četrnaest petnaest šesnaest sedamnaest osamnaest devetnaest"
).split()
TENS = {20: "dvadeset", 30: "trideset", 40: "četrdeset", 50: "pedeset"}
# am -> ujutru/izjutra, pm -> popodne/uveče/uvece per the compiler's meridiem
# adverb scheme; these are the single fixed forms used wherever the internal
# "am"/"pm" value itself would otherwise leak out as display text.
MERIDIEM_WORDS = {"am": "ujutru", "pm": "popodne"}
FAMILIES = [
    "spoken-clock",
    "fraction-clock",
    "qualified-clock",
    "compound-duration",
    "compound-shift",
    "fraction-duration",
    "prose-date",
    "numeric-date",
    "date-range",
    "datetime-range",
    "month-period",
    "month-week",
    "recurrence",
    "recurrence-bound",
    "monthly-exception",
    "shared-times",
]
RESERVED = [
    "možete li zakazati podsetnik za",
    "naša proba počinje u",
    "voz polazi u",
    "molim vas upišite ovo u moj dnevnik za",
]
RESERVED_DURATION = ["ostavite dodatno vreme", "radionica se nastavlja"]
# Registered rather than imported: background cannot see natural without closing
# the cycle that runs back through semantic.
background.reserve(RESERVED + RESERVED_DURATION)


def words(value, hyphen=False):
    if value < 20:
        return ONES[value]
    tens, ones = divmod(value, 10)
    # Serbian never hyphenates compound numbers; `hyphen` is kept only so
    # callers' existing rng draw still lands in the same place.
    return TENS[tens * 10] + (" " + ONES[ones] if ones else "")


def clock(s, mode=None, hour=None):
    r = s.rng
    h = hour if hour is not None else r.randint(1, 12)
    m = r.randrange(60)
    meridiem = r.choice(["am", "pm"])
    mode = mode or r.choice(["digits", "spoken", "qualified", "fraction"])
    if mode == "fraction":
        m = r.choice([15, 30, 45])
        subtract = m == 45
        if subtract:
            target = h % 12 + 1
            s.add("četvrt", "CLOCK_OFFSET")
            s.add("do", "GLUE")
            s.add(words(target), "HOUR")
            s.add(MERIDIEM_WORDS[meridiem], "MERIDIEM")
            target24 = target % 12 + (12 if meridiem == "pm" else 0)
            total = (target24 * 60 - 15) % 1440
            return {"hour": total // 60, "minute": total % 60}
        # "Past the hour" is not a CLOCK_OFFSET in Serbian: it is an ordinary
        # spoken minute joined to the hour with "i" ("pet i petnaest").
        s.add(words(h), "HOUR")
        s.add("i", "GLUE")
        s.add(words(m), "MINUTE")
        s.add(MERIDIEM_WORDS[meridiem], "MERIDIEM")
        target24 = h % 12 + (12 if meridiem == "pm" else 0)
        total = (target24 * 60 + m) % 1440
        return {"hour": total // 60, "minute": total % 60}
    s.add(words(h) if mode == "spoken" or r.random() < 0.4 else str(h), "HOUR")
    if mode == "spoken":
        if m:
            s.add(words(m, r.random() < 0.5), "MINUTE")
        else:
            # No Serbian "o'clock": a bare hour count word is just filler.
            s.add(unit_form(h, "hour"))
    elif mode == "qualified":
        m = 0
    else:
        s.add(":", "GLUE", "")
        s.add(f"{m:02}", "MINUTE", "")
    if mode == "qualified":
        qualifier = (
            r.choice(["ujutru", "izjutra"])
            if meridiem == "am"
            else r.choice(["popodne", "uveče", "noću"])
        )
        s.add(qualifier, "MERIDIEM")
        if h == 12 and qualifier == "noću":
            meridiem = "am"
    elif r.random() < 0.85:
        s.add(MERIDIEM_WORDS[meridiem], "MERIDIEM")
    else:
        meridiem = None
    return {
        "hour": h % 12 + (12 if meridiem == "pm" else 0) if meridiem else h,
        "minute": m,
    }


def quantity(s, amount, name):
    gender = unit_gender(name)
    if amount == 2 and gender == "f":
        spoken = "dve"
    elif amount == 1 and gender == "f":
        spoken = "jedna"
    else:
        spoken = words(amount)
    s.add(spoken if amount < 60 and s.rng.random() < 0.6 else str(amount), "NUM")
    s.add(unit_form(amount, name), "UNIT")


def calendar(s, date, numeric=False):
    r = s.rng
    if numeric:
        order = r.choice(["DMY", "DMY", "MDY"])
        sep = r.choice(["/", "-"])
        for i, key in enumerate(
            ["month", "day", "year"] if order == "MDY" else ["day", "month", "year"]
        ):
            if i:
                s.add(sep, "GLUE", "")
            s.add(
                (
                    str(date[key]).zfill(2)
                    if key != "year" and r.random() < 0.5
                    else str(date[key])
                ),
                {"month": "MONTH", "day": "DOM", "year": "YEAR"}[key],
                "",
            )
    else:
        # Day-before-month is the common Serbian prose order (matches the
        # DMY default); month-first stays available as a minority variant.
        day_first = r.random() < 0.8
        month_text = (
            MONTHS[date["month"] - 1]
            if r.random() < 0.5
            else MONTHS[date["month"] - 1][:3]
        )
        add_period = r.random() < 0.3
        if day_first:
            s.add(str(date["day"]), "DOM")
            s.add(".", "GLUE", "")
            s.add(month_text, "MONTH")
        else:
            s.add(month_text, "MONTH")
            if add_period:
                s.add(".", "GLUE", "")
            s.add(str(date["day"]), "DOM")
        if date.get("year"):
            s.add(str(date["year"]), "YEAR")


def render(s, reserved=False, family=None, bare=False):
    r = s.rng
    family = family or r.choice(FAMILIES)
    anchored = family not in (
        "compound-duration",
        "compound-shift",
        "fraction-duration",
    )
    if bare:
        prefix = ""
    elif reserved:
        prefix = r.choice(RESERVED if anchored else RESERVED_DURATION)
    elif r.random() < 0.85:
        prefix = background.prefix(r, connector=anchored)
    else:
        prefix = ""
    if prefix:
        s.add(prefix)
    s.clause()
    clause = {}
    if family in ("spoken-clock", "fraction-clock", "qualified-clock"):
        mode = {
            "spoken-clock": "spoken",
            "fraction-clock": "fraction",
            "qualified-clock": "qualified",
        }[family]
        clause = {"time": {"start": clock(s, mode)}}
    elif family in ("compound-duration", "compound-shift"):
        shift = family == "compound-shift"
        s.add("za", "DIR_AFTER" if shift else "DUR")
        first = r.randint(1, 5)
        second = r.randint(1, 11)
        units = r.choice([("hour", "minute"), ("day", "hour"), ("week", "day")])
        quantity(s, first, units[0])
        s.add("i", "GLUE")
        quantity(s, second, units[1])
        value = {
            "amount": first,
            "unit": units[0],
            "components": [{"amount": second, "unit": units[1]}],
        }
        if shift:
            value["direction"] = "after"
        clause = {"shift" if shift else "duration": value}
    elif family == "fraction-duration":
        shift = r.random() < 0.5
        s.add("za", "DIR_AFTER" if shift else "DUR")
        style = r.randrange(3)
        amount = r.randint(1, 4) + 0.5
        if style == 0:
            amount = 0.5
            s.add(r.choice(["pola", "po"]), "NUM")
            s.add("sata", "UNIT")
        elif style == 1:
            amount = 1.5
            s.add("sat", "UNIT")
            s.add("i", "GLUE")
            s.add("po", "NUM")
        else:
            s.add(str(amount), "NUM")
            s.add("sata", "UNIT")
        value = {"amount": amount, "unit": "hour"}
        if shift:
            value["direction"] = "after"
        clause = {"shift" if shift else "duration": value}
    elif family in ("prose-date", "numeric-date"):
        date = {
            "year": r.randint(1990, 2040),
            "month": r.randint(1, 12),
            "day": r.randint(13, 28),
        }
        if family == "prose-date" and r.random() < 0.35:
            date = {"day": r.randint(1, 28)}
            s.add(str(date["day"]), "DOM")
            s.add(".", "GLUE", "")
        else:
            calendar(s, date, family == "numeric-date")
        clause = {"date": {"kind": "calendar", **date}}
        if r.random() < 0.65:
            s.add("u", "GLUE")
            clause["time"] = {"start": clock(s)}
    elif family == "date-range":
        month = r.randint(1, 12)
        start = r.randint(1, 12)
        end = r.randint(16, 28)
        s.add("od", "RANGE_START")
        annotated = r.random() < 0.3
        if annotated:
            s.add(r.choice(DAYS), "WEEKDAY")
            s.add(str(start), "DOM")
            s.add(".", "GLUE", "")
        else:
            calendar(s, {"month": month, "day": start})
        s.add(r.choice(["do", "sve do", "kroz"]), "RANGE_END")
        if annotated:
            s.add(r.choice(DAYS), "WEEKDAY")
            s.add(str(end), "DOM")
            s.add(".", "GLUE", "")
        else:
            calendar(s, {"month": month, "day": end})
        clause = {
            "date": {
                "kind": "calendarRange",
                "from": {"month": month, "day": start},
                "to": {"month": month, "day": end},
            }
        }
        if annotated:
            clause = {
                "date": {
                    "kind": "calendarRange",
                    "from": {"day": start},
                    "to": {"day": end},
                }
            }
    elif family == "datetime-range":
        day = r.randint(0, 5)
        s.add(DAYS[day], "WEEKDAY")
        s.add("u", "GLUE")
        begin = clock(s, "digits")
        s.add(r.choice(["do", "sve do"]), "RANGE_END")
        s.add(DAYS[day + 1], "WEEKDAY")
        s.add("u", "GLUE")
        end = clock(s, "digits")
        clause = {
            "date": {"kind": "weekday", "days": [DAY_CODES[day]]},
            "endDate": {"kind": "weekday", "days": [DAY_CODES[day + 1]]},
            "time": {"start": begin, "end": end},
        }
    elif family in ("month-period", "month-week"):
        month = r.randint(1, 12)
        if family == "month-week":
            week = r.randint(1, 4)
            s.add(["prva", "druga", "treća", "četvrta"][week - 1], "ORD")
            s.add("nedelja", "UNIT")
            s.add("od", "GLUE")
            s.add(MONTHS[month - 1], "MONTH")
            clause = {"date": {"kind": "calendarPeriod", "month": month, "week": week}}
        else:
            modifier = r.choice(["this", "next", "last"])
            s.add(modifier_word(modifier, "m"), "DEICTIC")
            s.add(MONTHS[month - 1], "MONTH")
            clause = {
                "date": {"kind": "calendarPeriod", "month": month, "modifier": modifier}
            }
    else:
        day = r.randrange(7)
        interval = 1
        group = (
            family in ("recurrence", "recurrence-bound", "shared-times")
            and r.random() < 0.5
        )
        if not group or r.random() < 0.5:
            s.add("svaki", "RECUR")
        if family == "recurrence":
            interval = r.randint(1, 3)
            if interval > 1:
                has_unit = r.random() < 0.5
                gender = (
                    unit_gender("week")
                    if has_unit
                    else ("m" if group else weekday_gender(day))
                )
                if interval == 2:
                    s.add(
                        (
                            ("druga" if gender == "f" else "drugi")
                            if r.random() < 0.5
                            else ("dve" if gender == "f" else "dva")
                        ),
                        "NUM",
                    )
                else:
                    s.add(words(interval), "NUM")
                if has_unit:
                    s.add(unit_form(interval, "week"), "UNIT")
                    s.add("u", "GLUE")
        if group:
            s.add("radni dan" if r.random() < 0.5 else "radni dani", "DAYGROUP")
        else:
            s.add(DAYS[day], "WEEKDAY")
        rule = {"freq": "weekly", "interval": interval, "byDay": [DAY_CODES[day]]}
        if group:
            rule["byDay"] = DAY_CODES[:5]
        if group and family == "recurrence" and interval == 1 and r.random() < 0.3:
            return Specification(family, {"clauses": [{"recurrence": rule}]})
        s.add("u", "GLUE")
        start = clock(s)
        clause = {"recurrence": rule, "time": {"start": start}}
        if family == "recurrence-bound":
            s.add("do", "BOUND_END")
            date = {"year": 2036, "month": r.randint(1, 12), "day": r.randint(1, 28)}
            calendar(s, date)
            rule["until"] = {"kind": "calendar", **date}
        elif family == "monthly-exception":
            ordinal = r.choice([1, 2, -1])
            ord_word = {1: "prvi", 2: "drugi", -1: "poslednji"}[ordinal]
            if weekday_gender(day) == "f":
                ord_word = ordinal_feminine(ord_word)
            s.add("osim", "EXCEPT")
            s.add(ord_word, "ORD")
            s.add(DAYS[day], "WEEKDAY")
            s.add("od", "GLUE")
            s.add("svako", "RECUR")
            s.add("mesec", "UNIT")
            rule["except"] = [
                {
                    "kind": "ordinalWeekday",
                    "ordinal": ordinal,
                    "day": DAY_CODES[day],
                    "of": {"kind": "calendar"},
                    "recurring": True,
                }
            ]
        elif family == "shared-times":
            s.add("i", "JOIN")
            end = clock(s)
            return Specification(
                family,
                {
                    "clauses": [
                        clause,
                        {"recurrence": deepcopy(rule), "time": {"start": end}},
                    ]
                },
            )
    return Specification(family, {"clauses": [clause]})
