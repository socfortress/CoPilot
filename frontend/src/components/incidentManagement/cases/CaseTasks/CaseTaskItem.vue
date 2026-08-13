<template>
	<CardEntity
		:status="taskData?.status === 'DONE' ? 'success' : taskData?.status === 'NOT_NECESSARY' ? 'warning' : undefined"
		:embedded
		:hide-header-extra="!taskData"
		:hide-main-extra="!taskData"
		:hide-footer="!taskData"
	>
		<template #headerMain>
			<div class="flex flex-wrap items-center gap-3">
				<span class="text-default font-sans text-base">
					{{ taskData?.title }}
				</span>

				<n-tag v-if="taskData?.mandatory" :bordered="false" type="error" size="small">mandatory</n-tag>
				<n-tag v-if="taskData?.template_task_id == null" :bordered="false" type="default" size="small">
					custom
				</n-tag>
			</div>
		</template>
		<template #headerExtra>
			<n-select
				v-if="canEdit && taskData"
				v-model:value="taskData.status"
				:options="statusOptions"
				:status="
					taskData.status === 'DONE' ? 'success' : taskData.status === 'NOT_NECESSARY' ? 'warning' : undefined
				"
				size="small"
				class="w-38!"
				:consistent-menu-width="false"
				:loading="savingStatus"
			/>
			<n-tag v-else-if="taskData" :bordered="false" :type="statusTagType(taskData.status)" size="small">
				{{ statusLabel(taskData.status) }}
			</n-tag>
		</template>
		<template #default>
			<div class="flex flex-col gap-3">
				<p v-if="taskData?.description" class="text-secondary text-sm">{{ taskData.description }}</p>

				<details v-if="taskData?.guidelines" class="text-sm">
					<summary class="cursor-pointer font-medium">Guidelines</summary>
					<p class="text-secondary mt-1 whitespace-pre-line">{{ taskData.guidelines }}</p>
				</details>
			</div>
		</template>
		<template #mainExtra>
			<div class="flex flex-col gap-1">
				<div class="flex items-center justify-between">
					<div class="text-secondary text-xs uppercase">Evidence / notes</div>

					<div
						class="text-secondary text-right text-xs opacity-0 transition-opacity duration-300"
						:class="{ 'animate-pulse opacity-100': savingEvidenceComment }"
					>
						saving...
					</div>
				</div>
				<div v-if="canEdit && taskData" class="flex flex-col gap-1">
					<n-input
						v-model:value="taskData.evidence_comment"
						type="textarea"
						clearable
						placeholder="Logs, command output, links — what proves this was done?"
						:autosize="{ minRows: 2, maxRows: 8 }"
					/>
				</div>
				<p v-else-if="taskData?.evidence_comment" class="text-sm whitespace-pre-line">
					{{ taskData.evidence_comment }}
				</p>
				<p v-else class="text-tertiary text-sm italic">No notes recorded</p>
			</div>
		</template>
		<template #footer>
			<div v-if="taskData" class="flex flex-wrap items-center justify-between gap-2">
				<div class="text-secondary flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
					<div class="flex items-center gap-2">
						<span class="text-secondary text-xs uppercase">Assignee</span>
						<n-select
							v-if="canEdit"
							v-model:value="assignee"
							:options="assigneeOptions"
							:loading="loadingUsers || savingAssignee"
							size="tiny"
							class="w-44!"
							clearable
							filterable
							placeholder="Unassigned"
							:consistent-menu-width="false"
							@update:show="onAssigneeDropdown"
						/>
						<strong v-else-if="taskData.assigned_to">{{ taskData.assigned_to }}</strong>
						<span v-else class="text-tertiary italic">Unassigned</span>
					</div>

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

				<div>
					<div class="flex items-center justify-end gap-2">
						<n-button
							v-if="canEdit && taskData.template_task_id == null"
							size="tiny"
							quaternary
							type="error"
							:loading="deleting"
							@click="confirmDelete(taskData)"
						>
							<template #icon>
								<Icon :name="DeleteIcon" />
							</template>
							Delete
						</n-button>
					</div>
				</div>
			</div>
		</template>
	</CardEntity>
</template>

<script setup lang="ts">
import type { Ref } from "vue"
import type { ApiError } from "@/types/common"
import type { CaseTask, CaseTaskStatus } from "@/types/incidentManagement/case-templates"
import { useDebounceFn } from "@vueuse/core"
import axios from "axios"
import { NButton, NInput, NSelect, NTag, useDialog, useMessage } from "naive-ui"
import { computed, inject, onBeforeUnmount, ref, watch } from "vue"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"

const props = defineProps<{
	task: CaseTask
	caseId: number
	canEdit: boolean
	embedded?: boolean
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
const savingAssignee = ref(false)
const deleting = ref(false)

// Provided by CasesList / AlertsList. Falls back to an empty ref when this card
// is rendered outside those providers, in which case we lazily fetch on first
// dropdown open — one request per card, but only for cards actually interacted
// with, rather than N requests on mount.
const injectedUsers = inject<Ref<string[]>>("assignable-users", ref([]))
const loadingUsers = ref(false)
const fetchedUsers = ref<string[]>([])
const assignee = ref<string | null>(props.task.assigned_to ?? null)

const assigneeOptions = computed(() => {
	const names = injectedUsers.value.length ? injectedUsers.value : fetchedUsers.value
	const merged = new Set(names)
	// Keep the current assignee selectable even if they're no longer in the
	// assignable list (deactivated user) — otherwise the select renders blank
	// and the next save would silently unassign them.
	if (assignee.value) merged.add(assignee.value)
	return [...merged].map(name => ({ label: name, value: name }))
})

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
let assigneeAbortController = new AbortController()

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
}, 250)

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

function onAssigneeDropdown(show: boolean) {
	if (!show || injectedUsers.value.length || fetchedUsers.value.length || loadingUsers.value) return

	loadingUsers.value = true
	Api.incidentManagement.alerts
		.getAvailableUsers()
		.then(res => {
			if (res.data.success) {
				fetchedUsers.value = res.data?.available_users || []
			} else {
				message.warning(res.data?.message || "Could not load users")
			}
		})
		.catch(err => {
			message.error(getApiErrorMessage(err as ApiError) || "Could not load users")
		})
		.finally(() => {
			loadingUsers.value = false
		})
}

// Assignment is sent as an explicit key on every change, including null — the
// backend reads key *presence* to distinguish "unassign" from "leave alone", so
// omitting it here would make clearing the select a silent no-op.
const onAssigneeChange = useDebounceFn((value: string | null) => {
	if (!taskData.value) return

	assigneeAbortController.abort()
	assigneeAbortController = new AbortController()
	savingAssignee.value = true

	Api.incidentManagement.caseTemplates
		.updateCaseTask(taskData.value.id, { assigned_to: value }, assigneeAbortController.signal)
		.then(res => {
			if (res.data.success && res.data.task) {
				// Track the accepted value locally: the watcher guard compares
				// against it to decide whether a change still needs saving, so
				// leaving it stale would block the next edit.
				if (taskData.value) taskData.value.assigned_to = res.data.task.assigned_to ?? null
				emit("updated", res.data.task)
			} else {
				// Rejected (e.g. unknown user) — roll the select back so it
				// doesn't show an assignment the server never accepted.
				assignee.value = taskData.value?.assigned_to ?? null
				message.warning(res.data.message || "Assignment rejected")
			}
			savingAssignee.value = false
		})
		.catch(err => {
			if (!axios.isCancel(err)) {
				savingAssignee.value = false
				assignee.value = taskData.value?.assigned_to ?? null
				message.error(getApiErrorMessage(err as ApiError) || "Failed to update assignee")
			}
		})
}, 250)

// Custom-task delete (analysts can only delete custom tasks via the chip — keeps
// template-derived audit trails intact unless an admin really wants to nuke it).
function confirmDelete(task: CaseTask) {
	dialog.warning({
		title: "Delete task?",
		content: `"${task.title}" will be removed from this case.`,
		positiveText: "Delete",
		negativeText: "Cancel",
		onPositiveClick: () => {
			deleting.value = true

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
				.finally(() => {
					deleting.value = false
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

watch(assignee, (val, prev) => {
	// Guard on an actual change: the rollback paths above reassign this ref, and
	// without the guard that would re-fire the request in a loop.
	if (val === prev) return
	if (val === (taskData.value?.assigned_to ?? null)) return
	onAssigneeChange(val)
})

// Cancel anything still in flight when this component goes away: without it the
// request outlives the view — the backend keeps working for a page nobody is
// looking at, and the response resolves into a destroyed scope (#1072).
onBeforeUnmount(() => {
	statusAbortController?.abort()
	evidenceCommentAbortController?.abort()
	assigneeAbortController?.abort()
})
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
