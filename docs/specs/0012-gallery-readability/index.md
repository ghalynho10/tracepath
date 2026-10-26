# 0012. Gallery readability

**Date**: 2026-10-26
**Status**: In Progress

## Summary

This spec makes the answer gallery easier to read for a stranger. Stored text shows `code` and **bold** as formatted text, code looking words are styled by a fixed pattern, and each entry gets a clear heading order. The top of each answer puts the model's verdict and my mark side by side, then my note and a link to my full ruling, then one "Explore the graph" strip. One line of totals sits beside the key to the marks. A link to one question, the page address plus `#<slug>`, opens that question's graph. The page and the graph panel change; no command changes, and nothing is stored differently except that each note in `gallery/marks.json` becomes a public note I write myself.

## Requirements

**User stories**:
- As a reader, I want inline code and bold shown as formatted text, so I can read a claim without raw marker characters.
- As a reader, I want each entry to have a clear heading order, so I can tell the question, the answer and the evidence apart.
- As a reader, I want the model's verdict and the engineer's mark side by side in different words, so I can compare them at a glance.
- As a reader, I want one total of the engineer's marks next to the key that defines them, so I know how the answers were judged overall.
- As the engineer, I want each note on the page written for a public reader, with a link to the full ruling where one exists.
- As the engineer, I want to send one link that opens one question's graph, so a reader lands on the picture without searching the page.

**Acceptance criteria** (each holds one claim; a criterion marked _browser_ is checked by looking at the page at 1440 by 900 and 390 by 844, because no test in CI draws a page):

*The inline rule* (the rule is in Feature design, "Inline formatting")
- **AC-1**: A pair of single backticks on one line, with at least one character between them and no backtick between them, shows the characters between them as code, and the two backticks are not shown.
- **AC-2**: A pair of `**` on one line, with at least one character between them, shows the characters between them as bold, and the two markers are not shown.
- **AC-3**: A code span inside a bold span shows as bold code.
- **AC-4**: A `**` inside a code span is shown as the two characters.
- **AC-5**: A single backtick or a `**` with no partner on its line is shown as typed.
- **AC-6**: A pair of markers never reaches across a line break.
- **AC-7**: A run of two or more backticks is shown as typed and is not a marker.
- **AC-8**: A single `*` is shown as typed.
- **AC-9**: With the code word patterns off, for every question, claim, missing note, marks note, item text and link phrase of the 31 shown records, putting the markers back by the rebuild rule of Feature design gives the stored text.
- **AC-10**: Markup inside a code span or a bold span, for example `<figure`, is shown as visible text and is not interpreted.
- **AC-11**: Each space separated word of a code span is its own element, so a word is the smallest piece a line may break at.
- **AC-12** (_browser_): On a line wide enough for it, a code word is never split at a hyphen.
- **AC-13** (_browser_): A code word wider than its line breaks inside the word rather than running past the edge of the page.

*Where the rule runs*
- **AC-14**: The question of an entry is formatted by the rule.
- **AC-15**: The text of each claim is formatted by the rule.
- **AC-16**: Each note in an entry's "What the answer says the records lack" list is formatted by the rule.
- **AC-17**: The entry's note is formatted by the rule, from the markers I type in it.
- **AC-18**: The full text of each cited item in Items sent is formatted by the rule.
- **AC-19**: A selected item's text in the graph panel is formatted by the rule.

*Code looking words* (the patterns are in Feature design, "Code words")
- **AC-20**: A file name in a question or a claim, outside a code span, is shown as code.
- **AC-21**: A `$` name in a question or a claim, outside a code span, is shown as code.
- **AC-22**: A CAPITAL_SNAKE word in a question or a claim, outside a code span, is shown as code.
- **AC-23**: A `name()` word in a question or a claim, outside a code span, is shown as code.
- **AC-24**: A lower_snake word in a question or a claim, outside a code span, is shown as code.
- **AC-25**: A product name on the exclusion list (`Next.js`, `Node.js`) is not shown as code.
- **AC-26**: The words the patterns find in the 31 questions and 107 claims equal the list a test pins: 15 words in 5 questions and 16 words in 10 claims on 2026-10-26, found by the regular expressions of Feature design.
- **AC-27**: A note in the "What the answer says the records lack" list is read for code words by the same patterns.
- **AC-28**: A file name or other code looking word in item text, outside a code span, is not styled.
- **AC-29**: A word in the entry's note that is not inside a code span is not styled as code.

*The entry's headings and parts*
- **AC-30**: An entry's title is an `h3` and its section headings are `h4`.
- **AC-31**: An entry's section headings, in order, are Question, Answer, What the answer says the records lack (when it shows) and Items sent.
- **AC-32**: An entry whose record has a missing list shows the section "What the answer says the records lack", whatever its mark.
- **AC-33**: An entry whose record has no missing list shows no such section.
- **AC-34**: The words "Missing, as the answer says" appear nowhere on the page.
- **AC-35**: Inside Items sent, the groups Cited and Not cited are `h5`.
- **AC-36**: The closed Items sent summary reads "Show all (N, M cited)", where N is the items sent and M the items the answer cites.
- **AC-37**: A claim that cites at least one id has a line that begins "Cites:" and holds every cited id.
- **AC-38**: A claim has a line that begins "Labels:" in which each label is its own chip element.
- **AC-39** (_browser_): Each section heading sits under a dark rule 2 pixels thick, at both widths.
- **AC-40** (_browser_): The entry matches the board measures in Feature design at both widths.

*The verdict and the mark*
- **AC-41**: The Answer section opens with one block holding the model's verdict first and my mark second.
- **AC-42**: A stored verdict `answered` shows as "answered", in mono type.
- **AC-43**: A stored verdict `partly` shows as "partly answered", in mono type.
- **AC-44**: A stored verdict `not_supported` shows as "not supported by the records", in mono type.
- **AC-45**: A stored verdict `no_documented_link` shows as "no documented link", in mono type.
- **AC-46**: The verdict is followed by the caption "— the model's verdict on its own answer".
- **AC-47**: No verdict wording equals a mark word (`right`, `partly right`, `wrong`, `declined`).
- **AC-48**: The build fails, exit 1, naming the record, when its stored verdict is none of the four codes.
- **AC-49**: The mark `right` is drawn in bold on a swipe of `#B9E3EE`.
- **AC-50**: The mark `partly right` is drawn in bold on a swipe of `#F6E27F`.
- **AC-51**: The mark `wrong` is drawn in bold on a swipe of `#FFC8C2`.
- **AC-52**: The mark `declined` is drawn in bold on a swipe of `#CBD3DC`.
- **AC-53**: The mark is followed by the caption "— my mark".
- **AC-54**: The mark is not a button and has no border.
- **AC-55** (_browser_): At 561 pixels wide and wider, the verdict and the mark sit side by side, and the verdict's words wrap balanced.
- **AC-56** (_browser_): At 560 pixels wide and narrower, the mark sits under the verdict.

*My note and my full ruling*
- **AC-57**: An entry with a note shows the bold words "My note." followed by the note, below the verdict and mark block.
- **AC-58**: An entry with no note shows no "My note.".
- **AC-59**: A source path that starts with `experiments/` shows "My full ruling" as a link to that file in this repository on GitHub.
- **AC-60**: A source path that does not start with `experiments/` shows the plain text "My full ruling: the <row> in the project's scope notes (not published)." with no link.
- **AC-61**: The build fails, exit 1, naming the entry, when a `source_path` that starts with `experiments/` is not a file under the build root (`--root`).
- **AC-62**: The built page holds no link into the `docs/` folder of this repository.
- **AC-63**: The development section's "v1 finish line" is plain text with no link.
- **AC-64**: A test pins the mark of each of the 31 entries as it stands on 2026-10-26: 17 right, 2 partly right, 2 wrong, 10 declined.

*The graph strip*
- **AC-65**: The Graph button is a `button` that is a direct child of the entry's `article`.
- **AC-66**: The strip's title reads "Explore the graph".
- **AC-67**: The strip's counts read "N sent · M cited", the same N and M as the Items sent summary.
- **AC-68**: The strip's drawing is the same in every entry.
- **AC-69**: The strip's drawing highlights no node.
- **AC-70** (_browser_): With scripts off, the strip is not shown and leaves no gap between the source line and the claims.

*The total of my marks*
- **AC-71**: One line states the number of entries shown, and that number equals the number of entries in `gallery/marks.json`.
- **AC-72**: The same line states a count for each of the four marks, and each equals the entries that carry that mark (17, 2, 2 and 10 on 2026-10-26).
- **AC-73**: A mark carried by no entry shows `0` in that line.
- **AC-74**: That line is inside the Key section, above the list that defines each mark.
- **AC-75**: Each mark word in that line is drawn as the swipe of AC-49 to AC-52.

*The graph panel* (spec 0011)
- **AC-76**: `graph.js` finds the question, the verdict block and the claim list anywhere inside the entry, not only as its direct children.
- **AC-77**: Each entry holds exactly one `.question`.
- **AC-78**: `graph.js` never sets `innerHTML`.
- **AC-79**: An item whose text holds a marker pair has a `runs` key in its graph data.
- **AC-80**: The graph window's styles use none of the four swipe colours.
- **AC-81** (_browser_): With nothing selected, the panel shows the same verdict wording and captions as the list.

*The link to one graph* (added 2026-10-26; takes in the Deferred entry "Shareable graph link" of the scope, without item selection. The address is written as in Feature design, "The link to one graph")
- **AC-82**: Each entry's `article` carries its slug as its `id`.
- **AC-83** (_browser_): With scripts off, opening the page with `#<slug>` scrolls to that entry.
- **AC-84** (_browser_): With scripts running, opening the page with `#<slug>` of an entry opens that entry's graph.
- **AC-85** (_browser_): A click on an entry's strip replaces the address fragment with `#<slug>` and adds no history step.
- **AC-86** (_browser_): Pressing previous or next replaces the address fragment with the slug of the graph now open and adds no history step.
- **AC-87** (_browser_): Closing the graph, by Esc or by the close button, clears the address fragment and adds no history step.
- **AC-88** (_browser_): After the graph closes, the page is at the entry whose graph was showing.
- **AC-89** (_browser_): An address fragment that is not an entry's slug opens the page as usual, with no graph and no error message.
- **AC-90** (_browser_): Selecting an item changes nothing in the address.
- **AC-91**: `graph.js` changes the address only with `history.replaceState`, and never with `pushState` or by setting `location.hash`.
- **AC-92** (_browser_): The address fragment is `#` followed by the entry's slug as spec 0011 AC-67 makes it, and nothing else.

*Added 2026-10-26 after the cross check* (the numbers follow AC-92 so no criterion moved; each splits or settles a point of an earlier one)
- **AC-93** (splits AC-65): The Graph button carries `data-graph` holding the entry's slug.
- **AC-94** (splits AC-65): The Graph button carries `hidden` in the built page.
- **AC-95** (splits AC-65): The Graph button comes after the source line and before the claims.
- **AC-96** (settles AC-11): The spaces between the words of a code span stay as text between its word elements.
- **AC-97** (settles AC-65): The Graph button's accessible name reads "Explore the graph: <label>, N sent, M cited".
- **AC-98** (splits AC-79): An item whose text holds no marker pair has no `runs` key in its graph data.
- **AC-99**: A link's phrase in the graph panel is formatted by the rule, from its explicit markers only.
- **AC-100**: A link whose phrase holds a marker pair has a `phrase_runs` key in its graph data.
- **AC-101**: A link whose phrase holds no marker pair has no `phrase_runs` key in its graph data.
- **AC-102** (splits AC-75): Each mark word in the Key's list of marks is drawn as the swipe of AC-49 to AC-52.
- **AC-103** (splits AC-77): Each entry holds exactly one `.verdict`.
- **AC-104** (splits AC-77): Each entry holds at most one `ol`.
- **AC-105** (splits AC-59): The "My full ruling" link is followed by `source_row` as text.

## Decision

**Chosen option**: Option 1: format in Python, send the panel plain data, follow canvas direction B.

One pure Python module reads a stored string and returns runs (a run is a piece of text with a code flag and a bold flag). The list writes each run as escaped HTML. The graph panel receives the same runs for an item's text in its data block, and `graph.js` only turns each run into an element with `textContent`. The entry layout follows direction B of the Claude Design canvas "tracepath answer block", boards "B · Highlighter · desktop 44rem" and "B · Highlighter · phone 390" (read 2026-10-26, version 1793038020-cd73).

**Follows**: escape at the point where HTML is written (output encoding) · functional core with an imperative shell, as the project's own rule.

## Rationale

Reasoning and options: see [rationale.md](rationale.md).

## Feature design

**Mode and platform**: ENHANCEMENT of the static gallery page of [spec 0010](../0010-answer-gallery/index.md) and the graph window of [spec 0011](../0011-answer-graph/index.md). No command, no stored record and no API call changes.

**Data model sketch**: nothing is stored beyond what exists. Three changes to data:
- `gallery/marks.json`: the `note` field now holds a note I write for a public reader. It is no longer copied word for word. The `mark` field never changes (AC-64). The field list and the other fields are as in spec 0010.
- The graph data block of each entry (spec 0011): an item gains `runs`, a list of `[text, flags]` pairs (flags: 0 plain, 1 code, 2 bold, 3 bold code), and a link gains `phrase_runs` in the same shape. Each key is absent, not `null`, when the text holds no marker pair (AC-79, AC-98, AC-100, AC-101).
- A new module `src/tracepath/gallery/inline.py` (pure): `Run` (frozen, `text`, `code`, `bold`), `runs(text, code_words)` and `to_html(runs)`.

**Inline formatting** (the rule; measured on the 31 shown records on 2026-10-26)
1. Work on one line at a time. A line is a part of the text between line breaks (AC-6).
2. Code first. A code span opens at a run of exactly one backtick and closes at the next run of exactly one backtick on the same line, with at least one character between. What is inside is not read again, so a `**` inside is plain (AC-1, AC-4). A run of two or more backticks is plain text and is never a marker (AC-7).
3. Then bold. Outside code spans, `**` markers on the line pair in order, first with second, third with fourth. A pair with at least one character between them is bold, and it may hold code spans (AC-2, AC-3).
4. A marker with no partner on its line is left as typed (AC-5). A single `*` is not a marker (AC-8).
5. No other markdown is read: no headings, tables, links or italics.
6. Escaping: every run's text goes through `html.escape` when the run is written, and nothing else writes markup, so stored markup always shows as text (AC-10). Reading the markers before escaping gives the same result as escaping first, because `html.escape` changes only `&`, `<`, `>`, `"` and `'`, and no marker is one of them.
7. Nothing is dropped, by this rebuild rule (AC-9): write each run's text; put `**` at each point where the bold flag changes between one run and the next, and at the start and end of the text when it begins or ends bold; and put one backtick before and after each code run. Code words are not rebuilt, because they have no backticks, so AC-9 is checked with the code word patterns off. The rule cannot tell `**a****b**` (two bold pairs with nothing between) from `**ab**`; no stored text holds `****`. The stored text is never changed in the record or the marks file.
8. A code run is written as `<code>` holding one element per space separated word (class `w`), and `.w` is `display: inline-block; max-width: 100%; overflow-wrap: anywhere`. Each space between two words stays as a text node between the `w` elements, in `to_html` and in `graph.js` (AC-96). An inline block cannot be split at a hyphen by the line around it, and `anywhere` lets a word wider than the line break rather than overflow (AC-11 to AC-13). This is checked in a browser at `/check verify`, because no test in CI draws a page (AGENTS.md, Layout).

*Measured 2026-10-26 on the 31 shown records, 2,602 stored texts* (31 questions, 107 claims, 46 missing notes, 10 notes, 2,408 item texts), by a prototype of the rule above:
- **Unpaired markers: 0.** No backtick without a partner and no `**` without a partner on any line. Only 9 of the 2,602 texts run over more than one line, and for none of them does pairing by whole text differ from pairing by line, so the one line rule costs nothing today.
- 43 of 107 claims and 1 of 31 questions hold a backtick; of the 125 cited items, 94 hold a backtick and 86 hold bold; no text holds a heading or a table.
- Shapes the rule must handle, each present in real data: two code spans on one line (Q4, claim 3: `--font-mono` and `--font-sans`); runs of two backticks around a code span (Held out 2, Q1, Q8 and Held out 4: item 0017#build-plan:4); a `**` inside a code span (Held out 2 and Q8: item 0017#build-plan:2, `test/eval/**/*.test.ts`); bold code (Held out 2: item 0021#feature-design:25, `**`skillCounts`**`); single asterisks (Eval 1: item 0021#feature-design:13).
- Longest code word: 31 characters in a claim, question or missing note as typed in backticks; 37 in a code word the patterns style (`test/integration/profile-form.test.ts` in Held out 1's question); 46 in a cited item; 53 in an item of the pack (`supabase/migrations/20260825162457_data_model.sql:168`, item 0013#follow-up:13 of Q14 and Q19). So the break fallback of AC-13 may matter for a question on a phone and does matter for item text.
- **A record to test the rule on: Q4.** Claim 3 holds two code spans with a hyphen inside each on one line. The real data holds no unpaired marker, so a fixture holds those cases (AC-5, AC-6), and Held out 2 is the hardest real record (double backticks, `**` inside code, bold code).

**Where the formatting runs for the graph panel.** The panel's answer view is a clone of parts of the entry in the list, so the question, claims and verdict block carry the list's HTML and need nothing in `graph.js` (basis: `graph.js` lines 377 to 381 clone `.question`, `.verdict` and `ol`). A selected item's text, and the phrase of each link listed under it, are the two things the script fills itself, from the data block. They get `runs` and `phrase_runs` from Python, and `graph.js` makes one element per run with `createElement` and `textContent`, splitting a code run's text on spaces into `w` elements with the spaces kept between them (AC-19, AC-96, AC-99). Link phrases carry only explicit markers: 102 of the 2,854 stored phrases hold a backtick and 1,490 hold `**`, measured 2026-10-26. The script never parses a marker and never sets `innerHTML` (AC-78). The only other script change is to find the three cloned parts anywhere inside the entry (AC-76), because the new layout no longer makes them direct children. All of the parsing sits in pytest, and the script change is small enough to check in a browser (AC-19, AC-81).

**Code words** (a fixed pattern list; stored text never changes, only styled)
A word outside any code span in a question or a claim is shown as code when it matches one of these:

Each pattern is a regular expression searched in each line, outside code spans. They are tried together in this order at each place, leftmost first; a match equal to a product name below is skipped. A word inside bold is searched too, and shows as bold code.

| Kind | Regular expression | Example from the records |
|---|---|---|
| file name | `(?<![\w/.$-])\w[\w.-]*(?:/[\w.()-]+)*\.(?:tsx?\|jsx?\|mjs\|json\|md\|py\|css\|sql\|ya?ml\|html\|sh\|toml)\b` | `src/proxy.ts`, `band-anchors.test.ts` |
| `$` name | `\$[A-Za-z_][A-Za-z0-9_]*(?::\d+)*` | `$ACTION_REF_1`, `$ACTION_1:0` |
| CAPITAL_SNAKE | `\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b` | `NODE_ENV`, `DEV_SESSION_ENABLED` |
| `name()` | `\b[A-Za-z_][A-Za-z0-9_.]*\(\)` | `readOwnProfile()` |
| lower_snake | `\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b` | `good_match`, `salary_min` |

(In the file name expression the bars are alternatives; in a Markdown table they are written `\|`.) A word inside a call, such as `BAND_ANCHORS` in `bandAnchorsHash(BAND_ANCHORS)`, is styled by its own pattern; the call itself is styled only when it ends in `()`.

Excluded: product names `Next.js` and `Node.js` (a constant list), because the file name expression would otherwise take them.

*Measured 2026-10-26:* the patterns find 15 words in 5 of the 31 questions and 16 words in 10 of the 107 claims. A test pins that list (AC-26). They find 0 words in the 46 missing notes.

**Board measures** (copied from the two boards of the canvas on 2026-10-26; this spec is the authority, not the canvas)

| Part | Desktop, column of 44rem | Phone, 390 |
|---|---|---|
| Entry title | 44px, line 1.05, letter spacing −0.02em, bold | 36px |
| Details line | mono 11px, letter spacing .04em, `#3F5877`, 6px under the title | same |
| Section block | 24px above, 14px padding, 2px `#011936` rule above | 20px above, 12px padding |
| Section heading | 18px bold | 17px |
| Question text | 22px, line 1.35, 8px under the heading | 19px, 6px |
| Verdict and mark block | 18px above; two equal columns, 32px gap | 14px above; one column, 14px gap |
| Verdict word | mono 22px, line 1.3, balanced wrap | mono 18px |
| Mark word | bold 22px on the swipe | bold 18px |
| Swipe | padding 0 6px, left margin −6px, radius `3px 8px 4px 9px / 8px 3px 9px 4px`, box decoration break `clone` | padding 0 5px, margin −5px |
| Caption | 12.5px `#3F5877`, 8px under the word | 12px, 6px |
| Note and source | 18px above, 14px padding, 1px rule `rgba(1,25,54,.14)` above; "My note." bold, 15px line 1.6, 36rem wide at most; source line 12px `#3F5877` | 14px above, 12px padding |
| Graph strip | 20px above, full width, 1.5px `#011936` border, radius 10px; drawing 176 by 72; title 16px bold; a line "Every item the model was sent and how they link, the cited ones labelled" 13px; counts mono 11.5px; a round `#011936` button of 40px with a white arrow | 16px above; drawing 96 by 64; no sentence; button 36px |
| Claim | 12px above; 1px rules above and below; 22px padding; number mono 11px; text 16px line 1.6; "Cites:" mono 12px, 8px above; "Labels:" mono 12px, 6px above, chips 11px with a 1px `rgba(1,25,54,.35)` border and radius 3px | padding 18px; text 15px |
| Missing section | 28px above, section rule; list 16px line 1.6 `#3F5877` | 24px above; 15px |

The phone layout applies at 560 pixels and narrower (the column minus its gutters; the board is 390). The swipe colours, with ink `#011936` on each, measure 12.8 to 1 (`right`), 13.5 (`partly right`), 12.0 (`wrong`) and 11.6 (`declined`); the mark's meaning is its word, never its colour alone.

**Verdict wording** (fixed; the stored code is unchanged)

| Stored code | Shown as |
|---|---|
| `answered` | answered |
| `partly` | partly answered |
| `not_supported` | not supported by the records |
| `no_documented_link` | no documented link |

The four codes are the `Verdict` type in `src/tracepath/ask/answer.py` (basis: line 23). The failed claims tally "N of M claims failed a check" (spec 0010 AC-33) is a second caption line under the verdict caption, in the caption style; the boards do not draw it and no shown record has a failed claim today, so this placement is mine.

**The top of the Answer section**, in order: the verdict and mark block (`.verdict` holds the word and its caption lines; `.mark` holds the swipe and its caption); the ruling block, when there is a note ("My note." and the note) and then the source line; the strip. The strip is the existing `button[data-graph]` (so spec 0011's AC-1 to AC-3 still hold), hidden until the script runs, with its spacing on the button itself and no wrapper, so nothing remains with scripts off (AC-65, AC-70). The strip is a direct child of the `article` (AC-65) because the entry is flat: its children are the title, the details line, the section headings and their blocks, with no wrapper element around a section, and each `h4` carries its own rule. The strip comes after the source line and before the claims (AC-95), carries `data-graph` and `hidden` (AC-93, AC-94), and has an accessible name that names its entry, `Explore the graph: <label>, N sent, M cited`, set as `aria-label` so the 31 strips can be told apart; this replaces spec 0011's `Graph: <label>` (AC-97). Its drawing is the one fixed SVG below, the same for every entry, in ink at low opacity, with no highlighted node; entry specific facts are only in the text (AC-68, AC-69). It is the board's 176 by 72 drawing with its inline style replaced by a class and `preserveAspectRatio="xMidYMid slice"` added, so CSS can show it at 96 by 64 on a phone cropped to its middle.

```html
<svg class="strip-drawing" width="176" height="72" viewBox="0 0 176 72" preserveAspectRatio="xMidYMid slice" aria-hidden="true"><rect width="176" height="72" rx="6" fill="#F2F4F7"></rect><g stroke="rgba(1,25,54,.18)" stroke-width="1"><path d="M26 30 46 30M46 30 70 36M52 40 70 36M78 26 98 24M98 24 122 16M116 44 128 40M116 44 118 52M92 50 88 60M92 50 84 48M108 34 116 44M138 28 128 40M40 18 46 30M14 12 24 20M24 20 26 30M148 46 158 40M156 14 144 8M138 28 156 14"></path></g><g fill="rgba(1,25,54,.3)"><circle cx="14" cy="12" r="1.8"></circle><circle cx="26" cy="30" r="1.8"></circle><circle cx="12" cy="52" r="1.8"></circle><circle cx="34" cy="60" r="1.8"></circle><circle cx="40" cy="18" r="1.8"></circle><circle cx="52" cy="40" r="1.8"></circle><circle cx="30" cy="44" r="1.8"></circle><circle cx="60" cy="10" r="1.8"></circle><circle cx="66" cy="58" r="1.8"></circle><circle cx="78" cy="26" r="1.8"></circle><circle cx="84" cy="48" r="1.8"></circle><circle cx="96" cy="10" r="1.8"></circle><circle cx="100" cy="64" r="1.8"></circle><circle cx="108" cy="34" r="1.8"></circle><circle cx="118" cy="52" r="1.8"></circle><circle cx="122" cy="16" r="1.8"></circle><circle cx="134" cy="62" r="1.8"></circle><circle cx="138" cy="28" r="1.8"></circle><circle cx="148" cy="46" r="1.8"></circle><circle cx="156" cy="14" r="1.8"></circle><circle cx="162" cy="58" r="1.8"></circle><circle cx="168" cy="32" r="1.8"></circle><circle cx="20" cy="64" r="1.8"></circle><circle cx="46" cy="30" r="1.8"></circle><circle cx="112" cy="8" r="1.8"></circle><circle cx="128" cy="40" r="1.8"></circle><circle cx="144" cy="8" r="1.8"></circle><circle cx="158" cy="40" r="1.8"></circle><circle cx="56" cy="24" r="1.8"></circle><circle cx="88" cy="60" r="1.8"></circle><circle cx="24" cy="20" r="1.8"></circle><circle cx="140" cy="54" r="1.8"></circle><circle cx="76" cy="8" r="1.8"></circle></g><path d="M70 36 98 24 116 44 92 50Z" fill="none" stroke="rgba(1,25,54,.18)" stroke-width="1"></path><g fill="rgba(1,25,54,.3)"><circle cx="70" cy="36" r="1.8"></circle><circle cx="98" cy="24" r="1.8"></circle><circle cx="116" cy="44" r="1.8"></circle><circle cx="92" cy="50" r="1.8"></circle></g></svg>
```

**The source line.** For a path under `experiments/`: `<a href="…/blob/main/<path>">My full ruling</a>, <source_row>`. For any other path: the plain text `My full ruling: the <source_row> in the project's scope notes (not published).`, with no link and no path (the engineer's wording of 2026-10-26; today the only such path is `docs/scope/scope.md`). The 27 entries sourced from experiments 0016 and 0018 link; the four held out entries (source `docs/scope/scope.md`) are plain, because `docs/` leaves the public repository after this feature merges (history kept). The "v1 finish line" link of the development section becomes plain text for the same reason, and the constant that held its URL is removed.

**The total of my marks.** One line inside the Key section, above the list of mark definitions, built from the marks entries at build: "My marks on the N shown answers:" then each mark word as a swipe followed by its count, in the order right, partly right, wrong, declined. On 2026-10-26: 31, 17, 2, 2, 10 (the counts sum to the total). The Key's mark rows use the same swipe instead of the old pill.

**Value sourcing**:
| Action | Value produced / displayed | Source |
|---|---|---|
| Render the verdict | word shown | a constant table from the stored `verdict` code; an unknown code fails the build (AC-48) |
| Render the mark | word, swipe colour | `mark` in `gallery/marks.json`; colour from a constant table (the four colours above) |
| Render the note | text | `note` in `gallery/marks.json` (my public note); null shows nothing |
| Render the source line | link text, target, row | `source_path`, `source_row` in `gallery/marks.json`; target is the repository URL constant plus the path, only for a path under `experiments/` |
| Render the strip | N sent, M cited | N is the number of the record's items; M is the number of items a claim cites without rejecting, the same value the Items sent summary uses (one function) |
| Render the strip | accessible name | the entry's `label` and the same N and M, written as `Explore the graph: <label>, N sent, M cited` |
| Render the total | total and four counts | counted over the entries read from `gallery/marks.json` |
| Format a text | runs | `inline.runs` from the stored string; code words only for a question, a claim and a missing note |
| Fill a selected item | runs | the item's `runs` in the graph data block, built by `inline.runs` at build |
| Fill a listed link | phrase runs | the link's `phrase_runs` in the graph data block, built by `inline.runs` at build, explicit markers only |

**The link to one graph.** The link is the page address plus `#<slug>`, where the slug is the one `slug_of` makes from the entry's label and spec 0011 AC-67 keeps unique (`Eval 3` gives `eval-3`; basis: `graph.py` `slug_of`). There is no copy button: the address bar is the link once a graph is open.
- The build writes the slug as the `id` of each entry's `article` (AC-82). With scripts off this alone makes the link scroll to the entry, because the browser follows a fragment to an element with that id (AC-83).
- With scripts running, the script reads the fragment once, after it has registered every Graph button, and matches it against the keys of that registry, which are the slugs. A fragment equal to a slug opens that graph with `open(slug)`; the match is exact, so `#Q4` is not `#q4`. Any other fragment, including `#gw-key`, which is an id on the page but not a slug, does nothing, shows no message and is left as it is (AC-84, AC-89). Matching by element id instead would let `#gw-key` reach `open` and throw.
- Opening a graph by a click, and swapping it with previous or next, replaces the fragment with `#<slug>` by `history.replaceState`, so the back button is not used up (AC-85, AC-86).
- Closing, by Esc or the close button, replaces the address with the same path and query and no fragment, by `history.replaceState`. This does not scroll. The close event then hands focus to the Graph button of the graph that was showing (spec 0011 AC-6), so the page is at the entry whose graph was showing, which after a previous or next is not always the entry it was opened from; the code does not change (AC-87, AC-88). All closing paths end in the dialog's `close` event, where it is done.
- The script uses no other way to change the address (AC-91).
- The fragment holds the slug only. Selecting an item never changes the address, so a link cannot select an item (AC-90, AC-92). Item selection in a link stays deferred.
- A label is the key of its link. Renaming a label in `gallery/marks.json` changes its slug and breaks any link already sent; nothing in the build can know which links were sent (Consequences). A label must not make a slug that starts `graph-` or `gw-`, because the page already holds ids with those starts.
- Typing a new fragment into a page that is already open is not handled; the link opens its graph when the page loads.

**Key invariants**:
- No text reaches the page unescaped. Every run is escaped where HTML is written (AC-10).
- Stored text is never changed; formatting only styles it (AC-9).
- A mark is never changed by editing a note (AC-64).
- The page holds no link into this repository's `docs/` and no code or test reads `docs/` (AC-62). `docs/specs`, `docs/scope` and `docs/reviews` leave the public repository after this feature merges, so nothing here may depend on them being public.
- The build still makes no network or API call and writes only the output folder (spec 0010 AC-56, AC-57).

**Security model**: the page is public. The new risk is formatted text reaching HTML, and it is closed by escaping every run at write time and by `graph.js` never using `innerHTML` (AC-10, AC-78). No secret is read. No compliance scope applies.

**Configuration required**: none. Constants in code: the verdict wordings, the four swipe colours, the product name exclusion list, the code word patterns, the fixed strip drawing.

**Critical test scenarios** (each maps to an acceptance criterion):
- Happy path on a real record: Q4's claims show `--font-mono` and `--font-sans` as code with no backtick left, verifies **AC-1, AC-11, AC-15**.
- Edge on real records, through `inline.runs` and the data block (none of these items is cited, so the list shows no text for them): Held out 2's item 0017#build-plan:4 gives its code span with the double backticks as typed; item 0017#build-plan:2 gives `**` inside code as typed; item 0021#feature-design:25 gives bold code; Eval 1's item 0021#feature-design:13 gives its single asterisks as typed, verifies **AC-3, AC-4, AC-7, AC-8, AC-79, AC-98**.
- Property on the 31 records: a link phrase with a pair has `phrase_runs` and one without has none, verifies **AC-100, AC-101**.
- Fixture: a code span with spaces keeps its spaces between its word elements, verifies **AC-96**.
- Fixture: unpaired backtick, unpaired `**`, a pair split by a line break, verifies **AC-5, AC-6**.
- Property on the 31 records: with code words off, the rebuild rule gives back every one of the 2,602 stored texts and the 2,854 link phrases, verifies **AC-9**.
- Fixture: `<figure` inside a code span and inside bold, verifies **AC-10**.
- Pinned list: the code words of the 31 questions and 107 claims equal the list, verifies **AC-20 to AC-26, AC-29**.
- Fixture: a note in the missing list is read for code words, and a bare file name in item text is not, verifies **AC-27, AC-28**.
- Fixture per verdict code, and one unknown code, verifies **AC-42 to AC-48**.
- Real page: every entry has one `.question`, one `.verdict`, at most one `ol`; the Answer section opens with the verdict block, then the mark block; the strip is a hidden direct child after the source line and before the claims, with `data-graph`, its accessible name and its counts equal to the Items sent counts, verifies **AC-41, AC-65, AC-67, AC-77, AC-93 to AC-95, AC-97, AC-103, AC-104**.
- Real page: the total line reads 31, 17, 2, 2, 10 and sits in the Key above the mark list, verifies **AC-71 to AC-75, AC-102**.
- Real page: no link into this repository's `docs/`; the four held out entries read "My full ruling: the v1 finish line in the project's scope notes (not published)." as text; the 27 others link and show their row as text, verifies **AC-59, AC-60, AC-62, AC-63, AC-105**.
- Fixture: an `experiments/` source path that is not a file under the `--root` fails the build, verifies **AC-61**.
- Pinned marks: the 31 marks equal the pinned list, verifies **AC-64**.
- Static: `graph.js` finds the three parts anywhere in the entry and never sets `innerHTML`; the swipe colours are absent from the graph styles, verifies **AC-76, AC-78, AC-80**.
- Real page: each entry's `article` has its slug as `id`; the slugs are unique, verifies **AC-82**.
- Static: `graph.js` calls `history.replaceState` and never `pushState` or `location.hash =`, verifies **AC-91**.
- Browser: see `verify.md`, verifies **AC-12, AC-13, AC-39, AC-40, AC-55, AC-56, AC-70, AC-81, AC-83 to AC-90, AC-92**.

## Build plan

Approach: Tracer Bullet (the project default). The first slice is one thin thread through every layer that changes: a text formatted in Python, written into the list, carried in the data block and drawn by the script.

1. [x] Slice 1, the thread. Add `inline.py` with the rule (runs, escaping, code spans, bold, unpaired, double backticks, `w` words) and its tests on Q4 and Held out 2; format the claim text in the list; add `runs` to the graph data block and make `graph.js` draw a selected item's text from it with `textContent`, satisfies **AC-1 to AC-11, AC-15, AC-19, AC-78, AC-79, AC-96, AC-98**
2. [x] Slice 2, where the rule runs. Format the question, missing notes, the note and the cited items of Items sent, add the code word patterns with the pinned list test, and send `phrase_runs` for link phrases and draw them in the panel, satisfies **AC-14, AC-16, AC-17, AC-18, AC-20 to AC-29, AC-99, AC-100, AC-101**
3. [ ] Slice 3, verdict and mark. The verdict wording table with its failure on an unknown code, the four swipe colours, both captions, the Key's mark rows in the swipe style and the total line, satisfies **AC-41 to AC-54, AC-71 to AC-75, AC-102**
4. [ ] Slice 4, the entry's headings and the claim lines. The `h4` sections in order, the renamed missing section, `h5` groups and the Items sent summary, the "Cites:" and "Labels:" lines with chips; update the tests that name the old strings, satisfies **AC-30 to AC-38**
5. [ ] Slice 5, note, source and strip. "My note.", "My full ruling" with the `experiments/` rule and its build check, plain text for `docs/` sources and the development section's line, the pinned marks test, the strip with its fixed drawing, counts and accessible name, and the `graph.js` selectors; make the test fixture's marks paths real (it names `experiments/0016-hops/README.md`, but the folder is `0016-link-hops`) and give it the `experiments/` files the new check needs, satisfies **AC-57 to AC-70, AC-76, AC-77, AC-93 to AC-95, AC-97, AC-103, AC-104, AC-105**
6. [ ] Slice 6, the link to one graph. The slug as the `id` of each `article`; in `graph.js`, open the graph named by the fragment when the page loads, replace the fragment on open, swap and close with `history.replaceState`, and leave an unknown fragment alone, satisfies **AC-82, AC-84, AC-85, AC-86, AC-87, AC-89, AC-90, AC-91, AC-92**
7. [ ] Slice 7, the visual pass. Write the styles from the board measures at both widths; check each browser criterion in `verify.md` at 1440 by 900 and 390 by 844; keep the four swipe colours out of the graph styles, satisfies **AC-12, AC-13, AC-39, AC-40, AC-55, AC-56, AC-70, AC-80, AC-81, AC-83, AC-88**

## Consequences

**Positive**:
- A reader sees code and bold as formatted text, a heading order they can scan, and the model's verdict and my mark in different words side by side.
- The parsing is pure Python under pytest, so the one piece of script that stays untested in CI does no parsing.
- One total of the marks tells a stranger how the answers were judged.

**Negative / tradeoffs**:
- The graph data block grows. The 31 blocks hold 0.93 million characters of item text today (block size 2.6 MB of a 3.5 MB page), and `runs` repeats the text of an item that has a pair (about 0.9 million characters), and `phrase_runs` the 1,579 link phrases with a marker (about 0.08 million), so the page may grow by up to about 1 MB. This is far under GitHub Pages limits (basis: spec 0010 Consequences) and is accepted.
- The fixed word patterns can style a word that is not code, for example a snake case word in prose. They cannot style camelCase names. This is the price of a fixed list; the pinned list test shows each change.
- The four held out entries lose their public note wording and say their full ruling is in notes that are not published ("My full ruling: the v1 finish line in the project's scope notes (not published)."). This is the engineer's ruling.
- The design source is a private canvas. The table in this spec is the copy; the canvas can change without this spec.
- The styles and the `graph.js` changes (the cloned parts, the runs, the link to one graph) are checked in a browser, not in CI.
- Renaming a label in `gallery/marks.json` breaks links already sent, because the slug is made from the label. Nothing keeps a list of links that were sent.
- `gallery/marks.json`'s `note` is no longer a word for word copy, so the original wording lives only in the experiment READMEs (and `docs/scope/scope.md` until it leaves the public repository).

**Neutral**:
- New module `src/tracepath/gallery/inline.py`; `render.py`, `graph.py` and `graph.js` change; several tests that name old strings or the old pill change.
- Experiment 0018's README and `docs/scope/scope.md` keep the original notes untouched.
- It takes in the Deferred entry "Shareable graph link" of the scope without item selection. A link that also selects an item stays deferred (spec 0011 Follow-up).
- Out, by ruling: rewording "the engineer" or "the author" in JobHunt's text and in the answers that repeat it, and listing the 13 records the page does not show.

## Follow-up

- [x] Rule on the open question of the code word patterns. _Ruled 2026-10-26: keep both._ The "What the answer says the records lack" list follows the same patterns (AC-27), and item text does not (AC-28), because item text is JobHunt's own words, where the author already marked code. AC-27 and AC-28 stand.
- [x] Rule on the label chips (_ruled 2026-10-26: HISTORY as stored_): the board draws `history` in lower case; spec 0010 AC-27 and the Key show `HISTORY`. This spec keeps the stored wording of every label and chip.
- [ ] Write the notes: the 10 notes in `gallery/marks.json` are mine to write for a public reader. No note and no mark was drafted or changed by this spec.
- [x] Confirm the wording of the plain text source line and the placement of the failed claims caption under the verdict caption. _Ruled 2026-10-26: the source line reads "My full ruling: the v1 finish line in the project's scope notes (not published)."; the failed claims count is a caption under the verdict caption._
- [x] Phone layout at 560 pixels and narrower, AC-61, AC-64 and AC-86 kept; the `graph-` and `gw-` label prefixes stay unchecked and typing a fragment into an open page stays unhandled. _Ruled 2026-10-26._
- [ ] After the merge, `docs/specs`, `docs/scope` and `docs/reviews` leave the public repository. Reconcile the links in `README`, `AGENTS.md` and the gallery's own comments that name those paths, in a later change.
- [ ] Dark mode, recorded in spec 0010's Follow up, stays deferred; the swipe colours were chosen for a white page only.

## References

**Project sources**:
- [spec 0010](../0010-answer-gallery/index.md) (page, marks file, AC-12 to AC-16, AC-18, AC-20, AC-24, AC-25, AC-33, `index.md` line 132) and [spec 0011](../0011-answer-graph/index.md) (panel, AC-1, AC-2, AC-37, AC-42, AC-53).
- `src/tracepath/gallery/render.py` (heading, pill and eyebrow styles, `_verdict`, `_mark`, `_missing`, `SCOPE_URL`), `src/tracepath/gallery/assets/graph.js` (lines 377 to 381, 426) and `src/tracepath/ask/answer.py` (line 23).
- `AGENTS.md`: Layout (no JavaScript test or linter in CI), Rules (functional core, immutable data).
- The Claude Design canvas "tracepath answer block", boards B desktop and B phone, read 2026-10-26.
- `docs/scope/scope.md`, feature 19.

**Practices & standards**:
- Output encoding at the point where HTML is written.
- Pure parsing in a tested core, with the shell only mapping data to elements.
