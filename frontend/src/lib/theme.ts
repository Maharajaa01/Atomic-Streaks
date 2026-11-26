/**
 * Light / dark / system theme. The choice is kept per device (localStorage "atomic:theme", read
 * by an inline script in index.html before first paint) and mirrored to the profile later.
 */
import { ref } from "vue"

import type { Theme } from "@/api/types"
import { prefs } from "./pwa"

export const theme = ref<Theme>((prefs.get("theme") as Theme) || "System")
export const isDark = ref(false)

const media = typeof window !== "undefined" ? window.matchMedia?.("(prefers-color-scheme: dark)") : undefined

export function applyTheme(next: Theme = theme.value): void {
	theme.value = next
	prefs.set("theme", next)
	isDark.value = next === "Dark" || (next === "System" && !!media?.matches)
	document.documentElement.classList.toggle("dark", isDark.value)
	// status bar / app chrome blends into the page background, like a native app
	for (const meta of document.querySelectorAll('meta[name="theme-color"]')) meta.setAttribute("content", isDark.value ? "#0B1020" : "#F7F8FC")
}

media?.addEventListener?.("change", () => {
	if (theme.value === "System") applyTheme("System")
})
