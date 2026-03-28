"""
Learning Layer — Adaptive decision improvement from historical outcomes.

Storage chain: Convex → local JSON file → in-memory.
Tracks: task inputs, decisions, execution metrics, success/failure.
Uses stored data to bias future resource recommendations.
"""

import os
import json
import time
import threading
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

HISTORY_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "task_history.json")
MAX_HISTORY = 500


@dataclass
class TaskOutcome:
    task_type: str
    resource_used: str
    recommended_resource: str
    execution_time: float
    execution_cost: float
    execution_energy: float
    success: bool
    timestamp: float
    task_description: str = ""
    decision_source: str = "scoring"


class LearningStore:
    """Thread-safe learning store with Convex → JSON → memory fallback."""

    def __init__(self):
        self._lock = threading.Lock()
        self._history: List[dict] = []
        self._bias_cache: Dict[str, Dict[str, float]] = {}
        self._load()

    def _load(self):
        """Load history from JSON file if it exists."""
        try:
            os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
            if os.path.exists(HISTORY_FILE):
                with open(HISTORY_FILE, "r") as f:
                    self._history = json.load(f)
        except Exception:
            self._history = []

    def _save(self):
        """Persist history to JSON file."""
        try:
            os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
            with open(HISTORY_FILE, "w") as f:
                json.dump(self._history[-MAX_HISTORY:], f, indent=2)
        except Exception:
            pass

    def record_outcome(self, outcome: TaskOutcome) -> None:
        """Record a task outcome for future learning."""
        with self._lock:
            self._history.append(asdict(outcome))
            if len(self._history) > MAX_HISTORY:
                self._history = self._history[-MAX_HISTORY:]
            self._bias_cache.clear()
            self._save()

        self._try_convex_store(outcome)

    def _try_convex_store(self, outcome: TaskOutcome) -> None:
        """Attempt to store outcome in Convex for cross-session persistence."""
        try:
            from convex_client import is_convex_configured, _convex_mutation
            if is_convex_configured():
                _convex_mutation("createTask", {
                    "description": f"[learning] {outcome.task_description[:100]}",
                    "recommended_resource": outcome.resource_used,
                    "reasoning": (
                        f"Execution: {outcome.execution_time:.2f}s, "
                        f"${outcome.execution_cost:.4f}, "
                        f"{'success' if outcome.success else 'failed'}"
                    ),
                })
        except Exception:
            pass

    def get_bias(self, task_type: str) -> Dict[str, float]:
        """
        Compute resource bias scores from historical outcomes.
        Higher bias = resource performed well historically for this task type.
        Returns: {"cpu": 0.0-1.0, "gpu": 0.0-1.0, "cloud": 0.0-1.0}
        """
        with self._lock:
            if task_type in self._bias_cache:
                return self._bias_cache[task_type]

            relevant = [h for h in self._history if h.get("task_type") == task_type]
            if not relevant:
                return {"cpu": 0.0, "gpu": 0.0, "cloud": 0.0}

            bias = {"cpu": 0.0, "gpu": 0.0, "cloud": 0.0}
            counts = {"cpu": 0, "gpu": 0, "cloud": 0}

            for h in relevant:
                resource = h.get("resource_used", "cpu")
                if resource not in bias:
                    continue
                counts[resource] += 1

                score = 0.0
                if h.get("success", False):
                    score += 0.5

                # Faster execution → higher score
                exec_time = h.get("execution_time", 0)
                if exec_time > 0:
                    score += min(0.3, 10.0 / exec_time)

                # Lower cost → higher score
                exec_cost = h.get("execution_cost", 0)
                if exec_cost == 0:
                    score += 0.2
                else:
                    score += min(0.2, 0.5 / exec_cost)

                bias[resource] += score

            for r in bias:
                if counts[r] > 0:
                    bias[r] = round(bias[r] / counts[r], 3)

            self._bias_cache[task_type] = bias
            return bias

    def get_stats(self) -> dict:
        """Return learning statistics."""
        with self._lock:
            total = len(self._history)
            if total == 0:
                return {"total_tasks": 0, "resource_distribution": {}, "success_rate": 0}

            resource_counts = {}
            successes = 0
            for h in self._history:
                r = h.get("resource_used", "unknown")
                resource_counts[r] = resource_counts.get(r, 0) + 1
                if h.get("success", False):
                    successes += 1

            return {
                "total_tasks": total,
                "resource_distribution": resource_counts,
                "success_rate": round(successes / total, 2),
                "storage": "json" if os.path.exists(HISTORY_FILE) else "memory",
            }

    def get_recent(self, n: int = 10) -> List[dict]:
        """Return N most recent outcomes."""
        with self._lock:
            return list(reversed(self._history[-n:]))


# Singleton instance
_store: Optional[LearningStore] = None


def get_learning_store() -> LearningStore:
    global _store
    if _store is None:
        _store = LearningStore()
    return _store
