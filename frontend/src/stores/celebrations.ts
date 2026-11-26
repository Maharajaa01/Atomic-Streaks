/**
 * Badges earned and challenges finished, shown one at a time as a celebration.
 *
 * Every check-in response carries the user's new XP and any rewards not yet celebrated, so
 * this store hears about them wherever the check-in happened (Home, Calendar, a routine).
 * A reward is marked as celebrated on the server only once the user has seen it, so closing
 * the app mid-celebration just shows it again next time.
 */
import { defineStore } from "pinia"

import { getCelebrations, markCelebrated } from "@/api/growth"
import type { Celebrations, LevelProgress } from "@/api/types"

import { useSession } from "./session"

export interface Celebration {
	key: string
	kind: "achievement" | "challenge" | "level"
	name: string
	title: string
	body: string
	icon: string
	color: string
	xp: number
}

export const useCelebrations = defineStore("celebrations", {
	state: () => ({ queue: [] as Celebration[], seen: new Set<string>() }),
	getters: {
		current: (s): Celebration | null => s.queue[0] ?? null,
	},
	actions: {
		/** Feed a check-in response (or a /get_celebrations payload) into the queue. */
		ingest(c: Celebrations | undefined, xp?: LevelProgress) {
			const session = useSession()
			const profile = session.boot?.profile
			if (xp && profile) {
				const before = profile.level ?? 1
				profile.xp = xp.xp
				profile.level = xp.level
				if (xp.level > before) {
					this.push({
						key: `level-${xp.level}`,
						kind: "level",
						name: "",
						title: `Level ${xp.level}!`,
						body: "Every check-in is a vote for the person you want to become.",
						icon: "crown",
						color: "#7657F6",
						xp: 0,
					})
				}
			}
			for (const a of c?.achievements ?? []) {
				this.push({ key: `a-${a.name}`, kind: "achievement", name: a.name, title: a.title, body: a.description, icon: a.icon, color: a.color, xp: a.xp })
			}
			for (const ch of c?.challenges ?? []) {
				this.push({
					key: `c-${ch.name}`,
					kind: "challenge",
					name: ch.name,
					title: "Challenge complete!",
					body: ch.title,
					icon: ch.icon,
					color: ch.color,
					xp: ch.xp,
				})
			}
		},
		push(item: Celebration) {
			if (this.seen.has(item.key) || this.queue.some((q) => q.key === item.key)) return
			this.queue.push(item)
		},
		async refresh() {
			try {
				this.ingest(await getCelebrations())
			} catch {
				/* a missed celebration is shown next time */
			}
		},
		dismiss() {
			const item = this.queue.shift()
			if (!item) return
			this.seen.add(item.key)
			if (item.kind === "achievement") void markCelebrated([item.name], []).catch(() => undefined)
			if (item.kind === "challenge") void markCelebrated([], [item.name]).catch(() => undefined)
		},
	},
})
