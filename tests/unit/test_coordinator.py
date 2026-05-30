import os
import json
import tempfile
import shutil
import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.database import Base
from app.db.models import Project, BuildTask
from platform_core.core.environment.local import LocalEnvironment
from app.agents.coordinator import AgentCoordinator

# Setup temporary SQLite database for coordinator tests
TEST_DB_FILE = "./test_coordinator.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{TEST_DB_FILE}"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture
def temp_workspace():
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture(autouse=True)
def setup_test_db():
    # Create tables in the testing database
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    # Cleanup database file
    Base.metadata.drop_all(bind=engine)
    if os.path.exists(TEST_DB_FILE):
        try:
            os.remove(TEST_DB_FILE)
        except Exception:
            pass

@pytest.mark.asyncio
@patch('app.agents.personas.PMAgent.call_llm', new_callable=AsyncMock)
@patch('app.agents.personas.ArchitectAgent.call_llm', new_callable=AsyncMock)
async def test_coordinator_init_project(mock_arch_call, mock_pm_call, temp_workspace):
    env = LocalEnvironment(workspace_path=temp_workspace)
    coordinator = AgentCoordinator(env=env)
    
    # Override get_db_session to use the test database
    coordinator.get_db_session = lambda: TestingSessionLocal()

    # Setup mock PM LLM response
    mock_pm_call.return_value = json.dumps({
        "theme": "Dark Theme",
        "project_md": "# Product Specification",
        "roadmap_md": "# Roadmap steps",
        "state_md": "# Project State",
        "design_md": "colors: HSL variables"
    })

    # Setup mock Architect LLM response including workflow_yaml
    mock_arch_call.return_value = json.dumps({
        "architecture_md": "# System Components",
        "db_schema_sql": "CREATE TABLE users (id INT PRIMARY KEY);",
        "api_spec_yaml": "openapi: 3.0.0",
        "workflow_yaml": "workflow:\n  stages:\n    - backend\n    - frontend"
    })

    # Run target initialization
    project_id = await coordinator.init_project(name="E-Commerce Sandbox", concept="An online catalog app")

    assert project_id is not None
    assert env.exists("PROJECT.md")
    assert env.exists("ROADMAP.md")
    assert env.exists("STATE.md")
    assert env.exists("DESIGN.md")
    assert env.exists("architecture.md")
    assert env.exists("db_schema.sql")
    assert env.exists("api_spec.yaml")
    assert env.exists("workflow.yaml")

    # Verify Artifact storage and schemas
    artifacts = coordinator.artifact_mgr.list_artifacts()
    assert len(artifacts) == 2
    spec_art = next(art for art in artifacts if art.type == "spec")
    arch_art = next(art for art in artifacts if art.type == "architecture")

    assert spec_art.producer == "ProductManager"
    assert spec_art.project_id == project_id
    assert spec_art.content["project_md"] == "# Product Specification"
    
    assert arch_art.producer == "Architect"
    assert arch_art.project_id == project_id
    assert arch_art.parent_artifact == spec_art.id
    assert arch_art.content["db_schema_sql"] == "CREATE TABLE users (id INT PRIMARY KEY);"
    assert "workflow:\n  stages:" in arch_art.content["workflow_yaml"]

    # Verify Decision logging and artifact links
    decisions = coordinator.decision_mgr.list_decisions()
    assert len(decisions) == 2
    
    pm_dec = next(dec for dec in decisions if dec.agent == "ProductManager")
    arch_dec = next(dec for dec in decisions if dec.agent == "Architect")
    
    assert pm_dec.artifact_id == spec_art.id
    assert arch_dec.artifact_id == arch_art.id

    # Verify Event Store records
    events = coordinator.event_mgr.list_events(project_id=project_id)
    assert any(evt.type == "PROJECT_INITIATED" for evt in events)
    assert any(evt.type == "SPECIFICATION_GENERATED" for evt in events)
    assert any(evt.type == "ARCHITECTURE_DEFINED" for evt in events)
    assert any(evt.type == "STATE_TRANSITIONED" for evt in events)


@pytest.mark.asyncio
@patch('platform_core.core.llm.client.LLMClient.call_llm', new_callable=AsyncMock)
@patch('app.agents.personas.DesignerAgent.call_llm', new_callable=AsyncMock)
@patch('app.agents.personas.CoderAgent.call_llm', new_callable=AsyncMock)
@patch('app.agents.personas.CSSAgent.call_llm', new_callable=AsyncMock)
@patch('app.agents.personas.BackendAgent.call_llm', new_callable=AsyncMock)
@patch('app.agents.coordinator.AgentCoordinator.run_playwright_test', new_callable=AsyncMock)
@patch('app.agents.coordinator.AgentCoordinator.run_strix_security_scan', new_callable=AsyncMock)
async def test_coordinator_build_project_workflow(
    mock_scan, mock_pw, mock_backend, mock_css, mock_coder, mock_designer, mock_llm_call, temp_workspace
):
    env = LocalEnvironment(workspace_path=temp_workspace)
    coordinator = AgentCoordinator(env=env)
    
    # Override get_db_session to use the test database
    coordinator.get_db_session = lambda: TestingSessionLocal()

    # Create dummy project in test DB
    project_id = "test_build_proj"
    db = TestingSessionLocal()
    db.add(Project(
        id=project_id,
        name="Test Project",
        concept="Test Concept",
        status="PLANNING",
        workspace_path=temp_workspace
    ))
    db.commit()
    db.close()

    # Setup side-effect for generic LLMClient calls in tools
    async def mock_llm_side_effect(prompt, *args, **kwargs):
        if "html" in prompt.lower() or "html5" in prompt.lower():
            return "<html></html>"
        elif "express" in prompt.lower() or "mongoose" in prompt.lower() or "backend" in prompt.lower():
            return json.dumps([{"file": "server.js", "content": "console.log('hello');"}])
        elif "css" in prompt.lower():
            return "/* CSS */"
        return "mock response"
    mock_llm_call.side_effect = mock_llm_side_effect

    # Mock agent responses in case tools fallback
    mock_designer.return_value = "/* CSS */"
    mock_coder.return_value = "<html></html>"
    mock_css.return_value = "/* Upgraded CSS */"
    mock_backend.return_value = json.dumps([{"file": "server.js", "content": "console.log('hello');"}])

    # Run build
    await coordinator.build_project(project_id)

    # Assertions
    assert env.exists("index.css")
    assert env.exists("index.html")
    assert env.exists("server.js")
    mock_pw.assert_called_once()
    mock_scan.assert_called_once()

    db = TestingSessionLocal()
    project = db.query(Project).filter(Project.id == project_id).first()
    assert project.status == "PASSED"
    db.close()
