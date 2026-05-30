import os
from google import genai
from google.genai import types
from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

class BaseAgent:
    def __init__(self, name: str, role: str, system_instruction: str = None):
        self.name = name
        self.role = role
        self.system_instruction = system_instruction
        self._initialize_llm()

    def _initialize_llm(self):
        self.provider = os.getenv("LLM_PROVIDER", "gemini").lower()
        if self.provider == "deepseek":
            api_key = os.getenv("DEEPSEEK_API_KEY")
            api_base = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com")
            if not api_key:
                print("⚠️ Warning: DEEPSEEK_API_KEY not found in environment.")
            self.openai_client = AsyncOpenAI(api_key=api_key, base_url=api_base) if api_key else None
            self.sync_openai_client = OpenAI(api_key=api_key, base_url=api_base) if api_key else None
            self.genai_client = None
        else:
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if api_key:
                self.genai_client = genai.Client(api_key=api_key)
            else:
                self.genai_client = None
                print("⚠️ Warning: GEMINI_API_KEY or GOOGLE_API_KEY not found in environment.")

    async def call_llm(self, prompt: str) -> str:
        if self.provider == "deepseek":
            model_name = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
            if not self.openai_client:
                return "Error: DeepSeek API client not initialized. Please set DEEPSEEK_API_KEY."
            try:
                messages = []
                if self.system_instruction:
                    messages.append({"role": "system", "content": self.system_instruction})
                messages.append({"role": "user", "content": prompt})
                
                response = await self.openai_client.chat.completions.create(
                    model=model_name,
                    messages=messages
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"❌ Error in DeepSeek LLM call for agent {self.name}: {e}")
                # Simple synchronous fallback if async fails
                try:
                    messages = []
                    if self.system_instruction:
                        messages.append({"role": "system", "content": self.system_instruction})
                    messages.append({"role": "user", "content": prompt})
                    
                    response = self.sync_openai_client.chat.completions.create(
                        model=model_name,
                        messages=messages
                    )
                    return response.choices[0].message.content
                except Exception as sync_e:
                    return f"Error executing agent prompt via DeepSeek: {sync_e}"
        else:
            if not self.genai_client:
                try:
                    self.genai_client = genai.Client()
                except Exception:
                    pass
            if not self.genai_client:
                return "Mock Gemini Response (No API Key)"
            model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
            try:
                config = types.GenerateContentConfig(
                    system_instruction=self.system_instruction
                ) if self.system_instruction else None
                
                response = await self.genai_client.aio.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=config
                )
                return response.text
            except Exception as e:
                print(f"❌ Error in LLM call for agent {self.name}: {e}")
                # Simple synchronous fallback if async fails or model mismatch
                try:
                    config = types.GenerateContentConfig(
                        system_instruction=self.system_instruction
                    ) if self.system_instruction else None
                    
                    response = self.genai_client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=config
                    )
                    return response.text
                except Exception as sync_e:
                    return f"Error executing agent prompt: {sync_e}"
