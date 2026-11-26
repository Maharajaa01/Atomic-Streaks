/**
 * Thin wrapper over Frappe whitelisted methods under atomic_streak.api.*
 * Callers name endpoints as "habit.get_habits" rather than the full module path.
 *
 * Security: same-origin session cookie + Frappe's CSRF token (injected into the page by
 * www/atomic_streak_app.py) on every POST. No API keys or secrets ever live in the browser.
 */

import { ref } from "vue"

import { idbEntries, idbDelete, idbGet, idbSet } from "@/lib/idb"

export const APP_BASE = "/atomic-streak"

/** True while some screen is showing data saved on this device because the server is unreachable. */
export const usingSavedData = ref(false)
const PREFIX = "/api/method/atomic_streak.api."

export class ApiError extends Error {
	status: number
	excType: string

	constructor(message: string, status = 0, excType = "") {
		super(message)
		this.name = "ApiError"
		this.status = status
		this.excType = excType
	}

	get isNetwork(): boolean {
		return this.status === 0
	}
	get isAuth(): boolean {
		return this.status === 401 || (this.status === 403 && /SessionExpired|AuthenticationError/.test(this.excType))
	}
	get isPermission(): boolean {
		return this.status === 403 || /PermissionError/.test(this.excType)
	}
	get isRateLimited(): boolean {
		return this.status === 429
	}
}

function csrfToken(): string | null {
	const t = window.csrf_token
	return t && t !== "None" && !t.startsWith("{{") ? t : null
}

function htmlToText(html: string): string {
	const div = document.createElement("div")
	div.innerHTML = html.replace(/<br\s*\/?>/gi, "\n")
	return (div.textContent || "").trim()
}

/** Frappe sends user-facing errors as JSON strings inside `_server_messages`. */
export function parseServerMessages(raw: unknown): string[] {
	if (typeof raw !== "string" || !raw) return []
	try {
		return (JSON.parse(raw) as unknown[])
			.map((entry) => {
				const parsed = (typeof entry === "string" ? JSON.parse(entry) : entry) as { message?: string }
				return htmlToText(String(parsed.message ?? ""))
			})
			.filter(Boolean)
	} catch {
		return []
	}
}

export function errorFromPayload(status: number, payload: Record<string, unknown> | null): ApiError {
	const messages = parseServerMessages(payload?._server_messages)
	let message = messages[messages.length - 1]
	if (!message) {
		if (status === 429) message = "Too many attempts. Please wait a little and try again."
		else if (status === 403) message = "You don't have permission to do that."
		else if (status === 404) message = "That couldn't be found."
		else if (status >= 500) message = "The server ran into a problem. Please try again shortly."
		else message = "Something went wrong. Please try again."
	}
	return new ApiError(message, status, String(payload?.exc_type ?? ""))
}

/** In-app path ("/habits/abc") for the current location, used as the post-login target. */
export function currentAppPath(): string {
	const path = window.location.pathname.replace(new RegExp(`^${APP_BASE}`), "") || "/"
	return path + window.location.search
}

const AUTH_PAGES = ["/login", "/signup", "/forgot-password", "/reset-password"]

export function loginUrl(redirect = currentAppPath()): string {
	return redirect && redirect !== "/" && !AUTH_PAGES.some((p) => redirect.startsWith(p))
		? `${APP_BASE}/login?redirect=${encodeURIComponent(redirect)}`
		: `${APP_BASE}/login`
}

/** Only allow in-app paths after login (no open redirects). */
export function safeRedirect(raw: unknown): string {
	const value = typeof raw === "string" ? raw : ""
	if (!value.startsWith("/") || value.startsWith("//") || value.includes("\\") || AUTH_PAGES.some((p) => value.startsWith(p))) {
		return APP_BASE
	}
	return APP_BASE + value
}

function handleSessionExpiry(status: number, payload: Record<string, unknown> | null) {
	const text = String(payload?.exc_type ?? "") + String(payload?.exception ?? "") + String(payload?.session_expired ?? "")
	if ((status === 401 || status === 403) && /Login to access|session_expired|SessionExpired|Not permitted.*Guest/i.test(text)) {
		if (!AUTH_PAGES.some((p) => window.location.pathname.startsWith(APP_BASE + p))) window.location.replace(loginUrl())
	}
}

function parse(text: string): Record<string, unknown> | null {
	if (!text) return null
	try {
		return JSON.parse(text)
	} catch {
		return null
	}
}

async function send(url: string, init: RequestInit): Promise<{ response: Response; payload: Record<string, unknown> | null }> {
	let response: Response
	try {
		response = await fetch(url, { credentials: "same-origin", cache: "no-store", ...init })
	} catch (e) {
		if ((e as Error).name === "AbortError") throw e
		throw new ApiError("Can't reach the server. Check your connection and try again.")
	}
	return { response, payload: parse(await response.text()) }
}

export async function call<T>(
	name: string,
	args: Record<string, unknown> = {},
	opts: { method?: "GET" | "POST"; signal?: AbortSignal } = {},
): Promise<T> {
	const method = opts.method ?? "GET"
	const headers: Record<string, string> = { Accept: "application/json", "X-Requested-With": "XMLHttpRequest" }
	let url = PREFIX + name
	const init: RequestInit = { method, headers, signal: opts.signal }

	if (method === "GET") {
		const params = new URLSearchParams()
		for (const [k, v] of Object.entries(args)) {
			if (v === undefined || v === null || v === "") continue
			params.set(k, typeof v === "object" ? JSON.stringify(v) : String(v))
		}
		const qs = params.toString()
		if (qs) url += `?${qs}`
	} else {
		headers["Content-Type"] = "application/json"
		const token = csrfToken()
		if (token) headers["X-Frappe-CSRF-Token"] = token
		init.body = JSON.stringify(args)
	}

	const key = method === "GET" ? cacheKey(name, args) : null
	let result: Awaited<ReturnType<typeof send>>
	try {
		result = await send(url, init)
	} catch (e) {
		// offline: show the last copy this device saw, if there is one
		const saved = key ? await idbGet<{ data: T }>("cache", key) : undefined
		if (saved && e instanceof ApiError && e.isNetwork) {
			usingSavedData.value = true
			return saved.data
		}
		throw e
	}
	const { response, payload } = result
	if (!response.ok) {
		handleSessionExpiry(response.status, payload)
		throw errorFromPayload(response.status, payload)
	}
	const data = (payload?.message ?? null) as T
	if (key) {
		usingSavedData.value = false
		void idbSet("cache", key, { data, at: Date.now() })
	}
	return data
}

// ------------------------------------------------------------------ offline read cache
/** The signed-in user per Frappe's (non-secret) user_id cookie; reads are cached per user. */
export function currentUser(): string | null {
	const m = document.cookie.match(/(?:^|;\s*)user_id=([^;]*)/)
	const user = m ? decodeURIComponent(m[1]!) : ""
	return user && user !== "Guest" ? user : null
}

function cacheKey(name: string, args: Record<string, unknown>): string | null {
	const user = currentUser()
	if (!user || name.startsWith("auth.")) return null
	const params = Object.entries(args)
		.filter(([, v]) => v !== undefined && v !== null && v !== "")
		.sort(([a], [b]) => a.localeCompare(b))
		.map(([k, v]) => `${k}=${typeof v === "object" ? JSON.stringify(v) : String(v)}`)
		.join("&")
	return `${user}|${name}?${params}`
}

/** Update the saved copy of a read after a change made on this device (e.g. a check-in). */
export function saveToCache(name: string, args: Record<string, unknown>, data: unknown): void {
	const key = cacheKey(name, args)
	if (key) void idbSet("cache", key, { data, at: Date.now() })
}

/** Forget everything this device saved for `user` (on sign-out). */
export async function clearSavedData(user: string): Promise<void> {
	for (const [key] of await idbEntries("cache")) if (key.startsWith(`${user}|`)) await idbDelete("cache", key)
}

/** POST to a core Frappe method (login, logout, update_password) with the same error handling. */
export async function frappePost<T>(method: string, args: Record<string, unknown>): Promise<{ status: number; message: T }> {
	const headers: Record<string, string> = { "Content-Type": "application/json", Accept: "application/json" }
	const token = csrfToken()
	if (token) headers["X-Frappe-CSRF-Token"] = token
	const { response, payload } = await send(`/api/method/${method}`, { method: "POST", headers, body: JSON.stringify(args) })
	if (!response.ok) throw errorFromPayload(response.status, payload)
	return { status: response.status, message: (payload?.message ?? null) as T }
}
