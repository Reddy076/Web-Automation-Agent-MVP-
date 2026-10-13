# Web Automation Agent (resume project #10)

Prompt -> headless browser -> structured JSON + screenshot + audit log.

## Quickstart (Windows PowerShell)

```powershell
cd web-agent\api
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
# optional: $env:OPENAI_API_KEY="sk-..." for LLM planner, else heuristic planner
uvicorn main:app --reload --port 8000
# open http://localhost:8000
```

Try: `url=https://example.com`, `task=get headings and links`.

## Structure
- `api/main.py` — FastAPI (`POST /api/run`, `GET /api/runs`)
- `api/planner.py` — heuristic now, LLM if `OPENAI_API_KEY` set
- `api/executor.py` — Playwright goto/extract/screenshot + logs
- `web/index.html` — demo UI

## Next steps to make it resume-grade
1. Lock scope: allowlist 2-3 demo sites, add `ALLOWED_DOMAINS` in executor.py
2. Add queue: Redis + RQ/Celery, `POST` returns job id, poll/WS for progress
3. Add human-approve before click/submit, replay from `logs`
4. Add evals: success rate on 10 fixed tasks, save to `data/evals.json`
5. Dockerize + deploy API, record 60s demo GIF for README
