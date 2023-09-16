<template>
	<n-form ref="formRef" :model="model" :rules="rules">
		<n-form-item path="email" label="Email">
			<n-input v-model:value="model.email" @keydown.enter="signUp" size="large" placeholder="Example@email.com" />
		</n-form-item>
		<n-form-item path="password" label="Password">
			<n-input
				v-model:value="model.password"
				type="password"
				@keydown.enter="signUp"
				size="large"
				show-password-on="click"
				placeholder="At least 8 characters"
			/>
		</n-form-item>
		<n-form-item path="confirmPassword" label="Confirm Password" first>
			<n-input
				v-model:value="model.confirmPassword"
				type="password"
				:disabled="!model.password"
				@keydown.enter="signUp"
				size="large"
				show-password-on="click"
				placeholder="At least 8 characters"
			/>
		</n-form-item>
		<div class="flex flex-col items-end">
			<div class="w-full">
				<n-button type="primary" @click="signUp" class="!w-full" size="large">Create an account</n-button>
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
	NButton,
	type FormItemRule
} from "naive-ui"
import { useAuthStore } from "@/stores/auth"
import { useRouter } from "vue-router"

interface ModelType {
	email: string | null
	password: string | null
	confirmPassword: string | null
}

const router = useRouter()
const formRef = ref<FormInst | null>(null)
const message = useMessage()
const model = ref<ModelType>({
	email: "admin@admin.com",
	password: "password",
	confirmPassword: "password"
})

const rules: FormRules = {
	email: [
		{
			required: true,
			trigger: ["blur"],
			message: "Email is required"
		}
	],
	password: [
		{
			required: true,
			trigger: ["blur"],
			message: "Password is required"
		}
	],
	confirmPassword: [
		{
			required: true,
			trigger: ["blur"],
			message: "confirmPassword is required"
		},
		{
			validator: (rule: FormItemRule, value: string): boolean => {
				return value === model.value.password
			},
			message: "Password is not same as re-entered password!",
			trigger: ["blur", "password-input"]
		}
	]
}

function signUp(e: Event) {
	e.preventDefault()
	formRef.value?.validate((errors: Array<FormValidationError> | undefined) => {
		if (!errors) {
			if (model.value.email === "admin@admin.com" && model.value.password === "password") {
				useAuthStore().setLogged()
				router.push({ path: "/", replace: true })
			} else {
				message.error("Invalid credentials")
			}
		} else {
			message.error("Invalid credentials")
		}
	})
}
</script>
