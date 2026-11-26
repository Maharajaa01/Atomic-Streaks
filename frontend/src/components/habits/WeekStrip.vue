<script setup lang="ts">
import type { DayProgress } from "@/api/types"
import { parseDay } from "@/lib/dates"

import ProgressRing from "../ui/ProgressRing.vue"

defineProps<{ days: DayProgress[] }>()

function ringColor(d: DayProgress) {
	if (d.percent >= 100) return "#26C281"
	if (d.percent >= 50) return "#4D8DFF"
	return "#FF9F43"
}
</script>

<template>
	<section class="rounded-4xl bg-white p-4 shadow-soft dark:bg-night-900" aria-labelledby="week-title">
		<h2 id="week-title" class="mb-3 px-1 text-[17px] font-extrabold">This week</h2>
		<ol class="grid grid-cols-7 gap-1">
			<li
				v-for="d in days"
				:key="d.date"
				class="flex flex-col items-center gap-1.5 rounded-2xl py-2"
				:class="d.is_today && 'bg-grape-50 dark:bg-grape-500/15'"
				:aria-current="d.is_today ? 'date' : undefined"
				:aria-label="d.is_future ? `${d.weekday}: upcoming` : d.scheduled ? `${d.weekday}: ${d.completed} of ${d.scheduled} done` : `${d.weekday}: nothing scheduled`"
			>
				<span class="text-[11px] font-bold" :class="d.is_today ? 'text-grape-600 dark:text-grape-300' : 'text-ink-400'">{{ d.weekday }}</span>
				<ProgressRing :value="d.is_future ? 0 : d.percent" :size="36" :stroke="4" :color="ringColor(d)">
					<span class="text-[12px] font-bold" :class="d.is_future ? 'text-ink-300 dark:text-night-600' : 'text-ink-700 dark:text-ink-200'">
						{{ parseDay(d.date).getDate() }}
					</span>
				</ProgressRing>
			</li>
		</ol>
	</section>
</template>
