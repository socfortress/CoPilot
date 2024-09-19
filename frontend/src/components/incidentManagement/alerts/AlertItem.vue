<template>
	<div
		class="alert-item"
		:class="[`status-${alert?.status}`, { compact, embedded, 'cursor-pointer': compact, highlight }]"
		@click="compact ? openDetails() : undefined"
	>
		<n-spin :show="loading">
			<div v-if="alert" class="flex flex-col">
				<div class="header-box px-5 py-3 pb-0 flex justify-between items-center">
					<div class="id flex items-center gap-2 cursor-pointer" @click="openDetails()">
						<span>#{{ alert.id }} - {{ alert.source }}</span>
						<Icon v-if="!compact" :name="InfoIcon" :size="16"></Icon>
					</div>
					<div class="time">
						<n-popover
							v-if="!compact"
							overlap
							placement="top-end"
							style="max-height: 240px"
							scrollable
							to="body"
						>
							<template #trigger>
								<div class="flex items-center gap-2 cursor-help">
									<span v-if="alert.alert_creation_time">
										{{ formatDate(alert.alert_creation_time, dFormats.datetime) }}
									</span>
									<Icon :name="TimeIcon" :size="16"></Icon>
								</div>
							</template>
							<div class="flex flex-col py-2 px-1">
								<AlertTimeline v-if="alert" :alert />
							</div>
						</n-popover>
						<span v-if="compact && alert.alert_creation_time">
							{{ formatDate(alert.alert_creation_time, dFormats.datetime) }}
						</span>
					</div>
				</div>

				<div class="main-box flex flex-col gap-3 px-5 py-3">
					<div class="content flex flex-col gap-1 grow">
						<div class="title">
							{{ alert.alert_name }}
						</div>
					</div>

					<div v-if="compact" class="badges-box flex flex-wrap items-center gap-3">
						<Badge
							type="splitted"
							class="cursor-pointer"
							bright
							:color="
								alert.status === 'OPEN'
									? 'danger'
									: alert.status === 'IN_PROGRESS'
										? 'warning'
										: 'success'
							"
						>
							<template #iconLeft>
								<StatusIcon :status="alert.status" />
							</template>
							<template #label>Status</template>
							<template #value>
								<div class="flex gap-2 items-center">
									{{ alert.status || "n/d" }}
								</div>
							</template>
						</Badge>

						<Badge
							type="splitted"
							class="cursor-pointer"
							bright
							:color="alert.assigned_to ? 'success' : undefined"
						>
							<template #iconLeft>
								<AssigneeIcon :assignee="alert.assigned_to" />
							</template>
							<template #label>Assignee</template>
							<template #value>
								<div class="flex gap-2 items-center">
									{{ alert.assigned_to || "n/d" }}
								</div>
							</template>
						</Badge>
					</div>
					<div v-else class="badges-box flex flex-wrap items-center gap-3">
						<AlertStatusSwitch v-slot="{ loading: loadingStatus }" :alert @updated="updateAlert($event)">
							<Badge
								type="splitted"
								class="cursor-pointer"
								bright
								:color="
									alert.status === 'OPEN'
										? 'danger'
										: alert.status === 'IN_PROGRESS'
											? 'warning'
											: 'success'
								"
							>
								<template #iconLeft>
									<n-spin
										:size="12"
										:show="loadingStatus"
										content-class="flex flex-col justify-center"
									>
										<StatusIcon :status="alert.status" />
									</n-spin>
								</template>
								<template #label>Status</template>
								<template #value>
									<div class="flex gap-2 items-center">
										{{ alert.status || "n/d" }}
										<Icon :name="EditIcon" :size="13" />
									</div>
								</template>
							</Badge>
						</AlertStatusSwitch>

						<AlertAssignUser v-slot="{ loading: loadingAssignee }" :alert @updated="updateAlert($event)">
							<Badge
								type="splitted"
								class="cursor-pointer"
								bright
								:color="alert.assigned_to ? 'success' : undefined"
							>
								<template #iconLeft>
									<n-spin
										:size="12"
										:show="loadingAssignee"
										content-class="flex flex-col justify-center"
									>
										<AssigneeIcon :assignee="alert.assigned_to" />
									</n-spin>
								</template>
								<template #label>Assignee</template>
								<template #value>
									<div class="flex gap-2 items-center">
										{{ alert.assigned_to || "n/d" }}
										<Icon :name="EditIcon" :size="13" />
									</div>
								</template>
							</Badge>
						</AlertAssignUser>

						<Badge type="splitted" class="!hidden sm:!flex">
							<template #label>Customer</template>
							<template #value>
								<div class="flex items-center h-full">
									<code
										class="cursor-pointer text-primary-color leading-none"
										@click.stop="gotoCustomer({ code: alert.customer_code })"
									>
										#{{ alert.customer_code }}
										<Icon :name="LinkIcon" :size="14" class="top-0.5 relative" />
									</code>
								</div>
							</template>
						</Badge>
					</div>
				</div>

				<div v-if="!compact" class="footer-box px-5 py-3 flex justify-between items-center">
					<div class="details flex gap-3 items-center">
						<Badge v-if="alert.alert_creation_time" type="splitted" class="time">
							<template #iconLeft>
								<Icon :name="TimeIcon" :size="16" />
							</template>
							<template #value>
								{{ formatDate(alert.alert_creation_time, dFormats.datetime) }}
							</template>
						</Badge>

						<n-tooltip trigger="hover">
							<template #trigger>
								<Badge type="splitted" class="!hidden xs:!flex">
									<template #iconLeft>
										<Icon :name="AssetsIcon" :size="16" />
									</template>
									<template #value>
										{{ alert.assets?.length || 0 }}
									</template>
								</Badge>
							</template>
							Assets
						</n-tooltip>

						<n-tooltip trigger="hover">
							<template #trigger>
								<Badge type="splitted" class="!hidden xs:!flex">
									<template #iconLeft>
										<Icon :name="CommentsIcon" :size="16" />
									</template>
									<template #value>
										{{ alert.comments?.length || 0 }}
									</template>
								</Badge>
							</template>
							Comments
						</n-tooltip>

						<span v-for="tag of alert.tags" :key="tag.tag" class="text-secondary-color">
							#{{ tag.tag }}
						</span>
					</div>
					<div class="actions-box">
						<n-button quaternary size="tiny" @click.stop="handleDelete()">Delete</n-button>
					</div>
				</div>
			</div>
		</n-spin>

		<n-modal
			v-model:show="showDetails"
			:style="{ maxWidth: 'min(850px, 90vw)', minHeight: 'min(540px, 90vh)', overflow: 'hidden' }"
			display-directive="show"
		>
			<n-card
				content-class="flex flex-col !p-0"
				:title="alertNameTruncated"
				closable
				:bordered="false"
				segmented
				role="modal"
				@close="closeDetails()"
			>
				<AlertDetails v-if="alert" :alert-data="alert" @deleted="emitDelete()" @updated="updateAlert($event)" />
			</n-card>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import type { Alert } from "@/types/incidentManagement/alerts.d"
import Api from "@/api"
import Badge from "@/components/common/Badge.vue"
import Icon from "@/components/common/Icon.vue"
import { useGoto } from "@/composables/useGoto"
import { useSettingsStore } from "@/stores/settings"
import { formatDate } from "@/utils"
import _clone from "lodash/cloneDeep"
import _truncate from "lodash/truncate"
import { NButton, NCard, NModal, NPopover, NSpin, NTooltip, useDialog, useMessage } from "naive-ui"
import { computed, onBeforeMount, onMounted, ref, toRefs } from "vue"
import AssigneeIcon from "../common/AssigneeIcon.vue"
import StatusIcon from "../common/StatusIcon.vue"
import AlertAssignUser from "./AlertAssignUser.vue"
import AlertDetails from "./AlertDetails.vue"
import AlertStatusSwitch from "./AlertStatusSwitch.vue"
import AlertTimeline from "./AlertTimeline.vue"
import { handleDeleteAlert } from "./utils"

const props = defineProps<{
	alertData?: Alert
	alertId?: number
	compact?: boolean
	embedded?: boolean
	detailsOnMounted?: boolean
	highlight?: boolean
}>()
const emit = defineEmits<{
	(e: "opened"): void
	(e: "deleted"): void
	(e: "updated", value: Alert): void
}>()

const { alertData, alertId, compact, embedded, detailsOnMounted, highlight } = toRefs(props)

const InfoIcon = "carbon:information"
const LinkIcon = "carbon:launch"
const TimeIcon = "carbon:time"
const EditIcon = "uil:edit-alt"
const CommentsIcon = "carbon:chat"
const AssetsIcon = "carbon:document-security"

const { gotoCustomer } = useGoto()
const dialog = useDialog()
const message = useMessage()
const loading = ref(false)
const showDetails = ref(false)
const dFormats = useSettingsStore().dateFormat
const alert = ref<Alert | null>(null)
const alertNameTruncated = computed(() => _truncate(alert.value?.alert_name, { length: 50 }))

function updateAlert(updatedAlert: Alert) {
	alert.value = updatedAlert
	emit("updated", updatedAlert)
}

function getAlert(alertId: number) {
	loading.value = true

	Api.incidentManagement
		.getAlert(alertId)
		.then(res => {
			if (res.data.success) {
				alert.value = res.data?.alerts?.[0] || null
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
	if (alert.value) {
		handleDeleteAlert({
			alert: alert.value,
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
	if (alertId.value) {
		getAlert(alertId.value)
	} else if (alertData.value?.id && alertData.value?.linked_cases === undefined) {
		getAlert(alertData.value.id)
	} else if (alertData.value) {
		alert.value = _clone(alertData.value)
	}
})

onMounted(() => {
	if (detailsOnMounted.value) {
		openDetails()
	}
})
</script>

<style lang="scss" scoped>
.alert-item {
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
		box-shadow: 0px 0px 0px 1px var(--primary-color);
	}

	&.highlight {
		box-shadow: 0px 0px 0px 1px var(--primary-color);
	}

	&:not(.compact) {
		.header-box {
			.id {
				&:hover {
					color: var(--primary-color);
				}
			}
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
}
</style>
