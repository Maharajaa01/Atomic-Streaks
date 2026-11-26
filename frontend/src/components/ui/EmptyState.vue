<script setup lang="ts">
import type { Component } from "vue"

defineProps<{ icon?: Component; title: string; body?: string; tone?: string }>()
</script>

<template>
	<div class="flex flex-col items-center px-6 py-10 text-center">
		<div
			v-if="icon"
			class="mb-5 flex h-20 w-20 rotate-[-6deg] items-center justify-center rounded-[1.75rem] bg-gradient-to-br from-grape-400 to-sky-500 text-white shadow-lift"
		>
			<component :is="icon" class="h-9 w-9" :stroke-width="2.2" />
		</div>
		<h2 class="text-xl font-extrabold text-ink-900 dark:text-white">{{ title }}</h2>
		<p v-if="body" class="mt-2 max-w-xs text-[15px] leading-relaxed text-ink-500 dark:text-ink-400">{{ body }}</p>
		<div v-if="$slots.default" class="mt-6"><slot /></div>
	</div>
</template>
