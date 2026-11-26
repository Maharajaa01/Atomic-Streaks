<script setup lang="ts">
/**
 * The sign-in hero: four weeks of a habit chain filling in, day by day, in category colours.
 * One day is missed on purpose and the chain carries on after it: the app's recovery message
 * ("missed a day? start again") told without words. Plays once; respects reduced motion.
 */
import { computed } from "vue"

const props = withDefaults(defineProps<{ weeks?: number; compact?: boolean }>(), { weeks: 4 })

const COLORS = ["#FFD166", "#26C281", "#4D8DFF", "#F56FA1", "#FF9F43", "#FFFFFF"]
// a fixed mix where no cell matches its neighbour to the left or above: many habits, one chain
const SEQUENCE = "1523405043125431203152042041"
const MISSED = 5

const cells = computed(() => {
	const total = props.weeks * 7
	return Array.from({ length: total }, (_, i) => ({
		i,
		state: i === total - 1 ? "today" : i === MISSED ? "missed" : "done",
		color: COLORS[Number(SEQUENCE[i % SEQUENCE.length])],
		delay: `${120 + i * 45}ms`,
	}))
})
const streak = computed(() => props.weeks * 7 - 1 - (MISSED + 1))
</script>

<template>
	<figure :aria-label="`A habit chain with a ${streak}-day streak`">
		<div class="grid grid-cols-7" :class="compact ? 'gap-1.5' : 'gap-2.5'">
			<span
				v-for="c in cells"
				:key="c.i"
				class="aspect-square animate-cell-in"
				:class="[
					compact ? 'rounded-lg' : 'rounded-xl',
					c.state === 'missed' && 'border-2 border-dashed border-white/40',
					c.state === 'today' && 'border-2 border-white/90 bg-white/10',
				]"
				:style="{ animationDelay: c.delay, backgroundColor: c.state === 'done' ? c.color : undefined }"
			/>
		</div>
		<figcaption v-if="!compact" class="mt-6 flex items-end gap-3 text-white">
			<span class="font-display text-6xl font-extrabold leading-none tracking-tight">{{ streak }}</span>
			<span class="pb-1 text-[15px] leading-snug text-white/80">
				days in a row.<br />One missed day didn't break it.
			</span>
		</figcaption>
	</figure>
</template>
