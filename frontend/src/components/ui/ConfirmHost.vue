<script setup lang="ts">
import { useConfirm } from "@/stores/confirm"

import AppButton from "./AppButton.vue"
import BottomSheet from "./BottomSheet.vue"

const confirm = useConfirm()
</script>

<template>
	<BottomSheet :open="!!confirm.current" :title="confirm.current?.title ?? ''" @close="confirm.answer(false)">
		<p v-if="confirm.current?.body" class="text-[15px] leading-relaxed text-ink-600 dark:text-ink-300">{{ confirm.current.body }}</p>
		<div class="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
			<AppButton variant="secondary" size="lg" class="sm:size-auto" @click="confirm.answer(false)">Cancel</AppButton>
			<AppButton :variant="confirm.current?.danger ? 'danger' : 'primary'" size="lg" @click="confirm.answer(true)">
				{{ confirm.current?.confirmLabel }}
			</AppButton>
		</div>
	</BottomSheet>
</template>
