from src.utils import extract_json_from_llm_response
from src.prompts import round_1_prompt, round_2_prompt
from typing import List, Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent
import json
import os

MODEL_PROVIDER = os.getenv("MODEL_PROVIDER", "gemini")  

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

class CodeGenerator:
    """Handles LLM-based code generation using Gemini"""

    def __init__(self):
        if MODEL_PROVIDER == "openai":
            self.model = "openai:gpt-5-nano"
            print("🤖 Using OpenAI model")
        else: 
            self.model = "gemini-2.0-flash-exp"
            print("🤖 Using Gemini model")

        self.agent = Agent(self.model)

    async def generate_project(
        self, brief: str, checks: List[str], attachments: List[Attachment]
    ) -> dict:
        """Generate complete project files based on brief"""

        # Process attachments
        attachment_info = []
        for att in attachments:
            if att.url.startswith("data:"):
                # Extract base64 data
                parts = att.url.split(",", 1)
                if len(parts) == 2:
                    attachment_info.append(
                        {
                            "name": att.name,
                            "type": parts[0].split(";")[0].split(":")[1],
                            "size": f"{len(parts[1])} chars (base64)",
                        }
                    )

        prompt = f"""You are a senior full-stack web developer creating a production-ready static web application for GitHub Pages deployment with automated DOM-based testing.
                
        === TASK BRIEF ===
        {brief}

        === CRITICAL TEST CHECKS ===
        Your application MUST pass ALL of these JavaScript/DOM checks that will execute in the browser:
        {chr(10).join(f"  ✓ {check}" for check in checks)}

        **REQUIREMENTS:**
        • Every check will run via `eval()` or browser DevTools on the deployed page
        • Ensure all required IDs, classes, tags, and selectors exist in the HTML
        • Dynamic content must be rendered by JavaScript before checks run
        • If a check queries for an element, that element MUST be present in the DOM
        • No mocked or fake implementations—everything must actually work

        === ATTACHMENTS ===
        {json.dumps(attachment_info, indent=2) if attachment_info else "No attachments"}

        {round_1_prompt}"""
      
        result = await self.agent.run(prompt)
        response_text = result.output.strip() 
        
        print(f"📄 LLM Response length: {len(response_text)} chars")
        print(f"📄 First 100 chars: {response_text[:100]}")
        
        # Use robust JSON extraction
        try:
            files = extract_json_from_llm_response(response_text)
            
            # Validate response has required keys
            if "index.html" not in files or "README.md" not in files:
                raise ValueError(f"Missing required files. Got keys: {list(files.keys())}")
            
            print(f"✅ Successfully parsed {len(files)} files")
            return files
            
        except Exception as e:
            print(f"❌ JSON parsing failed: {str(e)}")
            raise

    async def improve_project(
        self, 
        brief: str, 
        checks: List[str], 
        attachments: List[Attachment],
        existing_files: dict
    ) -> dict:
        """Improve existing project files based on new brief"""

        # Process attachments
        attachment_info = []
        for att in attachments:
            if att.url.startswith("data:"):
                parts = att.url.split(",", 1)
                if len(parts) == 2:
                    attachment_info.append(
                        {
                            "name": att.name,
                            "type": parts[0].split(";")[0].split(":")[1],
                            "size": f"{len(parts[1])} chars (base64)"
                        }
                    )

        # Build existing code context
        existing_code = "\n\n".join([
            f"=== {filename} ===\n{content}" 
            for filename, content in existing_files.items()
            if filename not in ['LICENSE', '.nojekyll', '.gitattributes']
        ])

        prompt = f"""You are a senior full-stack web developer upgrading an existing static web application deployed on GitHub Pages.

        === EXISTING APPLICATION ===
        {existing_code}

        === NEW REQUIREMENTS (Round 2) ===
        {brief}

        === UPDATED TEST CHECKS (CRITICAL) ===
        Your upgraded application MUST pass ALL of these new checks in addition to maintaining previous functionality:
        {chr(10).join(f"  ✓ {check}" for check in checks)}

        **VALIDATION REQUIREMENTS:**
        • All checks will execute via JavaScript in the live browser DOM
        • Ensure every required element, ID, class, or attribute exists
        • Dynamic content must render correctly before checks execute
        • No broken functionality from Round 1
        • Backward compatibility with existing features

        === NEW ATTACHMENTS ===
        {json.dumps(attachment_info, indent=2) if attachment_info else "No new attachments"}

        {round_2_prompt}"""
        
        result = await self.agent.run(prompt)
        response_text = result.output.strip() 

        print(f"📄 LLM Response length: {len(response_text)} chars")
        
        # Use robust JSON extraction
        try:
            files = extract_json_from_llm_response(response_text)
            
            if "index.html" not in files or "README.md" not in files:
                raise ValueError(f"Missing required files. Got keys: {list(files.keys())}")
            
            print(f"✅ Successfully parsed {len(files)} files")
            return files
            
        except Exception as e:
            print(f"❌ JSON parsing failed: {str(e)}")
            raise