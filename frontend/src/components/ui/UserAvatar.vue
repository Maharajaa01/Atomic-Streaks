<script setup lang="ts">
import { ref } from "vue"

import { useSession } from "@/stores/session"

withDefaults(defineProps<{ size?: number }>(), { size: 44 })
const session = useSession()
const failed = ref(false)
</script>

<template>
	<span
		class="inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full bg-gradient-to-br from-blush-400 to-tangerine-500 font-display font-extrabold text-white ring-2 ring-white dark:ring-night-900"
		:style="{ width: `${size}px`, height: `${size}px`, fontSize: `${size * 0.38}px` }"
	>
		<img v-if="session.avatar && !failed" :src="session.avatar" alt="" class="h-full w-full object-cover" @error="failed = true" />
		<template v-else>{{ session.initials }}</template>
	</span>
</template>
