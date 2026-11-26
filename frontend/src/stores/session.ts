import { defineStore } from "pinia"

import { getBoot } from "@/api/auth"
import type { Boot } from "@/api/types"

/** First real word of a name, skipping initials ("S PRIYA" -> "Priya"). */
export function firstName(full: string): string {
	const words = full.trim().split(/\s+/).filter(Boolean)
	const word = words.find((w) => w.replace(/\./g, "").length > 1) ?? words[0] ?? ""
	return word ? word[0]!.toUpperCase() + word.slice(1).toLowerCase() : ""
}

export function initials(full: string): string {
	const words = full.trim().split(/\s+/).filter(Boolean)
	return ((words[0]?.[0] ?? "") + (words.length > 1 ? words[words.length - 1]![0] : "")).toUpperCase() || "?"
}

let inflight: Promise<void> | null = null

export const useSession = defineStore("session", {
	state: () => ({ boot: null as Boot | null, error: "" }),
	getters: {
		displayName: (s) => (s.boot?.profile?.full_name || s.boot?.full_name || s.boot?.user || "").trim(),
		firstName(): string {
			return firstName(this.displayName)
		},
		initials(): string {
			return initials(this.displayName)
		},
		avatar: (s) => s.boot?.profile?.avatar || s.boot?.user_image || null,
	},
	actions: {
		/** Concurrent callers (App.vue and router guards) share one request. */
		load(force = false) {
			if (inflight) return inflight
			if (this.boot && !force) return Promise.resolve()
			this.error = ""
			inflight = getBoot()
				.then((boot) => {
					this.boot = boot
				})
				.catch((e) => {
					this.error = (e as Error).message
				})
				.finally(() => {
					inflight = null
				})
			return inflight
		},
	},
})
