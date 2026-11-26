/**
 * The offline check-in outbox.
 *
 * A check-in made without a connection is kept on this device (IndexedDB) as the *desired
 * state* for that habit and day: a later tap on the same habit/day replaces the earlier one.
 * Nothing here ever claims the server has it; the UI marks these as "waiting to sync".
 *
 * Syncing (on reconnect, on app start, when the app comes back to the foreground, every
 * minute while anything is waiting, or when the user taps "Sync now"):
 *   * each item carries a client_id, so a resend after a dropped response is a no-op;
 *   * each item carries queued_at, so a newer change made on another device wins (conflict);
 *   * network trouble stops the run and keeps everything for next time;
 *   * an expired session keeps everything until the same person signs in again;
 *   * anything the server refuses (habit deleted, day too old...) is dropped and reported.
 */
import { defineStore } from "pinia"
import { computed, ref } from "vue"

import { ApiError, currentUser } from "@/api/client"
import * as api from "@/api/habits"
import { idbDelete, idbEntries, idbSet } from "@/lib/idb"
import { online } from "@/lib/pwa"

import { useToast } from "./toast"

export interface QueuedCheckIn {
	key: string
	user: string
	habit: string
	habit_name: string
	date: string
	/** the day's value; 0 means "not done" (undo) */
	value: number
	target: number
	client_id: string
	queued_at: number
}

const RETRY_MS = 60_000

function uuid(): string {
	if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID()
	return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`
}

export const useSync = defineStore("sync", () => {
	const toast = useToast()
	const items = ref<QueuedCheckIn[]>([])
	const syncing = ref(false)
	const needsSignIn = ref(false)
	const lastSynced = ref(0)
	let started = false
	let timer: ReturnType<typeof setInterval> | null = null
	/** Called after a run that changed server data (the habits store re-loads today). */
	let onSynced: (() => void) | null = null

	const count = computed(() => items.value.length)
	const pending = computed(() => new Map(items.value.map((i) => [i.key, i])))

	function keyOf(habit: string, date: string) {
		return `${habit}|${date}`
	}

	function isPending(habit: string, date: string | undefined): boolean {
		return !!date && pending.value.has(keyOf(habit, date))
	}

	async function load() {
		const user = currentUser()
		const all = (await idbEntries<QueuedCheckIn>("outbox")).map(([, v]) => v)
		items.value = all.filter((i) => i.user === user).sort((a, b) => a.queued_at - b.queued_at)
	}

	async function enqueue(entry: Omit<QueuedCheckIn, "key" | "user" | "client_id" | "queued_at">) {
		const user = currentUser()
		if (!user) return
		const item: QueuedCheckIn = { ...entry, key: keyOf(entry.habit, entry.date), user, client_id: uuid(), queued_at: Date.now() }
		await idbSet("outbox", `${user}|${item.key}`, item)
		items.value = [...items.value.filter((i) => i.key !== item.key), item]
		ensureTimer()
	}

	async function remove(item: QueuedCheckIn) {
		await idbDelete("outbox", `${item.user}|${item.key}`)
		items.value = items.value.filter((i) => i.key !== item.key || i.client_id !== item.client_id)
	}

	async function flush(): Promise<void> {
		if (syncing.value || !items.value.length || !online.value) return
		syncing.value = true
		let changed = false
		try {
			for (const item of [...items.value]) {
				// a newer tap for the same habit/day may have replaced this one meanwhile
				if (!items.value.some((i) => i.client_id === item.client_id)) continue
				try {
					const res =
						item.value > 0
							? await api.completeHabit(item.habit, {
									date: item.date,
									value: item.value,
									client_id: item.client_id,
									source: "Offline",
									queued_at: item.queued_at,
								})
							: await api.uncompleteHabit(item.habit, item.date, item.queued_at)
					await remove(item)
					changed = true
					needsSignIn.value = false
					if (res.conflict) toast.show(`"${item.habit_name}" was changed on another device, so that version was kept.`)
				} catch (e) {
					const err = e as ApiError
					if (err.isNetwork) break // still offline: try again later
					if (err.isAuth) {
						needsSignIn.value = true // keep everything until they sign in again
						break
					}
					if (err.isRateLimited) break
					await remove(item)
					toast.error(`Couldn't sync "${item.habit_name}": ${err.message}`)
				}
			}
		} finally {
			syncing.value = false
		}
		if (changed) {
			lastSynced.value = Date.now()
			onSynced?.()
			if (!items.value.length) toast.success("All check-ins synced.")
		}
		if (!items.value.length) stopTimer()
	}

	function ensureTimer() {
		if (!timer && typeof window !== "undefined") timer = setInterval(() => void flush(), RETRY_MS)
	}
	function stopTimer() {
		if (timer) clearInterval(timer)
		timer = null
	}

	/** Load this user's outbox and start listening for chances to sync. Safe to call twice. */
	async function start(afterSync?: () => void) {
		if (afterSync) onSynced = afterSync
		await load()
		if (!started && typeof window !== "undefined") {
			started = true
			window.addEventListener("online", () => void flush())
			document.addEventListener("visibilitychange", () => {
				if (document.visibilityState === "visible") void flush()
			})
		}
		if (items.value.length) ensureTimer()
		await flush()
	}

	/** Sign-out: forget this user's queued check-ins on this device. */
	async function clear() {
		for (const item of [...items.value]) await remove(item)
		stopTimer()
	}

	return { items, count, syncing, needsSignIn, lastSynced, isPending, pending, enqueue, flush, start, clear, load }
})
