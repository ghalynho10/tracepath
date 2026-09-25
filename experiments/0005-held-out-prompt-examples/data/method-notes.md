# Method notes, experiment 0005 ruling

Findings about the ruling method itself, kept apart from the item marks so the tally stays a clean count.

## Group A, entity 1 (`0021#requirements:1`, Feature): the deletion trick and user stories

The deletion trick asks whether a testable condition disappears, which has no answer for a Feature, since a Feature states why something exists rather than a testable behaviour. For "As a... I want... so that..." stories, the trick moves the "so that" clause (the value) into `rejected_spans`. That clause is not lost: it is stored as the entity's rationale (`src/tracepath/graph/model.py`) and shown as why-text. The open question is whether the value belongs in the Feature's span rather than its rationale. On this item the "so that" clause carried the feature's distinguishing value (the ranking being judgeable), not background; the engineer ruled the span too narrow. Scope: 20 of the corpus's 42 user stories carry a "so that", across 10 of 21 specs.

## Group A, entity 5 (`0021#requirements:6`, struck old AC-6): superseded text

Struck (superseded) text is ruled as one entity even when it bundles several conditions, since it is recorded as the thing that was replaced; atomicity is applied to current text only. Reason: splitting replaced text fragments the history without adding anything a chain needs.
