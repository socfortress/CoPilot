<template>
	<n-form ref="formRef" :model="model" :rules="rules">
		<n-form-item path="email" label="Email" first>
			<n-input
				v-model:value="model.email"
				placeholder="Input your email"
				size="large"
				@keydown.enter="forgotPassword"
			/>
		</n-form-item>
		<div class="flex flex-col items-end gap-6">
			<div class="w-full">
				<n-button type="primary" class="!w-full" size="large" :disabled="!isValid" @click="forgotPassword">
					Send Reset Link
				</n-button>
			</div>
		</div>
	</n-form>
</template>

<script lang="ts" setup>
import type { FormInst, FormItemRule, FormRules, FormValidationError } from "naive-ui"
import { NButton, NForm, NFormItem, NInput, useMessage } from "naive-ui"
import isEmail from "validator/es/lib/isEmail"
import { computed, ref, watch } from "vue"

interface ModelType {
	email: string | null
}

const formRef = ref<FormInst | null>(null)
const message = useMessage()
const model = ref<ModelType>({
	email: null
})

const rules: FormRules = {
	email: [
		{
			required: true,
			trigger: ["blur"],
			message: "The email is mandatory"
		},
		{
			validator: (_rule: FormItemRule, value: string): boolean => {
				return isEmail(value)
			},
			message: "The email is not formatted correctly",
			trigger: ["blur"]
		}
	]
}

const isValid = computed(() => {
	return isEmail(model.value.email || "")
})

function forgotPassword(e: Event) {
	e.preventDefault()
	formRef.value?.validate((errors: Array<FormValidationError> | undefined) => {
		if (!errors) {
			message.success("Reset Link sent")
		}
	})
}

watch(isValid, val => {
	if (val) {
		formRef.value?.validate()
	}
})
</script>
