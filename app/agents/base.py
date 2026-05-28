import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

class BaseAgent:
    def __init__(self, name: str, role: str, system_instruction: str = None):
        self.name = name
        self.role = role
        self.system_instruction = system_instruction
        self._initialize_gemini()

    def _initialize_gemini(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            # Fallback to general system check
            api_key = os.getenv("GOOGLE_API_KEY")
        
        if api_key:
            genai.configure(api_key=api_key)
        else:
            print("⚠️ Warning: GEMINI_API_KEY or GOOGLE_API_KEY not found in environment.")

    async def call_llm(self, prompt: str) -> str:
        model_name = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
        try:
            # Initialize model with system instruction if available
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=self.system_instruction
            )
            response = await model.generate_content_async(prompt)
            return response.text
        except Exception as e:
            print(f"❌ Error in LLM call for agent {self.name}: {e}")
            # Simple synchronous fallback if async fails or model mismatch
            try:
                model = genai.GenerativeModel(model_name=model_name, system_instruction=self.system_instruction)
                response = model.generate_content(prompt)
                return response.text
            except Exception as sync_e:
                return f"Error executing agent prompt: {sync_e}"
