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
				{{ templateLabel }}
			</div>
			<div class="flex flex-wrap gap-2">
				<Chip size="small" :value="`${report.total_alerts}`" :label="$t('reports.card.alerts')" />
				<Chip size="small" :value="`${report.total_cases}`" :label="$t('reports.card.cases')" />
				<Chip size="small" :value="`${report.open_cases}`" :label="$t('reports.card.open')" />
				<Chip size="small" :value="`${report.closed_cases}`" :label="$t('reports.card.closed')" />
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
						{{ $t("common.actions.download") }}
					</n-button>
					<n-button v-if="isCustomerGenerated && !readOnly" size="small" type="error" secondary @click="emit('delete')">
						<template #icon><Icon :name="DeleteIcon" :size="14" /></template>
						{{ $t("common.actions.delete") }}
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
import { useI18n } from "vue-i18n"
import Chip from "@/components/common/Chip.vue"
import Icon from "@/components/common/Icon.vue"
import { useReadOnly } from "@/composables/common/useReadOnly"
import { useSettingsStore } from "@/stores/settings"
import { elapsedLabel, secondsSince } from "@/utils/elapsed"
import { formatBytes, formatDate } from "@/utils/format"

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

const { t } = useI18n()
const dFormats = useSettingsStore().dateFormat

// Which report layout was used. Reports generated before templates existed have no
// field, so default to the complete report (the only layout available back then).
const TEMPLATES = ["full", "executive", "operational", "analytics"] as const
type Template = (typeof TEMPLATES)[number]

const template = computed<Template>(() => {
	const value = String(report.filters_applied?.report_template ?? "full")
	return (TEMPLATES as readonly string[]).includes(value) ? (value as Template) : "full"
})
const templateLabel = computed(() => t(`reports.card.templates.${template.value}.name`))
const templateDescription = computed(() => t(`reports.card.templates.${template.value}.description`))

// Customers may only delete reports they generated themselves; analyst/admin
// reports shared into the portal are read-only here (download still allowed).
const isCustomerGenerated = computed(() => report.generated_by_role === "customer_user")
// Nor by a user who may only read the report's customer (#1312).
const readOnly = useReadOnly(() => report.customer_code)

const ROLE_KEYS = {
	admin: "reports.card.roles.admin",
	analyst: "reports.card.roles.analyst",
	scheduler: "reports.card.roles.scheduler",
	customer_user: "reports.card.roles.customer_user"
} as const

const authorText = computed(() => {
	const roleKey = ROLE_KEYS[report.generated_by_role as keyof typeof ROLE_KEYS]
	const role = report.generated_by_role ? (roleKey ? t(roleKey) : report.generated_by_role) : null
	const name = report.generated_by_name
	if (name && role) return `${name} · ${role}`
	return name || role || ""
})

function statusLabel(status: IncidentCustomerReport["status"]) {
	return t(`reports.card.status.${status}`)
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
