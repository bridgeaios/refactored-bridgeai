import time
from pathlib import Path

import pytest
import requests

_BACKEND_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session", autouse=True)
def live_server():
    """Start the FastAPI server for E2E tests (optional — skip if port busy)."""
    import subprocess
    import sys

    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--port", "8001", "--host", "127.0.0.1"],
        cwd=str(_BACKEND_ROOT),
    )
    for _ in range(60):
        try:
            r = requests.get("http://127.0.0.1:8001/api/health", timeout=1)
            if r.status_code == 200:
                break
        except Exception:
            time.sleep(0.5)
    else:
        proc.terminate()
        proc.wait()
        pytest.skip("E2E server failed to start on 8001")
    yield
    proc.terminate()
    proc.wait()
