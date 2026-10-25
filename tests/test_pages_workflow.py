"""The Pages workflow that publishes the answer gallery (spec 0010 AC-59 to AC-62).

Read as text, line by line: the project has no YAML parser of its own, and these
checks only need the trigger, two job blocks and one `needs` line.
"""

import re
from pathlib import Path

WORKFLOW = Path(__file__).resolve().parents[1] / ".github" / "workflows" / "pages.yml"

#: The paths the workflow must run on, and only these (AC-61).
TRIGGER_PATHS = (
    "artifacts/asks/**",
    "gallery/**",
    "src/tracepath/**",
    "pyproject.toml",
    "uv.lock",
    "corpus/jobhunt/**",
    ".github/workflows/pages.yml",
)


def _lines() -> list[str]:
    return WORKFLOW.read_text(encoding="utf-8").splitlines()


def _block(lines: list[str], header: str, indent: int) -> list[str]:
    """The lines under `header` (at `indent` spaces) up to the next line as shallow or less."""
    start = lines.index(" " * indent + header)
    block: list[str] = []
    for line in lines[start + 1 :]:
        if line.strip() and len(line) - len(line.lstrip()) <= indent:
            break
        block.append(line)
    return block


def _job(name: str) -> list[str]:
    return _block(_block(_lines(), "jobs:", 0), f"{name}:", 2)


def test_workflow_builds_the_page_on_a_push_to_main() -> None:
    """AC-59."""
    push = _block(_block(_lines(), "on:", 0), "push:", 2)

    assert "    branches: [main]" in push
    assert any("tracepath gallery build --out site" in line for line in _job("build"))


def test_workflow_deploys_the_built_page_to_pages() -> None:
    """AC-60: the build uploads `site`, the deploy job deploys it to github-pages."""
    build = "\n".join(_job("build"))
    deploy = "\n".join(_job("deploy"))

    assert re.search(r"uses: actions/upload-pages-artifact@v\d+\n\s+with:\n\s+path: site", build)
    assert re.search(r"uses: actions/deploy-pages@v\d+", deploy)
    assert "name: github-pages" in deploy


def test_workflow_runs_only_on_the_paths_the_page_is_built_from() -> None:
    """AC-61."""
    paths = _block(_block(_block(_lines(), "on:", 0), "push:", 2), "paths:", 4)

    assert tuple(line.strip().removeprefix("- ").strip('"') for line in paths) == TRIGGER_PATHS


def test_deploy_job_needs_the_build_job() -> None:
    """AC-62: a failed build deploys nothing."""
    assert "    needs: build" in _job("deploy")
