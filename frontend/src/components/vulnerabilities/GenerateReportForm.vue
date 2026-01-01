<template>
	<n-form ref="formRef" :model="formData" :rules="rules" label-placement="top">
		<n-form-item label="Report Name" path="report_name">
			<n-input
				v-model:value="formData.report_name"
				placeholder="Leave empty for auto-generated name"
				clearable
			/>
		</n-form-item>

		<n-form-item label="Customer" path="customer_code" required>
			<n-select
				v-model:value="formData.customer_code"
				:options="customers"
				placeholder="Select customer"
				filterable
			/>
		</n-form-item>

		<n-divider>Optional Filters</n-divider>

		<n-form-item label="Agent Name" path="agent_name">
			<n-input v-model:value="formData.agent_name" placeholder="Filter by agent hostname" clearable />
		</n-form-item>

		<n-form-item label="Severity" path="severity">
			<n-select
				v-model:value="formData.severity"
				:options="severityOptions"
				placeholder="Filter by severity"
				clearable
			/>
		</n-form-item>

		<n-form-item label="CVE ID" path="cve_id">
			<n-input v-model:value="formData.cve_id" placeholder="Filter by CVE ID" clearable />
		</n-form-item>

		<n-form-item label="Package Name" path="package_name">
			<n-input v-model:value="formData.package_name" placeholder="Filter by package name" clearable />
		</n-form-item>

		<n-form-item label="Include EPSS Scores" path="include_epss">
			<n-switch v-model:value="formData.include_epss">
				<template #checked>Enabled</template>
				<template #unchecked>Disabled</template>
			</n-switch>
		</n-form-item>

		<div class="flex justify-end gap-3 mt-6">
			<n-button @click="$emit('cancel')">Cancel</n-button>
			<n-button type="primary" :loading="loading" @click="handleSubmit">Generate Report</n-button>
		</div>
	</n-form>
</template>

<script setup lang="ts">
import type { FormInst, FormRules } from "naive-ui"
import type { VulnerabilityReportGenerateRequest } from "@/types/vulnerabilities.d"
import { NButton, NDivider, NForm, NFormItem, NInput, NSelect, NSwitch } from "naive-ui"
import { ref } from "vue"
import { VulnerabilitySeverity } from "@/types/vulnerabilities.d"

interface Props {
    customers: Array<{ label: string; value: string }>
    loading?: boolean
}

defineProps<Props>()

const emit = defineEmits<{
    (e: "generate", value: VulnerabilityReportGenerateRequest): void
    (e: "cancel"): void
}>()

const formRef = ref<FormInst | null>(null)
const formData = ref<VulnerabilityReportGenerateRequest>({
    customer_code: "",
    report_name: "",
    agent_name: "",
    severity: undefined,
    cve_id: "",
    package_name: "",
    include_epss: false
})

const severityOptions = [
    { label: "Critical", value: VulnerabilitySeverity.Critical },
    { label: "High", value: VulnerabilitySeverity.High },
    { label: "Medium", value: VulnerabilitySeverity.Medium },
    { label: "Low", value: VulnerabilitySeverity.Low }
]

const rules: FormRules = {
    customer_code: [
        {
            required: true,
            message: "Please select a customer",
            trigger: ["blur", "change"]
        }
    ]
}

async function handleSubmit() {
    if (!formRef.value) return

    try {
        await formRef.value.validate()

        // Clean up empty strings
        const request: VulnerabilityReportGenerateRequest = {
            customer_code: formData.value.customer_code,
            include_epss: formData.value.include_epss
        }

        if (formData.value.report_name?.trim()) {
            request.report_name = formData.value.report_name.trim()
        }
        if (formData.value.agent_name?.trim()) {
            request.agent_name = formData.value.agent_name.trim()
        }
        if (formData.value.severity) {
            request.severity = formData.value.severity
        }
        if (formData.value.cve_id?.trim()) {
            request.cve_id = formData.value.cve_id.trim()
        }
        if (formData.value.package_name?.trim()) {
            request.package_name = formData.value.package_name.trim()
        }

        emit("generate", request)
    } catch (error) {
        console.error("Form validation failed:", error)
    }
}
</script>
