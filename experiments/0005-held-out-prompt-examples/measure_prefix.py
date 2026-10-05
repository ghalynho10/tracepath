"""Measure the `0003.0` prompt's input tokens with the token counting endpoint (AC-20).

Token counting is free (Anthropic's token counting page, "Pricing and rate limits"),
so this spends nothing. It counts every call the run manifest will make, schema
included, exactly as `extract_once` sends it, and splits each call's input into the
cached system prompt and the uncached rest, because the two bill at different rates.

Calibration first: the old `0002.3` prompt, read from the commit named below, counted
over `0001 ## Binding rules`, is compared against the 7,254 input tokens experiment 0004
actually billed for that same request. A count that does not land near it would mean
this method misses part of the request, and no estimate built on it should be trusted.

Run from the repository root: uv run python <this file>
"""

import ast
import json
import re
import subprocess
from pathlib import Path

import anthropic
from anthropic.types import TextBlockParam

from tracepath.config import load_anthropic_settings
from tracepath.extract.client import PROMPT_VERSION, SYSTEM_PROMPT, system_blocks, user_prompt
from tracepath.extract.schema import ExtractionOutput
from tracepath.extract.units import Unit, split_units

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"
HERE = Path(__file__).resolve().parent

#: The last commit whose `client.py` still holds the `0002.3` prompt.
OLD_PROMPT_COMMIT = "972907b"

#: What experiment 0004 billed for one `0001 ## Binding rules` call under `0002.3`.
MEASURED_OLD_INPUT = 7254

#: Every unit the manifest runs under `0003.0`, and how many calls each makes. The
#: held out befores are `0002.3` calls (uncached) and are counted with the old prompt.
AFTER = [
    ("specs/0021-", "Requirements", 3),
    ("specs/0013-", "Feature design", 3),
    ("scope/scope.md", "9. Profile entry · done", 3),
    # The type coverage set: the eight committed units, three calls each (AC-18).
    ("specs/0008-", "Preamble", 3),
    ("specs/0012-", "Requirements", 3),
    ("specs/0012-", "Follow-up", 3),
    ("specs/0012-", "Consequences", 3),
    ("specs/0012-", "Build plan", 3),
    ("scope/scope.md", "21. Terms & privacy notices · done · Alpha", 3),
    ("specs/0021-", "Requirements", 3),  # the coverage set's own three, apart from group A
    ("specs/0006-", "Feature design", 3),
]
BEFORE = [
    ("specs/0013-", "Feature design", 3),
    ("scope/scope.md", "9. Profile entry · done", 3),
]


def find(prefix: str, section: str) -> Unit:
    """The one unit a manifest key names."""
    if prefix.endswith(".md"):
        path = SNAPSHOT / prefix
    else:
        path = next(SNAPSHOT.glob(f"{prefix}*/index.md"))
    units = split_units(str(path.relative_to(SNAPSHOT)), path.read_text())
    return next(u for u in units if u.section == section)


def old_system_prompt() -> str:
    """The `0002.3` system prompt, read from git rather than kept as a second copy."""
    source = subprocess.run(
        ["git", "show", f"{OLD_PROMPT_COMMIT}:src/tracepath/extract/client.py"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    found = re.search(r'^SYSTEM_PROMPT = ("""\\\n.*?\n""")$', source, re.MULTILINE | re.DOTALL)
    if found is None:
        raise SystemExit(f"no SYSTEM_PROMPT literal at {OLD_PROMPT_COMMIT}")
    value = ast.literal_eval(found.group(1))
    assert isinstance(value, str)
    return value


def count(
    client: anthropic.Anthropic, model: str, system: str | list[TextBlockParam], text: str
) -> int:
    """Input tokens for one extraction call, schema included, as `extract_once` sends it."""
    return client.messages.count_tokens(
        model=model,
        system=system,
        messages=[{"role": "user", "content": text}],
        output_format=ExtractionOutput,
    ).input_tokens


def main() -> None:
    """Calibrate, then count the prefix and every manifest unit, and write the table."""
    settings = load_anthropic_settings()
    client = anthropic.Anthropic(api_key=settings.api_key)
    old = old_system_prompt()

    binding_rules = user_prompt(find("specs/0001-", "Binding rules"))
    calibration = count(client, settings.model, old, binding_rules)
    print(f"calibration: counted {calibration} against {MEASURED_OLD_INPUT} billed")

    # The cached prefix is the system block alone. The same tiny request counted with
    # the real block and with a one character block differs by exactly that block, so
    # the schema and the message, which are not cached, cancel out of the difference.
    probe = "Record: x\n---\nx\n---"
    new_total = count(client, settings.model, system_blocks(), probe)
    bare = count(client, settings.model, [{"type": "text", "text": "x"}], probe)
    prefix = new_total - bare

    rows: list[dict[str, object]] = []
    for label, table, system in (("after", AFTER, system_blocks()), ("before", BEFORE, old)):
        for prefix_path, section, calls in table:
            unit = find(prefix_path, section)
            total = count(client, settings.model, system, user_prompt(unit))
            rows.append(
                {
                    "group": label,
                    "unit": f"{unit.record_id} {unit.section}",
                    "chars": len(unit.text),
                    "calls": calls,
                    "input_tokens_per_call": total,
                    "uncached_tokens_per_call": total - prefix if label == "after" else total,
                }
            )

    report = {
        "prompt_version": PROMPT_VERSION,
        "system_prompt_chars": len(SYSTEM_PROMPT),
        "calibration_counted": calibration,
        "calibration_billed": MEASURED_OLD_INPUT,
        "prefix_tokens": prefix,
        "rows": rows,
    }
    (HERE / "data").mkdir(exist_ok=True)
    (HERE / "data" / "prefix-count.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
