import os
import json
import tempfile
import shutil
import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db.database import Base
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
    assert len(events) == 3
    assert any(evt.type == "PROJECT_INITIATED" for evt in events)
    assert any(evt.type == "SPECIFICATION_GENERATED" for evt in events)
    assert any(evt.type == "ARCHITECTURE_DEFINED" for evt in events)
