/** Date helpers. Dates travel as "YYYY-MM-DD" strings in the user's own timezone (set by the server). */

import type { DayPeriod } from "@/api/types"

export function parseDay(day: string): Date {
	const [y, m, d] = day.split("-").map(Number)
	return new Date(y!, (m ?? 1) - 1, d ?? 1)
}

export function formatDay(day: string, opts: Intl.DateTimeFormatOptions = { weekday: "long", day: "numeric", month: "long" }): string {
	return parseDay(day).toLocaleDateString(undefined, opts)
}

export function greeting(now = new Date()): string {
	const h = now.getHours()
	if (h < 5) return "Good evening"
	if (h < 12) return "Good morning"
	if (h < 17) return "Good afternoon"
	return "Good evening"
}

/** Which part of the day it is now: Morning 5–12, Afternoon 12–17, Evening 17–21, Night 21–5. */
export function dayPeriod(now = new Date()): DayPeriod {
	const h = now.getHours()
	if (h >= 5 && h < 12) return "Morning"
	if (h >= 12 && h < 17) return "Afternoon"
	if (h >= 17 && h < 21) return "Evening"
	return "Night"
}

/** "07:30" -> "7:30 AM" in the user's locale. */
export function formatTime(hhmm: string | null | undefined): string {
	if (!hhmm) return ""
	const [h, m] = hhmm.split(":").map(Number)
	const d = new Date()
	d.setHours(h ?? 0, m ?? 0, 0, 0)
	return d.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })
}

export function todayISO(): string {
	const d = new Date()
	return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`
}

export function iso(d: Date): string {
	return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`
}

export function addDays(day: string, n: number): string {
	const d = parseDay(day)
	d.setDate(d.getDate() + n)
	return iso(d)
}

/** Monday- or Sunday-based start of the week containing `day`. */
export function weekStart(day: string, startsOn: "Monday" | "Sunday" = "Monday"): string {
	const d = parseDay(day)
	const offset = startsOn === "Sunday" ? d.getDay() : (d.getDay() + 6) % 7
	d.setDate(d.getDate() - offset)
	return iso(d)
}

/** The 6x7 grid of days shown for the month containing `day` (always whole weeks). */
export function monthGrid(day: string, startsOn: "Monday" | "Sunday" = "Monday"): { start: string; end: string; month: number } {
	const d = parseDay(day)
	const first = iso(new Date(d.getFullYear(), d.getMonth(), 1))
	const start = weekStart(first, startsOn)
	return { start, end: addDays(start, 41), month: d.getMonth() }
}
