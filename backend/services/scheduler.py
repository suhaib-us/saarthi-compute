import asyncio
import uuid
import time
import sys
import os
from dataclasses import dataclass, field
from typing import Dict, Optional, Any

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "workers"))
from base_worker import WorkerResult
from cpu_worker import CPUWorker
from gpu_worker import GPUWorker, GPU_INFO, generate_colab_link
from cloud_worker import CloudWorker


@dataclass
class TaskRecord:
    task_id: str
    description: str
    state: str  # queued, scheduled, running, completed, failed
    recommended_resource: Optional[str] = None
    reasoning: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None


class TaskStore:
    """In-memory primary task store. No external dependencies."""

    def __init__(self):
        self._tasks: Dict[str, TaskRecord] = {}

    def create(self, description: str, recommended_resource: str = "", reasoning: str = "") -> TaskRecord:
        task_id = uuid.uuid4().hex[:12]
        record = TaskRecord(
            task_id=task_id,
            description=description,
            state="queued",
            recommended_resource=recommended_resource,
            reasoning=reasoning,
        )
        self._tasks[task_id] = record
        return record

    def get(self, task_id: str) -> Optional[TaskRecord]:
        return self._tasks.get(task_id)

    def update_state(self, task_id: str, state: str):
        rec = self._tasks.get(task_id)
        if rec:
            rec.state = state
            rec.updated_at = time.time()
            if state in ("completed", "failed"):
                rec.completed_at = time.time()

    def set_result(self, task_id: str, result: dict):
        rec = self._tasks.get(task_id)
        if rec:
            rec.result = result
            rec.updated_at = time.time()

    def set_error(self, task_id: str, error: str):
        rec = self._tasks.get(task_id)
        if rec:
            rec.error = error
            rec.updated_at = time.time()

    def list_recent(self, limit: int = 20) -> list:
        tasks = sorted(self._tasks.values(), key=lambda t: t.created_at, reverse=True)
        return tasks[:limit]


task_store = TaskStore()

_cpu_worker = CPUWorker()
_gpu_worker = GPUWorker()
_cloud_worker = CloudWorker()


def _get_worker(resource: str):
    if resource == "gpu" and _gpu_worker is not None:
        return _gpu_worker
    if resource == "cloud" and _cloud_worker is not None:
        return _cloud_worker
    return _cpu_worker


def register_gpu_worker(worker):
    global _gpu_worker
    _gpu_worker = worker


def register_cloud_worker(worker):
    global _cloud_worker
    _cloud_worker = worker


async def execute_task(
    task_id: str,
    task_type: str,
    resource: str,
    params: dict,
) -> WorkerResult:
    task_store.update_state(task_id, "scheduled")
    await asyncio.sleep(0.05)

    task_store.update_state(task_id, "running")

    worker = _get_worker(resource)

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, worker.execute, task_type, params)

    result_dict = {
        "resource": result.resource,
        "task_type": result.task_type,
        "time_seconds": result.time_seconds,
        "cost_usd": result.cost_usd,
        "energy_wh": result.energy_wh,
        "output_summary": result.output_summary,
        "metadata": result.metadata,
    }
    task_store.set_result(task_id, result_dict)
    task_store.update_state(task_id, "completed")

    return result


async def execute_comparison(
    task_id: str,
    task_type: str,
    params: dict,
) -> list:
    """Run the task on all available workers and return comparison."""
    results = []
    workers = [("cpu", _cpu_worker)]
    if _gpu_worker is not None:
        workers.append(("gpu", _gpu_worker))
    if _cloud_worker is not None:
        workers.append(("cloud", _cloud_worker))

    loop = asyncio.get_event_loop()
    for resource_name, worker in workers:
        r = await loop.run_in_executor(None, worker.execute, task_type, params)
        results.append({
            "resource": r.resource,
            "task_type": r.task_type,
            "time_seconds": r.time_seconds,
            "cost_usd": r.cost_usd,
            "energy_wh": r.energy_wh,
            "output_summary": r.output_summary,
            "metadata": r.metadata,
        })

    return results
