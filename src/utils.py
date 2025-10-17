import json
import re
import time
import shutil

def check_system_dependencies():
    """Check if required system dependencies are available"""
    missing = []
    
    # Check for git
    if not shutil.which("git"):
        missing.append("git")
    
    # Check for gh (GitHub CLI)
    if not shutil.which("gh"):
        missing.append("gh")
    
    if missing:
        raise RuntimeError(
            f"Missing required system dependencies: {', '.join(missing)}\n"
            f"Please install them or use the provided Dockerfile."
        )
    
def extract_json_from_llm_response(response_text: str) -> dict:
    """
    Robust JSON extraction from LLM responses.
    Handles markdown code blocks, extra text, and malformed JSON.
    """
    
    # Step 1: Remove markdown code blocks
    response_text = response_text.strip()
    
    # Remove ```json or ```
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        # Remove first line if it's ```json or ```
        if lines[0].strip().startswith("```"):
            lines = lines[1:]
        # Remove last line if it's ```
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        response_text = "\n".join(lines)
    
    # Step 2: Try direct JSON parsing
    try:
        return json.loads(response_text)
    except json.JSONDecodeError:
        pass
    
    # Step 3: Find JSON object using regex (greedy match)
    # Look for outermost { }
    json_pattern = r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}'
    matches = list(re.finditer(json_pattern, response_text, re.DOTALL))
    
    if not matches:
        # Try to find any JSON-like structure
        start = response_text.find('{')
        end = response_text.rfind('}')
        if start != -1 and end != -1 and end > start:
            response_text = response_text[start:end+1]
    else:
        # Use the largest match (usually the complete JSON)
        largest_match = max(matches, key=lambda m: len(m.group()))
        response_text = largest_match.group()
    
    # Step 4: Clean up common issues
    # Remove any text before first {
    first_brace = response_text.find('{')
    if first_brace > 0:
        response_text = response_text[first_brace:]
    
    # Remove any text after last }
    last_brace = response_text.rfind('}')
    if last_brace != -1:
        response_text = response_text[:last_brace+1]
    
    # Step 5: Fix common JSON issues
    # Remove trailing commas before closing braces/brackets
    response_text = re.sub(r',(\s*[}\]])', r'\1', response_text)
    
    # Fix unescaped quotes in strings (basic heuristic)
    # This is tricky and may not work for all cases
    
    # Step 6: Try parsing again
    try:
        return json.loads(response_text)
    except json.JSONDecodeError as e:
        # Step 7: Last resort - try to fix specific error
        print(f"JSON parsing error at position {e.pos}: {e.msg}")
        print(f"Context: ...{response_text[max(0, e.pos-50):e.pos+50]}...")
        
        # Save for debugging
        debug_file = f"/tmp/llm_raw_output_{int(time.time())}.txt"
        with open(debug_file, "w", encoding="utf-8") as f:
            f.write(response_text)
        
        raise ValueError(f"Could not parse LLM response as JSON. Saved to {debug_file}")
    
