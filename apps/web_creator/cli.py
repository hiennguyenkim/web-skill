import os
import sys
import argparse
import asyncio
import uvicorn

try:
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

async def run_cli_build(name: str, concept: str, workspace: str):
    from app.agents.coordinator import AgentCoordinator
    from platform_core.core.environment.local import LocalEnvironment
    env = LocalEnvironment(workspace_path=workspace)
    coordinator = AgentCoordinator(env=env)
    try:
        print(f"🚀 Initializing GSD specs for project: {name}...")
        project_id = await coordinator.init_project(name=name, concept=concept)
        print(f"✅ Initialized project {project_id} in: {workspace}")
        
        print("🚀 Executing autonomous multi-agent code generation and verification...")
        await coordinator.build_project(project_id)
        print("✅ Project build and browser validation completed successfully.")
    except Exception as e:
        print(f"❌ CLI Build failed: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Web Creator CLI Platform")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Server runner
    serve_parser = subparsers.add_parser("serve", help="Run FastAPI HTTP Server")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port to bind server")
    serve_parser.add_argument("--host", type=str, default="0.0.0.0", help="Host address to bind")

    # MCP STDIO runner
    mcp_parser = subparsers.add_parser("mcp", help="Run STDIO MCP Server")

    # Celery worker runner
    subparsers.add_parser("worker", help="Run Celery Background Worker")

    # Direct build runner
    build_parser = subparsers.add_parser("build", help="Run a direct local build task")
    build_parser.add_argument("name", type=str, help="Name of your web app")
    build_parser.add_argument("concept", type=str, help="Text concept descriptions or Word .docx path")
    build_parser.add_argument("--workspace", type=str, default=os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "projects", "cli_build").replace("\\", "/"), help="Target workspace path")

    args = parser.parse_args()

    if args.command == "serve":
        print(f"🚀 Starting FastAPI web server at http://{args.host}:{args.port}...")
        uvicorn.run("app.main:app", host=args.host, port=args.port, reload=False)
    
    elif args.command == "mcp":
        print("🚀 Starting Web Creator MCP Server over STDIO...")
        from app.mcp.server import mcp
        mcp.run("stdio")

    elif args.command == "worker":
        print("🚀 Starting Celery background worker...")
        from app.worker import celery_app
        celery_app.worker_main(argv=["worker", "--loglevel=info"])

    elif args.command == "build":
        asyncio.run(run_cli_build(name=args.name, concept=args.concept, workspace=args.workspace))

if __name__ == "__main__":
    main()
