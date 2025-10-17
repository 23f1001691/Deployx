import asyncio
import base64
import json
import os
import re
import subprocess
import tempfile
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import httpx
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from dotenv import load_dotenv

from src.prompts import MIT_LICENSE, round_1_prompt, round_2_prompt
from src.utils import extract_json_from_llm_response, check_system_dependencies
from src.github import GitHubDeployer
from src.evaluation import submit_evaluation
from src.llm import CodeGenerator

load_dotenv()

# Environment Configuration
SECRET_KEY = os.getenv("SECRET_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip().replace("\n", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "").strip().replace("\n", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME")

MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "gemini")  

app = FastAPI(title="LLM Code Deployment Server")


# def check_system_dependencies():
#     """Check if required system dependencies are available"""
#     missing = []
    
#     # Check for git
#     if not shutil.which("git"):
#         missing.append("git")
    
#     # Check for gh (GitHub CLI)
#     if not shutil.which("gh"):
#         missing.append("gh")
    
#     if missing:
#         raise RuntimeError(
#             f"Missing required system dependencies: {', '.join(missing)}\n"
#             f"Please install them or use the provided Dockerfile."
#         )


@app.on_event("startup")
async def startup_event():
    """Validate environment on startup"""
    print("Starting LLM Deployment Server...")
    
    # Check system dependencies
    try:
        check_system_dependencies()
        print("✓ System dependencies OK (git, gh)")
    except RuntimeError as e:
        print(f"✗ System dependency check failed:\n{e}")
        print("⚠ Server will start but deployments will fail!")

    # Check environment variables
    print(f"📊 Model Provider: {MODEL_PROVIDER}")

    if not SECRET_KEY:
        print("⚠ WARNING: SECRET_KEY not set")
    if MODEL_PROVIDER == "gemini" and not GOOGLE_API_KEY:
        print("⚠ WARNING: GOOGLE_API_KEY not set (required for Gemini)")
    if MODEL_PROVIDER == "openai" and not OPENAI_API_KEY and not OPENAI_BASE_URL:
        print("⚠ WARNING: OPENAI_API_KEY not set (required for OpenAI)")
    if not GITHUB_TOKEN:
        print("⚠ WARNING: GITHUB_TOKEN not set")
    if not GITHUB_USERNAME:
        print("⚠ WARNING: GITHUB_USERNAME not set")
    
    if all([SECRET_KEY, GITHUB_TOKEN, GITHUB_USERNAME]):
        print("✓ Core environment variables configured")
    
    print("✅ Server ready!")


# Request Models
class Attachment(BaseModel):
    name: str
    url: str


class DeploymentRequest(BaseModel):
    email: str
    secret: str
    task: str
    round: int
    nonce: str
    brief: str
    checks: List[str]
    evaluation_url: str
    attachments: Optional[List[Attachment]] = []


class EvaluationResponse(BaseModel):
    email: str
    task: str
    round: int
    nonce: str
    repo_url: str
    commit_sha: str
    pages_url: str


# MIT License Template
# MIT_LICENSE = """MIT License

# Copyright (c) {year}

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
# """


# class CodeGenerator:
#     """Handles LLM-based code generation using Gemini"""

#     def __init__(self):
#         if MODEL_PROVIDER == "openai":
#             self.model = "openai:gpt-5-nano"
#             print("🤖 Using OpenAI model")
#         else: 
#             self.model = "gemini-2.0-flash-exp"
#             print("🤖 Using Gemini model")

#         self.agent = Agent(self.model)

#     async def generate_project(
#         self, brief: str, checks: List[str], attachments: List[Attachment]
#     ) -> dict:
#         """Generate complete project files based on brief"""

#         # Process attachments
#         attachment_info = []
#         for att in attachments:
#             if att.url.startswith("data:"):
#                 # Extract base64 data
#                 parts = att.url.split(",", 1)
#                 if len(parts) == 2:
#                     attachment_info.append(
#                         {
#                             "name": att.name,
#                             "type": parts[0].split(";")[0].split(":")[1],
#                             "size": f"{len(parts[1])} chars (base64)",
#                         }
#                     )

#         prompt = f"""You are a senior full-stack web developer creating a production-ready static web application for GitHub Pages deployment with automated DOM-based testing.
                
#         === TASK BRIEF ===
#         {brief}

#         === CRITICAL TEST CHECKS ===
#         Your application MUST pass ALL of these JavaScript/DOM checks that will execute in the browser:
#         {chr(10).join(f"  ✓ {check}" for check in checks)}

#         **REQUIREMENTS:**
#         • Every check will run via `eval()` or browser DevTools on the deployed page
#         • Ensure all required IDs, classes, tags, and selectors exist in the HTML
#         • Dynamic content must be rendered by JavaScript before checks run
#         • If a check queries for an element, that element MUST be present in the DOM
#         • No mocked or fake implementations—everything must actually work

#         === ATTACHMENTS ===
#         {json.dumps(attachment_info, indent=2) if attachment_info else "No attachments"}

#         {round_1_prompt}"""
      
#         result = await self.agent.run(prompt)
#         response_text = result.output.strip() 
        
#         print(f"📄 LLM Response length: {len(response_text)} chars")
#         print(f"📄 First 100 chars: {response_text[:100]}")
        
#         # Use robust JSON extraction
#         try:
#             files = extract_json_from_llm_response(response_text)
            
#             # Validate response has required keys
#             if "index.html" not in files or "README.md" not in files:
#                 raise ValueError(f"Missing required files. Got keys: {list(files.keys())}")
            
#             print(f"✅ Successfully parsed {len(files)} files")
#             return files
            
#         except Exception as e:
#             print(f"❌ JSON parsing failed: {str(e)}")
#             raise

#     async def improve_project(
#         self, 
#         brief: str, 
#         checks: List[str], 
#         attachments: List[Attachment],
#         existing_files: dict
#     ) -> dict:
#         """Improve existing project files based on new brief"""

#         # Process attachments
#         attachment_info = []
#         for att in attachments:
#             if att.url.startswith("data:"):
#                 parts = att.url.split(",", 1)
#                 if len(parts) == 2:
#                     attachment_info.append(
#                         {
#                             "name": att.name,
#                             "type": parts[0].split(";")[0].split(":")[1],
#                             "size": f"{len(parts[1])} chars (base64)"
#                         }
#                     )

#         # Build existing code context
#         existing_code = "\n\n".join([
#             f"=== {filename} ===\n{content}" 
#             for filename, content in existing_files.items()
#             if filename not in ['LICENSE', '.nojekyll', '.gitattributes']
#         ])

#         prompt = f"""You are a senior full-stack web developer upgrading an existing static web application deployed on GitHub Pages.

#         === EXISTING APPLICATION ===
#         {existing_code}

#         === NEW REQUIREMENTS (Round 2) ===
#         {brief}

#         === UPDATED TEST CHECKS (CRITICAL) ===
#         Your upgraded application MUST pass ALL of these new checks in addition to maintaining previous functionality:
#         {chr(10).join(f"  ✓ {check}" for check in checks)}

#         **VALIDATION REQUIREMENTS:**
#         • All checks will execute via JavaScript in the live browser DOM
#         • Ensure every required element, ID, class, or attribute exists
#         • Dynamic content must render correctly before checks execute
#         • No broken functionality from Round 1
#         • Backward compatibility with existing features

#         === NEW ATTACHMENTS ===
#         {json.dumps(attachment_info, indent=2) if attachment_info else "No new attachments"}

#         {round_2_prompt}"""
        
#         result = await self.agent.run(prompt)
#         response_text = result.output.strip() 

#         print(f"📄 LLM Response length: {len(response_text)} chars")
        
#         # Use robust JSON extraction
#         try:
#             files = extract_json_from_llm_response(response_text)
            
#             if "index.html" not in files or "README.md" not in files:
#                 raise ValueError(f"Missing required files. Got keys: {list(files.keys())}")
            
#             print(f"✅ Successfully parsed {len(files)} files")
#             return files
            
#         except Exception as e:
#             print(f"❌ JSON parsing failed: {str(e)}")
#             raise
       

# class GitHubDeployer:
#     """Handles GitHub repository creation and Pages deployment"""

#     def __init__(self, username: str, token: str):
#         self.username = username
#         self.token = token

#     def clone_repository(self, repo_name: str, work_dir: Path) -> bool:
#         """Clone existing repository"""
#         try:
#             repo_url = f"https://{self.token}@github.com/{self.username}/{repo_name}.git"
#             subprocess.run(
#                 ["git", "clone", repo_url, str(work_dir)],
#                 check=True,
#                 capture_output=True
#             )
#             return True
#         except subprocess.CalledProcessError:
#             return False

#     def read_repository_files(self, work_dir: Path) -> dict:
#         """Read all files from repository"""
#         files = {}
#         for file_path in work_dir.rglob("*"):
#             if file_path.is_file() and not any(
#                 part.startswith(".git") for part in file_path.parts
#             ):
#                 rel_path = file_path.relative_to(work_dir)
#                 try:
#                     # Try to read as text
#                     content = file_path.read_text(encoding="utf-8")
#                     files[str(rel_path)] = content
#                 except UnicodeDecodeError:
#                     # Binary file, skip or handle differently
#                     pass
#         return files

#     def update_repository(self, work_dir: Path, commit_message: str) -> str:
#         """Update repository with changes"""

#         # Configure git 
#         subprocess.run(
#             ["git", "config", "user.name", self.username],
#             cwd=work_dir,
#             check=True,
#         )
#         subprocess.run(
#             ["git", "config", "user.email", f"{self.username}@ds.study.iitm.ac.in"],
#             cwd=work_dir,
#             check=True,
#         )

#         # Add all changes
#         subprocess.run(["git", "add", "."], cwd=work_dir, check=True)
        
#         # Check if there are changes to commit
#         result = subprocess.run(
#             ["git", "diff", "--staged", "--quiet"],
#             cwd=work_dir,
#             capture_output=True
#         )
        
#         if result.returncode != 0:  # There are changes
#             subprocess.run(
#                 ["git", "commit", "-m", commit_message],
#                 cwd=work_dir,
#                 check=True,
#             )
            
#             # Push changes
#             subprocess.run(
#                 ["git", "push", "origin", "main"],
#                 cwd=work_dir,
#                 check=True,
#             )

#         # Get commit SHA
#         result = subprocess.run(
#             ["git", "rev-parse", "HEAD"],
#             cwd=work_dir,
#             capture_output=True,
#             text=True,
#             check=True,
#         )
#         commit_sha = result.stdout.strip()
#         return commit_sha

#     def create_repository(self, repo_name: str, work_dir: Path) -> tuple[str, str]:
#         """Create GitHub repo and push code"""

#         try:
#             subprocess.run(["git", "init"], cwd=work_dir, check=True, capture_output=True)
            
#             subprocess.run(
#                 ["git", "config", "user.name", self.username],
#                 cwd=work_dir,
#                 check=True,
#                 capture_output=True
#             )
#             subprocess.run(
#                 ["git", "config", "user.email", f"{self.username}@ds.study.iitm.ac.in"],
#                 cwd=work_dir,
#                 check=True,
#                 capture_output=True
#             )

#             subprocess.run(["git", "branch", "-M", "main"], cwd=work_dir, check=True, capture_output=True)
#             subprocess.run(["git", "add", "."], cwd=work_dir, check=True, capture_output=True)
#             subprocess.run(
#                 ["git", "commit", "-m", "Initial commit"],
#                 cwd=work_dir,
#                 check=True,
#                 capture_output=True
#             )

#             env = os.environ.copy()
#             env["GH_TOKEN"] = self.token

#             subprocess.run(
#                 ["gh", "repo", "create", repo_name, "--public", "--source=.", "--remote=origin", "--push"],
#                 cwd=work_dir,
#                 env=env,
#                 check=True,
#                 capture_output=True,
#                 text=True
#             )

#             result = subprocess.run(
#                 ["git", "rev-parse", "HEAD"],
#                 cwd=work_dir,
#                 capture_output=True,
#                 text=True,
#                 check=True,
#             )
#             commit_sha = result.stdout.strip()

#             repo_url = f"https://github.com/{self.username}/{repo_name}"
#             return repo_url, commit_sha
            
#         except subprocess.CalledProcessError as e:
#             stderr = e.stderr.decode() if hasattr(e, 'stderr') and e.stderr else str(e)
#             error_msg = f"Git/GitHub operation failed: {stderr}"
#             print(f"ERROR: {error_msg}")
#             raise RuntimeError(error_msg)
#         except FileNotFoundError as e:
#             error_msg = f"Command not found: {e.filename}. Ensure git and gh are installed."
#             print(f"ERROR: {error_msg}")
#             raise RuntimeError(error_msg)

#     def enable_pages(self, repo_name: str) -> str:
#         """Enable GitHub Pages for repository"""

#         env = os.environ.copy()
#         env["GH_TOKEN"] = self.token

#         # Enable Pages using gh CLI
#         subprocess.run(
#             [
#                 "gh",
#                 "api",
#                 f"repos/{self.username}/{repo_name}/pages",
#                 "-X",
#                 "POST",
#                 "-f",
#                 "source[branch]=main",
#                 "-f",
#                 "source[path]=/",
#             ],
#             env=env,
#             check=True,
#         )

#         pages_url = f"https://{self.username}.github.io/{repo_name}/"
#         return pages_url

#     async def wait_for_pages(self, pages_url: str, max_wait: int = 300):
#         """Wait for GitHub Pages to be available"""

#         async with httpx.AsyncClient() as client:
#             for i in range(max_wait // 10):
#                 try:
#                     response = await client.get(pages_url, timeout=10)
#                     if response.status_code == 200:
#                         print(f"✅ Pages deployed successfully")
#                         return True
#                 except Exception:
#                     pass

#                 if i % 3 == 0:  # Log every 30 seconds
#                     print(f"⏳ Waiting for Pages deployment... ({i*10}s)")

#                 await asyncio.sleep(10)

#         print(f"⚠ Pages deployment timeout after {max_wait}s")
#         return False


# async def submit_evaluation(
#     evaluation_url: str, payload: EvaluationResponse, max_retries: int = 5
# ):
#     """Submit evaluation with exponential backoff"""

#     async with httpx.AsyncClient() as client:
#         for attempt in range(max_retries):
#             try:
#                 response = await client.post(
#                     evaluation_url,
#                     json=payload.model_dump(),
#                     headers={"Content-Type": "application/json"},
#                     timeout=30,
#                 )
#                 if response.status_code == 200:
#                     print(f"✅ Evaluation submitted successfully")
#                     return True
#                 else:
#                     print(f"⚠ Evaluation returned {response.status_code}")
#             except Exception as e:
#                 print(f"Evaluation submission attempt {attempt + 1} failed: {e}")

#             if attempt < max_retries - 1:
#                 delay = 2**attempt 
#                 await asyncio.sleep(delay)

#     return False


async def process_deployment(request: DeploymentRequest):
    """Main deployment workflow"""

    try:
        print(f"\n{'='*60}")
        print(f"📦 Starting deployment")
        print(f"   Task: {request.task}")
        print(f"   Round: {request.round}")
        print(f"   Checks: {len(request.checks)}")
        print(f"{'='*60}\n")

        repo_name = f"{request.task}-{request.nonce}".replace(" ", "-")
        
        if request.round == 1:
            await process_round_1(request, repo_name)
        else:
            await process_round_2(request, repo_name)

    except Exception as e:
        print(f"Deployment failed for task {request.task}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


async def process_round_1(request: DeploymentRequest, repo_name: str):
    """Process Round 1: Create new repository"""
    
    try:
        print(f"Round 1: Creating new repository {repo_name}")

        generator = CodeGenerator()
        files = await generator.generate_project(
            request.brief, request.checks, request.attachments
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            work_dir = Path(tmp_dir)

            # Write generated files
            for filename, content in files.items():
                file_path = work_dir / filename
                file_path.write_text(content, encoding="utf-8")
                print(f"   ✓ Created {filename} ({len(content)} chars)")

            # Add MIT License
            license_path = work_dir / "LICENSE"
            license_path.write_text(MIT_LICENSE.format(year=datetime.now().year), encoding="utf-8")

            # Add .nojekyll
            (work_dir / ".nojekyll").touch()

            # Add .gitattributes
            (work_dir / ".gitattributes").write_text(
                "* text=auto\n*.png binary\n*.jpg binary\n*.jpeg binary\n"
                "*.gif binary\n*.ico binary\n*.pdf binary\n*.svg binary\n",
                encoding="utf-8"
            )

            # Process attachments
            for att in request.attachments:
                if att.url.startswith("data:"):
                    parts = att.url.split(",", 1)
                    if len(parts) == 2:
                        data = base64.b64decode(parts[1])
                        (work_dir / att.name).write_bytes(data)
                        print(f"   ✓ Saved attachment {att.name}")

            # Deploy to GitHub
            deployer = GitHubDeployer(GITHUB_USERNAME, GITHUB_TOKEN)
            repo_url, commit_sha = deployer.create_repository(repo_name, work_dir)
            print(f"✅ Repository: {repo_url}")

            # Enable GitHub Pages
            pages_url = deployer.enable_pages(repo_name)
            print(f"✅ Pages URL: {pages_url}")

            # Wait for Pages
            await deployer.wait_for_pages(pages_url)

        # Submit evaluation
        evaluation = EvaluationResponse(
            email=request.email,
            task=request.task,
            round=request.round,
            nonce=request.nonce,
            repo_url=repo_url,
            commit_sha=commit_sha,
            pages_url=pages_url,
        )

        await submit_evaluation(request.evaluation_url, evaluation)

    except Exception as e:
        print(f"Round 1 deployment failed: {str(e)}")
        raise


async def process_round_2(request: DeploymentRequest, repo_name: str):
    """Process Round 2+: Update existing repository"""
    
    try:
        print(f"Round {request.round}: Updating existing repository {repo_name}")

        with tempfile.TemporaryDirectory() as tmp_dir:
            work_dir = Path(tmp_dir) / repo_name
            work_dir.mkdir(parents=True)

            deployer = GitHubDeployer(GITHUB_USERNAME, GITHUB_TOKEN)
            cloned = deployer.clone_repository(repo_name, work_dir)
            
            if not cloned:
                raise Exception(f"Repository {repo_name} not found. Cannot process round 2.")

            print(f"   ✓ Cloned repository")

            existing_files = deployer.read_repository_files(work_dir)
            print(f"   ✓ Read {len(existing_files)} existing files")

            generator = CodeGenerator()
            updated_files = await generator.improve_project(
                request.brief, request.checks, request.attachments, existing_files
            )

            # Write updated files
            for filename, content in updated_files.items():
                file_path = work_dir / filename
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content, encoding="utf-8")
                print(f"   ✓ Updated {filename}")

            # Process new attachments
            for att in request.attachments:
                if att.url.startswith("data:"):
                    parts = att.url.split(",", 1)
                    if len(parts) == 2:
                        data = base64.b64decode(parts[1])
                        (work_dir / att.name).write_bytes(data)

            # Commit and push
            commit_message = f"Round {request.round}: {int(time.time())}"
            commit_sha = deployer.update_repository(work_dir, commit_message)
            print(f"✅ Committed: {commit_sha[:8]}")

            repo_url = f"https://github.com/{GITHUB_USERNAME}/{repo_name}"
            pages_url = f"https://{GITHUB_USERNAME}.github.io/{repo_name}/"
            
            await asyncio.sleep(10)
            await deployer.wait_for_pages(pages_url)

        # Submit evaluation
        evaluation = EvaluationResponse(
            email=request.email,
            task=request.task,
            round=request.round,
            nonce=request.nonce,
            repo_url=repo_url,
            commit_sha=commit_sha,
            pages_url=pages_url,
        )

        await submit_evaluation(request.evaluation_url, evaluation)

    except Exception as e:
        print(f"Round {request.round} failed: {str(e)}")
        raise


@app.get("/")
async def root():
    return {"message": "LLM Code Deployment Server", "status": "running"}


@app.post("/notify")
async def ping_evaluation_url(response: EvaluationResponse):
    """Main endpoint for evaluation notifications"""

    if response and not all([response.email, response.task, response.nonce, response.repo_url, response.commit_sha, response.pages_url]):
        raise HTTPException(status_code=400, detail="Missing required fields")

    return {"status": "accepted", "message": "Evaluation received"}


@app.post("/api-endpoint")
async def deploy_code(request: DeploymentRequest, background_tasks: BackgroundTasks):
    """Main endpoint for code deployment requests"""

    # Validate secret key
    if request.secret != SECRET_KEY:
        raise HTTPException(status_code=401, detail="Invalid secret key")

    # Validate required fields
    if not all([request.brief, request.evaluation_url, request.task, request.nonce]):
        raise HTTPException(status_code=400, detail="Missing required fields")

    # Add deployment to background tasks
    background_tasks.add_task(process_deployment, request)

    # Return immediate 200 response
    return {"status": "accepted", "message": "Deployment started"}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)