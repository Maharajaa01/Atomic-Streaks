<script setup lang="ts">
import { computed, ref } from "vue"
import { useRoute } from "vue-router"

import { resetPassword } from "@/api/auth"
import { ApiError, APP_BASE } from "@/api/client"
import AlertBanner from "@/components/ui/AlertBanner.vue"
import AppButton from "@/components/ui/AppButton.vue"
import PasswordField from "@/components/ui/PasswordField.vue"
import AuthLayout from "@/layouts/AuthLayout.vue"
import { online } from "@/lib/pwa"

const route = useRoute()
const key = computed(() => (typeof route.query.key === "string" ? route.query.key : ""))
const password = ref("")
const confirm = ref("")
const busy = ref(false)
const error = ref("")
const expired = ref(false)
const errors = ref<{ password?: string; confirm?: string }>({})

async function submit() {
	error.value = ""
	const e: typeof errors.value = {}
	if (password.value.length < 8) e.password = "Use at least 8 characters."
	if (confirm.value !== password.value) e.confirm = "The two passwords don't match."
	errors.value = e
	if (Object.keys(e).length) return
	busy.value = true
	try {
		await resetPassword(key.value, password.value)
		// Frappe signs the user in after a successful reset; reload for the new session
		window.location.replace(APP_BASE)
	} catch (err) {
		expired.value = (err as ApiError).status === 410
		error.value = (err as Error).message
		busy.value = false
	}
}
</script>

<template>
	<AuthLayout title="Choose a new password" subtitle="Make it one you don't use anywhere else.">
		<AlertBanner v-if="!key" tone="error">
			This link is incomplete. Open the link from your email again, or
			<RouterLink to="/forgot-password" class="underline">ask for a new one</RouterLink>.
		</AlertBanner>

		<form v-else class="space-y-5" novalidate @submit.prevent="submit">
			<AlertBanner v-if="error" tone="error">
				{{ error }}
				<RouterLink v-if="expired" to="/forgot-password" class="mt-1 block underline">Send me a new link</RouterLink>
			</AlertBanner>
			<PasswordField id="new-password" v-model="password" label="New password" autocomplete="new-password" :error="errors.password" meter :disabled="busy" />
			<PasswordField id="confirm-password" v-model="confirm" label="Confirm new password" autocomplete="new-password" :error="errors.confirm" :disabled="busy" />
			<AppButton type="submit" size="lg" block :loading="busy" :disabled="!online">Save new password</AppButton>
		</form>
	</AuthLayout>
</template>
