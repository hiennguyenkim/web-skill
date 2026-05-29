import asyncio
from platform_core.core.skill_sdk import SkillServer, tool
from platform_core.core.llm.client import LLMClient

server = SkillServer("css-expert")
llm_designer = LLMClient(system_instruction=(
    "You are the UI/UX Designer agent. Your role is to select harmonized HSL color variables, "
    "google typography (Outfit, Inter, Playfair Display), glassmorphic shadow/blur tokens, "
    "and design background grid structures. You must output these parameters directly into PROJECT.md "
    "and hand them off to the Frontend Coder. You also guide asset creation."
))
llm_css = LLMClient(system_instruction=(
    "You are the Responsive CSS Architect agent. Your role is to write modular CSS styles "
    "in separate, dedicated stylesheets (e.g. public/css/style.css, public/css/dashboard.css). "
    "You never write inline CSS or include CSS inside <style> blocks in HTML files. "
    "You write styles using advanced CSS Grid, Flexbox, transitions (all 0.3s ease-in-out), custom scrollbars, "
    "glassmorphism overlays (backdrop-filter: blur), hover scales, and CSS keyframe animations. "
    "You target semantic classes and IDs assigned by the Coder. You do not use Tailwind CSS. "
    "You guarantee layout responsiveness for Mobile (375px), Tablet (768px), and Desktop (1280px) viewports."
))

@tool
async def generate_css_variables(name: str, theme: str) -> str:
    """Generate design system tokens and root HSL CSS variables based on theme name."""
    design_prompt = (
        f"Design CSS variables and assets for project '{name}' themed '{theme}'. "
        "Create design specifications that we will write to index.css. "
        "Output a stylesheet containing root variables, glassmorphic layout tokens, and body fonts. "
        "Return ONLY CSS code."
    )
    return await llm_designer.call_llm(design_prompt)

@tool
async def upgrade_css_styles(name: str, existing_variables: str) -> str:
    """Upgrade CSS styles to add full responsive viewports, keyframe animations, scrollbars, and hover effects."""
    css_prompt = (
        "Upgrade our current index.css stylesheet to implement full responsive designs "
        "(Desktop, Mobile, Tablet viewports), hover animations, and glassmorphic card grids. "
        "Ensure scrollbar stylings and fadeIn animation keyframes are included. "
        f"Here is the existing styling:\n{existing_variables}\n"
        "Return ONLY the upgraded CSS content."
    )
    return await llm_css.call_llm(css_prompt)

if __name__ == "__main__":
    server.run(transport="stdio")
