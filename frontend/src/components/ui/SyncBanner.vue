<script setup lang="ts">
/** Offline / waiting-to-sync status. Never says "saved" until the server has it. */
import { CloudOff, Loader2, LogIn, RefreshCw } from "lucide-vue-next"
import { computed } from "vue"

import { loginUrl, usingSavedData } from "@/api/client"
import { online } from "@/lib/pwa"
import { useSync } from "@/stores/sync"

const sync = useSync()
const waiting = computed(() => (sync.count ? `${sync.count} check-in${sync.count === 1 ? "" : "s"} waiting to sync` : ""))
</script>

<template>
	<div
		v-if="!online || sync.count || sync.needsSignIn"
		class="mb-4 flex items-center gap-3 rounded-2xl px-4 py-3 text-[14px] font-semibold"
		:class="sync.needsSignIn ? 'bg-blush-50 text-blush-700 dark:bg-blush-500/10 dark:text-blush-400' : 'bg-sky-50 text-sky-700 dark:bg-sky-500/10 dark:text-sky-400'"
		role="status"
		aria-live="polite"
	>
		<template v-if="sync.needsSignIn">
			<LogIn class="h-5 w-5 shrink-0" />
			<span class="flex-1">Your session ended. Sign in again to sync {{ waiting ? waiting.split(" waiting")[0] : "your check-ins" }}. They're safe on this device.</span>
			<a :href="loginUrl()" class="shrink-0 rounded-xl bg-blush-500 px-3 py-1.5 text-[13px] font-bold text-white">Sign in</a>
		</template>
		<template v-else-if="!online">
			<CloudOff class="h-5 w-5 shrink-0" />
			<span class="flex-1">
				You're offline<template v-if="usingSavedData">, showing what this device saved</template>.
				<template v-if="waiting">{{ waiting }}.</template>
				<template v-else>Check-ins will be kept here until you reconnect.</template>
			</span>
		</template>
		<template v-else>
			<Loader2 v-if="sync.syncing" class="h-5 w-5 shrink-0 animate-spin" />
			<RefreshCw v-else class="h-5 w-5 shrink-0" />
			<span class="flex-1">{{ sync.syncing ? "Syncing…" : waiting }}</span>
			<button v-if="!sync.syncing" type="button" class="shrink-0 rounded-xl bg-sky-500 px-3 py-1.5 text-[13px] font-bold text-white" @click="sync.flush()">Sync now</button>
		</template>
	</div>
</template>
