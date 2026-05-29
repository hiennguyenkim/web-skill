import os
import json
import tempfile
import shutil
import pytest
from platform_core.core.environment.local import LocalEnvironment
from platform_core.core.artifacts.base import Artifact, ArtifactManager
from platform_core.core.decisions.base import Decision, DecisionManager
from platform_core.core.events.base import Event, EventManager

@pytest.fixture
def temp_workspace():
    # Setup temporary directory for sandbox
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup after test
    shutil.rmtree(temp_dir)

def test_artifact_manager(temp_workspace):
    env = LocalEnvironment(workspace_path=temp_workspace)
    manager = ArtifactManager(env=env)

    # 1. Create and save artifact with new schema fields
    artifact = Artifact(
        artifact_type="spec",
        producer="ProductManager",
        content={"title": "Test Web App", "steps": 5},
        project_id="proj_123",
        version="2.1.0",
        parent_artifact="art_parent",
        status="APPROVED",
        metadata={"theme": "Dark HSL"}
    )
    
    assert artifact.id is not None
    manager.save_artifact(artifact)

    # Verify files created in temp_workspace
    art_file = f"artifacts/{artifact.id}.json"
    manifest_file = "artifacts/manifest.json"

    assert env.exists(art_file)
    assert env.exists(manifest_file)

    # 2. Get artifact
    retrieved = manager.get_artifact(artifact.id)
    assert retrieved is not None
    assert retrieved.id == artifact.id
    assert retrieved.type == "spec"
    assert retrieved.producer == "ProductManager"
    assert retrieved.project_id == "proj_123"
    assert retrieved.version == "2.1.0"
    assert retrieved.parent_artifact == "art_parent"
    assert retrieved.status == "APPROVED"
    assert retrieved.content["title"] == "Test Web App"

    # 3. List artifacts
    all_arts = manager.list_artifacts()
    assert len(all_arts) == 1
    assert all_arts[0].id == artifact.id

def test_decision_manager(temp_workspace):
    env = LocalEnvironment(workspace_path=temp_workspace)
    manager = DecisionManager(env=env)

    # 1. Log a decision with artifact link
    decision = Decision(
        decision="Use SQLite",
        reason="Lightweight and local storage needs",
        agent="Architect",
        artifact_id="art_xyz",
        context={"db_path": "test.db"}
    )
    
    assert decision.id is not None
    manager.log_decision(decision)

    # Verify files created in temp_workspace
    dec_file = f"decisions/{decision.id}.json"
    manifest_file = "decisions/manifest.json"

    assert env.exists(dec_file)
    assert env.exists(manifest_file)

    # 2. List decisions
    all_decs = manager.list_decisions()
    assert len(all_decs) == 1
    assert all_decs[0].id == decision.id
    assert all_decs[0].decision == "Use SQLite"
    assert all_decs[0].artifact_id == "art_xyz"

def test_event_manager(temp_workspace):
    env = LocalEnvironment(workspace_path=temp_workspace)
    manager = EventManager(env=env)

    # 1. Emit an event
    event = Event(
        event_type="SPECIFICATION_GENERATED",
        producer="ProductManager",
        project_id="proj_789",
        payload={"artifact_id": "art_spec_1"}
    )
    
    assert event.id is not None
    manager.emit_event(event)

    # Verify files created
    evt_file = f"events/{event.id}.json"
    manifest_file = "events/manifest.json"

    assert env.exists(evt_file)
    assert env.exists(manifest_file)

    # 2. List events
    all_evts = manager.list_events()
    assert len(all_evts) == 1
    assert all_evts[0].id == event.id
    assert all_evts[0].type == "SPECIFICATION_GENERATED"
    assert all_evts[0].project_id == "proj_789"
    assert all_evts[0].payload["artifact_id"] == "art_spec_1"

    # 3. Filtered list events
    filtered = manager.list_events(project_id="proj_789")
    assert len(filtered) == 1

    empty_filtered = manager.list_events(project_id="proj_other")
    assert len(empty_filtered) == 0
