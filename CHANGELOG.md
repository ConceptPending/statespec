# Changelog

Kernel tag series: `statespec-vX.Y.Z`. Contract changes are also recorded in
`docs/policy-artifact-contract.md`.

## 0.4.0 — tag `statespec-v0.4.0` (2026-07-03)

Contract-defect fix (freeze exception): `canonical()` now includes `title`, so
`presentation_digest` is independently verifiable from the artifact and
`diff()` can describe a title change. `semantic_digest`,
`presentation_digest`, and envelope `schema_version: 2` are all unchanged —
existing approval bindings are unaffected. Adds the golden contract fixture
(`tests/fixtures/golden.policy.json`) as a canonicalisation tripwire.

## 0.3.0

Baseline as extracted from `ConceptPending/baseplate` tag `statespec-v0.3.0`
(commit `2aca24e`, 2026-06-10). Policy artifact envelope `schema_version: 2`
(`semantic_digest` + `presentation_digest`). No behavioural changes at
extraction: import rename `app.statespec` → `statespec` and doc paths only.
