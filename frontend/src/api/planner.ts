/** Day planner: a to-do list per date. */
import { call } from "./client"
import type { PlanDay, PlanTask, TaskPriority } from "./types"

export interface PlanTaskInput {
	title: string
	notes: string
	start_time: string | null
	priority: TaskPriority
	plan_date: string
	is_done: boolean
}

export const getPlanDay = (date?: string) => call<PlanDay>("planner.get_day", { date })
export const savePlanTask = (data: Partial<PlanTaskInput>, name?: string) =>
	call<PlanTask>("planner.save_task", { data, name }, { method: "POST" })
export const setPlanTaskDone = (name: string, done: boolean) =>
	call<PlanTask>("planner.set_done", { name, done: done ? 1 : 0 }, { method: "POST" })
export const movePlanTasks = (names: string[], date: string) =>
	call<{ moved: number; date: string }>("planner.move_tasks", { names, date }, { method: "POST" })
export const deletePlanTask = (name: string) => call<{ ok: boolean }>("planner.delete_task", { name }, { method: "POST" })
