"""
Orchestrator — Central AI brain coordinating all services.

Pipeline:
  User Input
  → LLM-based Task Analysis (task_analyzer)
  → Learning Bias Lookup (learning)
  → Resource Discovery (resource_fetcher: Exa + Apify + static)
  → Availability Validation
  → Hybrid Decision Making (decision_engine: LLM + scoring)
  → Explanation Generation (ai_explainer: LLM + templates)
  → Convex persistence + in-memory fallback

This module replaces the manual chaining in main.py with a single
orchestrated pipeline that handles errors, fallbacks, and data flow.
"""

import os
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from task_analyzer import analyze_task, TaskProfile
from decision_engine import make_decision, Decision, UserConstraints, fmt
from resource_fetcher import fetch_resources, ComputeResource
from ai_explainer import generate_explanation
from learning import get_learning_store, TaskOutcome
from convex_client import (
    convex_create_task, convex_update_status,
    convex_update_metrics, is_convex_configured,
)

USD_TO_INR = 84


@dataclass
class OrchestratorResult:
    """Complete result from the orchestration pipeline."""
    success: bool
    task_id: str
    convex_id: Optional[str]

    profile: TaskProfile
    decision: Decision
    explanation: dict
    resources: List[ComputeResource]

    learning_bias: Dict[str, float]
    pipeline_stages: Dict[str, dict]
    total_time_ms: float


@dataclass
class PipelineStage:
    name: str
    status: str = "pending"
    time_ms: float = 0.0
    source: str = ""
    error: Optional[str] = None


class Orchestrator:
    """
    AI-driven orchestration pipeline. Coordinates all services with
    proper error handling, fallback chains, and timing telemetry.
    """

    def __init__(self):
        self.learning = get_learning_store()

    def analyze(
        self,
        task_description: str,
        budget_usd: float = 5.0,
        prefer_offline: bool = False,
        time_weight: float = 0.4,
        cost_weight: float = 0.35,
        energy_weight: float = 0.25,
        user_level: str = "beginner",
    ) -> OrchestratorResult:
        """
        Run the full AI orchestration pipeline.
        Each stage has timing, source tracking, and graceful fallback.
        """
        start = time.time()
        stages: Dict[str, dict] = {}

        # ── Stage 1: AI Task Analysis ─────────────────────────────
        t0 = time.time()
        profile = analyze_task(task_description)
        stages["task_analysis"] = {
            "status": "ok",
            "time_ms": round((time.time() - t0) * 1000, 1),
            "source": profile.analysis_source,
            "task_type": profile.task_type,
            "llm_reasoning": profile.llm_reasoning[:150] if profile.llm_reasoning else "",
        }

        # ── Stage 2: Learning Bias Lookup ─────────────────────────
        t0 = time.time()
        learning_bias = self.learning.get_bias(profile.task_type)
        stages["learning"] = {
            "status": "ok",
            "time_ms": round((time.time() - t0) * 1000, 1),
            "bias": learning_bias,
            "history_count": self.learning.get_stats()["total_tasks"],
        }

        # ── Stage 3: Resource Discovery ───────────────────────────
        t0 = time.time()
        try:
            resources = fetch_resources(profile.task_type, task_description)
            live_count = sum(1 for r in resources if r.source in ("exa", "apify"))
            stages["resource_discovery"] = {
                "status": "ok",
                "time_ms": round((time.time() - t0) * 1000, 1),
                "total_resources": len(resources),
                "live_resources": live_count,
                "sources": list(set(r.source for r in resources)),
            }
        except Exception as e:
            resources = []
            stages["resource_discovery"] = {
                "status": "fallback",
                "time_ms": round((time.time() - t0) * 1000, 1),
                "error": str(e)[:100],
            }

        # ── Stage 4: Availability Check ──────────────────────────
        t0 = time.time()
        available_count = sum(
            1 for r in resources
            if r.availability and r.availability.available
        )
        stages["availability_check"] = {
            "status": "ok",
            "time_ms": round((time.time() - t0) * 1000, 1),
            "available_resources": available_count,
            "total_checked": len(resources),
        }

        # ── Stage 5: Hybrid Decision Making ──────────────────────
        t0 = time.time()
        constraints = UserConstraints(
            budget_usd=budget_usd,
            prefer_offline=prefer_offline,
            time_weight=time_weight,
            cost_weight=cost_weight,
            energy_weight=energy_weight,
        )
        decision = make_decision(
            profile, constraints,
            learning_bias=learning_bias if any(v > 0 for v in learning_bias.values()) else None,
        )
        stages["decision"] = {
            "status": "ok",
            "time_ms": round((time.time() - t0) * 1000, 1),
            "source": decision.decision_source,
            "recommended": decision.recommended_resource,
            "confidence": decision.confidence,
        }

        # If the recommended resource is unavailable, try downgrading
        if resources:
            rec_available = any(
                r for r in resources
                if r.availability and r.availability.available
                and decision.recommended_resource in r.resource_type
            )
            # Only downgrade cloud → gpu or gpu → cpu
            if not rec_available and decision.recommended_resource == "cloud":
                gpu_opt = next(
                    (o for o in decision.options if o.resource == "gpu"), None
                )
                if gpu_opt:
                    decision.recommended_resource = "gpu"
                    decision.reasoning += " (Cloud unavailable → downgraded to GPU)"
                    for o in decision.options:
                        o.recommended = (o.resource == "gpu")

        # ── Stage 6: Explanation Generation ──────────────────────
        t0 = time.time()
        explanation = generate_explanation(profile, decision, user_level)
        stages["explanation"] = {
            "status": "ok",
            "time_ms": round((time.time() - t0) * 1000, 1),
            "source": explanation.get("source", "template"),
        }

        # ── Stage 7: Persistence (Convex primary, in-memory fallback) ─
        t0 = time.time()
        options_data = self._serialize_options(decision)
        convex_id = convex_create_task(
            description=task_description,
            recommended_resource=decision.recommended_resource,
            reasoning=decision.reasoning,
            explanation=explanation.get("explanation", ""),
            options=options_data,
        )

        from scheduler import task_store
        record = task_store.create(
            description=task_description,
            recommended_resource=decision.recommended_resource,
            reasoning=decision.reasoning,
        )
        task_id = convex_id or record.task_id

        stages["persistence"] = {
            "status": "ok",
            "time_ms": round((time.time() - t0) * 1000, 1),
            "convex": bool(convex_id),
            "fallback": "in_memory",
        }

        total_ms = round((time.time() - start) * 1000, 1)

        return OrchestratorResult(
            success=True,
            task_id=task_id,
            convex_id=convex_id,
            profile=profile,
            decision=decision,
            explanation=explanation,
            resources=resources,
            learning_bias=learning_bias,
            pipeline_stages=stages,
            total_time_ms=total_ms,
        )

    def record_execution(
        self,
        task_type: str,
        resource_used: str,
        recommended_resource: str,
        execution_time: float,
        execution_cost: float,
        execution_energy: float,
        success: bool,
        task_description: str = "",
        decision_source: str = "scoring",
    ) -> None:
        """Record an execution outcome for the learning layer."""
        outcome = TaskOutcome(
            task_type=task_type,
            resource_used=resource_used,
            recommended_resource=recommended_resource,
            execution_time=execution_time,
            execution_cost=execution_cost,
            execution_energy=execution_energy,
            success=success,
            timestamp=time.time(),
            task_description=task_description,
            decision_source=decision_source,
        )
        self.learning.record_outcome(outcome)

    def get_learning_stats(self) -> dict:
        return self.learning.get_stats()

    def get_learning_history(self, n: int = 10) -> List[dict]:
        return self.learning.get_recent(n)

    def _serialize_options(self, decision: Decision) -> List[dict]:
        options_data = []
        for opt in decision.options:
            options_data.append({
                "resource": opt.resource,
                "recommended": opt.recommended,
                "score": opt.score,
                "estimated_time_seconds": opt.estimated_time_seconds,
                "estimated_time_display": fmt(opt.estimated_time_seconds),
                "estimated_cost_usd": opt.estimated_cost_usd,
                "estimated_cost_inr": round(opt.estimated_cost_usd * USD_TO_INR, 2),
                "estimated_energy_wh": opt.estimated_energy_wh,
                "pros": opt.pros,
                "cons": opt.cons,
                "action": opt.action,
            })
        return options_data

    def serialize_resources(self, resources: List[ComputeResource]) -> List[dict]:
        result = []
        for r in resources[:6]:
            avail = None
            if r.availability:
                avail = {
                    "available": r.availability.available,
                    "confidence": r.availability.confidence,
                    "wait_time_minutes": r.availability.wait_time_minutes,
                    "usage_limit": r.availability.usage_limit,
                }
            result.append({
                "name": r.name,
                "url": r.url,
                "resource_type": r.resource_type,
                "description": r.description,
                "gpu_hours_free": r.gpu_hours_free,
                "best_for": r.best_for,
                "requires_signup": r.requires_signup,
                "source": r.source,
                "relevance_score": r.relevance_score,
                "availability": avail,
            })
        return result


# Singleton
_orchestrator: Optional[Orchestrator] = None


def get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator()
    return _orchestrator
