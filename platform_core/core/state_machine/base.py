"""
platform_core.core.state_machine.base
======================================
Formal State Machine for project lifecycle governance.

Uses only stdlib (enum, dataclasses, json) — no external dependencies.

Project Lifecycle
-----------------
CREATED → PLANNING → ARCHITECTING → CODING → REVIEWING → TESTING → DEPLOYING → DONE
                                                                              ↘ FAILED (from any state)
FAILED → TESTING  (via self-healing / resume)

Transitions are driven by Event types emitted by the platform.
Every state transition persists to ``state.json`` in the workspace and
emits a ``STATE_TRANSITIONED`` Event.
"""

import datetime
import json
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, TYPE_CHECKING

if TYPE_CHECKING:
    from platform_core.core.environment.base import Environment
    from platform_core.core.events.base import Event, EventManager


# ---------------------------------------------------------------------------
# State Enum
# ---------------------------------------------------------------------------

class ProjectState(str, Enum):
    """Ordered lifecycle states of a platform-managed project."""
    CREATED      = "CREATED"       # Project record exists; nothing started
    PLANNING     = "PLANNING"      # PM Agent generating specifications
    ARCHITECTING = "ARCHITECTING"  # Architect Agent designing system
    CODING       = "CODING"        # Coder/CSS/Backend Agents generating code
    REVIEWING    = "REVIEWING"     # Build assembled; under review
    TESTING      = "TESTING"       # QA Playwright tests running
    DEPLOYING    = "DEPLOYING"     # Build passed; being packaged
    DONE         = "DONE"          # Successfully completed
    FAILED       = "FAILED"        # Terminal failure state


# ---------------------------------------------------------------------------
# Transition definition
# ---------------------------------------------------------------------------

@dataclass
class StateTransition:
    """Defines a valid state transition triggered by a specific event type."""
    trigger: str           # Event type that fires this transition
    from_state: str        # Source ProjectState value (or "*" for any state)
    to_state: str          # Target ProjectState value
    description: str = ""


# ---------------------------------------------------------------------------
# Default transition table for web_creator workflow
# ---------------------------------------------------------------------------

DEFAULT_TRANSITIONS: List[StateTransition] = [
    StateTransition(
        trigger="PROJECT_INITIATED",
        from_state=ProjectState.CREATED,
        to_state=ProjectState.PLANNING,
        description="PM Agent started planning"
    ),
    StateTransition(
        trigger="SPECIFICATION_GENERATED",
        from_state=ProjectState.PLANNING,
        to_state=ProjectState.ARCHITECTING,
        description="PM specifications produced; Architect begins"
    ),
    StateTransition(
        trigger="ARCHITECTURE_DEFINED",
        from_state=ProjectState.ARCHITECTING,
        to_state=ProjectState.CODING,
        description="Architecture defined; coding phase begins"
    ),
    StateTransition(
        trigger="BACKEND_GENERATED",
        from_state=ProjectState.CODING,
        to_state=ProjectState.REVIEWING,
        description="All code artifacts produced"
    ),
    StateTransition(
        trigger="BUILD_STARTED",
        from_state=ProjectState.REVIEWING,
        to_state=ProjectState.TESTING,
        description="Build triggered; QA testing begins"
    ),
    StateTransition(
        trigger="TEST_PASSED",
        from_state=ProjectState.TESTING,
        to_state=ProjectState.DEPLOYING,
        description="All tests passed; moving to deployment"
    ),
    StateTransition(
        trigger="BUILD_FINISHED",
        from_state=ProjectState.DEPLOYING,
        to_state=ProjectState.DONE,
        description="Build finished successfully"
    ),
    # Self-healing resume: FAILED → TESTING
    StateTransition(
        trigger="SELF_HEALING_ATTEMPTED",
        from_state=ProjectState.FAILED,
        to_state=ProjectState.TESTING,
        description="Self-healing applied; retrying test phase"
    ),
    # Terminal failure from any state
    StateTransition(
        trigger="TEST_FAILED",
        from_state="*",
        to_state=ProjectState.FAILED,
        description="Tests failed terminally"
    ),
    StateTransition(
        trigger="BUILD_FAILED",
        from_state="*",
        to_state=ProjectState.FAILED,
        description="Build failed terminally"
    ),
]


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class InvalidTransitionError(RuntimeError):
    """Raised when a trigger event has no valid transition from the current state."""

    def __init__(self, trigger: str, current_state: str):
        self.trigger = trigger
        self.current_state = current_state
        super().__init__(
            f"No valid transition for trigger '{trigger}' from state '{current_state}'"
        )


# ---------------------------------------------------------------------------
# State Machine
# ---------------------------------------------------------------------------

class StateMachine:
    """
    Governs project lifecycle transitions.

    Usage
    -----
    sm = StateMachine(
        initial=ProjectState.CREATED,
        env=local_env,
        event_mgr=event_manager,
    )
    new_state = sm.transition("PROJECT_INITIATED", project_id="proj_abc")
    print(sm.current_state)  # ProjectState.PLANNING

    Persistence
    -----------
    State is persisted to ``state.json`` in the workspace root via ``env``.
    On construction the machine attempts to reload persisted state if it exists.

    Events
    ------
    Every successful transition emits a ``STATE_TRANSITIONED`` Event via
    ``event_mgr`` (if provided).
    """

    STATE_FILE = "state.json"

    def __init__(
        self,
        initial: ProjectState = ProjectState.CREATED,
        env: Optional["Environment"] = None,
        event_mgr: Optional["EventManager"] = None,
        transitions: Optional[List[StateTransition]] = None,
    ):
        self.env = env
        self.event_mgr = event_mgr
        self._transitions = transitions or DEFAULT_TRANSITIONS
        self._history: List[Dict] = []

        # Try to reload persisted state; fall back to initial
        persisted = self._load_state()
        if persisted:
            self._current = ProjectState(persisted["current_state"])
            self._history = persisted.get("history", [])
        else:
            self._current = initial
            self._persist()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def current_state(self) -> ProjectState:
        """The current lifecycle state."""
        return self._current

    def can_transition(self, trigger: str) -> bool:
        """Return True if ``trigger`` has a valid transition from the current state."""
        return self._find_transition(trigger) is not None

    def transition(self, trigger: str, project_id: Optional[str] = None) -> ProjectState:
        """
        Apply a transition triggered by ``trigger``.

        Parameters
        ----------
        trigger : str
            The event type string (e.g. ``"PROJECT_INITIATED"``).
        project_id : str, optional
            Used for event correlation when emitting ``STATE_TRANSITIONED``.

        Returns
        -------
        ProjectState
            The new (post-transition) state.

        Raises
        ------
        InvalidTransitionError
            If no transition is registered for ``trigger`` from the current state.
        """
        txn = self._find_transition(trigger)
        if txn is None:
            raise InvalidTransitionError(trigger, self._current)

        previous = self._current
        self._current = ProjectState(txn.to_state)

        # Record in history
        record = {
            "trigger": trigger,
            "from_state": previous.value,
            "to_state": self._current.value,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "description": txn.description,
        }
        self._history.append(record)
        self._persist()

        # Emit STATE_TRANSITIONED event
        self._emit_event(trigger, previous, project_id)

        return self._current

    def history(self) -> List[Dict]:
        """Return the full transition history as a list of dicts."""
        return list(self._history)

    def state_summary(self) -> Dict:
        """Return a dict snapshot of current machine state."""
        return {
            "current_state": self._current.value,
            "history": self._history,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _find_transition(self, trigger: str) -> Optional[StateTransition]:
        """Find the first matching transition for trigger + current state."""
        for txn in self._transitions:
            if txn.trigger != trigger:
                continue
            if txn.from_state == "*" or txn.from_state == self._current.value:
                return txn
        return None

    def _persist(self) -> None:
        """Write current state to workspace/state.json via Environment."""
        if self.env is None:
            return
        try:
            self.env.write_file(
                self.STATE_FILE,
                json.dumps(self.state_summary(), indent=2, ensure_ascii=False),
            )
        except Exception:
            pass  # Non-fatal — machine still functions in-memory

    def _load_state(self) -> Optional[Dict]:
        """Attempt to reload state from workspace/state.json."""
        if self.env is None:
            return None
        try:
            if self.env.exists(self.STATE_FILE):
                return json.loads(self.env.read_file(self.STATE_FILE))
        except Exception:
            pass
        return None

    def _emit_event(
        self,
        trigger: str,
        previous: ProjectState,
        project_id: Optional[str],
    ) -> None:
        """Emit a STATE_TRANSITIONED event via EventManager (if available)."""
        if self.event_mgr is None:
            return
        try:
            from platform_core.core.events.base import Event
            self.event_mgr.emit_event(Event(
                event_type="STATE_TRANSITIONED",
                producer="StateMachine",
                project_id=project_id,
                payload={
                    "trigger": trigger,
                    "from_state": previous.value,
                    "to_state": self._current.value,
                },
            ))
        except Exception:
            pass  # Non-fatal
