<script setup lang="ts">
/** One Day Plan task: a round tick button and the task text (tap the text to edit). */
import { Check, Clock, Flag } from "lucide-vue-next"

import type { PlanTask } from "@/api/types"
import { formatTime } from "@/lib/dates"

defineProps<{ task: PlanTask }>()
defineEmits<{ toggle: []; edit: [] }>()
</script>

<template>
	<div class="flex items-start gap-3 rounded-3xl bg-white p-3 pl-3.5 shadow-soft dark:bg-night-900" :class="task.is_done ? 'opacity-70' : ''">
		<button
			type="button"
			class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border-2 transition"
			:class="task.is_done ? 'border-mint-500 bg-mint-500 text-white' : 'border-ink-300 text-transparent hover:border-mint-500 dark:border-night-600'"
			:aria-label="task.is_done ? `Mark '${task.title}' as not done` : `Mark '${task.title}' as done`"
			:aria-pressed="!!task.is_done"
			@click="$emit('toggle')"
		>
			<Check class="h-5 w-5" :stroke-width="3" />
		</button>
		<button type="button" class="min-w-0 flex-1 self-center py-1 text-left" :aria-label="`Edit '${task.title}'`" @click="$emit('edit')">
			<span class="block whitespace-pre-line break-words text-[15px] font-semibold leading-snug" :class="task.is_done ? 'text-ink-400 line-through' : 'text-ink-900 dark:text-white'">{{ task.title }}</span>
			<span v-if="task.start_time || task.priority !== 'Normal' || task.notes" class="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[12.5px] text-ink-500 dark:text-ink-400">
				<span v-if="task.start_time" class="inline-flex items-center gap-1 font-bold"><Clock class="h-3.5 w-3.5" />{{ formatTime(task.start_time) }}</span>
				<span
					v-if="task.priority === 'High'"
					class="inline-flex items-center gap-1 rounded-md bg-blush-50 px-1.5 font-bold text-blush-600 dark:bg-blush-500/10 dark:text-blush-400"
				>
					<Flag class="h-3 w-3" />High
				</span>
				<span v-else-if="task.priority === 'Low'" class="rounded-md bg-ink-100 px-1.5 font-bold dark:bg-night-800">Low</span>
				<span v-if="task.notes" class="basis-full whitespace-pre-line break-words">{{ task.notes }}</span>
			</span>
		</button>
	</div>
</template>
