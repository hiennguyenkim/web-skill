import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "apps", "web_creator")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from unittest.mock import patch, AsyncMock
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app, get_db
from app.db.database import Base
from app.db.models import User, Project

# Setup temporary SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, 
    connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables in the testing database
Base.metadata.create_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

# Apply dependency override
app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

@pytest.fixture(autouse=True)
def clean_db():
    # Clean database tables before each test run
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield

def test_user_register_and_login():
    # 1. Register a new user
    reg_response = client.post(
        "/api/auth/register",
        json={"username": "testuser", "password": "securepassword", "role": "PO"}
    )
    assert reg_response.status_code == 200
    assert reg_response.json()["username"] == "testuser"
    assert reg_response.json()["role"] == "PO"

    # 2. Login with credentials
    login_response = client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "securepassword"}
    )
    assert login_response.status_code == 200
    token_data = login_response.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"

    # 3. Retrieve user details using token
    token = token_data["access_token"]
    me_response = client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert me_response.status_code == 200
    assert me_response.json()["username"] == "testuser"

def test_login_invalid_credentials():
    # Attempt login with non-existent user
    login_response = client.post(
        "/api/auth/login",
        json={"username": "invaliduser", "password": "wrongpassword"}
    )
    assert login_response.status_code == 400
    assert "Invalid username or password" in login_response.json()["detail"]

@patch('app.agents.coordinator.AgentCoordinator.init_project', new_callable=AsyncMock)
def test_project_init_and_list(mock_init_project):
    # Mock return project_id
    mock_init_project.return_value = "proj123"

    # Register and login to get JWT token
    client.post(
        "/api/auth/register",
        json={"username": "po_user", "password": "password123"}
    )
    login_res = client.post(
        "/api/auth/login",
        json={"username": "po_user", "password": "password123"}
    )
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Initialize a mock project
    init_res = client.post(
        "/api/project/init",
        json={"name": "Test Project", "concept": "Simple e-commerce landing page"},
        headers=headers
    )
    assert init_res.status_code == 200
    assert init_res.json()["project_id"] == "proj123"
    mock_init_project.assert_called_once_with(name="Test Project", concept="Simple e-commerce landing page")

    # Manually seed project fields in database to simulate successful PM setup
    db = TestingSessionLocal()
    db_proj = Project(
        id="proj123",
        name="Test Project",
        concept="Simple e-commerce landing page",
        status="PLANNING",
        workspace_path="d:/ai-web-skill/projects/test_project",
        owner_id=1
    )
    db.add(db_proj)
    db.commit()
    db.close()

    # Query projects list
    list_res = client.get("/api/projects", headers=headers)
    assert list_res.status_code == 200
    projects = list_res.json()
    assert len(projects) == 1
    assert projects[0]["id"] == "proj123"
    assert projects[0]["name"] == "Test Project"
