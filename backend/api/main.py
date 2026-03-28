"""
Saarthi Compute — FastAPI Backend (AI-Orchestrated)

All requests flow through the Orchestrator, which coordinates:
  LLM analysis → learning bias → resource discovery → availability →
  hybrid decision → explanation → persistence

Convex is the PRIMARY task store. In-memory dict is the crash-safety fallback.
"""

import sys
import os
import asyncio
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "workers"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "models"))

from task_analyzer import analyze_task
from decision_engine import make_decision, UserConstraints, fmt
from resource_fetcher import fetch_resources
from ai_explainer import generate_explanation
from scheduler import task_store, execute_task, execute_comparison, GPU_INFO, generate_colab_link
from convex_client import (
    convex_create_task, convex_update_status,
    convex_update_metrics, is_convex_configured,
)
from orchestrator import get_orchestrator
from learning import get_learning_store

USD_TO_INR = 84

app = FastAPI(title="Saarthi Compute API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _inr(usd: float) -> str:
    if usd == 0:
        return "₹0"
    return f"₹{usd * USD_TO_INR:.2f}"


class TaskRequest(BaseModel):
    task_description: str = Field(..., min_length=1, max_length=1000)
    budget_usd: float = Field(default=5.0, ge=0, le=100)
    prefer_offline: bool = Field(default=False)
    time_weight: float = Field(default=0.4, ge=0, le=1.0)
    cost_weight: float = Field(default=0.35, ge=0, le=1.0)
    energy_weight: float = Field(default=0.25, ge=0, le=1.0)
    user_level: str = Field(default="beginner")


class ExecuteRequest(BaseModel):
    task_description: str = Field(..., min_length=1)
    resource: Optional[str] = Field(default=None)
    matrix_size: int = Field(default=500, ge=10, le=5000)


@app.get("/")
def root():
    return {"message": "Saarthi Compute AI API", "version": "2.0.0", "status": "healthy"}


@app.get("/api/health")
def health():
    exa = bool(os.getenv("EXA_API_KEY", "").replace("your_exa_key_here", ""))
    openai_ok = bool(os.getenv("OPENAI_API_KEY", "").replace("your_openai_key_here", ""))
    apify = bool(os.getenv("APIFY_TOKEN", "").replace("your_apify_token_here", ""))

    store = get_learning_store()
    stats = store.get_stats()

    return {
        "status": "healthy",
        "version": "2.0.0",
        "ai_capabilities": {
            "openai_configured": openai_ok,
            "exa_configured": exa,
            "apify_configured": apify,
            "convex_configured": is_convex_configured(),
            "ollama_available": _check_ollama(),
        },
        "gpu": GPU_INFO,
        "learning": {
            "total_tasks_learned": stats["total_tasks"],
            "success_rate": stats.get("success_rate", 0),
        },
    }


def _check_ollama() -> bool:
    try:
        import requests
        r = requests.get("http://localhost:11434/api/tags", timeout=2)
        return r.ok
    except Exception:
        return False


@app.get("/api/colab-link")
def colab_link(task_type: str = "matrix_ops", matrix_size: int = 500):
    link = generate_colab_link(task_type, {"matrix_size": matrix_size})
    return {"url": link, "task_type": task_type}


@app.post("/api/analyze")
async def analyze(request: TaskRequest):
    """
    AI-orchestrated task analysis pipeline.
    Runs: LLM analysis → learning bias → resources → decision → explanation.
    """
    if not request.task_description.strip():
        raise HTTPException(400, "Task description required")

    orch = get_orchestrator()
    result = orch.analyze(
        task_description=request.task_description,
        budget_usd=request.budget_usd,
        prefer_offline=request.prefer_offline,
        time_weight=request.time_weight,
        cost_weight=request.cost_weight,
        energy_weight=request.energy_weight,
        user_level=request.user_level,
    )

    colab_url = generate_colab_link(result.profile.task_type, {"matrix_size": 500})

    return {
        "success": True,
        "task_id": result.task_id,
        "convex_id": result.convex_id,
        "task": {
            "input": result.profile.raw_input,
            "type": result.profile.task_type,
            "complexity": result.profile.complexity,
            "data_size": result.profile.estimated_data_size,
            "memory_mb": result.profile.estimated_memory_mb,
            "parallelizable": result.profile.parallelizable,
            "gpu_benefit_score": result.profile.gpu_benefit_score,
            "analysis_source": result.profile.analysis_source,
            "llm_reasoning": result.profile.llm_reasoning,
        },
        "recommendation": {
            "resource": result.decision.recommended_resource,
            "reasoning": result.decision.reasoning,
            "tip": result.decision.kashmir_tip,
            "confidence": result.decision.confidence,
            "decision_source": result.decision.decision_source,
        },
        "explanation": result.explanation.get("explanation", ""),
        "explanation_source": result.explanation.get("source", "template"),
        "action_steps": result.explanation.get("steps", []),
        "personalized_tip": result.explanation.get("personalized_tip", ""),
        "options": orch._serialize_options(result.decision),
        "resources": orch.serialize_resources(result.resources),
        "gpu_info": GPU_INFO,
        "colab_url": colab_url,
        "learning_bias": result.learning_bias,
        "pipeline": result.pipeline_stages,
        "total_pipeline_ms": result.total_time_ms,
    }


@app.post("/api/execute")
async def execute(request: ExecuteRequest):
    profile = analyze_task(request.task_description)
    constraints = UserConstraints()
    decision = make_decision(profile, constraints)
    resource = request.resource or decision.recommended_resource

    record = task_store.create(
        description=request.task_description,
        recommended_resource=resource,
        reasoning=decision.reasoning,
    )

    params = {"matrix_size": request.matrix_size, "array_size": 100_000,
              "width": 1024, "height": 1024, "num_rows": 50_000}

    result = await execute_task(record.task_id, profile.task_type, resource, params)

    orch = get_orchestrator()
    orch.record_execution(
        task_type=profile.task_type,
        resource_used=resource,
        recommended_resource=decision.recommended_resource,
        execution_time=result.time_seconds,
        execution_cost=result.cost_usd,
        execution_energy=result.energy_wh,
        success=True,
        task_description=request.task_description,
        decision_source=getattr(decision, "decision_source", "scoring"),
    )

    return {
        "success": True,
        "task_id": record.task_id,
        "result": {
            "resource": result.resource,
            "task_type": result.task_type,
            "time_seconds": result.time_seconds,
            "cost_usd": result.cost_usd,
            "cost_inr": round(result.cost_usd * USD_TO_INR, 2),
            "energy_wh": result.energy_wh,
            "output_summary": result.output_summary,
            "metadata": result.metadata,
        },
    }


@app.get("/api/task/{task_id}")
def get_task(task_id: str):
    record = task_store.get(task_id)
    if not record:
        raise HTTPException(404, "Task not found")
    return {
        "task_id": record.task_id,
        "description": record.description,
        "state": record.state,
        "recommended_resource": record.recommended_resource,
        "reasoning": record.reasoning,
        "result": record.result,
        "error": record.error,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "completed_at": record.completed_at,
    }


@app.post("/api/compare")
async def compare(request: ExecuteRequest):
    profile = analyze_task(request.task_description)

    record = task_store.create(
        description=request.task_description,
        recommended_resource="compare",
        reasoning="Running comparison across all workers",
    )

    params = {"matrix_size": request.matrix_size, "array_size": 100_000,
              "width": 1024, "height": 1024, "num_rows": 50_000}

    results = await execute_comparison(record.task_id, profile.task_type, params)

    for r in results:
        r["cost_inr"] = round(r["cost_usd"] * USD_TO_INR, 2)

    task_store.set_result(record.task_id, {"comparisons": results})
    task_store.update_state(record.task_id, "completed")

    orch = get_orchestrator()
    for r in results:
        orch.record_execution(
            task_type=profile.task_type,
            resource_used=r["resource"],
            recommended_resource="compare",
            execution_time=r["time_seconds"],
            execution_cost=r["cost_usd"],
            execution_energy=r["energy_wh"],
            success=True,
            task_description=request.task_description,
        )

    cpu_r = next((r for r in results if r["resource"] == "cpu"), None)
    cloud_r = next((r for r in results if r["resource"] == "cloud"), None)
    savings = ""
    if cpu_r and cloud_r:
        savings = (
            f"Local CPU: {_inr(cpu_r['cost_usd'])} (free) vs "
            f"Cloud: {_inr(cloud_r['cost_usd'])} — "
            f"you save {_inr(cloud_r['cost_usd'])}"
        )
    elif cpu_r:
        savings = f"Local CPU: {_inr(cpu_r['cost_usd'])} — zero cost, {cpu_r['time_seconds']:.3f}s"

    return {
        "success": True,
        "task_id": record.task_id,
        "description": request.task_description,
        "comparisons": results,
        "savings_summary": savings,
    }


@app.get("/api/tasks")
def list_tasks(limit: int = 20):
    records = task_store.list_recent(limit)
    return {
        "tasks": [
            {
                "task_id": r.task_id,
                "description": r.description,
                "state": r.state,
                "recommended_resource": r.recommended_resource,
                "created_at": r.created_at,
            }
            for r in records
        ]
    }


@app.get("/api/learning/stats")
def learning_stats():
    """Return learning layer statistics — how many tasks seen, biases, etc."""
    orch = get_orchestrator()
    return {
        "stats": orch.get_learning_stats(),
        "recent_outcomes": orch.get_learning_history(5),
    }


@app.get("/api/learning/bias/{task_type}")
def learning_bias(task_type: str):
    """Get the current resource bias for a specific task type."""
    store = get_learning_store()
    return {
        "task_type": task_type,
        "bias": store.get_bias(task_type),
    }


@app.get("/api/pipeline-info")
def pipeline_info():
    """Show current AI pipeline configuration and capabilities."""
    return {
        "pipeline": [
            {"stage": "Task Analysis", "engine": "OpenAI GPT → Ollama → Heuristic"},
            {"stage": "Learning Bias", "engine": "Historical outcome scoring"},
            {"stage": "Resource Discovery", "engine": "Exa semantic search + Apify scraping + static"},
            {"stage": "Availability Check", "engine": "Apify validation + pattern matching"},
            {"stage": "Decision Making", "engine": "LLM reasoning + weighted scoring (hybrid)"},
            {"stage": "Explanation", "engine": "OpenAI GPT → Ollama → Smart templates"},
            {"stage": "Persistence", "engine": "Convex (primary) + in-memory (fallback)"},
            {"stage": "Learning", "engine": "JSON file + Convex cross-session"},
        ],
        "fallback_design": "Every stage degrades gracefully. System works fully offline.",
    }


@app.websocket("/ws/task/{task_id}")
async def websocket_task(websocket: WebSocket, task_id: str):
    await websocket.accept()
    try:
        prev_state = None
        while True:
            record = task_store.get(task_id)
            if not record:
                await websocket.send_json({"error": "Task not found"})
                break
            if record.state != prev_state:
                prev_state = record.state
                await websocket.send_json({
                    "task_id": record.task_id,
                    "state": record.state,
                    "result": record.result,
                })
            if record.state in ("completed", "failed"):
                break
            await asyncio.sleep(0.2)
    except WebSocketDisconnect:
        pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
