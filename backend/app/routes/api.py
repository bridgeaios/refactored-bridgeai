import json
import os
import time
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse, Response
from pydantic import BaseModel

from app.cortex import (
    CAPABILITIES,
    auth_class_from_token,
    authority_allows,
    capability_enabled,
    get_boots_log,
    get_current_run,
    get_runs_log,
    get_sensor_mouse,
    get_sensor_wifi,
    get_state_hash,
    get_state_version,
    set_sensor_mouse,
    set_sensor_wifi,
    wrap_response,
)
from app.physics import (
    DETERMINISTIC_MODE,
    DRIFT_THRESHOLD,
    check_economic_risk,
    consume_evolution_budget,
    deterministic_seed,
    drift_score,
    ethical_conflict_score,
    ethical_reason_category,
    fallback_for,
    get_degradation,
    record_economic_action,
    replenish_evolution_budget,
    should_silence_for_ethics,
    should_trigger_governance,
    telemetry,
    validate_identity_immutability,
)
from app.runtime import (
    bossbots_service,
    cognitive_twin,
    emotion_service,
    esim_service,
    learning_service,
    marketplace_service,
    memory,
    mission_service,
    replication_engine,
    revenue_service,
    sdg_service,
    speech_embodiment,
    speech_reasoning,
    system_comprehension,
    twins_competition,
    ubi_service,
    voice_broker,
)
from app.services.speech_embodiment import SKILL_DEFINITION
from app.services.system_comprehension import SKILL_DEFINITION as SYS_COMP_SKILL_DEF

router = APIRouter()

class SkillModel(BaseModel):
    name: str
    tags: list[str]
    description: str | None = None

@router.get("/skills")
async def list_skills():
    """Return all stored skills (most recent 200)."""
    skills = await memory.get_recent("skills", 200)
    return {"ok": True, "skills": skills, "count": len(skills)}


@router.post("/skills")
async def add_skill(skill: SkillModel):
    await mission_service.save_skill(skill.model_dump())
    return {"ok": True}

@router.get("/mission/board")
async def mission_board():
    return await mission_service.get_counts()


# Shared XML — Twins share a canonical XML document (mission state, config, authority)
# Backend is human. I am the Bridge. I am the Founder. I am the System. I am the Authority.
TWIN_XML_KEY = "twin:shared_xml"
DEFAULT_TWIN_XML = '''<?xml version="1.0" encoding="UTF-8"?>
<twin>
  <authority>I am the Bridge. I am the Founder. I am the System. I am the Authority.</authority>
  <backend>human</backend>
  <mission><backlog>0</backlog><in_progress>0</in_progress><review>0</review><done>0</done></mission>
  <face_state>ALIVE</face_state>
</twin>'''

@router.get("/twin/shared-xml", response_class=PlainTextResponse)
async def get_shared_xml():
    """GET shared XML — all Twins read from this canonical document."""
    xml = await memory.get(TWIN_XML_KEY)
    if xml is None:
        xml = DEFAULT_TWIN_XML
        await memory.set(TWIN_XML_KEY, xml)
    return Response(content=xml, media_type="application/xml")

@router.post("/twin/shared-xml")
async def set_shared_xml(request: Request):
    """POST shared XML — Twins can update the canonical document."""
    body_bytes = await request.body()
    xml = body_bytes.decode("utf-8", errors="replace").strip()
    if not xml or not xml.lstrip().startswith("<"):
        raise HTTPException(status_code=400, detail="valid XML required")
    await memory.set(TWIN_XML_KEY, xml)
    return {"ok": True}


# Digital Cognitive Twin — Identity, Skill Stack, Decision Engine, Evolution
# Env keys: same list as audit-wall.ps1 / KEYS-REQUIRED.md. Twin is single source for key status; never returns secret values.
TWIN_ENV_KEY_CHECKS = [
    {"key": "OPENAI_API_KEY", "label": "OpenAI", "critical": True},
    {"key": "HF_TOKEN", "label": "Hugging Face", "critical": True},
    {"key": "HUGGING_FACE_API_KEY", "label": "Hugging Face (alt)", "critical": True},
    {"key": "CLOUDFLARE_ACCOUNT_ID", "label": "Cloudflare Account", "critical": True},
    {"key": "JWT_SECRET", "label": "JWT Secret", "critical": True},
    {"key": "JWT_SECRET_KEY", "label": "JWT Secret Key", "critical": True},
    {"key": "TURNSTILE_SECRET_KEY", "label": "Cloudflare Turnstile", "critical": False},
    {"key": "ELEVENLABS_API_KEY", "label": "ElevenLabs", "critical": False},
    {"key": "ANTHROPIC_API_KEY", "label": "Anthropic", "critical": False},
    {"key": "SMTP_PASSWORD", "label": "SMTP", "critical": False},
    {"key": "PAYPAL_CLIENT_ID", "label": "PayPal", "critical": False},
    {"key": "DISCORD_BOT_TOKEN", "label": "Discord Bot", "critical": False},
    {"key": "R2_BUCKET_NAME", "label": "Cloudflare R2 Bucket", "critical": False},
]
TWIN_PLACEHOLDER_SUBSTRINGS = (
    "your-", "sk-your-", "hf_your", "your_", "generate-a-strong", "change-me",
    "your-cloudflare", "your-email", "your-domain", "your-username", "your-paypal",
    "sk_test_", "pk_test_", "xai-your-", "gsk_your-", "pcsk_your-", "glhf_", "0x4AAAAAA",
)


def _twin_env_key_status():
    """Return key names and status only (configured/missing/placeholder). No secret values."""
    result = []
    for c in TWIN_ENV_KEY_CHECKS:
        val = os.environ.get(c["key"]) or ""
        if not val or len(val) < 8:
            status = "missing"
        elif any(p in val.lower() for p in TWIN_PLACEHOLDER_SUBSTRINGS):
            status = "placeholder"
        else:
            status = "configured"
        result.append({
            "key": c["key"],
            "label": c["label"],
            "critical": c["critical"],
            "status": status,
        })
    ok = sum(1 for r in result if r["status"] == "configured")
    critical_missing = sum(1 for r in result if r["critical"] and r["status"] != "configured")
    return {
        "keys": result,
        "summary": {"configured": ok, "criticalMissing": critical_missing},
    }


@router.get("/twin/profile")
async def get_twin_profile():
    """Return structured Twin Profile: Identity, Skill Stack, Decision Model, Adaptive Loop, Risk Model, Communication Style, Blind Spots, Upgrade Path."""
    return cognitive_twin.get_profile()


@router.get("/twin/env-keys")
async def get_twin_env_keys():
    """Digital Twin holds env API key status. Call this to get which keys are configured/missing/placeholder. Never returns secret values."""
    return _twin_env_key_status()


@router.post("/twin/decide")
async def twin_decide(payload: dict):
    """
    Decision engine. Returns Action or Silence. Deterministic mode: same inputs → same output.
    Ethical conflict → silence. Bridge_System_Comprehension alignment filter applied.
    Determinism with replay: seed + state_version in meta for exact reproduction.
    """
    t0 = time.perf_counter()
    env = payload.get("environment", {})
    goal = payload.get("goal_vector", [])
    constraints = set(payload.get("constraints", []))
    risk = float(payload.get("risk_threshold", 0.5))
    candidates = payload.get("candidates", [])
    state_version = await get_state_version(memory)
    seed = deterministic_seed({"env": env, "goal": goal, "candidates": candidates}, state_version)
    if DETERMINISTIC_MODE:
        import random
        random.seed(seed)
    result = cognitive_twin.decide(env, goal, constraints, risk, candidates)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    telemetry.record_decision(elapsed_ms)
    if DETERMINISTIC_MODE:
        telemetry.record_decision_with_seed(seed, state_version)
    if result is None:
        telemetry.record_silence()
        return wrap_response(
            {"action": None, "reason": "no_positive_value_output"},
            silence=True, confidence=0.0, deterministic_seed=seed, state_version=state_version,
        )
    action = result.get("action", {})
    action_obj = action if isinstance(action, dict) else {"action": action}
    ethical_score = ethical_conflict_score(action_obj, {"environment": env})
    if should_silence_for_ethics(action_obj, {"environment": env}):
        telemetry.record_silence()
        return wrap_response(
            {"action": None, "reason": "ethical_conflict"},
            silence=True, confidence=0.0,
            deterministic_seed=seed, state_version=state_version,
            ethical_score=ethical_score, ethical_reason=ethical_reason_category(action_obj, {"environment": env}),
        )
    action_id = (action_obj.get("action_id") or action_obj.get("action") or "") if isinstance(action_obj, dict) else str(action_obj)
    if action_id:
        aligned, reason = system_comprehension.filter_action(action_id, {"environment": env})
        if not aligned:
            telemetry.record_silence()
            return wrap_response(
                {"action": None, "reason": f"alignment_filter:{reason}"},
                silence=True, confidence=0.0,
                deterministic_seed=seed, state_version=state_version,
                ethical_reason="alignment_filter",
            )
    telemetry.record_action()
    return wrap_response(
        result, silence=False, confidence=result.get("confidence", 0.8),
        deterministic_seed=seed, state_version=state_version,
    )

@router.post("/twin/simulate")
async def twin_simulate(payload: dict):
    """
    Behavioral simulation under stress. Simulation state ≠ live canonical state.
    Degradation logic: stress accumulation, cognitive load, performance decay.
    """
    twin_id = payload.get("twin_id", "default")
    deg = get_degradation(twin_id)
    uncertainty = payload.get("uncertainty", 0)
    pressure = payload.get("pressure", 0)
    deg.accumulate_stress(uncertainty * 0.1)
    deg.set_cognitive_load(pressure)
    deg.decay_under_pressure(pressure)
    result = cognitive_twin.simulate_behavior(payload)
    result["simulation"] = True
    result["committed"] = False  # Never mutate canonical unless explicitly committed
    result["performance_factor"] = deg.performance_factor
    return result

@router.post("/twin/evolve")
async def twin_evolve(payload: dict):
    """
    Evolution loop. evolution_mode: "sandbox" | "commit".
    Requires orchestrator authority + evolution capability + evolution budget.
    Sandbox: feedback ingested, no canonical mutation.
    Commit: requires governanceVote reducer — no direct evolution to production.
    Identity immutability: core_values, mission_alignment, authority_class cannot change.
    """
    if not capability_enabled("evolution"):
        return wrap_response({"error": "evolution disabled", "feedback_ingested": False}, ok=False, silence=True)
    auth = auth_class_from_token(payload.get("authToken"))
    if not authority_allows(auth, "evolution"):
        return wrap_response({"error": "orchestrator authority required", "feedback_ingested": False}, ok=False, silence=True)
    if not consume_evolution_budget():
        return wrap_response({"error": "evolution_budget_exhausted", "feedback_ingested": False}, ok=False, silence=True)
    valid, reason = validate_identity_immutability(payload)
    if not valid:
        replenish_evolution_budget(1.0, "rollback_identity")  # refund on reject
        telemetry.record_failed_mutation()
        return wrap_response({"error": reason, "feedback_ingested": False}, ok=False, silence=True)
    evolution_mode = payload.get("evolution_mode", "sandbox")
    result = cognitive_twin.evolve(payload)
    result["evolution_mode"] = evolution_mode
    result["committed"] = False  # Commit requires governanceVote reducer; sandbox never commits
    return result


@router.post("/emotion/compute")
async def compute_emotion(payload: dict):
    """Emotion computation. Failure fallback: default neutral."""
    try:
        record = await emotion_service.compute(payload)
        return record
    except Exception:
        return fallback_for("emotion")

@router.get("/health")
async def health():
    return {"ok": True}


USER_SETTINGS_KEY_PREFIX = "user:settings:"


def _user_id_from_request(request: Request) -> str:
    """User id for settings: X-User-Id header (shared across domains) or default."""
    uid = request.headers.get("X-User-Id") or request.headers.get("X-Bridge-User-Id")
    if uid and isinstance(uid, str) and uid.strip():
        return uid.strip()[:128]
    return "default"


@router.get("/user/settings")
async def get_user_settings(request: Request):
    """
    Get user settings (shared per user across all domains).
    User id from X-User-Id or X-Bridge-User-Id header; otherwise "default".
    """
    uid = _user_id_from_request(request)
    key = USER_SETTINGS_KEY_PREFIX + uid
    raw = await memory.get(key)
    if not raw:
        return {"ok": True, "settings": {}}
    try:
        import json
        data = json.loads(raw) if isinstance(raw, str) else raw
        return {"ok": True, "settings": data if isinstance(data, dict) else {}}
    except Exception:
        return {"ok": True, "settings": {}}


@router.put("/user/settings")
async def put_user_settings(request: Request):
    """
    Save user settings (shared per user across all domains).
    Body: { "settings": { ... } } or { ... } (whole object as settings).
    """
    try:
        payload = await request.json()
    except Exception:
        payload = {}
    uid = _user_id_from_request(request)
    key = USER_SETTINGS_KEY_PREFIX + uid
    settings = payload.get("settings") if isinstance(payload.get("settings"), dict) else (payload if isinstance(payload, dict) else {})
    import json
    await memory.set(key, json.dumps(settings))
    return {"ok": True, "settings": settings}


@router.get("/health/extended")
async def health_extended():
    """
    Composite health score. One number: is the organism stable?
    health = (1 - error_rate) × (1 - silence_spike_deviation) × latency_factor × invariant_integrity
    """
    from app.physics import (
        economic_circuit_breaker_tripped,
        economic_entropy_score,
        telemetry,
    )
    err_rate = 0.0
    total = telemetry.state_mutation_count + telemetry.failed_mutation_count
    if total > 0:
        err_rate = telemetry.failed_mutation_count / total
    silence_dev = abs(telemetry.silence_rate - 0.5) * 2  # 0 at 50%, 1 at extremes
    dl = list(telemetry.decision_latency_ms)
    p95 = sorted(dl)[int(len(dl) * 0.95)] if dl else 0
    latency_factor = 1.0 if p95 <= 100 else max(0, 1.0 - (p95 - 100) / 500)
    circuit_ok = 0.0 if economic_circuit_breaker_tripped() else 1.0
    entropy_ok = 1.0 - min(1.0, economic_entropy_score())
    health_score = (1 - err_rate) * (1 - silence_dev) * latency_factor * circuit_ok * entropy_ok
    return {
        "ok": health_score >= 0.5,
        "health_score": round(health_score, 4),
        "components": {
            "error_rate": round(err_rate, 4),
            "silence_spike_deviation": round(silence_dev, 4),
            "latency_factor": round(latency_factor, 4),
            "circuit_breaker_ok": circuit_ok,
            "entropy_ok": round(entropy_ok, 4),
        },
    }


@router.post("/speech/reason")
async def speech_reason(payload: dict):
    """
    Speech communication reasoning layer.
    Accepts ASR transcript, returns normalized_text, intent, emotion, confidence, response.
    Never executes directly — outputs structured plan when appropriate.
    """
    transcript = payload.get("transcript") or payload.get("text") or ""
    context = payload.get("context") or {}
    result = speech_reasoning.process(transcript, context=context)
    return speech_reasoning.to_dict(result)


@router.post('/train/start')
async def start_training():
    # start training in background (if enough samples)
    started = await learning_service.train(emotion_service)
    if started:
        replenish_evolution_budget(2.0, "training_completion")
    return {"started": bool(started)}


@router.get('/train/status')
async def training_status():
    return learning_service.get_status()

@router.get('/esim/status')
async def esim_status():
    return esim_service.get_status()


@router.post("/ubi/claim")
@router.post("/ubi/distribute")
async def claim_ubi(payload: dict):
    """UBI claim/distribute. Economic risk governor: max exposure, cooldown."""
    address = payload.get('address') if isinstance(payload, dict) else None
    if not address:
        raise HTTPException(status_code=400, detail="address required")
    twin_id = str(address)[:16]
    amount = ubi_service.amount
    allowed, reason = check_economic_risk(twin_id, amount)
    if not allowed:
        raise HTTPException(status_code=429, detail=reason)
    amount = ubi_service.distribute(address)
    if amount > 0:
        record_economic_action(twin_id, amount)
        sdg_service.track('ubi_claims', 1)
        telemetry.record_economic_conversion()
        replenish_evolution_budget(min(0.5, amount / 200), "economic_surplus")
    return {"amount": amount}


@router.get('/marketplace/tasks')
async def get_tasks(status: str | None = None):
    return marketplace_service.get_tasks(status=status)


@router.post('/marketplace/task')
async def create_task(task: dict):
    if not isinstance(task, dict):
        raise HTTPException(status_code=400, detail='invalid task')
    t = marketplace_service.add_task(task)
    sdg_service.track('tasks_created', 1)
    # collect a small fee into revenue (simulated)
    try:
        reward = float(task.get('reward', 0))
        fee = reward * 0.05
        revenue_service.collect(fee, source="marketplace", method="marketplace")
    except Exception:
        pass
    return {"status": "created", "task": t}


@router.post('/marketplace/pledge')
async def pledge_task(data: dict):
    """
    Pledge to an upliftment task.
    Accepts optional event_id for idempotency (so clients can retry safely).
    """
    task_id = data.get('task_id')
    wallet = data.get('wallet')
    amount = data.get('amount')
    event_id = data.get('event_id')
    if not task_id or not wallet:
        raise HTTPException(status_code=400, detail='task_id and wallet required')
    try:
        amt = float(amount)  # type: ignore[arg-type]
    except Exception:
        raise HTTPException(status_code=400, detail='valid amount required') from None
    if amt <= 0:
        raise HTTPException(status_code=400, detail='amount must be > 0')
    t = marketplace_service.pledge_task(int(task_id), str(wallet), amt, str(event_id) if event_id else None)
    if not t:
        raise HTTPException(status_code=404, detail='task not found')
    # Treat pledges as a revenue inflow (simulated): small processing fee
    try:
        revenue_service.collect(max(0.01, amt * 0.01), source="marketplace", method="marketplace")
    except Exception:
        pass
    return {"status": "pledged", "task": t, "event_id": event_id}


@router.post('/marketplace/accept')
async def accept_task(data: dict):
    task_id = data.get('task_id')
    wallet = data.get('wallet')
    if not task_id or not wallet:
        raise HTTPException(status_code=400, detail='task_id and wallet required')
    t = marketplace_service.accept_task(int(task_id), wallet)
    if not t:
        raise HTTPException(status_code=404, detail='task not available')
    return {"status": "accepted", "task": t}


@router.post('/marketplace/complete')
async def complete_task(data: dict):
    """Complete a task. Credits the assigned twin if acceptor is twin:xxx."""
    task_id = data.get('task_id')
    if not task_id:
        raise HTTPException(status_code=400, detail='task_id required')
    t = twins_competition.complete_task(int(task_id), marketplace_service)
    if not t:
        raise HTTPException(status_code=404, detail='task not found or not in progress')
    sdg_service.track('tasks_completed', 1)
    return {"status": "completed", "task": t}


# -----------------------------------------------------------------------------
# Live map, report, orchestrate — pboots, runbs, map everything, direct, live display
# -----------------------------------------------------------------------------


def _load_config_map():
    """Load config/bridge-wall.config.json for services/modules map. Returns dict or None."""
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[2]
    config_path = repo_root / "config" / "bridge-wall.config.json"
    if not config_path.exists():
        return None
    try:
        return json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return None


@router.get("/live/map")
async def live_map():
    """
    Map everything: pboots, runbs, state version, services, twins, capabilities, telemetry, wiki.
    For orchestration and live display. Poll this or /api/live/report for live display.
    """
    cfg = _load_config_map()
    state_version = await get_state_version(memory)
    state_hash = await get_state_hash(memory)
    boots = await get_boots_log(memory)
    runs = await get_runs_log(memory)
    current_run = await get_current_run(memory)
    twins = twins_competition.list_twins()
    leaderboard = twins_competition.get_leaderboard()
    caps = {k: capability_enabled(k) for k in (CAPABILITIES or {})}
    telem = telemetry.to_dict() if hasattr(telemetry, "to_dict") else {}
    wiki_registry_path = None
    if cfg and isinstance(cfg.get("twinsSync"), dict):
        wiki_registry_path = cfg.get("twinsSync", {}).get("registryPath", "data/twin-registry.json")
    services = []
    if cfg and isinstance(cfg.get("services"), dict):
        for name, svc in cfg["services"].items():
            port = svc.get("port") or svc.get("hostPort")
            label = svc.get("label") or name
            services.append({"id": name, "label": label, "port": port})
    wifi_sensor = await get_sensor_wifi(memory)
    mouse_sensor = await get_sensor_mouse(memory)
    return {
        "ok": True,
        "ts": time.time(),
        "pboots": boots[-20:],
        "runbs": runs[-20:],
        "current_run": current_run,
        "state_version": state_version,
        "state_hash": state_hash,
        "twins": twins,
        "leaderboard": leaderboard,
        "capabilities": caps,
        "telemetry": telem,
        "services": services,
        "wiki_registry_path": wiki_registry_path,
        "config_loaded": cfg is not None,
        "sensors": {"wifi": wifi_sensor, "mouse": mouse_sensor},
    }


@router.get("/live/report")
async def live_report():
    """
    Single payload for live display. Report live: map + status. Poll e.g. every 5s for dashboard.
    """
    map_data = await live_map()
    from datetime import datetime
    map_data["report_at"] = datetime.utcnow().isoformat() + "Z"
    map_data["live_display"] = True
    return map_data


# Sensors (WiFi RF + mouse tracker from boot scripts)
@router.post("/sensors/wifi")
async def sensors_wifi_post(payload: dict):
    """Ingest WiFi RF sample from wifi-rf-boot.ps1. Expects signal, ssid, etc."""
    await set_sensor_wifi(memory, payload)
    return {"ok": True}


@router.get("/sensors/wifi")
async def sensors_wifi_get():
    """Return latest WiFi sensor sample."""
    out = await get_sensor_wifi(memory)
    return {"ok": True, "wifi": out}


_MOUSE_SESSION_KEY = "sensor:mouse:session"
_MOUSE_MOVES_PER_TASK = 12   # ~60 s of active tracking (5 s poll × 12)
_MOUSE_BRDG_PER_TASK = 0.5   # BRDG earned per milestone


@router.post("/sensors/mouse")
async def sensors_mouse_post(payload: dict):
    """
    Ingest mouse position/activity from mouse-tracker-boot.ps1.
    Every 12 active (moved=true) samples a marketplace task is auto-created
    and completed, earning the user 0.5 BRDG in the revenue pool.
    """
    await set_sensor_mouse(memory, payload)

    earned: float = 0.0
    task_created: bool = False

    if payload.get("moved"):
        # Load session counter
        raw = await memory.get(_MOUSE_SESSION_KEY)
        try:
            session: dict = json.loads(raw) if isinstance(raw, str) and raw else {}
        except Exception:
            session = {}

        active_count: int = int(session.get("active_count", 0)) + 1
        total_earned: float = float(session.get("total_earned", 0.0))

        if active_count >= _MOUSE_MOVES_PER_TASK:
            # Milestone reached → create + auto-complete a task
            task = marketplace_service.add_task({
                "title": "Mouse Activity — Human Presence",
                "description": f"Passive income: user active for ~{_MOUSE_MOVES_PER_TASK * 5}s",
                "reward": _MOUSE_BRDG_PER_TASK,
                "type": "sensor",
                "source": payload.get("source", "mouse-tracker"),
            })
            marketplace_service.accept_task(task["id"], "user")
            marketplace_service.complete_task(task["id"])
            revenue_service.collect(_MOUSE_BRDG_PER_TASK, source="sensor", method="sensor")
            earned = _MOUSE_BRDG_PER_TASK
            total_earned += earned
            active_count = 0
            task_created = True

        session["active_count"] = active_count
        session["total_earned"] = total_earned
        await memory.set(_MOUSE_SESSION_KEY, json.dumps(session))

    return {"ok": True, "earned": earned, "task_created": task_created}


@router.get("/sensors/mouse")
async def sensors_mouse_get():
    """Return latest mouse sensor sample plus lifetime session earnings."""
    out = await get_sensor_mouse(memory)
    raw = await memory.get(_MOUSE_SESSION_KEY)
    try:
        session: dict = json.loads(raw) if isinstance(raw, str) and raw else {}
    except Exception:
        session = {}
    return {"ok": True, "mouse": out, "session": session}


@router.get("/orchestrate/directives")
async def orchestrate_directives():
    """
    Orchestrate and direct: list of actions (scripts/commands) to run for sync, audit, wallpaper.
    Frontend can display these and user runs them (or a scheduler). No execution from API.
    """
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[2]
    directives = [
        {"id": "sync_twins_wiki", "label": "Sync twins and wiki", "script": ".\\scripts\\sync-twins-wiki.ps1", "cwd": str(repo_root), "description": "Sync all digital twins and C:\\Downloads versioned artifacts."},
        {"id": "audit", "label": "Full audit", "script": ".\\audit-wall.ps1", "cwd": str(repo_root), "description": "Run audit (keys, ports, DNS, E/C/D drives)."},
        {"id": "refresh_wallpaper", "label": "Refresh wallpaper", "script": ".\\update.ps1", "cwd": str(repo_root), "description": "Update digital twin wallpaper."},
        {"id": "port_list", "label": "Port status", "script": ".\\scripts\\port-handler.ps1 list", "cwd": str(repo_root), "description": "List port status (bridge-backend, auth, frontend, etc.)."},
    ]
    return {"ok": True, "directives": directives}


# Wiki-style version control — synced registry (twins + state + C:\Downloads artifacts)
@router.get("/wiki/registry")
async def get_wiki_registry():
    """Return twin registry if sync-twins-wiki.ps1 has been run. All digital twins + state version + versioned artifacts from C:\\Downloads."""
    from pathlib import Path
    repo_root = Path(__file__).resolve().parents[2]
    registry_path = repo_root / "data" / "twin-registry.json"
    if not registry_path.exists():
        return {"ok": False, "error": "Registry not found. Run .\\scripts\\sync-twins-wiki.ps1 first."}
    try:
        data = json.loads(registry_path.read_text(encoding="utf-8"))
        return {"ok": True, "registry": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read registry: {e}") from e


# Twins competition — auto-add, allocate, leaderboard
@router.get('/twins')
async def list_twins():
    return twins_competition.list_twins()


@router.get('/twins/leaderboard')
async def twins_leaderboard():
    return twins_competition.get_leaderboard()


@router.post('/twins/auto-add')
async def twins_auto_add():
    """Auto-add a random task from the Bridge task pool."""
    t = twins_competition.auto_add_task(marketplace_service)
    if not t:
        raise HTTPException(status_code=500, detail='auto-add failed')
    sdg_service.track('tasks_created', 1)
    return {"status": "created", "task": t}


@router.post('/twins/allocate')
async def twins_allocate(data: dict):
    """Allocate a task to a twin. Twins compete to build the most for the Bridge."""
    task_id = data.get('task_id')
    twin_id = data.get('twin_id')
    if not task_id or not twin_id:
        raise HTTPException(status_code=400, detail='task_id and twin_id required')
    t = twins_competition.allocate_task(int(task_id), twin_id, marketplace_service)
    if not t:
        raise HTTPException(status_code=404, detail='task not available or twin not found')
    return {"status": "allocated", "task": t}


@router.post('/twins/teach')
async def twins_teach(data: dict):
    """One twin teaches another a skill. Teacher must have the skill verified."""
    teacher_id = data.get('teacher_id')
    student_id = data.get('student_id')
    skill_name = data.get('skill_name')
    if not teacher_id or not student_id or not skill_name:
        raise HTTPException(status_code=400, detail='teacher_id, student_id, and skill_name required')
    result = twins_competition.teach_skill(teacher_id, student_id, skill_name)
    if not result:
        raise HTTPException(
            status_code=404,
            detail='twin not found or teacher does not have that skill verified'
        )
    return {"status": "taught", **result}


# Replication engine + node discovery (GLOBAL-TWIN-SWARM-ARCHITECTURE.md)
@router.get('/replication/status')
async def get_replication_status():
    """Replication engine status: last run, open_tasks, twin_count, rules_evaluated, twins_created."""
    return await replication_engine.get_status()


@router.get('/replication/nodes')
async def get_replication_nodes():
    """Registered nodes for mesh discovery."""
    nodes = await replication_engine.get_nodes()
    return {"ok": True, "nodes": nodes}


@router.post('/replication/register')
async def post_replication_register(data: dict):
    """Register a node for discovery (node_id, url, capabilities)."""
    node_id = data.get("node_id")
    url = data.get("url")
    if not node_id or not url:
        raise HTTPException(status_code=400, detail="node_id and url required")
    capabilities = data.get("capabilities")
    if isinstance(capabilities, str):
        capabilities = [c.strip() for c in capabilities.split(",") if c.strip()]
    await replication_engine.register_node(node_id, url, capabilities)
    return {"ok": True, "node_id": node_id, "url": url}


@router.get('/sdg/metrics')
async def get_sdg_metrics():
    return sdg_service.get_metrics()


@router.get('/revenue/status')
async def get_revenue():
    return revenue_service.get_status()


@router.post('/bossbots/trade')
async def execute_trade(trade: dict):
    """BossBots trade. Economic risk governor: max exposure, cooldown per twin."""
    asset = trade.get('asset') if isinstance(trade, dict) else None
    if not asset:
        raise HTTPException(status_code=400, detail='asset required')
    twin_id = trade.get("twin_id", "system")
    amount = 0.05  # simulated trade size
    allowed, reason = check_economic_risk(twin_id, amount)
    if not allowed:
        raise HTTPException(status_code=429, detail=reason)
    signal = bossbots_service.generate_signal(asset)
    twin_executions = twins_competition.execute_signal_for_twins(asset, signal)
    collected = revenue_service.collect(0.05, source="bossbots", method="trade")
    if collected:
        record_economic_action(twin_id, amount)
        sdg_service.track('trades_executed', 1)
        telemetry.record_economic_conversion()
        replenish_evolution_budget(0.1, "economic_surplus")
    return {"signal": signal, "twins_followed": twin_executions}


@router.get('/bossbots/signals')
async def get_signals():
    return bossbots_service.get_signals()


# Twin_Speech_Communication_Embodiment — full pipeline
@router.post("/speech/embody")
async def speech_embody(payload: dict):
    """
    Full speech embodiment: Language Engine → TTS → Phoneme Stream → Viseme Driver.
    Input: transcript (or prompt), context, audience_model.
    Output: response, phonemes (time-aligned), emotion, prosody, audio (base64).
    If semantic confidence < threshold → silence, no audio.
    """
    transcript = payload.get("transcript") or payload.get("prompt") or payload.get("text") or ""
    context = payload.get("context") or {}
    audience = payload.get("audience_model") or {}

    embody, execution_plan = speech_embodiment.process(transcript, context=context, audience_model=audience)

    if embody.silence:
        return {
            "response": "",
            "phonemes": [],
            "emotion": embody.emotion,
            "prosody": {"pitch": embody.prosody.pitch, "tempo": embody.prosody.tempo, "intensity": embody.prosody.intensity},
            "audio_base64": None,
            "silence": True,
            "confidence": embody.confidence,
            "execution_plan": execution_plan,
        }

    # TTS — failure fallback: return phonemes only (resilience under stress)
    t0 = time.perf_counter()
    audio_b64 = None
    try:
        chunks = []
        async for chunk in voice_broker.stream_tts(embody.text[:1000]):
            chunks.append(chunk)
        import base64
        audio_b64 = base64.b64encode(b"".join(chunks)).decode("ascii")
    except RuntimeError:
        pass  # Graceful degradation: phonemes only
    telemetry.record_speech((time.perf_counter() - t0) * 1000)

    phoneme_list = [
        {"viseme": p.viseme, "start_ms": p.start_ms, "end_ms": p.end_ms}
        for p in embody.phonemes
    ]

    return {
        "response": embody.text,
        "phonemes": phoneme_list,
        "emotion": embody.emotion,
        "prosody": {"pitch": embody.prosody.pitch, "tempo": embody.prosody.tempo, "intensity": embody.prosody.intensity},
        "audio_base64": audio_b64,
        "silence": False,
        "confidence": embody.confidence,
        "execution_plan": execution_plan,
        "viseme_map": {v: speech_embodiment.viseme_to_expression(v) for v in ("AA", "EE", "OH", "FV", "BMP", "TH", "Rest")},
    }


@router.post("/speech/embody/speak")
async def speech_embody_speak(payload: dict):
    """
    Speak pre-generated text with phoneme alignment. No language engine.
    Input: text. Output: phonemes, audio_base64, viseme_map.
    Use when response is already known (e.g. from WebSocket).
    """
    text = payload.get("text") or ""
    if not text.strip():
        return {"response": "", "phonemes": [], "audio_base64": None, "viseme_map": {}}

    phonemes = speech_embodiment.text_to_phoneme_sequence(text)
    phoneme_list = [{"viseme": p.viseme, "start_ms": p.start_ms, "end_ms": p.end_ms} for p in phonemes]

    audio_b64 = None
    try:
        chunks = []
        async for chunk in voice_broker.stream_tts(text[:1000]):
            chunks.append(chunk)
        import base64
        audio_b64 = base64.b64encode(b"".join(chunks)).decode("ascii")
    except RuntimeError:
        pass

    return {
        "response": text,
        "phonemes": phoneme_list,
        "emotion": "neutral",
        "audio_base64": audio_b64,
        "viseme_map": {v: speech_embodiment.viseme_to_expression(v) for v in ("AA", "EE", "OH", "FV", "BMP", "TH", "Rest")},
    }


@router.get("/speech/embodiment/skill")
async def get_embodiment_skill():
    """Return skill definition for Twin_Speech_Communication_Embodiment."""
    return SKILL_DEFINITION


@router.post("/speech/embodiment/memory/clear")
async def clear_embodiment_memory():
    """Clear conversational memory."""
    speech_embodiment.clear_memory()
    return {"ok": True}


@router.get("/speech/embodiment/memory")
async def get_embodiment_memory():
    """Return dialogue history."""
    return {"history": speech_embodiment.get_dialogue_history()}


# Bridge_System_Comprehension — structural mapping, alignment filter
@router.get("/system/comprehension")
async def get_system_comprehension():
    """Return full structural mapping: mission, architecture, economic engine, roles, governance, revenue."""
    return system_comprehension.get_system_map()


@router.get("/system/comprehension/explain")
async def explain_system(level: int = 1):
    """Explain The Bridge at Level 1 (simple), 2 (operational), or 3 (strategic)."""
    return {"level": level, "explanation": system_comprehension.explain(level)}


@router.get("/system/comprehension/operational-model")
async def get_operational_model():
    """Input → Processing → Output → Feedback → Reinforcement."""
    return {"model": system_comprehension.get_operational_model()}


@router.get("/system/comprehension/role-awareness")
async def get_role_awareness():
    """Twin function, authority boundaries, decision constraints."""
    return system_comprehension.get_role_awareness()


@router.post("/system/comprehension/check-alignment")
async def check_alignment(payload: dict):
    """Alignment filter. Returns aligned, reason, confidence, clarification_needed."""
    action = payload.get("action") or ""
    context = payload.get("context") or {}
    result = system_comprehension.check_alignment(action, context)
    return {
        "aligned": result.aligned,
        "reason": result.reason,
        "confidence": result.confidence,
        "clarification_needed": result.clarification_needed,
    }


@router.post("/system/comprehension/evolve")
async def system_comprehension_evolve(payload: dict):
    """Adaptive learning loop: ingest structural change. Requires orchestrator + evolution budget."""
    if not capability_enabled("evolution"):
        return wrap_response({"error": "evolution disabled"}, ok=False, silence=True)
    auth = auth_class_from_token(payload.get("authToken"))
    if not authority_allows(auth, "evolution"):
        return wrap_response({"error": "orchestrator authority required"}, ok=False, silence=True)
    if not consume_evolution_budget():
        return wrap_response({"error": "evolution_budget_exhausted"}, ok=False, silence=True)
    return system_comprehension.evolve(payload)


@router.get("/system/comprehension/skill")
async def get_system_comprehension_skill():
    """Return skill definition for Bridge_System_Comprehension."""
    return SYS_COMP_SKILL_DEF


@router.get("/audit/drift")
async def audit_drift():
    """
    Drift detection — immune system logic.
    Compare current state to baseline mission vector.
    If drift > threshold: trigger governanceVote or training (caller responsibility).
    """
    board = await mission_service.get_counts()
    current_state = {"mission_board": board}
    drift = drift_score(current_state)
    trigger = should_trigger_governance(drift)
    return {
        "drift_score": round(drift, 4),
        "threshold": DRIFT_THRESHOLD,
        "should_trigger_governance": trigger,
        "mission_board": board,
    }


@router.get('/tts/available')
async def tts_available():
    """Check if TTS backend is available (e.g. ElevenLabs configured)."""
    try:
        # Quick check - voice_broker may raise if no API key
        return {"available": True}
    except Exception:
        return {"available": False}


@router.post('/tts')
async def text_to_speech(payload: dict):
    """
    Raw audio stream. For phoneme-aware avatar sync, prefer POST /api/speech/embody/speak.
    Deprecation: /api/speech/embody/speak is canonical for embodiment (phonemes, visemes, audio).
    """
    text = payload.get('text') or ''
    if not text.strip():
        raise HTTPException(status_code=400, detail='text required')
    voice_id = payload.get('voice_id') or '21m00Tcm4TlvDq8ikWAM'
    try:
        chunks = []
        async for chunk in voice_broker.stream_tts(text[:1000], voice_id):
            chunks.append(chunk)
        from fastapi.responses import Response
        return Response(
            b''.join(chunks),
            media_type='audio/mpeg',
            headers={"X-Deprecation": "Prefer /api/speech/embody/speak for phoneme-aware use"},
        )
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e


# Founder TODO — linked to digital twin wallpaper. Live updates when objectives met.
FOUNDER_TODO_PATH = Path(os.environ.get("BRIDGE_LIVE_WALL_PATH", "C:/Users/supas/BridgeLiveWall")) / "founder-todo.json"


def _read_founder_todo():
    if not FOUNDER_TODO_PATH.exists():
        return {"version": 1, "updatedAt": None, "objectives": []}
    with open(FOUNDER_TODO_PATH, encoding="utf-8") as f:
        return json.load(f)


def _write_founder_todo(data):
    FOUNDER_TODO_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(FOUNDER_TODO_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


@router.get("/founder-todo")
async def get_founder_todo():
    """GET founder objectives. Wallpaper reads this; updates live when objectives met."""
    return _read_founder_todo()


@router.patch("/founder-todo/{obj_id}/complete")
async def complete_founder_objective(obj_id: str):
    """Mark objective complete. Wallpaper will update on next refresh (run-wallpaper-live.ps1)."""
    data = _read_founder_todo()
    objs = data.get("objectives", [])
    found = False
    for o in objs:
        if o.get("id") == obj_id:
            o["status"] = "complete"
            o["completedAt"] = datetime.utcnow().isoformat() + "Z"
            found = True
            break
    if not found:
        raise HTTPException(status_code=404, detail=f"Objective '{obj_id}' not found")
    data["updatedAt"] = datetime.utcnow().isoformat() + "Z"
    _write_founder_todo(data)
    return {"ok": True, "id": obj_id, "status": "complete"}
