<script setup lang="ts" generic="T extends string">
const model = defineModel<T>({ required: true })
defineProps<{ options: { value: T; label: string; hint?: string }[]; label: string }>()
</script>

<template>
	<div role="radiogroup" :aria-label="label" class="flex gap-1 rounded-2xl bg-ink-100 p-1 dark:bg-night-800" :class="options.length > 4 && 'flex-wrap'">
		<button
			v-for="o in options"
			:key="o.value"
			type="button"
			role="radio"
			:aria-checked="model === o.value"
			class="min-h-[44px] min-w-0 flex-1 whitespace-nowrap rounded-xl py-1.5 font-bold transition-all"
			:class="[options.length > 4 ? 'min-w-[5.5rem] px-2 text-[14px]' : 'px-2 text-[14px]', model === o.value ? 'bg-white text-ink-900 shadow-soft dark:bg-night-600 dark:text-white' : 'text-ink-500 hover:text-ink-800 dark:text-ink-400 dark:hover:text-ink-100']"
			@click="model = o.value"
		>
			{{ o.label }}
			<span v-if="o.hint" class="block text-[11px] font-semibold opacity-70">{{ o.hint }}</span>
		</button>
	</div>
</template>
