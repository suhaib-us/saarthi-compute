import { useState } from "react";
import TaskInput from "./components/TaskInput";
import DecisionCard from "./components/DecisionCard";
import ComparisonChart from "./components/ComparisonChart";
import ResourceList from "./components/ResourceList";
import TaskStatus from "./components/TaskStatus";
import ExecutePanel from "./components/ExecutePanel";
import { analyzeTask, type AnalyzeResponse } from "./lib/api";
import { useTask } from "./hooks/useTask";

export default function App() {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { task: convexTask, source: taskSource } = useTask(
    result?.convex_id ?? null,
    result?.task_id ?? null,
  );

  const handleSubmit = async (data: Parameters<typeof analyzeTask>[0]) => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await analyzeTask(data);
      setResult(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setLoading(false);
    }
  };

  const currentState = convexTask?.status ?? "completed";

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-indigo-50">
      {/* Header */}
      <header className="border-b border-gray-100 bg-white/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-xl font-bold text-gray-900 tracking-tight">
              Saarthi Compute
            </h1>
            <p className="text-xs text-gray-500">
              AI-powered compute advisor for the Next Billion
            </p>
          </div>
          <div className="flex items-center gap-2">
            {taskSource === "convex" && (
              <span className="text-xs px-2 py-1 bg-emerald-50 text-emerald-700 rounded-full border border-emerald-200">
                Convex live
              </span>
            )}
            <span className="text-xs px-2 py-1 bg-green-50 text-green-700 rounded-full border border-green-200">
              Local-first
            </span>
          </div>
        </div>
      </header>

      {/* Main content */}
      <main className="max-w-4xl mx-auto px-4 py-8 space-y-6">
        {!result && (
          <div className="text-center mb-6">
            <h2 className="text-2xl sm:text-3xl font-bold text-gray-900 mb-2">
              Where should your computation run?
            </h2>
            <p className="text-gray-500 max-w-lg mx-auto text-sm">
              Describe your task in plain language. Saarthi analyzes it and recommends
              the best compute option — optimizing for speed, cost, and energy.
            </p>
          </div>
        )}

        <TaskInput onSubmit={handleSubmit} loading={loading} />

        {error && (
          <div className="max-w-2xl mx-auto bg-red-50 border border-red-200 text-red-700
                          text-sm rounded-xl px-4 py-3">
            {error}
          </div>
        )}

        {result && (
          <div className="space-y-4">
            <TaskStatus taskId={result.task_id} state={currentState} />
            <DecisionCard data={result} />
            <ComparisonChart options={result.options} />
            <ExecutePanel taskDescription={result.task.input} />
            <ResourceList resources={result.resources} />
          </div>
        )}

        {/* Footer */}
        <footer className="text-center text-xs text-gray-400 py-8 space-y-1">
          <p>Built for the Next Billion — real problems, real solutions</p>
          <p>Saarthi Compute v1.0 | Powered by Cursor, Convex, Exa, Apify</p>
        </footer>
      </main>
    </div>
  );
}
