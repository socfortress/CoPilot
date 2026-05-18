<template>
	<div class="case-tasks-list flex flex-col gap-4">
		<CaseTasksToolbar
			:case-id
			:customer-code
			:can-edit
			:tasks
			:linked-alerts
			@updated="fetchTasks"
		/>

		<n-spin :show="loading">
			<div v-if="tasks.length" class="flex flex-col gap-4">
				<!--
				One group per originating alert plus a "Case-wide" bucket for
				orphaned / never-attached tasks (alert_id IS NULL). Group order:
				alerts in their linked order, case-wide last.
				-->
				<div v-for="group in groups" :key="group.key" class="task-group flex flex-col gap-2">
					<div class="task-group-header flex flex-wrap items-center gap-2">
						<template v-if="group.alert">
							<span class="task-group-title">{{ group.alert.alert_name }}</span>
							<code class="text-tertiary text-xs">{{ group.alert.source }}</code>
							<n-tag size="tiny" :bordered="false">alert #{{ group.alert.id }}</n-tag>
						</template>
						<template v-else>
							<span class="task-group-title">Case-wide / general</span>
							<n-tag size="tiny" :bordered="false" type="info">
								not attached to any alert
							</n-tag>
						</template>
						<n-tag size="tiny" :bordered="false">{{ group.tasks.length }} task(s)</n-tag>
					</div>

					<div class="flex flex-col gap-3 pl-2">
						<CaseTaskItem
							v-for="task in group.tasks"
							:key="task.id"
							:task
							:case-id
							:can-edit
							@deleted="fetchTasks"
							@updated="handleTaskUpdated"
						/>
					</div>
				</div>
			</div>
			<n-empty v-else-if="!loading" description="No tasks on this case" class="h-32 justify-center" />
		</n-spin>
	</div>
</template>

<script setup lang="ts">
import type { Alert } from "@/types/incidentManagement/alerts.d"
import type { CaseTask } from "@/types/incidentManagement/caseTemplates.d"
import { NEmpty, NSpin, NTag, useMessage } from "naive-ui"
import { computed, onBeforeMount, ref } from "vue"
import Api from "@/api"
import CaseTaskItem from "./CaseTaskItem.vue"
import CaseTasksToolbar from "./CaseTasksToolbar.vue"

const props = defineProps<{
	caseId: number
	customerCode?: string | null
	canEdit: boolean
	linkedAlerts?: Alert[]
}>()

const message = useMessage()
const tasks = ref<CaseTask[]>([])
const loading = ref(false)

interface TaskGroup {
	key: string
	alert: Alert | null
	tasks: CaseTask[]
}

const groups = computed<TaskGroup[]>(() => {
	// Index tasks by alert_id so we can attach them to their alert group; tasks
	// whose alert_id no longer matches a linked alert (orphans) fall through
	// to the case-wide bucket alongside genuine alert_id=null tasks.
	const linkedAlerts = props.linkedAlerts || []
	const linkedIds = new Set(linkedAlerts.map(a => a.id))
	const byAlert: Record<number, CaseTask[]> = {}
	const caseWide: CaseTask[] = []

	for (const t of tasks.value) {
		if (t.alert_id != null && linkedIds.has(t.alert_id)) {
			if (!byAlert[t.alert_id]) byAlert[t.alert_id] = []
			byAlert[t.alert_id].push(t)
		} else {
			caseWide.push(t)
		}
	}

	const out: TaskGroup[] = []
	for (const a of linkedAlerts) {
		const groupTasks = byAlert[a.id] || []
		if (!groupTasks.length) continue
		out.push({ key: `alert-${a.id}`, alert: a, tasks: groupTasks })
	}
	if (caseWide.length) {
		out.push({ key: "case-wide", alert: null, tasks: caseWide })
	}
	return out
})

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

<style scoped lang="scss">
.task-group-header {
	padding: 6px 8px;
	background: var(--bg-secondary-color);
	border: 1px solid var(--border-color);
	border-radius: var(--border-radius);
}
.task-group-title {
	font-weight: 600;
	color: var(--fg-default-color);
}
</style>
