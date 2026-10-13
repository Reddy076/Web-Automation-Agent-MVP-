"""Background job core: file-backed records.

Two backends, same record format:
- local dev (no REDIS_URL): ThreadPoolExecutor in main.py
- prod (REDIS_URL set): RQ worker in worker.py

Records live in data/jobs/<job_id>.json so api + worker share
state through a mounted volume. Screenshot payloads stay in the
record file, not in redis.
"""
import asyncio
import json
import os
import time
import uuid
from pathlib import Path

BASE_DIR = Path.cwd()
if BASE_DIR.name != "api" and (BASE_DIR / "api").is_dir():
    BASE_DIR = BASE_DIR / "api"
JOBS_DIR = BASE_DIR / "data" / "jobs"
JOBS_DIR.mkdir(parents=True, exist_ok=True)

MAX_JOBS = 50
QUEUE_NAME = os.getenv("RQ_QUEUE", "web-agent")


def use_redis() -> bool:
    return bool(os.getenv("REDIS_URL"))


def _path(job_id: str) -> Path:
    return JOBS_DIR / f"{job_id}.json"


def _write(record: dict) -> None:
    tmp = _path(record["job_id"]).with_suffix(".tmp")
    tmp.write_text(json.dumps(record), encoding="utf-8")
    tmp.replace(_path(record["job_id"]))


def _update(job_id: str, **fields) -> dict | None:
    p = _path(job_id)
    if not p.exists():
        return None
    record = json.loads(p.read_text(encoding="utf-8"))
    record.update(fields)
    record["updated"] = time.time()
    _write(record)
    return record


def create_job(task: str, url: str) -> dict:
    record = {
        "job_id": uuid.uuid4().hex[:8],
        "task": task,
        "url": url,
        "status": "queued",  # queued -> started -> finished | failed
        "steps": [],
        "logs": [],
        "result": None,
        "error": None,
        "created": time.time(),
        "updated": time.time(),
    }
    _write(record)
    # prune oldest beyond cap
    files = sorted(JOBS_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime)
    for old in files[:-MAX_JOBS]:
        try:
            old.unlink()
        except OSError:
            pass
    return record


def get_job(job_id: str) -> dict | None:
    p = _path(job_id)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def list_jobs() -> list[dict]:
    out = []
    for p in JOBS_DIR.glob("*.json"):
        try:
            r = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        out.append(
            {
                "job_id": r["job_id"],
                "task": r["task"],
                "url": r["url"],
                "status": r["status"],
                "updated": r["updated"],
            }
        )
    out.sort(key=lambda r: r["updated"], reverse=True)
    return out[:MAX_JOBS]


def run_job(job_id: str, task: str, url: str) -> str:
    """Execute one job synchronously. Called from a thread or an RQ worker."""
    from agent_executor import execute_stepwise
    from planner import plan

    _update(job_id, status="started")
    logs: list[dict] = []

    def on_log(entry: dict) -> None:
        logs.append(entry)
        _update(job_id, logs=logs)

    try:
        steps = plan(task, url)
        _update(job_id, steps=steps)
        out = asyncio.run(execute_stepwise(url, task, steps, log_fn=on_log))
        _update(
            job_id,
            status="finished",
            steps=out["steps"],
            logs=out["logs"],
            result=out["result"],
        )
    except Exception as e:  # record failure, never raise through the worker
        _update(job_id, status="failed", logs=logs, error=f"{type(e).__name__}: {e}")
    return job_id
