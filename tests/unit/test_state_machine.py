"""
tests/unit/test_state_machine.py
Tests for platform_core.core.state_machine
"""

import pytest
from platform_core.core.state_machine.base import (
    StateMachine,
    ProjectState,
    StateTransition,
    InvalidTransitionError,
    DEFAULT_TRANSITIONS,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fresh_sm(initial: ProjectState = ProjectState.CREATED) -> StateMachine:
    """StateMachine without env or event_mgr (in-memory only)."""
    return StateMachine(initial=initial, env=None, event_mgr=None)


# ---------------------------------------------------------------------------
# Test: initial state
# ---------------------------------------------------------------------------

def test_initial_state_is_created():
    sm = fresh_sm()
    assert sm.current_state == ProjectState.CREATED


def test_custom_initial_state():
    sm = fresh_sm(initial=ProjectState.TESTING)
    assert sm.current_state == ProjectState.TESTING


# ---------------------------------------------------------------------------
# Test: valid transitions
# ---------------------------------------------------------------------------

def test_transition_created_to_planning():
    sm = fresh_sm()
    new_state = sm.transition("PROJECT_INITIATED")
    assert new_state == ProjectState.PLANNING
    assert sm.current_state == ProjectState.PLANNING


def test_full_happy_path():
    sm = fresh_sm()
    sequence = [
        ("PROJECT_INITIATED",       ProjectState.PLANNING),
        ("SPECIFICATION_GENERATED", ProjectState.ARCHITECTING),
        ("ARCHITECTURE_DEFINED",    ProjectState.CODING),
        ("BACKEND_GENERATED",       ProjectState.REVIEWING),
        ("BUILD_STARTED",           ProjectState.TESTING),
        ("TEST_PASSED",             ProjectState.DEPLOYING),
        ("BUILD_FINISHED",          ProjectState.DONE),
    ]
    for trigger, expected_state in sequence:
        result = sm.transition(trigger)
        assert result == expected_state, (
            f"After trigger '{trigger}': expected {expected_state}, got {result}"
        )


def test_wildcard_fail_transition():
    """BUILD_FAILED can fire from any state."""
    for state in [
        ProjectState.PLANNING,
        ProjectState.CODING,
        ProjectState.TESTING,
        ProjectState.REVIEWING,
    ]:
        sm = fresh_sm(initial=state)
        result = sm.transition("BUILD_FAILED")
        assert result == ProjectState.FAILED


# ---------------------------------------------------------------------------
# Test: self-healing resume
# ---------------------------------------------------------------------------

def test_self_healing_resume_from_failed():
    sm = fresh_sm(initial=ProjectState.FAILED)
    result = sm.transition("SELF_HEALING_ATTEMPTED")
    assert result == ProjectState.TESTING


# ---------------------------------------------------------------------------
# Test: invalid transition raises error
# ---------------------------------------------------------------------------

def test_invalid_trigger_raises():
    sm = fresh_sm()  # CREATED
    with pytest.raises(InvalidTransitionError) as exc_info:
        sm.transition("BUILD_FINISHED")  # Not valid from CREATED
    err = exc_info.value
    assert err.trigger == "BUILD_FINISHED"
    assert err.current_state == ProjectState.CREATED


def test_nonexistent_trigger_raises():
    sm = fresh_sm()
    with pytest.raises(InvalidTransitionError):
        sm.transition("TOTALLY_MADE_UP_TRIGGER")


# ---------------------------------------------------------------------------
# Test: can_transition
# ---------------------------------------------------------------------------

def test_can_transition_valid():
    sm = fresh_sm()  # CREATED
    assert sm.can_transition("PROJECT_INITIATED") is True


def test_can_transition_invalid():
    sm = fresh_sm()  # CREATED
    assert sm.can_transition("BUILD_FINISHED") is False
    assert sm.can_transition("NONEXISTENT") is False


def test_can_transition_wildcard():
    """BUILD_FAILED is always possible."""
    for state in ProjectState:
        if state in (ProjectState.DONE,):
            continue  # wildcard still works but DONE→FAILED may be unusual
        sm = fresh_sm(initial=state)
        # Should be possible (wildcard)
        assert sm.can_transition("BUILD_FAILED") is True


# ---------------------------------------------------------------------------
# Test: history
# ---------------------------------------------------------------------------

def test_history_records_transitions():
    sm = fresh_sm()
    sm.transition("PROJECT_INITIATED")
    sm.transition("SPECIFICATION_GENERATED")
    hist = sm.history()
    assert len(hist) == 2
    assert hist[0]["trigger"] == "PROJECT_INITIATED"
    assert hist[0]["from_state"] == "CREATED"
    assert hist[0]["to_state"] == "PLANNING"
    assert hist[1]["trigger"] == "SPECIFICATION_GENERATED"
    assert hist[1]["from_state"] == "PLANNING"
    assert hist[1]["to_state"] == "ARCHITECTING"


def test_history_has_timestamps():
    sm = fresh_sm()
    sm.transition("PROJECT_INITIATED")
    hist = sm.history()
    assert "timestamp" in hist[0]
    assert hist[0]["timestamp"]  # not empty


# ---------------------------------------------------------------------------
# Test: state persistence via Environment
# ---------------------------------------------------------------------------

def test_state_persists_to_env(tmp_path):
    from platform_core.core.environment.local import LocalEnvironment
    env = LocalEnvironment(str(tmp_path))
    sm = StateMachine(initial=ProjectState.CREATED, env=env)
    sm.transition("PROJECT_INITIATED")

    # state.json should exist and contain PLANNING
    import json
    data = json.loads((tmp_path / "state.json").read_text())
    assert data["current_state"] == "PLANNING"


def test_state_reloads_from_env(tmp_path):
    from platform_core.core.environment.local import LocalEnvironment
    env = LocalEnvironment(str(tmp_path))

    # First machine — advance to ARCHITECTING
    sm1 = StateMachine(initial=ProjectState.CREATED, env=env)
    sm1.transition("PROJECT_INITIATED")
    sm1.transition("SPECIFICATION_GENERATED")

    # Second machine — should resume from persisted state
    sm2 = StateMachine(initial=ProjectState.CREATED, env=env)
    assert sm2.current_state == ProjectState.ARCHITECTING


# ---------------------------------------------------------------------------
# Test: STATE_TRANSITIONED event emitted
# ---------------------------------------------------------------------------

def test_event_emitted_on_transition(tmp_path):
    from platform_core.core.environment.local import LocalEnvironment
    from platform_core.core.events.base import EventManager

    env = LocalEnvironment(str(tmp_path))
    event_mgr = EventManager(env)
    sm = StateMachine(initial=ProjectState.CREATED, env=env, event_mgr=event_mgr)
    sm.transition("PROJECT_INITIATED", project_id="proj_test")

    events = event_mgr.list_events_by_type("STATE_TRANSITIONED")
    assert len(events) == 1
    assert events[0].payload["trigger"] == "PROJECT_INITIATED"
    assert events[0].payload["from_state"] == "CREATED"
    assert events[0].payload["to_state"] == "PLANNING"
