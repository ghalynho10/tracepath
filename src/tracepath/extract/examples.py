"""The worked examples, assembled into the few shot block of the extraction prompt.

Only each file's Input and Output reach the model (spec 0003, AC-9). Reasoning notes,
validation caveats and other commentary are written for the people who author the
examples, and carry project history the model has no use for. The files are read in
filename order, so the assembled block is byte identical from one call to the next and
the prompt cache prefix actually hits.
"""

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

#: Where the worked examples live, tracked in git beside the code that reads them.
EXAMPLES_DIR = Path(__file__).resolve().parents[3] / "examples"

#: The example's input: the one `text` fence under `## Input`.
INPUT_BLOCK = re.compile(r"^## Input\n.*?^```text\n(.*?)^```$", re.MULTILINE | re.DOTALL)

#: The example's output: the one `json` fence under `## Output`.
OUTPUT_BLOCK = re.compile(r"^## Output\n.*?^```json\n(.*?)^```$", re.MULTILINE | re.DOTALL)


class ExampleError(Exception):
    """A worked example cannot be read into the prompt as it stands."""


@dataclass(frozen=True)
class WorkedExample:
    """One worked example, reduced to the two parts the model is shown."""

    name: str
    input: str
    output: str


def parse_example(name: str, text: str) -> WorkedExample:
    """Read one example file's Input and Output fences.

    Raises:
        ExampleError: the file has no Input or Output fence, or its Output is not JSON.
    """
    found_input = INPUT_BLOCK.search(text)
    found_output = OUTPUT_BLOCK.search(text)
    if found_input is None or found_output is None:
        missing = "Input" if found_input is None else "Output"
        raise ExampleError(f"{name}: no `## {missing}` section with a fenced block under it")
    output = found_output.group(1).strip()
    try:
        json.loads(output)
    except json.JSONDecodeError as exc:
        raise ExampleError(f"{name}: the Output block is not valid JSON ({exc})") from exc
    return WorkedExample(name=name, input=found_input.group(1).strip(), output=output)


def read_examples(directory: Path) -> tuple[WorkedExample, ...]:
    """Every worked example in a directory, in filename order.

    Raises:
        ExampleError: the directory holds no example, or one of them cannot be read.
    """
    paths = sorted(directory.glob("*.md"))
    if not paths:
        raise ExampleError(f"no worked examples found in {directory}")
    examples: list[WorkedExample] = []
    for path in paths:
        try:
            text = path.read_text()
        except OSError as exc:
            raise ExampleError(f"{path.stem}: the example file cannot be read ({exc})") from exc
        examples.append(parse_example(path.stem, text))
    return tuple(examples)


def few_shot_block(examples: Sequence[WorkedExample], notes: Mapping[str, str]) -> str:
    """The examples as the prompt shows them, each with its note when it has one.

    Raises:
        ExampleError: a note names an example that is not among `examples`, which would
            otherwise drop the note silently.
    """
    names = {example.name for example in examples}
    stray = sorted(set(notes) - names)
    if stray:
        raise ExampleError(f"a note names no worked example: {', '.join(stray)}")
    parts: list[str] = []
    for example in examples:
        note = notes.get(example.name)
        lines = [f'<example name="{example.name}">']
        if note is not None:
            lines.append(f"<note>{note}</note>")
        lines += ["<input>", example.input, "</input>", "<output>", example.output, "</output>"]
        lines.append("</example>")
        parts.append("\n".join(lines))
    return "\n\n".join(parts)
