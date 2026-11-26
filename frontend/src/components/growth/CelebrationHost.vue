<script setup lang="ts">
/** One celebration at a time: a new badge, a finished challenge or a level-up. */
import { Sparkles } from "lucide-vue-next"
import { computed, nextTick, ref, watch } from "vue"

import AppButton from "@/components/ui/AppButton.vue"
import { iconFor } from "@/lib/icons"
import { useCelebrations } from "@/stores/celebrations"

const store = useCelebrations()
const item = computed(() => store.current)
const button = ref<InstanceType<typeof AppButton> | null>(null)

const KICKER = { achievement: "New badge", challenge: "You did it", level: "Level up" } as const

// confetti: fixed positions so it looks the same every time (and nothing random in tests)
const CONFETTI = Array.from({ length: 18 }, (_, i) => {
	const angle = (i / 18) * Math.PI * 2
	const dist = 90 + (i % 3) * 28
	return {
		"--bx": `${Math.round(Math.cos(angle) * dist)}px`,
		"--by": `${Math.round(Math.sin(angle) * dist)}px`,
		"animationDelay": `${(i % 4) * 60}ms`,
		"background": ["#7657F6", "#FF9F43", "#26C281", "#F56FA1", "#4D8DFF", "#FFD166"][i % 6],
	}
})

function onKey(e: KeyboardEvent) {
	if (e.key === "Escape" || e.key === "Enter") store.dismiss()
}

watch(
	() => item.value?.key,
	async (key) => {
		if (key) {
			document.addEventListener("keydown", onKey)
			await nextTick()
			;(button.value?.$el as HTMLElement | undefined)?.focus()
		} else {
			document.removeEventListener("keydown", onKey)
		}
	},
)
</script>

<template>
	<Teleport to="body">
		<Transition enter-active-class="transition-opacity duration-200" enter-from-class="opacity-0" leave-active-class="transition-opacity duration-150" leave-to-class="opacity-0">
			<div v-if="item" class="fixed inset-0 z-[90] flex items-center justify-center bg-ink-900/60 p-6 backdrop-blur-sm" @click.self="store.dismiss()">
				<div
					:key="item.key"
					role="alertdialog"
					aria-modal="true"
					:aria-label="`${KICKER[item.kind]}: ${item.title}`"
					class="relative w-full max-w-sm animate-fade-up rounded-4xl bg-white px-6 pb-6 pt-10 text-center shadow-sheet dark:bg-night-900"
				>
					<div class="relative mx-auto h-28 w-28">
						<span
							v-for="(style, i) in CONFETTI"
							:key="i"
							class="absolute left-1/2 top-1/2 -ml-1.5 -mt-1.5 h-3 w-3 animate-burst rounded-sm motion-reduce:hidden"
							:style="style"
							aria-hidden="true"
						/>
						<span
							class="relative flex h-28 w-28 animate-pop items-center justify-center rounded-[2.2rem] text-white shadow-lift"
							:style="{ background: `linear-gradient(145deg, ${item.color}, ${item.color}cc)` }"
						>
							<component :is="iconFor(item.icon)" class="h-14 w-14" :stroke-width="2.2" />
						</span>
					</div>
					<p class="mt-6 text-[13px] font-bold uppercase tracking-wider" :style="{ color: item.color }">{{ KICKER[item.kind] }}</p>
					<h2 class="mt-1 text-[26px] font-extrabold leading-tight">{{ item.title }}</h2>
					<p class="mt-2 text-[15px] text-ink-500 dark:text-ink-400">{{ item.body }}</p>
					<p v-if="item.xp" class="mt-4 inline-flex items-center gap-1.5 rounded-full bg-sun-50 px-3 py-1 text-[14px] font-extrabold text-sun-700 dark:bg-sun-500/15 dark:text-sun-400">
						<Sparkles class="h-4 w-4" /> +{{ item.xp }} XP
					</p>
					<AppButton ref="button" class="mt-6" size="lg" block @click="store.dismiss()">
						{{ store.queue.length > 1 ? "Next" : "Keep going" }}
					</AppButton>
				</div>
			</div>
		</Transition>
	</Teleport>
</template>
