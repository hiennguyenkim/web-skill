import os
import sys
import json
import datetime
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Append project root to import skills and core libraries
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))

from app.db.database import engine, Base, get_db
from app.db.models import Project, BuildTask, TestRun, SecurityScan, UserStory, Sprint, DevTask, User
from app.db.auth import hash_password, verify_password, create_access_token, get_current_user
from app.agents.coordinator import AgentCoordinator
from app.worker import build_project_task
from skills.po_toolkit.server import generate_user_story, prioritize_backlog, estimate_effort, breakdown_tasks

# Initialize database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Web Creator Multi-Agent Platform API", version="1.0.0")

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files mount for generated projects and reports
projects_dir = "d:/ai-web-skill/projects"
os.makedirs(projects_dir, exist_ok=True)
app.mount("/projects", StaticFiles(directory=projects_dir), name="projects")

# === AUTHENTICATION SCHEMAS & ENDPOINTS ===

class UserRegisterReq(BaseModel):
    username: str
    password: str
    role: Optional[str] = "PO"

class UserLoginReq(BaseModel):
    username: str
    password: str

@app.post("/api/auth/register")
async def register_user(req: UserRegisterReq, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.username == req.username).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    hashed = hash_password(req.password)
    db_user = User(username=req.username, hashed_password=hashed, role=req.role)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {"message": "User registered successfully", "username": db_user.username, "role": db_user.role}

@app.post("/api/auth/login")
async def login_user(req: UserLoginReq, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.username == req.username).first()
    if not db_user or not verify_password(req.password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Invalid username or password")
    
    access_token = create_access_token(data={"sub": db_user.username})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": db_user.username,
        "role": db_user.role
    }

@app.get("/api/auth/me")
async def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role
    }

# === BUILD PROJECT SCHEMAS & ENDPOINTS ===

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
    latest_security_scan: Optional[dict] = None

@app.get("/api/projects")
async def get_projects(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if current_user.role == "Admin":
        projects = db.query(Project).all()
    else:
        projects = db.query(Project).filter(Project.owner_id == current_user.id).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "concept": p.concept,
            "status": p.status,
            "theme": p.theme,
            "workspace_path": p.workspace_path,
            "created_at": p.created_at
        } for p in projects
    ]

@app.post("/api/project/init")
async def init_project(req: ProjectInitReq, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    workspace = req.workspace_path or f"d:/ai-web-skill/projects/{req.name.replace(' ', '_').lower()}"
    coordinator = AgentCoordinator(workspace_path=workspace)
    try:
        project_id = await coordinator.init_project(name=req.name, concept=req.concept)
        db_project = db.query(Project).filter(Project.id == project_id).first()
        if db_project:
            db_project.owner_id = current_user.id
            db.commit()
        return {"project_id": project_id, "status": "PLANNING", "workspace_path": workspace}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/project/build/{project_id}")
async def build_project(project_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
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
async def get_project_status(project_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    tasks = db.query(BuildTask).filter(BuildTask.project_id == project_id).all()
    latest_run_record = db.query(TestRun).filter(TestRun.project_id == project_id).order_by(TestRun.timestamp.desc()).first()
    
    latest_test_run_data = None
    if latest_run_record:
        latest_test_run_data = {
            "timestamp": latest_run_record.timestamp.isoformat(),
            "passed": latest_run_record.passed,
            "console_violations": latest_run_record.console_violations,
            "report_path": latest_run_record.report_path
        }

    latest_security_record = db.query(SecurityScan).filter(SecurityScan.project_id == project_id).order_by(SecurityScan.timestamp.desc()).first()
    latest_security_scan_data = None
    if latest_security_record:
        latest_security_scan_data = {
            "id": latest_security_record.id,
            "timestamp": latest_security_record.timestamp.isoformat(),
            "passed": latest_security_record.passed,
            "vulnerabilities_found": latest_security_record.vulnerabilities_found,
            "report_path": latest_security_record.report_path
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
        latest_test_run=latest_test_run_data,
        latest_security_scan=latest_security_scan_data
    )

@app.post("/api/project/forensics/{project_id}")
async def trigger_forensics(project_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    coordinator = AgentCoordinator(workspace_path=db_project.workspace_path)
    try:
        await coordinator.run_playwright_test(db_project)
        return {"status": "SUCCESS", "message": "Forensics run succeeded. Test passed."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Forensics test run failed: {e}")

# === PRODUCT OWNER (PO) API ENDPOINTS ===

class POStoriesGenerateReq(BaseModel):
    project_id: str

class POSprintCreateReq(BaseModel):
    name: str
    goal: Optional[str] = None
    start_date: Optional[datetime.datetime] = None
    end_date: Optional[datetime.datetime] = None

class POStoryPriorityEstimateReq(BaseModel):
    project_id: str

class StoryCreateReq(BaseModel):
    title: str
    description: Optional[str] = None
    persona: Optional[str] = None
    want: Optional[str] = None
    benefit: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    priority: Optional[str] = "Should"
    story_points: Optional[int] = None

class StoryUpdateReq(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    persona: Optional[str] = None
    want: Optional[str] = None
    benefit: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    priority: Optional[str] = None
    story_points: Optional[int] = None
    status: Optional[str] = None

class StoryStatusUpdateReq(BaseModel):
    status: str

class DevTaskStatusUpdateReq(BaseModel):
    status: str

class ChatReq(BaseModel):
    message: str
    history: Optional[List[dict]] = []

@app.post("/api/po/stories/generate")
async def generate_po_stories(req: POStoriesGenerateReq, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_project = db.query(Project).filter(Project.id == req.project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not db_project.concept:
        raise HTTPException(status_code=400, detail="Project concept is empty")

    try:
        # Call the PO MCP tool to generate stories
        raw_stories_json = await generate_user_story(db_project.concept)
        
        # Parse JSON
        clean_json = raw_stories_json.strip()
        if clean_json.startswith("```json"):
            clean_json = clean_json[7:]
        if clean_json.endswith("```"):
            clean_json = clean_json[:-3]
        clean_json = clean_json.strip()
        
        stories_data = json.loads(clean_json)
        created_stories = []
        
        for story in stories_data:
            desc = f"As a {story.get('Persona')}, I want to {story.get('Want')}, so that {story.get('Benefit')}"
            ac_list = story.get('AcceptanceCriteria', [])
            ac_text = "\n".join(ac_list) if isinstance(ac_list, list) else str(ac_list)
            
            db_story = UserStory(
                project_id=req.project_id,
                title=story.get('Title', 'Untitled Story'),
                description=desc,
                persona=story.get('Persona'),
                want=story.get('Want'),
                benefit=story.get('Benefit'),
                acceptance_criteria=ac_text,
                status="backlog"
            )
            db.add(db_story)
            created_stories.append(db_story)
        
        db.commit()
        
        return [
            {
                "id": s.id,
                "title": s.title,
                "description": s.description,
                "persona": s.persona,
                "want": s.want,
                "benefit": s.benefit,
                "acceptance_criteria": s.acceptance_criteria,
                "status": s.status
            } for s in created_stories
        ]
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to generate stories: {str(e)}")

@app.get("/api/po/projects/{project_id}/stories")
async def get_project_stories(project_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    stories = db.query(UserStory).filter(UserStory.project_id == project_id).all()
    return [
        {
            "id": s.id,
            "title": s.title,
            "description": s.description,
            "persona": s.persona,
            "want": s.want,
            "benefit": s.benefit,
            "acceptance_criteria": s.acceptance_criteria,
            "priority": s.priority,
            "business_value": s.business_value,
            "technical_risk": s.technical_risk,
            "story_points": s.story_points,
            "complexity_rationale": s.complexity_rationale,
            "status": s.status,
            "sprint_id": s.sprint_id
        } for s in stories
    ]

@app.post("/api/po/projects/{project_id}/stories")
async def create_story(project_id: str, req: StoryCreateReq, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    desc = req.description or f"As a {req.persona or 'User'}, I want to {req.want or 'perform action'}, so that {req.benefit or 'get value'}"
    story = UserStory(
        project_id=project_id,
        title=req.title,
        description=desc,
        persona=req.persona,
        want=req.want,
        benefit=req.benefit,
        acceptance_criteria=req.acceptance_criteria,
        priority=req.priority,
        story_points=req.story_points,
        status="backlog"
    )
    db.add(story)
    db.commit()
    db.refresh(story)
    return story

@app.put("/api/po/stories/{story_id}")
async def update_story_details(story_id: int, req: StoryUpdateReq, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    story = db.query(UserStory).filter(UserStory.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    if req.title is not None:
        story.title = req.title
    if req.description is not None:
        story.description = req.description
    if req.persona is not None:
        story.persona = req.persona
    if req.want is not None:
        story.want = req.want
    if req.benefit is not None:
        story.benefit = req.benefit
    if req.acceptance_criteria is not None:
        story.acceptance_criteria = req.acceptance_criteria
    if req.priority is not None:
        story.priority = req.priority
    if req.story_points is not None:
        story.story_points = req.story_points
    if req.status is not None:
        story.status = req.status
        
    db.commit()
    return {"message": "Story updated successfully", "story_id": story_id}

@app.put("/api/po/stories/{story_id}/status")
async def update_story_status(story_id: int, req: StoryStatusUpdateReq, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    story = db.query(UserStory).filter(UserStory.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    story.status = req.status
    db.commit()
    return {"message": "Story status updated successfully", "story_id": story_id, "status": story.status}

@app.delete("/api/po/stories/{story_id}")
async def delete_story(story_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    story = db.query(UserStory).filter(UserStory.id == story_id).first()
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    
    # Delete related dev tasks
    db.query(DevTask).filter(DevTask.story_id == story_id).delete()
    db.delete(story)
    db.commit()
    return {"message": "Story deleted successfully", "story_id": story_id}

@app.post("/api/po/stories/prioritize-estimate")
async def prioritize_and_estimate_stories(req: POStoryPriorityEstimateReq, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    stories = db.query(UserStory).filter(UserStory.project_id == req.project_id).all()
    if not stories:
        raise HTTPException(status_code=404, detail="No stories found for this project")
    
    # Prepare stories as JSON list
    stories_list = [
        {
            "id": s.id,
            "Title": s.title,
            "Persona": s.persona,
            "Want": s.want,
            "Benefit": s.benefit
        } for s in stories
    ]
    
    try:
        # 1. Call prioritize tool
        raw_prioritized = await prioritize_backlog(json.dumps(stories_list))
        clean_p = raw_prioritized.strip()
        if clean_p.startswith("```json"): clean_p = clean_p[7:]
        if clean_p.endswith("```"): clean_p = clean_p[:-3]
        prioritized_data = json.loads(clean_p.strip())
        
        # 2. Call estimate tool
        raw_estimated = await estimate_effort(json.dumps(prioritized_data))
        clean_e = raw_estimated.strip()
        if clean_e.startswith("```json"): clean_e = clean_e[7:]
        if clean_e.endswith("```"): clean_e = clean_e[:-3]
        estimated_data = json.loads(clean_e.strip())
        
        # Update stories in database
        updated_stories = []
        for item in estimated_data:
            s_id = item.get("id")
            db_story = db.query(UserStory).filter(UserStory.id == s_id).first()
            if db_story:
                db_story.priority = item.get("Priority", "Should")
                db_story.business_value = item.get("BusinessValue", 5)
                db_story.technical_risk = item.get("TechnicalRisk", 5)
                db_story.rationale = item.get("Rationale")
                db_story.story_points = item.get("StoryPoints")
                db_story.complexity_rationale = item.get("ComplexityRationale")
                updated_stories.append(db_story)
                
        db.commit()
        return {"status": "SUCCESS", "message": f"Prioritized and estimated {len(updated_stories)} stories"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to prioritize/estimate stories: {str(e)}")

@app.post("/api/po/stories/{story_id}/breakdown")
async def generate_story_tasks(story_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_story = db.query(UserStory).filter(UserStory.id == story_id).first()
    if not db_story:
        raise HTTPException(status_code=404, detail="Story not found")
        
    story_data = {
        "id": db_story.id,
        "title": db_story.title,
        "description": db_story.description,
        "acceptance_criteria": db_story.acceptance_criteria
    }
    
    try:
        raw_tasks_json = await breakdown_tasks(json.dumps(story_data))
        clean_json = raw_tasks_json.strip()
        if clean_json.startswith("```json"):
            clean_json = clean_json[7:]
        if clean_json.endswith("```"):
            clean_json = clean_json[:-3]
        clean_json = clean_json.strip()
        
        tasks_data = json.loads(clean_json)
        
        # Delete existing tasks for this story
        db.query(DevTask).filter(DevTask.story_id == story_id).delete()
        
        created_tasks = []
        for task in tasks_data:
            db_task = DevTask(
                story_id=story_id,
                task_type=task.get("Type", "API"),
                task_name=task.get("TaskName", "Task"),
                description=task.get("Description"),
                estimated_hours=task.get("EstimatedHours", 2),
                status="todo"
            )
            db.add(db_task)
            created_tasks.append(db_task)
            
        db.commit()
        return [
            {
                "id": t.id,
                "task_type": t.task_type,
                "task_name": t.task_name,
                "description": t.description,
                "estimated_hours": t.estimated_hours,
                "status": t.status
            } for t in created_tasks
        ]
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to breakdown tasks: {str(e)}")

@app.get("/api/po/stories/{story_id}/tasks")
async def get_story_tasks(story_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    tasks = db.query(DevTask).filter(DevTask.story_id == story_id).all()
    return [
        {
            "id": t.id,
            "task_type": t.task_type,
            "task_name": t.task_name,
            "description": t.description,
            "estimated_hours": t.estimated_hours,
            "status": t.status
        } for t in tasks
    ]

@app.put("/api/po/tasks/{task_id}/status")
async def update_task_status(task_id: int, req: DevTaskStatusUpdateReq, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    task = db.query(DevTask).filter(DevTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task.status = req.status
    db.commit()
    return {"message": "Task status updated successfully", "task_id": task_id, "status": task.status}

@app.post("/api/po/projects/{project_id}/sprints")
async def create_sprint(project_id: str, req: POSprintCreateReq, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_project = db.query(Project).filter(Project.id == project_id).first()
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    db_sprint = Sprint(
        project_id=project_id,
        name=req.name,
        goal=req.goal,
        start_date=req.start_date,
        end_date=req.end_date,
        status="planning"
    )
    db.add(db_sprint)
    db.commit()
    db.refresh(db_sprint)
    return db_sprint

@app.get("/api/po/projects/{project_id}/sprints")
async def get_project_sprints(project_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sprints = db.query(Sprint).filter(Sprint.project_id == project_id).all()
    return sprints

@app.post("/api/po/sprints/{sprint_id}/add-story/{story_id}")
async def assign_story_to_sprint(sprint_id: int, story_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_sprint = db.query(Sprint).filter(Sprint.id == sprint_id).first()
    if not db_sprint:
        raise HTTPException(status_code=404, detail="Sprint not found")
        
    db_story = db.query(UserStory).filter(UserStory.id == story_id).first()
    if not db_story:
        raise HTTPException(status_code=404, detail="Story not found")
        
    db_story.sprint_id = sprint_id
    db_story.status = "todo"
    db.commit()
    db.refresh(db_story)
    return db_story

@app.post("/api/po/chat")
async def po_chat(req: ChatReq, current_user: User = Depends(get_current_user)):
    from core.llm.client import LLMClient
    po_client = LLMClient(system_instruction=(
        "You are an Elite Product Owner agent assistant. Help the user clarify requirements, "
        "write high-quality user stories with acceptance criteria, prioritize their backlog (MoSCoW), "
        "estimate effort (Fibonacci story points), or break down technical tasks. "
        "Answer questions in the user's language (Vietnamese or English as input) clearly and professionally."
    ))
    
    chat_prompt = ""
    for h in req.history:
        role = "User" if h.get("role") == "user" else "Assistant"
        chat_prompt += f"{role}: {h.get('content')}\n"
    chat_prompt += f"User: {req.message}\nAssistant:"
    
    try:
        response_text = await po_client.call_llm(chat_prompt)
        return {"response": response_text.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM Chat execution failed: {str(e)}")

# === STATIC FILES MOUNT FOR DASHBOARD FRONTEND ===
# Serve dashboard static distribution if it has been compiled
dashboard_dist = "apps/po_dashboard/dist"
if os.path.exists(dashboard_dist):
    app.mount("/", StaticFiles(directory=dashboard_dist, html=True), name="dashboard")
