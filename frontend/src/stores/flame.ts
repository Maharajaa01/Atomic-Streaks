/**
 * The streak flame: tapping a habit on Home (or completing it) shows a burning fire with
 * that habit's streak. Only the habit's name is kept here; the overlay reads the live habit
 * from today's view, so the number follows the server once a check-in is confirmed.
 */
import { defineStore } from "pinia"

export const useFlame = defineStore("flame", {
	state: () => ({ habit: null as string | null, justCompleted: false }),
	actions: {
		show(habit: string, justCompleted = false) {
			this.habit = habit
			this.justCompleted = justCompleted
		},
		close() {
			this.habit = null
			this.justCompleted = false
		},
	},
})
