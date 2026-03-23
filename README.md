# Bridge AI OS

All documentation has been moved to the `docs/` folder.

## Quick Start

```powershell
# Run the unified runbook
.\bridge-runbook.ps1 install   # Full installation
.\bridge-runbook.ps1 deploy   # Deploy stack
.\bridge-runbook.ps1 audit    # Run audit
.\bridge-runbook.ps1 update   # Update wallpaper
.\bridge-runbook.ps1 wallpaper # Start live wallpaper
```

## Documentation

See `docs/` folder for all documentation:
- `docs/AGENTS.md` - Project development guidelines
- `docs/SPEC.md` - Project specifications  
- `docs/STATUS-AND-CAPABILITIES.md` - System capabilities
- `docs/README.md` - Project overview

## Project Structure

```
.
├── docs/           # All documentation
├── scripts/        # Automation scripts
├── backend/        # FastAPI backend
├── frontend/       # Frontend UI
├── bridge-auth/    # Auth service
├── bridge_defi/    # DeFi module
├── worker/         # Cloudflare worker
└── bridge-runbook.ps1  # Unified runbook
```
