<script setup lang="ts">
import { ArrowDown, ArrowUp, Check, Layers, Pencil, Play, Plus, RefreshCw, SkipForward, Trash2, X } from "lucide-vue-next"
import { computed, onMounted, ref } from "vue"

import { deleteRoutine, getRoutines, saveRoutine } from "@/api/growth"
import { completeHabit } from "@/api/habits"
import type { Routine, RoutineStep, TimeOfDay } from "@/api/types"
import HabitIcon from "@/components/habits/HabitIcon.vue"
import AppButton from "@/components/ui/AppButton.vue"
import BottomSheet from "@/components/ui/BottomSheet.vue"
import EmptyState from "@/components/ui/EmptyState.vue"
import PageHeader from "@/components/ui/PageHeader.vue"
import SkeletonBlock from "@/components/ui/SkeletonBlock.vue"
import TextField from "@/components/ui/TextField.vue"
import { online } from "@/lib/pwa"
import { useConfirm } from "@/stores/confirm"
import { useHabits } from "@/stores/habits"
import { useToast } from "@/stores/toast"

const habits = useHabits()
const toast = useToast()
const confirm = useConfirm()

const routines = ref<Routine[] | null>(null)
const error = ref("")

async function load() {
	error.value = ""
	try {
		routines.value = await getRoutines()
	} catch (e) {
		error.value = (e as Error).message
	}
}
onMounted(() => {
	void load()
	if (!habits.habits) void habits.loadHabits().catch(() => undefined)
})

// ------------------------------------------------------------------ editor
interface Draft {
	name?: string
	routine_name: string
	cue: string
	time_of_day: TimeOfDay
	steps: { habit: string; note: string }[]
}
const editing = ref<Draft | null>(null)
const saving = ref(false)
const picking = ref("")
const TIMES: TimeOfDay[] = ["Morning", "Afternoon", "Evening", "Night", "Anytime"]

const byName = computed(() => Object.fromEntries((habits.habits ?? []).map((h) => [h.name, h])))
const available = computed(() =>
	(habits.habits ?? []).filter((h) => h.status === "Active" && !editing.value?.steps.some((s) => s.habit === h.name)),
)

function openEditor(r?: Routine) {
	editing.value = r
		? {
				name: r.name,
				routine_name: r.routine_name,
				cue: r.cue ?? "",
				time_of_day: r.time_of_day ?? "Morning",
				steps: r.steps.map((s) => ({ habit: s.habit, note: s.note ?? "" })),
			}
		: { routine_name: "", cue: "", time_of_day: "Morning", steps: [] }
	picking.value = ""
}

function addStep() {
	if (!editing.value || !picking.value) return
	editing.value.steps.push({ habit: picking.value, note: "" })
	picking.value = ""
}

function move(i: number, by: number) {
	const steps = editing.value?.steps
	if (!steps || i + by < 0 || i + by >= steps.length) return
	const [s] = steps.splice(i, 1)
	steps.splice(i + by, 0, s!)
}

async function save() {
	const d = editing.value
	if (!d) return
	if (!d.routine_name.trim()) return toast.error("Give your routine a name.")
	if (!d.steps.length) return toast.error("Add at least one habit.")
	saving.value = true
	try {
		await saveRoutine(
			{
				routine_name: d.routine_name.trim(),
				cue: d.cue.trim(),
				time_of_day: d.time_of_day,
				steps: d.steps.map((s) => ({ habit: s.habit, note: s.note.trim() || undefined })),
			},
			d.name,
		)
		editing.value = null
		await load()
		toast.success("Routine saved")
	} catch (e) {
		toast.error((e as Error).message)
	} finally {
		saving.value = false
	}
}

async function remove(r: Routine) {
	const ok = await confirm.ask({ title: `Delete "${r.routine_name}"?`, body: "The habits themselves stay.", confirmLabel: "Delete", danger: true })
	if (!ok) return
	try {
		await deleteRoutine(r.name)
		await load()
	} catch (e) {
		toast.error((e as Error).message)
	}
}

// ------------------------------------------------------------------ guided run
const running = ref<Routine | null>(null)
const stepIndex = ref(0)
const stepBusy = ref(false)
const results = ref<("done" | "skipped")[]>([])

const runnable = (r: Routine) => r.steps.filter((s) => s.status === "Active")
const current = computed<RoutineStep | null>(() => (running.value ? (runnable(running.value)[stepIndex.value] ?? null) : null))
const finished = computed(() => !!running.value && !current.value)

function start(r: Routine) {
	const steps = runnable(r)
	if (!steps.length) return toast.error("This routine has no active habits.")
	running.value = r
	results.value = []
	// start at the first step not done yet today
	const first = steps.findIndex((s) => !s.done)
	stepIndex.value = first === -1 ? 0 : first
	for (let i = 0; i < stepIndex.value; i++) results.value.push("done")
}

async function markDone() {
	const s = current.value
	if (!s) return
	if (s.done) return next("done")
	if (!online.value) return toast.error("You're offline. Connect to save check-ins.")
	stepBusy.value = true
	try {
		await completeHabit(s.habit, { value: s.habit_type === "Build" ? Math.max(s.daily_target || 1, 1) : 1 })
		s.done = true
		next("done")
	} catch (e) {
		toast.error((e as Error).message)
	} finally {
		stepBusy.value = false
	}
}

function next(result: "done" | "skipped") {
	results.value[stepIndex.value] = result
	stepIndex.value++
}

function closeRun() {
	running.value = null
	void load()
	void habits.loadToday(true)
}

const doneCount = computed(() => results.value.filter((r) => r === "done").length)
</script>

<template>
	<div>
		<PageHeader title="Routines" subtitle="Stack habits so one leads to the next" :back="{ name: 'habits' }">
			<template #actions>
				<AppButton @click="openEditor()"><Plus class="h-5 w-5" :stroke-width="2.6" /> New</AppButton>
			</template>
		</PageHeader>

		<EmptyState v-if="error" :icon="RefreshCw" title="Couldn't load routines" :body="error"><AppButton @click="load">Try again</AppButton></EmptyState>

		<div v-else-if="!routines" class="space-y-3"><SkeletonBlock v-for="i in 2" :key="i" class="h-40 rounded-4xl" /></div>

		<div v-else-if="!routines.length" class="rounded-4xl bg-white shadow-soft dark:bg-night-900">
			<EmptyState
				:icon="Layers"
				title="Build your first routine"
				body="Chain habits to something you already do: &quot;After I wake up: drink water, stretch, read 2 pages.&quot;"
			>
				<AppButton size="lg" @click="openEditor()"><Plus class="h-5 w-5" /> Create a routine</AppButton>
			</EmptyState>
		</div>

		<ul v-else class="grid gap-3 sm:grid-cols-2">
			<li v-for="r in routines" :key="r.name" class="flex flex-col rounded-4xl bg-white p-5 shadow-soft dark:bg-night-900">
				<div class="flex items-start gap-3">
					<div class="min-w-0 flex-1">
						<p class="text-[12px] font-bold uppercase tracking-wide text-grape-600 dark:text-grape-300">{{ r.time_of_day || "Anytime" }}</p>
						<h3 class="text-[18px] font-extrabold leading-snug">{{ r.routine_name }}</h3>
						<p v-if="r.cue" class="mt-0.5 text-[14px] text-ink-500 dark:text-ink-400">{{ r.cue }}</p>
					</div>
					<button type="button" class="rounded-xl p-2 text-ink-400 hover:bg-ink-100 dark:hover:bg-night-800" :aria-label="`Edit ${r.routine_name}`" @click="openEditor(r)">
						<Pencil class="h-4 w-4" />
					</button>
					<button type="button" class="rounded-xl p-2 text-ink-400 hover:bg-ink-100 hover:text-blush-600 dark:hover:bg-night-800" :aria-label="`Delete ${r.routine_name}`" @click="remove(r)">
						<Trash2 class="h-4 w-4" />
					</button>
				</div>
				<ol class="mt-4 flex-1 space-y-2">
					<li v-for="(s, i) in r.steps" :key="s.habit" class="flex items-center gap-3" :class="s.status !== 'Active' ? 'opacity-50' : ''">
						<span class="w-5 text-center text-[13px] font-bold text-ink-400">{{ i + 1 }}</span>
						<HabitIcon :icon="s.icon" :color="s.color" size="sm" />
						<span class="min-w-0 flex-1 truncate text-[15px] font-semibold" :class="s.done ? 'text-ink-400 line-through' : ''">{{ s.habit_name }}</span>
						<Check v-if="s.done" class="h-5 w-5 text-mint-500" :stroke-width="3" />
					</li>
				</ol>
				<div class="mt-4 flex items-center justify-between gap-3">
					<span class="text-[13px] font-bold text-ink-500 dark:text-ink-400">{{ r.done_today }} of {{ r.steps.length }} done today</span>
					<AppButton :disabled="r.done_today >= r.steps.length" @click="start(r)">
						<Play class="h-4 w-4" /> {{ r.done_today ? "Continue" : "Start" }}
					</AppButton>
				</div>
			</li>
		</ul>

		<!-- editor -->
		<BottomSheet :open="!!editing" :title="editing?.name ? 'Edit routine' : 'New routine'" @close="editing = null">
			<form v-if="editing" class="space-y-4" @submit.prevent="save">
				<TextField id="r-name" v-model="editing.routine_name" label="Name" placeholder="Morning kick-off" maxlength="140" required />
				<TextField id="r-cue" v-model="editing.cue" label="Cue" placeholder="After I pour my morning tea" maxlength="140" hint="The thing you already do that starts it." />
				<div>
					<span class="field-label">When</span>
					<div class="flex flex-wrap gap-2">
						<button
							v-for="t in TIMES"
							:key="t"
							type="button"
							class="h-10 rounded-xl px-3.5 text-[14px] font-bold transition"
							:class="editing.time_of_day === t ? 'bg-grape-500 text-white' : 'bg-ink-100 text-ink-700 hover:bg-ink-200 dark:bg-night-800 dark:text-ink-200'"
							:aria-pressed="editing.time_of_day === t"
							@click="editing.time_of_day = t"
						>
							{{ t === "Anytime" ? "Any time" : t }}
						</button>
					</div>
				</div>
				<div>
					<span class="field-label">Habits, in order</span>
					<ol v-if="editing.steps.length" class="space-y-2">
						<li v-for="(s, i) in editing.steps" :key="s.habit" class="flex items-center gap-2 rounded-2xl bg-ink-50 p-2 dark:bg-night-800">
							<HabitIcon :icon="byName[s.habit]?.icon" :color="byName[s.habit]?.color" size="sm" />
							<span class="min-w-0 flex-1 truncate text-[14px] font-semibold">{{ byName[s.habit]?.habit_name ?? "Habit" }}</span>
							<button type="button" class="rounded-lg p-1.5 text-ink-500 disabled:opacity-30" :disabled="i === 0" :aria-label="`Move up`" @click="move(i, -1)"><ArrowUp class="h-4 w-4" /></button>
							<button type="button" class="rounded-lg p-1.5 text-ink-500 disabled:opacity-30" :disabled="i === editing.steps.length - 1" aria-label="Move down" @click="move(i, 1)"><ArrowDown class="h-4 w-4" /></button>
							<button type="button" class="rounded-lg p-1.5 text-ink-500 hover:text-blush-600" aria-label="Remove" @click="editing.steps.splice(i, 1)"><X class="h-4 w-4" /></button>
						</li>
					</ol>
					<div class="mt-2 flex gap-2">
						<label for="r-pick" class="sr-only">Add a habit</label>
						<select id="r-pick" v-model="picking" class="field flex-1">
							<option value="">{{ available.length ? "Add a habit…" : habits.habits ? "No more active habits" : "Loading…" }}</option>
							<option v-for="h in available" :key="h.name" :value="h.name">{{ h.habit_name }}</option>
						</select>
						<AppButton variant="secondary" :disabled="!picking" @click="addStep"><Plus class="h-5 w-5" /></AppButton>
					</div>
				</div>
				<AppButton type="submit" size="lg" block :loading="saving">Save routine</AppButton>
			</form>
		</BottomSheet>

		<!-- guided run-through -->
		<BottomSheet :open="!!running" :title="running?.routine_name ?? ''" @close="closeRun">
			<template v-if="running">
				<div class="mb-5 flex gap-1.5" aria-hidden="true">
					<span
						v-for="(_, i) in runnable(running)"
						:key="i"
						class="h-1.5 flex-1 rounded-full transition-colors"
						:class="results[i] === 'done' ? 'bg-mint-500' : results[i] === 'skipped' ? 'bg-ink-300 dark:bg-night-600' : i === stepIndex ? 'bg-grape-500' : 'bg-ink-100 dark:bg-night-800'"
					/>
				</div>

				<div v-if="current" :key="current.habit" class="animate-fade-up text-center">
					<p class="text-[13px] font-bold text-ink-500 dark:text-ink-400">
						Step {{ stepIndex + 1 }} of {{ runnable(running).length }}<template v-if="stepIndex === 0 && running.cue"> · {{ running.cue }}</template>
					</p>
					<HabitIcon :icon="current.icon" :color="current.color" size="lg" class="mx-auto mt-4 !h-24 !w-24 shadow-lift" />
					<h3 class="mt-4 text-[24px] font-extrabold leading-tight">{{ current.habit_name }}</h3>
					<p v-if="current.habit_type === 'Build' && current.daily_target > 1" class="mt-1 text-[15px] text-ink-500 dark:text-ink-400">
						{{ current.daily_target }} {{ current.target_unit }}
					</p>
					<p v-if="current.note" class="mt-2 text-[15px] text-ink-600 dark:text-ink-300">{{ current.note }}</p>
					<p v-if="current.done" class="mt-3 text-[14px] font-bold text-mint-600 dark:text-mint-400">Already done today</p>
					<div class="mt-7 grid grid-cols-[auto_1fr] gap-3">
						<AppButton variant="ghost" size="lg" @click="next('skipped')"><SkipForward class="h-5 w-5" /> Skip</AppButton>
						<AppButton size="lg" :loading="stepBusy" @click="markDone"><Check class="h-5 w-5" :stroke-width="3" /> {{ current.done ? "Next" : "Done" }}</AppButton>
					</div>
				</div>

				<div v-else-if="finished" class="animate-fade-up text-center">
					<span class="mx-auto flex h-20 w-20 items-center justify-center rounded-[1.8rem] bg-mint-500 text-white shadow-lift"><Check class="h-10 w-10" :stroke-width="3" /></span>
					<h3 class="mt-4 text-[24px] font-extrabold">Routine complete</h3>
					<p class="mt-1 text-[15px] text-ink-500 dark:text-ink-400">
						{{ doneCount }} of {{ runnable(running).length }} habits done. {{ doneCount === runnable(running).length ? "Every link in the chain." : "Showing up is what counts." }}
					</p>
					<AppButton class="mt-6" size="lg" block @click="closeRun">Finish</AppButton>
				</div>
			</template>
		</BottomSheet>
	</div>
</template>
