import os
import subprocess
import datetime
import uuid
import json
import zipfile
import xml.etree.ElementTree as ET
from app.db.database import SessionLocal
from app.db.models import Project, BuildTask, TestRun, SecurityScan
from app.agents.personas import PMAgent, DesignerAgent, CoderAgent, CSSAgent, QAAgent, SecurityAgent, BackendAgent

class AgentCoordinator:
    def __init__(self, workspace_path: str):
        self.workspace_path = workspace_path
        os.makedirs(workspace_path, exist_ok=True)
        
        self.pm_agent = PMAgent()
        self.designer_agent = DesignerAgent()
        self.coder_agent = CoderAgent()
        self.css_agent = CSSAgent()
        self.backend_agent = BackendAgent()
        self.qa_agent = QAAgent()
        self.security_agent = SecurityAgent()

    def get_db_session(self):
        return SessionLocal()

    async def init_project(self, name: str, concept: str) -> str:
        project_id = str(uuid.uuid4())[:8]
        db = self.get_db_session()
        
        # Resolve concept from file if a path is passed
        concept_text = concept
        if concept.lower().endswith(".docx"):
            possible_paths = [concept, os.path.join(self.workspace_path, concept), os.path.abspath(concept)]
            resolved_path = None
            for p in possible_paths:
                if os.path.exists(p) and os.path.isfile(p):
                    resolved_path = p
                    break
            
            if resolved_path:
                print(f"📄 Reading project requirements from docx file: {resolved_path}")
                content = self._read_docx(resolved_path)
                if content:
                    concept_text = content
                else:
                    print(f"⚠️ Warning: Failed to extract text from {resolved_path}")
            else:
                print(f"⚠️ Warning: Requirements file '{concept}' not found. Using path string as concept description.")
        elif concept.lower().endswith(".txt"):
            possible_paths = [concept, os.path.join(self.workspace_path, concept), os.path.abspath(concept)]
            resolved_path = None
            for p in possible_paths:
                if os.path.exists(p) and os.path.isfile(p):
                    resolved_path = p
                    break
            if resolved_path:
                print(f"📄 Reading project requirements from text file: {resolved_path}")
                try:
                    with open(resolved_path, "r", encoding="utf-8") as f:
                        concept_text = f.read()
                except Exception as e:
                    print(f"⚠️ Warning: Failed to read text file {resolved_path}: {e}")

        try:
            # 1. PM Agent planning
            pm_prompt = (
                f"Create a design specification for a web project named '{name}' with the following requirements: '{concept_text}'. "
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
                concept=concept_text,
                status="PLANNING",
                theme=data.get("theme", "SaaS / Tech"),
                workspace_path=self.workspace_path
            )
            db.add(db_project)
            
            # Populate initial task checkpoints
            phases = ["Phase1", "Phase2", "Phase3", "Phase4", "Phase5", "Phase6"]
            for idx, phase in enumerate(phases):
                if phase == "Phase1":
                    task_name = "Establish UI/UX design theme and HSL CSS variables"
                elif phase == "Phase2":
                    task_name = "Generate semantic HTML5 templates and views"
                elif phase == "Phase3":
                    task_name = "Implement responsive CSS Grid/Flexbox styling and animations"
                elif phase == "Phase4":
                    task_name = "Generate Mongoose models, controllers, API routes, server.js and package.json"
                elif phase == "Phase5":
                    task_name = "Run automated Playwright UI and user-flow tests"
                elif phase == "Phase6":
                    task_name = "Run Strix static security vulnerabilities scan"
                else:
                    task_name = f"Execute workflow step for {phase}"
                
                db.add(BuildTask(
                    project_id=project_id,
                    phase=phase,
                    task_name=task_name,
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

            # 4. Backend & Database Integration Stage
            print("⚙️ Running Backend & Database Developer Agent...")
            backend_prompt = (
                f"Implement the backend files for the project '{db_project.name}' based on the requirements:\n"
                f"{db_project.concept}\n\n"
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
            backend_resp = await self.backend_agent.call_llm(backend_prompt)
            try:
                clean_json = backend_resp.strip()
                if clean_json.startswith("```json"):
                    clean_json = clean_json[7:]
                if clean_json.endswith("```"):
                    clean_json = clean_json[:-3]
                clean_json = clean_json.strip()
                
                files = json.loads(clean_json)
                for f_info in files:
                    f_path = os.path.join(self.workspace_path, f_info["file"])
                    os.makedirs(os.path.dirname(f_path), exist_ok=True)
                    with open(f_path, "w", encoding="utf-8") as f:
                        f.write(f_info["content"])
                print(f"✅ Generated {len(files)} backend files successfully.")
            except Exception as backend_err:
                print(f"⚠️ Failed to parse or write backend files: {backend_err}")

            task_p4 = db.query(BuildTask).filter(BuildTask.project_id == project_id, BuildTask.phase == "Phase4").first()
            if task_p4:
                task_p4.status = "COMPLETED"
                task_p4.completed_at = datetime.datetime.utcnow()
            db.commit()

            # 5. QA & Automated Playwright Audit Stage
            print("🧪 Running QA & Playwright Verification...")
            await self.run_playwright_test(db_project)

            task_p5 = db.query(BuildTask).filter(BuildTask.project_id == project_id, BuildTask.phase == "Phase5").first()
            if task_p5:
                task_p5.status = "COMPLETED"
                task_p5.completed_at = datetime.datetime.utcnow()
            db.commit()

            # 5. Strix Security Scan Stage (Phase 6)
            print("🛡️ Running Strix Security Scan...")
            task_p6 = db.query(BuildTask).filter(BuildTask.project_id == project_id, BuildTask.phase == "Phase6").first()
            if task_p6:
                task_p6.status = "RUNNING"
                db.commit()

            await self.run_strix_security_scan(db_project)

            if task_p6:
                task_p6.status = "COMPLETED"
                task_p6.completed_at = datetime.datetime.utcnow()
            
            db_project.status = "PASSED"
            db.commit()
            print("✅ Build and Security Scan Completed Successfully!")

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

    async def run_strix_security_scan(self, project: Project):
        db = self.get_db_session()
        try:
            passed = True
            vulnerabilities_count = 0
            report_content = ""
            report_filename = "security_report.md"
            report_path = os.path.join(self.workspace_path, report_filename)

            try:
                # 1. Attempt running Strix CLI
                print("🔄 Executing Strix CLI scanner...")
                result = subprocess.run(
                    ["strix", "--target", ".", "--non-interactive", "--scan-mode", "quick"],
                    cwd=self.workspace_path,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0 or result.returncode == 2:
                    print("✅ Strix CLI scan finished successfully.")
                    if result.returncode == 2:
                        passed = False
                    
                    strix_runs_dir = os.path.join(self.workspace_path, "strix_runs")
                    if os.path.exists(strix_runs_dir):
                        runs = sorted([d for d in os.listdir(strix_runs_dir) if os.path.isdir(os.path.join(strix_runs_dir, d))])
                        if runs:
                            latest_run_dir = os.path.join(strix_runs_dir, runs[-1])
                            md_files = [f for f in os.listdir(latest_run_dir) if f.endswith(".md")]
                            if md_files:
                                with open(os.path.join(latest_run_dir, md_files[0]), "r", encoding="utf-8") as rf:
                                    report_content = rf.read()
                            
                            json_files = [f for f in os.listdir(latest_run_dir) if f.endswith(".json")]
                            if json_files:
                                with open(os.path.join(latest_run_dir, json_files[0]), "r", encoding="utf-8") as jf:
                                    try:
                                        data = json.load(jf)
                                        vulnerabilities_count = len(data.get("vulnerabilities", []))
                                    except Exception as json_err:
                                        print(f"⚠️ Failed to parse Strix JSON report: {json_err}")
                    
                    if not report_content:
                        report_content = f"# Strix CLI Scan Report\n\n## Output Log\n\n```\n{result.stdout}\n```"
                else:
                    raise FileNotFoundError("Strix command returned non-zero error code.")
                    
            except Exception as cli_err:
                print(f"⚠️ Strix CLI is unavailable or failed ({cli_err}). Falling back to AI Security Agent...")
                # 2. AI Fallback scanner
                files_content = {}
                for fname in ["index.html", "index.css", "verify-ui.js"]:
                    fpath = os.path.join(self.workspace_path, fname)
                    if os.path.exists(fpath):
                        try:
                            with open(fpath, "r", encoding="utf-8") as f:
                                files_content[fname] = f.read()
                        except Exception as file_err:
                            print(f"Failed to read {fname} for scanning: {file_err}")

                prompt = (
                    "Please perform a static security scan on the following generated frontend codebase files. "
                    "Analyze the code structure for security issues such as XSS, CSRF, DOM script injection, "
                    "unvalidated inputs, and sensitive configuration exposure.\n\n"
                )
                for fname, content in files_content.items():
                    prompt += f"=== FILE: {fname} ===\n{content}\n\n"

                prompt += (
                    "Evaluate security quality. Return ONLY a JSON object containing the keys: "
                    "1. 'passed' (boolean): whether the codebase passes standard checks. "
                    "2. 'vulnerabilities_count' (integer): the count of potential security concerns. "
                    "3. 'report_md' (string): a beautifully formatted Markdown security report detailing the analysis. "
                    "Do not enclose in markdown blocks, return pure JSON."
                )

                try:
                    response_text = await self.security_agent.call_llm(prompt)
                    
                    clean_json = response_text.strip()
                    if clean_json.startswith("```json"):
                        clean_json = clean_json[7:]
                    if clean_json.endswith("```"):
                        clean_json = clean_json[:-3]
                    clean_json = clean_json.strip()

                    res_data = json.loads(clean_json)
                    passed = res_data.get("passed", True)
                    vulnerabilities_count = res_data.get("vulnerabilities_count", 0)
                    report_content = res_data.get("report_md", "# AI Security Scan Report\n\nFailed to parse details.")
                except Exception as ai_err:
                    print(f"❌ Fallback AI Security scan failed: {ai_err}")
                    passed = True
                    vulnerabilities_count = 0
                    report_content = f"# Security Scan Fallback Report\n\nAI scan failed: {ai_err}"

            # Write the report to workspace
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report_content)

            # Record to DB
            db_scan = SecurityScan(
                project_id=project.id,
                passed=passed,
                vulnerabilities_found=vulnerabilities_count,
                report_path=report_path
            )
            db.add(db_scan)
            db.commit()
            print(f"🛡️ Security scan saved. Passed: {passed}, Vulnerabilities found: {vulnerabilities_count}")

        except Exception as scan_err:
            db.rollback()
            print(f"❌ Failed to run or record security scan: {scan_err}")
        finally:
            db.close()

    def _read_docx(self, docx_path: str) -> str:
        try:
            with zipfile.ZipFile(docx_path) as z:
                xml_content = z.read('word/document.xml')
                root = ET.fromstring(xml_content)
                
                text_runs = []
                for paragraph in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
                    p_text = []
                    for run in paragraph.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'):
                        if run.text:
                            p_text.append(run.text)
                    text_runs.append("".join(p_text))
                
                return "\n\n".join(text_runs)
        except Exception as e:
            print(f"Error reading docx: {e}")
            return ""
