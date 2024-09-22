<template>
	<n-form ref="formRef" :model="form" :rules="rules" label-width="120px" label-placement="top">
		<n-form-item label="Connector URL" path="connector_url">
			<n-input v-model:value="form.connector_url" required type="text" />
		</n-form-item>
		<n-form-item label="Username" path="connector_username">
			<n-input v-model:value="form.connector_username" required type="text" />
		</n-form-item>
		<n-form-item label="Password" path="connector_password">
			<n-input
				v-model:value="form.connector_password"
				required
				type="password"
				show-password-on="click"
				autocomplete="off"
			/>
		</n-form-item>
	</n-form>
</template>

<script setup lang="ts">
import { type FormInst, type FormItemRule, type FormRules, NForm, NFormItem, NInput } from "naive-ui"
import isURL from "validator/es/lib/isURL"
import { onMounted, ref, toRefs } from "vue"

export interface ICredentialsForm {
	connector_url: string
	connector_username: string
	connector_password: string
}

const props = defineProps<{
	form: ICredentialsForm
}>()

const emit = defineEmits<{
	(e: "mounted", value: FormInst): void
}>()

const { form } = toRefs(props)

const formRef = ref<FormInst>()

function validateUrl(rule: FormItemRule, value: string) {
	if (!value) {
		return new Error("Please input a valid URL")
	}
	if (!isURL(value, { require_tld: false })) {
		return new Error("Please input a valid URL")
	}

	return true
}

const rules: FormRules = {
	connector_url: [{ required: true, validator: validateUrl, trigger: "blur" }],
	connector_username: [{ required: true, message: "Please input a valid Username", trigger: "blur" }],
	connector_password: [{ required: true, message: "Please input a valid Password", trigger: "blur" }]
}

onMounted(() => {
	if (formRef.value) {
		emit("mounted", formRef.value)
	}
})
</script>
