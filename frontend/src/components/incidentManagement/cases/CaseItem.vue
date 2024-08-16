<template>
	<div class="case-item" :class="'status-' + incidentCase?.case_status">
		<n-spin :show="loading">
			<div class="flex flex-col" v-if="incidentCase">
				<div class="header-box px-5 py-3 pb-0 flex justify-between items-center">
					<div class="id flex items-center gap-2 cursor-pointer" @click="showDetails = true">
						<span>#{{ incidentCase.id }}</span>
						<Icon :name="InfoIcon" :size="16"></Icon>
					</div>
				</div>

				<div class="main-box flex flex-col gap-3 px-5 py-3">
					<div class="content flex flex-col gap-1 grow">
						<div class="title">
							{{ incidentCase.case_name }}
						</div>
					</div>

					<div class="badges-box flex flex-wrap items-center gap-3">
						<CaseStatusSwitch
							:caseData="incidentCase"
							v-slot="{ loading: loadingStatus }"
							@updated="updateCase($event)"
						>
							<Badge
								type="splitted"
								class="cursor-pointer"
								bright
								:color="
									incidentCase.case_status === 'OPEN'
										? 'danger'
										: incidentCase.case_status === 'IN_PROGRESS'
											? 'warning'
											: incidentCase.case_status === 'CLOSED'
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
										<StatusIcon :status="incidentCase.case_status" />
									</n-spin>
								</template>
								<template #label>Status</template>
								<template #value>
									<div class="flex gap-2 items-center">
										{{ incidentCase.case_status || "n/d" }}
										<Icon :name="EditIcon" :size="13" />
									</div>
								</template>
							</Badge>
						</CaseStatusSwitch>

						<CaseAssignUser
							:caseData="incidentCase"
							:users="availableUsers"
							v-slot="{ loading: loadingAssignee }"
							@updated="updateCase($event)"
						>
							<Badge
								type="splitted"
								class="cursor-pointer"
								bright
								:color="incidentCase.assigned_to ? 'success' : undefined"
							>
								<template #iconLeft>
									<n-spin
										:size="12"
										:show="loadingAssignee"
										content-class="flex flex-col justify-center"
									>
										<AssigneeIcon :assignee="incidentCase.assigned_to" />
									</n-spin>
								</template>
								<template #label>Assignee</template>
								<template #value>
									<div class="flex gap-2 items-center">
										{{ incidentCase.assigned_to || "n/d" }}
										<Icon :name="EditIcon" :size="13" />
									</div>
								</template>
							</Badge>
						</CaseAssignUser>
					</div>
				</div>

				<div class="footer-box px-5 py-3 flex justify-between items-center">
					<n-collapse :trigger-areas="['main', 'arrow']">
						<n-collapse-item name="alerts-list">
							<template #header>
								Alerts
								<code class="ml-2">{{ incidentCase.alerts.length }}</code>
							</template>
							<template #header-extra>
								<div class="actions-box">
									<n-button quaternary size="tiny" @click="handleDelete()">Delete Case</n-button>
								</div>
							</template>
							<div>
								<template v-if="incidentCase.alerts.length">
									<AlertItem
										v-for="alert of incidentCase.alerts"
										:key="alert.id"
										:alertData="alert"
										:availableUsers
										compact
										@deleted="getCase(incidentCase.id)"
										@updated="getCase(incidentCase.id)"
									/>
								</template>
								<template v-else>
									<n-empty
										description="No alerts attached"
										class="justify-center h-24"
										v-if="!loading"
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
			:style="{ maxWidth: 'min(850px, 90vw)', minHeight: 'min(540px, 90vh)', overflow: 'hidden' }"
		>
			<n-card
				content-class="flex flex-col !p-0"
				:title="caseNameTruncated"
				closable
				@close="showDetails = false"
				:bordered="false"
				segmented
				role="modal"
			>
				details
				<!--
				<AlertItemDetails
				v-if="alert"
				:caseData="alert"
				:availableUsers
				@deleted="emitDelete()"
				@updated="updateCase($event)"
				/>
				-->
			</n-card>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import { computed, onBeforeMount, ref, toRefs } from "vue"
import { NModal, NButton, NCollapse, NCollapseItem, NSpin, NCard, NEmpty, useMessage, useDialog } from "naive-ui"
import _clone from "lodash/cloneDeep"
import Api from "@/api"
import Icon from "@/components/common/Icon.vue"
import Badge from "@/components/common/Badge.vue"
import CaseAssignUser from "./CaseAssignUser.vue"
import CaseStatusSwitch from "./CaseStatusSwitch.vue"
import StatusIcon from "../common/StatusIcon.vue"
import AssigneeIcon from "../common/AssigneeIcon.vue"
import AlertItem from "../alerts/AlertItem.vue"
import { handleDeleteCase } from "./utils"
import _truncate from "lodash/truncate"
import type { Case } from "@/types/incidentManagement/cases.d"

const props = defineProps<{ caseData?: Case; caseId?: number; availableUsers?: string[] }>()
const { caseData, caseId, availableUsers } = toRefs(props)

const emit = defineEmits<{
	(e: "deleted"): void
	(e: "updated", value: Case): void
}>()

const InfoIcon = "carbon:information"
const EditIcon = "uil:edit-alt"

const dialog = useDialog()
const message = useMessage()
const loading = ref(false)
const showDetails = ref(false)
const incidentCase = ref<Case | null>(null)
const caseNameTruncated = computed(() => _truncate(incidentCase.value?.case_name, { length: 50 }))

function updateCase(updatedCase: Case) {
	incidentCase.value = updatedCase
	emit("updated", updatedCase)
}

function getCase(caseId: number) {
	loading.value = true

	Api.incidentManagement
		.getCase(caseId)
		.then(res => {
			if (res.data.success) {
				incidentCase.value = res.data?.cases?.[0] || null
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
	if (incidentCase.value) {
		handleDeleteCase({
			caseData: incidentCase.value,
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

onBeforeMount(() => {
	if (caseId.value) {
		getCase(caseId.value)
	} else if (caseData.value) {
		incidentCase.value = _clone(caseData.value)
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

	&:hover {
		box-shadow: 0px 0px 0px 1px var(--primary-040-color);
	}

	@container (max-width: 600px) {
		.header-box {
			.time {
				display: none;
			}
		}
		.footer-box {
			.time {
				display: flex;
			}
		}
	}
}
</style>
