import asyncio
import ipaddress
import os
import httpx
import re
import ast
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin, parse_qs, urlparse, unquote
from uuid import uuid4
import time
from datetime import datetime
from db import db
from osint import analyze_company
from app.core.emit import emit_job, emit_pipeline, emit_finance, emit_agent
from app.core.clock import stamp as clock_stamp, cycle_info
from app.core.cost import record_cost
from app.core.constraints import check_constraints
from app.core.lifecycle import register_agent, heartbeat as agent_heartbeat, retire_agent

# Internal API base — same process as app/main.py on port 8000
_UNIFIED_URL = os.environ.get("BRIDGE_CRM_URL", "http://localhost:8000")
# Internal service token — must match BRIDGE_INTERNAL_TOKEN in backend .env
_INTERNAL_TOKEN = os.environ.get("BRIDGE_INTERNAL_TOKEN", "")


def _auth_headers() -> dict:
    """Return Authorization header for internal API calls."""
    if _INTERNAL_TOKEN:
        return {"Authorization": f"Bearer {_INTERNAL_TOKEN}"}
    return {}

# Private/link-local CIDR blocks blocked for SSRF protection
_BLOCKED_NETWORKS = [
    ipaddress.ip_network(n) for n in (
        "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",
        "127.0.0.0/8", "169.254.0.0/16", "::1/128", "fc00::/7",
    )
]


def _is_safe_url(url: str) -> bool:
    """Return True for https public URLs. http://localhost is allowed for internal API calls."""
    try:
        parsed = urlparse(url)
        host = parsed.hostname or ""
        # Allow http only for localhost (internal API)
        if parsed.scheme == "http":
            return host in ("localhost", "127.0.0.1", "::1")
        if parsed.scheme != "https":
            return False
        try:
            addr = ipaddress.ip_address(host)
            return not any(addr in net for net in _BLOCKED_NETWORKS)
        except ValueError:
            return bool(host)
    except Exception:
        return False

# Module load marker for debugging
print("[WORKERS] Module loaded at", datetime.utcnow().isoformat())

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
}

# -------- EMAIL EXTRACTION ----------
def extract_emails(text):
    """Extract email addresses from text with improved regex"""
    # More comprehensive email regex
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    emails = re.findall(email_pattern, text)
    # Filter out common false positives
    valid_emails = [e for e in emails if not e.endswith(('.png', '.jpg', '.gif', '.svg'))]
    return list(set(valid_emails))


# -------- SCRAPE WEBSITE ----------
async def _ssrf_redirect_guard(response: httpx.Response) -> None:
    """Event hook: re-validate every redirect destination against the SSRF blocklist."""
    if response.is_redirect:
        location = response.headers.get("location", "")
        if location and not _is_safe_url(location):
            raise ValueError(f"SSRF: redirect to blocked destination '{location[:80]}' refused")


async def scrape_site(url):
    """Scrape website for emails and metadata"""
    try:
        if not _is_safe_url(url):
            print(f"[SCRAPE] Blocked unsafe URL: {url[:60]}")
            return None

        async with httpx.AsyncClient(
            timeout=10,
            follow_redirects=True,
            event_hooks={"response": [_ssrf_redirect_guard]},
        ) as client:
            try:
                r = await client.get(url, headers=HEADERS)
                print(f"[SCRAPE] Fetching {url[:50]}... status: {r.status_code}")
            except Exception as e:
                print(f"[SCRAPE] Failed to fetch {url}: {type(e).__name__}")
                return None

            soup = BeautifulSoup(r.text, "html.parser")

            # Extract text and find emails
            text = soup.get_text(" ", strip=True)
            emails = extract_emails(text)
            print(f"[SCRAPE]   Found {len(emails)} emails on main page")

            # Try contact page
            contact_link = None
            for a in soup.find_all("a", href=True):
                href = a["href"].lower()
                if any(keyword in href for keyword in ["contact", "about", "team", "email", "info"]):
                    contact_link = urljoin(url, a["href"])
                    print(f"[SCRAPE]   Found contact link: {contact_link[:60]}...")
                    break

            if contact_link and _is_safe_url(contact_link):
                try:
                    r2 = await client.get(contact_link, headers=HEADERS, timeout=10)
                    contact_emails = extract_emails(r2.text)
                    print(f"[SCRAPE]   Found {len(contact_emails)} emails on contact page")
                    emails += contact_emails
                except Exception as e:
                    print(f"[SCRAPE]   Failed to fetch contact page: {type(e).__name__}")

            unique_emails = list(set(emails))[:5]
            print(f"[SCRAPE]   Total unique emails: {len(unique_emails)}")

            return {
                "url": url,
                "emails": unique_emails,
                "title": soup.title.string if soup.title else ""
            }
    except Exception as e:
        print(f"[SCRAPE] Site scraping error: {type(e).__name__}: {e}")
        return None


# -------- SEARCH FOR BUSINESSES ----------
async def search_businesses(query):
    """Search for business websites using DuckDuckGo HTML endpoint"""
    results = []

    try:
        # DuckDuckGo HTML endpoint (JavaScript-free)
        url = f"https://html.duckduckgo.com/html?q={query.replace(' ','+')}"

        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            }
            r = await client.get(url, headers=headers)
            print(f"[SCRAPE] DuckDuckGo status: {r.status_code}, URL: {r.url}")

            soup = BeautifulSoup(r.text, "html.parser")

            # DuckDuckGo wraps results in redirect links with uddg parameter
            # Format: //duckduckgo.com/l/?uddg=<BASE64_OR_URL_ENCODED_URL>
            for link in soup.find_all("a"):
                href = link.get("href", "")

                # Extract URL from DuckDuckGo redirect
                if "uddg=" in href:
                    try:
                        # Parse uddg parameter
                        if "?" in href:
                            params = parse_qs(urlparse(href).query)
                            if "uddg" in params:
                                encoded_url = params["uddg"][0]
                                actual_url = unquote(encoded_url)
                                if _is_safe_url(actual_url):
                                    results.append(actual_url)
                                    print(f"[SCRAPE]   Found: {actual_url[:60]}...")
                    except Exception as e:
                        pass

                # Direct links (fallback)
                elif _is_safe_url(href) and not any(x in href for x in ["duckduckgo", "reddit.com", "wikipedia"]):
                    results.append(href)

            unique_results = list(set(results))
            print(f"[SCRAPE] Found {len(unique_results)} websites")

    except Exception as e:
        print(f"[SCRAPE] Search failed: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

    return list(set(results))[:10]


# -------- CORE EXECUTION ----------
async def execute_task(task):
    """Execute lead generation task - with robust payload parsing"""
    try:
        # Extract task metadata
        task_id = task["id"]
        agent_id = task["agent_id"]
        print(f"[TASK] Starting execution for task_id={task_id}, agent_id={agent_id}")

        # Parse payload (stored as string in DB)
        payload_raw = task["payload"]
        print(f"[TASK] Payload raw: type={type(payload_raw).__name__}, length={len(str(payload_raw))}")

        # Try JSON parsing first (most common for HTTP payloads)
        payload = None
        if isinstance(payload_raw, str):
            try:
                payload = json.loads(payload_raw)
                print(f"[TASK] [OK] Parsed as JSON")
            except json.JSONDecodeError:
                try:
                    payload = ast.literal_eval(payload_raw)
                    print(f"[TASK] [OK] Parsed as Python literal")
                except (ValueError, SyntaxError) as e:
                    print(f"[TASK] [FAIL] Failed to parse payload: {e}")
                    payload = {}
        else:
            payload = payload_raw if isinstance(payload_raw, dict) else {}
            print(f"[TASK] [OK] Already a dict")

        # Ensure payload is dict, extract query
        if not isinstance(payload, dict):
            print(f"[TASK] WARNING: Payload not dict after parsing, type={type(payload).__name__}, resetting to empty dict")
            payload = {}

        query = payload.get("query", "plumbing services south africa")
        print(f"[TASK] Query: '{query}'")

        # STEP 1: find businesses
        urls = await search_businesses(query)

        # STEP 2: scrape each site
        leads = []
        for url in urls:
            data = await scrape_site(url)
            if data and data["emails"]:
                leads.append(data)

        # STEP 3: store leads in registry AND queue for outreach
        from app.core.deps import get_memory as _get_mem
        _mem = _get_mem()

        for lead in leads:
            lead_id = str(uuid4())
            await _mem.set(f"registry:lead:{lead_id}", {
                "id": lead_id, "url": lead["url"], "entity_type": "lead",
                "metadata": lead, "registered_at": datetime.utcnow().isoformat(), "status": "active",
            })

            # STEP 3B: OSINT Analysis
            company_url = lead.get("url", "")
            company_title = lead.get("title", "")
            company_emails = lead.get("emails", [])

            # Emit gate (Agent channel): value = email count (signal quality), cost = 0.05/lead
            if not emit_agent(values=[float(len(company_emails))], cost=0.05):
                print(f"[OSINT] Skipping {company_url[:40]} — no emails found, zero signal value")
                continue

            # Cost accounting for OSINT inference cycle
            try:
                await record_cost(_mem, channel="X", label="osint_analysis", amount=0.05,
                                  ref_id=company_url[:60])
            except Exception:
                pass

            osint_profile = analyze_company(company_url, company_title, company_emails)
            print(f"[OSINT] Analyzed {osint_profile['company_name']}: {osint_profile['industry']} ({osint_profile['size_estimate']})")

            # STEP 3C: Create in CRM and Queue for outreach
            company_name = osint_profile["company_name"]

            # Unified API — single server handles CRM + outreach + OSINT
            if company_emails:
                try:
                    async with httpx.AsyncClient(timeout=10, headers=_auth_headers()) as client:
                        # 1. Create CRM lead
                        crm_resp = await client.post(f"{_UNIFIED_URL}/api/crm/leads", json={
                            "email": company_emails[0],
                            "company": company_name,
                            "osint_profile": osint_profile,
                            "source": "scraper"
                        })
                        if crm_resp.status_code == 200:
                            print(f"[CRM] [OK] Lead: {crm_resp.json().get('id', '?')}")

                        # 2. Queue emails for outreach
                        queued = 0
                        for email in company_emails[:2]:
                            resp = await client.post(f"{_UNIFIED_URL}/api/outreach/queue", json={
                                "email": email,
                                "company": company_name,
                                "template_type": osint_profile.get("template_type", "general")
                            })
                            if resp.status_code == 200:
                                queued += 1
                        if queued:
                            print(f"[OUTREACH] [OK] Queued {queued} ({osint_profile.get('template_type')})")

                        # 3. Register OSINT profile
                        await client.post(f"{_UNIFIED_URL}/api/osint/register", json={
                            "task_id": task_id,
                            "url": company_url,
                            "title": company_title,
                            "emails": company_emails,
                            "company_name": company_name,
                            "industry": osint_profile.get("industry"),
                            "size_estimate": osint_profile.get("size_estimate"),
                            "template_type": osint_profile.get("template_type"),
                            "profile_confidence": osint_profile.get("profile_confidence", 0),
                            "full_profile": osint_profile
                        })
                except Exception as e:
                    print(f"[UNIFIED] [ERROR] {type(e).__name__}: {e}")

        # STEP 4: assign value ($ per lead)
        value = len(leads) * 5.0   # $5 per lead

        # STEP 5: write to ledger (MemoryStore append)
        ledger: list = await _mem.get("osint:ledger") or []
        ledger.append({
            "id": str(uuid4()), "account": agent_id, "amount": value,
            "transaction_type": "leadgen_revenue", "timestamp": datetime.utcnow().isoformat(),
        })
        await _mem.set("osint:ledger", ledger)

        # STEP 6: telemetry — update hourly bucket for agent-activity chart
        buckets: list = await _mem.get("telemetry:hourly:tasks") or [0] * 24
        labels: list = await _mem.get("telemetry:hourly:labels") or []
        hour_label = datetime.utcnow().strftime("%H:00")
        buckets.append(len(leads))
        labels.append(hour_label)
        # Keep last 24 data points
        await _mem.set("telemetry:hourly:tasks", buckets[-24:])
        await _mem.set("telemetry:hourly:labels", labels[-24:])

        return {
            "leads_found": len(leads),
            "value_generated": value
        }
    except Exception as e:
        print(f"[TASK] [FAIL] EXECUTION FAILED: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise


# -------- MEMORY STORE HELPERS ----------

async def _mem_get_pending_tasks(mem, limit: int = 5) -> list[dict]:
    """Scan all agent task indexes for pending tasks."""
    agent_ids: list = await mem.get("agent:index") or []
    pending = []
    for agent_id in agent_ids:
        task_ids: list = await mem.get(f"agent:{agent_id}:tasks") or []
        for tid in task_ids:
            if len(pending) >= limit:
                break
            task = await mem.get(f"task:{tid}")
            if task and task.get("status") == "pending":
                pending.append(task)
        if len(pending) >= limit:
            break
    return pending


async def _mem_update_task(mem, task_id: str, status: str, result: dict) -> None:
    task = await mem.get(f"task:{task_id}")
    if task:
        task["status"] = status
        task["result"] = result
        await mem.set(f"task:{task_id}", task)


async def _mem_claim_task(mem, task_id: str) -> bool:
    """Atomically claim a task to prevent double-processing across worker instances.
    Uses setnx (set-if-not-exists) on a claim key. Returns True if this worker
    won the claim, False if another worker already claimed it.
    """
    return await mem.setnx(f"task:{task_id}:claimed", 1)


# -------- WORKER LOOP ----------
async def worker_loop():
    """Main worker loop - polls MemoryStore for tasks and executes them."""
    print("[WORKER] Starting worker loop...")
    loop_count = 0
    _overdue_check_every = 30  # flag_overdue every 30 cycles (~60 s at 2 s/cycle)

    from app.core.deps import get_memory

    # Register this worker process as a lifecycle agent
    _worker_agent_id = None
    try:
        _mem_init = get_memory()
        _worker_agent_id = await register_agent(_mem_init, name="worker_loop", channel="J")
        print(f"[WORKER] Registered as agent {_worker_agent_id}")
    except Exception as _reg_err:
        print(f"[WORKER] Lifecycle registration skipped: {_reg_err}")

    while True:
        loop_count += 1
        try:
            mem = get_memory()

            # Lifecycle heartbeat + clock stamp
            try:
                ci = cycle_info()
                await mem.set("worker:last_heartbeat", str(time.time()))
                await mem.set("worker:cycle", str(ci["cycle"]))
                await mem.set("worker:window", ci["window"])
                if _worker_agent_id:
                    await agent_heartbeat(mem, _worker_agent_id, meta={"cycle": loop_count, "clock": ci["window"]})
            except Exception:
                pass

            tasks = await _mem_get_pending_tasks(mem)

            if tasks:
                print(f"[WORKER] Cycle {loop_count}: Found {len(tasks)} pending task(s)")

                for task in tasks:
                    task_id = task.get("id", "unknown")
                    try:
                        # Atomically claim task — prevents double-processing across workers
                        claimed = await _mem_claim_task(mem, task_id)
                        if not claimed:
                            print(f"[WORKER] Task {task_id} already claimed, skipping")
                            continue

                        # Constraint check (budget + rate + queue depth)
                        constraint = await check_constraints(mem, channel="J", action="task")
                        if not constraint.ok:
                            print(f"[WORKER] Task {task_id} blocked by constraint: {constraint.reason}")
                            await _mem_update_task(mem, task_id, "void", {"reason": constraint.reason})
                            continue

                        # Emit gate: value = expected_leads (1.0 base), cost = 0.1 per task cycle
                        task_value = float(task.get("meta", {}).get("expected_value", 1.0))
                        if not emit_job(values=[task_value], cost=0.1):
                            print(f"[WORKER] Task {task_id} silenced — non-positive value")
                            await _mem_update_task(mem, task_id, "void", {"reason": "emit_gate"})
                            continue

                        # Record cost
                        try:
                            await record_cost(mem, channel="J", label="task_exec", amount=0.1, ref_id=task_id)
                        except Exception:
                            pass

                        await _mem_update_task(mem, task_id, "running", {})
                        print(f"[WORKER] Processing task {task_id}...")

                        result = await execute_task(task)
                        await _mem_update_task(mem, task_id, "done", result or {})
                        print(f"[WORKER] [OK] Task {task_id} completed")

                    except Exception as e:
                        print(f"[WORKER] [FAIL] Task {task_id} failed: {type(e).__name__}: {e}")
                        import traceback
                        traceback.print_exc()
                        await _mem_update_task(mem, task_id, "failed", {"error": type(e).__name__})
            else:
                if loop_count % 10 == 0:
                    print(f"[WORKER] Cycle {loop_count}: No pending tasks")

            # Dispatch pending outreach emails every cycle
            try:
                from app.domains.outreach.deps import get_outreach
                outreach = get_outreach()
                outreach_result = await outreach.dispatch_pending(limit=10)
                if outreach_result.get("sent"):
                    print(f"[OUTREACH] Dispatched {outreach_result['sent']} email(s)")
            except Exception as _oe:
                print(f"[OUTREACH] dispatch error: {type(_oe).__name__}: {_oe}")

            # Flag overdue invoices periodically
            if loop_count % _overdue_check_every == 0:
                try:
                    from app.domains.billing.deps import get_billing
                    billing = get_billing()
                    overdue_count = await billing.flag_overdue()
                    if overdue_count:
                        print(f"[BILLING] Flagged {overdue_count} overdue invoice(s)")
                except Exception as _be:
                    print(f"[BILLING] overdue check error: {type(_be).__name__}: {_be}")

            # Activation loop — mirrors bridge.js event chain
            if loop_count % 5 == 0:  # every ~10 s
                await _activation_loop(mem)

            await asyncio.sleep(2)

        except Exception as e:
            print(f"[WORKER] [FAIL] Loop error (cycle {loop_count}): {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            await asyncio.sleep(5)


# ======================================================================
# ACTIVATION LOOP — Python implementation of bridge.js event chain
# Maps each bridge.js event to real service calls:
#
#   lead.generated   → CRM lead scoring sweep (brain.process)
#   marketing.process→ promote high-score leads to 'qualified'
#   sale.converted   → auto-invoice on negotiation→won transition
#   payment.received → treasury.collect() with UBI + trading split
#   trading.execute  → record simulated trade P&L to treasury ledger
#   security.check   → verify MemoryStore health + pending task counts
#   brain.process    → re-score stale CRM leads via OSINT heuristic
# ======================================================================

import random
import math

def _emit(type_: str, data: dict) -> None:
    """Push event to control plane bus (best-effort — never raises)."""
    try:
        from app.routes.controlplane import emit_event
        emit_event(type_, data)
    except Exception:
        pass


async def _activation_loop(mem) -> None:
    """One cycle of the BridgeOS activation loop (bridge.js translated to Python)."""
    try:
        from app.core.deps import get_memory as _gmem
        from app.services.treasury import TreasuryService

        treasury = TreasuryService(mem)
        await mem.set("activation_loop:last_run", time.time())
        _emit("loop_tick", {"phase": "start"})

        # --- brain.process: re-score stale leads ---
        await _brain_process(mem)

        # --- marketing.process: qualify high-score leads ---
        converted = await _marketing_process(mem)

        # --- sale.converted + payment.received + trading.execute ---
        for invoice_value in converted:
            await _payment_received(treasury, invoice_value)

        # --- security.check ---
        await _security_check(mem)

    except Exception as e:
        print(f"[BRIDGE] activation loop error: {type(e).__name__}: {e}")


async def _brain_process(mem) -> None:
    """brain.process — refresh lead scores.

    Two drift components (mirrors bridge_real.py score update logic):
    1. Random drift: 0–0.09 per cycle for leads created in last 24 h
       (bridge_real: ABS(RANDOM()) % 10 / 100.0)
    2. Activity boost: +0.02 for leads with same-day activity
    """
    try:
        ids: list = await mem.get("crm:leads:index") or []
        updated = 0
        cutoff = datetime.utcnow().replace(hour=0, minute=0, second=0).isoformat()
        for lead_id in ids:
            lead = await mem.get(f"crm:lead:{lead_id}")
            if not lead or lead.get("stage") in ("won", "lost"):
                continue
            old_score = float(lead.get("score", 0.5))
            new_score = old_score

            # Random drift for leads created in last 24 h
            if (lead.get("created_at", "") >= cutoff):
                drift = round(random.randint(0, 9) / 100.0, 2)  # 0.00–0.09
                new_score = min(1.0, new_score + drift)

            # Activity boost for same-day activity
            activities = lead.get("activities", [])
            if activities:
                last_ts = (activities[-1].get("created_at") or "")[:10]
                today = datetime.utcnow().strftime("%Y-%m-%d")
                if last_ts == today:
                    new_score = min(1.0, new_score + 0.02)

            if new_score != old_score:
                lead["score"] = round(new_score, 4)
                await mem.set(f"crm:lead:{lead_id}", lead)
                updated += 1
        if updated:
            print(f"[BRAIN] Score drift applied to {updated} lead(s)")
    except Exception as e:
        print(f"[BRAIN] error: {type(e).__name__}: {e}")


async def _marketing_process(mem) -> list[float]:
    """marketing.process — move qualified leads with score ≥ 0.7 to proposal stage.
    Returns list of estimated deal values for converted leads (sale.converted).
    """
    converted_values: list[float] = []
    try:
        ids: list = await mem.get("crm:leads:index") or []
        for lead_id in ids:
            lead = await mem.get(f"crm:lead:{lead_id}")
            if not lead:
                continue
            stage = lead.get("stage", "new")
            score = float(lead.get("score", 0))

            # Qualified + high score → promote to proposal (70% chance, mirrors bridge.js)
            # Emit gate: value = [score, normalised_deal_estimate], cost = stage advancement cost
            est_value = score * 1000  # rough deal estimate before we know actual value
            if stage == "qualified" and score >= 0.7 and random.random() > 0.3 and \
               emit_pipeline(values=[score, est_value / 1000], cost=0.3):
                lead["stage"] = "proposal"
                lead.setdefault("activities", []).append({
                    "type": "stage_change",
                    "text": "Auto-promoted to proposal by activation loop",
                    "created_at": datetime.utcnow().isoformat(),
                })
                await mem.set(f"crm:lead:{lead_id}", lead)
                deal_value = round(score * random.uniform(500, 5000), 2)
                converted_values.append(deal_value)
                print(f"[MARKETING] Lead {lead_id[:8]} promoted → proposal (est. R{deal_value})")
                _emit("marketing_convert", {"lead_id": lead_id[:8], "score": score, "value": deal_value})

    except Exception as e:
        print(f"[MARKETING] error: {type(e).__name__}: {e}")
    return converted_values


async def _payment_received(treasury, amount: float) -> None:
    """payment.received → treasury.collect (split: UBI 40%, treasury 30%, ops 20%, founder 10%)
    then trading.execute on 20% of the amount.
    """
    # Emit gate: value = payment amount, cost = processing overhead (1% of amount)
    if not emit_finance(values=[amount], cost=amount * 0.01):
        print(f"[TREASURY] Payment R{amount:.2f} silenced by emit gate (non-positive value)")
        return
    # Cost accounting for finance operation
    try:
        from app.core.deps import get_memory as _get_mem
        _m = _get_mem()
        await record_cost(_m, channel="F", label="payment_collect", amount=amount * 0.01)
    except Exception:
        pass
    try:
        result = await treasury.collect(
            amount=amount,
            currency="ZAR",
            source_project="activation-loop",
            method="internal",
            type_="crm_conversion",
        )
        brdg = result.get("entry", {}).get("amount_brdg", 0)
        split = result.get("entry", {}).get("split", {})
        ubi_share = split.get("ubi", 0)
        print(f"[TREASURY] Collected R{amount} ({brdg:.4f} BRDG) | UBI share: {ubi_share:.4f}")
        _emit("payment_received", {"amount_zar": amount, "brdg": round(brdg, 6), "ubi": round(ubi_share, 6)})

        # economy.distribute — UBI leg (logged; actual on-chain claim stays pull-based)
        print(f"[UBI] Pool credited {ubi_share:.4f} BRDG")
        _emit("ubi_distribute", {"brdg": round(ubi_share, 6)})

        # trading.execute — deploy 20% of payment
        await _trading_execute(treasury, amount * 0.2)

    except Exception as e:
        print(f"[TREASURY] collect error: {type(e).__name__}: {e}")


async def _trading_execute(treasury, capital: float) -> None:
    """trading.execute — simulated trade; records P&L to treasury as 'trade' rail."""
    try:
        # Simulated return: -5% to +20% of deployed capital
        pnl_pct = random.uniform(-0.05, 0.20)
        profit = round(capital * pnl_pct, 4)
        print(f"[TRADING] Deployed R{capital:.2f} → P&L: R{profit:+.2f} ({pnl_pct*100:+.1f}%)")
        _emit("trade_executed", {"capital": round(capital, 2), "pnl": profit, "pnl_pct": round(pnl_pct * 100, 1)})
        # Emit gate: only record profitable trades to treasury (losses are silenced)
        if profit != 0 and emit_finance(values=[profit], cost=0.0):
            await treasury.collect(
                amount=abs(profit),
                currency="ZAR",
                source_project="boss-bot-trading",
                method="trade",
                type_="trade_pnl" if profit > 0 else "trade_loss",
                meta={"capital_deployed": capital, "pnl_pct": round(pnl_pct, 4)},
            )
    except Exception as e:
        print(f"[TRADING] error: {type(e).__name__}: {e}")


async def _security_check(mem) -> None:
    """security.check — verify MemoryStore reachability and report pending task backlog."""
    try:
        agent_ids: list = await mem.get("agent:index") or []
        pending = 0
        for agent_id in agent_ids:
            task_ids: list = await mem.get(f"agent:{agent_id}:tasks") or []
            for tid in task_ids:
                t = await mem.get(f"task:{tid}")
                if t and t.get("status") == "pending":
                    pending += 1
        print(f"[SECURITY] Integrity OK | agents={len(agent_ids)} | pending_tasks={pending}")
    except Exception as e:
        print(f"[SECURITY] check error: {type(e).__name__}: {e}")


if __name__ == "__main__":
    import asyncio as _asyncio
    print("[WORKERS] Starting worker loop...")
    _asyncio.run(worker_loop())
