from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
import datetime
from .database import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    concept = Column(Text, nullable=True)
    status = Column(String, default="INIT")  # INIT, PLANNING, BUILDING, PASSED, FAILED
    theme = Column(String, nullable=True)
    workspace_path = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    tasks = relationship("BuildTask", back_populates="project", cascade="all, delete-orphan")
    test_runs = relationship("TestRun", back_populates="project", cascade="all, delete-orphan")
    security_scans = relationship("SecurityScan", back_populates="project", cascade="all, delete-orphan")
    sprints = relationship("Sprint", back_populates="project", cascade="all, delete-orphan")
    user_stories = relationship("UserStory", back_populates="project", cascade="all, delete-orphan")
    owner = relationship("User", back_populates="projects")

class BuildTask(Base):
    __tablename__ = "build_tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    phase = Column(String, nullable=False)
    task_name = Column(String, nullable=False)
    assigned_persona = Column(String, nullable=True)
    status = Column(String, default="PENDING")  # PENDING, RUNNING, COMPLETED, FAILED
    completed_at = Column(DateTime, nullable=True)

    project = relationship("Project", back_populates="tasks")

class TestRun(Base):
    __tablename__ = "test_runs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    passed = Column(Boolean, default=False)
    console_violations = Column(Integer, default=0)
    load_time_ms = Column(Integer, default=0)
    ttfb_ms = Column(Integer, default=0)
    report_path = Column(String, nullable=True)

    project = relationship("Project", back_populates="test_runs")

class SecurityScan(Base):
    __tablename__ = "security_scans"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    passed = Column(Boolean, default=False)
    vulnerabilities_found = Column(Integer, default=0)
    report_path = Column(String, nullable=True)

    project = relationship("Project", back_populates="security_scans")


class Sprint(Base):
    __tablename__ = "sprints"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    name = Column(String, nullable=False)
    goal = Column(Text, nullable=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)
    status = Column(String, default="planning") # planning, active, completed

    project = relationship("Project", back_populates="sprints")
    user_stories = relationship("UserStory", back_populates="sprint")


class UserStory(Base):
    __tablename__ = "user_stories"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_id = Column(String, ForeignKey("projects.id"), nullable=False)
    sprint_id = Column(Integer, ForeignKey("sprints.id"), nullable=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    persona = Column(String, nullable=True)
    want = Column(Text, nullable=True)
    benefit = Column(Text, nullable=True)
    acceptance_criteria = Column(Text, nullable=True)
    priority = Column(String, default="Should") # Must, Should, Could, Won't
    business_value = Column(Integer, default=5)
    technical_risk = Column(Integer, default=5)
    rationale = Column(Text, nullable=True)
    story_points = Column(Integer, nullable=True)
    complexity_rationale = Column(Text, nullable=True)
    status = Column(String, default="backlog") # backlog, todo, in_progress, done
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    project = relationship("Project", back_populates="user_stories")
    sprint = relationship("Sprint", back_populates="user_stories")
    dev_tasks = relationship("DevTask", back_populates="user_story", cascade="all, delete-orphan")


class DevTask(Base):
    __tablename__ = "dev_tasks"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    story_id = Column(Integer, ForeignKey("user_stories.id"), nullable=False)
    task_type = Column(String, nullable=False) # Database, API, Frontend, QA
    task_name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    estimated_hours = Column(Integer, default=1)
    status = Column(String, default="todo") # todo, in_progress, done

    user_story = relationship("UserStory", back_populates="dev_tasks")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="PO") # PO, Admin
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    projects = relationship("Project", back_populates="owner")



