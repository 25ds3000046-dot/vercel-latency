from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
import json
from pathlib import Path

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # This adds the Access-Control-Allow-Origin: * header
    allow_credentials=True,
    allow_methods=["*"],  # Allows all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

DATA_PATH = Path(__file__).parent.parent / "q-vercel-latency.json"
with open(DATA_PATH) as f:
    RAW_DATA = json.load(f)

class Request(BaseModel):
    regions: List[str]
    threshold_ms: float

# This tells FastAPI to accept GET, POST, and OPTIONS on the root URL
@app.api_route("/", methods=["GET", "POST", "OPTIONS"])
@app.api_route("/api", methods=["GET", "POST", "OPTIONS"])

def latency_check():
    return {"status": "success", "message": "Latency check complete!"}
    
async def analyze(req: Request):
    result = {}
    for region in req.regions:
        records = [r for r in RAW_DATA if r["region"] == region]
        if not records:
            result[region] = None
            continue
        latencies = [r["latency_ms"] for r in records]
        uptimes = [r["uptime_pct"] for r in records]
        sorted_lat = sorted(latencies)
        p95_index = int(len(sorted_lat) * 0.95)
        result[region] = {
            "avg_latency": sum(latencies) / len(latencies),
            "p95_latency": sorted_lat[p95_index],
            "avg_uptime": sum(uptimes) / len(uptimes),
            "breaches": sum(1 for l in latencies if l > req.threshold_ms)
        }
    return JSONResponse(
        content=result,
        headers={"Access-Control-Allow-Origin": "*"}
    )
