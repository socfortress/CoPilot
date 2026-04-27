<template>
	<div class="case-tasks-list flex flex-col gap-4">
		<CaseTasksToolbar :case-id :customer-code :can-edit :tasks @updated="fetchTasks" />

		<n-spin :show="loading">
			<div v-if="tasks.length" class="flex flex-col gap-3">
				<CaseTaskItem
					v-for="task in tasks"
					:key="task.id"
					:task
					:case-id
					:can-edit
					@deleted="fetchTasks"
					@updated="handleTaskUpdated"
				/>
			</div>
			<n-empty v-else-if="!loading" description="No tasks on this case" class="h-32 justify-center" />
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { CaseTask } from "@/types/incidentManagement/caseTemplates.d"
import { NEmpty, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref } from "vue"
import Api from "@/api"
import CaseTaskItem from "./CaseTaskItem.vue"
import CaseTasksToolbar from "./CaseTasksToolbar.vue"

const props = defineProps<{
	caseId: number
	customerCode?: string | null
	canEdit: boolean
}>()

const message = useMessage()
const tasks = ref<CaseTask[]>([])
const loading = ref(false)

function fetchTasks() {
	loading.value = true
	Api.incidentManagement.caseTemplates
		.listCaseTasks(props.caseId)
		.then(res => {
			if (res.data.success) {
				tasks.value = res.data.tasks
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

function handleTaskUpdated(task: CaseTask) {
	tasks.value = tasks.value.map(t => (t.id === task.id ? task : t))
}

onBeforeMount(fetchTasks)
</script>
