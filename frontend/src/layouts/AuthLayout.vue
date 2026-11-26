<script setup lang="ts">
import AppLogo from "@/components/brand/AppLogo.vue"
import HabitChain from "@/components/brand/HabitChain.vue"

defineProps<{ title: string; subtitle?: string }>()
</script>

<template>
	<div class="min-h-[100dvh] bg-white dark:bg-night-900 lg:grid lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)] lg:bg-ink-50 lg:dark:bg-night-950">
		<!-- hero: compact band on phones, full panel on desktop -->
		<aside
			class="relative overflow-hidden bg-gradient-to-br from-[#8B6CFF] via-grape-500 to-sky-500 px-6 pb-14 text-white
				lg:m-4 lg:flex lg:flex-col lg:justify-between lg:rounded-4xl lg:p-12"
			style="padding-top: max(env(safe-area-inset-top), 1.5rem)"
		>
			<div aria-hidden="true" class="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-sun-500/30 blur-3xl" />
			<div aria-hidden="true" class="pointer-events-none absolute -bottom-32 -left-20 h-80 w-80 rounded-full bg-blush-500/30 blur-3xl" />

			<RouterLink to="/login" class="relative inline-block rounded-xl"><AppLogo light :size="36" /></RouterLink>

			<div class="relative mt-6 lg:mt-0">
				<p class="max-w-md font-display text-[28px] font-extrabold leading-[1.05] tracking-tight sm:text-4xl lg:text-6xl">
					Small habits. Remarkable change.
				</p>
				<p class="mt-3 hidden max-w-sm text-[16px] leading-relaxed text-white/80 lg:block">
					Check in each day, watch your chain grow, and get 1% better without the guilt.
				</p>
			</div>

			<div class="relative mt-6 max-w-[15rem] lg:mt-0 lg:max-w-md">
				<HabitChain class="lg:hidden" :weeks="2" compact />
				<HabitChain class="hidden lg:block" :weeks="4" />
			</div>
		</aside>

		<!-- form sheet -->
		<main
			class="relative -mt-8 rounded-t-4xl bg-white px-6 pt-8 shadow-sheet dark:bg-night-900
				lg:mt-0 lg:flex lg:items-center lg:justify-center lg:rounded-none lg:bg-transparent lg:shadow-none lg:dark:bg-transparent"
			style="padding-bottom: max(env(safe-area-inset-bottom), 2rem)"
		>
			<div class="mx-auto w-full max-w-sm animate-fade-up">
				<h1 class="text-[28px] font-extrabold leading-tight text-ink-900 dark:text-white">{{ title }}</h1>
				<p v-if="subtitle" class="mt-1.5 text-[15px] text-ink-500 dark:text-ink-400">{{ subtitle }}</p>
				<div class="mt-7"><slot /></div>
				<div v-if="$slots.footer" class="mt-8 text-center text-[14px] text-ink-500 dark:text-ink-400"><slot name="footer" /></div>
			</div>
		</main>
	</div>
</template>
