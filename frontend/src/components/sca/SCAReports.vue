<template>
	<div class="flex flex-col gap-4">
		<div class="flex items-center justify-between gap-4">
			<div class="flex flex-col gap-1">
				<h2 class="text-2xl font-bold">SCA Reports</h2>
				<p class="text-secondary">Generate, manage, and download Security Configuration Assessment reports</p>
			</div>
			<n-button type="primary" size="large" @click="showGenerateModal = true">
				<template #icon>
					<Icon :name="AddIcon" />
				</template>
				Generate Report
			</n-button>
		</div>

		<n-select
			v-model:value="filterCustomerCode"
			:options="customerOptions"
			placeholder="Filter by Customer"
			clearable
			filterable
			@update:value="onFilterChange"
		/>

		<n-spin :show="loading">
			<div v-if="reports.length" class="flex flex-col gap-4">
				<div class="flex flex-col gap-3">
					<SCAReportCard
						v-for="report in paginatedReports"
						:key="report.id"
						:report
						@download="handleDownload(report)"
						@delete="handleDeleteClick(report)"
					/>
				</div>

				<div v-if="reports.length > pageSize" class="flex justify-end">
					<n-pagination
						v-model:page="currentPage"
						v-model:page-size="pageSize"
						:item-count="reports.length"
						:page-sizes="[10, 20, 50, 100]"
						show-size-picker
					/>
				</div>
			</div>

			<n-empty v-else description="No SCA reports found" class="min-h-48 justify-center" />
		</n-spin>

		<n-modal v-model:show="showGenerateModal" preset="card" title="Generate SCA Report" class="max-w-160!" closable>
			<GenerateReportForm
				:customers
				:loading="generating"
				@generate="handleGenerateReport"
				@cancel="showGenerateModal = false"
			/>
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
			<p>Are you sure you want to delete the report "{{ reportToDelete?.report_name }}"?</p>
			<p class="text-secondary mt-2">This action cannot be undone.</p>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { Customer } from "@/types/customers"
import type { SCAReport, SCAReportGenerateRequest } from "@/types/sca"
import { saveAs } from "file-saver"
import { NButton, NEmpty, NModal, NPagination, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import GenerateReportForm from "./GenerateReportForm.vue"
import SCAReportCard from "./SCAReportCard.vue"

const AddIcon = "carbon:document-add"

const message = useMessage()

const loading = ref(false)
const generating = ref(false)
const reports = ref<SCAReport[]>([])
const showGenerateModal = ref(false)
const showDeleteModal = ref(false)
const reportToDelete = ref<SCAReport | null>(null)
const filterCustomerCode = ref<string | null>(null)
const customers = ref<Array<{ label: string; value: string }>>([])
const currentPage = ref(1)
const pageSize = ref(20)

const customerOptions = computed(() => [...customers.value])

const paginatedReports = computed(() => {
	const start = (currentPage.value - 1) * pageSize.value
	return reports.value.slice(start, start + pageSize.value)
})

function onFilterChange() {
	currentPage.value = 1
	loadReports()
}

watch(pageSize, () => {
	currentPage.value = 1
})

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
		message.error(getApiErrorMessage(error as ApiError) || "Failed to load reports")
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
		message.error(getApiErrorMessage(error as ApiError) || "Failed to generate report")
	} finally {
		generating.value = false
	}
}

async function handleDownload(report: SCAReport) {
	try {
		const response = await Api.sca.downloadReport(report.id)

		saveAs(new Blob([response.data]), report.file_name)

		message.success("Report downloaded successfully")
	} catch (error: any) {
		message.error(getApiErrorMessage(error as ApiError) || "Failed to download report")
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
		message.error(getApiErrorMessage(error as ApiError) || "Failed to delete report")
	} finally {
		showDeleteModal.value = false
		reportToDelete.value = null
	}
}

onBeforeMount(() => {
	loadReports()
	loadCustomers()
})
</script>
