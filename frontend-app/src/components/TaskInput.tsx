import { useState } from "react";

interface Props {
  onSubmit: (data: {
    task_description: string;
    budget_usd: number;
    prefer_offline: boolean;
    time_weight: number;
    cost_weight: number;
    energy_weight: number;
  }) => void;
  loading: boolean;
}

const EXAMPLES = [
  "Matrix multiplication of two 1000x1000 matrices",
  "Train sentiment model on 10,000 news articles",
  "Simple sum of 100 numbers",
  "Image processing — resize and filter 1000 photos",
  "Sort and aggregate 50,000 data rows",
];

export default function TaskInput({ onSubmit, loading }: Props) {
  const [desc, setDesc] = useState("");
  const [budget, setBudget] = useState(5);
  const [offline, setOffline] = useState(false);
  const [timeW, setTimeW] = useState(0.4);
  const [costW, setCostW] = useState(0.35);
  const [energyW, setEnergyW] = useState(0.25);
  const [showAdvanced, setShowAdvanced] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!desc.trim()) return;
    onSubmit({
      task_description: desc,
      budget_usd: budget,
      prefer_offline: offline,
      time_weight: timeW,
      cost_weight: costW,
      energy_weight: energyW,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="w-full max-w-2xl mx-auto">
      <div className="bg-white rounded-2xl shadow-lg border border-gray-100 p-6 space-y-5">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Describe your computation task
          </label>
          <textarea
            className="w-full px-4 py-3 border border-gray-200 rounded-xl text-base
                       focus:ring-2 focus:ring-indigo-500 focus:border-transparent
                       placeholder-gray-400 resize-none"
            rows={3}
            placeholder="e.g. Train a BERT model on 10,000 Kashmiri news articles..."
            value={desc}
            onChange={(e) => setDesc(e.target.value)}
          />
        </div>

        <div className="flex flex-wrap gap-2">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              type="button"
              onClick={() => setDesc(ex)}
              className="text-xs px-3 py-1.5 bg-gray-50 hover:bg-indigo-50
                         text-gray-600 hover:text-indigo-700 rounded-full
                         border border-gray-200 hover:border-indigo-200
                         transition-colors"
            >
              {ex.length > 40 ? ex.slice(0, 40) + "..." : ex}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={offline}
              onChange={(e) => setOffline(e.target.checked)}
              className="w-4 h-4 text-indigo-600 rounded"
            />
            <span className="text-sm text-gray-600">Prefer offline execution</span>
          </label>

          <div className="flex items-center gap-2 ml-auto">
            <span className="text-sm text-gray-500">Budget:</span>
            <span className="text-sm font-medium w-12 text-right">${budget}</span>
            <input
              type="range" min={0} max={20} step={0.5}
              value={budget} onChange={(e) => setBudget(Number(e.target.value))}
              className="w-24 accent-indigo-600"
            />
          </div>
        </div>

        <button
          type="button"
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="text-xs text-indigo-600 hover:text-indigo-800"
        >
          {showAdvanced ? "Hide" : "Show"} priority weights
        </button>

        {showAdvanced && (
          <div className="grid grid-cols-3 gap-4 p-3 bg-gray-50 rounded-xl">
            <WeightSlider label="Speed" value={timeW} onChange={setTimeW} color="blue" />
            <WeightSlider label="Cost" value={costW} onChange={setCostW} color="green" />
            <WeightSlider label="Energy" value={energyW} onChange={setEnergyW} color="amber" />
          </div>
        )}

        <button
          type="submit"
          disabled={loading || !desc.trim()}
          className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white
                     font-medium rounded-xl transition-colors disabled:opacity-50
                     disabled:cursor-not-allowed text-base"
        >
          {loading ? "Analyzing..." : "Analyze Task"}
        </button>
      </div>
    </form>
  );
}

function WeightSlider({
  label, value, onChange, color,
}: {
  label: string; value: number; onChange: (v: number) => void; color: string;
}) {
  return (
    <div className="text-center">
      <label className="text-xs font-medium text-gray-500 block mb-1">{label}</label>
      <input
        type="range" min={0} max={1} step={0.05}
        value={value} onChange={(e) => onChange(Number(e.target.value))}
        className={`w-full accent-${color}-500`}
      />
      <span className="text-xs text-gray-400">{(value * 100).toFixed(0)}%</span>
    </div>
  );
}
