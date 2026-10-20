"""Build experiment 0017's answers.json and its side by side answers from the kept traces.

Run from the tracepath root, with no API call:

    python3 -I experiments/0017-decision-memory-comparison/report.py

Reads each decision-memory `--debug` trace (`data/*-trace.txt.gz`) and each question's
prompt `ask-1` record under `artifacts/asks/`, writes `data/answers.json`, and prints the
side by side markdown that README.md carries. A query's cost is its Providers rows priced
at decision-memory's own documented rates (its experiments 0007 and 0001); the step to
model mapping is from its `openai_generation.py`.
"""

import gzip
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
DATA = HERE / "data"

# USD per million tokens, (input, output). gpt-4o: facets, answer, coverage.
# gpt-4o-mini: decompose, entailment. text-embedding-3-small: embedding.
RATES = {
    "facets": (2.50, 10.00),
    "answer": (2.50, 10.00),
    "coverage": (2.50, 10.00),
    "decompose": (0.15, 0.60),
    "entailment": (0.15, 0.60),
    "embedding": (0.02, 0.0),
}
PROVIDER_ROW = re.compile(r"^(\w+) attempt=\d+ .*?prompt_tokens=(\d+) completion_tokens=(\d+)")
SECTIONS = frozenset(
    {
        "Freshness",
        "Filter",
        "Lexical",
        "Semantic",
        "Fusion",
        "Diversity",
        "Settings",
        "Facets",
        "Draft",
        "Verification",
        "Sub claims",
        "Providers",
        "Citations",
        "Result",
    }
)
EVAL_FILES = {
    "eval": "eval/linked-records-research.json",
    "held-out": "eval/held-out.json",
}
# Each question's prompt ask-1 record. Eval question 1 was asked as free text before
# `--eval` existed; its wording is identical to the eval file's, checked below.
ASK1_RECORDS = {
    ("eval", 1): "2026-10-19T21-08-46Z-why-does-the-landing-rule.json",
    ("eval", 2): "2026-10-19T21-57-44Z-eval-linked-records-research-q2.json",
    ("eval", 3): "2026-10-19T21-57-56Z-eval-linked-records-research-q3.json",
    ("eval", 4): "2026-10-19T21-58-07Z-eval-linked-records-research-q4.json",
    ("eval", 5): "2026-10-19T21-58-18Z-eval-linked-records-research-q5.json",
    ("held-out", 1): "2026-10-19T22-17-23Z-eval-held-out-q1.json",
    ("held-out", 2): "2026-10-19T22-17-37Z-eval-held-out-q2.json",
    ("held-out", 3): "2026-10-19T22-17-49Z-eval-held-out-q3.json",
    ("held-out", 4): "2026-10-19T22-18-05Z-eval-held-out-q4.json",
}


def split_sections(text: str) -> dict[str, list[str]]:
    """Split a trace into its sections, each line stripped; `stdout` is what precedes them."""
    out: dict[str, list[str]] = {"stdout": []}
    current = "stdout"
    for line in text.split("\n"):
        if line in SECTIONS:
            current = line
            out[current] = []
        elif current == "stdout":
            out[current].append(line)
        elif line.strip():
            out[current].append(line.strip())
    return out


def decision_memory_side(kind: str, number: int) -> dict[str, object]:
    """One question's decision-memory answer, cost and verification outcome, from its trace."""
    trace = DATA / f"{kind}-q{number}-trace.txt.gz"
    sec = split_sections(gzip.decompress(trace.read_bytes()).decode())
    cost = 0.0
    calls: dict[str, int] = {}
    tokens = {"prompt": 0, "completion": 0}
    for line in sec["Providers"]:
        match = PROVIDER_ROW.match(line)
        if match is None:
            continue
        step, prompt, completion = match.group(1), int(match.group(2)), int(match.group(3))
        rate_in, rate_out = RATES[step]
        cost += prompt * rate_in / 1e6 + completion * rate_out / 1e6
        calls[step] = calls.get(step, 0) + 1
        tokens["prompt"] += prompt
        tokens["completion"] += completion
    result = {k.strip(): v.strip() for k, _, v in (line.partition(":") for line in sec["Result"])}
    # Filter rows: chunk id, record id, status, tags, value path, state, reasons.
    filter_rows = {parts[0]: parts for parts in (line.split() for line in sec["Filter"])}
    accepted_ids = next(
        line.split(": ", 1)[1].split(",")
        for line in sec["Diversity"]
        if line.startswith("accepted:")
    )
    return {
        "answer_verbatim": "\n".join(sec["stdout"]).strip("\n"),
        "citations": sec["Citations"],
        "state": result.get("state"),
        "abstention_stage": result.get("abstention_stage"),
        "cost_usd": round(cost, 4),
        "provider_calls": calls,
        "provider_tokens": tokens,
        "accepted_records": sorted({filter_rows[c][1] for c in accepted_ids}),
        "accepted_chunks": [f"{filter_rows[c][1]} {filter_rows[c][4]}" for c in accepted_ids],
        "facets": sec["Facets"],
        "draft_before_verification": sec["Draft"],
        "verification": sec["Verification"],
        "dropped": [line for line in sec["Sub claims"] if line.startswith("dropped_sentence")],
        "trace": trace.name,
    }


def tracepath_side(record_name: str, question: str) -> dict[str, object]:
    """One question's tracepath answer from its prompt ask-1 record."""
    ask = json.loads((Path("artifacts/asks") / record_name).read_text())
    if ask["question"] != question or ask["prompt_version"] != "ask-1":
        raise ValueError(f"{record_name} is not this question's ask-1 record")
    return {
        "record": f"artifacts/asks/{record_name}",
        "prompt_version": ask["prompt_version"],
        "model": ask["model"],
        "verdict": ask["verdict"],
        "claims": [
            {k: claim[k] for k in ("text", "cites", "basis", "inferred", "history")}
            for claim in ask["claims"]
        ],
        "missing": ask["missing"],
        "cost_usd": ask["cost_usd"],
    }


def side_by_side(entry: dict[str, object]) -> list[str]:
    """The README markdown for one question's two answers."""
    label = "Eval" if entry["set"] == EVAL_FILES["eval"] else "Held out"
    tp = entry["tracepath"]
    dm = entry["decision_memory"]
    assert isinstance(tp, dict) and isinstance(dm, dict)
    lines = [
        f"### {label} question {entry['question_number']}",
        "",
        f"> {entry['question']}",
        "",
        f"**tracepath** (`{tp['record'].split('/')[-1]}`, prompt `ask-1`, `{tp['model']}`, "
        f"${tp['cost_usd']:.4f}). Verdict: `{tp['verdict']}`.",
        "",
    ]
    for index, claim in enumerate(tp["claims"], 1):
        cites = ", ".join(f"`{c}`" for c in claim["cites"])
        flags = [name for name in ("inferred", "history") if claim[name]]
        flag = f" ({', '.join(flags)})" if flags else ""
        lines.append(f"{index}. {claim['text']} [{cites}]{flag}")
    if tp["missing"]:
        lines += ["", "Missing, as the answer states it:", ""]
        lines += [f"- {item}" for item in tp["missing"]]
    lines += [
        "",
        f"**decision-memory** (`data/{dm['trace']}`, ${dm['cost_usd']:.4f}). "
        f"State: `{dm['state']}` at `{dm['abstention_stage']}`.",
        "",
        "```text",
        dm["answer_verbatim"],
        "```",
        "",
    ]
    if dm["citations"]:
        lines += ["Citations:", ""] + [f"- `{c}`" for c in dm["citations"]]
    else:
        lines.append("Citations: none.")
    lines.append("")
    return lines


def main() -> None:
    """Write data/answers.json and print the side by side markdown and the cost total."""
    entries = []
    for (kind, number), record_name in ASK1_RECORDS.items():
        source = EVAL_FILES[kind]
        question = json.loads(Path(source).read_text())["entries"][number - 1]["question"]
        entries.append(
            {
                "set": source,
                "question_number": number,
                "question": question,
                "decision_memory": decision_memory_side(kind, number),
                "tracepath": tracepath_side(record_name, question),
            }
        )
    (DATA / "answers.json").write_text(json.dumps(entries, indent=2, ensure_ascii=False) + "\n")
    for entry in entries:
        print("\n".join(side_by_side(entry)))
    total = sum(e["decision_memory"]["cost_usd"] for e in entries)  # type: ignore[index]
    print(f"<!-- decision-memory queries: ${total:.4f} -->")


if __name__ == "__main__":
    main()
