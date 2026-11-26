<script setup lang="ts">
import { Archive, ArchiveRestore, CalendarClock, Flame, Pause, Pencil, Play, Target, Trash2, Trophy } from "lucide-vue-next"
import { computed, onMounted, ref } from "vue"
import { useRouter } from "vue-router"

import { getHabit } from "@/api/habits"
import { getHabitHistory } from "@/api/insights"
import type { CellState, Habit, HabitHistory, HabitStatus } from "@/api/types"
import CalendarHeatmap from "@/components/charts/CalendarHeatmap.vue"
import HabitIcon from "@/components/habits/HabitIcon.vue"
import AppButton from "@/components/ui/AppButton.vue"
import EmptyState from "@/components/ui/EmptyState.vue"
import PageHeader from "@/components/ui/PageHeader.vue"
import SkeletonBlock from "@/components/ui/SkeletonBlock.vue"
import { formatDay, formatTime } from "@/lib/dates"
import { describeSchedule, describeTarget } from "@/lib/describe"
import { tint } from "@/lib/palette"
import { STATE_META } from "@/lib/states"
import { isDark } from "@/lib/theme"
import { useConfirm } from "@/stores/confirm"
import { useHabits } from "@/stores/habits"
import { useSession } from "@/stores/session"
import { useToast } from "@/stores/toast"

const props = defineProps<{ name: string }>()
const router = useRouter()
const store = useHabits()
const session = useSession()
const confirm = useConfirm()
const toast = useToast()

const habit = ref<Habit | null>(null)
const history = ref<HabitHistory | null>(null)
const error = ref("")
const busy = ref("")

onMounted(async () => {
	try {
		habit.value = await getHabit(props.name)
		history.value = await getHabitHistory(props.name)
	} catch (e) {
		error.value = (e as Error).message
	}
})

function cellStyle(state: CellState) {
	const color = habit.value?.color ?? "#7657F6"
	const none = isDark.value ? "#1C2537" : "#EEF0F6"
	switch (state) {
		case "done":
			return { color }
		case "partial":
			return { color: tint(color, 0.4) }
		case "missed":
			return { color: "transparent", ring: "#F56FA1", dashed: true }
		case "pending":
			return { color: "transparent", ring: isDark.value ? "#9479F9" : "#7657F6" }
		case "bonus":
			return { color: "#FFD166" }
		default:
			return { color: none }
	}
}
const heatCells = computed(() =>
	(history.value?.cells ?? []).map((c) => ({
		date: c.date,
		...cellStyle(c.state),
		label: `${formatDay(c.date, { weekday: "short", day: "numeric", month: "short" })}: ${STATE_META[c.state].label}`,
	})),
)
const LEGEND: CellState[] = ["done", "partial", "missed", "pending", "off"]

const stats = computed(() => {
	const h = habit.value
	if (!h) return []
	return [
		{ label: "Current streak", value: h.current_streak, unit: "days", icon: Flame, color: "#FF9F43" },
		{ label: "Best streak", value: h.longest_streak, unit: "days", icon: Trophy, color: "#7657F6" },
		{ label: "Check-ins", value: h.total_completions, unit: "total", icon: Target, color: "#26C281" },
	]
})

async function setStatus(status: HabitStatus, message: string) {
	busy.value = status
	try {
		habit.value = await store.setStatus(props.name, status)
		toast.success(message)
	} catch (e) {
		toast.error((e as Error).message)
	} finally {
		busy.value = ""
	}
}

async function remove() {
	const ok = await confirm.ask({
		title: "Delete this habit?",
		body: `"${habit.value?.habit_name}" and all of its check-ins will be deleted for good. Archive it instead to keep the history.`,
		confirmLabel: "Delete habit",
		danger: true,
	})
	if (!ok) return
	busy.value = "delete"
	try {
		await store.remove(props.name)
		toast.success("Habit deleted")
		router.replace({ name: "habits" })
	} catch (e) {
		toast.error((e as Error).message)
		busy.value = ""
	}
}
</script>

<template>
	<div>
		<PageHeader :title="habit?.habit_name ?? 'Habit'" :back="{ name: 'habits' }">
			<template v-if="habit" #actions>
				<AppButton variant="secondary" @click="$router.push({ name: 'habit-edit', params: { name } })"><Pencil class="h-4 w-4" /> Edit</AppButton>
			</template>
		</PageHeader>

		<EmptyState v-if="error" title="Habit not found" :body="error"><AppButton @click="$router.push({ name: 'habits' })">Back to My Habits</AppButton></EmptyState>
		<div v-else-if="!habit" class="space-y-4"><SkeletonBlock class="h-44 rounded-4xl" /><SkeletonBlock class="h-24 rounded-4xl" /></div>

		<div v-else class="space-y-5">
			<section class="rounded-4xl p-5" :style="{ background: tint(habit.color, 0.12) }">
				<div class="flex items-center gap-4">
					<HabitIcon :icon="habit.icon" :color="habit.color" size="lg" />
					<div class="min-w-0">
						<p v-if="habit.category_info" class="text-[13px] font-bold" :style="{ color: habit.category_info.color }">{{ habit.category_info.label }}</p>
						<p class="text-[15px] font-semibold text-ink-700 dark:text-ink-200">{{ describeSchedule(habit) }}. {{ describeTarget(habit) }}</p>
						<p class="mt-0.5 text-[13px] text-ink-500 dark:text-ink-400">
							<CalendarClock class="-mt-0.5 mr-1 inline h-4 w-4" />Since {{ formatDay(habit.start_date!, { day: "numeric", month: "short", year: "numeric" }) }}
							<template v-if="habit.preferred_time">, at {{ formatTime(habit.preferred_time) }}</template>
						</p>
					</div>
				</div>
				<p v-if="habit.description" class="mt-4 text-[15px] leading-relaxed text-ink-700 dark:text-ink-200">{{ habit.description }}</p>
				<p v-if="habit.status !== 'Active'" class="mt-4 inline-block rounded-full bg-white/70 px-3 py-1 text-[13px] font-bold dark:bg-night-900/60">
					{{ habit.status === "Paused" ? "Paused. It won't show up on Home until you resume it." : habit.status === "Archived" ? "Archived" : "Goal reached" }}
				</p>
			</section>

			<dl class="grid grid-cols-3 gap-3">
				<div v-for="s in stats" :key="s.label" class="rounded-3xl bg-white p-4 shadow-soft dark:bg-night-900">
					<component :is="s.icon" class="h-5 w-5" :style="{ color: s.color }" :stroke-width="2.5" />
					<dd class="mt-2 font-display text-[28px] font-extrabold leading-none">{{ s.value }}</dd>
					<dt class="mt-1 text-[12px] font-semibold text-ink-500 dark:text-ink-400">{{ s.label }}</dt>
				</div>
			</dl>

			<section class="rounded-4xl bg-white p-5 shadow-soft dark:bg-night-900" aria-labelledby="history-title">
				<div class="flex flex-wrap items-baseline justify-between gap-2">
					<h2 id="history-title" class="text-[18px] font-extrabold">History</h2>
					<p v-if="history" class="text-[13px] font-semibold text-ink-500 dark:text-ink-400">
						This week {{ history.week_rate ?? "–" }}{{ history.week_rate !== null ? "%" : "" }}, this month {{ history.month_rate ?? "–" }}{{ history.month_rate !== null ? "%" : "" }}
					</p>
				</div>
				<SkeletonBlock v-if="!history" class="mt-3 h-28" />
				<template v-else>
					<CalendarHeatmap class="mt-3" :cells="heatCells" :starts-on="session.boot?.profile?.week_starts_on ?? 'Monday'" :cell="15" />
					<ul class="mt-3 flex flex-wrap gap-x-4 gap-y-1.5 text-[12px] font-semibold text-ink-600 dark:text-ink-300" aria-label="Legend">
						<li v-for="s in LEGEND" :key="s" class="inline-flex items-center gap-1.5">
							<span
								class="h-3 w-3 rounded-[3px]"
								:class="cellStyle(s).dashed && 'border border-dashed'"
								:style="{ background: cellStyle(s).color, borderColor: cellStyle(s).ring, boxShadow: cellStyle(s).ring && !cellStyle(s).dashed ? `inset 0 0 0 2px ${cellStyle(s).ring}` : undefined }"
							/>
							{{ STATE_META[s].label }}
						</li>
					</ul>
					<p v-if="history.comebacks" class="mt-3 text-[14px] font-semibold text-sun-700 dark:text-sun-400">
						You've bounced back after a missed day {{ history.comebacks }} time{{ history.comebacks === 1 ? "" : "s" }}. That's how habits stick.
					</p>
				</template>
			</section>

			<p v-if="habit.notes" class="whitespace-pre-line rounded-3xl bg-white p-4 text-[14px] text-ink-700 shadow-soft dark:bg-night-900 dark:text-ink-200">{{ habit.notes }}</p>

			<section class="space-y-2 rounded-4xl bg-white p-3 shadow-soft dark:bg-night-900" aria-label="Habit actions">
				<button
					v-if="habit.status === 'Active'"
					type="button"
					class="flex min-h-[52px] w-full items-center gap-3 rounded-2xl px-3 text-left text-[15px] font-bold hover:bg-ink-50 disabled:opacity-50 dark:hover:bg-night-800"
					:disabled="!!busy"
					@click="setStatus('Paused', 'Habit paused')"
				>
					<Pause class="h-5 w-5 text-ink-500" /> Pause habit
				</button>
				<button
					v-if="habit.status === 'Paused' || habit.status === 'Archived'"
					type="button"
					class="flex min-h-[52px] w-full items-center gap-3 rounded-2xl px-3 text-left text-[15px] font-bold hover:bg-ink-50 disabled:opacity-50 dark:hover:bg-night-800"
					:disabled="!!busy"
					@click="setStatus('Active', habit.status === 'Paused' ? 'Welcome back! Habit resumed.' : 'Habit restored')"
				>
					<component :is="habit.status === 'Paused' ? Play : ArchiveRestore" class="h-5 w-5 text-mint-600" />
					{{ habit.status === "Paused" ? "Resume habit" : "Restore habit" }}
				</button>
				<button
					v-if="habit.status !== 'Archived'"
					type="button"
					class="flex min-h-[52px] w-full items-center gap-3 rounded-2xl px-3 text-left text-[15px] font-bold hover:bg-ink-50 disabled:opacity-50 dark:hover:bg-night-800"
					:disabled="!!busy"
					@click="setStatus('Archived', 'Habit archived. Its history is kept.')"
				>
					<Archive class="h-5 w-5 text-ink-500" /> Archive habit
				</button>
				<button
					type="button"
					class="flex min-h-[52px] w-full items-center gap-3 rounded-2xl px-3 text-left text-[15px] font-bold text-blush-700 hover:bg-blush-50 disabled:opacity-50 dark:text-blush-400 dark:hover:bg-blush-500/10"
					:disabled="!!busy"
					@click="remove"
				>
					<Trash2 class="h-5 w-5" /> Delete habit
				</button>
			</section>
		</div>
	</div>
</template>
