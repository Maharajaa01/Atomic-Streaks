<script setup lang="ts">
import { AlertCircle, CheckCircle2, Info, X } from "lucide-vue-next"

import { useToast } from "@/stores/toast"

const toast = useToast()
const ICON = { success: CheckCircle2, error: AlertCircle, info: Info }
</script>

<template>
	<div
		class="pointer-events-none fixed inset-x-0 z-[60] flex flex-col items-center gap-2 px-4 lg:bottom-6 lg:left-64"
		style="bottom: calc(env(safe-area-inset-bottom) + 5.5rem)"
		aria-live="polite"
	>
		<TransitionGroup
			enter-active-class="transition duration-200 ease-out"
			enter-from-class="translate-y-3 opacity-0"
			leave-active-class="transition duration-150 ease-in"
			leave-to-class="opacity-0"
		>
			<div
				v-for="t in toast.items"
				:key="t.id"
				class="pointer-events-auto flex w-full max-w-md items-center gap-3 rounded-2xl bg-ink-900 px-4 py-3 text-white shadow-lift dark:bg-white dark:text-ink-900"
				:role="t.tone === 'error' ? 'alert' : 'status'"
			>
				<component
					:is="ICON[t.tone]"
					class="h-5 w-5 shrink-0"
					:class="{ 'text-mint-400 dark:text-mint-600': t.tone === 'success', 'text-blush-400 dark:text-blush-600': t.tone === 'error' }"
				/>
				<p class="flex-1 text-[14px] font-semibold leading-snug">{{ t.message }}</p>
				<button
					v-if="t.action"
					type="button"
					class="rounded-lg px-2 py-1 text-[13px] font-bold text-grape-300 hover:bg-white/10 dark:text-grape-600 dark:hover:bg-ink-100"
					@click="t.action.run(), toast.dismiss(t.id)"
				>
					{{ t.action.label }}
				</button>
				<button type="button" class="rounded-lg p-1 opacity-60 hover:opacity-100" aria-label="Dismiss" @click="toast.dismiss(t.id)">
					<X class="h-4 w-4" />
				</button>
			</div>
		</TransitionGroup>
	</div>
</template>
