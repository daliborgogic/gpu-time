# Neural-model walkthrough

The film follows words through tokens, vectors, model states, and scores. It uses a white background, dark Geist Mono text, and blue, teal, and violet accents. Duration: 91 seconds.

| Seconds | Animation                                                                    | Current implementation                                                                                            |
| ------- | ---------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| 0–5     | Sentence appears word by word                                                | Serbian weekly example, structurally matching the original English film (`svaki ponedeljak od 8 uveče do 10 uveče`, `Europe/Belgrade`)                                                                          |
| 5–12    | Original glyphs move into token boxes; source offsets appear                 | Numbers and meridiems split; whitespace retained internally                                                       |
| 12–22   | 32-value embedding grids rise from tokens                                    | Actual summed vectors from the 324-row learned embedding table                                                    |
| 22–30   | Context window travels; vector colors change                                 | Five-position depthwise convolution and nearest non-space neighbor mixing                                         |
| 30–40   | Context passes left and right; each state grid updates as the signal arrives | Actual gated forward/backward states, 32 channels                                                                 |
| 40–48   | Monday moves into the network; connections draw and carry pulses             | Combined token state + gated pooled context, 16 head gates, 64 hidden values, 40 role scores + boundary output    |
| 48–58   | Scores grow from zero; WEEKDAY wins                                          | Ten highest named-role logits for Monday; five reserved slots omitted from chart; boundary score shown separately |
| 58–64   | Roles land on the original tokens                                            | Actual RECUR, WEEKDAY, RANGE_START, HOUR, MERIDIEM, RANGE_END predictions                                         |
| 64–72   | Words move into frequency/day/window fields                                  | Internal calendar normalization; caller supplies reference/timezone; no public AST                                |
| 72–80   | Three dates appear; changed UTC times highlighted                            | Real public occurrences across New York DST                                                                       |
| 80–85   | Calendar properties appear                                                   | Real DTSTART, DTEND, RRULE returned by the current API                                                            |
| 85–91   | Original style closing lockup                                                | 32,953 parameters; local CPU/WebGPU; experimental status                                                          |

`export-data.ts` uses the production CPU diagnostic trace, compares every token
label with the tagger, and independently reconstructs the head to compare all
role scores. Full values and source/checkpoint hashes are stored in `data.json`.
All 32 embedding channels are shown as a four-by-eight grid. Each scene has one short title; formulas and secondary headings do not compete with the diagrams. Other node counts and connections are
sampled and labeled as such. No synthetic scores, accuracy, or speed claims.

Narration is generated afresh, with the original stock synthetic Kokoro af_heart
voice, and stays in English: Kokoro has no Serbian voice, so `narration.json`
describes the same schedule in English while the on-screen sentence, labels,
and captions are Serbian. A local eSpeak-NG `sr` voice was tried and works —
Piper's only nominally-Serbian voice turned out to be mislabeled Sorbian, and
Facebook's MMS-TTS lists Serbian as ASR/LID-only — but was rolled back in
favor of Kokoro's more natural voice. The original music and effect synthesis
is adapted to this duration and new render-derived event timings, including
forward/backward scans.
