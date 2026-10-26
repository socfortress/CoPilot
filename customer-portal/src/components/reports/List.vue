<template>
	<div class="flex flex-col gap-4">
		<div class="flex items-center justify-between gap-4">
			<div class="flex flex-col gap-1">
				<h2 class="text-xl font-bold">{{ $t("reports.list.title") }}</h2>
				<p class="text-secondary text-sm">{{ $t("reports.list.subtitle") }}</p>
			</div>
			<n-button type="primary" data-testid="generate-report-button" @click="openGenerateModal()">
				<template #icon>
					<Icon :name="AddIcon" />
				</template>
				{{ $t("reports.list.generate") }}
			</n-button>
		</div>

		<n-spin :show="loading">
			<div v-if="reports.length" class="grid grid-cols-1 gap-3 @2xl:grid-cols-2">
				<ReportCard
					v-for="report in reports"
					:key="report.id"
					data-testid="report-card"
					:report
					@download="handleDownload(report)"
					@delete="handleDeleteClick(report)"
				/>
			</div>

			<n-empty v-else :description="$t('reports.list.empty')" class="min-h-48 justify-center" />
		</n-spin>

		<n-modal
			v-model:show="showGenerateModal"
			preset="card"
			:title="$t('reports.list.generate')"
			class="max-w-140!"
			display-directive="show"
			closable
		>
			<n-form ref="formRef" :model="formData" :rules label-placement="top">
				<n-form-item :label="$t('reports.form.reportName')" path="report_name">
					<n-input
						v-model:value="formData.report_name"
						data-testid="report-name"
						:placeholder="$t('reports.form.reportNamePlaceholder')"
						clearable
					/>
				</n-form-item>

				<n-form-item
					v-if="hasMultipleCustomers"
					:label="$t('common.fields.customer')"
					path="customer_code"
					required
				>
					<n-select
						v-model:value="formData.customer_code"
						data-testid="report-customer"
						:options="customerOptions"
						:render-label="renderCustomerLabel"
						:filter="filterCustomer"
						filterable
					/>
				</n-form-item>

				<n-form-item :label="$t('reports.form.timeRange')" path="range">
					<n-select v-model:value="formData.range" :options="rangeOptions" />
				</n-form-item>

				<n-form-item
					v-if="formData.range === 'custom'"
					:label="$t('reports.form.customRange')"
					path="customRange"
				>
					<n-date-picker v-model:value="formData.customRange" type="daterange" clearable class="w-full" />
				</n-form-item>

				<n-form-item :label="$t('reports.form.template')" path="reportTemplate">
					<div class="flex w-full flex-col gap-1">
						<n-select v-model:value="formData.reportTemplate" :options="templateOptions" />
						<span class="text-secondary text-xs">{{ selectedTemplateDescription }}</span>
					</div>
				</n-form-item>

				<div class="mt-6 flex justify-end gap-3">
					<n-button @click="showGenerateModal = false">{{ $t("common.actions.cancel") }}</n-button>
					<n-button
						type="primary"
						:loading="generating"
						data-testid="report-generate-submit"
						@click="handleGenerate"
					>
						{{ $t("reports.list.generate") }}
					</n-button>
				</div>
			</n-form>
		</n-modal>

		<n-modal
			v-model:show="showDeleteModal"
			preset="dialog"
			:title="$t('reports.delete.title')"
			:positive-text="$t('common.actions.delete')"
			:negative-text="$t('common.actions.cancel')"
			@positive-click="confirmDelete"
			@negative-click="showDeleteModal = false"
		>
			<p>{{ $t("reports.delete.confirm", { name: reportToDelete?.report_name ?? "" }) }}</p>
			<p class="text-secondary mt-2">{{ $t("reports.delete.irreversible") }}</p>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { FormInst, FormRules } from "naive-ui"
import type { ApiError } from "@/types/common"
import type {
	IncidentCustomerReport,
	IncidentCustomerReportGenerateRequest,
	IncidentReportTemplate
} from "@/types/reports"
import { saveAs } from "file-saver"
import { NButton, NDatePicker, NEmpty, NForm, NFormItem, NInput, NModal, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref, watch } from "vue"
import { useI18n } from "vue-i18n"
import { useRoute, useRouter } from "vue-router"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import ReportCard from "@/components/reports/ReportCard.vue"
import { useCustomerPrefill } from "@/composables/common/useCustomerPrefill"
import { useLatestRequest } from "@/composables/common/useLatestRequest"
import { useCustomerFilterStore } from "@/stores/customerFilter"
import { useReportGenerationStore } from "@/stores/reportGeneration"
import { getApiErrorMessage } from "@/utils"
import { downloadQueryId, fileNameFromDisposition } from "./reportDownload"

const AddIcon = "carbon:document-add"

const message = useMessage()
const { t } = useI18n()
const { loading, run } = useLatestRequest()
const { customerOptions, filterCustomer, renderCustomerLabel, hasMultipleCustomers, initialCustomerCode } =
	useCustomerPrefill()
const reportGenerationStore = useReportGenerationStore()
const customerFilterStore = useCustomerFilterStore()
const route = useRoute()
const router = useRouter()

const generating = ref(false)
const reports = ref<IncidentCustomerReport[]>([])
const showGenerateModal = ref(false)
const showDeleteModal = ref(false)
const reportToDelete = ref<IncidentCustomerReport | null>(null)
const formRef = ref<FormInst | null>(null)

interface GenerateFormData {
	report_name?: string
	customer_code: string | null
	range: "30d" | "90d" | "custom"
	customRange: [number, number] | null
	reportTemplate: IncidentReportTemplate
}

function getDefaultFormData(): GenerateFormData {
	return {
		report_name: undefined,
		customer_code: initialCustomerCode(),
		range: "30d",
		customRange: null,
		reportTemplate: "full"
	}
}

const formData = ref<GenerateFormData>(getDefaultFormData())

// Reset on every open, like the case form: the customer is re-seeded from the global
// filter as it is now, not as it was when the page mounted.
function openGenerateModal() {
	formData.value = getDefaultFormData()
	showGenerateModal.value = true
}

const rangeOptions = computed(() => [
	{ label: t("reports.form.ranges.last30"), value: "30d" },
	{ label: t("reports.form.ranges.last90"), value: "90d" },
	{ label: t("reports.form.ranges.custom"), value: "custom" }
])

const TEMPLATES: IncidentReportTemplate[] = ["full", "executive", "operational", "analytics"]

const templateOptions = computed(() =>
	TEMPLATES.map(value => ({
		label: t(`reports.form.templates.${value}.label`),
		value,
		description: t(`reports.form.templates.${value}.description`)
	}))
)

const selectedTemplateDescription = computed(
	() => templateOptions.value.find(o => o.value === formData.value.reportTemplate)?.description ?? ""
)

const rules = computed<FormRules>(() => ({
	customer_code: [{ required: true, message: t("reports.form.selectCustomer"), trigger: ["blur", "change"] }],
	customRange: [
		{
			validator: () => {
				if (formData.value.range === "custom" && !formData.value.customRange) {
					return new Error(t("reports.form.selectRange"))
				}
				return true
			},
			trigger: ["change", "blur"]
		}
	]
}))

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

function loadReports() {
	return run(
		async signal => {
			const response = await Api.reports.listReports({
				customerCodes: customerFilterStore.queryCustomerCodes,
				signal
			})
			if (response.data.success) {
				reports.value = response.data.reports
			} else {
				message.error(response.data.message || t("reports.list.loadFailed"))
			}
		},
		error => message.error(getApiErrorMessage(error as ApiError) || t("reports.list.loadFailed"))
	)
}

async function handleGenerate() {
	if (!formRef.value) return
	try {
		await formRef.value.validate()
	} catch {
		return
	}

	const customerCode = formData.value.customer_code
	if (!customerCode) {
		message.error(t("reports.list.noCustomer"))
		return
	}

	const { date_from, date_to } = resolveRange()
	// Customers can only ever generate reports with their own portal branding.
	const request: IncidentCustomerReportGenerateRequest = {
		customer_code: customerCode,
		date_from,
		date_to,
		brand_theme: "customer",
		report_template: formData.value.reportTemplate
	}
	if (formData.value.report_name?.trim()) {
		request.report_name = formData.value.report_name.trim()
	}

	generating.value = true
	try {
		const response = await Api.reports.generateReportBackground(request)
		if (response.data.success) {
			showGenerateModal.value = false
			formData.value = getDefaultFormData()
			formRef.value?.restoreValidation()
			message.info(t("reports.list.queued"), { duration: 6000 })
			// The watch lives in the app-level store, so the notification arrives even if
			// the user leaves this page (or reloads) while the report is still generating.
			reportGenerationStore.track({ id: response.data.report_id, name: response.data.report_name })
			await loadReports()
		} else {
			message.error(t("reports.list.queueFailed"))
		}
	} catch (error) {
		message.error(getApiErrorMessage(error as ApiError) || t("reports.list.generateFailed"))
	} finally {
		generating.value = false
	}
}

async function downloadReport(reportId: number, fileName?: string) {
	try {
		const response = await Api.reports.downloadReport(reportId)
		const name =
			fileName ?? fileNameFromDisposition(response.headers?.["content-disposition"]) ?? `report-${reportId}.pdf`
		saveAs(new Blob([response.data]), name)
		message.success(t("reports.list.downloaded"))
	} catch (error) {
		message.error(getApiErrorMessage(error as ApiError) || t("reports.list.downloadFailed"))
	}
}

function handleDownload(report: IncidentCustomerReport) {
	downloadReport(report.id, report.file_name)
}

// "Download" on a "Report ready" notification (toast or bell) lands here with ?download=<id>.
// The query is dropped first, so a reload or the back button never downloads it again.
watch(
	() => route.query.download,
	value => {
		const reportId = downloadQueryId(value)
		if (value === undefined) return
		const { download: _download, ...query } = route.query
		router.replace({ query })
		if (reportId !== null) {
			downloadReport(reportId, reports.value.find(report => report.id === reportId)?.file_name)
		}
	},
	{ immediate: true }
)

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
			message.error(t("reports.list.deleteFailed"))
		}
	} catch (error) {
		message.error(getApiErrorMessage(error as ApiError) || t("reports.list.deleteFailed"))
	} finally {
		showDeleteModal.value = false
		reportToDelete.value = null
	}
}

// The global customer filter narrows the list. The store replaces the selection array on
// every change, so no deep watch is needed.
watch(
	() => customerFilterStore.queryCustomerCodes,
	() => {
		loadReports()
	}
)

// The store notifies the user; this only keeps the open list in sync with it.
watch(
	() => reportGenerationStore.lastResolvedAt,
	() => {
		loadReports()
	}
)

onBeforeMount(() => {
	loadReports()
})
</script>
