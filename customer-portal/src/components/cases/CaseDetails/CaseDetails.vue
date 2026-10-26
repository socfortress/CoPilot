<template>
	<n-spin :show="loadingDetails">
		<div class="@container min-h-50">
			<n-alert v-if="detailsError" :title="$t('cases.caseDetails.error')" type="error" :description="detailsError" />

			<template v-else-if="caseData">
				<WaitingOnYouNotice
					v-if="isWaitingOnCustomer(caseData.case_status)"
					entity="case"
					@reply="activeTab = 'comments'"
				/>

				<n-tabs v-model:value="activeTab" type="line" animated>
					<n-tab-pane name="overview" :tab="$t('cases.caseDetails.tabs.overview')">
						<CaseOverview
							:case-data
							@status-updated="handleStatusUpdated"
							@assigned-to-updated="handleAssignedToUpdated"
						/>
					</n-tab-pane>
					<n-tab-pane
						name="alerts"
						:tab="
							$t('cases.caseDetails.tabs.alerts', {
								count: caseData?.alerts?.length || caseData?.alert_ids?.length || 0
							})
						"
					>
						<CaseAlerts
							:case-data
							@updated="handleAlertUpdated"
							@unlinked="handleAlertUnlinked"
							@linked="handleAlertLinked"
						/>
					</n-tab-pane>
					<n-tab-pane name="tasks" :tab="$t('cases.caseDetails.tabs.tasks')">
						<CaseTasks :case-id="caseData.id" />
					</n-tab-pane>
					<n-tab-pane name="timeline" :tab="$t('cases.caseDetails.tabs.timeline')">
						<CaseTimeline :case-id="caseData.id" />
					</n-tab-pane>
					<n-tab-pane name="files" :tab="$t('cases.caseDetails.tabs.files')">
						<CaseFiles :case-id="caseData.id" />
					</n-tab-pane>
					<!-- Gated by the customer's Ask the SOC switch, managed by the SOC in CoPilot (#1305). -->
					<n-tab-pane v-if="askSocEnabled" name="ask-soc" tab="Ask the SOC" display-directive="show:lazy">
						<AskSoc entity="case" :entity-id="caseData.id" @asked="handleAsked" />
					</n-tab-pane>
					<n-tab-pane name="comments" :tab="$t('cases.caseDetails.tabs.comments', { count: caseData.comments?.length || 0 })">
						<CaseComments
							:case-data
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
import type { CaseAssignedUpdateSuccessPayload } from "../CaseAssignedSelect.vue"
import type { CaseStatusUpdateSuccessPayload } from "../CaseStatusSelect.vue"
import type { Case } from "@/types/cases"
import type { CommentItem } from "@/types/comments"
import type { ApiError } from "@/types/common"
import { NAlert, NSpin, NTabPane, NTabs } from "naive-ui"
import { ref, watch } from "vue"
import { useI18n } from "vue-i18n"
import Api from "@/api"
import WaitingOnYouNotice from "@/components/common/WaitingOnYouNotice.vue"
import AskSoc from "@/components/socRequests/AskSoc.vue"
import { useSocRequestsAvailability } from "@/composables/common/useSocRequestsAvailability"
import { getApiErrorMessage } from "@/utils"
import { isWaitingOnCustomer } from "@/utils/workflowStatus"
import CaseAlerts from "./CaseAlerts.vue"
import CaseComments from "./CaseComments.vue"
import CaseFiles from "./CaseFiles.vue"
import CaseOverview from "./CaseOverview.vue"
import CaseTasks from "./CaseTasks.vue"
import CaseTimeline from "./CaseTimeline.vue"

const props = defineProps<{
	caseId: number | null
}>()

const emit = defineEmits<{
	(e: "statusUpdated", value: CaseStatusUpdateSuccessPayload): void
	(e: "assignedToUpdated", value: CaseAssignedUpdateSuccessPayload): void
}>()

const { t } = useI18n()
const caseData = ref<Case | null>(null)
const detailsError = ref<string | null>(null)
const loadingDetails = ref(false)
const activeTab = ref("overview")
const askSocEnabled = ref(false)

const { isEnabledFor: isAskSocEnabledFor } = useSocRequestsAvailability()

async function loadCaseDetails() {
	if (props.caseId === null) return

	loadingDetails.value = true
	detailsError.value = null

	try {
		const response = await Api.cases.getCase(props.caseId)
		caseData.value = response.data.cases[0] || null
		if (!caseData.value) {
			detailsError.value = t("cases.caseDetails.notFound")
		}
	} catch (err) {
		detailsError.value = getApiErrorMessage(err as ApiError)
	} finally {
		loadingDetails.value = false
	}

	// Checked against the case's own customer: a portal user may be scoped to more than one.
	askSocEnabled.value = caseData.value ? await isAskSocEnabledFor(caseData.value.customer_code) : false
}

// A question is a comment signed by the user: read the case again. A comment hands a case
// the SOC waits on back to it, so tell the list.
async function handleAsked() {
	const wasWaiting = caseData.value ? isWaitingOnCustomer(caseData.value.case_status) : false
	await loadCaseDetails()
	if (wasWaiting && caseData.value && !isWaitingOnCustomer(caseData.value.case_status)) {
		emit("statusUpdated", { caseId: caseData.value.id, status: caseData.value.case_status })
	}
}

async function handleCommentAdded(comment: CommentItem) {
	if (!caseData.value) return

	if (!caseData.value.comments) {
		caseData.value.comments = []
	}
	caseData.value.comments.push(comment)

	// Replying to a case the SOC waits on hands it back, with the alerts waiting with it
	// (the backend moves them to IN_PROGRESS): read the new state, and tell the list.
	if (isWaitingOnCustomer(caseData.value.case_status)) {
		await loadCaseDetails()
		if (caseData.value && !isWaitingOnCustomer(caseData.value.case_status)) {
			emit("statusUpdated", { caseId: caseData.value.id, status: caseData.value.case_status })
		}
	}
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

watch(
	() => props.caseId,
	async newCaseId => {
		caseData.value = null
		detailsError.value = null
		askSocEnabled.value = false
		activeTab.value = "overview"

		if (newCaseId !== null) {
			await loadCaseDetails()
		}
	},
	{ immediate: true }
)
</script>
