"""
tests/unit/test_artifact_types.py
Tests for upgraded Artifact model: Enums, content_hash, backward compat.
"""

import json
import pytest

from platform_core.core.artifacts.base import (
    Artifact,
    ArtifactType,
    ArtifactFormat,
    ArtifactStatus,
)


# ---------------------------------------------------------------------------
# Test: ArtifactType Enum
# ---------------------------------------------------------------------------

def test_artifact_type_values():
    assert ArtifactType.SPECIFICATION == "specification"
    assert ArtifactType.CODE == "code"
    assert ArtifactType.ARCHITECTURE == "architecture"
    assert ArtifactType.SECURITY_REPORT == "security_report"


def test_artifact_type_is_str():
    """Enum values must be strings so existing string comparisons still work."""
    assert isinstance(ArtifactType.SPECIFICATION, str)
    assert ArtifactType.CODE == "code"   # direct str comparison


def test_artifact_format_values():
    assert ArtifactFormat.MARKDOWN == "markdown"
    assert ArtifactFormat.JSON == "json"
    assert ArtifactFormat.HTML == "html"
    assert ArtifactFormat.MIXED == "mixed"


def test_artifact_status_values():
    assert ArtifactStatus.COMPLETED == "COMPLETED"
    assert ArtifactStatus.FAILED == "FAILED"
    assert ArtifactStatus.PENDING == "PENDING"
    assert ArtifactStatus.SUPERSEDED == "SUPERSEDED"


# ---------------------------------------------------------------------------
# Test: content_hash property
# ---------------------------------------------------------------------------

def test_content_hash_string():
    art = Artifact(
        artifact_type=ArtifactType.SPECIFICATION,
        producer="PMAgent",
        content="# Hello World",
    )
    assert art.content_hash  # not empty
    assert len(art.content_hash) == 12  # first 12 hex chars of SHA-256


def test_content_hash_deterministic():
    """Same content must always produce same hash."""
    art1 = Artifact(
        artifact_type=ArtifactType.CODE,
        producer="CoderAgent",
        content="<html><body>Hello</body></html>",
    )
    art2 = Artifact(
        artifact_type=ArtifactType.CODE,
        producer="CoderAgent",
        content="<html><body>Hello</body></html>",
    )
    assert art1.content_hash == art2.content_hash


def test_content_hash_different_content():
    art1 = Artifact(artifact_type="code", producer="coder", content="AAA")
    art2 = Artifact(artifact_type="code", producer="coder", content="BBB")
    assert art1.content_hash != art2.content_hash


def test_content_hash_dict_content():
    """content_hash works for dict/list content (JSON-serialised)."""
    art = Artifact(
        artifact_type=ArtifactType.ARCHITECTURE,
        producer="ArchitectAgent",
        content={"files": ["server.js", "models/User.js"], "db": "mongodb"},
    )
    assert art.content_hash
    assert len(art.content_hash) == 12


def test_content_hash_in_to_dict():
    """content_hash should appear in serialised form."""
    art = Artifact(artifact_type="code", producer="coder", content="hello")
    d = art.to_dict()
    assert "content_hash" in d
    assert d["content_hash"] == art.content_hash


# ---------------------------------------------------------------------------
# Test: format field
# ---------------------------------------------------------------------------

def test_format_defaults_to_mixed():
    art = Artifact(artifact_type="code", producer="agent", content="x")
    assert art.format == ArtifactFormat.MIXED


def test_format_set_explicitly():
    art = Artifact(
        artifact_type=ArtifactType.SPECIFICATION,
        producer="PMAgent",
        content="# Spec",
        format=ArtifactFormat.MARKDOWN,
    )
    assert art.format == ArtifactFormat.MARKDOWN
    assert art.format == "markdown"  # str compat


# ---------------------------------------------------------------------------
# Test: backward compatibility — plain strings still work
# ---------------------------------------------------------------------------

def test_backward_compat_plain_string_type():
    """Old code passing string artifact_type must still work."""
    art = Artifact(artifact_type="code", producer="agent", content="x")
    assert art.type == "code"


def test_backward_compat_plain_string_status():
    art = Artifact(artifact_type="code", producer="agent", content="x", status="COMPLETED")
    assert art.status == "COMPLETED"


# ---------------------------------------------------------------------------
# Test: round-trip to_dict / from_dict
# ---------------------------------------------------------------------------

def test_roundtrip_with_enums():
    art = Artifact(
        artifact_type=ArtifactType.CODE,
        format=ArtifactFormat.HTML,
        producer="CoderAgent",
        content="<html/>",
        status=ArtifactStatus.COMPLETED,
        project_id="proj_001",
        metadata={"phase": "frontend"},
    )
    d = art.to_dict()
    restored = Artifact.from_dict(d)

    assert restored.id == art.id
    assert restored.type == "code"
    assert restored.format == "html"
    assert restored.producer == "CoderAgent"
    assert restored.content == "<html/>"
    assert restored.project_id == "proj_001"
    assert restored.metadata["phase"] == "frontend"


# ---------------------------------------------------------------------------
# Test: timezone-aware timestamps
# ---------------------------------------------------------------------------

def test_created_at_is_set():
    art = Artifact(artifact_type="code", producer="agent", content="x")
    assert art.created_at  # not empty/None
    # Should be ISO format with timezone (+00:00 or Z)
    assert "+" in art.created_at or art.created_at.endswith("Z")


# ---------------------------------------------------------------------------
# Test: ArtifactManager with new fields persists correctly
# ---------------------------------------------------------------------------

def test_artifact_manager_roundtrip(tmp_path):
    from platform_core.core.environment.local import LocalEnvironment
    from platform_core.core.artifacts.base import ArtifactManager

    env = LocalEnvironment(str(tmp_path))
    mgr = ArtifactManager(env)

    art = Artifact(
        artifact_type=ArtifactType.SPECIFICATION,
        format=ArtifactFormat.MARKDOWN,
        producer="PMAgent",
        content="# My Project Spec",
        project_id="proj_test",
    )
    mgr.save_artifact(art)

    retrieved = mgr.get_artifact(art.id)
    assert retrieved is not None
    assert retrieved.type == ArtifactType.SPECIFICATION
    assert retrieved.content == "# My Project Spec"
