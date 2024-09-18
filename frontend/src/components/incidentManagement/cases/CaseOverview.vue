<template>
	<n-spin :show="loading" class="flex flex-col grow" content-class="flex flex-col grow">
		<div class="flex flex-col gap-4 grow justify-between">
			<div class="content-box flex flex-col gap-4 py-3">
				<div class="px-7 flex sm:!flex-row flex-col gap-4">
					<KVCard
						:color="
							caseData.case_status === 'OPEN'
								? 'danger'
								: caseData.case_status === 'IN_PROGRESS'
									? 'warning'
									: caseData.case_status === 'CLOSED'
										? 'success'
										: undefined
						"
						size="lg"
						class="grow w-full"
					>
						<template #key>
							<div class="flex gap-2 items-center">
								<StatusIcon :status="caseData.case_status" />
								<span>Status</span>
							</div>
						</template>
						<template #value>
							<div class="flex">
								<CaseStatusSwitch
									v-slot="{ loading: loadingStatus }"
									:case-data
									@updated="updateCase($event)"
								>
									<div
										class="flex gap-3 items-center"
										:class="{
											'cursor-not-allowed': loadingStatus,
											'cursor-pointer': !loadingStatus
										}"
									>
										<span>{{ caseData.case_status || "n/d" }}</span>
										<n-spin
											:size="14"
											:show="loadingStatus"
											content-class="flex flex-col justify-center"
										>
											<Icon :name="EditIcon" />
										</n-spin>
									</div>
								</CaseStatusSwitch>
							</div>
						</template>
					</KVCard>

					<KVCard :color="caseData.assigned_to ? 'success' : undefined" size="lg" class="grow w-full">
						<template #key>
							<div class="flex gap-2 items-center">
								<AssigneeIcon :assignee="caseData.assigned_to" />
								<span>Assigned to</span>
							</div>
						</template>
						<template #value>
							<div class="flex">
								<CaseAssignUser
									v-slot="{ loading: loadingAssignee }"
									:case-data
									@updated="updateCase($event)"
								>
									<div
										class="flex gap-3 items-center"
										:class="{
											'cursor-not-allowed': loadingAssignee,
											'cursor-pointer': !loadingAssignee
										}"
									>
										<span>{{ caseData.assigned_to || "n/d" }}</span>
										<n-spin
											:size="14"
											:show="loadingAssignee"
											content-class="flex flex-col justify-center"
										>
											<Icon :name="EditIcon" />
										</n-spin>
									</div>
								</CaseAssignUser>
							</div>
						</template>
					</KVCard>
				</div>

				<div class="px-7">
					<KVCard>
						<template #key>description</template>
						<template #value>
							<span class="whitespace-pre-wrap">
								{{ caseData.case_description ?? "-" }}
							</span>
						</template>
					</KVCard>
				</div>

				<div class="px-7 grid gap-2 grid-auto-fit-250">
					<KVCard>
						<template #key>id</template>
						<template #value>#{{ caseData.id }}</template>
					</KVCard>

					<KVCard>
						<template #key>creation time</template>
						<template #value>
							{{ formatDate(caseData.case_creation_time, dFormats.datetime) }}
						</template>
					</KVCard>
				</div>
			</div>

			<div class="footer-box px-7 py-4 flex justify-end">
				<n-button type="error" secondary @click="handleDelete()">
					<template #icon>
						<Icon :name="TrashIcon" />
					</template>
					Delete
				</n-button>
			</div>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { Case } from "@/types/incidentManagement/cases.d"
import Icon from "@/components/common/Icon.vue"
import KVCard from "@/components/common/KVCard.vue"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import { NButton, NSpin, useDialog, useMessage } from "naive-ui"
import { ref, toRefs } from "vue"
import AssigneeIcon from "../common/AssigneeIcon.vue"
import StatusIcon from "../common/StatusIcon.vue"
import CaseAssignUser from "./CaseAssignUser.vue"
import CaseStatusSwitch from "./CaseStatusSwitch.vue"
import { handleDeleteCase } from "./utils"

const props = defineProps<{ caseData: Case }>()
const emit = defineEmits<{
	(e: "deleted"): void
	(e: "updated", value: Case): void
}>()

const { caseData } = toRefs(props)

const TrashIcon = "carbon:trash-can"
const EditIcon = "uil:edit-alt"

const dialog = useDialog()
const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const loading = ref(false)

function updateCase(updatedAlert: Case) {
	emit("updated", updatedAlert)
}

function handleDelete() {
	if (caseData.value) {
		handleDeleteCase({
			caseData: caseData.value,
			cbBefore: () => {
				loading.value = true
			},
			cbSuccess: () => {
				emit("deleted")
			},
			cbAfter: () => {
				loading.value = false
			},
			message,
			dialog
		})
	}
}
</script>

<style lang="scss" scoped>
.footer-box {
	border-top: var(--border-small-100);
	background-color: var(--bg-secondary-color);
}
</style>
