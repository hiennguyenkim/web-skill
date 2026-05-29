import datetime
import hashlib
import json
import uuid
from enum import Enum
from typing import Any, Dict, List, Optional

from platform_core.core.environment.base import Environment


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class ArtifactType(str, Enum):
    """Semantic category of an artifact produced by the platform."""
    SPECIFICATION  = "specification"   # PRD, PROJECT.md, DESIGN.md
    ARCHITECTURE   = "architecture"    # architecture.md, db_schema.sql, api_spec.yaml
    WORKFLOW       = "workflow"        # workflow.yaml
    DESIGN         = "design"          # CSS tokens, design systems
    CODE           = "code"            # HTML, JS, backend files
    TEST           = "test"            # Playwright results, QA reports
    SECURITY_REPORT = "security_report" # SAST scan results
    PATCH          = "patch"           # Self-healing diffs
    EVALUATION     = "evaluation"      # Benchmark scoring results


class ArtifactFormat(str, Enum):
    """Wire format / file type of the artifact content."""
    MARKDOWN   = "markdown"
    JSON       = "json"
    YAML       = "yaml"
    HTML       = "html"
    CSS        = "css"
    JAVASCRIPT = "javascript"
    PYTHON     = "python"
    SQL        = "sql"
    TEXT       = "text"
    MIXED      = "mixed"    # dict/list of multiple file contents


class ArtifactStatus(str, Enum):
    """Lifecycle status of an artifact."""
    PENDING    = "PENDING"
    COMPLETED  = "COMPLETED"
    FAILED     = "FAILED"
    SUPERSEDED = "SUPERSEDED"

class Artifact:
    """
    Represents any output produced by a platform agent or skill.

    ``artifact_type`` and ``status`` accept both typed Enum values and plain
    strings for backward compatibility (Enum inherits from str).
    """

    def __init__(
        self,
        artifact_type: str,          # ArtifactType Enum value or plain string
        producer: str,
        content: Any,                # str | dict | list — flexible
        id: Optional[str] = None,
        project_id: Optional[str] = None,
        version: str = "1.0.0",
        parent_artifact: Optional[str] = None,
        status: str = ArtifactStatus.COMPLETED,
        format: Optional[str] = None,  # ArtifactFormat Enum value or plain string
        created_at: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.id = id or f"art_{str(uuid.uuid4())[:8]}"
        self.type = artifact_type
        self.format = format or ArtifactFormat.MIXED
        self.producer = producer
        self.content = content
        self.project_id = project_id
        self.version = version
        self.parent_artifact = parent_artifact
        self.status = status
        self.created_at = (
            created_at
            or datetime.datetime.now(datetime.timezone.utc).isoformat()
        )
        self.metadata = metadata or {}

    @property
    def content_hash(self) -> str:
        """SHA-256 fingerprint of content (first 12 hex chars).

        Works for both string content and dict/list content (JSON-serialised).
        Useful for deduplication and change detection.
        """
        if isinstance(self.content, str):
            raw = self.content.encode("utf-8")
        else:
            raw = json.dumps(self.content, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:12]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "format": self.format,
            "producer": self.producer,
            "content": self.content,
            "content_hash": self.content_hash,
            "project_id": self.project_id,
            "version": self.version,
            "parent_artifact": self.parent_artifact,
            "status": self.status,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Artifact":
        return cls(
            id=data.get("id"),
            artifact_type=data.get("type"),
            format=data.get("format"),
            producer=data.get("producer"),
            content=data.get("content"),
            project_id=data.get("project_id"),
            version=data.get("version", "1.0.0"),
            parent_artifact=data.get("parent_artifact"),
            status=data.get("status", ArtifactStatus.COMPLETED),
            created_at=data.get("created_at"),
            metadata=data.get("metadata"),
        )


class ArtifactManager:
    def __init__(self, env: Environment):
        self.env = env

    def save_artifact(self, artifact: Artifact) -> None:
        """Saves an artifact into the sandboxed environment filesystem and updates the manifest."""
        artifact_path = f"artifacts/{artifact.id}.json"
        self.env.write_file(artifact_path, json.dumps(artifact.to_dict(), indent=2, ensure_ascii=False))

        # Update manifest
        manifest_path = "artifacts/manifest.json"
        manifest = []
        if self.env.exists(manifest_path):
            try:
                manifest = json.loads(self.env.read_file(manifest_path))
            except Exception:
                manifest = []

        # Remove existing if ID matches
        manifest = [item for item in manifest if item["id"] != artifact.id]
        manifest.append({
            "id": artifact.id,
            "type": artifact.type,
            "producer": artifact.producer,
            "project_id": artifact.project_id,
            "version": artifact.version,
            "parent_artifact": artifact.parent_artifact,
            "status": artifact.status,
            "created_at": artifact.created_at,
            "metadata": artifact.metadata,
            "path": artifact_path
        })
        self.env.write_file(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False))

    def get_artifact(self, artifact_id: str) -> Optional[Artifact]:
        """Retrieves a specific artifact by its unique ID."""
        artifact_path = f"artifacts/{artifact_id}.json"
        if not self.env.exists(artifact_path):
            return None
        try:
            data = json.loads(self.env.read_file(artifact_path))
            return Artifact.from_dict(data)
        except Exception:
            return None

    def list_artifacts(self, artifact_type: Optional[str] = None) -> List[Artifact]:
        """Lists all registered artifacts, optionally filtered by type."""
        manifest_path = "artifacts/manifest.json"
        if not self.env.exists(manifest_path):
            return []
        try:
            manifest = json.loads(self.env.read_file(manifest_path))
            artifacts = []
            for item in manifest:
                if artifact_type and item["type"] != artifact_type:
                    continue
                art = self.get_artifact(item["id"])
                if art:
                    artifacts.append(art)
            return artifacts
        except Exception:
            return []
