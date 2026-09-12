"""Generate supervision from semantic slots, never from the runtime parser.

A rendered slot supplies its label and source span. The shared browser tokenizer
later maps these spans onto tokens. Template partitions are disjoint by ID.
"""

from __future__ import annotations

import argparse
import json
import hashlib
import random
from collections import Counter
from pathlib import Path

from signature import fingerprint
import semantic
import background
import natural

ROOT = Path(__file__).resolve().parent.parent

DAYS = ["ponedeljak", "utorak", "sreda", "četvrtak", "petak", "subota", "nedelja"]
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
TENS = {
    20: "dvadeset",
    30: "trideset",
    40: "četrdeset",
    50: "pedeset",
    60: "šezdeset",
    70: "sedamdeset",
    80: "osamdeset",
    90: "devedeset",
}
ORDINALS = ["prvi", "drugi", "treći", "četvrti", "peti"]
DAY_ORDINALS = [
    "prvi", "drugi", "treći", "četvrti", "peti", "šesti", "sedmi",
    "osmi", "deveti", "deseti", "jedanaesti", "dvanaesti", "trinaesti",
    "četrnaesti", "petnaesti", "šesnaesti", "sedamnaesti", "osamnaesti",
    "devetnaesti", "dvadeseti", "dvadeset prvi", "dvadeset drugi",
    "dvadeset treći", "dvadeset četvrti", "dvadeset peti", "dvadeset šesti",
    "dvadeset sedmi", "dvadeset osmi", "dvadeset deveti", "trideseti",
    "trideset prvi",
]
HOLIDAYS = [
    "Božić",
    "Badnje veče",
    "Nova godina",
    "Silvestrovo",
    "Noć veštica",
    "Valentinovo",
]
# Internal Unit identifiers stay the TypeScript-facing English words; only the
# surface text (via semantic.unit_form) is ever Serbian.
UNITS = ["minute", "hour", "day", "week", "month", "year"]

# Gendered surface forms for the three DEICTIC "flavors", so a modifier can
# agree with whichever noun follows it (dan/mesec are masculine; nedelja/
# sedmica/godina are feminine). "sledeca" (no ć) is the exact feminine key
# already committed in lexicon.ts's modifiers map -- not a typo to "fix".
DEICTIC_FORMS = {
    "sledeći": {"m": "sledeći", "f": "sledeca", "n": "sledeće"},
    "ovaj": {"m": "ovaj", "f": "ova", "n": "ovo"},
    "prošli": {"m": "prošli", "f": "prošla", "n": "prošlo"},
    "naredni": {"m": "naredni", "f": "naredna", "n": "naredno"},
    "prethodni": {"m": "prethodni", "f": "prethodna", "n": "prethodno"},
}


class Sentence:
    def __init__(self, rng: random.Random, augment: bool = True):
        self.rng = rng
        self.augment = augment
        self.text = ""
        self.spans: list[dict] = []
        self.clauses = 0
        self.pending_clause = False
        self.in_expression = False

    def add(self, text: str, label: str = "O", separator: str = " ") -> None:
        if label in ("O", "GLUE") and self.in_expression:
            # A carrier ending in a preposition meeting a clause that opens with
            # one reads as "the appointment is at on the 18th".
            words = text.split()
            tail = self.text.split()
            if (
                words
                and tail
                and words[0] in background.CONNECTORS
                and tail[-1].lower() in background.CONNECTORS
            ):
                words = words[1:]
                if not words:
                    return
                text = " ".join(words)
        if label == "O" and self.in_expression:
            if (
                self.augment
                and text in ("u", "na", "od")
                and self.rng.random() < 0.3
            ):
                return
            label = "GLUE"
        if (
            self.augment
            and any(character.isalpha() for character in text)
            and self.rng.random() < 0.3
        ):
            text = self.rng.choice([text.lower(), text.upper(), text.capitalize()])
        if self.text:
            left, right = self.text[-1], text[0]
            would_merge = (
                (left.isalpha() or left == "_") and (right.isalpha() or right == "_")
            ) or (left.isdigit() and right.isdigit())
            if self.augment and separator == " ":
                separator = self.rng.choice(
                    [" ", " ", "  ", "\t"] if would_merge else ["", " ", " ", "  "]
                )
            # A caller asking for no separator cannot know what precedes it; two
            # tokens fused here leave a span the tokenizer cannot address.
            self.text += separator or (" " if would_merge else "")
        start = len(self.text.encode("utf-16-le")) // 2
        self.text += text
        end = len(self.text.encode("utf-16-le")) // 2
        boundary = self.pending_clause and label not in ("O", "GLUE", "JOIN")
        if boundary:
            self.pending_clause = False
        self.spans.append(
            {"start": start, "end": end, "label": label, "clauseStart": boundary}
        )

    def clause(self) -> None:
        self.in_expression = True
        self.pending_clause = self.clauses > 0
        self.clauses += 1

    def quantity(
        self, value: int | None = None, label: str = "NUM", gender: str = "m"
    ) -> int:
        value = (
            value
            if value is not None
            else self.rng.choice([1, 2, 3, 4, 5, 6, 7, 10, 12, 15, 24, 30, 45, 90])
        )
        spelled = value <= 12 and self.rng.random() < 0.35
        if spelled and gender == "f" and value == 2:
            text = "dve"
        elif spelled and gender == "f" and value == 1:
            text = "jedna"
        elif spelled:
            text = NUMBERS[value]
        else:
            text = str(value)
        self.add(text, label)
        return value

    def quantity_unit(
        self,
        units: list[str] = UNITS,
        amount: int | None = None,
    ) -> None:
        name = self.rng.choice(units)
        amount = (
            amount
            if amount is not None
            else self.rng.choice([1, 2, 3, 5, 7, 10, 12, 15, 30, 90])
        )
        self.quantity(amount, gender=semantic.unit_gender(name))
        self.add(semantic.unit_form(amount, name), "UNIT")

    def day(self, name: str | None = None) -> str:
        name = name if name is not None else self.rng.choice(DAYS)
        self.add(
            self.rng.choice([name, name.lower(), name[:3], name[:3].lower()]),
            "WEEKDAY",
        )
        if self.rng.random() < 0.08:
            self.add(".", separator="")
        return name

    def days(self, name: str | None = None) -> None:
        name = self.day(name)
        if self.rng.random() < 0.45:
            connector = self.rng.choice(["i", ",", "&", ""])
            if connector:
                self.add(connector, "JOIN")
            self.day()

    def ordinal(
        self, label: str = "ORD", day_of_month: bool = False, gender: str = "m"
    ) -> None:
        value = self.rng.randint(1, 31 if day_of_month else 5)
        if not day_of_month and self.rng.random() < 0.55:
            word = self.rng.choice(ORDINALS + ["poslednji"])
            if gender == "f":
                word = semantic.ordinal_feminine(word)
            self.add(word, label)
            return
        if day_of_month and self.rng.random() < 0.3:
            word = DAY_ORDINALS[value - 1]
            self.add(word, label)
            return
        self.add(str(value), label)
        self.add(".", separator="")

    def clock(self, style: int | None = None) -> None:
        style = self.rng.randrange(8) if style is None else style
        if style == 0:
            self.add(self.rng.choice(["podne", "ponoć", "ponoc"]), "TIME_NAMED")
            return
        if style == 1:
            self.add(
                self.rng.choice(["jutro", "popodne", "veče", "noć"]), "DAYPART"
            )
            return
        meridiem = style in (2, 3, 4)
        hour = self.rng.randint(1, 12) if meridiem else self.rng.randint(0, 23)
        self.add(
            NUMBERS[hour]
            if style == 7 and hour <= 12 and self.rng.random() < 0.2
            else str(hour),
            "HOUR",
        )
        if style in (3, 4, 5, 6):
            self.add(":", separator="")
            self.add(f"{self.rng.randint(0, 59):02d}", "MINUTE", separator="")
        if style in (4, 6):
            self.add(":", separator="")
            self.add(f"{self.rng.randint(0, 59):02d}", "SECOND", separator="")
        if meridiem:
            marker = self.rng.choice(
                ["ujutru", "izjutra", "popodne", "uveče", "uvece", "noću", "nocu"]
            )
            self.add(marker, "MERIDIEM", separator=self.rng.choice(["", " "]))

    def window(self, variant: int) -> None:
        if variant % 3 == 0:
            self.add("od", "RANGE_START")
        elif variant % 3 == 1:
            self.add("između", "RANGE_START")
        self.clock(self.rng.choice([2, 3, 5, 6, 7]))
        connector = (
            "i"
            if variant % 3 == 1
            else self.rng.choice(["-", "–", "do", "pre"])
        )
        self.add(
            connector, "RANGE_END", separator="" if connector in ("-", "–") else " "
        )
        self.clock(self.rng.choice([0, 2, 3, 5, 7]))

    def day_of_month(self, day: int, spoken: bool = False) -> None:
        if spoken or self.rng.random() < 0.3:
            word = DAY_ORDINALS[day - 1]
            self.add(word, "DOM")
            return
        self.add(str(day), "DOM")

    def date(self, variant: int) -> None:
        month = self.rng.randint(1, 12)
        day = self.rng.randint(1, 28)
        year = self.rng.randint(1990, 2035)
        if variant % 3 == 0:
            self.add(str(year), "YEAR")
            self.add("-", separator="")
            self.add(f"{month:02d}", "MONTH", separator="")
            self.add("-", separator="")
            self.add(f"{day:02d}", "DOM", separator="")
        elif variant != 8:
            # Day-before-month is the common Serbian prose order (matches the
            # DMY default); month-first stays available as a minority style.
            self.day_of_month(day)
            self.add(
                self.rng.choice([MONTHS[month - 1], MONTHS[month - 1][:3]]), "MONTH"
            )
            if self.rng.random() < 0.5:
                self.add(str(year), "YEAR")
        else:
            self.add(
                self.rng.choice([MONTHS[month - 1], MONTHS[month - 1][:3]]), "MONTH"
            )
            self.day_of_month(day)
            if self.rng.random() < 0.5:
                self.add(",", separator="")
                self.add(str(year), "YEAR")

    def recurrence(self, variant: int) -> None:
        if variant % 3 == 0:
            self.add(self.rng.choice(["svaki", "svako"]), "RECUR")
            add_num = self.rng.random() < 0.45
            if add_num:
                name = self.rng.choice(DAYS)
                self.add(
                    semantic.two_word(semantic.weekday_gender(name), ordinal=True),
                    "NUM",
                )
                self.days(name)
            else:
                self.days()
        elif variant % 3 == 1:
            self.add("svaki", "RECUR")
            unit_id = self.rng.choice(
                ["hour", "day", "week", "week_sedmica", "month", "year"]
            )
            amount = self.quantity(
                self.rng.randint(1, 6), gender=semantic.unit_gender(unit_id)
            )
            self.add(semantic.unit_form(amount, unit_id), "UNIT")
            if self.rng.random() < 0.5:
                self.add("u")
                self.day()
        else:
            self.add(
                self.rng.choice(
                    [
                        "dnevno",
                        "svakodnevno",
                        "nedeljno",
                        "sedmično",
                        "dvonedeljno",
                        "petnaestodnevno",
                        "mesečno",
                        "godišnje",
                    ]
                ),
                "FREQ",
            )
        if self.rng.random() < 0.6:
            self.add("u")
            self.clock()


def render(family: int, variant: int, rng: random.Random) -> Sentence:
    sentence = Sentence(rng)
    if rng.random() < 0.45:
        sentence.add(background.prefix(rng))
    sentence.clause()
    if family == 0:  # A weekday list shares a clock or a window.
        if variant == 8:
            sentence.clock()
            sentence.add(rng.choice([",", "na", "za", "—"]))
            sentence.days()
            return sentence
        name = None
        if variant % 3 == 0:
            name = rng.choice(DAYS)
            flavor = rng.choice(["sledeći", "ovaj", "prošli", "naredni", "prethodni"])
            sentence.add(
                DEICTIC_FORMS[flavor][semantic.weekday_gender(name)], "DEICTIC"
            )
        sentence.days(name)
        if rng.random() < 0.3:
            return sentence
        if variant % 2:
            sentence.add(rng.choice(["u", "na"]))
            sentence.clock()
        else:
            sentence.window(variant)
    elif family == 1:  # Relative quantity, with both prefix and suffix direction.
        if variant == 6:
            sentence.quantity_unit()
            sentence.add("od", "DIR_AFTER")
            sentence.add("sada", "NOW")
            return sentence
        if variant == 8:
            sentence.add("tačno")
            sentence.add("posle", "DIR_AFTER")
            sentence.quantity_unit()
            return sentence
        if variant % 2:
            sentence.add(rng.choice(["za", "posle"]), "DIR_AFTER")
        sentence.quantity_unit()
        if variant % 2 == 0:
            marker = rng.choice(["pre", "unazad", "ranije", "posle", "kasnije", "otad"])
            sentence.add(
                marker,
                "DIR_BEFORE" if marker in ("pre", "unazad", "ranije") else "DIR_AFTER",
            )
    elif family == 2:  # Relative quantity anchored to a date, not the reference.
        if variant == 8:
            sentence.add("pre", "DIR_BEFORE")
            sentence.date(0)
            sentence.add("za")
            amount = sentence.quantity()
            sentence.add(semantic.unit_form(amount, "day"), "UNIT")
            return sentence
        if variant in (0, 3):
            sentence.add(rng.choice(["tačno", "upravo", "još", "dodatnih"]))
        sentence.quantity_unit()
        marker = rng.choice(["pre", "posle"])
        sentence.add(marker, "DIR_BEFORE" if marker == "pre" else "DIR_AFTER")
        if variant % 3 == 0:
            sentence.add(rng.choice(HOLIDAYS), "HOLIDAY")
        elif variant % 3 == 1:
            sentence.add(rng.choice(["danas", "sutra", "juče"]), "REL_DAY")
            sentence.add("u")
            sentence.clock()
        else:
            sentence.day()
    elif family == 3:
        if variant in (6, 7):
            sentence.clock()
            sentence.add("svaki", "RECUR")
            sentence.days()
        elif variant == 8:
            sentence.days()
            sentence.clock()
            sentence.add("nedeljno", "FREQ")
        else:
            sentence.recurrence(variant)
    elif family == 4:
        sentence.date(variant)
        if rng.random() < 0.65:
            sentence.add("u")
            sentence.clock()
    elif family == 5:  # No connector is required between separately timed clauses.
        for clause in range(rng.randint(2, 3)):
            if clause:
                connector = rng.choice(["i", ",", ";", "zatim", "", "i zatim"])
                if connector:
                    sentence.add(connector, "JOIN")
                sentence.clause()
            if rng.random() < 0.25:
                sentence.add("svaki", "RECUR")
            if variant in (2, 6):
                sentence.clock()
                sentence.add(rng.choice(["—", ",", "za", "na", "u"]))
                sentence.days()
                continue
            sentence.days()
            if rng.random() < 0.65:
                sentence.window(variant + clause)
            else:
                sentence.clock()
    elif family == 6:
        name = rng.choice(DAYS)
        sentence.ordinal(gender=semantic.weekday_gender(name))
        sentence.day(name)
        sentence.add("od")
        if variant % 2:
            sentence.add("svaki", "RECUR")
        else:
            sentence.add(rng.choice(["sledeći", "ovaj", "prošli"]), "DEICTIC")
        sentence.add("mesec", "UNIT")
    elif family == 7:
        if variant % 2:
            sentence.ordinal("DOM", day_of_month=True)
            sentence.add("i")
            sentence.ordinal("DOM", day_of_month=True)
            sentence.add("od")
            sentence.add(rng.choice(["svako", "svaki"]), "RECUR")
            sentence.add("mesec", "UNIT")
            return sentence
        sentence.add("svaki", "RECUR")
        sentence.add("mesec", "UNIT")
        sentence.ordinal("DOM", day_of_month=True)
        if rng.random() < 0.4:
            sentence.add("i")
            sentence.ordinal("DOM", day_of_month=True)
    elif family == 8:
        if variant == 8:
            sentence.add("svaki", "RECUR")
            sentence.add(rng.choice(MONTHS), "MONTH")
            sentence.ordinal("DOM", day_of_month=True)
            return sentence
        sentence.add("svaki", "RECUR")
        if variant % 2:
            sentence.add("druga", "NUM")
        sentence.add("godina", "UNIT")
        sentence.ordinal("DOM", day_of_month=True)
        sentence.add("od")
        sentence.add(rng.choice(MONTHS), "MONTH")
    elif family == 9:
        if variant % 2:
            sentence.add(
                rng.choice(["danas", "sutra", "juče", "večeras"]), "REL_DAY"
            )
        else:
            if rng.random() < 0.4:
                sentence.add(rng.choice(["kraj", "početak"]), "EDGE")
                sentence.add("od")
            flavor = rng.choice(["sledeći", "ovaj", "prošli"])
            unit_id = rng.choice(["nedelja", "mesec", "godina"])
            gender = "f" if unit_id in ("nedelja", "godina") else "m"
            sentence.add(DEICTIC_FORMS[flavor][gender], "DEICTIC")
            sentence.add(unit_id, "UNIT")
        if rng.random() < 0.6:
            sentence.clock()
    elif family == 10:
        sentence.recurrence(variant)
        if variant == 5:
            sentence.add(rng.choice(["do", "sve do"]), "BOUND_END")
            sentence.day()
            return sentence
        if variant in (2, 4, 6):
            sentence.add(
                rng.choice(["do", "sve do", "zaključno sa"]), "BOUND_END"
            )
            sentence.add("kraj", "EDGE")
            sentence.add(rng.choice(["nedelja", "mesec", "godina"]), "UNIT")
            return sentence
        sentence.add(rng.choice(["od", "počev od", "počevši od"]), "BOUND_START")
        if variant % 2:
            sentence.add("naredna", "DEICTIC")
            sentence.add("nedelja", "UNIT")
        else:
            sentence.date(variant)
        if rng.random() < 0.5:
            sentence.add(
                rng.choice(["do", "sve do", "zaključno sa", "do kraja"]), "BOUND_END"
            )
            sentence.add(rng.choice(MONTHS), "MONTH")
            if rng.random() < 0.5:
                sentence.quantity(rng.randint(1, 31), "DOM")
    elif family == 11:
        if variant == 8:
            sentence.quantity(rng.randint(1, 12))
            sentence.add("još")
            sentence.add("puta", "COUNT")
            sentence.add("dnevno", "FREQ")
            return sentence
        sentence.recurrence(variant)
        if variant % 2:
            sentence.add("za")
            sentence.quantity(rng.randint(1, 12))
            sentence.add(rng.choice(["puta", "navrata"]), "COUNT")
        else:
            sentence.add("za", "DUR")
            unit_id = rng.choice(["day", "week", "week_sedmica", "month"])
            amount = rng.randint(1, 12)
            sentence.quantity(amount, gender=semantic.unit_gender(unit_id))
            sentence.add(semantic.unit_form(amount, unit_id), "UNIT")
    elif family == 12:
        if variant == 8:
            sentence.add("osim", "EXCEPT")
            sentence.days()
            sentence.add("dnevno", "FREQ")
            return sentence
        sentence.add("svaki", "RECUR")
        if rng.random() < 0.35:
            sentence.add(rng.choice(["dan", "dana"]), "UNIT")
        else:
            sentence.add(
                rng.choice(
                    ["radni dan", "radni dani", "vikend", "vikendi", "radnim danima"]
                ),
                "DAYGROUP",
            )
        sentence.add(rng.choice(["osim", "izuzev", "sem"]), "EXCEPT")
        sentence.days()
    elif family == 13:
        if variant == 8:
            sentence.add("u")
            sentence.clock()
            amount = sentence.quantity()
            sentence.add(semantic.unit_form(amount, "hour"), "UNIT")
            sentence.add("trajanje", "DUR")
            return sentence
        if variant in (0, 3):
            sentence.add(rng.choice(["od", "počev od"]), "BOUND_START")
            sentence.add("od", "RANGE_START")
            sentence.add(rng.choice(["danas", "sutra", "juče"]), "REL_DAY")
        elif variant not in (1, 4):
            sentence.clock()
        sentence.add(rng.choice(["za", "trajanje"]), "DUR")
        if rng.random() < 0.5:
            sentence.add(rng.choice(["sledeći", "naredni"]), "DEICTIC")
        sentence.quantity_unit()
    elif family == 14:
        if variant == 8:
            sentence.add("nedeljno", "FREQ")
            sentence.add(rng.choice(["jednom", "dvaput", "triput"]), "TIMES")
            return sentence
        if variant % 2:
            sentence.add(rng.choice(["jednom", "dvaput", "triput"]), "TIMES")
        else:
            sentence.quantity(rng.randint(2, 6))
            sentence.add("puta", "TIMES")
        if variant % 3 == 0:
            sentence.add("na", "RECUR")
        sentence.add(rng.choice(["dan", "nedelju"]), "UNIT")
    elif family == 15:
        if variant in (1, 3, 5):
            sentence.quantity(rng.randint(1, 28), "DOM")
            sentence.add(rng.choice(MONTHS), "MONTH")
            sentence.add(rng.choice(["-", "–", "do", "zaključno sa"]), "RANGE_END")
            sentence.quantity(rng.randint(1, 28), "DOM")
            sentence.add(rng.choice(MONTHS), "MONTH")
            return sentence
        sentence.add(rng.choice(MONTHS), "MONTH")
        if variant == 8:
            sentence.add("između", "RANGE_START")
        sentence.quantity(rng.randint(1, 14), "DOM")
        sentence.add(
            "i" if variant == 8 else rng.choice(["-", "–", "do"]), "RANGE_END"
        )
        sentence.quantity(rng.randint(15, 28), "DOM")
        if rng.random() < 0.5:
            sentence.add(",")
            sentence.add(str(rng.randint(2024, 2030)), "YEAR")
    elif family == 16:
        sentence.day()
        sentence.add(rng.choice(["-", "do", "kroz"]), "RANGE_END")
        sentence.day()
        if rng.random() < 0.7:
            sentence.window(variant)
    elif family == 17:
        sentence.clock()
    elif family == 18:
        sentence.window(variant)
    elif family == 19:
        sentence.add("za", "DIR_AFTER")
        sentence.quantity(rng.randint(1, 5))
        sentence.add("do", "RANGE_END")
        unit_id = rng.choice(["minute", "hour", "day"])
        amount = sentence.quantity(rng.randint(6, 12), gender=semantic.unit_gender(unit_id))
        sentence.add(semantic.unit_form(amount, unit_id), "UNIT")
    elif family == 20:
        sentence.add(rng.choice(["sada", "sad", "odmah"]), "NOW")
    elif family == 21:
        sentence.add(rng.choice(["danas", "sutra", "juče"]), "REL_DAY")
        if variant % 2:
            lead = rng.choice(["rano", "kasno", ""])
            if lead:
                sentence.add(lead)
        sentence.add(
            rng.choice(["jutro", "popodne", "veče", "noć"]), "DAYPART"
        )
    elif family == 22:
        sentence.add("prekosutra", "REL_DAY")
    else:
        sentence = Sentence(rng)
        if rng.random() < 0.85:
            sentence.add(background.sentence(rng))
            return sentence
        count = rng.randint(1, 99)
        year = rng.randint(1990, 2035)
        name = rng.choice(["Ana", "Marko", "Jovana", "Petar", "Milica", "Nikola", "Ivana"])
        sentence.add(
            rng.choice(
                [
                    "Mogu li da čujem vaše drugo mišljenje?",
                    f"Molim vas, pozovite {count} ljudi u sobi {rng.randint(1, 40)}.",
                    f"Poslednji slajd ima {count} dijagrama za {name}.",
                    "Marširamo zajedno i možemo uspeti.",
                    f"Verzija {year} ima {count} grešaka i upozorenja.",
                    f"Molim vas, pošaljite izveštaj {name}.",
                    "Naš drugi pokušaj je bio poslednji.",
                    "Mesec je jedinica u ovom rečniku.",
                    "Od Ane do Petra, poruka kaže zdravo.",
                    f"Ovaj broj je {count}, a onaj je {year}.",
                ]
            )
        )
    return sentence


TERSE_GROUPS = ["vikendi", "vikend", "radni dani", "radni dan"]


def dash(sentence: Sentence, choices: list[str]) -> None:
    connector = sentence.rng.choice(choices)
    sentence.add(
        connector,
        "RANGE_END",
        separator="" if connector in ("-", "–") else " ",
    )


def terse(sentence: Sentence, variant: int) -> str:
    rng = sentence.rng
    sentence.clause()
    shape = rng.randrange(8)
    if shape == 0:
        sentence.add(rng.choice(TERSE_GROUPS), "DAYGROUP")
    elif shape == 1:
        sentence.day()
        dash(sentence, ["-", "–", "do", "kroz"])
        sentence.day()
    elif shape == 2:
        name = MONTHS[rng.randint(1, 12) - 1]
        sentence.add(rng.choice([name, name[:3]]), "MONTH")
        first = rng.randint(1, 20)
        sentence.add(str(first), "DOM")
        dash(sentence, ["-", "–", "do"])
        sentence.add(str(rng.randint(first + 1, 28)), "DOM")
    elif shape == 3:
        sentence.window(variant)
    elif shape == 4:
        sentence.window(variant)
        sentence.day()
        dash(sentence, ["-", "–", "do"])
        sentence.day()
    elif shape == 5:
        day = rng.randint(1, 28)
        name = MONTHS[rng.randint(1, 12) - 1]
        if rng.random() < 0.8:  # day-first is the common Serbian prose order
            sentence.day_of_month(day, spoken=True)
            sentence.add("od")
            sentence.add(rng.choice([name, name[:3]]), "MONTH")
        else:
            sentence.add(rng.choice([name, name[:3]]), "MONTH")
            sentence.day_of_month(day, spoken=True)
    elif shape == 6:
        sentence.add(rng.choice(["za", "kroz"]), "DIR_AFTER")
        value = rng.choice([13, 15, 20, 21, 24, 25, 35, 40, 45])
        tens, ones = divmod(value, 10)
        if tens >= 2 and ones:
            joiner = rng.choice([" ", " i "])
            spoken = TENS[tens * 10] + joiner + NUMBERS[ones]
        elif tens >= 2:
            spoken = TENS[tens * 10]
        else:
            spoken = NUMBERS[value] if value <= 12 else str(value)
        sentence.add(spoken, "NUM")
        unit_id = rng.choice(["minute", "hour", "day"])
        sentence.add(semantic.unit_form(value, unit_id), "UNIT")
    else:
        pick = rng.randrange(4)
        if pick == 0:
            sentence.add(
                rng.choice(["prekjuče", "prekosutra", "juce"]),
                "REL_DAY",
            )
        elif pick == 1:
            sentence.add(rng.choice(["par", "nekoliko"]), "NUM")
            sentence.add(rng.choice(["dana", "nedelje", "sata"]), "UNIT")
            sentence.add("unazad", "DIR_BEFORE")
        elif pick == 2:
            sentence.add("za", "DIR_AFTER")
            sentence.add(rng.choice(["par", "nekoliko"]), "NUM")
            sentence.add(rng.choice(["dana", "nedelje", "sata"]), "UNIT")
        else:
            unit_choice = rng.choice(["ned", "nedelja", "mes", "mesec"])
            gender = "f" if unit_choice in ("ned", "nedelja") else "m"
            flavor = rng.choice(["sledeći", "ovaj"])
            deictic_word = (
                {"sledeći": "sledeći", "ovaj": "ovaj"}[flavor]
                if gender == "m"
                else {"sledeći": "sledeca", "ovaj": "ova"}[flavor]
            )
            sentence.add(deictic_word, "DEICTIC")
            sentence.add(unit_choice, "UNIT")
    return f"terse-{shape}"


def render_heldout(family: int, rng: random.Random) -> Sentence:
    """Alternative frames, not renamed copies of the training templates."""
    sentence = Sentence(rng)
    if rng.random() < 0.45:
        sentence.add(background.prefix(rng))
    sentence.clause()
    if family == 0:
        sentence.add("u")
        sentence.clock()
        sentence.add("u")
        sentence.days()
    elif family == 1:
        sentence.add("za", "DIR_AFTER")
        sentence.add(rng.choice(["tačno", "upravo", "još"]))
        unit_id = rng.choice(UNITS)
        amount = sentence.quantity(gender=semantic.unit_gender(unit_id))
        sentence.add(semantic.unit_form(amount, unit_id), "UNIT")
    elif family == 2:
        sentence.add("pre", "DIR_BEFORE")
        sentence.add(rng.choice(HOLIDAYS), "HOLIDAY")
        sentence.add("za")
        amount = sentence.quantity()
        sentence.add(semantic.unit_form(amount, "day"), "UNIT")
    elif family == 3:
        sentence.add("u")
        sentence.days()
        sentence.add("svako", "RECUR")
        sentence.add("nedelja", "UNIT")
        sentence.add("u")
        sentence.clock()
    elif family == 4:
        sentence.ordinal("DOM", day_of_month=True)
        sentence.add("od")
        sentence.add(rng.choice(MONTHS), "MONTH")
        sentence.add(str(rng.randint(2024, 2035)), "YEAR")
    elif family == 5:
        for clause in range(rng.randint(2, 3)):
            if clause:
                sentence.add(";", "JOIN")
                sentence.clause()
            sentence.clock(2)
            sentence.add("u")
            sentence.days()
    elif family == 6:
        sentence.add("sledeći", "DEICTIC")
        sentence.add("mesec", "UNIT")
        name = rng.choice(DAYS)
        sentence.ordinal(gender=semantic.weekday_gender(name))
        sentence.day(name)
    elif family == 7:
        sentence.ordinal("DOM", day_of_month=True)
        sentence.add("i")
        sentence.ordinal("DOM", day_of_month=True)
        sentence.add("mesečno", "FREQ")
    elif family == 8:
        sentence.add("svako", "RECUR")
        sentence.add(rng.choice(MONTHS), "MONTH")
        sentence.ordinal("DOM", day_of_month=True)
    elif family == 9:
        sentence.clock()
        sentence.add("u")
        sentence.add(rng.choice(["danas", "sutra", "juče"]), "REL_DAY")
    elif family == 10:
        sentence.add("od", "BOUND_START")
        sentence.add("sutra", "REL_DAY")
        sentence.add("nedeljno", "FREQ")
    elif family == 11:
        sentence.quantity(rng.randint(1, 12))
        sentence.add("još")
        sentence.add("puta", "COUNT")
        sentence.add("od", "BOUND_START")
        sentence.add("sutra", "REL_DAY")
        sentence.add("nedeljno", "FREQ")
    elif family == 12:
        sentence.add("izuzev", "EXCEPT")
        sentence.day()
        sentence.add("radni dani", "DAYGROUP")
        sentence.add("u")
        sentence.clock()
    elif family == 13:
        amount = sentence.quantity()
        sentence.add(semantic.unit_form(amount, "hour"), "UNIT")
        sentence.add("trajanje", "DUR")
        sentence.add("u")
        sentence.clock()
    elif family == 14:
        sentence.add("na", "RECUR")
        sentence.add("nedelju", "UNIT")
        sentence.add(rng.choice(["jednom", "dvaput", "triput"]), "TIMES")
    elif family == 15:
        sentence.add(rng.choice(MONTHS), "MONTH")
        sentence.add("od", "RANGE_START")
        sentence.quantity(rng.randint(1, 14), "DOM")
        sentence.add("do", "RANGE_END")
        sentence.quantity(rng.randint(15, 28), "DOM")
    elif family == 16:
        sentence.window(2)
        sentence.add("svaki", "RECUR")
        sentence.day()
        sentence.add("do", "RANGE_END")
        sentence.day()
    elif family == 17:
        sentence.add("u")
        sentence.clock(2)
    elif family == 18:
        sentence.add("između", "RANGE_START")
        sentence.add(rng.choice(["podne", "ponoć"]), "TIME_NAMED")
        sentence.add("i", "RANGE_END")
        sentence.clock(2)
    elif family == 19:
        sentence.quantity(rng.randint(1, 5))
        sentence.add("do", "RANGE_END")
        amount = sentence.quantity(rng.randint(6, 12))
        sentence.add(semantic.unit_form(amount, "minute"), "UNIT")
        sentence.add("kasnije", "DIR_AFTER")
    elif family == 20:
        sentence.add("baš")
        sentence.add("sada", "NOW")
    elif family == 21:
        sentence.add("rano")
        sentence.add("jutro", "DAYPART")
        sentence.add("sutra", "REL_DAY")
    elif family == 22:
        sentence.add("prekosutra", "REL_DAY")
        sentence.add("u")
        sentence.clock()
    else:
        sentence = Sentence(rng)
        sentence.add(background.sentence(rng))
    return sentence


def generate(
    path: Path, count: int, seed: int, split: str, exclude: Path | None = None
) -> dict:
    rng = random.Random(seed)
    variants = [9] if split == "heldout" else list(range(9))
    families = Counter()
    span_counts = Counter()
    templates = set()
    signatures = set()
    reserved = set(json.loads(exclude.read_text())) if exclude else set()
    rejected = 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as output:
        index = 0
        while index < count:
            family = rng.choices(
                range(24),
                weights=[
                    18,
                    8,
                    7,
                    14,
                    10,
                    12,
                    5,
                    4,
                    3,
                    6,
                    6,
                    5,
                    4,
                    4,
                    3,
                    4,
                    4,
                    2,
                    5,
                    3,
                    1,
                    3,
                    2,
                    24,
                ],
            )[0]
            variant = rng.choice(variants)
            spec = semantic.sample(rng) if family != 23 and rng.random() < 0.8 else None
            if rng.random() < 0.12:
                sentence = Sentence(rng)
                template = terse(sentence, variant)
                spec = None
            elif rng.random() < 0.4:
                sentence = Sentence(rng, augment=False)
                spec = natural.render(sentence, reserved=split == "heldout")
                template = f"natural-{spec.family}/" + ("reserved" if split == "heldout" else "train")
            elif spec:
                sentence = Sentence(rng)
                semantic.render(spec, sentence, variant)
                template = f"semantic-{spec.family}/surface-{variant}"
            else:
                sentence = (
                    render_heldout(family, rng)
                    if split == "heldout"
                    else render(family, variant, rng)
                )
                template = f"family-{family:02d}/" + (
                    "heldout-reordered" if split == "heldout" else f"surface-{variant}"
                )
            if sentence.clauses and rng.random() < 0.3:
                sentence.in_expression = False
                tail = background.suffix(rng)
                if tail[:1].isupper():
                    sentence.add(".", separator="")
                sentence.add(tail)
            row = {
                "id": f"{split}-{seed}-{index}",
                "template": template,
                "text": sentence.text,
                "spans": sentence.spans,
            }
            if spec:
                row["schedule"] = spec.schedule
            key = fingerprint(row)
            if key in reserved:
                rejected += 1
                continue
            row["fingerprint"] = key
            signatures.add(key)
            index += 1
            output.write(
                json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
            )
            families[spec.family if spec else family] += 1
            span_counts.update(span["label"] for span in sentence.spans)
            templates.add(template)
    path.with_suffix(".fingerprints.json").write_text(json.dumps(sorted(signatures)))
    prose = background.borrowed()
    return {
        "structuralFingerprints": len(signatures),
        "rejectedReservedFrames": rejected,
        "generatorSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "borrowedProse": len(prose),
        "borrowedProseSha256": (
            hashlib.sha256(background.PROSE.read_bytes()).hexdigest() if prose else None
        ),
        "sequences": count,
        "seed": seed,
        "split": split,
        "templates": sorted(templates),
        "families": dict(families),
        "spanCounts": dict(span_counts),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=300000)
    parser.add_argument("--seed", type=int, default=20260909)
    parser.add_argument(
        "--split", choices=["train", "validation", "heldout"], default="train"
    )
    parser.add_argument("--exclude", type=Path)
    parser.add_argument(
        "--out", type=Path, default=ROOT / "data/synth/train.jsonl"
    )
    args = parser.parse_args()
    report = generate(args.out, args.count, args.seed, args.split, args.exclude)
    args.out.with_suffix(".manifest.json").write_text(
        json.dumps(report, indent=2) + "\n"
    )
    print(json.dumps(report))
