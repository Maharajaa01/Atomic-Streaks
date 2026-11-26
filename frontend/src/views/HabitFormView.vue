<script setup lang="ts">
import { Check, Plus } from "lucide-vue-next"
import { computed, onMounted, reactive, ref } from "vue"
import { useRouter } from "vue-router"

import { getHabit } from "@/api/habits"
import type { Category, Frequency, HabitInput, HabitType, TimeOfDay, Weekday } from "@/api/types"
import HabitIcon from "@/components/habits/HabitIcon.vue"
import AlertBanner from "@/components/ui/AlertBanner.vue"
import AppButton from "@/components/ui/AppButton.vue"
import BottomSheet from "@/components/ui/BottomSheet.vue"
import NumberStepper from "@/components/ui/NumberStepper.vue"
import PageHeader from "@/components/ui/PageHeader.vue"
import SegmentedControl from "@/components/ui/SegmentedControl.vue"
import SkeletonBlock from "@/components/ui/SkeletonBlock.vue"
import ToggleSwitch from "@/components/ui/ToggleSwitch.vue"
import { todayISO } from "@/lib/dates"
import { iconFor, PICKER_ICONS } from "@/lib/icons"
import { HABIT_COLORS } from "@/lib/palette"
import { useHabits } from "@/stores/habits"
import { useToast } from "@/stores/toast"

const props = defineProps<{ name?: string }>()
const router = useRouter()
const store = useHabits()
const toast = useToast()
const editing = computed(() => !!props.name)

const WEEKDAYS: Weekday[] = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
const UNITS = ["times", "minutes", "pages", "glasses", "steps", "km"]
const IDEAS: Partial<HabitInput>[] = [
	{ habit_name: "Drink water", icon: "glass-water", color: "#4D8DFF", category: "Health", daily_target: 8, target_unit: "glasses" },
	{ habit_name: "Read 10 pages", icon: "book-open", color: "#7657F6", category: "Reading", daily_target: 10, target_unit: "pages", time_of_day: "Evening" },
	{ habit_name: "Meditate", icon: "flower-2", color: "#9B7BFF", category: "Mindfulness", daily_target: 5, target_unit: "minutes", time_of_day: "Morning" },
	{ habit_name: "Walk", icon: "footprints", color: "#26C281", category: "Fitness", daily_target: 20, target_unit: "minutes" },
	{ habit_name: "No sugar", icon: "candy-off", color: "#F56FA1", category: "Health", habit_type: "Break" },
]

const form = reactive<HabitInput>({
	habit_name: "",
	description: "",
	icon: "sparkles",
	category: null,
	color: "#7657F6",
	habit_type: "Build",
	frequency: "Daily",
	interval_days: 2,
	weekdays: [],
	start_date: todayISO(),
	end_date: null,
	time_of_day: "Anytime",
	preferred_time: null,
	daily_target: 1,
	target_unit: "times",
	difficulty: "Medium",
	reminder_enabled: 0,
	reminder_time: null,
	notes: "",
})
const loading = ref(false)
const saving = ref(false)
const error = ref("")
const errors = reactive<{ name?: string; weekdays?: string; reminder?: string; end?: string }>({})
const nameInput = ref<HTMLInputElement | null>(null)

const reminderOn = computed({ get: () => !!form.reminder_enabled, set: (v) => (form.reminder_enabled = v ? 1 : 0) })
const hasEnd = ref(false)

onMounted(async () => {
	void store.loadCategories()
	if (!props.name) {
		nameInput.value?.focus()
		return
	}
	loading.value = true
	try {
		const h = await getHabit(props.name)
		Object.assign(form, {
			...h,
			category: h.category || null,
			weekdays: [...h.weekdays],
			interval_days: h.interval_days || 2,
			preferred_time: h.preferred_time || null,
			reminder_time: h.reminder_time || null,
		})
		hasEnd.value = !!h.end_date
	} catch (e) {
		error.value = (e as Error).message
	} finally {
		loading.value = false
	}
})

function useIdea(idea: Partial<HabitInput>) {
	Object.assign(form, { habit_type: "Build", daily_target: 1, target_unit: "times", time_of_day: "Anytime", ...idea })
}

function toggleDay(d: Weekday) {
	const days = new Set(form.weekdays)
	if (days.has(d)) days.delete(d)
	else days.add(d)
	form.weekdays = WEEKDAYS.filter((w) => days.has(w))
}

function validate(): boolean {
	errors.name = form.habit_name.trim() ? undefined : "Give your habit a name."
	errors.weekdays = form.frequency === "Specific Days" && !form.weekdays?.length ? "Pick at least one day." : undefined
	errors.reminder = form.reminder_enabled && !form.reminder_time ? "Choose a reminder time." : undefined
	errors.end = hasEnd.value && form.end_date && form.start_date && form.end_date < form.start_date ? "The end date is before the start date." : undefined
	return !errors.name && !errors.weekdays && !errors.reminder && !errors.end
}

async function save() {
	error.value = ""
	if (!validate()) {
		error.value = "Check the highlighted fields."
		return
	}
	saving.value = true
	const payload: Partial<HabitInput> = { ...form, habit_name: form.habit_name.trim(), end_date: hasEnd.value ? form.end_date : null }
	try {
		const h = editing.value ? await store.update(props.name!, payload) : await store.create(payload)
		toast.success(editing.value ? "Habit saved" : `"${h.habit_name}" added. Small steps!`)
		router.replace(editing.value ? { name: "habit", params: { name: h.name } } : { name: "home" })
	} catch (e) {
		error.value = (e as Error).message
	} finally {
		saving.value = false
	}
}

// ---------------------------------------------------------------- custom category
const newCat = reactive({ open: false, label: "", busy: false, error: "" })
async function addCategory() {
	if (!newCat.label.trim()) {
		newCat.error = "Name the category."
		return
	}
	newCat.busy = true
	newCat.error = ""
	try {
		const c: Category = await store.addCategory(newCat.label.trim(), form.icon, form.color)
		form.category = c.name
		Object.assign(newCat, { open: false, label: "" })
	} catch (e) {
		newCat.error = (e as Error).message
	} finally {
		newCat.busy = false
	}
}

const TYPES: { value: HabitType; label: string; hint: string }[] = [
	{ value: "Build", label: "Build", hint: "a good habit" },
	{ value: "Break", label: "Break", hint: "a bad habit" },
	{ value: "One-time", label: "Goal", hint: "do it once" },
]
const FREQS: { value: Frequency; label: string }[] = [
	{ value: "Daily", label: "Every day" },
	{ value: "Specific Days", label: "Some days" },
	{ value: "Every N Days", label: "Every few days" },
]
const TIMES: { value: TimeOfDay; label: string }[] = [
	{ value: "Morning", label: "Morning" },
	{ value: "Afternoon", label: "Afternoon" },
	{ value: "Evening", label: "Evening" },
	{ value: "Night", label: "Night" },
	{ value: "Anytime", label: "Any time" },
]
</script>

<template>
	<div>
		<PageHeader :title="editing ? 'Edit habit' : 'New habit'" :back="editing ? { name: 'habit', params: { name } } : { name: 'home' }" />

		<div v-if="loading" class="space-y-4"><SkeletonBlock class="h-40 rounded-4xl" /><SkeletonBlock class="h-64 rounded-4xl" /></div>

		<form v-else class="space-y-5 pb-28" novalidate @submit.prevent="save">
			<AlertBanner v-if="error" tone="error">{{ error }}</AlertBanner>

			<!-- name + look -->
			<section class="rounded-4xl bg-white p-5 shadow-soft dark:bg-night-900">
				<div class="flex items-center gap-4">
					<HabitIcon :icon="form.icon" :color="form.color" size="lg" />
					<div class="min-w-0 flex-1">
						<label for="habit-name" class="field-label">What's the habit?</label>
						<input
							id="habit-name"
							ref="nameInput"
							v-model="form.habit_name"
							class="field"
							:class="errors.name && 'field-invalid'"
							maxlength="140"
							placeholder="e.g. Read 10 pages"
							:aria-invalid="!!errors.name || undefined"
							aria-describedby="habit-name-error"
						/>
						<p v-if="errors.name" id="habit-name-error" class="mt-1.5 text-[13px] font-medium text-blush-700 dark:text-blush-400">{{ errors.name }}</p>
					</div>
				</div>
				<div v-if="!editing" class="mt-4 flex flex-wrap gap-2" aria-label="Ideas">
					<button
						v-for="idea in IDEAS"
						:key="idea.habit_name"
						type="button"
						class="inline-flex items-center gap-1.5 rounded-full border-2 border-ink-200 px-3 py-1.5 text-[13px] font-bold text-ink-700 hover:border-ink-300 dark:border-night-700 dark:text-ink-200"
						@click="useIdea(idea)"
					>
						<component :is="iconFor(idea.icon)" class="h-4 w-4" :style="{ color: idea.color }" /> {{ idea.habit_name }}
					</button>
				</div>

				<h3 class="mb-2 mt-6 font-sans text-[13px] font-semibold tracking-normal text-ink-700 dark:text-ink-200">Icon</h3>
				<div class="grid grid-cols-8 gap-1.5 sm:grid-cols-10" role="radiogroup" aria-label="Icon">
					<button
						v-for="n in PICKER_ICONS"
						:key="n"
						type="button"
						role="radio"
						:aria-checked="form.icon === n"
						:aria-label="n.replace(/-/g, ' ')"
						class="flex aspect-square items-center justify-center rounded-xl transition-colors"
						:class="form.icon === n ? 'text-white' : 'bg-ink-100 text-ink-600 hover:bg-ink-200 dark:bg-night-800 dark:text-ink-300'"
						:style="form.icon === n ? { background: form.color } : {}"
						@click="form.icon = n"
					>
						<component :is="iconFor(n)" class="h-5 w-5" />
					</button>
				</div>

				<h3 class="mb-2 mt-5 font-sans text-[13px] font-semibold tracking-normal text-ink-700 dark:text-ink-200">Colour</h3>
				<div class="flex flex-wrap gap-2.5" role="radiogroup" aria-label="Colour">
					<button
						v-for="c in HABIT_COLORS"
						:key="c"
						type="button"
						role="radio"
						:aria-checked="form.color === c"
						:aria-label="`Colour ${c}`"
						class="flex h-10 w-10 items-center justify-center rounded-full ring-offset-2 transition dark:ring-offset-night-900"
						:class="form.color === c && 'ring-[3px] ring-ink-900 dark:ring-white'"
						:style="{ background: c }"
						@click="form.color = c"
					>
						<Check v-if="form.color === c" class="h-5 w-5 text-white" :stroke-width="3" />
					</button>
				</div>
			</section>

			<!-- type + category -->
			<section class="space-y-5 rounded-4xl bg-white p-5 shadow-soft dark:bg-night-900">
				<div>
					<span class="field-label">Type</span>
					<SegmentedControl v-model="form.habit_type" :options="TYPES" label="Habit type" />
					<p v-if="form.habit_type === 'Break'" class="mt-2 text-[13px] text-ink-500 dark:text-ink-400">Check in each day you resist. Each one keeps the streak going.</p>
				</div>
				<div>
					<span class="field-label">Category</span>
					<div class="flex flex-wrap gap-2" role="radiogroup" aria-label="Category">
						<button
							v-for="c in store.categories ?? []"
							:key="c.name"
							type="button"
							role="radio"
							:aria-checked="form.category === c.name"
							class="inline-flex min-h-[40px] items-center gap-1.5 rounded-full border-2 px-3 text-[13px] font-bold transition-colors"
							:class="form.category === c.name ? 'border-transparent text-white' : 'border-ink-200 text-ink-700 dark:border-night-700 dark:text-ink-200'"
							:style="form.category === c.name ? { background: c.color } : {}"
							@click="form.category = form.category === c.name ? null : c.name"
						>
							<component :is="iconFor(c.icon)" class="h-4 w-4" />{{ c.label }}
						</button>
						<button
							type="button"
							class="inline-flex min-h-[40px] items-center gap-1 rounded-full border-2 border-dashed border-ink-300 px-3 text-[13px] font-bold text-ink-600 dark:border-night-600 dark:text-ink-300"
							@click="newCat.open = true"
						>
							<Plus class="h-4 w-4" /> New category
						</button>
					</div>
				</div>
			</section>

			<!-- schedule -->
			<section class="space-y-5 rounded-4xl bg-white p-5 shadow-soft dark:bg-night-900">
				<h2 class="text-[18px] font-extrabold">Schedule</h2>
				<SegmentedControl v-model="form.frequency" :options="FREQS" label="How often" />
				<div v-if="form.frequency === 'Specific Days'">
					<div class="flex justify-between gap-1.5" role="group" aria-label="Days of the week">
						<button
							v-for="d in WEEKDAYS"
							:key="d"
							type="button"
							:aria-pressed="form.weekdays?.includes(d)"
							:aria-label="d"
							class="flex h-11 w-11 items-center justify-center rounded-full text-[14px] font-extrabold transition-colors"
							:class="form.weekdays?.includes(d) ? 'text-white' : 'bg-ink-100 text-ink-600 dark:bg-night-800 dark:text-ink-300'"
							:style="form.weekdays?.includes(d) ? { background: form.color } : {}"
							@click="toggleDay(d)"
						>
							{{ d.slice(0, 2) }}
						</button>
					</div>
					<p v-if="errors.weekdays" class="mt-2 text-[13px] font-medium text-blush-700 dark:text-blush-400">{{ errors.weekdays }}</p>
				</div>
				<div v-if="form.frequency === 'Every N Days'" class="flex items-center gap-3">
					<span class="text-[15px] font-semibold">Every</span>
					<NumberStepper v-model="form.interval_days!" label="days between check-ins" :min="2" :max="365" class="w-40" />
					<span class="text-[15px] font-semibold">days</span>
				</div>
				<div class="grid gap-4 sm:grid-cols-2">
					<div>
						<label for="start-date" class="field-label">Starts</label>
						<input id="start-date" v-model="form.start_date" type="date" class="field" required />
					</div>
					<div>
						<ToggleSwitch v-model="hasEnd" label="Ends on a date" />
						<input v-if="hasEnd" v-model="form.end_date" type="date" class="field mt-1" :class="errors.end && 'field-invalid'" aria-label="End date" />
						<p v-if="errors.end" class="mt-1.5 text-[13px] font-medium text-blush-700 dark:text-blush-400">{{ errors.end }}</p>
					</div>
				</div>
				<div>
					<span class="field-label">Best time of day</span>
					<SegmentedControl v-model="form.time_of_day" :options="TIMES" label="Time of day" />
				</div>
				<div class="max-w-[12rem]">
					<label for="preferred-time" class="field-label">At a set time (optional)</label>
					<input id="preferred-time" v-model="form.preferred_time" type="time" class="field" />
				</div>
			</section>

			<!-- target -->
			<section v-if="form.habit_type === 'Build'" class="space-y-4 rounded-4xl bg-white p-5 shadow-soft dark:bg-night-900">
				<h2 class="text-[18px] font-extrabold">Daily target</h2>
				<div class="grid grid-cols-[10rem_1fr] gap-3">
					<NumberStepper v-model="form.daily_target" label="Daily target" :min="1" />
					<input v-model="form.target_unit" class="field" maxlength="40" aria-label="Unit" placeholder="times" list="units" />
					<datalist id="units"><option v-for="u in UNITS" :key="u" :value="u" /></datalist>
				</div>
				<p class="text-[13px] text-ink-500 dark:text-ink-400">Tip: start smaller than you think. Two pages beats zero pages.</p>
				<div>
					<span class="field-label">Difficulty</span>
					<SegmentedControl
						v-model="form.difficulty"
						:options="[{ value: 'Easy', label: 'Easy' }, { value: 'Medium', label: 'Medium' }, { value: 'Hard', label: 'Hard' }]"
						label="Difficulty"
					/>
				</div>
			</section>

			<!-- reminder + notes -->
			<section class="space-y-4 rounded-4xl bg-white p-5 shadow-soft dark:bg-night-900">
				<ToggleSwitch v-model="reminderOn" label="Remind me" description="A notification at the time you choose, on devices where notifications are on (Profile)." />
				<div v-if="reminderOn" class="max-w-[12rem]">
					<label for="reminder-time" class="field-label">Reminder time</label>
					<input id="reminder-time" v-model="form.reminder_time" type="time" class="field" :class="errors.reminder && 'field-invalid'" />
					<p v-if="errors.reminder" class="mt-1.5 text-[13px] font-medium text-blush-700 dark:text-blush-400">{{ errors.reminder }}</p>
				</div>
				<div>
					<label for="description" class="field-label">Why it matters to you (optional)</label>
					<textarea id="description" v-model="form.description" rows="2" maxlength="1000" class="field h-auto py-3" placeholder="I want more energy in the mornings." />
				</div>
				<div>
					<label for="notes" class="field-label">Notes (optional)</label>
					<textarea id="notes" v-model="form.notes" rows="2" maxlength="4000" class="field h-auto py-3" />
				</div>
			</section>

			<!-- sticky save bar -->
			<div
				class="fixed inset-x-0 bottom-0 z-40 border-t border-ink-200/70 bg-white/95 px-4 pt-3 backdrop-blur-lg dark:border-night-800 dark:bg-night-900/95 lg:left-64"
				style="padding-bottom: max(env(safe-area-inset-bottom), 0.75rem)"
			>
				<div class="mx-auto flex max-w-xl gap-3">
					<AppButton variant="secondary" size="lg" class="flex-1" @click="$router.back()">Cancel</AppButton>
					<AppButton type="submit" size="lg" class="flex-[2]" :loading="saving">{{ editing ? "Save changes" : "Create habit" }}</AppButton>
				</div>
			</div>
		</form>

		<BottomSheet :open="newCat.open" title="New category" @close="newCat.open = false">
			<form class="space-y-4" novalidate @submit.prevent="addCategory">
				<AlertBanner v-if="newCat.error" tone="error">{{ newCat.error }}</AlertBanner>
				<div>
					<label for="cat-name" class="field-label">Name</label>
					<input id="cat-name" v-model="newCat.label" class="field" maxlength="60" placeholder="e.g. Music practice" />
				</div>
				<p class="text-[13px] text-ink-500 dark:text-ink-400">It uses the icon and colour you picked for this habit. Only you can see it.</p>
				<AppButton type="submit" size="lg" block :loading="newCat.busy">Add category</AppButton>
			</form>
		</BottomSheet>
	</div>
</template>
