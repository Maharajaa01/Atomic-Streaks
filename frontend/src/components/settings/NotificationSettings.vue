<script setup lang="ts">
import { BellOff, BellRing, Send } from "lucide-vue-next"
import { computed, onMounted, ref } from "vue"

import { updateProfile } from "@/api/habits"
import { getPushConfig, sendTestPush, type NotificationPrefs, type PushConfig } from "@/api/notifications"
import AppButton from "@/components/ui/AppButton.vue"
import ToggleSwitch from "@/components/ui/ToggleSwitch.vue"
import { isIOS, isStandalone } from "@/lib/pwa"
import { disablePush, enablePush, pushState, type PushState } from "@/lib/push"
import { useToast } from "@/stores/toast"

const toast = useToast()
const config = ref<PushConfig | null>(null)
const state = ref<PushState>("off")
const busy = ref(false)
const testing = ref(false)
const prefs = ref<NotificationPrefs | null>(null)
const loadError = ref("")

onMounted(async () => {
	try {
		config.value = await getPushConfig()
		prefs.value = { ...config.value.prefs }
		state.value = await pushState(isIOS(), isStandalone())
	} catch (e) {
		loadError.value = (e as Error).message
	}
})

const deviceOn = computed({
	get: () => state.value === "on",
	set: (v: boolean) => void toggleDevice(v),
})

async function toggleDevice(on: boolean) {
	if (!config.value?.public_key) return
	busy.value = true
	try {
		if (on) {
			state.value = await enablePush(config.value.public_key)
			if (state.value === "on") toast.success("Notifications are on for this device.")
		} else {
			await disablePush()
			state.value = "off"
		}
	} catch (e) {
		toast.error((e as Error).message)
		state.value = await pushState(isIOS(), isStandalone())
	} finally {
		busy.value = false
	}
}

async function test() {
	testing.value = true
	try {
		await sendTestPush()
		toast.success("Test sent. It should appear in a few seconds.")
	} catch (e) {
		toast.error((e as Error).message)
	} finally {
		testing.value = false
	}
}

async function savePref<K extends keyof NotificationPrefs>(field: K, value: NotificationPrefs[K]) {
	if (!prefs.value) return
	const before = prefs.value[field]
	prefs.value[field] = value
	try {
		await updateProfile({ [field]: field === "daily_reminder_time" ? `${value}:00` : value })
	} catch (e) {
		prefs.value[field] = before
		toast.error((e as Error).message)
	}
}

const bool = (field: "daily_reminder_enabled" | "weekly_summary_enabled" | "milestone_notifications") =>
	computed({
		get: () => !!prefs.value?.[field],
		set: (v: boolean) => void savePref(field, v ? 1 : 0),
	})
const daily = bool("daily_reminder_enabled")
const weekly = bool("weekly_summary_enabled")
const milestones = bool("milestone_notifications")
</script>

<template>
	<section class="mt-5 rounded-4xl bg-white p-5 shadow-soft dark:bg-night-900" aria-labelledby="notif-title">
		<h2 id="notif-title" class="text-[18px] font-extrabold">Notifications</h2>

		<p v-if="loadError" class="mt-3 text-[14px] text-ink-500 dark:text-ink-400">{{ loadError }}</p>

		<template v-else-if="config">
			<!-- this device -->
			<div class="mt-4">
				<p v-if="!config.enabled" class="flex items-start gap-2 rounded-2xl bg-ink-50 p-3.5 text-[14px] text-ink-600 dark:bg-night-800 dark:text-ink-300">
					<BellOff class="mt-0.5 h-5 w-5 shrink-0" /> Notifications are switched off for this site by the administrator.
				</p>
				<p v-else-if="state === 'needs-install'" class="rounded-2xl bg-sky-50 p-3.5 text-[14px] text-sky-700 dark:bg-sky-500/10 dark:text-sky-400">
					On iPhone and iPad, install the app first (Share, then "Add to Home Screen"), open it from your home screen, and turn notifications on here.
				</p>
				<p v-else-if="state === 'unsupported'" class="rounded-2xl bg-ink-50 p-3.5 text-[14px] text-ink-600 dark:bg-night-800 dark:text-ink-300">
					This browser can't show notifications. Try Chrome, Edge, Firefox or Safari.
				</p>
				<template v-else>
					<ToggleSwitch
						v-model="deviceOn"
						:class="busy ? 'pointer-events-none opacity-60' : ''"
						label="Notifications on this device"
						description="Reminders, challenge nudges and your weekly summary."
					/>
					<p v-if="state === 'denied'" class="mt-2 rounded-2xl bg-blush-50 p-3.5 text-[14px] text-blush-700 dark:bg-blush-500/10 dark:text-blush-400">
						Notifications are blocked for this site in your browser. Allow them in the browser's site settings (the icon next to the address), then come back here.
					</p>
					<AppButton v-if="state === 'on'" class="mt-3" variant="secondary" :loading="testing" @click="test"><Send class="h-4 w-4" /> Send a test</AppButton>
				</template>
			</div>

			<!-- what to send (applies to every device with notifications on) -->
			<div v-if="config.enabled && prefs" class="mt-5 space-y-4 border-t border-ink-100 pt-5 dark:border-night-800">
				<div>
					<ToggleSwitch v-model="daily" label="Daily reminder" description="If anything is still open for today." />
					<div v-if="daily" class="mt-2 max-w-[12rem]">
						<label for="daily-time" class="field-label">Time</label>
						<input
							id="daily-time"
							type="time"
							class="field"
							:value="prefs.daily_reminder_time"
							@change="savePref('daily_reminder_time', ($event.target as HTMLInputElement).value || '08:00')"
						/>
					</div>
				</div>
				<ToggleSwitch v-model="weekly" label="Weekly summary" description="How your week went, with one tip." />
				<ToggleSwitch v-model="milestones" label="Badges and challenges" description="When you earn a badge or finish a challenge." />
				<p class="flex items-start gap-2 text-[13px] text-ink-500 dark:text-ink-400">
					<BellRing class="mt-0.5 h-4 w-4 shrink-0" /> Each habit can also have its own reminder time. Set it when you edit the habit.
				</p>
			</div>
		</template>
	</section>
</template>
