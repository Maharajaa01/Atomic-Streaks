import { call } from "./client"

export interface NotificationPrefs {
	daily_reminder_enabled: 0 | 1
	daily_reminder_time: string
	weekly_summary_enabled: 0 | 1
	milestone_notifications: 0 | 1
}

export interface PushConfig {
	enabled: boolean
	public_key: string | null
	has_subscription: boolean
	prefs: NotificationPrefs
}

export const getPushConfig = () => call<PushConfig>("notifications.get_push_config")
export const subscribePush = (subscription: PushSubscriptionJSON) =>
	call<{ ok: boolean }>("notifications.subscribe", { subscription, user_agent: navigator.userAgent.slice(0, 255) }, { method: "POST" })
export const unsubscribePush = (endpoint: string) => call<{ ok: boolean }>("notifications.unsubscribe", { endpoint }, { method: "POST" })
export const sendTestPush = () => call<{ sent: number }>("notifications.send_test", {}, { method: "POST" })
