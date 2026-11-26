/**
 * Web Push on this device. Permission is only ever requested from a tap on the switch in
 * Profile (never on page load), and a "denied" answer is respected: we just explain how to
 * change it in the browser.
 */
import { subscribePush, unsubscribePush } from "@/api/notifications"

export type PushState = "unsupported" | "needs-install" | "denied" | "off" | "on"

export function pushSupported(): boolean {
	return typeof window !== "undefined" && "serviceWorker" in navigator && "PushManager" in window && "Notification" in window
}

function urlBase64ToUint8Array(base64: string): Uint8Array {
	const padded = (base64 + "=".repeat((4 - (base64.length % 4)) % 4)).replace(/-/g, "+").replace(/_/g, "/")
	const raw = atob(padded)
	return Uint8Array.from(raw, (c) => c.charCodeAt(0))
}

function sameKey(sub: PushSubscription, publicKey: string): boolean {
	const key = sub.options?.applicationServerKey
	if (!key) return true // can't tell; assume it matches
	const a = new Uint8Array(key)
	const b = urlBase64ToUint8Array(publicKey)
	return a.length === b.length && a.every((v, i) => v === b[i])
}

async function registration(): Promise<ServiceWorkerRegistration | null> {
	if (!pushSupported()) return null
	return (await navigator.serviceWorker.getRegistration("/atomic-streak")) ?? null
}

export async function currentSubscription(): Promise<PushSubscription | null> {
	const reg = await registration()
	return reg ? reg.pushManager.getSubscription() : null
}

export async function pushState(isIOS: boolean, standalone: boolean): Promise<PushState> {
	if (!pushSupported()) return isIOS && !standalone ? "needs-install" : "unsupported"
	if (Notification.permission === "denied") return "denied"
	if (Notification.permission !== "granted") return "off"
	return (await currentSubscription()) ? "on" : "off"
}

/** Must be called from a user action (tap). */
export async function enablePush(publicKey: string): Promise<PushState> {
	const permission = await Notification.requestPermission()
	if (permission !== "granted") return permission === "denied" ? "denied" : "off"
	const reg = await registration()
	if (!reg) throw new Error("The app's background worker isn't ready yet. Reload and try again.")
	let sub = await reg.pushManager.getSubscription()
	if (sub && !sameKey(sub, publicKey)) {
		await sub.unsubscribe()
		sub = null
	}
	sub ??= await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: urlBase64ToUint8Array(publicKey) })
	try {
		await subscribePush(sub.toJSON())
	} catch (e) {
		await sub.unsubscribe().catch(() => undefined) // don't leave the browser half-subscribed
		throw e
	}
	return "on"
}

export async function disablePush(): Promise<void> {
	const sub = await currentSubscription()
	if (!sub) return
	await unsubscribePush(sub.endpoint).catch(() => undefined)
	await sub.unsubscribe().catch(() => undefined)
}

/**
 * On app start: if this device already allowed notifications, make sure the server still has
 * its subscription (it may have expired, moved accounts or used an old key). Never prompts.
 */
export async function resyncPush(publicKey: string | null): Promise<void> {
	if (!publicKey || !pushSupported() || Notification.permission !== "granted") return
	const reg = await registration()
	let sub = reg ? await reg.pushManager.getSubscription() : null
	if (!reg || !sub) return
	if (!sameKey(sub, publicKey)) {
		await sub.unsubscribe()
		sub = await reg.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: urlBase64ToUint8Array(publicKey) })
	}
	await subscribePush(sub.toJSON())
}
