<script setup lang="ts">
import { CalendarCheck, Flag, Lock, Plus, RefreshCw, Sparkles, Trophy } from "lucide-vue-next"
import { computed, onMounted, ref, watch } from "vue"
import { useRoute, useRouter } from "vue-router"

import { createChallenge, getChallenges, getProgress, joinChallenge, leaveChallenge } from "@/api/growth"
import type { Challenge, ChallengesOverview, Participation, ProgressSummary } from "@/api/types"
import HabitIcon from "@/components/habits/HabitIcon.vue"
import AppButton from "@/components/ui/AppButton.vue"
import BottomSheet from "@/components/ui/BottomSheet.vue"
import EmptyState from "@/components/ui/EmptyState.vue"
import PageHeader from "@/components/ui/PageHeader.vue"
import ProgressRing from "@/components/ui/ProgressRing.vue"
import SegmentedControl from "@/components/ui/SegmentedControl.vue"
import SkeletonBlock from "@/components/ui/SkeletonBlock.vue"
import TextField from "@/components/ui/TextField.vue"
import { formatDay } from "@/lib/dates"
import { useCelebrations } from "@/stores/celebrations"
import { useConfirm } from "@/stores/confirm"
import { useHabits } from "@/stores/habits"
import { useToast } from "@/stores/toast"

type Tab = "mine" | "discover" | "badges"
const route = useRoute()
const router = useRouter()
const toast = useToast()
const confirm = useConfirm()
const habits = useHabits()
const celebrations = useCelebrations()

const tab = ref<Tab>((["mine", "discover", "badges"] as Tab[]).includes(route.query.tab as Tab) ? (route.query.tab as Tab) : "mine")
watch(tab, (t) => router.replace({ query: t === "mine" ? {} : { tab: t } }))

const data = ref<ChallengesOverview | null>(null)
const progress = ref<ProgressSummary | null>(null)
const error = ref("")

async function load() {
	error.value = ""
	try {
		;[data.value, progress.value] = await Promise.all([getChallenges(), getProgress()])
		if (!data.value.mine.some((p) => p.status === "Active") && tab.value === "mine" && !route.query.tab) tab.value = "discover"
	} catch (e) {
		error.value = (e as Error).message
	}
}
onMounted(() => {
	void load()
	void celebrations.refresh()
})

const active = computed(() => data.value?.mine.filter((p) => p.status === "Active") ?? [])
const finished = computed(() => data.value?.mine.filter((p) => p.status !== "Active").slice(0, 10) ?? [])
const earnedCount = computed(() => progress.value?.achievements.filter((a) => a.earned).length ?? 0)
const levelSpan = computed(() => (progress.value ? progress.value.next_level_at - progress.value.level_start : 1))

function percent(p: Participation): number {
	const needed = p.progress.needed || p.challenge_info.duration_days
	return Math.min(100, Math.round((100 * p.progress.done) / Math.max(needed, 1)))
}

const SHORT: Intl.DateTimeFormatOptions = { day: "numeric", month: "short" }

const STATUS_STYLE: Record<string, string> = {
	Completed: "bg-mint-50 text-mint-700 dark:bg-mint-500/15 dark:text-mint-400",
	Failed: "bg-ink-100 text-ink-600 dark:bg-night-800 dark:text-ink-300",
	Abandoned: "bg-ink-100 text-ink-500 dark:bg-night-800 dark:text-ink-400",
}
const STATUS_LABEL: Record<string, string> = { Completed: "Completed", Failed: "Ended", Abandoned: "Left" }

// ------------------------------------------------------------------ join
const joining = ref<Challenge | null>(null)
const joinMode = ref<"new" | "existing">("new")
const joinHabitName = ref("")
const joinHabit = ref("")
const joinBusy = ref(false)
const eligible = computed(() => (habits.habits ?? []).filter((h) => h.status === "Active" && h.habit_type !== "One-time"))

async function openJoin(c: Challenge) {
	joining.value = c
	joinMode.value = "new"
	joinHabitName.value = c.suggested_habit || c.title
	joinHabit.value = ""
	if (!habits.habits) void habits.loadHabits().catch(() => undefined)
}

async function confirmJoin() {
	if (!joining.value) return
	joinBusy.value = true
	try {
		const opts = joinMode.value === "existing" ? { habit: joinHabit.value } : { habit_name: joinHabitName.value.trim() }
		await joinChallenge(joining.value.name, opts)
		toast.success(`You're in! Day 1 of ${joining.value.duration_days} starts today.`)
		joining.value = null
		tab.value = "mine"
		void habits.loadToday(true)
		habits.habits = null
		await load()
		void celebrations.refresh() // joining can create a habit, which can earn a badge
	} catch (e) {
		toast.error((e as Error).message)
	} finally {
		joinBusy.value = false
	}
}

async function leave(p: Participation) {
	const ok = await confirm.ask({
		title: `Leave "${p.challenge_info.title}"?`,
		body: "Your habit and its check-ins stay. Only the challenge ends.",
		confirmLabel: "Leave challenge",
		danger: true,
	})
	if (!ok) return
	try {
		await leaveChallenge(p.name)
		await load()
	} catch (e) {
		toast.error((e as Error).message)
	}
}

// ------------------------------------------------------------------ create
const creating = ref(false)
const form = ref({ title: "", days: 14, description: "", icon: "target", color: "#FF9F43" })
const createBusy = ref(false)
const ICON_CHOICES = ["target", "flame", "trophy", "dumbbell", "book-open", "glass-water", "flower-2", "moon", "footprints", "pen-line", "wallet", "heart"]
const COLOR_CHOICES = ["#FF9F43", "#7657F6", "#26C281", "#4D8DFF", "#F56FA1", "#1FB5A8"]
const DAY_CHOICES = [7, 14, 21, 30, 60, 90]
const customXp = computed(() => Math.min(Math.max(form.value.days || 1, 1) * 10, 300))

async function submitCreate() {
	if (!form.value.title.trim()) return toast.error("Give your challenge a name.")
	createBusy.value = true
	try {
		await createChallenge({
			title: form.value.title.trim(),
			duration_days: form.value.days,
			description: form.value.description.trim() || undefined,
			icon: form.value.icon,
			color: form.value.color,
		})
		creating.value = false
		form.value = { title: "", days: 14, description: "", icon: "target", color: "#FF9F43" }
		await load()
		const mine = data.value?.discover.find((c) => c.is_mine && !c.joined)
		if (mine) void openJoin(mine)
	} catch (e) {
		toast.error((e as Error).message)
	} finally {
		createBusy.value = false
	}
}
</script>

<template>
	<div>
		<PageHeader title="Challenges" subtitle="Small habits, done for a set number of days">
			<template #actions>
				<AppButton variant="secondary" @click="creating = true"><Plus class="h-5 w-5" :stroke-width="2.6" /> Create</AppButton>
			</template>
		</PageHeader>

		<!-- level card -->
		<RouterLink
			v-if="progress"
			:to="{ query: { tab: 'badges' } }"
			class="mb-5 flex items-center gap-4 rounded-4xl bg-gradient-to-br from-grape-500 to-grape-700 p-5 text-white shadow-lift"
			@click="tab = 'badges'"
		>
			<span class="flex h-14 w-14 shrink-0 flex-col items-center justify-center rounded-2xl bg-white/15">
				<span class="text-[11px] font-bold uppercase tracking-wide opacity-80">Level</span>
				<span class="font-display text-[24px] font-extrabold leading-none">{{ progress.level }}</span>
			</span>
			<span class="min-w-0 flex-1">
				<span class="flex items-baseline justify-between gap-2 text-[14px] font-bold">
					<span>{{ progress.xp }} XP</span>
					<span class="opacity-80">{{ progress.next_level_at - progress.xp }} XP to level {{ progress.level + 1 }}</span>
				</span>
				<span
					class="mt-2 block h-2.5 overflow-hidden rounded-full bg-white/20"
					role="progressbar"
					:aria-valuenow="progress.xp - progress.level_start"
					aria-valuemin="0"
					:aria-valuemax="levelSpan"
					aria-label="Progress to the next level"
				>
					<span class="block h-full rounded-full bg-sun-400 transition-[width] duration-500" :style="{ width: `${progress.progress}%` }" />
				</span>
				<span class="mt-2 block text-[13px] opacity-85">{{ earnedCount }} of {{ progress.achievements.length }} badges earned</span>
			</span>
		</RouterLink>

		<SegmentedControl
			v-model="tab"
			class="mb-4 max-w-md"
			:options="[
				{ value: 'mine', label: active.length ? `Mine (${active.length})` : 'Mine' },
				{ value: 'discover', label: 'Discover' },
				{ value: 'badges', label: 'Badges' },
			]"
			label="Show"
		/>

		<EmptyState v-if="error" :icon="RefreshCw" title="Couldn't load challenges" :body="error"><AppButton @click="load">Try again</AppButton></EmptyState>

		<div v-else-if="!data" class="grid gap-3 sm:grid-cols-2"><SkeletonBlock v-for="i in 4" :key="i" class="h-36 rounded-4xl" /></div>

		<!-- mine -->
		<template v-else-if="tab === 'mine'">
			<div v-if="!active.length" class="rounded-4xl bg-white shadow-soft dark:bg-night-900">
				<EmptyState :icon="Flag" title="No challenge running" body="Pick a 7, 21 or 30-day challenge. Showing up most days is enough: one slip a week is forgiven.">
					<AppButton @click="tab = 'discover'">Find a challenge</AppButton>
				</EmptyState>
			</div>
			<ul class="grid gap-3 sm:grid-cols-2">
				<li v-for="p in active" :key="p.name" class="rounded-4xl bg-white p-5 shadow-soft dark:bg-night-900">
					<div class="flex items-start gap-4">
						<ProgressRing :value="percent(p)" :size="72" :stroke="9" :color="p.challenge_info.color" :label="`${percent(p)}% of the way`">
							<span class="font-display text-[18px] font-extrabold">{{ p.progress.done }}</span>
						</ProgressRing>
						<div class="min-w-0 flex-1">
							<p class="text-[12px] font-bold uppercase tracking-wide" :style="{ color: p.challenge_info.color }">Day {{ p.day }} of {{ p.challenge_info.duration_days }}</p>
							<h3 class="mt-0.5 text-[17px] font-extrabold leading-snug">{{ p.challenge_info.title }}</h3>
							<RouterLink v-if="p.habit_info" :to="{ name: 'habit', params: { name: p.habit } }" class="mt-1 flex items-center gap-1.5 text-[13px] font-semibold text-ink-500 hover:underline dark:text-ink-400">
								<HabitIcon :icon="p.habit_info.icon" :color="p.habit_info.color" size="sm" /> {{ p.habit_info.habit_name }}
							</RouterLink>
						</div>
					</div>
					<p class="mt-4 text-[14px] text-ink-600 dark:text-ink-300">
						<template v-if="p.progress.needed && p.progress.done >= p.progress.needed">Target reached. Finishing up!</template>
						<template v-else-if="p.progress.needed">
							{{ p.progress.done }} of {{ p.progress.needed }} days done.
							<span class="text-ink-500 dark:text-ink-400">{{ p.progress.remaining }} day{{ p.progress.remaining === 1 ? "" : "s" }} left to go.</span>
						</template>
					</p>
					<div class="mt-3 flex items-center justify-between">
						<span class="inline-flex items-center gap-1 text-[13px] font-bold text-sun-700 dark:text-sun-400"><Sparkles class="h-4 w-4" /> {{ p.challenge_info.xp_reward }} XP</span>
						<button type="button" class="rounded-lg px-2 py-1 text-[13px] font-semibold text-ink-500 hover:bg-ink-100 dark:text-ink-400 dark:hover:bg-night-800" @click="leave(p)">Leave</button>
					</div>
				</li>
			</ul>

			<section v-if="finished.length" class="mt-6">
				<h2 class="mb-2 px-1 text-[15px] font-extrabold">Past challenges</h2>
				<ul class="space-y-2">
					<li v-for="p in finished" :key="p.name" class="flex items-center gap-3 rounded-3xl bg-white p-3.5 shadow-soft dark:bg-night-900">
						<HabitIcon :icon="p.challenge_info.icon" :color="p.challenge_info.color" />
						<span class="min-w-0 flex-1">
							<span class="block truncate text-[15px] font-bold">{{ p.challenge_info.title }}</span>
							<span class="block text-[13px] text-ink-500 dark:text-ink-400">
								{{ p.days_completed }} days done<template v-if="p.completed_on">. Finished {{ formatDay(p.completed_on, SHORT) }}</template>
							</span>
						</span>
						<span class="rounded-full px-2.5 py-1 text-[12px] font-bold" :class="STATUS_STYLE[p.status]">{{ STATUS_LABEL[p.status] }}</span>
					</li>
				</ul>
			</section>
		</template>

		<!-- discover -->
		<ul v-else-if="tab === 'discover'" class="grid gap-3 sm:grid-cols-2">
			<li v-for="c in data.discover" :key="c.name" class="flex flex-col rounded-4xl bg-white p-5 shadow-soft dark:bg-night-900">
				<div class="flex items-start gap-3">
					<HabitIcon :icon="c.icon" :color="c.color" size="lg" />
					<div class="min-w-0 flex-1">
						<p class="text-[12px] font-bold uppercase tracking-wide" :style="{ color: c.color }">{{ c.duration_days }} days<template v-if="c.is_mine"> · yours</template></p>
						<h3 class="text-[17px] font-extrabold leading-snug">{{ c.title }}</h3>
					</div>
				</div>
				<p v-if="c.description" class="mt-3 flex-1 text-[14px] text-ink-600 dark:text-ink-300">{{ c.description }}</p>
				<div class="mt-4 flex items-center justify-between gap-3">
					<span class="inline-flex items-center gap-1 text-[13px] font-bold text-sun-700 dark:text-sun-400"><Sparkles class="h-4 w-4" /> {{ c.xp_reward }} XP</span>
					<span v-if="c.joined" class="inline-flex items-center gap-1 rounded-full bg-mint-50 px-3 py-1.5 text-[13px] font-bold text-mint-700 dark:bg-mint-500/15 dark:text-mint-400">
						<CalendarCheck class="h-4 w-4" /> Joined
					</span>
					<AppButton v-else @click="openJoin(c)">Join</AppButton>
				</div>
			</li>
		</ul>

		<!-- badges -->
		<ul v-else-if="progress" class="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
			<li
				v-for="a in progress.achievements"
				:key="a.name"
				class="flex flex-col items-center rounded-4xl bg-white p-4 text-center shadow-soft dark:bg-night-900"
				:class="a.earned ? '' : 'opacity-70'"
			>
				<HabitIcon v-if="a.earned" :icon="a.icon" :color="a.color" size="lg" class="shadow-lift" />
				<span v-else class="flex h-16 w-16 items-center justify-center rounded-3xl bg-ink-100 text-ink-400 dark:bg-night-800 dark:text-night-600">
					<Lock class="h-7 w-7" />
				</span>
				<span class="mt-3 text-[15px] font-extrabold leading-tight">{{ a.title }}</span>
				<span class="mt-1 text-[12px] leading-snug text-ink-500 dark:text-ink-400">{{ a.description }}</span>
				<span v-if="a.earned && a.achieved_on" class="mt-2 text-[12px] font-bold" :style="{ color: a.color }">{{ formatDay(a.achieved_on.slice(0, 10), SHORT) }}</span>
				<span v-else class="mt-2 inline-flex items-center gap-1 text-[12px] font-bold text-sun-700 dark:text-sun-400"><Trophy class="h-3.5 w-3.5" /> {{ a.xp_reward }} XP</span>
			</li>
		</ul>

		<!-- join sheet -->
		<BottomSheet :open="!!joining" :title="joining ? `Join ${joining.title}` : ''" @close="joining = null">
			<template v-if="joining">
				<p class="text-[14px] text-ink-600 dark:text-ink-300">
					Do the habit on most of the next {{ joining.duration_days }} days. One slip a week is forgiven.
				</p>
				<SegmentedControl
					v-model="joinMode"
					class="mt-4"
					:options="[{ value: 'new', label: 'New habit' }, { value: 'existing', label: 'One I have' }]"
					label="Which habit"
				/>
				<TextField v-if="joinMode === 'new'" id="join-habit" v-model="joinHabitName" class="mt-4" label="Habit name" maxlength="140" />
				<div v-else class="mt-4">
					<label for="join-existing" class="field-label">Your habit</label>
					<select id="join-existing" v-model="joinHabit" class="field">
						<option value="" disabled>Choose a habit</option>
						<option v-for="h in eligible" :key="h.name" :value="h.name">{{ h.habit_name }}</option>
					</select>
					<p v-if="habits.habits && !eligible.length" class="mt-1.5 text-[13px] text-ink-500 dark:text-ink-400">You have no active daily habits yet. Start a new one instead.</p>
				</div>
				<AppButton
					class="mt-6"
					size="lg"
					block
					:loading="joinBusy"
					:disabled="joinMode === 'new' ? !joinHabitName.trim() : !joinHabit"
					@click="confirmJoin"
				>
					Start today
				</AppButton>
			</template>
		</BottomSheet>

		<!-- create sheet -->
		<BottomSheet :open="creating" title="Create a challenge" @close="creating = false">
			<form class="space-y-4" @submit.prevent="submitCreate">
				<TextField id="ch-title" v-model="form.title" label="Name" placeholder="e.g. 14 days of stretching" maxlength="140" required />
				<div>
					<span class="field-label">How many days</span>
					<div class="flex flex-wrap gap-2">
						<button
							v-for="d in DAY_CHOICES"
							:key="d"
							type="button"
							class="h-10 min-w-[3.25rem] rounded-xl px-3 text-[14px] font-bold transition"
							:class="form.days === d ? 'bg-grape-500 text-white' : 'bg-ink-100 text-ink-700 hover:bg-ink-200 dark:bg-night-800 dark:text-ink-200'"
							:aria-pressed="form.days === d"
							@click="form.days = d"
						>
							{{ d }}
						</button>
					</div>
				</div>
				<div>
					<label for="ch-desc" class="field-label">Description <span class="font-normal text-ink-400">(optional)</span></label>
					<textarea id="ch-desc" v-model="form.description" class="field min-h-[4.5rem] py-2.5" maxlength="1000" />
				</div>
				<div>
					<span class="field-label">Icon and colour</span>
					<div class="flex flex-wrap gap-2">
						<button
							v-for="i in ICON_CHOICES"
							:key="i"
							type="button"
							class="rounded-2xl p-0.5 ring-2 transition"
							:class="form.icon === i ? 'ring-grape-500' : 'ring-transparent'"
							:aria-label="i.replace(/-/g, ' ')"
							:aria-pressed="form.icon === i"
							@click="form.icon = i"
						>
							<HabitIcon :icon="i" :color="form.color" />
						</button>
					</div>
					<div class="mt-3 flex gap-2">
						<button
							v-for="c in COLOR_CHOICES"
							:key="c"
							type="button"
							class="h-9 w-9 rounded-full ring-2 ring-offset-2 transition dark:ring-offset-night-900"
							:class="form.color === c ? 'ring-ink-900 dark:ring-white' : 'ring-transparent'"
							:style="{ background: c }"
							:aria-label="`Colour ${c}`"
							:aria-pressed="form.color === c"
							@click="form.color = c"
						/>
					</div>
				</div>
				<p class="rounded-2xl bg-sun-50 px-4 py-3 text-[14px] font-semibold text-sun-700 dark:bg-sun-500/10 dark:text-sun-400">
					Finishing it earns {{ customXp }} XP.
				</p>
				<AppButton type="submit" size="lg" block :loading="createBusy">Create and join</AppButton>
			</form>
		</BottomSheet>
	</div>
</template>
