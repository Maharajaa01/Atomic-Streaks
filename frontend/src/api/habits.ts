import { useCelebrations } from "@/stores/celebrations"

import { call } from "./client"
import type { Category, CheckInResult, Habit, HabitInput, HabitStatus, TodayView } from "./types"

export const getToday = (date?: string) => call<TodayView>("habit.get_today_habits", { date })
export const getHabits = (status?: "archived" | "all") => call<Habit[]>("habit.get_habits", { status })
export const getHabit = (name: string) => call<Habit>("habit.get_habit", { name })
export const createHabit = (data: Partial<HabitInput>) => call<Habit>("habit.create_habit", { data }, { method: "POST" })
export const updateHabit = (name: string, data: Partial<HabitInput>) =>
	call<Habit>("habit.update_habit", { name, data }, { method: "POST" })
export const setHabitStatus = (name: string, status: HabitStatus) =>
	call<Habit>("habit.set_habit_status", { name, status }, { method: "POST" })
export const deleteHabit = (name: string) => call<{ ok: boolean }>("habit.delete_habit", { name }, { method: "POST" })
export const reorderHabits = (names: string[]) => call<{ ok: boolean }>("habit.reorder_habits", { names }, { method: "POST" })

/** Every check-in answer carries new XP and any rewards earned; pass them on to be celebrated. */
function celebrate(res: CheckInResult): CheckInResult {
	useCelebrations().ingest(res.celebrations, res.xp)
	return res
}

export interface CheckInOptions {
	date?: string
	value?: number
	client_id?: string
	source?: "App" | "Offline" | "Routine"
	/** when the action was queued offline (epoch ms); a newer server change then wins */
	queued_at?: number
}

export const completeHabit = (habit: string, opts: CheckInOptions = {}) =>
	call<CheckInResult>("habit.complete_habit", { habit, ...opts }, { method: "POST" }).then(celebrate)
export const uncompleteHabit = (habit: string, date?: string, queued_at?: number) =>
	call<CheckInResult>("habit.uncomplete_habit", { habit, date, queued_at }, { method: "POST" }).then(celebrate)

export const getCategories = () => call<Category[]>("habit.get_categories")
export const createCategory = (label: string, icon: string, color: string) =>
	call<Category>("habit.create_category", { label, icon, color }, { method: "POST" })
export const deleteCategory = (name: string) => call<{ ok: boolean }>("habit.delete_category", { name }, { method: "POST" })

export const updateProfile = (data: Record<string, unknown>) =>
	call<Record<string, unknown>>("profile.update_profile", { data }, { method: "POST" })
