<template>
	<n-card size="small" :title="report.report_name" embedded>
		<template #header-extra>
			<n-tag :type="statusColor(report.status)" size="small" round data-testid="report-status">
				{{ statusText }}
			</n-tag>
		</template>

		<div class="flex flex-col gap-2 text-sm">
			<div class="text-secondary flex items-center gap-2 font-mono text-xs">
				<Icon :name="PeriodIcon" :size="14" />
				{{ formatDate(report.date_from, dFormats.date, { tz: true }) }} →
				{{ formatDate(report.date_to, dFormats.date, { tz: true }) }}
			</div>
			<div class="text-secondary flex items-center gap-2 text-xs" :title="templateDescription">
				<Icon :name="TemplateIcon" :size="14" />
				{{ templateLabel }} report
			</div>
			<div class="flex flex-wrap gap-2">
				<Chip size="small" :value="`${report.total_alerts}`" label="alerts" />
				<Chip size="small" :value="`${report.total_cases}`" label="cases" />
				<Chip size="small" :value="`${report.open_cases}`" label="open" />
				<Chip size="small" :value="`${report.closed_cases}`" label="closed" />
			</div>
			<p v-if="report.status === 'failed' && report.error_message" class="text-error text-xs">
				{{ report.error_message }}
			</p>
		</div>

		<template #footer>
			<div class="flex items-center justify-between gap-2">
				<span class="text-secondary text-xs">
					<template v-if="authorText">{{ authorText }} ·</template>
					{{ formatDate(report.generated_at, dFormats.datetime, { tz: true }) }} ·
					{{ formatBytes(report.file_size) }}
				</span>
				<div class="flex items-center gap-2">
					<n-button
						v-if="report.status === 'completed'"
						size="small"
						type="primary"
						secondary
						@click="emit('download')"
					>
						<template #icon><Icon :name="DownloadIcon" :size="14" /></template>
						Download
					</n-button>
					<n-button v-if="isCustomerGenerated" size="small" type="error" secondary @click="emit('delete')">
						<template #icon><Icon :name="DeleteIcon" :size="14" /></template>
						Delete
					</n-button>
				</div>
			</div>
		</template>
	</n-card>
</template>

<script setup lang="ts">
import type { IncidentCustomerReport } from "@/types/reports"
import { useIntervalFn, useNow } from "@vueuse/core"
import { NButton, NCard, NTag } from "naive-ui"
import { computed } from "vue"
import Chip from "@/components/common/Chip.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatBytes, formatDate } from "@/utils/format"
import { elapsedLabel, secondsSince } from "./reportTiming"

const { report } = defineProps<{
	report: IncidentCustomerReport
}>()

const emit = defineEmits<{
	download: []
	delete: []
}>()

const DownloadIcon = "carbon:download"
const DeleteIcon = "carbon:trash-can"
const PeriodIcon = "carbon:calendar"
const TemplateIcon = "carbon:document-multiple-01"

const dFormats = useSettingsStore().dateFormat

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

// Customers may only delete reports they generated themselves; analyst/admin
// reports shared into the portal are read-only here (download still allowed).
const isCustomerGenerated = computed(() => report.generated_by_role === "customer_user")

const authorText = computed(() => {
	const roleLabels: Record<string, string> = {
		admin: "Admin",
		analyst: "Analyst",
		scheduler: "Scheduler",
		customer_user: "Customer"
	}
	const role = report.generated_by_role ? (roleLabels[report.generated_by_role] ?? report.generated_by_role) : null
	const name = report.generated_by_name
	if (name && role) return `${name} · ${role}`
	return name || role || ""
})

function statusLabel(status: IncidentCustomerReport["status"]) {
	return { completed: "Completed", processing: "Generating", failed: "Failed" }[status]
}

// While it generates, say for how long (#1263): the times are stored as UTC, read as such.
const now = useNow({ scheduler: tick => useIntervalFn(tick, 15_000) })
const statusText = computed(() => {
	if (report.status !== "processing") return statusLabel(report.status)
	const seconds = secondsSince(report.generated_at, now.value.getTime())
	return seconds === null ? statusLabel(report.status) : `${statusLabel(report.status)} · ${elapsedLabel(seconds)}`
})

function statusColor(status: IncidentCustomerReport["status"]): "success" | "warning" | "error" {
	if (status === "completed") return "success"
	if (status === "processing") return "warning"
	return "error"
}
</script>
