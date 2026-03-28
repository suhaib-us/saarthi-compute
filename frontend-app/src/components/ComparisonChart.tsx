import type { ExecutionOption } from "../lib/api";
import { formatCost } from "../lib/currency";

interface Props {
  options: ExecutionOption[];
}

const COLORS: Record<string, { bar: string; bg: string }> = {
  cpu: { bar: "bg-blue-500", bg: "bg-blue-50" },
  gpu: { bar: "bg-purple-500", bg: "bg-purple-50" },
  cloud: { bar: "bg-sky-500", bg: "bg-sky-50" },
};

export default function ComparisonChart({ options }: Props) {
  if (!options.length) return null;

  const maxTime = Math.max(...options.map((o) => o.estimated_time_seconds), 0.001);
  const maxCost = Math.max(...options.map((o) => o.estimated_cost_usd), 0.001);
  const maxEnergy = Math.max(...options.map((o) => o.estimated_energy_wh), 0.001);

  return (
    <div className="w-full max-w-2xl mx-auto bg-white rounded-2xl shadow border border-gray-100 p-5">
      <h3 className="text-sm font-medium text-gray-500 mb-4">Performance Comparison</h3>

      <div className="space-y-6">
        <MetricSection
          title="Execution Time"
          options={options}
          getValue={(o) => o.estimated_time_seconds}
          formatValue={(o) => o.estimated_time_display}
          max={maxTime}
        />
        <MetricSection
          title="Cost (USD + ₹ INR)"
          options={options}
          getValue={(o) => o.estimated_cost_usd}
          formatValue={(o) => formatCost(o.estimated_cost_usd).display}
          max={maxCost}
        />
        <MetricSection
          title="Energy"
          options={options}
          getValue={(o) => o.estimated_energy_wh}
          formatValue={(o) => `${o.estimated_energy_wh.toFixed(2)} Wh`}
          max={maxEnergy}
        />
      </div>
    </div>
  );
}

function MetricSection({
  title,
  options,
  getValue,
  formatValue,
  max,
}: {
  title: string;
  options: ExecutionOption[];
  getValue: (o: ExecutionOption) => number;
  formatValue: (o: ExecutionOption) => string;
  max: number;
}) {
  return (
    <div>
      <p className="text-xs font-medium text-gray-400 mb-2">{title}</p>
      <div className="space-y-2">
        {options.map((opt) => {
          const pct = max > 0 ? (getValue(opt) / max) * 100 : 0;
          const c = COLORS[opt.resource] || COLORS.cpu;
          const isLowest = getValue(opt) === Math.min(...options.map(getValue));

          return (
            <div key={opt.resource} className="flex items-center gap-3">
              <span className="w-12 text-xs font-medium text-gray-500 uppercase shrink-0">
                {opt.resource}
              </span>
              <div className="flex-1 h-6 bg-gray-100 rounded-full overflow-hidden relative">
                <div
                  className={`h-full rounded-full transition-all duration-700 ${c.bar} ${
                    opt.recommended ? "opacity-100" : "opacity-70"
                  }`}
                  style={{ width: `${Math.max(pct, 2)}%` }}
                />
              </div>
              <span className={`text-xs w-28 text-right shrink-0 ${
                isLowest ? "font-bold text-green-700" : "text-gray-500"
              }`}>
                {formatValue(opt)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
