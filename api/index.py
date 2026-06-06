 from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
import json
from pathlib import Path

app = FastAPI()

# 1. CORS Configuration (Fixed Conflict)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=False, # MUST be False when origins is "*"
    allow_methods=["*"],  
    allow_headers=["*"],  
)

# 2. Safe Data Loading
DATA_PATH = Path(__file__).parent.parent / "q-vercel-latency.json"
RAW_DATA = []

if DATA_PATH.exists():
    with open(DATA_PATH) as f:
        RAW_DATA = json.load(f)
else:
    print(f"Warning: Data file not found at {DATA_PATH}")

# 3. Request Model
class AnalysisRequest(BaseModel):
    regions: List[str]
    threshold_ms: float

# 4. Health Check Route (Catches GET requests to prevent 405 errors)
@app.api_route("/", methods=["GET"])
@app.api_route("/api", methods=["GET"])
def health_check():
    return {"status": "success", "message": "API is awake and CORS is working!"}

# 5. Main Analysis Route (Catches POST requests from your frontend)
@app.api_route("/", methods=["POST", "OPTIONS"])
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
        
        # Calculate 95th percentile safely
        p95_index = int(len(sorted_lat) * 0.95)
        if p95_index >= len(sorted_lat):
            p95_index = len(sorted_lat) - 1
            
        result[region] = {
            "avg_latency": sum(latencies) / len(latencies),
            "p95_latency": sorted_lat[p95_index],
            "avg_uptime": sum(uptimes) / len(uptimes),
            "breaches": sum(1 for l in latencies if l > req.threshold_ms)
        }
    
    return result

# 6. Catch-all Preflight Handler (Crucial for Vercel)
@app.options("/{full_path:path}")
def preflight_handler():
    return {}
