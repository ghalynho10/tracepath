"""Measure the accept to review ratio per unit and per unit kind (spec 0008 AC-7), no API call.

Routing is rebuilt fresh from `artifacts/runs/` with default routing (no code pass, no
narrow hold rule), never read from `artifacts/review-queue.json`. Prints both tables
and writes them to `data/hold-ratio.md`, headed by the commit that last touched
`artifacts/runs/`.

Run from the repository root: uv run python <this file>
"""

import subprocess
from pathlib import Path

from tracepath.hold_ratio import ratio_lines, unit_holds
from tracepath.pipeline import resolve_accepted
from tracepath.rebuild import committed_units, records_for_units

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"
COMMIT = "2e40bcf"
OUT = Path(__file__).resolve().parent / "data" / "hold-ratio.md"


def runs_commit() -> str:
    """The last commit that touched `artifacts/runs/`."""
    return subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", "artifacts/runs"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


def main() -> None:
    """Rebuild, count, print and write the tables."""
    results = committed_units(ROOT, SNAPSHOT)
    corpus = resolve_accepted(results, records_for_units(results, SNAPSHOT, COMMIT))
    lines = (
        "# Accept to review ratio (spec 0008 AC-7)",
        "",
        f"Routing rebuilt from `artifacts/runs/` at {runs_commit()}, default routing, "
        f"{len(results)} units.",
        "",
        *ratio_lines(unit_holds(results, corpus)),
    )
    text = "\n".join(lines) + "\n"
    print(text, end="")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(text)


if __name__ == "__main__":
    main()
