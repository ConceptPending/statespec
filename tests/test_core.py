"""The enforcement path itself: can_fire/fire/apply refusal taxonomy and
precedence, the evidence trail, enabled_transitions, and validate's
structural (graph-shape) checks. test_expr.py covers the expression grammar
and typechecking; this file covers the claims the README makes about the
single interpreter."""

import pytest

from statespec import (
    GuardRejected,
    IllegalTransition,
    Invariant,
    PermissionDenied,
    StateSpec,
    Transition,
    UnknownAction,
    apply,
    can_fire,
    enabled_transitions,
    fire,
    validate,
)
from statespec.core import reachable_states
from statespec.expr import field


def _review_spec(**overrides):
    """A small but complete lifecycle: draft -> submitted -> approved|rejected."""
    kwargs = dict(
        name="review", title="Review",
        states={"draft": "", "submitted": "", "approved": "", "rejected": ""},
        fields={"amount": "int"},
        initial="draft",
        terminal=frozenset({"approved", "rejected"}),
        transitions=(
            Transition("submit", ("draft",), "submitted",
                       roles=frozenset({"author"})),
            Transition("approve", ("submitted",), "approved",
                       roles=frozenset({"reviewer"}),
                       guard=field("amount").le(100),
                       control_id="REV-APPROVE"),
            Transition("reject", ("submitted",), "rejected",
                       roles=frozenset({"reviewer"})),
        ),
        invariants=(Invariant("amount_nonneg", field("amount").ge(0)),),
    )
    kwargs.update(overrides)
    return StateSpec(**kwargs)


SPEC = _review_spec()


# --- refusal taxonomy and precedence ----------------------------------------


def test_unknown_action():
    with pytest.raises(UnknownAction):
        apply(SPEC, "frobnicate", "draft", frozenset({"author"}), {"amount": 1})


def test_illegal_transition_wrong_state():
    with pytest.raises(IllegalTransition):
        apply(SPEC, "approve", "draft", frozenset({"reviewer"}), {"amount": 1})


def test_terminal_states_are_sinks():
    # No transition leaves a terminal state, so any action from one is illegal.
    with pytest.raises(IllegalTransition):
        apply(SPEC, "submit", "approved", frozenset({"author"}), {"amount": 1})


def test_permission_denied():
    with pytest.raises(PermissionDenied):
        apply(SPEC, "approve", "submitted", frozenset({"author"}), {"amount": 1})


def test_guard_rejected():
    with pytest.raises(GuardRejected):
        apply(SPEC, "approve", "submitted", frozenset({"reviewer"}), {"amount": 101})


def test_precedence_state_before_role_before_guard():
    # Wrong state AND wrong role AND failing guard: source-state check wins.
    d = can_fire(SPEC, "approve", "draft", frozenset(), {"amount": 101})
    assert d.error is IllegalTransition
    # Right state, wrong role, failing guard: role check wins over guard.
    d = can_fire(SPEC, "approve", "submitted", frozenset(), {"amount": 101})
    assert d.error is PermissionDenied


def test_can_fire_refuses_without_raising():
    d = can_fire(SPEC, "approve", "submitted", frozenset({"author"}), {"amount": 1})
    assert d.allowed is False and d.dest is None and d.error is PermissionDenied
    ok = can_fire(SPEC, "approve", "submitted", frozenset({"reviewer"}), {"amount": 1})
    assert ok.allowed is True and ok.dest == "approved"


# --- the happy path and its evidence ----------------------------------------


def test_apply_returns_dest():
    assert apply(SPEC, "submit", "draft", frozenset({"author"}), {"amount": 1}) == "submitted"


def test_fire_returns_evidence_for_guard_and_invariants():
    dest, evals = fire(SPEC, "approve", "submitted", frozenset({"reviewer"}),
                       {"amount": 40})
    assert dest == "approved"
    by_kind = {(e.kind, e.control_id): e for e in evals}
    guard_ev = by_kind[("guard", "REV-APPROVE")]  # control_id, not the name
    assert guard_ev.result is True and guard_ev.inputs == {"amount": 40}
    inv_ev = by_kind[("invariant", "amount_nonneg")]  # defaults to the name
    assert inv_ev.result is True and inv_ev.inputs == {"amount": 40}


def test_post_overrides_participate_in_invariant_check():
    from statespec import InvariantViolation
    with pytest.raises(InvariantViolation) as exc:
        fire(SPEC, "submit", "draft", frozenset({"author"}), {"amount": 1},
             post_overrides={"amount": -5})
    assert exc.value.violated == ["amount_nonneg"]


def test_enabled_transitions_respects_state_role_guard():
    names = lambda ts: [t.name for t in ts]  # noqa: E731
    assert names(enabled_transitions(SPEC, "draft", frozenset({"author"}), {"amount": 1})) == ["submit"]
    assert names(enabled_transitions(SPEC, "submitted", frozenset({"reviewer"}), {"amount": 1})) == ["approve", "reject"]
    # Guard filters approve out; reject (unguarded) survives.
    assert names(enabled_transitions(SPEC, "submitted", frozenset({"reviewer"}), {"amount": 500})) == ["reject"]
    assert enabled_transitions(SPEC, "approved", frozenset({"author", "reviewer"}), {"amount": 1}) == []


# --- structural validation (graph shape) ------------------------------------


def test_wellformed_spec_validates_clean():
    assert validate(SPEC, known_roles=frozenset({"author", "reviewer"})) == []


def test_reachable_states():
    assert reachable_states(SPEC) == {"draft", "submitted", "approved", "rejected"}


def test_unreachable_state_flagged():
    spec = _review_spec(states={"draft": "", "submitted": "", "approved": "",
                                "rejected": "", "limbo": ""})
    assert any("'limbo' is unreachable" in p for p in validate(spec))


def test_trap_state_flagged():
    # submitted with no way out: drop approve/reject.
    spec = _review_spec(transitions=(
        Transition("submit", ("draft",), "submitted", roles=frozenset({"author"})),
    ))
    assert any("cannot reach any terminal state (trap)" in p for p in validate(spec))


def test_dead_edge_no_roles_flagged():
    spec = _review_spec(transitions=(
        Transition("submit", ("draft",), "submitted"),  # roles omitted = no one
        Transition("approve", ("submitted",), "approved", roles=frozenset({"reviewer"})),
        Transition("reject", ("submitted",), "rejected", roles=frozenset({"reviewer"})),
    ))
    assert any("no permitted roles (dead edge)" in p for p in validate(spec))


def test_transition_leaving_terminal_flagged():
    spec = _review_spec(transitions=SPEC.transitions + (
        Transition("reopen", ("approved",), "draft", roles=frozenset({"author"})),
    ))
    assert any("terminals must be sinks" in p for p in validate(spec))


def test_misspelled_role_flagged_against_catalogue():
    problems = validate(SPEC, known_roles=frozenset({"author", "reviewr"}))
    assert any("not in the catalogue: ['reviewer']" in p for p in problems)


def test_duplicate_names_flagged():
    spec = _review_spec(transitions=SPEC.transitions + (
        Transition("submit", ("submitted",), "rejected", roles=frozenset({"reviewer"})),
    ))
    assert any("duplicate transition name 'submit'" in p for p in validate(spec))
