"""Real run checking the AC-7 `label` round trip, spec 0001 and 0008.

Under spec 0001's run policy (Sonnet 5, medium effort, three runs each). At the time
this ran, 0008's Preamble already held committed real artifacts from the original
AC-14 coverage run, under the old prompt (no `label` field existed then); overwriting
them in place would have silently discarded that historical evidence, so this script
writes Preamble's own artifacts beside itself (`SCRATCH`), not into the repo's tracked
`artifacts/runs/`. They were moved into place by hand afterward, once the old ones
were moved aside to `artifacts/superseded/` (see the experiment's README). Binding
rules had no prior real artifacts, so its own runs write straight to the tracked path.

Run from the repository root: uv run python <this file>
"""

import json
from pathlib import Path

from tracepath.artifacts import now_utc, write_run
from tracepath.config import load_anthropic_settings
from tracepath.extract.client import build_client
from tracepath.extract.ids import section_slugs
from tracepath.extract.records import Record, read_commit, spec_record
from tracepath.extract.schema import ReferenceEndpoint, normalize_label
from tracepath.extract.units import Unit, UnitKind, split_units
from tracepath.pipeline import resolve_accepted, run_unit

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "corpus" / "jobhunt" / "docs"
SCRATCH = Path(__file__).parent


def unit_of(record: str, section: str, kind: UnitKind) -> tuple[Unit, str]:
    """The named unit of one spec, and its section slug made unique within it."""
    path = next(SNAPSHOT.glob(f"specs/{record}-*/index.md"))
    units = split_units(str(path.relative_to(SNAPSHOT)), path.read_text())
    own = [u for u in units if u.record_id == record]
    slugs = section_slugs(tuple(u.section for u in own))
    for u, slug in zip(own, slugs, strict=True):
        if u.kind is kind and (kind is UnitKind.PREAMBLE or u.section == section):
            return u, slug
    raise SystemExit(f"unit not found: {record} {section} {kind}")


def main() -> None:
    """Run both units for real, resolve them against each other, and report."""
    commit = read_commit((ROOT / "corpus" / "jobhunt" / "SNAPSHOT.md").read_text())
    settings = load_anthropic_settings()
    print(f"model={settings.model} effort={settings.effort} runs={settings.runs_per_unit}")
    client = build_client(settings)
    extracted_at = now_utc()

    br_unit, br_slug = unit_of("0001", "Binding rules", UnitKind.SECTION)
    pre_unit, pre_slug = unit_of("0008", "Preamble", UnitKind.PREAMBLE)
    print(f"Binding rules: {len(br_unit.text)} chars, slug={br_slug}")
    print(f"Preamble: {len(pre_unit.text)} chars, slug={pre_slug}")

    print("\n--- running 0001 Binding rules (3 calls) ---")
    br_result = run_unit(client, settings, br_unit, br_slug, commit, extracted_at)
    for a in br_result.artifacts:
        path = write_run(ROOT, a)  # tracked repo path: net new, no collision
        print("wrote", path.relative_to(ROOT))

    print("\n--- running 0008 Preamble (3 calls) ---")
    pre_result = run_unit(client, settings, pre_unit, pre_slug, commit, extracted_at)
    for a in pre_result.artifacts:
        path = write_run(SCRATCH, a)  # scratchpad: do not clobber committed evidence
        print("wrote (scratchpad)", path.relative_to(SCRATCH))

    path1 = SNAPSHOT / "specs" / "0001-stack-and-architecture" / "index.md"
    path8 = SNAPSHOT / "specs" / "0008-app-shell-and-navigation" / "index.md"
    records: list[Record] = [
        spec_record(str(path1.relative_to(SNAPSHOT)), path1.read_text(), commit),
        spec_record(str(path8.relative_to(SNAPSHOT)), path8.read_text(), commit),
    ]

    corpus = resolve_accepted([br_result, pre_result], records)

    report: dict[str, object] = {}

    # 1. Verbatim labels, both sides.
    entity_labels = [
        {"run": i + 1, "labels": [e.entity.label for e in out.entities if e.entity.label]}
        for i, out in enumerate(br_result.identified)
    ]
    ref_labels = []
    for i, out in enumerate(pre_result.identified):
        for rel in out.relationships:
            for endpoint in (rel.source, rel.target):
                if isinstance(endpoint, ReferenceEndpoint) and endpoint.label:
                    ref_labels.append(
                        {
                            "run": i + 1,
                            "type": str(rel.type),
                            "record": endpoint.record,
                            "id": endpoint.id,
                            "label": endpoint.label,
                            "mention": endpoint.mention,
                        }
                    )
    report["entity_labels_per_run"] = entity_labels
    report["reference_labels_per_run"] = ref_labels

    # Does any entity label, normalized, match any reference label, normalized?
    entity_norms = {
        normalize_label(lbl): lbl
        for run in entity_labels
        for lbl in run["labels"]  # type: ignore[union-attr]
    }
    matches = []
    for ref in ref_labels:
        norm = normalize_label(ref["label"])
        if norm in entity_norms:
            matches.append({"reference": ref["label"], "entity": entity_norms[norm], "norm": norm})
    report["normalized_matches"] = matches

    # 2. Agreement on label text, each side.
    report["binding_rules_agree"] = br_result.routed.comparison.agree
    report["preamble_agree"] = pre_result.routed.comparison.agree
    report["binding_rules_differing_entities"] = [
        list(s) for s in br_result.routed.comparison.differing_entities
    ]
    report["preamble_differing_relationships"] = [
        list(s) for s in pre_result.routed.comparison.differing_relationships
    ]

    # 3. What the 0008 reference resolved to.
    outcomes = []
    for link in corpus.resolution.links:
        outcomes.append(
            {
                "type": str(link.type),
                "source": {"id": link.source.canonical_id, "target": str(link.source.target)},
                "target": {"id": link.target.canonical_id, "target": str(link.target.target)},
            }
        )
    report["resolved_links"] = outcomes
    report["unresolved"] = [
        {"canonical_id": n.canonical_id, "mention": n.mention, "record": n.record, "label": n.label}
        for n in corpus.resolution.unresolved
    ]
    report["held"] = [
        {
            "record": h.record,
            "section": h.section,
            "signature": list(h.item.signature),
            "reasons": [{"name": str(r.name), "detail": r.detail} for r in h.item.reasons],
        }
        for h in corpus.held
    ]
    report["accepted_entities_binding_rules"] = [
        {"id": e.canonical_id, "label": e.entity.label, "type": str(e.entity.type)}
        for e in br_result.routed.accepted_entities
    ]
    report["review_binding_rules"] = [
        {
            "signature": list(i.signature),
            "canonical_id": i.canonical_id,
            "reasons": [{"name": str(r.name), "detail": r.detail} for r in i.reasons],
        }
        for i in br_result.routed.review
    ]

    # 4. Real cost.
    total_in = br_result.input_tokens + pre_result.input_tokens
    total_out = br_result.output_tokens + pre_result.output_tokens
    cost = round(total_in / 1e6 * 2 + total_out / 1e6 * 10, 4)
    report["cost"] = {
        "input_tokens": total_in,
        "output_tokens": total_out,
        "cost_usd": cost,
        "binding_rules_input": br_result.input_tokens,
        "binding_rules_output": br_result.output_tokens,
        "preamble_input": pre_result.input_tokens,
        "preamble_output": pre_result.output_tokens,
    }

    out_path = SCRATCH / "real_label_run_report.json"
    out_path.write_text(json.dumps(report, indent=2))
    print(f"\nReport written to {out_path}")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
