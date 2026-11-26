<script setup lang="ts">
/** The streak flame overlay: a burning fire with the habit's streak, a nudge and a quick check-in. */
import { ChevronRight, Flame, Trophy, X } from "lucide-vue-next"
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue"
import { useRouter } from "vue-router"

import AppButton from "@/components/ui/AppButton.vue"
import { isDone, isToggle, useHabits } from "@/stores/habits"
import { useFlame } from "@/stores/flame"

import HabitIcon from "./HabitIcon.vue"
import StreakFlame from "./StreakFlame.vue"

const flame = useFlame()
const store = useHabits()
const router = useRouter()

const habit = computed(() => (flame.habit ? (store.today?.habits.find((h) => h.name === flame.habit) ?? null) : null))
const streak = computed(() => habit.value?.current_streak ?? 0)
const best = computed(() => Math.max(habit.value?.longest_streak ?? 0, streak.value))
const done = computed(() => (habit.value ? isDone(habit.value) : false))
const canCheckIn = computed(() => !!habit.value && !done.value && store.today?.date === store.today?.today)
const days = (n: number) => `${n} ${n === 1 ? "day" : "days"}`

const message = computed(() => {
	const h = habit.value
	if (!h) return ""
	const n = streak.value
	if (done.value && flame.justCompleted) return n <= 1 ? "The fire is lit! Day one is the hardest. Come back tomorrow." : `${days(n)} in a row. Keep it burning!`
	if (done.value) return "Done for today. Your fire is safe until tomorrow."
	if (n > 0) return `Your ${n}-day streak needs fuel today. Check in to keep the fire burning.`
	if (best.value > 0) return `Your best run was ${days(best.value)}. Light a new fire today.`
	return "Check in today to light your first spark."
})

const checkInLabel = computed(() => {
	const h = habit.value
	if (!h) return ""
	if (h.habit_type === "Break") return "I resisted today"
	if (isToggle(h)) return "Mark as done"
	const v = h.completion?.value ?? 0
	const t = h.completion?.target || h.daily_target || 1
	return `Log one more (${v + 1}/${t})`
})

// the number counts up when the fire appears (and again when a check-in grows it)
const shown = ref(0)
let raf = 0
function countTo(to: number) {
	cancelAnimationFrame(raf)
	const from = Math.min(shown.value, to)
	const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches
	if (reduce || to === from) {
		shown.value = to
		return
	}
	const start = performance.now()
	const dur = Math.min(900, 300 + (to - from) * 40)
	const tick = (now: number) => {
		const p = Math.min(1, (now - start) / dur)
		shown.value = Math.round(from + (to - from) * (1 - Math.pow(1 - p, 3)))
		if (p < 1) raf = requestAnimationFrame(tick)
	}
	raf = requestAnimationFrame(tick)
}

const closeButton = ref<HTMLButtonElement | null>(null)
let lastFocus: Element | null = null

function onKey(e: KeyboardEvent) {
	if (e.key === "Escape") flame.close()
}

watch(
	() => flame.habit,
	async (name, before) => {
		if (name && !before) {
			lastFocus = document.activeElement
			document.addEventListener("keydown", onKey)
			shown.value = 0
			await nextTick()
			closeButton.value?.focus()
		} else if (!name) {
			document.removeEventListener("keydown", onKey)
			;(lastFocus as HTMLElement | null)?.focus?.()
		}
	},
)
watch([() => flame.habit, streak], ([name]) => name && countTo(streak.value), { immediate: true })
// the habit left today's list (archived, deleted, day changed): nothing to show
watch(habit, (h) => {
	if (flame.habit && store.today && !h) flame.close()
})
onBeforeUnmount(() => {
	document.removeEventListener("keydown", onKey)
	cancelAnimationFrame(raf)
})

function checkIn() {
	const h = habit.value
	if (!h) return
	if (store.toggle(h)) {
		flame.justCompleted = true
		navigator.vibrate?.([15, 40, 25])
	}
}

function details() {
	const name = flame.habit
	flame.close()
	if (name) void router.push({ name: "habit", params: { name } })
}
</script>

<template>
	<Teleport to="body">
		<Transition enter-active-class="transition-opacity duration-200" enter-from-class="opacity-0" leave-active-class="transition-opacity duration-150" leave-to-class="opacity-0">
			<div
				v-if="habit"
				class="fixed inset-0 z-[80] flex items-end justify-center bg-night-950/75 backdrop-blur-sm sm:items-center sm:p-6"
				@click.self="flame.close()"
			>
				<div
					role="dialog"
					aria-modal="true"
					:aria-label="`${habit.habit_name} streak`"
					class="relative w-full overflow-hidden rounded-t-4xl bg-gradient-to-b from-night-900 to-night-950 px-6 pb-6 pt-5 text-center text-white shadow-sheet animate-fade-up sm:max-w-sm sm:rounded-4xl"
					style="padding-bottom: max(env(safe-area-inset-bottom), 1.5rem)"
				>
					<div class="flex items-center gap-3 text-left">
						<HabitIcon :icon="habit.icon" :color="habit.color || '#7657F6'" />
						<div class="min-w-0 flex-1">
							<p class="truncate text-[16px] font-bold">{{ habit.habit_name }}</p>
							<p class="text-[12px] font-semibold text-ink-400">{{ done ? "Done today" : "Not done yet today" }}</p>
						</div>
						<button ref="closeButton" type="button" class="-m-1 rounded-xl p-2 text-ink-400 hover:bg-white/10 hover:text-white" aria-label="Close" @click="flame.close()">
							<X class="h-5 w-5" />
						</button>
					</div>

					<div class="mt-2 flex justify-center">
						<StreakFlame :key="`${habit.name}-${flame.justCompleted}`" :lit="streak > 0" :heat="Math.min(streak / 30, 1)" :size="170" />
					</div>

					<p class="-mt-3 font-display text-[64px] font-extrabold leading-none tabular-nums" :class="streak > 0 ? 'text-tangerine-400' : 'text-ink-400'">
						{{ shown }}
					</p>
					<p class="mt-1 text-[15px] font-bold uppercase tracking-wider text-ink-300">
						{{ habit.habit_type === "Break" ? (streak === 1 ? "day strong" : "days strong") : "day streak" }}
					</p>
					<p class="mx-auto mt-3 max-w-[18rem] text-[15px] leading-snug text-ink-200" role="status">{{ message }}</p>

					<div class="mt-4 flex justify-center gap-2 text-[12px] font-bold">
						<span class="inline-flex items-center gap-1 rounded-lg bg-white/10 px-2.5 py-1 text-ink-200"><Trophy class="h-3.5 w-3.5 text-sun-500" />Best {{ days(best) }}</span>
						<span class="inline-flex items-center gap-1 rounded-lg bg-white/10 px-2.5 py-1 text-ink-200"><Flame class="h-3.5 w-3.5 text-tangerine-400" />{{ habit.total_completions }} total</span>
					</div>

					<div class="mt-6 space-y-2">
						<AppButton v-if="canCheckIn" size="lg" block class="!bg-gradient-to-r !from-tangerine-500 !to-[#FF4D1A]" @click="checkIn">
							<Flame class="h-5 w-5" /> {{ checkInLabel }}
						</AppButton>
						<button type="button" class="inline-flex min-h-[44px] w-full items-center justify-center gap-1 rounded-2xl text-[15px] font-bold text-ink-300 hover:bg-white/5 hover:text-white" @click="details">
							View habit details <ChevronRight class="h-4 w-4" />
						</button>
					</div>
				</div>
			</div>
		</Transition>
	</Teleport>
</template>
