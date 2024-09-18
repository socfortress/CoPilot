<template>
	<div
		class="case-item"
		:class="[`status-${caseEntity?.case_status}`, { compact, embedded, 'cursor-pointer': compact, highlight }]"
	>
		<n-spin :show="loading">
			<div v-if="caseEntity" class="flex flex-col">
				<div class="header-box px-5 py-3 pb-0 flex justify-between items-center">
					<div class="id flex items-center gap-2 cursor-pointer" @click="compact ? undefined : openDetails()">
						<span>#{{ caseEntity.id }}</span>
						<Icon v-if="!compact" :name="InfoIcon" :size="16"></Icon>
					</div>
					<div v-if="caseEntity.case_creation_time" class="time">
						{{ formatDate(caseEntity.case_creation_time, dFormats.datetime) }}
					</div>
				</div>

				<div class="main-box flex flex-col gap-3 px-5 py-3">
					<div class="content flex flex-col gap-1 grow">
						<div class="title">
							{{ caseEntity.case_name }}
						</div>
					</div>

					<div v-if="compact" class="badges-box flex flex-wrap items-center gap-3">
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
							<template #label>
								Status
							</template>
							<template #value>
								<div class="flex gap-2 items-center">
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
							<template #label>
								Assignee
							</template>
							<template #value>
								<div class="flex gap-2 items-center">
									{{ caseEntity.assigned_to || "n/d" }}
								</div>
							</template>
						</Badge>
					</div>

					<div v-else class="badges-box flex flex-wrap items-center gap-3">
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
									<n-spin
										:size="12"
										:show="loadingStatus"
										content-class="flex flex-col justify-center"
									>
										<StatusIcon :status="caseEntity.case_status" />
									</n-spin>
								</template>
								<template #label>
									Status
								</template>
								<template #value>
									<div class="flex gap-2 items-center">
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
									<n-spin
										:size="12"
										:show="loadingAssignee"
										content-class="flex flex-col justify-center"
									>
										<AssigneeIcon :assignee="caseEntity.assigned_to" />
									</n-spin>
								</template>
								<template #label>
									Assignee
								</template>
								<template #value>
									<div class="flex gap-2 items-center">
										{{ caseEntity.assigned_to || "n/d" }}
										<Icon :name="EditIcon" :size="13" />
									</div>
								</template>
							</Badge>
						</CaseAssignUser>
					</div>
				</div>

				<div v-if="!compact" class="footer-box px-5 py-3 flex justify-between items-center">
					<n-collapse :trigger-areas="['main', 'arrow']">
						<n-collapse-item name="alerts-list">
							<template #header>
								Alerts
								<code class="ml-2">{{ caseEntity.alerts.length }}</code>
							</template>
							<template #header-extra>
								<div class="actions-box">
									<n-button quaternary size="tiny" @click="handleDelete()">
										Delete Case
									</n-button>
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
										class="justify-center h-24"
									/>
								</template>
							</div>
						</n-collapse-item>
					</n-collapse>
				</div>
			</div>
		</n-spin>

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
import Icon from "@/components/common/Icon.vue"
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

const InfoIcon = "carbon:information"
const EditIcon = "uil:edit-alt"

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

	Api.incidentManagement
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

<style lang="scss" scoped>
.case-item {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);
	transition: all 0.2s var(--bezier-ease);
	border: var(--border-small-050);
	overflow: hidden;

	.header-box {
		font-family: var(--font-family-mono);
		font-size: 13px;
		color: var(--fg-secondary-color);

		.id {
			word-break: break-word;
			line-height: 1.2;

			&:hover {
				color: var(--primary-color);
			}
		}
	}
	.main-box {
		.content {
			word-break: break-word;
		}
	}

	.footer-box {
		border-top: var(--border-small-100);
		font-size: 13px;
		background-color: var(--bg-secondary-color);

		.time {
			display: none;
		}
	}

	&.embedded {
		background-color: var(--bg-secondary-color);
	}

	&:hover {
		box-shadow: 0px 0px 0px 1px var(--primary-040-color);
	}

	&:hover {
		box-shadow: 0px 0px 0px 1px var(--primary-040-color);
	}

	&.highlight {
		box-shadow: 0px 0px 0px 1px var(--primary-color);
	}
}
</style>
