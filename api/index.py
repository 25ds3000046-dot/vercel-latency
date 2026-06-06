from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import json
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load data
with open("q-vercel-latency.json") as f:
    RAW_DATA = json.load(f)

class Request(BaseModel):
    regions: List[str]
    threshold_ms: float

@app.post("/")
@app.post("/api")
async def analyze(req: Request):
    result = {}
    for region in req.regions:
        records = [r for r in RAW_DATA if r["region"] == region]
        if not records:
            result[region] = None
            continue
        latencies = [r["latency_ms"] for r in records]
        uptimes = [r["uptime"] for r in records]
        sorted_lat = sorted(latencies)
        p95_index = int(len(sorted_lat) * 0.95)
        result[region] = {
            "avg_latency": sum(latencies) / len(latencies),
            "p95_latency": sorted_lat[p95_index],
            "avg_uptime": sum(uptimes) / len(uptimes),
            "breaches": sum(1 for l in latencies if l > req.threshold_ms)
        }
    return result
