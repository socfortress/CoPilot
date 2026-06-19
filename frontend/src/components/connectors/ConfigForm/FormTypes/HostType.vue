<template>
	<n-form ref="formRef" :model="form" :rules label-width="120px" label-placement="top">
		<n-form-item label="Connector URL" path="connector_url">
			<n-input v-model:value="form.connector_url" required type="text" />
		</n-form-item>
	</n-form>
</template>

<script setup lang="ts">
import type { FormInst, FormItemRule, FormRules } from "naive-ui"
import { NForm, NFormItem, NInput } from "naive-ui"
import isURL from "validator/es/lib/isURL"
import { ref, toRefs } from "vue"

export interface IHostForm {
	connector_url: string
}

const props = defineProps<{
	form: IHostForm
}>()

const { form } = toRefs(props)

const formRef = ref<FormInst>()

function validateUrl(_rule: FormItemRule, value: string) {
	if (!value) {
		return new Error("Please input a valid URL")
	}
	if (!isURL(value, { require_tld: false })) {
		return new Error("Please input a valid URL")
	}

	return true
}

const rules: FormRules = {
	connector_url: [{ required: true, validator: validateUrl, trigger: "blur" }]
}

defineExpose({
	formRef
})
</script>
