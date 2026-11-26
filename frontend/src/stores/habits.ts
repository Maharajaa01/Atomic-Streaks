/**
 * Habits + today's check-ins, with optimistic updates.
 *
 * A tap changes the screen at once; the request follows. Requests for the same habit run one
 * after another (in tap order) so the last tap always wins on the server. If a request fails
 * the habit snaps back to what it was, today's view is re-synced from the server, and the
 * user is told. Nothing is ever shown as saved unless the server accepted it.
 */
import { defineStore } from "pinia"
import { computed, ref } from "vue"

import * as api from "@/api/habits"
import type { Category, Completion, Habit, HabitInput, HabitStatus, TodayHabit, TodayView } from "@/api/types"
import { ApiError, saveToCache } from "@/api/client"
import { online } from "@/lib/pwa"

import { useCelebrations } from "./celebrations"
import { useSync } from "./sync"
import { useToast } from "./toast"

export function isDone(h: TodayHabit): boolean {
	return h.completion?.status === "Completed"
}

/** Habits whose button is a single "done" toggle rather than a counter. */
export function isToggle(h: Pick<Habit, "habit_type" | "daily_target">): boolean {
	return h.habit_type !== "Build" || (h.daily_target ?? 1) <= 1
}

export const useHabits = defineStore("habits", () => {
	const toast = useToast()

	const today = ref<TodayView | null>(null)
	const todayError = ref("")
	const loadingToday = ref(false)
	const habits = ref<Habit[] | null>(null)
	const categories = ref<Category[] | null>(null)
	const busy = ref(new Set<string>())

	const queues = new Map<string, Promise<unknown>>()

	// ------------------------------------------------------------------ loading
	async function loadToday(silent = false) {
		if (!silent) loadingToday.value = true
		todayError.value = ""
		try {
			today.value = await api.getToday()
			applyPending()
		} catch (e) {
			todayError.value = (e as Error).message
		} finally {
			loadingToday.value = false
		}
	}

	async function loadHabits(status?: "archived" | "all") {
		const list = await api.getHabits(status)
		if (!status) habits.value = list
		return list
	}

	async function loadCategories(force = false) {
		if (categories.value && !force) return categories.value
		categories.value = await api.getCategories()
		return categories.value
	}

	// ------------------------------------------------------------------ offline
	/** Show check-ins still waiting in the outbox on top of what the server (or cache) said. */
	function applyPending() {
		const t = today.value
		if (!t) return
		const sync = useSync()
		for (const h of t.habits) {
			const q = sync.pending.get(`${h.name}|${t.date}`)
			if (!q) continue
			h.completion =
				q.value > 0 ? { ...(h.completion ?? {}), value: q.value, target: q.target, status: q.value >= q.target ? "Completed" : "Partial" } : null
		}
		recount()
	}

	/** Keep the saved copy of today in step, so the app shows it correctly when opened offline. */
	function cacheToday() {
		if (today.value && today.value.date === today.value.today) saveToCache("habit.get_today_habits", {}, today.value)
	}

	function queueOffline(item: TodayHabit, value: number, target: number) {
		const date = today.value?.date
		if (!date) return
		void useSync().enqueue({ habit: item.name, habit_name: item.habit_name, date, value, target })
	}

	// ------------------------------------------------------------------ summary
	function recount() {
		const t = today.value
		if (!t) return
		const completed = t.habits.filter(isDone).length
		t.summary = {
			...t.summary,
			total: t.habits.length,
			completed,
			remaining: t.habits.length - completed,
			percent: t.habits.length ? Math.round((100 * completed) / t.habits.length) : 0,
		}
		const day = t.week.find((d) => d.is_today)
		if (day && t.date === t.today) {
			day.completed = Math.min(completed, day.scheduled || completed)
			day.percent = day.scheduled ? Math.round((100 * day.completed) / day.scheduled) : 0
		}
	}

	// ------------------------------------------------------------------ check-ins
	/** Set today's value for a habit (0 = not done). Returns true when this tap completed it. */
	function setValue(item: TodayHabit, value: number): boolean {
		const target = item.completion?.target || item.daily_target || 1
		const wasDone = isDone(item)
		const snapshot = { completion: item.completion ? { ...item.completion } : null, streak: item.current_streak }

		const next: Completion | null =
			value > 0 ? { ...(item.completion ?? {}), value, target, status: value >= target ? "Completed" : "Partial" } : null
		item.completion = next
		if (!wasDone && next?.status === "Completed") item.current_streak = (item.current_streak || 0) + 1
		if (wasDone && next?.status !== "Completed") item.current_streak = Math.max((item.current_streak || 0) - 1, 0)
		recount()

		const sync = useSync()
		// offline, or this habit/day already has a queued change: queue behind it, in order
		if (!online.value || sync.isPending(item.name, today.value?.date)) {
			queueOffline(item, value, target)
			if (!online.value && !sync.count) toast.show("You're offline. This check-in will sync when you reconnect.")
			return !wasDone && next?.status === "Completed"
		}

		const date = today.value?.date
		const run = async () => {
			busy.value.add(item.name)
			try {
				const res = value > 0 ? await api.completeHabit(item.name, { date, value }) : await api.uncompleteHabit(item.name, date)
				const live = today.value?.habits.find((h) => h.name === item.name)
				if (live && queues.get(item.name) === pending) {
					// last request in line: adopt the server's numbers
					live.completion = res.completion
					live.current_streak = res.stats.current_streak
					live.longest_streak = res.stats.longest_streak
					live.total_completions = res.stats.total_completions
				}
				if (today.value) today.value.streak = res.streak
				recount()
				cacheToday()
			} catch (e) {
				if (e instanceof ApiError && e.isNetwork) {
					// the connection dropped mid-request: keep the tap and sync it later
					queueOffline(item, value, target)
					return
				}
				item.completion = snapshot.completion
				item.current_streak = snapshot.streak
				recount()
				toast.error(`Couldn't save "${item.habit_name}". ${(e as Error).message}`)
				void loadToday(true) // re-sync with what the server really has
			} finally {
				busy.value.delete(item.name)
			}
		}
		const pending: Promise<unknown> = (queues.get(item.name) ?? Promise.resolve()).then(run)
		queues.set(item.name, pending)
		void pending.finally(() => {
			if (queues.get(item.name) === pending) queues.delete(item.name)
		})
		return !wasDone && next?.status === "Completed"
	}

	function toggle(item: TodayHabit): boolean {
		const target = item.completion?.target || item.daily_target || 1
		if (isToggle(item)) return setValue(item, isDone(item) ? 0 : target)
		const current = item.completion?.value ?? 0
		return setValue(item, current >= target ? 0 : Math.min(current + 1, target))
	}

	function step(item: TodayHabit, delta: number): boolean {
		const current = item.completion?.value ?? 0
		return setValue(item, Math.max(0, current + delta))
	}

	// ------------------------------------------------------------------ habit CRUD
	function upsert(h: Habit) {
		if (!habits.value) return
		const i = habits.value.findIndex((x) => x.name === h.name)
		if (i >= 0) habits.value[i] = h
		else habits.value.push(h)
	}

	async function create(data: Partial<HabitInput>) {
		const h = await api.createHabit(data)
		upsert(h)
		void loadToday(true)
		void useCelebrations().refresh() // e.g. the "Habit Builder" badge
		return h
	}

	async function update(name: string, data: Partial<HabitInput>) {
		const h = await api.updateHabit(name, data)
		upsert(h)
		void loadToday(true)
		return h
	}

	async function setStatus(name: string, status: HabitStatus) {
		const h = await api.setHabitStatus(name, status)
		if (habits.value) {
			if (status === "Archived") habits.value = habits.value.filter((x) => x.name !== name)
			else upsert(h)
		}
		void loadToday(true)
		return h
	}

	async function remove(name: string) {
		await api.deleteHabit(name)
		if (habits.value) habits.value = habits.value.filter((x) => x.name !== name)
		void loadToday(true)
	}

	async function addCategory(label: string, icon: string, color: string) {
		const c = await api.createCategory(label, icon, color)
		categories.value = [...(categories.value ?? []), c]
		return c
	}

	const byTimeOfDay = computed(() => {
		const groups: Record<string, TodayHabit[]> = { Morning: [], Afternoon: [], Evening: [], Night: [], Anytime: [] }
		for (const h of today.value?.habits ?? []) (groups[h.time_of_day] ?? groups.Anytime!).push(h)
		return Object.entries(groups).filter(([, list]) => list.length)
	})

	return {
		today,
		todayError,
		loadingToday,
		habits,
		categories,
		busy,
		byTimeOfDay,
		loadToday,
		loadHabits,
		loadCategories,
		setValue,
		toggle,
		step,
		create,
		update,
		setStatus,
		remove,
		addCategory,
	}
})
