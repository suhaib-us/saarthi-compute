import { useState } from "react";
import { compareTasks, type CompareResponse } from "../lib/api";
import { formatCost } from "../lib/currency";

interface Props {
  taskDescription: string;
}

export default function ExecutePanel({ taskDescription }: Props) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<CompareResponse | null>(null);

  const handleRun = async () => {
    setLoading(true);
    try {
      const res = await compareTasks(taskDescription, 500);
      setResult(res);
    } catch {
      // silently fail
    } finally {
      setLoading(false);
    }
  };

  if (!result) {
    return (
      <div className="w-full max-w-2xl mx-auto">
        <button
          onClick={handleRun}
          disabled={loading}
          className="w-full py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-medium
                     rounded-xl transition-colors disabled:opacity-50"
        >
          {loading ? "Running on all workers..." : "Execute & Compare (CPU vs GPU vs Cloud)"}
        </button>
      </div>
    );
  }

  return (
    <div className="w-full max-w-2xl mx-auto bg-white rounded-2xl shadow-lg border border-gray-100 p-5 space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-500">Real Execution Results</h3>
        <span className="text-xs text-emerald-600 font-medium bg-emerald-50 px-2 py-1 rounded-full">
          Live data
        </span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {result.comparisons.map((comp) => {
          const cost = formatCost(comp.cost_usd);
          return (
            <div
              key={comp.resource}
              className="rounded-xl border border-gray-100 p-4 bg-gray-50 space-y-2"
            >
              <div className="flex items-center gap-2">
                <span className="text-lg">
                  {comp.resource === "cpu" ? "🖥️" : comp.resource === "gpu" ? "🚀" : "☁️"}
                </span>
                <h4 className="font-semibold text-sm text-gray-900">{comp.resource.toUpperCase()}</h4>
              </div>

              <div className="space-y-1 text-xs">
                <div className="flex justify-between">
                  <span className="text-gray-500">Time</span>
                  <span className="font-mono font-medium">{comp.time_seconds.toFixed(4)}s</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Cost</span>
                  <span className={`font-medium ${comp.cost_usd === 0 ? "text-green-700" : "text-orange-600"}`}>
                    {cost.display}
                  </span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-500">Energy</span>
                  <span className="font-medium">{comp.energy_wh.toFixed(4)} Wh</span>
                </div>
              </div>

              <p className="text-xs text-gray-500 pt-1 border-t border-gray-200">
                {comp.output_summary.length > 80
                  ? comp.output_summary.slice(0, 80) + "..."
                  : comp.output_summary}
              </p>
            </div>
          );
        })}
      </div>

      {result.savings_summary && (
        <p className="text-sm text-emerald-700 bg-emerald-50 px-3 py-2 rounded-lg">
          {result.savings_summary}
        </p>
      )}

      <button
        onClick={handleRun}
        disabled={loading}
        className="w-full py-2 text-sm bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium
                   rounded-lg transition-colors disabled:opacity-50"
      >
        {loading ? "Re-running..." : "Run Again"}
      </button>
    </div>
  );
}
