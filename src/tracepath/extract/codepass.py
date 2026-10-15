"""The code pass of spec 0007: which acceptance criteria code decides from the text.

Pure. Code decides no span, no type and no link here. It decides only which ids are
settled enough that a `multi_condition_split` flag alone should not hold them: a
bullet code itself parsed out of a `## Requirements` section, whose every run produced
exactly one entity carrying that id, typed `AcceptanceCriterion`, with the canonical id
the bullet names. `route_runs()` then reads the flags (spec 0007 AC-12 to AC-14).

The pass is off by default (`--code-pass`), because runs agreeing shows they repeat,
not that they are right. Spec 0007's measure decides whether it is turned on.
"""

import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from tracepath.extract.ids import IdentifiedOutput
from tracepath.extract.schema import EntityType, IdSource, KnownTrapFlag
from tracepath.extract.units import Unit

#: What `accepted_by` reads on an entity the pass released (spec 0007 AC-16).
CODE_PASS = "code_pass"

#: The one section the pass parses (AC-9).
REQUIREMENTS_SECTION = "Requirements"

#: The flags that alone no longer hold a code decided entity (AC-12). Any other flag
#: still holds it.
RELEASED_FLAGS = frozenset({KnownTrapFlag.MULTI_CONDITION_SPLIT})

#: A top level bullet that opens like a criterion, parsed or not (AC-17's last count).
_CRITERION_LIKE = re.compile(r"^- \*\*AC-", re.MULTILINE)

#: A parsed bullet's opening: `- **AC-N**:`, N digits and an optional lower case
#: letter, at the start of a line (AC-9). Group 2 is the text after the colon.
_PARSED = re.compile(r"^- \*\*(AC-\d+[a-z]?)\*\*:(.*)$", re.MULTILINE)


@dataclass(frozen=True)
class BulletParse:
    """What AC-9's parse found in one unit's text.

    `parsed` holds every parsed bullet's id in text order, a repeated id once per
    bullet. `struck` counts bullets whose text after the colon opens with `~~`, left to
    the model. `unparsed` counts the other top level `- **AC-` bullets the parse refused.
    """

    parsed: tuple[str, ...]
    struck: int
    unparsed: int

    @property
    def repeated(self) -> tuple[str, ...]:
        """Every id two or more parsed bullets carry, in text order (AC-11)."""
        counted = Counter(self.parsed)
        return tuple(i for i in dict.fromkeys(self.parsed) if counted[i] > 1)


def parse_bullets(unit: Unit) -> BulletParse:
    """The criterion bullets of a `## Requirements` unit; any other unit parses none (AC-9)."""
    if unit.section != REQUIREMENTS_SECTION:
        return BulletParse(parsed=(), struck=0, unparsed=0)
    parsed: list[str] = []
    struck = 0
    for match in _PARSED.finditer(unit.text):
        if match.group(2).lstrip().startswith("~~"):
            struck += 1
        else:
            parsed.append(match.group(1))
    unparsed = len(_CRITERION_LIKE.findall(unit.text)) - len(parsed) - struck
    return BulletParse(parsed=tuple(parsed), struck=struck, unparsed=unparsed)


def _settles(output: IdentifiedOutput, verbatim: str, canonical_id: str) -> bool:
    """Whether one run holds exactly one entity carrying `verbatim`, typed and identified right."""
    claimants = [
        entity
        for entity in output.entities
        if entity.entity.id_source is IdSource.VERBATIM and entity.entity.id == verbatim
    ]
    return (
        len(claimants) == 1
        and claimants[0].entity.type is EntityType.ACCEPTANCE_CRITERION
        and claimants[0].canonical_id == canonical_id
    )


def code_decided_ids(unit: Unit, identified_outputs: Sequence[IdentifiedOutput]) -> frozenset[str]:
    """The canonical ids code decides in one unit, from its text and its runs (AC-9 to AC-11).

    A parsed bullet's id is decided only when every run agrees on it (AC-10). An id two
    parsed bullets carry is never decided (AC-11), whatever the runs say.
    """
    if not identified_outputs:
        return frozenset()
    parse = parse_bullets(unit)
    repeated = set(parse.repeated)
    return frozenset(
        f"{unit.record_id}/{verbatim}"
        for verbatim in dict.fromkeys(parse.parsed)
        if verbatim not in repeated
        and all(
            _settles(output, verbatim, f"{unit.record_id}/{verbatim}")
            for output in identified_outputs
        )
    )
