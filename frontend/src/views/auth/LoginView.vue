<script setup lang="ts">
import { Download, Mail } from "lucide-vue-next"
import { computed, onMounted, ref } from "vue"
import { useRoute } from "vue-router"

import { getAuthOptions, login } from "@/api/auth"
import { safeRedirect } from "@/api/client"
import AlertBanner from "@/components/ui/AlertBanner.vue"
import AppButton from "@/components/ui/AppButton.vue"
import PasswordField from "@/components/ui/PasswordField.vue"
import TextField from "@/components/ui/TextField.vue"
import AuthLayout from "@/layouts/AuthLayout.vue"
import { EMAIL } from "@/lib/password"
import { canInstall, isStandalone, online, promptInstall } from "@/lib/pwa"

const route = useRoute()
const email = ref(typeof route.query.email === "string" ? route.query.email : "")
const password = ref("")
const busy = ref(false)
const error = ref("")
const fieldErrors = ref<{ email?: string; password?: string }>({})
const allowSignup = ref(true)

const needsSignIn = computed(() => !!route.query.redirect)
const passwordChanged = computed(() => route.query.reset === "1")
const showInstall = computed(() => canInstall.value && !isStandalone())

onMounted(async () => {
	try {
		allowSignup.value = (await getAuthOptions()).allow_signup
	} catch {
		/* keep the link; the sign-up page explains if it's closed */
	}
})

function validate(): boolean {
	const errs: typeof fieldErrors.value = {}
	if (!email.value.trim()) errs.email = "Enter your email."
	else if (!EMAIL.test(email.value.trim()) && !/^[\w.-]+$/.test(email.value.trim())) errs.email = "Check your email address."
	if (!password.value) errs.password = "Enter your password."
	fieldErrors.value = errs
	return !errs.email && !errs.password
}

async function submit() {
	error.value = ""
	if (!validate()) return
	busy.value = true
	try {
		await login(email.value.trim(), password.value)
		// full load: the page must be rendered again for the new session's CSRF token
		window.location.replace(safeRedirect(route.query.redirect))
	} catch (e) {
		error.value = (e as Error).message
		password.value = ""
		busy.value = false
	}
}
</script>

<template>
	<AuthLayout title="Welcome back" subtitle="Sign in to keep your streak going.">
		<form class="space-y-5" novalidate @submit.prevent="submit">
			<AlertBanner v-if="passwordChanged && !error" tone="success">Your password was changed. Sign in with the new one.</AlertBanner>
			<AlertBanner v-else-if="needsSignIn && !error">Sign in to continue.</AlertBanner>
			<AlertBanner v-if="error" tone="error">{{ error }}</AlertBanner>
			<AlertBanner v-if="!online" tone="offline">You're offline. Connect to the internet to sign in.</AlertBanner>

			<TextField
				id="email"
				v-model="email"
				label="Email"
				:icon="Mail"
				:error="fieldErrors.email"
				type="email"
				inputmode="email"
				autocomplete="username"
				autocapitalize="none"
				spellcheck="false"
				placeholder="you@example.com"
				:disabled="busy"
			/>
			<div>
				<PasswordField id="password" v-model="password" label="Password" :error="fieldErrors.password" :disabled="busy" />
				<div class="mt-2 text-right">
					<RouterLink :to="{ name: 'forgot-password', query: email ? { email } : {} }" class="link text-[13px]">
						Forgot password?
					</RouterLink>
				</div>
			</div>

			<AppButton type="submit" size="lg" block :loading="busy" :disabled="!online">Sign in</AppButton>
		</form>

		<template #footer>
			<p v-if="allowSignup">New here? <RouterLink to="/signup" class="link">Create an account</RouterLink></p>
			<button
				v-if="showInstall"
				type="button"
				class="mt-6 inline-flex items-center gap-2 rounded-full border-2 border-ink-200 px-4 py-2 text-[13px] font-semibold text-ink-700 hover:border-ink-300 dark:border-night-700 dark:text-ink-200"
				@click="promptInstall"
			>
				<Download class="h-4 w-4" /> Install the app
			</button>
		</template>
	</AuthLayout>
</template>
