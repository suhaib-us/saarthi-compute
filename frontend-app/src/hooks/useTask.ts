/**
 * useTask — Convex-first real-time task hook.
 *
 * When VITE_CONVEX_URL is set, polls Convex HTTP API for real-time updates.
 * Otherwise, falls back to polling the FastAPI /api/task endpoint.
 * Stops polling once the task reaches a terminal state (completed/failed).
 */

import { useEffect, useState, useRef } from "react";

const CONVEX_URL = import.meta.env.VITE_CONVEX_URL as string | undefined;

interface ConvexTask {
  _id: string;
  description: string;
  status: string;
  recommended_resource: string;
  reasoning: string;
  explanation?: string;
  options?: unknown[];
  metrics?: {
    cpu_time: number;
    cpu_cost: number;
    cpu_energy: number;
    gpu_time: number;
    gpu_cost: number;
    gpu_energy: number;
    cloud_time: number;
    cloud_cost: number;
    cloud_energy: number;
  };
  result_summary?: string;
  created_at: number;
  completed_at?: number;
}

const TERMINAL_STATES = ["completed", "failed"];

export function useTask(
  convexId: string | null,
  fallbackId: string | null,
) {
  const [task, setTask] = useState<ConvexTask | null>(null);
  const [source, setSource] = useState<"convex" | "rest" | null>(null);
  const stoppedRef = useRef(false);

  useEffect(() => {
    stoppedRef.current = false;

    if (convexId && CONVEX_URL && !CONVEX_URL.includes("your_")) {
      let alive = true;

      const poll = async () => {
        if (stoppedRef.current) return;
        try {
          const res = await fetch(`${CONVEX_URL}/api/query`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              path: "tasks:getTask",
              args: { taskId: convexId },
            }),
          });
          if (res.ok && alive) {
            const data = await res.json();
            if (data.value) {
              setTask(data.value);
              setSource("convex");
              if (TERMINAL_STATES.includes(data.value.status)) {
                stoppedRef.current = true;
              }
            }
          }
        } catch {
          // Convex unreachable
        }
      };

      poll();
      const interval = setInterval(() => {
        if (!stoppedRef.current) poll();
      }, 500);

      return () => {
        alive = false;
        clearInterval(interval);
      };
    }

    if (fallbackId) {
      let alive = true;

      const poll = async () => {
        if (stoppedRef.current) return;
        try {
          const res = await fetch(`/api/task/${fallbackId}`);
          if (res.ok && alive) {
            const data = await res.json();
            const status = data.state;
            setTask({
              _id: data.task_id,
              description: data.description,
              status,
              recommended_resource: data.recommended_resource,
              reasoning: data.reasoning || "",
              created_at: data.created_at,
              completed_at: data.completed_at,
            });
            setSource("rest");
            if (TERMINAL_STATES.includes(status)) {
              stoppedRef.current = true;
            }
          }
        } catch {
          // silent
        }
      };

      poll();
      const interval = setInterval(() => {
        if (!stoppedRef.current) poll();
      }, 1000);

      return () => {
        alive = false;
        clearInterval(interval);
      };
    }
  }, [convexId, fallbackId]);

  return { task, source, isConvexConnected: source === "convex" };
}
