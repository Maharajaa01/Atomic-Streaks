import { call } from "./client"
import type { CalendarData, DayDetail, HabitHistory, Insights } from "./types"

export const getCalendar = (start: string, end: string, opts: { habit?: string; cells?: boolean } = {}) =>
	call<CalendarData>("calendar.get_calendar_data", { start, end, habit: opts.habit, cells: opts.cells ? 1 : undefined })
export const getDay = (date: string) => call<DayDetail>("calendar.get_day", { date })
export const getHabitHistory = (habit: string, days = 119) => call<HabitHistory>("calendar.get_habit_history", { habit, days })
export const getInsights = (days: 7 | 30 | 90) => call<Insights>("analytics.get_dashboard", { days })
