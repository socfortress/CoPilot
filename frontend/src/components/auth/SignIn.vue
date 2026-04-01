<template>
	<div>
		<!-- ── Normal login form ── -->
		<n-collapse-transition :show="!show2fa">
			<div class="flex flex-col">
				<n-form ref="formRef" :model :rules>
					<n-form-item path="username" label="Username">
						<n-input
							v-model:value="model.username"
							placeholder="Insert your username"
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
			</div>
		</n-collapse-transition>

		<n-collapse-transition :show="show2fa">
			<TotpForm v-model:two-fa-temp-token="twoFaTempToken" @cancel="cancel2fa" />
		</n-collapse-transition>
	</div>
</template>

<script lang="ts" setup>
import type { FormInst, FormRules, FormValidationError } from "naive-ui"
import type { LoginPayload } from "@/types/auth.d"
import { NButton, NCollapseTransition, NForm, NFormItem, NInput, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import { useRouter } from "vue-router"
import { useAuthStore } from "@/stores/auth"
import SsoOptions from "./SsoOptions.vue"
import TotpForm from "./TotpForm.vue"

interface ModelType {
	username: string | null
	password: string | null
}

const router = useRouter()
const authStore = useAuthStore()
const message = useMessage()

const loading = ref(false)
const formRef = ref<FormInst | null>(null)
const model = ref<ModelType>({
	username: null,
	password: null
})
const show2fa = ref(false)
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

function cancel2fa() {
	show2fa.value = false
	twoFaTempToken.value = ""
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

watch(isValid, val => {
	if (val) {
		formRef.value?.validate()
	}
})

onBeforeMount(() => {
	// Check if we're returning from SSO callback (token in URL fragment, not query)
	const params = new URLSearchParams(window.location.hash.substring(1) || window.location.search)
	const error_message = params.get("error_message")

	if (params.has("error_message")) {
		params.delete("error_message")
	}

	if (error_message) {
		message.error(error_message, { duration: 6_000 })
	}

	history.replaceState(null, "", `${window.location.pathname}?${params.toString()}`)
})
</script>
