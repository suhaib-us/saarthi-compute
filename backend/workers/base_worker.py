from dataclasses import dataclass, field
from typing import Any, Dict
from abc import ABC, abstractmethod


@dataclass
class WorkerResult:
    resource: str
    task_type: str
    time_seconds: float
    cost_usd: float
    energy_wh: float
    output_summary: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class BaseWorker(ABC):
    """Abstract base for all execution workers."""

    resource_name: str = "unknown"

    @abstractmethod
    def execute(self, task_type: str, params: dict) -> WorkerResult:
        """Execute a task and return measured results."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this worker is currently usable."""
        ...
