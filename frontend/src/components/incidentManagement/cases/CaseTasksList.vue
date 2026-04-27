<template>
	<div class="case-tasks-list flex flex-col gap-4">
		<!-- Header: counts + actions -->
		<div class="flex items-center justify-between gap-4">
			<div class="flex items-center gap-3 text-sm">
				<n-tag :bordered="false" type="info" size="small">
					{{ tasks.length }} task{{ tasks.length === 1 ? "" : "s" }}
				</n-tag>
				<n-tag v-if="mandatoryIncomplete > 0" :bordered="false" type="warning" size="small">
					{{ mandatoryIncomplete }} mandatory incomplete
				</n-tag>
				<n-tag v-if="totalDone > 0" :bordered="false" type="success" size="small">
					{{ totalDone }} / {{ tasks.length }} done
				</n-tag>
			</div>
			<div v-if="canEdit" class="flex items-center gap-2">
				<n-button size="small" @click="openApplyTemplate">
					<template #icon>
						<Icon :name="ApplyIcon" :size="14" />
					</template>
					Apply template
				</n-button>
				<n-button size="small" type="primary" @click="openAddTask">
					<template #icon>
						<Icon :name="AddIcon" :size="14" />
					</template>
					Add task
				</n-button>
			</div>
		</div>

		<n-divider class="!my-1" />

		<!-- Task list -->
		<n-spin :show="loading">
			<div v-if="tasks.length" class="flex flex-col gap-3">
				<div
					v-for="task in tasks"
					:key="task.id"
					class="task-card border-border rounded-md border p-4"
					:class="{
						'task-card--done': task.status === 'DONE',
						'task-card--skipped': task.status === 'NOT_NECESSARY'
					}"
				>
					<div class="flex flex-wrap items-start justify-between gap-3">
						<div class="flex flex-1 flex-col gap-1">
							<div class="flex items-center gap-2">
								<span class="font-medium">{{ task.title }}</span>
								<n-tag v-if="task.mandatory" :bordered="false" type="error" size="tiny">
									mandatory
								</n-tag>
								<n-tag
									v-if="task.template_task_id == null"
									:bordered="false"
									type="default"
									size="tiny"
								>
									custom
								</n-tag>
							</div>
							<p v-if="task.description" class="text-secondary text-sm">{{ task.description }}</p>
						</div>

						<!-- Status pill / dropdown -->
						<div class="flex shrink-0 items-center gap-2">
							<n-select
								v-if="canEdit"
								:value="task.status"
								:options="statusOptionsFor(task)"
								size="small"
								style="width: 160px"
								@update:value="onStatusChange(task, $event)"
							/>
							<n-tag v-else :bordered="false" :type="statusTagType(task.status)" size="small">
								{{ statusLabel(task.status) }}
							</n-tag>
							<n-button
								v-if="canEdit && task.template_task_id == null"
								size="tiny"
								quaternary
								type="error"
								@click="confirmDelete(task)"
							>
								<template #icon>
									<Icon :name="DeleteIcon" :size="14" />
								</template>
							</n-button>
						</div>
					</div>

					<!-- Guidelines (collapsible) -->
					<div v-if="task.guidelines" class="mt-3">
						<details class="text-sm">
							<summary class="cursor-pointer font-medium">Guidelines</summary>
							<p class="text-secondary mt-1 whitespace-pre-line">{{ task.guidelines }}</p>
						</details>
					</div>

					<!-- Evidence comment -->
					<div class="mt-3">
						<div class="text-secondary mb-1 text-xs uppercase">Evidence / notes</div>
						<n-input
							v-if="canEdit"
							:value="task.evidence_comment ?? ''"
							type="textarea"
							placeholder="Logs, command output, links — what proves this was done?"
							:autosize="{ minRows: 2, maxRows: 8 }"
							@blur="onCommentBlur(task, ($event.target as HTMLTextAreaElement).value)"
						/>
						<p v-else-if="task.evidence_comment" class="whitespace-pre-line text-sm">
							{{ task.evidence_comment }}
						</p>
						<p v-else class="text-tertiary text-sm italic">No notes recorded</p>
					</div>

					<!-- Audit footer -->
					<div class="text-tertiary mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs">
						<span v-if="task.completed_by">
							{{ task.status === "DONE" ? "Completed" : "Marked" }} by
							<strong>{{ task.completed_by }}</strong>
							<template v-if="task.completed_at"> · {{ formatDateTime(task.completed_at) }}</template>
						</span>
						<span v-else>Created by <strong>{{ task.created_by }}</strong></span>
					</div>
				</div>
			</div>
			<n-empty v-else-if="!loading" description="No tasks on this case" class="h-32 justify-center" />
		</n-spin>

		<!-- Add custom task modal (analyst only) -->
		<n-modal v-model:show="showAddModal" preset="card" title="Add custom task" style="max-width: 560px">
			<n-form ref="addFormRef" :model="addForm" :rules="addFormRules" label-placement="top">
				<n-form-item label="Title" path="title">
					<n-input v-model:value="addForm.title" placeholder="What needs to be done?" />
				</n-form-item>
				<n-form-item label="Description (optional)" path="description">
					<n-input
						v-model:value="addForm.description"
						type="textarea"
						:autosize="{ minRows: 2, maxRows: 4 }"
					/>
				</n-form-item>
				<n-form-item label="Guidelines (optional)" path="guidelines">
					<n-input
						v-model:value="addForm.guidelines"
						type="textarea"
						placeholder="Best practices / steps to follow"
						:autosize="{ minRows: 2, maxRows: 6 }"
					/>
				</n-form-item>
				<n-form-item path="mandatory">
					<n-checkbox v-model:checked="addForm.mandatory">
						Mandatory (blocks close-with-warning)
					</n-checkbox>
				</n-form-item>
			</n-form>
			<template #footer>
				<div class="flex justify-end gap-2">
					<n-button @click="showAddModal = false">Cancel</n-button>
					<n-button type="primary" :loading="addSubmitting" @click="submitAddTask">Add task</n-button>
				</div>
			</template>
		</n-modal>

		<!-- Apply template modal -->
		<n-modal v-model:show="showApplyModal" preset="card" title="Apply template" style="max-width: 520px">
			<n-spin :show="loadingTemplates">
				<n-form label-placement="top">
					<n-form-item label="Template">
						<n-select
							v-model:value="selectedTemplateId"
							:options="templateOptions"
							placeholder="Pick a template to apply"
							filterable
						/>
					</n-form-item>
					<p class="text-secondary text-xs">
						Adds the template's tasks to this case. Existing tasks are preserved — you can layer
						multiple templates over a single investigation.
					</p>
				</n-form>
			</n-spin>
			<template #footer>
				<div class="flex justify-end gap-2">
					<n-button @click="showApplyModal = false">Cancel</n-button>
					<n-button
						type="primary"
						:loading="applySubmitting"
						:disabled="selectedTemplateId == null"
						@click="submitApplyTemplate"
					>
						Apply
					</n-button>
				</div>
			</template>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { FormInst, FormRules } from "naive-ui"
import type {
	CaseTask,
	CaseTaskStatus,
	CaseTemplate
} from "@/types/incidentManagement/caseTemplates.d"
import {
	NButton,
	NCheckbox,
	NDivider,
	NEmpty,
	NForm,
	NFormItem,
	NInput,
	NModal,
	NSelect,
	NSpin,
	NTag,
	useDialog,
	useMessage
} from "naive-ui"
import { computed, onMounted, ref } from "vue"
import Icon from "@/components/common/Icon.vue"
import Api from "@/api"
import { formatDate } from "@/utils/format"

const props = defineProps<{
	caseId: number
	customerCode?: string | null
	canEdit: boolean
}>()
const emit = defineEmits<{
	(e: "tasks-changed", tasks: CaseTask[]): void
}>()

// Icons
const AddIcon = "carbon:add"
const ApplyIcon = "carbon:flow"
const DeleteIcon = "carbon:trash-can"

const message = useMessage()
const dialog = useDialog()

const tasks = ref<CaseTask[]>([])
const loading = ref(false)

const totalDone = computed(() => tasks.value.filter(t => t.status === "DONE").length)
const mandatoryIncomplete = computed(
	() => tasks.value.filter(t => t.mandatory && t.status !== "DONE").length
)

function statusOptionsFor(task: CaseTask) {
	const opts: { label: string; value: CaseTaskStatus; disabled?: boolean }[] = [
		{ label: "To do", value: "TODO" },
		{ label: "Done", value: "DONE" },
		{ label: "Not necessary", value: "NOT_NECESSARY", disabled: task.mandatory }
	]
	return opts
}

function statusLabel(status: CaseTaskStatus): string {
	return status === "TODO" ? "To do" : status === "DONE" ? "Done" : "Not necessary"
}

function statusTagType(status: CaseTaskStatus) {
	return status === "DONE" ? "success" : status === "NOT_NECESSARY" ? "warning" : "default"
}

function formatDateTime(iso: string): string {
	try {
		return formatDate(iso, "MMM D, YYYY HH:mm") as string
	} catch {
		return iso
	}
}

function fetchTasks() {
	loading.value = true
	Api.incidentManagement.caseTemplates
		.listCaseTasks(props.caseId)
		.then(res => {
			if (res.data.success) {
				tasks.value = res.data.tasks
				emit("tasks-changed", tasks.value)
			} else {
				message.warning(res.data.message)
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "Failed to load case tasks")
		})
		.finally(() => {
			loading.value = false
		})
}

// Status change with optional inline evidence on the textarea
function onStatusChange(task: CaseTask, newStatus: CaseTaskStatus) {
	if (newStatus === task.status) return

	Api.incidentManagement.caseTemplates
		.updateCaseTask(task.id, { status: newStatus })
		.then(res => {
			if (res.data.success && res.data.task) {
				const idx = tasks.value.findIndex(t => t.id === task.id)
				if (idx >= 0) tasks.value[idx] = res.data.task
				emit("tasks-changed", tasks.value)
			} else {
				message.warning(res.data.message || "Status update rejected")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "Failed to update task status")
		})
}

function onCommentBlur(task: CaseTask, value: string) {
	const trimmed = value.trim() === "" ? null : value
	if (trimmed === (task.evidence_comment ?? null)) return

	Api.incidentManagement.caseTemplates
		.updateCaseTask(task.id, { evidence_comment: trimmed })
		.then(res => {
			if (res.data.success && res.data.task) {
				const idx = tasks.value.findIndex(t => t.id === task.id)
				if (idx >= 0) tasks.value[idx] = res.data.task
			} else {
				message.warning(res.data.message)
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "Failed to save evidence comment")
		})
}

// Custom-task add modal
const showAddModal = ref(false)
const addSubmitting = ref(false)
const addFormRef = ref<FormInst | null>(null)
const addForm = ref({
	title: "",
	description: "",
	guidelines: "",
	mandatory: false
})
const addFormRules: FormRules = {
	title: { required: true, message: "Title is required", trigger: "blur" }
}

function openAddTask() {
	addForm.value = { title: "", description: "", guidelines: "", mandatory: false }
	showAddModal.value = true
}

async function submitAddTask() {
	try {
		await addFormRef.value?.validate()
	} catch {
		return
	}
	addSubmitting.value = true
	try {
		const res = await Api.incidentManagement.caseTemplates.addCaseTask(props.caseId, {
			title: addForm.value.title,
			description: addForm.value.description || null,
			guidelines: addForm.value.guidelines || null,
			mandatory: addForm.value.mandatory
		})
		if (res.data.success && res.data.task) {
			tasks.value = [...tasks.value, res.data.task]
			emit("tasks-changed", tasks.value)
			showAddModal.value = false
		} else {
			message.warning(res.data.message)
		}
	} catch (err: any) {
		message.error(err.response?.data?.message || "Failed to add task")
	} finally {
		addSubmitting.value = false
	}
}

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
						tasks.value = tasks.value.filter(t => t.id !== task.id)
						emit("tasks-changed", tasks.value)
					} else {
						message.warning(res.data.message)
					}
				})
				.catch(err => {
					message.error(err.response?.data?.message || "Failed to delete task")
				})
		}
	})
}

// Apply-template modal
const showApplyModal = ref(false)
const applySubmitting = ref(false)
const loadingTemplates = ref(false)
const availableTemplates = ref<CaseTemplate[]>([])
const selectedTemplateId = ref<number | null>(null)

const templateOptions = computed(() =>
	availableTemplates.value.map(t => ({
		label: `${t.name}${t.is_default ? " (default)" : ""}` +
			(t.customer_code ? ` — ${t.customer_code}` : "") +
			(t.source ? ` · ${t.source}` : ""),
		value: t.id
	}))
)

function openApplyTemplate() {
	selectedTemplateId.value = null
	showApplyModal.value = true
	loadingTemplates.value = true
	Api.incidentManagement.caseTemplates
		.listTemplates({
			customerCode: props.customerCode ?? undefined,
			includeGlobal: true
		})
		.then(res => {
			if (res.data.success) {
				availableTemplates.value = res.data.templates
			} else {
				message.warning(res.data.message)
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "Failed to load templates")
		})
		.finally(() => {
			loadingTemplates.value = false
		})
}

async function submitApplyTemplate() {
	if (selectedTemplateId.value == null) return
	applySubmitting.value = true
	try {
		const res = await Api.incidentManagement.caseTemplates.applyTemplateToCase(
			props.caseId,
			selectedTemplateId.value
		)
		if (res.data.success) {
			message.success(`Applied template — ${res.data.tasks_added} task(s) added`)
			showApplyModal.value = false
			fetchTasks()
		} else {
			message.warning(res.data.message)
		}
	} catch (err: any) {
		message.error(err.response?.data?.message || "Failed to apply template")
	} finally {
		applySubmitting.value = false
	}
}

defineExpose({ refresh: fetchTasks })

onMounted(fetchTasks)
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
