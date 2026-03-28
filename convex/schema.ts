import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  tasks: defineTable({
    description: v.string(),
    status: v.union(
      v.literal("queued"),
      v.literal("scheduled"),
      v.literal("running"),
      v.literal("completed"),
      v.literal("failed")
    ),
    recommended_resource: v.string(),
    reasoning: v.string(),
    explanation: v.optional(v.string()),
    options: v.optional(v.any()),
    metrics: v.optional(
      v.object({
        cpu_time: v.number(),
        cpu_cost: v.number(),
        cpu_energy: v.number(),
        gpu_time: v.number(),
        gpu_cost: v.number(),
        gpu_energy: v.number(),
        cloud_time: v.number(),
        cloud_cost: v.number(),
        cloud_energy: v.number(),
      })
    ),
    result_summary: v.optional(v.string()),
    created_at: v.number(),
    completed_at: v.optional(v.number()),
  }).index("by_created_at", ["created_at"]),
});
