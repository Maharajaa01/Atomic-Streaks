<script setup lang="ts">
import {
	ArrowRight,
	CalendarClock,
	CalendarDays,
	ChevronLeft,
	ChevronRight,
	History,
	ListTodo,
	Moon,
	Plus,
	RefreshCw,
	Trash2,
} from "lucide-vue-next"
import { computed, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

import { deletePlanTask, getPlanDay, movePlanTasks, savePlanTask, setPlanTaskDone } from "@/api/planner"
import type { PlanDay, PlanTask, TaskPriority } from "@/api/types"
import PlanTaskRow from "@/components/planner/PlanTaskRow.vue"
import AppButton from "@/components/ui/AppButton.vue"
import BottomSheet from "@/components/ui/BottomSheet.vue"
import EmptyState from "@/components/ui/EmptyState.vue"
import PageHeader from "@/components/ui/PageHeader.vue"
import SkeletonBlock from "@/components/ui/SkeletonBlock.vue"
import TextField from "@/components/ui/TextField.vue"
import { addDays, formatDay } from "@/lib/dates"
import { online } from "@/lib/pwa"
import { useConfirm } from "@/stores/confirm"
import { useToast } from "@/stores/toast"

const route = useRoute()
const router = useRouter()
const toast = useToast()
const confirm = useConfirm()

const ISO_DAY = /^\d{4}-\d{2}-\d{2}$/
const view = ref<PlanDay | null>(null)
const error = ref("")
const loading = ref(false)

/** The day in the URL (?date=), or today (as the server sees it in the user's timezone). */
const requested = computed(() => {
	const d = route.query.date
	return typeof d === "string" && ISO_DAY.test(d) ? d : undefined
})
const today = computed(() => view.value?.today ?? "")
const day = computed(() => view.value?.date ?? "")
const isToday = computed(() => !!day.value && day.value === today.value)

let seq = 0
async function load() {
	const mine = ++seq
	error.value = ""
	loading.value = true
	try {
		const res = await getPlanDay(requested.value)
		if (mine === seq) view.value = res
	} catch (e) {
		if (mine === seq) error.value = (e as Error).message
	} finally {
		if (mine === seq) loading.value = false
	}
}
watch(requested, load, { immediate: true })

function goTo(date: string) {
	void router.replace({ query: date && date !== today.value ? { date } : {} })
}

function relativeLabel(date: string): string {
	if (!today.value) return formatDay(date)
	if (date === today.value) return "Today"
	if (date === addDays(today.value, 1)) return "Tomorrow"
	if (date === addDays(today.value, -1)) return "Yesterday"
	return formatDay(date, { weekday: "short", day: "numeric", month: "short" })
}

const doneCount = computed(() => view.value?.tasks.filter((t) => t.is_done).length ?? 0)
/** Tasks just ticked stay in place for a moment so the tick is seen, then move to "Completed". */
const settling = ref(new Set<string>())
const openTasks = computed(() => view.value?.tasks.filter((t) => !t.is_done || settling.value.has(t.name)) ?? [])
const completedTasks = computed(() => view.value?.tasks.filter((t) => t.is_done && !settling.value.has(t.name)) ?? [])
const SHOW_DONE_KEY = "atomic-plan-show-completed"
const showCompleted = ref(localStorage.getItem(SHOW_DONE_KEY) === "1")
watch(showCompleted, (v) => localStorage.setItem(SHOW_DONE_KEY, v ? "1" : "0"))
const total = computed(() => view.value?.tasks.length ?? 0)
const isPast = computed(() => !!day.value && day.value < today.value)
/** In the evening, nudge towards planning tomorrow (the habit this page is built around). */
const evening = new Date().getHours() >= 18
const tomorrowCount = computed(() => view.value?.upcoming.find((u) => u.date === addDays(today.value, 1))?.total ?? 0)

function needOnline(): boolean {
	if (online.value) return true
	toast.error("You're offline. Connect to change your plan.")
	return false
}

// ------------------------------------------------------------------ quick add
const newTitle = ref("")
const newTime = ref("")
const adding = ref(false)

async function quickAdd() {
	const title = newTitle.value.trim()
	if (!title || !view.value || !needOnline()) return
	adding.value = true
	try {
		await savePlanTask({ title, start_time: newTime.value || null, plan_date: day.value })
		newTitle.value = ""
		newTime.value = ""
		await load()
		;(document.getElementById("plan-new") as HTMLInputElement | null)?.focus()
	} catch (e) {
		toast.error((e as Error).message)
	} finally {
		adding.value = false
	}
}

// ------------------------------------------------------------------ tick off
const busy = ref(new Set<string>())

async function toggle(t: PlanTask) {
	if (busy.value.has(t.name) || !needOnline()) return
	const next = t.is_done ? 0 : 1
	t.is_done = next // optimistic
	if (next) {
		settling.value.add(t.name)
		setTimeout(() => settling.value.delete(t.name), 600)
	}
	busy.value.add(t.name)
	try {
		await setPlanTaskDone(t.name, !!next)
		if (next && view.value && view.value.tasks.length && view.value.tasks.every((x) => x.is_done)) {
			toast.success(isToday.value ? "Everything on today's plan is done!" : "Every task on this day is done!")
		}
	} catch (e) {
		t.is_done = next ? 0 : 1
		toast.error((e as Error).message)
	} finally {
		busy.value.delete(t.name)
	}
}

// ------------------------------------------------------------------ carry over
const moving = ref(false)

async function moveTo(names: string[], date: string, label: string) {
	if (!names.length || !needOnline()) return
	moving.value = true
	try {
		const res = await movePlanTasks(names, date)
		toast.success(res.moved === 1 ? `Moved to ${label.toLowerCase()}` : `Moved ${res.moved} tasks to ${label.toLowerCase()}`)
		await load()
	} catch (e) {
		toast.error((e as Error).message)
	} finally {
		moving.value = false
	}
}

// ------------------------------------------------------------------ editor
interface Draft {
	name: string
	title: string
	notes: string
	start_time: string
	priority: TaskPriority
	plan_date: string
}
const editing = ref<Draft | null>(null)
const saving = ref(false)
const PRIORITIES: { value: TaskPriority; label: string }[] = [
	{ value: "High", label: "High" },
	{ value: "Normal", label: "Normal" },
	{ value: "Low", label: "Low" },
]

function openEditor(t: PlanTask) {
	editing.value = {
		name: t.name,
		title: t.title,
		notes: t.notes,
		start_time: t.start_time ?? "",
		priority: t.priority,
		plan_date: t.plan_date,
	}
}

async function saveEdit() {
	const d = editing.value
	if (!d || !needOnline()) return
	if (!d.title.trim()) return toast.error("Give the task a name.")
	if (!ISO_DAY.test(d.plan_date)) return toast.error("Pick a date.")
	saving.value = true
	try {
		await savePlanTask(
			{ title: d.title.trim(), notes: d.notes.trim(), start_time: d.start_time || null, priority: d.priority, plan_date: d.plan_date },
			d.name,
		)
		const movedAway = d.plan_date !== day.value
		editing.value = null
		await load()
		toast.success(movedAway ? `Moved to ${relativeLabel(d.plan_date)}` : "Task saved")
	} catch (e) {
		toast.error((e as Error).message)
	} finally {
		saving.value = false
	}
}

async function removeEdit() {
	const d = editing.value
	if (!d) return
	const ok = await confirm.ask({ title: `Delete "${d.title}"?`, body: "This can't be undone.", confirmLabel: "Delete", danger: true })
	if (!ok || !needOnline()) return
	try {
		await deletePlanTask(d.name)
		editing.value = null
		await load()
	} catch (e) {
		toast.error((e as Error).message)
	}
}
</script>

<template>
	<div>
		<PageHeader title="Day Plan" :subtitle="day ? formatDay(day) : 'Plan your day, one task at a time'" />

		<!-- day switcher -->
		<div class="mb-4 flex items-center gap-2">
			<button
				type="button"
				class="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-white text-ink-600 shadow-soft hover:text-ink-900 disabled:opacity-40 dark:bg-night-900 dark:text-ink-300"
				aria-label="Previous day"
				:disabled="!day"
				@click="goTo(addDays(day, -1))"
			>
				<ChevronLeft class="h-5 w-5" />
			</button>
			<div class="flex min-w-0 flex-1 gap-2 overflow-x-auto">
				<button
					v-for="offset in [0, 1]"
					:key="offset"
					type="button"
					class="h-11 shrink-0 rounded-2xl px-4 text-[14px] font-bold transition"
					:class="
						today && day === addDays(today, offset)
							? 'bg-grape-500 text-white shadow-lift'
							: 'bg-white text-ink-700 shadow-soft hover:text-ink-900 dark:bg-night-900 dark:text-ink-200'
					"
					:aria-pressed="!!today && day === addDays(today, offset)"
					:disabled="!today"
					@click="goTo(addDays(today, offset))"
				>
					{{ offset === 0 ? "Today" : "Tomorrow" }}
				</button>
				<label
					class="relative flex h-11 min-w-0 shrink-0 cursor-pointer items-center gap-2 rounded-2xl px-4 text-[14px] font-bold shadow-soft transition"
					:class="
						day && today && day !== today && day !== addDays(today, 1)
							? 'bg-grape-500 text-white shadow-lift'
							: 'bg-white text-ink-700 dark:bg-night-900 dark:text-ink-200'
					"
				>
					<CalendarDays class="h-4 w-4 shrink-0" />
					<span class="truncate">{{ day && today && day !== today && day !== addDays(today, 1) ? relativeLabel(day) : "Pick a date" }}</span>
					<input
						type="date"
						class="absolute inset-0 cursor-pointer opacity-0"
						aria-label="Pick a date"
						:value="day"
						@change="($event.target as HTMLInputElement).value && goTo(($event.target as HTMLInputElement).value)"
					/>
				</label>
			</div>
			<button
				type="button"
				class="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-white text-ink-600 shadow-soft hover:text-ink-900 disabled:opacity-40 dark:bg-night-900 dark:text-ink-300"
				aria-label="Next day"
				:disabled="!day"
				@click="goTo(addDays(day, 1))"
			>
				<ChevronRight class="h-5 w-5" />
			</button>
		</div>

		<EmptyState v-if="error && !view" :icon="RefreshCw" title="Couldn't load your plan" :body="error"><AppButton @click="load">Try again</AppButton></EmptyState>

		<div v-else-if="!view" class="space-y-3" aria-busy="true">
			<SkeletonBlock class="h-24 rounded-4xl" />
			<SkeletonBlock v-for="i in 3" :key="i" class="h-16 rounded-3xl" />
		</div>

		<div v-else class="grid grid-cols-[minmax(0,1fr)] gap-5 lg:grid-cols-[minmax(0,1fr)_20rem] lg:items-start" :class="loading ? 'opacity-70 transition-opacity' : ''">
			<div class="min-w-0 space-y-5">
				<!-- evening nudge: plan tomorrow -->
				<button
					v-if="isToday && evening"
					type="button"
					class="flex w-full items-center gap-3 rounded-3xl bg-grape-50 p-4 text-left dark:bg-grape-500/10"
					@click="goTo(addDays(today, 1))"
				>
					<span class="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-grape-500 text-white"><Moon class="h-5 w-5" /></span>
					<span class="min-w-0 flex-1">
						<span class="block text-[15px] font-bold text-ink-900 dark:text-white">Plan tomorrow</span>
						<span class="block text-[13px] text-ink-500 dark:text-ink-400">
							{{ tomorrowCount ? `${tomorrowCount} task${tomorrowCount === 1 ? "" : "s"} planned so far` : "Wake up knowing what to do first" }}
						</span>
					</span>
					<ArrowRight class="h-5 w-5 text-grape-600 dark:text-grape-300" />
				</button>

				<!-- quick add -->
				<form class="rounded-4xl bg-white p-4 shadow-soft dark:bg-night-900" @submit.prevent="quickAdd">
					<div class="mb-3 flex items-baseline justify-between gap-3">
						<h2 class="text-[18px] font-extrabold">{{ relativeLabel(day) }}</h2>
						<span v-if="total" class="text-[13px] font-bold tabular-nums text-ink-500 dark:text-ink-400">{{ doneCount }} of {{ total }} done</span>
					</div>
					<div v-if="total" class="mb-4 h-2 overflow-hidden rounded-full bg-ink-100 dark:bg-night-800" aria-hidden="true">
						<div class="h-full rounded-full bg-mint-500 transition-all duration-500" :style="{ width: `${(doneCount / total) * 100}%` }" />
					</div>
					<div class="flex gap-2">
						<label for="plan-new" class="sr-only">New task</label>
						<input
							id="plan-new"
							v-model="newTitle"
							class="field min-w-0 flex-1"
							maxlength="140"
							autocomplete="off"
							:placeholder="isToday ? 'What needs doing today?' : `Add a task for ${relativeLabel(day).toLowerCase()}…`"
						/>
						<label for="plan-new-time" class="sr-only">Time (optional)</label>
						<input id="plan-new-time" v-model="newTime" type="time" class="field w-[7.5rem] shrink-0 px-3" title="Time (optional)" />
						<AppButton type="submit" :loading="adding" :disabled="!newTitle.trim()" aria-label="Add task"><Plus class="h-5 w-5" :stroke-width="2.6" /></AppButton>
					</div>
					<p v-if="isPast" class="mt-2 text-[12px] font-semibold text-ink-500 dark:text-ink-400">This day has passed. You can still tick things off or move them.</p>
				</form>

				<!-- the day's tasks: open ones here; ticked ones move to "Completed" -->
				<section aria-labelledby="plan-tasks-title">
					<h2 id="plan-tasks-title" class="sr-only">Tasks for {{ relativeLabel(day) }}</h2>
					<div v-if="!view.tasks.length" class="rounded-4xl bg-white shadow-soft dark:bg-night-900">
						<EmptyState
							:icon="ListTodo"
							:title="isToday ? 'Nothing planned for today yet' : `Nothing planned for ${relativeLabel(day).toLowerCase()}`"
							:body="isPast ? 'No tasks were planned for this day.' : 'Add the things you want to get done. Tasks with a time are listed first, in time order.'"
						/>
					</div>
					<div v-else-if="!openTasks.length" class="rounded-4xl bg-mint-50 px-5 py-4 text-[15px] font-bold text-mint-700 dark:bg-mint-500/10 dark:text-mint-400" role="status">
						All done{{ isToday ? " for today" : "" }}! 🎉
					</div>
					<TransitionGroup
						v-else
						tag="ul"
						class="relative space-y-2.5"
						move-class="transition-transform duration-300"
						leave-active-class="absolute inset-x-0 transition-all duration-300"
						leave-to-class="translate-x-8 opacity-0"
					>
						<li v-for="t in openTasks" :key="t.name"><PlanTaskRow :task="t" @toggle="toggle(t)" @edit="openEditor(t)" /></li>
					</TransitionGroup>
				</section>

				<!-- completed tasks, shown only when the checkbox is ticked -->
				<section v-if="completedTasks.length" aria-labelledby="plan-done-title">
					<label class="inline-flex cursor-pointer select-none items-center gap-2.5 px-1 py-1 text-[14px] font-bold text-ink-600 dark:text-ink-300">
						<input v-model="showCompleted" type="checkbox" class="h-5 w-5 cursor-pointer rounded-md accent-mint-500" />
						<span id="plan-done-title">Show completed ({{ completedTasks.length }})</span>
					</label>
					<TransitionGroup v-if="showCompleted" tag="ul" class="mt-2.5 space-y-2.5" move-class="transition-transform duration-300">
						<li v-for="t in completedTasks" :key="t.name"><PlanTaskRow :task="t" @toggle="toggle(t)" @edit="openEditor(t)" /></li>
					</TransitionGroup>
				</section>
			</div>

			<aside class="space-y-5">
				<!-- unfinished from earlier days (today only) -->
				<section v-if="isToday && view.carryover.length" class="rounded-4xl bg-sun-50 p-4 dark:bg-sun-500/10" aria-labelledby="carry-title">
					<div class="mb-3 flex items-center gap-2">
						<History class="h-5 w-5 text-sun-700 dark:text-sun-400" />
						<h2 id="carry-title" class="flex-1 text-[16px] font-extrabold text-ink-900 dark:text-white">Unfinished from earlier</h2>
					</div>
					<ul class="space-y-2">
						<li v-for="t in view.carryover" :key="t.name" class="flex items-start gap-2 rounded-2xl bg-white/80 p-2.5 pl-3 dark:bg-night-900/70">
							<span class="min-w-0 flex-1">
								<span class="block break-words text-[14px] font-semibold leading-snug">{{ t.title }}</span>
								<span class="block text-[12px] text-ink-500 dark:text-ink-400">{{ relativeLabel(t.plan_date) }}</span>
							</span>
							<button
								type="button"
								class="shrink-0 rounded-xl px-2.5 py-1.5 text-[13px] font-bold text-grape-600 hover:bg-grape-50 disabled:opacity-50 dark:text-grape-300 dark:hover:bg-grape-500/10"
								:disabled="moving"
								@click="moveTo([t.name], today, 'Today')"
							>
								Do today
							</button>
						</li>
					</ul>
					<AppButton v-if="view.carryover.length > 1" class="mt-3" variant="secondary" block :loading="moving" @click="moveTo(view.carryover.map((t) => t.name), today, 'Today')">
						Move all {{ view.carryover.length }} to today
					</AppButton>
				</section>

				<!-- future days already planned -->
				<section class="rounded-4xl bg-white p-4 shadow-soft dark:bg-night-900" aria-labelledby="ahead-title">
					<div class="mb-2 flex items-center gap-2">
						<CalendarClock class="h-5 w-5 text-grape-600 dark:text-grape-300" />
						<h2 id="ahead-title" class="text-[16px] font-extrabold">Planned ahead</h2>
					</div>
					<p v-if="!view.upcoming.length" class="text-[13px] text-ink-500 dark:text-ink-400">
						Nothing planned beyond today yet. Pick a date above to plan ahead; tasks show up when their day arrives.
					</p>
					<ul v-else class="space-y-1">
						<li v-for="u in view.upcoming" :key="u.date">
							<button
								type="button"
								class="flex w-full items-center gap-3 rounded-2xl px-2 py-2 text-left transition hover:bg-ink-50 dark:hover:bg-night-800"
								:class="u.date === day ? 'bg-grape-50 dark:bg-grape-500/10' : ''"
								@click="goTo(u.date)"
							>
								<span class="min-w-0 flex-1 truncate text-[14px] font-semibold">{{ relativeLabel(u.date) }}</span>
								<span class="text-[12.5px] font-bold tabular-nums text-ink-500 dark:text-ink-400">
									{{ u.total }} task{{ u.total === 1 ? "" : "s" }}
								</span>
								<ChevronRight class="h-4 w-4 text-ink-400" />
							</button>
						</li>
					</ul>
				</section>
			</aside>
		</div>

		<!-- editor -->
		<BottomSheet :open="!!editing" title="Edit task" @close="editing = null">
			<form v-if="editing" class="space-y-4" @submit.prevent="saveEdit">
				<TextField id="t-title" v-model="editing.title" label="Task" maxlength="140" required />
				<div>
					<label for="t-notes" class="field-label">Notes (optional)</label>
					<textarea id="t-notes" v-model="editing.notes" rows="2" maxlength="1000" class="field h-auto py-3" />
				</div>
				<div class="grid grid-cols-2 gap-3">
					<div>
						<label for="t-date" class="field-label">Date</label>
						<input id="t-date" v-model="editing.plan_date" type="date" class="field px-3" required />
					</div>
					<div>
						<label for="t-time" class="field-label">Time (optional)</label>
						<input id="t-time" v-model="editing.start_time" type="time" class="field px-3" />
					</div>
				</div>
				<div class="flex flex-wrap gap-2">
					<button
						v-for="offset in [0, 1]"
						:key="offset"
						type="button"
						class="h-9 rounded-xl bg-ink-100 px-3 text-[13px] font-bold text-ink-700 hover:bg-ink-200 dark:bg-night-800 dark:text-ink-200"
						@click="editing.plan_date = addDays(today, offset)"
					>
						{{ offset === 0 ? "Today" : "Tomorrow" }}
					</button>
				</div>
				<div>
					<span class="field-label">Priority</span>
					<div class="flex gap-2">
						<button
							v-for="p in PRIORITIES"
							:key="p.value"
							type="button"
							class="h-10 flex-1 rounded-xl text-[14px] font-bold transition"
							:class="editing.priority === p.value ? 'bg-grape-500 text-white' : 'bg-ink-100 text-ink-700 hover:bg-ink-200 dark:bg-night-800 dark:text-ink-200'"
							:aria-pressed="editing.priority === p.value"
							@click="editing.priority = p.value"
						>
							{{ p.label }}
						</button>
					</div>
				</div>
				<div class="grid grid-cols-[auto_1fr] gap-3">
					<AppButton variant="ghost" size="lg" aria-label="Delete task" @click="removeEdit"><Trash2 class="h-5 w-5" /></AppButton>
					<AppButton type="submit" size="lg" block :loading="saving">Save</AppButton>
				</div>
			</form>
		</BottomSheet>
	</div>
</template>
