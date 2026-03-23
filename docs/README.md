# BRIDGE AI OS — Digital Twin

Quick start (local development):

1. Build and run with Docker Compose (recommended):

```powershell
docker-compose build
docker-compose up
```

- Backend API: http://localhost:8000
- Frontend: http://localhost:3000

2. Run backend locally without Docker (Windows PowerShell):

```powershell
python -m pip install -r backend/app/requirements.txt
uvicorn app.main:app --reload --port 8000
```

3. Start frontend dev server (option A — static):

```powershell
cd frontend
npm install
npx serve public --single --listen 3000
```

3b. Start frontend with API proxy (option B — recommends backend on 8000):

```powershell
cd frontend
$env:PORT="3020"; node serve-no-cache.cjs
```

Then open http://localhost:3020 (or 3000 for option A).

Model artifacts and training

- Trained emotion model is persisted to `backend/app/artifacts/emotion_model.pt` after training.
- Trigger training by POSTing to `/api/train/start` and check status at `/api/train/status`.

Dashboards & Mobile Navigation

- **Dashboards hub**: http://localhost:3020/dashboards.html — all dashboards, monetization & agents links
- **Mobile nav**: Hamburger menu (☰) on viewports ≤768px; 44px touch targets
- **Docs**: See [docs/TECHNICAL-IMPLEMENTATION-SUMMARY.md](docs/TECHNICAL-IMPLEMENTATION-SUMMARY.md) and [docs/MOBILE-NAV-AND-FEATURES.md](docs/MOBILE-NAV-AND-FEATURES.md)

Notes

- ElevenLabs API key: set `ELEVEN_API_KEY` in the backend service env.
- This repo contains simulated tools and blockchain price access.
- eSIM access is simulated; native app required for real eSIM control.

Running tests

```powershell
python -m pip install -r backend/app/requirements.txt
pytest -q
```

Conda setup (recommended for Python + PyTorch)

1. Create and activate environment:

```powershell
conda create -n bridge-ai python=3.12 -y
conda activate bridge-ai
```

2. Install PyTorch (CPU) and other deps via conda/pip:

```powershell
# Install PyTorch from the PyTorch channel (CPU-only)
conda install pytorch torchvision torchaudio cpuonly -c pytorch -y

# Install remaining Python dependencies
pip install -r backend/app/requirements.txt
```

3. Optional: use the provided environment file to recreate similarly (adjust channel/platform as needed):

```powershell
conda env create -f backend/environment.yml -n bridge-ai-backend
conda activate bridge-ai-backend
```

Notes on PyTorch: if you have CUDA GPU and want GPU-enabled PyTorch, follow installation instructions at https://pytorch.org/ to select the correct CUDA-enabled package.
