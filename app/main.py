from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
import datetime

from app.db.database import engine, Base, get_db
from app.db.models import Project, BuildTask, TestRun
from app.agents.coordinator import AgentCoordinator
from sqlalchemy.orm import Session
from app.worker import build_project_task

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Web Creator Multi-Agent Platform API", version="1.0.0")

class ProjectInitReq(BaseModel):
    name: str
    concept: str
    workspace_path: Optional[str] = None

class ProjectResponse(BaseModel):
    id: str
    name: str
    concept: Optional[str]
    status: str
    theme: Optional[str]
    workspace_path: str
    created_at: datetime.datetime

class TaskResponse(BaseModel):
    id: int
    phase: str
    task_name: str
    status: str
    completed_at: Optional[datetime.datetime]

class ProjectStatusResponse(BaseModel):
    project: ProjectResponse
    tasks: List[TaskResponse]
    latest_test_run: Optional[dict] = None

@app.post("/api/project/init")
async def init_project(req: ProjectInitReq):
    workspace = req.workspace_path or f"d:/ai-web-skill/projects/{req.name.replace(' ', '_').lower()}"
    coordinator = AgentCoordinator(workspace_path=workspace)
    try:
        project_id = await coordinator.init_project(name=req.name, concept=req.concept)
        return {"project_id": project_id, "status": "PLANNING", "workspace_path": workspace}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/project/build/{project_id}")
async def build_project(project_id: str, db: Session = Depends(get_db)):
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Queue the build task via Celery
    build_project_task.delay(project_id, db_project.workspace_path)
    
    # Update project status in DB to indicate it is queued
    db_project.status = "QUEUED"
    db.commit()
    return {"status": "QUEUED", "project_id": project_id}

@app.get("/api/project/{project_id}/status", response_model=ProjectStatusResponse)
async def get_project_status(project_id: str, db: Session = Depends(get_db)):
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    tasks = db.query(BuildTask).filter(BuildTask.project_id == project_id).all()
    latest_run = db.query(TestRun).filter(TestRun.project_id == project_id).order_index = TestRun.timestamp.desc()
    latest_run_record = db.query(TestRun).filter(TestRun.project_id == project_id).order_by(TestRun.timestamp.desc()).first()
    
    latest_test_run_data = None
    if latest_run_record:
        latest_test_run_data = {
            "timestamp": latest_run_record.timestamp.isoformat(),
            "passed": latest_run_record.passed,
            "console_violations": latest_run_record.console_violations,
            "report_path": latest_run_record.report_path
        }

    project_data = ProjectResponse(
        id=db_project.id,
        name=db_project.name,
        concept=db_project.concept,
        status=db_project.status,
        theme=db_project.theme,
        workspace_path=db_project.workspace_path,
        created_at=db_project.created_at
    )
    
    task_list = [
        TaskResponse(
            id=t.id,
            phase=t.phase,
            task_name=t.task_name,
            status=t.status,
            completed_at=t.completed_at
        ) for t in tasks
    ]

    return ProjectStatusResponse(
        project=project_data,
        tasks=task_list,
        latest_test_run=latest_test_run_data
    )

@app.post("/api/project/forensics/{project_id}")
async def trigger_forensics(project_id: str, db: Session = Depends(get_db)):
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    coordinator = AgentCoordinator(workspace_path=db_project.workspace_path)
    try:
        await coordinator.run_playwright_test(db_project)
        return {"status": "SUCCESS", "message": "Forensics run succeeded. Test passed."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forensics test run failed: {e}")
