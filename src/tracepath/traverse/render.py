"""A walked chain as plain lines, each step citing its record (spec 0004 AC-27 to AC-30).

Pure: the same chain always renders the same lines, with no timestamp or other value
that changes between runs (key invariant 6). The struck flag is printed as stored, with
no current or history label.
"""

from collections import Counter

from tracepath.traverse.graph_slice import Link, Node, NodeKind
from tracepath.traverse.walk import Chain, Direction, Step, Stop

#: How much of an entity's text a step shows. The full text is one hop away in its file,
#: at the cited line.
TEXT_LIMIT = 200

#: What a prompt version reads as when a node or link carries none.
NO_VERSION = "none recorded"

INDENT = "       "


def _shown(text: str | None) -> str:
    """An entity's text on one line, cut at `TEXT_LIMIT` characters."""
    flat = " ".join((text or "").split())
    return flat if len(flat) <= TEXT_LIMIT else flat[: TEXT_LIMIT - 1] + "…"


def _value(value: object) -> str:
    return "not stored" if value is None else str(value)


def _struck(node: Node) -> str:
    if node.struck is None:
        return "not stored"
    return "true" if node.struck else "false"


def _link_lines(step: Step, via: Link) -> list[str]:
    """The link a step was reached by: its stored direction, then its own citation."""
    seen_from = "outgoing from" if step.direction is Direction.OUTGOING else "incoming to"
    citation = (
        f"{_value(via.file)} · {_value(via.section)} · line {_value(via.line)} · "
        f"commit {_value(via.commit)} · prompt {via.prompt_version or NO_VERSION}"
    )
    if via.phrase:
        citation += f' · "{" ".join(via.phrase.split())}"'
    return [
        f"{INDENT}link  {via.source} -[{via.type}]-> {via.target} ({seen_from} {step.parent})",
        f"{INDENT}      {citation}",
    ]


def _node_lines(node: Node) -> list[str]:
    """What a step's own node prints, by kind (AC-28a to AC-28c, AC-29)."""
    if node.kind is NodeKind.RECORD:
        return [
            f'{INDENT}"{node.title or ""}"',
            f"{INDENT}{_value(node.path)} · commit {_value(node.commit)} · code, no model",
        ]
    if node.kind is NodeKind.UNRESOLVED:
        return [
            f'{INDENT}mention "{node.mention or ""}"',
            f"{INDENT}{_value(node.file)} · {_value(node.section)} · line {_value(node.line)} · "
            "no commit, no model",
        ]
    return [
        f'{INDENT}"{_shown(node.text)}"',
        f"{INDENT}{_value(node.file)} · {_value(node.section)} · "
        f"file line {_value(node.file_line)} · commit {_value(node.commit)} · "
        f"prompt {node.prompt_version or NO_VERSION}",
    ]


def _heading(step: Step) -> str:
    node = step.node
    if node.kind is NodeKind.ENTITY:
        kind = f"{node.type or 'Entity'}  struck: {_struck(node)}"
    else:
        kind = str(node.kind)
    return f"hop {step.hop}  {node.canonical_id}  {kind}"


def _stop_line(step: Step) -> list[str]:
    if step.stop is None:
        return []
    if step.stop is Stop.DEPTH_LIMIT:
        noun = "link" if step.unfollowed == 1 else "links"
        return [f"{INDENT}stopped: depth limit, {step.unfollowed} typed {noun} not followed"]
    return [f"{INDENT}stopped: {step.stop}"]


def model_made_versions(chain: Chain) -> Counter[str]:
    """The prompt version of every model made step, each counted once (AC-30).

    A model made step is an entity, or the link a step was reached by. Records and
    Unresolved nodes are code's, and carry none.
    """
    versions: Counter[str] = Counter()
    for step in chain.steps:
        if step.node.kind is NodeKind.ENTITY:
            versions[step.node.prompt_version or NO_VERSION] += 1
        if step.via is not None:
            versions[step.via.prompt_version or NO_VERSION] += 1
    return versions


def _versions_line(chain: Chain) -> str:
    versions = model_made_versions(chain)
    if not versions:
        return "Prompt versions: no model made step in this chain."
    if len(versions) == 1:
        [(version, count)] = versions.items()
        return f"Prompt versions: all {count} model made steps share prompt {version}."
    counts = ", ".join(f"{v}: {n}" for v, n in sorted(versions.items()))
    return f"Prompt versions: model made steps do not share one prompt version ({counts})."


def render_chain(chain: Chain) -> tuple[str, ...]:
    """Every line `trace` prints for one chain, in order."""
    count = len(chain.steps)
    lines = [
        f"Chain from {chain.start}: {count} step{'' if count == 1 else 's'}, "
        f"at most {chain.max_hops} hops, typed links both ways, PART_OF not followed.",
    ]
    for step in chain.steps:
        lines.append("")
        lines.append(_heading(step))
        if step.via is not None:
            lines.extend(_link_lines(step, step.via))
        lines.extend(_node_lines(step.node))
        lines.extend(_stop_line(step))
    lines.append("")
    lines.append(_versions_line(chain))
    return tuple(lines)
