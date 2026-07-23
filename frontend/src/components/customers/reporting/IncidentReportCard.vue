<template>
	<CardEntity
		size="small"
		embedded
		hoverable
		main-box-class="gap-3"
		:status="reportCardStatus(report.status)"
		:loading
		loading-description="Deleting report…"
	>
		<!-- Header: icon + title + period, status pill on the right -->
		<template #headerMain>
			<div class="flex min-w-0 items-start gap-2.5">
				<Icon :name="ReportIcon" :size="18" class="report-glyph mt-0.5 shrink-0" />
				<div class="flex min-w-0 flex-col gap-0.5">
					<span
						class="text-default line-clamp-2 text-sm leading-snug font-semibold"
						:title="report.report_name"
					>
						{{ report.report_name }}
					</span>
					<span class="text-secondary inline-flex items-center gap-1.5 text-xs">
						<Icon :name="PeriodIcon" :size="13" />
						<span class="font-mono">
							{{ formatDate(report.date_from, dFormats.date) }} –
							{{ formatDate(report.date_to, dFormats.date) }}
						</span>
					</span>
				</div>
			</div>
		</template>

		<template #headerExtra>
			<div class="flex items-center gap-2.5">
				<!-- Visibility toggle sits with the status: both describe report state (analyst/admin only) -->
				<n-tooltip v-if="!isCustomerGenerated" class="max-w-80 px-1.5! py-0.5! text-sm">
					<template #trigger>
						<div class="flex shrink-0 items-center gap-1.5">
							<Icon
								:name="report.visible_to_customer ? VisibleIcon : HiddenIcon"
								:size="14"
								class="text-secondary"
							/>
							<span class="text-secondary text-xs">
								{{ report.visible_to_customer ? "Visible" : "Hidden" }}
							</span>
							<n-switch
								:value="report.visible_to_customer"
								:loading="loadingVisibility"
								size="small"
								@update:value="onToggleVisibility"
							/>
						</div>
					</template>
					{{ visibilityTooltip }}
				</n-tooltip>
				<n-tag
					:type="statusTagType(report.status)"
					size="small"
					round
					:bordered="false"
					class="shrink-0 font-medium"
				>
					<template #icon>
						<Icon
							:name="statusIcon(report.status)"
							:size="12"
							:class="{ 'animate-spin': report.status === 'processing' }"
						/>
					</template>
					{{ statusLabel(report.status) }}
				</n-tag>
			</div>
		</template>

		<!-- Body: flat stat strip + optional error -->
		<template #default>
			<div class="stat-strip flex">
				<div v-for="tile in tiles" :key="tile.label" class="stat-col flex flex-1 flex-col px-3.5">
					<span
						class="font-mono text-xl leading-none font-bold"
						:style="tile.color ? { color: tile.color } : undefined"
					>
						{{ tile.value.toLocaleString() }}
					</span>
					<span class="text-tertiary mt-1.5 text-[10px] font-medium tracking-wider uppercase">
						{{ tile.label }}
					</span>
				</div>
			</div>

			<p v-if="report.status === 'failed' && report.error_message" class="text-error mt-3 text-xs">
				{{ report.error_message }}
			</p>
		</template>

		<!-- Footer: meta on the left, actions on the right -->
		<template #footerMain>
			<div class="text-secondary flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
				<span v-if="authorLabel" class="inline-flex items-center gap-1">
					<Icon :name="AuthorIcon" :size="13" :style="{ color: authorColorVar }" />
					{{ authorLabel }}
				</span>
				<span class="inline-flex items-center gap-1">
					<Icon :name="FileIcon" :size="13" />
					{{ formatBytes(report.file_size) }}
				</span>
				<span class="inline-flex items-center gap-1">
					<Icon :name="ClockIcon" :size="13" />
					{{ formatDate(report.generated_at, dFormats.datetime) }}
				</span>
				<span class="inline-flex items-center gap-1">
					<Icon :name="BrandIcon" :size="13" :style="{ color: brandColorVar }" />
					{{ brandLabel }}
				</span>
				<span class="inline-flex items-center gap-1" :title="templateDescription">
					<Icon :name="TemplateIcon" :size="13" />
					{{ templateLabel }}
				</span>
			</div>
		</template>

		<template #footerExtra>
			<div class="flex items-center gap-2">
				<n-button
					v-if="report.status === 'completed'"
					size="tiny"
					type="primary"
					secondary
					@click="emit('download')"
				>
					<template #icon><Icon :name="DownloadIcon" :size="14" /></template>
					Download
				</n-button>
				<n-button size="tiny" quaternary type="error" @click="emit('delete')">
					<template #icon><Icon :name="DeleteIcon" :size="16" /></template>
				</n-button>
			</div>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { IncidentCustomerReport } from "@/types/incidentReports"
import { NButton, NSwitch, NTag, NTooltip } from "naive-ui"
import { computed } from "vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatBytes, formatDate } from "@/utils/format"

const {
	report,
	loadingVisibility = false,
	loading = false
} = defineProps<{
	report: IncidentCustomerReport
	loadingVisibility?: boolean
	loading?: boolean
}>()

const emit = defineEmits<{
	download: []
	delete: []
	toggleVisibility: [visible: boolean]
}>()

const ReportIcon = "carbon:document"
const PeriodIcon = "carbon:calendar"
const DownloadIcon = "carbon:download"
const DeleteIcon = "carbon:trash-can"
const AuthorIcon = "carbon:user"
const FileIcon = "carbon:document-pdf"
const ClockIcon = "carbon:time"
const BrandIcon = "carbon:color-palette"
const TemplateIcon = "carbon:document-multiple-01"
const VisibleIcon = "carbon:view"
const HiddenIcon = "carbon:view-off"
const CheckIcon = "carbon:checkmark-filled"
const ErrorIcon = "carbon:warning-filled"
const LoadingIcon = "eos-icons:loading"

const dFormats = useSettingsStore().dateFormat

const isCustomerGenerated = computed(() => report.generated_by_role === "customer_user")

const visibilityTooltip = computed(() =>
	report.visible_to_customer
		? "Shared with the customer portal — the customer can see and download this report. Toggle to hide it."
		: "Hidden from the customer portal. Toggle to share this report with the customer."
)

const tiles = computed(() => [
	{ label: "Alerts", value: report.total_alerts, color: "var(--primary-color)" },
	{ label: "Cases", value: report.total_cases, color: undefined },
	{ label: "Open", value: report.open_cases, color: "var(--warning-color)" },
	{ label: "Closed", value: report.closed_cases, color: "var(--success-color)" }
])

const roleLabel = computed(() => {
	const labels: Record<string, string> = {
		admin: "Admin",
		analyst: "Analyst",
		scheduler: "Scheduler",
		customer_user: "Customer"
	}
	const role = report.generated_by_role
	if (!role) return null
	return labels[role] ?? role
})

const authorLabel = computed(() => {
	const name = report.generated_by_name
	const role = roleLabel.value
	if (name && role) return `${name} · ${role}`
	return name || role || null
})

const authorColorVar = computed(() =>
	report.generated_by_role === "customer_user" ? "var(--success-color)" : "var(--primary-color)"
)

// Reports generated before branding was recorded always used the customer portal
// look, so default to it when the field is absent.
const isSocfortressBrand = computed(() => report.filters_applied?.brand_theme === "socfortress")
const brandLabel = computed(() => (isSocfortressBrand.value ? "SOCFortress" : "Customer portal"))
const brandColorVar = computed(() => (isSocfortressBrand.value ? "var(--warning-color)" : "var(--primary-color)"))

// Which report layout was used. Reports generated before templates existed have no
// field, so default to the complete report (the only layout available back then).
const templateMeta: Record<string, { label: string; description: string }> = {
	full: {
		label: "Complete",
		description: "Executive summary, charts & trends, and open/closed cases with assets & IOCs"
	},
	executive: { label: "Executive", description: "One-look synthesis: KPIs, service metrics and a status chart" },
	operational: {
		label: "Operational",
		description: "Case-centric: open/closed cases in full detail (assets, IOCs, resolution)"
	},
	analytics: {
		label: "Analytics",
		description: "Metrics-centric: executive summary, all charts and the monthly trend table"
	}
}
const templateInfo = computed(
	() => templateMeta[String(report.filters_applied?.report_template ?? "full")] ?? templateMeta.full
)
const templateLabel = computed(() => templateInfo.value.label)
const templateDescription = computed(() => templateInfo.value.description)

function onToggleVisibility(visible: boolean) {
	emit("toggleVisibility", visible)
}

function statusLabel(status: IncidentCustomerReport["status"]) {
	return { completed: "Completed", processing: "Processing", failed: "Failed" }[status]
}

function statusIcon(status: IncidentCustomerReport["status"]) {
	if (status === "completed") return CheckIcon
	if (status === "processing") return LoadingIcon
	return ErrorIcon
}

function statusTagType(status: IncidentCustomerReport["status"]): "success" | "warning" | "error" {
	if (status === "completed") return "success"
	if (status === "processing") return "warning"
	return "error"
}

function reportCardStatus(status: IncidentCustomerReport["status"]): "success" | "warning" | "error" | undefined {
	if (status === "processing") return "warning"
	if (status === "failed") return "error"
	return undefined
}
</script>

<style scoped>
.report-glyph {
	color: var(--primary-color);
}

/* Flat stat strip: hairline separators between columns, no boxes */
.stat-col:first-child {
	padding-left: 0;
}
.stat-col + .stat-col {
	border-left: 1px solid var(--border-color);
}
</style>
