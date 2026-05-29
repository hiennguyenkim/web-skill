import json
from unittest.mock import patch
import pytest

from skills.po_toolkit.server import (
    generate_user_story,
    prioritize_backlog,
    estimate_effort,
    breakdown_tasks
)

@pytest.mark.asyncio
@patch('platform_core.core.llm.client.LLMClient.call_llm')
async def test_generate_user_story_success(mock_call):
    # Setup mock LLM response
    mock_response = [
        {
            "Title": "User Sign Up",
            "Persona": "Guest",
            "Want": "sign up with my email",
            "Benefit": "access my dashboard",
            "AcceptanceCriteria": ["Given a new email, when submitting details, then account is created."]
        }
    ]
    mock_call.return_value = json.dumps(mock_response)
    
    # Run target tool
    result_str = await generate_user_story("Tôi cần một trang đăng ký")
    result = json.loads(result_str)
    
    # Assertions
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["Title"] == "User Sign Up"
    assert result[0]["Persona"] == "Guest"
    mock_call.assert_called_once()

@pytest.mark.asyncio
@patch('platform_core.core.llm.client.LLMClient.call_llm')
async def test_prioritize_backlog_success(mock_call):
    # Setup inputs
    stories = [
        {
            "id": 1,
            "Title": "Story A",
            "Persona": "User",
            "Want": "Action A",
            "Benefit": "Value A"
        }
    ]
    
    # Setup mock LLM response
    mock_response = [
        {
            "id": 1,
            "Title": "Story A",
            "Persona": "User",
            "Want": "Action A",
            "Benefit": "Value A",
            "Priority": "Must",
            "BusinessValue": 9,
            "TechnicalRisk": 3,
            "Rationale": "Critical for MVP"
        }
    ]
    mock_call.return_value = json.dumps(mock_response)
    
    # Run target tool
    result_str = await prioritize_backlog(json.dumps(stories))
    result = json.loads(result_str)
    
    # Assertions
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["Priority"] == "Must"
    assert result[0]["BusinessValue"] == 9

@pytest.mark.asyncio
@patch('platform_core.core.llm.client.LLMClient.call_llm')
async def test_estimate_effort_success(mock_call):
    # Setup inputs
    stories = [
        {
            "id": 1,
            "Title": "Story A",
            "Priority": "Must"
        }
    ]
    
    # Setup mock LLM response
    mock_response = [
        {
            "id": 1,
            "Title": "Story A",
            "Priority": "Must",
            "StoryPoints": 5,
            "ComplexityRationale": "Requires database schema updates"
        }
    ]
    mock_call.return_value = json.dumps(mock_response)
    
    # Run target tool
    result_str = await estimate_effort(json.dumps(stories))
    result = json.loads(result_str)
    
    # Assertions
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["StoryPoints"] == 5
    assert "ComplexityRationale" in result[0]

@pytest.mark.asyncio
@patch('platform_core.core.llm.client.LLMClient.call_llm')
async def test_breakdown_tasks_success(mock_call):
    # Setup inputs
    story = {
        "id": 1,
        "title": "Story A",
        "description": "User login"
    }
    
    # Setup mock LLM response
    mock_response = [
        {
            "Type": "Database",
            "TaskName": "Create User Schema",
            "Description": "Define database fields for email and passwords",
            "EstimatedHours": 2
        },
        {
            "Type": "API",
            "TaskName": "Create Login Route",
            "Description": "Implement POST /api/auth/login endpoint",
            "EstimatedHours": 3
        }
    ]
    mock_call.return_value = json.dumps(mock_response)
    
    # Run target tool
    result_str = await breakdown_tasks(json.dumps(story))
    result = json.loads(result_str)
    
    # Assertions
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["Type"] == "Database"
    assert result[1]["Type"] == "API"
    assert result[1]["EstimatedHours"] == 3
