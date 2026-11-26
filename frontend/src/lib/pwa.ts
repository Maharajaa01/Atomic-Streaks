/**
 * Service worker registration, install prompt and update flow.
 *
 * The worker lives at /atomic_streak_sw.js (site root) so it can control /atomic-streak and
 * /atomic-streak/*. The scope is "/atomic-streak" (no trailing slash): Frappe redirects
 * "/atomic-streak/" to "/atomic-streak", so a trailing-slash scope would leave the home page out.
 * A new worker never takes over silently; it waits for the user to tap "Update".
 */
import { ref } from "vue"

type InstallPrompt = Event & { prompt: () => Promise<void>; userChoice: Promise<{ outcome: string }> }

const SW_URL = "/atomic_streak_sw.js"
const SCOPE = "/atomic-streak"

export const updateReady = ref(false)
export const canInstall = ref(false)
export const online = ref(typeof navigator === "undefined" ? true : navigator.onLine)
let waiting: ServiceWorker | null = null
let deferredPrompt: InstallPrompt | null = null
let updateRequested = false
let reloading = false

export function registerServiceWorker(): void {
	if (!("serviceWorker" in navigator) || import.meta.env.DEV) return
	window.addEventListener("load", async () => {
		try {
			const reg = await navigator.serviceWorker.register(SW_URL, { scope: SCOPE })
			const track = (w: ServiceWorker | null) => {
				w?.addEventListener("statechange", () => {
					if (w.state === "installed" && navigator.serviceWorker.controller) {
						waiting = w
						updateReady.value = true
					}
				})
			}
			if (reg.waiting && navigator.serviceWorker.controller) {
				waiting = reg.waiting
				updateReady.value = true
			}
			reg.addEventListener("updatefound", () => track(reg.installing))
			// look for a new build every 30 minutes while the app stays open
			setInterval(() => reg.update().catch(() => undefined), 30 * 60 * 1000)
		} catch (e) {
			console.warn("Atomic Streak: service worker registration failed", e)
		}
	})
	// Reload only when the user asked for the update; the first install also fires this.
	navigator.serviceWorker.addEventListener("controllerchange", () => {
		if (!updateRequested || reloading) return
		reloading = true
		window.location.reload()
	})
}

export function applyUpdate(): void {
	updateRequested = true
	if (waiting) waiting.postMessage({ type: "SKIP_WAITING" })
	else window.location.reload()
}

if (typeof window !== "undefined") {
	window.addEventListener("beforeinstallprompt", (e) => {
		e.preventDefault()
		deferredPrompt = e as InstallPrompt
		canInstall.value = true
	})
	window.addEventListener("appinstalled", () => {
		canInstall.value = false
		deferredPrompt = null
	})
	window.addEventListener("online", () => (online.value = true))
	window.addEventListener("offline", () => (online.value = false))
}

export async function promptInstall(): Promise<boolean> {
	if (!deferredPrompt) return false
	await deferredPrompt.prompt()
	const choice = await deferredPrompt.userChoice
	deferredPrompt = null
	canInstall.value = false
	return choice.outcome === "accepted"
}

export function isStandalone(): boolean {
	return (
		window.matchMedia?.("(display-mode: standalone)").matches ||
		(navigator as Navigator & { standalone?: boolean }).standalone === true
	)
}

/** iPhone/iPad Safari has no install prompt; users add the app from the Share menu. */
export function isIOS(): boolean {
	const ua = navigator.userAgent
	return /iPad|iPhone|iPod/.test(ua) || (ua.includes("Macintosh") && navigator.maxTouchPoints > 1)
}

/** Small per-device preferences. Never throws (private mode / blocked storage). */
export const prefs = {
	get(key: string): string | null {
		try {
			return window.localStorage.getItem(`atomic:${key}`)
		} catch {
			return null
		}
	},
	set(key: string, value: string): void {
		try {
			window.localStorage.setItem(`atomic:${key}`, value)
		} catch {
			/* fine */
		}
	},
}

export const LOGO = `${import.meta.env.BASE_URL}icons/logo.svg`
