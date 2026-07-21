<template>
	<CardEntity
		size="small"
		embedded
		main-box-class="gap-2"
		header-box-class="flex-nowrap! items-start"
		:status="reportCardStatus(report.status)"
		:loading
		loading-description="Deleting report…"
	>
		<template #headerMain>
			<span class="text-default line-clamp-2 text-sm leading-snug font-semibold" :title="report.report_name">
				{{ report.report_name }}
			</span>
		</template>

		<template #headerExtra>
			<div class="flex items-center gap-4">
				<div v-if="!isCustomerGenerated" class="flex items-center gap-2 pt-1">
					<n-switch
						:value="report.visible_to_customer"
						:loading="loadingVisibility"
						size="small"
						@update:value="onToggleVisibility"
					/>
					<span class="text-secondary inline-flex items-center gap-1 text-xs">
						<Icon :name="VisibilityIcon" :size="13" />
						Visible to customer
					</span>
				</div>
				<Badge type="splitted" bright size="small" :color="statusBadgeColor(report.status)">
					<template #label>
						<Icon :name="statusIcon(report.status)" :size="12" />
						Status
					</template>
					<template #value>{{ statusLabel(report.status) }}</template>
				</Badge>
			</div>
		</template>

		<template #default>
			<div class="flex flex-col gap-2">
				<div class="text-secondary flex min-w-0 items-center gap-2 text-xs">
					<span class="inline-flex shrink-0 items-center gap-1.5">
						<Icon :name="PeriodIcon" :size="14" />
						<span class="text-tertiary font-medium uppercase">Period</span>
					</span>
					<span class="truncate font-mono">
						{{ formatDate(report.date_from, dFormats.date) }} →
						{{ formatDate(report.date_to, dFormats.date) }}
					</span>
				</div>

				<div class="flex flex-wrap gap-2">
					<Badge type="splitted" size="small" color="primary">
						<template #label>Alerts</template>
						<template #value>{{ report.total_alerts.toLocaleString() }}</template>
					</Badge>
					<Badge type="splitted" size="small">
						<template #label>Cases</template>
						<template #value>{{ report.total_cases.toLocaleString() }}</template>
					</Badge>
					<Badge type="splitted" size="small" color="warning">
						<template #label>Open</template>
						<template #value>{{ report.open_cases.toLocaleString() }}</template>
					</Badge>
					<Badge type="splitted" size="small" color="success">
						<template #label>Closed</template>
						<template #value>{{ report.closed_cases.toLocaleString() }}</template>
					</Badge>
				</div>

				<p v-if="report.status === 'failed' && report.error_message" class="text-error text-xs">
					{{ report.error_message }}
				</p>
			</div>
		</template>

		<template #footerMain>
			<div class="flex flex-wrap items-center gap-2">
				<Badge v-if="report.generated_by_name || report.generated_by_role" type="splitted" :color="authorColor">
					<template #label>Author</template>
					<template #value>{{ authorLabel }}</template>
				</Badge>
				<Badge type="splitted" bright>
					<template #label>Size</template>
					<template #value>{{ formatBytes(report.file_size) }}</template>
				</Badge>
				<Badge type="splitted" bright>
					<template #label>Generated</template>
					<template #value>{{ formatDate(report.generated_at, dFormats.datetime) }}</template>
				</Badge>
				<Badge type="splitted" :color="brandColor">
					<template #label>
						<Icon :name="BrandIcon" :size="12" />
						Branding
					</template>
					<template #value>{{ brandLabel }}</template>
				</Badge>
			</div>
		</template>

		<template #footerExtra>
			<div class="flex items-center gap-2">
				<n-button
					v-if="report.status === 'completed'"
					size="small"
					type="primary"
					secondary
					@click="emit('download')"
				>
					<template #icon>
						<Icon :name="DownloadIcon" :size="14" />
					</template>
					Download
				</n-button>
				<n-button size="small" type="error" secondary @click="emit('delete')">
					<template #icon>
						<Icon :name="DeleteIcon" :size="14" />
					</template>
					Delete
				</n-button>
			</div>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { BadgeColor } from "@/components/common/Badge.vue"
import type { IncidentCustomerReport } from "@/types/incidentReports"
import { NButton, NSwitch } from "naive-ui"
import { computed } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatBytes, formatDate } from "@/utils/format"

const { report, loadingVisibility = false, loading = false } = defineProps<{
	report: IncidentCustomerReport
	loadingVisibility?: boolean
	loading?: boolean
}>()

const emit = defineEmits<{
	download: []
	delete: []
	toggleVisibility: [visible: boolean]
}>()

const DownloadIcon = "carbon:download"
const DeleteIcon = "carbon:trash-can"
const CheckIcon = "carbon:checkmark-filled"
const ErrorIcon = "carbon:warning-filled"
const LoadingIcon = "eos-icons:loading"
const VisibilityIcon = "carbon:view"
const BrandIcon = "carbon:color-palette"

const isCustomerGenerated = computed(() => report.generated_by_role === "customer_user")

// Reports generated before branding was recorded always used the customer portal
// look, so default to it when the field is absent — the badge is always shown.
const brandLabel = computed(() => (report.filters_applied?.brand_theme === "socfortress" ? "SOCFortress" : "Customer portal"))

const brandColor = computed<BadgeColor | undefined>(() =>
	report.filters_applied?.brand_theme === "socfortress" ? "warning" : "primary"
)

function onToggleVisibility(visible: boolean) {
	emit("toggleVisibility", visible)
}
const PeriodIcon = "carbon:calendar"

const dFormats = useSettingsStore().dateFormat

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
	return name || role || "—"
})

const authorColor = computed<BadgeColor | undefined>(() =>
	report.generated_by_role === "customer_user" ? "success" : "primary"
)

function statusLabel(status: IncidentCustomerReport["status"]) {
	const labels = {
		completed: "Completed",
		processing: "Processing",
		failed: "Failed"
	}
	return labels[status]
}

function statusIcon(status: IncidentCustomerReport["status"]) {
	if (status === "completed") return CheckIcon
	if (status === "processing") return LoadingIcon
	return ErrorIcon
}

function statusBadgeColor(status: IncidentCustomerReport["status"]): BadgeColor | undefined {
	if (status === "completed") return "success"
	if (status === "processing") return "warning"
	return "danger"
}

function reportCardStatus(status: IncidentCustomerReport["status"]): "success" | "warning" | "error" | undefined {
	if (status === "completed") return "success"
	if (status === "processing") return "warning"
	if (status === "failed") return "error"
	return undefined
}
</script>
