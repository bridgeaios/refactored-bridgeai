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
from datetime import datetime
from db import db
from osint import analyze_company

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
async def scrape_site(url):
    """Scrape website for emails and metadata"""
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
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


# -------- WORKER LOOP ----------
async def worker_loop():
    """Main worker loop - polls MemoryStore for tasks and executes them."""
    print("[WORKER] Starting worker loop...")
    loop_count = 0

    # Import MemoryStore inside the loop so it resolves after app startup
    from app.core.deps import get_memory

    while True:
        loop_count += 1
        try:
            mem = get_memory()
            tasks = await _mem_get_pending_tasks(mem)

            if tasks:
                print(f"[WORKER] Cycle {loop_count}: Found {len(tasks)} pending task(s)")

                for task in tasks:
                    task_id = task.get("id", "unknown")
                    try:
                        # Mark in-progress immediately to prevent double-processing
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

            await asyncio.sleep(2)

        except Exception as e:
            print(f"[WORKER] [FAIL] Loop error (cycle {loop_count}): {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            await asyncio.sleep(5)
