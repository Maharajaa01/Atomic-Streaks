<script setup lang="ts">
import { AlertCircle, CheckCircle2, Info, WifiOff } from "lucide-vue-next"
import { computed } from "vue"

const props = withDefaults(defineProps<{ tone?: "error" | "success" | "info" | "offline" }>(), { tone: "info" })
const icon = computed(() => ({ error: AlertCircle, success: CheckCircle2, info: Info, offline: WifiOff })[props.tone])
</script>

<template>
	<div
		:role="tone === 'error' ? 'alert' : 'status'"
		class="flex items-start gap-2.5 rounded-2xl px-4 py-3 text-[14px] font-medium leading-snug"
		:class="{
			'animate-shake bg-blush-50 text-blush-700 dark:bg-blush-500/10 dark:text-blush-400': tone === 'error',
			'bg-mint-50 text-mint-700 dark:bg-mint-500/10 dark:text-mint-400': tone === 'success',
			'bg-grape-50 text-grape-700 dark:bg-grape-500/10 dark:text-grape-200': tone === 'info',
			'bg-sun-50 text-sun-700 dark:bg-sun-500/10 dark:text-sun-400': tone === 'offline',
		}"
	>
		<component :is="icon" class="mt-px h-[18px] w-[18px] shrink-0" aria-hidden="true" />
		<div><slot /></div>
	</div>
</template>
