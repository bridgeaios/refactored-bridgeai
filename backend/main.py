from fastapi import FastAPI, HTTPException, Request, Header
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def verify_edge_access(x_edge_authorized: Optional[str] = Header(None)):
    if os.getenv("EDGE_MODE") == "required" and x_edge_authorized != "true":
        raise HTTPException(
            status_code=401, detail="Unauthorized: Must pass through edge"
        )


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "bridge-backend",
        "edge_mode": os.getenv("EDGE_MODE", "disabled"),
    }


@app.post("/run-task")
async def run_task(
    data: dict,
    request: Request,
    x_edge_authorized: Optional[str] = Header(None),
):
    verify_edge_access(x_edge_authorized)

    request_id = request.headers.get("X-Request-ID", "unknown")
    edge_ray = request.headers.get("X-Edge-Ray", "unknown")

    return {
        "status": "success",
        "data": data,
        "requestId": request_id,
        "edgeRay": edge_ray,
    }


@app.get("/internal/treasury/summary")
async def treasury_summary(
    x_edge_authorized: Optional[str] = Header(None),
    authorization: Optional[str] = Header(None),
):
    verify_edge_access(x_edge_authorized)

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Admin authorization required")

    return {
        "totalDistributed": 0,
        "totalFees": 0,
        "executionCount": 0,
    }
