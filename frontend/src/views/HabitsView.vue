<script setup lang="ts">
import { Archive, Flame, Layers, PauseCircle, Plus, Sprout } from "lucide-vue-next"
import { onMounted, ref, watch } from "vue"

import type { Habit } from "@/api/types"
import HabitIcon from "@/components/habits/HabitIcon.vue"
import AppButton from "@/components/ui/AppButton.vue"
import EmptyState from "@/components/ui/EmptyState.vue"
import PageHeader from "@/components/ui/PageHeader.vue"
import SegmentedControl from "@/components/ui/SegmentedControl.vue"
import SkeletonBlock from "@/components/ui/SkeletonBlock.vue"
import { describeSchedule, describeTarget } from "@/lib/describe"
import { useHabits } from "@/stores/habits"

const store = useHabits()
const tab = ref<"active" | "archived">("active")
const archived = ref<Habit[] | null>(null)
const error = ref("")

async function load() {
	error.value = ""
	try {
		if (tab.value === "active") await store.loadHabits()
		else archived.value = await store.loadHabits("archived")
	} catch (e) {
		error.value = (e as Error).message
	}
}
onMounted(load)
watch(tab, load)
</script>

<template>
	<div>
		<PageHeader title="My Habits" :subtitle="store.habits ? `${store.habits.length} habit${store.habits.length === 1 ? '' : 's'}` : undefined">
			<template #actions>
				<AppButton variant="secondary" @click="$router.push({ name: 'routines' })"><Layers class="h-5 w-5" /> Routines</AppButton>
				<AppButton @click="$router.push({ name: 'habit-new' })"><Plus class="h-5 w-5" :stroke-width="2.6" /> New</AppButton>
			</template>
		</PageHeader>

		<SegmentedControl
			v-model="tab"
			class="mb-4 max-w-xs"
			:options="[{ value: 'active', label: 'Current' }, { value: 'archived', label: 'Archived' }]"
			label="Which habits"
		/>

		<EmptyState v-if="error" title="Couldn't load your habits" :body="error"><AppButton @click="load">Try again</AppButton></EmptyState>

		<template v-else-if="tab === 'active'">
			<div v-if="!store.habits" class="space-y-2.5"><SkeletonBlock v-for="i in 4" :key="i" class="h-20 rounded-3xl" /></div>
			<div v-else-if="!store.habits.length" class="rounded-4xl bg-white shadow-soft dark:bg-night-900">
				<EmptyState :icon="Sprout" title="No habits yet" body="Habits are built one small step at a time. Add the first one.">
					<AppButton size="lg" @click="$router.push({ name: 'habit-new' })"><Plus class="h-5 w-5" /> Add a habit</AppButton>
				</EmptyState>
			</div>
			<ul v-else class="grid gap-2.5 sm:grid-cols-2">
				<li v-for="h in store.habits" :key="h.name">
					<RouterLink :to="{ name: 'habit', params: { name: h.name } }" class="flex items-center gap-3 rounded-3xl bg-white p-3.5 shadow-soft transition hover:shadow-md dark:bg-night-900">
						<HabitIcon :icon="h.icon" :color="h.color" />
						<span class="min-w-0 flex-1">
							<span class="block truncate text-[16px] font-bold">{{ h.habit_name }}</span>
							<span class="block truncate text-[13px] text-ink-500 dark:text-ink-400">{{ describeSchedule(h) }}. {{ describeTarget(h) }}</span>
						</span>
						<span v-if="h.status === 'Paused'" class="inline-flex items-center gap-1 rounded-full bg-ink-100 px-2 py-1 text-[12px] font-bold text-ink-600 dark:bg-night-800 dark:text-ink-300">
							<PauseCircle class="h-3.5 w-3.5" /> Paused
						</span>
						<span v-else-if="h.status === 'Completed'" class="rounded-full bg-mint-50 px-2 py-1 text-[12px] font-bold text-mint-700 dark:bg-mint-500/15 dark:text-mint-400">Done</span>
						<span v-else class="inline-flex items-center gap-1 font-display text-[18px] font-extrabold" :class="h.current_streak ? 'text-tangerine-600 dark:text-tangerine-400' : 'text-ink-300 dark:text-night-600'" :aria-label="`${h.current_streak}-day streak`">
							<Flame class="h-5 w-5" :stroke-width="2.5" />{{ h.current_streak }}
						</span>
					</RouterLink>
				</li>
			</ul>
		</template>

		<template v-else>
			<div v-if="!archived" class="space-y-2.5"><SkeletonBlock v-for="i in 2" :key="i" class="h-20 rounded-3xl" /></div>
			<EmptyState v-else-if="!archived.length" :icon="Archive" title="Nothing archived" body="Archive a habit to put it away without losing its history." />
			<ul v-else class="grid gap-2.5 sm:grid-cols-2">
				<li v-for="h in archived" :key="h.name">
					<RouterLink :to="{ name: 'habit', params: { name: h.name } }" class="flex items-center gap-3 rounded-3xl bg-white p-3.5 opacity-80 shadow-soft dark:bg-night-900">
						<HabitIcon :icon="h.icon" :color="h.color" />
						<span class="min-w-0 flex-1">
							<span class="block truncate text-[16px] font-bold">{{ h.habit_name }}</span>
							<span class="block text-[13px] text-ink-500 dark:text-ink-400">Best streak {{ h.longest_streak }} days. {{ h.total_completions }} check-ins.</span>
						</span>
					</RouterLink>
				</li>
			</ul>
		</template>
	</div>
</template>
