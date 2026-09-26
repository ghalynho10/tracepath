# Method notes, experiment 0005 ruling

## Convention: recording reasons

Each reason is one sub-bullet directly under the mark line, starting `reason:`, holding only the reason (no copied item text). Required on every `disagree` and `unsure` (say what it should have been), and on an `agree` when a rule decided it.

## blocked-by includes deliberate holds

`blocked-by` covers any item waiting on something to be done first, whether the wait is technical or a deliberate decision with a stated condition ("until it ships"). Set on group A relationship 4 (AC-13, held back until the real data version shipped; JobHunt's `hero-section.tsx:68-72` calls it "the condition that held it back").

Findings about the ruling method itself, kept apart from the item marks so the tally stays a clean count.

## Group A, entity 1 (`0021#requirements:1`, Feature): the deletion trick and user stories

The deletion trick asks whether a testable condition disappears, which has no answer for a Feature, since a Feature states why something exists rather than a testable behaviour. For "As a... I want... so that..." stories, the trick moves the "so that" clause (the value) into `rejected_spans`. That clause is not lost: it is stored as the entity's rationale (`src/tracepath/graph/model.py`) and shown as why-text. The open question is whether the value belongs in the Feature's span rather than its rationale. On this item the "so that" clause carried the feature's distinguishing value (the ranking being judgeable), not background; the engineer ruled the span too narrow. Scope: 20 of the corpus's 42 user stories carry a "so that", across 10 of 21 specs.

## Group A, entity 5 (`0021#requirements:6`, struck old AC-6): superseded text

Struck (superseded) text is ruled as one entity even when it bundles several conditions, since it is recorded as the thing that was replaced; atomicity is applied to current text only. Reason: splitting replaced text fragments the history without adding anything a chain needs.

## Open design question: partial supersession

- AC-4's new text says only its second sentence stopped being true, the first carried over. Splitting struck text would let the graph say exactly which part was superseded. Spec 0002 (AC-5 and its 0021 AC-2 test scenario) currently expects one struck entity per criterion, so the ruling applies the struck text rule consistently and leaves this as a possible spec 0002 amendment. Entity 4 was first ruled "should split" before the rule was set, then changed to agree for consistency.
- Second example: AC-7's tiebreaker fragment was superseded (single search rank replaced by the interleaved kept walk order), while AC-7 as a whole was amended.


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
