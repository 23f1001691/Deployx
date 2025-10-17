import asyncio
import httpx
from pydantic import BaseModel, Field

class EvaluationResponse(BaseModel):
    email: str
    task: str
    round: int
    nonce: str
    repo_url: str
    commit_sha: str
    pages_url: str

async def submit_evaluation(
    evaluation_url: str, payload: EvaluationResponse, max_retries: int = 5
):
    """Submit evaluation with exponential backoff"""

    async with httpx.AsyncClient() as client:
        for attempt in range(max_retries):
            try:
                response = await client.post(
                    evaluation_url,
                    json=payload.model_dump(),
                    headers={"Content-Type": "application/json"},
                    timeout=30,
                )
                if response.status_code == 200:
                    print(f"✅ Evaluation submitted successfully")
                    return True
                else:
                    print(f"⚠ Evaluation returned {response.status_code}")
            except Exception as e:
                print(f"Evaluation submission attempt {attempt + 1} failed: {e}")

            if attempt < max_retries - 1:
                delay = 2**attempt 
                await asyncio.sleep(delay)

    return False