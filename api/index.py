from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
import json
import os

app = FastAPI()

# 1. Hardcoded Headers (Bypassing middleware unreliability)
CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, Authorization, Accept",
}

# 2. File Loading
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(CURRENT_DIR, "q-vercel-latency.json")

RAW_DATA = []
if os.path.exists(DATA_PATH):
    with open(DATA_PATH) as f:
        RAW_DATA = json.load(f)

class AnalysisRequest(BaseModel):
    regions: List[str]
    threshold_ms: float

# 3. Health Route (Forcing headers)
@app.api_route("/", methods=["GET"])
@app.api_route("/api", methods=["GET"])
def health_check():
    if not RAW_DATA:
         return JSONResponse(
             content={"status": "error", "message": "JSON missing"}, 
             headers=CORS_HEADERS
         )
    return JSONResponse(
        content={"status": "success", "message": "API is awake!"}, 
        headers=CORS_HEADERS
    )

# 4. Main Route (Forcing headers)
@app.api_route("/", methods=["POST"])
@app.api_route("/api", methods=["POST"])
async def analyze(req: AnalysisRequest):
    if not RAW_DATA:
        return JSONResponse(
            status_code=500, 
            content={"error": "Data file missing"}, 
            headers=CORS_HEADERS
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
        if p95_index >= len(sorted_lat):
            p95_index = len(sorted_lat) - 1
            
        result[region] = {
            "avg_latency": sum(latencies) / len(latencies),
            "p95_latency": sorted_lat[p95_index],
            "avg_uptime": sum(uptimes) / len(uptimes),
            "breaches": sum(1 for l in latencies if l > req.threshold_ms)
        }
    
    # Explicitly stapling the header to the outgoing data
    return JSONResponse(content=result, headers=CORS_HEADERS)

# 5. Manual Preflight Catcher (Forcing headers)
@app.options("/{full_path:path}")
def preflight_handler(request: Request, full_path: str):
    return JSONResponse(content={}, headers=CORS_HEADERS)
