# Developer Guide: Creating & Integrating Custom MCP Skills

This guide walks you through creating a new Model Context Protocol (MCP) Skill Server, exposing tools via decorators, writing tests, and integrating them into the multi-agent build pipeline.

---

## 1. Skill Server Architecture

The platform uses an open, modular skill system. Each skill runs as an independent MCP server that exposes one or more tools.
* **Internal Calls**: The FastAPI backend or Agent Coordinator can import and invoke these tools directly as async Python functions.
* **External Calls**: Editor clients (like Cursor or VS Code) or other orchestrators can connect to the skill servers over the Standard I/O (STDIO) transport.

The platform provides a simple wrapper SDK at `core/skill_sdk` utilizing FastMCP.

---

## 2. Step-by-Step: Creating a New Skill

### Step 2.1: Define the Directory Structure
Create a new directory under `skills/` for your skill, for example: `skills/my_custom_skill/`.

```text
skills/
└── my_custom_skill/
    ├── __init__.py
    ├── server.py
    └── tests/
        └── test_server.py
```

### Step 2.2: Implement the Skill Server (`server.py`)
In `server.py`, initialize the `SkillServer` and register functions using the `@tool` decorator.

> [!IMPORTANT]
> FastMCP parses the function's docstring for the tool's description and relies on Python type hints to build the JSON Schema parameters. Always include type hints and clear docstrings.

```python
# skills/my_custom_skill/server.py
import json
from core.skill_sdk import SkillServer, tool
from core.llm.client import LLMClient

# 1. Initialize the Skill Server
server = SkillServer("my-custom-skill")

# 2. Setup LLM Client with specialized system instructions
llm = LLMClient(system_instruction=(
    "You are a specialized Data Schema Agent. Your role is to design schemas..."
))

# 3. Define and register your tools
@tool
async def generate_database_schema(description: str, db_type: str = "sqlite") -> str:
    """Generate a clean database schema script based on requirements description.
    
    Args:
        description: Text requirements for the database.
        db_type: Target database dialect (sqlite, postgres, mongodb).
    """
    prompt = (
        f"Design a database schema for: '{description}' using '{db_type}'.\n"
        "Return ONLY the SQL script or database schema declaration. No markdown code blocks."
    )
    # Invoke the LLM wrapper
    schema_code = await llm.call_llm(prompt)
    return schema_code.strip()

# 4. Standard boilerplate to execute via STDIO
if __name__ == "__main__":
    server.run(transport="stdio")
```

---

## 3. Registering the Skill into an Agent Persona

Once your skill is created, you can link it to a specific Agent.
For example, to register your database schema tool into the **Backend Developer Agent**:

1. Open [apps/web_creator/app/agents/personas.py](file:///d:/ai-web-skill/apps/web_creator/app/agents/personas.py).
2. Inside `BackendAgent`, import the custom tool:
   ```python
   # apps/web_creator/app/agents/personas.py
   from skills.my_custom_skill.server import generate_database_schema
   ```
3. The Agent can now leverage the tool natively or you can call it inside the Coordinator pipeline!

---

## 4. Running & Testing Locally

### Standard I/O (STDIO) testing
You can launch and test the skill directly from the CLI:
```bash
python skills/my_custom_skill/server.py
```
This starts the FastMCP server waiting for JSON-RPC messages on STDIO. You can pipe a standard MCP initialization command to test it, or hook it up to a tool inspector.

### Writing Unit Tests
Each skill should have a corresponding test file under its `tests/` directory (or in the root `tests/unit/` folder).

Use `pytest` and mock the LLM client call:
```python
# skills/my_custom_skill/tests/test_server.py
import json
from unittest.mock import patch
import pytest
from skills.my_custom_skill.server import generate_database_schema

@pytest.mark.asyncio
@patch('core.llm.client.LLMClient.call_llm')
async def test_generate_database_schema(mock_call):
    # Mock LLM return response
    mock_call.return_value = "CREATE TABLE users (id INTEGER PRIMARY KEY);"
    
    # Run tool
    result = await generate_database_schema("user profile table")
    
    assert "CREATE TABLE users" in result
    mock_call.assert_called_once()
```

Run tests from the repository root:
```bash
python -m pytest tests/
```
