import os
import subprocess
import datetime
import uuid
import json
from app.db.database import SessionLocal
from app.db.models import Project, BuildTask, TestRun
from app.agents.personas import PMAgent, DesignerAgent, CoderAgent, CSSAgent, QAAgent

class AgentCoordinator:
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        os.makedirs(workspace_path, exist_ok=True)
        
        self.pm_agent = PMAgent()
        self.designer_agent = DesignerAgent()
        self.coder_agent = CoderAgent()
        self.css_agent = CSSAgent()
        self.qa_agent = QAAgent()

    def get_db_session(self):
        return SessionLocal()

    async def init_project(self, name: str, concept: str) -> str:
        project_id = str(uuid.uuid4())[:8]
        db = self.get_db_session()
        
        try:
            # 1. PM Agent planning
            pm_prompt = (
                f"Create a design specification for a web project named '{name}' with the following requirements: '{concept}'. "
                "Structure your output as a JSON containing: "
                "1. 'theme': Suggested visual theme name. "
                "2. 'project_md': Complete content for PROJECT.md. "
                "3. 'roadmap_md': Complete content for ROADMAP.md. "
                "4. 'state_md': Complete content for STATE.md. "
                "Return ONLY a clean JSON object, no markdown wrappers."
            )
            llm_response = await self.pm_agent.call_llm(pm_prompt)
            
            # Clean response if LLM added code blocks
            clean_json = llm_response.strip()
            if clean_json.startswith("```json"):
                clean_json = clean_json[7:]
            if clean_json.endswith("```"):
                clean_json = clean_json[:-3]
            clean_json = clean_json.strip()
            
            data = json.loads(clean_json)
            
            # Write files to workspace
            with open(os.path.join(self.workspace_path, "PROJECT.md"), "w", encoding="utf-8") as f:
                f.write(data.get("project_md", ""))
            with open(os.path.join(self.workspace_path, "ROADMAP.md"), "w", encoding="utf-8") as f:
                f.write(data.get("roadmap_md", ""))
            with open(os.path.join(self.workspace_path, "STATE.md"), "w", encoding="utf-8") as f:
                f.write(data.get("state_md", ""))

            # Register Project in SQLite
            db_project = Project(
                id=project_id,
                name=name,
                concept=concept,
                status="PLANNING",
                theme=data.get("theme", "SaaS / Tech"),
                workspace_path=self.workspace_path
            )
            db.add(db_project)
            
            # Populate initial task checkpoints
            phases = ["Phase1", "Phase2", "Phase3", "Phase4", "Phase5"]
            for idx, phase in enumerate(phases):
                db.add(BuildTask(
                    project_id=project_id,
                    phase=phase,
                    task_name=f"Execute workflow step for {phase}",
                    status="PENDING"
                ))
            
            db.commit()
            return project_id
        except Exception as e:
            db.rollback()
            print(f"❌ Error during project initialization: {e}")
            raise e
        finally:
            db.close()

    async def build_project(self, project_id: str):
        db = self.get_db_session()
        db_project = db.query(Project).filter(Project.id == project_id).first()
        if not db_project:
            db.close()
            raise ValueError(f"Project {project_id} not found")
        
        db_project.status = "BUILDING"
        db.commit()

        try:
            # 1. Designer Stage
            print("🎨 Running UI/UX Designer Agent...")
            design_prompt = (
                f"Design CSS variables and assets for project '{db_project.name}' themed '{db_project.theme}'. "
                "Create design specifications that we will write to index.css. "
                "Output a stylesheet containing root variables, glassmorphic layout tokens, and body fonts. "
                "Return ONLY CSS code."
            )
            css_variables = await self.designer_agent.call_llm(design_prompt)
            with open(os.path.join(self.workspace_path, "index.css"), "w", encoding="utf-8") as f:
                f.write(css_variables)
            
            # Update Phase 1 task
            task_p1 = db.query(BuildTask).filter(BuildTask.project_id == project_id, BuildTask.phase == "Phase1").first()
            if task_p1:
                task_p1.status = "COMPLETED"
                task_p1.completed_at = datetime.datetime.utcnow()
            db.commit()

            # 2. Coder Stage (HTML + JS)
            print("🧱 Running Creative Frontend Coder Agent...")
            coder_prompt = (
                f"Write a responsive HTML5 structure for '{db_project.name}'. "
                "Integrate header, nav, main sections, a footer, and unique IDs. "
                "Include a link to 'index.css' and a script block or link to 'script.js' "
                "containing interactive DOM events (like nav toggles or slider logic). "
                "Return ONLY the complete HTML code."
            )
            html_code = await self.coder_agent.call_llm(coder_prompt)
            with open(os.path.join(self.workspace_path, "index.html"), "w", encoding="utf-8") as f:
                f.write(html_code)

            task_p2 = db.query(BuildTask).filter(BuildTask.project_id == project_id, BuildTask.phase == "Phase2").first()
            if task_p2:
                task_p2.status = "COMPLETED"
                task_p2.completed_at = datetime.datetime.utcnow()
            db.commit()

            # 3. CSS Architect Stage
            print("💎 Running Responsive CSS Architect Agent...")
            css_prompt = (
                "Upgrade our current index.css stylesheet to implement full responsive designs "
                "(Desktop, Mobile, Tablet viewports), hover animations, and glassmorphic card grids. "
                "Ensure scrollbar stylings and fadeIn animation keyframes are included. "
                f"Here is the existing styling:\n{css_variables}\n"
                "Return ONLY the upgraded CSS content."
            )
            full_css = await self.css_agent.call_llm(css_prompt)
            with open(os.path.join(self.workspace_path, "index.css"), "w", encoding="utf-8") as f:
                f.write(full_css)

            task_p3 = db.query(BuildTask).filter(BuildTask.project_id == project_id, BuildTask.phase == "Phase3").first()
            if task_p3:
                task_p3.status = "COMPLETED"
                task_p3.completed_at = datetime.datetime.utcnow()
            db.commit()

            # 4. QA & Automated Playwright Audit Stage
            print("🧪 Running QA & Playwright Verification...")
            await self.run_playwright_test(db_project)

            # Update Phase 4 & 5
            for phase in ["Phase4", "Phase5"]:
                task = db.query(BuildTask).filter(BuildTask.project_id == project_id, BuildTask.phase == phase).first()
                if task:
                    task.status = "COMPLETED"
                    task.completed_at = datetime.datetime.utcnow()
            
            db_project.status = "PASSED"
            db.commit()
            print("✅ Build Completed Successfully!")

        except Exception as e:
            db_project.status = "FAILED"
            db.commit()
            print(f"❌ Build Failed: {e}")
            raise e
        finally:
            db.close()

    async def run_playwright_test(self, project: Project):
        db = self.get_db_session()
        
        try:
            # 1. Copy verification script template
            template_path = path_to_template = os.path.join(
                os.path.dirname(__file__), "..", "templates", "playwright-template.js"
            )
            # Fallback pathing
            if not os.path.exists(template_path):
                template_path = os.path.join("d:\\ai-web-skill", ".gemini", "skills", "web-creator", "templates", "playwright-template.js")
            
            dest_path = os.path.join(self.workspace_path, "verify-ui.js")
            
            with open(template_path, "r", encoding="utf-8") as tf:
                script_content = tf.read()
            with open(dest_path, "w", encoding="utf-8") as df:
                df.write(script_content)
            
            # 2. Subprocess execution (OpenHands loop)
            max_retries = 3
            for iteration in range(max_retries):
                print(f"🔄 Run Playwright verification attempt {iteration + 1}...")
                result = subprocess.run(
                    ["node", "verify-ui.js"], 
                    cwd=self.workspace_path,
                    capture_output=True,
                    text=True
                )
                
                # Check outcome
                passed = (result.returncode == 0)
                print(result.stdout)
                
                if passed:
                    # Save run results in SQLite
                    db.add(TestRun(
                        project_id=project.id,
                        passed=True,
                        console_violations=0,
                        report_path=os.path.join(self.workspace_path, "assets", "test_report.html")
                    ))
                    db.commit()
                    return
                else:
                    print(f"⚠️ Verification Failed:\n{result.stderr}")
                    if iteration < max_retries - 1:
                        print("🤖 Entering Self-Healing Diagnostics Loop...")
                        # Run targeted fix using LLM forensics
                        await self.auto_repair(result.stderr or result.stdout)
                    else:
                        db.add(TestRun(
                            project_id=project.id,
                            passed=False,
                            console_violations=1,
                            report_path=None
                        ))
                        db.commit()
                        raise RuntimeError("Playwright test suite failed after maximum self-healing retries.")
        finally:
            db.close()

    async def auto_repair(self, error_logs: str):
        print("🔧 Auto-repairing files based on audit tracebacks...")
        # PM/Forensics Agent constructs patches
        forensics_prompt = (
            "You are a Forensics Specialist. Analyze these browser execution logs and tracebacks:\n"
            f"{error_logs}\n"
            "Produce clean corrected patches or scripts to fix index.html or index.css. "
            "Output the file modifications directly. Return JSON format containing keys 'file' and 'content' to rewrite."
        )
        repair_resp = await self.pm_agent.call_llm(forensics_prompt)
        try:
            clean_json = repair_resp.strip()
            if clean_json.startswith("```json"):
                clean_json = clean_json[7:]
            if clean_json.endswith("```"):
                clean_json = clean_json[:-3]
            clean_json = clean_json.strip()
            
            patch = json.loads(clean_json)
            target_file = patch.get("file", "index.html")
            with open(os.path.join(self.workspace_path, target_file), "w", encoding="utf-8") as f:
                f.write(patch.get("content", ""))
            print(f"🔧 Patched {target_file} successfully.")
        except Exception as repair_err:
            print(f"❌ Failed to parse and apply repair patch: {repair_err}")
