<template>
	<n-form :model="form" :rules="rules" label-width="120px" ref="formRef" label-placement="top">
		<n-form-item label="Connector URL" path="connector_url">
			<n-input v-model:value="form.connector_url" required type="text" />
		</n-form-item>
		<n-form-item label="API Key" path="connector_api_key">
			<n-input v-model:value="form.connector_api_key" required type="text" />
		</n-form-item>
	</n-form>
</template>

<script setup lang="ts">
import { onMounted, ref, toRefs } from "vue"
import isURL from "validator/es/lib/isURL"
import { NForm, NFormItem, NInput, type FormRules, type FormInst, type FormItemRule } from "naive-ui"

export interface ITokenForm {
	connector_url: string
	connector_api_key: string
}

const emit = defineEmits<{
	(e: "mounted", value: FormInst): void
}>()

const props = defineProps<{
	form: ITokenForm
}>()
const { form } = toRefs(props)

const formRef = ref<FormInst>()

const validateUrl = (rule: FormItemRule, value: string) => {
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
	connector_api_key: [{ required: true, message: "Please input a valid API Key", trigger: "blur" }]
}

onMounted(() => {
	if (formRef.value) {
		emit("mounted", formRef.value)
	}
})
</script>
