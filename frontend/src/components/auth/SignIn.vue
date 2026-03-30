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

			<!-- SSO Buttons -->
			<div v-if="ssoStatus?.sso_enabled" class="mt-6">
				<n-divider>
					<span class="text-secondary text-xs">or sign in with</span>
				</n-divider>
				<div class="flex flex-col gap-3">
					<n-button v-if="ssoStatus.azure_enabled" size="large" class="w-full!" @click="loginWithAzure">
						<template #icon>
							<Icon :name="AzureIcon" :size="18" />
						</template>
						Microsoft Entra ID
					</n-button>
					<n-button v-if="ssoStatus.google_enabled" size="large" class="w-full!" @click="loginWithGoogle">
						<template #icon>
							<Icon :name="GoogleIcon" :size="18" />
						</template>
						Google
					</n-button>
					<n-button
						v-if="ssoStatus.cf_enabled"
						size="large"
						class="w-full!"
						:loading="cfLoading"
						@click="loginWithCloudflare"
					>
						<template #icon>
							<Icon :name="CloudflareIcon" :size="18" />
						</template>
						Cloudflare Access
					</n-button>
				</div>
			</div>
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
import type { SSOPublicStatus } from "@/api/endpoints/sso"
import type { TOTPValidateRequest } from "@/api/endpoints/totp"
import type { LoginPayload } from "@/types/auth.d"
import { NButton, NCollapseTransition, NDivider, NForm, NFormItem, NInput, useMessage } from "naive-ui"
import { computed, onMounted, ref, watch } from "vue"
import { useRouter } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useAuthStore } from "@/stores/auth"
import { getSSOStatus, ssoAzure, ssoCloudflare, ssoGoogle } from "./sso"

const AzureIcon = "devicon-plain:azure"
const GoogleIcon = "devicon-plain:googlecloud"
const CloudflareIcon = "simple-icons:cloudflare"

interface ModelType {
	username: string | null
	password: string | null
}

const loading = ref(false)
const cfLoading = ref(false)
const router = useRouter()
const formRef = ref<FormInst | null>(null)
const message = useMessage()
const model = ref<ModelType>({
	username: null,
	password: null
})
const authStore = useAuthStore()
const ssoStatus = ref<SSOPublicStatus | null>(null)

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
						twoFaTempToken.value = res.access_token
						show2fa.value = true
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

function cancel2fa() {
	show2fa.value = false
	twoFaTempToken.value = ""
	twoFaCode.value = ""
	backupCode.value = ""
	showBackupInput.value = false
}

function loginWithAzure() {
	ssoAzure()
}

function loginWithGoogle() {
	ssoGoogle()
}

function loginWithCloudflare() {
	cfLoading.value = true

	ssoCloudflare((error, res) => {
		cfLoading.value = false

		if (error) {
			message.error(error)
			return
		}

		if (res?.requires_2fa && res?.access_token) {
			// Cloudflare auth OK but user has 2FA — show verification step
			twoFaTempToken.value = res.access_token
			show2fa.value = true
		} else if (res?.access_token) {
			authStore.setLogged(res.access_token)
			router.push({ path: "/", replace: true })
		}
	})
}

function loadSSOStatus() {
	getSSOStatus(status => {
		ssoStatus.value = status
	})
}

onMounted(() => {
	loadSSOStatus()

	// Check if we're returning from SSO callback (token in URL fragment, not query)
	if (window.location.hash) {
		const params = new URLSearchParams(window.location.hash.substring(1))
		const token = params.get("token")
		const needs2fa = params.get("requires_2fa") === "true"

		if (token && needs2fa) {
			// SSO succeeded but user has 2FA — show verification step
			twoFaTempToken.value = token
			show2fa.value = true
		} else if (token) {
			// Remove fragment from history so the token isn't stored in browser history
			history.replaceState(null, "", window.location.pathname + window.location.search)
			authStore.setLogged(token)
			router.push({ path: "/", replace: true })
		}
	}
})

watch(isValid, val => {
	if (val) {
		formRef.value?.validate()
	}
})
</script>
