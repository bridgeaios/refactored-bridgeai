"""
Query Cloudflare Workers Custom Domains API for bridge-ai-os-edge.
Uses workers:write permission (no dns:edit). Run with valid CF_API_TOKEN and ACCOUNT_ID.

Endpoint: GET /accounts/{account_id}/workers/scripts/{script_name}/domains
"""
import os
import sys
import json
import urllib.request
import urllib.error

ACCOUNT_ID = os.environ.get("CF_ACCOUNT_ID", "8e208744c31fc18f880f59bf18d4c645")
SCRIPT_NAME = "bridge-ai-os-edge"
BASE = "https://api.cloudflare.com/client/v4"

def main():
    token = os.environ.get("CF_API_TOKEN", "").strip()
    if not token:
        print("Error: Set CF_API_TOKEN (Cloudflare API token with Workers read)")
        sys.exit(1)

    # Workers Custom Domains API: list domains for a script (or account-level)
    # Try script-scoped first; fallback: GET /accounts/{id}/workers/domains
    url = f"{BASE}/accounts/{ACCOUNT_ID}/workers/scripts/{SCRIPT_NAME}/domains"
    req = urllib.request.Request(url, method="GET")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode()
            data = json.loads(body)
    except urllib.error.HTTPError as e:
        body = e.read().decode() if e.fp else "{}"
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = {"success": False, "errors": [{"message": str(e)}], "result": None}
        print("HTTP status:", e.code)
    except Exception as e:
        data = {"success": False, "errors": [{"message": str(e)}], "result": None}
        print("Request error:", e)

    # Output
    success = data.get("success", False)
    print("Success:", success)
    errors = data.get("errors", [])
    if errors:
        print("Errors:")
        for err in errors:
            print(" ", err.get("message", err))
        print("  (If 401: check token validity and Workers read / workers:write permission)")
    result = data.get("result")
    if result is not None:
        if isinstance(result, list):
            print("Custom domains on worker", SCRIPT_NAME + ":")
            for d in result:
                if isinstance(d, dict):
                    print(" ", d.get("hostname") or d.get("id") or d)
                else:
                    print(" ", d)
            if not result:
                print("  (none)")
        else:
            print("Result:", json.dumps(result, indent=2))
    else:
        print("Result: (null)")
    return 0 if success and not errors else 1

if __name__ == "__main__":
    sys.exit(main())
