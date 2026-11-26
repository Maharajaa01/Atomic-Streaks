<script setup lang="ts">
import { computed } from "vue"

import { iconFor } from "@/lib/icons"

const props = withDefaults(defineProps<{ icon?: string | null; color?: string | null; size?: "sm" | "md" | "lg" }>(), { size: "md" })
const component = computed(() => iconFor(props.icon))
</script>

<template>
	<span
		class="flex shrink-0 items-center justify-center text-white shadow-sm"
		:class="{
			'h-9 w-9 rounded-xl': size === 'sm',
			'h-12 w-12 rounded-2xl': size === 'md',
			'h-16 w-16 rounded-3xl': size === 'lg',
		}"
		:style="{ background: `linear-gradient(140deg, ${color || '#7657F6'}, ${color || '#7657F6'}cc)` }"
		aria-hidden="true"
	>
		<component :is="component" :class="size === 'lg' ? 'h-8 w-8' : size === 'md' ? 'h-6 w-6' : 'h-[18px] w-[18px]'" :stroke-width="2.2" />
	</span>
</template>
