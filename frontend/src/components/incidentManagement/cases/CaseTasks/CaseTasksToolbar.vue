<template>
	<div>
		<!-- Header: counts + actions -->
		<div class="flex items-center justify-between gap-4">
			<div class="flex items-center gap-3 text-sm">
				<Badge type="splitted">
					<template #label>Tasks</template>
					<template #value>
						{{ tasks.length }}
					</template>
				</Badge>
				<Badge v-if="mandatoryIncomplete > 0" color="warning" type="splitted" bright>
					<template #label>Mandatory incomplete</template>
					<template #value>
						{{ mandatoryIncomplete }}
					</template>
				</Badge>
				<Badge v-if="totalDone > 0" color="success" type="splitted" bright>
					<template #label>Done</template>
					<template #value>{{ totalDone }} / {{ tasks.length }}</template>
				</Badge>
			</div>
			<div v-if="canEdit" class="flex items-center gap-2">
				<n-button size="small" @click="openApplyTemplate">
					<template #icon>
						<Icon :name="ApplyIcon" />
					</template>
					Apply template
				</n-button>
				<n-button size="small" type="primary" @click="openAddTask">
					<template #icon>
						<Icon :name="AddIcon" />
					</template>
					Add task
				</n-button>
			</div>
		</div>

		<!-- Add custom task modal -->
		<n-modal
			v-model:show="showAddModal"
			preset="card"
			display-directive="show"
			title="Add custom task"
			:style="{ maxWidth: 'min(600px, 90vw)', minHeight: 'min(300px, 90vh)', overflow: 'hidden' }"
		>
			<CaseTasksCreateForm :case-id @success="handleAddTaskSuccess" />
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
						Adds the template's tasks to this case. Existing tasks are preserved — you can layer multiple
						templates over a single investigation.
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
import type { ApiError } from "@/types/common"
import type { CaseTask, CaseTemplate } from "@/types/incidentManagement/caseTemplates.d"
import { NButton, NForm, NFormItem, NModal, NSelect, NSpin, useMessage } from "naive-ui"
import { computed, ref } from "vue"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import Icon from "@/components/common/Icon.vue"
import { getApiErrorMessage } from "@/utils"
import CaseTasksCreateForm from "./CaseTasksCreateForm.vue"

const props = defineProps<{
	caseId: number
	customerCode?: string | null
	canEdit: boolean
	tasks: CaseTask[]
}>()

const emit = defineEmits<{
	(e: "updated"): void
}>()

// Icons
const AddIcon = "carbon:add"
const ApplyIcon = "carbon:flow"

const message = useMessage()

const totalDone = computed(() => props.tasks.filter(t => t.status === "DONE").length)
const mandatoryIncomplete = computed(() => props.tasks.filter(t => t.mandatory && t.status !== "DONE").length)

// Custom-task add modal
const showAddModal = ref(false)
const addForm = ref({
	title: "",
	description: "",
	guidelines: "",
	mandatory: false
})

function openAddTask() {
	addForm.value = { title: "", description: "", guidelines: "", mandatory: false }
	showAddModal.value = true
}

// Apply-template modal
const showApplyModal = ref(false)
const applySubmitting = ref(false)
const loadingTemplates = ref(false)
const availableTemplates = ref<CaseTemplate[]>([])
const selectedTemplateId = ref<number | null>(null)

const templateOptions = computed(() =>
	availableTemplates.value.map(t => ({
		label: `${t.name}${t.is_default ? " (default)" : ""}${
			t.customer_code ? ` — ${t.customer_code}` : ""
		}${t.source ? ` · ${t.source}` : ""}`,
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
			emit("updated")
		} else {
			message.warning(res.data.message)
		}
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError) || "Failed to apply template")
	} finally {
		applySubmitting.value = false
	}
}

function handleAddTaskSuccess() {
	emit("updated")
	showAddModal.value = false
}
</script>
