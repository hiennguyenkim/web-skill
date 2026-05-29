import asyncio
from core.skill_sdk import SkillServer, tool
from core.llm.client import LLMClient

server = SkillServer("backend-generator")
llm = LLMClient(system_instruction=(
    "You are the Backend and Database Developer agent. Your role is to write clean, secure "
    "Node.js server.js, Mongoose schemas under models/, Express API routes under routes/, "
    "authentication/authorization middlewares under middleware/, and MVC controller logic under controllers/. "
    "You ensure proper API connections, input validation, bcrypt password hashing, and jsonwebtoken session handling."
))

@tool
async def generate_backend(name: str, concept: str) -> str:
    """Generate Node.js Express.js MVC backend implementation files (models, controllers, routes, db config, and server.js) in JSON format."""
    backend_prompt = (
        f"Implement the backend files for the project '{name}' based on the requirements:\n"
        f"{concept}\n\n"
        "You must write the full, working implementation (no placeholders) for the following backend files:\n"
        "1. All Mongoose models under the 'models/' directory (e.g. User.js, Product.js, etc. as specified in the schema requirements).\n"
        "2. All Express routes under the 'routes/' directory (e.g. authRoutes.js, productRoutes.js).\n"
        "3. All controller files under the 'controllers/' directory (e.g. authController.js, productController.js).\n"
        "4. A MongoDB connection utility file at 'config/db.js'.\n"
        "5. The main entry point Express server 'server.js' that connects to the database, imports routes, serves static public assets and views directories, and listens on a port.\n"
        "6. A package.json file with express, mongoose, dotenv, cors, jsonwebtoken, bcryptjs, etc.\n"
        "Output your response as a JSON array where each item is an object with 'file' (the relative file path, e.g., 'models/User.js') and 'content' (the complete source code text).\n"
        "Return ONLY the clean JSON array of files. Do not wrap in markdown or include backticks."
    )
    return await llm.call_llm(backend_prompt)

if __name__ == "__main__":
    server.run(transport="stdio")
