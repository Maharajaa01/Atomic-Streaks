<script setup lang="ts">
import { ArrowDownRight, ArrowUpRight, BarChart3, Flame, Minus, Pencil, Sprout, Sunrise, Trophy } from "lucide-vue-next"
import { computed, onMounted, ref, watch } from "vue"

import { getInsights } from "@/api/insights"
import type { Insights } from "@/api/types"
import CalendarHeatmap from "@/components/charts/CalendarHeatmap.vue"
import EChart from "@/components/charts/EChart.vue"
import HabitIcon from "@/components/habits/HabitIcon.vue"
import AppButton from "@/components/ui/AppButton.vue"
import EmptyState from "@/components/ui/EmptyState.vue"
import PageHeader from "@/components/ui/PageHeader.vue"
import SegmentedControl from "@/components/ui/SegmentedControl.vue"
import SkeletonBlock from "@/components/ui/SkeletonBlock.vue"
import { formatDay, parseDay } from "@/lib/dates"
import { HEAT_DARK, HEAT_LIGHT, heatColor } from "@/lib/heat"
import { isDark } from "@/lib/theme"
import { useSession } from "@/stores/session"

const session = useSession()
const period = ref<"7" | "30" | "90">("30")
const data = ref<Insights | null>(null)
const error = ref("")
const loading = ref(false)

async function load() {
	loading.value = true
	error.value = ""
	try {
		data.value = await getInsights(Number(period.value) as 7 | 30 | 90)
	} catch (e) {
		error.value = (e as Error).message
	} finally {
		loading.value = false
	}
}
onMounted(load)
watch(period, load)

const pct = (v: number | null | undefined) => (v === null || v === undefined ? "–" : `${v}%`)
const delta = computed(() => {
	const d = data.value
	if (!d || d.rate === null || d.previous_rate === null) return null
	return d.rate - d.previous_rate
})
const empty = computed(() => !!data.value && !data.value.habits.length)

// -------------------------------------------------------------- chart options
const INK = { light: { axis: "#9AA1B5", grid: "#EEF0F6", text: "#363D50", tipBg: "#141826" }, dark: { axis: "#6B7389", grid: "#1C2537", text: "#C8CDDB", tipBg: "#FFFFFF" } }

const trendOption = computed(() => {
	const d = data.value
	return (dark: boolean) => {
		const c = dark ? INK.dark : INK.light
		const line = dark ? "#9479F9" : "#7657F6"
		return {
			animationDuration: 500,
			grid: { left: 36, right: 12, top: 12, bottom: 28 },
			tooltip: {
				trigger: "axis",
				axisPointer: { type: "line", lineStyle: { color: c.axis, width: 1 } },
				backgroundColor: c.tipBg,
				borderWidth: 0,
				textStyle: { color: dark ? "#141826" : "#FFFFFF", fontFamily: "Plus Jakarta Sans Variable", fontSize: 13 },
				formatter: (ps: { dataIndex: number }[]) => {
					const p = d?.trend[ps[0]!.dataIndex]
					if (!p) return ""
					const when = formatDay(p.date, { weekday: "short", day: "numeric", month: "short" })
					return p.scheduled ? `<b>${when}</b><br/>${p.rate}% done (${p.completed} of ${p.scheduled})` : `<b>${when}</b><br/>Nothing scheduled`
				},
			},
			xAxis: {
				type: "category",
				data: d?.trend.map((p) => parseDay(p.date).toLocaleDateString(undefined, { day: "numeric", month: "short" })) ?? [],
				axisLine: { lineStyle: { color: c.grid } },
				axisTick: { show: false },
				axisLabel: { color: c.axis, fontSize: 11, hideOverlap: true },
			},
			yAxis: {
				type: "value",
				min: 0,
				max: 100,
				interval: 50,
				axisLabel: { color: c.axis, fontSize: 11, formatter: "{value}%" },
				splitLine: { lineStyle: { color: c.grid } },
			},
			series: [
				{
					type: "line",
					data: d?.trend.map((p) => p.rate) ?? [],
					connectNulls: false,
					showSymbol: (d?.trend.length ?? 0) <= 7,
					symbolSize: 8,
					lineStyle: { width: 2, color: line },
					itemStyle: { color: line, borderColor: dark ? "#111827" : "#FFFFFF", borderWidth: 2 },
					areaStyle: {
						color: { type: "linear", x: 0, y: 0, x2: 0, y2: 1, colorStops: [{ offset: 0, color: dark ? "rgba(148,121,249,.28)" : "rgba(118,87,246,.18)" }, { offset: 1, color: "rgba(118,87,246,0)" }] },
					},
				},
			],
		}
	}
})

const weekdayOption = computed(() => {
	const d = data.value
	return (dark: boolean) => {
		const c = dark ? INK.dark : INK.light
		const best = Math.max(...(d?.weekdays.map((w) => w.rate ?? -1) ?? [-1]))
		return {
			animationDuration: 500,
			grid: { left: 36, right: 8, top: 22, bottom: 24 },
			tooltip: {
				trigger: "item",
				backgroundColor: c.tipBg,
				borderWidth: 0,
				textStyle: { color: dark ? "#141826" : "#FFFFFF", fontSize: 13 },
				formatter: (p: { dataIndex: number }) => {
					const w = d?.weekdays[p.dataIndex]
					return w?.scheduled ? `<b>${w.weekday}</b>: ${w.rate}% done` : `<b>${w?.weekday}</b>: nothing scheduled`
				},
			},
			xAxis: { type: "category", data: d?.weekdays.map((w) => w.weekday) ?? [], axisTick: { show: false }, axisLine: { lineStyle: { color: c.grid } }, axisLabel: { color: c.axis, fontSize: 11 } },
			yAxis: { type: "value", min: 0, max: 100, interval: 50, axisLabel: { color: c.axis, fontSize: 11, formatter: "{value}%" }, splitLine: { lineStyle: { color: c.grid } } },
			series: [
				{
					type: "bar",
					barMaxWidth: 26,
					data: (d?.weekdays ?? []).map((w) => ({
						value: w.rate ?? 0,
						itemStyle: { color: w.rate === best && best > 0 ? (dark ? "#9479F9" : "#6140E8") : dark ? "#41289E" : "#CFC3FF", borderRadius: [4, 4, 0, 0] },
						label: w.rate === best && best > 0 ? { show: true, position: "top", formatter: `${w.rate}%`, color: c.text, fontWeight: 700, fontSize: 12 } : undefined,
					})),
				},
			],
		}
	}
})

const heatCells = computed(() =>
	(data.value?.heatmap ?? []).map((h) => ({
		date: h.date,
		color: heatColor(h.percent, isDark.value),
		label: `${formatDay(h.date, { weekday: "short", day: "numeric", month: "short", year: "numeric" })}: ${h.scheduled ? `${h.completed} of ${h.scheduled} done` : "nothing scheduled"}`,
	})),
)
const startsOn = computed(() => session.boot?.profile?.week_starts_on ?? "Monday")
</script>

<template>
	<div>
		<PageHeader title="Insights" />
		<SegmentedControl
			v-model="period"
			class="-mt-1 mb-5 max-w-sm"
			:options="[{ value: '7', label: '7 days' }, { value: '30', label: '30 days' }, { value: '90', label: '90 days' }]"
			label="Period"
		/>

		<EmptyState v-if="error" title="Couldn't load your insights" :body="error"><AppButton @click="load">Try again</AppButton></EmptyState>

		<div v-else-if="!data" class="space-y-4"><SkeletonBlock class="h-40 rounded-4xl" /><SkeletonBlock class="h-64 rounded-4xl" /><SkeletonBlock class="h-48 rounded-4xl" /></div>

		<div v-else-if="empty" class="rounded-4xl bg-white shadow-soft dark:bg-night-900">
			<EmptyState :icon="BarChart3" title="Insights grow with your check-ins" body="Add a habit and check in for a few days. Your trends, best days and streaks will show up here.">
				<AppButton size="lg" @click="$router.push({ name: 'habit-new' })">Add a habit</AppButton>
			</EmptyState>
		</div>

		<div v-else class="space-y-5" :class="loading && 'opacity-70 transition-opacity'">
			<!-- headline -->
			<section class="grid grid-cols-2 gap-3 sm:grid-cols-[1.3fr_1fr_1fr] lg:grid-cols-[1.4fr_1fr_1fr_1fr]">
				<div class="col-span-2 rounded-4xl bg-gradient-to-br from-[#8B6CFF] via-grape-500 to-sky-500 p-5 text-white shadow-lift sm:col-span-1 sm:row-span-2 lg:row-span-1">
					<p class="text-[14px] font-semibold text-white/80">Completion, last {{ data.days }} days</p>
					<p class="mt-1 font-display text-[56px] font-extrabold leading-none">{{ pct(data.rate) }}</p>
					<p class="mt-2 text-[14px] text-white/85">{{ data.completed }} of {{ data.scheduled }} scheduled check-ins</p>
					<p v-if="delta !== null" class="mt-3 inline-flex items-center gap-1 rounded-full bg-white/20 px-2.5 py-1 text-[13px] font-bold">
						<component :is="delta > 0 ? ArrowUpRight : delta < 0 ? ArrowDownRight : Minus" class="h-4 w-4" />
						{{ delta === 0 ? "Same as" : `${Math.abs(delta)} points ${delta > 0 ? "up on" : "down on"}` }} the {{ data.days }} days before
					</p>
				</div>
				<div class="rounded-4xl bg-white p-4 shadow-soft dark:bg-night-900">
					<p class="text-[13px] font-semibold text-ink-500 dark:text-ink-400">This week</p>
					<p class="mt-1 font-display text-[32px] font-extrabold leading-none">{{ pct(data.week_rate) }}</p>
					<p class="mt-2 text-[13px] text-ink-500 dark:text-ink-400">This month: {{ pct(data.month_rate) }}</p>
				</div>
				<div class="rounded-4xl bg-white p-4 shadow-soft dark:bg-night-900">
					<p class="flex items-center gap-1 text-[13px] font-semibold text-ink-500 dark:text-ink-400"><Flame class="h-4 w-4 text-tangerine-500" /> Streak</p>
					<p class="mt-1 font-display text-[32px] font-extrabold leading-none">{{ data.streak.current }}<span class="text-[16px] text-ink-400"> days</span></p>
					<p class="mt-2 text-[13px] text-ink-500 dark:text-ink-400">Best ever: {{ data.streak.longest }} days</p>
				</div>
				<div class="col-span-2 rounded-4xl bg-white p-4 shadow-soft dark:bg-night-900 lg:col-span-1">
					<p class="flex items-center gap-1 text-[13px] font-semibold text-ink-500 dark:text-ink-400"><Sunrise class="h-4 w-4 text-sun-600" /> Bounce-backs</p>
					<p class="mt-1 font-display text-[32px] font-extrabold leading-none">{{ data.comebacks }}</p>
					<p class="mt-2 text-[13px] text-ink-500 dark:text-ink-400">Times you missed a day and came straight back.</p>
				</div>
			</section>

			<!-- trend -->
			<section class="rounded-4xl bg-white p-5 shadow-soft dark:bg-night-900" aria-labelledby="trend-title">
				<h2 id="trend-title" class="text-[18px] font-extrabold">Daily completion</h2>
				<p class="text-[13px] text-ink-500 dark:text-ink-400">Share of scheduled habits done each day. Gaps are days with nothing scheduled.</p>
				<EChart class="mt-3" :option="trendOption" :height="220" :label="`Line chart of daily completion over the last ${data.days} days`" />
				<details class="mt-2 text-[13px]">
					<summary class="cursor-pointer font-semibold text-grape-600 dark:text-grape-300">Show as a table</summary>
					<table class="mt-2 w-full text-left">
						<thead><tr class="text-ink-500"><th class="py-1 font-semibold">Day</th><th class="font-semibold">Done</th><th class="font-semibold">Rate</th></tr></thead>
						<tbody>
							<tr v-for="p in data.trend" :key="p.date" class="border-t border-ink-100 dark:border-night-800">
								<td class="py-1">{{ formatDay(p.date, { weekday: "short", day: "numeric", month: "short" }) }}</td>
								<td>{{ p.scheduled ? `${p.completed} of ${p.scheduled}` : "Nothing scheduled" }}</td>
								<td>{{ pct(p.rate) }}</td>
							</tr>
						</tbody>
					</table>
				</details>
			</section>

			<div class="grid gap-5 lg:grid-cols-2">
				<section class="rounded-4xl bg-white p-5 shadow-soft dark:bg-night-900" aria-labelledby="weekday-title">
					<h2 id="weekday-title" class="text-[18px] font-extrabold">Your strongest days</h2>
					<p class="text-[13px] text-ink-500 dark:text-ink-400">Completion by day of the week.</p>
					<EChart class="mt-2" :option="weekdayOption" :height="190" label="Bar chart of completion by weekday" />
					<p class="sr-only">{{ data.weekdays.map((w) => `${w.weekday}: ${pct(w.rate)}`).join(", ") }}</p>
				</section>

				<section class="rounded-4xl bg-white p-5 shadow-soft dark:bg-night-900" aria-labelledby="cat-title">
					<h2 id="cat-title" class="text-[18px] font-extrabold">By category</h2>
					<p class="text-[13px] text-ink-500 dark:text-ink-400">Completion for each kind of habit.</p>
					<ul class="mt-4 space-y-3">
						<li v-for="c in data.categories" :key="c.label">
							<div class="mb-1 flex items-center justify-between text-[14px]">
								<span class="inline-flex items-center gap-2 font-bold"><span class="h-2.5 w-2.5 rounded-full" :style="{ background: c.color }" />{{ c.label }}</span>
								<span class="font-display font-extrabold">{{ pct(c.rate) }}</span>
							</div>
							<div class="h-2.5 overflow-hidden rounded-full bg-ink-100 dark:bg-night-800" role="img" :aria-label="`${c.label}: ${pct(c.rate)}, ${c.completed} of ${c.scheduled}`">
								<div class="h-full rounded-full bg-grape-500 transition-[width] duration-500 dark:bg-grape-400" :style="{ width: `${c.rate ?? 0}%` }" />
							</div>
						</li>
						<li v-if="!data.categories.length" class="text-[14px] text-ink-500">Nothing scheduled in this period yet.</li>
					</ul>
				</section>
			</div>

			<div class="grid gap-5 lg:grid-cols-3">
				<section class="rounded-4xl bg-white p-5 shadow-soft dark:bg-night-900" aria-labelledby="best-title">
					<h2 id="best-title" class="flex items-center gap-2 text-[18px] font-extrabold"><Trophy class="h-5 w-5 text-tangerine-500" /> Going great</h2>
					<ol class="mt-3 space-y-2">
						<li v-for="h in data.best" :key="h.name">
							<RouterLink :to="{ name: 'habit', params: { name: h.name } }" class="flex items-center gap-3 rounded-2xl p-1.5 hover:bg-ink-50 dark:hover:bg-night-850">
								<HabitIcon :icon="h.icon" :color="h.color" size="sm" />
								<span class="min-w-0 flex-1 truncate text-[14px] font-bold">{{ h.habit_name }}</span>
								<span class="font-display text-[15px] font-extrabold">{{ pct(h.rate) }}</span>
							</RouterLink>
						</li>
						<li v-if="!data.best.length" class="text-[14px] text-ink-500">Check in for a few more days to see your top habits.</li>
					</ol>
				</section>

				<section class="rounded-4xl bg-white p-5 shadow-soft dark:bg-night-900" aria-labelledby="struggle-title">
					<h2 id="struggle-title" class="flex items-center gap-2 text-[18px] font-extrabold"><Sprout class="h-5 w-5 text-mint-600" /> Make these easier</h2>
					<ul class="mt-3 space-y-2">
						<li v-for="h in data.struggling" :key="h.name" class="flex items-center gap-3 rounded-2xl p-1.5">
							<HabitIcon :icon="h.icon" :color="h.color" size="sm" />
							<span class="min-w-0 flex-1">
								<span class="block truncate text-[14px] font-bold">{{ h.habit_name }}</span>
								<span class="block text-[12px] text-ink-500 dark:text-ink-400">Missed {{ h.missed }} time{{ h.missed === 1 ? "" : "s" }}. Try a 2-minute version.</span>
							</span>
							<RouterLink :to="{ name: 'habit-edit', params: { name: h.name } }" class="flex h-9 w-9 items-center justify-center rounded-xl text-ink-500 hover:bg-ink-100 dark:hover:bg-night-800" :aria-label="`Make ${h.habit_name} smaller`">
								<Pencil class="h-4 w-4" />
							</RouterLink>
						</li>
						<li v-if="!data.struggling.length" class="text-[14px] text-ink-500">No misses in this period. Lovely work.</li>
					</ul>
				</section>

				<section class="rounded-4xl bg-white p-5 shadow-soft dark:bg-night-900" aria-labelledby="streaks-title">
					<h2 id="streaks-title" class="flex items-center gap-2 text-[18px] font-extrabold"><Flame class="h-5 w-5 text-tangerine-500" /> Longest streaks</h2>
					<ol class="mt-3 space-y-2">
						<li v-for="h in data.longest_streaks.filter((x) => x.longest_streak > 0)" :key="h.name" class="flex items-center gap-3 rounded-2xl p-1.5">
							<HabitIcon :icon="h.icon" :color="h.color" size="sm" />
							<span class="min-w-0 flex-1 truncate text-[14px] font-bold">{{ h.habit_name }}</span>
							<span class="font-display text-[15px] font-extrabold">{{ h.longest_streak }} <span class="text-[12px] font-semibold text-ink-400">days</span></span>
						</li>
						<li v-if="!data.longest_streaks.some((x) => x.longest_streak > 0)" class="text-[14px] text-ink-500">Your first streak starts with one check-in.</li>
					</ol>
				</section>
			</div>

			<section class="rounded-4xl bg-white p-5 shadow-soft dark:bg-night-900" aria-labelledby="year-title">
				<h2 id="year-title" class="text-[18px] font-extrabold">Your year of check-ins</h2>
				<p class="mb-3 text-[13px] text-ink-500 dark:text-ink-400">Darker days had more of their habits done.</p>
				<CalendarHeatmap :cells="heatCells" :starts-on="startsOn">
					<template #legend>
						<div class="mt-3 flex items-center gap-1.5 text-[11px] font-semibold text-ink-500 dark:text-ink-400">
							<span class="mr-2 inline-flex items-center gap-1"><span class="h-3 w-3 rounded-[3px]" :style="{ background: heatColor(null, isDark) }" /> Nothing scheduled</span>
							None
							<span v-for="c in isDark ? HEAT_DARK : HEAT_LIGHT" :key="c" class="h-3 w-3 rounded-[3px]" :style="{ background: c }" />
							All done
						</div>
					</template>
				</CalendarHeatmap>
			</section>
		</div>
	</div>
</template>
