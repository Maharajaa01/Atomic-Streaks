/** Habit colours: the brand palette plus a few companions, all readable with white icons. */
export const HABIT_COLORS = [
	"#7657F6", "#4D8DFF", "#26C281", "#FF9F43", "#F56FA1", "#FFB020",
	"#1FB5A8", "#9B7BFF", "#FF6B8B", "#3BA7F0", "#5B6B8C", "#E5484D",
]

/** rgba() of a #RRGGBB colour, for tinted surfaces. */
export function tint(hex: string | null | undefined, alpha: number): string {
	const m = /^#([0-9a-f]{6})$/i.exec(hex ?? "")
	if (!m) return `rgba(118, 87, 246, ${alpha})`
	const n = parseInt(m[1]!, 16)
	return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${alpha})`
}
