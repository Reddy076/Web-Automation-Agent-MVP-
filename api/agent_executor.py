"""Playwright executor: goto + extract + screenshot with audit log."""
import base64
import re
import time
import uuid
from pathlib import Path

from playwright.async_api import async_playwright

DATA_DIR = Path.cwd() / "data" / "screenshots"
DATA_DIR.mkdir(parents=True, exist_ok=True)

PRICE_RE = re.compile(r"[$€£₹]\s?[\d,]+(?:\.\d{2})?")

ALLOWED_DOMAINS = None  # set e.g. {"example.com"} to lock demo scope

def _allowed(url: str) -> bool:
    if not ALLOWED_DOMAINS:
        return True
    try:
        from urllib.parse import urlparse
        return urlparse(url).netloc in ALLOWED_DOMAINS
    except Exception:
        return False

async def execute_stepwise(url: str, task: str, steps: list[dict], log_fn=None):
    run_id = uuid.uuid4().hex[:8]
    logs: list[dict] = []
    result: dict = {}

    def log(action: str, detail: str = "", ok: bool = True):
        entry = {"t": time.time(), "action": action, "detail": detail, "ok": ok}
        logs.append(entry)
        if log_fn:
            try:
                log_fn(entry)
            except Exception:
                pass

    if not _allowed(url):
        raise ValueError(f"Domain not allowlisted: {url}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        try:
            for i, step in enumerate(steps):
                a = step.get("action")
                log(a, str(step))
                if a == "goto":
                    target = step.get("url", url)
                    if not _allowed(target):
                        raise ValueError(f"Blocked domain: {target}")
                    await page.goto(target, wait_until="domcontentloaded", timeout=30000)
                    await page.wait_for_timeout(1500)
                    result["final_url"] = page.url
                    result["title"] = await page.title()
                elif a == "extract":
                    text = await page.inner_text("body")
                    result["text_preview"] = text[:4000]
                    result["prices"] = PRICE_RE.findall(text)[:20]
                    result["headings"] = await page.eval_on_selector_all(
                        "h1,h2,h3", "els => els.slice(0,20).map(e => e.innerText.slice(0,120))"
                    )
                    links = await page.eval_on_selector_all(
                        "a", "els => els.slice(0,30).map(e => ({text: e.innerText.slice(0,80), href: e.href}))"
                    )
                    result["links"] = links
                elif a == "screenshot":
                    path = DATA_DIR / f"{run_id}_{i}.png"
                    await page.screenshot(path=str(path), full_page=False)
                    with open(path, "rb") as f:
                        result["screenshot_b64"] = base64.b64encode(f.read()).decode()
                    result["screenshot_file"] = str(path)
                elif a == "click":
                    sel = step.get("selector", "a")
                    await page.click(sel, timeout=8000)
                    await page.wait_for_timeout(1200)
                elif a == "type":
                    sel = step.get("selector", "input")
                    await page.fill(sel, step.get("text", ""), timeout=8000)
        finally:
            await browser.close()

    return {"run_id": run_id, "task": task, "url": url, "steps": steps, "logs": logs, "result": result}
