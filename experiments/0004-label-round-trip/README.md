# 0004 · Does the AC-7 label round trip, for real?

**Date**: 2026-09-23
**Corpus commit**: `2e40bcf` (JobHunt `docs/`, pinned)
**Code commit**: `934bee8` (spec 0002 build plan tasks 16 and 17)
**Spec**: [0002, AC-7](../../docs/specs/0002-data-model/index.md), amended 2026-09-23
**Note**: this run uses `prompt_version` `0002.3`, the first to carry a `label` on a
reference endpoint. `0008 ## Preamble` already held three real runs from the original
AC-14 coverage run under `0002.2`, before that field existed; those are moved to
[`artifacts/superseded/2026-09-23-prompt-0002.2/0008/preamble/`](../../artifacts/superseded/2026-09-23-prompt-0002.2/0008/preamble/)
per `experiments/README.md`'s rule (never delete a run's artifacts, move them), and
this run's own artifacts take their place. Anything measured from the old Preamble
runs (entity counts, agreement, the AC-14 coverage figures) is not comparable with
anything measured here; this run only speaks to the `label` question.

## Question

Spec 0002's AC-7 amendment gave a reference endpoint a `label`, alongside `record` and
`id`, so a reference to a named but unnumbered item (`binding rule 6`) can resolve to
the entity that carries it. The whole mechanism depends on one thing nothing in the
amendment could verify without a real call: does the model write the *same* label
string on both sides, the entity that carries the label and the reference that names
it? Build plan task 17 flagged this "owed, not yet run." This is that run.

## Method

Two units, three runs each, under spec 0001's run policy, by
[real_label_run.py](real_label_run.py). Both are real pipeline output, so both land
under `artifacts/runs/`, not copied into this experiment's own `data/`:

- [`artifacts/runs/0001/binding-rules/`](../../artifacts/runs/0001/binding-rules/) —
  net new, no prior real artifacts existed for this unit.
- [`artifacts/runs/0008/preamble/`](../../artifacts/runs/0008/preamble/) — replaces the
  `0002.2` runs (superseded copy linked above), because this is the unit that names
  `binding rule 6` and needs a fresh run under the amended schema to test it.

[`data/report.json`](data/report.json) is this run's own analysis (verbatim labels,
agreement, resolution outcome, cost), computed from the two units above and kept here
because it is a measurement about the run, not pipeline output itself.

## Configuration

| | |
|---|---|
| Model | `claude-sonnet-5` |
| Runs | 3 per unit |
| Prompt version | `0002.3` |
| `max_tokens` | 64000, streaming |
| Effort | `medium` |
| Sampling parameters | none. Rejected outright on this model |

Every run artifact records all of the above.

## Result

| Unit | chars | agree | entities per run | accepted | review |
|---|---|---|---|---|---|
| `0001 ## Binding rules` | 10,238 | no | 13 / 19 / 9 | 6 | 33 |
| `0008 Preamble` | 4,040 | no | 15 / 14 / 15 | 0 | — (all held or queued; see below) |

Types per run:

| | Binding rules r1 | r2 | r3 | Preamble r1 | r2 | r3 |
|---|---|---|---|---|---|---|
| `Constraint` | 13 | 18 | 8 | 1 | 0 | 0 |
| `FollowUp` | 0 | 1 | 0 | 0 | 0 | 0 |
| `Consequence` | 0 | 0 | 1 | 0 | 0 | 0 |
| `AcceptanceCriterion` | 0 | 0 | 0 | 14 | 13 | 13 |
| `Feature` | 0 | 0 | 0 | 0 | 1 | 1 |
| `unclassified` | 0 | 0 | 0 | 0 | 0 | 1 |

### 1. The label strings, verbatim, both sides

**Entity side, spec 0001's `## Binding rules`**: no entity, in any of the three runs,
carries a `label`. Not a misspelling or a partial string, absent. This includes the
entity that *is* binding rule 6, `0001#binding-rules:10` in run 1's ordering
("Authorisation is never decided in the proxy. The proxy (`src/proxy.ts`...`)"), whose
`label` field reads `null` in every run's raw JSON.

**Reference side, `0008`'s Preamble**: every run's `amended-by` relationship carries
the same source endpoint, verbatim, all three times:

```json
{"kind": "reference", "record": "0001", "id": null, "label": "binding rule 6",
 "mention": "Spec 0001's binding rule 6 amendment"}
```

**`normalize_label()` equality**: moot, not false. There is no label on the entity
side to normalize and compare against; `build_label_index()` over all three Binding
rules runs returns `{}`. The reference's label is well formed and stable, it simply
has nothing to match.

(A second labeled reference appeared, `binding rule 5`, `record: null` this time, so
it was never going to resolve regardless: present in runs 1 and 2 with the identical
text `"binding rule 5"` each time, but under two different relationship types
[`unclassified`, `satisfies`] and absent from run 3, so it read as a disagreement
(`runs_disagree`) on type and count, not on the label string.)

### 2. Agreement on the label text, each side (AC-11e)

**Reference side**: the full relationship signature —
`('amended-by', 'ref:0001/|label:binding rule 6', '0008/AC-10b')` — is identical
across all three runs and reads as **agreement** (`comparison.shared_relationships`).
The `label` component was not what destabilized anything here; the same string
survived three independent calls untouched.

**Entity side**: nothing to disagree on. No run ever sets `label`, so there is no
run to run variance for AC-11e to catch on this axis. (Both units disagree overall,
`agree: false`, entirely on other content — see the review counts above; AC-11e adds
nothing to either unit's queue in this run.)

### 3. What the 0008 reference resolved to

**Held, under `endpoint_not_accepted` — and not for the reason the label mechanism
exists to catch.** The `amended-by` relationship's *other*, local endpoint,
`0008/AC-10b`, was itself not accepted (it did not survive the three run comparison on
its own terms), and AC-11c's rule holds the whole relationship on that account before
the labeled endpoint is ever evaluated for a match:

```json
{"detail": "0008/AC-10b", "name": "endpoint_not_accepted"}
```

Two things are true at once, and worth keeping separate:

- **The routing and hold mechanism did exactly what it was built to do.** A relationship
  is held when *either* endpoint fails to accept, and it correctly deferred here rather
  than guessing.
- **Separately, the label match itself was never going to succeed anyway.** Even with
  `0008/AC-10b` accepted, `label_index.get(("0001", "binding rule 6"))` returns nothing,
  because no entity anywhere in the corpus, across all three Binding rules runs,
  carries that label. The reference would have fallen through to `:Unresolved`,
  carrying `record: "0001"` and `label: "binding rule 6"` (AC-10), not a wrong guess,
  just the honest gap.

### 4. Real cost

**$1.0185** for the six calls, 37,950 input and 94,264 output tokens, against the
**$0.93** estimate given before the run: **9.5% over**, inside the "under $1.50 with
retries" bound the engineer approved. No retries: all six calls settled on their first
attempt (`input_tokens`/`output_tokens` breakdown, and the per unit split, in
[`data/report.json`](data/report.json)).

**Calibration note for the next estimate.** The pre run estimate interpolated cost from
character count alone, against two prior anchors. Output ran 94,264 tokens against
37,950 input, about 2.5 times, higher than either anchor's ratio, because both real
units here provoke more reasoning per character than a typical section: `## Binding
rules` is eight dense, individually numbered constraints rather than one continuous
argument, and the `Preamble` is six stacked revision notes, each its own small claim.
Size based interpolation reads chars, not argument density, and undercounts exactly
this shape. The 9.5% miss was small only because both units still sat in a similar
range to the anchors; a unit this dense but larger could miss by more. Carry a wider
margin, not a bigger point estimate, when a unit is this densely enumerated rather than
prose.

## Conclusion

**The label round trip does not happen, cleanly and reproducibly.** Not a near miss on
normalization, an absence: the model never writes `label` on the Constraint entity
that *is* binding rule 6, in any of three runs, while the reference side, in the same
real run, under the same prompt, correctly and stably writes `label: "binding rule 6"`
three times running. The gap is in extraction, not in resolution: `resolve_endpoints()`
and the routing it depends on behave exactly as spec 0002 amends them to, given what
they were handed. They were handed nothing to match on the entity side.

**A likely reason, found by reading the prompt rather than guessing at one**: the
`SYSTEM_PROMPT` rule this amendment added (`client.py`) instructs the model on `label`
only from the reference side —

> "...the same `label` you *would* give that item as an entity."

— which presupposes the model already knows to label the entity and never actually
tells it to. There is no rule anywhere in the prompt that positively instructs setting
`label` on an entity at all; the field exists in the schema (with a field description),
but nothing in the free text asks for it. This is consistent with, and does not
contradict, `AC-7`'s own build note that a prompt worked example was deliberately not
added here (it would preempt feature 12's still open question of how this project
wants to structure examples).

## What this owes the specs

Reported, not fixed here, per instruction: this result is itself the finding, and
adjusting the prompt to force a match would have hidden it rather than answered the
question asked.

- **Feature 12** (prompt examples, already the named owner) inherits this as concrete
  evidence: a rule that describes a field only from one side of a two sided contract is
  exactly the kind of gap a worked example would close, and this is a ready made one
  (the two real spans above, entity and reference, with the entity side's null shown
  next to the reference side's `"binding rule 6"`).
- **Spec 0002 / feature 4**'s build plan task 17 is now measured, not owed: the code
  and the resolution and hold paths are confirmed correct against real data; the
  entity side extraction gap is a new, separate finding, not a defect in what task 17
  built.
