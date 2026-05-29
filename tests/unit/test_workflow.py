"""
Unit tests for platform_core.core.workflow
"""
import asyncio
import pytest
from graphlib import CycleError
from platform_core.core.workflow.base import WorkflowEngine, WorkflowStage, WorkflowResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_engine() -> WorkflowEngine:
    """Return a WorkflowEngine with no env / event_mgr (not needed for parse/order tests)."""
    return WorkflowEngine(env=None, event_mgr=None)


SIMPLE_YAML = """
stages:
  pm_planning:
    name: PM Planning
    agent: ProductManager
    depends_on: []
    description: Create specs

  architecture:
    name: Architecture Design
    agent: ArchitectAgent
    depends_on: [pm_planning]
    description: Design system

  frontend:
    name: Frontend Generation
    agent: CoderAgent
    depends_on: [architecture]

  backend:
    name: Backend Generation
    agent: BackendAgent
    depends_on: [architecture]

  qa_testing:
    name: QA Testing
    agent: QAAgent
    depends_on: [frontend, backend]
"""

CYCLIC_YAML = """
stages:
  a:
    name: Stage A
    agent: AgentA
    depends_on: [b]
  b:
    name: Stage B
    agent: AgentB
    depends_on: [a]
"""

MISSING_DEP_YAML = """
stages:
  only_stage:
    name: Only Stage
    agent: SomeAgent
    depends_on: [nonexistent_stage]
"""


# ---------------------------------------------------------------------------
# Parse tests
# ---------------------------------------------------------------------------

def test_workflow_parse_yaml_stages_count():
    """WorkflowEngine should parse 5 stages from SIMPLE_YAML."""
    engine = make_engine()
    stages = engine.load_from_yaml(SIMPLE_YAML)
    assert len(stages) == 5


def test_workflow_parse_yaml_stage_fields():
    """Parsed stages should have correct id, agent, and depends_on."""
    engine = make_engine()
    stages = engine.load_from_yaml(SIMPLE_YAML)
    stage_map = {s.id: s for s in stages}

    assert "pm_planning" in stage_map
    assert stage_map["pm_planning"].agent == "ProductManager"
    assert stage_map["pm_planning"].depends_on == []

    assert "architecture" in stage_map
    assert stage_map["architecture"].depends_on == ["pm_planning"]

    assert "qa_testing" in stage_map
    assert set(stage_map["qa_testing"].depends_on) == {"frontend", "backend"}


def test_workflow_parse_list_format():
    """WorkflowEngine should also parse the list-of-stages YAML format."""
    list_yaml = """
stages:
  - id: step_a
    name: Step A
    agent: AgentA
    depends_on: []
  - id: step_b
    name: Step B
    agent: AgentB
    depends_on: [step_a]
"""
    engine = make_engine()
    stages = engine.load_from_yaml(list_yaml)
    assert len(stages) == 2
    assert stages[0].id == "step_a"
    assert stages[1].id == "step_b"


# ---------------------------------------------------------------------------
# Topological order tests
# ---------------------------------------------------------------------------

def test_workflow_execution_order_respects_deps():
    """Topological order: pm_planning must precede architecture, architecture before frontend/backend."""
    engine = make_engine()
    stages = engine.load_from_yaml(SIMPLE_YAML)
    ordered = engine.get_execution_order(stages)
    ids = [s.id for s in ordered]

    assert ids.index("pm_planning") < ids.index("architecture")
    assert ids.index("architecture") < ids.index("frontend")
    assert ids.index("architecture") < ids.index("backend")
    assert ids.index("frontend") < ids.index("qa_testing")
    assert ids.index("backend") < ids.index("qa_testing")


def test_workflow_cyclic_detection():
    """CycleError is raised when the dependency graph has a cycle."""
    engine = make_engine()
    stages = engine.load_from_yaml(CYCLIC_YAML)
    with pytest.raises(CycleError):
        engine.get_execution_order(stages)


def test_workflow_missing_dependency_raises():
    """KeyError is raised when a stage depends on a non-existent stage id."""
    engine = make_engine()
    stages = engine.load_from_yaml(MISSING_DEP_YAML)
    with pytest.raises(KeyError, match="nonexistent_stage"):
        engine.get_execution_order(stages)


# ---------------------------------------------------------------------------
# Run / execution tests (async)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_workflow_run_all_pass():
    """All stages complete successfully when runner always returns COMPLETED."""
    engine = make_engine()

    async def always_pass(stage: WorkflowStage, ctx: dict) -> WorkflowResult:
        return WorkflowResult(stage_id=stage.id, status="COMPLETED", artifact_ids=["art_fake"])

    results = await engine.run(SIMPLE_YAML, runner=always_pass, project_id="test_proj")
    assert len(results) == 5
    assert all(r.status == "COMPLETED" for r in results)


@pytest.mark.asyncio
async def test_workflow_run_skip_on_failure():
    """If 'architecture' fails, stages that depend on it are SKIPPED."""
    engine = make_engine()

    async def sometimes_fail(stage: WorkflowStage, ctx: dict) -> WorkflowResult:
        if stage.id == "architecture":
            return WorkflowResult(stage_id=stage.id, status="FAILED", error="Simulated failure")
        return WorkflowResult(stage_id=stage.id, status="COMPLETED")

    results = await engine.run(SIMPLE_YAML, runner=sometimes_fail, project_id="test_proj")

    result_map = {r.stage_id: r for r in results}
    assert result_map["architecture"].status == "FAILED"
    assert result_map["frontend"].status == "SKIPPED"
    assert result_map["backend"].status == "SKIPPED"
    assert result_map["qa_testing"].status == "SKIPPED"
    # pm_planning ran before failure
    assert result_map["pm_planning"].status == "COMPLETED"


@pytest.mark.asyncio
async def test_workflow_result_structure():
    """WorkflowResult has expected fields."""
    result = WorkflowResult(
        stage_id="my_stage",
        status="COMPLETED",
        artifact_ids=["art_001", "art_002"],
        metadata={"extra": "data"},
    )
    d = result.to_dict()
    assert d["stage_id"] == "my_stage"
    assert d["status"] == "COMPLETED"
    assert "art_001" in d["artifact_ids"]
    assert d["metadata"]["extra"] == "data"
    assert "finished_at" in d
