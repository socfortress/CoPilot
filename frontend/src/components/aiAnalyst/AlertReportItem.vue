<template>
	<div>
		<CardEntity hoverable clickable @click="openDetails()">
			<template v-if="alert" #headerMain>
				<div class="flex items-center gap-2">
					<span>#{{ alert.alert_id }} - {{ alert.source }}</span>
					<Icon :name="InfoIcon" :size="16" />
				</div>
			</template>

			<template v-if="alert?.alert_creation_time" #headerExtra>
				<div class="flex items-center gap-2">
					<span>{{ formatDate(alert.alert_creation_time, dFormats.datetime) }}</span>
					<Icon :name="TimeIcon" :size="16" />
				</div>
			</template>

			<template v-if="alert" #default>
				{{ alert.alert_name }}
			</template>

			<template v-if="alert" #mainExtra>
				<div class="flex flex-wrap items-center gap-3">
					<Badge
						type="splitted"
						bright
						:color="
							alert.status === 'OPEN' ? 'danger' : alert.status === 'IN_PROGRESS' ? 'warning' : 'success'
						"
					>
						<template #iconLeft>
							<Icon :name="StatusIcon" :size="14" />
						</template>
						<template #label>Status</template>
						<template #value>{{ alert.status || "n/d" }}</template>
					</Badge>

					<Badge v-if="alert.report.severity_assessment" type="splitted" bright :color="severityColor">
						<template #iconLeft>
							<Icon :name="SeverityIcon" :size="14" />
						</template>
						<template #label>Severity</template>
						<template #value>{{ alert.report.severity_assessment }}</template>
					</Badge>

					<Badge v-if="alert.assigned_to" type="splitted" bright color="success">
						<template #iconLeft>
							<Icon :name="AssigneeIcon" :size="14" />
						</template>
						<template #label>Assignee</template>
						<template #value>{{ alert.assigned_to }}</template>
					</Badge>

					<Badge type="splitted">
						<template #label>Customer</template>
						<template #value>
							<code class="text-primary leading-none">#{{ alert.customer_code }}</code>
						</template>
					</Badge>
				</div>
			</template>

			<template v-if="alert" #footerMain>
				<div class="flex items-center gap-2 text-sm opacity-70">
					<Icon :name="ReportIcon" :size="14" />
					<span>Report generated {{ formatDate(alert.report.created_at, dFormats.datetime) }}</span>
				</div>
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			:style="{ maxWidth: 'min(850px, 90vw)', minHeight: 'min(540px, 90vh)', overflow: 'hidden' }"
			display-directive="show"
		>
			<n-card
				content-class="flex flex-col p-0!"
				:title="alertNameTruncated"
				closable
				:bordered="false"
				segmented
				role="modal"
				@close="showDetails = false"
			>
				<AlertReportDetails v-if="alert" :alert />
			</n-card>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { AlertWithReport } from "@/types/aiAnalyst.d"
import _truncate from "lodash/truncate"
import { NCard, NModal } from "naive-ui"
import { computed, ref, toRefs } from "vue"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils/format"
import AlertReportDetails from "./AlertReportDetails.vue"

const props = defineProps<{
	alertData: AlertWithReport
}>()

const { alertData } = toRefs(props)

const InfoIcon = "carbon:information"
const TimeIcon = "carbon:time"
const StatusIcon = "carbon:circle-dash"
const SeverityIcon = "carbon:warning-alt"
const AssigneeIcon = "carbon:user"
const ReportIcon = "carbon:document"

const dFormats = useSettingsStore().dateFormat
const showDetails = ref(false)
const alert = computed(() => alertData.value)
const alertNameTruncated = computed(() => _truncate(alert.value?.alert_name, { length: 50 }))

const severityColor = computed(() => {
	const severity = alert.value?.report.severity_assessment
	if (severity === "Critical" || severity === "High") return "danger"
	if (severity === "Medium") return "warning"
	if (severity === "Low" || severity === "Informational") return "success"
	return undefined
})

function openDetails() {
	showDetails.value = true
}
</script>
