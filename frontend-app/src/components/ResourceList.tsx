import type { ComputeResource } from "../lib/api";

interface Props {
  resources: ComputeResource[];
}

export default function ResourceList({ resources }: Props) {
  if (!resources.length) return null;

  const hasLiveData = resources.some((r) => r.source === "apify" || r.source === "exa");

  return (
    <div className="w-full max-w-2xl mx-auto bg-white rounded-2xl shadow border border-gray-100 p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-gray-500">Free Compute Resources</h3>
        {hasLiveData && (
          <span className="inline-flex items-center gap-1 text-xs font-medium bg-emerald-50 text-emerald-700 px-2 py-0.5 rounded-full border border-emerald-200">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            Live
          </span>
        )}
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {resources.map((r, i) => (
          <a
            key={i}
            href={r.url || "#"}
            target="_blank"
            rel="noopener noreferrer"
            className="block p-3 rounded-xl border border-gray-100 hover:border-indigo-200
                       hover:bg-indigo-50/50 transition-colors group"
          >
            <div className="flex items-center gap-2 mb-1">
              <h4 className="text-sm font-semibold text-gray-900 group-hover:text-indigo-700">
                {r.name}
              </h4>
              {r.gpu_hours_free && r.gpu_hours_free !== "N/A" && (
                <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded-full">
                  {r.gpu_hours_free}
                </span>
              )}
              {(r.source === "apify" || r.source === "exa") && (
                <span className="text-xs bg-blue-50 text-blue-600 px-1.5 py-0.5 rounded-full">
                  {r.source === "apify" ? "Live" : "Exa"}
                </span>
              )}
            </div>
            <p className="text-xs text-gray-500 mb-1">{r.description}</p>
            <p className="text-xs text-gray-400">Best for: {r.best_for}</p>
          </a>
        ))}
      </div>
    </div>
  );
}
