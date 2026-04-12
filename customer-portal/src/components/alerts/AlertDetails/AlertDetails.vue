<template>
	<n-spin :show="loadingDetails">
		<div class="@container min-h-50">
			<n-alert v-if="detailsError" title="Error" type="error" :description="detailsError" />

			<n-tabs v-else-if="alert" type="line" animated>
				<n-tab-pane name="overview" tab="Overview">
					<AlertOverview :alert @status-updated="handleStatusUpdated" />
				</n-tab-pane>

				<n-tab-pane name="assets" tab="Assets">
					<AlertAssets :alert />
				</n-tab-pane>

				<n-tab-pane name="linked-cases" tab="Linked Cases">
					<AlertCases :alert />
				</n-tab-pane>

				<n-tab-pane name="iocs" tab="Indicators of Compromise (IoCs)">
					<AlertIocs :alert />
				</n-tab-pane>

				<n-tab-pane name="comments" :tab="`Comments (${alert.comments?.length || 0})`">
					<AlertComments :alert @success="addComment" />
				</n-tab-pane>
			</n-tabs>
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
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"
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

async function loadAlertDetails() {
	if (props.alertId === null) return

	loadingDetails.value = true
	detailsError.value = null

	try {
		const response = await Api.alerts.getAlert(props.alertId)
		alert.value = response.data.alerts[0] || null
		if (!alert.value) {
			detailsError.value = "Alert not found."
		}
	} catch (err) {
		detailsError.value = getApiErrorMessage(err as ApiError)
	} finally {
		loadingDetails.value = false
	}
}

async function addComment(comment: CommentItem) {
	if (!alert.value) return

	if (!alert.value.comments) {
		alert.value.comments = []
	}
	alert.value.comments.push(comment)
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

		if (newAlertId !== null) {
			await loadAlertDetails()
		}
	},
	{ immediate: true }
)
</script>
