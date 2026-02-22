from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import json
import os
import logging
from agent import InsuranceAgent

# Setup logging to see agent progress in the terminal
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MarvelX")

# Initialize FastAPI and your Agent
app = FastAPI(title="MarvelX Insurance API")
agent = InsuranceAgent()

# Simple persistent storage
RESULTS_FILE = "system_results3_v2.json"

def load_results() -> List[Dict[str, Any]]:
    """Loads all claims as a list to match your benchmark format."""
    if os.path.exists(RESULTS_FILE):
        try:
            with open(RESULTS_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
    return []

def save_result(full_data: Dict[str, Any]):
    """Saves the result while maintaining the list structure."""
    results = load_results()
    
    # Check if claim already exists; if so, update it. Otherwise, append.
    existing_index = next((i for i, item in enumerate(results) if item["claim_id"] == full_data["claim_id"]), None)
    
    if existing_index is not None:
        results[existing_index] = full_data
    else:
        results.append(full_data)
        
    with open(RESULTS_FILE, "w") as f:
        json.dump(results, f, indent=4)

# Data models for the API
class ClaimRequest(BaseModel):
    claim_id: str
    description: str
    document_paths: List[str]

@app.get("/", include_in_schema=False)
async def root():
    """Redirects the user directly to the interactive /docs page."""
    return RedirectResponse(url="/docs")

@app.post("/claims", response_model=Dict[str, Any])
async def create_claim(request: ClaimRequest):
    """Submits a claim for processing using the Gateman/Auditor logic."""
    logger.info(f"🚀 Received claim {request.claim_id}")
    
    try:
        # Process using your multi-agent InsuranceAgent
        # Note: Ensure agent.process_claim returns a dict with decision, reasoning, etc.
        result = agent.process_claim(request.description, request.document_paths)
        
        # Merge ID into result
        full_data = {
            "claim_id": request.claim_id, 
            **result
        }
        
        # Save to local storage
        save_result(full_data)
        
        logger.info(f"✅ Claim {request.claim_id} processed: {full_data.get('decision')}")
        return full_data
        
    except Exception as e:
        logger.error(f"❌ Error processing claim {request.claim_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Agent Error: {str(e)}")

@app.get("/claims")
def list_claims():
    """Returns all processed claims from the JSON store."""
    return load_results()

@app.get("/claims/{claim_id}")
def get_claim(claim_id: str):
    """Returns details for a specific claim by ID."""
    results = load_results()
    claim = next((item for item in results if item["claim_id"] == claim_id), None)
    
    if not claim:
        raise HTTPException(status_code=404, detail=f"Claim {claim_id} not found")
    return claim

if __name__ == "__main__":
    import uvicorn
    # Start the server
    uvicorn.run(app, host="127.0.0.1", port=8000)