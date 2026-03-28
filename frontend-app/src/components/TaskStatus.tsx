interface Props {
  taskId: string | null;
  state: string;
}

const STEPS = ["queued", "scheduled", "running", "completed"];

export default function TaskStatus({ taskId, state }: Props) {
  if (!taskId) return null;

  const currentIdx = STEPS.indexOf(state);

  return (
    <div className="w-full max-w-2xl mx-auto bg-white rounded-2xl shadow border border-gray-100 p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-gray-500">Task Lifecycle</h3>
        <span className="text-xs text-gray-400 font-mono">ID: {taskId}</span>
      </div>
      <div className="flex items-center gap-1">
        {STEPS.map((step, i) => {
          const isDone = i <= currentIdx;
          const isCurrent = i === currentIdx;

          return (
            <div key={step} className="flex-1 flex items-center">
              <div className="flex flex-col items-center w-full">
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-medium transition-all
                    ${isDone
                      ? "bg-indigo-600 text-white"
                      : "bg-gray-100 text-gray-400"
                    }
                    ${isCurrent ? "ring-2 ring-indigo-300 ring-offset-2" : ""}
                  `}
                >
                  {isDone && i < currentIdx ? "✓" : i + 1}
                </div>
                <span className={`text-xs mt-1 capitalize ${isDone ? "text-indigo-600 font-medium" : "text-gray-400"}`}>
                  {step}
                </span>
              </div>
              {i < STEPS.length - 1 && (
                <div className={`h-0.5 flex-1 mx-1 ${i < currentIdx ? "bg-indigo-600" : "bg-gray-200"}`} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
