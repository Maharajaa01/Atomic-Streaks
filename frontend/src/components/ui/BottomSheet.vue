<script setup lang="ts">
/** Bottom sheet on phones, centred dialog on larger screens. Esc / backdrop closes it. */
import { X } from "lucide-vue-next"
import { nextTick, onBeforeUnmount, ref, watch } from "vue"

const props = defineProps<{ open: boolean; title: string }>()
const emit = defineEmits<{ close: [] }>()
const panel = ref<HTMLElement | null>(null)
let lastFocus: Element | null = null

function onKey(e: KeyboardEvent) {
	if (e.key === "Escape") emit("close")
}

watch(
	() => props.open,
	async (open) => {
		if (open) {
			lastFocus = document.activeElement
			document.addEventListener("keydown", onKey)
			document.body.style.overflow = "hidden"
			await nextTick()
			panel.value?.focus()
		} else {
			document.removeEventListener("keydown", onKey)
			document.body.style.overflow = ""
			;(lastFocus as HTMLElement | null)?.focus?.()
		}
	},
)
onBeforeUnmount(() => {
	document.removeEventListener("keydown", onKey)
	document.body.style.overflow = ""
})
</script>

<template>
	<Teleport to="body">
		<Transition enter-active-class="transition-opacity duration-200" enter-from-class="opacity-0" leave-active-class="transition-opacity duration-150" leave-to-class="opacity-0">
			<div v-if="open" class="fixed inset-0 z-[70] flex items-end justify-center bg-ink-900/50 backdrop-blur-[2px] sm:items-center sm:p-6" @click.self="emit('close')">
				<div
					ref="panel"
					role="dialog"
					aria-modal="true"
					:aria-label="title"
					tabindex="-1"
					class="max-h-[92dvh] w-full overflow-y-auto rounded-t-4xl bg-white p-6 shadow-sheet outline-none animate-fade-up dark:bg-night-900 sm:max-w-md sm:rounded-4xl"
					style="padding-bottom: max(env(safe-area-inset-bottom), 1.5rem)"
				>
					<div class="mx-auto -mt-2 mb-4 h-1.5 w-10 rounded-full bg-ink-200 dark:bg-night-700 sm:hidden" aria-hidden="true" />
					<div class="mb-4 flex items-start justify-between gap-4">
						<h2 class="text-xl font-extrabold">{{ title }}</h2>
						<button type="button" class="-m-2 rounded-xl p-2 text-ink-400 hover:bg-ink-100 dark:hover:bg-night-800" aria-label="Close" @click="emit('close')">
							<X class="h-5 w-5" />
						</button>
					</div>
					<slot />
				</div>
			</div>
		</Transition>
	</Teleport>
</template>
