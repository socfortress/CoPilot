<template>
	<n-form ref="formRef" :model="form" :rules="rules">
		<div class="flex flex-col gap-2">
			<n-form-item label="Access Key ID" path="access_key_id">
				<n-input v-model:value.trim="form.access_key_id" placeholder="Please insert Access Key ID" clearable />
			</n-form-item>
			<n-form-item label="Secret Access Key" path="secret_access_key">
				<n-input
					v-model:value.trim="form.secret_access_key"
					placeholder="Please insert Secret Access Key"
					type="password"
					show-password-on="click"
					clearable
				/>
			</n-form-item>
		</div>
	</n-form>
</template>

<script setup lang="ts">
import type { FormInst, FormRules } from "naive-ui"
import type { ScoutSuiteAwsReportPayload } from "@/types/cloudSecurityAssessment.d"
import { NForm, NFormItem, NInput } from "naive-ui"
import { computed, onMounted, ref, watch } from "vue"

const emit = defineEmits<{
	(e: "mounted", value: FormInst): void
	(e: "model", value: Partial<ScoutSuiteAwsReportPayload>): void
	(e: "valid", value: boolean): void
}>()

const form = ref<Partial<ScoutSuiteAwsReportPayload>>({
	access_key_id: "",
	secret_access_key: ""
})
const formRef = ref<FormInst>()

const rules: FormRules = {
	access_key_id: {
		required: true,
		message: "Please input the Access Key ID",
		trigger: ["input", "blur"]
	},
	secret_access_key: {
		required: true,
		message: "Please input the Secret Access Key",
		trigger: ["input", "blur"]
	}
}

const isValid = computed(() => {
	if (!form.value.access_key_id) return false
	if (!form.value.secret_access_key) return false
	return true
})

watch(form, val => emit("model", val), { deep: true, immediate: true })

watch(isValid, val => emit("valid", val), { immediate: true })

onMounted(() => {
	if (formRef.value) {
		emit("mounted", formRef.value)
	}
})
</script>
