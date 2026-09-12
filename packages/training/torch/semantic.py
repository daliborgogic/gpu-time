"""Sample schedules first, then render their words and token supervision.

The expected AST comes from the sampled specification. Neither the browser
parser nor a date recognizer supplies training labels or expected schedules.
"""

from __future__ import annotations

import random
import background
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from generate import Sentence

DAYS = ["ponedeljak", "utorak", "sreda", "četvrtak", "petak", "subota", "nedelja"]
DAY_CODES = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
MONTHS = [
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
]
NUMBERS = [
    "nula",
    "jedan",
    "dva",
    "tri",
    "četiri",
    "pet",
    "šest",
    "sedam",
    "osam",
    "devet",
    "deset",
    "jedanaest",
    "dvanaest",
]
ORDINALS = [
    "prvi",
    "drugi",
    "treći",
    "četvrti",
    "peti",
    "šesti",
    "sedmi",
    "osmi",
    "deveti",
    "deseti",
    "jedanaesti",
    "dvanaesti",
]

GENERAL_FAMILIES = [
    "now",
    "clock",
    "day-part",
    "weekday",
    "day-group",
    "time-window",
    "date-range",
    "weekday-range",
    "duration",
    "anchored-relative",
    "recurrence",
    "yearly",
    "frequency-count",
    "exceptions",
    "recurrence-bounds",
    "holiday",
]
HOLIDAYS = {
    "christmas": "Božić",
    "christmas-eve": "Badnje veče",
    "new-year": "Nova godina",
    "new-years-eve": "Silvestrovo",
    "halloween": "Noć veštica",
    "valentines": "Valentinovo",
}

# Slavic numeral-noun agreement: singular / "few" (2-4) / "many" surface forms
# for each internal Unit identifier (plus the standalone "times" counter).
# "week_sedmica" is an alias some callers pick instead of "week" purely for
# surface variety -- it is never a real Unit/DateSpec field value.
UNIT_WORDS: dict[str, tuple[str, str, str]] = {
    "minute": ("minut", "minuta", "minuta"),
    "hour": ("sat", "sata", "sati"),
    "day": ("dan", "dana", "dana"),
    "week": ("nedelja", "nedelje", "nedelja"),
    "week_sedmica": ("sedmica", "sedmice", "sedmica"),
    "month": ("mesec", "meseca", "meseci"),
    "year": ("godina", "godine", "godina"),
    "times": ("put", "puta", "puta"),
}

# Gendered surface forms for the three schedule Modifier values ("this"/
# "next"/"last"), so a DEICTIC token can agree with whichever noun follows
# (dan/mesec are masculine; nedelja/sedmica/godina/vikend-adjacent nouns are
# feminine except vikend itself, which is masculine).
MODIFIER_FORMS = {
    "this": {"m": "ovaj", "f": "ova", "n": "ovo"},
    "next": {"m": "sledeći", "f": "sledeca", "n": "sledeće"},
    "last": {"m": "prošli", "f": "prošla", "n": "prošlo"},
}
EDGE_WORDS = {"start": "početak", "end": "kraj"}

# Grammatical gender of each internal Unit identifier's canonical Serbian
# noun: minut/sat/dan/mesec are masculine; nedelja/sedmica/godina (and the
# standalone "put" counter) -- put is masculine too, kept explicit for clarity.
UNIT_GENDER: dict[str, str] = {
    "minute": "m",
    "hour": "m",
    "day": "m",
    "week": "f",
    "week_sedmica": "f",
    "month": "m",
    "year": "f",
    "times": "m",
}

# Weekday gender, indexed the same way as DAYS/DAY_CODES (MO..SU): sreda,
# subota, nedelja are feminine; the other four weekdays are masculine.
WEEKDAY_GENDER = ["m", "m", "f", "m", "m", "f", "f"]

# The gendered "2" numeral and its ordinal, for agreement with whichever noun
# immediately follows (dva/drugi for masculine, dve/druga for feminine).
TWO_WORDS = {"m": "dva", "f": "dve"}
TWO_ORDINAL_WORDS = {"m": "drugi", "f": "druga"}

# Feminine forms of the small ordinals used for ORD/DEICTIC agreement with a
# feminine noun (a weekday like sreda/subota/nedelja, or a feminine unit).
ORDINAL_FEMININE = {
    "prvi": "prva",
    "drugi": "druga",
    "treći": "treća",
    "četvrti": "četvrta",
    "peti": "peta",
    "poslednji": "poslednja",
}


def unit_gender(unit: str) -> str:
    return UNIT_GENDER.get(unit, "m")


def weekday_gender(day) -> str:
    """Accepts a DAY_CODES string (MO..SU), a DAYS full/abbreviated name, or
    a plain 0..6 index into DAYS/DAY_CODES -- callers hold whichever of these
    they already have on hand, so this normalizes all three."""
    if isinstance(day, int):
        return WEEKDAY_GENDER[day]
    if day in DAY_CODES:
        return WEEKDAY_GENDER[DAY_CODES.index(day)]
    if day in DAYS:
        return WEEKDAY_GENDER[DAYS.index(day)]
    lowered = day.lower() if isinstance(day, str) else day
    for index, name in enumerate(DAYS):
        if lowered in (name, name.lower(), name[:3], name[:3].lower()):
            return WEEKDAY_GENDER[index]
    return "m"


def two_word(gender: str, ordinal: bool = False) -> str:
    return (TWO_ORDINAL_WORDS if ordinal else TWO_WORDS)[gender]


def ordinal_feminine(word: str) -> str:
    return ORDINAL_FEMININE.get(word, word)


def unit_form(amount: float, unit: str) -> str:
    """Serbian numeral-noun agreement: the singular / "few" (2-4) / "many"
    surface form of `unit` for `amount` (the teens 11-14 always take the
    "many" form, regardless of their last digit)."""
    n = abs(int(amount))
    if n % 100 in (11, 12, 13, 14):
        index = 2
    elif n % 10 == 1:
        index = 0
    elif n % 10 in (2, 3, 4):
        index = 1
    else:
        index = 2
    return UNIT_WORDS[unit][index]


def modifier_word(modifier: str, gender: str = "m") -> str:
    return MODIFIER_FORMS[modifier][gender]


@dataclass
class Specification:
    family: str
    schedule: dict


def sample(rng: random.Random) -> Specification:
    family = rng.choice(
        [
            "calendar",
            "relative",
            "weekday-windows",
            "monthly-days",
            "relative-day",
            "relative-unit",
            "modified-group",
            "weekday-points",
            "bounded-weekday",
            "monthly-ordinal",
        ]
        + GENERAL_FAMILIES
    )
    if family in GENERAL_FAMILIES:
        return Specification(family, {"clauses": [sample_general(family, rng)]})
    if family == "calendar":
        date = {
            "kind": "calendar",
            "month": rng.randint(1, 12),
            "day": rng.randint(1, 28),
        }
        if rng.random() < 0.65:
            date["year"] = rng.randint(1990, 2040)
        clause = {"date": date}
    elif family == "relative":
        clause = {
            "shift": {
                "amount": rng.choice([1, 2, 3, 5, 7, 10, 12, 15, 30, 90]),
                "unit": rng.choice(["minute", "hour", "day", "week", "month", "year"]),
                "direction": rng.choice(["before", "after"]),
            }
        }
        if rng.random() < 0.35:
            clause["date"] = {"kind": "relativeDay", "offset": rng.choice([-1, 0, 1])}
        elif rng.random() < 0.3:
            clause["date"] = {"kind": "now"}
            clause["shift"]["direction"] = "after"
    elif family == "relative-day":
        clause = {"date": {"kind": "relativeDay", "offset": rng.choice([-1, 0, 1, 2])}}
    elif family == "relative-unit":
        date = {
            "kind": "relativeUnit",
            "unit": rng.choice(["week", "month", "year"]),
            "modifier": rng.choice(["this", "next", "last"]),
        }
        if rng.random() < 0.65:
            date["edge"] = rng.choice(["start", "end"])
        clause = {"date": date}
    elif family == "modified-group":
        clause = {
            "date": {
                "kind": "dayGroup",
                "group": "weekend",
                "modifier": rng.choice(["this", "next", "last"]),
            }
        }
    elif family == "bounded-weekday":
        clause = {
            "recurrence": {
                "freq": "daily",
                "interval": 1,
                "until": {"kind": "weekday", "days": [rng.choice(DAY_CODES)]},
            }
        }
    elif family == "weekday-points":
        clauses = [
            {
                "date": {"kind": "weekday", "days": [day]},
                "time": {"start": {"hour": rng.randint(1, 12), "minute": 0}},
            }
            for day in rng.sample(DAY_CODES, rng.randint(2, 4))
        ]
        return Specification(family, {"clauses": clauses})
    elif family == "monthly-ordinal":
        clause = {
            "recurrence": {
                "freq": "monthly",
                "interval": 1,
                "byDay": [rng.choice(DAY_CODES)],
                "bySetPos": [rng.choice([-1, 1, 2, 3, 4, 5])],
            }
        }
    elif family == "monthly-days":
        clause = {
            "recurrence": {
                "freq": "monthly",
                "interval": 1,
                "byMonthDay": sorted(rng.sample(range(1, 29), rng.randint(1, 3))),
            }
        }
    else:
        clauses = []
        for _ in range(rng.randint(1, 3)):
            days = rng.sample(DAY_CODES, rng.randint(1, 3))
            start = {"hour": rng.randint(0, 23), "minute": rng.choice([0, 15, 30, 45])}
            end = {
                "hour": (start["hour"] + rng.randint(1, 12)) % 24,
                "minute": start["minute"],
            }
            clause = {"time": {"start": start, "end": end}}
            if rng.random() < 0.35:
                clause["recurrence"] = {
                    "freq": "weekly",
                    "interval": rng.randint(1, 4),
                    "byDay": days,
                }
            else:
                clause["date"] = {"kind": "weekday", "days": days}
            clauses.append(clause)
        return Specification(family, {"clauses": clauses})
    return Specification(family, {"clauses": [clause]})


def render(spec: Specification, sentence: Sentence, style: int) -> None:
    rng = sentence.rng
    if rng.random() < 0.4:
        anchored = spec.family not in ("duration", "weekday-range", "relative")
        sentence.add(background.prefix(rng, connector=anchored))
    for index, clause in enumerate(spec.schedule["clauses"]):
        if index and style % 2:
            sentence.add(rng.choice(["i", ";", ",", "zatim"]), "JOIN")
        sentence.clause()
        if spec.family in GENERAL_FAMILIES:
            render_general(clause, sentence, style)
        elif spec.family == "calendar":
            calendar(clause["date"], sentence, style)
        elif spec.family == "relative":
            relative(clause, sentence, style)
        elif spec.family == "relative-day":
            sentence.add(
                {
                    -1: "juče",
                    0: "danas",
                    1: "sutra",
                    2: "prekosutra",
                }[clause["date"]["offset"]],
                "REL_DAY",
            )
        elif spec.family == "relative-unit":
            date = clause["date"]
            if date.get("edge"):
                sentence.add(EDGE_WORDS[date["edge"]], "EDGE")
                sentence.add("od")
            gender = "f" if date["unit"] in ("week", "year") else "m"
            sentence.add(modifier_word(date["modifier"], gender), "DEICTIC")
            sentence.add(UNIT_WORDS[date["unit"]][0], "UNIT")
        elif spec.family == "modified-group":
            sentence.add(modifier_word(clause["date"]["modifier"], "m"), "DEICTIC")
            sentence.add("vikend", "DAYGROUP")
        elif spec.family == "bounded-weekday":
            sentence.add("svaki", "RECUR")
            sentence.add("dan", "UNIT")
            sentence.add(rng.choice(["do", "sve do"]), "BOUND_END")
            sentence.add(
                DAYS[DAY_CODES.index(clause["recurrence"]["until"]["days"][0])],
                "WEEKDAY",
            )
        elif spec.family == "weekday-points":
            day = DAYS[DAY_CODES.index(clause["date"]["days"][0])]
            sentence.add(day[:3] if style % 2 else day, "WEEKDAY")
            sentence.add("u")
            sentence.add(str(clause["time"]["start"]["hour"]), "HOUR")
        elif spec.family == "monthly-ordinal":
            rule = clause["recurrence"]
            position = rule["bySetPos"][0]
            day_code = rule["byDay"][0]
            ord_word = (
                "poslednji"
                if position == -1
                else ["prvi", "drugi", "treći", "četvrti", "peti"][position - 1]
            )
            if weekday_gender(day_code) == "f":
                ord_word = ordinal_feminine(ord_word)
            sentence.add(ord_word, "ORD")
            sentence.add(DAYS[DAY_CODES.index(day_code)], "WEEKDAY")
            sentence.add("od")
            if style % 2:
                sentence.add("svaki", "RECUR")
            sentence.add("mesec", "UNIT")
        elif spec.family == "monthly-days":
            days = clause["recurrence"]["byMonthDay"]
            if style % 2:
                sentence.add("svaki", "RECUR")
                sentence.add("mesec", "UNIT")
            for position, day in enumerate(days):
                if position:
                    sentence.add("i")
                ordinal(day, sentence)
            if style % 2 == 0:
                sentence.add("od")
                sentence.add("svako", "RECUR")
                sentence.add("mesec", "UNIT")
        else:
            recurrence = clause.get("recurrence")
            days = recurrence["byDay"] if recurrence else clause["date"]["days"]
            if recurrence:
                interval = recurrence["interval"]
                sentence.add(
                    rng.choice(["svaki", "svako"]) if interval == 1 else "svaki",
                    "RECUR",
                )
                if interval == 2 and style % 2:
                    gender = weekday_gender(days[0])
                    sentence.add("druga" if gender == "f" else "drugi", "NUM")
                elif interval > 1:
                    sentence.quantity(interval, gender=unit_gender("week"))
                    sentence.add(unit_form(interval, "week"), "UNIT")
                    sentence.add("u")
            for position, day in enumerate(days):
                if position and style % 3:
                    sentence.add(rng.choice(["i", ",", "&"]), "JOIN")
                name = DAYS[DAY_CODES.index(day)]
                sentence.add(name[:3] if style % 2 else name, "WEEKDAY")
            if style % 3 == 0:
                sentence.add("od", "RANGE_START")
            clock(clause["time"]["start"], sentence, style)
            sentence.add("do" if style % 3 == 0 else "-", "RANGE_END")
            clock(clause["time"]["end"], sentence, style)
    if rng.random() < 0.2:
        sentence.in_expression = False
        sentence.add(rng.choice(["molim", "za naš tim", "to mi odgovara"]))


def ordinal(day: int, sentence: Sentence) -> None:
    if day <= 12 and sentence.rng.random() < 0.3:
        sentence.add(ORDINALS[day - 1], "DOM")
        return
    sentence.add(str(day), "DOM")
    sentence.add(".", separator="")


def calendar(date: dict, sentence: Sentence, style: int) -> None:
    year, month, day = date.get("year"), date["month"], date["day"]
    separator = ["/", "-", "."][style % 3]
    if style % 6 == 0 and year:
        fields = [(year, "YEAR"), (month, "MONTH"), (day, "DOM")]
    elif style % 6 < 4:
        # Unambiguous day-first numeric examples do not contradict the default
        # month-first labels on inputs such as 03/04. Locale overrides belong to
        # the caller's dateOrder option, not to an unobservable training choice.
        fields = (
            [(day, "DOM"), (month, "MONTH")]
            if day > 12 and style % 2
            else [(month, "MONTH"), (day, "DOM")]
        )
        if year:
            fields.append((year, "YEAR"))
    else:
        named = MONTHS[month - 1]
        spell_day = day <= 12 and sentence.rng.random() < 0.5
        day_text = ORDINALS[day - 1] if spell_day else day
        # Day-before-month is the common Serbian prose order (matches the DMY
        # default); month-first stays available as a minority stylistic
        # variant, gated on the pre-existing spell_day/style draws so no new
        # RNG call is introduced.
        fields = (
            [(named, "MONTH"), (day_text, "DOM")]
            if spell_day and style % 2
            else [(day_text, "DOM"), (named, "MONTH")]
        )
        if year:
            fields.append((year, "YEAR"))
        separator = " "
    for index, (value, label) in enumerate(fields):
        if (
            label == "MONTH"
            and index
            and fields[index - 1][1] == "DOM"
            and separator == " "
            and sentence.rng.random() < 0.5
        ):
            sentence.add("od")
        if index and separator != " ":
            sentence.add(separator, separator="")
        sentence.add(str(value), label, separator="" if separator != " " else " ")


def relative(clause: dict, sentence: Sentence, style: int) -> None:
    shift = clause["shift"]
    direction = shift["direction"]
    label = "DIR_AFTER" if direction == "after" else "DIR_BEFORE"
    prefix = style % 2 and not clause.get("date")
    if prefix:
        sentence.add("za" if direction == "after" else "pre", label)
    sentence.quantity_unit([shift["unit"]], shift["amount"])
    if not prefix:
        sentence.add(
            (
                "od"
                if clause["date"]["kind"] == "now"
                else ("posle" if direction == "after" else "pre")
            )
            if clause.get("date")
            else sentence.rng.choice(
                ["posle", "kasnije"]
                if direction == "after"
                else ["pre", "unazad", "ranije"]
            ),
            label,
        )
    if clause.get("date"):
        if clause["date"]["kind"] == "now":
            sentence.add("sada", "NOW")
            return
        render_date(clause["date"], sentence, style)
        if clause.get("time"):
            sentence.add("u")
            clock(clause["time"]["start"], sentence, style)


def clock(value: dict, sentence: Sentence, style: int) -> None:
    if "named" in value:
        sentence.add({"noon": "podne", "midnight": "ponoć"}[value["named"]], "TIME_NAMED")
        return
    if "part" in value:
        sentence.add(
            {"morning": "jutro", "afternoon": "popodne", "evening": "veče", "night": "noć"}[
                value["part"]
            ],
            "DAYPART",
        )
        return
    hour, minute = value["hour"], value["minute"]
    meridiem = style % 2 == 0
    display = hour % 12 or 12 if meridiem else hour
    hour_text = (
        NUMBERS[display]
        if display <= 12 and style % 4 == 0 and minute == 0 and "second" not in value
        else str(display)
        if meridiem
        else f"{display:02d}"
    )
    sentence.add(hour_text, "HOUR")
    if minute or not meridiem or "second" in value:
        sentence.add(":", separator="")
        sentence.add(f"{minute:02d}", "MINUTE", separator="")
    if "second" in value:
        sentence.add(":", separator="")
        sentence.add(f"{value['second']:02d}", "SECOND", separator="")
    if meridiem:
        if sentence.rng.random() < 0.25:
            period = "ujutru" if hour < 12 else "popodne" if hour < 18 else "uveče"
            sentence.add(period, "MERIDIEM")
            return
        separator = (
            " " if hour_text.isalpha() and not minute and "second" not in value else ""
        )
        sentence.add(
            "popodne" if hour >= 12 else "ujutru", "MERIDIEM", separator=separator
        )


def sample_clock(rng: random.Random) -> dict:
    value = {"hour": rng.randint(0, 23), "minute": rng.choice([0, 15, 30, 45])}
    if rng.random() < 0.2:
        value["second"] = rng.randint(0, 59)
    return value


def sample_general(family: str, rng: random.Random) -> dict:
    if family == "now":
        return {"date": {"kind": "now"}}
    if family == "holiday":
        return {"date": {"kind": "holiday", "name": rng.choice(list(HOLIDAYS))}}
    if family == "clock":
        return {
            "time": {
                "start": rng.choice(
                    [sample_clock(rng), {"named": "noon"}, {"named": "midnight"}]
                )
            }
        }
    if family == "day-part":
        return {
            "date": {"kind": "relativeDay", "offset": rng.choice([0, 1, -1])},
            "time": {
                "start": {
                    "part": rng.choice(["morning", "afternoon", "evening", "night"])
                }
            },
        }
    if family == "weekday":
        date = {"kind": "weekday", "days": rng.sample(DAY_CODES, rng.randint(1, 3))}
        if rng.random() < 0.5:
            date["modifier"] = rng.choice(["this", "next", "last"])
        return {"date": date, "time": {"start": sample_clock(rng)}}
    if family == "weekday-range":
        start, end = rng.sample(DAY_CODES, 2)
        return {"date": {"kind": "weekdayRange", "from": start, "to": end}}
    if family == "day-group":
        return {
            "recurrence": {
                "freq": "weekly",
                "interval": 1,
                "byDay": DAY_CODES[:5] if rng.random() < 0.5 else DAY_CODES[5:],
            }
        }
    if family == "time-window":
        start = sample_clock(rng)
        return {
            "time": {
                "start": start,
                "end": {
                    "hour": (start["hour"] + rng.randint(1, 10)) % 24,
                    "minute": start["minute"],
                },
            }
        }
    if family == "date-range":
        month = rng.randint(1, 11)
        year = rng.randint(2020, 2035)
        return {
            "date": {
                "kind": "calendarRange",
                "from": {"year": year, "month": month, "day": rng.randint(1, 14)},
                "to": {
                    "year": year,
                    "month": month + rng.randint(0, 1),
                    "day": rng.randint(15, 28),
                },
            }
        }
    if family == "duration":
        clause = {
            "duration": {
                "amount": rng.choice([1, 2, 3, 6, 10, 30, 90]),
                "unit": rng.choice(["minute", "hour", "day", "week"]),
            }
        }
        if rng.random() < 0.5:
            clause["date"] = {"kind": "relativeDay", "offset": rng.choice([0, 1])}
        return clause
    if family == "anchored-relative":
        date = rng.choice(
            [
                {"kind": "weekday", "days": [rng.choice(DAY_CODES)]},
                {"kind": "holiday", "name": rng.choice(list(HOLIDAYS))},
                {
                    "kind": "calendar",
                    "month": rng.randint(1, 12),
                    "day": rng.randint(1, 28),
                },
            ]
        )
        clause = {
            "date": date,
            "shift": {
                "amount": rng.randint(1, 12),
                "unit": rng.choice(["hour", "day", "week"]),
                "direction": rng.choice(["before", "after"]),
            },
        }
        if rng.random() < 0.3:
            clause["time"] = {"start": {"named": "noon"}}
        return clause
    if family == "frequency-count":
        return {
            "recurrence": {
                "freq": rng.choice(["daily", "weekly"]),
                "interval": 1,
                "timesPer": rng.randint(1, 6),
            }
        }
    if family == "exceptions":
        return {
            "recurrence": {
                "freq": "daily",
                "interval": 1,
                "except": [
                    {
                        "kind": "weekday",
                        "days": rng.sample(DAY_CODES, rng.randint(1, 2)),
                    }
                ],
            }
        }
    if family == "yearly":
        return {
            "recurrence": {
                "freq": "yearly",
                "interval": rng.randint(1, 3),
                "byMonth": [rng.randint(1, 12)],
                "byMonthDay": [rng.randint(1, 28)],
            }
        }
    rule = {
        "freq": rng.choice(["hourly", "daily", "weekly", "monthly", "yearly"]),
        "interval": rng.randint(1, 4),
    }
    if rule["freq"] == "weekly" and rng.random() < 0.6:
        rule["byDay"] = rng.sample(DAY_CODES, rng.randint(1, 3))
    if family == "recurrence-bounds":
        bound = rng.choice(["count", "span", "until", "start"])
        if bound == "count":
            rule[bound] = rng.randint(1, 12)
        elif bound == "span":
            rule[bound] = {"amount": rng.randint(1, 12), "unit": "week"}
        elif bound == "start":
            rule[bound] = {"kind": "relativeUnit", "unit": "week", "modifier": "next"}
        else:
            rule[bound] = {
                "kind": "calendar",
                "month": rng.randint(1, 12),
                "day": rng.randint(1, 28),
            }
    return {"recurrence": rule, "time": {"start": sample_clock(rng)}}


def render_days(days: list[str], sentence: Sentence, style: int) -> None:
    for index, day in enumerate(days):
        if index:
            sentence.add("i", "JOIN")
        name = DAYS[DAY_CODES.index(day)]
        sentence.add(name[:3] if style % 2 else name, "WEEKDAY")


def render_date(date: dict, sentence: Sentence, style: int) -> None:
    kind = date["kind"]
    if kind == "now":
        sentence.add("sada", "NOW")
    elif kind == "relativeDay":
        sentence.add(
            {-1: "juče", 0: "danas", 1: "sutra", 2: "prekosutra"}[date["offset"]],
            "REL_DAY",
        )
    elif kind == "weekday":
        if date.get("modifier"):
            sentence.add(
                modifier_word(date["modifier"], weekday_gender(date["days"][0])),
                "DEICTIC",
            )
        render_days(date["days"], sentence, style)
    elif kind == "weekdayRange":
        sentence.add("od", "RANGE_START")
        render_days([date["from"]], sentence, style)
        sentence.add("do", "RANGE_END")
        render_days([date["to"]], sentence, style)
    elif kind == "holiday":
        sentence.add(HOLIDAYS[date["name"]], "HOLIDAY")
    elif kind == "calendar":
        calendar(date, sentence, style)
    elif kind == "calendarRange":
        calendar(date["from"], sentence, 5)
        sentence.add("do", "RANGE_END")
        calendar(date["to"], sentence, 5)
    elif kind == "relativeUnit":
        if date.get("edge"):
            sentence.add(EDGE_WORDS[date["edge"]], "EDGE")
            sentence.add("od")
        gender = "f" if date["unit"] in ("week", "year") else "m"
        sentence.add(modifier_word(date["modifier"], gender), "DEICTIC")
        sentence.add(UNIT_WORDS[date["unit"]][0], "UNIT")
    else:
        raise ValueError(f"No date renderer for {kind}")


def render_general(clause: dict, sentence: Sentence, style: int) -> None:
    if clause.get("shift"):
        relative(clause, sentence, style)
        return
    rule = clause.get("recurrence")
    if rule:
        if rule.get("timesPer"):
            sentence.quantity(rule["timesPer"])
            sentence.add("puta", "TIMES")
            sentence.add("na", "RECUR")
            sentence.add("dan" if rule["freq"] == "daily" else "nedelju", "UNIT")
        elif rule["interval"] == 1 and rule.get("byDay") in (
            DAY_CODES[:5],
            DAY_CODES[5:],
        ):
            sentence.add("svaki", "RECUR")
            sentence.add(
                "radni dan" if rule["byDay"] == DAY_CODES[:5] else "vikend", "DAYGROUP"
            )
        else:
            sentence.add("svaki", "RECUR")
            period = {
                "hourly": "hour",
                "daily": "day",
                "weekly": "week",
                "monthly": "month",
                "yearly": "year",
            }[rule["freq"]]
            if rule["interval"] > 1:
                sentence.quantity(rule["interval"], gender=unit_gender(period))
            sentence.add(
                unit_form(rule["interval"], period) if rule["interval"] > 1 else UNIT_WORDS[period][0],
                "UNIT",
            )
            if rule.get("byDay"):
                sentence.add("u")
                render_days(rule["byDay"], sentence, style)
            if rule.get("byMonth"):
                # Day-before-month, matching the calendar()/date() day-first fix.
                sentence.quantity(rule["byMonthDay"][0], "DOM")
                sentence.add(".", separator="")
                sentence.add(MONTHS[rule["byMonth"][0] - 1], "MONTH")
    elif clause.get("date"):
        render_date(clause["date"], sentence, style)
    if clause.get("time"):
        has_end = bool(clause["time"].get("end"))
        if has_end and style % 3 == 0:
            sentence.add("od", "RANGE_START")
        elif has_end and style % 3 == 1:
            sentence.add("između", "RANGE_START")
        else:
            sentence.add("u")
        clock(clause["time"]["start"], sentence, style)
        if has_end:
            sentence.add(
                "i"
                if style % 3 == 1
                else sentence.rng.choice(["do", "-", "–", "kroz"]),
                "RANGE_END",
            )
            clock(clause["time"]["end"], sentence, style)
    if rule:
        for field, marker, label in [
            ("start", "od", "BOUND_START"),
            ("until", "do", "BOUND_END"),
        ]:
            if rule.get(field):
                sentence.add(marker, label)
                render_date(rule[field], sentence, style)
        if rule.get("count"):
            sentence.add("za")
            sentence.quantity(rule["count"])
            sentence.add("puta", "COUNT")
        if rule.get("except"):
            sentence.add("osim", "EXCEPT")
            render_date(rule["except"][0], sentence, style)
    duration = clause.get("duration") or (rule or {}).get("span")
    if duration:
        sentence.add("za", "DUR")
        next_duration = sentence.rng.random() < 0.3
        if next_duration:
            sentence.add(sentence.rng.choice(["sledeći", "naredni"]), "DEICTIC")
        sentence.quantity_unit([duration["unit"]], duration["amount"])
