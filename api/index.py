# api/index.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
import statistics
import json

app = FastAPI()

# Enable CORS for POST requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_methods=["POST"],  # Only allows POST method
    allow_headers=["*"],  # Allows all headers
)

@app.post("/analytics")
async def analytics_endpoint(request: Request):
    # Parse the JSON body
    data = await request.json()
    regions: List[str] = data.get("regions", [])
    threshold_ms: float = data.get("threshold_ms", 180)
    
    # Load the telemetry data from JSON file
    try:
        with open("q-vercel-latency.json", "r") as f:
            telemetry_data = json.load(f)
    except FileNotFoundError:
        # Return error if file not found
        return {
            "error": "Telemetry data file not found",
            "results": []
        }
    except json.JSONDecodeError:
        # Return error if JSON is invalid
        return {
            "error": "Invalid telemetry data format",
            "results": []
        }
    
    # Calculate metrics per region
    results = []
    
    for region in regions:
        # Filter data for this region
        region_data = [record for record in telemetry_data if record.get("region") == region]
        
        if not region_data:
            results.append({
                "region": region,
                "avg_latency": 0,
                "p95_latency": 0,
                "avg_uptime": 0,
                "breaches": 0
            })
            continue
        
        # Extract latency values
        latencies = [record.get("latency_ms", 0) for record in region_data]
        uptimes = [record.get("uptime", 0) for record in region_data]
        
        # Calculate average latency (mean)
        avg_latency = statistics.mean(latencies) if latencies else 0
        
        # Calculate p95 (95th percentile)
        sorted_latencies = sorted(latencies)
        p95_index = int(len(sorted_latencies) * 0.95)
        p95_latency = sorted_latencies[min(p95_index, len(sorted_latencies) - 1)]
        
        # Calculate average uptime (mean)
        avg_uptime = statistics.mean(uptimes) if uptimes else 0
        
        # Count breaches (records above threshold)
        breaches = sum(1 for latency in latencies if latency > threshold_ms)
        
        results.append({
            "region": region,
            "avg_latency": round(avg_latency, 2),
            "p95_latency": round(p95_latency, 2),
            "avg_uptime": round(avg_uptime, 2),
            "breaches": breaches
        })
    
    return {"results": results}
