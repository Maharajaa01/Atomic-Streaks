import { describe, expect, it } from "vitest"

import { errorFromPayload, parseServerMessages, safeRedirect } from "@/api/client"
import { passwordScore } from "@/lib/password"
import { firstName, initials } from "@/stores/session"

describe("safeRedirect", () => {
	it("keeps in-app paths", () => {
		expect(safeRedirect("/habits/abc?x=1")).toBe("/atomic-streak/habits/abc?x=1")
	})
	it("blocks open redirects and auth loops", () => {
		for (const bad of ["https://evil.com", "//evil.com", "/\\evil.com", "/login", "/signup", "", undefined, 42]) {
			expect(safeRedirect(bad)).toBe("/atomic-streak")
		}
	})
})

describe("server messages", () => {
	it("extracts the last user-facing message as plain text", () => {
		const raw = JSON.stringify([JSON.stringify({ message: "First" }), JSON.stringify({ message: "<b>Use</b> at least 8 characters." })])
		expect(parseServerMessages(raw)).toEqual(["First", "Use at least 8 characters."])
		expect(errorFromPayload(417, { _server_messages: raw, exc_type: "ValidationError" }).message).toBe("Use at least 8 characters.")
	})
	it("falls back to a clear message", () => {
		expect(errorFromPayload(429, null).message).toMatch(/Too many attempts/)
		expect(errorFromPayload(500, null).isNetwork).toBe(false)
	})
})

describe("password hint", () => {
	it("scores", () => {
		expect(passwordScore("short")).toBe(0)
		expect(passwordScore("aaaaaaaaaaaa")).toBe(1)
		expect(passwordScore("Tr3e-Frog-Lamp-92")).toBe(4)
	})
})

describe("names", () => {
	it("greets by first real name", () => {
		expect(firstName("S PRIYA")).toBe("Priya")
		expect(firstName("priya raman")).toBe("Priya")
		expect(initials("Priya Raman")).toBe("PR")
	})
})
