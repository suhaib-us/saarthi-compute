"""
Saarthi Compute — Backend Endpoint Tests

Tests every FastAPI endpoint with assertions on response structure,
status codes, and data integrity. Runs against a live server on port 8000.
"""

import requests
import sys
import time

BASE = "http://localhost:8000"
PASSED = 0
FAILED = 0
RESULTS = []


def test(name, fn):
    global PASSED, FAILED
    try:
        fn()
        PASSED += 1
        RESULTS.append(("PASS", name))
        print(f"  ✅ {name}")
    except AssertionError as e:
        FAILED += 1
        RESULTS.append(("FAIL", name, str(e)))
        print(f"  ❌ {name} — {e}")
    except Exception as e:
        FAILED += 1
        RESULTS.append(("FAIL", name, str(e)))
        print(f"  ❌ {name} — {type(e).__name__}: {e}")


# ── 1. Root ───────────────────────────────────────────────────────────

def test_root():
    r = requests.get(f"{BASE}/")
    assert r.status_code == 200, f"status {r.status_code}"
    body = r.json()
    assert body["status"] == "healthy"
    assert "version" in body

# ── 2. Health ─────────────────────────────────────────────────────────

def test_health():
    r = requests.get(f"{BASE}/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "healthy"
    assert "ai_capabilities" in body
    caps = body["ai_capabilities"]
    for key in ["openai_configured", "exa_configured", "apify_configured",
                "convex_configured", "ollama_available"]:
        assert key in caps, f"missing ai_capabilities.{key}"
    assert "gpu" in body
    assert "learning" in body
    assert "total_tasks_learned" in body["learning"]

# ── 3. Analyze (main AI pipeline) ────────────────────────────────────

def test_analyze_basic():
    r = requests.post(f"{BASE}/api/analyze", json={
        "task_description": "Train a sentiment model on 5000 news articles",
    })
    assert r.status_code == 200, f"status {r.status_code}"
    body = r.json()
    assert body["success"] is True
    assert "task_id" in body
    assert body["task"]["type"] in [
        "ml_training", "nlp", "image_processing",
        "matrix_ops", "data_processing", "simple_compute", "simulation",
    ]

def test_analyze_response_structure():
    r = requests.post(f"{BASE}/api/analyze", json={
        "task_description": "Matrix multiplication of 1000x1000 matrices",
    })
    body = r.json()
    required_keys = [
        "success", "task_id", "convex_id", "task", "recommendation",
        "explanation", "explanation_source", "action_steps", "options",
        "resources", "gpu_info", "colab_url", "learning_bias", "pipeline",
        "total_pipeline_ms", "personalized_tip",
    ]
    for key in required_keys:
        assert key in body, f"missing top-level key: {key}"

def test_analyze_task_fields():
    r = requests.post(f"{BASE}/api/analyze", json={
        "task_description": "Simple sum of 100 numbers",
    })
    body = r.json()
    task = body["task"]
    for key in ["input", "type", "complexity", "data_size", "memory_mb",
                "parallelizable", "gpu_benefit_score", "analysis_source",
                "llm_reasoning"]:
        assert key in task, f"missing task.{key}"

def test_analyze_recommendation_fields():
    r = requests.post(f"{BASE}/api/analyze", json={
        "task_description": "Train BERT on 50,000 text samples",
    })
    body = r.json()
    rec = body["recommendation"]
    assert rec["resource"] in ("cpu", "gpu", "cloud")
    assert "reasoning" in rec
    assert "confidence" in rec
    assert "decision_source" in rec
    assert 0 <= rec["confidence"] <= 1.0

def test_analyze_options_structure():
    r = requests.post(f"{BASE}/api/analyze", json={
        "task_description": "Image classification on 10,000 photos",
    })
    body = r.json()
    options = body["options"]
    assert len(options) == 3, f"expected 3 options, got {len(options)}"
    resources_seen = set()
    for opt in options:
        for key in ["resource", "recommended", "score", "estimated_time_seconds",
                     "estimated_cost_usd", "estimated_cost_inr", "estimated_energy_wh",
                     "pros", "cons", "action"]:
            assert key in opt, f"missing option key: {key}"
        resources_seen.add(opt["resource"])
    assert resources_seen == {"cpu", "gpu", "cloud"}, f"unexpected resources: {resources_seen}"

def test_analyze_resources_have_availability():
    r = requests.post(f"{BASE}/api/analyze", json={
        "task_description": "NLP text processing task",
    })
    body = r.json()
    resources = body["resources"]
    assert len(resources) > 0, "no resources returned"
    for res in resources:
        for key in ["name", "url", "source", "relevance_score", "availability"]:
            assert key in res, f"missing resource key: {key}"
        if res["availability"]:
            avail = res["availability"]
            assert "available" in avail
            assert "confidence" in avail

def test_analyze_pipeline_telemetry():
    r = requests.post(f"{BASE}/api/analyze", json={
        "task_description": "Data processing with pandas on CSV",
    })
    body = r.json()
    pipeline = body["pipeline"]
    expected_stages = [
        "task_analysis", "learning", "resource_discovery",
        "availability_check", "decision", "explanation", "persistence",
    ]
    for stage in expected_stages:
        assert stage in pipeline, f"missing pipeline stage: {stage}"
        assert "status" in pipeline[stage]
        assert "time_ms" in pipeline[stage]
    assert body["total_pipeline_ms"] > 0

def test_analyze_empty_description():
    r = requests.post(f"{BASE}/api/analyze", json={
        "task_description": "",
    })
    assert r.status_code == 422, f"expected 422, got {r.status_code}"

def test_analyze_with_constraints():
    r = requests.post(f"{BASE}/api/analyze", json={
        "task_description": "Train a large neural network",
        "budget_usd": 0.5,
        "prefer_offline": True,
        "time_weight": 0.1,
        "cost_weight": 0.8,
        "energy_weight": 0.1,
        "user_level": "advanced",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True

# ── 4. Execute ────────────────────────────────────────────────────────

def test_execute_cpu():
    r = requests.post(f"{BASE}/api/execute", json={
        "task_description": "Matrix multiply 200x200",
        "resource": "cpu",
        "matrix_size": 100,
    })
    assert r.status_code == 200, f"status {r.status_code}"
    body = r.json()
    assert body["success"] is True
    result = body["result"]
    assert result["resource"] == "cpu"
    assert result["time_seconds"] > 0
    assert result["cost_usd"] == 0.0
    assert "cost_inr" in result
    assert "output_summary" in result

def test_execute_gpu():
    r = requests.post(f"{BASE}/api/execute", json={
        "task_description": "Matrix multiply",
        "resource": "gpu",
        "matrix_size": 100,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["result"]["resource"] == "gpu"

def test_execute_cloud():
    r = requests.post(f"{BASE}/api/execute", json={
        "task_description": "Matrix multiply",
        "resource": "cloud",
        "matrix_size": 100,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    assert body["result"]["resource"] == "cloud"

def test_execute_auto_resource():
    r = requests.post(f"{BASE}/api/execute", json={
        "task_description": "Simple sum of numbers",
        "matrix_size": 50,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["result"]["resource"] in ("cpu", "gpu", "cloud")

# ── 5. Compare ────────────────────────────────────────────────────────

def test_compare():
    r = requests.post(f"{BASE}/api/compare", json={
        "task_description": "Matrix multiply",
        "matrix_size": 100,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["success"] is True
    comparisons = body["comparisons"]
    assert len(comparisons) == 3
    resources = {c["resource"] for c in comparisons}
    assert resources == {"cpu", "gpu", "cloud"}
    for c in comparisons:
        assert "time_seconds" in c
        assert "cost_usd" in c
        assert "cost_inr" in c
        assert "energy_wh" in c
    assert "savings_summary" in body

# ── 6. Task retrieval ─────────────────────────────────────────────────

def test_get_task():
    create = requests.post(f"{BASE}/api/execute", json={
        "task_description": "Quick test",
        "resource": "cpu",
        "matrix_size": 50,
    })
    task_id = create.json()["task_id"]

    r = requests.get(f"{BASE}/api/task/{task_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["task_id"] == task_id
    assert "state" in body
    assert "description" in body

def test_get_task_not_found():
    r = requests.get(f"{BASE}/api/task/nonexistent_id_12345")
    assert r.status_code == 404

def test_list_tasks():
    r = requests.get(f"{BASE}/api/tasks?limit=5")
    assert r.status_code == 200
    body = r.json()
    assert "tasks" in body
    assert isinstance(body["tasks"], list)

# ── 7. Colab link ────────────────────────────────────────────────────

def test_colab_link():
    r = requests.get(f"{BASE}/api/colab-link?task_type=matrix_ops&matrix_size=500")
    assert r.status_code == 200
    body = r.json()
    assert "url" in body
    assert body["url"].startswith("https://colab.research.google.com")
    assert body["task_type"] == "matrix_ops"

# ── 8. Learning endpoints ────────────────────────────────────────────

def test_learning_stats():
    r = requests.get(f"{BASE}/api/learning/stats")
    assert r.status_code == 200
    body = r.json()
    assert "stats" in body
    stats = body["stats"]
    assert "total_tasks" in stats
    assert "success_rate" in stats
    assert "resource_distribution" in stats
    assert "recent_outcomes" in body

def test_learning_bias():
    r = requests.get(f"{BASE}/api/learning/bias/ml_training")
    assert r.status_code == 200
    body = r.json()
    assert body["task_type"] == "ml_training"
    assert "bias" in body
    bias = body["bias"]
    for key in ["cpu", "gpu", "cloud"]:
        assert key in bias

# ── 9. Pipeline info ─────────────────────────────────────────────────

def test_pipeline_info():
    r = requests.get(f"{BASE}/api/pipeline-info")
    assert r.status_code == 200
    body = r.json()
    assert "pipeline" in body
    stages = body["pipeline"]
    assert len(stages) == 8
    stage_names = [s["stage"] for s in stages]
    assert "Task Analysis" in stage_names
    assert "Decision Making" in stage_names
    assert "Learning" in stage_names
    assert "fallback_design" in body

# ── 10. INR pricing consistency ───────────────────────────────────────

def test_inr_pricing():
    r = requests.post(f"{BASE}/api/analyze", json={
        "task_description": "Cloud-scale ML training on huge dataset",
    })
    body = r.json()
    for opt in body["options"]:
        expected_inr = round(opt["estimated_cost_usd"] * 84, 2)
        assert opt["estimated_cost_inr"] == expected_inr, (
            f"{opt['resource']}: INR mismatch {opt['estimated_cost_inr']} != {expected_inr}"
        )


# ── Runner ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"\n{'='*60}")
    print("  Saarthi Compute — Backend Endpoint Tests")
    print(f"  Target: {BASE}")
    print(f"{'='*60}\n")

    # Check server is up
    try:
        r = requests.get(f"{BASE}/api/health", timeout=3)
        assert r.status_code == 200
        print("  Server is healthy. Running tests...\n")
    except Exception:
        print("  ❌ Server not reachable at port 8000. Start backend first.")
        sys.exit(1)

    tests = [
        ("GET  /", test_root),
        ("GET  /api/health", test_health),
        ("POST /api/analyze — basic", test_analyze_basic),
        ("POST /api/analyze — response structure", test_analyze_response_structure),
        ("POST /api/analyze — task fields", test_analyze_task_fields),
        ("POST /api/analyze — recommendation fields", test_analyze_recommendation_fields),
        ("POST /api/analyze — options structure", test_analyze_options_structure),
        ("POST /api/analyze — resources + availability", test_analyze_resources_have_availability),
        ("POST /api/analyze — pipeline telemetry", test_analyze_pipeline_telemetry),
        ("POST /api/analyze — empty description (422)", test_analyze_empty_description),
        ("POST /api/analyze — with constraints", test_analyze_with_constraints),
        ("POST /api/execute — CPU", test_execute_cpu),
        ("POST /api/execute — GPU", test_execute_gpu),
        ("POST /api/execute — Cloud", test_execute_cloud),
        ("POST /api/execute — auto resource", test_execute_auto_resource),
        ("POST /api/compare", test_compare),
        ("GET  /api/task/{id}", test_get_task),
        ("GET  /api/task/{id} — 404", test_get_task_not_found),
        ("GET  /api/tasks", test_list_tasks),
        ("GET  /api/colab-link", test_colab_link),
        ("GET  /api/learning/stats", test_learning_stats),
        ("GET  /api/learning/bias/{type}", test_learning_bias),
        ("GET  /api/pipeline-info", test_pipeline_info),
        ("POST /api/analyze — INR pricing", test_inr_pricing),
    ]

    for name, fn in tests:
        test(name, fn)

    print(f"\n{'='*60}")
    print(f"  Results: {PASSED} passed, {FAILED} failed, {PASSED + FAILED} total")
    print(f"{'='*60}\n")

    if FAILED > 0:
        print("  Failed tests:")
        for entry in RESULTS:
            if entry[0] == "FAIL":
                print(f"    ❌ {entry[1]}: {entry[2]}")
        print()

    sys.exit(1 if FAILED else 0)
