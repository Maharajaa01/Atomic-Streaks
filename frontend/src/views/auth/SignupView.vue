<script setup lang="ts">
import { Mail, UserRound } from "lucide-vue-next"
import { onMounted, ref } from "vue"

import { getAuthOptions, register } from "@/api/auth"
import { ApiError, APP_BASE } from "@/api/client"
import AlertBanner from "@/components/ui/AlertBanner.vue"
import AppButton from "@/components/ui/AppButton.vue"
import PasswordField from "@/components/ui/PasswordField.vue"
import TextField from "@/components/ui/TextField.vue"
import AuthLayout from "@/layouts/AuthLayout.vue"
import { EMAIL } from "@/lib/password"
import { online } from "@/lib/pwa"

const name = ref("")
const email = ref("")
const password = ref("")
const busy = ref(false)
const error = ref("")
const exists = ref(false)
const closed = ref(false)
const errors = ref<{ name?: string; email?: string; password?: string }>({})

onMounted(async () => {
	try {
		closed.value = !(await getAuthOptions()).allow_signup
	} catch {
		/* the server will say so on submit */
	}
})

function validate(): boolean {
	const e: typeof errors.value = {}
	if (!name.value.trim()) e.name = "Tell us what to call you."
	if (!EMAIL.test(email.value.trim())) e.email = "Enter a valid email address."
	if (password.value.length < 8) e.password = "Use at least 8 characters."
	errors.value = e
	return !Object.keys(e).length
}

async function submit() {
	error.value = ""
	exists.value = false
	if (!validate()) return
	busy.value = true
	try {
		await register(name.value.trim(), email.value.trim(), password.value)
		// signed in by the server; reload for the new session's CSRF token
		window.location.replace(APP_BASE)
	} catch (e) {
		const err = e as ApiError
		exists.value = /DuplicateEntry/.test(err.excType)
		error.value = err.message
		busy.value = false
	}
}
</script>

<template>
	<AuthLayout title="Start your streak" subtitle="Free, private, and takes a minute.">
		<AlertBanner v-if="closed" tone="info">
			New sign-ups are paused right now. If you already have an account,
			<RouterLink to="/login" class="underline">sign in</RouterLink>.
		</AlertBanner>

		<form v-else class="space-y-5" novalidate @submit.prevent="submit">
			<AlertBanner v-if="error" tone="error">
				{{ error }}
				<RouterLink v-if="exists" :to="{ name: 'login', query: { email: email.trim() } }" class="mt-1 block underline">
					Go to sign in
				</RouterLink>
			</AlertBanner>
			<AlertBanner v-if="!online" tone="offline">You're offline. Connect to the internet to create an account.</AlertBanner>

			<TextField
				id="name"
				v-model="name"
				label="Your name"
				:icon="UserRound"
				:error="errors.name"
				autocomplete="name"
				placeholder="Priya Raman"
				maxlength="140"
				:disabled="busy"
			/>
			<TextField
				id="email"
				v-model="email"
				label="Email"
				:icon="Mail"
				:error="errors.email"
				type="email"
				inputmode="email"
				autocomplete="email"
				autocapitalize="none"
				spellcheck="false"
				placeholder="you@example.com"
				:disabled="busy"
			/>
			<PasswordField
				id="password"
				v-model="password"
				label="Password"
				autocomplete="new-password"
				:error="errors.password"
				meter
				:disabled="busy"
			/>

			<AppButton type="submit" size="lg" block :loading="busy" :disabled="!online">Create account</AppButton>
		</form>

		<template #footer>
			<p>Already have an account? <RouterLink to="/login" class="link">Sign in</RouterLink></p>
		</template>
	</AuthLayout>
</template>
