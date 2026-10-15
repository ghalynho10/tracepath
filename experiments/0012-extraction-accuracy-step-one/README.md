# 0012 · Extraction accuracy, step one: are the items the code pass releases right?

**Date started**: 2026-10-11
**Spec**: [0007](../../docs/specs/0007-extraction-accuracy/index.md), the measure (AC-18 to AC-30)
**Status**: stage one ruled and scored 2026-10-14: inconclusive, the code pass stays off

## Question

The code pass of spec 0007 stops a `multi_condition_split` flag alone from holding an
acceptance criterion whose three runs agree on its id and type. Runs agreeing shows they
repeat, not that they are right. Are the items it releases right, by the engineer's own
rulings?

## Units

Chosen before any paid call and listed in [`units.json`](units.json), the only list the
step is scored from (AC-22). Their run artifacts must carry `extracted_at` values later
than this file's commit (AC-22b).

| Unit | Why it is clean |
|---|---|
| `0009` `## Requirements` | Not a held out, worked example or pass checked record (AC-23); never ruled (AC-24) |
| `0013` `## Requirements` | Same. Experiment 0005 ruled `0013` `## Feature design`, a different unit |
| `0015` `## Requirements` | Same. Experiment 0006 ruled `0015` `## Feature design`, a different unit |

`tests/test_step_units.py` checks this list against AC-23 and AC-24 on every run.

## Gate

The gate and its reason are spec 0007's AC-19 to AC-19i, as committed in `c004a30`
before any paid call (AC-19e). The step runs in two stages. Both gates count over every
drawn mark, not only the ruled ones: a mark ruled `unsure`, ruled disagree or left
unruled counts against, so ruling hard items `unsure` can never make a unit pass.

- **Stage one** (AC-19, AC-19b, AC-19c): per unit, 5 released entity marks are drawn,
  mixed blind with 3 control entity marks that are ruled but not gated (AC-25, AC-25b).
  Every chosen unit needs at least 4 of its 5 released marks ruled agree. A unit with
  fewer than 5 released entities is inconclusive, and stage one passes only when no unit
  is inconclusive. Nothing accepted without the pass may be lost with it.
- **Stage two** (AC-19f to AC-19i): runs only after stage one passes and the engineer
  wants the pass on by default. Per unit, up to 5 released link marks are drawn, mixed
  blind with 2 control accepted links that are ruled but not gated (AC-25e, AC-25g).
  Every unit with at least one released link needs two thirds of its drawn released
  link marks ruled agree, however few are drawn (1 of 1, 2 of 2, 2 of 3, 3 of 4, 4 of 5).
  A unit with none is reported as having none. A stage one pass alone never turns the
  pass on by default.

No dropped links are drawn (AC-25f). Experiment 0005's full bar is not measured in this
step; it is owed on feature 13's final state (AC-18b, AC-28e).

## Configuration

Model `claude-sonnet-5-5`, effort `medium`, prompt `0003.1`, corpus commit `2e40bcf`.
One paid extraction serves both arms: the control is the run files read without
`--code-pass`, the treatment the same files read with it (AC-20).

Cached prefix, as billed on `claude-sonnet-5-5`: the first call on that model
(`0009:Requirements` run 1, `artifacts/runs/0009/requirements/run-1.json`) wrote a 57,493
token cache, against the 57,494 in `cost.py` (measured on `claude-sonnet-5`, experiment
0008). Its input was 4,537 uncached plus 57,493 cached, the 62,030 the free count gave.
The difference is 1 token at the $4 per million cache write rate, $0.0000039 per call.
The engineer accepted it as recorded data, not a spec change: `cost.py` stays at 57,494,
and the note on spec 0007 AC-31g is deferred to the `/architect` session for the later
steps.

## Stage one sample

`prepare_stage_one.py` (no API call) draws, per unit, 5 entity marks from the entities
the code pass releases and 3 from the control arm's accepted entities, each draw with
its own seed (AC-25 to AC-25c), and writes three files under `data/`:

- `stage-one-packet.md`: the items mixed per unit, shuffled, under opaque ids, each
  showing only its span, type and source line (AC-26, AC-26d). The engineer rules here.
- `stage-one-arms.sha256`: the hash of the arm file, committed before any ruling
  (AC-26b).
- `stage-one-arms.json`: the arm file, naming every seed, every draw and its shortfall,
  and each item's arm. Kept uncommitted until the rulings are in (AC-26c); its hash
  must then match.

Drawn 2026-10-12, 22 items: `0009` 8, `0013` 6, `0015` 8. Shortfall (AC-25d): `0013`'s
released draw asked for 5 and found 3, so under AC-19c `0013` is inconclusive and stage
one cannot pass as drawn. Every other draw found what it asked for.

The seeds come from `secrets` at draw time, not from the script, so the arms cannot be
recomputed from committed code before the arm file is committed. The script refuses to
run once any of the three files exists, so the sample is drawn once.

## Eval chain reach (AC-28c)

`data/eval-before.txt` was recorded before the paid run, `data/eval-after.txt` after
the three units landed in the default graph (`tracepath load` then `tracepath eval`,
plain, no `--code-pass`). Every question's verdict is unchanged (1, 2, 3 and 5 fail,
4 is inconclusive). Question 5 counts one more accepted link outside its expected
sections (3 against 2).

## Result

Scored 2026-10-14 by `score_stage_one.py` (no API call) into
`data/stage-one-result.json`, from the ruled packet (`2b4baf4`) and the arm file
committed after it (`f5244a1`), whose hash matches the one committed before any ruling
(`dd92c57`).

**Stage one is inconclusive** (AC-19c): `0013` holds only 3 released entities, short of
the 5 the gate needs. The other two units pass. So the pass stays off (AC-19d) and
stage two is not run (AC-19h).

| Unit | Released marks ruled agree | Gate | Control marks ruled agree | Held items, pass off / on |
|---|---|---|---|---|
| `0009` `## Requirements` | 5 of 5 | pass | 1 of 3 | 16 / 9 |
| `0013` `## Requirements` | 3 of 3 | inconclusive | 1 of 3 | 9 / 4 |
| `0015` `## Requirements` | 5 of 5 | pass | 1 of 3 | 18 / 3 |

- **Released marks**: 13 drawn, 13 ruled agree, none disagree, unsure or unruled. 11 of
  the 13 carry `gap:bundled-ac`: a bundled criterion kept whole, ruled agree by the
  convention.
- **The flip of AC-26e** turned 3 rulings to disagree, all on control items: 1 in
  `0009` (`P06`), 2 in `0013` (`P11`, `P14`) and 0 in `0015`, as
  `data/stage-one-result.json` records. Each is an `AcceptanceCriterion` ruled agree
  with `gap:bundled-ac` whose entity the model did not flag `multi_condition_split`.
  No released item was flipped, since
  every released entity carries the flag (AC-12b). Before the flip the control marks
  read 6 agree, 3 disagree.
- **No regression** (AC-19b): over the three units, every entity and link accepted
  without the pass is accepted with it, checked by code.
- **Set apart**: no item unruled (AC-18e), no `unsure` (AC-18c), no disagreement
  citing knowledge not in the text (AC-18d, by keyword search of the reasons).
- **Provenance**: every run of the three units names `claude-sonnet-5-5` (AC-29b) and
  was extracted after `units.json` was first committed (AC-22b).
- **Eval chain reach** (AC-28c): see the section above; no question's verdict moved.
- None of the held item counts, eval chain reach or the control marks is a pass
  condition (AC-28d). Experiment 0005's full bar was not measured in this step; it is
  owed on feature 13's final state (AC-28e).

**The engineer's reading** (added 2026-10-14, after the result; it changes neither the
recorded result nor the gate): all 13 released items were ruled agree. The step reads
inconclusive only by the minimum of 5 released items per unit set before any ruling
(AC-19c), which `0013` missed with 3. The engineer judges the evidence clear, and step
one closes as the v1 finish line planned.

**Known weakness: an item's type partly reveals its arm.** AC-10 makes every released
entity an `AcceptanceCriterion`, while AC-25 draws control marks from all accepted
entities. 5 of the 9 control items were typed `Feature`, so they were visibly control,
and the 13 released items sat among only 17 `AcceptanceCriterion` items (4 of them
control). The released marks were therefore ruled less blind than the design meant.
A later step that wants a blind control should draw it from accepted entities of the
released items' type.

**The scope's tripwire** (feature 13, before feature 9 starts): every released mark was
ruled agree, so this falls on the "most are ruled agree" side: the cuts and types are
right, and the hold itself is the problem, which belongs to feature 11.

## Conclusion

On the two units that could be gated, the items the code pass releases were right by
the engineer's rulings, 10 of 10, and nothing accepted before was lost. `0013` had
too few released items to gate, so stage one does not pass, and the pass stays off by
default as the scope's v1 line already decided (feature 13 step one closes after these
rulings, whatever their result, with no fourth unit).
