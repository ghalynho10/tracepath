# 0008. Review volume and routing policy: rationale

## Context

Spec 0002's review routing (AC-11) holds an item back for one or more reasons: `runs_disagree` (the three runs don't agree on it), `known_trap_flag` (the model flagged something risky about its own cut, such as `multi_condition_split`), `unclassified_type`, `endpoint_not_accepted` (a link whose entity exists but was itself held), and `span_not_located`. The mechanism was built to be strict by design: nothing unverified reaches the graph by default. That strictness now produces 990 queued rows across 29 units (`artifacts/review-queue.json`, rebuilt at `2042871`): `known_trap_flag` 502, `runs_disagree` 471, `endpoint_not_accepted` 293, `unclassified_type` 6, `span_not_located` 1 (a row can carry more than one). Extrapolated to the whole corpus (feature 9), that is thousands of rows for one reviewer, which the project's own standing rule ("no verification layer, because the visible chain is the check") was never meant to require.

Two framings compete, and neither wins by argument alone. One reads the queue as the right mechanism with thresholds set too tight: measure where it over flags, loosen there, keep a person in the loop for what is left. The other reads a human review queue of this size as itself the verification layer the project's standing rule rejects, and asks whether a held item should instead be shown in the chain with its status, the way `unclassified` entities and `:Unresolved` links already surface uncertainty without blocking it. A status view of this kind (`--with-held`, spec 0005) already exists; the scope's own guard is that existing code must not win by default, only by evidence.

Two prior results narrow what the evidence can show. Experiment 0012 found that every item the existing `--code-pass` releases (a narrow rule already built for one specific case, spec 0007) was ruled agree by the engineer, 13 of 13, though too few of one unit's items were released to call that unit's result conclusive. Experiment 0013, a blind error analysis of 20 held items across the five hold reasons, found a sharp split: every item held only for `known_trap_flag` or `endpoint_not_accepted` where all three runs produced the identical signature (8 items) was ruled agree; every disagree (6 of 20) was a `runs_disagree` item, and of the 4 items only one run found, 3 were wrong. All 20 came from `claude-sonnet-5` units, so this is evidence about the kinds of failure behind each reason, not yet their rate on `claude-sonnet-5-5`.

Spec 0007 set a precedent worth following here: its decision rule (the code pass's exact release condition) was committed in `c004a30` before any paid call, and only then did experiment 0012 measure against it. The same shape resolves this spec's own ordering tension: the scope row asks that both candidates run through the eval before the spec is written, and that the decision rule be committed before either candidate runs. Both hold if the rule and the candidate definitions are committed now, the candidates are built and measured later, and a dated amendment then records the result without touching the committed rule.

## Options considered

### Option 1: Tune the routing (the narrow hold rule)

Measure where the queue over flags and release those items by a stated rule, keeping a person in the loop for what is left. This spec's `--narrow-hold` candidate is one concrete version: release `known_trap_flag` and `endpoint_not_accepted` holds where all three runs agree, the exact condition experiment 0013's evidence supports.

**Pros**:
- Reduces review volume directly when it wins, the scope row's own stated goal.
- Builds on a release mechanism (`accepted_by`, flag composition) spec 0007 already proved out for one narrower case.

**Cons**:
- Run agreement shows repeatability, not correctness; the blind ruling (AC-10) exists exactly because experiment 0012 could not call its own unit conclusive, and experiment 0013's sample is 20 items from `claude-sonnet-5` units only.
- Touches only two of five hold reasons; `runs_disagree`, the largest reason (471 rows), is untouched by design, because 0013's evidence points the other way for it (3 of 4 one run only items were wrong).

### Option 2: Question whether the queue belongs here (show with status)

Treat a held item the way `unclassified` and `:Unresolved` already work: visible in the chain, never silently blocking it. Spec 0005 already built this as an opt in view; this spec's question is only whether it becomes the default.

**Pros**:
- Matches the project's own standing rule, that the visible chain is the check, more literally than a review queue of any size does.
- Already built and measured once (experiment 0010); adopting it as default is a flag flip, not new code.

**Cons**:
- Never reduces review volume (spec 0005's own Consequences say so); feature 9's thousands of rows stay thousands of rows, just visible with a `HELD:` marker instead of absent.
- Cannot, by spec 0006's own scoring rule (AC-6b), ever turn a question's verdict into a pass; its only measurable win is visibility, which this spec's AC-11 states as a fact about the candidate rather than treating it as a defect in the comparison.

## Rationale

Neither option is chosen in this spec. The scope's own guard, that the framing with no build yet gets the same weight as the one already built, rules out picking Option 2 by default just because spec 0005 exists, and rules out picking Option 1 by default just because it is the more familiar "tune the thresholds" move. The first attempt at a decision rule in this spec's own design conversation tried to score both options against spec 0006's existing PASS/FAIL verdict, and that rule itself was biased: a held only step can never flip a verdict to PASS by construction (spec 0006 AC-6b), so Option 2 could never win under it regardless of evidence. The rule actually committed here (AC-9 to AC-12) instead measures each option on the terms its own value proposition claims: Option 1 is credited only for a step that newly becomes accepted (real review volume reduction), Option 2 only for a step that newly becomes visible (real status without acceptance). Neither can win by the other's measure, and both are reported from the same underlying table (AC-8), so the comparison is symmetric even though the two things being measured are different.

The blind ruling gate on Option 1 (AC-10) exists because experiment 0013's own known limits say so directly: "4 items per group show kinds of failure, not rates," and all 20 came from one model. A table showing a new accepted step is necessary evidence that the rule changes something, but spec 0002's own standard, that routing may not accept what the runs only repeat rather than confirm, means it is not sufficient; a human ruling, drawn blind and controlled against the exact weakness experiment 0012 already found (type alone revealing the arm), is what closes that gap without re running the full accuracy bar experiment 0005 and 0012 already carried.

The explicit fallback (AC-12) is what keeps this spec honest about a real possibility: that neither candidate changes a single step, because every one of the five eval questions' blocking holds is `runs_disagree` (not touched by Option 1) in a place `--with-held`'s own walk never reaches either. The scope row already names this exact alternative ("feature 9 is unblocked or explicitly allowed to run at the current ratio"), so the rule does not need to invent a third option to cover it.

An independent cross check of this spec's first draft found that adopting either candidate as written would silently contradict two already Accepted specs: spec 0002 AC-11 promises "only accepted items are written to the graph by default" and spec 0005's own invariants promise "no default path reads a held item," both of which a flipped default would break without anyone saying so. The fix applied (AC-10b, AC-11b) follows spec 0007's own precedent exactly: its AC-34 amended spec 0002 AC-11 for the code pass case before that case shipped, rather than letting the code silently diverge from the spec. Adopting either candidate here is therefore two commits, not one: the amendment to the affected already Accepted spec's own criteria (with its own tests updated in that same commit), then the default flip as a separate, following commit.

## References

**Project sources**:
- Spec 0002, AC-11 and its lettered amendments (the five hold reasons, the `endpoint_not_accepted` ordering, the counter assertion `GraphWriteFailed` guards)
- Spec 0005 (the held item view, `--with-held`, and its stated limit: "this view does not reduce the review volume")
- Spec 0006, AC-6b (a held only item counts as not reached, never a pass) and AC-28 (the held out guard)
- Spec 0007 (the `--code-pass` precedent: a committed release condition in `c004a30`, measured afterward by experiment 0012, and the `accepted_by` field this spec extends)
- `docs/scope/scope.md`, feature 11's row (the two candidate framings, the "equal terms" guard, and the Done when this spec's AC-7, AC-8, AC-12, AC-13 satisfy)
- Experiment 0012 (`experiments/0012-extraction-accuracy-step-one/README.md`): the blind ruling method this spec's AC-10 reuses, and its recorded weakness (type alone revealing the arm) that AC-10's control draw corrects for
- Experiment 0013 (`experiments/0013-held-item-error-analysis/README.md`): the evidence behind AC-1's exact release condition (`known_trap_flag`/`endpoint_not_accepted` under full agreement) and behind leaving `runs_disagree` untouched

**Practices & standards**:
- Committing a decision rule before measuring against it, then amending the record with the result rather than rewriting the rule (the pattern this spec and spec 0007 both follow)
