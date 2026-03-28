import { mutation, query } from "./_generated/server";
import { v } from "convex/values";

export const createTask = mutation({
  args: {
    description: v.string(),
    recommended_resource: v.string(),
    reasoning: v.string(),
    explanation: v.optional(v.string()),
    options: v.optional(v.any()),
  },
  handler: async (ctx, args) => {
    const taskId = await ctx.db.insert("tasks", {
      description: args.description,
      status: "queued",
      recommended_resource: args.recommended_resource,
      reasoning: args.reasoning,
      explanation: args.explanation,
      options: args.options,
      created_at: Date.now(),
    });
    return taskId;
  },
});

export const updateStatus = mutation({
  args: {
    taskId: v.id("tasks"),
    status: v.union(
      v.literal("queued"),
      v.literal("scheduled"),
      v.literal("running"),
      v.literal("completed"),
      v.literal("failed")
    ),
  },
  handler: async (ctx, args) => {
    const patch: Record<string, unknown> = { status: args.status };
    if (args.status === "completed" || args.status === "failed") {
      patch.completed_at = Date.now();
    }
    await ctx.db.patch(args.taskId, patch);
  },
});

export const updateMetrics = mutation({
  args: {
    taskId: v.id("tasks"),
    metrics: v.object({
      cpu_time: v.number(),
      cpu_cost: v.number(),
      cpu_energy: v.number(),
      gpu_time: v.number(),
      gpu_cost: v.number(),
      gpu_energy: v.number(),
      cloud_time: v.number(),
      cloud_cost: v.number(),
      cloud_energy: v.number(),
    }),
    result_summary: v.string(),
  },
  handler: async (ctx, args) => {
    await ctx.db.patch(args.taskId, {
      status: "completed",
      metrics: args.metrics,
      result_summary: args.result_summary,
      completed_at: Date.now(),
    });
  },
});

export const getTask = query({
  args: { taskId: v.id("tasks") },
  handler: async (ctx, args) => {
    return await ctx.db.get(args.taskId);
  },
});

export const listTasks = query({
  args: { limit: v.optional(v.number()) },
  handler: async (ctx, args) => {
    const limit = args.limit ?? 20;
    return await ctx.db
      .query("tasks")
      .withIndex("by_created_at")
      .order("desc")
      .take(limit);
  },
});
