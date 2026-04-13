<template>
	<n-spin :show="loadingDetails">
		<div class="@container min-h-50">
			<n-alert v-if="detailsError" title="Error" type="error" :description="detailsError" />

			<n-tabs v-else-if="caseData" type="line" animated>
				<n-tab-pane name="overview" tab="Overview">
					<CaseOverview
						:case-data
						@status-updated="handleStatusUpdated"
						@assigned-to-updated="handleAssignedToUpdated"
					/>
				</n-tab-pane>
				<n-tab-pane
					name="alerts"
					:tab="`Alerts (${caseData?.alerts?.length || caseData?.alert_ids?.length || 0})`"
				>
					<CaseAlerts :case-data @updated="handleAlertUpdated" />
				</n-tab-pane>
				<n-tab-pane name="files" tab="Files">
					<CaseFiles :case-id="caseData.id" />
				</n-tab-pane>
				<n-tab-pane name="comments" :tab="`Comments (${caseData.comments?.length || 0})`">
					<CaseComments
						:case-data
						@added="handleCommentAdded"
						@updated="handleCommentUpdated"
						@deleted="handleCommentDeleted"
					/>
				</n-tab-pane>
			</n-tabs>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { CaseAssignedUpdateSuccessPayload } from "../CaseAssignedSelect.vue"
import type { CaseStatusUpdateSuccessPayload } from "../CaseStatusSelect.vue"
import type { Case } from "@/types/cases"
import type { CommentItem } from "@/types/comments"
import type { ApiError } from "@/types/common"
import { NAlert, NSpin, NTabPane, NTabs } from "naive-ui"
import { ref, watch } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"
import CaseAlerts from "./CaseAlerts.vue"
import CaseComments from "./CaseComments.vue"
import CaseFiles from "./CaseFiles.vue"
import CaseOverview from "./CaseOverview.vue"

const props = defineProps<{
	caseId: number | null
}>()

const emit = defineEmits<{
	(e: "statusUpdated", value: CaseStatusUpdateSuccessPayload): void
	(e: "assignedToUpdated", value: CaseAssignedUpdateSuccessPayload): void
}>()

const caseData = ref<Case | null>(null)
const detailsError = ref<string | null>(null)
const loadingDetails = ref(false)

async function loadCaseDetails() {
	if (props.caseId === null) return

	loadingDetails.value = true
	detailsError.value = null

	try {
		const response = await Api.cases.getCase(props.caseId)
		caseData.value = response.data.cases[0] || null
		if (!caseData.value) {
			detailsError.value = "Case not found."
		}
	} catch (err) {
		detailsError.value = getApiErrorMessage(err as ApiError)
	} finally {
		loadingDetails.value = false
	}
}

function handleCommentAdded(comment: CommentItem) {
	if (!caseData.value) return

	if (!caseData.value.comments) {
		caseData.value.comments = []
	}
	caseData.value.comments.push(comment)
}

function handleCommentUpdated(comment: CommentItem) {
	if (!caseData.value) return
	caseData.value.comments = caseData.value.comments.map(c => (c.id === comment.id ? comment : c))
}

function handleCommentDeleted(commentId: number) {
	if (!caseData.value) return
	caseData.value.comments = caseData.value.comments.filter(c => c.id !== commentId)
}

function handleStatusUpdated(payload: CaseStatusUpdateSuccessPayload) {
	if (!caseData.value) return
	caseData.value.case_status = payload.status
	emit("statusUpdated", payload)
}

function handleAssignedToUpdated(payload: CaseAssignedUpdateSuccessPayload) {
	if (!caseData.value) return
	caseData.value.assigned_to = payload.assignedTo
	emit("assignedToUpdated", payload)
}

function handleAlertUpdated() {
	loadCaseDetails()
}

watch(
	() => props.caseId,
	async newCaseId => {
		caseData.value = null
		detailsError.value = null

		if (newCaseId !== null) {
			await loadCaseDetails()
		}
	},
	{ immediate: true }
)
</script>
