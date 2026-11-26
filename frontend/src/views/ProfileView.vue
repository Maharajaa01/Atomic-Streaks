<script setup lang="ts">
import { ChevronRight, Download, Flame, LogOut, Sparkles, Target, Trophy } from "lucide-vue-next"
import { computed, ref } from "vue"

import { updateProfile } from "@/api/habits"
import type { Theme } from "@/api/types"
import NotificationSettings from "@/components/settings/NotificationSettings.vue"
import AppButton from "@/components/ui/AppButton.vue"
import PageHeader from "@/components/ui/PageHeader.vue"
import SegmentedControl from "@/components/ui/SegmentedControl.vue"
import UserAvatar from "@/components/ui/UserAvatar.vue"
import { canInstall, isIOS, isStandalone, promptInstall } from "@/lib/pwa"
import { signOut } from "@/lib/signout"
import { applyTheme, theme } from "@/lib/theme"
import { useHabits } from "@/stores/habits"
import { useSession } from "@/stores/session"
import { useToast } from "@/stores/toast"

const session = useSession()
const habits = useHabits()
const toast = useToast()
const profile = computed(() => session.boot?.profile)

// Chromium lists some zones under old names (e.g. Asia/Calcutta); profiles use current ones.
const LEGACY: Record<string, string> = {
	"Asia/Calcutta": "Asia/Kolkata",
	"Asia/Katmandu": "Asia/Kathmandu",
	"Asia/Rangoon": "Asia/Yangon",
	"Asia/Saigon": "Asia/Ho_Chi_Minh",
	"Europe/Kiev": "Europe/Kyiv",
	"America/Buenos_Aires": "America/Argentina/Buenos_Aires",
}
const timezones = (() => {
	let list: string[] = []
	try {
		list = (Intl as unknown as { supportedValuesOf: (k: string) => string[] }).supportedValuesOf("timeZone")
	} catch {
		/* older browsers: just the profile's own zone */
	}
	// the saved zone must always be selectable, or the box shows blank
	const all = new Set([...list.map((z) => LEGACY[z] ?? z), profile.value?.timezone ?? "UTC"])
	return [...all].sort()
})()
const tz = ref(profile.value?.timezone ?? "UTC")
const weekStart = ref<"Monday" | "Sunday">(profile.value?.week_starts_on ?? "Monday")
const themeChoice = ref<Theme>(theme.value)

async function save(field: string, value: unknown, done = "Saved") {
	try {
		await updateProfile({ [field]: value })
		if (session.boot?.profile) Object.assign(session.boot.profile, { [field]: value })
		if (field !== "theme") void habits.loadToday(true)
		toast.success(done)
	} catch (e) {
		toast.error((e as Error).message)
	}
}

function setTheme(t: Theme) {
	themeChoice.value = t
	applyTheme(t)
	void save("theme", t, "Theme updated")
}


/** Same curve as the server (services/xp.py): level L starts at 50 * L * (L - 1) XP. */
const level = computed(() => {
	const xp = profile.value?.xp ?? 0
	const lvl = Math.max(profile.value?.level ?? 1, 1)
	const start = 50 * lvl * (lvl - 1)
	const next = 50 * (lvl + 1) * lvl
	return { level: lvl, toNext: Math.max(next - xp, 0), progress: Math.min(100, Math.max(0, Math.round((100 * (xp - start)) / (next - start)))) }
})

const stats = computed(() => [
	{ label: "Current streak", value: habits.today?.streak.current ?? profile.value?.current_streak ?? 0, icon: Flame, color: "#FF9F43" },
	{ label: "Best streak", value: habits.today?.streak.longest ?? profile.value?.longest_streak ?? 0, icon: Trophy, color: "#7657F6" },
	{ label: "Check-ins", value: habits.today?.streak.total_completions ?? profile.value?.total_completions ?? 0, icon: Target, color: "#26C281" },
])
</script>

<template>
	<div>
		<PageHeader title="Profile" />

		<section class="flex items-center gap-4 rounded-4xl bg-white p-5 shadow-soft dark:bg-night-900">
			<UserAvatar :size="72" />
			<div class="min-w-0">
				<h2 class="truncate text-[22px] font-extrabold">{{ session.displayName }}</h2>
				<p class="truncate text-[14px] text-ink-500 dark:text-ink-400">{{ session.boot?.user }}</p>
				<p class="mt-1.5 flex flex-wrap gap-1.5 text-[13px] font-bold">
					<span class="inline-flex items-center gap-1 rounded-full bg-grape-50 px-2.5 py-0.5 text-grape-700 dark:bg-grape-500/15 dark:text-grape-200">
						<Sparkles class="h-3.5 w-3.5" /> Level {{ profile?.level ?? 1 }}
					</span>
					<span class="rounded-full bg-sun-50 px-2.5 py-0.5 text-sun-700 dark:bg-sun-500/15 dark:text-sun-400">{{ profile?.xp ?? 0 }} XP</span>
				</p>
			</div>
		</section>

		<RouterLink
			:to="{ name: 'challenges', query: { tab: 'badges' } }"
			class="mt-4 flex items-center gap-4 rounded-4xl bg-white p-5 shadow-soft transition hover:shadow-md dark:bg-night-900"
		>
			<span class="min-w-0 flex-1">
				<span class="flex items-baseline justify-between gap-2 text-[14px] font-bold">
					<span>Level {{ level.level }}</span>
					<span class="text-ink-500 dark:text-ink-400">{{ level.toNext }} XP to level {{ level.level + 1 }}</span>
				</span>
				<span class="mt-2 block h-2.5 overflow-hidden rounded-full bg-ink-100 dark:bg-night-800" role="progressbar" :aria-valuenow="level.progress" aria-valuemin="0" aria-valuemax="100" aria-label="Progress to the next level">
					<span class="block h-full rounded-full bg-gradient-to-r from-grape-500 to-blush-500" :style="{ width: `${level.progress}%` }" />
				</span>
				<span class="mt-2 block text-[13px] font-semibold text-grape-600 dark:text-grape-300">See your badges</span>
			</span>
			<ChevronRight class="h-5 w-5 text-ink-400" />
		</RouterLink>

		<dl class="mt-4 grid grid-cols-3 gap-3">
			<div v-for="s in stats" :key="s.label" class="rounded-3xl bg-white p-4 shadow-soft dark:bg-night-900">
				<component :is="s.icon" class="h-5 w-5" :style="{ color: s.color }" :stroke-width="2.5" />
				<dd class="mt-2 font-display text-[26px] font-extrabold leading-none">{{ s.value }}</dd>
				<dt class="mt-1 text-[12px] font-semibold text-ink-500 dark:text-ink-400">{{ s.label }}</dt>
			</div>
		</dl>

		<section class="mt-5 space-y-5 rounded-4xl bg-white p-5 shadow-soft dark:bg-night-900">
			<h2 class="text-[18px] font-extrabold">Settings</h2>
			<div>
				<span class="field-label">Appearance</span>
				<SegmentedControl
					:model-value="themeChoice"
					:options="[{ value: 'System', label: 'Auto' }, { value: 'Light', label: 'Light' }, { value: 'Dark', label: 'Dark' }]"
					label="Appearance"
					@update:model-value="setTheme"
				/>
			</div>
			<div>
				<label for="tz" class="field-label">Timezone</label>
				<select id="tz" v-model="tz" class="field" @change="save('timezone', tz, 'Timezone saved. Your days now follow it.')">
					<option v-for="z in timezones" :key="z" :value="z">{{ z.replace(/_/g, " ") }}</option>
				</select>
				<p class="mt-1.5 text-[13px] text-ink-500 dark:text-ink-400">Your day starts and ends at midnight in this timezone.</p>
			</div>
			<div>
				<span class="field-label">Week starts on</span>
				<SegmentedControl
					v-model="weekStart"
					:options="[{ value: 'Monday', label: 'Monday' }, { value: 'Sunday', label: 'Sunday' }]"
					label="Week starts on"
					@update:model-value="(v: string) => save('week_starts_on', v)"
				/>
			</div>
		</section>

		<NotificationSettings />

		<section class="mt-5 space-y-3">
			<AppButton v-if="canInstall && !isStandalone()" variant="secondary" size="lg" block @click="promptInstall"><Download class="h-5 w-5" /> Install the app</AppButton>
			<p v-else-if="isIOS() && !isStandalone()" class="rounded-3xl bg-sky-50 p-4 text-[14px] text-sky-700 dark:bg-sky-500/10 dark:text-sky-400">
				To install on iPhone or iPad: tap the Share button in Safari, then "Add to Home Screen".
			</p>
			<AppButton variant="ghost" size="lg" block @click="signOut"><LogOut class="h-5 w-5" /> Sign out</AppButton>
		</section>
	</div>
</template>
