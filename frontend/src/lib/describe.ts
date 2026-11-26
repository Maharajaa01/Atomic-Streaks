import type { Habit } from "@/api/types"

const SHORT: Record<string, string> = {
	Monday: "Mon", Tuesday: "Tue", Wednesday: "Wed", Thursday: "Thu", Friday: "Fri", Saturday: "Sat", Sunday: "Sun",
}

/** "Every day", "Mon, Wed, Fri", "Every 3 days", "Once". */
export function describeSchedule(h: Pick<Habit, "frequency" | "weekdays" | "interval_days" | "habit_type">): string {
	if (h.habit_type === "One-time") return "One-time goal"
	if (h.frequency === "Specific Days") {
		const days = h.weekdays ?? []
		if (days.length === 7) return "Every day"
		if (days.length === 5 && !days.includes("Saturday") && !days.includes("Sunday")) return "Weekdays"
		if (days.length === 2 && days.includes("Saturday") && days.includes("Sunday")) return "Weekends"
		return days.map((d) => SHORT[d]).join(", ")
	}
	if (h.frequency === "Every N Days") return `Every ${h.interval_days} days`
	return "Every day"
}

export function describeTarget(h: Pick<Habit, "habit_type" | "daily_target" | "target_unit">): string {
	if (h.habit_type === "Break") return "Resist each day"
	if (h.habit_type === "One-time") return "Do it once"
	const unit = h.target_unit || "times"
	if (h.daily_target === 1 && unit === "times") return "Once a day"
	const n = Number.isInteger(h.daily_target) ? h.daily_target : h.daily_target.toFixed(1)
	return `${n} ${unit} a day`
}
