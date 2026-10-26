<template>
	<div>
		<!-- Signed out because the account was disabled while the session was open (#1296). -->
		<n-alert
			v-if="route.query.reason === 'disabled' && !show2faForm"
			type="error"
			:bordered="false"
			class="mb-4"
			data-testid="login-account-disabled"
		>
			{{ $t("auth.signIn.accountDisabled") }}
		</n-alert>
		<n-form v-if="!show2faForm" ref="formRef" :model :rules :disabled="loading">
			<n-form-item path="username" :label="$t('auth.signIn.username')">
				<n-input
					v-model:value="model.username"
					:placeholder="$t('auth.signIn.usernamePlaceholder')"
					:input-props="{ autocomplete: 'username' }"
					data-testid="login-username"
					size="large"
					@keydown.enter="signIn"
				/>
			</n-form-item>
			<n-form-item path="password" :label="$t('auth.signIn.password')">
				<n-input
					v-model:value="model.password"
					type="password"
					show-password-on="click"
					:placeholder="$t('auth.signIn.passwordPlaceholder')"
					:input-props="{ autocomplete: 'password' }"
					data-testid="login-password"
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
						data-testid="login-submit"
						@click="signIn"
					>
						{{ $t("auth.signIn.submit") }}
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
import { NAlert, NButton, NForm, NFormItem, NInput, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import { useI18n } from "vue-i18n"
import { useRoute, useRouter } from "vue-router"
import TotpForm from "@/components/auth/TotpForm.vue"
import { useAuthStore } from "@/stores/auth"
import { getSafeRedirect } from "@/utils/auth"

interface ModelType {
	username: string | null
	password: string | null
}

const loading = ref(false)
const router = useRouter()
const route = useRoute()
const formRef = ref<FormInst | null>(null)
const message = useMessage()
const model = ref<ModelType>({
	username: null,
	password: null
})
const authStore = useAuthStore()
const { t } = useI18n()

// 2FA challenge state — when login returns `requires_2fa`, we swap the credentials
// form for the TOTP challenge and hand it the short-lived temp token.
const show2faForm = ref(false)
const twoFaTempToken = ref("")

const rules = computed<FormRules>(() => ({
	username: [
		{
			required: true,
			trigger: ["blur"],
			message: t("auth.signIn.usernameRequired")
		}
	],
	password: [
		{
			required: true,
			trigger: ["blur"],
			message: t("auth.signIn.passwordRequired")
		}
	]
}))

const isValid = computed(() => {
	return model.value.username && model.value.password
})

async function login(payload: LoginPayload) {
	try {
		const res = await authStore.login(payload)
		if (res?.requires_2fa) {
			// Credentials accepted but a second factor is required. Carry the temp
			// token into the TOTP challenge; login completes in TotpForm.
			twoFaTempToken.value = res.access_token
			show2faForm.value = true
			return
		}
		router.replace(getSafeRedirect(route.query.redirect))
	} catch (err) {
		message.error((err as Error)?.message || t("auth.signIn.genericError"))
	} finally {
		loading.value = false
	}
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

			login(payload)
		} else {
			message.error(t("auth.signIn.invalidCredentials"))
		}
	})
}

watch(isValid, val => {
	if (val) {
		formRef.value?.validate()
	}
})
</script>
