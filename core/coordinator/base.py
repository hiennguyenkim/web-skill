import os
import json
import asyncio
from typing import Dict, Any, List
from core.llm.client import LLMClient

class AgentPersona:
    def __init__(self, name: str, role: str, system_instruction: str):
        self.name = name
        self.role = role
        self.system_instruction = system_instruction
        self.llm_client = LLMClient(system_instruction=system_instruction)

    async def execute(self, prompt: str) -> str:
        """Call the underlying LLM with the agent's specific instructions."""
        return await self.llm_client.call_llm(prompt)

class GenericCoordinator:
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        os.makedirs(workspace_path, exist_ok=True)
        self.personas: Dict[str, AgentPersona] = {}

    def register_persona(self, key: str, persona: AgentPersona):
        self.personas[key] = persona

    async def call_persona(self, key: str, prompt: str) -> str:
        if key not in self.personas:
            raise ValueError(f"Persona '{key}' is not registered in the coordinator.")
        return await self.personas[key].execute(prompt)
