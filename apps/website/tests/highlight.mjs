import assert from "node:assert/strict";
import { examples, highlight } from "../src/lib/demo.ts";

const marked = (text) =>
  highlight(text)
    .filter((part) => part.kind)
    .map((part) => `${part.kind}:${part.text}`);

// Parts must reassemble the input exactly, or the highlight layer drifts out of
// alignment with the input it sits behind.
for (const { text } of [
  ...examples,
  { text: "svaki ponedeljak od 8popodne do 10popodne" },
  { text: "" },
  { text: "gibberish" },
]) {
  assert.equal(
    highlight(text)
      .map((part) => part.text)
      .join(""),
    text,
    text,
  );
}

assert.deepEqual(marked("svaki ponedeljak od 8popodne do 10popodne"), [
  "repeat:svaki",
  "date:ponedeljak",
  "time:od 8popodne do 10popodne",
]);
assert.deepEqual(marked("svaki drugi petak u podne"), [
  "repeat:svaki drugi",
  "date:petak",
  "time:podne",
]);
assert.deepEqual(marked("za pola sata za 45 minuta"), [
  "duration:za pola sata",
  "duration:za 45 minuta",
]);
assert.deepEqual(marked("gibberish"), []);
console.log("highlight: parts reassemble and carry the expected meanings");
