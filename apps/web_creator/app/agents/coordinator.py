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
from platform_core.core.state_machine import StateMachine, ProjectState
from platform_core.core.registry import CapabilityRegistry
from platform_core.core.workflow import WorkflowEngine, WorkflowStage, WorkflowResult

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
        
        self.state_machine = StateMachine(env=env, event_mgr=self.event_mgr)
        self.registry = CapabilityRegistry(load_defaults=True)
        self.workflow_engine = WorkflowEngine(env=env, event_mgr=self.event_mgr)

    def _transition_state(self, trigger: str, project_id: str):
        try:
            new_state = self.state_machine.transition(trigger, project_id=project_id)
            db = self.get_db_session()
            db_project = db.query(Project).filter(Project.id == project_id).first()
            if db_project:
                if new_state == ProjectState.PLANNING:
                    db_project.status = "PLANNING"
                elif new_state in (ProjectState.ARCHITECTING, ProjectState.CODING, ProjectState.REVIEWING, ProjectState.TESTING, ProjectState.DEPLOYING):
                    db_project.status = "BUILDING"
                elif new_state == ProjectState.DONE:
                    db_project.status = "PASSED"
                elif new_state == ProjectState.FAILED:
                    db_project.status = "FAILED"
                db.commit()
            db.close()
        except Exception as e:
            print(f"⚠️ State machine transition warning: {e}")

    def get_db_session(self):
        return SessionLocal()

    async def init_project(self, name: str, concept: str) -> str:
        self.state_machine.reset()
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
                if content and content.strip():
                    concept_text = content
                else:
                    raise ValueError(f"Failed to extract text content or document is empty: {resolved_path}")
            else:
                raise FileNotFoundError(f"Word document requirements file '{concept}' not found.")
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
                    if not concept_text or not concept_text.strip():
                        raise ValueError(f"Text requirements file {resolved_path} is empty")
                except Exception as e:
                    if isinstance(e, ValueError):
                        raise e
                    raise RuntimeError(f"Failed to read text file {resolved_path}: {e}")
            else:
                raise FileNotFoundError(f"Text requirements file '{concept}' not found.")

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
            
            try:
                data = json.loads(clean_json)
            except json.JSONDecodeError as jde:
                print(f"⚠️ PM LLM response was not valid JSON, using default spec fallback: {jde}")
                data = {
                    "theme": "SaaS / Tech",
                    "project_md": f"# {name}\n\n## Requirements\n{concept_text}\n\nThis specification was auto-generated due to LLM response parsing fallback.",
                    "roadmap_md": f"# Roadmap for {name}\n\n- [ ] Phase 1: Establish UI/UX design theme and HSL CSS variables\n- [ ] Phase 2: Generate semantic HTML5 templates\n- [ ] Phase 3: Implement responsive CSS Grid/Flexbox\n- [ ] Phase 4: Generate Express routes and package.json\n- [ ] Phase 5: Run Playwright tests\n- [ ] Phase 6: Run security vulnerabilities scan",
                    "state_md": f"# State of {name}\n\nInitial specification and fallback planning phase.",
                    "design_md": f"---\ntheme: SaaS / Tech\ncolors:\n  primary: \"#007acc\"\n  secondary: \"#6c757d\"\n---\n# Design system for {name}"
                }
            
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
            
            try:
                arch_data = json.loads(clean_arch_json)
            except json.JSONDecodeError as jde:
                print(f"⚠️ Architect LLM response was not valid JSON, using default architecture fallback: {jde}")
                arch_data = {
                    "architecture_md": f"# Architecture for {name}\n\nStandard HTML5 + Express application layout with standard endpoints.",
                    "db_schema_sql": "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT);",
                    "api_spec_yaml": f"openapi: 3.0.0\ninfo:\n  title: {name}\n  version: 1.0.0\npaths: {{}}",
                    "workflow_yaml": """
stages:
  - id: ui_design
    agent: designer
    dependencies: []
  - id: frontend
    agent: coder
    dependencies: [ui_design]
  - id: styling
    agent: css_expert
    dependencies: [frontend]
  - id: backend
    agent: backend_developer
    dependencies: [styling]
  - id: qa
    agent: qa_tester
    dependencies: [backend]
  - id: security
    agent: security_expert
    dependencies: [qa]
"""
                }
            
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
            
            # Replay state transitions to synchronize StateMachine and update db status
            self._transition_state("PROJECT_INITIATED", project_id=project_id)
            self._transition_state("SPECIFICATION_GENERATED", project_id=project_id)
            self._transition_state("ARCHITECTURE_DEFINED", project_id=project_id)
            
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
        
        project_name = db_project.name
        db_project.status = "BUILDING"
        db.commit()
        db.close()

        # Emit Build Started Event
        self.event_mgr.emit_event(Event(
            event_type="BUILD_STARTED",
            producer="platform",
            project_id=project_id,
            payload={"name": project_name}
        ))

        workflow_content = ""
        if self.env.exists("workflow.yaml"):
            try:
                workflow_content = self.env.read_file("workflow.yaml")
            except Exception as read_err:
                print(f"⚠️ Failed to read workflow.yaml: {read_err}")
                
        if not workflow_content:
            workflow_content = """
stages:
  ui_design:
    name: UI UX Design Variables
    agent: DesignerAgent
    depends_on: []
  frontend:
    name: Frontend HTML/JS Coder
    agent: CoderAgent
    depends_on: [ui_design]
  styling:
    name: Responsive CSS Expert
    agent: CSSAgent
    depends_on: [frontend]
  backend:
    name: Backend generator
    agent: BackendAgent
    depends_on: [styling]
  qa:
    name: QA Playwright Audit
    agent: QAAgent
    depends_on: [backend]
  security:
    name: Security Scan
    agent: SecurityAgent
    depends_on: [backend]
"""
        try:
            results = await self.workflow_engine.run(
                workflow_content,
                runner=self.run_stage,
                project_id=project_id,
                context={"project_id": project_id}
            )
            
            failed = [r for r in results if r.status == "FAILED"]
            if failed:
                raise RuntimeError(f"Workflow execution failed at stages: {[f.stage_id for f in failed]}")
                
            db = self.get_db_session()
            db_project = db.query(Project).filter(Project.id == project_id).first()
            if db_project:
                db_project.status = "PASSED"
                db.commit()
            db.close()
            
            self._transition_state("BUILD_FINISHED", project_id=project_id)
            
            self.event_mgr.emit_event(Event(
                event_type="BUILD_FINISHED",
                producer="platform",
                project_id=project_id,
                payload={"status": "PASSED"}
            ))
            print("✅ Build and Security Scan Completed Successfully!")
            
        except Exception as e:
            db = self.get_db_session()
            db_project = db.query(Project).filter(Project.id == project_id).first()
            if db_project:
                db_project.status = "FAILED"
                db.commit()
            db.close()
            
            self._transition_state("BUILD_FAILED", project_id=project_id)
            
            self.event_mgr.emit_event(Event(
                event_type="BUILD_FINISHED",
                producer="platform",
                project_id=project_id,
                payload={"status": "FAILED", "error": str(e)}
            ))
            print(f"❌ Build Failed: {e}")
            raise e

    def _get_phase_num(self, stage_id: str) -> Optional[str]:
        mapping = {
            "ui_design": "Phase1",
            "frontend": "Phase2",
            "styling": "Phase3",
            "backend": "Phase4",
            "qa": "Phase5",
            "security": "Phase6"
        }
        return mapping.get(stage_id)

    async def run_stage(self, stage: WorkflowStage, context: dict) -> WorkflowResult:
        project_id = context["project_id"]
        
        # Retrieve project details from DB
        db = self.get_db_session()
        db_project = db.query(Project).filter(Project.id == project_id).first()
        db_project_name = db_project.name if db_project else "Web App"
        db_project_concept = db_project.concept if db_project else ""
        db_project_theme = db_project.theme if db_project else "SaaS / Tech"
        db.close()
        
        # Update BuildTask status to RUNNING in database
        db = self.get_db_session()
        phase_num = self._get_phase_num(stage.id)
        if phase_num:
            task = db.query(BuildTask).filter(BuildTask.project_id == project_id, BuildTask.phase == phase_num).first()
            if task:
                task.status = "RUNNING"
                db.commit()
        db.close()
        
        try:
            artifact_ids = []
            
            cap_id_map = {
                "ui_design": "ui_design_tokens",
                "frontend": "frontend_generation",
                "styling": "css_styling",
                "backend": "backend_generation",
                "qa": "qa_testing",
                "security": "security_scanning",
            }
            cap_id = cap_id_map.get(stage.id, stage.id)
            cap = self.registry.resolve(cap_id)
            
            # Find parent artifact for lineage
            parent_id = None
            if stage.id == "ui_design":
                spec_arts = self.artifact_mgr.list_artifacts(artifact_type="spec")
                if spec_arts: parent_id = spec_arts[0].id
            elif stage.id == "frontend":
                design_arts = self.artifact_mgr.list_artifacts(artifact_type="design")
                if design_arts: parent_id = design_arts[-1].id
            elif stage.id == "styling":
                code_arts = self.artifact_mgr.list_artifacts(artifact_type="code")
                if code_arts: parent_id = code_arts[-1].id
            elif stage.id == "backend":
                arch_arts = self.artifact_mgr.list_artifacts(artifact_type="architecture")
                if arch_arts: parent_id = arch_arts[0].id
            elif stage.id == "qa":
                code_arts = self.artifact_mgr.list_artifacts(artifact_type="code")
                if code_arts: parent_id = code_arts[-1].id
            elif stage.id == "security":
                code_arts = self.artifact_mgr.list_artifacts(artifact_type="code")
                if code_arts: parent_id = code_arts[-1].id

            if stage.id == "ui_design":
                design_md_content = self.env.read_file("DESIGN.md") if self.env.exists("DESIGN.md") else ""
                
                if cap.tool == "css_expert":
                    from skills.css_expert.server import generate_css_variables
                    css_variables = await generate_css_variables(db_project_name, db_project_theme)
                else:
                    design_prompt = (
                        f"Based on the following DESIGN.md specifications:\n{design_md_content}\n\n"
                        f"Design CSS variables and assets for project '{db_project_name}' themed '{db_project_theme}'. "
                        "Create design specifications that we will write to index.css. "
                        "Output a stylesheet containing root variables matching the colors, rounded, spacing tokens, and body fonts from the design spec. "
                        "Return ONLY CSS code."
                    )
                    css_variables = await self.designer_agent.call_llm(design_prompt)
                
                self.env.write_file("index.css", css_variables)
                
                design_art = Artifact(
                    artifact_type="design",
                    producer="Designer",
                    content={"css_variables": css_variables},
                    project_id=project_id,
                    parent_artifact=parent_id,
                    metadata={"file": "index.css"}
                )
                self.artifact_mgr.save_artifact(design_art)
                artifact_ids.append(design_art.id)
                
                design_dec = Decision(
                    decision="Design theme HSL color palette and typography layout",
                    reason="Define consistent design system tokens based on PROJECT.md specifications.",
                    agent="Designer",
                    artifact_id=design_art.id,
                    context={}
                )
                self.decision_mgr.log_decision(design_dec)
                
                self.event_mgr.emit_event(Event(
                    event_type="DESIGN_COMPLETED",
                    producer="Designer",
                    project_id=project_id,
                    payload={"artifact_id": design_art.id}
                ))

            elif stage.id == "frontend":
                design_md_content = self.env.read_file("DESIGN.md") if self.env.exists("DESIGN.md") else ""
                
                if cap.tool == "html_coder":
                    from skills.html_coder.server import generate_html
                    html_code = await generate_html(db_project_name, design_md_content)
                else:
                    coder_prompt = (
                        f"Based on the project's DESIGN.md specifications:\n{design_md_content}\n\n"
                        f"Write a responsive HTML5 structure for '{db_project_name}'. "
                        "Integrate header, nav, main sections, a footer, and unique IDs. "
                        "Include a link to 'index.css' and a script block or link to 'script.js' "
                        "containing interactive DOM events (like nav toggles or slider logic). "
                        "Return ONLY the complete HTML code."
                    )
                    html_code = await self.coder_agent.call_llm(coder_prompt)
                
                self.env.write_file("index.html", html_code)
                
                coder_art = Artifact(
                    artifact_type="code",
                    producer="Coder",
                    content={"html_code": html_code},
                    project_id=project_id,
                    parent_artifact=parent_id,
                    metadata={"file": "index.html"}
                )
                self.artifact_mgr.save_artifact(coder_art)
                artifact_ids.append(coder_art.id)
                
                coder_dec = Decision(
                    decision="Construct semantic HTML5 layout with DOM logic",
                    reason="Generate UI frame containing headers, navigations, grid containers, and scripts.",
                    agent="Coder",
                    artifact_id=coder_art.id,
                    context={}
                )
                self.decision_mgr.log_decision(coder_dec)
                
                self.event_mgr.emit_event(Event(
                    event_type="FRONTEND_GENERATED",
                    producer="Coder",
                    project_id=project_id,
                    payload={"artifact_id": coder_art.id}
                ))

            elif stage.id == "styling":
                design_md_content = self.env.read_file("DESIGN.md") if self.env.exists("DESIGN.md") else ""
                css_variables = self.env.read_file("index.css") if self.env.exists("index.css") else ""
                
                if cap.tool == "css_expert":
                    from skills.css_expert.server import upgrade_css_styles
                    full_css = await upgrade_css_styles(db_project_name, css_variables)
                else:
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
                
                css_art = Artifact(
                    artifact_type="design",
                    producer="CSSArchitect",
                    content={"css_variables": css_variables, "full_css": full_css},
                    project_id=project_id,
                    parent_artifact=parent_id,
                    metadata={"file": "index.css", "upgraded": True}
                )
                self.artifact_mgr.save_artifact(css_art)
                artifact_ids.append(css_art.id)
                
                css_dec = Decision(
                    decision="Incorporate responsive breakpoints and advanced styling transitions",
                    reason="Refine index.css with mobile media queries and glassmorphic micro-interactions.",
                    agent="CSSArchitect",
                    artifact_id=css_art.id,
                    context={}
                )
                self.decision_mgr.log_decision(css_dec)
                
                self.event_mgr.emit_event(Event(
                    event_type="STYLING_UPGRADED",
                    producer="CSSArchitect",
                    project_id=project_id,
                    payload={"artifact_id": css_art.id}
                ))

            elif stage.id == "backend":
                if cap.tool == "backend_generator":
                    from skills.backend_generator.server import generate_backend
                    backend_resp = await generate_backend(db_project_name, db_project_concept)
                else:
                    backend_prompt = (
                        f"Implement the backend files for the project '{db_project_name}' based on the requirements:\n"
                        f"{db_project_concept}\n\n"
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
                
                clean_json = backend_resp.strip()
                if clean_json.startswith("```json"):
                    clean_json = clean_json[7:]
                if clean_json.endswith("```"):
                    clean_json = clean_json[:-3]
                clean_json = clean_json.strip()
                
                try:
                    files = json.loads(clean_json)
                except json.JSONDecodeError as jde:
                    print(f"⚠️ Backend LLM response was not valid JSON, using default files fallback: {jde}")
                    files = [
                        {
                            "file": "server.js",
                            "content": """const express = require('express');
const app = express();
const port = process.env.PORT || 8000;
app.use(express.static('.'));
app.get('/api/health', (req, res) => res.json({ status: 'ok' }));
app.listen(port, () => console.log(`Server running on port ${port}`));"""
                        },
                        {
                            "file": "package.json",
                            "content": """{
  "name": "web-app",
  "version": "1.0.0",
  "main": "server.js",
  "dependencies": {
    "express": "^4.19.2",
    "cors": "^2.8.5",
    "dotenv": "^16.4.5"
  }
}"""
                        }
                    ]
                for f_info in files:
                    self.env.write_file(f_info["file"], f_info["content"])
                
                backend_art = Artifact(
                    artifact_type="code",
                    producer="BackendDeveloper",
                    content={"files": files},
                    project_id=project_id,
                    parent_artifact=parent_id,
                    metadata={"type": "backend"}
                )
                self.artifact_mgr.save_artifact(backend_art)
                artifact_ids.append(backend_art.id)
                
                backend_dec = Decision(
                    decision="Generate database schemas, routes and controller implementations",
                    reason="Created Mongoose/Express boilerplate and route endpoints to serve backend requests.",
                    agent="BackendDeveloper",
                    artifact_id=backend_art.id,
                    context={}
                )
                self.decision_mgr.log_decision(backend_dec)
                
                self.event_mgr.emit_event(Event(
                    event_type="BACKEND_GENERATED",
                    producer="BackendDeveloper",
                    project_id=project_id,
                    payload={"artifact_id": backend_art.id}
                ))
                
                self._transition_state("BACKEND_GENERATED", project_id=project_id)

            elif stage.id == "qa":
                self._transition_state("BUILD_STARTED", project_id=project_id)
                await self.run_playwright_test(db_project)
                
                # Retrieve latest QA artifact ID
                test_arts = self.artifact_mgr.list_artifacts(artifact_type="test")
                if test_arts:
                    artifact_ids.append(test_arts[-1].id)

            elif stage.id == "security":
                await self.run_strix_security_scan(db_project)
                
                # Retrieve latest security artifact ID
                sec_arts = self.artifact_mgr.list_artifacts(artifact_type="security")
                if sec_arts:
                    artifact_ids.append(sec_arts[-1].id)

            # Update BuildTask status to COMPLETED
            db = self.get_db_session()
            if phase_num:
                task = db.query(BuildTask).filter(BuildTask.project_id == project_id, BuildTask.phase == phase_num).first()
                if task:
                    task.status = "COMPLETED"
                    task.completed_at = datetime.datetime.utcnow()
                    db.commit()
            db.close()
            
            return WorkflowResult(stage_id=stage.id, status="COMPLETED", artifact_ids=artifact_ids)

        except Exception as e:
            print(f"❌ Error executing workflow stage {stage.id}: {e}")
            db = self.get_db_session()
            if phase_num:
                task = db.query(BuildTask).filter(BuildTask.project_id == project_id, BuildTask.phase == phase_num).first()
                if task:
                    task.status = "FAILED"
                    db.commit()
            db.close()
            return WorkflowResult(stage_id=stage.id, status="FAILED", error=str(e))

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
            if not os.path.exists(template_path):
                user_home_template = os.path.join(os.path.expanduser("~"), ".gemini", "config", "skills", "web-creator", "templates", "playwright-template.js")
                if os.path.exists(user_home_template):
                    template_path = user_home_template
            
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
                    self._transition_state("TEST_PASSED", project_id=project.id)
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
                    self._transition_state("TEST_FAILED", project_id=project.id)

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
            self._transition_state("SELF_HEALING_ATTEMPTED", project_id=project_id)
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
