FROM python:3.12-slim
WORKDIR /app

# ── Layer 1: system tools + pip upgrade ──────────────────────────────────────
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir --upgrade pip

# ── Layer 2: PyTorch CPU (heavy ~2GB — cached after first build) ──────────────
# Kept in its own RUN so the layer is reused on every subsequent rebuild.
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# ── Layer 3: App requirements (re-runs only when requirements.txt changes) ────
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# ── Layer 4: Application code ─────────────────────────────────────────────────
COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
