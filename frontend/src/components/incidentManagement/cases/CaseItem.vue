<template>
	<div>
		<CardEntity
			:loading
			:embedded
			hoverable
			:size="compact ? 'small' : 'medium'"
			:clickable="compact"
			:highlighted="highlight"
		>
			<template v-if="caseEntity" #headerMain>
				<div
					class="flex items-center gap-2 break-words"
					:class="{ 'hover:text-primary cursor-pointer': !compact }"
					@click="compact ? undefined : openDetails()"
				>
					<span>#{{ caseEntity.id }}</span>
					<Icon v-if="!compact" :name="InfoIcon" :size="16"></Icon>
				</div>
			</template>
			<template v-if="caseEntity?.case_creation_time" #headerExtra>
				{{ formatDate(caseEntity.case_creation_time, dFormats.datetime) }}
			</template>

			<template v-if="caseEntity" #default>
				{{ caseEntity.case_name }}
			</template>

			<template v-if="caseEntity" #mainExtra>
				<div v-if="compact" class="flex flex-wrap items-center gap-3">
					<Badge
						type="splitted"
						class="cursor-pointer"
						bright
						:color="
							caseEntity.case_status === 'OPEN'
								? 'danger'
								: caseEntity.case_status === 'IN_PROGRESS'
									? 'warning'
									: caseEntity.case_status === 'CLOSED'
										? 'success'
										: undefined
						"
					>
						<template #iconLeft>
							<StatusIcon :status="caseEntity.case_status" />
						</template>
						<template #label>Status</template>
						<template #value>
							<div class="flex items-center gap-2">
								{{ caseEntity.case_status || "n/d" }}
							</div>
						</template>
					</Badge>

					<Badge
						type="splitted"
						class="cursor-pointer"
						bright
						:color="caseEntity.assigned_to ? 'success' : undefined"
					>
						<template #iconLeft>
							<AssigneeIcon :assignee="caseEntity.assigned_to" />
						</template>
						<template #label>Assignee</template>
						<template #value>
							<div class="flex items-center gap-2">
								{{ caseEntity.assigned_to || "n/d" }}
							</div>
						</template>
					</Badge>
				</div>

				<div v-else class="flex flex-wrap items-center gap-3">
					<CaseStatusSwitch
						v-slot="{ loading: loadingStatus }"
						:case-data="caseEntity"
						@updated="updateCase($event)"
					>
						<Badge
							type="splitted"
							class="cursor-pointer"
							bright
							:color="
								caseEntity.case_status === 'OPEN'
									? 'danger'
									: caseEntity.case_status === 'IN_PROGRESS'
										? 'warning'
										: caseEntity.case_status === 'CLOSED'
											? 'success'
											: undefined
							"
						>
							<template #iconLeft>
								<n-spin :size="12" :show="loadingStatus" content-class="flex flex-col justify-center">
									<StatusIcon :status="caseEntity.case_status" />
								</n-spin>
							</template>
							<template #label>Status</template>
							<template #value>
								<div class="flex items-center gap-2">
									{{ caseEntity.case_status || "n/d" }}
									<Icon :name="EditIcon" :size="13" />
								</div>
							</template>
						</Badge>
					</CaseStatusSwitch>

					<CaseAssignUser
						v-slot="{ loading: loadingAssignee }"
						:case-data="caseEntity"
						@updated="updateCase($event)"
					>
						<Badge
							type="splitted"
							class="cursor-pointer"
							bright
							:color="caseEntity.assigned_to ? 'success' : undefined"
						>
							<template #iconLeft>
								<n-spin :size="12" :show="loadingAssignee" content-class="flex flex-col justify-center">
									<AssigneeIcon :assignee="caseEntity.assigned_to" />
								</n-spin>
							</template>
							<template #label>Assignee</template>
							<template #value>
								<div class="flex items-center gap-2">
									{{ caseEntity.assigned_to || "n/d" }}
									<Icon :name="EditIcon" :size="13" />
								</div>
							</template>
						</Badge>
					</CaseAssignUser>

					<Badge v-if="caseEntity.customer_code" type="splitted" class="!hidden sm:!flex">
						<template #label>Customer</template>
						<template #value>
							<div class="flex h-full items-center">
								<code
									class="text-primary cursor-pointer leading-none"
									@click.stop="gotoCustomer({ code: caseEntity.customer_code })"
								>
									#{{ caseEntity.customer_code }}
									<Icon :name="LinkIcon" :size="14" class="relative top-0.5" />
								</code>
							</div>
						</template>
					</Badge>
				</div>
			</template>

			<template v-if="caseEntity && !compact" #footer>
				<div class="flex items-center justify-between">
					<n-collapse :trigger-areas="['main', 'arrow']">
						<n-collapse-item name="alerts-list">
							<template #header>
								<span class="whitespace-nowrap">
									Alerts
									<code class="ml-2">{{ caseEntity.alerts.length }}</code>
								</span>
							</template>
							<template #header-extra>
								<div class="actions-box ml-2 flex flex-wrap items-center justify-end gap-2">
									<n-button quaternary size="tiny" class="xs:!flex !hidden" @click="handleDelete()">
										Delete Case
									</n-button>
									<CaseReportButton :case-id="caseEntity.id" size="tiny" />
									<CaseNotificationButton
										:case-id="caseEntity.id"
										:notification-invoked-number="caseEntity.notification_invoked_number || 0"
										size="tiny"
										@invoked="getCase(caseEntity.id)"
									/>
								</div>
							</template>
							<div class="flex flex-col gap-2">
								<template v-if="caseEntity.alerts.length">
									<AlertItem
										v-for="alert of caseEntity.alerts"
										:key="alert.id"
										:alert-data="alert"
										compact
										@deleted="getCase(caseEntity.id)"
										@updated="getCase(caseEntity.id)"
									/>
								</template>
								<template v-else>
									<n-empty
										v-if="!loading"
										description="No alerts attached"
										class="h-24 justify-center"
									/>
								</template>
							</div>
						</n-collapse-item>
					</n-collapse>
				</div>
			</template>
		</CardEntity>

		<n-modal
			v-model:show="showDetails"
			:style="{ maxWidth: 'min(850px, 90vw)', minHeight: 'min(482px, 90vh)', overflow: 'hidden' }"
		>
			<n-card
				content-class="flex flex-col !p-0"
				:title="caseNameTruncated"
				closable
				:bordered="false"
				segmented
				role="modal"
				@close="closeDetails()"
			>
				<CaseDetails
					v-if="caseEntity"
					:case-data="caseEntity"
					@deleted="emitDelete()"
					@updated="updateCase($event)"
				/>
			</n-card>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { Case } from "@/types/incidentManagement/cases.d"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import CardEntity from "@/components/common/cards/CardEntity.vue"
import Icon from "@/components/common/Icon.vue"
import { useGoto } from "@/composables/useGoto"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import _clone from "lodash/cloneDeep"
import _truncate from "lodash/truncate"
import { NButton, NCard, NCollapse, NCollapseItem, NEmpty, NModal, NSpin, useDialog, useMessage } from "naive-ui"
import { computed, onBeforeMount, onMounted, ref, toRefs } from "vue"
import AlertItem from "../alerts/AlertItem.vue"
import AssigneeIcon from "../common/AssigneeIcon.vue"
import StatusIcon from "../common/StatusIcon.vue"
import CaseAssignUser from "./CaseAssignUser.vue"
import CaseDetails from "./CaseDetails.vue"
import CaseNotificationButton from "./CaseNotificationButton.vue"
import CaseReportButton from "./CaseReportButton.vue"
import CaseStatusSwitch from "./CaseStatusSwitch.vue"
import { handleDeleteCase } from "./utils"

const props = defineProps<{
	caseData?: Case
	caseId?: number
	compact?: boolean
	embedded?: boolean
	detailsOnMounted?: boolean
	highlight?: boolean
}>()
const emit = defineEmits<{
	(e: "opened"): void
	(e: "deleted"): void
	(e: "updated", value: Case): void
}>()

const { caseData, caseId, compact, embedded, detailsOnMounted, highlight } = toRefs(props)

const LinkIcon = "carbon:launch"
const InfoIcon = "carbon:information"
const EditIcon = "uil:edit-alt"

const { gotoCustomer } = useGoto()
const dialog = useDialog()
const message = useMessage()
const dFormats = useSettingsStore().dateFormat
const loading = ref(false)
const showDetails = ref(false)
const caseEntity = ref<Case | null>(null)
const caseNameTruncated = computed(() => _truncate(caseEntity.value?.case_name, { length: 50 }))

function updateCase(updatedCase: Case) {
	caseEntity.value = updatedCase
	emit("updated", updatedCase)
}

function getCase(caseId: number) {
	loading.value = true

	Api.incidentManagement.cases
		.getCase(caseId)
		.then(res => {
			if (res.data.success) {
				caseEntity.value = res.data?.cases?.[0] || null
			} else {
				message.warning(res.data?.message || "An error occurred. Please try again later.")
			}
		})
		.catch(err => {
			message.error(err.response?.data?.message || "An error occurred. Please try again later.")
		})
		.finally(() => {
			loading.value = false
		})
}

function handleDelete() {
	if (caseEntity.value) {
		handleDeleteCase({
			caseData: caseEntity.value,
			cbBefore: () => {
				loading.value = true
			},
			cbSuccess: () => {
				emitDelete()
			},
			cbAfter: () => {
				loading.value = false
			},
			message,
			dialog
		})
	}
}

function emitDelete() {
	showDetails.value = false
	emit("deleted")
}

function openDetails() {
	emit("opened")
	showDetails.value = true
}

function closeDetails() {
	showDetails.value = false
}

onBeforeMount(() => {
	if (caseId.value) {
		getCase(caseId.value)
	} else if (caseData.value) {
		caseEntity.value = _clone(caseData.value)
	}
})

onMounted(() => {
	if (detailsOnMounted.value) {
		openDetails()
	}
})
</script>
