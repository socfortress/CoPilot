<template>
	<div
		class="task-card border-border rounded-md border p-4"
		:class="{
			'task-card--done': taskData?.status === 'DONE',
			'task-card--skipped': taskData?.status === 'NOT_NECESSARY'
		}"
	>
		<div v-if="taskData" class="flex flex-wrap items-start justify-between gap-3">
			<div class="flex flex-1 flex-col gap-1">
				<div class="flex items-center gap-2">
					<span class="font-medium">{{ taskData.title }}</span>
					<n-tag v-if="taskData.mandatory" :bordered="false" type="error" size="tiny">mandatory</n-tag>
					<n-tag v-if="taskData.template_task_id == null" :bordered="false" type="default" size="tiny">
						custom
					</n-tag>
				</div>
				<p v-if="taskData.description" class="text-secondary text-sm">{{ taskData.description }}</p>
			</div>

			<!-- Status pill / dropdown -->
			<div class="flex shrink-0 items-center gap-2">
				<n-select
					v-if="canEdit"
					v-model:value="taskData.status"
					:options="statusOptions"
					size="small"
					class="w-48"
					:loading="savingStatus"
				/>
				<n-tag v-else :bordered="false" :type="statusTagType(taskData.status)" size="small">
					{{ statusLabel(taskData.status) }}
				</n-tag>
				<n-button
					v-if="canEdit && taskData.template_task_id == null"
					size="tiny"
					quaternary
					type="error"
					@click="confirmDelete(taskData)"
				>
					<template #icon>
						<Icon :name="DeleteIcon" :size="14" />
					</template>
				</n-button>
			</div>
		</div>

		<!-- Guidelines (collapsible) -->
		<div v-if="taskData?.guidelines" class="mt-3">
			<details class="text-sm">
				<summary class="cursor-pointer font-medium">Guidelines</summary>
				<p class="text-secondary mt-1 whitespace-pre-line">{{ taskData.guidelines }}</p>
			</details>
		</div>

		<!-- Evidence comment -->
		<div v-if="taskData" class="mt-3">
			<div class="text-secondary mb-1 text-xs uppercase">Evidence / notes</div>
			<div v-if="canEdit">
				<n-input
					v-model:value="taskData.evidence_comment"
					type="textarea"
					placeholder="Logs, command output, links — what proves this was done?"
					:autosize="{ minRows: 2, maxRows: 8 }"
				/>
				<div v-if="savingEvidenceComment" class="text-secondary animate-pulse text-xs">saving...</div>
			</div>
			<p v-else-if="taskData.evidence_comment" class="text-sm whitespace-pre-line">
				{{ taskData.evidence_comment }}
			</p>
			<p v-else class="text-tertiary text-sm italic">No notes recorded</p>
		</div>

		<!-- Audit footer -->
		<div v-if="taskData" class="text-tertiary mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs">
			<span v-if="taskData.completed_by">
				{{ task.status === "DONE" ? "Completed" : "Marked" }} by
				<strong>{{ taskData.completed_by }}</strong>
				<template v-if="taskData.completed_at">
					· {{ formatDate(taskData.completed_at, dFormats.datetime) }}
				</template>
			</span>
			<span v-else>
				Created by
				<strong>{{ task.created_by }}</strong>
			</span>
		</div>
	</div>
</template>

<script setup lang="ts">
import type { ApiError } from "@/types/common"
import type { CaseTask, CaseTaskStatus } from "@/types/incidentManagement/caseTemplates.d"
import { useDebounceFn } from "@vueuse/core"
import axios from "axios"
import { NButton, NInput, NSelect, NTag, useDialog, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"

const props = defineProps<{
	task: CaseTask
	caseId: number
	canEdit: boolean
}>()

const emit = defineEmits<{
	(e: "updated", value: CaseTask): void
	(e: "deleted"): void
}>()

const DeleteIcon = "carbon:trash-can"

const message = useMessage()
const dialog = useDialog()
const dFormats = useSettingsStore().dateFormat
const taskData = ref<CaseTask | null>(props.task)

const savingStatus = ref(false)
const savingEvidenceComment = ref(false)

const statusOptions = computed(() => {
	const opts: { label: string; value: CaseTaskStatus; disabled?: boolean }[] = [
		{ label: "To do", value: "TODO" },
		{ label: "Done", value: "DONE" },
		{ label: "Not necessary", value: "NOT_NECESSARY", disabled: taskData.value?.mandatory }
	]
	return opts
})

let statusAbortController = new AbortController()
let evidenceCommentAbortController = new AbortController()

function statusLabel(status: CaseTaskStatus): string {
	return status === "TODO" ? "To do" : status === "DONE" ? "Done" : "Not necessary"
}

function statusTagType(status: CaseTaskStatus) {
	return status === "DONE" ? "success" : status === "NOT_NECESSARY" ? "warning" : "default"
}

const onStatusChange = useDebounceFn((newStatus: CaseTaskStatus) => {
	if (!taskData.value) return

	if (statusAbortController) {
		statusAbortController.abort()
	}

	statusAbortController = new AbortController()
	savingStatus.value = true

	Api.incidentManagement.caseTemplates
		.updateCaseTask(taskData.value.id, { status: newStatus }, statusAbortController.signal)
		.then(res => {
			if (res.data.success && res.data.task) {
				emit("updated", res.data.task)
			} else {
				message.warning(res.data.message || "Status update rejected")
			}
			savingStatus.value = false
		})
		.catch(err => {
			if (!axios.isCancel(err)) {
				savingStatus.value = false
				message.error(getApiErrorMessage(err as ApiError) || "Failed to update task status")
			}
		})
}, 500)

const onCommentChange = useDebounceFn((value: string | null) => {
	if (!taskData.value) return

	if (evidenceCommentAbortController) {
		evidenceCommentAbortController.abort()
	}

	evidenceCommentAbortController = new AbortController()
	savingEvidenceComment.value = true

	Api.incidentManagement.caseTemplates
		.updateCaseTask(taskData.value.id, { evidence_comment: value || "" }, evidenceCommentAbortController.signal)
		.then(res => {
			if (res.data.success && res.data.task) {
				emit("updated", res.data.task)
			} else {
				message.warning(res.data.message)
			}
			savingEvidenceComment.value = false
		})
		.catch(err => {
			if (!axios.isCancel(err)) {
				savingEvidenceComment.value = false
				message.error(getApiErrorMessage(err as ApiError) || "Failed to save evidence comment")
			}
		})
}, 500)

// Custom-task delete (analysts can only delete custom tasks via the chip — keeps
// template-derived audit trails intact unless an admin really wants to nuke it).
function confirmDelete(task: CaseTask) {
	dialog.warning({
		title: "Delete task?",
		content: `"${task.title}" will be removed from this case.`,
		positiveText: "Delete",
		negativeText: "Cancel",
		onPositiveClick: () => {
			Api.incidentManagement.caseTemplates
				.deleteCaseTask(task.id)
				.then(res => {
					if (res.data.success) {
						emit("deleted")
					} else {
						message.warning(res.data.message)
					}
				})
				.catch(err => {
					message.error(getApiErrorMessage(err as ApiError) || "Failed to delete task")
				})
		}
	})
}

watch(
	() => taskData.value?.status,
	val => {
		if (val) {
			onStatusChange(val)
		}
	}
)

watch(
	() => taskData.value?.evidence_comment,
	val => {
		onCommentChange(val || null)
	}
)
</script>

<style scoped lang="scss">
.task-card {
	transition: background-color 0.15s ease;

	&--done {
		background-color: rgba(0, 200, 80, 0.05);
	}

	&--skipped {
		background-color: rgba(160, 160, 160, 0.05);
	}
}
</style>
