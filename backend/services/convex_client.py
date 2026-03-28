"""
Convex HTTP client — writes task state to Convex as the PRIMARY store.
Falls back silently if Convex is unavailable (in-memory dict is crash-safety backup).
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

CONVEX_URL = os.getenv("CONVEX_URL", "")

USD_TO_INR = 84


def _convex_mutation(name: str, args: dict) -> dict | None:
    if not CONVEX_URL or CONVEX_URL.startswith("your_"):
        return None
    try:
        url = f"{CONVEX_URL}/api/mutation"
        resp = requests.post(url, json={"path": f"tasks:{name}", "args": args}, timeout=5)
        if resp.ok:
            return resp.json()
    except Exception:
        pass
    return None


def convex_create_task(description: str, recommended_resource: str, reasoning: str,
                       explanation: str = "", options: list | None = None) -> str | None:
    result = _convex_mutation("createTask", {
        "description": description,
        "recommended_resource": recommended_resource,
        "reasoning": reasoning,
        "explanation": explanation,
        "options": options or [],
    })
    return result.get("value") if result else None


def convex_update_status(convex_id: str, status: str) -> None:
    if not convex_id:
        return
    _convex_mutation("updateStatus", {"taskId": convex_id, "status": status})


def convex_update_metrics(convex_id: str, metrics: dict, result_summary: str) -> None:
    if not convex_id:
        return
    _convex_mutation("updateMetrics", {
        "taskId": convex_id,
        "metrics": metrics,
        "result_summary": result_summary,
    })


def is_convex_configured() -> bool:
    return bool(CONVEX_URL) and not CONVEX_URL.startswith("your_")
