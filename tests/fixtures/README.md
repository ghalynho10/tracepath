# Fixtures

`runs/` holds five extraction runs over one section of JobHunt's spec 0011, copied here
as fresh files so nothing in `src/` or `tests/` reads `reference/`, which is gitignored
and absent from CI and a fresh clone (spec 0002, AC-12).

- `run1.json`, `run2.json`, `run3.json`: three runs that agree on the comparison
  signature. They differ in span text and whitespace, which the signature ignores.
- `run_split.json`: the same section split into two entities instead of one, so it
  disagrees on the signature.
- `run_bad.json`: carries an invented flag name (`atomicity_boundary_call`), which the
  closed flag set rejects.
