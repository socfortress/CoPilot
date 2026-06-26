<template>
	<div>
		<n-form v-if="!show2faForm" ref="formRef" :model :rules :disabled="loading">
			<n-form-item path="username" label="Username">
				<n-input
					v-model:value="model.username"
					placeholder="Insert your Username"
					:input-props="{ autocomplete: 'username' }"
					size="large"
					@keydown.enter="signIn"
				/>
			</n-form-item>
			<n-form-item path="password" label="Password">
				<n-input
					v-model:value="model.password"
					type="password"
					show-password-on="click"
					placeholder="Insert your password"
					:input-props="{ autocomplete: 'password' }"
					size="large"
					@keydown.enter="signIn"
				/>
			</n-form-item>
			<div class="flex flex-col items-end gap-6">
				<div class="w-full">
					<n-button type="primary" class="w-full!" size="large" :loading :disabled="!isValid" @click="signIn">
						Sign in
					</n-button>
				</div>
			</div>
		</n-form>

		<TotpForm v-else v-model:two-fa-temp-token="twoFaTempToken" @cancel="show2faForm = false" />
	</div>
</template>

<script lang="ts" setup>
import type { FormInst, FormRules, FormValidationError } from "naive-ui"
import type { LoginPayload } from "@/api/endpoints/auth"
import { NButton, NForm, NFormItem, NInput, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import { useRouter } from "vue-router"
import TotpForm from "@/components/auth/TotpForm.vue"
import { useAuthStore } from "@/stores/auth"

interface ModelType {
	username: string | null
	password: string | null
}

const loading = ref(false)
const router = useRouter()
const formRef = ref<FormInst | null>(null)
const message = useMessage()
const model = ref<ModelType>({
	username: null,
	password: null
})
const authStore = useAuthStore()

// 2FA challenge state — when login returns `requires_2fa`, we swap the credentials
// form for the TOTP challenge and hand it the short-lived temp token.
const show2faForm = ref(false)
const twoFaTempToken = ref("")

const rules: FormRules = {
	username: [
		{
			required: true,
			trigger: ["blur"],
			message: "Username is required"
		}
	],
	password: [
		{
			required: true,
			trigger: ["blur"],
			message: "Password is required"
		}
	]
}

const isValid = computed(() => {
	return model.value.username && model.value.password
})

function signIn(e: Event) {
	e.preventDefault()
	formRef.value?.validate((errors: Array<FormValidationError> | undefined) => {
		if (!errors) {
			loading.value = true

			const payload: LoginPayload = {
				username: model.value.username || "",
				password: model.value.password || ""
			}

			authStore
				.login(payload)
				.then(res => {
					if (res?.requires_2fa) {
						// Credentials accepted but a second factor is required. Carry the temp
						// token into the TOTP challenge; login completes in TotpForm.
						twoFaTempToken.value = res.access_token
						show2faForm.value = true
						return
					}
					router.push({ path: "/", replace: true })
				})
				.catch(err => {
					message.error(err?.message || "An error occurred. Please try again later.")
				})
				.finally(() => {
					loading.value = false
				})
		} else {
			message.error("Invalid credentials")
		}
	})
}

watch(isValid, val => {
	if (val) {
		formRef.value?.validate()
	}
})
</script>
