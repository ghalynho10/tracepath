"""The inline rule of the gallery (spec 0012): `code`, **bold** and code looking words."""

import json
from pathlib import Path
from typing import Any

import pytest

from tracepath.ask.record import ASKS_DIR
from tracepath.gallery.inline import Run, has_pair, runs, to_html
from tracepath.gallery.records import MARKS_FILE
from tracepath.gallery.render import STYLE

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _marks() -> list[dict[str, Any]]:
    marks: list[dict[str, Any]] = json.loads((PROJECT_ROOT / MARKS_FILE).read_text("utf-8"))
    return marks


def _records() -> dict[str, dict[str, Any]]:
    """Each shown record, by its marks entry's label."""
    return {
        entry["label"]: json.loads(
            (PROJECT_ROOT / ASKS_DIR / entry["record"]).read_text(encoding="utf-8")
        )
        for entry in _marks()
    }


def _rebuilt(found: tuple[Run, ...]) -> str:
    """The rebuild rule of spec 0012: `**` where boldness changes, a backtick around code."""
    out = []
    bold = False
    for run in found:
        if run.bold != bold:
            out.append("**")
            bold = run.bold
        out.append(f"`{run.text}`" if run.code else run.text)
    return "".join(out) + ("**" if bold else "")


def _plain(text: str) -> tuple[Run, ...]:
    return (Run(text, code=False, bold=False),)


def test_a_backtick_pair_is_code_and_its_backticks_are_not_shown() -> None:
    """AC-1."""
    found = runs("set `--font-mono` here")

    assert found == (
        Run("set ", code=False, bold=False),
        Run("--font-mono", code=True, bold=False),
        Run(" here", code=False, bold=False),
    )
    assert "`" not in to_html(found)


def test_a_pair_of_double_stars_is_bold_and_its_markers_are_not_shown() -> None:
    """AC-2."""
    found = runs("a **firm** rule")

    assert found[1] == Run("firm", code=False, bold=True)
    assert to_html(found) == "a <strong>firm</strong> rule"


@pytest.mark.parametrize("text", ["a **** b", "****"])
def test_a_pair_of_double_stars_with_nothing_between_is_shown_as_typed(text: str) -> None:
    """AC-2: a pair needs at least one character between its markers."""
    assert runs(text) == _plain(text)


def test_a_code_span_inside_bold_is_bold_code() -> None:
    """AC-3."""
    found = runs("**`skillCounts`** (added)")

    assert found[0] == Run("skillCounts", code=True, bold=True)
    assert to_html(found).startswith('<strong><code><span class="w">skillCounts</span></code>')


def test_double_stars_inside_a_code_span_are_shown_as_typed() -> None:
    """AC-4."""
    assert runs('`["test/eval/**/*.test.ts"]`') == (
        Run('["test/eval/**/*.test.ts"]', code=True, bold=False),
    )


@pytest.mark.parametrize(
    "text", ["one `tick only", "one **star pair only", "`a` then `b", "**a** then **b"]
)
def test_a_marker_with_no_partner_is_shown_as_typed(text: str) -> None:
    """AC-5: the last marker of an odd count has no partner and stays in the text."""
    shown = "".join(run.text for run in runs(text))

    assert shown.count("`") + shown.count("**") == 1


@pytest.mark.parametrize("text", ["`a\nb`", "**a\nb**"])
def test_a_pair_never_reaches_across_a_line_break(text: str) -> None:
    """AC-6."""
    assert runs(text) == _plain(text)


@pytest.mark.parametrize("text", ["``a``", "a `` b `` c", "```a```"])
def test_a_run_of_two_or_more_backticks_is_not_a_marker(text: str) -> None:
    """AC-7."""
    assert runs(text) == _plain(text)


def test_a_code_span_keeps_double_backticks_around_it_as_typed() -> None:
    """AC-7: a single backtick pair still opens and closes beside a double run."""
    found = runs("named `` `${pair.id}` `` here")

    assert [run.text for run in found if run.code] == ["${pair.id}"]
    assert _rebuilt(found) == "named `` `${pair.id}` `` here"


@pytest.mark.parametrize("text", ["*a*", "a * b", "(*see above*)"])
def test_a_single_star_is_shown_as_typed(text: str) -> None:
    """AC-8."""
    assert runs(text) == _plain(text)


def _stored_texts() -> list[str]:
    """Every question, claim, missing note, marks note and item text of the shown records."""
    texts = [m["note"] for m in _marks() if m["note"] is not None]
    for record in _records().values():
        texts.append(record["question"])
        texts.extend(claim["text"] for claim in record["claims"])
        texts.extend(record["missing"])
        texts.extend(item["text"] for item in record["items"])
    return texts


def _phrases() -> list[str]:
    return [
        link["phrase"]
        for record in _records().values()
        for link in record["links"]
        if link["phrase"] is not None
    ]


def test_the_markers_put_back_give_every_stored_text() -> None:
    """AC-9: with code words off, nothing of a stored text is dropped or changed."""
    texts = _stored_texts() + _phrases()

    assert [_rebuilt(runs(text)) for text in texts] == texts
    assert len(_records()) == 31


@pytest.mark.parametrize("text", ["see `<figure>`", "see **<figure>**"])
def test_markup_inside_code_or_bold_is_shown_as_text(text: str) -> None:
    """AC-10."""
    shown = to_html(runs(text))

    assert "&lt;figure&gt;" in shown
    assert "<figure" not in shown


def test_each_word_of_a_code_span_is_its_own_element() -> None:
    """AC-11."""
    assert to_html(runs("`a b-c`")) == (
        '<code><span class="w">a</span> <span class="w">b-c</span></code>'
    )


@pytest.mark.parametrize(
    ("text", "shown"),
    [
        (
            "over (`a-b`), then",
            'over <span class="g">(<code><span class="w">a-b</span></code>),</span> then',
        ),
        (
            "see (`a` and `b`)",
            'see <span class="g">(<code><span class="w">a</span></code></span> and '
            '<span class="g"><code><span class="w">b</span></code>)</span>',
        ),
        (
            "`a`/`b`",
            '<span class="g"><code><span class="w">a</span></code>/'
            '<code><span class="w">b</span></code></span>',
        ),
        ("a `b` c", 'a <code><span class="w">b</span></code> c'),
        ("(`a`)\nb", '<span class="g">(<code><span class="w">a</span></code>)</span>\nb'),
    ],
)
def test_a_code_run_shares_one_element_with_the_text_it_touches(text: str, shown: str) -> None:
    """AC-12: a line never breaks between a code word and `(` or `),` against it."""
    assert to_html(runs(text)) == shown


def test_the_glue_never_breaks_at_its_edges_but_its_code_may_break_inside() -> None:
    """AC-12, AC-13: the glue does not wrap; a one word code inside it does not wrap at
    its end either, while a longer code breaks between its words and a word wider than
    its line still breaks inside itself."""
    assert ".g { white-space: nowrap; }" in STYLE
    assert ".g code { white-space: pre-wrap; }" in STYLE
    assert ".g code:has(> .w:only-child) { white-space: nowrap; }" in STYLE
    assert "overflow-wrap: anywhere; white-space: pre-wrap; }" in STYLE


def test_the_spaces_of_a_code_span_stay_as_text_between_its_words() -> None:
    """AC-96: every space is kept, between the word elements and never inside one."""
    shown = to_html(runs("` a  b `"))

    assert shown == '<code> <span class="w">a</span>  <span class="w">b</span> </code>'


@pytest.mark.parametrize(
    ("text", "word"),
    [
        pytest.param("read src/proxy.ts first", "src/proxy.ts", id="AC-20 file name"),
        pytest.param("the $ACTION_REF_1 key", "$ACTION_REF_1", id="AC-21 dollar name"),
        pytest.param("when NODE_ENV is set", "NODE_ENV", id="AC-22 CAPITAL_SNAKE"),
        pytest.param("calls readOwnProfile() once", "readOwnProfile()", id="AC-23 call"),
        pytest.param("a good_match row", "good_match", id="AC-24 lower_snake"),
    ],
)
def test_a_code_looking_word_is_code(text: str, word: str) -> None:
    """AC-20 to AC-24: each pattern, outside a code span, and only when asked."""
    assert [run.text for run in runs(text, code_words=True) if run.code] == [word]
    assert not has_pair(runs(text))


def test_a_code_looking_word_inside_bold_is_bold_code() -> None:
    """Code words: a word inside bold is searched too."""
    assert Run("NODE_ENV", code=True, bold=True) in runs("**NODE_ENV only**", code_words=True)


def test_a_product_name_is_not_code() -> None:
    """AC-25."""
    assert not has_pair(runs("built on Next.js and Node.js", code_words=True))


#: The code words the patterns find on 2026-10-26, by question (AC-26).
QUESTION_WORDS = {
    "Eval 1": ["src/lib/landing-rule.ts", "readOwnProfile()"],
    "Eval 2": ["src/proxy.ts"],
    "Held out 1": [
        "test/integration/profile-form.test.ts",
        "$ACTION_",
        "$ACTION_REF_1",
        "$ACTION_1:0",
        "$ACTION_1:1",
    ],
    "Held out 3": ["possible_match", "good_match", "good_match", "possible_match"],
    "Held out 4": ["band-anchors.test.ts", "BAND_ANCHORS", "BAND_ANCHORS"],
}

#: The same, by claim: the entry's label and the claim's number (AC-26).
CLAIM_WORDS = {
    ("Eval 2", 4): ["refresh_token_reuse_interval"],
    ("Eval 3", 1): ["NODE_ENV"],
    ("Eval 3", 3): ["NODE_ENV", "DEV_SESSION_ENABLED"],
    ("Held out 2", 1): ["possible_match"],
    ("Held out 2", 3): ["good_match"],
    ("Held out 2", 4): ["strong_match", "possible_match"],
    ("Q6", 1): ["profile_skill"],
    ("Q14", 2): ["salary_is_predicted", "salary_min", "salary_max"],
    ("Q21", 3): ["OPENAI_API_KEY"],
    ("Q21", 4): ["usage_cap", "ai_scoring", "ai_check"],
}


def _code_words(text: str) -> list[str]:
    """The code runs the patterns add to a text's explicit code spans."""
    explicit = [run for run in runs(text) if run.code]
    return [run.text for run in runs(text, code_words=True) if run.code and run not in explicit]


def test_the_code_words_of_the_shown_questions_and_claims_are_pinned() -> None:
    """AC-26: 15 words in 5 of the 31 questions, 16 in 10 of the 107 claims."""
    records = _records()
    questions = {label: _code_words(r["question"]) for label, r in records.items()}
    claims = {
        (label, number): _code_words(claim["text"])
        for label, record in records.items()
        for number, claim in enumerate(record["claims"], start=1)
    }

    assert {label: words for label, words in questions.items() if words} == QUESTION_WORDS
    assert {key: words for key, words in claims.items() if words} == CLAIM_WORDS
    assert sum(map(len, QUESTION_WORDS.values())) == 15
    assert sum(map(len, CLAIM_WORDS.values())) == 16
    assert len(claims) == 107


def test_the_shown_missing_notes_hold_no_code_word() -> None:
    """Code words, measured 2026-10-26: the patterns find no word in the 46 missing notes."""
    notes = [note for record in _records().values() for note in record["missing"]]

    assert len(notes) == 46
    assert not any(_code_words(note) for note in notes)


def test_q4_claim_3_shows_both_code_spans_with_no_backtick_left() -> None:
    """AC-1, AC-11, AC-15 on a real record: two code spans, a hyphen inside each."""
    claim = _records()["Q4"]["claims"][2]["text"]
    shown = to_html(runs(claim, code_words=True))

    assert '<code><span class="w">--font-mono</span></code>' in shown
    assert '<code><span class="w">--font-sans</span></code>' in shown
    assert "`" not in shown
