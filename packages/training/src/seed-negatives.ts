import { writeFileSync } from "node:fs";

const gold = new URL("../data/gold/", import.meta.url);

// Deliberately non-temporal sentences, including words that can be time words
// in other contexts. These are authored development checks, not training data.
const texts = [
  "Mogu li da čujem vaše drugo mišljenje?",
  "Možeš li poslati drugi nacrt Maji?",
  "Maja je napisala uvod u knjigu.",
  "Možemo objaviti još jedno izdanje.",
  "Vojnici marširaju preko trga.",
  "Molim vas, marširajte u pravoj liniji.",
  "Naš drugi pokušaj je uspeo.",
  "Nagrada za prvo mesto je otišla Aleksu.",
  "Ovo je poslednja stavka na spisku.",
  "Sledeći korak je da se otvori fajl.",
  "Prethodna verzija je imala drugačiji naslov.",
  "Na početku knjige, pripovedač govori.",
  "Kraj priče je iznenadio sve.",
  "Pokrenite program i otvorite meni.",
  "Tabela sadrži 12 kolona i 31 red.",
  "Verzija 2026 nije uspela sa 3 upozorenja.",
  "Molim vas, izaberite opciju 2 iz odeljka 3.",
  "Izveštaj ima 90 stranica.",
  "Pozovite 5 ljudi zbog dokumenta.",
  "Soba 10 sadrži 8 stolica.",
  "Poslao je fajl Jovanu.",
  "Molim vas, zatvorite prozor.",
  "Ova izmena izgleda ispravno.",
  "Od Ane do Bore, poruka kaže zdravo.",
  "Između dva izbora, ja preferiram prvi.",
  "Svaki primer na spisku sadrži broj.",
  "Svaki pasus treba naslov.",
  "Druga kolona je prazna.",
  "Mesec je jedinica u ovom rečniku.",
  "Polje nazvano godina sadrži tekst.",
  "Kolona vremenske oznake je prazna.",
  "Reč ponoć se javlja u rečniku.",
];
writeFileSync(
  new URL("negatives.jsonl", gold),
  texts
    .map((text, index) =>
      JSON.stringify({
        id: `negative-${String(index + 1).padStart(3, "0")}`,
        family: "non-temporal",
        text,
        schedule: null,
      }),
    )
    .join("\n") + "\n",
);
console.log(`Authored ${texts.length} negative controls.`);
