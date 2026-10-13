"""FastAPI entry: POST /api/run -> planner + playwright executor."""
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, HttpUrl

load_dotenv()

from agent_executor import execute_stepwise
from planner import plan

app = FastAPI(title="web-agent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

RUNS: dict = {}
MAX_RUNS = 50

class RunRequest(BaseModel):
    task: str
    url: HttpUrl

@app.get("/api/health")
def health():
    return {"ok": True, "llm": bool(os.getenv("OPENAI_API_KEY"))}

@app.post("/api/run")
async def run_agent(req: RunRequest):
    url = str(req.url)
    if len(req.task) < 3 or len(req.task) > 500:
        raise HTTPException(400, "task must be 3-500 chars")
    steps = plan(req.task, url)
    try:
        out = await execute_stepwise(url, req.task, steps)
    except ValueError as e:
        raise HTTPException(403, str(e))
    except Exception as e:
        raise HTTPException(500, f"run failed: {type(e).__name__}: {e}")
    RUNS[out["run_id"]] = out
    if len(RUNS) > MAX_RUNS:
        RUNS.pop(next(iter(RUNS)))
    # don't ship full b64 in list views, but ok for MVP detail
    return out

@app.get("/api/runs")
def list_runs():
    return [{"run_id": r["run_id"], "task": r["task"], "url": r["url"]} for r in RUNS.values()]

# serve demo UI
WEB = Path(__file__).parent.parent / "web" / "index.html"

@app.get("/")
def index():
    if WEB.exists():
        return FileResponse(str(WEB))
    return {"see": "/docs"}
