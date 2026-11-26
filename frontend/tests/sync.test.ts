import { createPinia, setActivePinia } from "pinia"
import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/api/habits", () => ({ completeHabit: vi.fn(), uncompleteHabit: vi.fn() }))

import { ApiError } from "@/api/client"
import * as api from "@/api/habits"
import type { CheckInResult } from "@/api/types"
import { online } from "@/lib/pwa"
import { useSync } from "@/stores/sync"
import { useToast } from "@/stores/toast"

const ok = (conflict = false) => ({ conflict }) as unknown as CheckInResult
const entry = (over = {}) => ({ habit: "h1", habit_name: "Read", date: "2026-11-22", value: 1, target: 1, ...over })

describe("offline sync queue", () => {
	beforeEach(async () => {
		setActivePinia(createPinia())
		document.cookie = "user_id=amy%40example.com"
		online.value = true
		vi.mocked(api.completeHabit).mockReset()
		vi.mocked(api.uncompleteHabit).mockReset()
		await useSync().clear()
	})

	it("keeps only the latest state per habit and day", async () => {
		const sync = useSync()
		online.value = false
		await sync.enqueue(entry({ value: 1 }))
		await sync.enqueue(entry({ value: 0 }))
		await sync.enqueue(entry({ habit: "h2", habit_name: "Walk" }))
		expect(sync.count).toBe(2)
		expect(sync.pending.get("h1|2026-11-22")?.value).toBe(0)
	})

	it("sends each item once with its client id and queue time, then clears it", async () => {
		const sync = useSync()
		online.value = false
		await sync.enqueue(entry({ value: 3, target: 8 }))
		await sync.enqueue(entry({ habit: "h2", value: 0 }))
		online.value = true
		vi.mocked(api.completeHabit).mockResolvedValue(ok())
		vi.mocked(api.uncompleteHabit).mockResolvedValue(ok())
		await sync.flush()
		const [habit, opts] = vi.mocked(api.completeHabit).mock.calls[0]!
		expect(habit).toBe("h1")
		expect(opts).toMatchObject({ date: "2026-11-22", value: 3, source: "Offline" })
		expect(opts?.client_id).toBeTruthy()
		expect(opts?.queued_at).toBeTypeOf("number")
		expect(api.uncompleteHabit).toHaveBeenCalledWith("h2", "2026-11-22", expect.any(Number))
		expect(sync.count).toBe(0)
		await sync.flush()
		expect(api.completeHabit).toHaveBeenCalledTimes(1)
	})

	it("network trouble keeps everything for later", async () => {
		const sync = useSync()
		await sync.enqueue(entry())
		vi.mocked(api.completeHabit).mockRejectedValue(new ApiError("offline", 0))
		await sync.flush()
		expect(sync.count).toBe(1)
	})

	it("an expired session keeps the queue and asks to sign in", async () => {
		const sync = useSync()
		await sync.enqueue(entry())
		vi.mocked(api.completeHabit).mockRejectedValue(new ApiError("expired", 401))
		await sync.flush()
		expect(sync.count).toBe(1)
		expect(sync.needsSignIn).toBe(true)
	})

	it("drops and reports what the server refuses, and carries on", async () => {
		const sync = useSync()
		await sync.enqueue(entry())
		await sync.enqueue(entry({ habit: "h2", habit_name: "Walk" }))
		vi.mocked(api.completeHabit).mockRejectedValueOnce(new ApiError("Check-ins can only be changed for the last 7 days.", 417)).mockResolvedValueOnce(ok())
		await sync.flush()
		expect(sync.count).toBe(0)
		expect(useToast().items.some((t) => t.tone === "error" && t.message.includes("last 7 days"))).toBe(true)
	})

	it("tells the user when another device's newer change won", async () => {
		const sync = useSync()
		await sync.enqueue(entry())
		vi.mocked(api.completeHabit).mockResolvedValue(ok(true))
		await sync.flush()
		expect(useToast().items.some((t) => t.message.includes("changed on another device"))).toBe(true)
	})

	it("only syncs the signed-in user's items", async () => {
		const sync = useSync()
		await sync.enqueue(entry())
		document.cookie = "user_id=ben%40example.com"
		await sync.load()
		expect(sync.count).toBe(0)
		document.cookie = "user_id=amy%40example.com"
		await sync.load()
		expect(sync.count).toBe(1)
	})
})
