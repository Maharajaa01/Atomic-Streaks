/**
 * Sign out and leave nothing of this person on the device: their push subscription (so this
 * device stops getting their reminders), saved screens, the cached app page and the outbox.
 */
import { logout } from "@/api/auth"
import { APP_BASE, clearSavedData, currentUser } from "@/api/client"
import { useConfirm } from "@/stores/confirm"
import { useSync } from "@/stores/sync"

import { disablePush } from "./push"

export async function signOut(): Promise<void> {
	const sync = useSync()
	if (sync.count) {
		const ok = await useConfirm().ask({
			title: `${sync.count} check-in${sync.count === 1 ? " hasn't" : "s haven't"} synced yet`,
			body: "If you sign out now, they'll be lost. Connect to the internet first to keep them.",
			confirmLabel: "Sign out anyway",
			danger: true,
		})
		if (!ok) return
	}
	const user = currentUser()
	await disablePush().catch(() => undefined)
	await sync.clear()
	if (user) await clearSavedData(user).catch(() => undefined)
	if ("caches" in window) await caches.delete("atomic-shell").catch(() => undefined)
	await logout()
	window.location.replace(`${APP_BASE}/login`)
}
