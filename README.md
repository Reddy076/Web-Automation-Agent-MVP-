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
- `api/main.py` — FastAPI (`POST /api/run` sync, `POST /api/jobs` async, `GET /api/jobs`)
- `api/jobs.py` — file-backed job records, shared by threads + RQ worker
- `api/worker.py` — RQ worker entry (`python worker.py`, needs `REDIS_URL`)
- `api/planner.py` — heuristic now, LLM if `OPENAI_API_KEY` set
- `api/agent_executor.py` — Playwright goto/extract/screenshot + logs
- `web/index.html` — demo UI (posts a job, polls for progress)
- `docker-compose.yml` — api + worker + redis

## Background jobs

Local (no redis, threads):
```powershell
cd web-agent\api
.\.venv\Scripts\python.exe -m uvicorn main:app --port 8000
```
`POST /api/jobs` returns `{"job_id": ..., "status": "queued"}` instantly,
then `GET /api/jobs/<id>` goes `queued -> started -> finished|failed`.

Prod (redis + RQ):
```powershell
docker compose up --build
# api on :8000 with REDIS_URL set, worker consumes the queue
$env:REDIS_URL="redis://localhost:6379/0"
.\.venv\Scripts\python.exe worker.py
```

## Next steps to make it resume-grade
1. Lock scope: allowlist 2-3 demo sites, add `ALLOWED_DOMAINS` in agent_executor.py
2. ~~Add queue~~ done: `POST /api/jobs` + poll, threads locally / RQ in compose
3. Add human-approve before click/submit, replay from `logs`
4. Add evals: success rate on 10 fixed tasks, save to `data/evals.json`
5. ~~Dockerize~~ done: `api/Dockerfile` + `docker-compose.yml`. Still to do: deploy + 60s demo GIF
