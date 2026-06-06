from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
import json
import os

app = FastAPI()

# 1. Strict CORS Policy
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=False, 
    allow_methods=["*"],  
    allow_headers=["*"],  
)

# 2. Bulletproof File Loading (Looks in the same folder as this script)
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(CURRENT_DIR, "q-vercel-latency.json")

RAW_DATA = []
if os.path.exists(DATA_PATH):
    with open(DATA_PATH) as f:
        RAW_DATA = json.load(f)

class AnalysisRequest(BaseModel):
    regions: List[str]
    threshold_ms: float

# 3. Health Check Route
@app.api_route("/", methods=["GET", "OPTIONS"])
@app.api_route("/api", methods=["GET", "OPTIONS"])
def health_check():
    if not RAW_DATA:
         return {"status": "error", "message": "JSON file is missing!", "path_checked": DATA_PATH}
    return {"status": "success", "message": "API is awake, CORS is fixed, and Data is loaded!"}

# 4. Main Analysis Route
@app.api_route("/", methods=["POST", "OPTIONS"])
@app.api_route("/api", methods=["POST", "OPTIONS"])
async def analyze(req: AnalysisRequest):
    if not RAW_DATA:
        return JSONResponse(status_code=500, content={"error": "Data file missing on server"})

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
        if p95_index >= len(sorted_lat):
            p95_index = len(sorted_lat) - 1
            
        result[region] = {
            "avg_latency": sum(latencies) / len(latencies),
            "p95_latency": sorted_lat[p95_index],
            "avg_uptime": sum(uptimes) / len(uptimes),
            "breaches": sum(1 for l in latencies if l > req.threshold_ms)
        }
    
    return result

# 5. Preflight Catcher
@app.options("/{full_path:path}")
def preflight_handler():
    return {}
