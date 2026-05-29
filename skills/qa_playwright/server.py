import asyncio
import os
import subprocess
import json
from platform_core.core.skill_sdk import SkillServer, tool
from platform_core.core.llm.client import LLMClient

server = SkillServer("qa-playwright")

llm_security = LLMClient(system_instruction=(
    "You are the Strix Security Specialist agent. Your role is to perform static application security "
    "testing (SAST) on generated codebase. Analyze HTML structures, script blocks, logic hooks, "
    "and CSS configuration details. Look for vulnerabilities including XSS, prototype pollution, CSRF, "
    "broken access control, configuration mistakes, and leaked secrets. "
    "Structure your output as a clean JSON containing: "
    "'passed' (boolean), 'vulnerabilities_count' (integer), and 'report_md' (string of the Markdown report). "
    "Return ONLY the clean JSON, no markdown code block wrappers."
))

@tool
async def verify_ui(workspace_path: str) -> str:
    """Run automated Playwright headless verification on the HTML frontend in the workspace."""
    dest_path = os.path.join(workspace_path, "verify-ui.js")
    
    if not os.path.exists(dest_path):
        test_script = """
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  console.log("Starting quick frontend UI check...");
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  
  const filesToCheck = ['index.html', 'products.html', 'cart.html'];
  let passed = true;
  
  for (const file of filesToCheck) {
    const filePath = path.join(__dirname, 'views', file);
    if (!fs.existsSync(filePath)) continue;
    
    try {
      await page.goto('file://' + filePath);
      const title = await page.title();
      console.log(`Page ${file} loaded successfully with title: ${title}`);
    } catch (err) {
      console.error(`Failed to load ${file}:`, err);
      passed = false;
    }
  }
  
  await browser.close();
  if (passed) {
    console.log("UI Check passed!");
    process.exit(0);
  } else {
    console.log("UI Check failed!");
    process.exit(1);
  }
})();
"""
        with open(dest_path, "w", encoding="utf-8") as f:
            f.write(test_script)
            
    try:
        result = subprocess.run(
            ["node", "verify-ui.js"], 
            cwd=workspace_path,
            capture_output=True,
            text=True,
            timeout=30
        )
        return json.dumps({
            "passed": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr
        })
    except Exception as e:
        return json.dumps({
            "passed": False,
            "error": str(e)
        })

@tool
async def scan_security(workspace_path: str) -> str:
    """Run security static audit (SAST) on the files index.html, index.css, server.js in the workspace."""
    files_content = {}
    for fname in ["views/index.html", "public/css/style.css", "server.js"]:
        fpath = os.path.join(workspace_path, fname)
        if os.path.exists(fpath):
            try:
                with open(fpath, "r", encoding="utf-8") as f:
                    files_content[fname] = f.read()[:5000]
            except Exception:
                pass
                
    prompt = (
        "Please perform a static security scan on the following generated codebase files. "
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
    return await llm_security.call_llm(prompt)

if __name__ == "__main__":
    server.run(transport="stdio")
