"""The answer's shape, its prompt, and the checks code makes on it (spec 0009 AC-15 to AC-20).

Pure: each reply is hand written, and the pack is built from `tests/ask_fixture.py`.
The pack for "landing" sends 9101, 9101/AC-1 to AC-4 (AC-3 struck, replaced by AC-4;
AC-2 held), the held Unresolved node and 9102/AC-1, with four links among them.
"""

import json

import pytest
from pydantic import ValidationError

from tests import ask_fixture as fx
from tracepath.ask.answer import (
    PROMPT_VERSION,
    Answer,
    Claim,
    answer_lines,
    check_claims,
    pack_message,
    system_prompt,
)
from tracepath.ask.retrieve import Pack, build_pack
from tracepath.extract.metered import ask_output_format


@pytest.fixture
def pack() -> Pack:
    return build_pack(fx.graph(), "landing")


def claim(text: str, *cites: str, basis: str = "text") -> Claim:
    return Claim.model_validate({"text": text, "cites": cites, "basis": basis})


def printed(
    pack: Pack, *claims: Claim, verdict: str = "answered", missing: tuple[str, ...] = ()
) -> tuple[str, ...]:
    answer = Answer.model_validate({"verdict": verdict, "claims": claims, "missing": missing})
    return answer_lines(answer, check_claims(answer, pack))


def test_ac_15_the_reply_is_a_verdict_claims_with_cites_and_basis_and_a_missing_list() -> None:
    """covers: AC-15."""
    reply = (
        '{"verdict": "partly", "claims": [{"text": "It reads once.", "cites": ["9101/AC-1"],'
        ' "basis": "text"}], "missing": ["why one row"]}'
    )

    answer = Answer.model_validate_json(reply)

    assert answer.verdict == "partly"
    assert answer.claims == (claim("It reads once.", "9101/AC-1"),)
    assert answer.missing == ("why one row",)


@pytest.mark.parametrize(
    "reply",
    [
        '{"verdict": "maybe", "claims": [], "missing": []}',
        '{"verdict": "answered", "claims": [{"text": "x", "cites": [], "basis": "guess"}], '
        '"missing": []}',
        '{"verdict": "answered", "claims": [], "missing": [], "prose": "extra"}',
    ],
)
def test_ac_15_a_reply_outside_the_shape_does_not_validate(reply: str) -> None:
    """covers: AC-15 (a bad verdict, a bad basis, an extra field)."""
    with pytest.raises(ValidationError):
        Answer.model_validate_json(reply)


def test_ac_15_note_no_documented_link_is_a_fourth_verdict_and_prints_as_given(
    pack: Pack,
) -> None:
    """covers: AC-15 note of 2026-10-19 (the absence verdict, prompt `ask-2`)."""
    lines = printed(pack, claim("It reads once.", "9101/AC-1"), verdict="no_documented_link")

    assert lines[0] == "Answer (verdict: no_documented_link):"


def test_ac_15_note_the_output_schema_offers_the_absence_verdict() -> None:
    """covers: AC-15 note of 2026-10-19 (the model can only send a verdict the schema lists)."""
    schema = json.dumps(ask_output_format()["schema"])

    assert "no_documented_link" in schema
    assert "not_supported" in schema


def test_ac_15_note_the_prompt_says_when_the_absence_verdict_applies() -> None:
    """covers: AC-15 note of 2026-10-19, with the prompt version bumped to `ask-2`."""
    prompt = " ".join(system_prompt().split())

    assert PROMPT_VERSION == "ask-2"
    assert "Use `no_documented_link` instead when the question asks how two" in prompt
    assert "no item's text and no listed link states a connection between them" in prompt
    assert "Use `not_supported` when the items for one of the things are missing" in prompt


def test_ac_15b_and_ac_20_the_answer_prints_verdict_numbered_claims_then_missing(
    pack: Pack,
) -> None:
    """covers: AC-15b, AC-20 (verdict above, `Missing:` below)."""
    lines = printed(
        pack,
        claim("The rule reads the row once.", "9101/AC-1"),
        claim("A dedicated query amends it.", "9101/AC-1", "9101/AC-2", basis="link"),
        verdict="partly",
        missing=("why a second query", "who asked"),
    )

    assert lines == (
        "Answer (verdict: partly):",
        "  1. The rule reads the row once. [9101/AC-1] read from text",
        "  2. A dedicated query amends it. [9101/AC-1] [9101/AC-2 held] link",
        "Missing: why a second query; who asked",
    )


def test_ac_15b_an_empty_missing_list_prints_no_missing_line(pack: Pack) -> None:
    """covers: AC-15b."""
    assert not any(line.startswith("Missing") for line in printed(pack, claim("x", "9101/AC-1")))


def test_ac_16_a_cited_id_that_was_not_sent_is_rejected(pack: Pack) -> None:
    """covers: AC-16."""
    (line,) = printed(pack, claim("It says so.", "9101/AC-1", "0001/AC-9"))[1:]

    assert (
        line
        == "  1. It says so. [9101/AC-1] [0001/AC-9] CITATION REJECTED: 0001/AC-9 read from text"
    )


def test_ac_16b_a_claim_citing_nothing_is_marked_uncited(pack: Pack) -> None:
    """covers: AC-16b."""
    (line,) = printed(pack, claim("Nothing backs this."))[1:]

    assert line == "  1. Nothing backs this. UNCITED read from text"


def test_ac_17_a_link_claim_holds_when_a_sent_link_joins_two_cited_ids_either_way(
    pack: Pack,
) -> None:
    """covers: AC-17. The AMENDED_BY link runs 9101/AC-1 to 9101/AC-2; cited the other way."""
    (line,) = printed(pack, claim("Amended.", "9101/AC-2", "9101/AC-1", basis="link"))[1:]

    assert line.endswith(" link")
    assert "INFERRED" not in line


def test_ac_17_a_link_claim_with_no_link_between_its_ids_prints_inferred(pack: Pack) -> None:
    """covers: AC-17. No link joins 9101/AC-1 and 9101/AC-4."""
    (line,) = printed(pack, claim("Linked.", "9101/AC-1", "9101/AC-4", basis="link"))[1:]

    assert line == "  1. Linked. [9101/AC-1] [9101/AC-4] INFERRED"


def test_ac_17_a_link_claim_citing_one_id_prints_inferred(pack: Pack) -> None:
    """covers: AC-17."""
    (line,) = printed(pack, claim("Linked.", "9101/AC-1", basis="link"))[1:]

    assert line.endswith("INFERRED")


def test_ac_17_note_a_link_claim_with_one_cited_id_left_unlinked_prints_inferred(
    pack: Pack,
) -> None:
    """covers: AC-17 note of 2026-10-19 (review finding 2). AC-1 and AC-2 are linked;
    no sent link joins 9101/AC-4 to either.
    """
    (line,) = printed(pack, claim("Linked.", "9101/AC-1", "9101/AC-2", "9101/AC-4", basis="link"))[
        1:
    ]

    assert line == "  1. Linked. [9101/AC-1] [9101/AC-2 held] [9101/AC-4] INFERRED"


def test_ac_17_note_a_link_claim_whose_every_cited_id_is_linked_to_another_passes(
    pack: Pack,
) -> None:
    """covers: AC-17 note of 2026-10-19. 9101/AC-1 to 9101/AC-2 to 9102/AC-1, a chain."""
    (line,) = printed(pack, claim("A chain.", "9101/AC-1", "9101/AC-2", "9102/AC-1", basis="link"))[
        1:
    ]

    assert line.endswith(" link")
    assert "INFERRED" not in line


def test_ac_17_note_a_link_claim_citing_an_id_not_sent_prints_inferred(pack: Pack) -> None:
    """covers: AC-17 note of 2026-10-19. A rejected id is joined by no sent link."""
    (line,) = printed(pack, claim("Linked.", "9101/AC-1", "9101/AC-2", "9999/AC-1", basis="link"))[
        1:
    ]

    assert line.endswith("INFERRED CITATION REJECTED: 9999/AC-1")


def test_ac_17b_an_inferred_claim_prints_inferred_and_a_text_claim_read_from_text(
    pack: Pack,
) -> None:
    """covers: AC-17b."""
    lines = printed(
        pack,
        claim("Guessed.", "9101/AC-1", "9102/AC-1", basis="inferred"),
        claim("Read.", "9101/AC-1"),
    )

    assert lines[1:] == (
        "  1. Guessed. [9101/AC-1] [9102/AC-1] INFERRED",
        "  2. Read. [9101/AC-1] read from text",
    )


def test_ac_17b_note_a_claim_whose_every_citation_is_rejected_prints_unsupported(
    pack: Pack,
) -> None:
    """covers: AC-17b note of 2026-10-19 (review nit 1), in place of its basis."""
    lines = printed(
        pack,
        claim("Read.", "9999/AC-1", "9999/AC-2"),
        claim("Linked.", "9999/AC-1", basis="link"),
    )

    assert lines[1:] == (
        "  1. Read. [9999/AC-1] [9999/AC-2] CITATION REJECTED: 9999/AC-1, 9999/AC-2 unsupported",
        "  2. Linked. [9999/AC-1] INFERRED CITATION REJECTED: 9999/AC-1 unsupported",
    )


def test_ac_20_note_the_verdict_line_counts_the_claims_that_failed_a_check(pack: Pack) -> None:
    """covers: AC-20 note of 2026-10-19 (review finding 3): a rejected id, no id, and a
    `link` not found each fail; a passing claim and the model's own `inferred` do not.
    """
    lines = printed(
        pack,
        claim("Read.", "9101/AC-1"),
        claim("Guessed.", "9101/AC-1", basis="inferred"),
        claim("Elsewhere.", "9999/AC-1"),
        claim("Nothing."),
        claim("Linked.", "9101/AC-1", "9101/AC-4", basis="link"),
        verdict="answered",
    )

    assert lines[0] == "Answer (verdict: answered; 3 of 5 claims failed a check):"


def test_ac_20_note_with_no_failed_check_the_verdict_line_is_unchanged(pack: Pack) -> None:
    """covers: AC-20 note of 2026-10-19."""
    lines = printed(
        pack, claim("Read.", "9101/AC-1"), claim("Guessed.", "9101/AC-1", basis="inferred")
    )

    assert lines[0] == "Answer (verdict: answered):"


def test_ac_18_a_claim_citing_a_history_item_prints_history_set_by_code(pack: Pack) -> None:
    """covers: AC-18, AC-14b. The claim's text says nothing of history; the replacement passes."""
    (line,) = printed(
        pack, claim("The check reads every row.", "9101/AC-3", "9101/AC-4", basis="link")
    )[1:]

    assert line == "  1. The check reads every row. [9101/AC-3] [9101/AC-4] HISTORY link"


def test_ac_18b_the_system_prompt_tells_the_model_to_say_history_and_what_replaced_it() -> None:
    """covers: AC-18b."""
    prompt = " ".join(system_prompt().split())

    assert "When a claim uses a HISTORY item, say so in the claim itself" in prompt
    assert "when the item says what replaced it, name that item in the claim" in prompt


def test_ac_19_a_held_cited_id_prints_held_beside_it(pack: Pack) -> None:
    """covers: AC-19."""
    (line,) = printed(pack, claim("Held.", "9101/AC-2", "unresolved:9101:feature-77"))[1:]

    assert "[9101/AC-2 held] [unresolved:9101:feature-77 held]" in line


def test_ac_20_marks_print_history_inferred_citation_rejected_in_that_order(pack: Pack) -> None:
    """covers: AC-20."""
    (line,) = printed(pack, claim("Old.", "9101/AC-3", "9999/AC-1", basis="link"))[1:]

    assert line.endswith("HISTORY INFERRED CITATION REJECTED: 9999/AC-1")


def test_ac_20_inferred_prints_before_uncited(pack: Pack) -> None:
    """covers: AC-20."""
    (line,) = printed(pack, claim("Nothing.", basis="link"))[1:]

    assert line.endswith("INFERRED UNCITED")


def test_the_pack_message_marks_held_and_history_and_names_the_replacement(pack: Pack) -> None:
    """Security model: held items are labelled HELD to the model; AC-14b's replacement named."""
    message = pack_message(pack)

    assert message.startswith("Question: landing\n\nItems:\n\n[9101] record, accepted")
    assert (
        f"[9101/AC-3] AcceptanceCriterion, accepted, HISTORY (struck through, replaced by "
        f"9101/AC-4) from {fx.FILE}\nThe old landing check read every row." in message
    )
    assert f"[9101/AC-2] AcceptanceCriterion, HELD from {fx.FILE}" in message
    assert '9101/AC-3 superseded-by 9101/AC-4, HELD: "replaced"' in message
    assert "9102/AC-2" not in message
