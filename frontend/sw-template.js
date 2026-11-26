/**
 * Atomic Streak service worker.
 *
 * Source of truth: frontend/sw-template.js. Built into atomic_streak/www/atomic_streak_sw.js by
 * frontend/scripts/make-page.mjs, which stamps CACHE_VERSION and the PRECACHE list on every
 * build. Never edit www/atomic_streak_sw.js by hand.
 *
 * Rules:
 *   1. Habit data is never cached here: /api/ and anything that is not a static build asset
 *      goes straight to the network. (The app keeps its own per-user copy of what it last
 *      loaded, and an outbox of offline check-ins, in IndexedDB; see src/stores/sync.ts.)
 *   2. Pages under /atomic-streak are network-first. The last good copy of the app page is
 *      kept so the app still opens offline; without one, a branded offline notice is shown.
 *      Sign-out deletes that copy (it carries the session's CSRF token).
 *   3. Hashed build assets are precached and served cache-first; their names change whenever
 *      their content does.
 *   4. A new worker waits until the user taps "Update", so nobody loses what they were doing.
 *   5. Push: show what the server sent; a tap opens (or focuses) the app at the given screen,
 *      and only ever at a path inside the app.
 */

const CACHE_VERSION = "__CACHE_VERSION__"
const PRECACHE = __PRECACHE__

const CACHE = `atomic-static-${CACHE_VERSION}`
const SHELL_CACHE = "atomic-shell"
const SHELL_KEY = "/atomic-streak"
const ASSET_PATH = "/assets/atomic_streak/frontend/"
const APP_SCOPE = "/atomic-streak"

const OFFLINE_HTML = `<!doctype html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta name="theme-color" content="#7657F6"><title>Offline · Atomic Streak</title>
<style>
body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;background:#F7F8FC;color:#141826;font:16px/1.5 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
@media (prefers-color-scheme:dark){body{background:#0B1020;color:#EEF0F6}p{color:#9AA1B5!important}}
.c{max-width:22rem;padding:2rem;text-align:center}
img{width:4.5rem;height:4.5rem;margin:0 auto 1.25rem;display:block}
h1{font-size:1.35rem;margin:0 0 .5rem}p{color:#6B7389;margin:0 0 1.5rem}
button{min-height:3.25rem;padding:0 1.75rem;border:0;border-radius:1rem;background:#7657F6;color:#fff;font:inherit;font-weight:700;cursor:pointer}
</style></head><body><main class="c"><img src="${ASSET_PATH}icons/logo.svg" alt="">
<h1>You're offline</h1>
<p>Connect to the internet to open Atomic Streak. Your habits are safe on the server.</p>
<button onclick="location.reload()">Try again</button></main></body></html>`

self.addEventListener("install", (event) => {
	event.waitUntil(
		caches
			.open(CACHE)
			.then((cache) => cache.addAll(PRECACHE))
			.catch(() => undefined),
	)
})

self.addEventListener("activate", (event) => {
	event.waitUntil(
		caches
			.keys()
			.then((keys) => Promise.all(keys.filter((k) => k.startsWith("atomic-static-") && k !== CACHE).map((k) => caches.delete(k))))
			.then(() => self.clients.claim()),
	)
})

self.addEventListener("message", (event) => {
	if (event.data && event.data.type === "SKIP_WAITING") self.skipWaiting()
})

self.addEventListener("fetch", (event) => {
	const req = event.request
	if (req.method !== "GET") return
	const url = new URL(req.url)
	if (url.origin !== self.location.origin) return

	if (req.mode === "navigate" && (url.pathname === APP_SCOPE || url.pathname.startsWith(APP_SCOPE + "/"))) {
		event.respondWith(
			fetch(req)
				.then((res) => {
					// every app route serves the same page; keep the last signed-in copy for offline use
					if (res.ok && res.type === "basic" && !res.redirected) {
						const copy = res.clone()
						copy
							.clone()
							.text()
							.then((html) => (html.includes("window.atomic_guest = 0;") ? caches.open(SHELL_CACHE).then((c) => c.put(SHELL_KEY, copy)) : undefined))
							.catch(() => undefined)
					}
					return res
				})
				.catch(async () => {
					const shell = await caches.match(SHELL_KEY, { cacheName: SHELL_CACHE })
					return (
						shell ||
						new Response(OFFLINE_HTML, {
							status: 503,
							headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" },
						})
					)
				}),
		)
		return
	}

	if (!url.pathname.startsWith(ASSET_PATH)) return

	event.respondWith(
		caches.open(CACHE).then(async (cache) => {
			const key = url.pathname // manifest/icons carry ?v=<hash>; the path is the cache key
			const hit = await cache.match(key)
			const hashed = url.pathname.startsWith(ASSET_PATH + "assets/")
			if (hit && hashed) return hit
			const network = fetch(req)
				.then((res) => {
					if (res.ok && res.type === "basic") cache.put(key, res.clone())
					return res
				})
				.catch(() => hit || Response.error())
			return hit || network
		}),
	)
})

// ------------------------------------------------------------------ push notifications
function appUrl(raw) {
	try {
		const url = new URL(raw || APP_SCOPE, self.location.origin)
		if (url.origin === self.location.origin && (url.pathname === APP_SCOPE || url.pathname.startsWith(APP_SCOPE + "/"))) return url.href
	} catch (e) {
		/* fall through */
	}
	return new URL(APP_SCOPE, self.location.origin).href
}

self.addEventListener("push", (event) => {
	let data = {}
	try {
		data = event.data ? event.data.json() : {}
	} catch (e) {
		data = { body: event.data ? event.data.text() : "" }
	}
	const title = String(data.title || "Atomic Streak").slice(0, 120)
	event.waitUntil(
		self.registration.showNotification(title, {
			body: String(data.body || "").slice(0, 300),
			tag: String(data.tag || "atomic-streak"),
			icon: ASSET_PATH + "icons/icon-192.png",
			lang: "en",
			data: { url: appUrl(data.url) },
		}),
	)
})

self.addEventListener("notificationclick", (event) => {
	event.notification.close()
	const target = appUrl(event.notification.data && event.notification.data.url)
	event.waitUntil(
		self.clients.matchAll({ type: "window", includeUncontrolled: true }).then(async (windows) => {
			const app = windows.find((w) => new URL(w.url).pathname.startsWith(APP_SCOPE))
			if (app) {
				await app.focus()
				if (app.url !== target && "navigate" in app) await app.navigate(target).catch(() => undefined)
				return
			}
			await self.clients.openWindow(target)
		}),
	)
})
