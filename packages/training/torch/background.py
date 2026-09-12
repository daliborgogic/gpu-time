"""Non-temporal language for contextual contrast with the time grammar."""

import random
from functools import lru_cache
from pathlib import Path

# The genuine preposition subset of compile.ts's filler set (u/na/od/za) --
# mirrors what can actually collide as a double-preposition glue artifact.
CONNECTORS = frozenset({"u", "na", "od", "za"})

PROSE = Path(__file__).resolve().parent.parent / "data/prose/sentences.txt"
RESERVED: set[str] = set()

ACTORS = ["ja", "mi", "ti", "oni"]
MODALS = ["ću", "ćemo", "možda", "trebalo bi da"]
STATES = ["biti odsutan", "biti ovde", "biti dostupan", "vratiti se"]
PLACES = ["kancelarija", "naša klinika", "prodavnica", "biblioteka"]
OPENINGS = ["je otvorena", "je zatvorena", "se otvara", "se zatvara"]
DETERMINERS = ["", "naš", "moj"]
EVENTS = ["sastanak", "termin", "intervju", "poziv", "čas"]
PREDICATES = ["je", "počinje", "je zakazan"]
LEADS = ["", "molim vas", "možete li", "da li možete", "želeo bih da"]
ASKS = [
    "zakažite {event}",
    "rezervišite {event}",
    "potvrdite {event}",
    "rezervišite sobu {room}",
    "podesite alarm",
    "podsetite me",
    "podsetite me da pozovem {name}",
]
NAMES = ["Ana", "Marko", "Jovana", "Petar", "Milica", "Nikola", "Ivana"]
ASIDES = ["", "", "", "molim,", "napomena:", "možete li pogledati ovo:"]
RECIPIENTS = ["mene", "nas", "tim"] + NAMES


def normal(text: str) -> str:
    return " ".join(text.lower().split())


def reserve(phrases) -> None:
    RESERVED.update(normal(phrase) for phrase in phrases)


@lru_cache(maxsize=1)
def borrowed() -> tuple[str, ...]:
    try:
        lines = PROSE.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ()
    # Carriers share the 32/64/128-token buckets train.py batches on.
    return tuple(line for line in map(str.strip, lines) if 0 < len(line) <= 120)


def _availability(rng: random.Random) -> tuple[str, tuple[str, ...]]:
    actor, modal = rng.choice(ACTORS), rng.choice(MODALS)
    return f"{actor} {modal} {rng.choice(STATES)}", ("u", "na", "za")


def _hours(rng: random.Random) -> tuple[str, tuple[str, ...]]:
    return f"{rng.choice(PLACES)} {rng.choice(OPENINGS)}", ("u", "na", "za")


def _event(rng: random.Random) -> tuple[str, tuple[str, ...]]:
    determiner, event = rng.choice(DETERMINERS), rng.choice(EVENTS)
    return f"{determiner} {event} {rng.choice(PREDICATES)}", ("u", "na")


def _request(rng: random.Random) -> tuple[str, tuple[str, ...]]:
    ask = rng.choice(ASKS).format(
        event=rng.choice(EVENTS), room=rng.randint(1, 50), name=rng.choice(NAMES)
    )
    return f"{rng.choice(LEADS)} {ask}".strip(), ("za", "u", "na", "o")


SHAPES = [_availability, _hours, _event, _request]


def _compose(rng: random.Random, connector: bool) -> str:
    body, connectors = rng.choice(SHAPES)(rng)
    if connector and rng.random() < 0.85:
        body += " " + rng.choice(connectors)
    return f"{rng.choice(ASIDES)} {body}".strip()


def _terminated(text: str) -> str:
    return text if text[-1] in ".!?" else text + "."


def prefix(rng: random.Random, connector: bool = True) -> str:
    """Ordinary prose before a time expression; every token is background."""
    pool = borrowed()
    while True:
        if pool and rng.random() < 0.2:
            text = _terminated(rng.choice(pool))
        else:
            text = _compose(rng, connector)
        if normal(text) not in RESERVED:
            return text


def suffix(rng: random.Random) -> str:
    pool = borrowed()
    while True:
        if pool and rng.random() < 0.2:
            text = _terminated(rng.choice(pool))
        elif rng.random() < 0.3:
            text = f"i {_availability(rng)[0]}"
        else:
            text = rng.choice(
                [
                    f"odgovara {rng.choice(RECIPIENTS)}",
                    f"za {rng.choice(RECIPIENTS)}",
                    f"ako to odgovara {rng.choice(RECIPIENTS)}",
                    "je krajnji rok",
                    "molim",
                ]
            )
        if normal(text) not in RESERVED:
            return text


def sentence(rng: random.Random) -> str:
    pool = borrowed()
    if pool and rng.random() < 0.15:
        return rng.choice(pool)
    if rng.random() < 0.12:
        subject = rng.choice(
            ["Naša klinika", "Kancelarija", "Prodavnica", "Tim", "Biblioteka"]
        )
        purpose = rng.choice(
            ["pitanja", "diskusiju", "povratne informacije", "predloge", "komentare"]
        )
        return f"{subject} prima {purpose}."
    if rng.random() < 0.25:
        modifier = rng.choice(["sledeći", "prethodni", "prošli", "prvi", "drugi"])
        subject = rng.choice(["korak", "pokušaj", "zadatak", "deo", "odeljak"])
        action = rng.choice(
            ["otvoriti", "pročitati", "pregledati", "kontrolisati", "kopirati", "zatvoriti"]
        )
        item = rng.choice(["fajl", "izveštaj", "dokument", "meni", "prozor"])
        return f"{modifier.capitalize()} {subject} je {action} {item}."
    noun = rng.choice(
        [
            "fajl",
            "dokument",
            "izveštaj",
            "poglavlje",
            "knjiga",
            "priča",
            "tabela",
            "kolona",
            "red",
            "prozor",
            "meni",
            "program",
            "spisak",
            "paragraf",
            "poruka",
            "nacrt",
            "strana",
            "odeljak",
            "opcija",
            "primer",
            "korak",
        ]
    )
    verb = rng.choice(
        [
            "otvoriti",
            "zatvoriti",
            "pročitati",
            "pregledati",
            "štampati",
            "izabrati",
            "poslati",
            "kontrolisati",
            "kopirati",
            "odobriti",
        ]
    )
    order = rng.choice(["prvi", "drugi", "treći", "poslednji", "sledeći", "prethodni"])
    name = rng.choice(NAMES)
    count = rng.randint(1, 99)
    version = rng.randint(1990, 2040)
    phrase = rng.choice(
        [
            f"Molim, treba {verb} {order} {noun}.",
            f"Možete li {verb} {noun} za {name}?",
            f"{order.capitalize()} {noun} sadrži {count} primera.",
            f"{noun.capitalize()} ima {count} redova i {rng.randint(1, 31)} kolona.",
            f"Početak od {noun} objašnjava format.",
            f"Na kraju {noun}, autor to potpisuje.",
            f"Možemo {verb} još jedan {noun}.",
            f"{name} je napisao {order} {noun}.",
            f"Pošaljite {order} {noun} osobi {name}.",
            f"Verzija {version} nije uspela sa {count} upozorenja.",
            f"Izaberite opciju {count} iz odeljka {rng.randint(1, 12)}.",
            f"{order.capitalize()} pokušaj je uspeo.",
            f"Svaki {noun} treba naslov.",
            f"Svaki {noun} na spisku sadrži broj.",
            f"Polje po imenu {rng.choice(['godina', 'vremenska oznaka', 'datum', 'trajanje'])} sadrži tekst.",
            f"Reč {rng.choice(['ponoć', 'sutra', 'jutro', 'vikend'])} se pojavljuje u rečniku.",
            f"Od {name} do Marka, poruka kaže zdravo.",
            f"Između dve opcije, {name} bira {order} izbor.",
            "Vojnici marširaju preko trga.",
            "Marširajte u pravoj liniji prema kapiji.",
            "Ova izmena izgleda ispravno.",
        ]
    )
    if rng.random() < 0.4:
        phrase = (
            rng.choice(["Molim, ", "Možete li pogledati ovo: ", "Napomena: "])
            + phrase[0].lower()
            + phrase[1:]
        )
    return phrase


if __name__ == "__main__":
    # Running this file as a script gives natural.py a second background module,
    # so the registration its import performs has to be repeated here.
    import natural

    reserve(natural.RESERVED + natural.RESERVED_DURATION)
    PROSE = Path("/nonexistent")
    borrowed.cache_clear()
    rng = random.Random(20260909)
    drawn = {normal(prefix(rng)) for _ in range(200000)}
    drawn |= {normal(prefix(rng, connector=False)) for _ in range(200000)}
    drawn |= {normal(suffix(rng)) for _ in range(200000)}
    assert not drawn & RESERVED
    assert len(drawn) > 5000, len(drawn)
    print(len(drawn))
