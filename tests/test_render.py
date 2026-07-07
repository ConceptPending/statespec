"""Rendering: the generated doc's consumer-facing hints and its core shape.
Identity/digests are untouched by anything here (render is presentation
tooling, not the canonicalisation contract)."""

from statespec.core import Invariant, StateSpec, Transition
from statespec.expr import field
from statespec.render import to_markdown_doc, to_mermaid, to_table

SPEC = StateSpec(
    name="review", title="Review",
    states={"a": "Start here", "b": "Done"},
    fields={"n": "int"},
    initial="a", terminal=frozenset({"b"}),
    transitions=(Transition("go", ("a",), "b", roles=frozenset({"r"}),
                            guard=field("n").le(1), label="Go forward"),),
    invariants=(Invariant("n_nonneg", field("n").ge(0), label="n stays sane"),),
)


def test_doc_default_hints_match_baseplate_layout():
    doc = to_markdown_doc(SPEC)
    assert "Regenerate with `make spec-doc`." in doc
    assert "`app/statespec/review_spec.py`" in doc


def test_doc_hints_are_parameterizable():
    doc = to_markdown_doc(
        SPEC,
        regenerate_hint="`make policy`",
        source_hint="`src/review/spec.py`",
    )
    assert "Regenerate with `make policy`." in doc
    assert "`src/review/spec.py`" in doc
    assert "app/statespec" not in doc


def test_doc_contains_diagram_table_and_invariants():
    doc = to_markdown_doc(SPEC)
    assert to_mermaid(SPEC) in doc
    assert to_table(SPEC) in doc
    assert "n stays sane" in doc
    # The invariants preamble recommends a property suite; it must not claim
    # one exists in the consuming repo.
    assert "Hypothesis" not in doc
