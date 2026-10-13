"""Heuristic planner + optional LLM planner for MVP."""
import json
import os

def heuristic_plan(task: str, url: str) -> list[dict]:
    return [
        {"action": "goto", "url": url, "reason": "navigate to start URL"},
        {"action": "extract", "reason": f"extract data for task: {task}"},
        {"action": "screenshot", "reason": "visual audit log"},
    ]

def llm_plan(task: str, url: str) -> list[dict]:
    """Use OpenAI if key present, else fallback. Keeps MVP runnable with no key."""
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return heuristic_plan(task, url)
    try:
        from openai import OpenAI
        client = OpenAI()
        prompt = f"""You drive a headless browser. Task: {task}. Start URL: {url}.
Return ONLY a JSON list of steps. Allowed actions: goto, extract, screenshot, click, type.
Example: [{{"action":"goto","url":"{url}"}}, {{"action":"extract"}}, {{"action":"screenshot"}}]
Max 5 steps."""
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        text = resp.choices[0].message.content.strip()
        # strip code fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        steps = json.loads(text)
        # safety: force first step goto, cap 6 steps, allowlist actions
        allowed = {"goto", "extract", "screenshot", "click", "type"}
        steps = [s for s in steps if s.get("action") in allowed][:6]
        if not steps or steps[0].get("action") != "goto":
            steps.insert(0, {"action": "goto", "url": url})
        return steps
    except Exception:
        return heuristic_plan(task, url)

def plan(task: str, url: str) -> list[dict]:
    return llm_plan(task, url)
