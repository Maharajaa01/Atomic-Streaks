<script setup lang="ts">
const model = defineModel<boolean>({ required: true })
defineProps<{ label: string; description?: string }>()
</script>

<template>
	<label class="flex min-h-[52px] cursor-pointer items-center gap-4">
		<span class="flex-1">
			<span class="block text-[15px] font-bold text-ink-900 dark:text-white">{{ label }}</span>
			<span v-if="description" class="block text-[13px] text-ink-500 dark:text-ink-400">{{ description }}</span>
		</span>
		<input v-model="model" type="checkbox" role="switch" class="peer sr-only" />
		<span
			class="relative h-8 w-[52px] shrink-0 rounded-full bg-ink-200 transition-colors peer-checked:bg-mint-500 peer-focus-visible:ring-4 peer-focus-visible:ring-grape-400/50 dark:bg-night-700
				after:absolute after:left-1 after:top-1 after:h-6 after:w-6 after:rounded-full after:bg-white after:shadow after:transition-transform peer-checked:after:translate-x-5"
			aria-hidden="true"
		/>
	</label>
</template>
