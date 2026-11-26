<script setup lang="ts">
/**
 * GitHub-style heatmap: one column per week, one row per weekday. Shows as many recent weeks as
 * fit the width (never scrolls sideways). Cells carry their own colour + a text label.
 */
import { computed, onBeforeUnmount, onMounted, ref } from "vue"

import { parseDay } from "@/lib/dates"

export interface HeatCell {
	date: string
	color: string
	label: string
	ring?: string
	dashed?: boolean
}

const props = withDefaults(defineProps<{ cells: HeatCell[]; startsOn?: "Monday" | "Sunday"; cell?: number; maxWeeks?: number }>(), {
	startsOn: "Monday",
	cell: 13,
	maxWeeks: 53,
})
const box = ref<HTMLElement | null>(null)
const width = ref(600)
const GAP = 3
let observer: ResizeObserver | null = null

onMounted(() => {
	observer = new ResizeObserver(([e]) => (width.value = e!.contentRect.width))
	if (box.value) observer.observe(box.value)
})
onBeforeUnmount(() => observer?.disconnect())

const weeks = computed(() => {
	const rowOf = (d: string) => (props.startsOn === "Sunday" ? parseDay(d).getDay() : (parseDay(d).getDay() + 6) % 7)
	const cols: (HeatCell | null)[][] = []
	let col: (HeatCell | null)[] = Array(7).fill(null)
	for (const c of props.cells) {
		const r = rowOf(c.date)
		if (r === 0 && col.some(Boolean)) {
			cols.push(col)
			col = Array(7).fill(null)
		}
		col[r] = c
	}
	if (col.some(Boolean)) cols.push(col)
	// day-label column (19px) + one gap, then (cell + gap) per week
	const fit = Math.max(4, Math.floor((width.value - 19 - GAP) / (props.cell + GAP)))
	return cols.slice(-Math.min(fit, props.maxWeeks))
})

const months = computed(() => {
	let lastAt = -9
	return weeks.value.map((w, i) => {
		const first = w.find(Boolean)
		if (!first) return ""
		const m = parseDay(first.date).getMonth()
		const prev = weeks.value[i - 1]?.find(Boolean)
		const starts = !prev || parseDay(prev.date).getMonth() !== m
		if (!starts || i - lastAt < 3) return "" // keep labels from colliding
		lastAt = i
		return parseDay(first.date).toLocaleDateString(undefined, { month: "short" })
	})
})
const dayLabels = computed(() => (props.startsOn === "Sunday" ? ["", "Mon", "", "Wed", "", "Fri", ""] : ["Mon", "", "Wed", "", "Fri", "", ""]))
</script>

<template>
	<div ref="box" class="w-full overflow-hidden">
		<div class="flex" :style="{ gap: `${GAP}px` }">
			<div class="flex shrink-0 flex-col pt-[18px] text-[10px] font-semibold leading-none text-ink-400" :style="{ gap: `${GAP}px`, width: '19px' }" aria-hidden="true">
				<span v-for="(l, i) in dayLabels" :key="i" class="flex items-center" :style="{ height: `${cell}px` }">{{ l }}</span>
			</div>
			<div v-for="(w, i) in weeks" :key="i" class="flex shrink-0 flex-col" :style="{ gap: `${GAP}px`, width: `${cell}px` }">
				<span class="h-[15px] overflow-visible whitespace-nowrap text-[10px] font-semibold leading-none text-ink-400" aria-hidden="true">{{ months[i] }}</span>
				<span
					v-for="(c, r) in w"
					:key="r"
					class="block rounded-[4px]"
					:class="c?.dashed && 'border border-dashed'"
					:style="{
						width: `${cell}px`,
						height: `${cell}px`,
						background: c ? c.color : 'transparent',
						borderColor: c?.dashed ? c.ring : undefined,
						boxShadow: c?.ring && !c.dashed ? `inset 0 0 0 2px ${c.ring}` : undefined,
					}"
					:title="c?.label"
					:aria-label="c?.label"
					:role="c ? 'img' : undefined"
				/>
			</div>
		</div>
		<slot name="legend" />
	</div>
</template>
