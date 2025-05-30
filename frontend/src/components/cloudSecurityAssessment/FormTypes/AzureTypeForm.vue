<template>
	<n-form ref="formRef" :model="form" :rules="rules">
		<div class="flex flex-col gap-2">
			<n-form-item label="Username" path="username">
				<n-input v-model:value.trim="form.username" placeholder="Please insert Username" clearable />
			</n-form-item>
			<n-form-item label="Password" path="password">
				<n-input
					v-model:value.trim="form.password"
					placeholder="Please insert Password"
					type="password"
					show-password-on="click"
					clearable
				/>
			</n-form-item>
			<n-form-item label="Tenant ID" path="tenant_id">
				<n-input v-model:value.trim="form.tenant_id" placeholder="Please insert Tenant ID" clearable />
			</n-form-item>

			<p class="text-center">ScoutSuite for Azure must be ran with a user where MFA is disabled</p>
		</div>
	</n-form>
</template>

<script setup lang="ts">
import type { FormInst, FormRules } from "naive-ui"
import type { ScoutSuiteAzureReportPayload } from "@/types/cloudSecurityAssessment.d"
import { NForm, NFormItem, NInput } from "naive-ui"
import { computed, onMounted, ref, watch } from "vue"

const emit = defineEmits<{
	(e: "mounted", value: FormInst): void
	(e: "model", value: Partial<ScoutSuiteAzureReportPayload>): void
	(e: "valid", value: boolean): void
}>()

const form = ref<Partial<ScoutSuiteAzureReportPayload>>({
	username: "",
	password: "",
	tenant_id: ""
})
const formRef = ref<FormInst>()

const rules: FormRules = {
	username: {
		required: true,
		message: "Please input the Username",
		trigger: ["input", "blur"]
	},
	password: {
		required: true,
		message: "Please input the Password",
		trigger: ["input", "blur"]
	},
	tenant_id: {
		required: true,
		message: "Please input the Tenant ID",
		trigger: ["input", "blur"]
	}
}

const isValid = computed(() => {
	if (!form.value.username) return false
	if (!form.value.password) return false
	if (!form.value.tenant_id) return false
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
