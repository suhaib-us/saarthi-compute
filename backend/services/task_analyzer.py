"""
Task Analyzer — AI-first workload understanding.

Chain: OpenAI LLM → Ollama (local) → heuristic fallback.
Parses natural language into structured TaskProfile with reasoning.
"""

import os
import re
import json
from dataclasses import dataclass
from typing import Optional, Tuple
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))


@dataclass
class TaskProfile:
    raw_input: str
    task_type: str
    complexity: str
    parallelizable: bool
    estimated_data_size: str
    latency_sensitive: bool
    estimated_memory_mb: int
    gpu_benefit_score: float
    cloud_benefit_score: float
    description: str
    analysis_source: str = "heuristic"
    llm_reasoning: str = ""


VALID_TASK_TYPES = [
    "matrix_ops", "ml_training", "image_processing",
    "nlp", "data_processing", "simple_compute", "simulation",
]

LLM_SYSTEM_PROMPT = """You are Saarthi, an AI compute workload analyzer. Given a task description, output ONLY valid JSON:
{
  "task_type": "matrix_ops|ml_training|image_processing|nlp|data_processing|simple_compute|simulation",
  "complexity": "O(n)|O(n log n)|O(n²)|O(n³)",
  "estimated_data_size": "small|medium|large",
  "gpu_benefit_score": 0.0 to 1.0,
  "cloud_benefit_score": 0.0 to 1.0,
  "parallelizable": true or false,
  "estimated_memory_mb": integer,
  "latency_sensitive": true or false,
  "reasoning": "1-2 sentence explanation of why you classified it this way"
}
Consider: operation type, data volume, compute intensity, parallelism potential, memory needs.
A score of 0.9+ for gpu means the task heavily benefits from GPU acceleration (matrix ops, deep learning, image convolutions).
A score below 0.3 means CPU is sufficient (simple math, small data)."""


def _try_openai(user_input: str) -> Optional[dict]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or api_key.startswith("your_"):
        return None
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": LLM_SYSTEM_PROMPT},
                {"role": "user", "content": f"Analyze this compute task:\n\n{user_input}"},
            ],
            max_tokens=300,
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        text = response.choices[0].message.content
        return json.loads(text)
    except Exception:
        return None


def _try_ollama(user_input: str) -> Optional[dict]:
    """Try local Ollama LLM for offline AI analysis."""
    try:
        import requests
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.2",
                "prompt": f"{LLM_SYSTEM_PROMPT}\n\nAnalyze this compute task:\n\n{user_input}\n\nJSON:",
                "stream": False,
                "format": "json",
            },
            timeout=10,
        )
        if response.ok:
            text = response.json().get("response", "")
            return json.loads(text)
    except Exception:
        pass
    return None


def _parse_llm_result(raw: dict, user_input: str, source: str) -> Optional[TaskProfile]:
    """Validate and convert LLM JSON into a TaskProfile."""
    try:
        task_type = raw.get("task_type", "simple_compute")
        if task_type not in VALID_TASK_TYPES:
            task_type = "simple_compute"

        gpu_score = max(0.0, min(1.0, float(raw.get("gpu_benefit_score", 0.5))))
        cloud_score = max(0.0, min(1.0, float(raw.get("cloud_benefit_score", 0.5))))
        memory = max(64, int(raw.get("estimated_memory_mb", 256)))

        complexity = raw.get("complexity", "O(n)")
        if complexity not in ("O(n)", "O(n log n)", "O(n²)", "O(n³)"):
            complexity = "O(n)"

        data_size = raw.get("estimated_data_size", "medium")
        if data_size not in ("small", "medium", "large"):
            data_size = "medium"

        return TaskProfile(
            raw_input=user_input,
            task_type=task_type,
            complexity=complexity,
            parallelizable=bool(raw.get("parallelizable", False)),
            estimated_data_size=data_size,
            latency_sensitive=bool(raw.get("latency_sensitive", False)),
            estimated_memory_mb=memory,
            gpu_benefit_score=round(gpu_score, 2),
            cloud_benefit_score=round(cloud_score, 2),
            description=f"{task_type.replace('_', ' ').title()} — {data_size} dataset",
            analysis_source=source,
            llm_reasoning=raw.get("reasoning", ""),
        )
    except Exception:
        return None


# ── Heuristic fallback (original logic, always works offline) ─────────

TASK_PATTERNS = {
    "matrix_ops": {
        "keywords": ["matrix", "multiply", "linear algebra", "numpy", "dot product",
                      "eigenvalue", "decomposition", "inverse", "transpose"],
        "complexity": "O(n³)", "parallelizable": True,
        "gpu_benefit": 0.95, "cloud_benefit": 0.6, "base_memory_mb": 512
    },
    "ml_training": {
        "keywords": ["train", "fine-tune", "model", "neural", "bert", "gpt",
                      "classification", "regression", "sentiment", "deep learning",
                      "epoch", "backpropagation", "gradient", "loss function"],
        "complexity": "O(n²)", "parallelizable": True,
        "gpu_benefit": 0.98, "cloud_benefit": 0.85, "base_memory_mb": 2048
    },
    "image_processing": {
        "keywords": ["image", "photo", "vision", "detection", "segmentation",
                      "filter", "convolution", "resize", "crop", "augment"],
        "complexity": "O(n²)", "parallelizable": True,
        "gpu_benefit": 0.90, "cloud_benefit": 0.7, "base_memory_mb": 1024
    },
    "nlp": {
        "keywords": ["text", "nlp", "language", "translation", "summarize",
                      "kashmiri", "urdu", "tokenize", "news articles",
                      "embedding", "transformer", "corpus"],
        "complexity": "O(n²)", "parallelizable": True,
        "gpu_benefit": 0.88, "cloud_benefit": 0.75, "base_memory_mb": 1536
    },
    "data_processing": {
        "keywords": ["csv", "pandas", "dataframe", "sort", "filter", "aggregate",
                      "merge", "join", "etl", "pipeline", "clean"],
        "complexity": "O(n log n)", "parallelizable": False,
        "gpu_benefit": 0.3, "cloud_benefit": 0.5, "base_memory_mb": 256
    },
    "simple_compute": {
        "keywords": ["calculate", "sum", "count", "simple", "basic", "small",
                      "average", "mean", "add", "subtract"],
        "complexity": "O(n)", "parallelizable": False,
        "gpu_benefit": 0.1, "cloud_benefit": 0.1, "base_memory_mb": 64
    },
}


def _estimate_data_size(text: str) -> Tuple[str, float]:
    text_lower = text.lower()
    patterns = [
        (r'(\d+)\s*gb', 1024, 'large'),
        (r'(\d+)\s*mb', 1, 'medium'),
        (r'(\d+)k\s*(rows|samples|images|records|articles)', 0.1, 'medium'),
        (r'(\d+)\s*million', 100, 'large'),
        (r'(\d+)\s*thousand', 0.1, 'medium'),
    ]
    for pattern, multiplier, size_label in patterns:
        match = re.search(pattern, text_lower)
        if match:
            amount = float(match.group(1)) * multiplier
            if amount > 1024:
                return 'large', amount
            elif amount > 100:
                return 'medium', amount
            else:
                return 'small', amount

    if any(w in text_lower for w in ['large', 'huge', 'millions', 'billion']):
        return 'large', 2048
    elif any(w in text_lower for w in ['small', 'tiny', 'quick', 'few']):
        return 'small', 10
    return 'medium', 256


def _heuristic_analyze(user_input: str) -> TaskProfile:
    text_lower = user_input.lower()
    best_match = "simple_compute"
    best_score = 0

    for task_type, config in TASK_PATTERNS.items():
        score = sum(1 for kw in config["keywords"] if kw in text_lower)
        if score > best_score:
            best_score = score
            best_match = task_type

    config = TASK_PATTERNS[best_match]
    data_size, data_mb = _estimate_data_size(user_input)

    gpu_score = config["gpu_benefit"]
    cloud_score = config["cloud_benefit"]

    if data_size == 'large':
        gpu_score = min(1.0, gpu_score + 0.1)
        cloud_score = min(1.0, cloud_score + 0.2)
    elif data_size == 'small':
        gpu_score = max(0.0, gpu_score - 0.3)
        cloud_score = max(0.0, cloud_score - 0.3)

    latency_sensitive = any(w in text_lower for w in ['real-time', 'fast', 'urgent', 'live'])
    memory_mb = config["base_memory_mb"]
    if data_size == 'large':
        memory_mb *= 4
    elif data_size == 'small':
        memory_mb = max(64, memory_mb // 4)

    return TaskProfile(
        raw_input=user_input,
        task_type=best_match,
        complexity=config["complexity"],
        parallelizable=config["parallelizable"],
        estimated_data_size=data_size,
        latency_sensitive=latency_sensitive,
        estimated_memory_mb=memory_mb,
        gpu_benefit_score=round(gpu_score, 2),
        cloud_benefit_score=round(cloud_score, 2),
        description=f"{best_match.replace('_', ' ').title()} — {data_size} dataset",
        analysis_source="heuristic",
        llm_reasoning="Classified using keyword pattern matching and data size estimation.",
    )


# ── Public API ────────────────────────────────────────────────────────

def analyze_task(user_input: str) -> TaskProfile:
    """
    AI-first task analysis chain:
      1. OpenAI LLM (best understanding)
      2. Ollama local LLM (offline AI)
      3. Heuristic fallback (always works)
    """
    llm_result = _try_openai(user_input)
    if llm_result:
        profile = _parse_llm_result(llm_result, user_input, "openai")
        if profile:
            return profile

    llm_result = _try_ollama(user_input)
    if llm_result:
        profile = _parse_llm_result(llm_result, user_input, "ollama")
        if profile:
            return profile

    return _heuristic_analyze(user_input)


if __name__ == "__main__":
    tests = [
        "Train a sentiment model on 10,000 Kashmiri news articles",
        "Matrix multiplication of two 1000x1000 matrices",
        "Simple sum of 100 numbers",
        "Fine-tune BERT for multilingual text classification with 50GB dataset",
    ]
    for t in tests:
        p = analyze_task(t)
        print(f"\n Input: {t[:60]}")
        print(f"   Type: {p.task_type} | GPU: {p.gpu_benefit_score} | Size: {p.estimated_data_size}")
        print(f"   Source: {p.analysis_source} | Reasoning: {p.llm_reasoning[:80]}")
