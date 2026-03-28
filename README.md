# Saarthi Compute

**AI-Powered Heterogeneous Execution & Scheduling System for the Next Billion**

Saarthi Compute is an intelligent orchestration system that analyzes computational workloads, decides the optimal execution environment (CPU, GPU, or Cloud), and runs them — providing real-time feedback, cost estimation, and performance insights.

Built for the **"Build for the Next Billion"** hackathon theme: real problems, real solutions for underserved communities.

## Why This Matters

Billions of users globally face:
- **Low-end devices** (no GPU, limited RAM)
- **Expensive or unreliable internet**
- **High sensitivity to cloud costs** — every rupee matters
- **Lack of technical expertise** in systems optimization

Saarthi breaks the assumption that users have high-end hardware, stable connectivity, and deep systems knowledge.

## Architecture

```
User Input → Task Analyzer → Weighted Scoring Model → Async Scheduler → Workers → Metrics
                                    ↓                        ↓
                              AI Explainer               CPU / GPU / Cloud
                              Exa + Apify Resources      (local-first)
                              Convex (real-time)
```

**Key design decisions:**
- **Local-first**: CPU worker always works offline, zero cost
- **Weighted scoring model**: Multi-objective optimization (time, cost, energy) with user-tunable weights — not just if/else rules
- **Convex PRIMARY store**: Real-time task lifecycle tracking. In-memory dict is the crash-safety fallback.
- **Real CUDA detection**: GPU worker honestly reports whether it's using real CUDA, Apple MPS, or multiprocessing simulation
- **INR pricing**: All costs shown in both USD and ₹ INR for accessibility
- **Progressive disclosure**: Mobbin-inspired UX — summary first, expandable detail

## Quick Start

### Backend

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd api && python main.py
```

Server runs at http://localhost:8000

### Frontend

```bash
cd frontend-app
npm install
npm run dev
```

Dashboard at http://localhost:5173

### Convex (Primary real-time store)

```bash
npx convex dev
```

Set `CONVEX_URL` and `VITE_CONVEX_URL` in `.env` after deployment. The system works fully without it (in-memory fallback), but judges will see real-time reactivity across browser tabs when Convex is configured.

### API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/api/analyze` | POST | Analyze task + weighted recommendation with INR pricing |
| `/api/execute` | POST | Execute on specified worker |
| `/api/compare` | POST | Run on all workers, compare results (INR + USD) |
| `/api/task/{id}` | GET | Task status from in-memory store |
| `/api/health` | GET | Health check + GPU detection + API status |
| `/api/colab-link` | GET | Generate Colab notebook link |

## Sponsor Tool Integration Table

| Tool | How Used | File / Location |
|---|---|---|
| **Cursor** | Entire codebase generated and debugged using Cursor AI agent | All files — development workflow |
| **Convex** | PRIMARY real-time task store — schema, mutations, queries; enables multi-tab live updates | `convex/schema.ts`, `convex/tasks.ts`, `backend/services/convex_client.py`, `frontend-app/src/hooks/useTask.ts` |
| **Exa** | Semantic search for free compute resources matching the user's task description | `backend/services/resource_fetcher.py` → `_fetch_exa_resources()` |
| **Apify** | Live web-scraper actor fetching current free GPU availability from Kaggle/Colab | `backend/services/resource_fetcher.py` → `_fetch_apify_resources()` |
| **v0** | UI component generation inspiration for dashboard cards and layout | `frontend-app/src/components/DecisionCard.tsx`, `TaskInput.tsx` |
| **Mobbin** | Progressive disclosure pattern applied to DecisionCard — summary first, expandable detail | `frontend-app/src/components/DecisionCard.tsx` (see comment: `// Pattern: Progressive disclosure — Mobbin fintech dashboard reference`) |
| **OpenAI** | AI explanation generation for task recommendations (with template fallback) | `backend/services/ai_explainer.py` → `_openai_explanation()` |

## Demo Flow

1. Open dashboard — describe a computation task in plain language
2. Saarthi analyzes complexity, parallelizability, and data size
3. Weighted scoring model recommends optimal resource (CPU/GPU/Cloud)
4. **Progressive disclosure**: See summary recommendation; click to expand full scores
5. View estimated time, cost (**₹ INR + $USD**), and energy for each option
6. **GPU honesty badge**: See whether GPU is real CUDA or simulated + Colab link
7. Adjust priority weights live (speed vs cost vs energy)
8. Execute & Compare — run on all workers and see real metrics
9. Browse free compute resources (**Live badge** when Apify/Exa data is fresh)
10. **Two-tab demo**: Open two browser tabs — both show task lifecycle updates via Convex

## Project Structure

```
saarthi-compute/
├── backend/
│   ├── api/main.py              # FastAPI server (Convex primary, in-memory fallback)
│   ├── services/
│   │   ├── task_analyzer.py     # Workload characterization
│   │   ├── decision_engine.py   # Weighted scoring model
│   │   ├── scheduler.py         # Async scheduler + in-memory store
│   │   ├── convex_client.py     # Convex HTTP client (primary store writes)
│   │   ├── resource_fetcher.py  # Apify + Exa + static fallback
│   │   └── ai_explainer.py      # OpenAI + template explanations (INR)
│   └── workers/
│       ├── cpu_worker.py        # Local CPU (always works)
│       ├── gpu_worker.py        # CUDA / MPS / multiprocessing + Colab link
│       └── cloud_worker.py      # Simulated cloud with latency
├── frontend-app/                # React + Vite + Tailwind
│   └── src/
│       ├── components/
│       │   ├── DecisionCard.tsx  # Progressive disclosure (Mobbin pattern)
│       │   ├── ComparisonChart.tsx # INR + USD bars
│       │   ├── ExecutePanel.tsx  # Live execution with INR
│       │   ├── ResourceList.tsx  # Live badge (Apify/Exa)
│       │   └── TaskStatus.tsx    # Lifecycle tracker
│       ├── hooks/useTask.ts     # Convex real-time hook
│       └── lib/
│           ├── api.ts           # API client
│           └── currency.ts      # USD ↔ INR formatter
├── convex/                      # Primary real-time store
│   ├── schema.ts
│   └── tasks.ts
└── README.md
```

## License

MIT
