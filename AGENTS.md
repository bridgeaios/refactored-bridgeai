# AGENTS.md - Bridge Task Runner

## Project Overview

- **Type**: FastAPI backend + HTML frontend Docker application
- **Stack**: Python 3.11 (FastAPI, Uvicorn), Nginx, Docker

## Build Commands

### Docker
```bash
docker-compose up --build        # Build and start
docker-compose up -d             # Background
docker-compose down              # Stop
docker-compose logs -f          # View logs
```

### Local Development
```bash
# Backend
cd backend && pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Frontend
cd frontend && python -m http.server 8082
```

### Test Commands
```bash
pytest                    # Run all tests
pytest -v               # Verbose
pytest -k "test_name"   # Single test
pytest tests/test_main.py -v  # Specific file
```

### Lint Commands
```bash
ruff check .            # Lint Python
mypy backend/           # Type check
```

## Code Style

### Python

**Imports**: stdlib → external → local
```python
import os
from typing import Optional
from fastapi import FastAPI
from . import utils
```

**Types**: Always use type hints
```python
def process_task(task_id: int, data: dict) -> dict[str, Any]: ...
async def get_user(user_id: int) -> Optional[User]: ...
```

**Naming**: snake_case (vars/funcs), PascalCase (classes), UPPER_SNAKE (constants)

**Error Handling**
```python
try:
    result = await process_data(data)
except ValueError as e:
    logger.warning(f"Invalid input: {e}")
    raise HTTPException(status_code=400, detail=str(e))
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")
```

**Async**: Use `async def` for I/O-bound ops, always `await`

### HTML/Frontend
- Semantic HTML5, meaningful IDs/classes
- ES6+ syntax, `const` by default, never `var`
- Handle errors in async operations

### Docker
- Specific version tags (not `latest`)
- Combine RUN commands to reduce layers
- Use `.dockerignore`

## Project Structure
```
.
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── index.html
│   └── Dockerfile
└── docker-compose.yml
```

## API Endpoints

| Method | Endpoint  | Description    |
|--------|-----------|---------------|
| POST   | /run-task | Submit a task |

Ports: Backend 8080, Frontend 8082

## Cursor Rules

When working on related projects (e.g., boss_bot_x_github):
- Write clean, production-ready Python code
- Use Decimal for money calculations
- Type hints required on all functions
- Docstrings for all functions/classes
- Error handling for critical operations
- No placeholders or TODOs in production
- Direct, minimal, engineering-focused tone
