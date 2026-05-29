import json
from platform_core.core.skill_sdk import SkillServer, tool
from platform_core.core.llm.client import LLMClient

server = SkillServer("po-toolkit")
llm = LLMClient(system_instruction=(
    "You are an Elite Product Owner agent (PO Toolkit). Your role is to analyze project requirements, "
    "generate professional User Stories, manage and prioritize backlogs, estimate development efforts, "
    "and break down requirements into clear technical tasks. "
    "You communicate clearly, logically, and structure your data following precise JSON contracts "
    "or highly readable Markdown."
))

@tool
async def generate_user_story(requirement: str) -> str:
    """Generate professional User Stories from raw requirements text.
    Each user story follows the standard template: 'As a... I want to... So that...'
    along with clear Acceptance Criteria.
    """
    prompt = (
        f"Read the following project requirements and extract them into a list of structured User Stories:\n"
        f"{requirement}\n\n"
        "Each User Story must contain:\n"
        "- Title: Short descriptive title.\n"
        "- Persona: The role/actor (e.g. Guest, Customer, Admin, Staff).\n"
        "- Want: What action they want to perform.\n"
        "- Benefit: The business value or reason.\n"
        "- AcceptanceCriteria: A bulleted list of acceptance criteria (e.g. Given... When... Then...)./behavior validations.\n\n"
        "Return your response as a JSON array of stories. Return ONLY the clean JSON, no markdown code block wrappers."
    )
    return await llm.call_llm(prompt)

@tool
async def prioritize_backlog(backlog_json: str) -> str:
    """Prioritize a list of user stories based on Business Value, Effort, and risk.
    Applies the MoSCoW methodology (Must have, Should have, Could have, Won't have)
    or WSJF (Weighted Shortest Job First).
    Input backlog_json must be a JSON array of user stories.
    """
    prompt = (
        f"Analyze this backlog of user stories:\n{backlog_json}\n\n"
        "Prioritize them using the MoSCoW method and assign each story:\n"
        "- Priority: Must, Should, Could, or Won't.\n"
        "- BusinessValue: Score from 1 to 10 (10 being highest).\n"
        "- TechnicalRisk: Score from 1 to 10 (10 being highest).\n"
        "- Rationale: A brief sentence justifying the priority level.\n\n"
        "Sort the backlog with 'Must' have items first, then 'Should', then 'Could'.\n"
        "Return the sorted list as a JSON array of objects containing the original story fields plus "
        "priority, business value, technical risk, and rationale. Return ONLY the clean JSON."
    )
    return await llm.call_llm(prompt)

@tool
async def estimate_effort(stories_json: str) -> str:
    """Estimate implementation effort (in Story Points: 1, 2, 3, 5, 8, 13) for each user story.
    Input stories_json must be a JSON array of stories.
    """
    prompt = (
        f"Estimate the implementation effort for each of these user stories:\n{stories_json}\n\n"
        "Assign to each story:\n"
        "- StoryPoints: Fibonacci number (1, 2, 3, 5, 8, 13).\n"
        "- ComplexityRationale: A short explanation of the complexity (e.g. database schema changes, frontend styling, third-party API integration).\n\n"
        "Return the updated JSON array containing the original stories plus 'story_points' and 'complexity_rationale'. Return ONLY clean JSON."
    )
    return await llm.call_llm(prompt)

@tool
async def breakdown_tasks(story_json: str) -> str:
    """Break down a single user story into concrete technical sub-tasks for developers.
    Input story_json must be a JSON object representing a single user story.
    """
    prompt = (
        f"Break down the following user story into technical tasks for developers:\n{story_json}\n\n"
        "Generate tasks covering:\n"
        "- Database: schema/model changes (Mongoose).\n"
        "- API/Backend: routes, controllers, middleware (Express).\n"
        "- Frontend: views/HTML, interactivity/JS, style/CSS.\n"
        "- QA/Testing: Playwright assertions, verification checks.\n\n"
        "Return your response as a JSON array of task objects, where each object has:\n"
        "- Type: 'Database', 'API', 'Frontend', or 'QA'.\n"
        "- TaskName: A short descriptive task name.\n"
        "- Description: What needs to be implemented.\n"
        "- EstimatedHours: Simple hour estimation.\n\n"
        "Return ONLY the clean JSON array of tasks."
    )
    return await llm.call_llm(prompt)

if __name__ == "__main__":
    server.run(transport="stdio")
