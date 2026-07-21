<template>
	<n-form ref="formRef" :model="formData" :rules label-placement="top">
		<n-form-item label="Report Name" path="report_name">
			<n-input v-model:value="formData.report_name" placeholder="Leave empty for auto-generated name" clearable />
		</n-form-item>

		<n-form-item label="Time Range" path="range">
			<n-select v-model:value="formData.range" :options="rangeOptions" />
		</n-form-item>

		<n-form-item v-if="formData.range === 'custom'" label="Custom Date Range" path="customRange">
			<n-date-picker
				v-model:value="formData.customRange"
				type="daterange"
				clearable
				class="w-full"
			/>
		</n-form-item>

		<n-form-item label="Visible to customer" path="visibleToCustomer">
			<div class="flex items-center gap-2">
				<n-switch v-model:value="formData.visibleToCustomer" />
				<span class="text-secondary text-xs">
					{{ formData.visibleToCustomer ? "The customer will see this report in their portal" : "Hidden from the customer portal (you can share it later)" }}
				</span>
			</div>
		</n-form-item>

		<div class="text-secondary text-xs">Customer: <span class="font-mono">{{ customerCode }}</span></div>

		<div class="mt-6 flex justify-end gap-3">
			<n-button @click="$emit('cancel')">Cancel</n-button>
			<n-button type="primary" :loading @click="handleSubmit">Generate Report</n-button>
		</div>
	</n-form>
</template>

<script setup lang="ts">
import type { FormInst, FormRules } from "naive-ui"
import type { ApiError } from "@/types/common"
import type { IncidentCustomerReportGenerateRequest } from "@/types/incidentReports"
import { NButton, NDatePicker, NForm, NFormItem, NInput, NSelect, NSwitch, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"

const props = defineProps<{
	customerCode: string
}>()

const emit = defineEmits<{
	(e: "generated", reportId: number): void
	(e: "cancel"): void
}>()

const message = useMessage()

const formRef = ref<FormInst | null>(null)
const generating = ref(false)
const formData = ref<{
	report_name?: string
	range: "30d" | "90d" | "custom"
	customRange: [number, number] | null
	visibleToCustomer: boolean
}>({
	report_name: undefined,
	range: "30d",
	customRange: null,
	visibleToCustomer: false
})

const loading = computed(() => generating.value)

const rangeOptions = [
	{ label: "Last 30 days", value: "30d" },
	{ label: "Last 3 months", value: "90d" },
	{ label: "Custom range", value: "custom" }
]

const rules: FormRules = {
	customRange: [
		{
			validator: () => {
				if (formData.value.range === "custom" && !formData.value.customRange) {
					return new Error("Please select a date range")
				}
				return true
			},
			trigger: ["change", "blur"]
		}
	]
}

/** Format a Date as a naive UTC "YYYY-MM-DDTHH:mm:ss" string (DB timestamps are UTC). */
function toUtcNaive(date: Date): string {
	return date.toISOString().slice(0, 19)
}

function resolveRange(): { date_from: string; date_to: string } {
	if (formData.value.range === "custom" && formData.value.customRange) {
		const [start, end] = formData.value.customRange
		const from = new Date(start)
		const to = new Date(end)
		to.setHours(23, 59, 59, 999)
		return { date_from: toUtcNaive(from), date_to: toUtcNaive(to) }
	}
	const to = new Date()
	const from = new Date()
	from.setDate(from.getDate() - (formData.value.range === "90d" ? 90 : 30))
	return { date_from: toUtcNaive(from), date_to: toUtcNaive(to) }
}

async function handleSubmit() {
	if (!formRef.value) return

	try {
		await formRef.value.validate()

		const { date_from, date_to } = resolveRange()
		const request: IncidentCustomerReportGenerateRequest = {
			customer_code: props.customerCode,
			date_from,
			date_to,
			visible_to_customer: formData.value.visibleToCustomer
		}
		if (formData.value.report_name?.trim()) {
			request.report_name = formData.value.report_name.trim()
		}

		generating.value = true
		try {
			const response = await Api.incidentReports.generateReportBackground(request)

			if (response.data.success) {
				message.success(response.data.message)
				emit("generated", response.data.report_id)
			} else {
				message.error("Failed to queue report generation")
			}
		} catch (error) {
			message.error(getApiErrorMessage(error as ApiError) || "Failed to generate report")
		} finally {
			generating.value = false
		}
	} catch (error) {
		console.error("Form validation failed:", error)
	}
}
</script>
