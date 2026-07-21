<template>
	<div class="flex flex-col gap-4">
		<div class="flex items-center justify-between gap-4">
			<div class="flex flex-col gap-1">
				<h2 class="text-xl font-bold">Reports</h2>
				<p class="text-secondary text-sm">Generate and download PDF activity reports for your organization</p>
			</div>
			<n-button type="primary" @click="showGenerateModal = true">
				<template #icon>
					<Icon :name="AddIcon" />
				</template>
				Generate Report
			</n-button>
		</div>

		<n-spin :show="loading">
			<div v-if="reports.length" class="grid grid-cols-1 gap-3 @2xl:grid-cols-2">
				<ReportCard
					v-for="report in reports"
					:key="report.id"
					:report
					@download="handleDownload(report)"
					@delete="handleDeleteClick(report)"
				/>
			</div>

			<n-empty v-else description="No reports generated yet" class="min-h-48 justify-center" />
		</n-spin>

		<n-modal
			v-model:show="showGenerateModal"
			preset="card"
			title="Generate Report"
			class="max-w-140!"
			display-directive="show"
			closable
		>
			<n-form ref="formRef" :model="formData" :rules label-placement="top">
				<n-form-item label="Report Name" path="report_name">
					<n-input
						v-model:value="formData.report_name"
						placeholder="Leave empty for auto-generated name"
						clearable
					/>
				</n-form-item>

				<n-form-item v-if="customerOptions.length > 1" label="Customer" path="customer_code" required>
					<n-select v-model:value="formData.customer_code" :options="customerOptions" filterable />
				</n-form-item>

				<n-form-item label="Time Range" path="range">
					<n-select v-model:value="formData.range" :options="rangeOptions" />
				</n-form-item>

				<n-form-item v-if="formData.range === 'custom'" label="Custom Date Range" path="customRange">
					<n-date-picker v-model:value="formData.customRange" type="daterange" clearable class="w-full" />
				</n-form-item>

				<div class="mt-6 flex justify-end gap-3">
					<n-button @click="showGenerateModal = false">Cancel</n-button>
					<n-button type="primary" :loading="generating" @click="handleGenerate">Generate Report</n-button>
				</div>
			</n-form>
		</n-modal>

		<n-modal
			v-model:show="showDeleteModal"
			preset="dialog"
			title="Delete Report"
			positive-text="Delete"
			negative-text="Cancel"
			@positive-click="confirmDelete"
			@negative-click="showDeleteModal = false"
		>
			<p>Are you sure you want to delete "{{ reportToDelete?.report_name }}"?</p>
			<p class="text-secondary mt-2">This action cannot be undone.</p>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { FormInst, FormRules } from "naive-ui"
import type { ApiError } from "@/types/common"
import type { IncidentCustomerReport, IncidentCustomerReportGenerateRequest } from "@/types/reports"
import axios from "axios"
import { saveAs } from "file-saver"
import { NButton, NDatePicker, NEmpty, NForm, NFormItem, NInput, NModal, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import ReportCard from "@/components/reports/ReportCard.vue"
import { useAuthStore } from "@/stores/auth"
import { getApiErrorMessage } from "@/utils"

const AddIcon = "carbon:document-add"

const message = useMessage()
const authStore = useAuthStore()

const loading = ref(false)
const generating = ref(false)
const reports = ref<IncidentCustomerReport[]>([])
const showGenerateModal = ref(false)
const showDeleteModal = ref(false)
const reportToDelete = ref<IncidentCustomerReport | null>(null)
const formRef = ref<FormInst | null>(null)
let abortController: AbortController | null = null

const customerOptions = computed(() => authStore.accessibleCustomerCodes.map(code => ({ label: code, value: code })))

const formData = ref<{
	report_name?: string
	customer_code: string | null
	range: "30d" | "90d" | "custom"
	customRange: [number, number] | null
}>({
	report_name: undefined,
	customer_code: authStore.userCustomerCode,
	range: "30d",
	customRange: null
})

const rangeOptions = [
	{ label: "Last 30 days", value: "30d" },
	{ label: "Last 3 months", value: "90d" },
	{ label: "Custom range", value: "custom" }
]

const rules: FormRules = {
	customer_code: [{ required: true, message: "Please select a customer", trigger: ["blur", "change"] }],
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

async function loadReports() {
	abortController?.abort()
	abortController = new AbortController()

	loading.value = true
	try {
		const response = await Api.reports.listReports(abortController.signal)
		if (response.data.success) {
			reports.value = response.data.reports
		} else {
			message.error(response.data.message || "Failed to load reports")
		}
		loading.value = false
	} catch (error) {
		if (!axios.isCancel(error)) {
			message.error(getApiErrorMessage(error as ApiError) || "Failed to load reports")
			loading.value = false
		}
	}
}

function startStatusPolling(reportId: number) {
	const pollInterval = setInterval(async () => {
		try {
			await loadReports()
			const report = reports.value.find(r => r.id === reportId)
			if (report && report.status !== "processing") {
				clearInterval(pollInterval)
				if (report.status === "completed") {
					message.success(`Report "${report.report_name}" completed successfully`)
				} else if (report.status === "failed") {
					message.error(`Report "${report.report_name}" failed`)
				}
			}
		} catch {
			clearInterval(pollInterval)
		}
	}, 3000)

	setTimeout(clearInterval, 300000, pollInterval)
}

async function handleGenerate() {
	if (!formRef.value) return
	try {
		await formRef.value.validate()
	} catch {
		return
	}

	const customerCode = formData.value.customer_code || authStore.userCustomerCode
	if (!customerCode) {
		message.error("No customer available for report generation")
		return
	}

	const { date_from, date_to } = resolveRange()
	const request: IncidentCustomerReportGenerateRequest = { customer_code: customerCode, date_from, date_to }
	if (formData.value.report_name?.trim()) {
		request.report_name = formData.value.report_name.trim()
	}

	generating.value = true
	try {
		const response = await Api.reports.generateReportBackground(request)
		if (response.data.success) {
			message.success(response.data.message)
			showGenerateModal.value = false
			await loadReports()
			startStatusPolling(response.data.report_id)
		} else {
			message.error("Failed to queue report generation")
		}
	} catch (error) {
		message.error(getApiErrorMessage(error as ApiError) || "Failed to generate report")
	} finally {
		generating.value = false
	}
}

async function handleDownload(report: IncidentCustomerReport) {
	try {
		const response = await Api.reports.downloadReport(report.id)
		saveAs(new Blob([response.data]), report.file_name)
		message.success("Report downloaded successfully")
	} catch (error) {
		message.error(getApiErrorMessage(error as ApiError) || "Failed to download report")
	}
}

function handleDeleteClick(report: IncidentCustomerReport) {
	reportToDelete.value = report
	showDeleteModal.value = true
}

async function confirmDelete() {
	if (!reportToDelete.value) return
	try {
		const response = await Api.reports.deleteReport(reportToDelete.value.id)
		if (response.data.success) {
			message.success(response.data.message)
			await loadReports()
		} else {
			message.error("Failed to delete report")
		}
	} catch (error) {
		message.error(getApiErrorMessage(error as ApiError) || "Failed to delete report")
	} finally {
		showDeleteModal.value = false
		reportToDelete.value = null
	}
}

onBeforeMount(() => {
	loadReports()
})
</script>
