<script setup lang="ts">
import { Mail, MailCheck } from "lucide-vue-next"
import { onMounted, ref } from "vue"
import { useRoute } from "vue-router"

import { getAuthOptions, requestPasswordReset } from "@/api/auth"
import AlertBanner from "@/components/ui/AlertBanner.vue"
import AppButton from "@/components/ui/AppButton.vue"
import TextField from "@/components/ui/TextField.vue"
import AuthLayout from "@/layouts/AuthLayout.vue"
import { EMAIL } from "@/lib/password"
import { online } from "@/lib/pwa"

const route = useRoute()
const email = ref(typeof route.query.email === "string" ? route.query.email : "")
const busy = ref(false)
const sent = ref(false)
const error = ref("")
const fieldError = ref("")
const canEmail = ref<boolean | null>(null)

onMounted(async () => {
	try {
		canEmail.value = (await getAuthOptions()).can_reset_password
	} catch {
		canEmail.value = true // let them try; the request itself answers generically
	}
})

async function submit() {
	error.value = ""
	fieldError.value = EMAIL.test(email.value.trim()) ? "" : "Enter the email you signed up with."
	if (fieldError.value) return
	busy.value = true
	try {
		await requestPasswordReset(email.value.trim())
		sent.value = true
	} catch (e) {
		error.value = (e as Error).message
	} finally {
		busy.value = false
	}
}
</script>

<template>
	<AuthLayout
		:title="sent ? 'Check your inbox' : 'Forgot your password?'"
		:subtitle="sent ? undefined : 'We\'ll email you a link to choose a new one.'"
	>
		<div v-if="sent" class="space-y-5">
			<div class="flex h-16 w-16 items-center justify-center rounded-3xl bg-mint-50 text-mint-600 dark:bg-mint-500/10">
				<MailCheck class="h-8 w-8" />
			</div>
			<p class="text-[15px] leading-relaxed text-ink-600 dark:text-ink-300">
				If <b class="text-ink-900 dark:text-white">{{ email.trim() }}</b> has an Atomic Streak account, a reset link is on
				its way. It can take a few minutes, so check your spam folder too.
			</p>
			<AppButton variant="secondary" size="lg" block @click="$router.push('/login')">Back to sign in</AppButton>
		</div>

		<AlertBanner v-else-if="canEmail === false" tone="info">
			Password reset emails aren't set up on this server yet. Ask the site administrator to reset your password for you.
		</AlertBanner>

		<form v-else class="space-y-5" novalidate @submit.prevent="submit">
			<AlertBanner v-if="error" tone="error">{{ error }}</AlertBanner>
			<AlertBanner v-if="!online" tone="offline">You're offline. Connect to the internet to continue.</AlertBanner>
			<TextField
				id="email"
				v-model="email"
				label="Email"
				:icon="Mail"
				:error="fieldError"
				type="email"
				inputmode="email"
				autocomplete="email"
				autocapitalize="none"
				spellcheck="false"
				placeholder="you@example.com"
				:disabled="busy"
			/>
			<AppButton type="submit" size="lg" block :loading="busy" :disabled="!online || canEmail === null">Send reset link</AppButton>
		</form>

		<template #footer>
			<p v-if="!sent">Remembered it? <RouterLink to="/login" class="link">Sign in</RouterLink></p>
		</template>
	</AuthLayout>
</template>
