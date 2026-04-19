<template>
	<n-spin :show="loadingDetails">
		<div class="@container min-h-50">
			<n-alert v-if="detailsError" title="Error" type="error" :description="detailsError" />

			<n-tabs v-else-if="caseData" type="line" animated>
				<n-tab-pane name="overview" tab="Overview">
					<div class="flex flex-col gap-4">
						<CaseOverview
							:case-data
							@status-updated="handleStatusUpdated"
							@assigned-to-updated="handleAssignedToUpdated"
						/>
						<div class="flex justify-end">
							<n-popconfirm to="body" @positive-click="handleDeleteCase">
								<template #trigger>
									<n-button
										size="small"
										:focusable="false"
										:loading="deleting"
										type="error"
										secondary
									>
										<template #icon>
											<Icon name="carbon:trash-can" />
										</template>
										Delete Case
									</n-button>
								</template>
								Are you sure you want to delete this case?
							</n-popconfirm>
						</div>
					</div>
				</n-tab-pane>
				<n-tab-pane
					name="alerts"
					:tab="`Alerts (${caseData?.alerts?.length || caseData?.alert_ids?.length || 0})`"
				>
					<CaseAlerts
						:case-data
						@updated="handleAlertUpdated"
						@unlinked="handleAlertUnlinked"
						@linked="handleAlertLinked"
					/>
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
import { NAlert, NButton, NPopconfirm, NSpin, NTabPane, NTabs, useMessage } from "naive-ui"
import { ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
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
	(e: "deleted"): void
}>()

const message = useMessage()
const caseData = ref<Case | null>(null)
const detailsError = ref<string | null>(null)
const loadingDetails = ref(false)
const deleting = ref(false)

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

function handleAlertUnlinked() {
	loadCaseDetails()
}

function handleAlertLinked() {
	loadCaseDetails()
}

function handleDeleteCase() {
	if (!caseData.value) return

	deleting.value = true

	Api.cases
		.deleteCase(caseData.value.id)
		.then(res => {
			if (res.data.success) {
				message.success("Case deleted successfully")
				emit("deleted")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError))
		})
		.finally(() => {
			deleting.value = false
		})
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
