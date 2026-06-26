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
					<template #value>{{ totalDone }}</template>
				</Badge>
			</div>
			<div v-if="canEdit" class="flex items-center gap-2">
				<n-button size="small" secondary @click="openApplyTemplate">
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
			:style="{ maxWidth: 'min(600px, 90vw)', overflow: 'hidden' }"
		>
			<CaseTasksCreateForm :case-id :linked-alerts="linkedAlerts || []" @success="handleAddTaskSuccess" />
		</n-modal>

		<!-- Apply template modal -->
		<n-modal
			v-model:show="showApplyModal"
			preset="card"
			display-directive="show"
			title="Apply template"
			:style="{ maxWidth: 'min(600px, 90vw)', overflow: 'hidden' }"
		>
			<CaseTasksToolbarApplyTemplateForm :case-id :customer-code @success="handleApplyTemplateSuccess" />
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { Alert } from "@/types/incidentManagement/alerts"
import type { CaseTask } from "@/types/incidentManagement/case-templates"
import { NButton, NModal } from "naive-ui"
import { computed, ref } from "vue"
import Badge from "@/components/common/Badge.vue"
import Icon from "@/components/common/Icon.vue"
import CaseTasksCreateForm from "./CaseTasksCreateForm.vue"
import CaseTasksToolbarApplyTemplateForm from "./CaseTasksToolbarApplyTemplateForm.vue"

const props = defineProps<{
	caseId: number
	customerCode?: string | null
	canEdit: boolean
	tasks: CaseTask[]
	linkedAlerts?: Alert[]
}>()

const emit = defineEmits<{
	(e: "updated"): void
}>()

const AddIcon = "carbon:add"
const ApplyIcon = "carbon:flow"

const totalDone = computed(() => props.tasks.filter(t => t.status === "DONE").length)
const mandatoryIncomplete = computed(() => props.tasks.filter(t => t.mandatory && t.status !== "DONE").length)

const showAddModal = ref(false)
const showApplyModal = ref(false)

function openAddTask() {
	showAddModal.value = true
}

function openApplyTemplate() {
	showApplyModal.value = true
}

function handleAddTaskSuccess() {
	emit("updated")
	showAddModal.value = false
}

function handleApplyTemplateSuccess() {
	emit("updated")
	showApplyModal.value = false
}
</script>
