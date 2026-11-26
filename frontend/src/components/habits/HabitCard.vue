<script setup lang="ts">
import { Check, CloudUpload, Flame, Minus, Plus, ShieldCheck } from "lucide-vue-next"
import { computed, ref } from "vue"

import type { TodayHabit } from "@/api/types"
import { formatTime } from "@/lib/dates"
import { tint } from "@/lib/palette"
import { useFlame } from "@/stores/flame"
import { isDone, isToggle, useHabits } from "@/stores/habits"
import { useSync } from "@/stores/sync"

import ProgressRing from "../ui/ProgressRing.vue"
import HabitIcon from "./HabitIcon.vue"

const props = defineProps<{ habit: TodayHabit; readonly?: boolean }>()
const store = useHabits()
const flame = useFlame()
const sync = useSync()
const waiting = computed(() => sync.isPending(props.habit.name, store.today?.date))

const done = computed(() => isDone(props.habit))
const toggle = computed(() => isToggle(props.habit))
const target = computed(() => props.habit.completion?.target || props.habit.daily_target || 1)
const value = computed(() => props.habit.completion?.value ?? 0)
const percent = computed(() => Math.min(100, (100 * value.value) / target.value))
const color = computed(() => props.habit.color || "#7657F6")
const unit = computed(() => props.habit.target_unit || "times")
const celebrate = ref(0)

const targetLabel = computed(() => {
	if (props.habit.habit_type === "Break") return "Stay strong today"
	if (props.habit.habit_type === "One-time") return "One-time goal"
	return toggle.value ? null : `${fmt(target.value)} ${unit.value}`
})

const buttonLabel = computed(() => {
	const n = props.habit.habit_name
	if (toggle.value) {
		if (props.habit.habit_type === "Break") return done.value ? `Undo: resisted ${n}` : `I resisted ${n} today`
		return done.value ? `Mark ${n} as not done` : `Mark ${n} as done`
	}
	return done.value ? `${n} done. Tap to reset` : `Log one more for ${n}: ${fmt(value.value)} of ${fmt(target.value)} ${unit.value}`
})

function fmt(n: number) {
	return Number.isInteger(n) ? String(n) : n.toFixed(1)
}

function tap() {
	if (props.readonly) return
	if (store.toggle(props.habit)) {
		celebrate.value++
		navigator.vibrate?.(15)
		// let the check burst play, then light the streak fire
		const name = props.habit.name
		setTimeout(() => flame.show(name, true), 450)
	}
}

const BURST = [0, 60, 120, 180, 240, 300].map((deg) => ({
	"--bx": `${Math.cos((deg * Math.PI) / 180) * 34}px`,
	"--by": `${Math.sin((deg * Math.PI) / 180) * 34}px`,
}))
</script>

<template>
	<article
		class="flex items-center gap-3 rounded-3xl p-3.5 shadow-soft transition-colors duration-300"
		:class="done ? '' : 'bg-white dark:bg-night-900'"
		:style="done ? { background: tint(color, 0.12) } : {}"
	>
		<!-- the habit name is the control; its ::after stretches over the whole body so any tap on it works -->
		<div class="relative flex min-w-0 flex-1 items-center gap-3 rounded-2xl">
			<HabitIcon :icon="habit.icon" :color="color" />
			<div class="min-w-0">
				<h3 class="truncate font-sans text-[16px] font-bold tracking-normal text-ink-900 dark:text-white">
					<RouterLink v-if="readonly" :to="{ name: 'habit', params: { name: habit.name } }" class="after:absolute after:inset-0 after:rounded-2xl">{{ habit.habit_name }}</RouterLink>
					<button
						v-else
						type="button"
						class="block w-full truncate text-left after:absolute after:inset-0 after:rounded-2xl focus-visible:outline-none focus-visible:after:ring-2 focus-visible:after:ring-grape-500"
						aria-haspopup="dialog"
						@click="flame.show(habit.name)"
					>{{ habit.habit_name }}<span class="sr-only">, show streak</span></button>
				</h3>
				<div class="mt-1 flex flex-wrap items-center gap-1.5 text-[12px] font-semibold text-ink-500 dark:text-ink-400">
					<span
						v-if="waiting"
						class="inline-flex items-center gap-1 rounded-md bg-sky-50 px-1.5 py-0.5 text-sky-700 dark:bg-sky-500/15 dark:text-sky-400"
						title="Kept on this device until it syncs"
					>
						<CloudUpload class="h-3.5 w-3.5" :stroke-width="2.5" />Waiting to sync
					</span>
					<span v-if="habit.category_info" class="inline-flex items-center gap-1">
						<span class="h-2 w-2 rounded-full" :style="{ background: habit.category_info.color }" />{{ habit.category_info.label }}
					</span>
					<span v-if="targetLabel" class="rounded-md bg-ink-100 px-1.5 py-0.5 dark:bg-night-800">{{ targetLabel }}</span>
					<span v-if="habit.preferred_time" class="rounded-md bg-ink-100 px-1.5 py-0.5 dark:bg-night-800">{{ formatTime(habit.preferred_time) }}</span>
					<span
						v-if="habit.current_streak > 0"
						class="inline-flex items-center gap-0.5 rounded-md bg-tangerine-50 px-1.5 py-0.5 text-tangerine-700 dark:bg-tangerine-500/15 dark:text-tangerine-400"
						:aria-label="`${habit.current_streak}-day streak`"
					>
						<Flame class="h-3.5 w-3.5" :stroke-width="2.5" />{{ habit.current_streak }}
					</span>
				</div>
			</div>
		</div>

		<div class="flex shrink-0 items-center gap-1.5">
			<button
				v-if="!toggle && value > 0 && !done && !readonly"
				type="button"
				class="flex h-9 w-9 items-center justify-center rounded-full text-ink-500 hover:bg-ink-100 dark:hover:bg-night-800"
				:aria-label="`Log one less for ${habit.habit_name}`"
				@click="store.step(habit, -1)"
			>
				<Minus class="h-4 w-4" :stroke-width="2.6" />
			</button>

			<button
				type="button"
				class="relative flex h-14 w-14 items-center justify-center rounded-full transition-transform active:scale-90 disabled:opacity-60"
				:aria-label="buttonLabel"
				:aria-pressed="toggle ? done : undefined"
				:disabled="readonly"
				@click="tap"
			>
				<span v-for="(style, i) in BURST" v-show="celebrate" :key="`${celebrate}-${i}`" class="absolute h-2 w-2 animate-burst rounded-full" :style="{ ...style, background: color }" aria-hidden="true" />

				<template v-if="toggle">
					<span
						:key="celebrate"
						class="flex h-12 w-12 items-center justify-center rounded-full border-[3px] transition-colors duration-200"
						:class="done ? 'animate-pop border-transparent text-white' : 'border-ink-200 text-ink-300 dark:border-night-700 dark:text-night-600'"
						:style="done ? { background: color } : {}"
					>
						<ShieldCheck v-if="habit.habit_type === 'Break'" class="h-6 w-6" :stroke-width="2.6" />
						<Check v-else class="h-6 w-6" :stroke-width="3" />
					</span>
				</template>
				<ProgressRing v-else :value="percent" :size="52" :stroke="5" :color="color">
					<span v-if="done" :key="celebrate" class="flex h-9 w-9 animate-pop items-center justify-center rounded-full text-white" :style="{ background: color }">
						<Check class="h-5 w-5" :stroke-width="3" />
					</span>
					<span v-else-if="value > 0" class="font-display text-[13px] font-extrabold leading-none text-ink-800 dark:text-ink-100">
						{{ fmt(value) }}<span class="text-ink-400">/{{ fmt(target) }}</span>
					</span>
					<Plus v-else class="h-5 w-5 text-ink-400" :stroke-width="2.8" />
				</ProgressRing>
			</button>
		</div>
	</article>
</template>
