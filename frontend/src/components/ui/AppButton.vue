<script setup lang="ts">
import { Loader2 } from "lucide-vue-next"

withDefaults(
	defineProps<{
		variant?: "primary" | "secondary" | "ghost" | "danger"
		size?: "md" | "lg"
		type?: "button" | "submit"
		block?: boolean
		loading?: boolean
		disabled?: boolean
	}>(),
	{ variant: "primary", size: "md", type: "button" },
)
</script>

<template>
	<button
		:type="type"
		:disabled="disabled || loading"
		:aria-busy="loading || undefined"
		class="relative inline-flex select-none items-center justify-center gap-2 rounded-2xl font-bold transition
			active:scale-[.98] disabled:cursor-not-allowed disabled:opacity-60 disabled:active:scale-100"
		:class="[
			block && 'w-full',
			size === 'lg' ? 'h-14 px-6 text-[16px]' : 'h-11 px-4 text-[14px]',
			variant === 'primary' &&
				'bg-gradient-to-br from-grape-500 to-grape-600 text-white shadow-lift hover:from-grape-500 hover:to-grape-700',
			variant === 'secondary' &&
				'border-2 border-ink-200 bg-white text-ink-800 hover:border-ink-300 dark:border-night-700 dark:bg-night-850 dark:text-ink-100',
			variant === 'ghost' && 'text-grape-600 hover:bg-grape-50 dark:text-grape-300 dark:hover:bg-night-800',
			variant === 'danger' && 'bg-blush-600 text-white hover:bg-blush-700',
		]"
	>
		<Loader2 v-if="loading" class="h-5 w-5 animate-spin" aria-hidden="true" />
		<slot v-else />
		<span v-if="loading" class="sr-only">Working…</span>
	</button>
</template>
