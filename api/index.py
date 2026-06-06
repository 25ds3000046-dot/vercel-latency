from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
import json
from pathlib import Path

app = FastAPI()

# FIX 1: allow_credentials MUST be False if origins is "*"
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=False, 
    allow_methods=["*"],  
    allow_headers=["*"],  
)

# SAFE LOAD: Prevents a 500 server crash (which causes a CORS error) if the file is missing on Vercel
DATA_PATH = Path(__file__).parent.parent / "q-vercel-latency.json"
RAW_DATA = []
if DATA_PATH.exists():
    with open(DATA_PATH) as f:
        RAW_DATA = json.load(f)
else:
    print(f"Warning: Data file not found at {DATA_PATH}")

class AnalysisRequest(BaseModel):
    regions: List[str]
    threshold_ms: float

# Basic health check route for the browser
@app.api_route("/", methods=["GET", "OPTIONS"])
def health_check():
    return {"status": "success", "message": "API is awake and CORS is working!"}

# FIX 2: The analyze function is now properly routed to receive POST requests!
@app.api_route("/api", methods=["POST", "OPTIONS"])
async def analyze(req: AnalysisRequest):
    if not RAW_DATA:
        return JSONResponse(
            status_code=500,
            content={"error": "Data file missing on server"}
        )

    result = {}
    for region in req.regions:
        records = [r for r in RAW_DATA if r.get("region") == region]
        if not records:
            result[region] = None
            continue
        latencies = [r["latency_ms"] for r in records]
        uptimes = [r["uptime_pct"] for r in records]
        sorted_lat = sorted(latencies)
        p95_index = int(len(sorted_lat) * 0.95)
        
        # Ensure we don't go out of bounds on the index
        if p95_index >= len(sorted_lat):
            p95_index = len(sorted_lat) - 1
            
        result[region] = {
            "avg_latency": sum(latencies) / len(latencies),
            "p95_latency": sorted_lat[p95_index],
            "avg_uptime": sum(uptimes) / len(uptimes),
            "breaches": sum(1 for l in latencies if l > req.threshold_ms)
        }
    
    # FastAPI automatically handles the JSON conversion and CORS headers
    return result

# Catch-all preflight handler for Vercel
@app.options("/{full_path:path}")
def preflight_handler():
    return {}
