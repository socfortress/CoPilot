<template>
	<n-spin :show="loading" class="flex grow flex-col" content-class="flex grow flex-col">
		<div class="flex grow flex-col justify-between gap-4">
			<div class="content-box flex flex-col gap-4 py-3">
				<div class="flex flex-col gap-4 px-7 sm:!flex-row">
					<CardKV
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
						class="w-full grow"
					>
						<template #key>
							<div class="flex items-center gap-2">
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
										class="flex items-center gap-3"
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
					</CardKV>

					<CardKV :color="caseData.assigned_to ? 'success' : undefined" size="lg" class="w-full grow">
						<template #key>
							<div class="flex items-center gap-2">
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
										class="flex items-center gap-3"
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
					</CardKV>
				</div>

				<div class="px-7">
					<CardKV>
						<template #key>description</template>
						<template #value>
							<span class="whitespace-pre-wrap">
								{{ caseData.case_description ?? "-" }}
							</span>
						</template>
					</CardKV>
				</div>

				<div class="grid-auto-fit-250 grid gap-2 px-7">
					<CardKV>
						<template #key>id</template>
						<template #value>#{{ caseData.id }}</template>
					</CardKV>

					<CardKV>
						<template #key>creation time</template>
						<template #value>
							{{
								caseData.case_creation_time
									? formatDate(caseData.case_creation_time, dFormats.datetime)
									: "-"
							}}
						</template>
					</CardKV>

					<CardKV>
						<template #key>customer code</template>
						<template #value>
							<code
								v-if="caseData.customer_code"
								class="text-primary cursor-pointer"
								@click="gotoCustomer({ code: caseData.customer_code })"
							>
								{{ caseData.customer_code }}
								<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
							</code>
							<span v-else>-</span>
						</template>
					</CardKV>
				</div>
			</div>

			<div class="footer-box bg-secondary flex justify-end gap-3 px-7 py-4">
				<n-button type="error" secondary @click="handleDelete()">
					<template #icon>
						<Icon :name="TrashIcon" />
					</template>
					Delete
				</n-button>
				<CaseReportButton :case-id="caseData.id" />
			</div>
		</div>
	</n-spin>
</template>

<script setup lang="ts">
import type { Case } from "@/types/incidentManagement/cases.d"
import CardKV from "@/components/common/cards/CardKV.vue"
import Icon from "@/components/common/Icon.vue"
import { useGoto } from "@/composables/useGoto"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import { NButton, NSpin, useDialog, useMessage } from "naive-ui"
import { ref, toRefs } from "vue"
import AssigneeIcon from "../common/AssigneeIcon.vue"
import StatusIcon from "../common/StatusIcon.vue"
import CaseAssignUser from "./CaseAssignUser.vue"
import CaseReportButton from "./CaseReportButton.vue"
import CaseStatusSwitch from "./CaseStatusSwitch.vue"
import { handleDeleteCase } from "./utils"

const props = defineProps<{ caseData: Case }>()
const emit = defineEmits<{
	(e: "deleted"): void
	(e: "updated", value: Case): void
}>()

const { caseData } = toRefs(props)

const TrashIcon = "carbon:trash-can"
const LinkIcon = "carbon:launch"
const EditIcon = "uil:edit-alt"

const { gotoCustomer } = useGoto()
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
	border-top: 1px solid var(--border-color);
}
</style>
