<script setup lang="ts">
import { computed } from "vue"

import type { DaySummary } from "@/api/types"
import { parseDay } from "@/lib/dates"

import ProgressRing from "../ui/ProgressRing.vue"

const props = defineProps<{ day: DaySummary; selected: boolean; outside: boolean; isToday: boolean }>()
const n = computed(() => parseDay(props.day.date).getDate())

const label = computed(() => {
	const d = props.day
	const date = parseDay(d.date).toLocaleDateString(undefined, { weekday: "long", day: "numeric", month: "long" })
	switch (d.state) {
		case "done":
			return `${date}: all ${d.scheduled} done`
		case "partial":
			return `${date}: ${d.completed} of ${d.scheduled} done`
		case "missed":
			return `${date}: missed`
		case "pending":
			return `${date}: ${d.scheduled} still to do`
		case "bonus":
			return `${date}: extra check-in`
		case "future":
			return `${date}: upcoming`
		default:
			return `${date}: nothing scheduled`
	}
})
</script>

<template>
	<button
		type="button"
		class="relative flex aspect-square min-h-[44px] w-full items-center justify-center rounded-2xl transition"
		:class="[outside && 'opacity-35', selected ? 'ring-[3px] ring-ink-900 ring-offset-2 dark:ring-white dark:ring-offset-night-900' : 'hover:bg-ink-100 dark:hover:bg-night-800']"
		:aria-label="label"
		:aria-pressed="selected"
	>
		<span
			v-if="day.state === 'done'"
			class="flex h-[86%] w-[86%] items-center justify-center rounded-full bg-mint-600 font-display text-[15px] font-extrabold text-white"
		>{{ n }}</span>
		<ProgressRing v-else-if="day.state === 'partial'" :value="day.percent" :size="40" :stroke="4" color="#2F6FE6" class="scale-90 sm:scale-100">
			<span class="font-display text-[15px] font-extrabold text-ink-800 dark:text-ink-100">{{ n }}</span>
		</ProgressRing>
		<span
			v-else
			class="flex h-[86%] w-[86%] items-center justify-center rounded-full font-display text-[15px] font-bold"
			:class="{
				'border-2 border-dashed border-blush-400 text-blush-700 dark:text-blush-400': day.state === 'missed',
				'border-2 border-grape-500 text-grape-700 dark:text-grape-300': day.state === 'pending',
				'text-ink-700 dark:text-ink-200': day.state === 'none' || day.state === 'bonus',
				'text-ink-300 dark:text-night-600': day.state === 'future',
			}"
		>{{ n }}</span>
		<span v-if="day.bonus && day.state !== 'future'" class="absolute bottom-1 h-1.5 w-1.5 rounded-full bg-sun-500" aria-hidden="true" />
		<span v-if="isToday" class="absolute -top-0.5 right-1 h-2 w-2 rounded-full bg-grape-500" aria-hidden="true" />
	</button>
</template>
