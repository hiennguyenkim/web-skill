import datetime
import json
import uuid
from typing import Any, Dict, List, Optional

from platform_core.core.environment.base import Environment


class Event:
    def __init__(
        self,
        event_type: str,
        producer: str,
        project_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
        id: Optional[str] = None,
        timestamp: Optional[str] = None,
        correlation_id: Optional[str] = None,  # links related events in a pipeline run
    ):
        self.id = id or f"evt_{str(uuid.uuid4())[:8]}"
        self.type = event_type
        self.producer = producer
        self.project_id = project_id
        self.payload = payload or {}
        self.correlation_id = correlation_id
        self.timestamp = (
            timestamp
            or datetime.datetime.now(datetime.timezone.utc).isoformat()
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "producer": self.producer,
            "project_id": self.project_id,
            "payload": self.payload,
            "correlation_id": self.correlation_id,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        return cls(
            id=data.get("id"),
            event_type=data.get("type"),
            producer=data.get("producer"),
            project_id=data.get("project_id"),
            payload=data.get("payload"),
            timestamp=data.get("timestamp"),
            correlation_id=data.get("correlation_id"),
        )


class EventManager:
    def __init__(self, env: Environment):
        self.env = env

    def emit_event(self, event: Event) -> None:
        """Emits an event by writing it as a JSON file and updating the event manifest."""
        event_path = f"events/{event.id}.json"
        self.env.write_file(event_path, json.dumps(event.to_dict(), indent=2, ensure_ascii=False))

        # Update manifest
        manifest_path = "events/manifest.json"
        manifest = []
        if self.env.exists(manifest_path):
            try:
                manifest = json.loads(self.env.read_file(manifest_path))
            except Exception:
                manifest = []

        # Remove existing if ID matches
        manifest = [item for item in manifest if item["id"] != event.id]
        manifest.append({
            "id": event.id,
            "type": event.type,
            "producer": event.producer,
            "project_id": event.project_id,
            "timestamp": event.timestamp,
            "path": event_path
        })
        self.env.write_file(manifest_path, json.dumps(manifest, indent=2, ensure_ascii=False))

    def list_events_by_type(self, event_type: str, project_id: Optional[str] = None) -> List[Event]:
        """Returns events filtered by type, optionally also by project_id."""
        return [
            e for e in self.list_events(project_id=project_id)
            if e.type == event_type
        ]

    def list_events(self, project_id: Optional[str] = None) -> List[Event]:
        """Lists all emitted events, optionally filtered by project_id."""
        manifest_path = "events/manifest.json"
        if not self.env.exists(manifest_path):
            return []
        try:
            manifest = json.loads(self.env.read_file(manifest_path))
            events = []
            for item in manifest:
                if project_id and item["project_id"] != project_id:
                    continue
                evt_path = f"events/{item['id']}.json"
                if self.env.exists(evt_path):
                    try:
                        data = json.loads(self.env.read_file(evt_path))
                        events.append(Event.from_dict(data))
                    except Exception:
                        pass
            return events
        except Exception:
            return []
