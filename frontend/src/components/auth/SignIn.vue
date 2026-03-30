<template>
	<div>
		<!-- ── Normal login form ── -->
		<template v-if="!show2fa">
			<n-form ref="formRef" :model :rules>
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
						<n-button
							type="primary"
							class="w-full!"
							size="large"
							:loading
							:disabled="!isValid"
							@click="signIn"
						>
							Sign in
						</n-button>
					</div>
				</div>
			</n-form>

			<SsoOptions @show2fa-form="handleShow2faForm" @login-success="handleLoginSuccess" />
		</template>

		<!-- ── 2FA verification step ── -->
		<template v-if="show2fa">
			<div class="mb-6 text-center">
				<Icon name="carbon:locked" :size="48" class="text-primary mb-3" />
				<h3 class="mb-2 text-xl font-semibold">Two-Factor Authentication</h3>
				<p class="text-secondary text-sm leading-relaxed">Enter the 6-digit code from your authenticator app</p>
			</div>

			<div class="mb-4">
				<n-input
					v-model:value="twoFaCode"
					placeholder="123456"
					maxlength="6"
					size="large"
					:input-props="{ autocomplete: 'one-time-code', inputmode: 'numeric' }"
					@keydown.enter="verify2fa()"
				/>
			</div>

			<n-button
				type="primary"
				class="mb-5 w-full!"
				size="large"
				:loading="twoFaLoading"
				:disabled="twoFaCode.length < 6"
				@click="verify2fa()"
			>
				Verify
			</n-button>

			<n-collapse-transition :show="showBackupInput">
				<div class="mb-3">
					<n-input
						v-model:value="backupCode"
						placeholder="Backup code (e.g. ABCD1234EF)"
						size="large"
						@keydown.enter="verify2fa({ useBackupCode: true })"
					/>
				</div>
				<n-button
					class="mb-5 w-full!"
					size="large"
					:loading="twoFaLoading"
					:disabled="!backupCode"
					@click="verify2fa({ useBackupCode: true })"
				>
					Use backup code
				</n-button>
			</n-collapse-transition>

			<div class="border-divider flex items-center justify-between border-t pt-2">
				<n-button text size="small" @click="showBackupInput = !showBackupInput">
					{{ showBackupInput ? "← Use authenticator code" : "Use a backup code instead" }}
				</n-button>
				<n-button text size="small" @click="cancel2fa">Back to login</n-button>
			</div>
		</template>
	</div>
</template>

<script lang="ts" setup>
import type { FormInst, FormRules, FormValidationError } from "naive-ui"
import type { TOTPValidateRequest } from "@/api/endpoints/totp"
import type { LoginPayload } from "@/types/auth.d"
import { NButton, NCollapseTransition, NForm, NFormItem, NInput, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import { useRouter } from "vue-router"
import Icon from "@/components/common/Icon.vue"
import { useAuthStore } from "@/stores/auth"
import SsoOptions from "./SsoOptions.vue"

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

// ── 2FA state ────────────────────────────────────────────────────────────────
const show2fa = ref(false)
const twoFaTempToken = ref("")
const twoFaCode = ref("")
const backupCode = ref("")
const twoFaLoading = ref(false)
const showBackupInput = ref(false)

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

function cancel2fa() {
	show2fa.value = false
	twoFaTempToken.value = ""
	twoFaCode.value = ""
	backupCode.value = ""
	showBackupInput.value = false
}

function handleShow2faForm(token: string) {
	twoFaTempToken.value = token
	show2fa.value = true
}

function handleLoginSuccess(token: string) {
	authStore.setLogged(token)
	router.push({ path: "/", replace: true })
}

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
					// Check if 2FA is required
					if (res?.requires_2fa) {
						handleShow2faForm(res.access_token)
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

async function verify2fa(params?: { useBackupCode?: boolean }) {
	twoFaLoading.value = true

	const payload: TOTPValidateRequest = {
		temp_token: twoFaTempToken.value,
		code: params?.useBackupCode ? undefined : twoFaCode.value,
		backup_code: params?.useBackupCode ? backupCode.value : undefined
	}

	authStore
		.verify2fa(payload)
		.then(() => {
			router.push({ path: "/", replace: true })
		})
		.catch(err => {
			message.error(err?.message || err.response?.data?.detail || "An error occurred. Please try again later.")
		})
		.finally(() => {
			twoFaLoading.value = false
		})
}

watch(isValid, val => {
	if (val) {
		formRef.value?.validate()
	}
})
</script>
