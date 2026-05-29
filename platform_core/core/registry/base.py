"""
platform_core.core.registry.base
=================================
Capability Registry — maps logical capability identifiers to concrete
agent/tool implementations.

Concepts
--------
CapabilityDescriptor
    Metadata record for a single capability: its id, human-readable name,
    description, which agent_type handles it, the concrete tool name/path,
    and a set of tags for filtering.

CapabilityRegistry
    In-memory registry.  Populated at startup by each application (e.g.
    web_creator registers its agents here).  Supports lookup by id, filter
    by tag, and listing all capabilities.

Default web_creator capabilities are pre-registered so the registry is
immediately useful without any extra configuration.
"""

from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------

class CapabilityNotFoundError(KeyError):
    """Raised when resolve() is called with an unregistered capability id."""

    def __init__(self, capability_id: str):
        self.capability_id = capability_id
        super().__init__(
            f"No capability registered with id '{capability_id}'. "
            "Call registry.register() or check the id spelling."
        )


# ---------------------------------------------------------------------------
# Descriptor
# ---------------------------------------------------------------------------

class CapabilityDescriptor:
    """Describes one capability that the platform can invoke."""

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        agent_type: str,
        tool: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict] = None,
    ):
        self.id = id                          # e.g. "frontend_generation"
        self.name = name                      # e.g. "Frontend HTML/JS Generation"
        self.description = description        # human description
        self.agent_type = agent_type          # e.g. "CoderAgent"
        self.tool = tool                      # optional: MCP skill tool name
        self.tags: List[str] = tags or []
        self.metadata: Dict = metadata or {}

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "agent_type": self.agent_type,
            "tool": self.tool,
            "tags": self.tags,
            "metadata": self.metadata,
        }

    def __repr__(self) -> str:
        return f"<CapabilityDescriptor id={self.id!r} agent={self.agent_type!r}>"


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class CapabilityRegistry:
    """
    In-memory registry of platform capabilities.

    By default, the web_creator application's standard capabilities are
    pre-registered.  Applications can extend the registry at startup.
    """

    def __init__(self, load_defaults: bool = True):
        self._store: Dict[str, CapabilityDescriptor] = {}
        if load_defaults:
            self._register_defaults()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def register(self, descriptor: CapabilityDescriptor) -> None:
        """Register a capability (overwrites if same id already exists)."""
        self._store[descriptor.id] = descriptor

    def unregister(self, capability_id: str) -> bool:
        """Remove a capability by id. Returns True if it existed."""
        if capability_id in self._store:
            del self._store[capability_id]
            return True
        return False

    def get(self, capability_id: str) -> Optional[CapabilityDescriptor]:
        """Retrieve a capability descriptor by id, or None."""
        return self._store.get(capability_id)

    def resolve(self, capability_id: str) -> CapabilityDescriptor:
        """
        Resolve a capability by id — like ``get()`` but raises ``CapabilityNotFoundError``
        instead of returning None.

        This is the *dispatch-path* method.  Agents should call ``resolve()``
        so that missing capabilities fail loudly rather than silently.

        Parameters
        ----------
        capability_id : str
            The logical capability identifier, e.g. ``"frontend_generation"``.

        Returns
        -------
        CapabilityDescriptor

        Raises
        ------
        CapabilityNotFoundError
            If no capability is registered for the given id.
        """
        descriptor = self._store.get(capability_id)
        if descriptor is None:
            raise CapabilityNotFoundError(capability_id)
        return descriptor

    def list_all(self) -> List[CapabilityDescriptor]:
        """Return all registered capabilities."""
        return list(self._store.values())

    def list_by_tag(self, tag: str) -> List[CapabilityDescriptor]:
        """Return capabilities whose tags include `tag`."""
        return [c for c in self._store.values() if tag in c.tags]

    def list_by_agent(self, agent_type: str) -> List[CapabilityDescriptor]:
        """Return capabilities handled by a specific agent type."""
        return [c for c in self._store.values() if c.agent_type == agent_type]

    def __len__(self) -> int:
        return len(self._store)

    def __contains__(self, capability_id: str) -> bool:
        return capability_id in self._store

    # ------------------------------------------------------------------
    # Default web_creator capabilities
    # ------------------------------------------------------------------

    def _register_defaults(self) -> None:
        """Pre-populate the registry with web_creator's standard capabilities."""
        defaults = [
            CapabilityDescriptor(
                id="product_planning",
                name="Product Planning & Specification",
                description=(
                    "Produces PROJECT.md, ROADMAP.md, STATE.md, and DESIGN.md "
                    "from a product concept description."
                ),
                agent_type="ProductManager",
                tool=None,
                tags=["planning", "specification", "pm"],
            ),
            CapabilityDescriptor(
                id="architecture_design",
                name="Application Architecture Design",
                description=(
                    "Generates architecture.md, db_schema.sql, api_spec.yaml, "
                    "and workflow.yaml from product specifications."
                ),
                agent_type="ArchitectAgent",
                tool=None,
                tags=["architecture", "design", "planning"],
            ),
            CapabilityDescriptor(
                id="ui_design_tokens",
                name="UI/UX Design Token Generation",
                description=(
                    "Creates CSS custom property design tokens (colors, typography, "
                    "spacing) aligned with the DESIGN.md spec."
                ),
                agent_type="DesignerAgent",
                tool=None,
                tags=["design", "css", "frontend"],
            ),
            CapabilityDescriptor(
                id="frontend_generation",
                name="Frontend HTML/JS Generation",
                description=(
                    "Generates semantic HTML5 structure with interactive JavaScript "
                    "for a web project based on design specifications."
                ),
                agent_type="CoderAgent",
                tool="html_coder",
                tags=["frontend", "html", "javascript"],
            ),
            CapabilityDescriptor(
                id="css_styling",
                name="Responsive CSS Styling",
                description=(
                    "Upgrades index.css with responsive breakpoints, hover animations, "
                    "glassmorphic grids, and keyframe animations."
                ),
                agent_type="CSSAgent",
                tool="css_expert",
                tags=["frontend", "css", "responsive"],
            ),
            CapabilityDescriptor(
                id="backend_generation",
                name="Backend API & Database Generation",
                description=(
                    "Generates Mongoose models, Express routes, controllers, "
                    "server.js, config/db.js, and package.json."
                ),
                agent_type="BackendAgent",
                tool="backend_generator",
                tags=["backend", "api", "database", "nodejs"],
            ),
            CapabilityDescriptor(
                id="qa_testing",
                name="QA Automated Testing",
                description=(
                    "Runs Playwright browser automation tests against the generated "
                    "frontend to verify functional correctness."
                ),
                agent_type="QAAgent",
                tool="qa_playwright",
                tags=["qa", "testing", "playwright", "automation"],
            ),
            CapabilityDescriptor(
                id="security_scanning",
                name="Static Security Scanning",
                description=(
                    "Performs XSS, CSRF, DOM injection, and configuration exposure "
                    "analysis on the generated codebase via Strix CLI or AI fallback."
                ),
                agent_type="SecurityAgent",
                tool=None,
                tags=["security", "scanning", "audit"],
            ),
            CapabilityDescriptor(
                id="self_healing",
                name="Self-Healing Auto Repair",
                description=(
                    "Analyzes Playwright error logs and applies corrective patches "
                    "to index.html or index.css via forensics LLM analysis."
                ),
                agent_type="ProductManager",
                tool=None,
                tags=["repair", "forensics", "self-healing"],
            ),
            CapabilityDescriptor(
                id="po_user_stories",
                name="Product Owner — User Stories",
                description=(
                    "Generates structured user stories, backlog prioritization, "
                    "effort estimates, and task breakdowns."
                ),
                agent_type="POAgent",
                tool="po_toolkit",
                tags=["planning", "po", "agile", "user-stories"],
            ),
        ]
        for cap in defaults:
            self.register(cap)
