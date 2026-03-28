"""
Decision Engine — Hybrid AI + scoring model.

Combines:
  1. Weighted multi-objective scoring (time/cost/energy)
  2. LLM reasoning (OpenAI/Ollama) for nuanced decisions
  3. Resource availability awareness
  4. Learning bias from historical outcomes

The scoring model provides deterministic ranking; the LLM provides
reasoning, edge-case handling, and human-readable justification.
"""

import os
import json
from dataclasses import dataclass, field
from typing import List, Optional, Dict
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

from task_analyzer import TaskProfile


@dataclass
class ExecutionOption:
    resource: str
    recommended: bool
    score: float
    estimated_time_seconds: float
    estimated_cost_usd: float
    estimated_energy_wh: float
    pros: List[str]
    cons: List[str]
    action: str
    availability: Optional[Dict] = None


@dataclass
class Decision:
    recommended_resource: str
    reasoning: str
    options: List[ExecutionOption]
    kashmir_tip: str
    decision_source: str = "scoring"
    confidence: float = 0.0


@dataclass
class UserConstraints:
    budget_usd: float = 5.0
    prefer_offline: bool = False
    time_weight: float = 0.4
    cost_weight: float = 0.35
    energy_weight: float = 0.25


USD_TO_INR = 84

BASE_TIMES = {
    "matrix_ops": 45, "ml_training": 3600, "image_processing": 120,
    "data_processing": 30, "nlp": 1800, "simulation": 300, "simple_compute": 2,
}
SIZE_MULT = {"small": 0.1, "medium": 1.0, "large": 8.0, "massive": 50.0}

TIPS = {
    "cpu": "Small tasks run fine locally — saves your internet data and works offline.",
    "gpu": "Kaggle gives 30 free GPU hours/week. No credit card needed. Perfect for students!",
    "cloud": "AWS Mumbai (ap-south-1) gives lowest latency from South Asia.",
}


def fmt(s):
    if s < 60:
        return f"{s:.1f} sec"
    if s < 3600:
        return f"{s/60:.1f} min"
    return f"{s/3600:.1f} hrs"


# ── Weighted Scoring Model (deterministic) ────────────────────────────

class DecisionPolicy:
    """
    Weighted multi-objective scoring model.
    Scores each compute option against user-tunable weights for
    time, cost, and energy, then applies soft constraint penalties.
    """

    def __init__(self, constraints: UserConstraints):
        self.constraints = constraints
        total = constraints.time_weight + constraints.cost_weight + constraints.energy_weight
        if total == 0:
            total = 1.0
        self.weights = {
            "time": constraints.time_weight / total,
            "cost": constraints.cost_weight / total,
            "energy": constraints.energy_weight / total,
        }

    def score_options(self, options: List[dict]) -> List[dict]:
        max_time = max(o["time"] for o in options) or 1.0
        max_cost = max(o["cost"] for o in options) or 1.0
        max_energy = max(o["energy"] for o in options) or 1.0

        for opt in options:
            norm_time = opt["time"] / max_time
            norm_cost = opt["cost"] / max_cost
            norm_energy = opt["energy"] / max_energy

            score = (
                self.weights["time"] * (1 - norm_time)
                + self.weights["cost"] * (1 - norm_cost)
                + self.weights["energy"] * (1 - norm_energy)
            )

            if self.constraints.prefer_offline and opt["resource"] != "cpu":
                score *= 0.3

            if opt["cost"] > self.constraints.budget_usd:
                score *= 0.1

            if opt["resource"] == "gpu" and not opt.get("gpu_available", False):
                score *= 0.85

            opt["score"] = round(score, 4)

        return sorted(options, key=lambda o: o["score"], reverse=True)


# ── LLM Decision Reasoning ────────────────────────────────────────────

DECISION_SYSTEM_PROMPT = """You are Saarthi, an AI compute advisor for resource-constrained students.

Given a task profile and three compute options (CPU, GPU, Cloud) with scores, provide:
1. Your recommended resource (must be one of: cpu, gpu, cloud)
2. A confidence level (0.0 to 1.0)
3. Reasoning (2-3 sentences, mention ₹ costs, practical constraints)
4. A tip for the student

Consider: the student may have unreliable internet, limited budget, no GPU hardware.
Prefer free options. Prefer offline when internet is poor. Mention Kaggle free GPU hours.

Output ONLY valid JSON:
{
  "recommended": "cpu|gpu|cloud",
  "confidence": 0.0-1.0,
  "reasoning": "...",
  "tip": "..."
}"""


def _llm_decide(profile: TaskProfile, scored_options: List[dict],
                constraints: UserConstraints) -> Optional[dict]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key.startswith("your_"):
        return None

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        options_summary = "\n".join(
            f"  {o['resource'].upper()}: score={o['score']}, "
            f"time={fmt(o['time'])}, cost=${o['cost']:.2f} (₹{o['cost']*USD_TO_INR:.2f}), "
            f"energy={o['energy']:.1f}Wh"
            for o in scored_options
        )

        user_msg = (
            f"Task: \"{profile.raw_input}\"\n"
            f"Type: {profile.task_type}, Complexity: {profile.complexity}, "
            f"Data: {profile.estimated_data_size}, GPU benefit: {profile.gpu_benefit_score}\n"
            f"User budget: ${constraints.budget_usd} (₹{constraints.budget_usd * USD_TO_INR:.0f}), "
            f"Prefer offline: {constraints.prefer_offline}\n"
            f"Scored options:\n{options_summary}"
        )

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": DECISION_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=200,
            temperature=0.3,
            response_format={"type": "json_object"},
        )
        return json.loads(response.choices[0].message.content)
    except Exception:
        return None


# ── Option Builder ────────────────────────────────────────────────────

def _build_raw_options(profile: TaskProfile) -> List[dict]:
    base = BASE_TIMES.get(profile.task_type, 60)
    mult = SIZE_MULT.get(profile.estimated_data_size, 1.0)

    cpu_t = base * mult
    speedup = 1 + (profile.gpu_benefit_score * 24)
    gpu_t = cpu_t / speedup
    cloud_t = gpu_t + 15

    cpu_cost = 0.0
    gpu_cost = 0.0
    cloud_cost = max(0.01, (cloud_t / 3600) * 0.50)

    cpu_energy = (cpu_t / 3600) * 65
    gpu_energy = (gpu_t / 3600) * 250
    cloud_energy = (cloud_t / 3600) * 15

    return [
        {
            "resource": "cpu",
            "time": cpu_t, "cost": cpu_cost, "energy": cpu_energy,
            "pros": ["Free", "No internet needed", "Works offline", "Private data"],
            "cons": [f"Takes {fmt(cpu_t)}", "High battery use for large tasks"],
            "action": "Run locally — no setup needed",
        },
        {
            "resource": "gpu",
            "time": gpu_t, "cost": gpu_cost, "energy": gpu_energy,
            "gpu_available": False,
            "pros": [
                f"{int(cpu_t / max(gpu_t, 0.1))}x faster than CPU",
                "Free on Kaggle (30 hrs/week)",
                "No credit card needed",
            ],
            "cons": ["Needs internet", "30hr/week limit on free tier"],
            "action": "kaggle.com/code — New Notebook — Enable GPU",
        },
        {
            "resource": "cloud",
            "time": cloud_t, "cost": cloud_cost, "energy": cloud_energy,
            "pros": ["Scalable", "Most reliable", "Enterprise grade"],
            "cons": [f"Costs ${cloud_cost:.2f} (₹{cloud_cost * USD_TO_INR:.2f})", "Needs stable internet"],
            "action": f"AWS Mumbai region — est. ${cloud_cost:.2f} (₹{cloud_cost * USD_TO_INR:.2f})",
        },
    ]


# ── Hybrid Decision: merge scoring + LLM ─────────────────────────────

def make_decision(
    profile: TaskProfile,
    constraints: Optional[UserConstraints] = None,
    budget_usd: float = 5.0,
    learning_bias: Optional[Dict[str, float]] = None,
) -> Decision:
    if constraints is None:
        constraints = UserConstraints(budget_usd=budget_usd)

    raw_options = _build_raw_options(profile)

    # Apply learning bias from historical outcomes
    if learning_bias:
        for opt in raw_options:
            bias = learning_bias.get(opt["resource"], 0.0)
            opt["time"] *= max(0.5, 1.0 - bias * 0.1)

    policy = DecisionPolicy(constraints)
    scored = policy.score_options(raw_options)

    scoring_best = scored[0]["resource"]
    scoring_score = scored[0]["score"]

    # Try LLM for nuanced reasoning
    llm_result = _llm_decide(profile, scored, constraints)

    if llm_result and llm_result.get("recommended") in ("cpu", "gpu", "cloud"):
        llm_rec = llm_result["recommended"]
        llm_confidence = min(1.0, max(0.0, float(llm_result.get("confidence", 0.5))))
        llm_reasoning = llm_result.get("reasoning", "")
        llm_tip = llm_result.get("tip", "")

        # Hybrid merge: if LLM and scoring agree, high confidence.
        # If they disagree, scoring wins unless LLM confidence > 0.8.
        if llm_rec == scoring_best:
            final_rec = scoring_best
            final_reasoning = llm_reasoning
            source = "hybrid_agree"
            confidence = min(1.0, (scoring_score + llm_confidence) / 2 + 0.1)
        elif llm_confidence > 0.8:
            final_rec = llm_rec
            final_reasoning = f"AI override: {llm_reasoning}"
            source = "llm_override"
            confidence = llm_confidence
        else:
            final_rec = scoring_best
            final_reasoning = (
                f"Scoring model chose {scoring_best.upper()} (score: {scoring_score}). "
                f"AI suggested {llm_rec.upper()} but with lower confidence ({llm_confidence:.1f}). "
                f"Going with the scoring model."
            )
            source = "scoring_wins"
            confidence = scoring_score

        tip = llm_tip or TIPS.get(final_rec, "")
    else:
        final_rec = scoring_best
        confidence = scoring_score
        source = "scoring"
        tip = TIPS.get(final_rec, "")

        cpu_opt = next(o for o in scored if o["resource"] == "cpu")
        gpu_opt = next(o for o in scored if o["resource"] == "gpu")
        reasoning_map = {
            "cpu": (
                f"Lightweight task — your CPU handles it in {fmt(cpu_opt['time'])}. "
                f"Score: {cpu_opt['score']} (highest). No GPU or cloud needed."
            ),
            "gpu": (
                f"Highly parallel task ({profile.complexity}). Free Kaggle GPU is "
                f"{int(cpu_opt['time'] / max(gpu_opt['time'], 0.1))}x faster — completes in "
                f"{fmt(gpu_opt['time'])} vs {fmt(cpu_opt['time'])} on CPU. "
                f"Score: {gpu_opt['score']} (highest)."
            ),
            "cloud": (
                f"Scale demands cloud at ${scored[0]['cost']:.2f}. "
                f"Score: {scored[0]['score']} (highest among options)."
            ),
        }
        final_reasoning = reasoning_map.get(final_rec, f"Best score: {scoring_score}")

    options = []
    for opt in scored:
        options.append(ExecutionOption(
            resource=opt["resource"],
            recommended=(opt["resource"] == final_rec),
            score=opt["score"],
            estimated_time_seconds=opt["time"],
            estimated_cost_usd=opt["cost"],
            estimated_energy_wh=round(opt["energy"], 2),
            pros=opt["pros"],
            cons=opt["cons"],
            action=opt["action"],
        ))

    return Decision(
        recommended_resource=final_rec,
        reasoning=final_reasoning,
        options=options,
        kashmir_tip=tip,
        decision_source=source,
        confidence=round(confidence, 2),
    )


if __name__ == "__main__":
    from task_analyzer import analyze_task

    tests = [
        ("Train BERT on 50,000 Kashmiri text samples", UserConstraints()),
        ("Simple sum of 100 numbers", UserConstraints()),
        ("Matrix multiply 2000x2000", UserConstraints(prefer_offline=True)),
    ]

    for desc, constraints in tests:
        profile = analyze_task(desc)
        d = make_decision(profile, constraints)
        print(f"\nTask: {desc}")
        print(f"  Source: {d.decision_source} | Confidence: {d.confidence}")
        print(f"  Recommended: {d.recommended_resource.upper()}")
        print(f"  Reason: {d.reasoning[:100]}")
