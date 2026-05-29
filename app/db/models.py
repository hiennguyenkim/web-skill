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

    tasks = relationship("BuildTask", back_populates="project", cascade="all, delete-orphan")
    test_runs = relationship("TestRun", back_populates="project", cascade="all, delete-orphan")
    security_scans = relationship("SecurityScan", back_populates="project", cascade="all, delete-orphan")

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

