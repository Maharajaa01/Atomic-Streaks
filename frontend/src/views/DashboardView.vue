<script setup lang="ts">
import { Bot, ChevronRight, LayoutList, ListTodo, Moon, Plus, RefreshCw, Sprout, Sun, Sunrise, Sunset, Trophy } from "lucide-vue-next"
import { computed, onMounted, ref, watch } from "vue"

import { getPlanDay } from "@/api/planner"
import type { DayPeriod, PlanDay, TodayHabit } from "@/api/types"

import DailyProgressCard from "@/components/habits/DailyProgressCard.vue"
import HabitCard from "@/components/habits/HabitCard.vue"
import WeekStrip from "@/components/habits/WeekStrip.vue"
import AppButton from "@/components/ui/AppButton.vue"
import EmptyState from "@/components/ui/EmptyState.vue"
import SkeletonBlock from "@/components/ui/SkeletonBlock.vue"
import UserAvatar from "@/components/ui/UserAvatar.vue"
import { dayPeriod, formatDay, greeting } from "@/lib/dates"
import { isDone, useHabits } from "@/stores/habits"
import { useSession } from "@/stores/session"

const session = useSession()
const store = useHabits()

const plan = ref<PlanDay | null>(null)
onMounted(() => {
	void store.loadToday(!!store.today)
	getPlanDay()
		.then((p) => (plan.value = p))
		.catch(() => undefined) // the card just shows its default text
})
const planSummary = computed(() => {
	const p = plan.value
	if (!p) return "Plan your day"
	const open = p.tasks.filter((t) => !t.is_done)
	if (!p.tasks.length) return new Date().getHours() >= 18 ? "Plan tomorrow tonight" : "Nothing planned yet"
	if (!open.length) return `All ${p.tasks.length} done today`
	return `${p.tasks.length - open.length} of ${p.tasks.length} done · next: ${open[0]!.title}`
})

const view = computed(() => store.today)
const comeback = computed(() => {
	const v = view.value
	return !!v && v.streak.current === 0 && v.streak.longest > 0 && v.summary.completed === 0 && v.summary.total > 0
})
const SECTION_LABEL: Record<string, string> = { Morning: "Morning", Afternoon: "Afternoon", Evening: "Evening", Night: "Night", Anytime: "Any time" }

// Morning / Afternoon / Evening / Night tabs. Opens on the part of the day it is now; "Any time"
// habits show under every tab, since they fit whenever you get to them.
type PeriodTab = DayPeriod | "All"
const PERIODS: { value: PeriodTab; label: string; icon: typeof Sun }[] = [
	{ value: "Morning", label: "Morning", icon: Sunrise },
	{ value: "Afternoon", label: "Afternoon", icon: Sun },
	{ value: "Evening", label: "Evening", icon: Sunset },
	{ value: "Night", label: "Night", icon: Moon },
	{ value: "All", label: "All", icon: LayoutList },
]
const now = dayPeriod()
const period = ref<PeriodTab>(now)

const counts = computed(() => {
	const out: Record<string, { done: number; total: number }> = {}
	for (const p of PERIODS) out[p.value] = { done: 0, total: 0 }
	for (const h of view.value?.habits ?? []) {
		for (const key of [h.time_of_day in out ? h.time_of_day : null, "All"]) {
			if (!key || key === "Anytime") continue
			out[key]!.total++
			if (isDone(h)) out[key]!.done++
		}
	}
	return out
})
const sections = computed(() =>
	period.value === "All" ? store.byTimeOfDay : store.byTimeOfDay.filter(([s]) => s === period.value || s === "Anytime"),
)
const periodEmpty = computed(() => period.value !== "All" && !sections.value.some(([s]) => s === period.value))

// "Completed" checkbox: unticked shows what's still to do, ticked shows what's been completed.
// A habit that was just completed stays put briefly so its check-in animation is seen.
const SHOW_DONE_KEY = "atomic-home-show-completed"
const showCompleted = ref(localStorage.getItem(SHOW_DONE_KEY) === "1")
watch(showCompleted, (v) => localStorage.setItem(SHOW_DONE_KEY, v ? "1" : "0"))
const settling = ref(new Set<string>())
const doneNames = computed(() => (view.value?.habits ?? []).filter(isDone).map((h) => h.name))
watch(doneNames, (now, before) => {
	if (!before) return
	for (const name of now) {
		if (before.includes(name)) continue
		settling.value.add(name)
		setTimeout(() => settling.value.delete(name), 900)
	}
})
const shown = (h: TodayHabit) =>
	showCompleted.value ? isDone(h) && !settling.value.has(h.name) : !isDone(h) || settling.value.has(h.name)
const visibleSections = computed(() =>
	sections.value.map(([s, list]) => [s, list.filter(shown)] as const).filter(([, list]) => list.length),
)
const completedInPeriod = computed(() => sections.value.reduce((n, [, list]) => n + list.filter(isDone).length, 0))
</script>

<template>
	<div>
		<header class="flex items-center gap-3 pb-5" style="padding-top: max(env(safe-area-inset-top), 1.25rem)">
			<div class="min-w-0 flex-1">
				<p class="text-[13px] font-semibold text-ink-500 dark:text-ink-400">{{ view ? formatDay(view.today) : " " }}</p>
				<h1 class="mt-0.5 text-[28px] font-extrabold leading-tight sm:text-[32px]">
					{{ greeting() }}{{ session.firstName ? `, ${session.firstName}` : "" }}!
				</h1>
				<p class="mt-1 text-[15px] text-ink-500 dark:text-ink-400">Ready to become 1% better today?</p>
			</div>
			<RouterLink :to="{ name: 'profile' }" class="rounded-full lg:hidden" aria-label="Your profile"><UserAvatar :size="48" /></RouterLink>
		</header>

		<!-- first load -->
		<div v-if="!view && store.loadingToday" class="space-y-4" aria-busy="true">
			<SkeletonBlock class="h-56 rounded-4xl" />
			<SkeletonBlock class="h-28 rounded-4xl" />
			<SkeletonBlock v-for="i in 3" :key="i" class="h-20 rounded-3xl" />
		</div>

		<EmptyState v-else-if="!view && store.todayError" :icon="RefreshCw" title="Couldn't load today" :body="store.todayError">
			<AppButton @click="store.loadToday()">Try again</AppButton>
		</EmptyState>

		<div v-else-if="view" class="grid grid-cols-[minmax(0,1fr)] gap-5 lg:grid-cols-[minmax(0,1fr)_20rem] lg:items-start">
			<div class="min-w-0 space-y-5">
				<DailyProgressCard :view="view" />
				<WeekStrip class="lg:hidden" :days="view.week" />

				<div
					v-if="comeback"
					class="flex items-start gap-3 rounded-3xl bg-sun-50 p-4 text-sun-700 dark:bg-sun-500/10 dark:text-sun-400"
					role="status"
				>
					<Sunrise class="mt-0.5 h-6 w-6 shrink-0" />
					<p class="text-[14px] font-semibold leading-snug">
						Missed a day? That's part of it. Your best run was {{ view.streak.longest }} days. Check in once today and a new
						streak begins.
					</p>
				</div>

				<!-- today's habits -->
				<section aria-labelledby="today-title">
					<div class="mb-3 flex items-center justify-between">
						<h2 id="today-title" class="text-[20px] font-extrabold">Today's habits</h2>
						<RouterLink :to="{ name: 'habit-new' }" class="hidden items-center gap-1 text-[14px] font-bold text-grape-600 hover:underline dark:text-grape-300 sm:inline-flex">
							<Plus class="h-4 w-4" :stroke-width="2.6" /> Add habit
						</RouterLink>
					</div>

					<div v-if="!view.habits.length" class="rounded-4xl bg-white shadow-soft dark:bg-night-900">
						<EmptyState
							v-if="!view.summary.active_habits"
							:icon="Sprout"
							title="Start with one tiny habit"
							body="Pick something so small it's hard to skip, like drinking a glass of water after you wake up."
						>
							<AppButton size="lg" @click="$router.push({ name: 'habit-new' })"><Plus class="h-5 w-5" /> Create your first habit</AppButton>
						</EmptyState>
						<EmptyState v-else :icon="Sunrise" title="Nothing due today" body="None of your habits are scheduled for today. Rest counts too." />
					</div>

					<div v-if="view.habits.length" role="tablist" aria-label="Part of the day" class="mb-4 grid grid-cols-5 gap-1.5 sm:gap-2">
						<button
							v-for="p in PERIODS"
							:key="p.value"
							type="button"
							role="tab"
							:aria-selected="period === p.value"
							aria-controls="period-panel"
							class="relative flex min-h-[44px] min-w-0 flex-col items-center gap-0.5 rounded-2xl px-0.5 py-2 text-[11.5px] font-bold tracking-tight transition-colors sm:flex-row sm:tracking-normal sm:justify-center sm:gap-1.5 sm:px-3 sm:text-[14px]"
							:class="
								period === p.value
									? 'bg-grape-500 text-white shadow-lift'
									: 'bg-white text-ink-600 shadow-soft hover:text-ink-900 dark:bg-night-900 dark:text-ink-300 dark:hover:text-white'
							"
							@click="period = p.value"
						>
							<component :is="p.icon" class="h-5 w-5 shrink-0 sm:h-4 sm:w-4" :stroke-width="2.5" />
							<span class="max-w-full truncate">{{ p.label }}</span>
							<span
								v-if="counts[p.value]!.total"
								class="rounded-md px-1.5 text-[10.5px] tabular-nums sm:text-[11px]"
								:class="period === p.value ? 'bg-white/20' : 'bg-ink-100 dark:bg-night-800'"
							>
								{{ counts[p.value]!.done }}/{{ counts[p.value]!.total }}
							</span>
							<span v-if="p.value === now" class="absolute -top-1 right-1.5 h-2.5 w-2.5 rounded-full border-2 border-white bg-mint-500 dark:border-night-950" title="Now" />
							<span v-if="p.value === now" class="sr-only">(now)</span>
						</button>
					</div>

					<div v-if="view.habits.length" class="-mt-2 mb-3 flex justify-end">
						<label class="inline-flex cursor-pointer select-none items-center gap-2.5 px-1 py-1 text-[14px] font-bold text-ink-600 dark:text-ink-300">
							<input v-model="showCompleted" type="checkbox" class="h-5 w-5 cursor-pointer rounded-md accent-mint-500" />
							Completed
							<span class="rounded-md bg-ink-100 px-1.5 text-[12px] tabular-nums dark:bg-night-800">{{ completedInPeriod }}</span>
						</label>
					</div>

					<div id="period-panel" role="tabpanel">
						<p
							v-if="view.habits.length && periodEmpty"
							class="mb-4 rounded-3xl bg-white px-4 py-3.5 text-[14px] font-semibold text-ink-500 shadow-soft dark:bg-night-900 dark:text-ink-400"
						>
							No {{ period.toLowerCase() }} habits today.
							<RouterLink :to="{ name: 'habit-new' }" class="link">Add one</RouterLink>
						</p>

						<p
							v-else-if="view.habits.length && !visibleSections.length"
							class="mb-4 rounded-3xl px-4 py-3.5 text-[14px] font-semibold"
							:class="showCompleted ? 'bg-white text-ink-500 shadow-soft dark:bg-night-900 dark:text-ink-400' : 'bg-mint-50 text-mint-700 dark:bg-mint-500/10 dark:text-mint-400'"
							role="status"
						>
							<template v-if="showCompleted">Nothing completed {{ period === "All" ? "today" : `this ${period.toLowerCase()}` }} yet.</template>
							<template v-else>All done {{ period === "All" ? "for today" : `for the ${period.toLowerCase()}` }}! 🎉 Tick “Completed” to see them.</template>
						</p>

						<div v-for="[section, list] in visibleSections" :key="section" class="mb-5">
							<h3 class="mb-2 px-1 font-sans text-[13px] font-bold tracking-normal text-ink-500 dark:text-ink-400">{{ SECTION_LABEL[section] }}</h3>
							<TransitionGroup tag="ul" class="space-y-2.5" move-class="transition-transform duration-300">
								<li v-for="h in list" :key="h.name"><HabitCard :habit="h" /></li>
							</TransitionGroup>
						</div>
					</div>
				</section>
			</div>

			<aside class="space-y-5">
				<WeekStrip class="hidden lg:block" :days="view.week" />
				<nav aria-label="More ways to grow" class="grid grid-cols-2 gap-3 lg:grid-cols-1">
					<RouterLink :to="{ name: 'plan' }" class="group col-span-2 flex items-center gap-3 rounded-3xl bg-sky-50 p-4 dark:bg-sky-500/10 lg:col-span-1">
						<span class="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-sky-500 text-white"><ListTodo class="h-5 w-5" /></span>
						<span class="min-w-0 flex-1">
							<span class="block text-[15px] font-bold text-ink-900 dark:text-white">Day Plan</span>
							<span class="block truncate text-[12px] text-ink-500 dark:text-ink-400">{{ planSummary }}</span>
						</span>
						<ChevronRight class="h-5 w-5 text-ink-400" />
					</RouterLink>
					<RouterLink :to="{ name: 'challenges' }" class="group flex items-center gap-3 rounded-3xl bg-tangerine-50 p-4 dark:bg-tangerine-500/10">
						<span class="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-tangerine-500 text-white"><Trophy class="h-5 w-5" /></span>
						<span class="min-w-0 flex-1">
							<span class="block text-[15px] font-bold text-ink-900 dark:text-white">Challenges</span>
							<span class="block truncate text-[12px] text-ink-500 dark:text-ink-400">7, 21 and 30 days</span>
						</span>
						<ChevronRight class="hidden h-5 w-5 text-ink-400 sm:block" />
					</RouterLink>
					<RouterLink :to="{ name: 'coach' }" class="group flex items-center gap-3 rounded-3xl bg-grape-50 p-4 dark:bg-grape-500/10">
						<span class="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl bg-grape-500 text-white"><Bot class="h-5 w-5" /></span>
						<span class="min-w-0 flex-1">
							<span class="block text-[15px] font-bold text-ink-900 dark:text-white">AI Coach</span>
							<span class="block truncate text-[12px] text-ink-500 dark:text-ink-400">Ideas and tips</span>
						</span>
						<ChevronRight class="hidden h-5 w-5 text-ink-400 sm:block" />
					</RouterLink>
				</nav>
			</aside>
		</div>

		<!-- quick add (phones) -->
		<RouterLink
			:to="{ name: 'habit-new' }"
			class="fixed right-5 z-30 flex h-16 w-16 items-center justify-center rounded-[1.4rem] bg-gradient-to-br from-grape-500 to-grape-600 text-white shadow-lift active:scale-95 lg:hidden"
			style="bottom: calc(env(safe-area-inset-bottom) + 5.5rem)"
			aria-label="Add a habit"
		>
			<Plus class="h-8 w-8" :stroke-width="2.6" />
		</RouterLink>
	</div>
</template>
