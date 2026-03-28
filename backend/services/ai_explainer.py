"""
AI Explainer — Context-aware, personalized explanation generator.

Chain: OpenAI LLM → Ollama local → Smart templates.
Generates explanations, actionable steps, and user-level-specific tips.
All cost displays include INR (₹) alongside USD.
"""

import os
import json
from typing import Optional
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

USD_TO_INR = 84


def _inr(usd: float) -> str:
    if usd == 0:
        return "₹0 — zero rupees"
    return f"₹{usd * USD_TO_INR:.2f}"


def _fmt(s: float) -> str:
    if s < 60:
        return f"{s:.1f} seconds"
    if s < 3600:
        return f"{s / 60:.1f} minutes"
    return f"{s / 3600:.1f} hours"


EXPLAINER_SYSTEM_PROMPT = """You are Saarthi, a friendly AI compute advisor for students in resource-constrained environments.

Generate an explanation for a compute task recommendation. The student may have:
- Unreliable or expensive internet
- No GPU hardware
- Limited budget (think in ₹ INR, where $1 = ₹84)

Output ONLY valid JSON:
{
  "explanation": "2-3 sentence friendly explanation of why this resource was recommended. Mention specific numbers (time saved, cost in ₹). Be encouraging.",
  "steps": ["step 1", "step 2", "..."],
  "tips": {
    "beginner": "Tip for someone new to coding/ML",
    "advanced": "Tip for someone with experience"
  },
  "quick_tip": "One practical offline-friendly tip"
}"""


def generate_explanation(profile, decision, user_level: str = "beginner") -> dict:
    """
    Generate personalized explanation.
    Chain: OpenAI → Ollama → template.
    user_level: "beginner" or "advanced"
    """
    result = _try_openai_explanation(profile, decision, user_level)
    if result:
        return result

    result = _try_ollama_explanation(profile, decision, user_level)
    if result:
        return result

    return _template_explanation(profile, decision, user_level)


def _build_context(profile, decision) -> str:
    rec = decision.recommended_resource
    rec_opt = next(o for o in decision.options if o.resource == rec)
    cpu_opt = next(o for o in decision.options if o.resource == "cpu")

    return (
        f"Task: \"{profile.raw_input}\"\n"
        f"Type: {profile.task_type}, Complexity: {profile.complexity}, "
        f"Data: {profile.estimated_data_size}, GPU benefit: {profile.gpu_benefit_score}\n"
        f"Recommended: {rec.upper()} (score: {rec_opt.score})\n"
        f"CPU time: {_fmt(cpu_opt.estimated_time_seconds)}, "
        f"{rec.upper()} time: {_fmt(rec_opt.estimated_time_seconds)}\n"
        f"CPU cost: {_inr(cpu_opt.estimated_cost_usd)}, "
        f"{rec.upper()} cost: {_inr(rec_opt.estimated_cost_usd)}\n"
        f"Decision source: {getattr(decision, 'decision_source', 'scoring')}\n"
        f"Decision reasoning: {decision.reasoning[:200]}"
    )


def _try_openai_explanation(profile, decision, user_level: str) -> Optional[dict]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key.startswith("your_"):
        return None

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)

        context = _build_context(profile, decision)
        user_msg = f"{context}\n\nUser level: {user_level}"

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": EXPLAINER_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            max_tokens=350,
            temperature=0.7,
            response_format={"type": "json_object"},
        )
        parsed = json.loads(response.choices[0].message.content)

        tips = parsed.get("tips", {})
        personalized_tip = tips.get(user_level, tips.get("beginner", ""))

        return {
            "explanation": parsed.get("explanation", "Analysis complete."),
            "source": "openai",
            "steps": parsed.get("steps", _get_action_steps(decision.recommended_resource)),
            "quick_tip": parsed.get("quick_tip", decision.kashmir_tip),
            "personalized_tip": personalized_tip,
            "user_level": user_level,
        }
    except Exception:
        return None


def _try_ollama_explanation(profile, decision, user_level: str) -> Optional[dict]:
    try:
        import requests
        context = _build_context(profile, decision)
        prompt = (
            f"{EXPLAINER_SYSTEM_PROMPT}\n\n{context}\n\nUser level: {user_level}\n\nJSON:"
        )
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2",
                "prompt": prompt,
                "stream": False,
                "format": "json",
            },
            timeout=10,
        )
        if response.ok:
            text = response.json().get("response", "")
            parsed = json.loads(text)
            tips = parsed.get("tips", {})
            personalized_tip = tips.get(user_level, tips.get("beginner", ""))

            return {
                "explanation": parsed.get("explanation", "Analysis complete."),
                "source": "ollama",
                "steps": parsed.get("steps", _get_action_steps(decision.recommended_resource)),
                "quick_tip": parsed.get("quick_tip", decision.kashmir_tip),
                "personalized_tip": personalized_tip,
                "user_level": user_level,
            }
    except Exception:
        pass
    return None


def _template_explanation(profile, decision, user_level: str = "beginner") -> dict:
    rec = decision.recommended_resource
    rec_opt = next(o for o in decision.options if o.resource == rec)
    cpu_opt = next(o for o in decision.options if o.resource == "cpu")
    gpu_opt = next(o for o in decision.options if o.resource == "gpu")

    analysis_note = ""
    source_name = getattr(decision, 'decision_source', 'scoring')
    if source_name.startswith("hybrid") or source_name == "llm_override":
        analysis_note = " Our AI analyzed your specific task to make this recommendation."

    templates = {
        "cpu": (
            f"Your task is lightweight enough to run right on your laptop! "
            f"It'll complete in {_fmt(rec_opt.estimated_time_seconds)} using your CPU — "
            f"no internet, no cloud account, {_inr(0)}. "
            f"This is the most practical choice when internet can be unreliable.{analysis_note}"
        ),
        "gpu": (
            f"Your {profile.task_type.replace('_', ' ')} task involves "
            f"{profile.complexity} operations that GPUs are built for. "
            f"A free Kaggle GPU will be "
            f"{int(cpu_opt.estimated_time_seconds / max(gpu_opt.estimated_time_seconds, 0.1))}x "
            f"faster than your CPU — completing in {_fmt(rec_opt.estimated_time_seconds)} "
            f"instead of {_fmt(cpu_opt.estimated_time_seconds)}. "
            f"Cost: {_inr(0)} on Kaggle, no credit card required.{analysis_note}"
        ),
        "cloud": (
            f"Your workload is large enough to need cloud infrastructure. "
            f"At just ${rec_opt.estimated_cost_usd:.2f} ({_inr(rec_opt.estimated_cost_usd)}), "
            f"a cloud instance offers the best reliability. "
            f"AWS Mumbai region gives low latency from South Asia.{analysis_note}"
        ),
    }

    beginner_tips = {
        "cpu": "No setup needed — just open your terminal and run your script!",
        "gpu": "Kaggle is like Google Docs for coding. Sign up free, no credit card.",
        "cloud": "Start with AWS free tier — you get 750 hours free for 12 months.",
    }
    advanced_tips = {
        "cpu": "Use multiprocessing for CPU-bound tasks. Profile with cProfile first.",
        "gpu": "Mix precision (FP16) training can double your throughput on Kaggle T4.",
        "cloud": "Use spot instances to save 60-90% on GPU compute costs.",
    }

    tip = (beginner_tips if user_level == "beginner" else advanced_tips).get(rec, "")

    return {
        "explanation": templates.get(rec, "Analysis complete."),
        "source": "template",
        "steps": _get_action_steps(rec),
        "quick_tip": decision.kashmir_tip,
        "personalized_tip": tip,
        "user_level": user_level,
    }


def _get_action_steps(rec: str) -> list:
    steps = {
        "cpu": [
            "Open your terminal",
            "Make sure Python is installed: python3 --version",
            "Install dependencies: pip install numpy",
            "Run your script: python your_script.py",
            "View results in terminal or save to file",
        ],
        "gpu": [
            "Go to kaggle.com/code (sign up free, no card needed)",
            "Click 'New Notebook'",
            "Go to Settings → Accelerator → Select 'GPU T4 x2'",
            "Upload your dataset or connect from Kaggle datasets",
            "Run your training code — enjoy the speedup!",
            "Download results when done",
        ],
        "cloud": [
            "Create AWS free tier account at aws.amazon.com",
            "Select Mumbai region (ap-south-1) for best latency",
            "Launch EC2 instance or use SageMaker for ML",
            "Upload your code and data",
            "Run and monitor — remember to stop instance when done!",
        ],
    }
    return steps.get(rec, [])
