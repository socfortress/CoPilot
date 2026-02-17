<template>
	<div class="sca-reports">
		<div class="header mb-6 flex items-center justify-between">
			<div>
				<h2 class="mb-2 text-2xl font-bold">SCA Reports</h2>
				<p class="text-secondary">Generate, manage, and download Security Configuration Assessment reports</p>
			</div>
			<n-button type="primary" size="large" @click="showGenerateModal = true">
				<template #icon>
					<Icon :name="AddIcon" />
				</template>
				Generate Report
			</n-button>
		</div>

		<!-- Filters -->
		<n-card class="mb-6">
			<div class="flex gap-4">
				<n-select
					v-model:value="filterCustomerCode"
					:options="customerOptions"
					placeholder="Filter by Customer"
					clearable
					filterable
					class="flex-1"
					@update:value="loadReports"
				/>
				<n-button :loading="loading" @click="loadReports">
					<template #icon>
						<Icon :name="RefreshIcon" />
					</template>
					Refresh
				</n-button>
			</div>
		</n-card>

		<!-- Reports Table -->
		<n-card>
			<n-data-table
				:columns="columns"
				:data="reports"
				:loading="loading"
				:pagination="pagination"
				:row-key="(row: SCAReport) => row.id"
			/>
		</n-card>

		<!-- Generate Report Modal -->
		<n-modal
			v-model:show="showGenerateModal"
			preset="card"
			title="Generate SCA Report"
			style="width: 600px; max-width: 90vw"
			:closable="true"
		>
			<GenerateReportForm
				:customers="customers"
				:loading="generating"
				@generate="handleGenerateReport"
				@cancel="showGenerateModal = false"
			/>
		</n-modal>

		<!-- Delete Confirmation Modal -->
		<n-modal
			v-model:show="showDeleteModal"
			preset="dialog"
			title="Delete Report"
			positive-text="Delete"
			negative-text="Cancel"
			@positive-click="confirmDelete"
			@negative-click="showDeleteModal = false"
		>
			<p>Are you sure you want to delete the report "{{ reportToDelete?.report_name }}"?</p>
			<p class="text-secondary mt-2">This action cannot be undone.</p>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
// TODO: refactor
import type { DataTableColumns } from "naive-ui"
import type { Customer } from "@/types/customers"
import type { SCAReport, SCAReportGenerateRequest } from "@/types/sca.d"
import { NButton, NCard, NDataTable, NModal, NSelect, NSpace, NTag, NTooltip, useMessage } from "naive-ui"
import { computed, h, onMounted, ref } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatBytes, formatDate } from "@/utils/format"
import GenerateReportForm from "./GenerateReportForm.vue"

const AddIcon = "carbon:document-add"
const RefreshIcon = "carbon:renew"
const DownloadIcon = "carbon:download"
const DeleteIcon = "carbon:trash-can"
const CheckIcon = "carbon:checkmark-filled"
const ErrorIcon = "carbon:warning-filled"
const LoadingIcon = "eos-icons:loading"

const message = useMessage()
const dFormats = useSettingsStore().dateFormat

const loading = ref(false)
const generating = ref(false)
const reports = ref<SCAReport[]>([])
const showGenerateModal = ref(false)
const showDeleteModal = ref(false)
const reportToDelete = ref<SCAReport | null>(null)
const filterCustomerCode = ref<string | null>(null)
const customers = ref<Array<{ label: string; value: string }>>([])

const customerOptions = computed(() => [...customers.value])

const pagination = {
	pageSize: 20,
	showSizePicker: true,
	pageSizes: [10, 20, 50, 100]
}

const columns: DataTableColumns<SCAReport> = [
	{
		title: "Report Name",
		key: "report_name",
		ellipsis: {
			tooltip: true
		}
	},
	{
		title: "Customer",
		key: "customer_code",
		width: 120
	},
	{
		title: "Status",
		key: "status",
		width: 120,
		render: (row: SCAReport) => {
			const statusMap = {
				completed: { type: "success", icon: CheckIcon, text: "Completed" },
				processing: { type: "warning", icon: LoadingIcon, text: "Processing" },
				failed: { type: "error", icon: ErrorIcon, text: "Failed" }
			}
			const status = statusMap[row.status]
			return h(
				NTag,
				{ type: status.type as any, size: "small" },
				{
					default: () => status.text,
					icon: () => h(Icon, { name: status.icon, size: 14 })
				}
			)
		}
	},
	{
		title: "Policies",
		key: "total_policies",
		width: 100,
		render: (row: SCAReport) => row.total_policies.toLocaleString()
	},
	{
		title: "Checks",
		key: "total_checks",
		width: 140,
		render: (row: SCAReport) => {
			return h(
				NTooltip,
				{},
				{
					trigger: () => row.total_checks.toLocaleString(),
					default: () =>
						h("div", {}, [
							h("div", {}, `Passed: ${row.passed_count}`),
							h("div", {}, `Failed: ${row.failed_count}`),
							h("div", {}, `Invalid: ${row.invalid_count}`)
						])
				}
			)
		}
	},
	{
		title: "File Size",
		key: "file_size",
		width: 120,
		render: (row: SCAReport) => formatBytes(row.file_size)
	},
	{
		title: "Generated",
		key: "generated_at",
		width: 180,
		render: (row: SCAReport) => `${formatDate(row.generated_at, dFormats.datetime)}`
	},
	{
		title: "Actions",
		key: "actions",
		width: 140,
		render: (row: SCAReport) => {
			return h(
				NSpace,
				{ size: "small" },
				{
					default: () => [
						row.status === "completed"
							? h(
									NButton,
									{
										size: "small",
										type: "primary",
										onClick: () => handleDownload(row)
									},
									{
										icon: () => h(Icon, { name: DownloadIcon })
									}
								)
							: null,
						h(
							NButton,
							{
								size: "small",
								type: "error",
								onClick: () => handleDeleteClick(row)
							},
							{
								icon: () => h(Icon, { name: DeleteIcon })
							}
						)
					]
				}
			)
		}
	}
]

async function loadReports() {
	loading.value = true
	try {
		const response = await Api.sca.listReports(filterCustomerCode.value || undefined)
		if (response.data.success) {
			reports.value = response.data.reports
		} else {
			message.error(response.data.message || "Failed to load reports")
		}
	} catch (error: any) {
		message.error(error?.response?.data?.detail || "Failed to load reports")
	} finally {
		loading.value = false
	}
}

async function loadCustomers() {
	try {
		const response = await Api.customers.getCustomers()
		const customerData = response.data.customers || []

		customers.value = customerData.map((c: Customer) => ({
			label: `${c.customer_name} (${c.customer_code})`,
			value: c.customer_code
		}))
	} catch (error: any) {
		console.error("Failed to load customers:", error)
		message.error("Failed to load customers list")
	}
}

async function handleGenerateReport(request: SCAReportGenerateRequest) {
	generating.value = true
	try {
		const response = await Api.sca.generateReport(request)

		if (response.data.success) {
			message.success(response.data.message)
			showGenerateModal.value = false
			await loadReports()
		} else {
			message.error(response.data.error || "Failed to generate report")
		}
	} catch (error: any) {
		message.error(error?.response?.data?.detail || "Failed to generate report")
	} finally {
		generating.value = false
	}
}

async function handleDownload(report: SCAReport) {
	try {
		const response = await Api.sca.downloadReport(report.id)

		const url = window.URL.createObjectURL(new Blob([response.data]))
		const link = document.createElement("a")
		link.href = url
		link.setAttribute("download", report.file_name)
		document.body.appendChild(link)
		link.click()
		link.remove()
		window.URL.revokeObjectURL(url)

		message.success("Report downloaded successfully")
	} catch (error: any) {
		message.error(error?.response?.data?.detail || "Failed to download report")
	}
}

function handleDeleteClick(report: SCAReport) {
	reportToDelete.value = report
	showDeleteModal.value = true
}

async function confirmDelete() {
	if (!reportToDelete.value) return

	try {
		const response = await Api.sca.deleteReport(reportToDelete.value.id)

		if (response.data.success) {
			message.success(response.data.message)
			await loadReports()
		} else {
			message.error("Failed to delete report")
		}
	} catch (error: any) {
		message.error(error?.response?.data?.detail || "Failed to delete report")
	} finally {
		showDeleteModal.value = false
		reportToDelete.value = null
	}
}

onMounted(() => {
	loadReports()
	loadCustomers()
})
</script>

<style scoped>
.sca-reports {
	padding: 20px;
}
</style>
