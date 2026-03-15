$ErrorActionPreference = "Stop"

$BASE = "bridge_stack"

Write-Host "Creating project structure..."

New-Item -ItemType Directory -Force -Path "$BASE/backend" | Out-Null
New-Item -ItemType Directory -Force -Path "$BASE/frontend" | Out-Null

# ---------------- BACKEND ----------------

@"
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/run-task")
async def run_task(data: dict):
    return {"status": "success", "data": data}
"@ | Set-Content "$BASE/backend/main.py"

@"
fastapi
uvicorn
"@ | Set-Content "$BASE/backend/requirements.txt"

@"
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
"@ | Set-Content "$BASE/backend/Dockerfile"

# ---------------- FRONTEND ----------------

@"
<!DOCTYPE html>
<html>
<head>
  <title>Bridge UI</title>
</head>
<body>
  <h1>Run Task</h1>
  <button onclick="submitTask()">Send</button>

  <script>
    async function submitTask() {
      const res = await fetch("http://localhost:8000/run-task", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ task: "bridge" })
      });
      const data = await res.json();
      alert(JSON.stringify(data));
    }
  </script>
</body>
</html>
"@ | Set-Content "$BASE/frontend/index.html"

@"
FROM nginx:alpine
COPY index.html /usr/share/nginx/html/index.html
EXPOSE 80
"@ | Set-Content "$BASE/frontend/Dockerfile"

# ---------------- DOCKER COMPOSE ----------------

@"
version: "3.9"
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"

  frontend:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
"@ | Set-Content "$BASE/docker-compose.yml"

# ---------------- IF / THEN DOCKER CHECK ----------------

Write-Host "Checking Docker installation..."

try {
    docker --version | Out-Null
    Write-Host "Docker detected. Building and running stack..."
    Set-Location $BASE
    docker compose up --build
}
catch {
    Write-Host "Docker not found. Install Docker Desktop and re-run."
    exit 1
}
