<template>
	<div class="case-tasks-list flex flex-col gap-4">
		<CaseTasksToolbar :case-id :customer-code :can-edit :tasks :linked-alerts @updated="fetchTasks" />

		<n-spin :show="loading">
			<div v-if="tasks.length" class="flex flex-col gap-4">
				<!--
				One group per originating alert plus a "Case-wide" bucket for
				orphaned / never-attached tasks (alert_id IS NULL). Group order:
				alerts in their linked order, case-wide last.
				-->
				<CardEntity
					v-for="group in groups"
					:key="group.key"
					embedded
					size="small"
					header-box-class="flex flex-wrap items-center gap-2"
				>
					<template #header>
						<div v-if="group.alert" class="flex flex-wrap items-center gap-2">
							<span class="text-default text-base font-semibold">{{ group.alert.alert_name }}</span>
							<n-tag size="small" :bordered="false">{{ group.alert.source }}</n-tag>
							<n-tag size="small" :bordered="false">alert #{{ group.alert.id }}</n-tag>
							<n-tag size="small" :bordered="false">{{ group.tasks.length }} task(s)</n-tag>
						</div>
						<div v-else class="flex flex-wrap items-center gap-2">
							<span class="text-default text-base font-semibold">Case-wide / general</span>
							<n-tag size="small" :bordered="false" type="info">not attached to any alert</n-tag>
							<n-tag size="small" :bordered="false">{{ group.tasks.length }} task(s)</n-tag>
						</div>
					</template>
					<template #mainExtra>
						<div class="flex flex-col gap-3">
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
					</template>
				</CardEntity>
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
import CardEntity from "@/components/common/cards/CardEntity.vue"
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
