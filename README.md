# Healthcare Agentic Appointment System

Professional modular structure for the existing LangGraph healthcare appointment project.

## Folders
- `agents/`: individual agent logic
- `tools/`: reusable database, appointment and web-search tools
- `orchestration/`: LangGraph state, nodes, routing and graph
- `api/`: FastAPI backend and routes
- `ui/`: Streamlit frontend (communicates with backend over HTTP)
- `database/`: connection, models, repositories and migrations
- `guardrails/`: input/output validation, safety and access-control checks
- `schemas/`: Pydantic request and response models
- `evaluation/`: synthetic evaluation data and AI evaluation runner
- `tests/`: pytest automated tests
- `config/`: settings and prompts
- `data/`: local development database
- `logs/`: local logs

## Migration safety
This is a skeleton, not a replacement for your working code. Copy existing files into the matching folders gradually and update imports. Keep your existing `healthcare.db` and backup files unchanged. Do not commit `.env`, real credentials, or real patient data.

Run commands will be finalized after we migrate and test the existing code.
