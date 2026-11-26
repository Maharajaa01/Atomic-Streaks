<script setup lang="ts">
import { Eye, EyeOff, Lock } from "lucide-vue-next"
import { computed, ref } from "vue"

import { passwordScore } from "@/lib/password"
import TextField from "./TextField.vue"

const model = defineModel<string>({ default: "" })
const props = defineProps<{ id: string; label: string; error?: string; autocomplete?: string; meter?: boolean; disabled?: boolean }>()
const visible = ref(false)

const score = computed(() => passwordScore(model.value))
const LEVELS = [
	{ label: "Too short", bar: "bg-blush-500", text: "text-blush-700 dark:text-blush-400" },
	{ label: "Weak", bar: "bg-blush-500", text: "text-blush-700 dark:text-blush-400" },
	{ label: "Okay", bar: "bg-tangerine-500", text: "text-tangerine-700 dark:text-tangerine-400" },
	{ label: "Good", bar: "bg-sky-500", text: "text-sky-700 dark:text-sky-400" },
	{ label: "Strong", bar: "bg-mint-500", text: "text-mint-700 dark:text-mint-400" },
]
const level = computed(() => LEVELS[score.value]!)
</script>

<template>
	<TextField
		:id="props.id"
		v-model="model"
		:label="props.label"
		:icon="Lock"
		:error="props.error"
		:type="visible ? 'text' : 'password'"
		:autocomplete="props.autocomplete ?? 'current-password'"
		:disabled="props.disabled"
		autocapitalize="none"
		spellcheck="false"
	>
		<template #trailing>
			<button
				type="button"
				class="flex h-11 w-11 items-center justify-center rounded-xl text-ink-400 hover:bg-ink-100 hover:text-ink-700 dark:hover:bg-night-800 dark:hover:text-ink-200"
				:aria-label="visible ? 'Hide password' : 'Show password'"
				:aria-pressed="visible"
				@click="visible = !visible"
			>
				<EyeOff v-if="visible" class="h-5 w-5" />
				<Eye v-else class="h-5 w-5" />
			</button>
		</template>
		<template v-if="props.meter && model" #below>
			<div class="mt-2 flex items-center gap-3" aria-live="polite">
				<div class="flex flex-1 gap-1">
					<span
						v-for="i in 4"
						:key="i"
						class="h-1.5 flex-1 rounded-full transition-colors"
						:class="i <= score ? level.bar : 'bg-ink-200 dark:bg-night-700'"
					/>
				</div>
				<span class="w-16 text-right text-[12px] font-semibold" :class="level.text">{{ level.label }}</span>
			</div>
		</template>
	</TextField>
</template>
