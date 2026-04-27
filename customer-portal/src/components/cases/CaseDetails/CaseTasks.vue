<template>
	<n-spin :show="loading">
		<div class="flex flex-col gap-3">
			<div class="flex items-center gap-3 text-sm">
				<n-tag :bordered="false" type="info" size="small">
					{{ tasks.length }} task{{ tasks.length === 1 ? "" : "s" }}
				</n-tag>
				<n-tag v-if="totalDone > 0" :bordered="false" type="success" size="small">
					{{ totalDone }} / {{ tasks.length }} done
				</n-tag>
				<n-tag v-if="mandatoryIncomplete > 0" :bordered="false" type="warning" size="small">
					{{ mandatoryIncomplete }} mandatory incomplete
				</n-tag>
			</div>

			<p class="text-secondary text-xs">
				Read-only view of investigation tasks performed by the SOC team on this case.
			</p>

			<div v-if="tasks.length" class="flex flex-col gap-3">
				<div
					v-for="task in tasks"
					:key="task.id"
					class="task-card border-border rounded-md border p-4"
					:class="{ 'task-card--done': task.status === 'DONE', 'task-card--skipped': task.status === 'NOT_NECESSARY' }"
				>
					<div class="flex flex-wrap items-start justify-between gap-2">
						<div class="flex flex-1 flex-col gap-1">
							<div class="flex items-center gap-2">
								<span class="font-medium">{{ task.title }}</span>
								<n-tag v-if="task.mandatory" :bordered="false" type="error" size="tiny">
									mandatory
								</n-tag>
							</div>
							<p v-if="task.description" class="text-secondary text-sm">{{ task.description }}</p>
						</div>
						<n-tag :bordered="false" :type="statusTagType(task.status)" size="small">
							{{ statusLabel(task.status) }}
						</n-tag>
					</div>

					<div v-if="task.guidelines" class="mt-3">
						<details class="text-sm">
							<summary class="cursor-pointer font-medium">Guidelines</summary>
							<p class="text-secondary mt-1 whitespace-pre-line">{{ task.guidelines }}</p>
						</details>
					</div>

					<div v-if="task.evidence_comment" class="mt-3">
						<div class="text-secondary mb-1 text-xs uppercase">Notes from analyst</div>
						<p class="whitespace-pre-line text-sm">{{ task.evidence_comment }}</p>
					</div>

					<div class="text-tertiary mt-3 text-xs">
						<span v-if="task.completed_by">
							{{ task.status === "DONE" ? "Completed" : "Marked" }} by
							<strong>{{ task.completed_by }}</strong>
							<template v-if="task.completed_at"> · {{ formatDateTime(task.completed_at) }}</template>
						</span>
					</div>
				</div>
			</div>
			<n-empty v-else-if="!loading" description="No tasks on this case yet" class="h-32 justify-center" />
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { CaseTask, CaseTaskStatus } from "@/types/caseTemplates"
import type { ApiError } from "@/types/common"
import dayjs from "@/utils/dayjs"
import { NEmpty, NSpin, NTag, useMessage } from "naive-ui"
import { computed, onMounted, ref, watch } from "vue"
import Api from "@/api"
import { getApiErrorMessage } from "@/utils"

const props = defineProps<{
	caseId: number
}>()

const message = useMessage()
const tasks = ref<CaseTask[]>([])
const loading = ref(false)

const totalDone = computed(() => tasks.value.filter(t => t.status === "DONE").length)
const mandatoryIncomplete = computed(
	() => tasks.value.filter(t => t.mandatory && t.status !== "DONE").length
)

function statusLabel(s: CaseTaskStatus): string {
	return s === "TODO" ? "To do" : s === "DONE" ? "Done" : "Not necessary"
}
function statusTagType(s: CaseTaskStatus) {
	return s === "DONE" ? "success" : s === "NOT_NECESSARY" ? "warning" : "default"
}
function formatDateTime(iso: string): string {
	return dayjs(iso).format("MMM D, YYYY HH:mm")
}

async function fetchTasks() {
	loading.value = true
	try {
		const res = await Api.caseTemplates.getCaseTasks(props.caseId)
		tasks.value = res.data.tasks ?? []
	} catch (err) {
		message.error(getApiErrorMessage(err as ApiError))
	} finally {
		loading.value = false
	}
}

watch(() => props.caseId, fetchTasks)
onMounted(fetchTasks)
</script>

<style scoped lang="scss">
.task-card {
	&--done {
		background-color: rgba(0, 200, 80, 0.05);
	}
	&--skipped {
		background-color: rgba(160, 160, 160, 0.05);
	}
}
</style>
