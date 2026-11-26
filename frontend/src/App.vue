<script setup lang="ts">
import { LogOut, Sparkles, WifiOff } from "lucide-vue-next"
import { onMounted, ref, watch } from "vue"
import { useRoute } from "vue-router"

import { join } from "@/api/auth"
import { getPushConfig } from "@/api/notifications"
import AppLogo from "@/components/brand/AppLogo.vue"
import AppButton from "@/components/ui/AppButton.vue"
import AlertBanner from "@/components/ui/AlertBanner.vue"
import CelebrationHost from "@/components/growth/CelebrationHost.vue"
import FlameHost from "@/components/habits/FlameHost.vue"
import ConfirmHost from "@/components/ui/ConfirmHost.vue"
import ToastHost from "@/components/ui/ToastHost.vue"
import AppShell from "@/layouts/AppShell.vue"
import { applyUpdate, updateReady } from "@/lib/pwa"
import { resyncPush } from "@/lib/push"
import { signOut } from "@/lib/signout"
import { applyTheme } from "@/lib/theme"
import { useCelebrations } from "@/stores/celebrations"
import { useHabits } from "@/stores/habits"
import { useSession } from "@/stores/session"
import { useSync } from "@/stores/sync"

const session = useSession()
const celebrations = useCelebrations()
const sync = useSync()
const habits = useHabits()
const route = useRoute()
const joining = ref(false)
const joinError = ref("")

onMounted(() => {
	if (window.atomic_guest !== 1) session.load()
})

// rewards earned on another device (or before the app was closed) are celebrated on open
watch(
	() => session.boot?.has_access,
	(ok) => {
		if (!ok) return
		void celebrations.refresh()
		// send anything recorded offline, then keep today's screen in step after each sync
		void sync.start(() => void habits.loadToday(true))
		// already allowed notifications on this device? make sure the server still has it (no prompt)
		void getPushConfig()
			.then((c) => resyncPush(c.public_key))
			.catch(() => undefined)
	},
)

// the profile's theme follows the user across devices
watch(
	() => session.boot?.profile?.theme,
	(t) => {
		if (t) applyTheme(t)
	},
)

async function joinApp() {
	joining.value = true
	joinError.value = ""
	try {
		await join()
		await session.load(true)
	} catch (e) {
		joinError.value = (e as Error).message
	} finally {
		joining.value = false
	}
}

</script>

<template>
	<RouterView v-if="route.meta.public" />

	<div v-else-if="!session.boot && !session.error" class="flex min-h-[100dvh] items-center justify-center" aria-busy="true">
		<AppLogo :size="56" :wordmark="false" class="animate-pulse" />
		<span class="sr-only">Loading</span>
	</div>

	<div v-else-if="session.error" class="flex min-h-[100dvh] items-center justify-center p-6">
		<div class="w-full max-w-sm text-center">
			<WifiOff class="mx-auto h-10 w-10 text-ink-400" />
			<h1 class="mt-4 text-xl font-extrabold">Couldn't load Atomic Streak</h1>
			<p class="mt-2 text-ink-500 dark:text-ink-400">{{ session.error }}</p>
			<AppButton class="mt-6" @click="session.load(true)">Try again</AppButton>
		</div>
	</div>

	<!-- signed in with an existing account (e.g. ERP staff) that hasn't joined the app yet -->
	<div v-else-if="!session.boot?.has_access" class="flex min-h-[100dvh] items-center justify-center p-6">
		<div class="w-full max-w-sm">
			<AppLogo :size="48" :wordmark="false" />
			<h1 class="mt-6 text-[28px] font-extrabold leading-tight">Hi {{ session.firstName }}, start tracking your habits</h1>
			<p class="mt-2 text-[15px] text-ink-500 dark:text-ink-400">
				You're signed in as {{ session.boot?.user }}. Your habits stay private to you.
			</p>
			<AlertBanner v-if="joinError" tone="error" class="mt-5">{{ joinError }}</AlertBanner>
			<AppButton v-if="session.boot?.allow_join" class="mt-7" size="lg" block :loading="joining" @click="joinApp">
				<Sparkles class="h-5 w-5" /> Start using Atomic Streak
			</AppButton>
			<AlertBanner v-else class="mt-7">Atomic Streak isn't open to new members right now.</AlertBanner>
			<AppButton class="mt-3" variant="ghost" block @click="signOut"><LogOut class="h-4 w-4" /> Use another account</AppButton>
		</div>
	</div>

	<AppShell v-else>
		<RouterView v-slot="{ Component, route: r }">
			<Transition enter-active-class="transition-opacity duration-150 ease-out" enter-from-class="opacity-0" mode="out-in">
				<component :is="Component" :key="r.fullPath.split('?')[0]" />
			</Transition>
		</RouterView>
	</AppShell>

	<ToastHost />
	<ConfirmHost />
	<FlameHost />
	<CelebrationHost />

	<div
		v-if="updateReady"
		class="fixed inset-x-4 z-50 mx-auto flex max-w-sm items-center gap-3 rounded-2xl bg-ink-900 px-4 py-3 text-white shadow-lift dark:bg-white dark:text-ink-900"
		style="bottom: max(env(safe-area-inset-bottom), 1rem)"
		role="status"
	>
		<span class="flex-1 text-[14px] font-semibold">A new version is ready.</span>
		<button type="button" class="rounded-xl bg-grape-500 px-3 py-2 text-[13px] font-bold text-white" @click="applyUpdate">Update</button>
	</div>
</template>
