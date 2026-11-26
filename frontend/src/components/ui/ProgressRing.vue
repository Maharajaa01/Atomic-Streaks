<script setup lang="ts">
import { computed } from "vue"

const props = withDefaults(
	defineProps<{ value: number; size?: number; stroke?: number; color?: string; track?: string; label?: string }>(),
	{ size: 64, stroke: 8, color: "#7657F6", track: "rgba(120,120,140,.16)" },
)
const r = computed(() => (props.size - props.stroke) / 2)
const c = computed(() => 2 * Math.PI * r.value)
const offset = computed(() => c.value * (1 - Math.min(Math.max(props.value, 0), 100) / 100))
</script>

<template>
	<div class="relative inline-flex shrink-0 items-center justify-center" :style="{ width: `${size}px`, height: `${size}px` }">
		<svg :width="size" :height="size" class="-rotate-90" role="img" :aria-label="label ?? `${Math.round(value)}% complete`">
			<circle :cx="size / 2" :cy="size / 2" :r="r" fill="none" :stroke="track" :stroke-width="stroke" />
			<circle
				:cx="size / 2"
				:cy="size / 2"
				:r="r"
				fill="none"
				:stroke="color"
				:stroke-width="stroke"
				stroke-linecap="round"
				:stroke-dasharray="c"
				:stroke-dashoffset="offset"
				class="transition-[stroke-dashoffset] duration-500 ease-out"
			/>
		</svg>
		<div class="absolute inset-0 flex items-center justify-center"><slot /></div>
	</div>
</template>
