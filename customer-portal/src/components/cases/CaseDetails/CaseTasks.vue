<template>
	<n-spin :show="loading">
		<div class="flex flex-col gap-3">
			<div class="flex items-center gap-3 text-sm">
				<Chip :value="tasks.length" :label="$t('cases.caseTasks.tasks')" :bordered="false" />
				<Chip
					v-if="totalDone > 0"
					:value="totalDone"
					:label="$t('cases.caseTasks.done')"
					type="success"
					:bordered="false"
				/>
				<Chip
					v-if="mandatoryIncomplete > 0"
					:bordered="false"
					:value="mandatoryIncomplete"
					:label="$t('cases.caseTasks.mandatoryIncomplete')"
					type="warning"
				/>
			</div>

			<p class="text-xs">{{ $t("cases.caseTasks.intro") }}</p>

			<div v-if="tasks.length" class="flex flex-col gap-3">
				<CardEntity
					v-for="task in tasks"
					:key="task.id"
					:status="
						task.status === 'DONE' ? 'success' : task.status === 'NOT_NECESSARY' ? 'warning' : undefined
					"
					embedded
				>
					<template #header-main>
						<div class="flex flex-wrap items-center gap-3">
							<span class="text-default font-sans text-base">
								{{ task.title }}
							</span>

							<n-tag v-if="task.mandatory" :bordered="false" type="error" size="small">
								{{ $t("cases.caseTasks.mandatory") }}
							</n-tag>
							<n-tag v-if="task.template_task_id == null" :bordered="false" type="default" size="small">
								{{ $t("cases.caseTasks.custom") }}
							</n-tag>
						</div>
					</template>
					<template #header-extra>
						<Chip :value="statusLabel(task.status)" :type="statusTagType(task.status)" :bordered="false" />
					</template>
					<template #default>
						<div class="flex flex-col gap-3">
							<p v-if="task.description" class="text-secondary text-sm">{{ task.description }}</p>

							<details v-if="task.guidelines" class="text-sm">
								<summary class="cursor-pointer font-medium">{{ $t("cases.caseTasks.guidelines") }}</summary>
								<p class="text-secondary mt-1 whitespace-pre-line">{{ task.guidelines }}</p>
							</details>
						</div>
					</template>
					<template v-if="task.evidence_comment" #main-extra>
						<div class="flex flex-col gap-1">
							<div class="text-secondary text-xs uppercase">{{ $t("cases.caseTasks.notes") }}</div>
							<p class="text-sm whitespace-pre-line">
								{{ task.evidence_comment }}
							</p>
						</div>
					</template>
					<template #footer>
						<div class="flex flex-wrap items-center justify-between gap-2">
							<div class="text-secondary flex flex-wrap gap-x-4 gap-y-1 text-sm">
								<span v-if="task.completed_by">
									<i18n-t
										:keypath="task.status === 'DONE' ? 'cases.caseTasks.completedBy' : 'cases.caseTasks.markedBy'"
										scope="global"
									>
										<template #user>
											<strong>{{ task.completed_by }}</strong>
										</template>
									</i18n-t>
									<template v-if="task.completed_at">
										· {{ formatDate(task.completed_at, dFormats.datetime) }}
									</template>
								</span>
								<i18n-t v-else keypath="cases.caseTasks.createdBy" tag="span" scope="global">
									<template #user>
										<strong>{{ task.created_by }}</strong>
									</template>
								</i18n-t>
							</div>

							<div></div>
						</div>
					</template>
				</CardEntity>
			</div>
			<n-empty v-else-if="!loading" :description="$t('cases.caseTasks.empty')" class="h-32 justify-center" />
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { CaseTask, CaseTaskStatus } from "@/types/caseTemplates"
import type { ApiError } from "@/types/common"
import { NEmpty, NSpin, NTag, useMessage } from "naive-ui"
import { computed, ref, watch } from "vue"
import { useI18n } from "vue-i18n"
import Api from "@/api"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Chip from "@/components/common/Chip.vue"
import { useSettingsStore } from "@/stores/settings"
import { getApiErrorMessage } from "@/utils"
import { formatDate } from "@/utils/format"

const props = defineProps<{
	caseId: number
}>()

const message = useMessage()
const { t } = useI18n()
const tasks = ref<CaseTask[]>([])
const loading = ref(false)
const dFormats = useSettingsStore().dateFormat
const totalDone = computed(() => tasks.value.filter(t => t.status === "DONE").length)
const mandatoryIncomplete = computed(() => tasks.value.filter(t => t.mandatory && t.status !== "DONE").length)

function statusLabel(s: CaseTaskStatus): string {
	return t(s === "TODO" ? "cases.caseTasks.status.todo" : s === "DONE" ? "cases.caseTasks.status.done" : "cases.caseTasks.status.notNecessary")
}

function statusTagType(s: CaseTaskStatus) {
	return s === "DONE" ? "success" : s === "NOT_NECESSARY" ? "warning" : "default"
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

watch(() => props.caseId, fetchTasks, { immediate: true })
</script>
