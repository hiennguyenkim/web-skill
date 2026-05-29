import asyncio
from platform_core.core.skill_sdk import SkillServer, tool
from platform_core.core.llm.client import LLMClient

server = SkillServer("html-coder")
llm = LLMClient(system_instruction=(
    "You are the Creative Frontend Coder agent. Your role is to write clean, semantic HTML5 files "
    "(using header, nav, main, section, footer tags) and assign unique IDs to elements. "
    "You also write modular, modern ES6+ JavaScript to handle frontend states, click toggles, API fetches, "
    "and DOM rendering. You do not write styles, nor do you write inline styles or use <style> blocks in HTML files. "
    "You keep HTML completely clean of CSS, and hand off the HTML structure, classes, and IDs to the CSS Architect."
))

@tool
async def generate_html(name: str, prompt: str) -> str:
    """Generate clean semantic HTML5 layout for a web app."""
    coder_prompt = (
        f"Write a responsive HTML5 structure for '{name}'. "
        f"Context/Concept: {prompt}\n"
        "Integrate header, nav, main sections, a footer, and unique IDs. "
        "Include a link to 'index.css' and a script block or link to 'script.js' "
        "containing interactive DOM events (like nav toggles or slider logic). "
        "Do not embed CSS styles. "
        "Return ONLY the complete HTML code."
    )
    return await llm.call_llm(coder_prompt)

if __name__ == "__main__":
    server.run(transport="stdio")
