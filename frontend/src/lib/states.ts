/**
 * How check-in states look everywhere (calendar, heatmaps, day lists). Status colours always
 * travel with an icon and a word, never colour alone (and green/pink sit below 3:1 on white).
 */
import { Check, CircleDashed, Clock, Minus, Sparkle, X } from "lucide-vue-next"
import type { Component } from "vue"

import type { CellState } from "@/api/types"

export const STATE_META: Record<CellState, { label: string; icon: Component; text: string; chip: string }> = {
	done: { label: "Done", icon: Check, text: "text-mint-700 dark:text-mint-400", chip: "bg-mint-600 text-white" },
	partial: { label: "Partly done", icon: Minus, text: "text-sky-700 dark:text-sky-400", chip: "bg-sky-100 text-sky-700 dark:bg-sky-500/20 dark:text-sky-400" },
	missed: { label: "Missed", icon: X, text: "text-blush-700 dark:text-blush-400", chip: "border-2 border-dashed border-blush-400 text-blush-600 dark:text-blush-400" },
	pending: { label: "Still to do", icon: Clock, text: "text-grape-700 dark:text-grape-300", chip: "border-2 border-grape-400 text-grape-600 dark:text-grape-300" },
	bonus: { label: "Extra check-in", icon: Sparkle, text: "text-sun-700 dark:text-sun-400", chip: "bg-sun-100 text-sun-700 dark:bg-sun-500/20 dark:text-sun-400" },
	off: { label: "Not scheduled", icon: CircleDashed, text: "text-ink-400", chip: "bg-ink-100 text-ink-300 dark:bg-night-800 dark:text-night-600" },
}
