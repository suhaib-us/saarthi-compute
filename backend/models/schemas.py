from pydantic import BaseModel, Field
from typing import Optional, List
from enum import Enum


class TaskState(str, Enum):
    QUEUED = "queued"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TaskRequest(BaseModel):
    task_description: str = Field(..., min_length=1, max_length=1000)
    budget_usd: float = Field(default=5.0, ge=0, le=100)
    prefer_offline: bool = Field(default=False)
    time_weight: float = Field(default=0.4, ge=0, le=1.0)
    cost_weight: float = Field(default=0.35, ge=0, le=1.0)
    energy_weight: float = Field(default=0.25, ge=0, le=1.0)


class ExecutionOptionResponse(BaseModel):
    resource: str
    recommended: bool
    score: float
    estimated_time_seconds: float
    estimated_time_display: str
    estimated_cost_usd: float
    estimated_energy_wh: float
    pros: List[str]
    cons: List[str]
    action: str


class TaskResponse(BaseModel):
    success: bool
    task_id: str
    task: dict
    recommendation: dict
    explanation: str
    action_steps: List[str]
    options: List[ExecutionOptionResponse]
    resources: List[dict]


class ExecuteRequest(BaseModel):
    task_description: str = Field(..., min_length=1)
    resource: Optional[str] = Field(default=None, description="cpu, gpu, or cloud. If None, uses recommendation.")
    matrix_size: Optional[int] = Field(default=500, ge=10, le=5000)


class WorkerResultResponse(BaseModel):
    resource: str
    task_type: str
    time_seconds: float
    cost_usd: float
    energy_wh: float
    output_summary: str
    metadata: dict


class TaskStatusResponse(BaseModel):
    task_id: str
    state: TaskState
    description: str
    recommended_resource: Optional[str] = None
    reasoning: Optional[str] = None
    result: Optional[WorkerResultResponse] = None
    created_at: float
    updated_at: float
    completed_at: Optional[float] = None


class CompareResponse(BaseModel):
    task_id: str
    description: str
    comparisons: List[WorkerResultResponse]
    recommendation: str
    savings_summary: str
