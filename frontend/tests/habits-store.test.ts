import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"

import type { TodayHabit, TodayView } from "@/api/types"

vi.mock("@/api/habits", () => ({
	completeHabit: vi.fn(),
	uncompleteHabit: vi.fn(),
	getToday: vi.fn(),
}))

import * as api from "@/api/habits"
import { describeSchedule, describeTarget } from "@/lib/describe"
import { online } from "@/lib/pwa"
import { useHabits } from "@/stores/habits"
import { useSync } from "@/stores/sync"
import { useToast } from "@/stores/toast"

function habit(over: Partial<TodayHabit> = {}): TodayHabit {
	return {
		name: "h1", habit_name: "Read", icon: "book-open", color: "#7657F6", habit_type: "Build", frequency: "Daily",
		weekdays: [], time_of_day: "Anytime", daily_target: 1, target_unit: "times", difficulty: "Medium",
		reminder_enabled: 0, status: "Active", sort_order: 1, current_streak: 2, longest_streak: 5, total_completions: 9,
		last_completed_on: null, category_info: null, completion: null, ...over,
	} as TodayHabit
}

function view(h: TodayHabit): TodayView {
	return {
		date: "2026-11-22", today: "2026-11-22", habits: [h],
		summary: { total: 1, completed: 0, remaining: 1, percent: 0, active_habits: 1 },
		streak: { current: 2, longest: 5, total_completions: 9 }, xp: 0, level: 1,
		week: [{ date: "2026-11-22", weekday: "Sun", scheduled: 1, completed: 0, percent: 0, is_today: true, is_future: false }],
	}
}

const flush = () => new Promise((r) => setTimeout(r, 0))

describe("optimistic check-ins", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		vi.mocked(api.completeHabit).mockReset()
		vi.mocked(api.getToday).mockReset()
		online.value = true
	})

	it("shows done at once and then adopts the server's numbers", async () => {
		const store = useHabits()
		store.today = view(habit())
		vi.mocked(api.completeHabit).mockResolvedValue({
			date: "2026-11-22", habit: "h1", completion: { value: 1, target: 1, status: "Completed" },
			stats: { current_streak: 3, longest_streak: 5, total_completions: 10, status: "Active" },
			streak: { current: 3, longest: 5, total_completions: 10 },
			xp: { xp: 40, level: 1, level_start: 0, next_level_at: 100, progress: 40 },
			celebrations: { achievements: [], challenges: [] },
		})
		const item = store.today.habits[0]!
		expect(store.toggle(item)).toBe(true)
		expect(item.completion?.status).toBe("Completed")
		expect(store.today.summary.percent).toBe(100)
		await flush()
		expect(api.completeHabit).toHaveBeenCalledWith("h1", { date: "2026-11-22", value: 1 })
		expect(store.today.habits[0]!.current_streak).toBe(3)
		expect(store.today.streak.current).toBe(3)
	})

	it("rolls back and tells the user when saving fails", async () => {
		const store = useHabits()
		store.today = view(habit())
		vi.mocked(api.completeHabit).mockRejectedValue(new Error("Server unavailable"))
		vi.mocked(api.getToday).mockResolvedValue(view(habit()))
		const item = store.today.habits[0]!
		store.toggle(item)
		await flush()
		await flush()
		expect(store.today!.habits[0]!.completion).toBeNull()
		expect(store.today!.summary.completed).toBe(0)
		expect(useToast().items[0]?.tone).toBe("error")
	})

	it("counts up for numeric targets and marks partial", async () => {
		const store = useHabits()
		store.today = view(habit({ daily_target: 3, target_unit: "glasses" }))
		vi.mocked(api.completeHabit).mockReturnValue(new Promise(() => undefined))
		const item = store.today.habits[0]!
		expect(store.toggle(item)).toBe(false)
		expect(item.completion).toMatchObject({ value: 1, status: "Partial" })
		store.toggle(item)
		expect(store.toggle(item)).toBe(true)
		expect(item.completion).toMatchObject({ value: 3, status: "Completed" })
	})

	it("offline: keeps the tap on this device, marked as waiting, without calling the server", async () => {
		document.cookie = "user_id=amy%40example.com"
		const store = useHabits()
		store.today = view(habit())
		online.value = false
		expect(store.toggle(store.today.habits[0]!)).toBe(true)
		await flush()
		expect(store.today.habits[0]!.completion?.status).toBe("Completed")
		expect(api.completeHabit).not.toHaveBeenCalled()
		expect(useSync().isPending("h1", "2026-11-22")).toBe(true)
	})
})

describe("describe", () => {
	it("schedules", () => {
		expect(describeSchedule({ frequency: "Daily", weekdays: [], habit_type: "Build" })).toBe("Every day")
		expect(describeSchedule({ frequency: "Specific Days", weekdays: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"], habit_type: "Build" })).toBe("Weekdays")
		expect(describeSchedule({ frequency: "Specific Days", weekdays: ["Monday", "Friday"], habit_type: "Build" })).toBe("Mon, Fri")
		expect(describeSchedule({ frequency: "Every N Days", weekdays: [], interval_days: 3, habit_type: "Build" })).toBe("Every 3 days")
	})
	it("targets", () => {
		expect(describeTarget({ habit_type: "Build", daily_target: 10, target_unit: "pages" })).toBe("10 pages a day")
		expect(describeTarget({ habit_type: "Break", daily_target: 1, target_unit: "day" })).toBe("Resist each day")
		expect(describeTarget({ habit_type: "Build", daily_target: 1, target_unit: "times" })).toBe("Once a day")
	})
})

import { addDays, monthGrid, weekStart } from "@/lib/dates"
import { heatColor, HEAT_LIGHT } from "@/lib/heat"

describe("calendar dates", () => {
	it("weeks start on the chosen day", () => {
		expect(weekStart("2026-11-22", "Monday")).toBe("2026-11-16") // Sunday -> previous Monday
		expect(weekStart("2026-11-22", "Sunday")).toBe("2026-11-22")
	})
	it("month grid is six whole weeks", () => {
		const g = monthGrid("2026-11-22", "Monday")
		expect(g.start).toBe("2026-10-26")
		expect(addDays(g.start, 41)).toBe(g.end)
		expect(g.month).toBe(10)
	})
	it("heat ramp", () => {
		expect(heatColor(100, false)).toBe(HEAT_LIGHT[4])
		expect(heatColor(0, false)).toBe(HEAT_LIGHT[0])
		expect(heatColor(null, false)).not.toBe(HEAT_LIGHT[0])
	})
})

describe("dayPeriod", () => {
	it("splits the day into morning, afternoon, evening and night", async () => {
		const { dayPeriod } = await import("@/lib/dates")
		const at = (h: number) => dayPeriod(new Date(2026, 10, 24, h, 30))
		expect([at(4), at(5), at(11), at(12), at(16), at(17), at(20), at(21), at(23)]).toEqual([
			"Night", "Morning", "Morning", "Afternoon", "Afternoon", "Evening", "Evening", "Night", "Night",
		])
	})
})
