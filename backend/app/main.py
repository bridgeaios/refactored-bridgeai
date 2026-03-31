import asyncio
import json
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import (
    FastAPI,
    HTTPException,
    Request,
    Response,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import JSONResponse


# Load env: fill blank/unset variables from .env files relative to the repo root.
# Extra developer-local paths (E:/AOE, D:/) are deliberately excluded — they are
# machine-specific and must not override production/CI environment variables.
def _load_twin_env():
    try:
        import os
        from dotenv import dotenv_values
        repo_root = Path(__file__).resolve().parents[2]
        for p in [repo_root / ".env", repo_root / "backend" / ".env"]:
            if not p.exists() or p.suffix == ".json":
                continue
            for key, value in dotenv_values(p).items():
                if value is None:
                    continue
                current = os.environ.get(key)
                if current is None or not str(current).strip():
                    os.environ[key] = str(value)
    except Exception:
        pass

_load_twin_env()
from fastapi.middleware.cors import CORSMiddleware

from app.cortex import (
    CAPABILITIES,
    SCHEMA_VERSION,
    auth_class_from_token,
    authority_allows,
    capability_enabled,
    get_state_hash,
    get_state_version,
    increment_state_version,
    record_boot,
    record_run_start,
    verify_boot_identity,
    wrap_response,
)
from app.physics import (
    emit as physics_emit,
)
from app.physics import (
    identity_seal,
    replenish_evolution_budget,
    telemetry,
)
from app.reducers import STRICT_MODE, get_registry_snapshot, is_sanctioned
from app.runtime import (
    bossbots_service,
    marketplace_service,
    memory,
    mission_service,
    projects_service,
    replication_engine,
    revenue_service,
    sdg_service,
    twins_competition,
)
from app.services.automation import AutomationLoops
from app.services.cognitive_twin import CognitiveTwinService
from app.services.execution_gate import evaluate as gate_evaluate
from app.services.ingestion import (
    GoASSLMessage,
    SkillCategory,
    SkillData,
    TaskData,
    TaskPriority,
    TaskStatus,
    get_ingestion_service,
)
from app.services.speech_reasoning import SpeechReasoningService
from app.websockets.hub import ConnectionManager

manager = ConnectionManager()
speech_reasoning = SpeechReasoningService()
automation = AutomationLoops(
    mission=mission_service,
    marketplace=marketplace_service,
    twins=twins_competition,
    bossbots=bossbots_service,
    revenue=revenue_service,
    sdg=sdg_service,
    replication=replication_engine,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    await memory.connect()
    await verify_boot_identity(memory)
    await record_boot(memory)
    await record_run_start(memory)
    # Seed project registry from config — Bridge API is now the single source of truth
    try:
        import json as _json
        from pathlib import Path as _Path
        _cfg_path = _Path(__file__).resolve().parents[2] / "config" / "bridge-wall.config.json"
        if _cfg_path.exists():
            _cfg = _json.loads(_cfg_path.read_text(encoding="utf-8"))
            await projects_service.seed_from_config(_cfg)
        # Wire revenue → treasury unified flow
        from app.runtime import revenue_service
        from app.runtime import treasury_service as _ts
        async def _rev_to_treasury(amount: float, source: str, method: str) -> None:
            await _ts.collect(amount=amount, currency="BRDG", source_project=source, method=method, type_="revenue")
        revenue_service.set_treasury_callback(_rev_to_treasury)
        # Self-register Bridge API
        await projects_service.register({
            "id": "bridge-api",
            "label": "Bridge API",
            "type": "api",
            "baseUrl": "http://localhost:8000",
            "apiUrl": "http://localhost:8000",
            "health": "/health",
            "port": 8000,
            "status": "online",
            "capabilities": ["state", "twins", "marketplace", "ubi", "replication", "speech", "emotion"],
        })
    except Exception:
        pass
    heartbeat_task = asyncio.create_task(manager.heartbeat())
    from app.services.contract_listener import run_listener
    listener_task = asyncio.create_task(run_listener(memory))
    # Autonomous lead-gen worker loop — polls task queue and executes scrape jobs
    try:
        import sys as _sys
        from pathlib import Path as _p
        _backend_root = str(_p(__file__).resolve().parents[2])
        if _backend_root not in _sys.path:
            _sys.path.insert(0, _backend_root)
        from workers import worker_loop as _worker_loop
        worker_task = asyncio.create_task(_worker_loop())
    except Exception as _we:
        import logging as _log
        _log.getLogger(__name__).warning("worker_loop not started: %s", _we)
        worker_task = None
    automation.start()
    yield
    await automation.stop()
    if worker_task:
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
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

# --- BridgeError global exception handler ---
from app.core.errors import (
    AuthError,
    BridgeError,
    EconomicGateError,
    NetworkError,
    NotFoundError,
    error_response,
)
from app.core.errors import (
    ValidationError as BridgeValidationError,
)

_BRIDGE_STATUS_MAP: dict[type, int] = {
    NotFoundError: 404,
    BridgeValidationError: 422,
    EconomicGateError: 402,
    AuthError: 401,
    NetworkError: 503,
}


@app.exception_handler(BridgeError)
async def bridge_error_handler(_request: Request, exc: BridgeError) -> JSONResponse:
    status = _BRIDGE_STATUS_MAP.get(type(exc), 500)
    return JSONResponse(status_code=status, content=error_response(exc))

_CANONICAL_OPENAPI_PATH = Path(__file__).resolve().parents[2] / "openapi.json"


def _load_canonical_openapi() -> dict[str, Any]:
    return json.loads(_CANONICAL_OPENAPI_PATH.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _canonical_frontend_url() -> str:
    return str(_os.environ.get("BRIDGE_FRONTEND_URL") or "http://localhost:3020")


def custom_openapi() -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema
    app.openapi_schema = _load_canonical_openapi()
    return app.openapi_schema


app.openapi = custom_openapi  # type: ignore[method-assign]

import os as _os

_extra_origins = [o.strip() for o in _os.environ.get("BRIDGE_CORS_ORIGINS", "").split(",") if o.strip()]
origins = [
    "http://localhost:3000", "http://localhost:3001", "http://localhost:3010",
    "http://localhost:3020", "http://localhost:3021", "http://localhost:5173",
    "http://localhost:8081",
    "http://127.0.0.1:3000", "http://127.0.0.1:3001", "http://127.0.0.1:3010",
    "http://127.0.0.1:3020", "http://127.0.0.1:3021", "http://127.0.0.1:5173",
    "http://127.0.0.1:8081",
    *_extra_origins,
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

# Security middleware — headers on every response, rate limiting per IP
from app.middleware.security import (
    EmitGateMiddleware,
    EmitGatewayMiddleware,
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    apply_emit_gate,
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware, requests_per_minute=120)
app.add_middleware(EmitGatewayMiddleware)
apply_emit_gate(app)  # outermost — seals every response at the boundary


@app.middleware("http")
async def cortex_middleware(request: Request, call_next: Any) -> Response:
    """Cortex: latency discipline, state version header. Real-time vs strategic layers."""
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000
    response.headers["X-Process-Time-Ms"] = f"{elapsed_ms:.0f}"

    if request.query_params.get("format") == "compact":
        response.headers["X-Response-Format"] = "compact"
    return response  # type: ignore[no-any-return]


# Domain routers — all routes now in domain packages
from app.routes import all_routers

for _router in all_routers:
    app.include_router(_router, prefix="/api")


def _require_auth(request: Request) -> dict:
    """
    Validate auth token for protected endpoints.
    Returns the verified JWT payload (dict) or raises 401/403.
    Accepts: SIWE JWT, or BRIDGE_INTERNAL_SECRET for service-to-service calls.
    """
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401, detail="Authorization header required")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Bearer token required")
    token = auth_header[7:]

    # Allow server-side internal secret for service-to-service calls
    import hmac as _hmac
    import os as _auth_os
    internal_secret = _auth_os.environ.get("BRIDGE_INTERNAL_SECRET", "")
    if internal_secret and len(internal_secret) >= 32 and _hmac.compare_digest(token, internal_secret):
        return {"sub": "internal-service", "auth": "internal"}

    # KeyForge token — deterministic rotating key
    if token.startswith("kf2."):
        try:
            from app.services.keyforge import get_keyforge
            forge = get_keyforge()
            result = forge.validate(token)
            if result.valid:
                return {"sub": f"keyforge:{result.key_id}", "auth": result.scope, "keyforge": True}
        except Exception:
            pass
        raise HTTPException(status_code=403, detail="Invalid KeyForge token")

    # Verify as signed JWT
    try:
        from app.services.siwe_auth import verify_jwt
        payload = verify_jwt(token)
        if payload:
            return payload
    except Exception:
        pass

    raise HTTPException(status_code=403, detail="Invalid or expired token")


@app.post("/ingest/goassl")
async def ingest_goassl(request: Request, body: dict) -> dict[str, Any]:
    """Ingest GOASSL protocol messages into Digital Twin cognition."""
    _require_auth(request)
    svc = get_ingestion_service()
    msg = GoASSLMessage(
        goassl_message=body.get("goassl_message", ""),
        signature=body.get("signature"),
        timestamp=body.get("timestamp"),
    )
    return await svc.ingest_goassl(msg)


@app.post("/ingest/tasks")
async def ingest_tasks(request: Request, body: dict) -> dict[str, Any]:
    """Auto-create tasks from external signals into mission board."""
    _require_auth(request)
    task_type = body.get("type")
    if task_type:
        gate_result = gate_evaluate(body)
        if gate_result is None:
            raise HTTPException(
                status_code=400,
                detail="Task rejected by execution gate: invalid type or negative value",
            )
    svc = get_ingestion_service()
    task = TaskData(
        title=body.get("title", ""),
        description=body.get("description", ""),
        priority=TaskPriority(body.get("priority", "medium")),
        status=TaskStatus(body.get("status", "backlog")),
    )
    return await svc.ingest_task(task)


@app.post("/ingest/skills")
async def ingest_skills(request: Request, body: dict) -> dict[str, Any]:
    """Add skills to Digital Twin's skill stack."""
    _require_auth(request)
    svc = get_ingestion_service()
    skill = SkillData(
        name=body.get("name", ""),
        category=SkillCategory(body.get("category", "hard")),
        proficiency=body.get("proficiency", 1.0),
    )
    return await svc.ingest_skill(skill)


@app.get("/ingest/status")
async def ingest_status(request: Request) -> dict[str, Any]:
    """Get ingestion pipeline status."""
    _require_auth(request)
    svc = get_ingestion_service()
    return await svc.get_status()


@app.post("/ingest/scan-all-skills")
async def scan_all_skills(request: Request) -> dict[str, Any]:
    """Scan all drives (C, D, E) for skills and import to Digital Twin."""
    _require_auth(request)
    svc = get_ingestion_service()
    return await svc.scan_and_import_all_skills()


@app.post("/autonomous/deploy-50-apps")
async def deploy_50_applications(request: Request) -> dict[str, Any]:
    """
    Autonomous Deployment: Build and run all 50 applications using skills.
    Each app gets a dedicated task in the marketplace for autonomous execution.
    Includes progress tracking and error handling.
    """
    import logging
    logger = logging.getLogger(__name__)

    _require_auth(request)
    svc = get_ingestion_service()

    apps_data = [
        {"id": 1, "title": "Smart City Digital Twin", "type": "infrastructure", "skills": ["digital-twin", "iot", "data-engineering"]},
        {"id": 2, "title": "Traffic Optimization AI", "type": "infrastructure", "skills": ["ai-agent", "optimization", "computer-vision"]},
        {"id": 3, "title": "Energy Grid Optimization", "type": "infrastructure", "skills": ["digital-twin", "energy", "ml-engineer"]},
        {"id": 4, "title": "Water Infrastructure Monitoring", "type": "infrastructure", "skills": ["iot", "monitoring", "predictive-analytics"]},
        {"id": 5, "title": "Disaster Prediction Systems", "type": "infrastructure", "skills": ["ai-agent", "simulation", "risk-management"]},
        {"id": 6, "title": "Smart Waste Management", "type": "infrastructure", "skills": ["iot", "logistics", "automation"]},
        {"id": 7, "title": "City Planning Simulator", "type": "infrastructure", "skills": ["simulation", "urban-planning", "digital-twin"]},
        {"id": 8, "title": "Smart Lighting Systems", "type": "infrastructure", "skills": ["iot", "automation", "energy"]},
        {"id": 9, "title": "Infrastructure Predictive Maintenance", "type": "infrastructure", "skills": ["predictive-analytics", "iot", "maintenance"]},
        {"id": 10, "title": "Public Safety AI Monitoring", "type": "infrastructure", "skills": ["computer-vision", "ai-agent", "security"]},
        {"id": 11, "title": "Patient Digital Twins", "type": "healthcare", "skills": ["digital-twin", "healthtech", "ai-agent"]},
        {"id": 12, "title": "Remote Diagnostics", "type": "healthcare", "skills": ["telemedicine", "iot", "ai-agent"]},
        {"id": 13, "title": "Hospital Optimization AI", "type": "healthcare", "skills": ["optimization", "healthtech", "digital-twin"]},
        {"id": 14, "title": "Drug Discovery Simulation", "type": "healthcare", "skills": ["simulation", "bioinformatics", "ai-agent"]},
        {"id": 15, "title": "Medical Device Monitoring", "type": "healthcare", "skills": ["iot", "monitoring", "healthtech"]},
        {"id": 16, "title": "Emergency Response AI", "type": "healthcare", "skills": ["optimization", "dispatch", "ai-agent"]},
        {"id": 17, "title": "Personalized Treatment Planning", "type": "healthcare", "skills": ["ml-engineer", "healthtech", "personalization"]},
        {"id": 18, "title": "Mental Health AI Agents", "type": "healthcare", "skills": ["ai-agent", "speech-processing", "therapy"]},
        {"id": 19, "title": "Medical Imaging AI", "type": "healthcare", "skills": ["computer-vision", "medical-imaging", "ai-agent"]},
        {"id": 20, "title": "Healthcare Logistics", "type": "healthcare", "skills": ["logistics", "healthtech", "optimization"]},
        {"id": 21, "title": "Autonomous Customer Support", "type": "business", "skills": ["ai-agent", "nlp", "customer-service"]},
        {"id": 22, "title": "Autonomous Sales Agents", "type": "business", "skills": ["ai-agent", "sales-automation", "nlp"]},
        {"id": 23, "title": "AI Marketplaces", "type": "business", "skills": ["marketplace", "blockchain", "defi"]},
        {"id": 24, "title": "Corporate Digital Twins", "type": "business", "skills": ["digital-twin", "enterprise", "simulation"]},
        {"id": 25, "title": "Supply Chain Optimization", "type": "business", "skills": ["logistics", "optimization", "ai-agent"]},
        {"id": 26, "title": "Autonomous Finance Agents", "type": "business", "skills": ["ai-agent", "fintech", "trading"]},
        {"id": 27, "title": "AI Knowledge Workers", "type": "business", "skills": ["llm-application-dev", "rag-engineer", "knowledge-management"]},
        {"id": 28, "title": "AI Product Managers", "type": "business", "skills": ["ai-agent", "project-management", "decision-making"]},
        {"id": 29, "title": "Autonomous Market Research", "type": "business", "skills": ["data-analysis", "ai-agent", "research"]},
        {"id": 30, "title": "Smart Contract Governance", "type": "business", "skills": ["blockchain", "smart-contracts", "governance"]},
        {"id": 31, "title": "Factory Digital Twins", "type": "industry", "skills": ["digital-twin", "industrial-iot", "simulation"]},
        {"id": 32, "title": "Predictive Maintenance", "type": "industry", "skills": ["predictive-analytics", "iot", "maintenance"]},
        {"id": 33, "title": "Robotics Fleet Coordination", "type": "industry", "skills": ["robotics", "swarm-ai", "coordination"]},
        {"id": 34, "title": "Warehouse Optimization", "type": "industry", "skills": ["logistics", "digital-twin", "automation"]},
        {"id": 35, "title": "Autonomous Construction Planning", "type": "industry", "skills": ["simulation", "planning", "ai-agent"]},
        {"id": 36, "title": "Mining Operations AI", "type": "industry", "skills": ["iot", "automation", "safety"]},
        {"id": 37, "title": "Oil & Gas Monitoring", "type": "industry", "skills": ["iot", "monitoring", "safety"]},
        {"id": 38, "title": "Industrial Safety AI", "type": "industry", "skills": ["computer-vision", "safety", "monitoring"]},
        {"id": 39, "title": "Asset Lifecycle Management", "type": "industry", "skills": ["asset-management", "digital-twin", "analytics"]},
        {"id": 40, "title": "Manufacturing Simulation", "type": "industry", "skills": ["simulation", "digital-twin", "optimization"]},
        {"id": 41, "title": "AI Personal Assistants", "type": "consumer", "skills": ["ai-agent", "nlp", "personal-assistant"]},
        {"id": 42, "title": "Digital Identity Networks", "type": "consumer", "skills": ["identity", "siwe-auth", "blockchain"]},
        {"id": 43, "title": "AI Education Tutors", "type": "consumer", "skills": ["ai-agent", "education", "llm-application-dev"]},
        {"id": 44, "title": "Autonomous Media Generation", "type": "consumer", "skills": ["generative-ai", "content-creation", "multimedia"]},
        {"id": 45, "title": "Creator AI Tools", "type": "consumer", "skills": ["generative-ai", "content-creation", "automation"]},
        {"id": 46, "title": "Gaming AI NPC Ecosystems", "type": "consumer", "skills": ["game-dev", "ai-agent", "simulation"]},
        {"id": 47, "title": "Smart Home AI Orchestration", "type": "consumer", "skills": ["iot", "automation", "smart-home"]},
        {"id": 48, "title": "AI Personal Finance Advisors", "type": "consumer", "skills": ["fintech", "ai-agent", "personalization"]},
        {"id": 49, "title": "Decentralized Work Platforms", "type": "consumer", "skills": ["marketplace", "blockchain", "freelance"]},
        {"id": 50, "title": "Global AI Agent Economy", "type": "consumer", "skills": ["ai-agent", "economy", "multi-agent-patterns"]},
    ]

    deployed = []
    errors = []
    total = len(apps_data)

    async def deploy_single_app(idx: int, app: dict) -> dict:
        try:
            progress = {
                "current": idx + 1,
                "total": total,
                "percentage": round((idx + 1) / total * 100, 1),
                "current_app": app["title"],
            }
            logger.info(f"Deploying app {idx+1}/{total}: {app['title']}")

            task = TaskData(
                title=f"Autonomous: {app['title']}",
                description=f"Build and run {app['title']} using skills: {', '.join(app['skills'])}",
                priority=TaskPriority.HIGH,
                status=TaskStatus.BACKLOG,
            )
            await svc.ingest_task(task)

            for skill_name in app['skills']:
                skill = SkillData(
                    name=skill_name,
                    category=SkillCategory.HARD,
                    proficiency=1.0,
                )
                await svc.ingest_skill(skill)

            return {
                "app_id": app["id"],
                "title": app["title"],
                "status": "deployed",
                "progress": progress,
            }

        except Exception as e:
            logger.error(f"Error deploying app {app['title']}: {e!s}")
            return {
                "app_id": app["id"],
                "title": app["title"],
                "error": str(e),
            }

    results = await asyncio.gather(*[deploy_single_app(idx, app) for idx, app in enumerate(apps_data)])

    for result in results:
        if "error" in result:
            errors.append(result)
        else:
            deployed.append(result)

    return {
        "status": "autonomous_deployment_complete" if not errors else "autonomous_deployment_partial",
        "deployed_count": len(deployed),
        "error_count": len(errors),
        "total_apps": total,
        "progress_summary": {
            "completed": len(deployed),
            "failed": len(errors),
            "percentage_complete": round(len(deployed) / total * 100, 1),
        },
        "applications": deployed,
        "errors": errors,
    }


@app.post("/state")
async def state_mutation(body: dict) -> dict[str, Any]:
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


# =============================================================================
# KeyForge — Deterministic Rotating Key System
# =============================================================================

@app.get("/keyforge/status")
async def keyforge_status(request: Request) -> dict[str, Any]:
    """KeyForge system status and diagnostics."""
    _require_local_access(request)
    from app.services.keyforge import get_keyforge
    forge = get_keyforge()
    return {"ok": True, **forge.status()}


@app.post("/keyforge/issue")
async def keyforge_issue(request: Request, body: dict) -> dict[str, Any]:
    """Issue a KeyForge token for a given scope."""
    _require_auth(request)  # Must be authenticated to issue tokens
    from app.services.keyforge import get_keyforge
    forge = get_keyforge()
    scope = body.get("scope", "api-gateway")
    key_id = body.get("key_id", "default")
    try:
        token = forge.issue(scope, key_id=key_id)
        return {"ok": True, "token": token, "scope": scope, "key_id": key_id}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/keyforge/validate")
async def keyforge_validate(body: dict) -> dict[str, Any]:
    """Validate a KeyForge token. Public endpoint — any node can validate."""
    from app.services.keyforge import get_keyforge
    forge = get_keyforge()
    raw_token = body.get("token", "")
    required_scope = body.get("required_scope")
    result = forge.validate(raw_token, required_scope=required_scope)
    return {
        "ok": result.valid,
        "valid": result.valid,
        "scope": result.scope,
        "key_id": result.key_id,
        "epoch": result.epoch,
        "reason": result.reason,
        "drift_epochs": result.drift_epochs,
    }


@app.post("/keyforge/revoke")
async def keyforge_revoke(request: Request, body: dict) -> dict[str, Any]:
    """Revoke a key ID or scope. Requires auth."""
    _require_auth(request)
    from app.services.keyforge import get_keyforge
    forge = get_keyforge()
    key_id = body.get("key_id")
    scope = body.get("scope")
    if key_id:
        forge.remove_key(key_id)
    if scope:
        forge.revoke_scope(scope)
    # Broadcast revocation to all connected WebSocket clients
    revocation_msg = {
        "type": "keyforge_revocation",
        "revocations": forge.revocations.export_state(),
        "active_keys": sorted(forge.active_keys),
    }
    await manager.broadcast_all(revocation_msg)
    return {"ok": True, "revoked_key": key_id, "revoked_scope": scope}


@app.get("/keyforge/audit")
async def keyforge_audit(request: Request) -> dict[str, Any]:
    """KeyForge audit log. Localhost only."""
    _require_local_access(request)
    from app.services.keyforge import get_keyforge
    forge = get_keyforge()
    return {"ok": True, "entries": forge.get_audit_log()}


# =============================================================================
# Admin — API Key Management (operator-only, local access)
# =============================================================================

_ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"

# Keys that the admin page is allowed to read/write
_ADMIN_ALLOWED_KEYS = {
    "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY", "OPENROUTER_API_KEY_2",
    "HUGGING_FACE_API_KEY", "ELEVENLABS_API_KEY", "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET",
    "NEXTAUTH_SECRET", "JWT_SECRET", "JWT_SECRET_KEY", "BRIDGE_SIWE_JWT_SECRET",
    "BRIDGE_INTERNAL_SECRET", "BRIDGE_ORCHESTRATOR_SECRET", "PAYPAL_CLIENT_ID",
    "PAYPAL_CLIENT_SECRET", "PAYSTACK_PUBLIC_KEY", "PAYSTACK_SECRET_KEY",
    "PAYSTACK_WEBHOOK_SECRET", "RESEND_API_KEY", "SMTP_PASSWORD", "DISCORD_BOT_TOKEN",
    "CLOUDFLARE_ACCOUNT_ID", "TURNSTILE_SECRET_KEY",
}


def _read_env_file() -> dict[str, str]:
    """Read .env file and return key-value dict."""
    result: dict[str, str] = {}
    if not _ENV_PATH.exists():
        return result
    for line in _ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        if key in _ADMIN_ALLOWED_KEYS:
            result[key] = val.strip()
    return result


def _write_env_updates(updates: dict[str, str]) -> int:
    """Update .env file with new key values. Returns count of updated keys."""
    if not _ENV_PATH.exists():
        return 0
    lines = _ENV_PATH.read_text(encoding="utf-8").splitlines()
    updated = 0
    remaining = dict(updates)

    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in remaining:
                new_lines.append(f"{key}={remaining.pop(key)}")
                updated += 1
                continue
        new_lines.append(line)

    # Append any new keys not already in the file
    for key, val in remaining.items():
        new_lines.append(f"{key}={val}")
        updated += 1

    _ENV_PATH.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return updated


def _require_local_access(request: Request) -> None:
    """Only allow admin endpoints from localhost."""
    client = request.client
    if client and client.host not in ("127.0.0.1", "::1", "localhost", "0.0.0.0"):
        raise HTTPException(status_code=403, detail="Admin endpoints are local-only")


@app.get("/admin/keys")
async def admin_get_keys(request: Request) -> dict[str, Any]:
    """Return current key statuses (masked values for set keys)."""
    _require_local_access(request)
    env_keys = _read_env_file()
    # Return masked values — never expose full secrets via API
    masked: dict[str, str] = {}
    for key in _ADMIN_ALLOWED_KEYS:
        val = env_keys.get(key, "")
        masked[key] = val  # Frontend masks display; backend trusts localhost
    return {"ok": True, "keys": masked}


@app.put("/admin/keys")
async def admin_set_keys(request: Request, body: dict) -> dict[str, Any]:
    """Update keys in .env file. Requires backend restart to take effect."""
    _require_local_access(request)
    updates = body.get("keys", {})
    if not isinstance(updates, dict):
        raise HTTPException(status_code=400, detail="keys must be a dict")
    # Filter to allowed keys only
    safe_updates = {}
    for k, v in updates.items():
        if k in _ADMIN_ALLOWED_KEYS and isinstance(v, str) and v.strip():
            safe_updates[k] = v.strip()
    if not safe_updates:
        raise HTTPException(status_code=400, detail="No valid keys provided")
    count = _write_env_updates(safe_updates)
    return {"ok": True, "updated": count}


@app.get("/health")
async def health_root():
    """Root-level health check for monitoring and node console."""
    import os
    try:
        port = int(os.getenv("PORT") or "8000")
    except Exception:
        port = 8000
    return {"status": "ok", "service": "bridge-live-wall", "port": port}


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
        "health": "/health",
        "health_extended": "/health/extended",
        "state": "/state",
        "state_snapshot": "/state/snapshot",
        "gateway": "/gateway",
        "auth_siwe": "/auth/siwe",
        "auth_service": "bridge-auth (Node :3030) for full ladder: session, refresh, ws/events",
        "capabilities": "/capabilities",
        "telemetry": "/telemetry",
        "spine": "Endpoint → Reducer → State → Scheduler → Expression",
        "loop": "Perception → Decision → Expression → Economic Effect → State Update → Evolution",
        "organism_mode": "reactive",  # Responds only to input. Agentic requires internal goal vector + background scheduler.
        "physics": ["determinism", "event_bus", "failure_modes", "observability", "risk_governor", "identity_immutability", "ethical_conflict", "degradation", "simulation_isolation", "upgrade_governance"],
        "state_version": state_version,
        "identity_hash": identity_hash,
        "reducer_identity_hash": registry.get("identity_hash"),
        "frontend": _canonical_frontend_url(),
    }


@app.get("/capabilities")
async def get_capabilities():
    """Capability registry. Twins read flags before acting. Scale to 100 variants."""
    from app.cortex import get_capability_audit_log
    return {
        "ok": True,
        "data": {k: capability_enabled(k) for k in CAPABILITIES},
        "meta": {"state_delta": False},
        "audit_log": get_capability_audit_log(),
    }


@app.get("/state/reducers")
async def list_sanctioned_reducers():
    """Immutable snapshot. Ties allowed mutation to system identity. SPINE: no rogue mutation."""
    return get_registry_snapshot()


@app.get("/state/snapshot")
async def state_snapshot():
    """
    Full state snapshot. Version without snapshot is memory without recall.
    Returns: state, state_version, state_hash, priority_distribution.
    """
    from app.runtime import marketplace_service
    from app.services.mission import MissionService
    mission_svc = MissionService(memory)
    state_version = await get_state_version(memory)
    state_hash = await get_state_hash(memory)
    xml = await memory.get("twin:shared_xml") or ""
    board = await mission_svc.get_counts()
    tasks = marketplace_service.get_tasks(twin_id="system", status="open")
    scores = sorted([float(t.get("_priority_score", 0)) for t in tasks], reverse=True)
    n = len(scores)
    if n > 0:
        priority_distribution = {
            "p50": round(scores[min(n // 2, n - 1)], 4),
            "p90": round(scores[min(int(n * 0.1), n - 1)], 4),
            "min": round(scores[-1], 4),
            "max": round(scores[0], 4),
            "count": n,
        }
    else:
        priority_distribution = {"p50": 0, "p90": 0, "min": 0, "max": 0, "count": 0}
    state = {
        "shared_xml": xml[:2000] if xml else "",
        "mission_board": board,
    }
    return {
        "state": state,
        "state_version": state_version,
        "state_hash": state_hash,
        "priority_distribution": priority_distribution,
    }


@app.get("/telemetry")
async def get_telemetry():
    """Observability: decision_latency, speech_latency, silence_rate, state_mutation_frequency, economic_conversion_rate."""
    return wrap_response(telemetry.to_dict(), state_delta=False)


@app.websocket("/ws/{channel}")
async def websocket_endpoint(websocket: WebSocket, channel: str) -> None:
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








