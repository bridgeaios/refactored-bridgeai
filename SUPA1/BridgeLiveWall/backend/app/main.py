import os
import asyncio
import json
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.errors import BridgeError, error_response as _error_response
from app.routes import all_routers
from app.websockets.hub import ConnectionManager
from app.runtime import (
    memory,
    mission_service,
    marketplace_service,
    twins_competition,
    bossbots_service,
    revenue_service,
    sdg_service,
)
from app.services.speech_reasoning import SpeechReasoningService
from app.services.automation import AutomationLoops
from app.cortex import (
    CAPABILITIES,
    capability_enabled,
    auth_class_from_token,
    authority_allows,
    wrap_response,
    get_state_version,
    get_state_hash,
    increment_state_version,
    SCHEMA_VERSION,
    verify_boot_identity,
)
from app.physics import (
    DETERMINISTIC_MODE,
    emit as physics_emit,
    telemetry,
    fallback_for,
    check_economic_risk,
    validate_identity_immutability,
    should_silence_for_ethics,
    get_degradation,
    require_commit_for_canonical,
    replenish_evolution_budget,
)

manager = ConnectionManager()
speech_reasoning = SpeechReasoningService()
automation = AutomationLoops(
    mission=mission_service,
    marketplace=marketplace_service,
    twins=twins_competition,
    bossbots=bossbots_service,
    revenue=revenue_service,
    sdg=sdg_service,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await memory.connect()
    await verify_boot_identity(memory)
    heartbeat_task = asyncio.create_task(manager.heartbeat())
    from app.services.contract_listener import run_listener
    listener_task = asyncio.create_task(run_listener(memory))
    automation.start()
    yield
    await automation.stop()
    listener_task.cancel()
    try:
        await listener_task
    except asyncio.CancelledError:
        pass
    heartbeat_task.cancel()
    try:
        await heartbeat_task
    except asyncio.CancelledError:
        pass
    await memory.disconnect()


app = FastAPI(title="Bridge AI OS", lifespan=lifespan)

_STATUS_MAP: dict[str, int] = {
    "NOT_FOUND": 404,
    "VALIDATION_ERROR": 422,
    "ECONOMIC_GATE_ERROR": 402,
    "AUTH_ERROR": 401,
    "NETWORK_ERROR": 503,
}


@app.exception_handler(BridgeError)
async def _bridge_error_handler(request: Request, exc: BridgeError) -> JSONResponse:
    status = _STATUS_MAP.get(exc.code, 500)
    return JSONResponse(status_code=status, content=_error_response(exc))


origins = [
    "http://localhost:3000", "http://localhost:3001", "http://localhost:3010",
    "http://localhost:3020", "http://localhost:3021", "http://localhost:5173",
    "http://localhost:8081",
    "http://127.0.0.1:3000", "http://127.0.0.1:3001", "http://127.0.0.1:3010",
    "http://127.0.0.1:3020", "http://127.0.0.1:3021", "http://127.0.0.1:5173",
    "http://127.0.0.1:8081",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


@app.middleware("http")
async def cortex_middleware(request: Request, call_next):
    """Cortex: latency discipline, state version header. Real-time vs strategic layers."""
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.0f}"
    return response


for _domain_router in all_routers:
    app.include_router(_domain_router, prefix="/api")

from app.reducers import is_sanctioned, STRICT_MODE, get_registry_snapshot
from app.services.cognitive_twin import CognitiveTwinService
from app.physics import identity_seal


@app.post("/api/state")
async def state_mutation(body: dict):
    """
    Mutate canonical state via sanctioned reducers.
    Authority: internal or orchestrator only. SPINE: Endpoint → Reducer → State → Scheduler → Expression
    """
    from fastapi import HTTPException
    reducer = body.get("reducer")
    payload = body.get("payload") or {}
    auth_token = body.get("authToken")
    if not reducer or not isinstance(reducer, str):
        raise HTTPException(status_code=400, detail="reducer required")
    if not capability_enabled("state_mutation"):
        raise HTTPException(status_code=503, detail="state_mutation capability disabled")
    if STRICT_MODE and not is_sanctioned(reducer):
        raise HTTPException(status_code=400, detail=f"reducer '{reducer}' not sanctioned")
    auth = auth_class_from_token(auth_token)
    if not authority_allows(auth, "state_mutation"):
        raise HTTPException(status_code=403, detail=f"authority {auth.value} cannot mutate state")
    state_version = await increment_state_version(memory)
    auth_class = auth.value
    if reducer == "governanceVote":
        replenish_evolution_budget(5.0, "governance_approval")
    msg = {"type": "stateMutation", "reducer": reducer, "payload": payload, "auth": {"class": auth_class}, "state_version": state_version}
    await manager.broadcast_all(msg)
    telemetry.record_state_mutation()
    physics_emit("state_mutation", {"reducer": reducer, "payload": payload, "state_version": state_version})
    return wrap_response({"broadcast": True}, state_delta=True, state_version=state_version)


@app.get("/")
async def root():
    """API root — service metadata. SPINE: perception-aligned control surface."""
    state_version = await get_state_version(memory)
    registry = get_registry_snapshot()
    twin = CognitiveTwinService()
    profile = twin.get_profile()
    identity = profile.get("identity", {})
    identity_hash = identity_seal(
        json.dumps(identity.get("core_values", [])),
        identity.get("mission_alignment", ""),
        identity.get("authority_class", "public"),
    )
    return {
        "service": "Bridge AI OS API",
        "version": "1.0.0",
        "schema_version": SCHEMA_VERSION,
        "docs": "/docs",
        "health": "/api/health",
        "health_extended": "/api/health/extended",
        "state": "/api/state",
        "state_snapshot": "/api/state/snapshot",
        "gateway": "/gateway",
        "auth_siwe": "/api/auth/siwe",
        "auth_service": "bridge-auth (Node :3030) for full ladder: session, refresh, ws/events",
        "capabilities": "/api/capabilities",
        "telemetry": "/api/telemetry",
        "spine": "Endpoint → Reducer → State → Scheduler → Expression",
        "loop": "Perception → Decision → Expression → Economic Effect → State Update → Evolution",
        "organism_mode": "reactive",  # Responds only to input. Agentic requires internal goal vector + background scheduler.
        "physics": ["determinism", "event_bus", "failure_modes", "observability", "risk_governor", "identity_immutability", "ethical_conflict", "degradation", "simulation_isolation", "upgrade_governance"],
        "state_version": state_version,
        "identity_hash": identity_hash,
        "reducer_identity_hash": registry.get("identity_hash"),
        "frontend": "http://localhost:3010",
    }


@app.get("/api/capabilities")
async def get_capabilities():
    """Capability registry. Twins read flags before acting. Scale to 100 variants."""
    from app.cortex import get_capability_audit_log
    return {
        "ok": True,
        "data": {k: capability_enabled(k) for k in CAPABILITIES},
        "meta": {"state_delta": False},
        "audit_log": get_capability_audit_log(),
    }


@app.get("/api/state/reducers")
async def list_sanctioned_reducers():
    """Immutable snapshot. Ties allowed mutation to system identity. SPINE: no rogue mutation."""
    return get_registry_snapshot()


@app.get("/api/state/snapshot")
async def state_snapshot():
    """
    Full state snapshot. Version without snapshot is memory without recall.
    Returns: state, state_version, state_hash.
    """
    from app.services.mission import MissionService
    mission_svc = MissionService(memory)
    state_version = await get_state_version(memory)
    state_hash = await get_state_hash(memory)
    xml = await memory.get("twin:shared_xml") or ""
    board = await mission_svc.get_counts()
    state = {
        "shared_xml": xml[:2000] if xml else "",
        "mission_board": board,
    }
    return {
        "state": state,
        "state_version": state_version,
        "state_hash": state_hash,
    }


@app.get("/api/telemetry")
async def get_telemetry():
    """Observability: decision_latency, speech_latency, silence_rate, state_mutation_frequency, economic_conversion_rate."""
    return wrap_response(telemetry.to_dict(), state_delta=False)


@app.websocket("/ws/{channel}")
async def websocket_endpoint(websocket: WebSocket, channel: str):
    await manager.connect(channel, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Expect JSON messages; minimal routing
            try:
                msg = json.loads(data)
            except Exception:
                await websocket.send_text(json.dumps({"type":"error","error":"invalid_json"}))
                continue
            t = msg.get("type")
            if t == "hello":
                await websocket.send_text(json.dumps({"type":"welcome","ts": asyncio.get_event_loop().time()}))
            elif t == "subscribe":
                pass
            elif "prompt" in msg or t == "transcript":
                # ASR transcript → reasoning buffer → response (never raw execution)
                raw = (msg.get("prompt") or msg.get("transcript") or "").strip()
                result = speech_reasoning.process(raw, context={"channel": channel})
                payload = speech_reasoning.to_dict(result)
                out = {
                    "type": "response",
                    "response": result.response,
                    "emotion_state": result.emotion,
                    "topic": result.topic,
                    "reasoning": payload,
                }
                await websocket.send_text(json.dumps(out))
            else:
                await manager.broadcast(channel, msg)
    except WebSocketDisconnect:
        await manager.disconnect(channel, websocket)
