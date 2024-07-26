<template>
	<div class="alert-item" :class="'status-' + alert?.status">
		<n-spin :show="loading">
			<div class="flex flex-col gap-3 px-5 py-3" v-if="alert">
				<div class="header-box flex justify-between items-center">
					<div class="id flex items-center gap-2 cursor-pointer" @click="showDetails = true">
						<span>#{{ alert.id }} - {{ alert.source }}</span>
						<Icon :name="InfoIcon" :size="16"></Icon>
					</div>
					<div class="time">
						<n-popover overlap placement="top-end" style="max-height: 240px" scrollable to="body">
							<template #trigger>
								<div class="flex items-center gap-2 cursor-help">
									<span v-if="alert.alert_creation_time">
										{{ formatDate(alert.alert_creation_time, dFormats.datetime) }}
									</span>
									<Icon :name="TimeIcon" :size="16"></Icon>
								</div>
							</template>
							<div class="flex flex-col py-2 px-1">
								<AlertTimeline :alert v-if="alert" />
							</div>
						</n-popover>
					</div>
				</div>

				<div class="main-box">
					<div class="content flex flex-col gap-1 grow">
						<div class="title">
							{{ alert.alert_name }}
						</div>
					</div>
				</div>

				<div class="badges-box flex flex-wrap items-center gap-3">
					<AlertStatusSwitch :alert v-slot="{ loading: loadingStatus }" @updated="getAlert(alert.id)">
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
								<n-spin :size="12" :show="loadingStatus" content-class="flex flex-col justify-center">
									<AlertStatusIcon :status="alert.status" />
								</n-spin>
							</template>
							<template #label>Status</template>
							<template #value>{{ alert.status || "n/d" }}</template>
						</Badge>
					</AlertStatusSwitch>

					<AlertAssignUser
						:alert
						:users="availableUsers"
						v-slot="{ loading: loadingAssignee }"
						@updated="getAlert(alert.id)"
					>
						<Badge
							type="splitted"
							class="cursor-pointer"
							bright
							:color="alert.assigned_to ? 'success' : undefined"
						>
							<template #iconLeft>
								<n-spin :size="12" :show="loadingAssignee" content-class="flex flex-col justify-center">
									<AlertAssigneeIcon :assignee="alert.assigned_to" />
								</n-spin>
							</template>
							<template #label>Assignee</template>
							<template #value>{{ alert.assigned_to || "n/d" }}</template>
						</Badge>
					</AlertAssignUser>

					<Badge type="active" class="cursor-pointer" @click="gotoCustomer({ code: alert.customer_code })">
						<template #iconRight>
							<Icon :name="LinkIcon" :size="14"></Icon>
						</template>
						<template #label>Customer #{{ alert.customer_code }}</template>
					</Badge>
					<!--
				<Badge type="splitted" color="primary" v-if="agentVersion">
					<template #label>Agent version</template>
					<template #value>{{ agentVersion }}</template>
				</Badge>

				<Badge type="splitted" color="primary" v-if="source === 'velociraptor'">
					<template #label>Velociraptor Id</template>
					<template #value>{{ healthData.velociraptor_id }}</template>
				</Badge>

				<n-popover overlap placement="bottom-start">
					<template #trigger>
						<Badge type="splitted" color="primary" hint-cursor>
							<template #iconLeft>
								<Icon :name="AgentIcon" :size="13" class="!opacity-80"></Icon>
							</template>
							<template #label>Agent</template>
							<template #value>
								{{ healthData.hostname }}
							</template>
						</Badge>
					</template>
					<div class="flex flex-col gap-1">
						<div class="box">
							agent_id:
							<code class="cursor-pointer text-primary-color" @click="gotoAgent(healthData.agent_id)">
								{{ healthData.agent_id }}
								<Icon :name="LinkIcon" :size="13" class="relative top-0.5" />
							</code>
						</div>
						<div class="box">
							hostname:
							<code>{{ healthData.hostname }}</code>
						</div>
					</div>
				</n-popover>
				-->
				</div>

				<div class="footer-box flex justify-between items-center">
					test - delete
					<!--

			<div class="actions-box flex flex-col justify-end" v-if="stream.is_editable">
				<n-button @click="stop()" :loading="loading" v-if="!stream.disabled" size="small">
					<template #icon><Icon :name="StopIcon"></Icon></template>
					Stop
				</n-button>
				<n-button @click="start()" :loading="loading" v-else type="primary" size="small">
					<template #icon><Icon :name="StartIcon"></Icon></template>
					Start
				</n-button>
			</div>
			<div class="time">{{ formatDate(stream.created_at, dFormats.datetimesec) }}</div>
				-->
				</div>
			</div>
		</n-spin>

		<n-modal
			v-model:show="showDetails"
			preset="card"
			:style="{ maxWidth: 'min(600px, 90vw)', overflow: 'hidden' }"
			:title="alert?.alert_name"
			:bordered="false"
			segmented
		>
			<div class="mb-2">Matching type :</div>
			<div class="mb-2">Remove matches from default stream :</div>
		</n-modal>
	</div>
</template>

<script setup lang="ts">
import { useSettingsStore } from "@/stores/settings"
import Icon from "@/components/common/Icon.vue"
import Badge from "@/components/common/Badge.vue"
import { formatDate } from "@/utils"
import { NModal, NPopover, NButton, NSpin, useMessage } from "naive-ui"
import { onBeforeMount, ref, toRefs } from "vue"
import Api from "@/api"
import type { Alert } from "@/types/incidentManagement/alerts.d"
import _clone from "lodash/cloneDeep"
import AlertTimeline from "./AlertTimeline.vue"
import AlertAssignUser from "./AlertAssignUser.vue"
import AlertStatusSwitch from "./AlertStatusSwitch.vue"
import AlertStatusIcon from "./AlertStatusIcon.vue"
import AlertAssigneeIcon from "./AlertAssigneeIcon.vue"
import { useGoto } from "@/composables/useGoto"

const props = defineProps<{ alertData?: Alert; alertId?: number; availableUsers?: string[] }>()
const { alertData, alertId, availableUsers } = toRefs(props)

const UserIcon = "carbon:user"
const ProgressIcon = "carbon:hourglass"
const CheckIcon = "carbon:checkmark-outline"
const WarningIcon = "carbon:warning-hex"
const InfoIcon = "carbon:information"
const AssigneeIcon = "carbon:user-military"
const LinkIcon = "carbon:launch"
const DisabledIcon = "carbon:subtract"
const EnabledIcon = "ph:check-bold"
const TimeIcon = "carbon:time"
const StopIcon = "carbon:stop"
const StartIcon = "carbon:play"

const { gotoCustomer, gotoIndex } = useGoto()
const message = useMessage()
const loading = ref(false)
const showDetails = ref(false)
const dFormats = useSettingsStore().dateFormat
const alert = ref<Alert | null>(null)

/*
function start() {
	loading.value = true

	Api.graylog
		.startStream(stream.value.id)
		.then(res => {
			if (res.data.success) {
				stream.value.disabled = false
				message.success(res.data?.message || "Stream started.")
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
		*/

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

onBeforeMount(() => {
	if (alertId.value) {
		getAlert(alertId.value)
	} else if (alertData.value) {
		alert.value = _clone(alertData.value)
	}
})
</script>

<style lang="scss" scoped>
.alert-item {
	border-radius: var(--border-radius);
	background-color: var(--bg-color);
	transition: all 0.2s var(--bezier-ease);
	border: var(--border-small-050);

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
		border-top: var(--border-small-050);
		font-size: 13px;
	}

	&.default {
		background-color: var(--primary-005-color);
		box-shadow: 0px 0px 0px 1px inset var(--primary-030-color);
	}

	&:hover {
		box-shadow: 0px 0px 0px 1px inset var(--primary-color);
	}

	@container (max-width: 650px) {
		.header-box {
			.time {
				display: none;
			}
		}
		.main-box {
			.actions-box {
				display: none;
			}
		}
		.footer-box {
			display: flex;
		}
	}
}
</style>
