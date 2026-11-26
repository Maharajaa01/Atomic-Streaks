import { ApiError, call, errorFromPayload, frappePost } from "./client"
import type { AuthOptions, Boot } from "./types"

export const getBoot = () => call<Boot>("session.get_boot")
export const getAuthOptions = () => call<AuthOptions>("auth.get_auth_options")

export function browserTimezone(): string | undefined {
	try {
		return Intl.DateTimeFormat().resolvedOptions().timeZone || undefined
	} catch {
		return undefined
	}
}

/** Sign in through Frappe's standard login (same users, passwords, lockouts and sessions). */
export async function login(usr: string, pwd: string): Promise<void> {
	let response: Response
	try {
		response = await fetch("/api/method/login", {
			method: "POST",
			credentials: "same-origin",
			headers: { "Content-Type": "application/json", Accept: "application/json" },
			body: JSON.stringify({ usr, pwd }),
		})
	} catch {
		throw new ApiError("Can't reach the server. Check your connection and try again.")
	}
	const text = await response.text()
	let payload: Record<string, unknown> | null = null
	try {
		payload = text ? JSON.parse(text) : null
	} catch {
		/* not JSON */
	}
	if (!response.ok) {
		if (response.status === 401) throw new ApiError("That email and password don't match. Try again.", 401)
		throw errorFromPayload(response.status, payload)
	}
	if (payload && (payload as { verification?: unknown }).verification) {
		throw new ApiError("Your account uses two-step sign-in. Please sign in from the main site login page.", 400)
	}
}

export async function logout(): Promise<void> {
	await frappePost("logout", {}).catch(() => undefined)
}

export const register = (fullName: string, email: string, password: string) =>
	call<{ ok: boolean }>("auth.register", { full_name: fullName, email, password, timezone: browserTimezone() }, { method: "POST" })

export const join = () => call<{ ok: boolean }>("auth.join", { timezone: browserTimezone() }, { method: "POST" })

export const requestPasswordReset = (email: string) =>
	call<{ ok: boolean }>("auth.request_password_reset", { email }, { method: "POST" })

/** Redeem a reset link with Frappe's own update_password (checks the key and its expiry, then signs in). */
export async function resetPassword(key: string, newPassword: string): Promise<void> {
	const expired = () => new ApiError("This reset link has expired or was already used. Ask for a new one.", 410)
	try {
		const { message } = await frappePost<string>("frappe.core.doctype.user.user.update_password", {
			key,
			new_password: newPassword,
		})
		if (typeof message === "string" && /expired|invalid|used before/i.test(message)) throw expired()
	} catch (e) {
		// an expired or used link comes back as HTTP 410 with a message instead of a redirect path
		if (e instanceof ApiError && e.status === 410) throw expired()
		throw e
	}
}
