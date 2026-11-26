<script setup lang="ts">
import type { Component } from "vue"

defineOptions({ inheritAttrs: false })

const model = defineModel<string>({ default: "" })
defineProps<{ id: string; label: string; icon?: Component; error?: string; hint?: string }>()
</script>

<template>
	<div>
		<label :for="id" class="field-label">{{ label }}</label>
		<div class="relative">
			<component
				:is="icon"
				v-if="icon"
				class="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-ink-400"
				aria-hidden="true"
			/>
			<input
				:id="id"
				v-model="model"
				v-bind="$attrs"
				class="field"
				:class="[icon && 'pl-12', error && 'field-invalid', $slots.trailing && 'pr-14']"
				:aria-invalid="!!error || undefined"
				:aria-describedby="error ? `${id}-error` : hint ? `${id}-hint` : undefined"
			/>
			<div v-if="$slots.trailing" class="absolute right-1.5 top-1/2 -translate-y-1/2"><slot name="trailing" /></div>
		</div>
		<p v-if="error" :id="`${id}-error`" class="mt-1.5 text-[13px] font-medium text-blush-700 dark:text-blush-400">{{ error }}</p>
		<p v-else-if="hint" :id="`${id}-hint`" class="mt-1.5 text-[13px] text-ink-500 dark:text-ink-400">{{ hint }}</p>
		<slot name="below" />
	</div>
</template>
