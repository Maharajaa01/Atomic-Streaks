import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/api/growth", () => ({
	getCelebrations: vi.fn(),
	markCelebrated: vi.fn().mockResolvedValue({ ok: true }),
}))

import * as api from "@/api/growth"
import type { Boot, Celebrations } from "@/api/types"
import { useCelebrations } from "@/stores/celebrations"
import { useSession } from "@/stores/session"

const badge = (name: string) => ({ name, code: name, xp: 20, title: "First Step", description: "d", icon: "footprints", color: "#26C281" })
const payload = (over: Partial<Celebrations> = {}): Celebrations => ({ achievements: [], challenges: [], ...over })

describe("celebrations", () => {
	beforeEach(() => {
		setActivePinia(createPinia())
		vi.mocked(api.markCelebrated).mockClear()
		useSession().boot = { profile: { xp: 90, level: 1 } } as unknown as Boot
	})

	it("queues badges and challenges once, in order", () => {
		const store = useCelebrations()
		const c = payload({ achievements: [badge("ua1")], challenges: [{ name: "p1", xp: 70, title: "7 Days", icon: "trophy", color: "#FF9F43" }] })
		store.ingest(c)
		store.ingest(c) // the next check-in reports the same pending rewards
		expect(store.queue.map((q) => q.key)).toEqual(["a-ua1", "c-p1"])
		expect(store.current?.title).toBe("First Step")
	})

	it("marks each reward seen on the server only when dismissed, and never shows it again", () => {
		const store = useCelebrations()
		store.ingest(payload({ achievements: [badge("ua1")] }))
		expect(api.markCelebrated).not.toHaveBeenCalled()
		store.dismiss()
		expect(api.markCelebrated).toHaveBeenCalledWith(["ua1"], [])
		store.ingest(payload({ achievements: [badge("ua1")] }))
		expect(store.queue).toEqual([])
	})

	it("updates the profile XP and celebrates a level-up", () => {
		const store = useCelebrations()
		store.ingest(payload(), { xp: 110, level: 2, level_start: 100, next_level_at: 300, progress: 5 })
		expect(useSession().boot?.profile).toMatchObject({ xp: 110, level: 2 })
		expect(store.current).toMatchObject({ kind: "level", title: "Level 2!" })
		// same level again: nothing new
		store.dismiss()
		store.ingest(payload(), { xp: 120, level: 2, level_start: 100, next_level_at: 300, progress: 10 })
		expect(store.queue).toEqual([])
	})
})
