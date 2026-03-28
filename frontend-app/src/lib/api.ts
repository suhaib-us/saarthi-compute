const BASE = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : "/api";

export interface AnalyzeRequest {
  task_description: string;
  budget_usd: number;
  prefer_offline: boolean;
  time_weight: number;
  cost_weight: number;
  energy_weight: number;
}

export interface ExecutionOption {
  resource: string;
  recommended: boolean;
  score: number;
  estimated_time_seconds: number;
  estimated_time_display: string;
  estimated_cost_usd: number;
  estimated_cost_inr: number;
  estimated_energy_wh: number;
  pros: string[];
  cons: string[];
  action: string;
}

export interface ComputeResource {
  name: string;
  url: string;
  resource_type: string;
  description: string;
  gpu_hours_free: string;
  best_for: string;
  requires_signup: boolean;
  source: string;
}

export interface GPUInfo {
  available: boolean;
  backend: string;
  name: string;
  memory_mb?: number;
  cores?: number;
}

export interface AnalyzeResponse {
  success: boolean;
  task_id: string;
  convex_id: string | null;
  task: {
    input: string;
    type: string;
    complexity: string;
    data_size: string;
    memory_mb: number;
    parallelizable: boolean;
    gpu_benefit_score: number;
  };
  recommendation: {
    resource: string;
    reasoning: string;
    tip: string;
  };
  explanation: string;
  explanation_source: string;
  action_steps: string[];
  options: ExecutionOption[];
  resources: ComputeResource[];
  gpu_info: GPUInfo;
  colab_url: string;
}

export interface ExecuteResponse {
  success: boolean;
  task_id: string;
  result: {
    resource: string;
    task_type: string;
    time_seconds: number;
    cost_usd: number;
    cost_inr: number;
    energy_wh: number;
    output_summary: string;
    metadata: Record<string, unknown>;
  };
}

export interface CompareResponse {
  success: boolean;
  task_id: string;
  description: string;
  comparisons: (ExecuteResponse["result"] & { cost_inr: number })[];
  savings_summary: string;
}

export async function analyzeTask(req: AnalyzeRequest): Promise<AnalyzeResponse> {
  const res = await fetch(`${BASE}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function executeTask(
  description: string,
  resource?: string,
  matrixSize = 500,
): Promise<ExecuteResponse> {
  const res = await fetch(`${BASE}/execute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      task_description: description,
      resource,
      matrix_size: matrixSize,
    }),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function compareTasks(
  description: string,
  matrixSize = 500,
): Promise<CompareResponse> {
  const res = await fetch(`${BASE}/compare`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ task_description: description, matrix_size: matrixSize }),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}
