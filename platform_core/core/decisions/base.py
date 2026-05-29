import datetime
import json
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from platform_core.core.environment.base import Environment


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class DecisionStatus(str, Enum):
    """Lifecycle status of a decision made by an agent or human."""
    PROPOSED   = "PROPOSED"    # Decision recorded, not yet validated
    APPROVED   = "APPROVED"    # Accepted by downstream consumer or human
    REJECTED   = "REJECTED"    # Overridden / reverted
    SUPERSEDED = "SUPERSEDED"  # Replaced by a later decision


# ---------------------------------------------------------------------------
# Decision model
# ---------------------------------------------------------------------------

class Decision:
    """
    Records *why* something happened — the rationale behind an agent action.

    Links:
      - ``input_artifact_ids``  : artifacts examined before this decision
      - ``output_artifact_ids`` : artifacts produced as a result of this decision
      - ``artifact_id``         : primary output artifact (convenience; first of output_artifact_ids)
    """

    def __init__(
        self,
        decision: str,                           # Short title / description of the decision
        reason: str,                             # Detailed rationale
        agent: str,                              # Agent or "human:<username>" that made it
        id: Optional[str] = None,
        artifact_id: Optional[str] = None,       # Primary output artifact (backward compat)
        input_artifact_ids: Optional[List[str]] = None,   # Evidence chain
        output_artifact_ids: Optional[List[str]] = None,  # Produced artifacts
        status: str = DecisionStatus.PROPOSED,
        created_at: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        self.id = id or f"dec_{str(uuid.uuid4())[:8]}"
        self.decision = decision          # kept as 'decision' for backward compat
        self.title = decision             # semantic alias
        self.reason = reason
        self.agent = agent
        self.status = status

        # Artifact linkage
        self.artifact_id = artifact_id   # backward compat single pointer
        self.input_artifact_ids: List[str] = input_artifact_ids or []
        # output_artifact_ids: if artifact_id provided, it is the primary output
        self.output_artifact_ids: List[str] = output_artifact_ids or (
            [artifact_id] if artifact_id else []
        )

        self.created_at = (
            created_at
            or datetime.datetime.now(datetime.timezone.utc).isoformat()
        )
        self.context = context or {}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "decision": self.decision,
            "reason": self.reason,
            "agent": self.agent,
            "status": self.status,
            "artifact_id": self.artifact_id,
            "input_artifact_ids": self.input_artifact_ids,
            "output_artifact_ids": self.output_artifact_ids,
            "created_at": self.created_at,
            "context": self.context,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Decision":
        return cls(
            id=data.get("id"),
            decision=data.get("decision", ""),
            reason=data.get("reason", ""),
            agent=data.get("agent", ""),
            artifact_id=data.get("artifact_id"),
            input_artifact_ids=data.get("input_artifact_ids") or [],
            output_artifact_ids=data.get("output_artifact_ids") or [],
            status=data.get("status", DecisionStatus.PROPOSED),
            created_at=data.get("created_at"),
            context=data.get("context"),
        )


# ---------------------------------------------------------------------------
# DecisionManager
# ---------------------------------------------------------------------------

class DecisionManager:
    def __init__(self, env: Environment):
        self.env = env

    def log_decision(self, decision: Decision) -> None:
        """Saves a decision into the sandboxed environment filesystem and updates the manifest."""
        decision_path = f"decisions/{decision.id}.json"
        self.env.write_file(decision_path, json.dumps(decision.to_dict(), indent=2, ensure_ascii=False))

        # Update manifest
        manifest_path = "decisions/manifest.json"
        manifest = []
        if self.env.exists(manifest_path):
            try:
                manifest = json.loads(self.env.read_file(manifest_path))
            except Exception:
                manifest = []

        manifest = [item for item in manifest if item["id"] != decision.id]
        manifest.append({
            "id": decision.id,
            "decision": decision.decision,
            "reason": decision.reason,
            "agent": decision.agent,
            "status": decision.status,
            "artifact_id": decision.artifact_id,
            "input_artifact_ids": decision.input_artifact_ids,
            "output_artifact_ids": decision.output_artifact_ids,
            "created_at": decision.created_at,
            "path": decision_path,
        })
        self.env.write_file(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False))

    def list_decisions(self) -> List[Decision]:
        """Lists all registered decisions."""
        manifest_path = "decisions/manifest.json"
        if not self.env.exists(manifest_path):
            return []
        try:
            manifest = json.loads(self.env.read_file(manifest_path))
            decisions = []
            for item in manifest:
                dec_path = f"decisions/{item['id']}.json"
                if self.env.exists(dec_path):
                    try:
                        data = json.loads(self.env.read_file(dec_path))
                        decisions.append(Decision.from_dict(data))
                    except Exception:
                        pass
            return decisions
        except Exception:
            return []

    def list_by_agent(self, agent: str) -> List[Decision]:
        """Returns all decisions made by a specific agent."""
        return [d for d in self.list_decisions() if d.agent == agent]

    def list_by_artifact(self, artifact_id: str) -> List[Decision]:
        """Returns all decisions that reference a specific artifact (input or output)."""
        result = []
        for d in self.list_decisions():
            if (d.artifact_id == artifact_id
                    or artifact_id in d.input_artifact_ids
                    or artifact_id in d.output_artifact_ids):
                result.append(d)
        return result
