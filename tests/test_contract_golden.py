"""Golden contract tripwire: the committed artifact for a fixed spec must be
byte-stable across kernel changes. If this test fails, the canonicalisation
contract moved — that is a schema_version + tag event, never an accident.

Regenerate deliberately (after a contract decision) with:
    python tests/test_contract_golden.py
"""

import json
from pathlib import Path

from statespec import identity
from statespec.core import Invariant, StateSpec, Transition
from statespec.expr import field

FIXTURE = Path(__file__).parent / "fixtures" / "golden.policy.json"


def _golden_spec() -> StateSpec:
    # Deliberately no Opaque guards: opaque hashes depend on inspect.getsource
    # formatting, which would make the fixture fragile for no contract value.
    return StateSpec(
        name="golden",
        title="Golden fixture workflow",
        states={"draft": "Being written", "review": "Awaiting review", "done": "Closed out"},
        fields={"errors": "int", "amount": "decimal"},
        initial="draft",
        terminal=frozenset({"done"}),
        transitions=(
            Transition("submit", ("draft",), "review", roles=frozenset({"author"}),
                       guard=field("errors").le(0), label="Submit for review",
                       control_id="GOLD-SUBMIT"),
            Transition("approve", ("review",), "done", roles=frozenset({"reviewer"}),
                       guard=None, label="Approve", control_id="GOLD-APPROVE"),
        ),
        invariants=(
            Invariant("non_negative", field("amount").ge(0),
                      label="Amount never negative", control_id="GOLD-INV-1"),
        ),
        version=1,
    )


def test_golden_artifact_byte_stable():
    committed = json.loads(FIXTURE.read_text())
    fresh = identity.policy_record(_golden_spec())
    assert fresh == committed, (
        "policy_record() output diverged from the committed golden artifact — "
        "the canonicalisation contract changed"
    )
    # Byte-level: the exact serialisation the digests are computed over.
    assert (
        json.dumps(fresh, sort_keys=True, separators=(",", ":"))
        == json.dumps(committed, sort_keys=True, separators=(",", ":"))
    )


def test_golden_digests_pinned():
    committed = json.loads(FIXTURE.read_text())
    spec = _golden_spec()
    assert identity.semantic_digest(spec) == committed["semantic_digest"]
    assert identity.presentation_digest(spec) == committed["presentation_digest"]
    assert committed["schema_version"] == 2


if __name__ == "__main__":
    FIXTURE.parent.mkdir(exist_ok=True)
    FIXTURE.write_text(json.dumps(identity.policy_record(_golden_spec()), indent=2,
                                  sort_keys=True) + "\n")
    print(f"wrote {FIXTURE}")
