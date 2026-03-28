// Pattern: Progressive disclosure — Mobbin fintech dashboard reference
// Summary view first (icon + recommendation + one-line reason),
// expandable to show full scores, comparison, and action steps.

import { useState } from "react";
import type { AnalyzeResponse, ExecutionOption, GPUInfo } from "../lib/api";
import { formatCost } from "../lib/currency";

const ICONS: Record<string, string> = {
  cpu: "🖥️",
  gpu: "🚀",
  cloud: "☁️",
};

const BADGE: Record<string, string> = {
  cpu: "bg-blue-100 text-blue-800",
  gpu: "bg-purple-100 text-purple-800",
  cloud: "bg-sky-100 text-sky-800",
};

interface Props {
  data: AnalyzeResponse;
}

export default function DecisionCard({ data }: Props) {
  const [expanded, setExpanded] = useState(false);
  const rec = data.recommendation;

  return (
    <div className="w-full max-w-2xl mx-auto space-y-4">
      {/* Summary — always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full bg-white rounded-2xl shadow-lg border border-gray-100 p-6
                   hover:shadow-xl transition-shadow text-left"
      >
        <div className="flex items-start gap-4">
          <span className="text-4xl">{ICONS[rec.resource] || "⚡"}</span>
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-1">
              <h2 className="text-lg font-semibold text-gray-900">
                Recommended: {rec.resource.toUpperCase()}
              </h2>
              <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${BADGE[rec.resource]}`}>
                Best match
              </span>
            </div>
            <p className="text-sm text-gray-600 leading-relaxed">{rec.reasoning}</p>
          </div>
          <span className={`text-gray-400 transition-transform ${expanded ? "rotate-180" : ""}`}>
            ▼
          </span>
        </div>
        {rec.tip && (
          <p className="text-sm text-amber-700 bg-amber-50 px-3 py-2 rounded-lg mt-3">
            {rec.tip}
          </p>
        )}
      </button>

      {/* Expanded detail — progressive disclosure */}
      {expanded && (
        <>
          {/* GPU Honesty Badge */}
          {data.gpu_info && <GPUStatusBadge gpu={data.gpu_info} colabUrl={data.colab_url} />}

          {/* AI Explanation */}
          <div className="bg-white rounded-2xl shadow border border-gray-100 p-5">
            <h3 className="text-sm font-medium text-gray-500 mb-2">AI Explanation</h3>
            <p className="text-sm text-gray-700 leading-relaxed">{data.explanation}</p>
            {data.explanation_source === "openai" && (
              <span className="inline-block text-xs text-gray-400 mt-2">Powered by OpenAI</span>
            )}
          </div>

          {/* Options comparison with INR */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {data.options.map((opt) => (
              <OptionCard key={opt.resource} option={opt} />
            ))}
          </div>

          {/* Action steps */}
          {data.action_steps.length > 0 && (
            <div className="bg-white rounded-2xl shadow border border-gray-100 p-5">
              <h3 className="text-sm font-medium text-gray-500 mb-3">What to do next</h3>
              <ol className="space-y-2">
                {data.action_steps.map((step, i) => (
                  <li key={i} className="flex gap-3 text-sm">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-indigo-100
                                   text-indigo-700 flex items-center justify-center text-xs font-medium">
                      {i + 1}
                    </span>
                    <span className="text-gray-700">{step}</span>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {/* Task details */}
          <div className="bg-white rounded-2xl shadow border border-gray-100 p-5">
            <h3 className="text-sm font-medium text-gray-500 mb-3">Task Analysis</h3>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
              <Stat label="Type" value={data.task.type.replace("_", " ")} />
              <Stat label="Complexity" value={data.task.complexity} />
              <Stat label="Data Size" value={data.task.data_size} />
              <Stat label="GPU Benefit" value={`${(data.task.gpu_benefit_score * 100).toFixed(0)}%`} />
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function GPUStatusBadge({ gpu, colabUrl }: { gpu: GPUInfo; colabUrl: string }) {
  const isReal = gpu.available;
  const label = isReal
    ? `${gpu.backend.toUpperCase()}: ${gpu.name}`
    : `Simulated: ${gpu.name}`;

  return (
    <div className="bg-white rounded-2xl shadow border border-gray-100 p-4 flex items-center justify-between gap-3">
      <div className="flex items-center gap-3">
        <span className="text-lg">🚀</span>
        <div>
          <p className="text-sm font-medium text-gray-900">GPU Status</p>
          <div className="flex items-center gap-2 mt-0.5">
            <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${
              isReal
                ? "bg-green-100 text-green-800"
                : "bg-amber-100 text-amber-800"
            }`}>
              <span className={`w-1.5 h-1.5 rounded-full ${isReal ? "bg-green-500" : "bg-amber-500"}`} />
              {label}
            </span>
          </div>
        </div>
      </div>
      {colabUrl && (
        <a
          href={colabUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs bg-indigo-600 text-white px-3 py-1.5 rounded-lg
                     hover:bg-indigo-700 transition-colors whitespace-nowrap"
        >
          Open in Colab
        </a>
      )}
    </div>
  );
}

function OptionCard({ option: opt }: { option: ExecutionOption }) {
  const cost = formatCost(opt.estimated_cost_usd);

  return (
    <div
      className={`rounded-xl border-2 p-4 transition-all ${
        opt.recommended
          ? "border-indigo-400 bg-indigo-50 shadow-md"
          : "border-gray-100 bg-white"
      }`}
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-lg">{ICONS[opt.resource] || "⚡"}</span>
        {opt.recommended && (
          <span className="text-xs bg-indigo-600 text-white px-2 py-0.5 rounded-full font-medium">
            Best
          </span>
        )}
      </div>
      <h4 className="font-semibold text-gray-900 text-sm mb-1">{opt.resource.toUpperCase()}</h4>
      <p className="text-xs text-gray-400 mb-3">Score: {opt.score.toFixed(2)}</p>

      <div className="space-y-1.5 text-xs">
        <div className="flex justify-between">
          <span className="text-gray-500">Time</span>
          <span className="font-medium">{opt.estimated_time_display}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Cost</span>
          <span className="font-medium text-green-700">{cost.display}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-gray-500">Energy</span>
          <span className="font-medium">{opt.estimated_energy_wh.toFixed(1)} Wh</span>
        </div>
      </div>

      <div className="mt-3 space-y-1">
        {opt.pros.slice(0, 2).map((p, i) => (
          <p key={i} className="text-xs text-green-700">+ {p}</p>
        ))}
        {opt.cons.slice(0, 1).map((c, i) => (
          <p key={i} className="text-xs text-red-600">- {c}</p>
        ))}
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-gray-50 rounded-lg p-2">
      <p className="text-xs text-gray-400">{label}</p>
      <p className="font-medium text-sm text-gray-900 capitalize">{value}</p>
    </div>
  );
}
