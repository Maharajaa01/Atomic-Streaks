<script setup lang="ts">
/** Sticky page header on phones (with optional back link); a plain title row on desktop. */
import { ChevronLeft } from "lucide-vue-next"
import type { RouteLocationRaw } from "vue-router"

defineProps<{ title: string; subtitle?: string; back?: RouteLocationRaw }>()
</script>

<template>
	<header
		class="sticky top-0 z-30 -mx-4 mb-4 flex items-center gap-2 bg-ink-50/85 px-4 pb-3 backdrop-blur-lg dark:bg-night-950/85 lg:static lg:mx-0 lg:mb-6 lg:bg-transparent lg:px-0 lg:pt-0 lg:backdrop-blur-none"
		style="padding-top: max(env(safe-area-inset-top), 0.75rem)"
	>
		<RouterLink
			v-if="back"
			:to="back"
			class="-ml-2 flex h-11 w-11 items-center justify-center rounded-2xl text-ink-600 hover:bg-ink-100 dark:text-ink-300 dark:hover:bg-night-800"
			aria-label="Back"
		>
			<ChevronLeft class="h-6 w-6" />
		</RouterLink>
		<div class="min-w-0 flex-1">
			<h1 class="truncate text-[26px] font-extrabold leading-tight text-ink-900 dark:text-white lg:text-3xl">{{ title }}</h1>
			<p v-if="subtitle" class="truncate text-[14px] text-ink-500 dark:text-ink-400">{{ subtitle }}</p>
		</div>
		<div class="flex shrink-0 items-center gap-2"><slot name="actions" /></div>
	</header>
</template>
