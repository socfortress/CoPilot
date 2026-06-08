<template>
	<CardEntity
		size="small"
		embedded
		main-box-class="gap-2"
		header-box-class="flex-nowrap! items-start"
		:status="reportCardStatus(report.status)"
	>
		<template #headerMain>
			<span class="text-default line-clamp-2 text-sm leading-snug font-semibold" :title="report.report_name">
				{{ report.report_name }}
			</span>
		</template>

		<template #headerExtra>
			<Badge type="splitted" bright size="small" :color="statusBadgeColor(report.status)">
				<template #label>
					<Icon :name="statusIcon(report.status)" :size="12" />
					Status
				</template>
				<template #value>{{ statusLabel(report.status) }}</template>
			</Badge>
		</template>

		<template #default>
			<div class="flex flex-col gap-2">
				<div class="text-secondary flex min-w-0 items-center gap-2 text-xs">
					<span class="inline-flex shrink-0 items-center gap-1.5">
						<Icon :name="CustomerIcon" :size="14" />
						<span class="text-tertiary font-medium uppercase">Customer</span>
					</span>
					<span class="truncate font-mono" :title="report.customer_code">{{ report.customer_code }}</span>
				</div>

				<div class="flex flex-wrap gap-2">
					<Badge type="splitted" bright size="small">
						<template #label>Policies</template>
						<template #value>{{ report.total_policies.toLocaleString() }}</template>
					</Badge>
					<Badge type="splitted" size="small" color="success">
						<template #label>Passed</template>
						<template #value>{{ report.passed_count.toLocaleString() }}</template>
					</Badge>
					<Badge type="splitted" size="small" color="danger">
						<template #label>Failed</template>
						<template #value>{{ report.failed_count.toLocaleString() }}</template>
					</Badge>
					<Badge type="splitted" size="small" color="warning">
						<template #label>Invalid</template>
						<template #value>{{ report.invalid_count.toLocaleString() }}</template>
					</Badge>
					<Badge type="splitted" bright size="small">
						<template #label>Checks</template>
						<template #value>{{ report.total_checks.toLocaleString() }}</template>
					</Badge>
				</div>

				<p v-if="report.status === 'failed' && report.error_message" class="text-error text-xs">
					{{ report.error_message }}
				</p>
			</div>
		</template>

		<template #footerMain>
			<div class="flex flex-wrap items-center gap-2">
				<Badge type="splitted" bright size="small">
					<template #label>File</template>
					<template #value>{{ report.file_name }}</template>
				</Badge>
				<Badge type="splitted" bright size="small">
					<template #label>Size</template>
					<template #value>{{ formatBytes(report.file_size) }}</template>
				</Badge>
				<Badge type="splitted" bright size="small">
					<template #label>Generated</template>
					<template #value>{{ formatDate(report.generated_at, dFormats.datetime) }}</template>
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
import type { SCAReport } from "@/types/sca.d"
import { NButton } from "naive-ui"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatBytes, formatDate } from "@/utils/format"

const { report } = defineProps<{
	report: SCAReport
}>()

const emit = defineEmits<{
	download: []
	delete: []
}>()

const DownloadIcon = "carbon:download"
const DeleteIcon = "carbon:trash-can"
const CheckIcon = "carbon:checkmark-filled"
const ErrorIcon = "carbon:warning-filled"
const LoadingIcon = "eos-icons:loading"
const CustomerIcon = "carbon:user"

const dFormats = useSettingsStore().dateFormat

function statusLabel(status: SCAReport["status"]) {
	const labels = {
		completed: "Completed",
		processing: "Processing",
		failed: "Failed"
	}
	return labels[status]
}

function statusIcon(status: SCAReport["status"]) {
	if (status === "completed") return CheckIcon
	if (status === "processing") return LoadingIcon
	return ErrorIcon
}

function statusBadgeColor(status: SCAReport["status"]): BadgeColor | undefined {
	if (status === "completed") return "success"
	if (status === "processing") return "warning"
	return "danger"
}

function reportCardStatus(status: SCAReport["status"]): "success" | "warning" | "error" | undefined {
	if (status === "completed") return "success"
	if (status === "processing") return "warning"
	if (status === "failed") return "error"
	return undefined
}
</script>
