"""Measure the re check's 18 call manifest, free, with the token counting endpoint.

Spec 0003, AC-30, step 26: the re check's go ahead figure is computed from the
measured token count of the `0003.1` prompt and the measured per call cost from
experiment 0005's runs, never estimated. This counts input tokens only (the free
endpoint); the per call dollar cost is computed from `report.py`'s own committed
after and before cost figures, not measured again here.

Run from the repository root: uv run python <this file>
"""

import json
from pathlib import Path

import anthropic

from tracepath.config import load_anthropic_settings
from tracepath.extract.client import PROMPT_VERSION, SYSTEM_PROMPT, system_blocks, user_prompt
from tracepath.extract.schema import ExtractionOutput
from tracepath.extract.units import Unit, split_units

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"
HERE = Path(__file__).resolve().parent

#: The re check's three fresh held out units (AC-30), none in group A, B, C, any
#: worked example, or the type coverage set.
UNITS = [
    ("specs/0014-", "Requirements"),
    ("specs/0015-", "Feature design"),
    ("scope/scope.md", "33. Band anchor review · done"),
]

#: The commit the re check's before calls run under (AC-30), same as group A's.
OLD_PROMPT_COMMIT = "972907b"


def find(prefix: str, section: str) -> Unit:
    """The one unit a manifest key names."""
    if prefix.endswith(".md"):
        path = SNAPSHOT / prefix
    else:
        path = next(SNAPSHOT.glob(f"{prefix}*/index.md"))
    units = split_units(str(path.relative_to(SNAPSHOT)), path.read_text())
    return next(u for u in units if u.section == section)


def old_system_prompt() -> str:
    """The `0002.3` system prompt, read from git, matching `measure_prefix.py`."""
    import ast
    import re
    import subprocess

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


def count(client: anthropic.Anthropic, model: str, system: object, text: str) -> int:
    """Input tokens for one extraction call, schema included, as `extract_once` sends it."""
    return client.messages.count_tokens(
        model=model,
        system=system,  # type: ignore[arg-type]
        messages=[{"role": "user", "content": text}],
        output_format=ExtractionOutput,
    ).input_tokens


def main() -> None:
    """Count the `0003.1` prefix and every re check unit, under both prompts."""
    settings = load_anthropic_settings()
    client = anthropic.Anthropic(api_key=settings.api_key)
    old = old_system_prompt()

    # The cached prefix is the system block alone (spec 0003, AC-19). A tiny probe
    # counted with the real block and with a one character block differs by exactly
    # that block, since the schema and the message, uncached, cancel out.
    probe = "Record: x\n---\nx\n---"
    new_total = count(client, settings.model, system_blocks(), probe)
    bare = count(client, settings.model, [{"type": "text", "text": "x"}], probe)
    prefix = new_total - bare

    rows: list[dict[str, object]] = []
    for prefix_path, section in UNITS:
        unit = find(prefix_path, section)
        after_total = count(client, settings.model, system_blocks(), user_prompt(unit))
        before_total = count(client, settings.model, old, user_prompt(unit))
        rows.append(
            {
                "unit": f"{unit.record_id} {unit.section}",
                "unit_kind": str(unit.kind),
                "chars": len(unit.text),
                "after_input_tokens_per_call": after_total,
                "after_uncached_tokens_per_call": after_total - prefix,
                "before_input_tokens_per_call": before_total,
            }
        )

    report = {
        "prompt_version": PROMPT_VERSION,
        "system_prompt_chars": len(SYSTEM_PROMPT),
        "prefix_tokens": prefix,
        "rows": rows,
    }
    (HERE / "data").mkdir(exist_ok=True)
    (HERE / "data" / "prefix-count.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
