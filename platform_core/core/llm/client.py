import os
import google.generativeai as genai
from openai import OpenAI, AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

class LLMClient:
    def __init__(self, system_instruction: str = None):
        self.system_instruction = system_instruction
        self._initialize_llm()

    def _initialize_llm(self):
        self.provider = os.getenv("LLM_PROVIDER", "gemini").lower()
        if self.provider == "deepseek":
            api_key = os.getenv("DEEPSEEK_API_KEY")
            api_base = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com")
            if not api_key:
                print("Warning: DEEPSEEK_API_KEY not found in environment.")
            self.openai_client = AsyncOpenAI(api_key=api_key, base_url=api_base) if api_key else None
            self.sync_openai_client = OpenAI(api_key=api_key, base_url=api_base) if api_key else None
        else:
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if api_key:
                genai.configure(api_key=api_key)
            else:
                print("Warning: GEMINI_API_KEY or GOOGLE_API_KEY not found in environment.")

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
                print(f"Error in DeepSeek LLM call: {e}")
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
                print(f"Error in Gemini LLM call: {e}")
                # Simple synchronous fallback if async fails or model mismatch
                try:
                    model = genai.GenerativeModel(model_name=model_name, system_instruction=self.system_instruction)
                    response = model.generate_content(prompt)
                    return response.text
                except Exception as sync_e:
                    return f"Error executing agent prompt: {sync_e}"
