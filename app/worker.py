import os
import asyncio
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

# Initialize Celery app with Redis broker and result backend
celery_app = Celery(
    "web_creator_tasks",
    broker=REDIS_URL,
    backend=REDIS_URL
)

# Optional configuration overrides
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True
)

@celery_app.task(name="build_project_task")
def build_project_task(project_id: str, workspace_path: str):
    """
    Background worker task to coordinate and build the project.
    Runs the async coordinator pipeline using asyncio.run.
    """
    print(f"📥 Received background task: Dựng dự án {project_id} tại {workspace_path}")
    from app.agents.coordinator import AgentCoordinator
    
    # Run the async agent loop in a synchronous Celery worker thread
    coordinator = AgentCoordinator(workspace_path=workspace_path)
    try:
        asyncio.run(coordinator.build_project(project_id=project_id))
        print(f"🎉 Background task COMPLETED: Dự án {project_id} đã được dựng và kiểm thử thành công.")
        return {"status": "SUCCESS", "project_id": project_id}
    except Exception as e:
        print(f"❌ Background task FAILED for project {project_id}: {e}")
        # Mark project status as FAILED in database
        from app.db.database import SessionLocal
        from app.db.models import Project
        db = SessionLocal()
        try:
            project = db.query(Project).filter(Project.id == project_id).first()
            if project:
                project.status = "FAILED"
                db.commit()
        except Exception as db_err:
            print(f"Failed to record error status in DB: {db_err}")
        finally:
            db.close()
        raise e
