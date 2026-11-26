<script setup lang="ts">
import { CalendarCheck, Check, ChevronLeft, ChevronRight, RotateCcw } from "lucide-vue-next"
import { computed, onMounted, ref, watch } from "vue"

import { completeHabit, uncompleteHabit } from "@/api/habits"
import { getCalendar, getDay } from "@/api/insights"
import type { CalendarData, CellState, DayDetail } from "@/api/types"
import DayCell from "@/components/calendar/DayCell.vue"
import HabitIcon from "@/components/habits/HabitIcon.vue"
import AppButton from "@/components/ui/AppButton.vue"
import EmptyState from "@/components/ui/EmptyState.vue"
import PageHeader from "@/components/ui/PageHeader.vue"
import SegmentedControl from "@/components/ui/SegmentedControl.vue"
import SkeletonBlock from "@/components/ui/SkeletonBlock.vue"
import { addDays, formatDay, iso, monthGrid, parseDay, weekStart } from "@/lib/dates"
import { online } from "@/lib/pwa"
import { STATE_META } from "@/lib/states"
import { useHabits } from "@/stores/habits"
import { useSession } from "@/stores/session"
import { useToast } from "@/stores/toast"

const session = useSession()
const habits = useHabits()
const toast = useToast()
const startsOn = computed(() => session.boot?.profile?.week_starts_on ?? "Monday")

const mode = ref<"month" | "week">("month")
const anchor = ref(iso(new Date())) // any day inside the shown month/week
const habit = ref("")
const data = ref<CalendarData | null>(null)
const error = ref("")
const loading = ref(false)
const selected = ref<string | null>(null)
const day = ref<DayDetail | null>(null)
const dayLoading = ref(false)
const saving = ref("")

const range = computed(() => {
	if (mode.value === "week") {
		const start = weekStart(anchor.value, startsOn.value)
		return { start, end: addDays(start, 6), month: -1 }
	}
	return monthGrid(anchor.value, startsOn.value)
})
const title = computed(() => {
	const d = parseDay(anchor.value)
	if (mode.value === "month") return d.toLocaleDateString(undefined, { month: "long", year: "numeric" })
	const s = parseDay(range.value.start)
	const e = parseDay(range.value.end)
	return `${s.toLocaleDateString(undefined, { day: "numeric", month: "short" })} to ${e.toLocaleDateString(undefined, { day: "numeric", month: "short" })}`
})
const weekdayNames = computed(() =>
	Array.from({ length: 7 }, (_, i) => parseDay(addDays(range.value.start, i)).toLocaleDateString(undefined, { weekday: "short" })),
)
const today = computed(() => data.value?.today ?? iso(new Date()))
const canGoForward = computed(() => range.value.end < today.value || (mode.value === "month" && parseDay(anchor.value).getMonth() !== parseDay(today.value).getMonth()))

const monthTotals = computed(() => {
	const days = (data.value?.days ?? []).filter((d) => mode.value === "week" || parseDay(d.date).getMonth() === range.value.month)
	return {
		done: days.filter((d) => d.state === "done").length,
		partial: days.filter((d) => d.state === "partial").length,
		missed: days.filter((d) => d.state === "missed").length,
	}
})

async function load() {
	loading.value = true
	error.value = ""
	try {
		data.value = await getCalendar(range.value.start, range.value.end, {
			habit: mode.value === "month" ? habit.value || undefined : undefined,
			cells: mode.value === "week",
		})
	} catch (e) {
		error.value = (e as Error).message
	} finally {
		loading.value = false
	}
}

async function openDay(date: string) {
	if (date > today.value) return
	selected.value = date
	dayLoading.value = true
	try {
		day.value = await getDay(date)
	} catch (e) {
		toast.error((e as Error).message)
	} finally {
		dayLoading.value = false
	}
}

function shift(dir: number) {
	const d = parseDay(anchor.value)
	if (mode.value === "month") anchor.value = iso(new Date(d.getFullYear(), d.getMonth() + dir, 1))
	else anchor.value = addDays(anchor.value, 7 * dir)
}

function goToday() {
	anchor.value = today.value
	void openDay(today.value)
}

async function setDone(item: DayDetail["habits"][number], done: boolean) {
	if (!online.value) {
		toast.error("You're offline. Connect to the internet to change check-ins.")
		return
	}
	saving.value = item.name
	try {
		if (done) await completeHabit(item.name, { date: day.value!.date })
		else await uncompleteHabit(item.name, day.value!.date)
		toast.success(done ? `${item.habit_name} marked done` : `Check-in removed`)
		await Promise.all([load(), openDay(day.value!.date)])
		void habits.loadToday(true)
	} catch (e) {
		toast.error((e as Error).message)
	} finally {
		saving.value = ""
	}
}

watch([range, habit], load)
onMounted(async () => {
	await load()
	void openDay(today.value)
})

const LEGEND: CellState[] = ["done", "partial", "missed", "pending", "bonus"]
function cellsFor(name: string) {
	return data.value?.cells?.[name] ?? []
}
</script>

<template>
	<div>
		<PageHeader title="Calendar">
			<template #actions>
				<SegmentedControl v-model="mode" class="w-44" :options="[{ value: 'month', label: 'Month' }, { value: 'week', label: 'Week' }]" label="View" />
			</template>
		</PageHeader>

		<div class="grid gap-5 lg:grid-cols-[minmax(0,1fr)_22rem] lg:items-start">
			<section class="rounded-4xl bg-white p-4 shadow-soft dark:bg-night-900 sm:p-5" aria-labelledby="cal-title">
				<div class="mb-4 flex items-center gap-2">
					<button type="button" class="flex h-11 w-11 items-center justify-center rounded-2xl hover:bg-ink-100 dark:hover:bg-night-800" aria-label="Previous" @click="shift(-1)">
						<ChevronLeft class="h-5 w-5" />
					</button>
					<h2 id="cal-title" class="flex-1 text-center text-[18px] font-extrabold" aria-live="polite">{{ title }}</h2>
					<button type="button" class="flex h-11 w-11 items-center justify-center rounded-2xl hover:bg-ink-100 disabled:opacity-30 dark:hover:bg-night-800" aria-label="Next" :disabled="!canGoForward" @click="shift(1)">
						<ChevronRight class="h-5 w-5" />
					</button>
				</div>
				<div class="mb-4 flex flex-wrap items-center gap-2">
					<select v-if="mode === 'month'" v-model="habit" class="field h-11 max-w-[16rem] flex-1 py-0 text-[14px]" aria-label="Show habit">
						<option value="">All habits</option>
						<option v-for="h in data?.habits ?? []" :key="h.name" :value="h.name">{{ h.habit_name }}</option>
					</select>
					<AppButton variant="secondary" class="ml-auto" @click="goToday"><CalendarCheck class="h-4 w-4" /> Today</AppButton>
				</div>

				<EmptyState v-if="error" title="Couldn't load the calendar" :body="error"><AppButton @click="load">Try again</AppButton></EmptyState>

				<!-- month -->
				<template v-else-if="mode === 'month'">
					<div class="grid grid-cols-7 gap-1 text-center text-[12px] font-bold text-ink-400" aria-hidden="true">
						<span v-for="w in weekdayNames" :key="w" class="py-1">{{ w }}</span>
					</div>
					<div v-if="!data" class="grid grid-cols-7 gap-1"><SkeletonBlock v-for="i in 42" :key="i" class="aspect-square rounded-2xl" /></div>
					<div v-else class="grid grid-cols-7 gap-1" :class="loading && 'opacity-60'">
						<DayCell
							v-for="d in data.days"
							:key="d.date"
							:day="d"
							:selected="selected === d.date"
							:outside="parseDay(d.date).getMonth() !== range.month"
							:is-today="d.date === data.today"
							@click="openDay(d.date)"
						/>
					</div>
				</template>

				<!-- week: habit x day tracker -->
				<template v-else>
					<div v-if="!data" class="space-y-2"><SkeletonBlock v-for="i in 4" :key="i" class="h-12 rounded-2xl" /></div>
					<p v-else-if="!data.cells || !Object.keys(data.cells).length" class="py-8 text-center text-ink-500">Nothing was scheduled this week.</p>
					<table v-else class="w-full table-fixed border-separate border-spacing-y-1.5" :class="loading && 'opacity-60'">
						<caption class="sr-only">Check-ins for each habit this week</caption>
						<thead>
							<tr>
								<th scope="col" class="w-[34%] text-left text-[12px] font-bold text-ink-400"><span class="sr-only">Habit</span></th>
								<th v-for="(d, i) in data.days" :key="d.date" scope="col" class="text-center">
									<button type="button" class="mx-auto flex flex-col items-center rounded-xl px-1 py-1 text-[11px] font-bold" :class="selected === d.date ? 'bg-ink-900 text-white dark:bg-white dark:text-ink-900' : d.date === data.today ? 'text-grape-600 dark:text-grape-300' : 'text-ink-400'" :disabled="d.date > data.today" @click="openDay(d.date)">
										{{ weekdayNames[i] }}<span class="font-display text-[14px]">{{ parseDay(d.date).getDate() }}</span>
									</button>
								</th>
							</tr>
						</thead>
						<tbody>
							<tr v-for="h in data.habits.filter((x) => data!.cells![x.name])" :key="h.name">
								<th scope="row" class="pr-2 text-left">
									<span class="flex min-w-0 items-center gap-2">
										<HabitIcon :icon="h.icon" :color="h.color" size="sm" />
										<span class="truncate text-[13px] font-bold">{{ h.habit_name }}</span>
									</span>
								</th>
								<td v-for="(state, i) in cellsFor(h.name)" :key="i" class="text-center">
									<span
										class="mx-auto flex h-8 w-8 items-center justify-center rounded-full"
										:class="state === 'done' ? '' : STATE_META[state].chip"
										:style="state === 'done' ? { background: h.color, color: '#fff' } : {}"
										:title="STATE_META[state].label"
									>
										<component :is="STATE_META[state].icon" class="h-4 w-4" :stroke-width="3" aria-hidden="true" />
										<span class="sr-only">{{ STATE_META[state].label }}</span>
									</span>
								</td>
							</tr>
						</tbody>
					</table>
				</template>

				<ul class="mt-4 flex flex-wrap gap-x-4 gap-y-2 border-t border-ink-100 pt-4 text-[12px] font-semibold text-ink-600 dark:border-night-800 dark:text-ink-300" aria-label="Legend">
					<li v-for="s in LEGEND" :key="s" class="inline-flex items-center gap-1.5">
						<span class="flex h-5 w-5 items-center justify-center rounded-full" :class="STATE_META[s].chip"><component :is="STATE_META[s].icon" class="h-3 w-3" :stroke-width="3" /></span>
						{{ s === "done" && mode === "month" ? "All done" : STATE_META[s].label }}
					</li>
				</ul>
				<p v-if="data" class="mt-3 text-[13px] text-ink-500 dark:text-ink-400">
					This {{ mode }}: {{ monthTotals.done }} perfect day{{ monthTotals.done === 1 ? "" : "s" }}, {{ monthTotals.partial }} partly done,
					{{ monthTotals.missed }} missed.
				</p>
			</section>

			<!-- selected day -->
			<section class="rounded-4xl bg-white p-5 shadow-soft dark:bg-night-900" aria-live="polite" aria-labelledby="day-title">
				<template v-if="day && selected">
					<h2 id="day-title" class="text-[18px] font-extrabold">{{ formatDay(day.date) }}</h2>
					<p class="mt-0.5 text-[14px] text-ink-500 dark:text-ink-400">
						<template v-if="day.summary.scheduled">{{ day.summary.completed }} of {{ day.summary.scheduled }} done</template>
						<template v-else>Nothing scheduled</template>
					</p>
					<div v-if="dayLoading" class="mt-4 space-y-2"><SkeletonBlock v-for="i in 3" :key="i" class="h-16 rounded-2xl" /></div>
					<p v-else-if="!day.habits.length" class="mt-6 text-center text-[14px] text-ink-500">No habits were due on this day.</p>
					<ul v-else class="mt-4 space-y-2">
						<li v-for="h in day.habits" :key="h.name" class="flex items-center gap-3 rounded-2xl bg-ink-50 p-3 dark:bg-night-850">
							<HabitIcon :icon="h.icon" :color="h.color" size="sm" />
							<div class="min-w-0 flex-1">
								<RouterLink :to="{ name: 'habit', params: { name: h.name } }" class="block truncate text-[14px] font-bold hover:underline">{{ h.habit_name }}</RouterLink>
								<span class="inline-flex items-center gap-1 text-[12px] font-bold" :class="STATE_META[h.state].text">
									<component :is="STATE_META[h.state].icon" class="h-3.5 w-3.5" :stroke-width="3" />
									{{ STATE_META[h.state].label }}<template v-if="h.state === 'partial'">: {{ h.value }} of {{ h.target }} {{ h.target_unit }}</template>
								</span>
							</div>
							<template v-if="h.can_edit">
								<button
									v-if="h.state === 'done' || h.state === 'bonus'"
									type="button"
									class="flex h-10 items-center gap-1 rounded-xl px-2.5 text-[13px] font-bold text-ink-600 hover:bg-ink-200 disabled:opacity-50 dark:text-ink-300 dark:hover:bg-night-700"
									:disabled="saving === h.name"
									@click="setDone(h, false)"
								>
									<RotateCcw class="h-4 w-4" /> Undo
								</button>
								<button
									v-else
									type="button"
									class="flex h-10 items-center gap-1 rounded-xl bg-mint-600 px-3 text-[13px] font-bold text-white hover:bg-mint-700 disabled:opacity-50"
									:disabled="saving === h.name"
									@click="setDone(h, true)"
								>
									<Check class="h-4 w-4" :stroke-width="3" /> Mark done
								</button>
							</template>
						</li>
					</ul>
					<p v-if="day.habits.some((h) => !h.can_edit) && day.habits.length" class="mt-3 text-[12px] text-ink-500 dark:text-ink-400">
						Check-ins can be changed for the last 7 days, on active habits.
					</p>
				</template>
				<p v-else class="py-6 text-center text-[14px] text-ink-500">Pick a day to see its check-ins.</p>
			</section>
		</div>
	</div>
</template>
