<template>
	<div class="flex flex-col gap-4">
		<div class="flex items-center justify-between gap-4">
			<div class="flex flex-col gap-1">
				<h3 class="text-lg font-bold">Incident Management Reports</h3>
				<p class="text-secondary text-sm">
					Generate and download aggregated PDF reports of alerts and cases for this customer
				</p>
			</div>
			<GenerateIncidentReportButton :customer-code @generated="handleReportGenerated" />
		</div>

		<n-spin :show="loading">
			<div v-if="reports.length" class="flex flex-col gap-4">
				<div class="flex flex-col gap-3">
					<IncidentReportCard
						v-for="report in paginatedReports"
						:key="report.id"
						:report
						:loading-visibility="visibilityLoadingId === report.id"
						:loading="deletingId === report.id"
						@download="handleDownload(report)"
						@delete="handleDeleteClick(report)"
						@toggle-visibility="handleToggleVisibility(report, $event)"
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

			<n-empty v-else description="No reports generated yet" class="min-h-48 justify-center" />
		</n-spin>

		<n-modal
			v-model:show="showDeleteModal"
			preset="dialog"
			title="Delete Report"
			positive-text="Delete"
			negative-text="Cancel"
			@positive-click="handleDeleteConfirm"
			@negative-click="showDeleteModal = false"
		>
			<p>Are you sure you want to delete the report "{{ reportToDelete?.report_name }}"?</p>
			<p class="text-secondary mt-2">This action cannot be undone.</p>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { IncidentCustomerReport } from "@/types/incidentReports"
import axios from "axios"
import { saveAs } from "file-saver"
import { NEmpty, NModal, NPagination, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"
import GenerateIncidentReportButton from "./GenerateIncidentReportButton.vue"
import IncidentReportCard from "./IncidentReportCard.vue"

const { customerCode } = defineProps<{
	customerCode: string
}>()

const message = useMessage()

const loading = ref(false)
const reports = ref<IncidentCustomerReport[]>([])
const showDeleteModal = ref(false)
const reportToDelete = ref<IncidentCustomerReport | null>(null)
const currentPage = ref(1)
const pageSize = ref(20)
const visibilityLoadingId = ref<number | null>(null)
const deletingId = ref<number | null>(null)
let abortController: AbortController | null = null

const paginatedReports = computed(() => {
	const start = (currentPage.value - 1) * pageSize.value
	return reports.value.slice(start, start + pageSize.value)
})

watch(pageSize, () => {
	currentPage.value = 1
})

async function loadReports() {
	abortController?.abort()
	abortController = new AbortController()

	loading.value = true
	try {
		const response = await Api.incidentReports.listReports(customerCode, abortController.signal)
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

async function handleReportGenerated(reportId: number) {
	await loadReports()
	startStatusPolling(reportId)
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
					message.error(`Report "${report.report_name}" failed: ${report.error_message}`)
				}
			}
		} catch {
			clearInterval(pollInterval)
		}
	}, 3000)

	setTimeout(clearInterval, 300000, pollInterval)
}

async function handleDownload(report: IncidentCustomerReport) {
	try {
		const response = await Api.incidentReports.downloadReport(report.id)
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

async function handleToggleVisibility(report: IncidentCustomerReport, visible: boolean) {
	visibilityLoadingId.value = report.id
	try {
		const response = await Api.incidentReports.setVisibility(report.id, visible)
		if (response.data.success) {
			report.visible_to_customer = visible
			message.success(response.data.message)
		} else {
			message.error(response.data.message || "Failed to update visibility")
		}
	} catch (error) {
		message.error(getApiErrorMessage(error as ApiError) || "Failed to update visibility")
	} finally {
		visibilityLoadingId.value = null
	}
}

function handleDeleteConfirm() {
	// Close the confirmation immediately; the card itself shows the loading state.
	const report = reportToDelete.value
	showDeleteModal.value = false
	reportToDelete.value = null
	if (report) deleteReport(report)
}

async function deleteReport(report: IncidentCustomerReport) {
	deletingId.value = report.id
	try {
		const response = await Api.incidentReports.deleteReport(report.id)

		if (response.data.success) {
			message.success(response.data.message)
			await loadReports()
		} else {
			message.error("Failed to delete report")
		}
	} catch (error) {
		message.error(getApiErrorMessage(error as ApiError) || "Failed to delete report")
	} finally {
		deletingId.value = null
	}
}

onBeforeMount(() => {
	loadReports()
})
</script>
