<template>
	<n-form ref="formRef" :model="model" :rules="rules">
		<n-form-item path="username" label="Username">
			<n-input
				v-model:value="model.username"
				placeholder="Username..."
				size="large"
				autocomplete="on"
				@keydown.enter="signIn"
			/>
		</n-form-item>
		<n-form-item path="password" label="Password">
			<n-input
				v-model:value="model.password"
				type="password"
				show-password-on="click"
				placeholder="Password..."
				autocomplete="on"
				size="large"
				@keydown.enter="signIn"
			/>
		</n-form-item>
		<div class="flex flex-col items-end gap-6">
			<div class="w-full">
				<n-button type="primary" class="!w-full" size="large" :loading :disabled="!isValid" @click="signIn">
					Sign in
				</n-button>
			</div>
		</div>
	</n-form>
</template>

<script lang="ts" setup>
import type { LoginPayload } from "@/types/auth.d"
import { useAuthStore } from "@/stores/auth"
import {
	type FormInst,
	type FormRules,
	type FormValidationError,
	NButton,
	NForm,
	NFormItem,
	NInput,
	useMessage
} from "naive-ui"
import { computed, ref, watch } from "vue"
import { useRouter } from "vue-router"

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
				.then(() => {
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
