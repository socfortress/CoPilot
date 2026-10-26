<template>
	<n-spin :show="loadingDetails">
		<div class="@container min-h-50">
			<n-alert v-if="detailsError" :title="$t('alerts.details.error')" type="error" :description="detailsError" />

			<template v-else-if="alert">
				<WaitingOnYouNotice
					v-if="isWaitingOnCustomer(alert.status)"
					entity="alert"
					@reply="activeTab = 'comments'"
				/>

				<n-tabs v-model:value="activeTab" type="line" animated>
					<n-tab-pane name="overview" :tab="$t('alerts.details.tabs.overview')">
						<AlertOverview :alert @status-updated="handleStatusUpdated" />
					</n-tab-pane>

					<n-tab-pane name="assets" :tab="$t('alerts.details.tabs.assets')">
						<AlertAssets :alert />
					</n-tab-pane>

					<n-tab-pane
						name="linked-cases"
						:tab="
							$t('alerts.details.tabs.linkedCases', {
								count: alert?.linked_cases?.length || alert?.case_ids?.length || 0
							})
						"
					>
						<AlertCases
							:alert
							@created="handleCaseCreated"
							@updated="handleCaseCreated"
							@unlinked="handleCaseUnlinked"
							@linked="handleCaseLinked"
						/>
					</n-tab-pane>

					<n-tab-pane name="iocs" :tab="$t('alerts.details.tabs.iocs')">
						<AlertIocs :alert />
					</n-tab-pane>

					<!-- Gated by the customer's AI report switch, managed by the SOC in CoPilot. -->
					<n-tab-pane
						v-if="aiReportEnabled"
						name="ai-report"
						:tab="$t('alerts.details.tabs.aiReport')"
						display-directive="show:lazy"
					>
						<AlertAiReport :alert-id="alert.id" />
					</n-tab-pane>

					<n-tab-pane name="comments" :tab="$t('alerts.details.tabs.comments', { count: alert.comments?.length || 0 })">
						<AlertComments
							:alert
							@added="handleCommentAdded"
							@updated="handleCommentUpdated"
							@deleted="handleCommentDeleted"
						/>
					</n-tab-pane>
				</n-tabs>
			</template>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { AlertStatusUpdateSuccessPayload } from "../AlertStatusSelect.vue"
import type { Alert } from "@/types/alerts"
import type { CommentItem } from "@/types/comments"
import type { ApiError } from "@/types/common"
import { NAlert, NSpin, NTabPane, NTabs } from "naive-ui"
import { ref, watch } from "vue"
import { useI18n } from "vue-i18n"
import Api from "@/api"
import WaitingOnYouNotice from "@/components/common/WaitingOnYouNotice.vue"
import { useAiReportsAvailability } from "@/composables/common/useAiReportsAvailability"
import { getApiErrorMessage } from "@/utils"
import { isWaitingOnCustomer } from "@/utils/workflowStatus"
import AlertAiReport from "./AlertAiReport.vue"
import AlertAssets from "./AlertAssets.vue"
import AlertCases from "./AlertCases.vue"
import AlertComments from "./AlertComments.vue"
import AlertIocs from "./AlertIocs.vue"
import AlertOverview from "./AlertOverview.vue"

const props = defineProps<{
	alertId: number | null
}>()

const emit = defineEmits<{
	(e: "statusUpdated", value: AlertStatusUpdateSuccessPayload): void
}>()

const alert = ref<Alert | null>(null)
const detailsError = ref<string | null>(null)
const loadingDetails = ref(false)
const aiReportEnabled = ref(false)
const activeTab = ref("overview")

const { isEnabledFor } = useAiReportsAvailability()
const { t } = useI18n()

async function loadAlertDetails() {
	if (props.alertId === null) return

	loadingDetails.value = true
	detailsError.value = null

	try {
		const response = await Api.alerts.getAlert(props.alertId)
		alert.value = response.data.alerts[0] || null
		if (!alert.value) {
			detailsError.value = t("alerts.details.notFound")
		}
	} catch (err) {
		detailsError.value = getApiErrorMessage(err as ApiError)
	} finally {
		loadingDetails.value = false
	}

	// Resolved after the alert so the switch is checked against its owning
	// customer — a portal user may be scoped to more than one.
	aiReportEnabled.value = alert.value ? await isEnabledFor(alert.value.customer_code) : false
}

async function handleCommentAdded(comment: CommentItem) {
	if (!alert.value) return

	if (!alert.value.comments) {
		alert.value.comments = []
	}
	alert.value.comments.push(comment)

	// Replying to an alert the SOC waits on hands it back (the backend moves it to
	// IN_PROGRESS): read the status it now has, and tell the list.
	if (isWaitingOnCustomer(alert.value.status)) {
		await loadAlertDetails()
		if (alert.value && !isWaitingOnCustomer(alert.value.status)) {
			emit("statusUpdated", { alertId: alert.value.id, status: alert.value.status })
		}
	}
}

function handleCommentUpdated(comment: CommentItem) {
	if (!alert.value) return
	alert.value.comments = alert.value.comments.map(c => (c.id === comment.id ? comment : c))
}

function handleCommentDeleted(commentId: number) {
	if (!alert.value) return
	alert.value.comments = alert.value.comments.filter(c => c.id !== commentId)
}

function handleCaseCreated() {
	loadAlertDetails()
}

function handleCaseUnlinked() {
	loadAlertDetails()
}

function handleCaseLinked() {
	loadAlertDetails()
}

function handleStatusUpdated(payload: AlertStatusUpdateSuccessPayload) {
	if (!alert.value) return
	alert.value.status = payload.status
	emit("statusUpdated", payload)
}

watch(
	() => props.alertId,
	async newAlertId => {
		alert.value = null
		detailsError.value = null
		aiReportEnabled.value = false
		activeTab.value = "overview"

		if (newAlertId !== null) {
			await loadAlertDetails()
		}
	},
	{ immediate: true }
)
</script>
