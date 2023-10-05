<template>
	<n-form ref="formRef" :model="model" :rules="rules">
		<n-form-item path="username" label="Username">
			<n-input
				v-model:value="model.username"
				@keydown.enter="signIn"
				placeholder="Username..."
				size="large"
				autocomplete="on"
			/>
		</n-form-item>
		<n-form-item path="password" label="Password">
			<n-input
				v-model:value="model.password"
				type="password"
				show-password-on="click"
				placeholder="Password..."
				@keydown.enter="signIn"
				autocomplete="on"
				size="large"
			/>
		</n-form-item>
		<div class="flex flex-col items-end gap-6">
			<div class="flex justify-end w-full">
				<n-button text type="primary" @click="emit('goto-forgot-password')">Forgot Password?</n-button>
			</div>
			<div class="w-full">
				<n-button type="primary" @click="signIn" class="!w-full" size="large">Sign in</n-button>
			</div>
		</div>
	</n-form>
</template>

<script lang="ts" setup>
import { ref } from "vue"

import {
	type FormInst,
	type FormValidationError,
	useMessage,
	type FormRules,
	NForm,
	NFormItem,
	NInput,
	NButton
} from "naive-ui"
import { useAuthStore } from "@/stores/auth"
import Api from "@/api"
import { useRouter } from "vue-router"
import type { LoginPayload } from "@/types/auth.d"

interface ModelType {
	username: string
	password: string
}

const emit = defineEmits<{
	(e: "goto-forgot-password"): void
}>()

const loading = ref(false)
const router = useRouter()
const formRef = ref<FormInst | null>(null)
const message = useMessage()
const model = ref<ModelType>({
	username: "",
	password: ""
})

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

function signIn(e: Event) {
	e.preventDefault()
	formRef.value?.validate((errors: Array<FormValidationError> | undefined) => {
		if (!errors) {
			loading.value = true

			const payload: LoginPayload = {
				username: model.value.username,
				password: model.value.password
			}

			Api.auth
				.login(payload)
				.then(res => {
					if (res.data.success && res.data.token) {
						useAuthStore().setLogged({
							token: res.data.token
						})
						router.push({ path: "/", replace: true })
					} else {
						message.warning(res.data?.message || "An error occurred. Please try again later.")
					}
				})
				.catch(err => {
					message.error(err.response?.data?.message || "An error occurred. Please try again later.")
				})
				.finally(() => {
					loading.value = false
				})
		} else {
			message.error("Invalid credentials")
		}
	})
}
</script>
