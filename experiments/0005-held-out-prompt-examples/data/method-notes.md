# Method notes, experiment 0005 ruling

Findings about the ruling method itself, kept apart from the item marks so the tally stays a clean count.

## Group A, entity 1 (`0021#requirements:1`, Feature): the deletion trick and user stories

The deletion trick asks whether a testable condition disappears, which has no answer for a Feature, since a Feature states why something exists rather than a testable behaviour. For "As a... I want... so that..." stories, the trick moves the "so that" clause (the value) into `rejected_spans`. That clause is not lost: it is stored as the entity's rationale (`src/tracepath/graph/model.py`) and shown as why-text. The open question is whether the value belongs in the Feature's span rather than its rationale. On this item the "so that" clause carried the feature's distinguishing value (the ranking being judgeable), not background; the engineer ruled the span too narrow. Scope: 20 of the corpus's 42 user stories carry a "so that", across 10 of 21 specs.

## Group A, entity 5 (`0021#requirements:6`, struck old AC-6): superseded text

Struck (superseded) text is ruled as one entity even when it bundles several conditions, since it is recorded as the thing that was replaced; atomicity is applied to current text only. Reason: splitting replaced text fragments the history without adding anything a chain needs.

## Open design question: partial supersession

AC-4's new text says only its second sentence stopped being true, the first carried over. Splitting struck text would let the graph say exactly which part was superseded. Spec 0002 (AC-5 and its 0021 AC-2 test scenario) currently expects one struck entity per criterion, so the ruling applies the struck text rule consistently and leaves this as a possible spec 0002 amendment. Entity 4 was first ruled "should split" before the rule was set, then changed to agree for consistency.

## Group A findings

- AC-12 (line 111) and AC-15 (line 129) each state that the fault state and the not-yet state must render distinguishable copy, but no after run wrote any link between them. It would be `unclassified`, phrase "the two must render distinguishable copy".
- AC-17 (lines 137 to 158) carries a struck old version; run 1 left it out of the span, correctly, but did not extract it as its own old-version entity, as spec 0002 AC-5 expects and as the model did for AC-2 and AC-6.
- Entities ruled: 7 of 10 (1 to 5, 8 and 10); 6, 7 and 9 skipped by choice.
