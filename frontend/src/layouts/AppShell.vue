<script setup lang="ts">
import { Plus } from "lucide-vue-next"
import { computed } from "vue"
import { useRoute } from "vue-router"

import AppLogo from "@/components/brand/AppLogo.vue"
import SyncBanner from "@/components/ui/SyncBanner.vue"
import UserAvatar from "@/components/ui/UserAvatar.vue"
import { useSession } from "@/stores/session"

import { PRIMARY, SECONDARY } from "./navigation"

const route = useRoute()
const session = useSession()

/** Which tab a route belongs to (detail pages light up their parent tab). */
const section = computed(() => (route.meta.section as string | undefined) ?? (route.name as string))
const hideTabs = computed(() => !!route.meta.hideTabs)
</script>

<template>
	<div class="min-h-[100dvh]">
		<a href="#main" class="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[80] focus:rounded-xl focus:bg-white focus:px-4 focus:py-2">
			Skip to content
		</a>

		<!-- desktop sidebar -->
		<aside class="fixed inset-y-0 left-0 z-40 hidden w-64 flex-col border-r border-ink-200/70 bg-white px-4 py-6 dark:border-night-800 dark:bg-night-900 lg:flex">
			<RouterLink to="/" class="mb-8 rounded-xl px-2"><AppLogo :size="36" /></RouterLink>
			<nav aria-label="Main" class="flex flex-col gap-1">
				<RouterLink
					v-for="item in [...PRIMARY, ...SECONDARY]"
					:key="item.name"
					:to="{ name: item.name }"
					class="group flex h-12 items-center gap-3 rounded-2xl px-3 text-[15px] font-semibold transition-colors"
					:class="
						section === item.name
							? 'bg-grape-50 text-grape-700 dark:bg-grape-500/15 dark:text-grape-200'
							: 'text-ink-600 hover:bg-ink-100 dark:text-ink-300 dark:hover:bg-night-800'
					"
					:aria-current="section === item.name ? 'page' : undefined"
				>
					<span
						class="flex h-8 w-8 items-center justify-center rounded-xl transition-colors"
						:style="section === item.name ? { background: item.color, color: '#fff' } : {}"
					>
						<component :is="item.icon" class="h-[18px] w-[18px]" :stroke-width="2.3" />
					</span>
					{{ item.label }}
				</RouterLink>
			</nav>
			<RouterLink
				:to="{ name: 'habit-new' }"
				class="mt-6 flex h-12 items-center justify-center gap-2 rounded-2xl bg-gradient-to-br from-grape-500 to-grape-600 font-bold text-white shadow-lift hover:to-grape-700"
			>
				<Plus class="h-5 w-5" :stroke-width="2.6" /> New habit
			</RouterLink>
			<RouterLink
				:to="{ name: 'profile' }"
				class="mt-auto flex items-center gap-3 rounded-2xl p-2 hover:bg-ink-100 dark:hover:bg-night-800"
			>
				<UserAvatar :size="40" />
				<span class="min-w-0">
					<span class="block truncate text-[14px] font-bold">{{ session.displayName }}</span>
					<span class="block text-[12px] text-ink-500 dark:text-ink-400">Level {{ session.boot?.profile?.level ?? 1 }}</span>
				</span>
			</RouterLink>
		</aside>

		<main id="main" class="mx-auto max-w-3xl px-4 lg:ml-64 lg:max-w-none lg:px-10 lg:py-8" :class="hideTabs ? 'pb-10' : 'pb-32 lg:pb-10'">
			<div class="mx-auto lg:max-w-4xl"><SyncBanner class="mt-4 lg:mt-0" /><slot /></div>
		</main>

		<!-- phone tab bar -->
		<nav
			v-if="!hideTabs"
			aria-label="Main"
			class="fixed inset-x-0 bottom-0 z-40 border-t border-ink-200/70 bg-white/95 backdrop-blur-lg dark:border-night-800 dark:bg-night-900/95 lg:hidden"
			style="padding-bottom: env(safe-area-inset-bottom)"
		>
			<ul class="mx-auto flex max-w-lg">
				<li v-for="item in PRIMARY" :key="item.name" class="flex-1">
					<RouterLink
						:to="{ name: item.name }"
						class="flex h-16 flex-col items-center justify-center gap-1 text-[11px] font-bold"
						:class="section === item.name ? 'text-ink-900 dark:text-white' : 'text-ink-400 dark:text-ink-500'"
						:aria-current="section === item.name ? 'page' : undefined"
					>
						<span
							class="flex h-8 w-14 items-center justify-center rounded-full transition-all duration-200"
							:style="section === item.name ? { background: item.color, color: '#fff' } : {}"
						>
							<component :is="item.icon" class="h-[22px] w-[22px]" :stroke-width="section === item.name ? 2.5 : 2.1" />
						</span>
						{{ item.label }}
					</RouterLink>
				</li>
			</ul>
		</nav>
	</div>
</template>
