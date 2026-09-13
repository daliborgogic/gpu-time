# gpu-time model card

## Model

The package embeds checkpoint `serbian-v1`, epoch index 18, with artifact SHA-256 `b186a201db5970687c090794b7b9ac7a7b2ba2d8df47fe4d1127284843db33cd`. It has 32,953 parameters, 580 embedding rows, and 40 role slots (35 named roles plus five reserved). Weights use 6-bit symmetric per-tensor quantization, with f16 storage and f32 intermediate calculations. The active report records 19,869 Brotli bytes for the weights, a single cold-start checkpoint (this is the first Serbian-language training run, not a continuation of the retired English lineage), and 119,701,286 training tokens.

The model predicts one role per token, such as hour, weekday, quantity, recurrence marker, or filler. A separate boundary score splits the input into expressions at threshold 1.75. The `CLOCK_OFFSET` role represents half-hour and quarter-hour clock arithmetic.

Timezone is not a model role. TypeScript handles calendar arithmetic, daylight saving time, the reference instant, and expansion limits after the model runs.

## Intended use

The parser turns short Serbian (Latin script) time expressions into dates, ranges, and recurrence rules on the client. Examples include reminder fields, schedule forms, and command bars.

It is not suitable for parsing documents, extracting dates from long prose, legal or medical scheduling, billing, compliance, or any decision where a wrong or invented date has real consequences. It supports Serbian (Latin script) only and has no language detection.

## Training data

Supervision is entirely generated. `packages/training/torch/generate.py` renders schedules, and `natural.py` adds natural-phrasing families, including negative prose containing no time expression. Labels come from the generator's structure, never from the runtime parser, so the model is not trained on its own predictions.

The active weights are a single cold-started run (`serbian-v1`, 20 epochs, 300,000 fresh examples per epoch, 119,701,286 training tokens total). English's retired lineage does not carry over: Serbian's vocabulary, grammar, and case system are different enough that warm-starting from the English checkpoint's embeddings was judged not to help, so this run began from scratch rather than continuing `spoken2`'s 22-checkpoint history.

Generated corpora live under the ignored `packages/training/data/synth/` and include the training data built with `pnpm gen`. Hand-authored evaluation corpora are tracked in `packages/training/data/gold/`.

The training data reflect the generators, so these scores do not establish accuracy on real user language.

The generators combine surrounding phrases and use filtered Tatoeba sentences as background text. They also generate terse forms, including bare day groups, abbreviated weekday ranges, month-day ranges, and bare clock ranges.

## Evaluation

These numbers all describe the active `serbian-v1` export; there is no prior Serbian checkpoint to compare against.

- **Unseen (reserved) carriers: 808/1000 exact token-label and boundary sequences.** The reserved surrounding words in `natural.py::RESERVED` are absent from training. This is the export gate's own criterion — decoded 6-bit weights, scored in the same process as the baseline they must beat. The retired English `spoken2` checkpoint scores 36/1000 on this same Serbian-language corpus, which is expected (it was never trained on Serbian) rather than informative as a comparison.
- Held-in development metrics from the training run: 99.66% token accuracy and 95.73% exact label-and-boundary sequences on the validation split; 98.85% token accuracy and 89.04% exact sequences on heldout. Both splits share generator families with training and are development metrics, not real-user language accuracy.
- The gold fixtures under `packages/training/data/gold/` (25 adversarial schedules, 3 packaged user-case fixtures, 32 hand-labeled oracle cases, 109 core-grammar cases plus 260 derived casing/spacing/abbreviation variants, 24 prose carriers plus casing variants, 32 non-temporal negative controls) all pass through the built parser, with three documented exceptions — see `knownGaps` in `packages/core/test/grammar-model.test.ts`. These fixtures influenced implementation and training; they are a regression gate, not an untouched test.
- Unit tests cover tokenization, compilation, calendar resolution, DST, RFC 5545 export, and inference workspace reuse. The full suite passes except one model-parity numeric-tolerance check (see Limitations).
- Independent third-party comparisons (the previous card's Microsoft Recognizers figure, and `packages/benchmark`'s cross-library timing) are not carried over: those baselines don't support Serbian, so scoring them against this model isn't a meaningful comparison. The cross-library harness (chrono, compromise, later, rrule, Recognizers-Text, and the Python `dateparser`/`parsedatetime`/`recurrent`/`timefhuman` sidecar) has been removed rather than kept disabled; `packages/benchmark` now measures gpu-time's own size and browser/CPU performance only.

### Known gaps

A handful of constructions found during Serbian porting are undertrained rather than unsupported by the compiler — more training epochs or corpus weighting should close these, not a code change:

- Genitive-case modifiers ("svakog", "sledećeg") in the rare ordinal-weekday-of-month family (e.g. "prvi ponedeljak svakog meseca") — the nominative equivalent ("prvi ponedeljak meseca") works.
- A few specific spoken compound-minute values (40, 27, 42) after "i" aren't reliably read as minutes; smaller/rounder values (15, 30, 35) are fine.
- "pola do X" (half to the hour) is underrepresented next to "četvrt do X" (quarter to the hour).
- ALL-CAPS text loses the monthly-ordinal recurrence flag on some phrasings, and "petak" (Friday) abbreviated to "pet" collides with the number word "pet" (five).

## Limitations

- Accuracy on real user phrasing is unmeasured. The generated expressions share training families, including those with reserved surrounding prose.
- Serbian (Latin script) only. Other languages, and Serbian Cyrillic, can produce incorrect results without a diagnostic.
- Vague expressions (`ASAP`, `after work`, `soon`) are deliberately given no clock value rather than a guessed one.
- Ambiguous numeric dates depend on the caller's `dateOrder` (`DMY` by default). `03/04/2027` is ambiguous. `21/04/2016` is not and resolves correctly either way.
- Complex recurring exception combinations preview correctly but can return an `unsupported-export` diagnostic when no single RFC 5545 rule represents them.
- Quantization and browser GPU implementations can differ from the PyTorch reference unless parity is explicitly tested. It is, but only for the fixtures listed above. One parity check currently exceeds its tolerance by a small margin (max logit error 0.00109 against a 0.001 threshold), with zero label or boundary mismatches — a precision artifact, not a wrong prediction. A `--storage f32` retrain (`serbian-f32`, tried and discarded) did close this gap, but shifted the model's per-construct accuracy enough to break duration parsing on "X i po"/"X i [minute]" and a yearly-recurrence pattern, and produce one false positive on a negative control — a worse trade than the tolerance overage itself. Kept `serbian-v1`.
- WebGPU startup and dispatch overhead make small inputs slower than a CPU parser, which is why `auto` keeps them on the CPU.
- The release build must stay within the 50,000-byte Brotli limit.

## Reproducibility

`packages/training/active/` holds `export-report.json` (selected weights, lineage, calibration, source hashes, token metrics), `provenance.json` (the checkpoint chain with hash verification — a single entry for this cold-started run), and the `parity.*` fixtures that check decoded int6 inference against PyTorch logits.

`packages/training/runs/serbian-v1/` keeps the promoted run's report and a source snapshot of the exact generator, tokenizer, and label set used to produce it. The export source directory recorded in `export-report.json` keeps the export-time snapshot and lockfile. The `.pt` checkpoint itself is not tracked, so re-export requires the local checkpoint.

`pnpm --filter @gpu-time/training audit:model` re-verifies the weight file hash and the training source hashes against the recorded chain. Superseded runs and exports were untracked during the monorepo restructure and remain recoverable from Git history.

## Promotion

Export is gated. A candidate must improve the unseen-carrier score and pass per-family and bare-expression guards with a two-proportion statistical tolerance. The exporter decodes both models from their 6-bit form and scores them on the same corpus in one process. It reads the baseline from the shipped `weights.gen.ts`. It replaces files by rename and writes the report last. `--force` overrides the decision and records what it overrode.

The export gate measures exact token labels and expression boundaries in PyTorch, including filler labels, on the reserved-carrier corpus. The active model scores **808/1000** by this measure. There is no prior Serbian checkpoint to compare it against; the retired English `spoken2` checkpoint's **982/1000** was scored on English reserved carriers and is not a comparable number.

Held-in metrics do not control promotion. `calibrate()` uses the `heldout` split to select the boundary threshold, so that split supplies development metrics.