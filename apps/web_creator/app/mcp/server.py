import os
from mcp.server.fastmcp import FastMCP
from app.agents.coordinator import AgentCoordinator
from app.db.database import BASE_DIR
import asyncio

mcp = FastMCP("Web-Creator-MCP-Server")

@mcp.tool()
async def web_creator_init(name: str, concept: str, workspace_path: str = None) -> str:
    """
    Initialize a web creation project.
    Generates specifications (PROJECT.md), checks and roadmap files.
    """
    path = workspace_path or os.path.join(BASE_DIR, "projects", name.replace(' ', '_').lower()).replace("\\", "/")
    from platform_core.core.environment.local import LocalEnvironment
    env = LocalEnvironment(workspace_path=path)
    coordinator = AgentCoordinator(env=env)
    try:
        project_id = await coordinator.init_project(name=name, concept=concept)
        return f"✅ Project successfully initialized. Project ID: {project_id} | Workspace: {path}"
    except Exception as e:
        return f"❌ Failed to initialize project: {str(e)}"

@mcp.tool()
async def web_creator_build(project_id: str) -> str:
    """
    Run the autonomous multi-agent build pipeline (PM, Designer, Coder, CSS Architect, QA Specialist)
    for the given Project ID. Generates layout files and runs Playwright testing.
    """
    from app.db.database import SessionLocal
    from app.db.models import Project
    
    db = SessionLocal()
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        db.close()
        return f"❌ Error: Project with ID {project_id} not found."
    
    workspace = project.workspace_path
    db.close()

    from platform_core.core.environment.local import LocalEnvironment
    env = LocalEnvironment(workspace_path=workspace)
    coordinator = AgentCoordinator(env=env)
    try:
        await coordinator.build_project(project_id=project_id)
        return f"✅ Web Creator build succeeded for project {project_id}. Site generated and verified in {workspace}."
    except Exception as e:
        return f"❌ Web Creator build failed: {str(e)}"

@mcp.tool()
async def web_creator_forensics(project_id: str) -> str:
    """
    Diagnose and auto-repair styling or console errors in the specified project.
    Runs a headless Playwright test suite and applies surgical patches if tests fail.
    """
    from app.db.database import SessionLocal
    from app.db.models import Project
    
    db = SessionLocal()
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        db.close()
        return f"❌ Error: Project with ID {project_id} not found."
    
    workspace = project.workspace_path
    db.close()

    from platform_core.core.environment.local import LocalEnvironment
    env = LocalEnvironment(workspace_path=workspace)
    coordinator = AgentCoordinator(env=env)
    try:
        await coordinator.run_playwright_test(project)
        return f"✅ Diagnostics run succeeded. Project is verified and console-clean."
    except Exception as e:
        return f"❌ Diagnostics run or self-healing repair failed: {str(e)}"
