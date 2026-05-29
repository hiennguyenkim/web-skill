"""
Unit tests for platform_core.core.registry
"""
import pytest
from platform_core.core.registry.base import CapabilityRegistry, CapabilityDescriptor


# ---------------------------------------------------------------------------
# Basic CRUD
# ---------------------------------------------------------------------------

def test_registry_register_and_get():
    """A freshly-registered capability should be retrievable by its id."""
    registry = CapabilityRegistry(load_defaults=False)
    cap = CapabilityDescriptor(
        id="test_capability",
        name="Test Capability",
        description="A test cap",
        agent_type="TestAgent",
        tags=["test"],
    )
    registry.register(cap)
    result = registry.get("test_capability")
    assert result is not None
    assert result.id == "test_capability"
    assert result.agent_type == "TestAgent"


def test_registry_get_missing_returns_none():
    """Getting a non-existent capability should return None."""
    registry = CapabilityRegistry(load_defaults=False)
    assert registry.get("does_not_exist") is None


def test_registry_overwrite_on_re_register():
    """Re-registering the same id should overwrite the old descriptor."""
    registry = CapabilityRegistry(load_defaults=False)
    registry.register(CapabilityDescriptor(
        id="cap_x", name="Old", description="old", agent_type="OldAgent",
    ))
    registry.register(CapabilityDescriptor(
        id="cap_x", name="New", description="new", agent_type="NewAgent",
    ))
    result = registry.get("cap_x")
    assert result.agent_type == "NewAgent"
    assert result.name == "New"


def test_registry_unregister():
    """Unregistering should remove the capability."""
    registry = CapabilityRegistry(load_defaults=False)
    registry.register(CapabilityDescriptor(
        id="ephemeral", name="Ephemeral", description="", agent_type="Tmp"
    ))
    assert "ephemeral" in registry
    removed = registry.unregister("ephemeral")
    assert removed is True
    assert registry.get("ephemeral") is None


def test_registry_unregister_nonexistent():
    """Unregistering a non-existent id should return False."""
    registry = CapabilityRegistry(load_defaults=False)
    assert registry.unregister("ghost") is False


# ---------------------------------------------------------------------------
# List / filter
# ---------------------------------------------------------------------------

def test_registry_list_by_tag():
    """list_by_tag should return only capabilities whose tags include the given tag."""
    registry = CapabilityRegistry(load_defaults=False)
    registry.register(CapabilityDescriptor(
        id="cap_a", name="A", description="", agent_type="AgentA", tags=["frontend", "html"]
    ))
    registry.register(CapabilityDescriptor(
        id="cap_b", name="B", description="", agent_type="AgentB", tags=["backend"]
    ))
    registry.register(CapabilityDescriptor(
        id="cap_c", name="C", description="", agent_type="AgentC", tags=["frontend", "css"]
    ))
    frontend_caps = registry.list_by_tag("frontend")
    ids = {c.id for c in frontend_caps}
    assert "cap_a" in ids
    assert "cap_c" in ids
    assert "cap_b" not in ids


def test_registry_list_by_agent():
    """list_by_agent should return capabilities for the specified agent_type."""
    registry = CapabilityRegistry(load_defaults=False)
    registry.register(CapabilityDescriptor(
        id="cap_1", name="1", description="", agent_type="CoderAgent"
    ))
    registry.register(CapabilityDescriptor(
        id="cap_2", name="2", description="", agent_type="QAAgent"
    ))
    registry.register(CapabilityDescriptor(
        id="cap_3", name="3", description="", agent_type="CoderAgent"
    ))
    coder_caps = registry.list_by_agent("CoderAgent")
    assert len(coder_caps) == 2
    assert all(c.agent_type == "CoderAgent" for c in coder_caps)


def test_registry_list_all():
    """list_all should return every registered capability."""
    registry = CapabilityRegistry(load_defaults=False)
    for i in range(5):
        registry.register(CapabilityDescriptor(
            id=f"cap_{i}", name=str(i), description="", agent_type="Agent"
        ))
    assert len(registry.list_all()) == 5


# ---------------------------------------------------------------------------
# Default web_creator capabilities
# ---------------------------------------------------------------------------

def test_registry_defaults_loaded():
    """Default registry should have the 10 pre-registered web_creator capabilities."""
    registry = CapabilityRegistry(load_defaults=True)
    assert len(registry) >= 10


def test_registry_default_capability_ids():
    """All expected web_creator capability IDs should be present by default."""
    registry = CapabilityRegistry(load_defaults=True)
    expected_ids = [
        "product_planning",
        "architecture_design",
        "ui_design_tokens",
        "frontend_generation",
        "css_styling",
        "backend_generation",
        "qa_testing",
        "security_scanning",
        "self_healing",
        "po_user_stories",
    ]
    for cap_id in expected_ids:
        assert cap_id in registry, f"Missing default capability: {cap_id}"


def test_registry_default_frontend_generation():
    """frontend_generation capability should map to CoderAgent with tool=html_coder."""
    registry = CapabilityRegistry(load_defaults=True)
    cap = registry.get("frontend_generation")
    assert cap is not None
    assert cap.agent_type == "CoderAgent"
    assert cap.tool == "html_coder"
    assert "frontend" in cap.tags


def test_registry_default_qa_has_playwright_tag():
    """qa_testing capability should have the 'playwright' tag."""
    registry = CapabilityRegistry(load_defaults=True)
    cap = registry.get("qa_testing")
    assert cap is not None
    assert "playwright" in cap.tags


def test_registry_descriptor_to_dict():
    """CapabilityDescriptor.to_dict() should contain all expected keys."""
    cap = CapabilityDescriptor(
        id="my_cap",
        name="My Cap",
        description="A test",
        agent_type="MyAgent",
        tool="my_tool",
        tags=["t1", "t2"],
        metadata={"version": "1"},
    )
    d = cap.to_dict()
    assert d["id"] == "my_cap"
    assert d["agent_type"] == "MyAgent"
    assert d["tool"] == "my_tool"
    assert "t1" in d["tags"]
    assert d["metadata"]["version"] == "1"
