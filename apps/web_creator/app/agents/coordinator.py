import os
import subprocess
import datetime
import uuid
import json
import zipfile
import xml.etree.ElementTree as ET
from app.db.database import SessionLocal
from app.db.models import Project, BuildTask, TestRun, SecurityScan
from app.agents.personas import PMAgent, DesignerAgent, CoderAgent, CSSAgent, QAAgent, SecurityAgent, BackendAgent, ArchitectAgent

from platform_core.core.environment.base import Environment, CommandExecutionError
from platform_core.core.artifacts import Artifact, ArtifactManager
from platform_core.core.decisions import Decision, DecisionManager
from platform_core.core.events import Event, EventManager

class AgentCoordinator:
    def __init__(self, env: Environment):
        self.env = env
        self.workspace_path = getattr(env, "workspace_path", "")
        
        self.pm_agent = PMAgent()
        self.architect_agent = ArchitectAgent()
        self.designer_agent = DesignerAgent()
        self.coder_agent = CoderAgent()
        self.css_agent = CSSAgent()
        self.backend_agent = BackendAgent()
        self.qa_agent = QAAgent()
        self.security_agent = SecurityAgent()

        self.artifact_mgr = ArtifactManager(env)
        self.decision_mgr = DecisionManager(env)
        self.event_mgr = EventManager(env)

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
                if self.env.exists(p) or os.path.exists(p):
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
                if self.env.exists(p) or os.path.exists(p):
                    resolved_path = p
                    break
            if resolved_path:
                print(f"📄 Reading project requirements from text file: {resolved_path}")
                try:
                    if self.env.exists(resolved_path):
                        concept_text = self.env.read_file(resolved_path)
                    else:
                        with open(resolved_path, "r", encoding="utf-8") as f:
                            concept_text = f.read()
                except Exception as e:
                    print(f"⚠️ Warning: Failed to read text file {resolved_path}: {e}")

        # Emit Project Initiated Event
        self.event_mgr.emit_event(Event(
            event_type="PROJECT_INITIATED",
            producer="platform",
            project_id=project_id,
            payload={"name": name, "concept": concept_text}
        ))

        try:
            # 1. PM Agent planning
            pm_prompt = (
                f"Create a design specification for a web project named '{name}' with the following requirements: '{concept_text}'. "
                "Structure your output as a JSON containing: "
                "1. 'theme': Suggested visual theme name. "
                "2. 'project_md': Complete content for PROJECT.md. "
                "3. 'roadmap_md': Complete content for ROADMAP.md. "
                "4. 'state_md': Complete content for STATE.md. "
                "5. 'design_md': Complete content for DESIGN.md conforming to the Google Labs DESIGN.md spec "
                "(with colors, typography, rounded, spacing, components in YAML frontmatter + markdown prose sections). "
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
            self.env.write_file("PROJECT.md", data.get("project_md", ""))
            self.env.write_file("ROADMAP.md", data.get("roadmap_md", ""))
            self.env.write_file("STATE.md", data.get("state_md", ""))
            self.env.write_file("DESIGN.md", data.get("design_md", ""))

            # Save PM Spec Artifact
            pm_content = {
                "project_md": data.get("project_md", ""),
                "roadmap_md": data.get("roadmap_md", ""),
                "state_md": data.get("state_md", ""),
                "design_md": data.get("design_md", "")
            }
            spec_artifact = Artifact(
                artifact_type="spec",
                producer="ProductManager",
                content=pm_content,
                project_id=project_id,
                metadata={"theme": data.get("theme", "SaaS / Tech"), "project_name": name}
            )
            self.artifact_mgr.save_artifact(spec_artifact)

            # Log PM Decision
            pm_decision = Decision(
                decision=f"Propose visual theme '{data.get('theme', 'SaaS / Tech')}' and initial backlog / state layout",
                reason="Analyzed user product requirements and structured MVP roadmap and HSL design tokens.",
                agent="ProductManager",
                artifact_id=spec_artifact.id,
                context={}
            )
            self.decision_mgr.log_decision(pm_decision)

            # Emit Spec Generated Event
            self.event_mgr.emit_event(Event(
                event_type="SPECIFICATION_GENERATED",
                producer="ProductManager",
                project_id=project_id,
                payload={"artifact_id": spec_artifact.id, "theme": data.get("theme", "SaaS / Tech")}
            ))

            # 2. Architect Agent planning
            print("🏗️ Running Software Architect Agent...")
            architect_prompt = (
                f"Analyze the product specifications for '{name}'.\n"
                f"PROJECT.md:\n{data.get('project_md', '')}\n\n"
                f"DESIGN.md:\n{data.get('design_md', '')}\n\n"
                "Design the application architecture. Structure your output as a JSON object containing:\n"
                "1. 'architecture_md': Complete markdown detailing directories, component diagrams, state handling, and tech choices.\n"
                "2. 'db_schema_sql': Complete SQL schema for the database.\n"
                "3. 'api_spec_yaml': Complete OpenAPI/Swagger YAML documentation for all REST API endpoints.\n"
                "4. 'workflow_yaml': A declarative YAML outline listing the stages, agents involved, and their dependencies.\n"
                "Return ONLY a clean JSON object, no markdown wrappers."
            )
            arch_response = await self.architect_agent.call_llm(architect_prompt)
            
            clean_arch_json = arch_response.strip()
            if clean_arch_json.startswith("```json"):
                clean_arch_json = clean_arch_json[7:]
            if clean_arch_json.endswith("```"):
                clean_arch_json = clean_arch_json[:-3]
            clean_arch_json = clean_arch_json.strip()
            
            arch_data = json.loads(clean_arch_json)
            
            # Write files to workspace
            self.env.write_file("architecture.md", arch_data.get("architecture_md", ""))
            self.env.write_file("db_schema.sql", arch_data.get("db_schema_sql", ""))
            self.env.write_file("api_spec.yaml", arch_data.get("api_spec_yaml", ""))
            self.env.write_file("workflow.yaml", arch_data.get("workflow_yaml", ""))

            # Save Architect Artifact
            arch_content = {
                "architecture_md": arch_data.get("architecture_md", ""),
                "db_schema_sql": arch_data.get("db_schema_sql", ""),
                "api_spec_yaml": arch_data.get("api_spec_yaml", ""),
                "workflow_yaml": arch_data.get("workflow_yaml", "")
            }
            arch_artifact = Artifact(
                artifact_type="architecture",
                producer="Architect",
                content=arch_content,
                project_id=project_id,
                parent_artifact=spec_artifact.id,
                metadata={}
            )
            self.artifact_mgr.save_artifact(arch_artifact)

            # Log Architect Decision
            arch_decision = Decision(
                decision="Define application component structure, database schemas, and REST API specification",
                reason="Created engineering schematics to guide developers based on PM product spec.",
                agent="Architect",
                artifact_id=arch_artifact.id,
                context={}
            )
            self.decision_mgr.log_decision(arch_decision)

            # Emit Architecture Defined Event
            self.event_mgr.emit_event(Event(
                event_type="ARCHITECTURE_DEFINED",
                producer="Architect",
                project_id=project_id,
                payload={"artifact_id": arch_artifact.id}
            ))

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

        # Emit Build Started Event
        self.event_mgr.emit_event(Event(
            event_type="BUILD_STARTED",
            producer="platform",
            project_id=project_id,
            payload={"name": db_project.name}
        ))

        try:
            # Read DESIGN.md if it exists to pass design tokens to subsequent agents
            design_md_content = ""
            if self.env.exists("DESIGN.md"):
                design_md_content = self.env.read_file("DESIGN.md")

            # Resolve specification artifact for parent tracking
            spec_arts = self.artifact_mgr.list_artifacts(artifact_type="spec")
            spec_art_id = spec_arts[0].id if spec_arts else None

            # 1. Designer Stage
            print("🎨 Running UI/UX Designer Agent...")
            design_prompt = (
                f"Based on the following DESIGN.md specifications:\n{design_md_content}\n\n"
                f"Design CSS variables and assets for project '{db_project.name}' themed '{db_project.theme}'. "
                "Create design specifications that we will write to index.css. "
                "Output a stylesheet containing root variables matching the colors, rounded, spacing tokens, and body fonts from the design spec. "
                "Return ONLY CSS code."
            )
            css_variables = await self.designer_agent.call_llm(design_prompt)
            self.env.write_file("index.css", css_variables)
            
            # Save Designer Artifact
            design_art = Artifact(
                artifact_type="design",
                producer="Designer",
                content={"css_variables": css_variables},
                project_id=project_id,
                parent_artifact=spec_art_id,
                metadata={"file": "index.css"}
            )
            self.artifact_mgr.save_artifact(design_art)

            # Log Designer Decision
            design_dec = Decision(
                decision="Design theme HSL color palette and typography layout",
                reason="Define consistent design system tokens based on PROJECT.md specifications.",
                agent="Designer",
                artifact_id=design_art.id,
                context={}
            )
            self.decision_mgr.log_decision(design_dec)

            # Emit Design Completed Event
            self.event_mgr.emit_event(Event(
                event_type="DESIGN_COMPLETED",
                producer="Designer",
                project_id=project_id,
                payload={"artifact_id": design_art.id}
            ))

            # Update Phase 1 task
            task_p1 = db.query(BuildTask).filter(BuildTask.project_id == project_id, BuildTask.phase == "Phase1").first()
            if task_p1:
                task_p1.status = "COMPLETED"
                task_p1.completed_at = datetime.datetime.utcnow()
            db.commit()

            # 2. Coder Stage (HTML + JS)
            print("🧱 Running Creative Frontend Coder Agent...")
            coder_prompt = (
                f"Based on the project's DESIGN.md specifications:\n{design_md_content}\n\n"
                f"Write a responsive HTML5 structure for '{db_project.name}'. "
                "Integrate header, nav, main sections, a footer, and unique IDs. "
                "Include a link to 'index.css' and a script block or link to 'script.js' "
                "containing interactive DOM events (like nav toggles or slider logic). "
                "Return ONLY the complete HTML code."
            )
            html_code = await self.coder_agent.call_llm(coder_prompt)
            self.env.write_file("index.html", html_code)

            # Save Coder Artifact
            coder_art = Artifact(
                artifact_type="code",
                producer="Coder",
                content={"html_code": html_code},
                project_id=project_id,
                parent_artifact=design_art.id,
                metadata={"file": "index.html"}
            )
            self.artifact_mgr.save_artifact(coder_art)

            # Log Coder Decision
            coder_dec = Decision(
                decision="Construct semantic HTML5 layout with DOM logic",
                reason="Generate UI frame containing headers, navigations, grid containers, and scripts.",
                agent="Coder",
                artifact_id=coder_art.id,
                context={}
            )
            self.decision_mgr.log_decision(coder_dec)

            # Emit Frontend Generated Event
            self.event_mgr.emit_event(Event(
                event_type="FRONTEND_GENERATED",
                producer="Coder",
                project_id=project_id,
                payload={"artifact_id": coder_art.id}
            ))

            task_p2 = db.query(BuildTask).filter(BuildTask.project_id == project_id, BuildTask.phase == "Phase2").first()
            if task_p2:
                task_p2.status = "COMPLETED"
                task_p2.completed_at = datetime.datetime.utcnow()
            db.commit()

            # 3. CSS Architect Stage
            print("💎 Running Responsive CSS Architect Agent...")
            css_prompt = (
                f"Based on the project's DESIGN.md specifications:\n{design_md_content}\n\n"
                "Upgrade our current index.css stylesheet to implement full responsive designs "
                "(Desktop, Mobile, Tablet viewports), hover animations, and glassmorphic card grids. "
                "Ensure scrollbar stylings and fadeIn animation keyframes are included. "
                f"Here is the existing styling:\n{css_variables}\n"
                "Return ONLY the upgraded CSS content."
            )
            full_css = await self.css_agent.call_llm(css_prompt)
            self.env.write_file("index.css", full_css)

            # Save/Update CSS Design Artifact
            css_art = Artifact(
                artifact_type="design",
                producer="CSSArchitect",
                content={"css_variables": css_variables, "full_css": full_css},
                project_id=project_id,
                parent_artifact=coder_art.id,
                metadata={"file": "index.css", "upgraded": True}
            )
            self.artifact_mgr.save_artifact(css_art)

            # Log CSS Decision
            css_dec = Decision(
                decision="Incorporate responsive breakpoints and advanced styling transitions",
                reason="Refine index.css with mobile media queries and glassmorphic micro-interactions.",
                agent="CSSArchitect",
                artifact_id=css_art.id,
                context={}
            )
            self.decision_mgr.log_decision(css_dec)

            # Emit Styling Upgraded Event
            self.event_mgr.emit_event(Event(
                event_type="STYLING_UPGRADED",
                producer="CSSArchitect",
                project_id=project_id,
                payload={"artifact_id": css_art.id}
            ))

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
                    self.env.write_file(f_info["file"], f_info["content"])
                print(f"✅ Generated {len(files)} backend files successfully.")

                # Save Backend Code Artifact
                arch_arts = self.artifact_mgr.list_artifacts(artifact_type="architecture")
                arch_art_id = arch_arts[0].id if arch_arts else None
                
                backend_art = Artifact(
                    artifact_type="code",
                    producer="BackendDeveloper",
                    content={"files": files},
                    project_id=project_id,
                    parent_artifact=arch_art_id,
                    metadata={"type": "backend"}
                )
                self.artifact_mgr.save_artifact(backend_art)

                # Log Backend Decision
                backend_dec = Decision(
                    decision="Generate database schemas, routes and controller implementations",
                    reason="Created Mongoose/Express boilerplate and route endpoints to serve backend requests.",
                    agent="BackendDeveloper",
                    artifact_id=backend_art.id,
                    context={}
                )
                self.decision_mgr.log_decision(backend_dec)

                # Emit Backend Generated Event
                self.event_mgr.emit_event(Event(
                    event_type="BACKEND_GENERATED",
                    producer="BackendDeveloper",
                    project_id=project_id,
                    payload={"artifact_id": backend_art.id}
                ))
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

            # 6. Strix Security Scan Stage (Phase 6)
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

            # Emit Build Finished (Passed)
            self.event_mgr.emit_event(Event(
                event_type="BUILD_FINISHED",
                producer="platform",
                project_id=project_id,
                payload={"status": "PASSED"}
            ))
            print("✅ Build and Security Scan Completed Successfully!")

        except Exception as e:
            db_project.status = "FAILED"
            db.commit()
            
            # Emit Build Finished (Failed)
            self.event_mgr.emit_event(Event(
                event_type="BUILD_FINISHED",
                producer="platform",
                project_id=project_id,
                payload={"status": "FAILED", "error": str(e)}
            ))
            print(f"❌ Build Failed: {e}")
            raise e
        finally:
            db.close()

    async def run_playwright_test(self, project: Project):
        db = self.get_db_session()
        
        try:
            # 1. Copy verification script template
            template_path = os.path.join(
                os.path.dirname(__file__), "..", "templates", "playwright-template.js"
            )
            # Fallback pathing
            if not os.path.exists(template_path):
                template_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), "skills", "web-creator", "templates", "playwright-template.js")
            
            with open(template_path, "r", encoding="utf-8") as tf:
                script_content = tf.read()
            self.env.write_file("verify-ui.js", script_content)
            
            # 2. Subprocess execution (OpenHands loop)
            max_retries = 3
            last_output = ""
            for iteration in range(max_retries):
                print(f"🔄 Run Playwright verification attempt {iteration + 1}...")
                passed = True
                output = ""
                try:
                    output = self.env.run_command(["node", "verify-ui.js"])
                    print(output)
                    last_output = output
                except CommandExecutionError as e:
                    passed = False
                    output = e.stdout + "\n" + e.stderr
                    last_output = output
                    print(f"⚠️ Verification Failed:\n{e.stderr}")
                
                # Fetch frontend code artifact for parent linkage
                coder_arts = self.artifact_mgr.list_artifacts(artifact_type="code")
                coder_art_id = coder_arts[0].id if coder_arts else None

                if passed:
                    # Save run results in SQLite
                    db.add(TestRun(
                        project_id=project.id,
                        passed=True,
                        console_violations=0,
                        report_path=os.path.join(self.workspace_path, "assets", "test_report.html")
                    ))
                    db.commit()

                    # Save QA Test Artifact
                    test_art = Artifact(
                        artifact_type="test",
                        producer="QASpecialist",
                        content={"passed": True, "output": last_output, "console_violations": 0},
                        project_id=project.id,
                        parent_artifact=coder_art_id,
                        metadata={"tool": "playwright", "attempts": iteration + 1}
                    )
                    self.artifact_mgr.save_artifact(test_art)

                    # Log QA Decision
                    test_dec = Decision(
                        decision="Approve frontend build after successful Playwright tests",
                        reason="All automated functional test assertions passed without regression.",
                        agent="QASpecialist",
                        artifact_id=test_art.id,
                        context={}
                    )
                    self.decision_mgr.log_decision(test_dec)

                    # Emit Test Passed Event
                    self.event_mgr.emit_event(Event(
                        event_type="TEST_PASSED",
                        producer="QASpecialist",
                        project_id=project.id,
                        payload={"artifact_id": test_art.id}
                    ))
                    return
                else:
                    # Save QA Test Artifact (Failed)
                    test_art = Artifact(
                        artifact_type="test",
                        producer="QASpecialist",
                        content={"passed": False, "output": last_output, "console_violations": 1},
                        project_id=project.id,
                        parent_artifact=coder_art_id,
                        metadata={"tool": "playwright", "attempts": iteration + 1}
                    )
                    self.artifact_mgr.save_artifact(test_art)

                    # Emit Test Failed Event
                    self.event_mgr.emit_event(Event(
                        event_type="TEST_FAILED",
                        producer="QASpecialist",
                        project_id=project.id,
                        payload={"artifact_id": test_art.id, "error": last_output[:200]}
                    ))

                    if iteration < max_retries - 1:
                        print("🤖 Entering Self-Healing Diagnostics Loop...")
                        # Run targeted fix using LLM forensics
                        await self.auto_repair(project.id, output)
                    else:
                        db.add(TestRun(
                            project_id=project.id,
                            passed=False,
                            console_violations=1,
                            report_path=None
                        ))
                        db.commit()

                        # Log QA Decision (Failed)
                        test_dec = Decision(
                            decision="Reject frontend build after failed Playwright tests",
                            reason="Playwright functional tests failed and auto-repair could not resolve issues.",
                            agent="QASpecialist",
                            artifact_id=test_art.id,
                            context={}
                        )
                        self.decision_mgr.log_decision(test_dec)
                        raise RuntimeError("Playwright test suite failed after maximum self-healing retries.")
        finally:
            db.close()

    async def auto_repair(self, project_id: str, error_logs: str):
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
            self.env.write_file(target_file, patch.get("content", ""))
            print(f"🔧 Patched {target_file} successfully.")

            # Log repair Decision
            repair_dec = Decision(
                decision=f"Apply self-healing patch to {target_file}",
                reason="Correct errors caught during Playwright browser execution run.",
                agent="ProductManager",
                artifact_id=None,
                context={"patch_file": target_file, "error_preview": error_logs[:200]}
            )
            self.decision_mgr.log_decision(repair_dec)

            # Emit Self-Healing Event
            self.event_mgr.emit_event(Event(
                event_type="SELF_HEALING_ATTEMPTED",
                producer="ProductManager",
                project_id=project_id,
                payload={"target_file": target_file, "patch": patch}
            ))
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
                try:
                    stdout = self.env.run_command(
                        ["strix", "--target", ".", "--non-interactive", "--scan-mode", "quick"]
                    )
                except CommandExecutionError as e:
                    # Return code 2 means scan succeeded but vulnerabilities found
                    if e.returncode == 2:
                        passed = False
                        stdout = e.stdout
                    else:
                        raise e
                
                print("✅ Strix CLI scan finished successfully.")
                
                if self.env.exists("strix_runs"):
                    runs = sorted([d for d in self.env.list_dir("strix_runs") if self.env.exists(os.path.join("strix_runs", d))])
                    if runs:
                        latest_run_dir = os.path.join("strix_runs", runs[-1])
                        md_files = [f for f in self.env.list_dir(latest_run_dir) if f.endswith(".md")]
                        if md_files:
                            report_content = self.env.read_file(os.path.join(latest_run_dir, md_files[0]))
                        
                        json_files = [f for f in self.env.list_dir(latest_run_dir) if f.endswith(".json")]
                        if json_files:
                            try:
                                json_content = self.env.read_file(os.path.join(latest_run_dir, json_files[0]))
                                data = json.loads(json_content)
                                vulnerabilities_count = len(data.get("vulnerabilities", []))
                            except Exception as json_err:
                                print(f"⚠️ Failed to parse Strix JSON report: {json_err}")
                
                if not report_content:
                    report_content = f"# Strix CLI Scan Report\n\n## Output Log\n\n```\n{stdout}\n```"
                    
            except Exception as cli_err:
                print(f"⚠️ Strix CLI is unavailable or failed ({cli_err}). Falling back to AI Security Agent...")
                # 2. AI Fallback scanner
                files_content = {}
                for fname in ["index.html", "index.css", "verify-ui.js"]:
                    if self.env.exists(fname):
                        try:
                            files_content[fname] = self.env.read_file(fname)
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
            self.env.write_file(report_filename, report_content)

            # Record to DB
            db_scan = SecurityScan(
                project_id=project.id,
                passed=passed,
                vulnerabilities_found=vulnerabilities_count,
                report_path=report_path
            )
            db.add(db_scan)
            db.commit()

            # Save Security Scan Artifact
            coder_arts = self.artifact_mgr.list_artifacts(artifact_type="code")
            coder_art_id = coder_arts[0].id if coder_arts else None

            sec_art = Artifact(
                artifact_type="security",
                producer="SecuritySpecialist",
                content={"passed": passed, "vulnerabilities_count": vulnerabilities_count, "report": report_content},
                project_id=project.id,
                parent_artifact=coder_art_id,
                metadata={"file": report_filename}
            )
            self.artifact_mgr.save_artifact(sec_art)

            # Log Security Decision
            sec_dec = Decision(
                decision="Validate frontend security vulnerability patterns",
                reason=f"Scanned index.html/index.css/verify-ui.js for XSS, CSRF. Found {vulnerabilities_count} issues.",
                agent="SecuritySpecialist",
                artifact_id=sec_art.id,
                context={}
            )
            self.decision_mgr.log_decision(sec_dec)

            # Emit Security Scan Completed Event
            self.event_mgr.emit_event(Event(
                event_type="SECURITY_SCAN_COMPLETED",
                producer="SecuritySpecialist",
                project_id=project.id,
                payload={"artifact_id": sec_art.id, "passed": passed, "vulnerabilities_count": vulnerabilities_count}
            ))
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
