"""RQ worker entry. Needs REDIS_URL, e.g. redis://localhost:6379/0.

Local dev:  python worker.py
Docker:     handled by docker-compose.yml (worker service)
"""
import os

from redis import Redis
from rq import Queue, Worker

QUEUE_NAME = os.getenv("RQ_QUEUE", "web-agent")


def main() -> None:
    redis_url = os.environ.get("REDIS_URL")
    if not redis_url:
        raise SystemExit("REDIS_URL is not set - worker has nothing to listen to")
    conn = Redis.from_url(redis_url)
    queue = Queue(QUEUE_NAME, connection=conn)
    worker = Worker([queue], connection=conn)
    print(f"listening on queue '{QUEUE_NAME}' via {redis_url}")
    worker.work()


if __name__ == "__main__":
    main()
