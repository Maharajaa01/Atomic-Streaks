<script setup lang="ts">
import { Flame, Sparkles } from "lucide-vue-next"
import { computed } from "vue"

import type { TodayView } from "@/api/types"

import ProgressRing from "../ui/ProgressRing.vue"

const props = defineProps<{ view: TodayView }>()
const s = computed(() => props.view.summary)

const message = computed(() => {
	if (!s.value.total) return "Nothing is due today. Enjoy the rest day."
	if (s.value.completed === s.value.total) return "Perfect day. Every habit done!"
	if (!s.value.completed) return "One small step gets the day going."
	return s.value.remaining === 1 ? "Just one more to go." : `Keep going. ${s.value.remaining} to go.`
})
</script>

<template>
	<section
		class="relative overflow-hidden rounded-4xl bg-gradient-to-br from-[#8B6CFF] via-grape-500 to-sky-500 p-5 text-white shadow-lift sm:p-6"
		aria-labelledby="today-progress"
	>
		<div aria-hidden="true" class="pointer-events-none absolute -right-16 -top-20 h-56 w-56 rounded-full bg-sun-500/25 blur-3xl" />
		<div class="relative flex items-center gap-5">
			<ProgressRing :value="s.percent" :size="112" :stroke="12" color="#FFFFFF" track="rgba(255,255,255,.22)" :label="`${s.percent}% of today's habits done`">
				<span class="font-display text-[30px] font-extrabold leading-none">{{ s.percent }}<span class="text-[16px]">%</span></span>
			</ProgressRing>
			<div class="min-w-0">
				<h2 id="today-progress" class="text-[22px] font-extrabold leading-tight">
					{{ s.completed }} of {{ s.total }} done
				</h2>
				<p class="mt-1 text-[14px] leading-snug text-white/85">{{ message }}</p>
				<div class="mt-3 flex flex-wrap gap-2">
					<span class="inline-flex items-center gap-1 rounded-full bg-white/20 px-2.5 py-1 text-[13px] font-bold backdrop-blur">
						<Flame class="h-4 w-4 text-sun-400" :stroke-width="2.6" />
						{{ view.streak.current }}-day streak
					</span>
					<span class="inline-flex items-center gap-1 rounded-full bg-white/20 px-2.5 py-1 text-[13px] font-bold backdrop-blur">
						<Sparkles class="h-4 w-4 text-sun-400" :stroke-width="2.6" /> Level {{ view.level }}
					</span>
				</div>
			</div>
		</div>
		<dl class="relative mt-5 grid grid-cols-3 gap-2 rounded-3xl bg-white/15 p-3 text-center backdrop-blur">
			<div>
				<dt class="text-[12px] font-semibold text-white/75">Active habits</dt>
				<dd class="font-display text-2xl font-extrabold">{{ s.active_habits }}</dd>
			</div>
			<div>
				<dt class="text-[12px] font-semibold text-white/75">Done today</dt>
				<dd class="font-display text-2xl font-extrabold">{{ s.completed }}</dd>
			</div>
			<div>
				<dt class="text-[12px] font-semibold text-white/75">Left today</dt>
				<dd class="font-display text-2xl font-extrabold">{{ s.remaining }}</dd>
			</div>
		</dl>
	</section>
</template>
