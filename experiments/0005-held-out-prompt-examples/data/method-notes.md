# Method notes, experiment 0005 ruling

## Convention: recording reasons

Each reason is one sub-bullet directly under the mark line, starting `reason:`, holding only the reason (no copied item text). Required on every `disagree` and `unsure` (say what it should have been), and on an `agree` when a rule decided it.

- JobHunt's session reads the live repo, not the pinned snapshot (2e40bcf, 2026-09-18). Spec 0010's AC-5 was superseded on 2026-09-23 (232aba8), after the snapshot; rulings judge the pinned text, so later changes do not count against the model.

## Links start from the connected item, not the sentence that states the connection

A link's source is the item that is actually connected, not a note that describes the connection. Set on group C relationship 5, where one run drew the link from "That last clause is spec 0001's third runner constraint..." (a provenance note) instead of from the no-browser rule it describes.

## Rule by what the text supports, including its context

The extractor sees only the text, so a ruling judges its cut against what the text and its context support under the three-question test, not against knowledge only the author has. Where the author's knowledge differs, it goes in the reason. Set on group B entity 2 (0013's "dropped and counted"), first ruled a split, then changed to one rule once its context showed counting serves the all-failed exception. Separately, a JobHunt finding: adzuna.ts drops failing listings but counts them only when every listing fails (droppedCount, line 295).

## blocked-by includes deliberate holds

`blocked-by` covers any item waiting on something to be done first, whether the wait is technical or a deliberate decision with a stated condition ("until it ships"). Set on group A relationship 4 (AC-13, held back until the real data version shipped; JobHunt's `hero-section.tsx:68-72` calls it "the condition that held it back").

Findings about the ruling method itself, kept apart from the item marks so the tally stays a clean count.

## Group A, entity 1 (`0021#requirements:1`, Feature): the deletion trick and user stories

The deletion trick asks whether a testable condition disappears, which has no answer for a Feature, since a Feature states why something exists rather than a testable behaviour. For "As a... I want... so that..." stories, the trick moves the "so that" clause (the value) into `rejected_spans`. That clause is not lost: it is stored as the entity's rationale (`src/tracepath/graph/model.py`) and shown as why-text. The open question is whether the value belongs in the Feature's span rather than its rationale. On this item the "so that" clause carried the feature's distinguishing value (the ranking being judgeable), not background; the engineer ruled the span too narrow. Scope: 20 of the corpus's 42 user stories carry a "so that", across 10 of 21 specs.

## Group A, entity 5 (`0021#requirements:6`, struck old AC-6): superseded text

Struck (superseded) text is ruled as one entity even when it bundles several conditions, since it is recorded as the thing that was replaced; atomicity is applied to current text only. Reason: splitting replaced text fragments the history without adding anything a chain needs.

## Group A, entities 0021 AC-12 and AC-17: a bundled AC-N kept whole

A criterion with a verbatim `AC-N` id is one item however many conditions it bundles, and the prompt keeps it whole and flags it `multi_condition_split` (spec 0003, AC-28). Splitting would give the verbatim id to the first part only (`ids.py`, `_verbatim_keepers`), so every reference to the id would land on that part; the eval set and about 40 lines of `0021` cite these criteria as one item. The two rulings made before this decision, AC-12 and AC-17 "should split", stay as recorded disagreements, tagged `gap:bundled-ac` (2); the tally is not rewritten. From the re check on, a bundled `AC-N` kept whole and flagged `multi_condition_split` is ruled `agree`, with a reason line tagged `gap:bundled-ac`, the same way struck text kept whole is ruled. A bundled `AC-N` kept whole but left unflagged, or one that was split, is ruled `disagree`. The accuracy bar's thresholds do not change. Sub ids and a part of link reopen only if an eval chain or the re check needs a part of one criterion; the design then starts from a general parent `AC-N` node that bare references resolve to, with parts listed under it and no automatic part matching.

## Open design question: partial supersession

- AC-4's new text says only its second sentence stopped being true, the first carried over. Splitting struck text would let the graph say exactly which part was superseded. Spec 0002 (AC-5 and its 0021 AC-2 test scenario) currently expects one struck entity per criterion, so the ruling applies the struck text rule consistently and leaves this as a possible spec 0002 amendment. Entity 4 was first ruled "should split" before the rule was set, then changed to agree for consistency.
- Second example: AC-7's tiebreaker fragment was superseded (single search rank replaced by the interleaved kept walk order), while AC-7 as a whole was amended.

## Open design question: stages and steps

Scope rows mix workflow stages (Design it, Build it, Verify it, Test it) with build steps nested under Build it, and the model types all of them as BuildStep. The stages split into building (Build it, whose sub-steps carry the "· AC-..." tags and satisfy criteria) and checking (Verify it, Test it, which mention criteria only as checked or found failing, never tagged as delivered, across all 22 Verify and 20 Test lines in the scope). Only building maps to BuildStep; checking has no stage-level type, so group C entity 10 was ruled unclassified. Whether to add a stage type, or a part-of link from sub-steps to their stage, is a design question for later.

## Group A findings

- AC-12 (line 111) and AC-15 (line 129) each state that the fault state and the not-yet state must render distinguishable copy, but no after run wrote any link between them. It would be `unclassified`, phrase "the two must render distinguishable copy".
- AC-17 (lines 137 to 158) carries a struck old version; run 1 left it out of the span, correctly, but did not extract it as its own old-version entity, as spec 0002 AC-5 expects and as the model did for AC-2 and AC-6.
- Entities ruled: 7 of 10 (1 to 5, 8 and 10); 6, 7 and 9 skipped by choice.
- The reason AC-2, AC-3 and AC-6 moved from fake to real data (2026-09-14) is the user story's "so that" clause (0021/index.md:31-32), which the text never links to those changes; a "why did AC-2 change" chain cannot reach it today.
- AC-7's "best band first" depends on the band order defined in spec 0015 AC-1, which AC-7 never names; the text points at `/search` instead, so no chain can reach the real dependency from AC-7 today.

## History link types: judged by what changed, not the author's stamp

The type reflects what actually changed; the author's literal wording is kept in `phrase` either way. `superseded-by` means the old version is retired and the new one goes a different direction. `amended-by` means the same direction with a changed scope or an addition, the old premise still standing. `corrected-by` means the old version was wrong. Set on group A relationship 2 (old AC-4 to new AC-4, stamped "SUPERSEDED" but narrowed, not retired); the runs split the same way, 2 superseded to 1 amended.

Unnamed dependencies (a dependency the text never names, e.g. AC-2's change back to its user story, AC-7 back to spec 0015 AC-1, AC-9 back to spec 0013 AC-7): 3 found in group A's ~15 relationship items. Keep counting through groups B and C; whether they matter is decided by whether any eval chain needs one. No clear feature owns them: feature 7 covers the same thing named several ways, not links never named at all.

Group A: the old prompt wrote 27 to 35 unclassified links per run, the new prompt 0 to 1. Lost links test whether the drop removed only junk (files, PRs, tools, self-links) or also real criterion-to-criterion pointers (lost link 1, AC-2 to AC-17, was real; #6 and #10 are the same shape).

Named but unlinkable: AC-17 points to Feature design's "Refresh outcomes" section (0021 lines 388 to 390, decisions ratified from the build), but a sub-section is not a record, an AC id or a label, so AC-7's endpoint shapes cannot name it; run 1 moved the sentence into rejected_spans.

Second example: feature 9's Done when names "spec 0001's third runner constraint", one sentence in spec 0001's Test runners row (line 58); "third" means the one left over after spec 0004 met the other two (spec 0004, line 52), not third in the list. The link can only point at the whole of spec 0001; the deferral itself is captured by a separate link to spec 0004 in all 3 runs.


- A reference like "the same convention spec X uses" can import rules from another spec without stating them; by the deletion trick it stays in the span. No run linked 0013 to spec 0007, though the text names 0007's convention as the one it follows.

- Category prefixes are not labels: 0013's test list uses prefixes ("Failure case:" three times, "Happy path:", "Gate:"), and runs 1 and 2 set the label "Failure case" on all three failure bullets, run 3 on none. Spec 0003 AC-6 sets a label only for an item's own name, so a shared prefix gets none (three identical labels would also tie under AC-7). JobHunt observations: the third "Failure case" bullet renders the page normally (AC-1, AC-5), unlike the other two; the first bullet holds two tests ("and, separately"); the "every item fails" branch has no bullet of its own.

## Vocabulary gaps: running tally

Tag a reason with gap:<name> when a disagreement comes from something tracepath cannot express. Counts so far (groups A to C):

- gap:reuses-type (3): feature 12 reuses 0013's shape (B rel 1); 0013 follows 0007's copy convention (B entity 3); AC-9 reuses 0013's attribution pairing (A lost link 4). Spec 0002 already lists "reuses or seeds" as a candidate type awaiting evidence.
- gap:partial-supersession (2): AC-4 (A rel 2), AC-7's tiebreaker (A rel 3).
- gap:unlinkable-target (2): AC-17 to Feature design "Refresh outcomes" (A lost link 7); spec 0001's "third runner constraint" (C rel 1).
- gap:stage-type (1): "Verify it" (C entity 10).
- gap:bundled-ac (2): 0021 AC-12 and AC-17, kept whole by design (spec 0003, AC-28).
The most frequent gap is the first candidate for a spec change.
New gaps get a new tag when first seen. To find ones not yet noticed: group the phrases on unclassified links and the notes on unclassified entities across all runs, check unresolved nodes that carry a record and label, and look at relationship_type_ambiguous flags; anything that recurs is a candidate. Most useful after the whole-corpus run (feature 9).

## Accuracy bar for AC-16 (set after seeing rough counts)

Judged on usefulness by the engineer, counting every disagreement whatever its cause; disagreements that come only from knowledge not in the text are reported separately and do not fail a group. Good enough to move on if at least two thirds of entity marks and of relationship marks in each group agree, and no more than 1 in 5 of the dropped links sampled were real.

Counts at the time: entities A 4/7, B 2/5, C 1/5; relationships A 2/5, B 5/5, C 3/5; knowledge-not-in-text disagreements: 0 by keyword search of the reasons, to be confirmed by the build session's pre-sort (the one intent case, group B entity 2, was ruled on the text and ended agree). Dropped links: 2 real of 10, sampled evenly spaced (not random) from 50. That is exactly 1 in 5, so it sits on the line, and the 95% Wilson interval (5.7% to 51.0%) is too wide to show it is under; about 15 samples with none real, or more if some are, could.

On these counts the bar fails on five of the six results (entities and relationships in groups A, B and C; only B's relationships reach two thirds), so this experiment says fix first. Descriptive, not a test: set after seeing the counts, not pre-registered. Re-check after fixes on units not used in this tally or in the prompt examples (API spend, estimate first), with a larger dropped-link sample, a few random passages read cold for real links missing from accepted, held and dropped alike, and about 10 of the engineer's own calls re-judged blind for self-agreement. Then once on the five eval chains when the eval runner (feature 6) exists.

Fix ladder, cheapest cause first: rules the model was never given (add them to the prompt), then prompt or example quality; vocabulary gaps go to a later spec change, starting with the most frequent tag in the running tally.

## Candidates from the 0006 ruling (not yet rules)

1. **Docs record a plan, history only partly matches it** (JobHunt, checked at `2e40bcf`): a build step's `AC-N` tag states intended delivery, not always what shipped (feature 9: `9f831e5` built all sections, `5cb762f` ticked all the steps at once); a scope row's steps do not match commit boundaries (AC-16 landed alone in `85f36fd`); a test scenario's `verifies` can claim more than its own test checks (0013's Empty scenario, `page.test.ts:291` checks only AC-4's first clause); a forward looking "Feature 12 imports this exact shape later" was never acted on (feature 12 defines `ListingSnapshot`). Marks stay on the text as extracted; these findings go in reason lines only, never into the mark itself.

2. **The "so" clause test**: a clause is its own condition only if it can fail while the rest of the sentence still passes, and the build has to make it true. 0014 AC-4's second sentence passes both and stays in the span. AC-6's final clause fails the first test (it cannot fail independently of the rest) and goes to `rejected_spans`, the reason line. AC-20's Next.js premise passes the first test but fails the second (the build does not have to make it true, it is stated background) and also goes to `rejected_spans`, the reason line.

3. **The "so that" rule, a second example**: 0014's first user story (disagree: the "so that" clause rules out an application process of the app's own, a claim stated nowhere else in the unit, so it belongs in the span) against its third user story (agree: the clause reads as rationale, since the story's own action is delivered by AC-9).

4. **Blind re-read**: 7 of 10 matched, an upper bound, since memory makes a blind re-read look more consistent than a genuinely independent one would. Items 3 and 5 were misreads on the second pass; the original rulings stand. Item 10 changed on reflection (a stated reuse is not itself a link), so `gap:reuses-type` drops from 3 to 2 in the running tally, and no single gap now leads it.

5. **0014's relationships 1 to 3** are dependency shaped `unclassified` links (relies on, incorporates by reference, scope boundary): evidence for a possible `depends on` type. Not counted as gaps here, since all three were ruled agree.
