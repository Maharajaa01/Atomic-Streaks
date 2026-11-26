<script setup lang="ts">
import { LOGO } from "@/lib/pwa"

withDefaults(defineProps<{ size?: number; wordmark?: boolean; light?: boolean }>(), { size: 40, wordmark: true })
</script>

<template>
	<span class="inline-flex items-center gap-2.5">
		<img
			:src="LOGO"
			alt=""
			:width="size"
			:height="size"
			class="shrink-0 rounded-[24%] drop-shadow-sm"
			:class="light && 'ring-2 ring-white/40'"
		/>
		<span
			v-if="wordmark"
			class="font-display text-[20px] font-extrabold tracking-tight"
			:class="light ? 'text-white' : 'text-ink-900 dark:text-white'"
		>
			Atomic Streak
		</span>
	</span>
</template>
