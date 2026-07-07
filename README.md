# statespec

Declarative lifecycle policy for entities whose `status` moves through reviewable steps.
A spec is plain data — states, named transitions (roles + guards), invariants — and the
same artifact is human-readable (Mermaid / plain-English table), machine-checkable
(`validate`), enforced through a single interpreter (`apply` / `fire`), and identified
by content digests (`identity`) so that behavioural change is mechanically
distinguishable from wording change.

- `statespec.core` — the engine: `StateSpec`, `Transition`, `Invariant`, `apply`, `fire`, `validate`.
- `statespec.expr` — closed guard/invariant expression grammar (compare + boolean), with a
  versioned `Opaque` escape hatch whose body is hashed into the policy identity.
- `statespec.identity` — `canonical()`, `semantic_digest` / `presentation_digest`,
  `change_kind`, `diff`, and `policy_record()` (the versioned `.policy.json` envelope —
  see `docs/policy-artifact-contract.md`, the authoritative copy of the contract).
- `statespec.render` — Mermaid, tables, and the generated lifecycle doc.

Pure Python, stdlib-only, no dependencies.

## Quick start

```bash
pip install statespec
```

```python
from statespec import StateSpec, Transition, apply, validate
from statespec.expr import field

spec = StateSpec(
    name="review", title="Review",
    states={"draft": "Being written", "submitted": "Awaiting review",
            "approved": "Done"},
    fields={"amount": "int"},
    initial="draft", terminal=frozenset({"approved"}),
    transitions=(
        Transition("submit", ("draft",), "submitted",
                   roles=frozenset({"author"})),
        Transition("approve", ("submitted",), "approved",
                   roles=frozenset({"reviewer"}),
                   guard=field("amount").le(100)),
    ),
)

assert validate(spec, known_roles=frozenset({"author", "reviewer"})) == []
apply(spec, "approve", "submitted", frozenset({"reviewer"}), {"amount": 40})
# -> "approved". Wrong role -> PermissionDenied; amount 500 -> GuardRejected;
# fire() returns the same decision plus structured evidence per condition.
```

Every claim above is exercised by the test suite: the refusal taxonomy and
its precedence in `tests/test_core.py`, the expression grammar and
typechecking in `tests/test_expr.py`, digests/diff in `tests/test_identity.py`,
and canonicalisation byte-stability against a golden artifact in
`tests/test_contract_golden.py`.

## Boundaries (what this does not do)

statespec sits *above* concurrency and persistence. It decides whether a
transition is legal; it does not make the write atomic or durable. It will
not stop a race between two concurrent transitions (pair it with optimistic
locking or a version column at the persistence layer), a forgotten lock, an
out-of-band mutation that sets `status` around the interpreter, or a
cross-system inconsistency. The "single enforcement path" property holds
only if every status write in the application routes through `apply`/`fire`
— enforce that with a repo-level convention or CI gate, not by trust. The
digests identify *policy* change; they do not verify that deployed code
matches the artifact — that check belongs to CI or a control plane.

## Provenance

Extracted from [`ConceptPending/baseplate`](https://github.com/ConceptPending/baseplate)
branch `example/state-machine` at tag `statespec-v0.3.0` (commit `2aca24e`, 2026-06-10),
where the kernel was developed and frozen. The only changes at extraction were the import
rename `app.statespec` → `statespec` and doc-path adjustments. This repository is the
kernel's authoritative home from `statespec-v0.4.0` onward; the in-tree copy in baseplate
remains frozen at v0.3.0 as part of the reference example.

## Versioning and freeze discipline

Kernel tags form their own series (`statespec-vX.Y.Z`), separate from any consuming
product's versions. The canonicalisation and digest rules are a **frozen contract**:
any change to the policy-artifact envelope bumps `schema_version` and the kernel tag
together, and is recorded in `docs/policy-artifact-contract.md`'s changelog. Changes
that alter existing digests are breaking and require explicit re-binding by consumers
(e.g. approval planes). Exceptions to the freeze: genuine bugs, security issues, or
contract defects.

Known consumers: `baseplate` (reference example, v0.3.0), `baseplate-control`
(approval plane; vendors this kernel byte-identically and verifies digests independently).

## Development

```bash
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pytest
.venv/bin/ruff check src tests
```
