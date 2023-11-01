<template>
	<n-form ref="formRef" :model="model" :rules="rules">
		<n-form-item path="email" label="Email">
			<n-input
				v-model:value="model.email"
				@keydown.enter="forgotPassword"
				placeholder="Example@email.com"
				size="large"
			/>
		</n-form-item>
		<div class="flex flex-col items-end gap-6">
			<div class="w-full">
				<n-button type="primary" @click="forgotPassword" class="!w-full" size="large">Send Reset Link</n-button>
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

interface ModelType {
	email: string | null
}

const formRef = ref<FormInst | null>(null)
const message = useMessage()
const model = ref<ModelType>({
	email: ""
})

const rules: FormRules = {
	email: [
		{
			required: true,
			trigger: ["blur"],
			message: "Email is required"
		}
	]
}

function forgotPassword(e: Event) {
	e.preventDefault()
	formRef.value?.validate((errors: Array<FormValidationError> | undefined) => {
		if (!errors) {
			message.success("Reset Link sent")
		}
	})
}
</script>
