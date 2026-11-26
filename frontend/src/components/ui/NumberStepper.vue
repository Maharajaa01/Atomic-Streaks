<script setup lang="ts">
import { Minus, Plus } from "lucide-vue-next"

const model = defineModel<number>({ required: true })
const props = withDefaults(defineProps<{ label: string; min?: number; max?: number; step?: number }>(), { min: 1, max: 100000, step: 1 })

function set(v: number) {
	if (Number.isNaN(v)) return
	model.value = Math.min(props.max, Math.max(props.min, Math.round(v * 100) / 100))
}
</script>

<template>
	<div class="flex h-[52px] items-center rounded-2xl border-2 border-ink-200 bg-white dark:border-night-700 dark:bg-night-850">
		<button type="button" class="flex h-full w-12 items-center justify-center text-ink-500 disabled:opacity-30" :aria-label="`Decrease ${label}`" :disabled="model <= min" @click="set(model - step)">
			<Minus class="h-5 w-5" :stroke-width="2.6" />
		</button>
		<input
			:value="model"
			type="number"
			inputmode="decimal"
			:min="min"
			:max="max"
			:step="step"
			:aria-label="label"
			class="h-full w-full min-w-0 bg-transparent text-center font-display text-xl font-extrabold text-ink-900 outline-none [appearance:textfield] dark:text-white [&::-webkit-inner-spin-button]:appearance-none"
			@change="set(Number(($event.target as HTMLInputElement).value))"
		/>
		<button type="button" class="flex h-full w-12 items-center justify-center text-ink-500 disabled:opacity-30" :aria-label="`Increase ${label}`" :disabled="model >= max" @click="set(model + step)">
			<Plus class="h-5 w-5" :stroke-width="2.6" />
		</button>
	</div>
</template>
