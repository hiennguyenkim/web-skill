"""
platform_core.core.workflow.base
================================
Declarative, topologically-sorted Workflow Engine.

Concepts
--------
WorkflowStage
    A single step in a pipeline: has an id, an agent, a list of
    dependencies (depends_on), expected inputs/outputs, and runtime status.

WorkflowResult
    The outcome of executing a single stage: status + any artifact IDs produced.

WorkflowEngine
    Parses a workflow.yaml string, resolves execution order via
    stdlib `graphlib.TopologicalSorter`, emits Events for every
    stage transition, and drives a stage callback provided by the caller.
"""

import uuid
import datetime
from graphlib import TopologicalSorter, CycleError  # stdlib Python 3.9+
from typing import Any, Callable, Coroutine, Dict, List, Optional

try:
    import yaml
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False

from platform_core.core.environment.base import Environment
from platform_core.core.events.base import Event, EventManager


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

class WorkflowStage:
    """Represents one stage in a declarative workflow."""

    def __init__(
        self,
        id: str,
        name: str,
        agent: str,
        depends_on: Optional[List[str]] = None,
        inputs: Optional[Dict[str, Any]] = None,
        outputs: Optional[List[str]] = None,
        description: str = "",
        status: str = "PENDING",
    ):
        self.id = id
        self.name = name
        self.agent = agent
        self.depends_on: List[str] = depends_on or []
        self.inputs: Dict[str, Any] = inputs or {}
        self.outputs: List[str] = outputs or []
        self.description = description
        self.status = status  # PENDING | RUNNING | COMPLETED | FAILED | SKIPPED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "agent": self.agent,
            "depends_on": self.depends_on,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "description": self.description,
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WorkflowStage":
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data.get("name", ""),
            agent=data.get("agent", ""),
            depends_on=data.get("depends_on") or [],
            inputs=data.get("inputs") or {},
            outputs=data.get("outputs") or [],
            description=data.get("description", ""),
            status=data.get("status", "PENDING"),
        )


class WorkflowResult:
    """Outcome of a single stage execution."""

    def __init__(
        self,
        stage_id: str,
        status: str,
        artifact_ids: Optional[List[str]] = None,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.stage_id = stage_id
        self.status = status          # COMPLETED | FAILED | SKIPPED
        self.artifact_ids: List[str] = artifact_ids or []
        self.error = error
        self.metadata: Dict[str, Any] = metadata or {}
        self.finished_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "status": self.status,
            "artifact_ids": self.artifact_ids,
            "error": self.error,
            "metadata": self.metadata,
            "finished_at": self.finished_at,
        }


# ---------------------------------------------------------------------------
# Workflow Engine
# ---------------------------------------------------------------------------

# Type alias: an async function that receives (stage, context) and returns WorkflowResult
StageRunner = Callable[["WorkflowStage", Dict[str, Any]], Coroutine[Any, Any, WorkflowResult]]


class WorkflowEngine:
    """
    Parses and drives a declarative pipeline defined in workflow.yaml format.

    Usage
    -----
    engine = WorkflowEngine(env=env, event_mgr=event_mgr)
    stages = engine.load_from_yaml(yaml_string)
    order  = engine.get_execution_order(stages)
    results = await engine.run(yaml_string, project_id="proj_abc", runner=my_runner, context={})
    """

    def __init__(self, env: Environment, event_mgr: Optional[EventManager] = None):
        self.env = env
        self.event_mgr = event_mgr

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def load_from_yaml(self, yaml_content: str) -> List[WorkflowStage]:
        """
        Parse a YAML string into a list of WorkflowStage objects.

        Supports both dict-of-stages and list-of-stages formats:

        Dict format (preferred):
            stages:
              pm_planning:
                name: PM Planning
                agent: ProductManager
                depends_on: []
                ...

        List format:
            stages:
              - id: pm_planning
                name: PM Planning
                ...
        """
        if not _YAML_AVAILABLE:
            raise ImportError(
                "PyYAML is required for WorkflowEngine.load_from_yaml(). "
                "Install it with: pip install pyyaml"
            )

        data = yaml.safe_load(yaml_content) or {}
        raw_stages = data.get("stages", {})

        stages: List[WorkflowStage] = []

        if isinstance(raw_stages, dict):
            for stage_id, stage_data in raw_stages.items():
                if not isinstance(stage_data, dict):
                    continue
                stage_data = dict(stage_data)
                stage_data.setdefault("id", stage_id)
                stages.append(WorkflowStage.from_dict(stage_data))

        elif isinstance(raw_stages, list):
            for item in raw_stages:
                if isinstance(item, dict):
                    stages.append(WorkflowStage.from_dict(item))

        return stages

    def load_from_dict(self, stages_list: List[Dict[str, Any]]) -> List[WorkflowStage]:
        """Parse from a plain list of dicts (e.g. already-parsed JSON)."""
        return [WorkflowStage.from_dict(s) for s in stages_list]

    # ------------------------------------------------------------------
    # Topological ordering
    # ------------------------------------------------------------------

    def get_execution_order(self, stages: List[WorkflowStage]) -> List[WorkflowStage]:
        """
        Return stages sorted so every stage appears after all its dependencies.

        Raises
        ------
        graphlib.CycleError
            If the dependency graph contains a cycle.
        KeyError
            If a stage references a non-existent dependency id.
        """
        stage_map: Dict[str, WorkflowStage] = {s.id: s for s in stages}

        # Validate all referenced deps exist
        for stage in stages:
            for dep_id in stage.depends_on:
                if dep_id not in stage_map:
                    raise KeyError(
                        f"Stage '{stage.id}' depends on unknown stage '{dep_id}'"
                    )

        # Build graph: {node: set_of_predecessors}
        graph: Dict[str, set] = {s.id: set(s.depends_on) for s in stages}
        sorter = TopologicalSorter(graph)
        ordered_ids = list(sorter.static_order())  # raises CycleError if cyclic

        return [stage_map[sid] for sid in ordered_ids if sid in stage_map]

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def _emit(self, event_type: str, producer: str, project_id: Optional[str], payload: Dict):
        if self.event_mgr:
            self.event_mgr.emit_event(Event(
                event_type=event_type,
                producer=producer,
                project_id=project_id,
                payload=payload,
            ))

    async def run(
        self,
        yaml_content: str,
        runner: StageRunner,
        project_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[WorkflowResult]:
        """
        Full pipeline execution.

        Parameters
        ----------
        yaml_content : str
            The workflow.yaml content string.
        runner : StageRunner
            An async callable(stage, context) → WorkflowResult provided by
            the application layer (e.g. AgentCoordinator).
        project_id : str, optional
            Used for event correlation.
        context : dict, optional
            Shared mutable context passed to every stage runner.

        Returns
        -------
        List[WorkflowResult]
            One result per executed stage, in execution order.
        """
        context = context or {}
        stages = self.load_from_yaml(yaml_content)
        ordered = self.get_execution_order(stages)

        self._emit(
            "WORKFLOW_STARTED",
            "WorkflowEngine",
            project_id,
            {"stage_count": len(ordered), "stages": [s.id for s in ordered]},
        )

        results: List[WorkflowResult] = []
        failed_stages: set = set()
        skipped_stages: set = set()

        for stage in ordered:
            # Skip if any dependency failed OR was already skipped
            if any(dep in failed_stages or dep in skipped_stages for dep in stage.depends_on):
                stage.status = "SKIPPED"
                result = WorkflowResult(
                    stage_id=stage.id,
                    status="SKIPPED",
                    error=f"Skipped because a dependency failed: {stage.depends_on}",
                )
                skipped_stages.add(stage.id)
                results.append(result)
                self._emit(
                    "STAGE_SKIPPED",
                    "WorkflowEngine",
                    project_id,
                    {"stage_id": stage.id, "reason": result.error},
                )
                continue

            stage.status = "RUNNING"
            self._emit(
                "STAGE_STARTED",
                stage.agent,
                project_id,
                {"stage_id": stage.id, "agent": stage.agent},
            )

            try:
                result = await runner(stage, context)
                stage.status = result.status

                if result.status == "FAILED":
                    failed_stages.add(stage.id)
                    self._emit(
                        "STAGE_FAILED",
                        stage.agent,
                        project_id,
                        {"stage_id": stage.id, "error": result.error},
                    )
                else:
                    self._emit(
                        "STAGE_COMPLETED",
                        stage.agent,
                        project_id,
                        {
                            "stage_id": stage.id,
                            "artifact_ids": result.artifact_ids,
                        },
                    )
            except Exception as exc:
                stage.status = "FAILED"
                failed_stages.add(stage.id)
                result = WorkflowResult(
                    stage_id=stage.id,
                    status="FAILED",
                    error=str(exc),
                )
                self._emit(
                    "STAGE_FAILED",
                    stage.agent,
                    project_id,
                    {"stage_id": stage.id, "error": str(exc)},
                )

            results.append(result)

        final_status = "COMPLETED" if not failed_stages else "PARTIALLY_FAILED"
        self._emit(
            "WORKFLOW_FINISHED",
            "WorkflowEngine",
            project_id,
            {
                "status": final_status,
                "completed": [r.stage_id for r in results if r.status == "COMPLETED"],
                "failed": list(failed_stages),
                "skipped": [r.stage_id for r in results if r.status == "SKIPPED"],
            },
        )

        return results
